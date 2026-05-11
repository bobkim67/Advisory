"""UniverseTool — facade.

Phase C-pre:
  - classifier 룰을 yaml 에서 로드 가능 (생성자 주입 또는 ConfigLoader fallback).
  - diagnostics 강화: total_products, passed_filter_count, classified_count,
    unclassified_count, classified_by_asset_class, unclassified_samples,
    asset_classes_with_zero_count, match_reasons_by_asset_class.
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from datetime import date
from typing import Any, TYPE_CHECKING

from tdf_engine.domain.enums import ProductType
from tdf_engine.domain.models import ProductInfo, UniverseResult
from tdf_engine.universe.classifier import ProductClassifier
from tdf_engine.universe.filters import FilterConfig, UniverseFilter

if TYPE_CHECKING:  # pragma: no cover
    from tdf_engine.repositories.interfaces import ProductRepository

logger = logging.getLogger(__name__)


def _parse_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return None
        return float(v)
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    s = s.replace(",", "")
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date_yyyymmdd(v) -> date | None:
    if v is None:
        return None
    s = str(v).strip()
    if len(s) < 8:
        return None
    try:
        y = int(s[:4])
        m = int(s[4:6])
        d = int(s[6:8])
        return date(y, m, d)
    except ValueError:
        return None


def _row_to_product_info(row: dict) -> ProductInfo:
    return ProductInfo(
        product_id=str(row.get("상품번호", "") or "").strip(),
        fund_code=str(row.get("제로인협회펀드코드", "") or "").strip() or None,
        name=str(row.get("펀드명(Short)", "") or "").strip(),
        product_type=ProductType.ETF,  # caller 가 덮어씀
        kis_asset_class=str(row.get("대유형(KIS MP)", "") or "").strip(),
        sub_type=str(row.get("소유형", "") or "").strip(),
        region=(str(row.get("지역", "") or "").strip() or None),
        theme=(str(row.get("테마", "") or "").strip() or None),
        manager=str(row.get("운용사", "") or "").strip(),
        inception_date=_parse_date_yyyymmdd(row.get("설정일")),
        risk_grade=(str(row.get("위험등급", "") or "").strip() or None),
        quant_score=_parse_float(row.get("정량평가")),
        quant_grade=(str(row.get("정량평가등급", "") or "").strip() or None),
        return_1y=_parse_float(row.get("수익률(1Y)")),
        return_3y=_parse_float(row.get("수익률(3Y)")),
        sharpe_1y=_parse_float(row.get("수정샤프(1Y)")),
        aum=_parse_float(row.get("운용규모")),
        investment_limit=_parse_float(row.get("투자한도")),
    )


class UniverseTool:
    def __init__(
        self,
        repo: "ProductRepository",
        universe_config: dict[str, Any],
        product_type: ProductType,
        classifier: ProductClassifier | None = None,
    ):
        self.repo = repo
        self.universe_config = universe_config
        self.product_type = product_type
        self.filter = UniverseFilter(self._build_filter_config())
        self.classifier = classifier or ProductClassifier()

    def _build_filter_config(self) -> FilterConfig:
        common = self.universe_config.get("common", {}) or {}
        type_block = self.universe_config.get(self.product_type.value, {}) or {}

        kws = list(common.get("exclude_keywords") or [])
        kws.extend(type_block.get("exclude_keywords_extra") or [])

        synth = (common.get("synthetic_policy") or {})
        return FilterConfig(
            include_kis_mp_categories=tuple(common.get("include_kis_mp_categories") or []),
            exclude_keywords=tuple(kws),
            exclude_sub_types=tuple(common.get("exclude_sub_types") or []),
            synthetic_mode=str(synth.get("mode", "whitelist")),
            synthetic_whitelist=tuple(synth.get("whitelist_keywords") or []),
        )

    def _load_raw(self):
        if self.product_type is ProductType.ETF:
            return self.repo.load_etf_universe()
        return self.repo.load_fund_universe()

    def run(self) -> UniverseResult:
        raw = self._load_raw()
        raw_count = int(len(raw))

        products: list[ProductInfo] = []
        excluded: list[tuple[ProductInfo, str]] = []
        unclassified_samples: list[dict] = []
        classified_counter: Counter = Counter()
        match_reasons_by_class: dict[str, list[str]] = defaultdict(list)
        passed_filter_count = 0

        for _, r in raw.iterrows():
            row = r.to_dict()
            base = _row_to_product_info(row)
            base = ProductInfo(**{**base.__dict__, "product_type": self.product_type})

            ex, reason = self.filter.is_excluded(row)
            if ex:
                excluded.append((base, reason or "excluded"))
                continue
            passed_filter_count += 1

            asset_key, match_reason = self.classifier.classify(row)
            if asset_key is None:
                if len(unclassified_samples) < 25:
                    unclassified_samples.append(
                        {
                            "product_id": base.product_id,
                            "name": base.name,
                            "kis_asset_class": base.kis_asset_class,
                            "sub_type": base.sub_type,
                            "region": base.region,
                        }
                    )
                excluded.append((base, "classify: no_asset_match"))
                continue

            classified_counter[asset_key] += 1
            if len(match_reasons_by_class[asset_key]) < 5:
                match_reasons_by_class[asset_key].append(
                    f"{base.product_id}:{base.name[:30]} ← {match_reason}"
                )
            products.append(
                ProductInfo(**{**base.__dict__, "mvo_asset_class": asset_key})
            )

        # zero-count 자산군: 룰에는 등장하지만 매칭 0인 asset_key 들
        rule_asset_keys = {r.asset_key for r in self.classifier.rules}
        zero_count = sorted(rule_asset_keys - set(classified_counter.keys()))

        diagnostics = {
            "product_type": self.product_type.value,
            "total_products": raw_count,
            "raw_count": raw_count,                          # B 호환
            "passed_filter_count": passed_filter_count,
            "classified_count": len(products),
            "unclassified_count": passed_filter_count - len(products),
            "filtered_count": len(products),                 # B 호환
            "excluded_count": len(excluded),
            "classified_by_asset_class": dict(classified_counter),
            "asset_classes_with_zero_count": zero_count,
            "unclassified_samples": unclassified_samples,
            "match_reasons_by_asset_class": {
                k: v for k, v in match_reasons_by_class.items()
            },
        }

        return UniverseResult(
            raw_count=raw_count,
            filtered_count=len(products),
            products=products,
            excluded=excluded,
            diagnostics=diagnostics,
        )
