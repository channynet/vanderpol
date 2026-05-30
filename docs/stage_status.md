# Stage Status

## Stage 1: Synthetic smoke path

Implemented.

- Package scaffold under `src/vanderpol`.
- Synthetic Gois-Savi-inspired coupled Van der Pol simulator.
- ECG-like projection with His-Purkinje QRS pulse proxy.
- Five scenario sampler: NSR, SVT/flutter-like, monomorphic VT,
  polymorphic VT, and VF-like.
- Hand-crafted ECG feature extractor and ACLS-style labels.
- Five electrical stimulation algorithms with one common `run` interface.
- Reward function, ACLS-style rule baseline, and LinUCB selector smoke path.
- Scripts for Phase 1 smoke, Phase 2 matrix, selector smoke, and data manifest.
- Unit/integration smoke tests.

## Suggested Stage 2

Implemented.

- Add WFDB loaders for MIT-BIH, CUDB, and PhysioNet/CinC 2015.
- Validate R-peak, RR, QRS-width, entropy, and dominant-frequency features.
- Save feature distributions from real ECG and compare them with synthetic
  scenario distributions.

The code now supports the first three items when local WFDB records and the
optional `wfdb` dependency are available. Treatment probability and energy-scale
calibration remains the next step.

## Suggested Stage 3

Calibrate the synthetic treatment library against literature anchors before
using Phase 2 results as research claims.

- Add a calibration config for success probability, acceleration risk, safety
  penalties, and energy scales.
- Add a small calibration report script that compares current synthetic matrix
  values against configured target ranges.
- Add figure generation for the 5x5 algorithm-by-scenario matrix.

## Real Data Smoke

Completed a first real-data smoke pass after installing `wfdb`.

- Downloaded MIT-BIH sample records `100`, `101`.
- Downloaded CUDB sample records `cu01`, `cu02`.
- Produced `outputs/mitdb_features.csv`, `outputs/cudb_features.csv`, and
  `outputs/cudb_features_wide.csv`.
- See `docs/real_data_validation.md` for the current observations.

## Stage 3: Annotation Sampling And Calibration

Implemented.

- Added WFDB rhythm annotation parsing for `aux_note` labels such as `(VT`,
  `(VF`, and `(N`.
- Added CUDB-style bracket segment parsing for `[` and `]`.
- Added `scripts/extract_annotated_windows.py`.
- Produced `outputs/cudb_annotated_vt_vf.csv` from CUDB records `cu01`, `cu02`.
- Added `configs/calibration.json` and `scripts/run_calibration_report.py`.
- Produced `outputs/calibration_report.json`; current smoke pass rate is 1.0.

## Suggested Stage 4

Implemented.

- Generate 5x5 algorithm-by-scenario heatmaps for success, energy, time, and
  safety.
- Generate selector-vs-ACLS-vs-oracle summary tables.
- Add a decision-boundary grid over QRS width and RR regularity.
- See `docs/stage4_reporting.md` for generated outputs and smoke metrics.

## Suggested Stage 5

Implemented.

- Run the Phase 2 matrix with at least 100 patients per scenario.
- Run selector reports with train/test split stability over multiple seeds.
- Add confidence intervals or bootstrap summaries to heatmaps and reports.
- Add noise/OOD generalization sweeps using PhysioNet/CinC 2015 style noise.
- See `docs/stage5_analysis.md` for generated outputs and smoke observations.

## Suggested Stage 6

Implemented.

- Download a PhysioNet/CinC 2015 sample set.
- Estimate baseline wander, artifact, and false-alarm feature shifts from real
  ICU-style windows.
- Tune the Stage 5 noise profiles to match those measured distributions.
- Add robustness-aware selector training or conservative fallback rules.
- See `docs/stage6_real_noise.md` for generated outputs and smoke observations.

## Suggested Stage 7

Implemented.

- Download a balanced Challenge 2015 sample across alarm categories.
- Estimate per-alarm-category real-noise profiles.
- Sweep conservative fallback thresholds.
- Compare selector, conservative selector, ACLS-rule, and oracle under a full
  30 second horizon with bootstrap intervals.
- See `docs/stage7_balanced_robustness.md` for generated outputs and smoke
  observations.

## Suggested Stage 8

Implemented.

- Add one command that runs Phase 2 matrix, selector report, robustness sweeps,
  and figures with consistent seeds.
- Add a machine-readable `outputs/run_manifest.json`.
- Add an executive summary markdown generator for the latest run.
- Keep full-scale defaults configurable so small smoke runs stay fast.
- See `docs/stage8_bundle.md` for the smoke bundle result.

## Suggested Stage 9

Implemented.

- Added `configs/bundle_n20.json` as an intermediate paper-prep run size.
- Added manuscript-ready table generation from Stage 8 bundle manifests.
- Added citation metadata for external ECG, guideline, ATP, resonant-drift, and
  simulator anchors.
- Added a limitations section generator that flags toy-model assumptions and
  non-clinical-use constraints.
- Added live progress files, resume support, and partial-result reporting for
  long bundle runs.
- See `docs/stage9_paper_artifacts.md` for generated outputs and commands.
