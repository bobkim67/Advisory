# Phase E-12 — Integrated Review Packet (Design)

작성일: 2026-05-11. **E-8 Regime Clock + E-9 SAA Frontier + E-10 TAA Tilt + E-11B Product
Selection 4 standalone 산출물을 운용역 review packet 1건으로 묶는 packaging phase.**

> 새 분석 차트 미생성. MVP-X polish 미진행. E-12 = layout / orchestration only.

---

## 0. TL;DR

| 항목 | 결정 |
|---|---|
| **Scope** | 4 phase 산출물을 1개 packet 으로 packaging. 새 차트/분석 X. |
| **Format** | **Primary: Markdown**, **Secondary: HTML** (simple CSS, no JS). PDF 는 후속 옵션 (E-15 후보). |
| **변경** | reporting/review_packet.py + tools/build_review_packet.py + 신규 tests 만 추가. allocation/optimizer/TAA/selection/scoring/config/MVP-X/E-7~E-11B 무변경. |
| **출력 위치** | `out/db_review_relaxed_e62/review_packet/<as_of_run>/` |
| **자산 복사** | `assets/` 서브디렉토리에 모든 PNG 복사 (relative link 보장 — md/html 모두 portable) |
| **MVP-X 위치** | 본 packet 의 main 섹션 진입 금지 (deprecated). `--include-appendix` 옵션으로만 별도 섹션 추가 가능. |

---

## 1. Packet purpose

운용역이 한 파일을 읽고 다음 6개 질문에 답할 수 있어야 한다:

1. 현재 경기국면이 어디에 있는가? (E-8)
2. SAA 는 어떤 MVO 입력/제약으로 산출되었는가? (E-9)
3. TAA 는 어떤 rule 로 어떤 자산을 tilt 했는가? (E-10)
4. 최종 상품은 어떤 universe / filter / score / rank 로 선택되었는가? (E-11B)
5. 최종 자산/상품 비중은 무엇이고 quality 는 어떤가? (portfolio JSON / review_*.md)
6. 어떤 데이터/방법론 한계가 있는가? (각 phase 의 missing_data 통합)

---

## 2. Target reader / Tone

- **Reader**: 포트폴리오 운용역 / 검토 관리자.
- **Tone**: diagnostic, conservative. 한계 / 가정을 숨기지 않음.
- **Style**: 한 문장 요약 + 차트 + 핵심 metric 표. 분석 정의나 코드 설명 금지 (별도 docs 참조).

---

## 3. Output formats

| 형식 | 용도 | 본 phase 산출 |
|---|---|---|
| **Markdown (`.md`)** | git diff / review-friendly, 텍스트 우선 | ✅ 산출 |
| **HTML (`.html`)** | 브라우저 / 인쇄 / 공유, simple CSS embed | ✅ 산출 |
| **PDF** | hard-copy distribution | ⏳ 후속 phase E-15 후보 (HTML 구조 확정 후 wkhtmltopdf / weasyprint 등 도입) |

### MD rendering policy
- relative image links (`assets/...`).
- 표는 GitHub-flavored markdown.
- 한 섹션당 짧은 한 문단 요약 + 차트 + metric 표.

### HTML rendering policy
- Markdown 과 동일 contents (HTML escape + img tag 변환).
- 단일 파일 — 외부 JS 의존 없음. CSS 는 inline `<style>` 블록.
- 인쇄 친화 — `@media print` rule 로 page break 힌트.
- 이미지: `assets/` 디렉토리 상대 link (또는 옵션으로 base64 embed — 본 phase 미적용).

---

## 4. Section order (8 + appendix)

```
0. Cover / Run Metadata
1. Executive Summary
2. Regime Assessment           ← E-8
3. SAA Construction            ← E-9
4. TAA Overlay                 ← E-10
5. Product Selection           ← E-11B
6. Final Portfolio Snapshot    ← portfolio_*.json + review_*.md
7. Diagnostics / Missing Data  ← 4 phase 통합
8. Appendix (opt-in, --include-appendix)
   - MVP-X prototype PNG
   - E-6 9 PNG legacy set
```

### 0. Cover / Run Metadata
- product_type, portfolio_as_of_date, source_mode, operating_mode, generated_at, quality_status, pytest baseline (옵션).
- "RELAXED DIAGNOSTIC RUN — NOT a production portfolio" disclaimer 5줄 (기존 review packet banner 와 일치).

### 1. Executive Summary
- 한 문단 portfolio construction 요약.
- 핵심 metric 표:
  - SAA top weights / TAA target / Final asset weights / Top product
  - regime + Sharpe (SAA / TAA before-after)
- 핵심 caveats 5건 명시:
  - relaxed diagnostic (not production)
  - rule-based TAA (not optimized TAA / not regime-conditioned MVO)
  - ticker mapping unavailable
  - regime-conditioned assumptions unavailable
  - efficient frontier sampled (E-9 grid scan, not analytical)

### 2. Regime Assessment (E-8)
- Source artifacts:
  - `regime_clock_<pt>_<as_of>.png`
  - `regime_history_<pt>_<as_of>.json`
- Include:
  - Regime clock PNG (full size)
  - current regime card: R<n>, label, P, V, region
  - portfolio as_of vs regime signal as_of distinction (signal lags)
  - transition summary (recent N obs, regime change comment)
  - coverage status (`full` / `partial` / `insufficient`)

### 3. SAA Construction (E-9)
- Source artifacts:
  - `saa_mvo_<pt>_<as_of>.png`
  - `saa_frontier_<pt>_<as_of>.json`
- Include:
  - SAA MVO PNG (full size)
  - selected SAA point: E[R] / σ / Sharpe / non-zero weights
  - max-Sharpe / min-vol reference
  - `selected_matches_max_sharpe` 플래그
  - active constraint summary (long-only + sum=1, 비활성 항목 명시)
  - relaxed diagnostic caveat ("asset caps / bucket bands not applied")

### 4. TAA Overlay (E-10)
- Source artifacts:
  - `taa_tilt_<pt>_<as_of>.png`
  - `taa_tilt_<pt>_<as_of>.json`
- Include:
  - TAA tilt PNG (full size)
  - applied tilt rules table (asset / SAA / tilt / TAA target / direction / rationale)
  - SAA → TAA before/after metrics (E[R], σ, Sharpe, Δ)
  - **Limitation text 강조** (red box equivalent): "Current TAA is rule-based regime overlay. Not regime-conditioned MVO and not optimized TAA."

### 5. Product Selection (E-11B)
- Source artifacts:
  - `product_selection_<pt>_<as_of>.png`
  - `product_selection_visualization_<pt>_<as_of>.json`
- Include:
  - product selection PNG (full size)
  - universe funnel (raw → passed → classified → eligible → selected)
  - 자산군별 coverage (sufficient / limited / none)
  - selected product table (asset / rank / score / weight / id / name / manager)
  - missing ticker caveat ("Ticker mapping unavailable; product_id / product_name used as identifier.")

### 6. Final Portfolio Snapshot
- Source artifacts:
  - `portfolio_<pt>_<as_of_run>.json` (e62 또는 e62_e11a)
  - `review_<pt>_<as_of_run>.md` (옵션)
- Include:
  - final asset_weights (9 자산)
  - final product top N (default 10)
  - constraints_passed / quality_status
  - max_abs_projection_drift / max_abs_asset_weight_drift
  - ETF + Fund 둘 다 있을 때 nested comparison 표 (--product-type both)

### 7. Diagnostics / Missing Data
- 5 phase 의 missing_data 항목을 unique field 별로 통합:
  - E-7 explainability
  - E-8 regime history
  - E-9 SAA frontier
  - E-10 TAA tilt
  - E-11B product selection visualization
- 표 형식: `field` / `impact` / `recommended_next_step` / `source_phase`.

### 8. Appendix (opt-in)
- `--include-appendix` 명시 시에만:
  - MVP-X prototype PNG (`figures_polish/main/00_mvpx_bridge_<pt>_*.png`) — *deprecated, prototype only* 라벨
  - E-6 legacy 9 PNG (옵션) — *legacy downstream-only* 라벨

---

## 5. Source artifacts (자동 lookup)

CLI는 `--review-root`(기본 `out/db_review_relaxed_e62`) + `--as-of-run`(기본 `20260511`)로 다음 경로 자동 탐색:

```
<review_root>/regime_history/<as_of_run>/regime_clock_<pt>_<as_of_run>.png
<review_root>/regime_history/<as_of_run>/regime_history_<pt>_<as_of_run>.json
<review_root>/saa_frontier/<as_of_run>/saa_mvo_<pt>_<as_of_run>.png
<review_root>/saa_frontier/<as_of_run>/saa_frontier_<pt>_<as_of_run>.json
<review_root>/taa_tilt/<as_of_run>/taa_tilt_<pt>_<as_of_run>.png
<review_root>/taa_tilt/<as_of_run>/taa_tilt_<pt>_<as_of_run>.json
<review_root>/product_selection_visualization/<as_of_run>/product_selection_<pt>_<as_of_run>.png
<review_root>/product_selection_visualization/<as_of_run>/product_selection_visualization_<pt>_<as_of_run>.json
<review_root>/explainability/<as_of_run>/explainability_<pt>_<as_of_run>.json
<portfolio_dir>/portfolio_<pt>_<run_date>.json   (e62 또는 e62_e11a, --portfolio-dir)
<portfolio_dir>/review_<pt>_<run_date>.md         (옵션)
```

미존재 artifact 는 packet 의 해당 섹션을 비우고 missing_data 에 `<phase>_artifact_missing` 추가 (silent skip 금지).

---

## 6. Missing data handling

- 각 phase 산출 JSON 의 `diagnostics.missing_data` 또는 `report_ready_summary.missing_data` 가 있으면 §7 통합.
- artifact 자체가 없으면 explicit 처리:
  ```
  field: "<phase>_artifact_missing"
  impact: "<phase> 섹션 비어 있음"
  recommended_next_step: "build_<phase> CLI 재실행 — 경로: <expected_path>"
  source_phase: "<phase>"
  ```
- silent omit 금지.

---

## 7. CLI design

```
python -m tdf_engine.tools.build_review_packet \
    --as-of-run 20260511 \
    --product-type etf | fund | both \
    --review-root out/db_review_relaxed_e62 \
    --portfolio-dir out/db_etf_relaxed_e62_e11a   # ETF; --product-type both 시 두 개 필요
    --portfolio-dir-fund out/db_fund_relaxed_e62_e11a   # 옵션
    --output-dir out/db_review_relaxed_e62/review_packet/20260511 \
    --format md | html | both \
    [--include-appendix]
```

### Output layout

```
out/db_review_relaxed_e62/review_packet/20260511/
├── review_packet_etf_20260511.md
├── review_packet_etf_20260511.html
├── review_packet_fund_20260511.md
├── review_packet_fund_20260511.html
├── review_packet_both_20260511.md
├── review_packet_both_20260511.html
└── assets/
    ├── regime_clock_etf_20260511.png
    ├── regime_clock_fund_20260511.png
    ├── saa_mvo_etf_20260511.png
    ├── saa_mvo_fund_20260511.png
    ├── taa_tilt_etf_20260511.png
    ├── taa_tilt_fund_20260511.png
    ├── product_selection_etf_20260511.png
    └── product_selection_fund_20260511.png
```

`assets/` 는 source PNG 의 사본만 (mtime preserved, hash unchanged) — 원본 파일 미변경.

---

## 8. Hard requirements (E-12 영구)

```
✗ 새 분석 차트 생성 금지
✗ E-8/E-9/E-10/E-11B chart 로직 변경 금지
✗ allocation / optimizer / TAA / selection / scoring / config 변경 금지
✗ 기존 production output (out/db_*_relaxed/*) overwrite 금지
✗ 기존 e62 / e62_e11a output overwrite 금지
✗ 기존 phase 산출물 (regime_history/saa_frontier/taa_tilt/product_selection_visualization/explainability) overwrite 금지
✗ Decision Register count (14) 변경 금지
✗ MVP-X 를 main 섹션에 포함 금지 (--include-appendix 시에만 appendix)
✓ assets/ 에 PNG 복사만 허용 (원본 미변경)
✓ packet md/html 만 신규 생성
✓ silent missing artifact 금지 — explicit missing_data 기록
```

---

## 9. Test plan

`tests/test_phase_e12_review_packet.py`:

1. ETF markdown packet 생성 + 4 core image 임베드.
2. Fund markdown packet 생성.
3. Both packet 생성 (ETF + Fund 비교 섹션 포함).
4. HTML packet 생성 (`--format html`, `--format both`).
5. limitation text 명시 검증:
   - "relaxed diagnostic"
   - "rule-based" / "not optimized TAA" / "not regime-conditioned"
   - "ticker mapping unavailable" or 동등 표현
6. missing_data 통합 (5 phase 항목 모두 포함 or 명시 부재 사유).
7. assets/ 복사 검증 (원본 sha256 == 사본 sha256).
8. source JSON / PNG mutation 없음.
9. CLI smoke (md / html / both / appendix).
10. pytest 전체 green.

---

## 10. 다음 phase 후보 (E-12 이후)

| candidate | 영역 |
|---|---|
| E-13 | MVP-X deprecation / replacement (figures_polish 정식 deprecate 또는 packet appendix 로 격하 결정) |
| E-14 | Final report design polish (typography / 색상 정합 / 인쇄 layout 강화) |
| E-15 | PDF export (HTML → PDF wkhtmltopdf / weasyprint 도입) |

각 후속 phase 는 별도 sign-off 필요. 본 turn = E-12A design + E-12B implementation.

---

## 11. 한 줄 요약

> **E-12 = 4 standalone 차트 (E-8/E-9/E-10/E-11B) 를 운용역 review packet 1개 (md+html) 로
> 묶는 packaging phase. 새 분석 차트 미생성, allocation/TAA/selection 미변경,
> assets/ PNG 복사만, 모든 missing_data 통합, MVP-X 는 opt-in appendix only.**
