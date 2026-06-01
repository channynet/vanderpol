# UI/UX Redesign For Analysis Workflow

## Purpose

이 문서는 Vanderpol ECG selector 프로젝트의 화면 UI/UX를 다시 설계하기
위한 구현 기준 문서다.

1차 구현 기준은 기존 `src/vanderpol/dashboard.py` 기반 로컬 Python
대시보드다. 별도 React 앱 전환은 즉시 전제하지 않는다. 다만 화면 상태와
컴포넌트 구조가 커질 가능성이 높으므로, React 전환 기준과 라우트 후보를
후반부에 로드맵으로 남긴다.

이 UI는 임상 의사결정 도구가 아니다. 모든 결과 화면은 simulation-only
outcome, reduced-order model, non-clinical use guardrail을 유지해야 한다.

## Project Analysis

### 프로젝트 성격

이 프로젝트는 4초 ECG 관찰 윈도우에서 handcrafted feature를 추출하고,
5개 전기자극 전략 중 하나를 선택하는 연구용 simulation/selector
pipeline이다.

핵심 episode 흐름은 다음과 같다.

```text
patient/scenario -> 4s ECG observation -> feature extraction
-> treatment action selection -> simulator episode
-> success/time/energy/safety/reward logging
```

현재 action set은 다음 5개다.

| ID | Action | UI 표시 이름 |
| ---: | --- | --- |
| 0 | `synchronized_cardioversion` | Synchronized cardioversion |
| 1 | `unsynchronized_defibrillation` | Unsynchronized defibrillation |
| 2 | `atp_burst_pacing` | ATP burst pacing |
| 3 | `resonant_drift_pacing` | Resonant drift pacing |
| 4 | `adaptive_low_energy_pacing` | Adaptive low-energy pacing |

현재 rhythm scenario는 다음 5개다.

| Scenario | 의미 |
| --- | --- |
| `nsr` | 정상 리듬. adaptive withhold가 중요한 안전 기준이다. |
| `svt_flutter` | organized tachyarrhythmia 계열. synchronized cardioversion anchor다. |
| `monomorphic_vt` | regular VT 계열. ATP/low-energy pacing 비교가 중요하다. |
| `polymorphic_vt` | irregular shockable rhythm 계열. defibrillation/fallback 판단이 중요하다. |
| `vf_like` | chaotic VF-like rhythm. unsynchronized defibrillation anchor다. |

### 데이터와 분석 흐름

현재 프로젝트의 실제 분석 흐름은 다음 파일/단계에 흩어져 있다.

```text
synthetic/real ECG data
-> configs/bundle_*.json
-> scripts/run_experiment_bundle.py
-> src/vanderpol/stage8.py
-> outputs/runs/<run_id>/*
-> src/vanderpol/stage9.py
-> outputs/runs/<run_id>/paper_artifacts/*
```

일반적인 분석 실험 흐름과 프로젝트 내부 단계를 매핑하면 다음과 같다.

| 일반 실험 흐름 | Vanderpol 내부 단계 | 현재 주요 산출물 |
| --- | --- | --- |
| Data | scenario presets, external ECG, calibration sources | `configs/calibration.json`, `data/raw/*`, `outputs/*noise*.json` |
| 분석 방법 설정 | bundle config, reward, selector, noise/fallback params | `configs/bundle_*.json`, `launch_config.json`, `run_manifest.json` |
| 분석 | Stage 8 bundle run | `events.jsonl`, `metrics.jsonl`, `current_progress.json`, step outputs |
| 중간 분석결과 리뷰 | step-level result review | phase2 figures, calibration, selector, decision boundary, CI, stability, noise, fallback |
| 종합 결과 리뷰 | run-level synthesis | selector vs ACLS/oracle, scenario winners, robustness, limitations |
| 결과 정리 | Stage 9 paper artifacts | `paper_summary.md`, paper tables, citations, limitations, artifact manifest |

### 현재 Stage 8 분석 단계

Stage 8 bundle은 다음 순서로 실행된다.

| Order | Step | 목적 | 대표 산출물 |
| ---: | --- | --- | --- |
| 1 | `phase2_figures` | scenario x algorithm 성능 행렬과 heatmap 생성 | `figures/phase2_*.png`, `phase2_matrix_summary.csv` |
| 2 | `calibration_report` | guideline/literature anchor 범위 통과 여부 확인 | `calibration_report.json` |
| 3 | `selector_report` | selector, ACLS rule, oracle, always-action baseline 비교 | `selector_report.json`, `selector_report.csv` |
| 4 | `decision_boundary` | QRS width x RR variability에서 selector/ACLS 결정 경계 확인 | `decision_boundary.png`, `decision_boundary.csv` |
| 5 | `bootstrap_ci` | scenario/algorithm metric 불확실성 확인 | `bootstrap_matrix_ci.csv` |
| 6 | `selector_stability` | seed별 selector 안정성 확인 | `selector_stability.json`, `selector_stability.csv` |
| 7 | `noise_ood_sweep` | clean/mild/moderate/severe noise robustness 확인 | `noise_ood_sweep.json`, `noise_ood_sweep.csv` |
| 8 | `fallback_threshold_sweep` | conservative fallback threshold grid 평가 | `fallback_threshold_sweep.*` |

### 현재 UI 구성요소 추출

현재 `render_dashboard_html()`는 다음 메뉴를 제공한다.

| 현재 메뉴 | 분류 | 주요 역할 | 재설계 판단 |
| --- | --- | --- | --- |
| Overview | Run monitoring | status, progress, ETA 요약 | `Runs`/`Analysis`에 흡수 |
| Timeline | Run monitoring | step timeline | `Analysis` 핵심 화면으로 이동 |
| Deep Progress | Run monitoring/debug | current unit counters, events, failure | `Analysis` 하위 상세 패널 |
| Outputs | Artifact browsing | artifact list, preview, gallery | `System` 또는 각 review 화면 보조 패널 |
| Metrics | Monitoring/review | scalar metric chart | `Intermediate Review`와 `Analysis` 보조 패널 |
| Settings | Method setup | current config editor, dry-run estimate | `Method Setup`으로 승격 |
| Compare | Review/iteration | run comparison JSON | `Runs`와 `Comprehensive Review`에 통합 |
| Diagnostics | System debug | PID/CPU/memory/heartbeat | `System` 하위 메뉴 |
| Control | Run operation | safe stop, resume, start | `Analysis` 하위 control zone |
| Provenance | Reproducibility | config, command, environment | `System`과 `Paper Result` 보조 정보 |
| Runs sidebar | Run selection | selected run context | `Runs` top-level로 승격 |
| Dry Run Estimate | Method setup | rough unit estimate | `Method Setup`에 배치 |

현재 UI의 가장 큰 문제는 정보가 운영/모니터링 기준으로 나뉘어 있어,
사용자의 분석 사고 흐름인 Data -> Method Setup -> Analysis ->
Intermediate Review -> Comprehensive Review -> Paper Result와 직접
연결되지 않는다는 점이다.

## Information Architecture

### Global Workflow Stepper

화면 상단 또는 좌측 상단에 고정 workflow stepper를 둔다.

```text
Data -> Method Setup -> Analysis Run -> Intermediate Review
-> Comprehensive Review -> Paper Result
```

Stepper는 단순 장식이 아니라 현재 선택된 `run_id`의 진행 상태와 연결된다.

| Stepper 단계 | 활성 조건 |
| --- | --- |
| Data | 항상 접근 가능 |
| Method Setup | config 또는 selected run이 있을 때 활성 |
| Analysis Run | run이 시작되었거나 기존 run을 선택했을 때 활성 |
| Intermediate Review | 하나 이상의 step artifact가 존재할 때 활성 |
| Comprehensive Review | selector/matrix/noise/fallback 중 2개 이상 artifact가 존재할 때 활성 |
| Paper Result | `paper_artifacts` 또는 생성 가능한 manifest가 있을 때 활성 |

### Top-level 메뉴

Top-level 메뉴는 다음 8개로 재구성한다.

| Top-level | 목적 | 대표 하위 메뉴 |
| --- | --- | --- |
| Runs | run 선택과 비교 기준 설정 | Run List, Run Snapshot, Baseline Compare |
| Data | 데이터와 simulation scope 이해 | Synthetic Scenarios, External ECG, Calibration Sources, Limitations |
| Method Setup | 분석 조건 설정과 dry-run estimate | Scale, Selector, Uncertainty, Noise/Fallback, Reward/Calibration |
| Analysis | 실행 상태와 checkpoint-safe control | Overview, Timeline, Deep Progress, Failure Triage, Safe Controls |
| Intermediate Review | 단계별 중간 결과 검토 | Calibration, Selector, Matrix, Boundary, CI, Stability, Noise, Fallback |
| Comprehensive Review | 종합 결론 판단 | Headline, Scenario Winners, Robustness, Fallback Recommendation, Confidence, Guardrails |
| Paper Result | 논문 형식 결과 정리 | Abstract, Methods, Results, Figures/Tables, Limitations, Citations, Artifact Index |
| System | 원천 파일과 재현성/진단 정보 | Artifacts, Provenance, Diagnostics, Raw Events, Raw Metrics |

### 메뉴 결정 근거

`Runs`, `Data`, `Method Setup`, `Analysis`, `Intermediate Review`,
`Comprehensive Review`, `Paper Result`는 사용자가 실제로 실험을 진행하고
해석하는 순서에 맞춘다.

`System`은 사용자가 "왜 값이 이렇게 나왔는지" 또는 "재현 가능한가"를
확인할 때 접근하는 보조 영역으로 둔다. 기존 `Outputs`, `Metrics`,
`Provenance`, `Diagnostics`는 독립 top-level보다 System 또는 각 review
화면의 context panel이 적합하다.

## Screen Design

### 1. Runs

목표는 사용자가 현재 보고 있는 run과 비교 기준 run을 명확히 인지하는 것이다.

주요 구성요소:

- run list: `run_id`, terminal/running status, current step, compact progress indicator.
- selected run summary: preset, patients per scenario, horizon, completed steps,
  terminal status, progress, live progress, heartbeat age, updated time.
- baseline selector: 현재 run과 비교할 `baseline_run_id` 지정.
- comparison preview: config diff, headline metric diff, changed artifacts count.

기존 `Overview`의 status card는 이 화면과 `Analysis Overview`에서 재사용한다.

#### Runs 목록 위치 상세 분석

Run 항목 목록은 좌측 전역 sidebar가 아니라 Top-level `Runs` 메뉴의 본문
하위 콘텐츠로 두는 것이 더 적합하다. 사용자는 `Runs` 메뉴를 눌렀을 때
run 선택, 현재 run 요약, baseline 비교를 한 화면에서 기대한다. 반대로
좌측 sidebar는 `Data`, `Method Setup`, `Analysis`, `Review`, `Paper`로
이동하는 전역 navigation 역할에 집중해야 한다.

따라서 `stage9_n100_time2`, `dashboard_smoke_observability`,
`stage9_n100` 같은 run 항목들은 `Runs` 화면 내부의 `Run Selector`
영역에 배치한다. 사이드바에는 Top-level 메뉴인 `Runs` 버튼만 남기고,
선택 가능한 run 리스트를 별도 navigation 그룹처럼 반복 노출하지 않는다.
이렇게 하면 `Runs`가 메뉴인지, run 목록인지 역할이 섞이는 문제를 줄일 수
있다.

다만 run item 안에
`stage9_n100_time2`, `completed step 100.0% live 100.0%`처럼 상세 상태
문장을 모두 넣는 것도 적합하지 않다.

이유는 다음과 같다.

| 항목 | Run Selector 표시 여부 | 이유 |
| --- | --- | --- |
| `run_id` | 표시 | 선택 대상의 기본 식별자다. |
| terminal/running status | 표시 | completed, running, stalled, failed 정도는 빠른 스캔에 필요하다. |
| current step | 조건부 표시 | running/stalled run에서는 유용하지만 completed run에서는 빈 값이거나 중복이다. |
| coarse progress bar | 표시 가능 | 텍스트보다 시각적이고 공간을 적게 쓴다. |
| `step 100.0%` text | 목록에서는 제외 | 아래 Run Snapshot/Analysis에서 더 정확한 맥락으로 보여야 한다. |
| `live 100.0%` text | 목록에서는 제외 | display progress와 coarse progress의 차이는 설명이 필요한 분석 정보다. |
| heartbeat age, updated time | 목록에서는 제외 | 목록을 복잡하게 만들며 Analysis/System 성격의 정보다. |

따라서 `Runs` 메뉴 본문은 다음 순서로 구성한다.

1. `Run Selector`: run 목록과 coarse progress bar.
2. `Run Snapshot`: 선택 run의 상태, step progress, live estimate,
   heartbeat age, elapsed/ETA.
3. `Baseline Compare`: 기준 run 선택과 diff preview.

권장 run item 표시 형식은 다음과 같다.

```text
stage9_n100_time2
completed
[compact progress bar]
```

running 또는 stalled run만 current step을 보조 텍스트로 덧붙인다.

```text
stage9_n100
stalled - fallback_threshold_sweep
[compact progress bar]
```

이렇게 하면 좌측은 navigation 역할에 집중하고, run 선택은 `Runs` 메뉴의
하위 콘텐츠로 명확해진다. `completed_steps`, `progress_fraction`,
`display_progress_fraction`, `heartbeat_age_s` 같은 상세 상태는 같은 화면의
`Run Snapshot` 또는 `Analysis` 본문에서 비교/해석 가능한 형태로 유지된다.

### 2. Data

목표는 이 실험이 어떤 데이터와 어떤 한계를 바탕으로 실행되는지 먼저 보이게
하는 것이다.

하위 화면:

| Submenu | 표시 항목 |
| --- | --- |
| Synthetic Scenarios | 5 rhythm scenario, patient preset, variability, generated outcome 역할 |
| External ECG | MIT-BIH, CUDB, Challenge 2015, PTB-XL의 사용/미사용 역할 |
| Calibration Sources | `configs/calibration.json` targets, source, target min/max, pass/fail 연결 |
| Limitations | `configs/limitations.json`, simulation-only treatment outcome, non-clinical guardrail |

Data 화면은 분석 결과를 주장하기 전에 해석 범위를 잠그는 장치다.

### 3. Method Setup

목표는 분석 파라미터를 사람이 이해하는 그룹으로 보여주고, 변경하면 어떤 결과가
영향을 받는지 즉시 알게 하는 것이다.

파라미터 그룹:

| Group | Parameters | 영향을 받는 결과 |
| --- | --- | --- |
| Scale | `patients_per_scenario`, `horizon_s`, `n_jobs` | 모든 Stage 8 step, runtime, CI width |
| Selector | `train_fraction`, `selector_seed`, `selector_stability_seeds` | selector report, stability, decision boundary |
| Uncertainty | `bootstrap_samples`, `decision_grid_size` | bootstrap CI, decision boundary runtime/detail |
| Noise/Fallback | `noise_profiles`, `real_noise_stats`, `category_noise_stats`, `fallback_min_sqi`, `fallback_entropy`, `fallback_rr_cv` | noise/OOD, fallback sweep, conservative selector |
| Reward/Calibration | `reward_weights`, `calibration_config` | reward ranking, calibration pass/fail, paper claims |

UI 동작:

- running run의 config는 read-only로 표시한다.
- config edit은 새 run 생성 후보로 취급한다.
- `Dry Run Estimate`는 변경된 config에 대해 rough unit count와 영향받는 step을
  함께 표시한다.
- 변경된 parameter는 `changed from baseline` badge를 붙인다.

### 4. Analysis

목표는 분석 실행 중 사용자가 진행 상황과 이상 상태를 신뢰할 수 있게 보는 것이다.

하위 화면:

| Submenu | 표시 항목 |
| --- | --- |
| Overview | status, completed steps, display progress, ETA, heartbeat, current step |
| Timeline | 8개 Stage 8 step의 status, duration, outputs count, latest message |
| Deep Progress | current detail JSON을 사람이 읽는 counters로 변환 |
| Failure Triage | failed/stalled/warning일 때 exception, traceback tail, stderr tail, last event |
| Safe Controls | safe stop request, resume, start from config |

`fallback_threshold_sweep`는 가장 긴 단계이므로 별도 detailed card를 둔다.

- precomputing profiles: `completed_profiles / total_profiles`
- evaluating configs: `completed_configs / total_configs`
- current config: `min_signal_quality`, `high_entropy_threshold`,
  `high_rr_cv_threshold`
- partial artifacts: `.partial.json`, `.partial.csv`

### 5. Intermediate Review

목표는 각 분석 단계가 끝날 때 사용자가 중간 결론을 단계별로 검토하고, 다음
iteration에서 조정할 파라미터를 찾게 하는 것이다.

하위 화면:

| Review | Source artifact | 핵심 질문 | 표시 구성요소 |
| --- | --- | --- | --- |
| Calibration | `calibration_report.json` | simulation behavior가 anchor range를 통과하는가 | pass rate, failed checks, target/value table |
| Selector | `selector_report.*` | selector가 ACLS/oracle/fixed baseline 대비 어떤가 | policy table, reward/oracle gap/success cards |
| Matrix | `phase2_matrix_summary.csv`, heatmaps | scenario별 best algorithm이 타당한가 | metric tabs, scenario winner table, heatmap gallery |
| Boundary | `decision_boundary.*` | selector decision boundary가 collapse 되었는가 | selector vs ACLS panel, grid CSV preview |
| Bootstrap CI | `bootstrap_matrix_ci.csv` | metric uncertainty가 큰 조합은 어디인가 | CI table, wide CI highlight |
| Stability | `selector_stability.*` | seed 변화에 selector가 안정적인가 | seed summary, mean/std table |
| Noise/OOD | `noise_ood_sweep.*` | noise profile이 selector를 얼마나 약화시키는가 | profile x policy table, severe-noise delta |
| Fallback | `fallback_threshold_sweep.*` | conservative fallback threshold가 개선을 만드는가 | threshold grid, best configs, fallback reason summary |

각 review 화면에는 `Related Parameters` 패널을 둔다. 예를 들어 Fallback review는
`fallback_min_sqi`, `fallback_entropy`, `fallback_rr_cv`, `noise_profiles`,
`real_noise_stats`, `category_noise_stats`를 직접 연결한다.

### 6. Comprehensive Review

목표는 단일 step 결과가 아니라 전체 run의 해석 가능한 결론을 만든다.

필수 구성요소:

| Section | 표시 내용 |
| --- | --- |
| Headline Result | selector, conservative selector, ACLS, oracle의 reward/oracle gap/success |
| Scenario Winners | scenario별 best algorithm과 clinical-intuition alignment |
| Robustness | clean -> severe noise에서 selector/ACLS/oracle 변화 |
| Fallback Recommendation | best threshold region, selector 개선량, ACLS 대비 남은 gap |
| Confidence | bootstrap CI, stability seed variance, incomplete/missing artifacts |
| Failure Modes | decision-boundary collapse, noise sensitivity, weak scenario/action |
| Guardrails | simulation-only outcomes, non-clinical use, reduced-order model limitations |

종합 리뷰는 "AI가 ACLS를 이겼는가" 같은 단정형 문장을 자동으로 만들지 않는다.
현재 결과가 ACLS baseline보다 약하면 그 사실을 headline에 그대로 드러낸다.

### 7. Paper Result

목표는 Stage 9 산출물을 사용해 논문 형식의 결과 정리 페이지를 제공하는 것이다.

하위 화면:

| Section | Source | 내용 |
| --- | --- | --- |
| Abstract-style Summary | `paper_summary.md`, derived metrics | background, method, main result, limitation |
| Methods | `run_manifest.json`, config | simulator, scenarios, feature vector, selector, evaluation setup |
| Results | paper tables, figures | policy comparison, scenario matrix, robustness, fallback |
| Figures/Tables | `paper_artifacts/*` | manuscript-ready table links and figure gallery |
| Limitations | `limitations.md` | simulation-only, reduced-order, data limitations |
| Citations | `citations.md` | source list and role |
| Artifact Index | `paper_artifacts_manifest.json` | generated file inventory |

이 페이지는 결과를 "정리"하는 화면이다. raw artifact preview가 아니라, 논문
독자가 읽는 순서에 맞춰 재배치해야 한다.

### 8. System

목표는 debugging, reproducibility, raw artifact inspection을 한곳에 모으는 것이다.

하위 화면:

- Artifacts: 기존 `Outputs` 기능. step/kind/status/search filter와 preview 유지.
- Provenance: command line, resolved config, environment, git availability.
- Diagnostics: PID/CPU/memory, heartbeat age, worker count.
- Raw Events: `events.jsonl` tail.
- Raw Metrics: `metrics.jsonl` raw table and simple chart.
- Failure Raw: `failure_summary.json` raw view.

## Parameter Iteration UX

### Shared Context

모든 화면은 다음 상태를 공유한다.

```text
selected_run_id
baseline_run_id
draft_config
active_workflow_step
active_review_step
```

`selected_run_id`는 결과를 읽는 기준이고, `baseline_run_id`는 비교 기준이다.
`draft_config`는 아직 실행되지 않은 다음 iteration 후보 config다.

### Iteration Flow

권장 iteration 흐름:

```text
Comprehensive Review에서 failure mode 확인
-> Intermediate Review에서 관련 step drill-down
-> Related Parameters에서 조정 후보 확인
-> Method Setup에서 draft_config 변경
-> Dry Run Estimate 확인
-> 새 run 시작
-> Runs에서 baseline과 비교
```

### Parameter-to-Result Linking

파라미터 조정 시 UI는 영향받는 결과를 즉시 표시한다.

| Parameter | 표시할 영향 |
| --- | --- |
| `patients_per_scenario` | all matrix scale, runtime, bootstrap CI stability |
| `horizon_s` | success/time/reward interpretation |
| `reward_weights` | mean reward ranking, scenario winners, selector policy comparison |
| `train_fraction` | selector report, stability, boundary |
| `selector_seed` | selector split, selected actions, oracle gap |
| `selector_stability_seeds` | stability report runtime and variance |
| `bootstrap_samples` | CI reliability and runtime |
| `decision_grid_size` | decision boundary resolution and runtime |
| `noise_profiles` | noise/OOD rows and fallback profile coverage |
| `real_noise_stats` | real-estimated profile availability |
| `category_noise_stats` | alarm-category-derived profiles |
| `fallback_min_sqi` | low-SQI fallback behavior |
| `fallback_entropy` | chaotic rhythm fallback behavior |
| `fallback_rr_cv` | irregular rhythm fallback behavior |
| `calibration_config` | calibration pass/fail and paper guardrails |

### Run Compare

Run comparison은 JSON dump가 아니라 세 구획으로 보여준다.

1. Config diff: changed parameters only, grouped by Method Setup group.
2. Metric diff: selector/ACLS/oracle/conservative selector의 reward, oracle gap,
   success, safety violations 변화.
3. Artifact diff: 새로 생성된 artifact, 누락 artifact, partial/final status.

## API And Helper Changes

### Existing APIs To Keep

현재 API는 유지하고 우선 활용한다.

| API | 사용 화면 |
| --- | --- |
| `GET /api/runs` | Runs |
| `GET /api/runs/{run_id}/progress` | Runs, Analysis |
| `GET /api/runs/{run_id}/events?tail=200` | Analysis, System |
| `GET /api/runs/{run_id}/metrics` | Analysis, Intermediate Review, System |
| `GET /api/runs/{run_id}/artifacts` | Review pages, Paper Result, System |
| `GET /api/runs/{run_id}/failure` | Analysis, System |
| `GET /api/runs/{run_id}/diagnostics` | System |
| `GET /api/compare?runs=a,b` | Runs, Comprehensive Review |
| `GET /api/dry-run?config=...` | Method Setup |

기존 `run_manifest.json`, `current_progress.json`, `events.jsonl`,
`metrics.jsonl`, `artifacts.jsonl` 스키마는 유지한다.

### Recommended Read-only Helpers

구현 편의를 위해 다음 helper/API를 추가할 수 있다.

| Helper | API | 역할 |
| --- | --- | --- |
| `load_analysis_summary(run_dir)` | `GET /api/runs/{id}/analysis-summary` | selector/matrix/noise/fallback 핵심 metric을 한 번에 반환 |
| `load_paper_artifact_index(run_dir)` | `GET /api/runs/{id}/paper-artifacts` | paper artifact 존재 여부, 링크, warning 반환 |
| `load_config_diff(base_run, target_run)` | `/api/compare` 확장 또는 별도 endpoint | Method Setup group 기준 config diff 반환 |

`load_analysis_summary` 권장 반환 구조:

```json
{
  "run_id": "stage9_n20",
  "status": "completed",
  "headline": {
    "selector_linucb": {"mean_reward": 84.9, "oracle_gap": 14.5, "success_rate": 0.867},
    "acls_rule": {"mean_reward": 91.4, "oracle_gap": 8.0, "success_rate": 0.933},
    "oracle": {"mean_reward": 99.4, "oracle_gap": 0.0, "success_rate": 1.0}
  },
  "scenario_winners": [],
  "robustness": [],
  "fallback_best_configs": [],
  "warnings": []
}
```

이 helper는 UI 전용 read model이다. 분석 원천 산출물의 스키마를 대체하지 않는다.

## React Roadmap

### Recommendation

지금 당장 전체 React 전환은 필수는 아니다. 현재 프로젝트는 Python 분석
pipeline이 중심이고, 로컬 단일 사용자 dashboard가 이미 API와 artifact viewer를
갖고 있다.

다만 다음 조건 중 2개 이상이 충족되면 React 전환을 시작한다.

- 파라미터 draft/edit 상태가 복잡해져 vanilla JS 유지보수가 어려워진다.
- review 화면이 5개 이상 독립 view state를 갖는다.
- run comparison이 table/chart/filter 상태를 많이 갖는다.
- paper result page가 interactive outline, editable sections, export workflow를
  필요로 한다.
- dashboard.py의 HTML/JS 문자열이 1개 파일에서 계속 커져 테스트가 어려워진다.

### React Route Candidates

React로 전환하더라도 동일 API를 소비한다.

| Route | 대응 메뉴 |
| --- | --- |
| `/runs` | Runs |
| `/data` | Data |
| `/setup` | Method Setup |
| `/analysis` | Analysis |
| `/review/intermediate` | Intermediate Review |
| `/review/comprehensive` | Comprehensive Review |
| `/paper` | Paper Result |
| `/system` | System |

### Component Candidates

| Component | 역할 |
| --- | --- |
| `WorkflowStepper` | Data -> Paper Result 진행 표시 |
| `RunSelector` | selected/baseline run 선택 |
| `StatusCards` | status, progress, heartbeat, ETA |
| `ConfigGroupEditor` | grouped config editing and diff badges |
| `DryRunEstimatePanel` | rough unit count, affected steps |
| `StageTimeline` | Stage 8 step list |
| `ReviewTabs` | calibration/selector/matrix/noise/fallback drill-down |
| `PolicyComparisonTable` | selector/ACLS/oracle 비교 |
| `ScenarioWinnerTable` | scenario별 best algorithm |
| `ArtifactPreviewer` | md/csv/json/png/html preview |
| `GuardrailBanner` | non-clinical limitation reminder |

### Migration Strategy

1. 먼저 기존 dashboard에 `analysis-summary`, `paper-artifacts`, grouped compare
   read model을 추가한다.
2. 단일 HTML UI에서도 새 IA와 workflow stepper를 적용한다.
3. API/read model이 안정되면 React 앱을 별도 `frontend/` 또는 `web/`로 만든다.
4. React 앱은 기존 Python server가 static build를 서빙하거나, 개발 중에는 Vite
   dev server가 Python API proxy를 사용한다.

## Implementation Notes

### First Python Dashboard Iteration

1차 구현에서 `dashboard.py`는 다음 순서로 수정한다.

1. sidebar 메뉴를 새 top-level IA로 교체한다.
2. 기존 panel을 삭제하지 않고 새 메뉴의 하위 panel로 재배치한다.
3. `Runs`, `Method Setup`, `Analysis`를 먼저 연결해 현재 기능 손실을 막는다.
4. `Intermediate Review`와 `Comprehensive Review`는 artifact-derived summary를
   우선 표시하고, raw preview는 System으로 이동한다.
5. `Paper Result`는 `paper_artifacts` 폴더가 있으면 해당 파일을 보여주고, 없으면
   생성 명령과 missing artifact list를 보여준다.

### Visual Design Direction

- 연구/운영 도구이므로 landing page나 hero page를 만들지 않는다.
- 화면은 dense but organized dashboard 스타일을 유지한다.
- card는 반복 항목, modal, 개별 panel에만 사용하고, page section은 넓은 band나
  unframed layout으로 둔다.
- 버튼은 icon + tooltip 중심으로 하고, 낯선 action만 text label을 붙인다.
- 논문형 결과 페이지는 읽기 흐름이 중요하므로 시각적 장식보다 heading,
  table, figure order를 우선한다.

## Test And Acceptance Criteria

### Documentation Acceptance

- 현재 메뉴 구성요소가 추출되고 분류되어 있다.
- 어떤 메뉴를 top-level로 두고 어떤 항목을 submenu/context panel로 둘지 결정되어 있다.
- 일반 실험 흐름과 Stage 8 실제 단계가 매핑되어 있다.
- 파라미터 iteration에서 parameter -> affected result 연결이 정의되어 있다.
- 종합 리뷰 페이지와 논문형 결과 정리 페이지의 구성요소가 명확하다.
- React는 즉시 전환이 아니라 전환 로드맵으로 기록되어 있다.

### Future Code Tests

후속 UI 구현 시 `tests/test_dashboard.py`에 다음 테스트를 추가한다.

- `load_analysis_summary()`가 selector report가 있는 run에서 headline metrics를 반환한다.
- `load_analysis_summary()`가 일부 artifact가 없는 partial run에서도 warnings를 반환하고 실패하지 않는다.
- `load_paper_artifact_index()`가 `paper_artifacts_manifest.json`,
  `paper_summary.md`, paper tables, citations, limitations 존재 여부를 반환한다.
- grouped config diff가 scale/selector/uncertainty/noise/fallback/reward group으로
  changed parameters를 분류한다.
- `/api/runs/{id}/analysis-summary`와 `/api/runs/{id}/paper-artifacts`가 JSON-safe
  payload를 반환한다.

### Manual Verification

1차 dashboard 구현 후 수동 확인 항목:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python scripts/serve_dashboard.py --host 127.0.0.1 --port 8765
```

브라우저 확인:

- `http://127.0.0.1:8765`가 열린다.
- `Runs`에서 기존 run을 선택할 수 있다.
- workflow stepper가 selected run의 artifact 상태와 맞게 활성화된다.
- `Method Setup`에서 config group과 dry-run estimate가 보인다.
- `Analysis`에서 timeline/deep progress/failure triage가 보인다.
- `Intermediate Review`에서 각 Stage 8 artifact가 단계별로 보인다.
- `Comprehensive Review`에서 selector vs ACLS vs oracle 결론이 보인다.
- `Paper Result`에서 `paper_artifacts` 기반 논문형 정리가 보인다.
- `System`에서 raw artifacts/provenance/diagnostics/events/metrics를 확인할 수 있다.

## Defaults And Assumptions

- 1차 구현은 기존 Python 단일 HTML dashboard 개선이다.
- run 상태와 artifact는 기존 `outputs/runs/<run_id>` 파일을 source of truth로 둔다.
- running run의 parameter는 직접 수정하지 않는다. 수정은 새 run draft config를 만든다.
- 새 database, authentication, multi-user orchestration은 범위 밖이다.
- UI는 모든 결과 리뷰에서 "not a clinical tool" guardrail을 유지한다.
