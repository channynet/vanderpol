# v001 Figure Guide

All process figures are here:

- `outputs/versioned_runs/v001_full_pipeline/process_visualizations`

## Figure List

| Figure | Meaning | Main takeaway |
| --- | --- | --- |
| `00_pipeline_step_durations.png` | Runtime per pipeline step. | The slow parts are fallback sweep, selector stability, and noise/OOD sweep. |
| `01_phase2_core_metric_heatmaps.png` | Success, reward, and time by scenario and algorithm. | Different rhythms favor different algorithms. |
| `02_calibration_target_ranges.png` | Calibration target ranges vs observed values. | All configured checks pass. |
| `03_selector_policy_comparison.png` | Selector vs ACLS vs oracle vs fixed baselines. | Selector is below ACLS but above fixed baselines. |
| `04_decision_boundary_selector_vs_acls.png` | Selector and ACLS choices over QRS width/RR variability. | Selector over-selects adaptive pacing. |
| `05_bootstrap_best_reward_ci.png` | Bootstrap CI for best algorithm reward by scenario. | More samples would make estimates more stable. |
| `06_selector_stability_across_seeds.png` | Seed sensitivity. | Selector performance varies with seed. |
| `07_noise_ood_robustness.png` | Performance under noise. | Selector degrades under moderate/severe noise. |
| `08_fallback_threshold_sweep.png` | Conservative fallback threshold sweep. | Threshold fallback alone does not solve robustness. |

## Most Important Figures

For presentation, prioritize:

1. `01_phase2_core_metric_heatmaps.png`
2. `03_selector_policy_comparison.png`
3. `04_decision_boundary_selector_vs_acls.png`
4. `07_noise_ood_robustness.png`

## One-Slide Interpretation

The treatment matrix is meaningful because each rhythm has a different best
algorithm. However, the learned selector is not yet strong enough: it overuses
adaptive pacing and becomes weak under noise. This explains why ACLS still beats
the learned selector in the main `v001` result.
