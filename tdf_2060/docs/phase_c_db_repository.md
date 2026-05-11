# Phase C — DB Repository

작성일: 2026-05-07. Phase B / B.5 / B.5+ / C-pre 완료 위에 SCIP DB 연동을 추가.

> **목표**: file repository 기반 입력을 DB repository 기반 입력으로 교체할 수 있게 한다. core(optimization/regime/portfolio) 로직은 DB를 모르고, repository layer에서 흡수한다.

## 1. 범위와 비범위

| 포함 | 제외 |
|---|---|
| `DBMarketDataRepository` (SCIP `back_datapoint`) 구현 | optimization/regime/fallback/selection 고도화 |
| `db_sources.yaml` (asset_key ↔ dataset_id 매핑) | 실 DB 운영 매핑 확정 (운영자 결정 사항) |
| ust30 매핑 정책 (`direct/proxy/synthetic/requires_decision`) | synthetic 모드 실제 구현 (Phase C+ 예정) |
| `parse_data_blob` 표준 helper | regime_source/regime_return DB 모드 (file 폴백 유지) |
| CLI `--source {file|db}` + `--as-of-date` | DB credential 관리 (환경변수 사용) |
| `db_source` diagnostics + payload `source_type` | reporting / 대시보드 |

## 2. 설계

### 2.1 layer 경계

```
core ──────────► OptimizationTool / RegimeAnalysisTool / TAAOverlayTool / PortfolioBuilder
   │                          │
   │                          ▼ (Protocol: MarketDataRepository)
   │                ┌─────────────────────┐
   │                │ FileMarketDataRepo  │  ← Phase B 그대로
   │                │ DBMarketDataRepo    │  ← Phase C 신규 (SCIP back_datapoint)
   │                │ CompositeRepo       │  ← 일부는 DB, 일부는 file 위임
   │                └─────────────────────┘
   ▼
core 는 DB 를 모름. 어떤 repo 든 같은 normalized DataFrame 반환.
```

`load_asset_rt_vol() → DataFrame columns=['Asset Class','Ticker','Name','σ','E[R]']`
`load_corr_matrix() → DataFrame index=Name, columns=Name`

### 2.2 신규/수정 파일

신규
- `tdf_engine/repositories/_blob.py` — `parse_data_blob`
- `tdf_engine/repositories/db_market_data.py` — `DBMarketDataRepository`, `DBSourceDiagnostics`
- `tdf_engine/repositories/composite.py` — `CompositeMarketDataRepository`
- `tdf_engine/config/db_sources.yaml` — asset_key↔dataset_id/dataseries 매핑
- `tests/test_phase_c_db.py` — 7 tests

수정
- `tdf_engine/config/loader.py` — `load_db_sources_raw()`
- `tdf_engine/config/asset_mapping.yaml` — ust30 `db_mapping_mode` 추가
- `tdf_engine/tools/build_portfolio.py` — `--source` / `--as-of-date` 옵션, payload `source_type`/`as_of_date`

### 2.3 DBMarketDataRepository 동작

- 시계열 query: `back_datapoint WHERE dataset_id=? AND dataseries_id=?`
- blob 파싱: `parse_data_blob(blob, currency=...)` (3 패턴: dict / 단일 숫자 / 문자열 숫자)
- σ, E[R] 산출:
  ```
  monthly = levels.resample("ME").last().dropna()
  ret = monthly.pct_change().dropna()
  σ  = ret.std() * sqrt(annualization)
  μ  = ret.mean() * annualization
  ```
  yaml `asset_rt_vol.{lookback_years, annualization}`로 조정.
- 상관행렬: 자산별 월간 수익률 시리즈를 join (`how="any"`) → `corr()`
- `as_of_date` 적용: `s.loc[: as_of_date]`. 그 이후 데이터는 사용하지 않음.
- 결측: silent fill 금지. `DBSourceDiagnostics.{datasets_missing, warnings}`에 기록.
- engine 인자: SQLAlchemy Engine / PyMySQL conn / **`dict[(dataset_id, dataseries_id) → DataFrame]`** in-memory fake — 모두 허용 (테스트 용이성).

### 2.4 CompositeMarketDataRepository

`primary` (DB) 가 `NotImplementedError`를 내면 `fallback` (file) 로 위임. Phase C 1차에서 `regime_source`/`regime_return_source`는 자동으로 file 로 빠짐.

## 3. ust30 매핑 정책

`asset_mapping.yaml::us_treasury_30y.db_mapping_mode` ∈ `{direct, proxy, synthetic, requires_decision}`.
`db_sources.yaml::us_treasury_30y` 가 같은 키로 정합.

| mode | 동작 | 사용 시기 |
|---|---|---|
| `direct` | `dataset_id` 명시 → 그대로 사용 | SCIP에 `USGG30YR` 또는 미국 30Y 시계열이 있을 때 |
| `proxy` | `proxy.proxy_dataset_id` 명시 → 그것을 사용 + `proxy_used=True` 진단 + `proxy_mappings[asset_key]` 기록 | 30Y 미존재 시. `reason` 명시 의무 |
| `synthetic` | (Phase C 미구현) hook만 — `components: [{dataset_id, weight}, ...]` | 합성 시계열 필요 시 Phase C+ |
| `requires_decision` | 즉시 `ValueError` (silent fallback 금지) | 정책 미결정 — 기본값 |

`required=true` + `mapping_mode=requires_decision` 인 자산은 운영자 결정 전에는 DB 모드 실행 자체가 막힘. Phase B의 강한 error 정책과 정합.

## 4. CLI 사용법

```bash
# file 모드 (기본)
python -m tdf_engine.tools.build_portfolio \
    --source-root C:/Users/user/Downloads/python/Advisory \
    --product-type fund \
    --output-dir out

# db 모드
python -m tdf_engine.tools.build_portfolio \
    --source-root C:/Users/user/Downloads/python/Advisory \
    --product-type fund \
    --source db \
    --as-of-date 2026-03-31 \
    --output-dir out
```

DB credential (환경변수, 미지정 시 default):
```
TDF_DB_HOST=${DB_HOST}
TDF_DB_USER=solution
TDF_DB_PASSWORD=${DB_PASSWORD}
TDF_DB_NAME=SCIP
```

DB 연결 실패 시: `RuntimeError("DB 연결 실패 (host=..., db=...): {원인}. 내부망/VPN 또는 환경변수 확인.")`.
ust30 매핑 미결정 시: `ValueError("us_treasury_30y: db_sources.yaml::mapping_mode=requires_decision. 운영자가 direct/proxy/synthetic 중 1개 선택 후 dataset 매핑 명시 필요.")`.

## 5. CLI payload 변경

JSON 최상위에 추가:
- `source_type: "file" | "db"`
- `as_of_date: str | null`

`diagnostics.db_source` (DB 모드 시):
```jsonc
{
  "source_type": "db",
  "datasets_loaded": [144, 11, 12, ...],
  "datasets_missing": [],
  "proxy_used": false,
  "proxy_mappings": {},
  "latest_data_date_by_dataset": {"144": "2026-03-31", "11": "2026-03-30", ...},
  "as_of_date": "2026-03-31",
  "warnings": [],
  "config_path": null
}
```

## 6. 테스트 결과

```
$ pytest tests/ -q
103 passed in 3.97s
```

- Phase A 44 + B 33 + B.5 5 + B.5+ 7 + C-pre 7 + **C 7** = 103
- 신규 (`tests/test_phase_c_db.py`):
  - `test_db_repository_returns_normalized_asset_rt_vol`
  - `test_db_repository_returns_normalized_corr_matrix`
  - `test_db_repository_missing_required_dataset_raises`
  - `test_build_portfolio_source_file_still_works`
  - `test_build_portfolio_source_db_with_fake_repo_produces_valid_result`
  - `test_us_treasury_30y_proxy_records_warning`
  - `test_source_type_is_written_to_output_payload`

실 DB 접속 없이 in-memory `dict[(dataset_id, dataseries_id) → DataFrame]` fake로 검증.

### 6.1 file vs db 동등성

- 형식 정합성: `product_weight_sum=1.0`, `len(asset_weights)=9`, equity bucket ∈ [0.74, 0.86] — 두 모드 동일.
- 수치 동일성: 입력 데이터가 다르면 weights 도 다름. fake 데이터로 비교한 본 테스트는 *형식 정합성*만 검증. 실제 SCIP 시계열을 file과 정확히 동일한 σ/Σ로 산출하려면 `lookback_years`, `annualization`, 월말 정의 등 yaml 파라미터를 file 산출 정책과 맞춰야 함.

### 6.2 실 DB CLI 시도 결과

`--source db --as-of-date 2026-03-31` 으로 실행 시:
```
ValueError: us_treasury_30y: db_sources.yaml::mapping_mode=requires_decision.
  운영자가 direct/proxy/synthetic 중 1개 선택 후 dataset 매핑 명시 필요.
```
의도된 동작. `db_sources.yaml::us_treasury_30y.mapping_mode`를 `direct` 또는 `proxy`로 결정하면 진행.

## 7. 남은 한계

1. **`db_sources.yaml::assets` 의 일부 dataset_id가 null** — 운영자가 SCIP `back_dataset` 조회 후 채워야 함. Phase C 1차는 9개 자산군 중 5개(`kr_equity`, `us_growth_equity`, `us_value_equity`, `dm_ex_us_equity`, `em_equity`)만 알려진 ID 채움.
2. **`regime_source`/`regime_return_source` DB 모드 미구현** — `enabled: false`. file 폴백으로 동작. Phase C+에서 `solution.roboadvisorAPI_economicregime` 활용 검토.
3. **synthetic 모드 미구현** — hook만 열어둠.
4. **수치 동일성 보장 안 됨** — file 산출(현 시점 단일 cross-section) vs DB 산출(시계열 추정)은 정의가 달라 σ/Σ가 자연스럽게 다를 수 있음. 운영 적용 전 file vs DB 결과 차이를 정량 비교 필요.
5. **`back_datapoint.data` blob 기반 시계열 query 비용** — `dataset_id`별 1.6M행 중 일부를 가져오는데, lookback이 길고 자산이 많으면 query 시간 증가 가능. 인덱스 (`dataset_id`, `dataseries_id`)는 존재.
6. **DB credential** — 환경변수 default가 운영 default(`${DB_PASSWORD}`)와 동일. 운영 시 secret manager로 교체 권장.

## 8. Phase C 이후 다음 단계

권장 순서:
1. **운영자가 `db_sources.yaml::assets` 의 null dataset_id 채움** (특히 `kr_aggregate_bond`, `kr_treasury_10y`, `us_treasury_30y`, `us_high_yield`).
   - SCIP `back_dataset`에서 `name LIKE '%KIS%'`, `'%Korea Treasury%'`, `'%30%Year%'`, `'%LF98TRUU%'` 등 후보 조회.
2. **ust30 mapping_mode 결정**: direct가 우선, 없으면 proxy(예: `Treasury 20Y` id=1).
3. **file vs DB 결과 정량 비교** — 동일 augmented fixture로 build → max_abs_drift 측정.
4. **`regime_source` DB 모드 활성** — `solution.roboadvisorAPI_economicregime` 매핑.
5. **GlidePath 엑셀 연동** — DRM 해제 후 `glidepath.yaml` 또는 `solution.roboadvisorAPI_glidepath` 사용.
6. **`final_asset_bounds` hard enforce 정책 합의**.
7. **reporting 모듈** — HTML/대시보드.

---

## 9. Phase C.1 — Semantic Validation + Sanity + Dry-run

### 9.1 트리거

Phase C 1차에서 DB 매핑 *구조*는 완성됐으나 **DB 시계열의 의미가 검증되지 않은 채 MVO에 들어가는 위험**이 남았음:
- yield 시계열에 `pct_change`를 적용하면 "금리 변화율"이지 채권 수익률이 아님.
- spread/macro indicator는 MVO 입력으로 부적합.
- file 산출과 DB 산출이 다를 때 stale data / extreme outlier 등 원인 추적 불가.

Phase C.1는 fallback 추가가 아니라 **검증 layer**를 삽입.

### 9.2 semantic_type / return_transform 정책

`db_sources.yaml::assets[*]`에 `semantic_type` + `return_transform` 추가.
검증 로직: `tdf_engine/repositories/semantic.py::resolve_transform`.

| `semantic_type` | 허용 `return_transform` | default | MVO 사용 |
|---|---|---|---|
| `total_return_index` | `pct_change` | `pct_change` | ✅ |
| `price_index` | `pct_change` | `pct_change` | ✅ |
| `nav` | `pct_change` | `pct_change` | ✅ |
| `return_series` | `already_return` | `already_return` | ✅ |
| `yield` | `diff` / `duration_proxy` / `not_allowed` | **명시 필수** | ⚠️ |
| `spread` | `diff` / `not_allowed` | **명시 필수** | ⚠️ |
| `macro_indicator` | `not_allowed` | **명시 필수** | ❌ |

규칙:
- `yield`/`spread`/`macro_indicator` 에 `return_transform` 미명시 → `ValueError` (조용한 `pct_change` 금지).
- `not_allowed` → 즉시 `ValueError`.
- `duration_proxy` → Phase C.1 미구현 → `NotImplementedError`.

**현재 9개 자산의 semantic 분류** (운영자 검토 필요):

| asset_key | semantic_type | return_transform | 메모 |
|---|---|---|---|
| kr_equity / us_growth_equity / us_value_equity / dm_ex_us_equity / em_equity / us_high_yield | `total_return_index` | `pct_change` | TR index 가정 — 운영자 확인 |
| kr_aggregate_bond | `total_return_index` | `pct_change` | KIS bond index 가 TR 인지 확인 필요 |
| **kr_treasury_10y** | `yield` | `duration_proxy` | ⚠️ 미구현. TR index 매핑으로 교체 권장 |
| us_treasury_30y | `total_return_index` | `pct_change` | 단 `mapping_mode=requires_decision` 이므로 진행 막힘 |

### 9.3 sanity check (`DBSourceDiagnostics.sanity`)

자산별 항목:
```jsonc
{
  "asset_key": "kr_equity",
  "dataset_id": 144,
  "semantic_type": "total_return_index",
  "start_date": "2021-04-30",
  "end_date":   "2026-03-31",
  "obs_count":  60,
  "missing_ratio": 0.0,
  "latest_date":  "2026-03-31",
  "annualized_return": 0.072,
  "annualized_vol":    0.156,
  "min_monthly_return": -0.082,
  "max_monthly_return": +0.094,
  "suspicious_flags": []
}
```

`suspicious_flags` 후보:
`too_few_observations` / `stale_data` / `latest_date_before_as_of` / `latest_date_after_as_of` / `extreme_return` / `zero_volatility` / `annualized_vol_too_low` / `annualized_vol_too_high` / `semantic_type_not_returnable`.

threshold: `repositories/db_market_data.py::SanityThresholds` (조정 가능).

### 9.4 corr / covariance 검증

`load_corr_matrix` 가 추가로 기록:
- `diagnostics.db_source.corr_nan_warning` — 자산 시계열 join 후 NaN ratio > 20% 이면 경고.
- `diagnostics.db_source.cov_matrix_psd_warning` — 상관행렬 최소 고유값 < −1e-8 이면 경고. **nearest PSD repair 는 Phase C+ 미구현**.
- corr 자체에 NaN 있으면 → `fillna(0.0)` + 대각=1, warning 기록.

### 9.5 inspect_db_sources CLI

```bash
python -m tdf_engine.tools.inspect_db_sources --query "Treasury"
python -m tdf_engine.tools.inspect_db_sources --query "30"
python -m tdf_engine.tools.inspect_db_sources --query "High Yield"
python -m tdf_engine.tools.inspect_db_sources --query "KIS"

# 특정 dataset 의 series/sample
python -m tdf_engine.tools.inspect_db_sources --dataset-id 11 --include-series

# 옵션: --top N / --include-series / --no-semantic-guess
```

출력 예 (semantic_guess 컬럼은 이름 휴리스틱):
```
id   | name                                | ISIN          | symbol     | semantic_guess     | transform_guess
-----+-------------------------------------+---------------+------------+--------------------+----------------
11   | Vanguard Growth ETF                 | US9229087369  | VUG-US     | nav                | pct_change
1    | Treasury 20Y                        | -             | -          | -                  | -
```

read-only. credential 은 환경변수 (`TDF_DB_HOST/USER/PASSWORD/NAME`).

### 9.6 --dry-run-db-check CLI

```bash
python -m tdf_engine.tools.build_portfolio \
  --source-root <Advisory> \
  --source db \
  --as-of-date 2026-03-31 \
  --dry-run-db-check \
  [--output-dir out]
```

동작:
- 포트폴리오 산출 없이 `DBMarketDataRepository(..., permissive=True)` 로 `load_asset_rt_vol` + `load_corr_matrix` 만 시도.
- `permissive=True` 로 `requires_decision` / yield 미명시 등 strict error 도 잡고 진행 → **모든 자산 진단을 한 번에** 출력.
- 자산별 `obs_count`, `latest_date`, `annualized_vol`, `suspicious_flags` 표시.
- `--output-dir` 지정 시 `db_dry_run.json` 저장.

stdout 요약 예:
```
=== DB dry-run ===
load_ok            : True
as_of_date         : 2026-03-31
asset_rt_vol_error : DBMarketDataRepository: asset_rt_vol — 유효한 자산 데이터 없음. ...
datasets_loaded    : []
datasets_missing   : ['kr_equity', ..., 'us_treasury_30y', 'us_high_yield']
proxy_used         : False
warnings (8):
  - kr_equity: dataset_id=144 시계열 비어있음
  - kr_treasury_10y: semantic 정책 위반 — duration_proxy Phase C.1 미구현
  - us_treasury_30y: mapping_mode=requires_decision — db_sources.yaml 결정 필요
```

### 9.7 실제 DB 매핑 확정 절차 (운영자용)

```
1. python -m tdf_engine.tools.build_portfolio --source-root <Advisory> \
       --source db --as-of-date <YYYY-MM-DD> --dry-run-db-check
   → missing / semantic 위반 / sanity flag 한 번에 확인
2. python -m tdf_engine.tools.inspect_db_sources --query <키워드>
   → 후보 dataset_id 탐색 (예: "Treasury 30", "KPGB10", "LF98TRUU")
3. 후보 dataset 의 series/sample:
   python -m tdf_engine.tools.inspect_db_sources --dataset-id <id> --include-series
4. db_sources.yaml::assets 의 dataset_id / semantic_type / return_transform 채움
5. 다시 dry-run → suspicious_flags 비어있는지 확인
6. 정식 빌드:
   python -m tdf_engine.tools.build_portfolio --source-root <Advisory> \
       --source db --as-of-date <YYYY-MM-DD> --product-type fund --output-dir out
7. file 결과와 비교 (max_abs_asset_weight_drift)
```

### 9.8 아직 구현하지 않은 것

1. **`return_transform=duration_proxy`** — yield × duration 추정.
2. **`mapping_mode=synthetic`** — 여러 시계열 합성. hook 만 열어둠.
3. **nearest PSD covariance repair** — warning 만 기록.
4. **`regime_source` / `regime_return_source` DB 모드** — `enabled: false`. file 폴백 유지.
5. **missing_ratio 정확 계산** — 월말 그리드 대비 누락 정확 산출은 Phase C+ 에서.
6. **`datasets_missing` 중복 dedupe** — 현재 동일 자산이 두 단계에서 추가될 수 있음 (`_resolve_dataset_id` + `load_asset_rt_vol` 본문).

### 9.9 Phase C.1 변경 파일

신규
- `tdf_engine/repositories/semantic.py`
- `tdf_engine/tools/inspect_db_sources.py`
- `tests/test_phase_c1_db_validation.py`

수정
- `tdf_engine/config/db_sources.yaml` — 9 자산에 `semantic_type` + `return_transform`, comment 보강
- `tdf_engine/repositories/db_market_data.py` — `resolve_transform`, `SanityThresholds`, `DBSourceDiagnostics.sanity / cov_matrix_psd_warning / corr_nan_warning`, `permissive` 옵션, `_record_sanity`, NaN/PSD 검증
- `tdf_engine/tools/build_portfolio.py` — `dry_run_db_check()`, `--dry-run-db-check` 옵션 (`--product-type` optional)

### 9.10 Phase C.1 결과

```
$ pytest tests/ -q
110 passed in 4.24s
```

- Phase A 44 + B 33 + B.5 5 + B.5+ 7 + C-pre 7 + C 7 + **C.1 7** = 110
- 신규 (`tests/test_phase_c1_db_validation.py`):
  - `test_db_semantic_type_yield_without_transform_raises`
  - `test_db_semantic_type_total_return_index_allows_pct_change`
  - `test_db_sanity_flags_stale_data`
  - `test_db_sanity_flags_extreme_return`
  - `test_db_dry_run_reports_missing_dataset`
  - `test_inspect_db_sources_formats_candidates`
  - `test_covariance_nan_warning_is_reported`

### 9.11 운영자가 결정해야 할 dataset_id (C.1 끝 시점)

| asset_key | 현재 매핑 | 결정 필요 |
|---|---|---|
| `kr_aggregate_bond` | `dataset_id: null` | SPBKRCOT/KISKALBI 의 SCIP id (`inspect_db_sources --query "KIS"`) |
| `kr_treasury_10y` | `dataset_id: null`, `semantic_type=yield`, `return_transform=duration_proxy` | TR index 매핑으로 교체 (예: KIS KTB 10Y TR) → semantic_type 도 `total_return_index` |
| `us_treasury_30y` | `mapping_mode=requires_decision` | direct (USGG30YR TR 존재 시) / proxy (TLT/EDV 등) / 명시 reason |
| `us_high_yield` | `dataset_id: null` | LF98TRUU TR index 의 SCIP id (404 OAS Spread 는 `not_allowed`) |

5개 자산 (`kr_equity`, `us_growth_equity`, `us_value_equity`, `dm_ex_us_equity`, `em_equity`) 은 알려진 ID로 매핑됐으나 운영자가 inspect로 검증 권장.

---

## 10. Phase C.2 — 실 SCIP 매핑 확정 + DB E2E 검증

### 10.1 트리거

C.1 끝 시점 4개 미결정 자산을 실제 SCIP 탐색으로 채워 file→DB 전환 완성. `inspect_db_sources` + 운영자 추가 정보로 dataset 확정.

### 10.2 SCIP 후보 탐색 결과

`inspect_db_sources` 사용. 정확 ticker / 키워드 단계별 좁혀가며 후보 식별.

| asset_key | 검토한 후보 | 채택 / 사유 |
|---|---|---|
| `kr_aggregate_bond` | **id=59 KIS Pricing Composite TR (KST0000T)** ✅ / id=157 KIS 종합채권 A-이상(총수익) / id=43 Kim Kindex KIS Active Bond ETF | id=59 채택. `dataseries=9` (TOT RETURN INDEX NET DVDS), 단일 숫자, 2015~. 정확한 TR index. |
| `kr_treasury_10y` | **id=421 KRX 10년채권지수 (KTBITR Index)** ✅ / id=261 RISE 국고채10년 ETF (2024.05~ 2년 미만) | id=421 채택. `dataseries=9`, 2010~ 풍부. 이전 yield only 매핑(KPGB10YR) 폐기. |
| `us_treasury_30y` | id=99 Treasury 30Y (FactSet) — `series=7 FG Yield (YTM)` 만 → **not_allowed** / id=73 TLT (US 20+Y ETF) — proxy 후보 / **id=201 KIS 미국채 30Y TR 지수 (BRFUT004)** ✅ (운영자 지정) | id=201 채택. `dataseries=33` (KIS Bond Index), KIS dict blob `{totRtnIndex, cleanPriceIndex, mktPriceIndex, avgDur=15.3, avgYtm=4.96, ...}`. 30Y 직접 TR 매핑. |
| `us_high_yield` | **id=401 Bloomberg US HY TR (LF98TRUU)** ✅ / id=72 HYG ETF / id=404 HY OAS Spread (level 아님 → 사용 금지) | id=401 채택. `dataseries=9`, 1999~. 정확한 LF98TRUU TR. |

확정된 매핑 + KIS bond index dict blob 처리를 위해 `parse_data_blob`에 `key=` 인자 추가, `db_sources.yaml`에 `blob_key` 필드 신설.

### 10.3 db_sources.yaml 최종 매핑

| asset_key | dataset_id | dataseries | blob_key | semantic_type / transform |
|---|---:|---:|---|---|
| kr_equity | 144 | 6 | (currency=USD) | `total_return_index` / `pct_change` |
| us_growth_equity | 11 | 6 | USD | `total_return_index` / `pct_change` |
| us_value_equity | 12 | 6 | USD | `total_return_index` / `pct_change` |
| dm_ex_us_equity | 63 | 6 | USD | `total_return_index` / `pct_change` |
| em_equity | 37 | 6 | USD | `total_return_index` / `pct_change` |
| **kr_aggregate_bond** | **59** | **9** | (단일 숫자) | `total_return_index` / `pct_change` |
| **kr_treasury_10y** | **421** | **9** | (단일 숫자) | `total_return_index` / `pct_change` |
| **us_treasury_30y** | **201** | **33** | **`totRtnIndex`** | `total_return_index` / `pct_change` |
| **us_high_yield** | **401** | **9** | (단일 숫자) | `total_return_index` / `pct_change` |

`asset_mapping.yaml::us_treasury_30y` 도 `source_names.optimization="BRFUT004"`, `db_mapping_mode=direct`로 갱신.
**미결정/proxy 0건. mapping_mode=requires_decision 도 0건.**

### 10.4 dry-run-db-check 결과

```
$ python -m tdf_engine.tools.build_portfolio --source db --as-of-date 2026-03-31 \
      --dry-run-db-check --output-dir out/db_dry_run

=== DB dry-run ===
load_ok            : True
as_of_date         : 2026-03-31
asset_rt_vol_rows  : 9
corr_shape         : [9, 9]
datasets_loaded    : [144, 11, 12, 63, 37, 59, 421, 201, 401]
datasets_missing   : []
proxy_used         : False
warnings (0):
--- sanity per asset ---
  kr_equity                obs=120 latest=2026-03-31 ann_vol=+0.2693 flags=[]
  us_growth_equity         obs=120 latest=2026-03-31 ann_vol=+0.1784 flags=[]
  us_value_equity          obs=120 latest=2026-03-31 ann_vol=+0.1460 flags=[]
  dm_ex_us_equity          obs=120 latest=2026-03-31 ann_vol=+0.1489 flags=[]
  em_equity                obs=120 latest=2026-03-31 ann_vol=+0.1541 flags=[]
  kr_aggregate_bond        obs=120 latest=2026-03-31 ann_vol=+0.0352 flags=[]
  kr_treasury_10y          obs=120 latest=2026-03-31 ann_vol=+0.0594 flags=[]
  us_treasury_30y          obs= 87 latest=2026-03-31 ann_vol=+0.1550 flags=[]
  us_high_yield            obs=120 latest=2026-03-31 ann_vol=+0.0717 flags=[]
```

- 9개 자산 모두 매핑 OK
- `corr_nan_warning` / `cov_matrix_psd_warning` 없음
- 자산별 `ann_vol`이 운용 상식 범위 내
- ust30 obs=87 (2018-12 ~ 2026-03 = 약 7년)는 lookback이 dataset 시작일에 묶여 짧음. 다른 자산 120월 (10년).

### 10.5 DB E2E 결과 (returncode 2 — 운영 불가 상태)

```
$ python -m tdf_engine.tools.build_portfolio --source db --product-type etf \
      --as-of-date 2026-03-31 --output-dir out/db_etf
[warning] constraints not fully passed
returncode: 2
```

| 항목 | ETF (db) | Fund (db) |
|---|---|---|
| `product_weight_sum` | **1.050000** ⚠️ | **1.050000** ⚠️ |
| `asset_weight_sum` | 1.000000 | 1.000000 |
| `constraints_passed` | **False** | **False** |
| `quality_status` | **review_required** | **review_required** |
| `max_abs_asset_drift` | 3.00% | 3.00% |
| `fallback_used` | True | True |
| `db_source.proxy_used` | False | False |
| `db_source.warnings` | [] | [] |

**Validation issues**:
- `product_weight sum 1.05 != 1.0`
- `2 asset weights are negative`
- `equity bucket 0.8589 outside [0.7500, 0.8500]`
- `fixed_income bucket 0.1411 outside [0.1500, 0.2500]`

### 10.6 file vs DB 자산 비중 비교

| asset_key | file (augmented) | **db (실 SCIP)** | drift | 해석 |
|---|---:|---:|---:|---|
| kr_equity | +5.00% | +5.89% | +0.89%p | 비슷 |
| us_growth_equity | +40.00% (cap) | +40.00% (cap) | 0% | 동일 cap 도달 |
| us_value_equity | +19.98% | **+30.00%** (cap) | **+10.02%p** | DB가 us_value 더 매력 → cap 도달 |
| dm_ex_us_equity | +5.00% | +5.00% | 0% | 동일 |
| em_equity | +9.02% | +5.00% (lb) | -4.02%p | DB가 em 덜 매력 → lower bound |
| kr_aggregate_bond | +4.28% | **+11.11%** | **+6.83%p** | KIS TR index 의 sharpe 가 file 대비 높음 |
| **kr_treasury_10y** | +8.00% | **-2.00%** ⚠️ | **-10.00%p** | DB SAA 0% → TAA tilt -2% → **음수** |
| **us_treasury_30y** | +0.72% | **-3.00%** ⚠️ | **-3.72%p** | DB SAA 0% → TAA tilt -3% → **음수** |
| us_high_yield | +8.00% | +8.00% | 0% | 동일 |

bucket:
| | file | db |
|---|---:|---:|
| equity | 79.00% | **85.89%** ⚠️ |
| fixed_income | 21.00% | **14.11%** ⚠️ |

### 10.7 발견된 핵심 이슈 (Phase C.2 가 노출시킨 것)

1. **TAA overlay 가 SAA=0 자산을 음수로 끌어내림** — Phase B.5의 cash-neutral 조정에서 음수 floor 가 없음. `kr_treasury_10y`/`us_treasury_30y`가 SAA에서 0이었는데 regime 1의 -2%/-3% tilt가 직접 더해져 음수.
2. **product_weight_sum 1.05 (>1)** — 음수 자산은 fallback 대상에서 제외되어 양수만 합산. 0.95 + 5%p (음수 자산 흡수 안 함) ≠ 1.0.
3. **Equity bucket 85.89% > 0.85** — TAA 가 fixed_income 음수로 만들고 그만큼 equity 가 늘어남. taa_bounds 위반.
4. **DB σ vs file σ 차이가 커서 SAA 자체가 다름** — file은 단일 cross-section assumption (ust30 placeholder σ=13%, μ=3.5%), DB는 10년 시계열 추정. ust30 ann_vol=15.5% (DB) vs 13% (file). kr_treasury_10y ann_vol=5.94% (DB) vs σ=8% (file의 KPGB10YR). 자산별 sharpe 순위가 달라져 SAA cap 도달 자산이 바뀜.

### 10.8 Phase C.2 변경 파일

수정
- `tdf_engine/config/db_sources.yaml` — 4개 미결정 매핑 확정, ticker 라벨을 asset_mapping의 source_names.optimization 과 정합 (BRFUT004 / KST0000T → "M2KR INDEX" 등 표시 라벨), `blob_key` 필드 신설.
- `tdf_engine/config/asset_mapping.yaml` — `us_treasury_30y.source_names.optimization="BRFUT004"`, `db_mapping_mode=direct`, `db_dataset_id=201`.
- `tdf_engine/repositories/_blob.py` — `parse_data_blob(blob, currency=None, key=None)` — KIS bond dict 처럼 비숫자 key 가 섞여있어도 동작. `currency` 는 `key` 의 alias.
- `tdf_engine/repositories/db_market_data.py` — `_query_levels(blob_key=...)`, `_monthly_returns(blob_key=...)` 시그니처. 코드 동작은 동일.
- `tests/test_phase_c1_db_validation.py::test_db_dry_run_reports_missing_dataset` — ust30 mapping_mode 변경에 맞춰 어셔션 갱신.

### 10.9 운영 적용 가능 여부 — Claude 판단

**아직 운영 적용 불가**. Phase C 의 *DB 연결 자체*는 완성됐으나 (9개 자산 모두 dataset 매핑 + dry-run sanity 통과) **Phase B.5 의 TAA overlay 가 long-only 가정을 강제하지 않아** SAA=0 자산이 음수가 되는 경우가 발생.

운영 적용 전 다음 작은 수정이 필수:
1. **TAA overlay 음수 floor (long-only)** — `taa_weights = max(0, saa + tilt)` 적용 후 cash-neutral 재정규화.
2. **product 단위 sum=1 보장** — 음수 자산 처리 후 fallback 정책에 통합.
3. **equity bucket 0.7500~0.8500 강제** — 현재 warning. TAA overlay 단계에서 hard clip 또는 SAA bound 정합.

이 3가지는 모두 `taa/overlay.py` + `portfolio/fallback.py` 의 작은 수정 (Phase B.5+ 보강 또는 Phase C+ 단계). 사용자 지시(=Phase C.2는 핵심 로직 수정 금지)에 따라 본 단계에서는 *문제 노출과 보고만* 수행.

### 10.10 운영자 후속 결정 항목

1. **TAA overlay long-only 강제 정책** — 위 1번. 명시 동의 후 작은 수정.
2. **us_treasury_30y obs=87 (7년)** — 다른 자산 (120월=10년) 대비 짧음. 가능하면 동일 lookback 으로 잘라서 비교 fair. 또는 acceptable.
3. **DB σ vs file σ 차이의 운용 의도 검토** — DB σ가 운영 기준이 되는지, file (cross-section) 가 정의 자체가 다른지 운용역과 협의.
4. **us_value_equity cap 30% 도달** — DB sharpe 가 매우 높아 cap. weight_bounds 재검토 또는 valuation 적정성 확인.

### 10.11 Phase C.2 결과 / 회귀

```
$ pytest tests/ -q
110 passed in 3.92s
```

기존 110개 테스트 그대로 통과. Phase C.2 는 코드 추가 없이 yaml + 매핑 갱신 위주.
- `tests/test_phase_c1_db_validation.py::test_db_dry_run_reports_missing_dataset` 만 어셔션 갱신 (ust30 매핑 확정으로 더 이상 `requires_decision` 가 아님).

---

## 11. Phase C.3 — TAA Feasibility Projection

### 11.1 트리거

Phase C.2 끝에 발견된 운영 차단 이슈:
- `kr_treasury_10y = -2.00%`, `us_treasury_30y = -3.00%` (음수 weight)
- `product_weight_sum = 1.05` (양수만 합산되어 100% 초과)
- `equity bucket = 85.89% > 0.85`, `fixed_income bucket = 14.11% < 0.15`
- `constraints_passed = False`, `quality_status = review_required`

원인 흐름:
```
SAA 결과: 일부 자산 lower bound 0% (DB σ/μ 분포가 file 과 달라 ust30/kr_t10 매력 ↓)
↓
Regime 1 TAA tilt: kr_treasury_10y -2%, us_treasury_30y -3%
↓
target = SAA(0%) + tilt(-3%) = -3%   ← long-only 가정 위반
↓
TAA overlay 가 그대로 통과 → portfolio 단계에서 음수 weight + bucket 위반
```

### 11.2 설계 — projection 으로 항상 feasible

`tdf_engine/taa/projection.py::project_to_feasible`:

```
minimize    Σ (w_i - target_i)^2
subject to  Σ w_i = sum_target               (보통 1.0)
            asset_lb_i ≤ w_i ≤ asset_ub_i    (long-only 면 lb≥0)
            bucket_lb ≤ Σ_{i ∈ bucket} w_i ≤ bucket_ub
```

- SLSQP 사용 (MVO 와 동일 솔버).
- target 이 이미 feasible 이면 즉시 반환 (objective=0, projection_used=False).
- 결과 numerical residual: `clip(0, None) + 비례 재정규화`로 안전 처리.

### 11.3 통합

- **`taa/overlay.py::TAAOverlayEngine`** — `apply()` 끝에 projection 호출. `enable_projection=False` 로 끌 수 있음 (역호환).
- **`taa/tool.py::TAAOverlayTool`** — `tdf_config` 추가 인자. `final_asset_bounds → weight_bounds` 우선순위로 asset_bounds, `taa_bounds`로 bucket_bounds 추출 후 engine에 주입.
- **`tools/build_portfolio.py`** — TAAOverlayTool 호출 시 `tdf_config=tdf_config` 전달.

### 11.4 diagnostics — `taa_feasibility`

`portfolio.diagnostics["taa_diagnostics"]["taa_feasibility"]`:

```jsonc
{
  "projection_used": true,
  "projection_success": true,
  "projection_message": "Optimization terminated successfully",
  "target_weights_before_projection": {ak: w_target},
  "final_weights_after_projection": {ak: w_final},
  "negative_weight_assets_before_projection": {"kr_treasury_10y": -0.02, ...},
  "clipped_weight_total": 0.05,
  "bucket_weights_before_projection": {"equity": 0.8589, "fixed_income": 0.1411},
  "bucket_weights_after_projection":  {"equity": 0.8232, "fixed_income": 0.1768},
  "asset_weight_drift_from_target": {ak: w_final - w_target},
  "max_abs_projection_drift": 0.03,
  "constraints_after_projection": {"feasible": true, "sum": 1.0, "min_weight": 0.0, ...}
}
```

### 11.5 Validator 강화 (`portfolio/validator.py`)

`taa_feasibility.projection_used=True` 이면 `warnings`에 다음을 추가:
```
taa_projection_used: max_abs_projection_drift=3.0000%
negative weights before projection: kr_treasury_10y=-2.0000%, us_treasury_30y=-3.0000%
bucket after projection: equity=82.3168%, fixed_income=17.6832%
```

`projection_success=False` 면 `bucket_bounds_ok=False` + `issues`에 메시지 → `constraints_passed=False`.

### 11.6 DB E2E 결과 (Phase C.3 적용 후)

| 항목 | Phase C.2 | **Phase C.3** | 비고 |
|---|---|---|---|
| `constraints_passed` | False | **True** | ✅ |
| `asset_weight_sum` | 1.000 | 1.000 | |
| **`product_weight_sum`** | **1.050** ⚠️ | **1.000** | ✅ projection 으로 음수 제거 후 sum 보존 |
| `quality_status` | review_required | **warning** | fallback 만 |
| 음수 자산 수 | 2 (kr_t10, ust30) | **0** | ✅ |
| `equity bucket` | 85.89% ⚠️ | **82.32%** | bucket bound 안 |
| `fixed_income bucket` | 14.11% ⚠️ | **17.68%** | bucket bound 안 |
| `validation issues` | 4건 | **0건** | ✅ |
| `projection_used` | (없음) | **True** | |
| `max_abs_projection_drift` | (없음) | 3.00% | ust30 -3% → 0% |
| `proxy_used` | False | False | DB 직접 매핑 유지 |
| returncode | 2 | **0** | |

### 11.7 file vs DB 자산 비중 비교 (Phase C.3 기준)

| asset_key | file (target=final) | DB target (before proj) | DB final (after proj) | drift (DB→DB) |
|---|---:|---:|---:|---:|
| kr_equity | +5.00% | +5.89% | +5.17% | -0.71%p |
| us_growth_equity | +40.00% (cap) | +40.00% (cap) | +39.29% | -0.71%p |
| us_value_equity | +19.98% | +30.00% (cap) | +29.29% | -0.71%p |
| dm_ex_us_equity | +5.00% | +5.00% | +4.29% | -0.71%p |
| em_equity | +9.02% | +5.00% (lb) | +4.29% | -0.71%p |
| kr_aggregate_bond | +4.28% | +11.11% | +10.40% | -0.71%p |
| **kr_treasury_10y** | +8.00% | **−2.00%** | **+0.00%** | +2.00%p |
| **us_treasury_30y** | +0.72% | **−3.00%** | **+0.00%** | +3.00%p |
| us_high_yield | +8.00% | +8.00% | +7.29% | -0.71%p |
| equity bucket | 79.00% | 85.89% | **82.32%** | |
| fixed_income | 21.00% | 14.11% | **17.68%** | |
| projection_used | False (이미 feasible) | — | True | |
| max_abs_drift | 0% | — | 3.00% | |

projection 동작 해석:
- 음수 자산 2개를 0으로 끌어올림 (총 +5%p 흡수 필요)
- 양수 자산 7개에서 비례 ~0.71%p씩 감소 (5%p / 7개 ≈ 0.71%p)
- 결과적으로 sum=1, 모두 ≥0, equity bucket 안에 들어옴

### 11.8 Phase C.3 변경 파일

신규
- `tdf_engine/taa/projection.py` — `project_to_feasible`, `ProjectionDiagnostics`
- `tests/test_phase_c3_projection.py` — 7 tests

수정
- `tdf_engine/taa/overlay.py` — projection 호출, `taa_feasibility` diagnostics 추가, `enable_projection` 옵션
- `tdf_engine/taa/tool.py` — `tdf_config` 인자, `final_asset_bounds`/`weight_bounds`/`taa_bounds`에서 bounds 추출 후 engine 주입
- `tdf_engine/tools/build_portfolio.py` — TAAOverlayTool에 `tdf_config` 전달
- `tdf_engine/portfolio/validator.py` — projection 관련 warning + projection_failed 시 issues
- `tests/conftest.py::augmented_source_root` — Asset_rt_vol fixture row 의 Ticker `USGG30YR Index → BRFUT004` (yaml 매핑과 정합)
- `tests/conftest.py::augmented_assets` — Phase C.2 yaml 자체가 BRFUT004 이므로 수정 없이 그대로 반환 (호환 유지)
- `tests/test_phase_c_db.py::_TICKER_BY_KEY` — ust30 ticker `BRFUT004`

### 11.9 Phase C.3 결과

```
$ pytest tests/ -q
117 passed in 4.10s
```

- Phase A 44 + B 33 + B.5 5 + B.5+ 7 + C-pre 7 + C 7 + C.1 7 + **C.3 7** = 117
- 신규 (`tests/test_phase_c3_projection.py`):
  - `test_taa_projection_removes_negative_weights`
  - `test_taa_projection_preserves_sum_to_one`
  - `test_taa_projection_enforces_bucket_bounds`
  - `test_taa_projection_records_negative_assets_before_projection`
  - `test_db_e2e_after_projection_product_weight_sum_is_one`
  - `test_db_e2e_after_projection_constraints_pass`
  - `test_validator_reports_projection_warning`

### 11.10 남은 한계 (C.3 끝 시점)

1. **Projection 의 quadratic 거리**: target 에서 가장 가까운 feasible 점을 찾지만, "가까움" 의 metric 이 단순 L2. 운용 의도로는 *bucket 단위 비율 보존* 또는 *high-conviction 자산 우선* 이 더 자연스러울 수 있음.
2. **DB σ vs file σ 정의 차이**: 본질적으로 file (cross-section assumption) ≠ DB (10년 시계열 추정). 운용 기준이 어느 쪽인지 협의 필요.
3. **us_treasury_30y obs=87** (다른 자산 120월 대비 짧음) — lookback 통일 정책 미정.
4. **ust30 / kr_t10 SAA=0**: SAA 단계에서 이 두 자산이 매력 없다고 판단됨. weight_bounds 의 lower bound 를 0% 보다 높여서 강제 편입할지 운용 정책 결정 필요.
5. **Regime 모델 DB 미연결**: `regime_source` 여전히 file 폴백 (`solution.roboadvisorAPI_economicregime` 미사용).
6. **GlidePath xlsx 미연결**: 단일 vintage(2060) 그대로.
7. **ETF/Fund 의 SAA 가 동일** (DB 모드): 두 시나리오의 차이는 universe/selection 단계에서만 발생.

### 11.11 Phase C 완료 여부 — Claude 판단

**완료. 운영 검토 가능 수준.**

Phase C 시리즈 (C → C.1 → C.2 → C.3) 가 합쳐서 다음을 달성:
1. ✅ DB repository 구조 (Phase C)
2. ✅ semantic / sanity / dry-run / inspect (Phase C.1)
3. ✅ 9개 자산 SCIP dataset 매핑 확정 (Phase C.2)
4. ✅ TAA 결과의 long-only + bucket bound feasibility (Phase C.3)

DB → CMA → SAA → TAA(+ projection) → Selection → Portfolio → CSV/JSON 흐름이 실 SCIP 데이터로 `constraints_passed=True`, `product_weight_sum=1.0`, `quality_status=warning` 까지 도달.

**다음 우선순위 (운영 적용 전)**:
1. **운영자 승인** — DB 실 결과를 운용역이 보고 weight band/bucket band 정책 동의.
2. **`final_asset_bounds` 운영 값 확정** — Phase B.5+ 초안 그대로 사용 중. 운용역 review.
3. **regime DB 연결 (`solution.roboadvisorAPI_economicregime`)** — Phase C+.
4. **GlidePath 엑셀 연동** — DRM 해제 후.
5. **reporting 모듈** — HTML/대시보드.

위 5개는 기능 *추가*이지 운영 차단이 아님. Phase C.3 까지의 산출물은 **DB 기반 운영 시작 가능 수준**.

---

## 12. Phase C.4 — 운용역 검토 패킷 (Review Packet)

### 12.1 목적

Phase C.3 까지 엔진이 작동하지만, 운용역이 *결과를 보고 승인/수정 판단할 수 있게* 하는 산출물이 부족.
- C.4 는 모델 로직 변경 없이 결과를 정리.
- 운용역이 "이 비중을 그대로 적용해도 되는지"를 빠르게 판단할 수 있는 review packet (json 키 + Markdown 리포트) 추가.

### 12.2 신규 모듈

`tdf_engine/reporting/review.py`:
- `build_review_packet(portfolio, assets, tdf_config) → dict`
- `render_markdown(packet) → str`

코어 (optimization / regime / TAA / selection / fallback / quality) 변경 0.
portfolio.diagnostics 만으로 derive.

### 12.3 review_summary 구조

운용역이 한눈에 보는 17개 키:

```jsonc
{
  "source_type": "db",
  "as_of_date": "2026-03-31",
  "portfolio_type": "etf",
  "constraints_passed": true,
  "quality_status": "warning",
  "asset_weight_sum": 1.0,
  "product_weight_sum": 1.0,
  "equity_bucket_weight": 0.8232,
  "fixed_income_bucket_weight": 0.1768,
  "fallback_used": true,
  "projection_used": true,
  "max_abs_projection_drift": 0.03,
  "max_abs_asset_weight_drift": 0.0,
  "proxy_used": false,
  "db_warnings_count": 0,
  "validation_issues_count": 0,
  "validation_warnings_count": 8
}
```

### 12.4 projection_summary 구조

```jsonc
{
  "projection_used": true,
  "projection_success": true,
  "reason": "Optimization terminated successfully",
  "negative_assets_before_projection": {
    "kr_treasury_10y": -0.02,
    "us_treasury_30y": -0.03
  },
  "bucket_before": {"equity": 0.8589, "fixed_income": 0.1411},
  "bucket_after":  {"equity": 0.8232, "fixed_income": 0.1768},
  "max_abs_projection_drift": 0.03,
  "largest_projection_drifts_top5": [
    {"asset_key": "us_treasury_30y", "drift": 0.03, "before": -0.03, "after": 0.0},
    {"asset_key": "kr_treasury_10y", "drift": 0.02, "before": -0.02, "after": 0.0},
    {"asset_key": "us_value_equity", "drift": -0.0071, "before": 0.30, "after": 0.2929},
    ...
  ]
}
```

### 12.5 asset_allocation table

자산별로 SAA / TAA target / final / projection drift / final_asset_bound / status 9 컬럼:

| asset_key | bucket | TAA target | final | drift | bound [lb, ub] | status |
|---|---|---:|---:|---:|---|---|
| kr_equity | equity | +5.89% | **+5.17%** | -0.71% | [2%, 22%] | ok |
| us_growth_equity | equity | +40.00% | **+39.29%** | -0.71% | [4%, 42%] | ok |
| us_value_equity | equity | +30.00% | **+29.29%** | -0.71% | [4%, 32%] | ok |
| dm_ex_us_equity | equity | +5.00% | **+4.29%** | -0.71% | [4%, 27%] | **near_bound** |
| em_equity | equity | +5.00% | **+4.29%** | -0.71% | [2%, 17%] | ok |
| kr_aggregate_bond | fixed_income | +11.11% | **+10.40%** | -0.71% | [0%, 17%] | ok |
| **kr_treasury_10y** | fixed_income | -2.00% | **+0.00%** | +2.00% | [0%, 12%] | near_bound |
| **us_treasury_30y** | fixed_income | -3.00% | **+0.00%** | +3.00% | [0%, 17%] | near_bound |
| us_high_yield | fixed_income | +8.00% | **+7.29%** | -0.71% | [0%, 9%] | ok |

`bound_status` ∈ `{ok, near_bound, violation_below, violation_above, no_bound}`.

### 12.6 product_allocation 보강 (json 내)

기존 csv 컬럼 + 운용역 검토 컬럼:
- `product_type`, `bucket`, `source_asset_weight`, `selection_reason`, `fallback_absorbed_weight`, `warning_flags[]`
- `score` 는 selection 에 score 보존 안 함 → `null`

`warning_flags` 예: `["unfilled_cause=product_cap_clipping", "fallback_absorber"]`, `["cash_placeholder"]`.

### 12.7 policy_review_items 자동 추출 (운용역 confirm 항목)

휴리스틱:
1. 자산 weight = 0 (especially 자산 bound min > 0 일 때)
2. final_asset_bound 위반 (`violation_below` / `violation_above`)
3. final_asset_bound 근접 (`near_bound`)
4. projection 사용 시 max_abs_projection_drift confirm
5. 자산별 obs_count 차이 (lookback 정책)
6. cash placeholder 사용
7. no_candidates_in_universe 발생 자산

실 DB ETF 결과의 7개 자동 감지:
```
- kr_treasury_10y final weight is 0.00%; confirm whether zero allocation is acceptable.
- us_treasury_30y final weight is 0.00%; confirm whether zero allocation is acceptable.
- dm_ex_us_equity final weight 4.2857% is near a final bound; confirm cap appropriateness.
- kr_treasury_10y final weight 0.0000% is near a final bound; confirm cap appropriateness.
- us_treasury_30y final weight 0.0000% is near a final bound; confirm cap appropriateness.
- projection was used; confirm max_abs_projection_drift 3.0000% is acceptable.
- us_treasury_30y has shorter history, obs=87 vs others 120; confirm lookback policy.
```

리뷰자가 짚었던 `dm_ex_us_equity 4.29% 가 lower bound 5%` 의심도 자동 감지됨 (4% 가 final bound min 이라 ok 이지만 near_bound 로 표시).

### 12.8 Markdown report

`out/<dir>/review_<etf|fund>_<YYYYMMDD>.md` 자동 생성. 8 섹션:
1. 요약 (review_summary 표)
2. 최종 자산배분 (asset_allocation 표)
3. Projection 전후 (bucket before/after, top-5 drift, 음수 자산)
4. 최종 상품 (product_allocation 표 + flags)
5. Validation (issues/warnings 카운트)
6. Quality (status + drift)
7. DB source (source_type/proxy/warnings)
8. 운용역 확인 필요 사항 (policy_review_items)

### 12.9 운용역 검토 workflow

```
1. python -m tdf_engine.tools.build_portfolio --source db \
     --product-type {etf|fund} --as-of-date <date> --output-dir out/<dir>
   → portfolio_<pt>_<date>.csv / .json / review_<pt>_<date>.md 생성
2. review_<pt>_<date>.md §1 (요약): constraints_passed / quality_status / drift 빠른 점검
3. §2 (자산배분): bound_status 가 violation_* 인 자산 우선 검토
4. §3 (projection): 음수 자산 / drift 합리적인지
5. §4 (상품): warning_flags 가 있는 상품 review
6. §8 (확인 항목): 운용역 의사결정 — 그대로 / 수정 / 재산출
```

### 12.10 변경 파일

신규
- `tdf_engine/reporting/review.py` — `build_review_packet`, `render_markdown`, `_bound_status`
- `tests/test_phase_c4_review.py` — 5 tests

수정
- `tdf_engine/tools/build_portfolio.py::write_outputs` — assets/tdf_config 인자, json payload 에 review packet 키 추가, `review_<pt>_<date>.md` 저장
- `tdf_engine/tools/build_portfolio.py::main` — write_outputs 호출 시 loader 로 assets/tdf_config 로드

### 12.11 Phase C.4 결과

```
$ pytest tests/ -q
122 passed in 4.68s
```

- Phase A 44 + B 33 + B.5 5 + B.5+ 7 + C-pre 7 + C 7 + C.1 7 + C.3 7 + **C.4 5** = 122
- 신규 (`tests/test_phase_c4_review.py`):
  - `test_review_summary_contains_required_keys`
  - `test_asset_allocation_comparison_distinguishes_target_and_final`
  - `test_policy_review_items_include_zero_weight_required_assets`
  - `test_projection_summary_lists_negative_assets_before_projection`
  - `test_review_markdown_is_written`

### 12.12 다음 단계 제안

이제 **운용역 review 단계**가 시작됩니다. 코드 입장에서 우선순위:

1. **운용역 의사결정** (C.4 산출물 기반)
   - us_treasury_30y / kr_treasury_10y 0% 수용 vs 강제 편입
   - dm_ex_us_equity 4.29% 가 5% lower bound 의도와 맞는지
   - us_value_equity 30% cap 도달 적정성
2. **regime DB 연결** (`solution.roboadvisorAPI_economicregime` 7,550행) — Phase C+
3. **GlidePath 엑셀 / DB 연결** (`solution.roboadvisorAPI_glidepath` 1,017행)
4. **HTML report / 대시보드** — 현재 Markdown 만. Plotly/Dash 위 layer
5. **score 보존 + product_allocation 의 score 컬럼 활성화** — selection.tool 작은 수정으로 가능

위 1번이 운용역 review 결과 *수정 요청*을 만들면 그게 다음 작업의 기준이 됩니다. 그 외에는 모두 *기능 추가*입니다.
