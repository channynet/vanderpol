# Stage 9 Paper Artifacts

Stage 9 turns a Stage 8 run manifest into manuscript-facing tables and guardrail
documents.

## Commands

```powershell
python scripts/run_experiment_bundle.py --config configs/bundle_n20.json --output-dir outputs/runs --run-id stage9_n20 --resume
python scripts/generate_paper_artifacts.py outputs/runs/stage9_n20/run_manifest.json
```

To inspect or visualize partial results while the run is still incomplete:

```powershell
python scripts/show_run_progress.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
python scripts/generate_live_report.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
```

`generate_live_report.py` can be run while a bundle is still incomplete. Missing
tables are reported as warnings, and existing figures/tables are refreshed.

For a fast smoke check using the existing Stage 8 run:

```powershell
python scripts/generate_paper_artifacts.py outputs/runs/stage8_smoke/run_manifest.json
```

## Generated Files

- `paper_selector_table.csv` and `.md`
- `paper_calibration_table.csv` and `.md`
- `paper_algorithm_matrix_table.csv` and `.md`
- `paper_algorithm_winners.csv` and `.md`
- `paper_noise_robustness_table.csv` and `.md`
- `paper_fallback_sweep_table.csv` and `.md`
- `citations.md`
- `limitations.md`
- `live_dashboard.html`
- `paper_summary.md`
- `paper_artifacts_manifest.json`

## Interpretation

The generated artifacts are reporting outputs. They do not change model
behavior, simulator rewards, or selector training. They make the current result
bundle easier to audit and move into a paper draft.

The required guardrail remains unchanged: external ECG data validates observation
features and noise realism, while treatment success and reward are produced by
the simulator.
