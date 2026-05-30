# v001 Full Pipeline Interpretation

The preserved baseline run is:

- `outputs/versioned_runs/v001_full_pipeline`

Main interpretation file:

- `outputs/versioned_runs/v001_full_pipeline/RESULT_INTERPRETATION.md`

Short conclusion:

- The full pipeline completed successfully.
- The learned LinUCB selector is better than fixed always-action baselines.
- The learned selector does not yet beat the ACLS-style rule baseline.
- The oracle is substantially better than both, so there is still useful
  treatment-choice signal that the current selector does not capture.

Headline numbers:

| Policy | Reward | Success | Oracle gap |
| --- | ---: | ---: | ---: |
| Selector LinUCB | 85.190 | 0.900 | 13.071 |
| ACLS-rule baseline | 89.149 | 0.933 | 9.113 |
| Oracle | 98.261 | 1.000 | 0.000 |

Next work should prioritize real ECG abnormal-rhythm matching, missing rhythm
scenarios, noisy-observation training, and a supervised oracle-label classifier
baseline.
