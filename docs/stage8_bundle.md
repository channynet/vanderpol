# Stage 8 Experiment Bundle Snapshot

Stage 8 adds a single runner that collects the core experiment outputs into one
run directory with a machine-readable manifest and a markdown executive summary.

## Commands run

```powershell
python scripts/run_experiment_bundle.py --config configs/bundle_smoke.json --output-dir outputs/runs --run-id stage8_smoke
python scripts/generate_executive_summary.py outputs/runs/stage8_smoke/run_manifest.json --output-md outputs/runs/stage8_smoke/executive_summary_regenerated.md
```

Longer runs can be resumed and monitored:

```powershell
python scripts/run_experiment_bundle.py --config configs/bundle_n20.json --output-dir outputs/runs --run-id stage9_n20 --resume
python scripts/show_run_progress.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
python scripts/generate_live_report.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
```

## Generated outputs

- `outputs/runs/stage8_smoke/run_manifest.json`
- `outputs/runs/stage8_smoke/run_progress.json`
- `outputs/runs/stage8_smoke/run_progress.md`
- `outputs/runs/stage8_smoke/executive_summary.md`
- `outputs/runs/stage8_smoke/figures/phase2_*.png`
- `outputs/runs/stage8_smoke/selector_report.json`
- `outputs/runs/stage8_smoke/calibration_report.json`
- `outputs/runs/stage8_smoke/bootstrap_matrix_ci.csv`
- `outputs/runs/stage8_smoke/selector_stability.*`
- `outputs/runs/stage8_smoke/noise_ood_sweep.*`
- `outputs/runs/stage8_smoke/fallback_threshold_sweep.*`

## Smoke result

The `stage8_smoke` bundle completed with no failed steps.

- duration: 63.26 seconds
- calibration pass rate: 0.88
- selector reward: 98.99
- ACLS-rule reward: 99.21
- oracle reward: 99.21

These values are smoke-run checks only: the config uses 1 patient per scenario
and a 3 second horizon.

## Presets

- `configs/bundle_smoke.json`: fast end-to-end verification
- `configs/bundle_full.json`: full-scale intended settings

The bundle runner also accepts `enabled_steps` in a JSON config for partial
runs, for example only `calibration_report` and `selector_report`.

During execution the runner updates `run_manifest.json`, `run_progress.json`,
and `run_progress.md` after every completed step. If a run is interrupted,
re-run the same command with `--resume` to reuse completed step outputs.
