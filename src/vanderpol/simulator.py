"""Synthetic Gois-Savi-inspired coupled Van der Pol simulator."""

from __future__ import annotations

from typing import Callable

import numpy as np

from .types import PatientParams, RhythmScenario, SimulationTrace, StimulusProtocol


StimulusFn = Callable[[float], float]


class GoisSaviSimulator:
    """Three coupled oscillators representing SA, AV, and His-Purkinje dynamics."""

    def __init__(self, fs_hz: int = 250):
        self.fs_hz = int(fs_hz)
        self.dt_s = 1.0 / float(fs_hz)

    def initial_state(self, patient: PatientParams) -> np.ndarray:
        rng = np.random.default_rng(patient.seed)
        phases = rng.uniform(0.0, 2.0 * np.pi, size=3)
        amplitudes = np.array([0.6, 0.45, 0.8], dtype=float)
        state = np.zeros(6, dtype=float)
        state[0::2] = amplitudes * np.cos(phases)
        state[1::2] = -amplitudes * np.sin(phases)
        return state

    def simulate(
        self,
        patient: PatientParams,
        duration_s: float,
        protocol: StimulusProtocol | None = None,
    ) -> SimulationTrace:
        n_steps = max(2, int(round(duration_s * self.fs_hz)))
        time_s = np.arange(n_steps, dtype=float) * self.dt_s
        states = np.zeros((n_steps, 6), dtype=float)
        state = self.initial_state(patient)

        for idx, t_s in enumerate(time_s):
            states[idx] = state
            state = self._rk4_step(state, t_s, patient, protocol)
            state = np.clip(state, -6.0, 6.0)

        ecg = project_ecg(time_s, states, patient, self.fs_hz)
        return SimulationTrace(
            time_s=time_s,
            states=states,
            ecg=ecg,
            fs_hz=self.fs_hz,
            protocol=protocol,
        )

    def _rk4_step(
        self,
        state: np.ndarray,
        t_s: float,
        patient: PatientParams,
        protocol: StimulusProtocol | None,
    ) -> np.ndarray:
        dt = self.dt_s
        f = self._derivative
        k1 = f(t_s, state, patient, protocol)
        k2 = f(t_s + 0.5 * dt, state + 0.5 * dt * k1, patient, protocol)
        k3 = f(t_s + 0.5 * dt, state + 0.5 * dt * k2, patient, protocol)
        k4 = f(t_s + dt, state + dt * k3, patient, protocol)
        return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    def _derivative(
        self,
        t_s: float,
        state: np.ndarray,
        patient: PatientParams,
        protocol: StimulusProtocol | None,
    ) -> np.ndarray:
        x_sa, y_sa, x_av, y_av, x_hp, y_hp = state
        freqs = self._instantaneous_frequencies(t_s, patient)
        omega_sa, omega_av, omega_hp = 2.0 * np.pi * freqs
        stimulus = protocol.stimulus_at(t_s) if protocol is not None else 0.0

        c_sa = patient.coupling_hp_sa * (x_hp - x_sa)
        c_av = patient.coupling_sa_av * (x_sa - x_av)
        c_hp = patient.coupling_av_hp * (x_av - x_hp)

        dx_sa = y_sa
        dy_sa = patient.mu_sa * (1.0 - x_sa * x_sa) * y_sa - omega_sa * omega_sa * x_sa + c_sa
        dx_av = y_av
        dy_av = patient.mu_av * (1.0 - x_av * x_av) * y_av - omega_av * omega_av * x_av + c_av
        dx_hp = y_hp
        dy_hp = (
            patient.mu_hp * (1.0 - x_hp * x_hp) * y_hp
            - omega_hp * omega_hp * x_hp
            + c_hp
            + 18.0 * stimulus
        )

        return np.array([dx_sa, dy_sa, dx_av, dy_av, dx_hp, dy_hp], dtype=float)

    def _instantaneous_frequencies(
        self, t_s: float, patient: PatientParams
    ) -> np.ndarray:
        sa = patient.sa_frequency_hz
        av = patient.av_frequency_hz
        hp = patient.hp_frequency_hz

        if patient.rhythm == RhythmScenario.SVT_FLUTTER:
            av *= 1.0 + patient.irregularity * 0.08 * np.sin(2.0 * np.pi * 0.71 * t_s)
            hp *= 1.0 + patient.irregularity * 0.12 * np.sin(2.0 * np.pi * 0.83 * t_s)
            hp *= 1.0 + patient.irregularity * 0.04 * np.sin(2.0 * np.pi * 1.63 * t_s)
        elif patient.rhythm == RhythmScenario.MONOMORPHIC_VT:
            hp *= 1.0 + patient.irregularity * 0.42 * np.sin(2.0 * np.pi * 0.47 * t_s)
            hp *= 1.0 + patient.irregularity * 0.16 * np.sin(2.0 * np.pi * 0.91 * t_s)
        elif patient.rhythm == RhythmScenario.POLYMORPHIC_VT:
            hp *= 1.0 + patient.irregularity * 0.35 * np.sin(2.0 * np.pi * 0.43 * t_s)
            hp *= 1.0 + patient.irregularity * 0.18 * np.sin(2.0 * np.pi * 1.1 * t_s)
        elif patient.rhythm == RhythmScenario.VF_LIKE:
            hp *= 1.0 + patient.irregularity * 0.25 * np.sin(2.0 * np.pi * 3.7 * t_s)
            av *= 1.0 + patient.irregularity * 0.2 * np.sin(2.0 * np.pi * 2.1 * t_s)

        return np.array([sa, av, max(0.2, hp)], dtype=float)


def project_ecg(
    time_s: np.ndarray,
    states: np.ndarray,
    patient: PatientParams,
    fs_hz: int,
) -> np.ndarray:
    """Project oscillator states into a single ECG-like lead.

    The oscillator states set timing and broad rhythm dynamics, while this
    projection adds rhythm-specific ECG morphology. This keeps the generator
    medium-fidelity, but avoids representing every abnormal rhythm as the same
    Gaussian QRS pulse with different frequencies.
    """

    x_sa = states[:, 0]
    x_av = states[:, 2]
    x_hp = states[:, 4]
    hp_velocity = np.gradient(x_hp, 1.0 / fs_hz)
    events = _qrs_event_indices(x_hp, fs_hz, patient.rhythm)
    morph_rng = np.random.default_rng(patient.seed + 301)

    if patient.rhythm == RhythmScenario.MONOMORPHIC_VT:
        qrs = _qrs_complex_train(
            events,
            len(time_s),
            fs_hz,
            patient.qrs_width_s,
            "wide_monomorphic",
            morph_rng,
            patient.irregularity,
        )
        ecg = 0.03 * x_sa + 0.04 * x_av + 0.16 * x_hp + 1.35 * qrs
        ecg += 0.015 * hp_velocity
    elif patient.rhythm == RhythmScenario.POLYMORPHIC_VT:
        qrs = _qrs_complex_train(
            events,
            len(time_s),
            fs_hz,
            patient.qrs_width_s,
            "wide_polymorphic",
            morph_rng,
            patient.irregularity,
        )
        wobble = 1.0 + 0.18 * np.sin(2.0 * np.pi * 0.29 * time_s + 0.4)
        ecg = wobble * (0.03 * x_sa + 0.05 * x_av + 0.12 * x_hp + 1.25 * qrs)
        ecg += 0.012 * hp_velocity
    elif patient.rhythm == RhythmScenario.VF_LIKE:
        fibrillatory = _fibrillatory_wave(time_s, patient.irregularity, morph_rng)
        ecg = 0.03 * x_av + 0.15 * x_hp + fibrillatory
    elif patient.rhythm == RhythmScenario.SVT_FLUTTER:
        qrs = _qrs_complex_train(
            events,
            len(time_s),
            fs_hz,
            patient.qrs_width_s,
            "narrow",
            morph_rng,
            patient.irregularity,
        )
        flutter = _flutter_wave(time_s, patient.sa_frequency_hz * 2.0, morph_rng)
        ecg = 0.04 * x_sa + 0.08 * x_av + 0.10 * x_hp + 1.05 * qrs + 0.20 * flutter
    else:
        qrs = _qrs_complex_train(
            events,
            len(time_s),
            fs_hz,
            patient.qrs_width_s,
            "narrow",
            morph_rng,
            patient.irregularity,
        )
        p_t = _p_t_wave_train(events, len(time_s), fs_hz, patient.qrs_width_s)
        ecg = 0.08 * x_sa + 0.13 * x_av + 0.12 * x_hp + 1.05 * qrs + 0.18 * p_t

    rng = np.random.default_rng(patient.seed + 17)
    baseline = patient.artifact_level * np.sin(2.0 * np.pi * 0.33 * time_s)
    powerline = 0.15 * patient.artifact_level * np.sin(2.0 * np.pi * 50.0 * time_s)
    noise = rng.normal(0.0, patient.noise_std, size=len(time_s))
    ecg = ecg + baseline + powerline + noise

    centered = ecg - np.median(ecg)
    scale = np.percentile(np.abs(centered), 95)
    if scale > 1e-8:
        centered = centered / scale
    return centered.astype(float)


def _qrs_event_indices(
    x_hp: np.ndarray,
    fs_hz: int,
    rhythm: RhythmScenario,
) -> list[int]:
    """Select ventricular activation events from His-Purkinje maxima."""

    if len(x_hp) < 3:
        return []
    threshold = np.median(x_hp) + 0.35 * np.std(x_hp)
    peaks = np.flatnonzero(
        (x_hp[1:-1] > x_hp[:-2])
        & (x_hp[1:-1] >= x_hp[2:])
        & (x_hp[1:-1] > threshold)
    ) + 1
    refractory_s = 0.2
    if rhythm == RhythmScenario.VF_LIKE:
        refractory_s = 0.09
    elif rhythm == RhythmScenario.POLYMORPHIC_VT:
        refractory_s = 0.15
    refractory = max(1, int(round(refractory_s * fs_hz)))
    selected: list[int] = []
    for peak in peaks:
        if not selected or peak - selected[-1] >= refractory:
            selected.append(int(peak))
        elif x_hp[peak] > x_hp[selected[-1]]:
            selected[-1] = int(peak)
    return selected


def _qrs_complex_train(
    events: list[int],
    n_samples: int,
    fs_hz: int,
    qrs_width_s: float,
    morphology: str,
    rng: np.random.Generator,
    irregularity: float,
) -> np.ndarray:
    """Create rhythm-specific QRS complexes from ventricular activation events."""

    pulses = np.zeros(n_samples, dtype=float)
    if not events:
        return pulses

    if morphology == "narrow":
        for center in events:
            _add_gaussian(pulses, center - int(round(0.018 * fs_hz)), 0.008 * fs_hz, -0.12)
            _add_gaussian(pulses, center, max(1.0, 0.018 * fs_hz), 1.08)
            _add_gaussian(pulses, center + int(round(0.026 * fs_hz)), 0.012 * fs_hz, -0.28)
        return pulses

    if morphology == "wide_monomorphic":
        polarity = 1.0 if rng.random() >= 0.35 else -1.0
        phase = rng.uniform(0.0, 2.0 * np.pi)
        for beat_idx, center in enumerate(events):
            width = max(0.075, qrs_width_s)
            timing_shift_s = irregularity * (
                0.20 * np.sin(phase + 0.73 * beat_idx)
                + 0.045 * rng.normal()
            )
            c = center + int(round(timing_shift_s * fs_hz))
            _add_gaussian(pulses, c - int(round(0.036 * fs_hz)), 0.38 * width * fs_hz, 0.66 * polarity)
            _add_gaussian(pulses, c + int(round(0.014 * fs_hz)), 0.42 * width * fs_hz, -0.94 * polarity)
            _add_gaussian(pulses, c + int(round(0.078 * fs_hz)), 0.34 * width * fs_hz, 0.34 * polarity)
        return pulses

    if morphology == "wide_polymorphic":
        phase = rng.uniform(0.0, 2.0 * np.pi)
        for beat_idx, center in enumerate(events):
            theta = phase + 0.86 * beat_idx
            polarity = np.sin(theta)
            amplitude = 0.85 + 0.35 * np.cos(theta + 0.7)
            width = qrs_width_s * (1.0 + 0.25 * np.sin(theta + 1.2))
            width = float(np.clip(width, 0.10, 0.22))
            jitter = int(round(irregularity * fs_hz * 0.018 * np.sin(theta * 1.7)))
            c = center + jitter
            _add_gaussian(pulses, c - int(round(0.045 * fs_hz)), 0.28 * width * fs_hz, amplitude * polarity)
            _add_gaussian(pulses, c + int(round(0.018 * fs_hz)), 0.32 * width * fs_hz, -0.82 * amplitude * polarity)
            _add_gaussian(pulses, c + int(round(0.082 * fs_hz)), 0.30 * width * fs_hz, 0.42 * amplitude * np.cos(theta))
        return pulses

    raise ValueError(f"Unknown QRS morphology: {morphology}")


def _p_t_wave_train(
    events: list[int],
    n_samples: int,
    fs_hz: int,
    qrs_width_s: float,
) -> np.ndarray:
    waves = np.zeros(n_samples, dtype=float)
    for center in events:
        _add_gaussian(waves, center - int(round(0.16 * fs_hz)), 0.035 * fs_hz, 0.10)
        _add_gaussian(waves, center + int(round(0.22 * fs_hz)), 0.085 * fs_hz, 0.16)
    return waves


def _flutter_wave(
    time_s: np.ndarray,
    frequency_hz: float,
    rng: np.random.Generator,
) -> np.ndarray:
    phase = rng.uniform(0.0, 2.0 * np.pi)
    frequency_hz = float(np.clip(frequency_hz, 4.2, 6.5))
    return (
        0.80 * np.sin(2.0 * np.pi * frequency_hz * time_s + phase)
        + 0.28 * np.sin(4.0 * np.pi * frequency_hz * time_s + phase + 0.8)
    )


def _fibrillatory_wave(
    time_s: np.ndarray,
    irregularity: float,
    rng: np.random.Generator,
) -> np.ndarray:
    freqs = np.array([2.4, 3.1, 4.2, 5.4, 6.6], dtype=float)
    freqs *= rng.uniform(0.90, 1.10, size=len(freqs))
    phases = rng.uniform(0.0, 2.0 * np.pi, size=len(freqs))
    amps = rng.uniform(0.08, 0.22, size=len(freqs))
    wave = np.zeros_like(time_s, dtype=float)
    for freq, phase, amp in zip(freqs, phases, amps):
        modulation = 0.035 * irregularity * np.sin(2.0 * np.pi * rng.uniform(0.3, 1.0) * time_s + phase)
        wave += amp * np.sin(2.0 * np.pi * freq * time_s + phase + modulation)

    envelope = (
        0.85
        + 0.28 * np.sin(2.0 * np.pi * 0.73 * time_s + phases[0])
        + 0.16 * np.sin(2.0 * np.pi * 1.37 * time_s + phases[1])
    )
    coarse_noise = rng.normal(0.0, 0.018 + 0.025 * irregularity, size=len(time_s))
    smooth_kernel = np.ones(7, dtype=float) / 7.0
    coarse_noise = np.convolve(coarse_noise, smooth_kernel, mode="same")
    return envelope * wave + coarse_noise


def _add_gaussian(
    signal: np.ndarray,
    center: int,
    sigma_samples: float,
    amplitude: float,
) -> None:
    sigma = max(1.0, float(sigma_samples))
    radius = int(max(2, round(3.0 * sigma)))
    left = max(0, int(center) - radius)
    right = min(len(signal), int(center) + radius + 1)
    if left >= right:
        return
    local = np.arange(left, right, dtype=float) - float(center)
    signal[left:right] += float(amplitude) * np.exp(-0.5 * (local / sigma) ** 2)
