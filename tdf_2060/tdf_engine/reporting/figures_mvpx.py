"""Phase E-6.2 (MVP-X) — 1-page integrated bridge.

운용역이 한 페이지에서 다음 문장을 읽을 수 있게 하는 정적 시각화:

    "이 국면 판단을 바탕으로 SAA가 산출되었고,
     TAA tilt와 projection 조정을 거쳐 최종 자산배분이 만들어졌으며,
     그 결과 이런 상품들이 선택되었다."

7 섹션 vertical flow (단일 PNG):
    1. Header                — product_type / as_of_date / source / regime / quality
    2. Regime                — current card + placement·velocity + 5-obs mini timeline
    3. SAA (direct)          — diagnostics.saa_diagnostics.saa_weights (E-6.2 T-6 필수)
    4. SAA → TAA bridge      — direct SAA + (TAA target − SAA) tilt magnitude
    5. Projection            — pre/post bucket + clipping/redistribution
    6. Final asset           — asset_allocation[].final_asset_weight
    7. Product top           — product_allocation 상위 8

Hard requirements (사용자 명시 — 본 모듈은 이를 enforce):
    - SAA 는 direct telemetry (`saa_diagnostics.saa_weights`) 만 사용. inferred 경로 없음.
      missing 이면 ValueError 명시 raise.
    - allocation/optimizer/TAA/projection/selection/config 미참조 (read-only on dict).
    - 입력 portfolio dict / json 파일 모두 mutation 없음 (caller 가 deepcopy 권장).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import gridspec as _gridspec  # noqa: E402

# 색상 / 라벨은 figures.py 와 정합
from tdf_engine.reporting.figures import (
    BUCKET_COLORS,
    DRIFT_SOURCE_COLORS,
    RELAXED_TAG,
    RISK_ASSET_KEYS,
    _asset_color,
    _short,
    load_portfolio_json,
)


MVPX_FIG_SIZE: tuple[float, float] = (12.0, 20.5)
MVPX_DPI: int = 140

REGIME_QUADRANT_LABELS: dict[int, str] = {
    1: "Expansion / Acceleration",
    2: "Expansion / Deceleration",
    3: "Contraction / Deceleration",
    4: "Contraction / Acceleration",
}


# ---------------------------------------------------------------------------
# Telemetry extractors (read-only, with explicit validation)
# ---------------------------------------------------------------------------


def _require_direct_saa_telemetry(portfolio: dict[str, Any]) -> dict[str, float]:
    """E-6.2 (T-6) — direct SAA weights. 미존재 시 명시 ValueError.

    inferred (taa_target − asset_tilts) 경로는 본 모듈에서 절대 사용하지 않는다.
    """
    diag = portfolio.get("diagnostics") or {}
    saa_diag = diag.get("saa_diagnostics") or {}
    saa_w = saa_diag.get("saa_weights")
    if not saa_w or not isinstance(saa_w, dict):
        raise ValueError(
            "MVP-X requires direct SAA telemetry at "
            "`diagnostics.saa_diagnostics.saa_weights` (E-6.2 T-6). "
            "Inferred SAA (taa_target − asset_tilts) is explicitly disallowed. "
            "Re-run build_portfolio with the E-6.2 telemetry patch applied."
        )
    out: dict[str, float] = {}
    for k, v in saa_w.items():
        out[str(k)] = float(v)
    return out


def _taa_target(portfolio: dict[str, Any]) -> dict[str, float]:
    feas = (
        ((portfolio.get("diagnostics") or {}).get("taa_diagnostics") or {})
        .get("taa_feasibility")
        or {}
    )
    raw = feas.get("target_weights_before_projection") or {}
    return {str(k): float(v) for k, v in raw.items()}


def _bucket_by_asset(portfolio: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in portfolio.get("asset_allocation") or []:
        out[str(r.get("asset_key"))] = str(r.get("bucket") or "")
    return out


def _final_by_asset(portfolio: dict[str, Any]) -> dict[str, float]:
    return {
        str(r.get("asset_key")): float(r.get("final_asset_weight") or 0.0)
        for r in portfolio.get("asset_allocation") or []
    }


def _ordered_asset_keys(portfolio: dict[str, Any]) -> list[str]:
    """bucket 그룹 (equity → fixed_income → 기타) + 영문 key 정렬."""
    rows = portfolio.get("asset_allocation") or []
    bucket_order = {"equity": 0, "fixed_income": 1}
    keyed = [
        (
            bucket_order.get(str(r.get("bucket") or ""), 9),
            str(r.get("asset_key") or ""),
        )
        for r in rows
    ]
    return [k for _, k in sorted(keyed)]


# ---------------------------------------------------------------------------
# Section renderers (each takes an Axes)
# ---------------------------------------------------------------------------


def _section_header(ax: plt.Axes, portfolio: dict[str, Any]) -> None:
    """Header: title (top) / sub-meta (mid) / relaxed disclaimer (bottom).

    polish #1: subplot 안에서 3 행을 충분한 간격으로 분산.
    """
    ax.set_axis_off()
    rs = portfolio.get("review_summary") or {}
    diag = portfolio.get("diagnostics") or {}
    regime = diag.get("regime") or {}
    db = diag.get("db_source") or {}
    pt = str(portfolio.get("portfolio_type", "")).upper() or "—"
    as_of = str(rs.get("as_of_date") or portfolio.get("as_of_date") or "—")
    source = str(rs.get("source_type") or db.get("source_type") or "file")
    quality = str(rs.get("quality_status") or "—")
    regime_id = regime.get("regime")
    regime_label = regime.get("regime_label") or "—"

    title = f"TDF 2060 — {pt} Portfolio Construction Bridge"
    sub = (
        f"as_of_date={as_of}  ·  source={source}  ·  "
        f"quality={quality}  ·  regime={regime_id} ({regime_label})"
    )
    ax.text(
        0.0, 0.85, title, fontsize=16, fontweight="bold", transform=ax.transAxes,
        va="top",
    )
    ax.text(
        0.0, 0.45, sub, fontsize=10.5, transform=ax.transAxes, color="#333",
        va="center",
    )
    ax.text(
        0.0, 0.05,
        f"{RELAXED_TAG}  ·  Read-only diagnostic. Allocation logic was not re-executed.",
        fontsize=9,
        transform=ax.transAxes,
        color="#7a3a3a",
        va="bottom",
    )


def _section_regime(ax_card: plt.Axes, ax_timeline: plt.Axes, portfolio: dict[str, Any]) -> None:
    """좌: 현재 regime card. 우: 5-obs mini timeline (P/V & regime stripe)."""
    diag = portfolio.get("diagnostics") or {}
    regime = diag.get("regime") or {}

    # ── card
    ax_card.set_axis_off()
    regime_id = regime.get("regime")
    regime_label = regime.get("regime_label") or "—"
    placement = regime.get("placement")
    velocity = regime.get("velocity")
    region = regime.get("region") or "—"
    as_of = regime.get("as_of") or "—"

    def fmt(v: Any) -> str:
        try:
            return f"{float(v):+.4f}"
        except (TypeError, ValueError):
            return "n/a"

    ax_card.text(
        0.02, 0.92, "1. Regime State",
        fontsize=12, fontweight="bold", transform=ax_card.transAxes,
    )
    ax_card.text(
        0.02, 0.72, f"Regime  :  {regime_id}  ({regime_label})",
        fontsize=11, transform=ax_card.transAxes,
    )
    ax_card.text(
        0.02, 0.55, f"Region  :  {region}",
        fontsize=10.5, transform=ax_card.transAxes,
    )
    ax_card.text(
        0.02, 0.42, f"as_of   :  {as_of}",
        fontsize=10.5, transform=ax_card.transAxes,
    )
    ax_card.text(
        0.02, 0.27, f"Placement: {fmt(placement)}",
        fontsize=10.5, transform=ax_card.transAxes,
    )
    ax_card.text(
        0.02, 0.14, f"Velocity : {fmt(velocity)}",
        fontsize=10.5, transform=ax_card.transAxes,
    )
    quad = REGIME_QUADRANT_LABELS.get(int(regime_id) if regime_id is not None else 0)
    if quad:
        ax_card.text(
            0.02, 0.00, f"Quadrant : {quad}",
            fontsize=10, color="#555", transform=ax_card.transAxes,
        )

    # ── timeline
    history = list(regime.get("history") or [])
    ax_timeline.set_title("Regime mini-timeline (latest observations)", fontsize=10)
    if not history:
        ax_timeline.text(
            0.5, 0.5, "regime.history 미존재 — E-6.2 telemetry 필요",
            ha="center", va="center", transform=ax_timeline.transAxes,
            fontsize=10, color="#7a3a3a",
        )
        ax_timeline.set_axis_off()
        return

    xs = list(range(len(history)))
    p = [float(h.get("placement") or 0.0) for h in history]
    v = [float(h.get("velocity") or 0.0) for h in history]
    labels = [str(h.get("as_of") or "") for h in history]
    regimes = [int(h.get("regime") or 0) for h in history]

    ax_timeline.plot(xs, p, marker="o", color="#3a6db0", label="Placement")
    ax_timeline.plot(xs, v, marker="s", color="#c97a2a", label="Velocity")
    ax_timeline.axhline(0, color="#888", linewidth=0.6)
    ax_timeline.set_xticks(xs)
    ax_timeline.set_xticklabels(labels, fontsize=8, rotation=15, ha="right")
    ax_timeline.grid(axis="y", linestyle=":", alpha=0.4)
    ax_timeline.legend(loc="best", fontsize=8)
    # regime label annotation (last)
    ax_timeline.text(
        xs[-1], p[-1], f" R{regimes[-1]}",
        fontsize=8, color="#3a6db0", va="bottom",
    )


_ZERO_WEIGHT_THRESHOLD: float = 0.005  # 0.5% 미만은 zero-bucket 으로 묶는다


def _section_saa(ax: plt.Axes, portfolio: dict[str, Any]) -> None:
    """direct SAA telemetry (saa_diagnostics.saa_weights) horizontal bar.

    polish #4: 0% (또는 < 0.5%) 자산은 bar 에서 생략하고 footer 에 omitted count + 자산명.
    """
    saa = _require_direct_saa_telemetry(portfolio)  # raises if missing
    bucket = _bucket_by_asset(portfolio)
    all_keys = _ordered_asset_keys(portfolio) or list(saa.keys())

    # non-zero / zero 분리
    keys = [k for k in all_keys if saa.get(k, 0.0) >= _ZERO_WEIGHT_THRESHOLD]
    omitted = [k for k in all_keys if saa.get(k, 0.0) < _ZERO_WEIGHT_THRESHOLD]
    weights = [saa.get(k, 0.0) * 100 for k in keys]
    colors = [_asset_color(k, bucket.get(k, "")) for k in keys]

    if not keys:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "no non-zero SAA weights", ha="center", va="center")
        return

    bars = ax.barh(keys, weights, color=colors)
    ax.invert_yaxis()
    ax.set_title(
        "2. SAA Weights (direct telemetry — saa_diagnostics.saa_weights)",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax.set_xlabel("SAA weight (%)")
    upper = max(weights) * 1.18 if weights else 1.0
    ax.set_xlim(0, max(upper, 1.0))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    for bar, w in zip(bars, weights):
        ax.text(
            bar.get_width() + (upper * 0.005),
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%",
            va="center", fontsize=9,
        )

    if omitted:
        omitted_short = ", ".join(omitted[:6]) + ("…" if len(omitted) > 6 else "")
        ax.text(
            1.0, -0.18,
            f"omitted (< {_ZERO_WEIGHT_THRESHOLD * 100:.1f}%): {len(omitted)} assets — {omitted_short}",
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=8.5, color="#666",
        )


def _section_taa_bridge(ax: plt.Axes, portfolio: dict[str, Any]) -> None:
    """SAA(direct) → TAA target overlay + tilt label.

    polish #5: tilt annotation 위치를 그래프 우측 고정 컬럼에 정렬, 양수=▲(녹) /
    음수=▼(적) prefix + light bbox 로 가독성 확보. tilt=0 자산은 생략.
    """
    saa = _require_direct_saa_telemetry(portfolio)
    taa = _taa_target(portfolio)
    keys = _ordered_asset_keys(portfolio) or list(saa.keys())
    saa_pct = [saa.get(k, 0.0) * 100 for k in keys]
    taa_pct = [taa.get(k, 0.0) * 100 for k in keys]
    tilt_pp = [taa.get(k, 0.0) * 100 - saa.get(k, 0.0) * 100 for k in keys]

    import numpy as np

    y = np.arange(len(keys))
    h = 0.4
    ax.barh(y - h / 2, saa_pct, height=h, color="#9aa3ad", label="SAA (direct)")
    ax.barh(y + h / 2, taa_pct, height=h, color="#3a6db0", label="TAA target")
    ax.set_yticks(y)
    ax.set_yticklabels(keys)
    ax.invert_yaxis()
    ax.set_title(
        "3. SAA → TAA Bridge (TAA target = SAA + regime asset_tilts)",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Weight (%)")
    max_bar = max(max(saa_pct), max(taa_pct)) if (saa_pct or taa_pct) else 1.0
    # tilt annotation 을 위해 우측 여백 18% 추가 확보
    upper = max_bar * 1.22
    ax.set_xlim(0, max(upper, 1.0))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9)

    # tilt annotation — 양수/음수 모두 우측 고정 컬럼 (max_bar + 8% margin) 에 정렬
    annot_x = max_bar + (upper * 0.04)
    for i, d in enumerate(tilt_pp):
        if abs(d) < 1e-6:
            continue
        if d > 0:
            arrow, color = "▲", "#2a8a3e"
        else:
            arrow, color = "▼", "#a83232"
        sign = "+" if d > 0 else ""
        ax.text(
            annot_x, i,
            f"{arrow} {sign}{d:.2f}pp",
            va="center", ha="left",
            fontsize=8.5, color=color,
            bbox=dict(
                facecolor="white", edgecolor="none", alpha=0.7, pad=1.0
            ),
        )


def _section_projection(ax: plt.Axes, portfolio: dict[str, Any]) -> None:
    """Pre/post bucket + clipping / redistribution summary.

    polish #2: title 짧게 + metric 5개를 별도 subtitle (한 줄 strip) 으로 분리.
    """
    proj = portfolio.get("projection_summary") or {}
    feas = (
        ((portfolio.get("diagnostics") or {}).get("taa_diagnostics") or {})
        .get("taa_feasibility") or {}
    )
    quality = (portfolio.get("diagnostics") or {}).get("quality") or {}

    eq_bef = float((proj.get("bucket_before") or {}).get("equity", 0.0)) * 100
    fi_bef = float((proj.get("bucket_before") or {}).get("fixed_income", 0.0)) * 100
    eq_aft = float((proj.get("bucket_after") or {}).get("equity", 0.0)) * 100
    fi_aft = float((proj.get("bucket_after") or {}).get("fixed_income", 0.0)) * 100
    max_proj = float(proj.get("max_abs_projection_drift", 0.0)) * 100

    clip = (feas.get("clipping_summary") or {})
    n_clip = int(clip.get("n_clipped", 0))
    clip_total = float(clip.get("clipped_weight_total", 0.0)) * 100

    qcs = quality.get("drift_clipping_summary") or {}
    n_outflow = int(qcs.get("n_assets_with_outflow") or 0)
    n_inflow = int(qcs.get("n_assets_with_inflow") or 0)
    primary = qcs.get("drift_source_primary") or "n/a"
    enforcement = quality.get("enforcement_mode") or "telemetry_only"

    import numpy as np

    labels = ["Equity", "Fixed Income"]
    before = [eq_bef, fi_bef]
    after = [eq_aft, fi_aft]
    x = np.arange(len(labels))
    w = 0.35
    ax.bar(x - w / 2, before, width=w, color="#9aa3ad", label="pre-projection")
    ax.bar(x + w / 2, after, width=w, color="#3a6db0", label="post-projection")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Bucket weight (%)")
    ax.set_ylim(min(0, min(before + after) - 5), max(105, max(before + after) + 10))
    ax.axhline(0, color="#888", linewidth=0.6)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9)

    for xi, v in zip(x - w / 2, before):
        ax.text(xi, v + 1, f"{v:.2f}%", ha="center", fontsize=8, color="#444")
    for xi, v in zip(x + w / 2, after):
        ax.text(xi, v + 1, f"{v:.2f}%", ha="center", fontsize=8)

    # title 짧게 — section number + 핵심 단어 만
    ax.set_title(
        "4. Projection & Clipping",
        fontsize=12, fontweight="bold", loc="left",
    )

    # metric strip — axis 아래 (xlabel 아래) footer 위치, monospace 한 줄
    metric_strip = (
        f"max_proj_drift={max_proj:.2f}%   "
        f"long_only_clipped={n_clip} ({clip_total:.2f}%p)   "
        f"product_outflow={n_outflow} / inflow={n_inflow}   "
        f"primary={primary}   "
        f"enforcement={enforcement}"
    )
    ax.text(
        0.0, -0.32, metric_strip,
        transform=ax.transAxes,
        ha="left", va="top",
        fontsize=8.5, color="#555", family="monospace",
    )


def _section_final(ax: plt.Axes, portfolio: dict[str, Any]) -> None:
    """Final asset weight bar — direction (vs TAA target) 색상으로 표시.

    polish #3: < 0.5% (zero-bucket) 자산은 bar / 라벨 모두 생략, footer 에 omitted count.
    """
    final = _final_by_asset(portfolio)
    taa = _taa_target(portfolio)
    bucket = _bucket_by_asset(portfolio)
    all_keys = _ordered_asset_keys(portfolio) or list(final.keys())

    keys = [k for k in all_keys if final.get(k, 0.0) >= _ZERO_WEIGHT_THRESHOLD]
    omitted = [k for k in all_keys if final.get(k, 0.0) < _ZERO_WEIGHT_THRESHOLD]
    final_pct = [final.get(k, 0.0) * 100 for k in keys]
    diff_pp = [final.get(k, 0.0) * 100 - taa.get(k, 0.0) * 100 for k in keys]
    colors = [_asset_color(k, bucket.get(k, "")) for k in keys]

    if not keys:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "no non-zero final weights", ha="center", va="center")
        return

    bars = ax.barh(keys, final_pct, color=colors)
    ax.invert_yaxis()
    ax.set_title(
        "5. Final Asset Allocation (post-projection · post-product-cap)",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Final asset weight (%)")
    upper = max(final_pct) * 1.20 if final_pct else 1.0
    ax.set_xlim(0, max(upper, 1.0))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    for bar, w, d in zip(bars, final_pct, diff_pp):
        suffix = ""
        color = "#444"
        if abs(d) >= 0.005:
            sign = "+" if d > 0 else ""
            suffix = f"  ({sign}{d:.2f}pp vs TAA)"
            color = "#2a8a3e" if d > 0 else "#a83232"
        ax.text(
            bar.get_width() + (upper * 0.005),
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%{suffix}",
            va="center", fontsize=9, color=color,
        )

    if omitted:
        omitted_short = ", ".join(omitted[:6]) + ("…" if len(omitted) > 6 else "")
        ax.text(
            1.0, -0.18,
            f"omitted (< {_ZERO_WEIGHT_THRESHOLD * 100:.1f}%): {len(omitted)} assets — {omitted_short}",
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=8.5, color="#666",
        )


def _section_products(ax: plt.Axes, portfolio: dict[str, Any], top_n: int = 8) -> None:
    products = list(portfolio.get("product_allocation") or [])
    if not products:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "no products", ha="center", va="center")
        return
    products.sort(key=lambda r: float(r.get("final_weight") or 0.0), reverse=True)
    top = products[:top_n]
    names = [
        f"{_short(r.get('product_name') or r.get('product_id') or '')}  ·  {r.get('manager') or '?'}  ·  [{r.get('asset_key', '')}]"
        for r in top
    ]
    weights = [float(r.get("final_weight") or 0.0) * 100 for r in top]
    colors = [_asset_color(r.get("asset_key", ""), r.get("bucket", "")) for r in top]

    bars = ax.barh(names, weights, color=colors)
    ax.invert_yaxis()
    ax.set_title(
        f"6. Selected Products (Top {len(top)} by final weight)",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Product weight (%)")
    upper = max(weights) * 1.18 if weights else 1.0
    ax.set_xlim(0, max(upper, 1.0))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    for bar, w in zip(bars, weights):
        ax.text(
            bar.get_width() + (upper * 0.005),
            bar.get_y() + bar.get_height() / 2,
            f"{w:.2f}%",
            va="center", fontsize=9,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_mvpx_bridge(
    portfolio: dict[str, Any],
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """1-page integrated bridge PNG. read-only on portfolio dict.

    raises ValueError when direct SAA telemetry is missing (E-6.2 T-6).
    """
    # mutation 방지
    portfolio = deepcopy(portfolio)
    _ = _require_direct_saa_telemetry(portfolio)  # fail-fast

    fig = plt.figure(figsize=MVPX_FIG_SIZE)
    # 7 row layout: header / regime(card+timeline split) / saa / taa-bridge /
    # projection / final / products
    # polish #1 — header 높이 0.6 → 0.95 (3행 분산 공간).
    # polish #2 — projection 1.4 → 1.7 (metric strip subtitle 공간 확보).
    gs = _gridspec.GridSpec(
        nrows=7,
        ncols=2,
        height_ratios=[0.95, 1.4, 2.0, 2.4, 1.7, 2.4, 2.4],
        width_ratios=[1.0, 1.6],
        hspace=0.65,
        wspace=0.10,
        left=0.10,
        right=0.97,
        top=0.97,
        bottom=0.04,
    )

    ax_header = fig.add_subplot(gs[0, :])
    ax_regime_card = fig.add_subplot(gs[1, 0])
    ax_regime_timeline = fig.add_subplot(gs[1, 1])
    ax_saa = fig.add_subplot(gs[2, :])
    ax_taa = fig.add_subplot(gs[3, :])
    ax_proj = fig.add_subplot(gs[4, :])
    ax_final = fig.add_subplot(gs[5, :])
    ax_products = fig.add_subplot(gs[6, :])

    _section_header(ax_header, portfolio)
    _section_regime(ax_regime_card, ax_regime_timeline, portfolio)
    _section_saa(ax_saa, portfolio)
    _section_taa_bridge(ax_taa, portfolio)
    _section_projection(ax_proj, portfolio)
    _section_final(ax_final, portfolio)
    _section_products(ax_products, portfolio)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=MVPX_DPI)
    plt.close(fig)
    return out_path


def build_mvpx_for_portfolio_json(
    portfolio_json: Path,
    out_path: Path,
    *,
    label: str | None = None,
) -> Path:
    """편의 wrapper — JSON 경로 입력. 입력 파일은 변경하지 않는다."""
    portfolio = load_portfolio_json(Path(portfolio_json))
    return render_mvpx_bridge(portfolio, Path(out_path), label=label)


__all__ = [
    "render_mvpx_bridge",
    "build_mvpx_for_portfolio_json",
    "MVPX_FIG_SIZE",
    "MVPX_DPI",
]
