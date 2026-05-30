"""Stage 6: real-noise-informed robustness and conservative selector fallback."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .bandit import LinUCB, oracle_actions
from .data.wfdb_loader import ExternalDataError, iter_observation_windows, load_record
from .features import classify_acls_features, feature_vector
from .noise import NoiseProfile
from .reporting import evaluate_policy, metric_matrices_from_rows
from .reward import acls_rule_action
from .stage5 import run_noisy_algorithm_matrix
from .types import ObservationWindow, RhythmScenario


@dataclass(frozen=True)
class ConservativeFallbackConfig:
    min_signal_quality: float = 0.42
    high_entropy_threshold: float = 0.62
    high_rr_cv_threshold: float = 0.30
    vf_dominant_frequency_hz: float = 5.0
    normal_hr_bpm: float = 120.0
    normal_rr_cv: float = 0.25
    normal_qrs_s: float = 0.12


@dataclass(frozen=True)
class RealNoiseStats:
    dataset: str
    n_windows: int
    feature_means: dict[str, float]
    feature_stds: dict[str, float]
    feature_quantiles: dict[str, dict[str, float]]
    acls_label_counts: dict[str, int]
    recommended_profile: NoiseProfile


FEATURE_KEYS = (
    "heart_rate_bpm",
    "rr_cv",
    "qrs_width_s",
    "dominant_frequency_hz",
    "spectral_entropy",
    "sample_entropy",
    "signal_quality",
)


def estimate_real_noise_stats(
    root: str | Path,
    dataset: str,
    records: Iterable[str],
    channel: int = 0,
    window_s: float = 4.0,
    stride_s: float = 30.0,
    max_windows_per_record: int = 8,
) -> RealNoiseStats:
    """Estimate feature-level real-noise statistics from local WFDB records."""

    feature_rows: list[dict[str, float]] = []
    label_counts: dict[str, int] = {}
    for record_name in records:
        record = load_record(root, record_name, dataset=dataset, channel=channel)
        for _, observation in iter_observation_windows(
            record,
            window_s=window_s,
            stride_s=stride_s,
            max_windows=max_windows_per_record,
        ):
            feature_rows.append(observation.features)
            label = classify_acls_features(observation.features)
            label_counts[label] = label_counts.get(label, 0) + 1

    if not feature_rows:
        raise ExternalDataError("No windows available for real-noise estimation.")

    matrix = np.asarray(
        [[features.get(key, np.nan) for key in FEATURE_KEYS] for features in feature_rows],
        dtype=float,
    )
    means = _nan_column_stat(matrix, np.nanmean)
    stds = _nan_column_stat(matrix, np.nanstd)
    quantiles = {
        key: {
            "p05": float(np.nanquantile(matrix[:, idx], 0.05)),
            "p25": float(np.nanquantile(matrix[:, idx], 0.25)),
            "p50": float(np.nanquantile(matrix[:, idx], 0.50)),
            "p75": float(np.nanquantile(matrix[:, idx], 0.75)),
            "p95": float(np.nanquantile(matrix[:, idx], 0.95)),
        }
        for idx, key in enumerate(FEATURE_KEYS)
    }
    feature_means = {key: float(means[idx]) for idx, key in enumerate(FEATURE_KEYS)}
    feature_stds = {key: float(stds[idx]) for idx, key in enumerate(FEATURE_KEYS)}

    return RealNoiseStats(
        dataset=dataset,
        n_windows=len(feature_rows),
        feature_means=feature_means,
        feature_stds=feature_stds,
        feature_quantiles=quantiles,
        acls_label_counts=dict(sorted(label_counts.items())),
        recommended_profile=recommend_noise_profile(feature_means, feature_stds, quantiles),
    )


def recommend_noise_profile(
    means: dict[str, float],
    stds: dict[str, float],
    quantiles: dict[str, dict[str, float]],
) -> NoiseProfile:
    """Map real feature spread into a conservative synthetic corruption profile."""

    signal_quality = means.get("signal_quality", 0.55)
    entropy = means.get("spectral_entropy", 0.5)
    rr_cv_spread = stds.get("rr_cv", 0.15)
    sample_entropy = means.get("sample_entropy", 0.4)

    severity = np.clip(
        0.45 * (1.0 - signal_quality)
        + 0.25 * entropy
        + 0.20 * min(1.0, rr_cv_spread / 0.35)
        + 0.10 * min(1.0, sample_entropy / 1.2),
        0.0,
        1.0,
    )
    return NoiseProfile(
        name="real_estimated",
        gaussian_std=float(0.03 + 0.14 * severity),
        baseline_wander_amp=float(0.04 + 0.18 * severity),
        muscle_amp=float(0.015 + 0.07 * severity),
        powerline_amp=float(0.01 + 0.04 * severity),
        dropout_fraction=float(0.02 * severity),
        clip_value=1.4 if severity > 0.65 else None,
    )


def conservative_action(
    model_action: int,
    observation: ObservationWindow,
    config: ConservativeFallbackConfig = ConservativeFallbackConfig(),
) -> tuple[int, str]:
    """Return a final action plus the reason for using or overriding the model."""

    features = observation.features
    hr = features.get("heart_rate_bpm", 0.0)
    rr_cv = features.get("rr_cv", 1.0)
    qrs = features.get("qrs_width_s", 0.18)
    entropy = features.get("spectral_entropy", 1.0)
    dom = features.get("dominant_frequency_hz", 0.0)
    sqi = features.get("signal_quality", 0.0)

    if hr < config.normal_hr_bpm and rr_cv < config.normal_rr_cv and qrs < config.normal_qrs_s:
        return 4, "normal_withhold"
    if (
        dom >= config.vf_dominant_frequency_hz
        and hr >= 130.0
        and (entropy >= config.high_entropy_threshold or rr_cv >= config.high_rr_cv_threshold)
    ):
        return 1, "shockable_chaotic"
    if sqi < config.min_signal_quality:
        return acls_rule_action(observation), "low_signal_quality_acls"
    if rr_cv >= config.high_rr_cv_threshold and model_action in {2, 3}:
        return acls_rule_action(observation), "irregular_rhythm_acls"
    return model_action, "model"


def conservative_noise_ood_sweep(
    patients_per_scenario: int,
    profiles: list[NoiseProfile],
    config: ConservativeFallbackConfig = ConservativeFallbackConfig(),
    train_fraction: float = 1.0,
    train_variability: float = 0.2,
    eval_variability: float = 0.2,
    horizon_s: float = 30.0,
    seed: int = 7,
    n_jobs: int | str | None = 1,
) -> dict[str, Any]:
    from .experiments import run_algorithm_matrix

    _, _, clean_contexts, clean_rewards, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        variability=train_variability,
        horizon_s=horizon_s,
        n_jobs=n_jobs,
    )
    model = LinUCB(n_actions=5, n_features=clean_contexts.shape[1], alpha=0.5)
    train_indices = _training_indices(len(clean_contexts), train_fraction, seed)
    for idx in train_indices:
        for action in range(5):
            model.update(action, clean_contexts[idx], clean_rewards[idx, action])

    reports = []
    for profile in profiles:
        rows, _, contexts, rewards, acls_actions = run_noisy_algorithm_matrix(
            patients_per_scenario=patients_per_scenario,
            profile=profile,
            variability=eval_variability,
            horizon_s=horizon_s,
            n_jobs=n_jobs,
        )
        observations = _reconstruct_noisy_observations(
            patients_per_scenario=patients_per_scenario,
            profile=profile,
            variability=eval_variability,
        )
        model_actions = model.predict_many(contexts)
        conservative = []
        fallback_reasons: dict[str, int] = {}
        for action, observation in zip(model_actions, observations):
            final_action, reason = conservative_action(action, observation, config)
            conservative.append(final_action)
            fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1

        metric_matrices = metric_matrices_from_rows(rows)
        indices = np.arange(len(contexts))
        oracle = oracle_actions(rewards)
        reports.append(
            {
                "profile": profile.__dict__,
                "n_contexts": int(len(contexts)),
                "fallback_reasons": dict(sorted(fallback_reasons.items())),
                "policies": {
                    "selector_linucb": evaluate_policy(model_actions, rewards, metric_matrices, indices),
                    "conservative_selector": evaluate_policy(
                        np.asarray(conservative, dtype=int),
                        rewards,
                        metric_matrices,
                        indices,
                    ),
                    "acls_rule": evaluate_policy(acls_actions, rewards, metric_matrices, indices),
                    "oracle": evaluate_policy(oracle, rewards, metric_matrices, indices),
                },
            }
        )
    return {
        "patients_per_scenario": patients_per_scenario,
        "train_fraction": train_fraction,
        "train_variability": train_variability,
        "eval_variability": eval_variability,
        "horizon_s": horizon_s,
        "fallback_config": config.__dict__,
        "n_train_contexts": int(len(train_indices)),
        "profiles": reports,
    }


def save_real_noise_stats(stats: RealNoiseStats, output_json: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(
            {
                "dataset": stats.dataset,
                "n_windows": stats.n_windows,
                "feature_means": stats.feature_means,
                "feature_stds": stats.feature_stds,
                "feature_quantiles": stats.feature_quantiles,
                "acls_label_counts": stats.acls_label_counts,
                "recommended_profile": stats.recommended_profile.__dict__,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def save_conservative_sweep(report: dict[str, Any], output_json: str | Path, output_csv: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "profile",
        "policy",
        "mean_reward",
        "oracle_gap",
        "success_rate",
        "mean_energy",
        "mean_time_s",
        "mean_safety_violations",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for profile_report in report["profiles"]:
            profile_name = profile_report["profile"]["name"]
            for policy, values in profile_report["policies"].items():
                writer.writerow({"profile": profile_name, "policy": policy, **values})


def load_noise_profile_from_stats(path: str | Path) -> NoiseProfile:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    data = payload["recommended_profile"]
    return NoiseProfile(**data)


def _reconstruct_noisy_observations(
    patients_per_scenario: int,
    profile: NoiseProfile,
    variability: float,
) -> list[ObservationWindow]:
    from .noise import corrupt_ecg
    from .scenarios import sample_patient
    from .simulator import GoisSaviSimulator
    from .features import make_observation

    simulator = GoisSaviSimulator(fs_hz=250)
    observations: list[ObservationWindow] = []
    for scenario_index, scenario in enumerate(RhythmScenario):
        for patient_index in range(patients_per_scenario):
            seed = 1000 + scenario_index * 10_000 + patient_index
            patient = sample_patient(scenario, seed=seed, variability=variability)
            trace = simulator.simulate(patient, 4.0)
            corrupted = corrupt_ecg(trace.ecg, trace.fs_hz, profile=profile, seed=900_000 + seed)
            observations.append(make_observation(corrupted, trace.fs_hz))
    return observations


def _training_indices(n_contexts: int, train_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    indices = np.arange(n_contexts)
    rng.shuffle(indices)
    n_train = int(np.clip(round(train_fraction * n_contexts), 1, n_contexts))
    return np.sort(indices[:n_train])


def _nan_column_stat(matrix: np.ndarray, fn) -> np.ndarray:
    values = []
    for column in matrix.T:
        values.append(float(fn(column)) if np.isfinite(column).any() else float("nan"))
    return np.asarray(values, dtype=float)
