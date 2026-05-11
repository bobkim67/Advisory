# DB Schema — ${DB_HOST}

수집 일시: 2026-05-07. `information_schema` 자동 추출 + 테이블명/CLAUDE.md 기반 용도 추론.

내부망 전용. 접속: `solution / ${DB_PASSWORD}`. Charset: `utf8mb4` (단 `dt`는 `utf8` 권장).

| DB | 테이블 | 컬럼 | 용도 |
|---|---:|---:|---|
| `dt` | 42 | 1,468 | 펀드 운용 데이터 (기준가/보유/거래/PA + 벤치마크 인덱스) |
| `SCIP` | 16 | 73 | 시장 시계열 데이터 (FactSet/Bloomberg/OECD blob) |
| `solution` | 80 | 771 | 로보어드바이저 백엔드 + VP/MP 리밸런싱 + 자산 유니버스 |
| `cream` | 4 | 41 | 제로인 펀드 데이터 |

총 142 테이블 / 2,353 컬럼. 컬럼 상세는 information_schema 재조회로 언제든 추출 가능.

---

## 1. dt — 펀드 운용 (42개)

운용사 필터: `IMC_CD = '003228'` (한국투자신탁운용).
부서 필터: `DEPT_CD IN ('166','061','064')`.

### 1.1 펀드운용 핵심 — DWPM* (11개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `DWPM10510` | 1.07M | 74 | **펀드 기준가** (NAV/MOD_STPR/DD1_ERN_RT) — SAA 성과 분석의 출발점 |
| `DWPM10530` | 12.06M | 85 | **펀드 보유내역** (ITEM_CD/EVL_AMT/NAST_TAMT_AGNST_WGH) — 자산배분 분해 |
| `DWPM10520` | 558k | 47 | 펀드 거래내역 (매매수량/단가/매매손익) |
| `DWPM12880` | 1.29M | 18 | 설정해지 거래 (OPNG/CLSR amt) |
| `DWPM10040` | 2.08M | 42 | **기간 수익률** (1D~5Y/YTD/설정후, F=펀드/B=BM 구분) |
| `DWPM10041` | 285k | 44 | 서브BM별 수익률 (복합BM 구성요소) |
| `DWPM10120` | 477k | 15 | 예수금 설정/환매 (모자펀드 자금 흐름) |
| `DWPM11030` | 88M | 13 | 총계정원장 (계정과목별 차/대변) |
| `DWPM11060` | 293k | 66 | 외화 미결제 (해외 매매 후 결제 미완료) |
| `DWPM12790` | 189k | 15 | 해외현금 거래내역 |
| `DWPM12900` | 411k | 19 | 해외미수채권 |

### 1.2 마스터 — DWPI* (2개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `DWPI10011` | 771 | 152 | **펀드 기본정보** (FUND_NM/SET_DT/MNC_DS_CD 모자/HDG_YN/약관 등) |
| `DWPI10021` | 3.87M | 68 | **종목 기본정보** (ITEM_NM/ISIN_CD/GICS/TKR_CD/거래국가) |

### 1.3 참조/공통 — DWCI* (6개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `DWCI10160` | 5,577 | 23 | 거래코드 (TR_CD/SYNP_CD → 매매/설해 거래 라벨) |
| `DWCI10170` | 4,481 | 12 | 공통그룹코드 |
| `DWCI10180` | 60,631 | 26 | 공통코드 (구분코드의 코드명 매핑) |
| `DWCI10220` | 18,672 | 12 | **달력/영업일** (HLDY_YN/DAY_DS_CD) — 컬럼명 *소문자* 주의 |
| `DWCI10260` | 545k | 12 | **환율** (CURR_DS_CD/TR_STD_RT) |
| `DWCI10310` | 5,141 | 21 | 매매처 코드 |

### 1.4 성과 / 보수 / 외부 — (5개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `MA000410` | 13.95M | 18 | **펀드 성과분해 (Brinson PA)** — PL_GB(평가/환산/이자/배당/매매), MODIFY_UNAV_CHG |
| `BOS3203` | 3,661 | 8 | 보수율 정보 (FEE_RATE_BP, 기간별 적용) |
| `FDTFN001` | 177k | ? | 제로인 일별 분석 (보조) |
| `FDTFN201` | 108M | 73 | **제로인 펀드데일리분석** — 자산별 평가액 73컬럼 |
| `FDTPF301` | 158M | 24 | 펀드보유내역 — 협회 |

### 1.5 벤치마크 / 외부 인덱스 — (4개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `BMJISU` | 15,544 | 15 | **KIS 채권지수** (Duration/Convexity/YTM) |
| `MI_DJISU` | 74,285 | 35 | **MSCI 지수** (PE/PB/EPS/ROE/PriceToBook) — Tab4 매크로 지표 후보 |
| `MI_DSJISU` | 304k | 4 | MSCI 섹터지수 비중 |
| `MI_CTY_W` | 574k | 4 | MSCI 국가별 비중 |

### 1.6 CRSP / Bloomberg TDF 인덱스 — (13개)

TDF 벤치마크 구성종목 / 리밸런싱 추적용. **현재 미사용**. 섹터·국가 attribution 시 활용.

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `CR_EOD0IX` | 213k | ? | CRSP 인덱스 레벨 |
| `CR_EOD0JG_O` | 15.6M | ? | CRSP 구성종목 (T+1 시가 기준) |
| `CR_EOD0JG_C` | 16.1M | ? | CRSP 구성종목 (T 종가 기준) |
| `CR_EOD0CA` | 7,193 | ? | CRSP 편출입 이벤트 |
| `BB_EOD0IX` | 1,278 | ? | Bloomberg TDF ETF 인덱스 |
| `BB_TDF0JG` | 3,550 | ? | Bloomberg TDF/자산배분 인덱스 |
| `BB_LVLOPN`/`BB_LVLCLS` | 32k | ? | Bloomberg DM/EM/EMV/DXAVP 레벨 (open/close) |
| `BB_HLDOPN`/`BB_HLDCLS` | 184k/11.3M | ? | Bloomberg 종목별 Holdings (open/close) |
| `BB_HLDDLT` | 56k | ? | Bloomberg Holdings 변동분 |
| `BB_HLDPFM` | 1.24M | ? | Bloomberg 리밸런싱 예정 포트폴리오 |
| `BB_IDXEVT` | 1.3M | ? | Bloomberg 인덱스 이벤트 (편출입/배당) |

### 1.7 판매사 — (1개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `ST_KITCA_DS` | 207M | 17 | **판매사별 설정현황** — 판매사/운용/수탁/사무수탁 보수 분해 |

---

## 2. SCIP — 시장 시계열 (16개)

Django 백엔드. 핵심은 4개 `back_*` 테이블.

### 2.1 시계열 데이터 핵심 — back_* (5개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `back_datapoint` | 1.67M | 9 | **시계열 데이터** — `data` longblob (3 패턴: dict/숫자/문자열). `parse_data_blob()` 필수 |
| `back_dataset` | 396 | 5 | **종목/자산 정의** (id/name/ISIN/symbol). `ISIN`이 dt.DWPM10530.ITEM_CD와 매칭 |
| `back_dataseries` | 40 | 4 | 시리즈 정의 (id=6 FG Return, 15 FG Price, 24 12M Fwd P/E, 31 12M Fwd EPS, 39 Total Return Index 등) |
| `back_source` | 8 | 2 | 데이터 소스 (3=Factset, 4=OECD, 5=Bloomberg, 6=Solution, 7=User, 11=FRED, ...) |
| `back_dataseriesupdate` | 544 | 5 | dataseries 갱신 이력 |

핵심 dataset: `id=11` Vanguard Growth ETF, `id=24` S&P 500 TR, `id=31` USD/KRW, `id=37` Vanguard FTSE EM, `id=403` VIX, `id=406` UST 10Y-2Y curve, `id=408` Gold Spot.

### 2.2 Django 인증/관리 — (11개)

| Table | Rows | 용도 |
|---|---:|---|
| `auth_user` | 42 | Django 사용자 |
| `auth_group`/`auth_permission` 등 | 0~180 | Django 권한 |
| `django_session` | 37,776 | 세션 |
| `django_admin_log` | 1,301 | admin 변경 이력 |
| `django_content_type`/`django_migrations` | 14/35 | Django 메타 |
| `knox_authtoken` | 89 | API 토큰 |

> **사용 안 함**. 데이터 분석에서는 `back_*` 5개만 보면 됨.

---

## 3. solution — 로보어드바이저 + VP/MP + 자산분류 (80개)

내용이 가장 큼. 6개 그룹.

### 3.1 로보어드바이저 백엔드 — roboadvisorAPI_* (37개)

별도 Django 앱. **MP/CMA/Glidepath/Benchmark/Universe/Account** 등 운용 시스템 핵심.

| Table | Rows | 용도 |
|---|---:|---|
| `_modelportfolio` | 84 | MP 정의 (vintage/시나리오 단위) |
| `_normalizedmodelportfolio` | 26 | 정규화 MP |
| `_normalizedmodelportfolioweight` | 24,640 | 정규화 MP 자산 비중 |
| `_riskadjustedmodelportfolio` | 256 | 리스크 조정 MP |
| `_riskadjustedmodelportfolioweight` | **359,773** | 리스크별 자산 비중 (대량) |
| `_virtualportfolio` | 265 | VP 정의 |
| `_virtualportfolioweight` | **352,440** | VP 자산 비중 (대량) |
| `_capitalmarketassumption` | 4 | CMA 시나리오 (Phase C SCIP 연결 후보) |
| `_cmacomponent` | 155 | CMA 자산 정의 |
| `_cmacorrelation` | 2,449 | 자산 상관행렬 |
| `_glidepath` | 4 | **글라이드패스 정의** — DRM 보호된 xlsx의 DB 버전 후보 |
| `_glidepathdetail` | 1,017 | 글라이드패스 vintage×자산 비중 |
| `_benchmark`/`_benchmarktimeseries` | 26/3,799 | 벤치마크 정의/시계열 |
| `_equitybenchmarkweights` | 5,159 | 주식 BM 가중치 |
| `_security`/`_securitytimeseries` | 109/29,234 | 증권 마스터/시계열 |
| `_securitytype`/`_securitygeography` | 2/2 | 증권 분류 |
| `_basket`/`_basketcomponent` | 27/91 | 바스켓 정의 |
| `_universe`/`_universecomponent` | 2/25 | 유니버스 정의 |
| `_economicregime` | 7,550 | **경기 국면 시계열** — Regime 분석 후보 |
| `_algorithm` | 6 | 알고리즘 메타 |
| `_riskappetite` | 9 | 리스크 성향 |
| `_account*` 6종 | 0~15,699 | 계정/포트폴리오 원장 |
| `_mutualfundweight` | 14,303 | 펀드 비중 |
| `_questionnaire*` 4종 | 0 | 설문지 (미사용) |
| `_peeraccount*` 2종 | 0 | 동료 계정 (미사용) |
| `_userprofile` | 48 | 사용자 프로필 |
| `_transactiontype` | 5 | 거래 유형 |

> **Phase C 핵심 후보**: `_glidepath`/`_glidepathdetail`(GlidePath xlsx 대체), `_capitalmarketassumption`/`_cmacorrelation`(CMA), `_economicregime`(Regime), `_modelportfolio*`/`_riskadjustedmodelportfolio*`(MP).

### 3.2 자체 sol_* 백업/복사본 (13개)

dt/외부 테이블의 solution-side 복사본 + VP/MP 운영 데이터.

| Table | Rows | 용도 |
|---|---:|---|
| `sol_DWPM10510` | 25,111 | dt.DWPM10510 복사 (VP 기준가) |
| `sol_DWPM10530` | 312,172 | dt.DWPM10530 복사 (VP 보유) |
| `sol_DWPI10021` | **12.4M** | 종목 기본정보 복사 |
| `sol_FDFTN210` | 26M | 제로인 분석 복사 |
| `sol_FDTPF301` | 700k | 협회 보유내역 복사 |
| `sol_FFIO90002` | 413k | 추가 외부데이터 복사 (불명) |
| `sol_VP_rebalancing_inform` | 282 | **VP 리밸런싱 이력** (펀드/경기국면/ISIN/weight/version) |
| `sol_MP_released_inform` | 2,222 | **MP 발표/버전 관리** (Release_date/펀드/경기국면/ISIN/weight/for_ACE) |
| `sol_fund_classification` | 409 | 펀드 분류 매핑 |
| `sol_index_inform` | 112 | 인덱스 정보 |
| `sol_universe_inform` | 393 | 자산유니버스 분류 기준 |
| `sol_wrap_pr` | 33 | 랩상품 기준가 |
| `sol_wrap_details` | 429 | 랩상품 보유종목 |

### 3.3 자산 유니버스/분류 (6개)

| Table | Rows | 용도 |
|---|---:|---|
| `universe_non_derivative` | 2,847 | **비파생 자산 유니버스** (primary_source_id ↔ SCIP.back_dataset.id 매핑) |
| `universe_derivative` | 22 | 파생 자산 분류 |
| `universe_classification` | 25 | 자산 분류 정의 |
| `classification_method` | 5 | 분류 방법 코드 |
| `classification_value` | 25 | 분류 값 코드 |
| `non_derivatives` / `non_derivatives_classification` | 557 / 2,122 | 비파생 종목 분류 (보조) |

### 3.4 DO 상품 / 일별 리포트 (5개)

| Table | Rows | 용도 |
|---|---:|---|
| `do_product_info` | 315 | DO 상품 정의 |
| `do_product_components` | 1,852 | DO 상품 구성 |
| `do_component_info` | 142 | DO 구성종목 정보 |
| `do_performance` | 2,485 | DO 성과 |
| `daily_report` | 102 | 일별 리포트 메타 |

### 3.5 Django 인증 + 협회 코드 (12개)

`auth_*`(6) / `django_*`(4) / `knox_authtoken`(1) — Django 표준.
`fi_cd_by_kfti`(112) — KFTI 펀드 코드. `imc_cd_by_kfia`(56) — KFIA 운용사 코드.

### 3.6 기타 운영 (4개)

| Table | Rows | 용도 |
|---|---:|---|
| `krx_etf_bydd_trd` | **1.49M** | KRX ETF 일별 체결 (대량) |
| `DOMP001` | 2,736 | DO MP (불명) |
| `file_audit_log` | 4 | 파일 감사 로그 |
| `users` | 1 | 단일 user (테스트?) |

---

## 4. cream — 제로인 (4개)

| Table | Rows | Cols | 용도 |
|---|---:|---:|---|
| `data` | 241,080 | ? | **제로인 펀드 가격** (date/fundCode/price = SUIK_JISU 수익지수) |
| `deposit` | 241,080 | ? | 예금/설정해지 금액 (data와 동일 행수 → 페어 추정) |
| `fundlist` | 209 | ? | **제로인 펀드 목록** (fundCode/fundName) |
| `report` | 65,874 | ? | 제로인 리포트 데이터 |

---

## 5. 핵심 연결 고리

```
SCIP.back_dataset.ISIN  ⇄  dt.DWPM10530.ITEM_CD
SCIP.back_dataset.id    ⇄  solution.universe_non_derivative.primary_source_id
solution.sol_VP_rebalancing_inform.ISIN  ⇄  dt.DWPM10530.ITEM_CD
cream.fundlist.fundCode  ⇄  dt.DWPI10011 (협회펀드코드 매핑 필요)
```

가격 우선순위:
- `dataseries_id=6` (FG Return) 우선, fallback `id=39` (Total Return Index)
- 환율: `dataset_id=31, dataseries_id=6` → blob `"USD"` 키

USD 자산 시차: T일 KRW 기준가 = USD가격(T-1) × 환율(T).

---

## 6. Phase C 진입 시 우선 확인 테이블

1. **`SCIP.back_datapoint`** — `dataset_id=31` (USDKRW), `dataseries_id=6/15/39` 이용해 Asset_rt_vol/Corr_mat 자체를 SCIP 시계열로 산출 가능.
2. **`solution.roboadvisorAPI_glidepath` + `_glidepathdetail`** — DRM xlsx 대체. vintage별 SAA 비중이 DB에 이미 존재할 가능성 높음.
3. **`solution.roboadvisorAPI_capitalmarketassumption` + `_cmacomponent` + `_cmacorrelation`** — CMA가 DB에 정의되어 있다면 `CapitalMarketAssumptionBuilder`를 file 대신 DB로 갈아끼움.
4. **`solution.roboadvisorAPI_economicregime`** — Regime 시계열 7,550건. `regime_src` 대체 후보.
5. **`solution.universe_non_derivative.primary_source_id`** — `asset_mapping.yaml::db_dataset_id` 채울 1차 단서.
6. **`dt.DWPI10021`** — 종목 ISIN_CD/GICS_IDTP_CD/거래국가 — universe classifier 보강 후보 (펀드명 키워드 외 정확한 분류 가능).

---

## 7. 컬럼 상세

컬럼별 타입/NULL/KEY/COMMENT 명세는 information_schema에서 자동 추출 가능 (`tools/run_*` 형태로 별도 추출 권장).
필요 시:

```python
import pymysql
c = pymysql.connect(host='${DB_HOST}', user=${DB_USER}, password='${DB_PASSWORD}', db='dt', charset='utf8mb4')
with c.cursor() as cur:
    cur.execute("""
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
        FROM information_schema.columns
        WHERE TABLE_SCHEMA='dt' AND TABLE_NAME='DWPM10510'
        ORDER BY ORDINAL_POSITION
    """)
    for r in cur.fetchall(): print(r)
```

이 매뉴얼은 카탈로그 수준이며 실제 데이터 샘플/분포는 검증되지 않음. blob 파싱·실제 row 검증은 사용 시점에 별도 확인.
