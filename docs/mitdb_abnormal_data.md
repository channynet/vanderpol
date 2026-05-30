# MIT-BIH Abnormal Rhythm Windows

This file documents the real abnormal ECG windows extracted from the MIT-BIH
Arrhythmia Database directory page and WFDB annotations.

## Source

- Directory page: https://archive.physionet.org/physiobank/database/html/mitdbdir/records.htm
- Downloaded WFDB files: `data/raw/mitdb/*.hea`, `data/raw/mitdb/*.dat`, `data/raw/mitdb/*.atr`
- Extraction script: `scripts/prepare_mitdb_abnormal_windows.py`

The directory page was used to choose records with abnormal rhythm episodes
such as `SVTA`, `Atrial fibrillation`, `Atrial flutter`, `Ventricular
tachycardia`, `Ventricular flutter`, `Ventricular bigeminy`, and `Ventricular
trigeminy`. The actual windows were then extracted from the local WFDB
annotation files, not from free-text page timestamps.

## Outputs

- Metadata and features: `outputs/mitdb_abnormal_windows.csv`
- Raw 4-second ECG windows: `outputs/mitdb_abnormal_windows.npz`
- Extraction manifest: `outputs/mitdb_abnormal_windows.json`
- Example plot: `outputs/figures/mitdb_abnormal_windows/mitdb_abnormal_examples_grid.png`

## Extracted Labels

Latest extraction:

| Label | Windows |
| --- | ---: |
| AFIB | 337 |
| AFL | 79 |
| IVR | 5 |
| NODAL | 51 |
| SVT | 45 |
| VENTRICULAR_BIGEMINY | 324 |
| VENTRICULAR_TRIGEMINY | 78 |
| VF | 28 |
| VT | 70 |

Total windows: `1017`.

## How This Data Is Used

These windows are real MIT-BIH abnormal ECG observations. They should be used
for:

- validating that synthetic abnormal rhythms have similar feature
  distributions;
- plotting real abnormal ECG examples in the presentation;
- training or testing an ECG rhythm/state encoder;
- replacing synthetic observation windows when the task is rhythm
  classification or representation learning.

They should not be used as treatment-outcome data. MIT-BIH provides ECG
signals and annotations, but not results for electrical therapies such as
cardioversion, defibrillation, or ATP.

## Rebuild Command

```powershell
python scripts/prepare_mitdb_abnormal_windows.py --download-missing --output-prefix outputs/mitdb_abnormal_windows
```

