"""Base class for stimulation algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np

from ..features import classify_acls_features, extract_features
from ..simulator import GoisSaviSimulator
from ..types import (
    EpisodeResult,
    ObservationWindow,
    PatientParams,
    RhythmScenario,
    StimulusProtocol,
)


class StimulationAlgorithm(ABC):
    action_id: int
    name: str

    @abstractmethod
    def make_protocol(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> StimulusProtocol:
        raise NotImplementedError

    @abstractmethod
    def base_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        raise NotImplementedError

    def run(
        self,
        patient: PatientParams,
        observation: ObservationWindow,
        simulator: GoisSaviSimulator,
        horizon_s: float = 30.0,
    ) -> EpisodeResult:
        protocol = self.make_protocol(patient, observation)
        trace = simulator.simulate(patient, horizon_s, protocol=protocol)
        post_features = extract_features(trace.ecg[-observation.fs_hz * 4 :], trace.fs_hz)

        probability = self._adjust_success_probability(patient, observation)
        if patient.rhythm == RhythmScenario.NSR and protocol.metadata.get("mode") == "withhold":
            probability = 1.0
            success = True
        else:
            rng = np.random.default_rng(patient.seed * 1009 + self.action_id * 9173)
            success = bool(rng.random() < probability)
        time_to_termination = self._time_to_termination(protocol, success, horizon_s)
        violations = self._safety_violations(patient, observation, protocol, success)

        restored = RhythmScenario.NSR if success else patient.rhythm
        return EpisodeResult(
            algorithm=self.name,
            action_id=self.action_id,
            patient=patient,
            success=success,
            restored_rhythm=restored,
            energy=protocol.energy,
            time_to_termination_s=time_to_termination,
            safety_violations=violations,
            protocol=protocol,
            trace_summary={
                "post_hr_bpm": post_features["heart_rate_bpm"],
                "post_rr_cv": post_features["rr_cv"],
                "success_probability": probability,
                "acls_label": float(_label_code(classify_acls_features(observation.features))),
            },
        )

    def _adjust_success_probability(
        self, patient: PatientParams, observation: ObservationWindow
    ) -> float:
        base = self.base_success_probability(patient, observation)
        regularity = observation.features.get("regularity", 0.5)
        quality = observation.features.get("signal_quality", 0.5)
        entropy = observation.features.get("spectral_entropy", 0.5)
        sensitivity = patient.treatment_sensitivity
        adjusted = base * (0.75 + 0.35 * sensitivity)

        if self.action_id in {2, 3, 4}:
            adjusted *= 0.65 + 0.45 * regularity
        if self.action_id == 3:
            adjusted *= 0.65 + 0.5 * patient.phase_sensitivity
            adjusted *= 0.75 + 0.35 * quality
        if self.action_id == 1 and entropy > 0.55:
            adjusted *= 1.08

        return float(np.clip(adjusted, 0.0, 0.98))

    def _time_to_termination(
        self, protocol: StimulusProtocol, success: bool, horizon_s: float
    ) -> float:
        if not success:
            return float(horizon_s)
        if not protocol.pulse_times_s:
            return 0.0
        return float(min(horizon_s, max(protocol.pulse_times_s) + 1.0 + 0.25 * self.action_id))

    def _safety_violations(
        self,
        patient: PatientParams,
        observation: ObservationWindow,
        protocol: StimulusProtocol,
        success: bool,
    ) -> int:
        violations = 0
        hr = observation.features.get("heart_rate_bpm", 0.0)
        entropy = observation.features.get("spectral_entropy", 0.0)
        regularity = observation.features.get("regularity", 0.0)

        if patient.rhythm == RhythmScenario.NSR and protocol.energy > 0.0:
            violations += 2
        if self.action_id == 0 and entropy > 0.62:
            violations += 1
        if self.action_id in {2, 3} and regularity < 0.65:
            violations += 1
        if self.action_id == 2 and patient.rhythm in {
            RhythmScenario.POLYMORPHIC_VT,
            RhythmScenario.VF_LIKE,
        }:
            violations += 1
        if hr < 100.0 and protocol.energy > 0.5:
            violations += 1
        if not success and protocol.energy > patient.energy_tolerance:
            violations += 1
        return violations


def all_algorithms() -> Sequence[StimulationAlgorithm]:
    from .protocols import (
        AdaptiveLowEnergyPacing,
        ATPBurstPacing,
        ResonantDriftPacing,
        SynchronizedCardioversion,
        UnsynchronizedDefibrillation,
    )

    return [
        SynchronizedCardioversion(),
        UnsynchronizedDefibrillation(),
        ATPBurstPacing(),
        ResonantDriftPacing(),
        AdaptiveLowEnergyPacing(),
    ]


def _label_code(label: str) -> int:
    labels = {
        "normal_or_sinus": 0,
        "regular_narrow_tachycardia": 1,
        "irregular_narrow_tachycardia": 2,
        "regular_wide_tachycardia": 3,
        "irregular_wide_tachycardia": 4,
        "vf_or_chaotic": 5,
        "indeterminate": 6,
    }
    return labels.get(label, 6)
