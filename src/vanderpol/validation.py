"""Feature validation and synthetic-vs-real comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .experiments import observe_patient
from .features import classify_acls_features
from .simulator import GoisSaviSimulator
from .types import RhythmScenario


FEATURE_KEYS = (
    "heart_rate_bpm",
    "rr_cv",
    "qrs_width_s",
    "dominant_frequency_hz",
    "spectral_entropy",
    "sample_entropy",
    "signal_quality",
)


@dataclass(frozen=True)
class FeatureSummary:
    group: str
    n: int
    means: dict[str, float]
    stds: dict[str, float]


def summarize_feature_dicts(
    feature_dicts: list[dict[str, float]],
    group: str,
) -> FeatureSummary:
    if not feature_dicts:
        return FeatureSummary(group=group, n=0, means={}, stds={})
    matrix = np.array(
        [[features.get(key, np.nan) for key in FEATURE_KEYS] for features in feature_dicts],
        dtype=float,
    )
    means = np.array(
        [
            float(np.nanmean(column)) if np.isfinite(column).any() else float("nan")
            for column in matrix.T
        ],
        dtype=float,
    )
    stds = np.array(
        [
            float(np.nanstd(column)) if np.isfinite(column).any() else float("nan")
            for column in matrix.T
        ],
        dtype=float,
    )
    return FeatureSummary(
        group=group,
        n=len(feature_dicts),
        means={key: float(value) for key, value in zip(FEATURE_KEYS, means)},
        stds={key: float(value) for key, value in zip(FEATURE_KEYS, stds)},
    )


def synthetic_feature_summaries(
    patients_per_scenario: int = 20,
    fs_hz: int = 250,
    observation_s: float = 4.0,
    variability: float = 0.2,
) -> list[FeatureSummary]:
    simulator = GoisSaviSimulator(fs_hz=fs_hz)
    summaries = []
    for scenario_index, scenario in enumerate(RhythmScenario):
        feature_dicts = []
        for idx in range(patients_per_scenario):
            _, observation, _ = observe_patient(
                simulator,
                scenario,
                seed=50_000 + 10_000 * scenario_index + idx,
                observation_s=observation_s,
                variability=variability,
            )
            feature_dicts.append(observation.features)
        summaries.append(summarize_feature_dicts(feature_dicts, scenario.value))
    return summaries


def label_counts(feature_dicts: list[dict[str, float]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for features in feature_dicts:
        label = classify_acls_features(features)
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def compare_feature_summaries(
    synthetic: FeatureSummary,
    real: FeatureSummary,
) -> dict[str, float]:
    """Compute absolute standardized mean gaps for common feature keys."""

    gaps: dict[str, float] = {}
    for key in FEATURE_KEYS:
        if key not in synthetic.means or key not in real.means:
            continue
        pooled = np.sqrt(
            0.5
            * (
                synthetic.stds.get(key, 0.0) ** 2
                + real.stds.get(key, 0.0) ** 2
            )
        )
        gaps[key] = float(abs(synthetic.means[key] - real.means[key]) / (pooled + 1e-8))
    return gaps
