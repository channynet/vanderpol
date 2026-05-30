"""Reward functions and rule-based baselines."""

from __future__ import annotations

from dataclasses import dataclass

from .features import classify_acls_features
from .types import EpisodeResult, ObservationWindow


@dataclass(frozen=True)
class RewardWeights:
    success_bonus: float = 100.0
    energy_weight: float = 0.0
    time_weight: float = 1.0
    safety_weight: float = 0.0


def episode_reward(
    result: EpisodeResult,
    weights: RewardWeights = RewardWeights(),
) -> float:
    """Score an episode using only measured episode outputs.

    The default reward intentionally avoids hidden scenario labels, medically
    inferred safety heuristics, and dimensionless simulation energy. Safety or
    energy penalties can still be enabled by setting their weights explicitly,
    but the baseline reward is based on directly logged success and termination
    time.
    """

    return float(
        (weights.success_bonus if result.success else 0.0)
        - weights.energy_weight * result.energy
        - weights.time_weight * result.time_to_termination_s
        - weights.safety_weight * result.safety_violations
    )


def acls_rule_action(observation: ObservationWindow) -> int:
    """Map ACLS-style ECG labels to the five electrical actions."""

    label = classify_acls_features(observation.features)
    if label == "normal_or_sinus":
        return 4
    if label == "vf_or_chaotic":
        return 1
    if label == "regular_wide_tachycardia":
        return 2
    if label == "irregular_wide_tachycardia":
        return 1
    if label == "regular_narrow_tachycardia":
        return 0
    if label == "irregular_narrow_tachycardia":
        return 0
    return 4
