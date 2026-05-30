# Calibration Report Snapshot

This project uses calibration ranges as simulation anchors, not clinical
claims. Current target definitions live in `configs/calibration.json`.

## Command run

```powershell
python scripts/run_calibration_report.py --patients-per-scenario 5 --output outputs/calibration_report.json
```

## Current result

- Calibration checks: 8
- Pass rate: 1.0
- Key anchors:
  - synchronized cardioversion succeeds for organized SVT/flutter-like rhythm
  - ATP succeeds for regular monomorphic VT and remains poor for polymorphic VT
  - unsynchronized defibrillation succeeds for VF-like rhythm
  - synchronized cardioversion does not solve VF-like rhythm
  - resonant drift uses low energy relative to unsynchronized defibrillation
  - adaptive low-energy pacing withholds stimulation in NSR

## Caveat

The current report is a smoke calibration with 5 patients per scenario. It
checks code and rough ordering, not final statistical behavior. Before using
the matrix in a paper-style result, run at least 100 patients per scenario and
replace broad target ranges with explicitly cited parameter values.
