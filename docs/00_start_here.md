# Start Here

## What This Project Is

This is a simulation research repo for choosing one electrical stimulation
strategy from a short ECG observation window.

It is not a clinical decision tool.

The current model observes a 4-second ECG window, extracts ECG features, and
chooses one of five actions:

| ID | Action |
| ---: | --- |
| 0 | Synchronized cardioversion |
| 1 | Unsynchronized defibrillation |
| 2 | ATP burst pacing |
| 3 | Resonant drift pacing |
| 4 | Adaptive low-energy pacing |

## Current Best Run

The current saved baseline is:

- `outputs/versioned_runs/v001_full_pipeline`

It completed all `8/8` pipeline steps.

## Read These First

1. [`03_v001_result_summary.md`](03_v001_result_summary.md)
2. [`04_v001_figure_guide.md`](04_v001_figure_guide.md)
3. [`02_data_usage.md`](02_data_usage.md)
4. [`05_next_work.md`](05_next_work.md)

## Main Result

| Policy | Reward | Success | Oracle gap |
| --- | ---: | ---: | ---: |
| Selector LinUCB | 85.190 | 0.900 | 13.071 |
| ACLS-rule baseline | 89.149 | 0.933 | 9.113 |
| Oracle | 98.261 | 1.000 | 0.000 |

## Interpretation

The current selector is better than fixed always-action baselines, but it does
not yet beat the ACLS-rule baseline.

This means the framework is working, but the learned selector still needs
better ECG realism, noise robustness, and training.
