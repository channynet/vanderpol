# Stage 7 Balanced Robustness Snapshot

Stage 7 adds Challenge 2015 alarm-category balancing and conservative fallback
threshold sweeps.

## Commands run

```powershell
python scripts/download_challenge_balanced.py --list-only
python scripts/download_challenge_balanced.py --per-category 1 --seed 11 --manifest outputs/challenge2015_balanced_manifest.csv
python scripts/estimate_alarm_noise_by_category.py --manifest outputs/challenge2015_balanced_manifest.csv --stride-s 10 --max-windows-per-record 4 --output-json outputs/challenge2015_category_noise.json
python scripts/fallback_threshold_sweep.py --patients-per-scenario 1 --profiles severe --real-noise-stats outputs/real_noise_stats.json --min-sqi 0.35 0.50 --entropy 0.62 --rr-cv 0.30 --horizon-s 3 --output-json outputs/fallback_threshold_sweep.json --output-csv outputs/fallback_threshold_sweep.csv
```

## Alarm category counts

- Asystole: 122 total, 22 true, 100 false
- Bradycardia: 89 total, 46 true, 43 false
- Tachycardia: 140 total, 131 true, 9 false
- Ventricular_Flutter_Fib: 58 total, 6 true, 52 false
- Ventricular_Tachycardia: 341 total, 89 true, 252 false

## Balanced smoke sample

One record per category:

- Asystole: `a539l`
- Bradycardia: `b562s`
- Tachycardia: `t742s`
- Ventricular_Flutter_Fib: `f545l`
- Ventricular_Tachycardia: `v557l`

Generated:

- `outputs/challenge2015_balanced_manifest.csv`
- `outputs/challenge2015_category_noise.json`
- `outputs/fallback_threshold_sweep.json`
- `outputs/fallback_threshold_sweep.csv`

## Threshold sweep smoke observation

This smoke used 1 patient per scenario and a 3 second horizon, so it is only a
pipeline check.

- With `min_signal_quality=0.35`, selector and conservative selector matched.
- With `min_signal_quality=0.50`, the real-estimated profile became worse for
  the conservative selector in this tiny sample.
- This confirms the threshold sweep is necessary; fallback rules should be tuned
  against regret, not set by intuition alone.

## Next scale-up

Use category-balanced data with more records:

```powershell
python scripts/download_challenge_balanced.py --per-category 10 --seed 11 --manifest outputs/challenge2015_balanced_manifest_n10.csv
python scripts/estimate_alarm_noise_by_category.py --manifest outputs/challenge2015_balanced_manifest_n10.csv --stride-s 10 --max-windows-per-record 8 --output-json outputs/challenge2015_category_noise_n10.json
python scripts/fallback_threshold_sweep.py --patients-per-scenario 20 --profiles severe --category-noise-stats outputs/challenge2015_category_noise_n10.json --min-sqi 0.30 0.35 0.42 0.50 --entropy 0.55 0.62 0.70 --rr-cv 0.25 0.30 0.40 --horizon-s 30 --output-json outputs/fallback_threshold_sweep_n20.json --output-csv outputs/fallback_threshold_sweep_n20.csv
```
