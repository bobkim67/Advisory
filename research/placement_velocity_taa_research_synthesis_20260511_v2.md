# Placement / Velocity 기반 TAA 엔진 리서치 취합본

작성일: 2026-05-08  
주제: 경기국면모델 × Dynamic Programming / MDP / RL / MPC / Stochastic Programming 기반 TAA 엔진 설계  
적용 맥락: 퇴직연금 / OCIO / TDF / LDI / ALM 자산배분 엔진

---

## 0. 문서 목적

오늘 논의한 내용을 기준으로, 다음 자료를 하나의 실무 설계 문서로 취합한다.

1. 기존 대화에서 논의된 **Dynamic Programming, LDI, TAA, OOP 모델링 맥락**
2. 사용자가 제안한 **placement / velocity 기반 경기국면 TAA 아이디어**
3. ICAPS FinPlan 2023 / J.P. Morgan AI Research 논문 검토 내용
4. OpenAI Deep Research용 프롬프트
5. Gemini 리포트 취합
6. Claude / Compass 리포트 취합
7. OpenAI Deep Research 리포트 취합
8. 최종 통합 설계 방향과 Claude에게 전달 가능한 작업지시서
9. SAA → TAA → 상품선정 → 성과귀속을 설명하기 위한 시각화 / 보고서 레이어

핵심 결론은 다음과 같다.

> **바로 end-to-end RL로 자산비중을 만들기보다, “해석 가능한 placement / velocity 경기국면 지도”를 먼저 만들고, 그 위에 regime-conditioned MVO → HMM/Markov transition → MPC → RL overlay 순서로 단계적으로 확장하는 구조가 가장 실무적이다.**

---

## 1. 오늘 대화 흐름 요약

### 1.1 과거 논의 확인

사용자는 과거에 Dynamic Programming, LDI, TAA, OOP 모델링 관련 논의를 했는지 질문했다.

정리된 과거 맥락은 다음과 같다.

| 주제 | 과거 논의 내용 | 현재 연결점 |
|---|---|---|
| DB ALM / LDI | 부채 현금흐름, Funding Ratio, Surplus, 듀레이션, 할인율 기반 ALM 시뮬레이션 | LDI-aware reward / liability state 설계 |
| Dynamic Programming / RL | 금리 레벨·변동성·부채 상태를 포함한 DP/RL 기반 최적 자산배분 엔진 아이디어 | v5 이후 DP/RL 정책 학습 후보 |
| TAA | 경기국면별 TAA tilt, regime-based allocation, rule-based prototype | 현재 placement / velocity regime map으로 고도화 |
| OOP 모델링 | TDF 2060 엔진에서 domain / repositories / optimization / regime / taa / portfolio 등 모듈 분리 | 이번 TAA 엔진도 동일한 OOP 구조 적용 가능 |

기존 TDF 2060 엔진의 현재 상태는 **SAA는 MVO 기반, TAA는 rule-based prototype overlay**에 가깝다. 따라서 이번 논의의 핵심은 현재의 rule-based TAA를 **설명 가능한 경기국면 모델 + 다기간 최적화 엔진**으로 확장하는 것이다.

---

## 2. 사용자의 핵심 아이디어

사용자의 아이디어는 다음과 같이 요약된다.

> 경기국면을 단순히 expansion / slowdown / recession / recovery로 나누지 말고, 각 거시지표가 현재 어디에 있는지와 어느 방향·속도로 움직이는지를 함께 본다. 즉, **placement + velocity** 좌표를 만들고, 각 좌표별로 자산군별 적정 포지션을 정한다. 그 위에 DP, MDP, RL, MPC 등을 결합할 수 있다.

### 2.1 Placement 정의

`placement`는 거시 또는 시장 변수의 현재 위치다.

예시:

- 성장률 레벨
- Output gap
- OECD CLI level
- Inflation gap
- 금리 레벨
- Credit spread level
- Valuation level
- Volatility level
- Funding ratio level

### 2.2 Velocity 정의

`velocity`는 해당 변수의 변화속도 또는 방향성이다.

예시:

- 전월 대비 변화율
- 3개월 slope
- acceleration
- momentum
- short-term vs long-term volatility ratio
- vol20 / vol60
- earnings revision momentum
- credit spread widening / tightening speed

### 2.3 상태공간 구조

```text
state_t = {
    growth_placement,
    growth_velocity,
    inflation_placement,
    inflation_velocity,
    rate_placement,
    rate_velocity,
    credit_spread_placement,
    credit_spread_velocity,
    volatility_placement,
    volatility_velocity,
    valuation_placement,
    earnings_velocity,
    current_weight,
    funding_ratio,
    surplus,
    duration_gap,
    time_to_retirement
}
```

### 2.4 Action 구조

TDF / OCIO / LDI에 바로 적용하려면, action은 전체 포트폴리오 비중을 자유롭게 만드는 방식보다 **기준 포트폴리오 대비 active tilt**가 더 적절하다.

```text
action_t = benchmark_relative_active_tilt

예시:
- 한국주식 +2%
- 미국성장주 -3%
- 미국가치주 +1%
- 국내채권 +2%
- 미국장기채 -1%
- 금 +1%
```

---

## 3. 관련 문헌과 기존 프레임워크 연결

Placement / velocity 아이디어는 완전히 새로운 개념이라기보다 기존 경기국면·레짐 기반 자산배분 연구의 **state representation**을 더 명시적으로 정리한 것이다.

| 사용자 개념 | 문헌 / 실무 프레임워크 대응 | 해석 |
|---|---|---|
| Growth placement + velocity | OECD CLI, Investment Clock, All Weather | 경기 위치와 변화 방향 |
| Inflation placement + velocity | Inflation regime, inflation trend signal | 인플레이션 레벨과 가속/둔화 |
| Volatility placement + velocity | vol20, vol60, vol20/vol60, VIX | 위험국면 전환 신호 |
| Credit spread level + change | Credit stress regime | 경기침체·유동성 스트레스 감지 |
| Valuation level + earnings momentum | Factor / equity style allocation | 주식 스타일 TAA 근거 |
| Regime probability | HMM, Markov switching, jump model | 국면의 확률적 전이 |
| State → weight mapping | Regime-conditioned MVO, MPC, RL | 국면별 최적 포지션 산출 |

---

## 4. ICAPS FinPlan 2023 / J.P. Morgan AI Research 논문 검토

검토한 논문:

> **Deep Reinforcement Learning for Optimal Portfolio Allocation: A Comparative Study with Mean-Variance Optimization**  
> Srijan Sood, Kassiani Papasotiriou, Marius Vaiciulis, Tucker Balch  
> J.P. Morgan AI Research / ICAPS FinPlan 2023

### 4.1 이 논문이 유용한 이유

이 논문은 placement / velocity 기반 TAA 아이디어와 완전히 같은 논문은 아니지만, **RL 기반 포트폴리오 엔진을 실제 환경으로 구현하는 방법**을 보여주는 좋은 청사진이다.

특히 다음 요소가 중요하다.

| 요소 | 원 논문 구조 | 프로젝트 적용 방향 |
|---|---|---|
| Environment | Market data replay | TAA / TDF / OCIO backtest environment로 차용 |
| State | 현재 weight + 60일 log return + vol20 + vol20/vol60 + VIX | 여기에 macro placement / velocity, funding ratio, duration gap 추가 |
| Action | Portfolio weight | 전체 weight가 아니라 benchmark-relative active tilt 권장 |
| Constraint | Softmax로 long-only / fully-invested | projection layer 또는 constrained action band와 결합 |
| Reward | Differential Sharpe Ratio | 단독 사용은 부적합. DSR은 보조항으로 사용 |
| Validation | train / burn / test rolling window | walk-forward backtest 표준으로 차용 |
| Leakage 방지 | Expanding lookback standardization | macro release lag와 함께 필수 적용 |

### 4.2 그대로 차용할 부분

```text
1. market data replay 기반 RL environment
2. action을 portfolio weight 또는 active tilt로 정의하는 방식
3. long-only / fully-invested 제약을 softmax 또는 projection으로 처리하는 방식
4. state에 현재 weight, lookback return matrix, volatility regime signal을 포함하는 방식
5. vol20, vol60, vol20/vol60, VIX를 volatility placement / velocity로 활용하는 방식
6. rolling train / burn / test split
7. expanding-window standardization으로 leakage를 방지하는 방식
```

### 4.3 수정해야 할 부분

```text
1. Differential Sharpe Ratio를 주목적함수로 쓰지 않는다.
2. 거래비용, 슬리피지, turnover penalty를 reward 또는 environment에 넣는다.
3. drawdown penalty를 명시한다.
4. TDF / LDI 목적에 맞게 funding ratio, surplus, duration gap, time-to-retirement를 state에 넣는다.
5. action space를 전체 weight simplex가 아니라 기준 포트폴리오 대비 active band로 제한한다.
6. 일간 RL보다 월간 macro TAA를 기본으로 한다.
```

### 4.4 TDF / OCIO / LDI용 reward 설계

```text
reward_t =
    λ1 * portfolio_return
  + λ2 * surplus_return
  + λ3 * funding_ratio_improvement
  - λ4 * shortfall_penalty
  - λ5 * drawdown_penalty
  - λ6 * turnover_penalty
  - λ7 * transaction_cost
  - λ8 * glide_path_deviation_penalty
  - λ9 * constraint_violation_penalty
  + λ10 * differential_sharpe_auxiliary_term
```

핵심은 **수익률 최대화가 아니라 정책 목적 최적화**다.

- TDF: 은퇴시점 성공확률, downside risk, glide path 안정성
- DB / LDI: funding ratio, surplus, duration gap, contribution stability, downside shortfall
- OCIO: IPS 준수, active risk, turnover, drawdown, 성과 안정성

---

## 5. 모델별 리서치 결과물 취합

### 5.1 Gemini 리포트 요약

Gemini 리포트는 전반적으로 **DRL / Meta-RL / 하이브리드 제어 확장**에 강점이 있었다.

#### 핵심 주장

- Placement / velocity는 거시 지표를 다차원 state-space로 표현하는 방식이다.
- MDP를 구축하고 DRL / MPC 기반 최적 TAA를 설계할 수 있다.
- 포트폴리오 weight를 action으로 두고 softmax projection으로 제약을 처리할 수 있다.
- Funding ratio, drawdown, transaction cost, liability duration 등을 reward에 통합해야 한다.
- Meta-RL, goal-based investing, regime-aware RL, MPC-guided RL 등이 후속 연구 후보가 될 수 있다.

#### Gemini의 강점

| 항목 | 내용 |
|---|---|
| RL 확장성 | PPO, Meta-RL, regime-aware RL, goal-based wealth management까지 확장 |
| 구현 감각 | MacroFeatureEngine, RegimeTransitionEngine 등 코드 골격 제시 |
| 하이브리드 제어 | MPC의 제약처리와 RL의 비선형 적응력 결합 제안 |
| 기관투자자 목적함수 | funding ratio, drawdown, transaction cost, liability duration 반영 제안 |

#### 주의점

- 일부 최신 논문 / working paper는 검증 필요.
- RL을 너무 빠르게 메인 엔진으로 올리면 explainability와 reward hacking 문제가 커질 수 있음.
- 실무 적용 순서는 Gemini 제안보다 더 보수적으로 가야 함.

#### Gemini에서 흡수할 아이디어

```text
1. Regime-aware RL 후보를 secondary research queue로 편입
2. Meta-RL / goal-based investing은 장기 TDF 연구 후보로 보관
3. MPC-guided RL은 v5 이후 고급형 구조로 검토
4. Python OOP skeleton 일부는 Claude 작업지시서에 반영 가능
```

---

### 5.2 Claude / Compass 리포트 요약

Claude / Compass 리포트는 가장 **문헌 정리와 실무형 설계 균형**이 좋았다.

#### 핵심 주장

- Placement / velocity는 새 발명이 아니라 기존 레짐 기반 자산배분의 state representation이다.
- 핵심 파이프라인은 다음과 같다.

```text
Regime Identification
    → Regime-conditioned Optimization
    → Multi-period Control
```

- v0 rule-based tilt에서 시작해 v1 regime map, v2 regime-conditioned MVO, v3 HMM, v4 MPC, v5 DP/RL 순서로 가야 한다.
- JPM / ICAPS 논문은 RL environment의 직접 청사진이지만, DSR은 funding ratio / shortfall / drawdown / turnover reward로 교체해야 한다.
- 한국 퇴직연금 적용 시 DC/IRP 위험자산 한도, 적격 TDF 요건, 주식비중 제한, HY 제한 등을 constraint layer에 넣어야 한다.

#### Claude / Compass의 강점

| 항목 | 내용 |
|---|---|
| 문헌 우선순위 | Sood, Nystrup, Boyd, Guidolin, Bae, Brennan 등 core literature 정리 |
| 단계적 로드맵 | v0~v7 구조가 현실적 |
| 한국 제약 반영 | 적격 TDF, 위험자산 한도, HY 제한 등 고려 |
| MPC 강조 | HMM + MPC + drawdown control을 실무 핵심 중간 단계로 제시 |

#### Claude / Compass에서 흡수할 아이디어

```text
1. Placement/velocity는 표현(representation)으로 정의
2. Rule → HMM → MPC → DRL 순서로 모듈 교체 가능하게 설계
3. Nystrup/Boyd 계열 MPC를 v4 핵심 엔진으로 채택
4. 한국형 constraint layer를 별도 모듈로 분리
5. Committee report / governance layer를 처음부터 포함
```

---

### 5.3 OpenAI Deep Research 리포트 요약

OpenAI Deep Research 리포트는 **보수적 실무 결론과 LDI / ALM 목적함수 정리**가 강했다.

#### 핵심 주장

- Placement + velocity 기반 경기국면 map은 문헌적으로 충분히 정당화된다.
- 관련 연구는 세 갈래로 나뉜다.

```text
1. 국면 식별 연구
   - OECD CLI
   - Investment Clock
   - Macro regime detection

2. 국면 전이와 자산배분 연결 연구
   - Guidolin & Timmermann
   - Bae, Kim & Mulvey
   - HMM / regime-switching / clustering

3. 다기간 제어와 부채 연동 목적함수 연구
   - SOA LDI
   - stochastic optimization
   - dynamic programming
   - funding ratio / surplus / contribution risk
```

- 가장 유망한 구조는 **해석 가능한 placement / velocity 국면맵 + 확률적 전이 / 제어 엔진**의 2층 구조다.
- RL은 처음부터 메인 엔진으로 두지 말고, **liability-aware benchmark policy를 교정하는 overlay**로 써야 한다.
- 월간 macro regime map → liability-aware MPC → RL overlay 순서가 가장 타당하다.

#### Deep Research의 강점

| 항목 | 내용 |
|---|---|
| 보수적 실무 판단 | RL은 보조 엔진으로 사용해야 한다는 결론 |
| LDI 목적함수 | funding ratio, surplus, contribution, liability constraints 강조 |
| ICAPS 논문 해석 | vol20/vol60을 volatility velocity로 해석 |
| Backtest 설계 | 월간 리밸런싱, release lag, walk-forward validation 강조 |

#### Deep Research에서 흡수할 아이디어

```text
1. Core TAA는 월간 리밸런싱으로 설계
2. GDP/CPI/CLI 등은 publication lag를 반영한 point-in-time 처리 필수
3. RL action은 full weight가 아니라 benchmark-relative active tilt로 제한
4. Differential Sharpe는 tactical sleeve의 보조항으로만 사용
5. Signal report에 현재 좌표, regime, transition probability, active tilt 근거를 함께 출력
```

---

### 5.4 ChatGPT 대화 기반 통합 판단

오늘 대화에서 정리된 최종 판단은 다음과 같다.

> **이 프로젝트는 “AI가 알아서 자산배분을 하는 블랙박스 엔진”이 아니라, 경기국면의 위치와 속도를 시각화하고, 국면 전이확률을 반영해 MVO / MPC / RL이 단계적으로 포트폴리오를 조정하는 설명 가능한 TAA 엔진으로 포지셔닝해야 한다.**

---

## 6. 모델별 차이와 통합 판단

| 구분 | Gemini | Claude / Compass | OpenAI Deep Research | 통합 판단 |
|---|---|---|---|---|
| 핵심 톤 | 공격적, DRL/Meta-RL 확장 | 균형형, 문헌+실무 설계 | 보수적, LDI/ALM 실무 중심 | Deep Research / Claude를 베이스로 Gemini 확장 아이디어 흡수 |
| RL 위치 | 핵심 엔진 후보 | v5 이후 단계 | overlay / corrective module | RL은 초기 메인 엔진 금지, v5 이후 제한적 사용 |
| MPC 위치 | RL과 결합 가능한 제어엔진 | v4 핵심 | liability-aware 중간 엔진 | v4 핵심 엔진으로 채택 |
| Regime Map | State-space 표현 | representation layer | 해석 가능한 상단 레이어 | v1에서 우선 구현 |
| Reward | funding ratio 등 포함 | DSR 대체 강조 | 정책 목적함수 강조 | DSR은 보조항, LDI/TDF reward 별도 설계 |
| Backtest | DRL 중심 | 단계별 검증 | 월간 / release lag / walk-forward | 월간 PIT backtest 기본 |
| 한국 퇴직연금 제약 | 상대적으로 약함 | 강함 | 일부 반영 | constraint layer에 명시 |

---

## 7. 최종 권장 아키텍처

### 7.1 전체 흐름

```text
[Raw Data]
  ├─ Market Data
  ├─ Macro Data
  ├─ Valuation Data
  ├─ Credit / Volatility Data
  └─ Liability / Glide Path Data
        │
        ▼
[MacroFeatureEngine]
  ├─ placement 계산
  ├─ velocity 계산
  ├─ z-score / percentile / slope / acceleration
  └─ publication lag / point-in-time 정렬
        │
        ▼
[RegimeMapEngine]
  ├─ OECD CLI 4국면
  ├─ Growth / Inflation 4국면
  ├─ Investment Clock
  ├─ Volatility regime
  └─ Credit stress regime
        │
        ▼
[RegimeTransitionEngine]
  ├─ transition matrix
  ├─ Markov switching
  ├─ HMM probability
  └─ jump model 후보
        │
        ▼
[TAAOptimizer]
  ├─ v0 RuleBasedTilter
  ├─ v2 RegimeConditionedMVO
  ├─ v3 StochasticProgramOptimizer
  ├─ v4 MPCOptimizer
  └─ v5 RLOverlayAgent
        │
        ▼
[ConstraintLayer]
  ├─ long-only
  ├─ fully-invested
  ├─ active band
  ├─ turnover limit
  ├─ TDF glide path
  ├─ Korea retirement constraints
  └─ policy limit
        │
        ▼
[BacktestEngine]
  ├─ walk-forward validation
  ├─ train / validation / burn / test
  ├─ transaction cost
  ├─ benchmark comparison
  └─ attribution
        │
        ▼
[SignalReport / CommitteePack]
```

### 7.2 Python 패키지 구조 초안

```text
tdf_taa_engine/
│
├─ data/
│   ├─ market_loader.py
│   ├─ macro_loader.py
│   ├─ liability_loader.py
│   └─ release_calendar.py
│
├─ features/
│   ├─ macro_features.py
│   ├─ market_features.py
│   ├─ liability_features.py
│   └─ standardization.py
│
├─ regime/
│   ├─ regime_map.py
│   ├─ regime_transition.py
│   ├─ hmm_model.py
│   └─ phase_plane.py
│
├─ optimizer/
│   ├─ rule_tilter.py
│   ├─ regime_mvo.py
│   ├─ stochastic_program.py
│   ├─ mpc_optimizer.py
│   └─ policy_band_allocator.py
│
├─ rl/
│   ├─ env.py
│   ├─ reward.py
│   ├─ agent.py
│   └─ policy_overlay.py
│
├─ constraints/
│   ├─ base.py
│   ├─ retirement_constraints.py
│   ├─ tdf_constraints.py
│   ├─ active_band.py
│   └─ turnover.py
│
├─ backtest/
│   ├─ engine.py
│   ├─ rolling_window.py
│   ├─ benchmark.py
│   ├─ cost_model.py
│   └─ attribution.py
│
├─ reporting/
│   ├─ signal_report.py
│   ├─ committee_pack.py
│   ├─ regime_chart.py
│   └─ attribution_report.py
│
└─ tests/
    ├─ test_features.py
    ├─ test_regime_map.py
    ├─ test_constraints.py
    ├─ test_backtest_no_leakage.py
    └─ test_optimizer_smoke.py
```

---

## 8. Core Literature 통합 리스트

아래 문헌군을 우선순위로 관리한다.

| 순위 | 문헌 | 역할 |
|---:|---|---|
| 1 | Sood, Papasotiriou, Vaiciulis, Balch (2023), J.P. Morgan AI Research / ICAPS | RL environment / action / reward / rolling validation 청사진 |
| 2 | Nystrup, Boyd, Lindström, Madsen (2019), Multi-period portfolio selection with drawdown control | HMM + MPC + drawdown control |
| 3 | Boyd et al. (2017), Multi-Period Trading via Convex Optimization | 거래비용·제약 포함 다기간 convex optimization |
| 4 | Guidolin & Timmermann (2007), Asset allocation under multivariate regime switching | regime-switching asset allocation 이론 기반 |
| 5 | Ang & Bekaert (2002), International Asset Allocation With Regime Shifts | 국제 자산배분과 regime shift |
| 6 | Kritzman, Page, Turkington (2012), Regime Shifts | turbulence / growth / inflation regime |
| 7 | Bae, Kim, Mulvey (2014), Dynamic asset allocation under regime switching | HMM + stochastic programming, pension example |
| 8 | Brennan, Schwartz, Lagnado (1997), Strategic Asset Allocation | DP 기반 다기간 SAA 표준 |
| 9 | Brandt, Goyal, Santa-Clara, Stroud (2005), Simulation Approach to Dynamic Portfolio Choice | simulation-based DP / BGSS |
| 10 | Greetham & Hartnett (2004), The Investment Clock | growth / inflation phase-plane baseline |
| 11 | SOA, Deep Learning for Liability-Driven Investment | LDI RL state/action/reward 참고 |
| 12 | Jang, Clare, Owadally (2024), LDI stochastic optimization with real assets | funding ratio / contribution / buyout cost 목적함수 |
| 13 | Vanguard, Revisiting pension asset allocation | funding-status driven glide path |
| 14 | MSCI, Adaptive multi-factor allocation / macro regime | macro cycle + momentum + valuation + sentiment |
| 15 | OECD CLI documentation | placement / velocity 4국면 해석 근거 |

---

## 9. 개발 로드맵

### Phase 0. Literature-to-Spec 정리

목표:

- Gemini / Claude / Deep Research 문헌 리스트를 통합
- core literature와 secondary research queue 분리
- TDF 2060 엔진에 바로 필요한 subset 확정

산출물:

```text
docs/research/placement_velocity_taa_literature_map.md
docs/research/core_literature_register.md
docs/research/secondary_research_queue.md
```

---

### Phase 1. MacroFeatureEngine

목표:

- placement / velocity feature 생성
- expanding z-score
- percentile
- 3M slope
- acceleration
- publication lag 처리

필수 구현:

```text
calculate_placement(series, method='zscore|percentile|gap')
calculate_velocity(series, method='mom|slope|acceleration')
apply_publication_lag(data, release_calendar)
standardize_expanding(data)
```

주의:

- look-ahead bias 방지
- macro revision 문제 명시
- point-in-time 데이터가 없으면 최소한 발표 지연 shift 적용

---

### Phase 2. RegimeMapEngine

목표:

- 사람이 이해할 수 있는 phase-plane 생성
- OECD CLI식 4국면
- Growth / Inflation 4국면
- Volatility regime
- Credit stress regime

출력 예시:

```text
current_regime = {
    'growth_phase': 'recovery',
    'inflation_phase': 'disinflation',
    'volatility_regime': 'rising_vol',
    'credit_regime': 'normal',
    'regime_score': 0.67
}
```

---

### Phase 3. RegimeTransitionEngine

목표:

- transition matrix
- HMM probability
- Markov switching 후보
- regime persistence / turnover 점검

출력 예시:

```text
P(next_regime | current_features) = {
    'expansion': 0.35,
    'slowdown': 0.40,
    'recession': 0.15,
    'recovery': 0.10
}
```

---

### Phase 4. Regime-conditioned MVO

목표:

- regime별 expected return / covariance 추정
- regime probability로 혼합
- 기존 SAA 대비 active tilt 산출

설계:

```text
mu_t = Σ_k P(regime=k) * mu_k
cov_t = Σ_k P(regime=k) * cov_k
w_target = argmax utility(w | mu_t, cov_t, constraints)
active_tilt = w_target - w_policy
```

---

### Phase 5. MPCOptimizer

목표:

- 다기간 path 최적화
- turnover penalty
- transaction cost
- active band
- drawdown-aware risk aversion

목적함수 예시:

```text
maximize Σ_t [
    expected_return_t
  - risk_aversion_t * variance_t
  - transaction_cost_t
  - turnover_penalty_t
  - drawdown_penalty_t
  - policy_deviation_penalty_t
]
```

---

### Phase 6. RLEnvironment Prototype

목표:

- market replay environment
- action = benchmark-relative active tilt
- reward = return + auxiliary DSR - turnover - drawdown
- softmax 또는 projection 기반 제약 처리

주의:

- RL은 전체 weight 생성기가 아니라 overlay agent
- 초기에는 실험용으로만 사용
- committee reporting 가능성을 해치면 안 됨

---

### Phase 7. LDI / TDF Reward 확장

목표:

- funding ratio
- surplus
- duration gap
- glide path deviation
- time-to-retirement
- shortfall penalty

TDF reward:

```text
reward_tdf =
    λ1 * portfolio_return
  - λ2 * downside_risk
  - λ3 * glide_path_deviation
  - λ4 * turnover
  - λ5 * shortfall_probability
```

LDI reward:

```text
reward_ldi =
    λ1 * surplus_return
  + λ2 * funding_ratio_improvement
  - λ3 * funding_ratio_volatility
  - λ4 * duration_gap_penalty
  - λ5 * contribution_volatility
  - λ6 * turnover
```

---

### Phase 8. Backtest / Governance

목표:

- train / validation / burn / test
- walk-forward backtest
- benchmark comparison
- signal report
- committee pack

벤치마크:

```text
1. Static SAA
2. Strategic glide path
3. Risk parity
4. Vanilla MVO
5. Regime-conditioned MVO
6. MPC
7. RL overlay
8. LDI hedge policy
```

보고 항목:

```text
1. 현재 placement / velocity 좌표
2. 현재 regime label
3. 다음 국면 전이확률
4. 기준 포트폴리오 대비 active tilt
5. tilt 근거 feature
6. 제약조건 통과 여부
7. turnover / cost impact
8. drawdown / funding ratio 영향
9. benchmark 대비 성과
10. attribution
```

---

## 10. 실무 구현 원칙

### 원칙 1. 월간 리밸런싱을 기본으로 한다

거시 데이터는 월간/분기 단위가 많고, 발표 지연이 존재한다. 따라서 core TAA는 월간 리밸런싱이 적절하다. 일간 RL은 tactical sleeve 또는 연구용으로 제한한다.

### 원칙 2. Point-in-Time 처리가 없으면 신뢰도가 떨어진다

GDP, CPI, PMI, OECD CLI는 발표 지연과 수정치 문제가 있다. 확정치를 그대로 백테스트하면 look-ahead bias가 발생한다. 최소한 release lag shift를 적용해야 한다.

### 원칙 3. RL은 보조 엔진이다

실무 구조는 다음과 같아야 한다.

```text
Policy benchmark
  + Regime-conditioned MVO / MPC target
  + RL corrective overlay
  - Constraint projection
```

### 원칙 4. Constraint layer를 독립 모듈로 둔다

특히 한국 퇴직연금 / TDF 적용 시 다음 제약을 별도 관리한다.

- long-only
- fully-invested
- 위험자산 한도
- 적격 TDF 요건
- 주식비중 상한
- HY / 투자부적격 채권 한도
- 해외 특정국가 비중 제한
- active band
- turnover limit
- liquidity constraint

### 원칙 5. 위원회 보고 가능성이 설계 기준이다

최종 weight보다 더 중요한 것은 **왜 그 weight가 나왔는지 설명하는 것**이다.

---

## 11. 최종 설계 포지셔닝

이 프로젝트의 적절한 포지셔닝은 다음과 같다.

> 블랙박스 AI 자산배분 엔진이 아니라, 경기국면의 위치와 속도를 시각화하고, 국면 전이확률을 반영해 MVO / MPC / RL이 단계적으로 포트폴리오를 조정하는 **설명 가능한 TAA 엔진**.

이렇게 포지셔닝하면 다음 장점이 있다.

1. 투자위원회 / 운용역 / 고객에게 설명 가능
2. 기존 SAA / 글라이드패스 체계와 충돌이 작음
3. RL 도입 시에도 governance 부담이 낮음
4. 리스크 관리와 제약조건 반영이 쉬움
5. TDF / OCIO / LDI 각각으로 확장 가능

---


## 12. 시각화 / 보고서 설계 레이어 보강

추가로 검토한 자료는 기존 리서치 취합본의 **모델링 엔진** 자체보다는, 엔진 산출물을 운용역·투자위원회·고객에게 설명하는 **시각화 / 보고서 / 아키텍처 흐름도 레이어**에 연결하는 것이 가장 적절하다.

핵심 판단은 다음과 같다.

> 현재 산출물이 단순 계산 결과나 diagnostic sheet처럼 보이면 안 된다. 최종 보고서는 **Regime → SAA → TAA → Implementation / Selection → Attribution / Monitoring**의 운용 의사결정 스토리를 보여줘야 한다.

### 12.1 기존 엔진 아키텍처와의 연결 위치

기존 아키텍처는 다음 흐름이었다.

```text
Raw Data
  → MacroFeatureEngine
  → RegimeMapEngine
  → RegimeTransitionEngine
  → TAAOptimizer / MPC / RL Overlay
  → ConstraintLayer
  → BacktestEngine
  → SignalReport
```

이번에 추가한 자료는 마지막 두 단계, 즉 **SignalReport / CommitteePackBuilder / Visualization Layer**를 강화한다.

```text
Model Engine
  ├─ Placement / Velocity Regime State
  ├─ SAA Optimizer Output
  ├─ TAA Overlay Output
  ├─ Product / Fund Selection Output
  └─ Performance Attribution Output
        ↓
Visualization & Committee Pack Layer
  ├─ Regime Page
  ├─ SAA Page
  ├─ TAA Page
  ├─ Implementation / Selection Page
  └─ Attribution / Monitoring Page
```

따라서 코드 아키텍처에는 아래 모듈을 추가하는 것이 좋다.

```text
tdf_taa_engine/
└─ reporting/
   ├─ RegimePageBuilder
   ├─ SAAPageBuilder
   ├─ TAAPageBuilder
   ├─ SelectionPageBuilder
   ├─ AttributionPageBuilder
   ├─ CommitteePackBuilder
   └─ VisualizationSpecBuilder
```

### 12.2 참고자료별 역할

| 참고자료 | 연결되는 레이어 | 활용 방식 |
|---|---|---|
| CFA Institute / PIMCO - Factor Investing and Asset Allocation: A Business Cycle Perspective | Regime / TAA 이론축 | Business cycle에 따라 risk premia, expected return, volatility가 달라지는 논리 설명 |
| Vanguard - Time-varying asset allocation: Vanguard's approach to dynamic portfolios | SAA / TVAA 프로세스축 | 자산우주, 제약조건, return forecast, policy portfolio, risk aversion, optimization 흐름 참고 |
| BlackRock Portfolio Perspectives / CMA framework | SAA 시각화 | CMA, uncertainty, multiple return pathways, robust optimization을 통해 왜 SAA가 나왔는지 설명 |
| Research Affiliates - Patience Helps in Low-Return World | 장기 forecast / EF 시각화 | GTAA를 단순 market timing이 아니라 장기 기대수익 기반 frontier 이동으로 설명 |
| Fidelity Business Cycle Framework | Regime page 벤치마크 | Cycle phase, current assessment, asset allocation outlook을 함께 보여주는 구조 참고 |
| BlackRock MASS brochure | SAA → TAA → Manager Research / Security Selection 연결 | 상품선정 단계에서 due diligence, 전략 적합성, ongoing monitoring을 설명 |
| NBIM Annual Report | Attribution / Monitoring | Market exposure, security selection, fund allocation 등 decision bucket별 성과기여 설명 |

### 12.3 보고서 페이지 구조 제안

#### Page 1. Regime Page

목적: 현재 경기국면을 **좌표와 경로**로 설명한다.

필수 구성:

```text
1. Placement / Velocity Clock
2. 최근 12~24개월 이동 궤적
3. 현재 포인트
4. phase 정의
5. 현재 regime label
6. 다음 국면 전이확률
7. 자산군 선호도 heatmap
```

보고서 메시지:

> 현재 국면이 어디에 있고, 어느 방향으로 이동 중이며, 그 결과 어떤 자산군을 선호하거나 축소해야 하는지 보여준다.

#### Page 2. SAA Page

목적: SAA가 단순 비중표가 아니라 **입력 가정과 제약조건의 결과**임을 설명한다.

필수 구성:

```text
1. CMA 입력 요약
2. 자산군별 expected return / volatility
3. correlation 또는 risk contribution 요약
4. 제약조건 박스
5. efficient frontier
6. 채택된 SAA 포인트
7. SAA risk contribution
```

보고서 메시지:

> SAA는 임의의 기준비중이 아니라, 장기 기대수익·위험·상관·제약조건을 반영해 선택된 정책 포트폴리오다.

#### Page 3. TAA Page

목적: TAA tilt가 단순 ±%p 조정이 아니라 **현재 regime에서의 기대수익 / 위험 변화**에 근거한다는 점을 설명한다.

필수 구성:

```text
1. 현재 regime 기준 자산군별 expected return 변화
2. 자산군별 volatility 변화
3. Sharpe 또는 utility 변화
4. regime-conditioned frontier 변화
5. SAA 대비 TAA 이동 화살표
6. recommended active tilt
7. turnover / cost impact
```

보고서 메시지:

> 현재 경기국면에서 자산군별 보상 대비 위험이 어떻게 달라졌고, 그 결과 SAA에서 TAA로 어떤 방향의 active tilt가 발생했는지 보여준다.

#### Page 4. Implementation / Selection Page

목적: 최종 편입 상품이 **왜 선택됐는지** 설명한다.

필수 구성:

```text
1. 자산군별 후보 universe
2. 스코어링 항목
   - 전략 적합성
   - 성과
   - 위험
   - 수수료
   - 추적오차
   - 유동성
   - 운용철학 / 프로세스
   - 분산효과
3. 최종 선택 상품
4. 대체 후보 대비 선정 이유
5. ongoing due diligence 항목
```

보고서 메시지:

> 엔진이 특정 상품을 선택했다는 결과보다, 어떤 기준으로 후보를 걸러내고 최종 상품을 선정했는지가 중요하다.

#### Page 5. Attribution / Monitoring Page

목적: 성과를 decision bucket별로 사후 설명한다.

필수 구성:

```text
1. 전체 성과 vs BM
2. SAA / policy allocation 효과
3. TAA active tilt 효과
4. selection 효과
5. FX / hedge 효과
6. cost / turnover 효과
7. regime call 적중 여부
8. 다음 리밸런싱 검토 사항
```

보고서 메시지:

> 성과가 어디서 발생했는지를 asset allocation, tactical tilt, selection, cost, hedge 등 의사결정 단위별로 귀속한다.

### 12.4 기존 지적사항과의 연결

| 기존 문제제기 | 보강 방향 |
|---|---|
| Regime mini-timeline이 약함 | Placement-velocity clock + 최근 12~24개월 경로 + phase 정의 + 자산군 선호도 heatmap 추가 |
| SAA가 왜 그렇게 나왔는지 설명 부족 | CMA / volatility / correlation / constraints / efficient frontier / risk contribution 추가 |
| TAA tilt의 근거 부족 | regime별 expected return / volatility / utility 변화와 SAA→TAA 이동 시각화 추가 |
| Projection clipping 장표가 불필요 | 본문에서 제거하고 appendix / diagnostic / QA 섹션으로 이동 |
| 상품선정 이유 부족 | universe → scoring → selected product → alternative comparison → due diligence 흐름 추가 |
| 성과귀속 구조 부족 | allocation / tactical tilt / selection / hedge / cost bucket으로 attribution 재설계 |

### 12.5 최종 보고서 목차 예시

TDF 2060 또는 OCIO TAA 엔진 보고서는 6~8장 정도가 적절하다.

```text
1. Executive Summary
   - 현재 regime
   - SAA 대비 주요 active tilt
   - 예상 리스크 변화
   - 주요 의사결정 포인트

2. Regime Dashboard
   - placement-velocity clock
   - 12~24개월 궤적
   - phase 정의
   - transition probability
   - asset implication heatmap

3. SAA Construction
   - CMA / vol / corr
   - constraints
   - efficient frontier
   - selected SAA
   - risk contribution

4. TAA Overlay
   - regime-conditioned expected return / risk
   - SAA → TAA 이동
   - recommended tilt
   - turnover / cost

5. Portfolio Implementation
   - target asset-class weights
   - product universe
   - scoring
   - selected product / fund
   - 대체 후보 대비 선정 이유

6. Risk & Constraint Check
   - long-only / fully-invested
   - TDF glide path band
   - risk asset limit
   - turnover
   - drawdown / VaR / CVaR
   - funding ratio sensitivity, if LDI mode

7. Attribution & Monitoring
   - SAA effect
   - TAA effect
   - selection effect
   - hedge / FX effect
   - cost effect
   - regime call review

8. Appendix / Diagnostics
   - projection clipping
   - solver diagnostics
   - constraint binding details
   - data quality checks
```

### 12.6 Claude 작업지시서에 추가할 문구

기존 Claude 작업지시서에 아래 요구사항을 추가한다.

```text
추가 요구사항: Visualization / Committee Pack Layer 보강

1. 기존 엔진 산출물을 단순 diagnostic sheet로 보여주지 말고,
   운용 의사결정 스토리로 재구성한다.

2. 최종 보고서 흐름은 다음 순서를 따른다.
   Regime → SAA → TAA → Implementation / Selection → Attribution / Monitoring

3. reporting/ 아래에 다음 builder 인터페이스를 설계한다.
   - RegimePageBuilder
   - SAAPageBuilder
   - TAAPageBuilder
   - SelectionPageBuilder
   - AttributionPageBuilder
   - CommitteePackBuilder
   - VisualizationSpecBuilder

4. Regime page에는 placement-velocity clock, 최근 12~24개월 궤적,
   현재 포인트, phase 정의, 자산군 선호도 heatmap을 포함한다.

5. SAA page에는 CMA, vol/corr, 제약조건, efficient frontier,
   채택된 SAA 포인트, risk contribution을 포함한다.

6. TAA page에는 regime별 expected return / volatility / utility 변화,
   SAA 대비 TAA 이동, recommended tilt, turnover/cost impact를 포함한다.

7. Selection page에는 자산군별 universe, scoring criteria,
   최종 선택 상품, 대체 후보 대비 선정 이유, ongoing due diligence 항목을 포함한다.

8. Attribution page에는 성과를 SAA allocation, TAA tilt, selection,
   FX/hedge, cost bucket으로 분해한다.

9. Projection clipping, solver telemetry, constraint binding details는
   본문이 아니라 Appendix / Diagnostics로 이동한다.

10. 산출물은 docs/reporting/placement_velocity_committee_pack_spec.md에 정리한다.
```

---

## 13. Claude에게 전달할 작업지시서

아래 지시서를 Claude에게 전달하면 된다.

```text
프로젝트: Placement / Velocity 기반 TAA 엔진 설계 문서화 및 초기 모듈 스펙 작성

역할:
너는 TDF 2060 / OCIO / LDI 자산배분 엔진을 구현하는 Claude Code다.
이번 작업은 코딩 전 단계의 설계 정리 작업이다.

배경:
사용자는 경기국면을 단순 regime label이 아니라 placement(현재 위치)와 velocity(변화속도)의 2차원 또는 다차원 state-space로 정의하고자 한다.
이 state-space를 기반으로 rule-based TAA → regime-conditioned MVO → HMM/Markov transition → MPC → RL overlay 순서로 발전시키는 엔진을 설계한다.

중요 원칙:
1. RL을 초기 메인 엔진으로 두지 말 것.
2. 우선 해석 가능한 RegimeMapEngine을 만든다.
3. 그 다음 RegimeTransitionEngine과 RegimeConditionedMVO를 붙인다.
4. MPC는 v4의 핵심 중간 엔진으로 둔다.
5. RL은 v5 이후 benchmark-relative active tilt overlay로 제한한다.
6. Differential Sharpe Ratio는 보조항으로만 쓰고, TDF/LDI reward는 funding ratio, shortfall, drawdown, turnover, glide path deviation 중심으로 별도 설계한다.
7. 모든 macro feature는 publication lag와 expanding-window standardization을 고려한다.
8. 최종 산출물은 투자위원회에 설명 가능한 SignalReport를 포함해야 한다.

이번 작업 산출물:

1. docs/research/placement_velocity_taa_spec.md
   - placement / velocity 개념 정의
   - 문헌 매핑
   - 모델별 리서치 결과 취합
   - 최종 아키텍처
   - 개발 로드맵

2. docs/research/core_literature_register.md
   - Sood et al. 2023
   - Nystrup et al. 2019
   - Boyd et al. 2017
   - Guidolin & Timmermann 2007
   - Bae, Kim & Mulvey 2014
   - Brennan, Schwartz & Lagnado 1997
   - Brandt et al. 2005
   - Investment Clock
   - SOA LDI
   - Jang / Clare / Owadally 2024

3. docs/architecture/placement_velocity_taa_architecture.md
   - MacroFeatureEngine
   - RegimeMapEngine
   - RegimeTransitionEngine
   - TAAOptimizer
   - MPCOptimizer
   - RLEnvironment
   - ConstraintLayer
   - BacktestEngine
   - SignalReport

4. docs/roadmap/placement_velocity_taa_roadmap.md
   - Phase 0~8 단계별 구현 계획
   - 각 단계 entry criteria / exit criteria
   - 테스트 기준
   - 운영 리스크

5. 선택적으로 tdf_taa_engine/ 패키지 skeleton만 생성
   단, 실제 알고리즘 구현은 아직 하지 말고 클래스 인터페이스와 docstring 중심으로 작성한다.

주의:
- 현재 단계에서는 full RL training loop 구현 금지.
- HMM / MPC / RL은 interface만 열어둔다.
- point-in-time data와 look-ahead bias 관련 경고를 문서에 명시한다.
- 사용자가 투자위원회 / 운용역에게 설명할 수 있는 구조를 우선한다.
```

---

## 14. 다음 의사결정 필요 사항

| 번호 | 의사결정 | 기본 권고 |
|---:|---|---|
| 1 | core rebalancing frequency | 월간 |
| 2 | RL 도입 시점 | v5 이후 |
| 3 | RL action space | benchmark-relative active tilt |
| 4 | reward 주목적함수 | TDF/LDI별 분리 |
| 5 | first optimizer | regime-conditioned MVO |
| 6 | multi-period optimizer | MPC |
| 7 | regime model first version | rule-based phase-plane |
| 8 | transition model first version | empirical transition matrix → HMM |
| 9 | reporting requirement | signal report 필수 |
| 10 | Korean retirement constraints | 별도 constraint layer |

---

## 15. 후속 검색 키워드

```text
placement velocity business cycle asset allocation
level and momentum macro regime tactical asset allocation
OECD CLI above below 100 month-on-month asset allocation
business cycle phase plane portfolio allocation
investment clock regime switching tactical asset allocation
vol20 vol60 VIX reinforcement learning portfolio
macroeconomic regime detection tactical asset allocation FRED-MD
liability aware reinforcement learning pension asset allocation
funding ratio reward reinforcement learning pension
model predictive control tactical asset allocation regime
jump model regime switching portfolio allocation
funding-status glide path pension tactical overlay
target date fund dynamic glide path tactical asset allocation
duration gap reward RL LDI
turnover penalized drawdown penalized reward portfolio RL
regime-aware reinforcement learning long-horizon portfolio optimization
meta reinforcement learning goals-based wealth management
MPC-guided reinforcement learning portfolio allocation
```

---

## 16. 최종 요약

최종적으로 채택할 설계 방향은 다음이다.

```text
1. Placement / Velocity는 핵심 state representation으로 채택한다.
2. 첫 구현은 해석 가능한 RegimeMapEngine이다.
3. TAA 비중은 곧바로 RL로 만들지 않는다.
4. Regime-conditioned MVO와 MPC를 먼저 구현한다.
5. RL은 benchmark-relative corrective overlay로 제한한다.
6. TDF/LDI 목적함수는 Sharpe가 아니라 funding ratio, shortfall, drawdown, turnover, glide path deviation 중심으로 설계한다.
7. 모든 백테스트는 publication lag, expanding standardization, walk-forward validation을 전제로 한다.
8. 최종 산출물은 weight가 아니라 signal + rationale + constraint check + attribution report다.
9. 고객/위원회용 보고서는 Regime → SAA → TAA → Selection → Attribution 흐름으로 구성한다.
```

한 문장으로 정리하면 다음과 같다.

> **Placement / Velocity 기반 경기국면 지도는 TAA 엔진의 설명 가능한 상단 레이어이고, MPC / RL은 그 지도를 활용해 제약조건 안에서 active tilt를 조정하는 하단 제어 레이어로 두는 것이 가장 실무적이다.**
