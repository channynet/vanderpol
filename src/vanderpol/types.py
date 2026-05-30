"""Core data contracts shared by simulator, algorithms, and selectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class RhythmScenario(str, Enum):
    NSR = "nsr"
    SVT_FLUTTER = "svt_flutter"
    MONOMORPHIC_VT = "monomorphic_vt"
    POLYMORPHIC_VT = "polymorphic_vt"
    VF_LIKE = "vf_like"


@dataclass(frozen=True)
class PatientParams:
    """Synthetic patient and rhythm parameters.

    The model is intentionally medium-fidelity: parameters expose the same
    control knobs that will later be calibrated against ECG and ICD literature.
    """

    rhythm: RhythmScenario
    seed: int
    sa_frequency_hz: float
    av_frequency_hz: float
    hp_frequency_hz: float
    mu_sa: float
    mu_av: float
    mu_hp: float
    coupling_sa_av: float
    coupling_av_hp: float
    coupling_hp_sa: float
    delay_sa_av_s: float
    delay_av_hp_s: float
    qrs_width_s: float
    noise_std: float
    artifact_level: float
    treatment_sensitivity: float
    phase_sensitivity: float
    energy_tolerance: float
    irregularity: float


@dataclass(frozen=True)
class ObservationWindow:
    ecg: np.ndarray
    fs_hz: int
    duration_s: float
    features: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class StimulusProtocol:
    name: str
    pulse_times_s: tuple[float, ...]
    amplitudes: tuple[float, ...]
    pulse_width_s: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def energy(self) -> float:
        return float(
            sum((amp * amp) * self.pulse_width_s for amp in self.amplitudes)
        )

    def stimulus_at(self, t_s: float) -> float:
        half_width = 0.5 * self.pulse_width_s
        total = 0.0
        for pulse_t, amp in zip(self.pulse_times_s, self.amplitudes):
            if abs(t_s - pulse_t) <= half_width:
                total += amp
        return total


@dataclass(frozen=True)
class SimulationTrace:
    time_s: np.ndarray
    states: np.ndarray
    ecg: np.ndarray
    fs_hz: int
    protocol: StimulusProtocol | None = None


@dataclass(frozen=True)
class EpisodeResult:
    algorithm: str
    action_id: int
    patient: PatientParams
    success: bool
    restored_rhythm: RhythmScenario
    energy: float
    time_to_termination_s: float
    safety_violations: int
    protocol: StimulusProtocol
    trace_summary: dict[str, float]
