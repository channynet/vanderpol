# Stage 9 n20 Result Summary

Prepared on: 2026-05-20

This file is the single entry point for the `stage9_n20` results. It links the
main outputs, records the headline metrics, and explains how to read each
artifact. The system is a simulation research scaffold, not a clinical decision
tool.

## 1. Run Status

- Run ID: `stage9_n20`
- Preset: `n20`
- Patients per scenario: `20`
- Treatment horizon: `30.0` seconds
- Final status: `8/8 completed`
- Calibration pass rate: `1.000`
- Fallback threshold configs: `12`
- Paper artifacts: `17`

Progress files:

- [run_progress.md](../outputs/runs/stage9_n20/run_progress.md)
- [run_manifest.json](../outputs/runs/stage9_n20/run_manifest.json)

## 2. Start Here

Open these first:

- [paper_summary.md](../outputs/runs/stage9_n20/paper_artifacts/paper_summary.md): headline result summary
- [live_dashboard.html](../outputs/runs/stage9_n20/paper_artifacts/live_dashboard.html): visual dashboard and artifact links
- [paper_selector_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_selector_table.md): selector vs baselines

## 3. Headline Metrics

Final selector comparison:

| Policy | Mean reward | Oracle gap | Success rate | Mean energy | Mean time s | Safety violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Selector LinUCB | 84.914 | 14.539 | 0.867 | 0.264 | 5.954 | 0.000 |
| ACLS-rule baseline | 91.456 | 7.996 | 0.933 | 0.295 | 3.661 | 0.033 |
| Oracle | 99.452 | 0.000 | 1.000 | 0.333 | 0.858 | 0.000 |

Interpretation:

- The current `LinUCB` selector is weaker than the ACLS-rule baseline on mean reward.
- The oracle gap remains substantial, so the learned policy is not close to the simulator upper bound yet.
- The correct claim is not "AI beats ACLS." The correct claim is that the selector framework works, but this handcrafted-feature LinUCB policy needs better representation or policy learning.
- The always-policy baselines are mostly weaker than selector/ACLS, so patient-specific algorithm selection is still a meaningful problem.

## 4. Best Algorithm By Scenario

Files:

- [paper_algorithm_winners.md](../outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_winners.md)
- [phase2_mean_reward.png](../outputs/runs/stage9_n20/figures/phase2_mean_reward.png)
- [phase2_success_rate.png](../outputs/runs/stage9_n20/figures/phase2_success_rate.png)

Summary:

| Scenario | Best algorithm | Mean reward | Success rate |
| --- | --- | ---: | ---: |
| `nsr` | `adaptive_low_energy_pacing` | 100.000 | 1.000 |
| `svt_flutter` | `synchronized_cardioversion` | 94.080 | 0.950 |
| `monomorphic_vt` | `atp_burst_pacing` | 99.010 | 1.000 |
| `polymorphic_vt` | `unsynchronized_defibrillation` | 88.274 | 0.900 |
| `vf_like` | `unsynchronized_defibrillation` | 98.992 | 1.000 |

Interpretation:

- Normal rhythm is best handled by withholding stimulation through the adaptive option.
- Monomorphic VT favors ATP burst pacing.
- VF-like and polymorphic VT favor unsynchronized defibrillation.
- SVT/flutter favors synchronized cardioversion.
- This scenario matrix is directionally consistent with the intended clinical intuition.

## 5. Noise And OOD Robustness

Files:

- [paper_noise_robustness_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_noise_robustness_table.md)
- [noise_ood_sweep.csv](../outputs/runs/stage9_n20/noise_ood_sweep.csv)

How to read it:

- Profiles progress from `clean` to `mild`, `moderate`, and `severe`.
- Higher `mean_reward` is better.
- Lower `oracle_gap` is better.
- Lower `mean_safety_violations` is better.

Important observation:

- Under severe noise, selector reward drops to `77.692`.
- Under severe noise, ACLS-rule reward is `82.462`.
- The current handcrafted selector is more noise-sensitive than the ACLS-rule baseline.

## 6. Conservative Fallback Sweep

Files:

- [paper_fallback_sweep_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_fallback_sweep_table.md)
- [fallback_threshold_sweep.csv](../outputs/runs/stage9_n20/fallback_threshold_sweep.csv)
- [fallback_threshold_sweep.json](../outputs/runs/stage9_n20/fallback_threshold_sweep.json)

This sweep asks when the model should trust the learned selector and when it
should fall back to an ACLS-style conservative rule.

Threshold variables:

| Variable | Meaning |
| --- | --- |
| `min_signal_quality` | If SQI is below this value, trust the selector less |
| `high_entropy_threshold` | If entropy is above this value, treat rhythm/noise as more chaotic |
| `high_rr_cv_threshold` | If RR variability is above this value, treat rhythm as more irregular |

Best average conservative-selector region:

| min_signal_quality | high_entropy_threshold | high_rr_cv_threshold | Mean reward | Oracle gap | Success rate | Safety violations |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | 0.55 or 0.62 | 0.25 or 0.3 | 84.742 | 13.354 | 0.879 | 0.073 |

Average comparison in that region:

| Policy | Mean reward | Oracle gap | Success rate | Safety violations |
| --- | ---: | ---: | ---: | ---: |
| Raw selector | 82.554 | 15.541 | 0.860 | 0.079 |
| Conservative selector | 84.742 | 13.354 | 0.879 | 0.073 |
| ACLS-rule | 85.906 | 12.189 | 0.893 | 0.094 |
| Oracle | 98.095 | 0.000 | 1.000 | 0.063 |

Interpretation:

- Conservative fallback improves the raw selector.
- ACLS-rule still has better mean reward and success rate.
- Conservative selector has fewer safety violations than ACLS-rule in this aggregate.
- The clean conclusion is: fallback helps the selector, but it does not yet outperform ACLS-rule overall.

## 7. Main Figures

| Figure | Use |
| --- | --- |
| [phase2_mean_reward.png](../outputs/runs/stage9_n20/figures/phase2_mean_reward.png) | Scenario by algorithm reward heatmap |
| [phase2_success_rate.png](../outputs/runs/stage9_n20/figures/phase2_success_rate.png) | Success-rate heatmap |
| [phase2_mean_energy.png](../outputs/runs/stage9_n20/figures/phase2_mean_energy.png) | Energy-use heatmap |
| [phase2_mean_time_s.png](../outputs/runs/stage9_n20/figures/phase2_mean_time_s.png) | Time-to-termination heatmap |
| [phase2_mean_safety_violations.png](../outputs/runs/stage9_n20/figures/phase2_mean_safety_violations.png) | Safety-violation heatmap |
| [decision_boundary.png](../outputs/runs/stage9_n20/figures/decision_boundary.png) | QRS width by RR regularity decision boundary |

Recommended figure-reading order:

1. Use `phase2_mean_reward.png` to identify which algorithms specialize in which scenarios.
2. Use `phase2_success_rate.png` to check whether reward is mostly driven by success.
3. Use `phase2_mean_safety_violations.png` to find risky scenario/algorithm combinations.
4. Use `decision_boundary.png` to inspect how the selector partitions feature space.

## 8. Bottom Line

Current `stage9_n20` conclusion:

1. The simulator and algorithm matrix behave in a clinically plausible direction.
2. `LinUCB` with handcrafted features is weaker than the ACLS-rule baseline.
3. Conservative fallback improves the raw selector.
4. ACLS-rule remains stronger on mean reward in this run.
5. The next technical step should be better representation: learned ECG encoder, richer features, or refined reward/threshold calibration.

Short version:

> This run supports the framework and the safety-fallback analysis. It does not yet support a claim that the learned selector beats ACLS-rule.
