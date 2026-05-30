"""Five electrical stimulation protocol implementations."""

from __future__ import annotations

import numpy as np

from ..types import ObservationWindow, PatientParams, RhythmScenario, StimulusProtocol
from .base import StimulationAlgorithm


class SynchronizedCardioversion(StimulationAlgorithm):
    action_id = 0
    name = "synchronized_cardioversion"

    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        rr_s = _cycle_length_s(observation)
        sync_delay = min(0.18, max(0.02, 0.08 * rr_s))
        return StimulusProtocol(
            name=self.name,
            pulse_times_s=(sync_delay,),
            amplitudes=(5.0,),
            pulse_width_s=0.012,
            metadata={"sync": "r_peak_proxy"},
        )

    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        table = {
            RhythmScenario.NSR: 0.02,
            RhythmScenario.SVT_FLUTTER: 0.88,
            RhythmScenario.MONOMORPHIC_VT: 0.78,
            RhythmScenario.POLYMORPHIC_VT: 0.38,
            RhythmScenario.VF_LIKE: 0.04,
        }
        return table[patient.rhythm]


class UnsynchronizedDefibrillation(StimulationAlgorithm):
    action_id = 1
    name = "unsynchronized_defibrillation"

    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        return StimulusProtocol(
            name=self.name,
            pulse_times_s=(0.04,),
            amplitudes=(7.0,),
            pulse_width_s=0.014,
            metadata={"sync": "none"},
        )

    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        table = {
            RhythmScenario.NSR: 0.01,
            RhythmScenario.SVT_FLUTTER: 0.42,
            RhythmScenario.MONOMORPHIC_VT: 0.58,
            RhythmScenario.POLYMORPHIC_VT: 0.78,
            RhythmScenario.VF_LIKE: 0.88,
        }
        return table[patient.rhythm]


class ATPBurstPacing(StimulationAlgorithm):
    action_id = 2
    name = "atp_burst_pacing"

    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        cycle = _cycle_length_s(observation)
        interval = float(np.clip(0.86 * cycle, 0.18, 0.42))
        pulse_times = tuple(0.12 + interval * i for i in range(8))
        return StimulusProtocol(
            name=self.name,
            pulse_times_s=pulse_times,
            amplitudes=tuple([1.0] * len(pulse_times)),
            pulse_width_s=0.01,
            metadata={"cycle_length_s": cycle, "interval_s": interval},
        )

    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        table = {
            RhythmScenario.NSR: 0.05,
            RhythmScenario.SVT_FLUTTER: 0.62,
            RhythmScenario.MONOMORPHIC_VT: 0.86,
            RhythmScenario.POLYMORPHIC_VT: 0.12,
            RhythmScenario.VF_LIKE: 0.02,
        }
        return table[patient.rhythm]


class ResonantDriftPacing(StimulationAlgorithm):
    action_id = 3
    name = "resonant_drift_pacing"

    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        dom = observation.features.get("dominant_frequency_hz", patient.hp_frequency_hz)
        period = float(np.clip(1.0 / max(dom, 0.5), 0.16, 0.7))
        pulse_times = tuple(0.1 + period * i for i in range(18))
        return StimulusProtocol(
            name=self.name,
            pulse_times_s=pulse_times,
            amplitudes=tuple([0.45] * len(pulse_times)),
            pulse_width_s=0.008,
            metadata={"phase_target_rad": 0.0, "period_s": period},
        )

    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        table = {
            RhythmScenario.NSR: 0.03,
            RhythmScenario.SVT_FLUTTER: 0.5,
            RhythmScenario.MONOMORPHIC_VT: 0.74,
            RhythmScenario.POLYMORPHIC_VT: 0.32,
            RhythmScenario.VF_LIKE: 0.13,
        }
        return table[patient.rhythm]


class AdaptiveLowEnergyPacing(StimulationAlgorithm):
    action_id = 4
    name = "adaptive_low_energy_pacing"

    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        hr = observation.features.get("heart_rate_bpm", 0.0)
        regularity = observation.features.get("regularity", 0.0)
        if hr < 130.0 and regularity > 0.75:
            return StimulusProtocol(
                name=self.name,
                pulse_times_s=(),
                amplitudes=(),
                pulse_width_s=0.0,
                metadata={"mode": "withhold"},
            )

        cycle = _cycle_length_s(observation)
        interval = float(np.clip(0.9 * cycle, 0.17, 0.5))
        pulse_times = tuple(0.15 + interval * i for i in range(10))
        amplitudes = tuple(float(0.55 + 0.05 * min(i, 5)) for i in range(len(pulse_times)))
        return StimulusProtocol(
            name=self.name,
            pulse_times_s=pulse_times,
            amplitudes=amplitudes,
            pulse_width_s=0.008,
            metadata={"mode": "ramp_phase_reset", "interval_s": interval},
        )

    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        table = {
            RhythmScenario.NSR: 0.98,
            RhythmScenario.SVT_FLUTTER: 0.68,
            RhythmScenario.MONOMORPHIC_VT: 0.78,
            RhythmScenario.POLYMORPHIC_VT: 0.43,
            RhythmScenario.VF_LIKE: 0.22,
        }
        return table[patient.rhythm]


def _cycle_length_s(observation: ObservationWindow) -> float:
    hr = observation.features.get("heart_rate_bpm", 0.0)
    if hr <= 1e-6:
        dom = observation.features.get("dominant_frequency_hz", 2.5)
        return float(np.clip(1.0 / max(dom, 0.5), 0.2, 1.0))
    return float(np.clip(60.0 / hr, 0.2, 1.2))
