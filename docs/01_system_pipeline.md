# System Pipeline

## One Episode

Each episode follows this structure:

1. Generate or load a patient ECG observation.
2. Observe a 4-second ECG window.
3. Extract ECG features.
4. Select one treatment action.
5. Run the treatment in the simulator.
6. Log success, time, energy, safety flags, and reward.

## Observation

The observation is a 4-second ECG-like signal.

The current handcrafted feature vector includes:

| Feature | Meaning |
| --- | --- |
| `heart_rate_bpm` | Estimated heart rate. |
| `rr_cv` | RR interval variability. |
| `regularity` | Inverse-style regularity score derived from RR variability. |
| `qrs_width_s` | QRS-width proxy. |
| `dominant_frequency_hz` | Dominant frequency in the ECG window. |
| `spectral_entropy` | Frequency-domain complexity. |
| `sample_entropy` | Time-domain complexity proxy. |
| `signal_quality` | Signal quality estimate. |

## Treatment Algorithms

| Action | Algorithm | Intended strength |
| ---: | --- | --- |
| 0 | Synchronized cardioversion | Organized tachycardia, SVT/flutter-like rhythms. |
| 1 | Unsynchronized defibrillation | VF-like and polymorphic shockable rhythms. |
| 2 | ATP burst pacing | Regular monomorphic VT-like rhythms. |
| 3 | Resonant drift pacing | Low-energy phase-based pacing, mainly regular rhythms. |
| 4 | Adaptive low-energy pacing | Withhold for normal rhythm, low-energy pacing for selected tachy rhythms. |

## Reward

The current default reward is:

```text
reward = 100 * success - time_to_termination_s
```

Energy is logged but does not affect the current default reward.

Safety flags are logged but do not affect the current default reward.

## Selector Evaluation

The simulator produces a full treatment matrix:

```text
patient contexts x treatment algorithms
```

For `v001_full_pipeline`:

- `5` rhythm scenarios
- `20` patients per scenario
- `100` patient contexts
- `5` algorithms per context
- `500` treatment episodes in the base matrix

The selector is trained/evaluated against this simulated matrix and compared to:

- ACLS-rule baseline
- Oracle upper bound
- Always-use-one-action baselines
