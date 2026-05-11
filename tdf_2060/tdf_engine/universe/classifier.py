"""ProductClassifier — ETF/Fund row → MVO 자산군 매핑.

Phase C-pre:
  - 룰을 yaml (`universe_classification.yaml`) 로 외부화.
  - YAML 부재 시 DEFAULT_RULES (코드 룰) 폴백.
  - classify() 가 (asset_key, match_reason) 반환.
  - 룰은 priority 오름차순 정렬 후 첫 매칭 우선.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassificationRule:
    asset_key: str
    priority: int = 100
    keywords_any: tuple[str, ...] = ()       # = include_keywords
    kis_mp_categories: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    name_excludes: tuple[str, ...] = ()
    sub_types: tuple[str, ...] = ()


# ── code-default fallback (yaml 부재 시 사용) ─────────────────────────
DEFAULT_RULES: list[ClassificationRule] = [
    ClassificationRule(
        asset_key="us_high_yield",
        priority=10,
        keywords_any=("하이일드", "High Yield", "HY", "Hi-Yield"),
    ),
    ClassificationRule(
        asset_key="us_treasury_30y",
        priority=20,
        keywords_any=(
            "미국30년", "미국 30년", "미국국채30", "美30Y", "TLT", "EDV", "30년국채",
            "미국장기국채", "미국 장기국채", "미국장기채", "장기미국채",
            "미국투자등급장기채", "미국투자등급장기채권",
            "US Treasury", "UST 30",
        ),
        name_excludes=("하이일드",),
    ),
    ClassificationRule(
        asset_key="kr_treasury_10y",
        priority=30,
        kis_mp_categories=("국내채권",),
        keywords_any=(
            "국고채10", "국고채 10", "국고10년", "10년국고",
            "장기국공채", "중기국공채", "국공채", "국채",
        ),
        name_excludes=(
            "미국", "회사채", "하이일드", "단기", "초단기", "MMF", "머니마켓", "단기국공채",
        ),
    ),
    ClassificationRule(
        asset_key="kr_aggregate_bond",
        priority=40,
        kis_mp_categories=("국내채권",),
        name_excludes=("국고채10", "국고채 10", "미국", "하이일드"),
    ),
    ClassificationRule(
        asset_key="us_growth_equity",
        priority=50,
        regions=("미국",),
        keywords_any=("성장", "그로스", "Growth", "나스닥", "Nasdaq", "NASDAQ"),
    ),
    ClassificationRule(
        asset_key="us_value_equity",
        priority=60,
        regions=("미국",),
        keywords_any=("가치", "Value", "배당"),
    ),
    ClassificationRule(
        asset_key="em_equity",
        priority=70,
        kis_mp_categories=("신흥국주식",),
    ),
    ClassificationRule(
        asset_key="em_equity",
        priority=71,
        regions=(
            "중국", "인도", "베트남", "인도네시아", "브라질",
            "신흥국", "멕시코", "필리핀", "대만", "중국+베트남",
        ),
    ),
    ClassificationRule(
        asset_key="dm_ex_us_equity",
        priority=80,
        kis_mp_categories=("글로벌주식",),
        regions=("일본", "유럽", "독일", "아시아", "글로벌선진국"),
    ),
    ClassificationRule(
        asset_key="dm_ex_us_equity",
        priority=81,
        keywords_any=("선진국",),
    ),
    ClassificationRule(
        asset_key="kr_equity",
        priority=90,
        kis_mp_categories=("국내주식",),
        regions=("국내",),
    ),
]


def rules_from_yaml(raw: dict[str, Any] | None) -> list[ClassificationRule]:
    """yaml dict → list[ClassificationRule]. raw 가 None/빈 dict 면 빈 리스트."""
    if not raw:
        return []
    out: list[ClassificationRule] = []
    for entry in raw.get("classification_rules", []) or []:
        out.append(
            ClassificationRule(
                asset_key=str(entry["asset_key"]),
                priority=int(entry.get("priority", 100)),
                keywords_any=tuple(entry.get("include_keywords") or entry.get("keywords_any") or ()),
                kis_mp_categories=tuple(entry.get("kis_mp_categories") or ()),
                regions=tuple(entry.get("regions") or ()),
                name_excludes=tuple(
                    entry.get("name_excludes") or entry.get("exclude_keywords") or ()
                ),
                sub_types=tuple(entry.get("sub_types") or ()),
            )
        )
    return out


def load_rules(raw_yaml: dict[str, Any] | None) -> list[ClassificationRule]:
    """yaml 우선, 없으면 DEFAULT_RULES. priority 오름차순 정렬."""
    rules = rules_from_yaml(raw_yaml) if raw_yaml else []
    if not rules:
        rules = list(DEFAULT_RULES)
    rules.sort(key=lambda r: r.priority)
    return rules


class ProductClassifier:
    """단일 product (row dict) 를 MVO 자산군 (asset_key) 에 매핑."""

    def __init__(self, rules: list[ClassificationRule] | None = None):
        if rules is None:
            rules = list(DEFAULT_RULES)
        # 항상 priority 정렬
        self.rules = sorted(rules, key=lambda r: r.priority)

    def classify(self, row: dict) -> tuple[str | None, str | None]:
        """반환: (asset_key 또는 None, match_reason 또는 None).

        match_reason 예: "kis_mp=국내채권 + keyword=국고채10"
        """
        name = str(row.get("펀드명(Short)", "") or "")
        kis = str(row.get("대유형(KIS MP)", "") or "")
        region = str(row.get("지역", "") or "")

        for rule in self.rules:
            if rule.kis_mp_categories and kis not in rule.kis_mp_categories:
                continue
            if rule.regions and region not in rule.regions:
                continue
            if rule.name_excludes and any(ex and ex in name for ex in rule.name_excludes):
                continue
            matched_kw: str | None = None
            if rule.keywords_any:
                matched_kw = next(
                    (kw for kw in rule.keywords_any if kw and kw in name), None
                )
                if matched_kw is None:
                    continue

            parts: list[str] = []
            if rule.kis_mp_categories:
                parts.append(f"kis_mp={kis}")
            if rule.regions:
                parts.append(f"region={region}")
            if matched_kw is not None:
                parts.append(f"keyword='{matched_kw}'")
            if not parts:
                parts.append("rule_only")
            return rule.asset_key, " + ".join(parts)
        return None, None
