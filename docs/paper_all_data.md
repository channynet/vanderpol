# Stage 9 n20 Paper Data Compendium

Run ID: `stage9_n20`
Source directory: `outputs/runs/stage9_n20/paper_artifacts`
Generated from paper artifact Markdown files.

## Included Sections

- Paper Summary: `outputs/runs/stage9_n20/paper_artifacts/paper_summary.md`
- Selector Policy Table: `outputs/runs/stage9_n20/paper_artifacts/paper_selector_table.md`
- Best Algorithm By Scenario: `outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_winners.md`
- Algorithm By Scenario Matrix: `outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_matrix_table.md`
- Calibration Checks: `outputs/runs/stage9_n20/paper_artifacts/paper_calibration_table.md`
- Noise And OOD Robustness: `outputs/runs/stage9_n20/paper_artifacts/paper_noise_robustness_table.md`
- Conservative Fallback Threshold Sweep: `outputs/runs/stage9_n20/paper_artifacts/paper_fallback_sweep_table.md`
- Evidence And Data Sources: `outputs/runs/stage9_n20/paper_artifacts/citations.md`
- Limitations And Guardrails: `outputs/runs/stage9_n20/paper_artifacts/limitations.md`

---

## Paper Summary

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_summary.md`

# Paper Artifact Summary

- Run ID: `stage9_n20`
- Preset: `n20`
- Patients per scenario: `20`
- Horizon: `30.0` seconds
- Generated artifacts: `17`

## Headline Selector Metrics

- Selector LinUCB: reward `84.914`, oracle gap `14.539`, success `0.867`
- ACLS-rule baseline: reward `91.456`, oracle gap `7.996`, success `0.933`
- Oracle: reward `99.452`, oracle gap `0.000`, success `1.000`

## Calibration

- Pass rate: `1.000`
- Checks: `8`

## Scenario Winners

- `monomorphic_vt`: `atp_burst_pacing` (reward `99.010`)
- `nsr`: `adaptive_low_energy_pacing` (reward `100.000`)
- `polymorphic_vt`: `unsynchronized_defibrillation` (reward `88.274`)
- `svt_flutter`: `synchronized_cardioversion` (reward `94.080`)
- `vf_like`: `unsynchronized_defibrillation` (reward `98.992`)

## Robustness Coverage

- Noise profiles: `4`

## Fallback Sweep Coverage

- Threshold configs: `12`

## Required Guardrails

- Simulation-only treatment outcomes
- Reduced-order heart model
- Dimensionless energy units
- Small real-data smoke samples

## Artifact Index

- `citations_md`: `outputs\runs\stage9_n20\paper_artifacts\citations.md`
- `limitations_md`: `outputs\runs\stage9_n20\paper_artifacts\limitations.md`
- `live_dashboard_html`: `outputs\runs\stage9_n20\paper_artifacts\live_dashboard.html`
- `paper_algorithm_matrix_table_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_algorithm_matrix_table.csv`
- `paper_algorithm_matrix_table_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_algorithm_matrix_table.md`
- `paper_algorithm_winners_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_algorithm_winners.csv`
- `paper_algorithm_winners_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_algorithm_winners.md`
- `paper_artifacts_manifest_json`: `outputs\runs\stage9_n20\paper_artifacts\paper_artifacts_manifest.json`
- `paper_calibration_table_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_calibration_table.csv`
- `paper_calibration_table_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_calibration_table.md`
- `paper_fallback_sweep_table_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_fallback_sweep_table.csv`
- `paper_fallback_sweep_table_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_fallback_sweep_table.md`
- `paper_noise_robustness_table_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_noise_robustness_table.csv`
- `paper_noise_robustness_table_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_noise_robustness_table.md`
- `paper_selector_table_csv`: `outputs\runs\stage9_n20\paper_artifacts\paper_selector_table.csv`
- `paper_selector_table_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_selector_table.md`
- `paper_summary_md`: `outputs\runs\stage9_n20\paper_artifacts\paper_summary.md`

---

## Selector Policy Table

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_selector_table.md`

# Selector Policy Summary

| policy | policy_id | mean_reward | oracle_gap | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Selector LinUCB | selector_linucb | 84.914 | 14.539 | 0.867 | 0.264 | 5.954 | 0.000 |
| ACLS-rule baseline | acls_rule | 91.456 | 7.996 | 0.933 | 0.295 | 3.661 | 0.033 |
| Oracle | oracle | 99.452 | 0.000 | 1.000 | 0.333 | 0.858 | 0.000 |
| Always synchronized cardioversion | always_synchronized_cardioversion | 36.488 | 62.964 | 0.500 | 0.300 | 15.514 | 0.467 |
| Always unsynchronized defibrillation | always_unsynchronized_defibrillation | 45.693 | 53.759 | 0.633 | 0.686 | 11.817 | 0.700 |
| Always ATP | always_atp | 17.040 | 82.413 | 0.400 | 0.080 | 19.522 | 0.900 |
| Always resonant drift | always_resonant_drift | 27.556 | 71.897 | 0.433 | 0.029 | 20.328 | 0.533 |
| Always adaptive low-energy pacing | always_adaptive | 70.660 | 28.792 | 0.733 | 0.033 | 10.561 | 0.000 |

---

## Best Algorithm By Scenario

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_winners.md`

# Best Algorithm By Scenario

| scenario | best_algorithm | mean_reward | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | --- | --- | --- | --- | --- |
| monomorphic_vt | atp_burst_pacing | 99.010 | 1.000 | 0.080 | 3.639 | 0.000 |
| nsr | adaptive_low_energy_pacing | 100.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| polymorphic_vt | unsynchronized_defibrillation | 88.274 | 0.900 | 0.686 | 4.161 | 0.000 |
| svt_flutter | synchronized_cardioversion | 94.080 | 0.950 | 0.300 | 2.478 | 0.000 |
| vf_like | unsynchronized_defibrillation | 98.992 | 1.000 | 0.686 | 1.290 | 0.000 |

---

## Algorithm By Scenario Matrix

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_algorithm_matrix_table.md`

# Algorithm By Scenario Matrix

| scenario | algorithm | mean_reward | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | --- | --- | --- | --- | --- |
| nsr | synchronized_cardioversion | -47.800 | 0.000 | 0.300 | 30.000 | 2.000 |
| nsr | unsynchronized_defibrillation | -68.186 | 0.000 | 0.686 | 30.000 | 3.000 |
| nsr | atp_burst_pacing | -42.262 | 0.050 | 0.080 | 28.728 | 2.000 |
| nsr | resonant_drift_pacing | -47.529 | 0.000 | 0.029 | 30.000 | 2.000 |
| nsr | adaptive_low_energy_pacing | 100.000 | 1.000 | 0.000 | 0.000 | 0.000 |
| svt_flutter | synchronized_cardioversion | 94.080 | 0.950 | 0.300 | 2.478 | 0.000 |
| svt_flutter | unsynchronized_defibrillation | 66.838 | 0.700 | 0.686 | 9.903 | 0.000 |
| svt_flutter | atp_burst_pacing | 77.650 | 0.800 | 0.080 | 9.079 | 0.000 |
| svt_flutter | resonant_drift_pacing | 55.734 | 0.600 | 0.029 | 16.946 | 0.000 |
| svt_flutter | adaptive_low_energy_pacing | 66.820 | 0.700 | 0.043 | 12.549 | 0.000 |
| monomorphic_vt | synchronized_cardioversion | 88.719 | 0.900 | 0.300 | 3.924 | 0.000 |
| monomorphic_vt | unsynchronized_defibrillation | 77.556 | 0.800 | 0.686 | 7.032 | 0.000 |
| monomorphic_vt | atp_burst_pacing | 99.010 | 1.000 | 0.080 | 3.639 | 0.000 |
| monomorphic_vt | resonant_drift_pacing | 92.801 | 0.950 | 0.029 | 8.679 | 0.000 |
| monomorphic_vt | adaptive_low_energy_pacing | 98.741 | 1.000 | 0.043 | 4.867 | 0.000 |
| polymorphic_vt | synchronized_cardioversion | 35.097 | 0.400 | 0.300 | 18.412 | 0.000 |
| polymorphic_vt | unsynchronized_defibrillation | 88.274 | 0.900 | 0.686 | 4.161 | 0.000 |
| polymorphic_vt | atp_burst_pacing | -30.262 | 0.050 | 0.080 | 28.728 | 1.400 |
| polymorphic_vt | resonant_drift_pacing | 37.317 | 0.500 | 0.029 | 18.616 | 0.400 |
| polymorphic_vt | adaptive_low_energy_pacing | 24.317 | 0.300 | 0.043 | 22.562 | 0.000 |
| vf_like | synchronized_cardioversion | -2.438 | 0.050 | 0.300 | 28.552 | 0.000 |
| vf_like | unsynchronized_defibrillation | 98.992 | 1.000 | 0.686 | 1.290 | 0.000 |
| vf_like | atp_burst_pacing | -27.580 | 0.000 | 0.080 | 30.000 | 1.000 |
| vf_like | resonant_drift_pacing | 3.107 | 0.100 | 0.029 | 27.457 | 0.000 |
| vf_like | adaptive_low_energy_pacing | 13.703 | 0.200 | 0.043 | 25.018 | 0.000 |

---

## Calibration Checks

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_calibration_table.md`

# Calibration Checks

| scenario | algorithm | metric | value | target_min | target_max | status | source | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| svt_flutter | synchronized_cardioversion | success_rate | 0.950 | 0.750 | 0.980 | pass | AHA ACLS tachyarrhythmia guidance | Unstable tachycardia and organized tachyarrhythmia electrical therapy anchor. |
| monomorphic_vt | atp_burst_pacing | success_rate | 1.000 | 0.750 | 1.000 | pass | ICD/ATP ventricular tachycardia literature | Monomorphic VT ATP should terminate most simulated regular VT episodes. |
| polymorphic_vt | atp_burst_pacing | success_rate | 0.050 | 0.000 | 0.250 | pass | ICD/ATP ventricular tachycardia literature | Irregular polymorphic rhythm is modeled as a poor ATP target. |
| vf_like | unsynchronized_defibrillation | success_rate | 1.000 | 0.750 | 1.000 | pass | AHA ACLS shockable rhythm guidance | VF-like rhythm should favor unsynchronized high-energy shock. |
| vf_like | synchronized_cardioversion | success_rate | 0.050 | 0.000 | 0.200 | pass | AHA ACLS tachyarrhythmia guidance | VF-like rhythm has no stable R-wave sync target in this simulator. |
| monomorphic_vt | resonant_drift_pacing | energy_ratio_vs_unsync_defibrillation | 0.043 | 0.000 | 0.200 | pass | Morgan/Biktashev resonant-drift simulation work | Low-energy feedback pacing should use a small fraction of defibrillation energy. |
| vf_like | resonant_drift_pacing | success_rate | 0.100 | 0.000 | 0.350 | pass | Morgan/Biktashev resonant-drift simulation work | Chaotic VF-like signals remain difficult for phase-based pacing. |
| nsr | adaptive_low_energy_pacing | success_rate | 1.000 | 0.950 | 1.000 | pass | Safety default | Normal rhythm should be recognized and stimulation withheld. |

---

## Noise And OOD Robustness

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_noise_robustness_table.md`

# Noise And OOD Robustness

| profile | policy | policy_id | n_contexts | mean_reward | oracle_gap | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clean | ACLS-rule baseline | acls_rule | 100 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| clean | Always adaptive low-energy pacing | always_adaptive | 100 | 60.716 | 38.685 | 0.640 | 0.034 | 12.999 | 0.000 |
| clean | Always unsynchronized defibrillation | always_unsynchronized_defibrillation | 100 | 52.695 | 46.706 | 0.680 | 0.686 | 10.477 | 0.600 |
| clean | Oracle | oracle | 100 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| clean | Selector LinUCB | selector_linucb | 100 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| mild | ACLS-rule baseline | acls_rule | 100 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| mild | Always adaptive low-energy pacing | always_adaptive | 100 | 60.720 | 38.681 | 0.640 | 0.034 | 12.986 | 0.000 |
| mild | Always unsynchronized defibrillation | always_unsynchronized_defibrillation | 100 | 52.695 | 46.706 | 0.680 | 0.686 | 10.477 | 0.600 |
| mild | Oracle | oracle | 100 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| mild | Selector LinUCB | selector_linucb | 100 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| moderate | ACLS-rule baseline | acls_rule | 100 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| moderate | Always adaptive low-energy pacing | always_adaptive | 100 | 60.315 | 38.679 | 0.640 | 0.034 | 13.002 | 0.020 |
| moderate | Always unsynchronized defibrillation | always_unsynchronized_defibrillation | 100 | 52.695 | 46.299 | 0.680 | 0.686 | 10.477 | 0.600 |
| moderate | Oracle | oracle | 100 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| moderate | Selector LinUCB | selector_linucb | 100 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| severe | ACLS-rule baseline | acls_rule | 100 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| severe | Always adaptive low-energy pacing | always_adaptive | 100 | 55.889 | 39.558 | 0.630 | 0.037 | 13.895 | 0.180 |
| severe | Always unsynchronized defibrillation | always_unsynchronized_defibrillation | 100 | 52.495 | 42.953 | 0.680 | 0.686 | 10.477 | 0.610 |
| severe | Oracle | oracle | 100 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| severe | Selector LinUCB | selector_linucb | 100 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |

---

## Conservative Fallback Threshold Sweep

Source: `outputs/runs/stage9_n20/paper_artifacts/paper_fallback_sweep_table.md`

# Conservative Fallback Threshold Sweep

| min_signal_quality | high_entropy_threshold | high_rr_cv_threshold | profile | policy | policy_id | n_contexts | fallback_reasons | mean_reward | oracle_gap | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.300 | 0.550 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.300 | 0.550 | 0.250 | clean | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.550 | 0.250 | clean | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.550 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.550 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.300 | 0.550 | 0.250 | mild | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.550 | 0.250 | mild | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.550 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.550 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.300 | 0.550 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.550 | 0.250 | moderate | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.550 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.300 | 0.550 | 0.250 | severe | Conservative selector | conservative_selector | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.550 | 0.250 | severe | Oracle | oracle | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.300 | 0.550 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.550 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.300 | 0.550 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.550 | 0.250 | real_estimated | Oracle | oracle | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.300 | 0.550 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.550 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.550 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.250 | real_asystole | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.550 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.550 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.550 | 0.250 | real_bradycardia | Oracle | oracle | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.550 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.550 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.550 | 0.250 | real_tachycardia | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.550 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.300 | 0.550 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.550 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.300 | 0.550 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.550 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.550 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.550 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.300 | 0.550 | 0.300 | clean | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.550 | 0.300 | clean | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.550 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.550 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.300 | 0.550 | 0.300 | mild | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.550 | 0.300 | mild | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.550 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.550 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.300 | 0.550 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.550 | 0.300 | moderate | Oracle | oracle | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.550 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.300 | 0.550 | 0.300 | severe | Conservative selector | conservative_selector | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.550 | 0.300 | severe | Oracle | oracle | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.300 | 0.550 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.550 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.300 | 0.550 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.550 | 0.300 | real_estimated | Oracle | oracle | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.300 | 0.550 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.550 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.550 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.300 | real_asystole | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.550 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.550 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.550 | 0.300 | real_bradycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.550 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.550 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.550 | 0.300 | real_tachycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.550 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.550 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.300 | 0.550 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.550 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.300 | 0.550 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.550 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.550 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.550 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.550 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.300 | 0.620 | 0.250 | clean | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.620 | 0.250 | clean | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.620 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.620 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.300 | 0.620 | 0.250 | mild | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.620 | 0.250 | mild | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.620 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.620 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.300 | 0.620 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.620 | 0.250 | moderate | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.620 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.300 | 0.620 | 0.250 | severe | Conservative selector | conservative_selector | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.620 | 0.250 | severe | Oracle | oracle | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.300 | 0.620 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.620 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.300 | 0.620 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.620 | 0.250 | real_estimated | Oracle | oracle | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.300 | 0.620 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.620 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.620 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.250 | real_asystole | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.620 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.620 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.620 | 0.250 | real_bradycardia | Oracle | oracle | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.620 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.620 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.620 | 0.250 | real_tachycardia | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.620 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.300 | 0.620 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.620 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.300 | 0.620 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.620 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.620 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.620 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.300 | 0.620 | 0.300 | clean | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.620 | 0.300 | clean | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.620 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.300 | 0.620 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.300 | 0.620 | 0.300 | mild | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.620 | 0.300 | mild | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.300 | 0.620 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.300 | 0.620 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.300 | 0.620 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.620 | 0.300 | moderate | Oracle | oracle | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.300 | 0.620 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.300 | 0.620 | 0.300 | severe | Conservative selector | conservative_selector | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.620 | 0.300 | severe | Oracle | oracle | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.300 | 0.620 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.300 | 0.620 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.300 | 0.620 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.620 | 0.300 | real_estimated | Oracle | oracle | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.300 | 0.620 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.300 | 0.620 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.620 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.300 | real_asystole | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.620 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.620 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.620 | 0.300 | real_bradycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.300 | 0.620 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.300 | 0.620 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.620 | 0.300 | real_tachycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.300 | 0.620 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.300 | 0.620 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.300 | 0.620 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.620 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.300 | 0.620 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.300 | 0.620 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.300 | 0.620 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.300 | 0.620 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.300 | 0.620 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.420 | 0.550 | 0.250 | clean | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.550 | 0.250 | clean | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.550 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.550 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.420 | 0.550 | 0.250 | mild | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.550 | 0.250 | mild | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.550 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.550 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.420 | 0.550 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.550 | 0.250 | moderate | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.550 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.420 | 0.550 | 0.250 | severe | Conservative selector | conservative_selector | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.550 | 0.250 | severe | Oracle | oracle | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.420 | 0.550 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.550 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.420 | 0.550 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.550 | 0.250 | real_estimated | Oracle | oracle | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.420 | 0.550 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.550 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.550 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.250 | real_asystole | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.550 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.550 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.550 | 0.250 | real_bradycardia | Oracle | oracle | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.550 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.550 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.550 | 0.250 | real_tachycardia | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.550 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.420 | 0.550 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.550 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.420 | 0.550 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.550 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.550 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.550 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.420 | 0.550 | 0.300 | clean | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.550 | 0.300 | clean | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.550 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.550 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.420 | 0.550 | 0.300 | mild | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.550 | 0.300 | mild | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.550 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.550 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.420 | 0.550 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.550 | 0.300 | moderate | Oracle | oracle | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.550 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.420 | 0.550 | 0.300 | severe | Conservative selector | conservative_selector | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.550 | 0.300 | severe | Oracle | oracle | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.420 | 0.550 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | model=85; normal_withhold=4; shockable_chaotic=11 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.550 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.420 | 0.550 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.550 | 0.300 | real_estimated | Oracle | oracle | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.420 | 0.550 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.550 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.550 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.300 | real_asystole | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.550 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.550 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.550 | 0.300 | real_bradycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.550 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.550 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.550 | 0.300 | real_tachycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.550 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.550 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.420 | 0.550 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.550 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.420 | 0.550 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.550 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.550 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.550 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.550 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.420 | 0.620 | 0.250 | clean | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.620 | 0.250 | clean | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.620 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.620 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.420 | 0.620 | 0.250 | mild | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.620 | 0.250 | mild | Oracle | oracle | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.620 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.620 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.420 | 0.620 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.620 | 0.250 | moderate | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.620 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.420 | 0.620 | 0.250 | severe | Conservative selector | conservative_selector | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.620 | 0.250 | severe | Oracle | oracle | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.420 | 0.620 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | model=84; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.620 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.420 | 0.620 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.620 | 0.250 | real_estimated | Oracle | oracle | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.420 | 0.620 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.620 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.620 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.250 | real_asystole | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.620 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.620 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.620 | 0.250 | real_bradycardia | Oracle | oracle | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=67; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.620 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.620 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.620 | 0.250 | real_tachycardia | Oracle | oracle | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=68; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.620 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.420 | 0.620 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.620 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.420 | 0.620 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.620 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.620 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.620 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=71; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.420 | 0.620 | 0.300 | clean | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.620 | 0.300 | clean | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.620 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.420 | 0.620 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.420 | 0.620 | 0.300 | mild | Conservative selector | conservative_selector | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.620 | 0.300 | mild | Oracle | oracle | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.420 | 0.620 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | model=73; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.420 | 0.620 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.420 | 0.620 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.620 | 0.300 | moderate | Oracle | oracle | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | model=72; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.420 | 0.620 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.420 | 0.620 | 0.300 | severe | Conservative selector | conservative_selector | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.620 | 0.300 | severe | Oracle | oracle | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.420 | 0.620 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | model=88; normal_withhold=4; shockable_chaotic=8 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.420 | 0.620 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.420 | 0.620 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.620 | 0.300 | real_estimated | Oracle | oracle | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.420 | 0.620 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | model=79; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.420 | 0.620 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.620 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.300 | real_asystole | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.620 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.620 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.620 | 0.300 | real_bradycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.420 | 0.620 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.420 | 0.620 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.620 | 0.300 | real_tachycardia | Oracle | oracle | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.420 | 0.620 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | model=74; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.420 | 0.620 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.420 | 0.620 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.620 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.420 | 0.620 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | model=80; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.420 | 0.620 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.420 | 0.620 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.420 | 0.620 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.420 | 0.620 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | model=78; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.550 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.500 | 0.550 | 0.250 | clean | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 88.320 | 11.081 | 0.900 | 0.338 | 4.569 | 0.010 |
| 0.500 | 0.550 | 0.250 | clean | Oracle | oracle | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.550 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.500 | 0.550 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.500 | 0.550 | 0.250 | mild | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 87.265 | 12.136 | 0.890 | 0.347 | 4.752 | 0.010 |
| 0.500 | 0.550 | 0.250 | mild | Oracle | oracle | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.550 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.500 | 0.550 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.500 | 0.550 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 85.954 | 13.040 | 0.880 | 0.418 | 4.912 | 0.020 |
| 0.500 | 0.550 | 0.250 | moderate | Oracle | oracle | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.500 | 0.550 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.500 | 0.550 | 0.250 | severe | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 76.627 | 18.821 | 0.830 | 0.436 | 6.948 | 0.210 |
| 0.500 | 0.550 | 0.250 | severe | Oracle | oracle | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.500 | 0.550 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.500 | 0.550 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.500 | 0.550 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 82.998 | 14.328 | 0.870 | 0.442 | 5.439 | 0.110 |
| 0.500 | 0.550 | 0.250 | real_estimated | Oracle | oracle | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.500 | 0.550 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.500 | 0.550 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.550 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 83.415 | 14.328 | 0.870 | 0.442 | 5.372 | 0.090 |
| 0.500 | 0.550 | 0.250 | real_asystole | Oracle | oracle | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.550 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.550 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.550 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 87.884 | 11.110 | 0.900 | 0.428 | 4.351 | 0.030 |
| 0.500 | 0.550 | 0.250 | real_bradycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.500 | 0.550 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.550 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 89.144 | 9.850 | 0.910 | 0.426 | 4.120 | 0.020 |
| 0.500 | 0.550 | 0.250 | real_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.500 | 0.550 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.500 | 0.550 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 81.318 | 15.591 | 0.860 | 0.455 | 5.706 | 0.140 |
| 0.500 | 0.550 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.500 | 0.550 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.500 | 0.550 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.550 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 84.492 | 13.251 | 0.880 | 0.438 | 5.083 | 0.090 |
| 0.500 | 0.550 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.550 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.550 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.500 | 0.550 | 0.300 | clean | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 88.320 | 11.081 | 0.900 | 0.338 | 4.569 | 0.010 |
| 0.500 | 0.550 | 0.300 | clean | Oracle | oracle | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.550 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.500 | 0.550 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.500 | 0.550 | 0.300 | mild | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 87.265 | 12.136 | 0.890 | 0.347 | 4.752 | 0.010 |
| 0.500 | 0.550 | 0.300 | mild | Oracle | oracle | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.550 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.500 | 0.550 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.500 | 0.550 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 85.954 | 13.040 | 0.880 | 0.418 | 4.912 | 0.020 |
| 0.500 | 0.550 | 0.300 | moderate | Oracle | oracle | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.500 | 0.550 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=2; model=83; normal_withhold=4; shockable_chaotic=11 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.500 | 0.550 | 0.300 | severe | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=2; model=83; normal_withhold=4; shockable_chaotic=11 | 76.627 | 18.821 | 0.830 | 0.436 | 6.948 | 0.210 |
| 0.500 | 0.550 | 0.300 | severe | Oracle | oracle | 100 | low_signal_quality_acls=2; model=83; normal_withhold=4; shockable_chaotic=11 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.500 | 0.550 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=2; model=83; normal_withhold=4; shockable_chaotic=11 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.500 | 0.550 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.500 | 0.550 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 82.998 | 14.328 | 0.870 | 0.442 | 5.439 | 0.110 |
| 0.500 | 0.550 | 0.300 | real_estimated | Oracle | oracle | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.500 | 0.550 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.500 | 0.550 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.550 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 83.415 | 14.328 | 0.870 | 0.442 | 5.372 | 0.090 |
| 0.500 | 0.550 | 0.300 | real_asystole | Oracle | oracle | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.550 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.550 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.550 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 87.884 | 11.110 | 0.900 | 0.428 | 4.351 | 0.030 |
| 0.500 | 0.550 | 0.300 | real_bradycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.500 | 0.550 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.550 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 89.144 | 9.850 | 0.910 | 0.426 | 4.120 | 0.020 |
| 0.500 | 0.550 | 0.300 | real_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.550 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.500 | 0.550 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.500 | 0.550 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 81.318 | 15.591 | 0.860 | 0.455 | 5.706 | 0.140 |
| 0.500 | 0.550 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.500 | 0.550 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.500 | 0.550 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.550 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 84.492 | 13.251 | 0.880 | 0.438 | 5.083 | 0.090 |
| 0.500 | 0.550 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.550 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.620 | 0.250 | clean | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.500 | 0.620 | 0.250 | clean | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 88.320 | 11.081 | 0.900 | 0.338 | 4.569 | 0.010 |
| 0.500 | 0.620 | 0.250 | clean | Oracle | oracle | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.620 | 0.250 | clean | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=24; model=43; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.500 | 0.620 | 0.250 | mild | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.500 | 0.620 | 0.250 | mild | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 87.265 | 12.136 | 0.890 | 0.347 | 4.752 | 0.010 |
| 0.500 | 0.620 | 0.250 | mild | Oracle | oracle | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.620 | 0.250 | mild | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=26; model=41; normal_withhold=20; shockable_chaotic=13 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.500 | 0.620 | 0.250 | moderate | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.500 | 0.620 | 0.250 | moderate | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 85.954 | 13.040 | 0.880 | 0.418 | 4.912 | 0.020 |
| 0.500 | 0.620 | 0.250 | moderate | Oracle | oracle | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.250 | moderate | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=16; model=52; normal_withhold=18; shockable_chaotic=14 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.500 | 0.620 | 0.250 | severe | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.500 | 0.620 | 0.250 | severe | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 76.627 | 18.821 | 0.830 | 0.436 | 6.948 | 0.210 |
| 0.500 | 0.620 | 0.250 | severe | Oracle | oracle | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.500 | 0.620 | 0.250 | severe | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=2; model=82; normal_withhold=4; shockable_chaotic=12 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.500 | 0.620 | 0.250 | real_estimated | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.500 | 0.620 | 0.250 | real_estimated | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 82.998 | 14.328 | 0.870 | 0.442 | 5.439 | 0.110 |
| 0.500 | 0.620 | 0.250 | real_estimated | Oracle | oracle | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.500 | 0.620 | 0.250 | real_estimated | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=60; normal_withhold=13; shockable_chaotic=15 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.500 | 0.620 | 0.250 | real_asystole | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.620 | 0.250 | real_asystole | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 83.415 | 14.328 | 0.870 | 0.442 | 5.372 | 0.090 |
| 0.500 | 0.620 | 0.250 | real_asystole | Oracle | oracle | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.620 | 0.250 | real_asystole | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=59; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.620 | 0.250 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.620 | 0.250 | real_bradycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 87.884 | 11.110 | 0.900 | 0.428 | 4.351 | 0.030 |
| 0.500 | 0.620 | 0.250 | real_bradycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.250 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=54; normal_withhold=18; shockable_chaotic=15 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.500 | 0.620 | 0.250 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.620 | 0.250 | real_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 89.144 | 9.850 | 0.910 | 0.426 | 4.120 | 0.020 |
| 0.500 | 0.620 | 0.250 | real_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.250 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=56; normal_withhold=18; shockable_chaotic=14 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.500 | 0.620 | 0.250 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.500 | 0.620 | 0.250 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 81.318 | 15.591 | 0.860 | 0.455 | 5.706 | 0.140 |
| 0.500 | 0.620 | 0.250 | real_ventricular_flutter_fib | Oracle | oracle | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.500 | 0.620 | 0.250 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=61; normal_withhold=12; shockable_chaotic=15 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.500 | 0.620 | 0.250 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.620 | 0.250 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 84.492 | 13.251 | 0.880 | 0.438 | 5.083 | 0.090 |
| 0.500 | 0.620 | 0.250 | real_ventricular_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.620 | 0.250 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=58; normal_withhold=14; shockable_chaotic=15 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.620 | 0.300 | clean | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 83.903 | 15.498 | 0.860 | 0.290 | 5.631 | 0.020 |
| 0.500 | 0.620 | 0.300 | clean | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 88.320 | 11.081 | 0.900 | 0.338 | 4.569 | 0.010 |
| 0.500 | 0.620 | 0.300 | clean | Oracle | oracle | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.620 | 0.300 | clean | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=24; model=49; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.321 | 5.435 | 0.000 |
| 0.500 | 0.620 | 0.300 | mild | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 83.510 | 15.891 | 0.860 | 0.294 | 5.585 | 0.040 |
| 0.500 | 0.620 | 0.300 | mild | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 87.265 | 12.136 | 0.890 | 0.347 | 4.752 | 0.010 |
| 0.500 | 0.620 | 0.300 | mild | Oracle | oracle | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 99.401 | 0.000 | 1.000 | 0.359 | 0.959 | 0.000 |
| 0.500 | 0.620 | 0.300 | mild | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=26; model=47; normal_withhold=20; shockable_chaotic=7 | 86.320 | 13.081 | 0.880 | 0.346 | 5.336 | 0.000 |
| 0.500 | 0.620 | 0.300 | moderate | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 86.495 | 12.499 | 0.890 | 0.338 | 4.669 | 0.050 |
| 0.500 | 0.620 | 0.300 | moderate | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 85.954 | 13.040 | 0.880 | 0.418 | 4.912 | 0.020 |
| 0.500 | 0.620 | 0.300 | moderate | Oracle | oracle | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.300 | moderate | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=16; model=56; normal_withhold=18; shockable_chaotic=10 | 83.777 | 15.217 | 0.860 | 0.427 | 5.583 | 0.020 |
| 0.500 | 0.620 | 0.300 | severe | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=2; model=86; normal_withhold=4; shockable_chaotic=8 | 82.462 | 12.986 | 0.880 | 0.353 | 5.540 | 0.190 |
| 0.500 | 0.620 | 0.300 | severe | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=2; model=86; normal_withhold=4; shockable_chaotic=8 | 76.627 | 18.821 | 0.830 | 0.436 | 6.948 | 0.210 |
| 0.500 | 0.620 | 0.300 | severe | Oracle | oracle | 100 | low_signal_quality_acls=2; model=86; normal_withhold=4; shockable_chaotic=8 | 95.447 | 0.000 | 1.000 | 0.369 | 1.534 | 0.190 |
| 0.500 | 0.620 | 0.300 | severe | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=2; model=86; normal_withhold=4; shockable_chaotic=8 | 77.692 | 17.756 | 0.840 | 0.443 | 6.661 | 0.210 |
| 0.500 | 0.620 | 0.300 | real_estimated | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 85.713 | 11.613 | 0.900 | 0.318 | 4.676 | 0.140 |
| 0.500 | 0.620 | 0.300 | real_estimated | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 82.998 | 14.328 | 0.870 | 0.442 | 5.439 | 0.110 |
| 0.500 | 0.620 | 0.300 | real_estimated | Oracle | oracle | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 97.326 | 0.000 | 1.000 | 0.354 | 1.278 | 0.100 |
| 0.500 | 0.620 | 0.300 | real_estimated | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=67; normal_withhold=13; shockable_chaotic=8 | 80.437 | 16.889 | 0.850 | 0.461 | 6.009 | 0.130 |
| 0.500 | 0.620 | 0.300 | real_asystole | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.620 | 0.300 | real_asystole | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 83.415 | 14.328 | 0.870 | 0.442 | 5.372 | 0.090 |
| 0.500 | 0.620 | 0.300 | real_asystole | Oracle | oracle | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.620 | 0.300 | real_asystole | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=66; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |
| 0.500 | 0.620 | 0.300 | real_bradycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.620 | 0.300 | real_bradycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 87.884 | 11.110 | 0.900 | 0.428 | 4.351 | 0.030 |
| 0.500 | 0.620 | 0.300 | real_bradycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.300 | real_bradycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=61; normal_withhold=18; shockable_chaotic=8 | 84.633 | 14.361 | 0.870 | 0.440 | 5.309 | 0.030 |
| 0.500 | 0.620 | 0.300 | real_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 89.711 | 9.284 | 0.920 | 0.316 | 3.893 | 0.050 |
| 0.500 | 0.620 | 0.300 | real_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 89.144 | 9.850 | 0.910 | 0.426 | 4.120 | 0.020 |
| 0.500 | 0.620 | 0.300 | real_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 98.994 | 0.000 | 1.000 | 0.353 | 1.013 | 0.020 |
| 0.500 | 0.620 | 0.300 | real_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=62; normal_withhold=18; shockable_chaotic=8 | 85.898 | 13.097 | 0.880 | 0.433 | 5.076 | 0.020 |
| 0.500 | 0.620 | 0.300 | real_ventricular_flutter_fib | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 85.296 | 11.613 | 0.900 | 0.318 | 4.742 | 0.160 |
| 0.500 | 0.620 | 0.300 | real_ventricular_flutter_fib | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 81.318 | 15.591 | 0.860 | 0.455 | 5.706 | 0.140 |
| 0.500 | 0.620 | 0.300 | real_ventricular_flutter_fib | Oracle | oracle | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 96.909 | 0.000 | 1.000 | 0.355 | 1.345 | 0.120 |
| 0.500 | 0.620 | 0.300 | real_ventricular_flutter_fib | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=12; model=68; normal_withhold=12; shockable_chaotic=8 | 78.757 | 18.152 | 0.840 | 0.474 | 6.276 | 0.160 |
| 0.500 | 0.620 | 0.300 | real_ventricular_tachycardia | ACLS-rule baseline | acls_rule | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 86.130 | 11.613 | 0.900 | 0.317 | 4.609 | 0.120 |
| 0.500 | 0.620 | 0.300 | real_ventricular_tachycardia | Conservative selector | conservative_selector | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 84.492 | 13.251 | 0.880 | 0.438 | 5.083 | 0.090 |
| 0.500 | 0.620 | 0.300 | real_ventricular_tachycardia | Oracle | oracle | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 97.743 | 0.000 | 1.000 | 0.354 | 1.212 | 0.080 |
| 0.500 | 0.620 | 0.300 | real_ventricular_tachycardia | Selector LinUCB | selector_linucb | 100 | low_signal_quality_acls=13; model=65; normal_withhold=14; shockable_chaotic=8 | 80.854 | 16.889 | 0.850 | 0.460 | 5.943 | 0.110 |

---

## Evidence And Data Sources

Source: `outputs/runs/stage9_n20/paper_artifacts/citations.md`

# Evidence And Data Sources

## Gois-Savi coupled oscillator heart rhythm model

- ID: `gois_savi_2009`
- Type: `simulator_model`
- Phase: `Phase 1`
- URL: https://ideas.repec.org/a/eee/chsofr/v41y2009i5p2553-2565.html
- Role: Reduced-order oscillator reference for the simulator environment.

## MIT-BIH Arrhythmia Database

- ID: `mitdb`
- Type: `external_ecg`
- Phase: `Phase 3`
- URL: https://physionet.org/content/mitdb/1.0.0/
- Role: Annotated arrhythmia morphology and R/RR/QRS feature validation.

## Creighton University Ventricular Tachyarrhythmia Database

- ID: `cudb`
- Type: `external_ecg`
- Phase: `Phase 3`
- URL: https://physionet.org/content/cudb/1.0.0/
- Role: Sustained VT, ventricular flutter, and VF-like waveform validation.

## PhysioNet/CinC Challenge 2015

- ID: `challenge_2015`
- Type: `external_ecg_noise`
- Phase: `Phase 5`
- URL: https://physionet.org/content/challenge-2015/1.0.0/
- Role: ICU alarm-like noisy ECG and false-alarm robustness checks.

## PTB-XL ECG dataset

- ID: `ptb_xl`
- Type: `optional_pretraining`
- Phase: `Phase 3 extension`
- URL: https://physionet.org/content/ptb-xl/1.0.3/
- Role: Optional large-scale ECG encoder pretraining source.

## AHA Adult Advanced Life Support and tachyarrhythmia algorithms

- ID: `aha_acls_2025`
- Type: `guideline_anchor`
- Phase: `Phase 4`
- URL: https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/adult-advanced-life-support/
- Role: ACLS-style baseline thresholds and electrical cardioversion rule anchors.

## ICD anti-tachycardia pacing literature anchor

- ID: `atp_icd_anchor`
- Type: `calibration_anchor`
- Phase: `Phase 2`
- URL: https://pubmed.ncbi.nlm.nih.gov/20525727/
- Role: Monomorphic VT ATP success-rate target range for simulator calibration.

## Morgan/Biktashev resonant drift low-energy defibrillation simulation

- ID: `morgan_biktashev_2008`
- Type: `calibration_anchor`
- Phase: `Phase 2`
- URL: https://arxiv.org/abs/0805.0223
- Role: Low-energy phase-feedback pacing energy-scale calibration.

---

## Limitations And Guardrails

Source: `outputs/runs/stage9_n20/paper_artifacts/limitations.md`

# Limitations And Guardrails

## Simulation-only treatment outcomes

Treatment success, failure, reward, and safety penalties are generated by the simulator, not learned from patient treatment outcomes.

Mitigation: State this clearly in every report and use external ECG data only for observation realism, feature validation, and noise stress testing.

## Reduced-order heart model

The Gois-Savi/Van der Pol environment is a control-policy test bed, not a full electrophysiology tissue model.

Mitigation: Report it as a toy to medium-fidelity simulator and avoid claims about direct clinical efficacy.

## Dimensionless energy units

Simulation pulse amplitudes and energy are dimensionless unless a separate mapping to device Joules is introduced.

Mitigation: Use energy comparisons only as relative within-simulator trade-offs.

## Small real-data smoke samples

The included local external ECG samples are enough for pipeline validation but not for definitive ECG encoder validation.

Mitigation: Use the n20 or full bundle with larger downloaded PhysioNet subsets before making quantitative claims.

## Simplified ACLS baseline

The ACLS-style baseline encodes selected rhythm thresholds and electrical treatment ideas, not the full clinical algorithm with drugs, sedation, or expert judgment.

Mitigation: Describe it as a rule baseline rather than a complete ACLS implementation.

## Not a clinical decision tool

The selector is a research simulator artifact and must not be used for patient care.

Mitigation: Keep this disclaimer in generated summaries, documentation, and paper draft artifacts.

---
