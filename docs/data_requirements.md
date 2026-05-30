# Data Requirements

External data has two separate jobs in this project:

1. ECG observation realism: make the 4-second window and extracted features look
   like real ECG.
2. Calibration and validation: anchor rule baselines, treatment probability
   ranges, safety penalties, and reporting claims.

Treatment outcome rewards remain simulator-generated.

## Required next

- MIT-BIH Arrhythmia Database
  - Use for R-peak, RR regularity, QRS-width proxy, and basic arrhythmia
    morphology checks.
  - Needed before claiming the observation features are realistic.
  - Current script: `python scripts/download_physionet_sample.py --dataset mitdb --limit 2`
  - Abnormal rhythm windows can be prepared with:
    `python scripts/prepare_mitdb_abnormal_windows.py --download-missing --output-prefix outputs/mitdb_abnormal_windows`
  - Current abnormal-window outputs:
    `outputs/mitdb_abnormal_windows.csv`,
    `outputs/mitdb_abnormal_windows.npz`, and
    `outputs/mitdb_abnormal_windows.json`.

- Creighton University Ventricular Tachyarrhythmia Database
  - Use for sustained VT, ventricular flutter, and VF-like morphology.
  - Needed before tuning monomorphic VT, polymorphic VT, and VF-like scenarios.
  - Current script: `python scripts/download_physionet_sample.py --dataset cudb --limit 2`

- AHA ACLS tachyarrhythmia guidance
  - Use for the ACLS-style rule baseline and clinically named thresholds.
  - Needed before formal selector-vs-ACLS comparisons.

- ICD/ATP and resonant-drift literature
  - Use for success-rate, acceleration-risk, and low-energy scaling ranges.
  - Needed before Phase 2 matrix results are more than toy calibration.
  - Current config: `configs/calibration.json`

## Current validation commands

```powershell
python -m pip install wfdb
python scripts/validate_external_features.py --dataset mitdb --max-windows-per-record 5 --output outputs/mitdb_features.csv
python scripts/validate_external_features.py --dataset cudb --max-windows-per-record 5 --output outputs/cudb_features.csv
python scripts/compare_synthetic_real_features.py --real-csv outputs/mitdb_features.csv
python scripts/extract_annotated_windows.py --dataset cudb --records cu01 cu02 --labels VT VF --output outputs/cudb_annotated_vt_vf.csv
python scripts/run_calibration_report.py --patients-per-scenario 5 --output outputs/calibration_report.json
python scripts/estimate_real_noise.py --dataset challenge-2015 --records v100s v101l a103l a104s --stride-s 10 --max-windows-per-record 6 --output-json outputs/real_noise_stats.json
python scripts/conservative_sweep.py --patients-per-scenario 2 --profiles clean mild moderate severe --real-noise-stats outputs/real_noise_stats.json --horizon-s 5 --output-json outputs/conservative_sweep.json --output-csv outputs/conservative_sweep.csv
python scripts/estimate_alarm_noise_by_category.py --manifest outputs/challenge2015_balanced_manifest.csv --stride-s 10 --max-windows-per-record 4 --output-json outputs/challenge2015_category_noise.json
python scripts/fallback_threshold_sweep.py --patients-per-scenario 1 --profiles severe --real-noise-stats outputs/real_noise_stats.json --min-sqi 0.35 0.50 --entropy 0.62 --rr-cv 0.30 --horizon-s 3 --output-json outputs/fallback_threshold_sweep.json --output-csv outputs/fallback_threshold_sweep.csv
```

## Needed later

- PhysioNet/CinC Challenge 2015
  - Use for noisy ICU alarm-like ECG and false-alarm robustness.
  - Needed for Phase 3/5 noise and generalization experiments.
  - Current script: `python scripts/download_physionet_sample.py --dataset challenge-2015 --records v100s v101l a103l a104s`
  - Balanced script: `python scripts/download_challenge_balanced.py --per-category 1 --seed 11 --manifest outputs/challenge2015_balanced_manifest.csv`

- PTB-XL
  - Use for optional learned ECG encoder pretraining.
  - Not required for the hand-crafted-feature selector path.
