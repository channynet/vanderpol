# Stage 4 Reporting Snapshot

Stage 4 adds the reporting layer for Phase 2 and selector analysis.

## Commands run

```powershell
python scripts/generate_phase2_figures.py --patients-per-scenario 3 --output-dir outputs/figures
python scripts/generate_selector_report.py --patients-per-scenario 3 --output-json outputs/selector_report.json --output-csv outputs/selector_report.csv
python scripts/generate_decision_boundary.py --patients-per-scenario 3 --grid-size 20 --output-png outputs/figures/decision_boundary.png --output-csv outputs/decision_boundary.csv
```

## Generated outputs

- `outputs/figures/phase2_success_rate.png`
- `outputs/figures/phase2_mean_energy.png`
- `outputs/figures/phase2_mean_time_s.png`
- `outputs/figures/phase2_mean_safety_violations.png`
- `outputs/figures/phase2_mean_reward.png`
- `outputs/figures/phase2_matrix_summary.csv`
- `outputs/selector_report.json`
- `outputs/selector_report.csv`
- `outputs/figures/decision_boundary.png`
- `outputs/decision_boundary.csv`

## Current smoke result

With 3 patients per scenario, the selector report is only a pipeline check.
The held-out evaluation included 5 contexts:

- oracle mean reward: 99.28
- selector LinUCB mean reward: 77.74
- ACLS-rule mean reward: 77.89
- selector oracle gap: 21.54
- ACLS oracle gap: 21.39

This is too small for a research claim, but it confirms the comparison table,
baseline metrics, and decision-boundary figure generation all work.

## Next reporting scale

For a paper-like Phase 2 figure, rerun with at least:

```powershell
python scripts/generate_phase2_figures.py --patients-per-scenario 100 --output-dir outputs/figures_n100
python scripts/generate_selector_report.py --patients-per-scenario 100 --output-json outputs/selector_report_n100.json --output-csv outputs/selector_report_n100.csv
python scripts/generate_decision_boundary.py --patients-per-scenario 100 --grid-size 80 --output-png outputs/figures_n100/decision_boundary.png --output-csv outputs/decision_boundary_n100.csv
```
