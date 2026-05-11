# Phase E — Next Session First Prompt

작성일: 2026-05-11 (E-12 완료 직후). **다음 세션 진입 시 사용할 first prompt 텍스트**.

본 문서는 두 부분으로 구성:
1. §1 — **세션 시작 시 즉시 실행할 액션 (handoff sanity)**
2. §2 — **사용자가 Claude 에게 보낼 first prompt 후보 (선택지 4건)**

---

## 1. 세션 시작 즉시 실행 (handoff sanity)

새 세션 시작 시 Claude 가 자동으로 실행해야 할 단계 — 사용자 first prompt 와 무관하게 항상 동일:

```text
1. 메모리 정독:
   - C:\Users\user\.claude\projects\C--Users-user-Downloads-python-Advisory\memory\MEMORY.md (인덱스, 12 항목)
   - memory/project_state.md (Phase E-12 완료 상태)
   - memory/phase_e_visualization_state.md (E-6.2~E-12 6 turn 누적)
   - memory/feedback_taa_rule_based_label.md ("optimized TAA" 라벨 금지)
   - memory/feedback_mvpx_prototype_only.md (MVP-X = appendix only)
   - memory/reference_bit_identical_baseline.md (selection 코드 변경 시 baseline 검증)

2. 정본 문서 정독:
   - tdf_2060/docs/phase_e_current_handoff.md (2026-05-11 갱신, E-7~E-12 완료 반영)
   - tdf_2060/docs/phase_e12_integrated_review_packet.md (E-12 설계, 가장 최근)

3. pytest sanity:
   /c/Users/user/Downloads/python/.venv/Scripts/python.exe -m pytest tdf_2060/tests/ -q
   기대: 240 passed, 5 skipped, 1 xfailed

4. 산출물 sanity (production / 직전 phase 산출물 untouched):
   sha256 검증 8건 (E-7~E-11B PNG / JSON + e62/e62_e11a portfolio + taa_policy.yaml + MVP-X).
   기존 phase_e_current_handoff.md §4.5 의 디렉토리 트리와 일치 확인.

5. 사용자 first prompt 대기 — §2 의 선택지 중 사용자 결정 입력.
```

기대치 미달 시 (예: pytest fail / 산출물 missing) — **코드 변경 진입 금지**, 사용자에게 root cause 보고 + 복구 방안 제안 후 명시 승인 받기.

---

## 2. First Prompt 후보 (사용자가 보낼 텍스트)

사용자는 아래 4 옵션 중 1개를 선택해 보냄. 각 옵션은 Claude 에게 명확한 진입점을 제공.

### Option A — E-13 진입 (MVP-X deprecation / replacement)

```text id="e13-prompt"
Claude, 새 세션 진입.

이전 세션에서 Phase E-12 (Integrated Review Packet) 까지 완료했다.
정본은 tdf_2060/docs/phase_e_current_handoff.md (2026-05-11 갱신).
pytest 240 passed 가 baseline.

다음은 E-13 MVP-X deprecation / replacement 으로 진행한다.

Goal:
figures_polish/ 디렉토리의 MVP-X 1-page bridge PNG 를 명시 deprecated 로 격하 또는 제거.
신규 분석 차트 미생성, E-7~E-12 산출물 변경 없음.

Required design decision (사용자 결정 필요):
1. figures_polish/ 디렉토리 자체 제거
2. figures_polish/ → figures_polish/_deprecated/ 로 이동
3. 유지하되 README / packet 내 "MVP-X = prototype only, deprecated" 명시만

권고: option (2) — 보존 + 명확한 deprecation 라벨. 단 사용자 결정 후 진입.

Hard requirements:
- E-12 packet 의 --include-appendix 옵션 호환성 유지
- pytest 240 baseline 유지
- 기존 production output unchanged
- Decision Register count = 14 unchanged
```

### Option B — E-14 진입 (Final report design polish)

```text id="e14-prompt"
Claude, 새 세션 진입.

이전 세션에서 Phase E-12 까지 완료했다. pytest 240 passed.
정본 = tdf_2060/docs/phase_e_current_handoff.md.

다음은 E-14 Final report design polish 로 진행한다.

Goal:
E-12 review_packet.py 의 HTML CSS / typography / 인쇄 layout / 표 너비 polish.
시각 polish 만 — data / 분석 / allocation 미변경.

Scope:
1. review_packet.py 의 _HTML_CSS 강화
   - font-family 정합 (Malgun Gothic + DejaVu Sans fallback)
   - @media print rule 강화 (페이지 break 힌트, A4 base)
   - 테이블 너비 조정 (max-width, overflow-wrap)
   - 색상 정합 (E-8~E-11B 차트 색상과 packet text 색상 일관성)
2. md / html 본문은 변경 없음 (CSS 만)
3. ETF / Fund / Both packet 재렌더 + 시각 확인

Hard requirements:
- review_packet.py 외 모든 모듈 미변경
- 4 standalone PNG 미변경 (assets/ 복사 그대로)
- pytest 240 baseline 유지
- HTML 외부 JS 의존 없음 (inline CSS only)
```

### Option C — E-15 진입 (PDF export)

```text id="e15-prompt"
Claude, 새 세션 진입.

이전 세션에서 Phase E-12 까지 완료. pytest 240 passed.
정본 = tdf_2060/docs/phase_e_current_handoff.md.

다음은 E-15 PDF export 진입을 검토한다.

Step 1 — 환경 평가 (코드 변경 없이 검토만):
- weasyprint Windows install 가능성 (Cairo / Pango 의존)
- wkhtmltopdf Windows binary 가용성
- playwright headless Chrome install 부담 (~150MB)

Step 2 — 사용자 결정 후 진입:
- backend 선택
- E-12 HTML → PDF 변환 CLI 신설 (build_review_packet_pdf.py)
- A4 layout + page break 검증

Hard requirements:
- E-12 HTML structure 미변경 (PDF 변환 input 으로만 사용)
- 새 분석 차트 미생성
- pytest 240 baseline 유지 (PDF test 는 add)
- Windows 환경에서 install 검증 필수
```

### Option D — 운용역 결정 입력 대기 / sanity 점검

```text id="ops-prompt"
Claude, 새 세션 진입.

이전 세션에서 Phase E-12 까지 완료. pytest 240 passed.
정본 = tdf_2060/docs/phase_e_current_handoff.md.

새 phase 진입 없이 운용역 결정 입력 대기 또는 sanity 점검만 진행한다.

가능한 작업:
1. pytest 240 + 산출물 sha256 sanity 점검 (자동 실행, 보고만)
2. Decision Register 14 건 상태 확인 (D-06 pending_external / D-11/12/14 deferred / D-13 closed 등)
3. E-7~E-12 산출물 디렉토리 트리 점검 (정본 §4.5 와 일치 검증)
4. 운용역 결정 입력 시 적용 위치 미리 식별:
   - D-06 ERR 정의 → optimization_constraints.yaml::err
   - D-11 (dm_ex_us lower bound) → tdf_2060.yaml::final_asset_bounds
   - D-12 (us_value cap) → tdf_2060.yaml::final_asset_bounds
   - D-14 (manager concentration) → universe_filter.yaml

Hard requirements:
- 코드 변경 없음
- 사용자 결정 없이 정책 변경 진입 금지
- pytest / 산출물 / Decision Register count (14) 모두 unchanged 확인만
```

---

## 3. 추천 진입 순서 (참고)

사용자 결정이 없을 때 Claude 가 제안할 권고 순서:

```
1차: Option A (E-13) — MVP-X deprecation 명확화 (가장 가벼움, 후속 phase 의 정합성 확보)
2차: Option B (E-14) — packet design polish (시각 품질 향상)
3차: Option C (E-15) — PDF export (환경 의존 큼, 결정 신중)
```

또는 사용자가 Option D (대기) 를 선택하면 운용역 결정 입력 시점까지 코드 변경 없이 보존.

---

## 4. Claude 가 자동 거부해야 할 함정 입력 (stale instruction)

다음 종류 입력은 stale 또는 정책 위반 — Claude 는 거부 + 사용자에게 정본 인용:

| 함정 입력 | 거부 사유 |
|---|---|
| "MVP-X 폴리시 더 진행" | `feedback_mvpx_prototype_only.md` — prototype only, polish 추가 금지 |
| "TAA optimizer 도입" | 영구 금지 (handoff §9 + register D-13/D-14) |
| "production mode 로 전환" | 영구 금지 (operating_mode=relaxed_diagnostic) |
| "selection score weights 변경" | bit-identical baseline 깨짐 (`reference_bit_identical_baseline.md`) |
| "asset cap / floor 추가" | 영구 금지 (handoff §9) |
| "Decision Register 에 새 항목 정식 등록" | count=14 유지 (D-15/D-16/D-17 informational candidate only) |
| "MVP-X 를 review packet main 으로 승격" | `feedback_mvpx_prototype_only.md` — main 자격 미달 |
| "regime-conditioned MVO 구현" | TAA = rule-based only (영구), regime_mvo = future_study only |
| 결과 차트만 만들고 main 자격 주장 | `feedback_visualization_construction_story.md` — Regime → MVO → SAA → TAA → Product 흐름 필수 |

---

## 5. 한 줄 요약

> **다음 세션: §1 자동 sanity (메모리 + 정본 + pytest 240) 실행 → §2 Option A~D 중 사용자 1건 선택 →
> Claude 가 정본 (`phase_e_current_handoff.md`) 의 hard requirements 준수하며 진입.
> §4 함정 입력은 거부 + 정본 인용.**
