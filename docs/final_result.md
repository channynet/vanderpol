# Consolidated Final Result

- Generated at: `2026-06-15T04:44:05.554286+00:00`
- Runs considered: `71` paper-ready runs, `70` completed
- Selection rule: completed paper-ready run with the largest patients_per_scenario, then horizon_s, then noise profile count
- Primary evidence run: `stage9_n100_time2`
- Primary preset: `n100_time2`
- Patients per scenario: `100`
- Horizon: `30.0` seconds
- Noise profiles: `4`
- Fallback threshold configs: `12`

## Final Conclusion

The final manuscript-facing result should use the primary evidence run above, not the one-patient mutation runs, because it has the largest completed evaluation scale in the current workspace.

The simulator supports the main claim that scenario-specific electrical treatment choices differ across rhythm classes. The strongest scenario-level actions in the primary run are listed below. Clinical efficacy is not claimed; treatment success and safety are simulator outcomes.

## Versioned AI Model Results

Across 4 selector-evaluated versioned runs, the learned selector exceeds the ACLS-rule baseline on average, but not consistently.

- Versioned runs considered: `4`
- Selector-evaluated runs: `4`
- Runs where selector reward beats ACLS reward: `3/4`
- Average selector reward: `87.625`
- Average ACLS reward: `75.901`
- Average oracle reward: `98.311`
- Average reward delta vs ACLS: `11.725`
- Latest realism run: `v004_existing_rhythm_realism_mitdb_cudb`
- Latest realism mean SMD: `0.971`
- Latest realism mean KS: `0.482`
- Latest worst realism feature: `vt_vs_monomorphic_vt/sample_entropy`

v002-v004 were evaluated with the same n20 AI selector configuration, so their selector metrics are reproducible and match each other; their real-vs-synthetic rhythm validation differs by version.

| run_id | status | selector_reward | acls_reward | oracle_reward | selector_success | mean_smd | mean_ks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `v001_full_pipeline` | completed | 85.190 | 89.149 | 98.261 | 0.900 |  |  |
| `v002_existing_rhythm_realism_tuning` | completed | 88.437 | 71.485 | 98.328 | 0.933 | 1.307 | 0.555 |
| `v003_existing_rhythm_realism_tuning_pass2` | completed | 88.437 | 71.485 | 98.328 | 0.933 | 1.026 | 0.497 |
| `v004_existing_rhythm_realism_mitdb_cudb` | completed | 88.437 | 71.485 | 98.328 | 0.933 | 0.971 | 0.482 |


## Policy-Level Metrics

| policy | mean_reward | oracle_gap | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ACLS-rule baseline | 66.045 | 27.929 | 0.813 | 0.228 | 7.644 | 0.213 |
| Oracle | 93.974 | 0.000 | 0.980 | 0.320 | 2.013 | 0.260 |
| Always synchronized cardioversion | 15.808 | 78.166 | 0.480 | 0.300 | 16.096 | 0.567 |
| Always unsynchronized defibrillation | 31.304 | 62.671 | 0.580 | 0.686 | 13.348 | 0.560 |
| Always ATP | 1.738 | 92.236 | 0.407 | 0.080 | 19.464 | 0.833 |
| Always resonant drift | -9.608 | 103.582 | 0.353 | 0.029 | 22.470 | 0.447 |
| Always adaptive low-energy pacing | 45.370 | 48.604 | 0.693 | 0.032 | 11.981 | 0.200 |

## Scenario-Level Final Actions

| scenario | final_action | mean_reward | success_rate | mean_energy | mean_time_s | mean_safety_violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| monomorphic_vt | atp_burst_pacing | 90.283 | 0.990 | 0.080 | 4.359 | 0.000 |
| nsr | adaptive_low_energy_pacing | 90.650 | 0.990 | 0.026 | 4.175 | 1.200 |
| polymorphic_vt | unsynchronized_defibrillation | 76.955 | 0.870 | 0.686 | 5.022 | 0.000 |
| svt_flutter | synchronized_cardioversion | 93.196 | 0.970 | 0.300 | 1.902 | 0.130 |
| vf_like | unsynchronized_defibrillation | 91.123 | 0.960 | 0.686 | 2.438 | 0.000 |

## Calibration And Robustness

- Calibration checks: `8/8` pass, pass rate `1.000`
- Robustness profiles summarized: `4`

| profile | policy | mean_reward | oracle_gap | success_rate | mean_safety_violations |
| --- | --- | ---: | ---: | ---: | ---: |
| clean | acls_rule | 61.226 | 33.593 | 0.784 | 0.262 |
| clean | oracle | 94.819 | 0.000 | 0.988 | 0.310 |
| mild | acls_rule | 62.377 | 32.281 | 0.792 | 0.286 |
| mild | oracle | 94.658 | 0.000 | 0.988 | 0.330 |
| moderate | acls_rule | 66.378 | 28.227 | 0.818 | 0.346 |
| moderate | oracle | 94.605 | 0.000 | 0.988 | 0.442 |
| severe | acls_rule | 52.588 | 42.064 | 0.732 | 0.414 |
| severe | oracle | 94.652 | 0.000 | 0.990 | 0.640 |

## Included Runs

| run_id | status | patients_per_scenario | horizon_s | preset | paper_dir |
| --- | --- | ---: | ---: | --- | --- |
| `stage9_n100_time2` | completed | 100 | 30.0 | n100_time2 | `outputs\runs\stage9_n100_time2\paper_artifacts` |
| `stage9_n20_reward_vfpoly_lowenergy_20260520_143550` | completed | 20 | 30.0 | n20 | `outputs\runs\stage9_n20_reward_vfpoly_lowenergy_20260520_143550\paper_artifacts` |
| `stage9_n20` | completed | 20 | 30.0 | n20 | `outputs\runs\stage9_n20\paper_artifacts` |
| `codex_auto_mut_0064` | completed | 2 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0064\paper_artifacts` |
| `codex_auto_mut_0060` | completed | 2 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0060\paper_artifacts` |
| `codex_auto_mut_0056` | completed | 2 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0056\paper_artifacts` |
| `codex_auto_mut_0052` | completed | 2 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0052\paper_artifacts` |
| `codex_auto_mut_0048` | completed | 2 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0048\paper_artifacts` |
| `codex_auto_mut_0044` | completed | 2 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0044\paper_artifacts` |
| `codex_auto_mut_0040` | completed | 2 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0040\paper_artifacts` |
| `codex_auto_mut_0036` | completed | 2 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0036\paper_artifacts` |
| `codex_auto_mut_0032` | completed | 2 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0032\paper_artifacts` |
| `codex_auto_mut_0028` | completed | 2 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0028\paper_artifacts` |
| `codex_auto_mut_0024` | completed | 2 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0024\paper_artifacts` |
| `codex_auto_mut_0020` | completed | 2 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0020\paper_artifacts` |
| `codex_auto_mut_0016` | completed | 2 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0016\paper_artifacts` |
| `codex_auto_mut_0012` | completed | 2 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0012\paper_artifacts` |
| `codex_auto_mut_0008` | completed | 2 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0008\paper_artifacts` |
| `codex_auto_mut_0004` | completed | 2 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0004\paper_artifacts` |
| `codex_auto_mut_0066` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0066\paper_artifacts` |
| `codex_auto_mut_0065` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0065\paper_artifacts` |
| `codex_auto_mut_0063` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0063\paper_artifacts` |
| `codex_auto_mut_0062` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0062\paper_artifacts` |
| `codex_auto_mut_0061` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0061\paper_artifacts` |
| `codex_auto_mut_0058` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0058\paper_artifacts` |
| `codex_auto_mut_0057` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0057\paper_artifacts` |
| `codex_auto_mut_0055` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0055\paper_artifacts` |
| `codex_auto_mut_0054` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0054\paper_artifacts` |
| `codex_auto_mut_0053` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0053\paper_artifacts` |
| `codex_auto_mut_0051` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0051\paper_artifacts` |
| `codex_auto_mut_0050` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0050\paper_artifacts` |
| `codex_auto_mut_0049` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0049\paper_artifacts` |
| `codex_auto_mut_0047` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0047\paper_artifacts` |
| `codex_auto_mut_0046` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0046\paper_artifacts` |
| `codex_auto_mut_0045` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0045\paper_artifacts` |
| `codex_auto_mut_0043` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0043\paper_artifacts` |
| `codex_auto_mut_0042` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0042\paper_artifacts` |
| `codex_auto_mut_0041` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0041\paper_artifacts` |
| `codex_auto_mut_0039` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0039\paper_artifacts` |
| `codex_auto_mut_0038` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0038\paper_artifacts` |
| `codex_auto_mut_0037` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0037\paper_artifacts` |
| `codex_auto_mut_0035` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0035\paper_artifacts` |
| `codex_auto_mut_0034` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0034\paper_artifacts` |
| `codex_auto_mut_0033` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0033\paper_artifacts` |
| `codex_auto_mut_0031` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0031\paper_artifacts` |
| `codex_auto_mut_0030` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0030\paper_artifacts` |
| `codex_auto_mut_0029` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0029\paper_artifacts` |
| `codex_auto_mut_0027` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0027\paper_artifacts` |
| `codex_auto_mut_0026` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0026\paper_artifacts` |
| `codex_auto_mut_0025` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0025\paper_artifacts` |
| `codex_auto_mut_0023` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0023\paper_artifacts` |
| `codex_auto_mut_0022` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0022\paper_artifacts` |
| `codex_auto_mut_0021` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0021\paper_artifacts` |
| `codex_auto_mut_0019` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0019\paper_artifacts` |
| `codex_auto_mut_0018` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0018\paper_artifacts` |
| `codex_auto_mut_0017` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0017\paper_artifacts` |
| `codex_auto_mut_0015` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0015\paper_artifacts` |
| `codex_auto_mut_0014` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0014\paper_artifacts` |
| `codex_auto_mut_0013` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0013\paper_artifacts` |
| `codex_auto_mut_0011` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0011\paper_artifacts` |
| `codex_auto_mut_0010` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0010\paper_artifacts` |
| `codex_auto_mut_0009` | completed | 1 | 4.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0009\paper_artifacts` |
| `codex_auto_mut_0007` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0007\paper_artifacts` |
| `codex_auto_mut_0006` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0006\paper_artifacts` |
| `codex_auto_mut_0005` | completed | 1 | 5.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0005\paper_artifacts` |
| `codex_auto_mut_0003` | completed | 1 | 4.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0003\paper_artifacts` |
| `codex_auto_mut_0002` | completed | 1 | 3.5 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0002\paper_artifacts` |
| `codex_auto_mut_0001` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_mut_0001\paper_artifacts` |
| `codex_auto_test_0001` | completed | 1 | 3.0 | codex_auto_mutation | `outputs\runs\codex_auto_test_0001\paper_artifacts` |
| `codex_probe_smoke` | completed | 1 | 3.0 | smoke | `outputs\runs\codex_probe_smoke\paper_artifacts` |
| `stage8_smoke` | unknown | 1 | 3.0 | smoke | `outputs\runs\stage8_smoke\paper_artifacts` |

## Required Guardrail

This final result is a research-simulator result. External ECG data is used for feature/noise validation, while reward, success, and safety outcomes are generated by the simulator.
