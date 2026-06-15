# Start Here

## What This Project Is

This is a simulation research repo for choosing one electrical stimulation
strategy from a short ECG observation window.

It is not a clinical decision tool.

The current model observes a short ECG window, extracts ECG features, and
chooses one of five actions:

| ID | Action |
| ---: | --- |
| 0 | Synchronized cardioversion |
| 1 | Unsynchronized defibrillation |
| 2 | ATP burst pacing |
| 3 | Resonant drift pacing |
| 4 | Adaptive low-energy pacing |

## Current Shared Result

The current dashboard-facing result is:

- [`final_result.md`](final_result.md)
- Primary evidence run: `outputs/runs/stage9_n100_time2`
- Run set: `71` paper-ready runs, `70` completed
- Primary scale: `100` patients per scenario, `30.0` second horizon

The first preserved versioned baseline is still:

- `outputs/versioned_runs/v001_full_pipeline`

It completed all `8/8` pipeline steps.

## Read These First

1. [`final_result.md`](final_result.md)
2. [`dashboard_results_share.md`](dashboard_results_share.md)
3. [`03_v001_result_summary.md`](03_v001_result_summary.md)
4. [`04_v001_figure_guide.md`](04_v001_figure_guide.md)
5. [`02_data_usage.md`](02_data_usage.md)
6. [`05_next_work.md`](05_next_work.md)

## Main Result

Primary manuscript-facing run:

| Policy | Reward | Success | Oracle gap |
| --- | ---: | ---: | ---: |
| ACLS-rule baseline | 66.045 | 0.813 | 27.929 |
| Oracle | 93.974 | 0.980 | 0.000 |

Versioned AI selector comparison:

| Policy | Average reward | Average success | Average oracle gap |
| --- | ---: | ---: | ---: |
| Selector LinUCB | 87.625 | 0.925 | 10.686 |
| ACLS-rule baseline | 75.901 | 0.833 | 22.410 |
| Oracle | 98.311 | 1.000 | 0.000 |

## Interpretation

The dashboard has two related result layers:

- `stage9_n100_time2` is the best current manuscript-facing simulator run by
  scale.
- The four versioned AI selector runs beat ACLS on average and in `3/4`
  comparable runs, but not consistently.

This means the framework is working, but the learned selector still needs
better ECG realism, noise robustness, and training before claiming clinical or
AI-over-ACLS performance.
