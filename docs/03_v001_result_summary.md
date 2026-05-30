# v001 Result Summary

## Run Location

- `outputs/versioned_runs/v001_full_pipeline`

## Run Status

| Item | Value |
| --- | --- |
| Status | Completed |
| Steps | 8/8 |
| Config | `configs/bundle_n20.json` |
| Patients per scenario | 20 |
| Horizon | 30 seconds |
| Failed steps | None |

## Main Selector Result

| Policy | Mean reward | Oracle gap | Success rate | Mean time s |
| --- | ---: | ---: | ---: | ---: |
| Selector LinUCB | 85.190 | 13.071 | 0.900 | 4.810 |
| ACLS-rule baseline | 89.149 | 9.113 | 0.933 | 4.185 |
| Oracle | 98.261 | 0.000 | 1.000 | 1.739 |

## Meaning

The learned selector is better than fixed always-action baselines, but it is
not yet better than the ACLS-rule baseline.

The oracle is much better than both, which means there is still useful
patient-specific treatment-choice signal that the current selector is not
capturing.

## Scenario Winners

| Scenario | Best algorithm | Reward | Success |
| --- | --- | ---: | ---: |
| `nsr` | Adaptive low-energy pacing | 89.936 | 0.950 |
| `svt_flutter` | Synchronized cardioversion | 92.525 | 0.950 |
| `monomorphic_vt` | Adaptive low-energy pacing | 94.963 | 1.000 |
| `polymorphic_vt` | Unsynchronized defibrillation | 92.275 | 0.950 |
| `vf_like` | Unsynchronized defibrillation | 98.710 | 1.000 |

## Main Problem

The selector decision boundary collapses too much toward adaptive low-energy
pacing. Under moderate and severe noise, selector performance also drops
strongly.

## Defensible Claim

The project can currently claim:

- The pipeline runs end to end.
- The simulator creates a nontrivial treatment-selection problem.
- The current selector exposes clear failure modes.
- More realistic ECG generation and noise-aware learning are needed before
  claiming improvement over ACLS.
