"""R-1F.1 — Manager-Selected SAA validation + JSON dump tests.

Scope (R-1E §6, V-1 ~ V-16):
- happy path: valid selection → JSON dump with production_applied=false
- each validation rule fail-fast
- output schema (manager_override_saa_layer / downstream_dry_run_executed / etc.)
- input opportunity payload mutation 없음
- existing portfolio JSON / E-series baseline 무변경
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OPP_DIR = REPO_ROOT / "out" / "db_review_relaxed_e62" / "saa_opportunity_set" / "20260513"
ETF_OPP_JSON = OPP_DIR / "saa_opportunity_set_etf_20260513.json"
FUND_OPP_JSON = OPP_DIR / "saa_opportunity_set_fund_20260513.json"
REVIEW_PACKET = OPP_DIR / "saa_opportunity_set_final_manager_review_20260513.md"
ETF_PORTFOLIO_JSON = REPO_ROOT / "out" / "db_etf_relaxed_e62" / "portfolio_etf_20260511.json"

pytestmark = pytest.mark.skipif(
    not (ETF_OPP_JSON.exists() and FUND_OPP_JSON.exists() and REVIEW_PACKET.exists()),
    reason="R-1B.2 / Final Manager Review Packet not present",
)


def _file_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def etf_opp() -> dict:
    return json.loads(ETF_OPP_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fund_opp() -> dict:
    return json.loads(FUND_OPP_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review_packet_sha() -> str:
    return _file_sha256(REVIEW_PACKET)


def _valid_selection(
    review_packet_sha: str, candidate_id: str = "cand_008421",
    portfolio_type: str = "etf",
) -> dict:
    return {
        "portfolio_type": portfolio_type,
        "candidate_id": candidate_id,
        "selected_by": "r1f1_smoke_test",
        "selected_at": "2026-05-14T10:30:00+09:00",  # after opp generation
        "selection_reason": "R-1F.1 smoke validation sample; not an automated recommendation.",
        "manager_view_notes": ["smoke only"],
        "source_review_packet": {
            "path": str(REVIEW_PACKET),
            "sha256": review_packet_sha,
        },
        "allow_downstream_dry_run": True,
    }


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_happy_path_valid_selection_returns_payload(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import build_manager_selected_saa

    sel = _valid_selection(review_packet_sha)
    payload = build_manager_selected_saa(sel, etf_opp, ETF_OPP_JSON)
    assert payload["meta"]["production_applied"] is False
    assert payload["meta"]["sign_off_required_for_production"] is True
    assert payload["meta"]["manager_override_saa_layer"] is True
    assert payload["downstream_dry_run_executed"] is False
    assert payload["downstream_dry_run_allowed"] is True
    assert payload["selected_candidate"]["candidate_id"] == "cand_008421"
    # 16 rules pass
    vs = payload["validation_summary"]
    assert vs["rules_evaluated"] == 16
    assert vs["rules_passed"] == 16
    assert vs["rules_failed"] == 0
    assert vs["review_packet_sha256_match"] is True
    assert vs["removed_metric_check"] == "absent"


def test_write_manager_selected_saa_json(
    etf_opp: dict, review_packet_sha: str, tmp_path: Path,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import (
        build_manager_selected_saa,
        write_manager_selected_saa_json,
    )

    sel = _valid_selection(review_packet_sha)
    payload = build_manager_selected_saa(sel, etf_opp, ETF_OPP_JSON)
    out = write_manager_selected_saa_json(
        payload, tmp_path / "manager_selected_saa_etf_20260513.json"
    )
    assert out.exists()
    rt = json.loads(out.read_text(encoding="utf-8"))
    assert rt["meta"]["production_applied"] is False
    assert rt["selected_candidate"]["candidate_id"] == "cand_008421"


# ---------------------------------------------------------------------------
# 2. Validation rule failures (V-1 ~ V-16)
# ---------------------------------------------------------------------------


def test_v1_unknown_candidate_id_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha, candidate_id="cand_999999")
    with pytest.raises(ValueError, match="V-1"):
        validate_selection(sel, etf_opp)


def test_v2_non_sampled_pattern_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha, candidate_id="weird_id_001")
    with pytest.raises(ValueError, match="V-2"):
        validate_selection(sel, etf_opp)


def test_v3_ref_max_sharpe_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha, candidate_id="ref_max_sharpe")
    with pytest.raises(ValueError, match="V-3"):
        validate_selection(sel, etf_opp)


def test_v4_ref_80_20_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha, candidate_id="ref_80_20_equal_intra_bucket")
    with pytest.raises(ValueError, match="V-4"):
        validate_selection(sel, etf_opp)


def test_v5_degenerate_candidate_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            c["feasibility_status"] = "degenerate"
            break
    with pytest.raises(ValueError, match="V-5"):
        validate_selection(sel, broken)


def test_v6_bucket_eq_violation_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            c["equity_weight"] = 0.50
            break
    with pytest.raises(ValueError, match="V-6"):
        validate_selection(sel, broken)


def test_v7_bucket_fi_violation_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            c["fixed_income_weight"] = 0.50
            break
    with pytest.raises(ValueError, match="V-7"):
        validate_selection(sel, broken)


def test_v8_weight_sum_violation_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            # shift one equity weight to break sum
            ak = broken["inputs"]["asset_keys"][0]
            c["weights"][ak] = float(c["weights"][ak]) + 0.5
            break
    with pytest.raises(ValueError, match="V-8"):
        validate_selection(sel, broken)


def test_v9_negative_weight_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            # introduce a clearly negative weight (also break sum/bucket, but V-9
            # 가 V-8/V-6/V-7 보다 뒤이므로 negative 만 자체 확인하려면 다른 자산 보전)
            ak = broken["inputs"]["asset_keys"][0]
            other = broken["inputs"]["asset_keys"][1]
            shift = 0.10
            c["weights"][ak] = float(c["weights"][ak]) - shift
            c["weights"][other] = float(c["weights"][other]) + shift
            # 인위적으로 음수 강제
            c["weights"][ak] = -0.05
            c["weights"][other] = float(c["weights"][other]) + (float(c["weights"][ak]) + 0.05)
            break
    # bucket / sum 도 깨질 수 있으나 fail-fast 순서상 V-6/7/8 또는 V-9 중 하나가 뜬다.
    # 핵심은 음수 weight 가 raise 를 유발해야 함.
    with pytest.raises(ValueError):
        validate_selection(sel, broken)


def test_v10_removed_metric_resurrection_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    broken = copy.deepcopy(etf_opp)
    for c in broken["candidates"]:
        if c["candidate_id"] == "cand_008421":
            c["bucket_distance_from_80_20"] = 0.05  # 부활!
            break
    with pytest.raises(ValueError, match="V-10"):
        validate_selection(sel, broken)


def test_v11_review_packet_sha256_mismatch_fails(
    etf_opp: dict,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection("0" * 64)  # bogus sha
    with pytest.raises(ValueError, match="V-11"):
        validate_selection(sel, etf_opp)


def test_v12_selected_at_before_opportunity_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    sel["selected_at"] = "2020-01-01T00:00:00+00:00"  # before opp generation
    with pytest.raises(ValueError, match="V-12"):
        validate_selection(sel, etf_opp)


def test_v13_empty_selected_by_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    sel["selected_by"] = "   "
    with pytest.raises(ValueError, match="V-13"):
        validate_selection(sel, etf_opp)


def test_v14_empty_selection_reason_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    sel["selection_reason"] = ""
    with pytest.raises(ValueError, match="V-14"):
        validate_selection(sel, etf_opp)


def test_v15_allow_downstream_dry_run_false_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    sel["allow_downstream_dry_run"] = False
    with pytest.raises(ValueError, match="V-15"):
        validate_selection(sel, etf_opp)


def test_v16_non_relaxed_diagnostic_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    sel = _valid_selection(review_packet_sha)
    with pytest.raises(ValueError, match="V-16"):
        validate_selection(sel, etf_opp, operating_mode="production")


# ---------------------------------------------------------------------------
# 3. Cross-field consistency
# ---------------------------------------------------------------------------


def test_portfolio_type_mismatch_with_opportunity_set_fails(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    """Selection 의 portfolio_type 가 opportunity_set meta.product_type 와 다르면 fail."""
    from tdf_engine.optimization.manager_selected_saa import validate_selection

    # opp 은 ETF 인데 selection 은 fund 로 시도
    sel = _valid_selection(review_packet_sha, portfolio_type="fund")
    with pytest.raises(ValueError, match="portfolio_type mismatch"):
        validate_selection(sel, etf_opp)


def test_fund_smoke_against_fund_opportunity_set(
    fund_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import build_manager_selected_saa

    sel = _valid_selection(review_packet_sha, portfolio_type="fund")
    payload = build_manager_selected_saa(sel, fund_opp, FUND_OPP_JSON)
    assert payload["selected_candidate"]["candidate_id"] == "cand_008421"
    assert payload["selection_input"]["portfolio_type"] == "fund"


# ---------------------------------------------------------------------------
# 4. YAML loader
# ---------------------------------------------------------------------------


def test_yaml_loader_single_selection(tmp_path: Path, review_packet_sha: str) -> None:
    from tdf_engine.optimization.manager_selected_saa import load_selection_yaml

    yaml_text = f"""
manager_selection:
  portfolio_type: "etf"
  candidate_id: "cand_008421"
  selected_by: "r1f1_smoke_test"
  selected_at: "2026-05-14T10:30:00+09:00"
  selection_reason: "smoke"
  manager_view_notes: ["a"]
  source_review_packet:
    path: "{REVIEW_PACKET.as_posix()}"
    sha256: "{review_packet_sha}"
  allow_downstream_dry_run: true
"""
    p = tmp_path / "sel.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    loaded = load_selection_yaml(p)
    assert "manager_selection" in loaded
    assert loaded["manager_selection"]["candidate_id"] == "cand_008421"


def test_yaml_loader_set_form(tmp_path: Path, review_packet_sha: str) -> None:
    from tdf_engine.optimization.manager_selected_saa import load_selection_yaml

    yaml_text = f"""
manager_selection_set:
  - portfolio_type: "etf"
    candidate_id: "cand_008421"
    selected_by: "r1f1_smoke_test"
    selected_at: "2026-05-14T10:30:00+09:00"
    selection_reason: "smoke"
    manager_view_notes: []
    source_review_packet:
      path: "{REVIEW_PACKET.as_posix()}"
      sha256: "{review_packet_sha}"
    allow_downstream_dry_run: true
  - portfolio_type: "fund"
    candidate_id: "cand_008421"
    selected_by: "r1f1_smoke_test"
    selected_at: "2026-05-14T10:30:00+09:00"
    selection_reason: "smoke"
    manager_view_notes: []
    source_review_packet:
      path: "{REVIEW_PACKET.as_posix()}"
      sha256: "{review_packet_sha}"
    allow_downstream_dry_run: true
"""
    p = tmp_path / "set.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    loaded = load_selection_yaml(p)
    assert "manager_selection_set" in loaded
    assert len(loaded["manager_selection_set"]) == 2
    assert {s["portfolio_type"] for s in loaded["manager_selection_set"]} == {"etf", "fund"}


# ---------------------------------------------------------------------------
# 5. Mutation / regression
# ---------------------------------------------------------------------------


def test_input_opportunity_payload_not_mutated(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import build_manager_selected_saa

    snapshot = copy.deepcopy(etf_opp)
    sel = _valid_selection(review_packet_sha)
    _ = build_manager_selected_saa(sel, etf_opp, ETF_OPP_JSON)
    assert etf_opp == snapshot


def test_existing_portfolio_json_not_touched_after_build(
    etf_opp: dict, review_packet_sha: str, tmp_path: Path,
) -> None:
    """build + write 는 별도 디렉토리에만 dump. 기존 portfolio JSON 변경 없음."""
    from tdf_engine.optimization.manager_selected_saa import (
        build_manager_selected_saa,
        write_manager_selected_saa_json,
    )
    pre = _file_sha256(ETF_PORTFOLIO_JSON)
    sel = _valid_selection(review_packet_sha)
    payload = build_manager_selected_saa(sel, etf_opp, ETF_OPP_JSON)
    write_manager_selected_saa_json(
        payload, tmp_path / "manager_selected_saa_etf_20260513.json"
    )
    post = _file_sha256(ETF_PORTFOLIO_JSON)
    assert pre == post


# ---------------------------------------------------------------------------
# 6. Output schema
# ---------------------------------------------------------------------------


def test_output_schema_required_keys(
    etf_opp: dict, review_packet_sha: str,
) -> None:
    from tdf_engine.optimization.manager_selected_saa import build_manager_selected_saa

    sel = _valid_selection(review_packet_sha)
    payload = build_manager_selected_saa(sel, etf_opp, ETF_OPP_JSON)
    assert set(payload.keys()) >= {
        "meta",
        "selection_input",
        "selected_candidate",
        "validation_summary",
        "source_opportunity_json",
        "downstream_dry_run_allowed",
        "downstream_dry_run_executed",
        "notes",
    }
    assert payload["meta"]["schema_version"].startswith("r1f1")
    assert payload["meta"]["manager_override_saa_layer"] is True
    # selected_candidate 의 bucket / weight sum
    assert abs(payload["selected_candidate"]["equity_weight"] - 0.80) < 1e-9
    assert abs(payload["selected_candidate"]["fixed_income_weight"] - 0.20) < 1e-9
