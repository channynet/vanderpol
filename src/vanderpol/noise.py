"""Synthetic ECG corruption profiles for robustness and OOD sweeps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NoiseProfile:
    name: str
    gaussian_std: float = 0.0
    baseline_wander_amp: float = 0.0
    muscle_amp: float = 0.0
    powerline_amp: float = 0.0
    dropout_fraction: float = 0.0
    clip_value: float | None = None


DEFAULT_NOISE_PROFILES: tuple[NoiseProfile, ...] = (
    NoiseProfile(name="clean"),
    NoiseProfile(
        name="mild",
        gaussian_std=0.03,
        baseline_wander_amp=0.04,
        muscle_amp=0.015,
        powerline_amp=0.01,
    ),
    NoiseProfile(
        name="moderate",
        gaussian_std=0.08,
        baseline_wander_amp=0.10,
        muscle_amp=0.04,
        powerline_amp=0.025,
        dropout_fraction=0.03,
    ),
    NoiseProfile(
        name="severe",
        gaussian_std=0.16,
        baseline_wander_amp=0.20,
        muscle_amp=0.08,
        powerline_amp=0.05,
        dropout_fraction=0.08,
        clip_value=1.4,
    ),
)


def get_noise_profiles(names: list[str] | None = None) -> list[NoiseProfile]:
    profiles = {profile.name: profile for profile in DEFAULT_NOISE_PROFILES}
    if names is None:
        return list(DEFAULT_NOISE_PROFILES)
    missing = [name for name in names if name not in profiles]
    if missing:
        known = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown noise profile(s): {missing}. Known: {known}.")
    return [profiles[name] for name in names]


def corrupt_ecg(
    ecg: np.ndarray,
    fs_hz: int,
    profile: NoiseProfile,
    seed: int,
) -> np.ndarray:
    """Apply deterministic observation corruption to an ECG window."""

    rng = np.random.default_rng(seed)
    ecg = np.asarray(ecg, dtype=float).copy()
    if profile.name == "clean":
        return ecg

    time_s = np.arange(len(ecg), dtype=float) / float(fs_hz)
    if profile.baseline_wander_amp:
        phase = rng.uniform(0.0, 2.0 * np.pi)
        ecg += profile.baseline_wander_amp * np.sin(2.0 * np.pi * 0.33 * time_s + phase)
    if profile.powerline_amp:
        phase = rng.uniform(0.0, 2.0 * np.pi)
        ecg += profile.powerline_amp * np.sin(2.0 * np.pi * 50.0 * time_s + phase)
    if profile.muscle_amp:
        white = rng.normal(0.0, profile.muscle_amp, size=len(ecg))
        high = white - np.convolve(white, np.ones(9) / 9.0, mode="same")
        ecg += high
    if profile.gaussian_std:
        ecg += rng.normal(0.0, profile.gaussian_std, size=len(ecg))
    if profile.dropout_fraction > 0.0 and len(ecg):
        dropout_n = int(round(profile.dropout_fraction * len(ecg)))
        if dropout_n > 0:
            start = int(rng.integers(0, max(1, len(ecg) - dropout_n + 1)))
            fill = float(np.median(ecg))
            ecg[start : start + dropout_n] = fill
    if profile.clip_value is not None:
        ecg = np.clip(ecg, -profile.clip_value, profile.clip_value)
    return ecg
