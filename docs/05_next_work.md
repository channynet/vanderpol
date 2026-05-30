# Next Work

## Priority 1: Make Abnormal ECG More Realistic

Status:

- In progress, current result saved at
  `outputs/versioned_runs/v004_existing_rhythm_realism_mitdb_cudb`.
- The current five scenario set is kept fixed. No AFIB, bigeminy, trigeminy,
  IVR, or nodal rhythm scenario is being added in this iteration.
- MIT-BIH abnormal windows and CUDB VT/VF rows are now included in the abnormal
  validation path.
- Main remaining mismatch: synthetic sample entropy is still too high, VT RR
  variability is still too low, and SVT/flutter spectral entropy is still too
  low.

Problem:

- Current synthetic abnormal rhythms are not yet close enough to real abnormal
  ECG feature distributions.

Actions:

1. Use MIT-BIH abnormal windows to tune SVT/AFL and other abnormal rhythms.
2. Use CUDB to tune VT/VF-like waveforms.
3. Keep the current five scenario set for now:
   - NSR
   - SVT/flutter-like
   - monomorphic VT
   - polymorphic VT
   - VF-like chaos
4. Do not add AFIB, bigeminy, trigeminy, IVR, or nodal rhythm in the next
   iteration unless the project needs broader arrhythmia coverage later.

## Priority 2: Improve Selector Learning

Problem:

- LinUCB selector is weaker than ACLS and over-selects adaptive pacing.

Actions:

1. Add supervised oracle-label classifier.
2. Compare handcrafted features vs learned ECG encoder.
3. Train with noisy observations instead of only clean synthetic observations.
4. Add class/action balancing so the selector does not collapse to one action.

## Priority 3: Improve Adaptive Low-Energy Pacing

Problem:

- Adaptive works well for NSR/monomorphic VT but poorly for chaotic rhythms.

Actions:

1. Add rhythm gate:
   - NSR -> withhold
   - VF/polymorphic -> defib fallback
   - regular wide VT -> ATP/ramp pacing
   - regular narrow tachycardia -> SVT-specific pacing or sync fallback
2. Add interval sweep:
   - `0.85 x cycle`
   - `0.88 x cycle`
   - `0.92 x cycle`
3. Add response monitoring after pulses.
4. Add escalation if low-energy pacing fails.

## Priority 4: Speed Up Experiments

Problem:

- The current pipeline recomputes the algorithm matrix many times.

Actions:

1. Cache the base algorithm matrix.
2. Reuse the cached matrix for selector report, decision boundary, bootstrap,
   and stability.
3. Save partial matrix rows during long runs.

## Recommended v002

Use a controlled next version:

```text
v002_n50_real_validation
```

Suggested changes:

- `patients_per_scenario = 50`
- MIT-BIH abnormal validation included for the current matched rhythm groups
- CUDB VT/VF validation included
- noisy observation training included
- supervised oracle-label classifier baseline added
- adaptive option changed to rhythm-gated closed-loop behavior
