# Vanderpol ECG Electrical-Stimulation Selector

This repository is a research scaffold for a contextual-bandit selector that
chooses one electrical stimulation strategy from a short ECG observation window.

It is not a clinical tool.

## Documentation

Start here:

- [`docs/README.md`](docs/README.md)
- [`docs/00_start_here.md`](docs/00_start_here.md)
- [`docs/03_v001_result_summary.md`](docs/03_v001_result_summary.md)
- [`docs/04_v001_figure_guide.md`](docs/04_v001_figure_guide.md)
- [`docs/05_next_work.md`](docs/05_next_work.md)

Current preserved run:

- `outputs/versioned_runs/v001_full_pipeline`

Current headline:

- The full pipeline completed successfully.
- The learned selector beats fixed always-action baselines.
- The learned selector does not yet beat the ACLS-rule baseline.
- The main weaknesses are decision-boundary collapse and noise sensitivity.

## Implemented Stage 1

- Synthetic Gois-Savi-inspired coupled Van der Pol oscillator simulator.
- ECG-like projection from SA, AV, and His-Purkinje oscillator states.
- Scenario sampler for NSR, SVT/flutter-like, monomorphic VT, polymorphic VT,
  and VF-like rhythms.
- Hand-crafted features: HR, RR regularity, QRS-width proxy, dominant
  frequency, spectral entropy, sample entropy, and signal quality.
- Five stimulation actions:
  - synchronized cardioversion
  - unsynchronized defibrillation
  - ATP burst pacing
  - resonant drift pacing
  - adaptive low-energy pacing with a withhold behavior for normal rhythm
- Episode reward and ACLS-style rule baseline.
- LinUCB contextual-bandit smoke implementation.

## Implemented Stage 2

- Optional WFDB loader for local PhysioNet records.
- PhysioNet sample downloader for selected WFDB files.
- External ECG feature validation script.
- Synthetic-vs-real feature distribution comparison utility.
- External data scripts degrade cleanly when WFDB or local records are missing.

## Implemented Stage 3

- WFDB annotation parser for rhythm notes such as `(VT` and `(VF`.
- Annotation-aware ECG window extraction for CUDB/MIT-BIH-style records.
- Literature-guided calibration target config.
- Calibration report comparing synthetic algorithm matrix metrics to target
  ranges.

## Implemented Stage 4

- Phase 2 heatmaps for success, energy, time, safety, and reward.
- Selector-vs-ACLS-vs-oracle report table.
- QRS-width by RR-regularity decision-boundary figure.

## Implemented Stage 5

- Bootstrap confidence intervals for algorithm-by-scenario matrix metrics.
- Multi-seed selector stability reports.
- Synthetic ECG observation corruption profiles.
- Noise/OOD selector-vs-baseline sweep.

## Implemented Stage 6

- PhysioNet/CinC Challenge 2015 training sample download support.
- Real ECG noise/statistics estimation from WFDB `.mat` records.
- Real-noise-derived synthetic corruption profile.
- Conservative selector fallback for low-SQI, chaotic, normal, and irregular-risk cases.

## Implemented Stage 7

- Challenge 2015 alarm metadata parsing.
- Balanced sample download by alarm category.
- Per-alarm-category real-noise profile estimation.
- Conservative fallback threshold sweep.

## Implemented Stage 8

- End-to-end experiment bundle runner.
- Smoke/full bundle configs.
- Machine-readable run manifest.
- Markdown executive summary generator.

## Implemented Stage 9

- Intermediate `n20` experiment bundle config.
- Manuscript-ready table generator from Stage 8 run manifests.
- Citation metadata for external ECG, guideline, and calibration anchors.
- Limitations/guardrail document generator for non-clinical simulation claims.

## Quick Checks

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python scripts/run_phase1_smoke.py
python scripts/run_phase2_matrix.py --patients-per-scenario 3
python scripts/train_selector_smoke.py --patients-per-scenario 5
python scripts/prepare_external_data.py
```

## External ECG Validation

```powershell
python scripts/download_physionet_sample.py --dataset mitdb --limit 2
python -m pip install wfdb
python scripts/validate_external_features.py --dataset mitdb --max-windows-per-record 5 --output outputs/mitdb_features.csv
python scripts/compare_synthetic_real_features.py --real-csv outputs/mitdb_features.csv
python scripts/extract_annotated_windows.py --dataset cudb --records cu01 cu02 --labels VT VF --output outputs/cudb_annotated_vt_vf.csv
python scripts/run_versioned_abnormal_validation.py
python scripts/run_calibration_report.py --patients-per-scenario 5 --output outputs/calibration_report.json
python scripts/generate_phase2_figures.py --patients-per-scenario 3 --output-dir outputs/figures
python scripts/generate_selector_report.py --patients-per-scenario 3 --output-json outputs/selector_report.json --output-csv outputs/selector_report.csv
python scripts/generate_decision_boundary.py --patients-per-scenario 3 --grid-size 20 --output-png outputs/figures/decision_boundary.png --output-csv outputs/decision_boundary.csv
python scripts/bootstrap_matrix_report.py --patients-per-scenario 2 --n-bootstrap 50 --horizon-s 5 --output-csv outputs/bootstrap_matrix_ci.csv
python scripts/selector_stability_report.py --patients-per-scenario 2 --seeds 1 7 13 --horizon-s 5 --output-json outputs/selector_stability.json --output-csv outputs/selector_stability.csv
python scripts/noise_ood_sweep.py --patients-per-scenario 2 --profiles clean mild moderate severe --horizon-s 5 --output-json outputs/noise_ood_sweep.json --output-csv outputs/noise_ood_sweep.csv
python scripts/download_physionet_sample.py --dataset challenge-2015 --records v100s v101l a103l a104s
python scripts/estimate_real_noise.py --dataset challenge-2015 --records v100s v101l a103l a104s --stride-s 10 --max-windows-per-record 6 --output-json outputs/real_noise_stats.json
python scripts/conservative_sweep.py --patients-per-scenario 2 --profiles clean mild moderate severe --real-noise-stats outputs/real_noise_stats.json --horizon-s 5 --output-json outputs/conservative_sweep.json --output-csv outputs/conservative_sweep.csv
python scripts/download_challenge_balanced.py --per-category 1 --seed 11 --manifest outputs/challenge2015_balanced_manifest.csv
python scripts/estimate_alarm_noise_by_category.py --manifest outputs/challenge2015_balanced_manifest.csv --stride-s 10 --max-windows-per-record 4 --output-json outputs/challenge2015_category_noise.json
python scripts/fallback_threshold_sweep.py --patients-per-scenario 1 --profiles severe --real-noise-stats outputs/real_noise_stats.json --min-sqi 0.35 0.50 --entropy 0.62 --rr-cv 0.30 --horizon-s 3 --output-json outputs/fallback_threshold_sweep.json --output-csv outputs/fallback_threshold_sweep.csv
python scripts/run_experiment_bundle.py --config configs/bundle_smoke.json --output-dir outputs/runs --run-id stage8_smoke
python scripts/generate_paper_artifacts.py outputs/runs/stage8_smoke/run_manifest.json
python scripts/run_experiment_bundle.py --config configs/bundle_n20.json --output-dir outputs/runs --run-id stage9_n20 --resume
python scripts/show_run_progress.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
python scripts/generate_live_report.py outputs/runs/stage9_n20 --config configs/bundle_n20.json
```

## Versioned Results

Use `outputs/versioned_runs/v001_*`, `v002_*`, ... for results that should be
kept and compared across revisions.

```powershell
python scripts/run_versioned_abnormal_validation.py
python scripts/run_versioned_abnormal_validation.py --label tuned_svt_vt_vf
```

Each versioned folder contains a `version_manifest.json`, a short `README.md`,
and the experiment outputs under a named subfolder such as `comparison/`.

## External Data Role

External ECG data is intended for observation realism and validation, not for
directly learning treatment outcomes. Treatment rewards are produced by the
simulator.

- MIT-BIH Arrhythmia Database: R/RR/QRS and arrhythmia morphology validation.
- CUDB: VT, ventricular flutter, and VF-like validation.
- PhysioNet/CinC 2015: noisy ICU alarm-like ECG robustness.
- PTB-XL: optional larger-scale encoder pretraining.
- AHA ACLS and ICD/ATP literature: rule baseline and calibration anchors.
