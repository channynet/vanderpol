"""Scenario presets and reproducible patient sampling."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .types import PatientParams, RhythmScenario


_PRESETS: dict[RhythmScenario, PatientParams] = {
    RhythmScenario.NSR: PatientParams(
        rhythm=RhythmScenario.NSR,
        seed=0,
        sa_frequency_hz=1.15,
        av_frequency_hz=1.15,
        hp_frequency_hz=1.15,
        mu_sa=1.0,
        mu_av=1.0,
        mu_hp=1.0,
        coupling_sa_av=0.35,
        coupling_av_hp=0.35,
        coupling_hp_sa=0.05,
        delay_sa_av_s=0.12,
        delay_av_hp_s=0.08,
        qrs_width_s=0.085,
        noise_std=0.025,
        artifact_level=0.01,
        treatment_sensitivity=1.0,
        phase_sensitivity=0.8,
        energy_tolerance=1.0,
        irregularity=0.03,
    ),
    RhythmScenario.SVT_FLUTTER: PatientParams(
        rhythm=RhythmScenario.SVT_FLUTTER,
        seed=0,
        sa_frequency_hz=2.35,
        av_frequency_hz=2.35,
        hp_frequency_hz=2.35,
        mu_sa=1.25,
        mu_av=1.15,
        mu_hp=1.05,
        coupling_sa_av=0.45,
        coupling_av_hp=0.35,
        coupling_hp_sa=0.02,
        delay_sa_av_s=0.08,
        delay_av_hp_s=0.06,
        qrs_width_s=0.09,
        noise_std=0.035,
        artifact_level=0.035,
        treatment_sensitivity=1.05,
        phase_sensitivity=0.85,
        energy_tolerance=1.0,
        irregularity=0.18,
    ),
    RhythmScenario.MONOMORPHIC_VT: PatientParams(
        rhythm=RhythmScenario.MONOMORPHIC_VT,
        seed=0,
        sa_frequency_hz=1.1,
        av_frequency_hz=1.4,
        hp_frequency_hz=2.45,
        mu_sa=0.9,
        mu_av=1.0,
        mu_hp=1.45,
        coupling_sa_av=0.08,
        coupling_av_hp=0.08,
        coupling_hp_sa=0.35,
        delay_sa_av_s=0.1,
        delay_av_hp_s=0.08,
        qrs_width_s=0.115,
        noise_std=0.045,
        artifact_level=0.04,
        treatment_sensitivity=1.1,
        phase_sensitivity=1.1,
        energy_tolerance=0.95,
        irregularity=0.36,
    ),
    RhythmScenario.POLYMORPHIC_VT: PatientParams(
        rhythm=RhythmScenario.POLYMORPHIC_VT,
        seed=0,
        sa_frequency_hz=1.1,
        av_frequency_hz=1.5,
        hp_frequency_hz=3.65,
        mu_sa=0.9,
        mu_av=1.0,
        mu_hp=1.7,
        coupling_sa_av=0.04,
        coupling_av_hp=0.05,
        coupling_hp_sa=0.45,
        delay_sa_av_s=0.1,
        delay_av_hp_s=0.08,
        qrs_width_s=0.17,
        noise_std=0.055,
        artifact_level=0.05,
        treatment_sensitivity=0.95,
        phase_sensitivity=0.65,
        energy_tolerance=0.9,
        irregularity=0.28,
    ),
    RhythmScenario.VF_LIKE: PatientParams(
        rhythm=RhythmScenario.VF_LIKE,
        seed=0,
        sa_frequency_hz=1.0,
        av_frequency_hz=1.8,
        hp_frequency_hz=3.30,
        mu_sa=0.8,
        mu_av=1.05,
        mu_hp=1.8,
        coupling_sa_av=0.02,
        coupling_av_hp=0.02,
        coupling_hp_sa=0.6,
        delay_sa_av_s=0.08,
        delay_av_hp_s=0.05,
        qrs_width_s=0.15,
        noise_std=0.040,
        artifact_level=0.045,
        treatment_sensitivity=0.9,
        phase_sensitivity=0.35,
        energy_tolerance=0.85,
        irregularity=0.42,
    ),
}


def scenario_names() -> list[str]:
    return [scenario.value for scenario in RhythmScenario]


def get_preset(scenario: RhythmScenario | str) -> PatientParams:
    scenario = RhythmScenario(scenario)
    return _PRESETS[scenario]


def sample_patient(
    scenario: RhythmScenario | str,
    seed: int,
    variability: float = 0.2,
) -> PatientParams:
    """Sample a deterministic synthetic patient around a scenario preset."""

    scenario = RhythmScenario(scenario)
    preset = _PRESETS[scenario]
    rng = np.random.default_rng(seed)

    def jitter(value: float, width: float = variability, floor: float = 0.0) -> float:
        multiplier = 1.0 + rng.uniform(-width, width)
        return max(floor, float(value * multiplier))

    return replace(
        preset,
        seed=int(seed),
        sa_frequency_hz=jitter(preset.sa_frequency_hz, floor=0.2),
        av_frequency_hz=jitter(preset.av_frequency_hz, floor=0.2),
        hp_frequency_hz=jitter(preset.hp_frequency_hz, floor=0.2),
        mu_sa=jitter(preset.mu_sa, 0.15, floor=0.2),
        mu_av=jitter(preset.mu_av, 0.15, floor=0.2),
        mu_hp=jitter(preset.mu_hp, 0.2, floor=0.2),
        coupling_sa_av=jitter(preset.coupling_sa_av, 0.25),
        coupling_av_hp=jitter(preset.coupling_av_hp, 0.25),
        coupling_hp_sa=jitter(preset.coupling_hp_sa, 0.25),
        qrs_width_s=jitter(preset.qrs_width_s, 0.2, floor=0.045),
        noise_std=jitter(preset.noise_std, 0.5),
        artifact_level=jitter(preset.artifact_level, 0.7),
        treatment_sensitivity=jitter(preset.treatment_sensitivity, 0.25, floor=0.35),
        phase_sensitivity=jitter(preset.phase_sensitivity, 0.3, floor=0.1),
        energy_tolerance=jitter(preset.energy_tolerance, 0.2, floor=0.2),
        irregularity=min(0.95, jitter(preset.irregularity, 0.4)),
    )
