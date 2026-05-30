# Stage 6 Real-Noise Robustness Snapshot

Stage 6 adds PhysioNet/CinC Challenge 2015 sample ingestion, feature-level
real-noise estimation, and a conservative selector fallback.

## Commands run

```powershell
python scripts/download_physionet_sample.py --dataset challenge-2015 --records v100s v101l a103l a104s
python scripts/estimate_real_noise.py --dataset challenge-2015 --records v100s v101l a103l a104s --stride-s 10 --max-windows-per-record 6 --output-json outputs/real_noise_stats.json
python scripts/conservative_sweep.py --patients-per-scenario 2 --profiles clean mild moderate severe --real-noise-stats outputs/real_noise_stats.json --horizon-s 5 --output-json outputs/conservative_sweep.json --output-csv outputs/conservative_sweep.csv
```

## Generated outputs

- `outputs/real_noise_stats.json`
- `outputs/conservative_sweep.json`
- `outputs/conservative_sweep.csv`
- `data/raw/challenge-2015/*.hea`
- `data/raw/challenge-2015/*.mat`

## Real-noise estimate

From 24 Challenge 2015 windows:

- mean HR: 167.35 bpm
- mean dominant frequency: 7.09 Hz
- mean spectral entropy: 0.70
- mean signal quality: 0.45
- ACLS-style labels: 18 `vf_or_chaotic`, 5 `indeterminate`, 1 `normal_or_sinus`

Recommended synthetic corruption profile:

- gaussian std: 0.103
- baseline wander amp: 0.134
- muscle amp: 0.052
- powerline amp: 0.031
- dropout fraction: 0.010

## Conservative Selector Smoke

With 2 patients per scenario and a 5 second horizon:

- clean selector reward: 89.04
- clean conservative reward: 89.04
- severe selector reward: 64.86
- severe conservative reward: 64.89
- severe ACLS-rule reward: 75.05
- real-estimated selector reward: 84.92
- real-estimated conservative reward: 84.92

The conservative fallback currently avoids changing most decisions. This first
pass only overrides obvious normal-withhold, chaotic shockable, low-SQI, and
irregular-pacing-risk cases.

## Next Robustness Work

- Expand Challenge 2015 samples by alarm category.
- Estimate per-category noise profiles instead of one pooled profile.
- Add fallback threshold sweeps and tune them against selector-vs-ACLS regret.
- Add a conservative training objective that penalizes low-SQI disagreement
  with the ACLS-rule baseline.
