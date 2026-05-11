# Placement/Velocity 기반 TAA 엔진: 경기 사이클 × DP/MDP/RL/MPC/SP 통합 설계 보고서

> 본 보고서는 글로벌 멀티에셋 OCIO/연기금/TDF 운용을 전제로, 사용자의 placement(레벨)·velocity(모멘텀) 2차원 상태공간 아이디어를 학술 문헌·산업 사례에 매핑하고, 단계별로 구현 가능한 엔진 아키텍처와 한국 퇴직연금 적용 시 제약을 정리한 실무 설계 문서임. Python 클래스 골격 수준의 의사코드만 제공하며, 학습 루프는 포함하지 않음.

---

## 1. Executive Summary

**BLUF.** 사용자의 placement(레벨) × velocity(모멘텀) 프레임은 (i) Merrill Lynch Investment Clock(2004, Greetham–Hartnett)의 "성장 vs 추세, 인플레이션의 방향" 4분면, (ii) Bridgewater All Weather의 "성장↑/↓ × 인플레이션↑/↓" 4박스, (iii) Kritzman·Page·Turkington(FAJ 2012)의 turbulence·growth·inflation 3축 Markov-switching, (iv) Nystrup·Boyd·Lindström·Madsen(Annals OR 2019)의 HMM+MPC drawdown control과 거의 동형이다. 즉 placement/velocity는 새 발명이 아니라 **레짐 식별 → 레짐 조건부 최적화 → 다기간 제어**라는 확립된 3단 파이프라인의 입력 표현(state representation)에 해당한다. 따라서 v0~v7 단계별 로드맵의 핵심은 (a) placement/velocity의 z-score·percentile·기울기를 **누설 없는(expanding window) 표준화**로 만들고, (b) 이 상태에 조건부로 MVO→Markov/HMM→MPC→DRL을 단계 격상시키며, (c) 연기금/TDF 도메인에서는 reward를 Sharpe가 아닌 **funding ratio·shortfall·drawdown 페널티**로 교체하는 것이다.

J.P. Morgan AI Research의 Sood–Papasotiriou–Vaiciulis–Balch(ICAPS FinPlan 2023, "Deep Reinforcement Learning for Optimal Portfolio Allocation")는 본 프로젝트의 **RL 환경 청사진으로 가장 가까운 공개 문헌**이다. 시장 리플레이 환경, softmax 기반 long-only/fully-invested 제약, state에 (현재 비중 ‖ 60일 로그수익 매트릭스 ‖ vol20 ‖ vol20/vol60 ‖ VIX) 포함, Differential Sharpe Ratio reward, expanding lookback 표준화로 정보 누설 차단, 5+1+1년 rolling-train/burn/test, PPO 기반 정책 — 모두 그대로 차용 가능하다. 그러나 TDF/OCIO/LDI 용도로는 **Differential Sharpe를 그대로 쓰지 말고**, funding ratio 변화·shortfall·turnover·drawdown을 가중합한 다목적 reward로 교체해야 한다.

**한국 퇴직연금 특수성.** DC/IRP는 근로자퇴직급여보장법 시행령 §26에 의해 국내·외 개별주식 직접투자가 금지되며, 위험자산 70% 한도가 적용된다. 다만 **"적격 TDF"**는 위험자산 한도 적용에서 면제되어 100% 편입 가능하다. 적격 TDF 요건은 (i) 빈티지가 펀드명에 표시되고 운용계획에 글라이드패스가 명시, (ii) 운용기간 중 주식 비중 80% 초과 금지, (iii) 목표시점 도달 후 주식 40% 이하, (iv) 투자부적격 채권 비중 총자산의 20% 이내, (v) 2025년 4월부터 시행된 강화 기준에서 특정 해외국가 비중 80% 이내·적립기 안전자산 20% 이상·인출기 60% 이상의 분산투자 요건 추가(퇴직연금감독규정 시행세칙 제5조의2 개정). 본 엔진의 한국형 구현은 이 박스 안에서 작동해야 한다.

### TL;DR (3 bullets)

- **Placement(레벨) + velocity(모멘텀)** 2차원 상태공간은 Investment Clock·All Weather·Kritzman 3-factor regime의 일반화이며, 학술적으로 새 발견이 아니라 **표현(representation)** 선택의 문제다. 가치는 (a) 누설 방지 z-score/percentile/slope 파이프라인, (b) 레짐 조건부 최적화 계층화, (c) MPC/DRL의 다기간 의사결정 결합에서 나온다.
- **JPM Sood et al. (2023)** 논문은 본 프로젝트 RL 환경의 직접적 청사진(market replay, softmax long-only, state = weights ‖ 60d log-return matrix ‖ vol20 ‖ vol20/vol60 ‖ VIX, Differential Sharpe Ratio reward, 5y train + 1y burn + 1y test rolling)이며, **DSR을 funding-ratio·drawdown·turnover 가중 reward로 교체하면** TDF/OCIO/LDI에 즉시 이식 가능하다.
- 구현 로드맵은 **v0 룰베이스 틸팅 → v1 placement/velocity 레짐 맵 → v2 레짐 조건부 MVO → v3 HMM/Markov 전이 → v4 rolling-horizon MPC(Boyd+Nystrup 형식) → v5 DP/RL → v6 LDI/funding-ratio reward → v7 글라이드패스 통합**의 단계별 격상이 위험·검증 부담을 최소화하며, 한국 적용 시 적격 TDF 박스(주식 ≤80%·해외 1국가 ≤80%·HY ≤20%·인출기 주식 ≤40%) 안에서 액션을 projection하는 제약 레이어가 필수다.

---

## 2. 사용자의 placement/velocity 아이디어와 기존 문헌 매핑

| 사용자 표현 | 학술/실무 매핑 |
|---|---|
| growth level + growth momentum | Merrill Lynch Investment Clock (Greetham–Hartnett 2004): 출력갭(성장 vs 추세) × 인플레이션 방향. Bridgewater All Weather: 성장↑/↓ × 인플레↑/↓ 4박스 |
| inflation level + inflation momentum | FactSet "Inflation Trend Signal" = 3M annualized CPI − 36M annualized CPI; Kritzman·Page·Turkington(FAJ 2012)의 inflation regime |
| volatility level + vol20/vol60 ratio | Sood et al. (JPM/ICAPS 2023): state에 vol20·vol20/vol60·VIX 포함; Nystrup et al. (Quantitative Finance 2018, Annals OR 2019): HMM 변동성 레짐 |
| credit spread level + change | Sheikh & Sun (2012, J. Investing): "Regime Change"의 4-factor(성장·인플레·통화정책·노동슬랙) |
| OECD CLI level + MoM 변화 | OECD CLI 자체가 추세대비 출력갭을 측정 → 6~9개월 선행. Allocate Smartly의 Global Growth Cycle, Link "GGC Enhanced"가 CLI 확산지수+모멘텀 결합 |
| 4분면 phase plane | Investment Clock 4단계(Reflation/Recovery/Overheat/Stagflation), All Weather 4박스, Guidolin–Timmermann(JEDC 2007)의 4-state regime(crash/slow growth/bull/recovery) |
| 상태 → 자산 비중 매핑 | Bae·Kim·Mulvey(EJOR 2014, KAIST·Princeton): HMM으로 식별한 레짐별 다른 (μ, Σ) → stochastic program으로 동적 자산배분 |

**핵심 통찰.** Placement/velocity는 (level, slope)의 동일 변수 두 모먼트로, 레짐 식별기(rule-based 4분면, Markov-switching, HMM, jump model)의 **입력 피처**로 전부 변환 가능하다. 즉 동일 데이터 표현 위에 v0(rule)→v3(HMM)→v5(DRL)을 갈아끼울 수 있다는 것이 본 프레임의 가장 큰 실무적 이점이다.

---

## 3. Top 10 가장 관련성 높은 문헌 (실무 가치 순위)

1. **Sood, Papasotiriou, Vaiciulis, Balch (2023)**, "Deep Reinforcement Learning for Optimal Portfolio Allocation: A Comparative Study with Mean-Variance Optimization", ICAPS FinPlan'23 / arXiv 2602.17098 — JPM AI Research.
2. **Nystrup, Boyd, Lindström, Madsen (2019)**, "Multi-period portfolio selection with drawdown control", *Annals of Operations Research* 282, 245–271.
3. **Boyd, Busseti, Diamond, Kahn, Koh, Nystrup, Speth (2017)**, "Multi-Period Trading via Convex Optimization", *Foundations and Trends in Optimization* 3(1), 1–76 + cvxportfolio.
4. **Guidolin & Timmermann (2007)**, "Asset allocation under multivariate regime switching", *Journal of Economic Dynamics and Control* 31(11), 3503–3544.
5. **Ang & Bekaert (2002)**, "International Asset Allocation With Regime Shifts", *Review of Financial Studies* 15(4), 1137–1187.
6. **Kritzman, Page, Turkington (2012)**, "Regime Shifts: Implications for Dynamic Strategies", *Financial Analysts Journal* 68(3) — turbulence·inflation·growth Markov-switching.
7. **Bae, Kim, Mulvey (2014)**, "Dynamic asset allocation for varied financial markets under regime switching framework", *European Journal of Operational Research* 234(2), 450–458 — HMM + stochastic program, pension example.
8. **Brennan, Schwartz, Lagnado (1997)**, "Strategic Asset Allocation", *Journal of Economic Dynamics and Control* 21(8–9), 1377–1403 — DP 기반 다기간 자산배분의 표준 레퍼런스.
9. **Brandt, Goyal, Santa-Clara, Stroud (2005)**, "A Simulation Approach to Dynamic Portfolio Choice", *Review of Financial Studies* 18(3), 831–873 — BGSS, 시뮬레이션 기반 DP.
10. **Greetham & Hartnett (Merrill Lynch, 10 Nov 2004)**, "The Investment Clock — Special Report #1: Making Money from Macro" — 성장(출력갭) × 인플레이션 방향의 4 phase 표준.

추가로 (지면관계상 11위 이하 압축): Mulvey & Liu (2016) "Identifying Economic Regimes" *J. Portfolio Mgmt* (downside risk reduction); Nystrup·Hansen·Madsen·Lindström (2015) JPM regime-based vs static; Nystrup·Madsen·Lindström (2018, *Quantitative Finance* 18(1)) HMM+MPC; Geyer & Ziemba (2008, *Operations Research*) InnoALM Austrian pension; Cariño·Ziemba et al. (1994/1998) Russell-Yasuda; Konicz·Pisinger·Rasmussen (2014, *OR Spectrum*) personal pension SP+optimal control; Shu·Yu·Mulvey (2024) statistical jump model; Kim & Kwon (2023, *J. Asset Management*) regime approach with Korean implications; Faria (SSRN 2021) glide path multi-period; Moody·Wu·Liao·Saffell (1998, *J. Forecasting*) Differential Sharpe Ratio.

---

## 4. Top 10 상세 정리

### 4.1 Sood et al. 2023 (JPM/ICAPS) — 본 프로젝트 RL 환경의 레퍼런스 구현

(별도 §5에서 본격 분석)

### 4.2 Nystrup–Boyd–Lindström–Madsen (Annals OR 2019) — HMM + MPC + drawdown control

- **모형구조.** Time-varying parameter multivariate HMM이 forecast (μ̂_τ|t, Σ̂_τ|t) 생성 → MPC가 H-step planning horizon에서 mean-variance 목적+거래/보유비용+drawdown penalty로 해를 풀고 첫 단계 trade만 실행, 다음 시점에 재최적화(receding horizon).
- **지표.** Major liquid asset class index (MSCI World, US Treasury, Developed Real Estate, BofA US HY, US IG, commodities 등) — 2 decade out-of-sample.
- **핵심 메커니즘.** 실현 drawdown D_t에 따라 risk aversion γ를 동적 조정: γ_t = γ_0 · f(D_t / D_max) — drawdown이 한도에 가까울수록 위험회피도 상승. "drawdown control with little or no sacrifice of mean–variance efficiency."
- **차용 포인트.** (a) HMM 한 모듈, MPC 한 모듈로 **분리** 설계 → 사용자 v3·v4 단계와 정확히 일치. (b) drawdown-aware risk aversion은 LDI 펀딩비율 제약과 직접 매핑됨(funding ratio가 buyout 임계치 근접 시 risk aversion 자동 증가).
- **한계.** HMM 가정(state 내부 i.i.d. Gaussian)이 fat tail에 약함 → Nystrup·Lindström·Madsen(2020)의 jump model 또는 Shu·Yu·Mulvey(2024) 통계적 jump model로 대체 가능.

### 4.3 Boyd et al. 2017 (Foundations & Trends in Optimization) — 다기간 컨벡스 최적화 표준 레퍼런스

- **구조.** 매 시점 t에서 다음 풀이:
  
  maximize Σ_{τ=t}^{t+H-1} [α̂_τ^⊤ w_τ − γ_risk · w_τ^⊤ Σ̂_τ w_τ − Φ_trade(w_τ − w_{τ−1}) − Φ_hold(w_τ)]
  
  s.t. 1^⊤w_τ = 1, w_τ ∈ W (long-only/leverage/sector caps 등), τ = t,…,t+H−1.

- **개념적 위치.** "MPC traces back to Markowitz (1952)"; 입력은 **임의의 forecaster**의 (α̂, Σ̂) — 즉 placement/velocity 시그널을 alpha forecaster에 그대로 주입 가능. cvxportfolio 오픈소스 구현 존재.
- **차용 포인트.** Φ_trade는 turnover penalty(L1 + bid-ask), Φ_hold는 borrow cost·short fee — 본 엔진의 거래비용·턴오버 페널티 구현 표준.
- **한계.** Forecast (α̂, Σ̂)을 deterministic으로 취급(certainty equivalent) → stochastic version은 SP/DP가 필요.

### 4.4 Guidolin & Timmermann (JEDC 2007) — 4-state regime, 자산배분에 강한 영향

- **구조.** Stock+bond returns의 결합분포에 4-state(Crash/Slow Growth/Bull/Recovery) Markov-switching 적합. Optimal allocation은 호라이즌·현재 state probability에 따라 비단조(non-monotone). Bull state에선 horizon ↑일수록 stock ↓, Crash state에선 horizon ↑일수록 stock ↑. "Welfare costs from ignoring regime switching can be substantial."
- **차용 포인트.** (a) 단순 2-state(bull/bear)가 아닌 **4-state**가 stock-bond joint distribution에 통계적으로 우수 — 사용자의 "growth × inflation" 4박스와 의미적으로 호환. (b) state probability를 직접 weight 함수의 입력으로 사용하는 패턴.

### 4.5 Ang & Bekaert (RFS 2002) — 국제 자산배분의 regime shift 효시

- **구조.** US/UK/Germany 주식의 regime-switching VAR; high-vol/low-vol 두 레짐, high-vol에서 상관계수·변동성 동시 상승. Conditionally risk-free asset 사용 시 regime 무시 비용 큼.
- **차용 포인트.** Equity correlation breakdown은 high-vol regime에서 발생 → vol20/vol60 ratio가 1을 크게 상회할 때 분산효과 약해짐을 액션에 반영해야 한다는 명시적 근거.

### 4.6 Kritzman, Page, Turkington (FAJ 2012) — 3-factor Markov-switching

- **요인.** Market turbulence(Mahalanobis distance), inflation, economic growth — 각각 2-state Markov-switching, 동적 risk-on/off.
- **결과.** "dynamic process outperformed static asset allocation, especially for investors who seek to avoid large losses." Fully-invested 60/40 대비 max drawdown 큰폭 축소.
- **차용 포인트.** (a) turbulence(Mahalanobis)는 placement/velocity와 직교한 추가 피처. (b) 3-factor independent Markov-switching → state space = 2^3 = 8개 — 사용자의 다차원 phase plane과 호환.

### 4.7 Bae, Kim, Mulvey (EJOR 2014) — HMM + stochastic program (한국인 저자, KAIST)

- **구조.** Stock·bond·commodity·real estate의 multivariate HMM → regime별 (μ, Σ) → scenario tree → multistage SP. Pension fund 예시에서 rolling-horizon으로 검증.
- **차용 포인트.** (a) 한국 연구자가 한국 시장에 가까운 universe로 검증한 거의 유일한 학술 레퍼런스. (b) regime probability를 SP의 시나리오 가중치로 변환하는 구체적 절차 제시.

### 4.8 Brennan, Schwartz, Lagnado (JEDC 1997) — DP 기반 SAA 표준

- **상태변수.** 단기금리 r, 장기금리 R, 배당수익률 d (3차원 Markov 프로세스).
- **방법.** Bellman equation을 grid 위에서 backward induction. 장기 투자자의 최적 비중이 myopic(tactical) 비중과 크게 다름을 처음으로 정량적으로 보임.
- **차용 포인트.** placement 차원(rate level, valuation level)이 정확히 BSL의 state variable과 동형 → DP 베이스라인의 이론적 기초.
- **한계.** 차원의 저주(curse of dimensionality) — 3차원이 실용 한계, 그래서 RL/MPC가 필요.

### 4.9 Brandt, Goyal, Santa-Clara, Stroud (RFS 2005) — BGSS 시뮬레이션 기반 DP

- **구조.** Cross-sectional regression으로 conditional expected utility를 근사 → backward induction. 비표준 선호(loss aversion, recursive utility)와 path-dependent state, 학습/parameter uncertainty 수용.
- **차용 포인트.** RL이 어려운 환경(소량 데이터, 명시적 효용함수 필요)에서 BGSS는 **DRL의 supervised 변형**으로 작동 — 본 엔진 v5의 fallback.

### 4.10 Greetham & Hartnett (ML 2004) — Investment Clock 원전

- **정의.** "ML's Investment Clock splits the economic cycle into four phases depending on the direction of growth relative to trend (i.e., the 'output gap') and the direction of inflation."
- **4 phase·자산 매핑:**

| Phase | Growth(추세대비) | Inflation | Best Asset | Best Equity Sectors | Yield Curve |
|---|---|---|---|---|---|
| I Reflation | ↓ | ↓ | **Bonds** | Defensive Growth | Bull Steepening |
| II Recovery | ↑ | ↓ | **Stocks** | Cyclical Growth | — |
| III Overheat | ↑ | ↑ | **Commodities** | Cyclical Value | Bear Flattening |
| IV Stagflation | ↓ | ↑ | **Cash** | Defensive Value | — |

- **차용 포인트.** v0~v1 룰베이스 baseline의 직접적 청사진. placement = 출력갭 부호, velocity = 인플레이션 변화 부호 → Clock phase 자동 매핑.

---

## 5. JPM Sood et al. (2023) 논문 정밀 분석 — 본 프로젝트 RL 청사진

논문 풀텍스트에서 직접 추출한 사양:

### 5.1 환경(Environment)
- Market replay 방식. 일별 종가 기반 log return r_t = log(P_t/P_{t-1}). Lookback T=60.
- 자산: S&P500 11개 sector indices(2006–2021) + cash. VIX 별도.
- "no transaction costs in the environment, and we allow for immediate rebalancing of the portfolio" — 비용은 future work로 명시.

### 5.2 액션(Action)
- N자산에 대해 w = [w_1,…,w_n], Σw_i = 1, 0 ≤ w_i ≤ 1.
- "constraints can be enforced by applying the softmax function to an agent's continuous actions." → long-only + fully-invested 자동 보장.

### 5.3 상태(State) — 본 프로젝트가 그대로 차용할 표현
S_t는 (n+1) × T 행렬:

| col_0 (현재 weight) | col_1 ~ col_{T} (60일 로그수익) |
|---|---|
| w_1 | r_{1,t-1}, …, r_{1,t-T+1} |
| w_2 | r_{2,t-1}, …, r_{2,t-T+1} |
| ⋮ | ⋮ |
| w_n | r_{n,t-1}, …, r_{n,t-T+1} |
| **w_c** | **vol20, vol20/vol60, VIX_t, …** |

마지막 row(cash row)에 변동성 레짐 시그널을 임베드한 것이 핵심 트릭. **vol20/vol60 > 1** ⇒ low→high vol 전이; **< 1** ⇒ 반대. 모든 vol·VIX는 **expanding lookback z-score**로 표준화하여 정보누설 차단. 사용자의 placement/velocity는 동일 row 또는 추가 row로 자연스럽게 확장된다(예: row +1 = OECD CLI z-score, OECD CLI 3M slope, CPI inflation gap, term spread, IG credit spread).

### 5.4 보상(Reward) — Differential Sharpe Ratio
Sharpe ratio S_t = A_t / [K_t·(B_t − A_t²)^{1/2}], A_t = (1/t)Σ R_i, B_t = (1/t)Σ R_i², K_t=(t/(t-1))^{1/2}. 지수이동평균으로 재귀화하면 differential

**D_t = (B_{t-1} ΔA_t − ½ A_{t-1} ΔB_t) / (B_{t-1} − A_{t-1}²)^{3/2}**

with ΔA_t = R_t − A_{t-1}, ΔB_t = R_t² − B_{t-1}, η ≈ 1/252. 출처: Moody·Wu·Liao·Saffell (1998, *J. Forecasting* 17). DSR을 reward로 쓰면 RL의 step-by-step 보상구조와 Sharpe의 시계열 정의의 부정합을 해결한다.

### 5.5 학습 알고리즘·하이퍼파라미터
- PPO (StableBaselines3). Hyperparameters(논문 Table 1): training_timesteps 7.5M, n_envs 10, n_steps 756, batch_size 1260, n_epochs 16, gamma 0.9, gae_lambda 0.9, clip_range 0.25, lr 3e-4 anneal to 1e-5, MLP [64, 64] tanh, log_std_init = −1.
- 5 random seeds → best-on-validation 선택 → seed로 다음 라운드 정책 초기화.

### 5.6 백테스트 분할 — 정보누설 방지의 표준 프로토콜
10개 sliding 7년 그룹: **5년 train + 1년 burn(validation) + 1년 OOS test**, 1년 단위 shift, 2012–2021. **Burn year**가 train 마지막 시점과 test 사이의 정보누설을 차단하는 결정적 장치.

### 5.7 결과(저자 보고치, Table 2; 10-backtest 평균)

| Metric | DRL | MVO |
|---|---|---|
| Annual return | 0.1211 | 0.0653 |
| Sharpe | 1.1662 | 0.6776 |
| Calmar | 2.3133 | 1.1608 |
| Max drawdown | −0.3296 | −0.3303 |
| Sortino | 1.7208 | 1.0060 |
| Daily VaR | −0.0152 | −0.0181 |

(주의: 결과는 단일 universe·기간이며 거래비용 0 가정 하의 수치다. 본격 배포 전 비용·슬리피지·턴오버 페널티 추가 백테스트 필수.)

### 5.8 그대로 차용 vs 수정 vs TDF/OCIO/LDI 누락

**그대로 차용(as-is).**
1. 시장 리플레이 환경 + 1일 단위 종가 기반 step.
2. Softmax projection으로 long-only/fully-invested 자동 보장.
3. State 행렬에 (current weights ‖ lookback returns ‖ volatility regime row) 구조.
4. **Expanding-window 표준화** — 정보누설 방지 표준.
5. **5y train / 1y burn / 1y test rolling**, 1y shift × 10 windows.
6. 5 seed 병렬 학습 + best-on-validation seed propagation.
7. PPO·하이퍼파라미터를 v0 baseline으로 채택.

**수정(modify).**
1. **Universe 확장.** 11 sector→글로벌 자산군(US/DM/EM equity, UST/DM sov, IG/HY credit, commodities, cash). state row 수만 증가.
2. **State에 placement/velocity row 추가.** 추가 row: OECD CLI z-score, OECD CLI 3M slope, CPI inflation gap(= 3M annualized − 36M annualized, FactSet식), 10y−2y term spread, IG OAS z-score, BAA-AAA spread velocity, S&P 500 forward P/E z-score, valuation percentile.
3. **거래비용·턴오버·드로다운 페널티**를 reward에 명시적으로 추가(논문이 future work로 남긴 항목).
4. **레짐 분기 정책.** "low-volatility agent vs high-volatility agent" 아이디어를 (vol20/vol60·VIX z-score) 기반 게이트로 명시화 — 둘 다 학습한 후, 게이트 모델이 weight 평균화. Mixture-of-experts.

**TDF/OCIO/LDI에 누락된 것·필수 추가 사항.**
1. **Liability/funding ratio 상태.** F_t = A_t / L_t, L_t는 부채 듀레이션·할인율로 평가. State에 z-score로 포함.
2. **수명주기(time-to-retirement).** TDF에선 t→T 까지의 잔여기간이 핵심 상태.
3. **Contribution flow.** DC의 정기 기여금 c_t는 wealth dynamics에 외생적으로 가산.
4. **Reward 교체.** Differential Sharpe만으로는 funding shortfall 회피·glide path 안정성을 표현 불가.

### 5.9 권장 reward 함수 — TDF/OCIO/LDI용

DSR을 **그대로 쓰지 말고** 다음 가중합으로 교체할 것을 권장한다:

**R_t = λ_1 · ΔF_t  − λ_2 · 1{F_t < F̲}·(F̲ − F_t)²  − λ_3 · max(0, DD_t − DD̲)²  − λ_4 · ‖w_t − w_{t-1}‖_1  − λ_5 · CVaR_α(R_t^{port})  + λ_6 · DSR_t**

- ΔF_t: funding ratio 1-step 변화(LDI 핵심).
- 두 번째 항: shortfall(F̲ = 100% 또는 규제 trigger) 비대칭 제곱 페널티.
- 세 번째 항: drawdown 한도(DD̲, 예 −10%) 초과시 quadratic penalty(Nystrup et al. 2019 형식).
- 네 번째 항: turnover L1 페널티(Boyd 2017 Φ_trade).
- 다섯 번째 항: CVaR(Expected Shortfall) 페널티 — fat tail.
- DSR을 잔여 6번째 항으로 두어 TAA 단기 risk-adjusted return 신호도 보존.

λ는 LDI 모드·TDF accumulation/decumulation 모드·OCIO 모드별 프리셋으로 관리.

### 5.10 공정한 MVO vs DRL 백테스트 설계
JPM 논문이 정한 fairness 원칙을 그대로 따르되 강화:
1. **동일 lookback(60일)·동일 표준화·동일 universe·동일 제약·동일 거래비용** 가정.
2. MVO 측 covariance는 Ledoit-Wolf shrinkage(논문이 사용), eigenvalue clipping으로 PSD 보정.
3. MVO 측 목적함수 = Sharpe maximization(DRL이 DSR을 쓰므로 호환).
4. **Burn year 동일 적용** — MVO도 60일 lookback이 burn 외부에서 시작.
5. **벤치마크 다층화.** (i) 60/40 buy-and-hold, (ii) static SAA(IPS), (iii) risk parity, (iv) MVO Sharpe-max, (v) regime-conditioned MVO(레짐별 사전 추정 (μ_k, Σ_k)), (vi) MPC(Boyd 2017), (vii) DRL.
6. **메트릭.** annualized return, Sharpe, Sortino, Calmar, max DD, average turnover, transaction cost-adjusted return, funding ratio terminal distribution(LDI 모드), shortfall probability.

---

## 6. 구현 가능 모델 아키텍처 제안

### 6.1 전체 데이터 흐름

```
[Raw Data]
  ├─ Macro (OECD CLI, GDP, CPI, PMI, term spread, etc.)
  ├─ Market (asset prices, VIX, OAS, valuation ratios)
  └─ Liability (DB cashflows, mortality, discount curve)
        │
        ▼
[MacroFeatureEngine]
  → placement (level z-score, percentile)
  → velocity (1M/3M slope, MoM change, acceleration)
  → vol features (vol20, vol60, vol20/vol60 ratio)
        │
        ▼
[RegimeMapEngine]
  → rule-based 4 phases (Investment Clock)
  → vol regime, credit stress regime
        │
        ▼
[RegimeTransitionEngine]
  → HMM / Markov-switching / jump model
  → P(s_t = k | features), transition matrix
        │
        ▼
[TAAOptimizer]                ←──────── [LiabilityModel] (DB/TDF)
  v0: rule tilt   v1: regime tilt   v2: regime-conditioned MVO
  v3: HMM-conditioned SP    v4: MPC (Boyd/Nystrup)
  v5: DP/RL                 v6: LDI-aware reward
  v7: glide-path-integrated TAA
        │
        ▼
[ConstraintLayer] (long-only, sector caps, Korea risk-asset 70%, 적격 TDF box)
        │
        ▼
[ExecutionLayer] (portfolio weights w_t)
        │
        ▼
[BacktestEngine] ─→ [SignalReport]
```

### 6.2 모듈별 책임

**MacroFeatureEngine** — 입력: raw 시계열. 출력: 표준화된 (level, slope, accel, percentile) 피처 매트릭스. 핵심 함수: expanding-window mean/std, OECD CLI publication lag(통상 1~2주)을 반영한 **point-in-time(PIT)** 정렬. Look-ahead bias prevention은 release date 기준의 sparse forward fill.

**RegimeMapEngine** — placement·velocity 부호 기반 4사분면 라벨링. 추가로 vol regime(vol20/vol60 vs 임계치) 및 credit stress(IG OAS z-score > τ) flag.

**RegimeTransitionEngine** — Hamilton(1989) Markov-switching, multivariate HMM(hmmlearn), Nystrup et al.(2020) penalized-jump HMM, Bemporad·Breschi·Piga·Boyd(2018) statistical jump model 중 **선택 가능한 백엔드**. 출력: P(s_t = k | x_{1:t}), 전이행렬 P̂.

**TAAOptimizer** — 백엔드 다중화:
- `RuleTilter`(v0/v1)
- `RegimeMVO`(v2): 레짐별 (μ_k, Σ_k) 사전 추정 → P(s)로 weighted average → Sharpe-max convex program
- `HMMStochasticProgram`(v3): scenario tree from HMM → multistage SP (Bae·Kim·Mulvey 2014 방식)
- `MPCSolver`(v4): cvxportfolio 기반 receding horizon convex program with Φ_trade, Φ_hold, drawdown-aware γ_t (Nystrup et al. 2019)
- `DRLAgent`(v5): JPM Sood et al. 환경+PPO

**RLEnvironment** — Sood et al.의 정확한 카피. softmax 액션, market replay, expanding standardization. **단, reward만 §5.9의 다목적 함수로 교체.**

**BacktestEngine** — 5y/1y/1y rolling window, vintage-안전 macro 데이터(OECD CLI 초기 vintage), survivorship-bias 제거(상장폐지 ETF/펀드 포함), 성과지표 패널, 모든 v0~v5의 **동일 비용·동일 universe·동일 burn year** 비교.

**SignalReport** — 실무자용 출력: 현재 placement/velocity 좌표, 4사분면 phase, regime probabilities, 전이확률, 추천 비중·턴오버, 주요 기여 피처(SHAP 또는 정책 그라디언트), drawdown 페널티 활성 여부.

---

## 7. 단계별 개발 로드맵 (v0 → v7)

| 버전 | 핵심 결과물 | 데이터·인프라 | 검증 게이트 |
|---|---|---|---|
| **v0** | Rule-based 4사분면 틸팅. 출력갭·CPI 부호로 IPS SAA에 ±5%p 틸트 | OECD CLI release-date 정렬, FRED CPI | 정적 SAA 대비 Sharpe 동등 + DD 개선 |
| **v1** | placement/velocity 2D phase plane, z-score+slope. 레짐 라벨 안정성(transition rate ≤ N/year) | PIT 매크로 vintage DB | 전이 횟수 합리적, regime 라벨 시계열의 시각적 합리성 |
| **v2** | Regime-conditioned MVO. 레짐별 (μ_k, Σ_k) Ledoit-Wolf 추정 → P(s)·MVO | cvxpy, PyPortfolioOpt | static MVO 대비 Sharpe·Calmar 개선 |
| **v3** | Markov-switching/HMM TAA. Hamilton 또는 multivariate HMM, regime probability를 weight로 직접 사용 | hmmlearn, statsmodels.tsa.regime_switching | Guidolin–Timmermann 식 4-state 통계 검정 통과 |
| **v4** | Receding-horizon MPC. cvxportfolio + Nystrup drawdown-aware γ_t | cvxportfolio | turnover 통제 하 Sharpe 개선, max DD ≤ target |
| **v5** | DRL 정책. Sood et al. 환경+PPO, mixture-of-experts(low/high vol) | StableBaselines3, vectorized envs | MVO·MPC·regime SP 모두 대비 OOS Sharpe·Calmar 우위 |
| **v6** | LDI/funding-ratio reward. §5.9 다목적 R_t. DB 부채 모델 + 할인커브 시뮬 | actuarial cashflow, swap curve | shortfall probability ↓, terminal funding ratio 분포 우수 |
| **v7** | TDF glide-path × regime-aware TAA 통합. base glide path를 strategic anchor로, regime overlay로 ±band 안에서 tactical 조정. 적격 TDF 박스 내 projection | Vanguard VLCM 식 lifecycle util + regime engine | Monte Carlo 은퇴자산 분포의 5%-VaR·median 개선 |

각 단계에서 **반드시 직전 버전을 벤치마크로 유지**해 회귀 가능성을 확보한다.

---

## 8. 실무 구현 함정 (Practical Pitfalls)

1. **데이터 빈도와 매크로 발표 지연.** OECD CLI는 월간이며 발표가 1~2주 지연된다. 일별 RL state에 매크로를 넣을 땐 release-date stamp를 사용한 forward-fill이 필수. 그렇지 않으면 모든 백테스트가 정보누설을 포함한다.
2. **Look-ahead bias.** Z-score·percentile은 반드시 expanding window(JPM 논문 방식). Full-sample 표준화는 누설.
3. **CLI revision.** OECD CLI는 후속 발표에서 개정됨. **earliest-vintage(real-time)** CLI를 써야 한다(Allocate Smartly의 GGC 검증에서 명시적 언급).
4. **Survivorship bias.** ETF·펀드 universe에서 폐지 종목 제외 시 결과 과대평가.
5. **Regime labeling 불안정성.** HMM은 label switching 문제(state 0과 state 1의 의미가 추정마다 바뀜) — Ang–Bekaert RCM(regime classification measure) 모니터링 필수.
6. **Transition matrix estimation.** 짧은 표본에서 P̂이 매우 불안정 → Dirichlet prior 또는 Nystrup et al. (2020) jump-penalty 사용.
7. **State space explosion.** 10개 placement + 10개 velocity + 5개 vol·credit feature → 25차원. RL의 sample efficiency 심각히 저하 → 핵심 PCA·autoencoder로 압축, 또는 Fons et al.(2019)의 Feature Saliency HMM으로 자동선택.
8. **Reward hacking.** DSR 단독은 잦은 turnover로 Sharpe를 부풀리는 정책을 만든다 → §5.9의 turnover penalty 필수.
9. **Overfitting.** 5 seed × 짧은 OOS test(1년) → 해당 1년 우연성 큼. JPM 논문의 10-window 평균을 반드시 따라야 한다.
10. **Transaction cost·slippage.** Sood et al.이 명시적으로 "no transaction costs"로 가정 — 실배포 전 sector ETF별 spread·시장충격 모델 추가.
11. **드로다운 페널티 캘리브레이션.** Quadratic penalty 계수가 너무 크면 stock allocation을 영구적으로 0으로 만든다 — Nystrup et al.(2019)의 γ_t 동적 스케일이 안전.
12. **제약 위반.** Softmax는 sum=1·long-only만 보장 — sector cap, 70% risk asset cap, 적격 TDF box는 별도 projection layer 필요.
13. **설명가능성.** 연기금 IC·OCIO 보고에는 RL black-box 부적합 → SHAP·정책 그라디언트의 feature attribution + regime-state contribution을 항상 함께 출력. v0~v3은 본질적으로 설명가능.
14. **실무자 시그널 리포트 디자인.** 좌표(placement, velocity), 4사분면 위치, regime probability bar, 추천 비중 vs 현재 비중, 턴오버 비용 추정, drawdown trigger flag, "why did weights change today" 텍스트 — 한 페이지에 압축.

---

## 9. Python 클래스 골격 (학습 루프 미포함)

```python
from dataclasses import dataclass
from typing import Protocol, Mapping, Sequence
import numpy as np

# ─────────────────────── 1. Macro Feature ───────────────────────
@dataclass
class MacroSeries:
    name: str
    values: np.ndarray            # raw level, indexed by release_date
    release_dates: np.ndarray     # PIT timestamps (NOT observation dates)

class MacroFeatureEngine:
    """placement/velocity 표준화 파이프라인. expanding window only."""
    def __init__(self, series: Sequence[MacroSeries], asof: np.datetime64): ...
    def level_z(self, name: str, window: int | None = None) -> float: ...
    def percentile(self, name: str, window: int = 252*5) -> float: ...
    def slope(self, name: str, window_months: int = 3) -> float: ...
    def acceleration(self, name: str) -> float: ...
    def vol_ratio(self, asset: str, short: int = 20, long: int = 60) -> float: ...
    def build_state_row(self, names: Sequence[str]) -> np.ndarray: ...
    # 누설 방지: 호출 시점 asof <= release_date인 데이터만 사용

# ─────────────────────── 2. Regime Map ───────────────────────
class RegimeMapEngine:
    PHASES = ("Reflation", "Recovery", "Overheat", "Stagflation")
    def label_phase(self, growth_z: float, infl_velocity: float) -> str: ...
    def vol_regime(self, vol_ratio: float, threshold: float = 1.0) -> str: ...
    def credit_stress(self, oas_z: float, threshold: float = 1.5) -> bool: ...

# ─────────────────────── 3. Regime Transition ───────────────────────
class RegimeBackend(Protocol):
    def fit(self, X: np.ndarray) -> None: ...
    def state_probs(self, X: np.ndarray) -> np.ndarray: ...   # (T, K)
    def transition_matrix(self) -> np.ndarray: ...            # (K, K)

class HMMBackend:           # via hmmlearn
    def __init__(self, n_states: int = 4, covariance_type: str = "full"): ...

class JumpModelBackend:     # Nystrup/Bemporad jump-penalty
    def __init__(self, n_states: int = 4, jump_penalty: float = 25.0): ...

class MarkovSwitchingBackend:   # statsmodels.tsa.regime_switching
    def __init__(self, n_states: int = 4): ...

class RegimeTransitionEngine:
    def __init__(self, backend: RegimeBackend): ...

# ─────────────────────── 4. TAA Optimizer ───────────────────────
@dataclass
class OptimizerConfig:
    risk_aversion: float
    turnover_penalty: float       # Boyd Φ_trade
    holding_cost: float           # Boyd Φ_hold
    drawdown_limit: float | None
    long_only: bool = True
    fully_invested: bool = True
    sector_caps: Mapping[str, float] | None = None
    korea_risk_asset_cap: float | None = None    # 0.70 if DC/IRP
    qualified_tdf_box: bool = False               # if True, ignore 0.70

class TAAOptimizer(Protocol):
    def solve(self, state, regime_probs, prev_w, mu_k, Sigma_k, cfg) -> np.ndarray: ...

class RuleTilter:           ...                  # v0/v1
class RegimeMVO:            ...                  # v2
class HMMStochasticProgram: ...                  # v3 (Bae-Kim-Mulvey)
class MPCSolver:            ...                  # v4 (Boyd 2017 + Nystrup 2019)
    # solve over horizon H, drawdown-aware γ_t
class DRLPolicy:            ...                  # v5

# ─────────────────────── 5. RL Environment ───────────────────────
class TAAEnv:
    """Sood et al. (2023) 환경의 글로벌 멀티에셋 확장.
       observation: (n+1, T) 행렬; 마지막 row에 vol·VIX·placement/velocity·funding ratio.
       action: continuous (n,) -> softmax -> projection onto constraint set.
       reward: §5.9 다목적 함수.
    """
    def __init__(self, prices, macro_engine: MacroFeatureEngine,
                 lookback: int = 60, fee_bps: float = 2.0,
                 reward_weights: Mapping[str, float] | None = None,
                 liability_model=None): ...
    def reset(self): ...
    def _project_to_constraints(self, w_raw: np.ndarray) -> np.ndarray:
        """softmax → sector cap → Korea 70% box → 적격 TDF box."""
    def _reward(self, r_t, w_t, w_prev, F_t, F_prev, dd_t) -> float:
        # λ1 ΔF − λ2 shortfall² − λ3 dd_excess² − λ4 turnover − λ5 CVaR + λ6 DSR
        ...
    def step(self, action): ...

# ─────────────────────── 6. Backtest ───────────────────────
@dataclass
class BacktestSpec:
    train_years: int = 5
    burn_years:  int = 1
    test_years:  int = 1
    shift_years: int = 1
    n_seeds: int = 5

class BacktestEngine:
    def __init__(self, spec: BacktestSpec, env_factory, optimizer_factory,
                 benchmarks: Sequence[str]): ...
    def run_walk_forward(self): ...
    def metrics(self) -> dict: ...      # Sharpe, Sortino, Calmar, MaxDD,
                                        # turnover, costadj_ret, funding_var
    def fairness_check(self): ...        # 동일 lookback·universe·cost 검증

# ─────────────────────── 7. Liability/Glide Path ───────────────────────
class LiabilityModel:
    def funding_ratio(self, assets: float, asof) -> float: ...
    def liability_duration(self) -> float: ...
    def shortfall_prob(self, scenarios) -> float: ...

class GlidePathOverlay:
    """Strategic glide path × regime-aware tactical band."""
    def __init__(self, base_glide, max_tilt: float = 0.10): ...
    def adjust(self, base_w, regime_signal, qualified_tdf_box: bool): ...
```

---

## 10. 한국 TDF/DC 연금 구현 시 법규·실무 제약 (전용 섹션)

### 10.1 법적 박스
- **근로자퇴직급여보장법 시행령 §26**: DC/IRP는 국내·외 개별주식 직접투자 금지. 따라서 부동산투자회사(REITs) 지분 형태도 직접 편입 불가(현행). 본 엔진은 ETF·펀드·집합투자증권 단위로만 액션을 정의해야 한다.
- **위험자산 70% 한도**: 실적배당형(주식 비중 ≥40%) 상품에 적립금의 70% 초과 투자 금지. 액션 projection layer에서 hard constraint.
- **자본시장법**: 일반/사모 집합투자기구의 분류·운용제한 적용. 사모펀드는 적격투자자 한정(법 §249-2).
- **퇴직연금감독규정 시행세칙 제5조의2(적격 집합투자증권 인정기준)**: 위험자산 70% 한도 적용 면제 기준.

### 10.2 적격 TDF 요건 (현행 + 2025년 4월 강화)
충족 시 위험자산 70% 한도 미적용, **DC/IRP 적립금의 100%까지 편입 가능**.
1. 빈티지 펀드명 표시(2030/2040/2050 등) + 글라이드패스가 투자설명서에 명시.
2. 빈티지가 펀드 설정일로부터 5년 이상 남아 있을 것.
3. 운용기간 내 주식 비중 80% 초과 금지.
4. 목표시점(빈티지) 도달 후 주식 40% 이하.
5. 투자부적격등급 채권 비중 총자산의 20% 이내.
6. **(2025.4 시행, 시행세칙 개정)** 특정 해외국가 비중 80% 이내, 적립기 안전자산 20% 이상, 인출기 60% 이상의 분산투자 요건.

> 보도/규제 동향: 금감원·고용노동부는 TDF ETF를 적격 TDF에서 제외하는 방안을 검토 중이며 근로자퇴직급여보장법 시행세칙 개정 추진 중(2025년 9월 보도). 본 엔진의 한국 모듈은 "적격 TDF 박스" 검증을 별도 함수로 두고, 규정 개정 시 파라미터만 갱신하면 되도록 설계한다.

### 10.3 디폴트옵션(사전지정운용제도) 위험등급별 구성 (실무 가이드)
2023.7.12 시행. DC·IRP 적용. 4단계:

| 위험등급 | 일반 구성 | 적립금 비중 (2025 4Q 기준 은행권/보험권 합산 추정) |
|---|---|---|
| 초저위험(안정형) | 100% 원리금보장(예적금·GIC) | ~85% 쏠림 |
| 저위험 | 원리금보장 50–70% + TDF/BF 30–50% | 소수 |
| 중위험 | 예적금 20–40% + TDF/BF 60–80% | 소수 |
| 고위험(적극투자형) | 대부분 실적배당형(TDF/BF/EMP) | 소수 |

본 엔진의 **레짐 조건부 비중**은 디폴트옵션의 위험등급 라인업 안에서 작동해야 한다. v7에서 등급별로 4개 동시 글라이드패스를 산출 가능.

### 10.4 한국 자산 universe
- **주식**: KOSPI200 ETF, KOSDAQ150 ETF, 국내 sector ETF, 미국·DM·EM equity ETF(원화 또는 H/UH), 일본·중국 ETF.
- **채권**: KTB(국고채), KIS 종합채권 ETF, 한국 IG 크레딧 ETF, 글로벌 IG/HY ETF(FX-hedged 권장).
- **대체**: 국내·해외 리츠 펀드(개별주식 형태 REITs 직접편입 불가), 인프라 펀드, 금 ETF, 원자재 ETF(IRP에선 일부 제한).
- **현금**: MMF, 단기채.
- **FX**: 글로벌 자산은 H(헤지)/UH(언헤지) 두 버전 허용. 본 엔진은 placement에 KRW-USD level + 3M slope를 추가 피처로 포함.

### 10.5 한국 placement/velocity 구성 권장
- **Growth**: OECD KOR CLI level + MoM. 한국은행 GDP 발표(분기) 보조.
- **Inflation**: KOR CPI YoY level + 3M annualized − 36M annualized gap.
- **Rate**: 3년 KTB yield level + 3M slope; 10y−3y term spread.
- **Credit**: 한국 IG·HY OAS proxy(KIS 채권 스프레드). 한미 IG OAS spread.
- **Valuation**: KOSPI200 forward P/E z-score(대비 vs 10y).
- **Volatility**: KOSPI200 realized vol(20/60), VKOSPI level+ratio.
- **FX**: USD/KRW level z-score, 3M slope; DXY와 결합.

### 10.6 한국 시장 전용 함정
- 미국식 4분면 라벨이 한국에 그대로 안 맞을 수 있음. 한국은 **수출 사이클 + 글로벌 반도체 사이클**이 GDP·CPI보다 시장 수익을 더 잘 설명하는 시기가 있음 → 보조 placement로 수출 YoY·반도체 BB ratio 권장.
- KRW의 dual nature(EM성 약세 + 안전자산 흐름 강세 혼재) → FX-hedge 결정이 개별 자산 비중만큼 중요. v4 MPC에서 hedge ratio도 액션 차원으로 추가하는 것을 권장.
- Bae·Kim·Mulvey(EJOR 2014)의 KAIST·Princeton 협업 논문이 한국 자산 universe에 가장 가까운 학술 레퍼런스 — 한국형 v3 베이스라인의 출발점.

---

## 11. 추천 추가 검색 키워드

학술/공개 자료 추가 탐색 시:
- "regime-conditional mean-variance optimization" / "regime-switching MVO"
- "expanding window standardization look-ahead bias backtest"
- "mixture of experts portfolio reinforcement learning"
- "constrained policy optimization portfolio softmax projection"
- "differential downside deviation reward reinforcement learning"
- "funding ratio reward reinforcement learning pension"
- "CVaR Expected Shortfall reinforcement learning portfolio"
- "scenario tree multistage stochastic programming pension"
- "Bemporad jump model regime identification"
- "Mahalanobis turbulence Kritzman" / "financial turbulence index"
- "OECD CLI vintage real-time data" / "ALFRED FRED-MD vintage"
- "macro nowcasting MIDAS factor model"
- "robust portfolio uncertainty set Bertsimas"
- "Garleanu Pedersen dynamic trading transaction costs"
- "Moallemi Saglam linear rebalancing rules"
- "Konicz Mulvey personal pension stochastic programming"
- "Detemple Rindisbacher liability driven investment"
- "Martellini Milhau funding ratio target income"
- "퇴직연금 감독규정 시행세칙 적격 TDF 분산투자"
- "디폴트옵션 적립금 추이 위험등급" "고용노동부 금융감독원 분기 공시"
- "KAIST Mulvey regime switching pension" / "Bae Kim 2014 EJOR"

---

## Caveats

1. JPM Sood et al. 논문의 보고된 수치(Sharpe 1.17, max DD −33%)는 **거래비용 0 가정** 하의 결과이며, S&P500 sector indices universe·2012–2021 구간에 한정된 단일 검증이다. 글로벌 멀티에셋·실비용·다른 시장 사이클로 일반화될지는 별도 검증이 필요하다.
2. Investment Clock 4-phase 매핑(Reflation→Bonds, Recovery→Stocks, Overheat→Commodities, Stagflation→Cash)은 **장기 평균적 경향**이며 모든 사이클에서 일관되게 작동하지 않는다(Greetham & Hartnett 자체가 인정). 단순 룰베이스 v0은 baseline으로만 사용하고 v3 이상의 모델이 phase 매핑을 데이터 기반으로 재학습해야 한다.
3. Bridgewater All Weather는 "성장·인플레 4박스에 동일 risk 배분"을 표방하지만 ALLW ETF의 자산비중 합이 100%를 초과(레버리지 사용)하며 일반 DC/IRP 계좌 구조와 직접 비교 불가하다.
4. 한국 적격 TDF 규정은 2025년 4월 강화 시행 이후에도 추가 개정(특히 TDF ETF 제외 여부)이 진행 중이다(2025년 9월 보도). 본 엔진은 적격 박스 검증 모듈을 분리해 규정 변경에 빠르게 대응할 수 있도록 설계해야 한다.
5. `run_blocking_subagent` 및 `enrich_draft` 도구는 본 환경에서 사용 불가능했으므로, 한국 규정 인용은 공개된 보도자료(금융위 73294, 한국경제, 서울경제, 헤럴드, KB증권/하나은행/미래에셋 공시) 및 자본시장연구원·법제처 자료 기반이다. 정식 시행세칙 본문 인용은 별도로 법제처 국가법령정보센터 원문 검증을 권장한다.
6. RL 정책의 fat-tail 신뢰성은 train 구간(2006–2010 포함) GFC 노출 여부에 결정적으로 의존한다. 본 엔진의 v5 배포 전 1997 아시아 위기, 2008 GFC, 2020 COVID, 2022 QT 4개 stress regime 모두에서의 OOS 검증을 필수 게이트로 둔다.
7. Regime의 ex-post 라벨(예: "Crash")이 ex-ante 사용 가능한 P(s_t)와 다르다는 점에서 Guidolin–Timmermann·Kritzman 등의 in-sample 결과는 실제 운용성과를 과대표현할 수 있다. v3~v5 모두 ex-ante regime probability만 사용하도록 코딩 수준에서 강제할 것.