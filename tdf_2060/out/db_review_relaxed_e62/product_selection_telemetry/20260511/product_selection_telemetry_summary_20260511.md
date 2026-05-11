# Product Selection Score Telemetry Summary (20260511)

> schema_version: e11a.1
> Read-only diagnostic. selection logic / allocation 결과 미변경 (bit-identical 검증 통과).

## ETF

- portfolio as_of: **2026-03-31**, source: **db**
- universe: total=932, raw=932, passed_filter=736, classified=572
- score_method: **hard_filter**, factors=5, scored_products=395, selected=17

### universe.by_asset

| asset_key | raw | eligible | selected |
|---|---:|---:|---:|
| dm_ex_us_equity | 15 | 14 | 3 |
| em_equity | 55 | 36 | 3 |
| kr_aggregate_bond | 97 | 0 | 0 |
| kr_equity | 347 | 304 | 3 |
| kr_treasury_10y | 10 | 0 | 0 |
| us_growth_equity | 22 | 22 | 3 |
| us_high_yield | 2 | 2 | 2 |
| us_treasury_30y | 6 | 0 | 0 |
| us_value_equity | 18 | 17 | 3 |

### final_selection.selected_products

| asset_key | product_id | product_name | manager | rank | score | weight |
|---|---|---|---|---:|---:|---:|
| us_growth_equity | 426030 | 타임폴리오TIME미국나스닥100액티브상장지수(주식) | 타임폴리오자산운용 | 1 | 83.3879 | 20.00% |
| us_growth_equity | 411420 | 삼성KODEX미국나스닥AI테크액티브상장지수[주식] | 삼성운용 | 2 | 79.1210 | 20.00% |
| us_growth_equity | 381180 | 미래에셋TIGER미국필라델피아반도체나스닥상장지수(주식) | 미래에셋운용 | 3 | 70.0295 | 20.00% |
| us_value_equity | 402970 | 한국투자ACE미국배당다우존스상장지수(주식) | 한국투자신탁운용 | 1 | 46.3980 | 20.00% |
| us_value_equity | 446720 | 신한SOL미국배당다우존스상장지수[주식] | 신한자산운용 | 2 | 46.1828 | 4.66% |
| us_value_equity | 429000 | 미래에셋TIGER미국S&P500배당귀족상장지수(주식) | 미래에셋운용 | 3 | 37.3153 | 4.66% |
| em_equity | 446690 | 삼성KODEX아시아AI반도체exChina액티브상장지수[주식] | 삼성운용 | 1 | 96.2103 | 1.76% |
| kr_equity | 434730 | NH-AmundiHANARO원자력iSelect상장지수(주식) | NH-Amundi운용 | 1 | 155.6356 | 1.76% |
| em_equity | 105010 | 미래에셋TIGER라틴상장지수(주식) | 미래에셋운용 | 2 | 53.6687 | 1.06% |
| em_equity | 277540 | 한국투자ACE아시아TOP50상장지수(주식) | 한국투자신탁운용 | 3 | 52.6580 | 1.06% |
| kr_equity | 449450 | 한화PLUSK방산상장지수(주식) | 한화운용 | 2 | 152.0764 | 1.06% |
| kr_equity | 433500 | 한국투자ACE원자력TOP10상장지수(주식) | 한국투자신탁운용 | 3 | 148.6765 | 1.06% |
| dm_ex_us_equity | 238720 | 한국투자ACE일본Nikkei225상장지수(주식-파생)(H) | 한국투자신탁운용 | 1 | 49.1052 | 0.96% |
| dm_ex_us_equity | 101280 | 삼성KODEX일본TOPIX100상장지수[주식] | 삼성운용 | 2 | 47.4795 | 0.96% |
| dm_ex_us_equity | 251350 | 삼성KODEXMSCI선진국상장지수[주식] | 삼성운용 | 3 | 46.5682 | 0.96% |
| us_high_yield | 468380 | 삼성KODEXiShares미국하이일드액티브상장지수[채권-재간접] | 삼성운용 | 1 | 27.4297 | 0.00% |
| us_high_yield | 455660 | 한국투자ACE미국하이일드액티브상장지수[채권-재간접](H) | 한국투자신탁운용 | 2 | 17.6621 | 0.00% |

### diagnostics.missing_data

- **final_selection.selected_products[].ticker** — Bloomberg/Reuters ticker 표기 불가 → next: 외부 ticker mapping table 도입 또는 DBProductRepository.product_metadata 확장
- **scoring.score_factors[].cost_penalty** — 비용 패널티 미사용 (weight=0.0) → next: future phase — fee/expense ratio 데이터 도입

## Fund

- portfolio as_of: **2026-03-31**, source: **db**
- universe: total=781, raw=781, passed_filter=414, classified=262
- score_method: **score_penalty**, factors=5, scored_products=208, selected=17

### universe.by_asset

| asset_key | raw | eligible | selected |
|---|---:|---:|---:|
| dm_ex_us_equity | 15 | 15 | 3 |
| em_equity | 72 | 72 | 3 |
| kr_aggregate_bond | 40 | 0 | 0 |
| kr_equity | 99 | 99 | 3 |
| kr_treasury_10y | 4 | 0 | 0 |
| us_growth_equity | 10 | 10 | 3 |
| us_high_yield | 10 | 10 | 3 |
| us_treasury_30y | 10 | 0 | 0 |
| us_value_equity | 2 | 2 | 2 |

### final_selection.selected_products

| asset_key | product_id | product_name | manager | rank | score | weight |
|---|---|---|---|---:|---:|---:|
| us_growth_equity | 76305 | KB미국대표성장주자(주식)(UH)C-퇴직 | KB운용 | 1 | 45.1470 | 30.00% |
| us_value_equity | 70467 | 한국투자미국배당귀족자UH(주식)(C-R) | 한국투자신탁운용 | 1 | 26.6587 | 21.92% |
| us_growth_equity | 74176 | 삼성미국그로스자UH[주식-재간접]_Cp(퇴직연금) | 삼성운용 | 2 | 29.7045 | 20.30% |
| us_growth_equity | 73125 | AB미국그로스UH(주식-재간접)종류C-P2 | AB자산운용 | 3 | 29.6766 | 20.30% |
| us_value_equity | 70455 | 한국투자미국배당귀족자H(주식)(C-R) | 한국투자신탁운용 | 2 | 17.9962 | 5.48% |
| em_equity | 2074 | NH-Amundi성장중소형주[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | 1 | 61.1890 | 0.80% |
| kr_equity | 43306 | 한국밸류10년투자파이오니아(주식)(C-Re) | 한국투자밸류운용 | 1 | 90.3132 | 0.80% |
| em_equity | 71972 | 마이다스아시아리더스성장주자(H)(주식)C-P2 | 마이다스운용 | 2 | 55.4582 | 0.10% |
| em_equity | 71976 | 마이다스아시아리더스성장주자(UH)(주식)C-P2 | 마이다스운용 | 3 | 54.9564 | 0.10% |
| kr_equity | 43040 | NH-Amundi필승코리아[주식]ClassC-P2(퇴직연금) | NH-Amundi운용 | 2 | 78.0547 | 0.10% |
| kr_equity | 41944 | 교보악사파워인덱스자 1[주식]ClassCP | 교보악사운용 | 3 | 70.0344 | 0.10% |
| us_high_yield | 71800 | 베어링글로벌하이일드자[UH](채권-재간접)ClassC-P2e | 베어링운용 | 1 | 32.7665 | 0.00% |
| us_high_yield | 71791 | 베어링글로벌하이일드자[H](채권-재간접)ClassC-P2 | 베어링운용 | 2 | 16.4028 | 0.00% |
| us_high_yield | 74369 | 교보악사미국코어하이일드자(UH)[채권-재간접]_ClassC-Re(퇴직연금 | 교보악사운용 | 3 | 16.2624 | 0.00% |
| dm_ex_us_equity | 42669 | 한화천연자원자(주식)P클래스 | 한화운용 | 1 | 53.2596 | 0.00% |
| dm_ex_us_equity | 71463 | 피델리티재팬자(주식-재간접)CP | 피델리티운용 | 2 | 52.9513 | 0.00% |
| dm_ex_us_equity | 70744 | 삼성일본리더스전환자 1[주식](Cp(퇴직연금)) | 삼성운용 | 3 | 48.3389 | 0.00% |

### diagnostics.missing_data

- **final_selection.selected_products[].ticker** — Bloomberg/Reuters ticker 표기 불가 → next: 외부 ticker mapping table 도입 또는 DBProductRepository.product_metadata 확장
- **scoring.score_factors[].cost_penalty** — 비용 패널티 미사용 (weight=0.0) → next: future phase — fee/expense ratio 데이터 도입
