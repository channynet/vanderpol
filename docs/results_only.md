# Stage 9 n20 Results Only

## Run

| Field | Value |
| --- | --- |
| run_id | `stage9_n20` |
| preset | `n20` |
| patients_per_scenario | `20` |
| horizon_s | `30.0` |
| status | `completed` |
| progress | `8/8` |
| calibration_pass_rate | `1.000` |
| fallback_threshold_configs | `12` |
| paper_artifacts | `17` |

## Selector Policy Summary

| Policy | Policy ID | Mean reward | Oracle gap | Success rate | Mean energy | Mean time s | Safety violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Selector LinUCB | `selector_linucb` | 84.914 | 14.539 | 0.867 | 0.264 | 5.954 | 0.000 |
| ACLS-rule baseline | `acls_rule` | 91.456 | 7.996 | 0.933 | 0.295 | 3.661 | 0.033 |
| Oracle | `oracle` | 99.452 | 0.000 | 1.000 | 0.333 | 0.858 | 0.000 |
| Always synchronized cardioversion | `always_synchronized_cardioversion` | 36.488 | 62.964 | 0.500 | 0.300 | 15.514 | 0.467 |
| Always unsynchronized defibrillation | `always_unsynchronized_defibrillation` | 45.693 | 53.759 | 0.633 | 0.686 | 11.817 | 0.700 |
| Always ATP | `always_atp` | 17.040 | 82.413 | 0.400 | 0.080 | 19.522 | 0.900 |
| Always resonant drift | `always_resonant_drift` | 27.556 | 71.897 | 0.433 | 0.029 | 20.328 | 0.533 |
| Always adaptive low-energy pacing | `always_adaptive` | 70.660 | 28.792 | 0.733 | 0.033 | 10.561 | 0.000 |

## Best Algorithm By Scenario

| Scenario | Best algorithm | Mean reward | Success rate | Mean energy | Mean time s | Safety violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `nsr` | `adaptive_low_energy_pacing` | 100.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| `svt_flutter` | `synchronized_cardioversion` | 94.080 | 0.950 | 0.300 | 2.478 | 0.000 |
| `monomorphic_vt` | `atp_burst_pacing` | 99.010 | 1.000 | 0.080 | 3.639 | 0.000 |
| `polymorphic_vt` | `unsynchronized_defibrillation` | 88.274 | 0.900 | 0.686 | 4.161 | 0.000 |
| `vf_like` | `unsynchronized_defibrillation` | 98.992 | 1.000 | 0.686 | 1.290 | 0.000 |

## Calibration Checks

| Scenario | Algorithm | Metric | Value | Target min | Target max | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `svt_flutter` | `synchronized_cardioversion` | `success_rate` | 0.950 | 0.750 | 0.980 | `pass` |
| `monomorphic_vt` | `atp_burst_pacing` | `success_rate` | 1.000 | 0.750 | 1.000 | `pass` |
| `polymorphic_vt` | `atp_burst_pacing` | `success_rate` | 0.050 | 0.000 | 0.250 | `pass` |
| `vf_like` | `unsynchronized_defibrillation` | `success_rate` | 1.000 | 0.750 | 1.000 | `pass` |
| `vf_like` | `synchronized_cardioversion` | `success_rate` | 0.050 | 0.000 | 0.200 | `pass` |
| `monomorphic_vt` | `resonant_drift_pacing` | `energy_ratio_vs_unsync_defibrillation` | 0.043 | 0.000 | 0.200 | `pass` |
| `vf_like` | `resonant_drift_pacing` | `success_rate` | 0.100 | 0.000 | 0.350 | `pass` |
| `nsr` | `adaptive_low_energy_pacing` | `success_rate` | 1.000 | 0.950 | 1.000 | `pass` |

## Noise Robustness

| Profile | Policy | Mean reward | Oracle gap | Success rate | Mean energy | Mean time s | Safety violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `clean` | Selector LinUCB | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| `clean` | ACLS-rule baseline | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| `clean` | Oracle | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| `mild` | Selector LinUCB | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| `mild` | ACLS-rule baseline | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| `mild` | Oracle | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| `moderate` | Selector LinUCB | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| `moderate` | ACLS-rule baseline | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| `moderate` | Oracle | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| `severe` | Selector LinUCB | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| `severe` | ACLS-rule baseline | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| `severe` | Oracle | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |

## Fallback Sweep Aggregate

| Threshold region | Policy | Mean reward | Oracle gap | Success rate | Safety violations |
| --- | --- | ---: | ---: | ---: | ---: |
| `min_signal_quality=0.5`, `entropy=0.55 or 0.62`, `rr_cv=0.25 or 0.3` | Raw selector | 82.554 | 15.541 | 0.860 | 0.079 |
| `min_signal_quality=0.5`, `entropy=0.55 or 0.62`, `rr_cv=0.25 or 0.3` | Conservative selector | 84.742 | 13.354 | 0.879 | 0.073 |
| `min_signal_quality=0.5`, `entropy=0.55 or 0.62`, `rr_cv=0.25 or 0.3` | ACLS-rule | 85.906 | 12.189 | 0.893 | 0.094 |
| `min_signal_quality=0.5`, `entropy=0.55 or 0.62`, `rr_cv=0.25 or 0.3` | Oracle | 98.095 | 0.000 | 1.000 | 0.063 |

## Output Files

| Artifact | Path |
| --- | --- |
| Paper summary | [paper_summary.md](../outputs/runs/stage9_n20/paper_artifacts/paper_summary.md) |
| Dashboard | [live_dashboard.html](../outputs/runs/stage9_n20/paper_artifacts/live_dashboard.html) |
| Selector table | [paper_selector_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_selector_table.md) |
| Algorithm matrix table | [paper_algorithm_matrix_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_matrix_table.md) |
| Algorithm winners | [paper_algorithm_winners.md](../outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_winners.md) |
| Noise robustness table | [paper_noise_robustness_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_noise_robustness_table.md) |
| Fallback sweep table | [paper_fallback_sweep_table.md](../outputs/runs/stage9_n20/paper_artifacts/paper_fallback_sweep_table.md) |
| Fallback sweep CSV | [fallback_threshold_sweep.csv](../outputs/runs/stage9_n20/fallback_threshold_sweep.csv) |
| Run progress | [run_progress.md](../outputs/runs/stage9_n20/run_progress.md) |

## Figures

| Figure | Path |
| --- | --- |
| Mean reward heatmap | [phase2_mean_reward.png](../outputs/runs/stage9_n20/figures/phase2_mean_reward.png) |
| Success rate heatmap | [phase2_success_rate.png](../outputs/runs/stage9_n20/figures/phase2_success_rate.png) |
| Mean energy heatmap | [phase2_mean_energy.png](../outputs/runs/stage9_n20/figures/phase2_mean_energy.png) |
| Mean time heatmap | [phase2_mean_time_s.png](../outputs/runs/stage9_n20/figures/phase2_mean_time_s.png) |
| Safety violations heatmap | [phase2_mean_safety_violations.png](../outputs/runs/stage9_n20/figures/phase2_mean_safety_violations.png) |
| Decision boundary | [decision_boundary.png](../outputs/runs/stage9_n20/figures/decision_boundary.png) |
