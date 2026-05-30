# Real ECG Validation Snapshot

This snapshot records the first real-data smoke validation after installing
`wfdb` and downloading two records each from MIT-BIH and CUDB.

## Commands run

```powershell
python -m pip install wfdb
python scripts/download_physionet_sample.py --dataset mitdb --records 100 101
python scripts/download_physionet_sample.py --dataset cudb --records cu01 cu02
python scripts/validate_external_features.py --dataset mitdb --records 100 101 --max-windows-per-record 8 --output outputs/mitdb_features.csv
python scripts/validate_external_features.py --dataset cudb --records cu01 cu02 --max-windows-per-record 8 --output outputs/cudb_features.csv
python scripts/validate_external_features.py --dataset cudb --records cu01 cu02 --stride-s 30 --max-windows-per-record 20 --output outputs/cudb_features_wide.csv
```

## Observations

- MIT-BIH records `100` and `101`, first 16 windows:
  - labels: 8 `normal_or_sinus`, 7 `indeterminate`, 1 `vf_or_chaotic`
  - mean HR: 98.19 bpm
  - mean QRS proxy: 0.043 s
  - mean RR CV: 0.213

- CUDB records `cu01` and `cu02`, first 16 windows:
  - labels: 6 `normal_or_sinus`, 10 `indeterminate`
  - mean HR: 85.92 bpm
  - mean QRS proxy: 0.122 s

- CUDB records `cu01` and `cu02`, sparse 30 s stride:
  - labels: 19 `normal_or_sinus`, 10 `indeterminate`, 5 `vf_or_chaotic`
  - mean HR: 103.36 bpm
  - mean QRS proxy: 0.125 s

## Interpretation

- The ECG loader and feature pipeline work on real WFDB records.
- Entropy-only VF detection was too aggressive for real narrow-complex ECG, so
  the ACLS-style label rule now protects narrow, regular, HR < 120 bpm windows.
- CUDB should be sampled across the record, not only from the beginning, because
  early windows can be normal or indeterminate before tachyarrhythmia segments.
- The synthetic model still has visible distribution gaps, especially spectral
  entropy and sample entropy. These are calibration targets, not blockers.
