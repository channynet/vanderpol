# Stage 5 Analysis Snapshot

Stage 5 adds uncertainty and robustness analysis around the Stage 4 result
figures.

## Commands run

```powershell
python scripts/bootstrap_matrix_report.py --patients-per-scenario 2 --n-bootstrap 50 --horizon-s 5 --output-csv outputs/bootstrap_matrix_ci.csv
python scripts/selector_stability_report.py --patients-per-scenario 2 --seeds 1 7 13 --horizon-s 5 --output-json outputs/selector_stability.json --output-csv outputs/selector_stability.csv
python scripts/noise_ood_sweep.py --patients-per-scenario 2 --profiles clean mild moderate severe --horizon-s 5 --output-json outputs/noise_ood_sweep.json --output-csv outputs/noise_ood_sweep.csv
```

## Generated outputs

- `outputs/bootstrap_matrix_ci.csv`
- `outputs/selector_stability.json`
- `outputs/selector_stability.csv`
- `outputs/noise_ood_sweep.json`
- `outputs/noise_ood_sweep.csv`

## Current smoke observations

These runs use only 2 patients per scenario and a 5 second treatment horizon, so
they are pipeline checks rather than research claims.

- Multi-seed selector stability over seeds 1, 7, 13:
  - selector mean reward: 87.65 +/- 15.74
  - ACLS-rule mean reward: 99.06 +/- 0.06
  - oracle mean reward: 99.14 +/- 0.00

- Noise/OOD sweep:
  - clean selector mean reward: 89.04
  - moderate-noise selector mean reward: 79.01
  - severe-noise selector mean reward: 64.86
  - severe-noise ACLS-rule mean reward: 75.05

## Interpretation

- Bootstrap CI generation works and should be rerun on the full 30 second
  horizon with larger patient counts.
- Selector stability varies noticeably across tiny train/test splits, which is
  expected at this sample size.
- Severe observation corruption can degrade the learned selector more than the
  ACLS-rule baseline. That is a useful robustness target for the next stage.

## Larger run suggestion

```powershell
python scripts/bootstrap_matrix_report.py --patients-per-scenario 100 --n-bootstrap 1000 --horizon-s 30 --output-csv outputs/bootstrap_matrix_ci_n100.csv
python scripts/selector_stability_report.py --patients-per-scenario 100 --seeds 1 7 13 21 42 --horizon-s 30 --output-json outputs/selector_stability_n100.json --output-csv outputs/selector_stability_n100.csv
python scripts/noise_ood_sweep.py --patients-per-scenario 50 --profiles clean mild moderate severe --horizon-s 30 --eval-variability 0.4 --output-json outputs/noise_ood_sweep_n50.json --output-csv outputs/noise_ood_sweep_n50.csv
```
