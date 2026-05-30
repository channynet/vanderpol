"""Stage 5 analysis: confidence intervals, seed stability, and noise/OOD sweeps."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np

from .algorithms import all_algorithms
from .bandit import LinUCB, oracle_actions
from .experiments import MatrixRow, run_algorithm_matrix, resolve_n_jobs
from .features import feature_vector, make_observation
from .noise import NoiseProfile, corrupt_ecg, get_noise_profiles
from .reporting import (
    ALGORITHM_ORDER,
    SCENARIO_ORDER,
    build_selector_report,
    evaluate_policy,
    metric_matrices_from_rows,
)
from .reward import RewardWeights, acls_rule_action, episode_reward
from .scenarios import sample_patient
from .simulator import GoisSaviSimulator
from .types import EpisodeResult, RhythmScenario


@dataclass(frozen=True)
class BootstrapCI:
    scenario: str
    algorithm: str
    metric: str
    mean: float
    ci_low: float
    ci_high: float
    n: int


def bootstrap_matrix_ci(
    rows: list[MatrixRow],
    metrics: tuple[str, ...] = (
        "reward",
        "success",
        "energy",
        "time_to_termination_s",
        "safety_violations",
    ),
    n_bootstrap: int = 500,
    seed: int = 7,
    alpha: float = 0.05,
) -> list[BootstrapCI]:
    """Bootstrap CIs for per-scenario/per-algorithm episode metrics."""

    rng = np.random.default_rng(seed)
    grouped: dict[tuple[str, str], list[MatrixRow]] = {}
    for row in rows:
        grouped.setdefault((row.scenario.value, row.algorithm), []).append(row)

    output: list[BootstrapCI] = []
    for scenario in SCENARIO_ORDER:
        for algorithm in ALGORITHM_ORDER:
            group = grouped.get((scenario, algorithm), [])
            if not group:
                continue
            for metric in metrics:
                values = np.asarray([_row_metric(row, metric) for row in group], dtype=float)
                samples = []
                for _ in range(n_bootstrap):
                    draw = rng.choice(values, size=len(values), replace=True)
                    samples.append(float(np.mean(draw)))
                low, high = np.quantile(samples, [alpha / 2.0, 1.0 - alpha / 2.0])
                output.append(
                    BootstrapCI(
                        scenario=scenario,
                        algorithm=algorithm,
                        metric=metric,
                        mean=float(np.mean(values)),
                        ci_low=float(low),
                        ci_high=float(high),
                        n=len(values),
                    )
                )
    return output


def save_bootstrap_ci(rows: list[BootstrapCI], output_csv: str | Path) -> None:
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario", "algorithm", "metric", "mean", "ci_low", "ci_high", "n"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def selector_stability_report(
    patients_per_scenario: int,
    seeds: Iterable[int],
    train_fraction: float = 0.7,
    horizon_s: float = 30.0,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> dict[str, Any]:
    """Run selector reports over multiple train/test split seeds."""

    seed_list = [int(seed) for seed in seeds]
    per_seed = []
    for seed in seed_list:
        report = build_selector_report(
            patients_per_scenario=patients_per_scenario,
            train_fraction=train_fraction,
            seed=seed,
            horizon_s=horizon_s,
            weights=weights,
            n_jobs=n_jobs,
        )
        per_seed.append(
            {
                "seed": seed,
                "n_train": report.n_train,
                "n_eval": report.n_eval,
                "policy_summary": report.policy_summary,
            }
        )
    return {
        "patients_per_scenario": patients_per_scenario,
        "train_fraction": train_fraction,
        "seeds": seed_list,
        "per_seed": per_seed,
        "aggregate": _aggregate_policy_metrics(per_seed),
    }


def save_selector_stability(report: dict[str, Any], output_json: str | Path, output_csv: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["policy", "metric", "mean", "std", "min", "max", "n_seeds"],
        )
        writer.writeheader()
        for policy, metrics in report["aggregate"].items():
            for metric, values in metrics.items():
                writer.writerow({"policy": policy, "metric": metric, **values})


def run_noisy_algorithm_matrix(
    patients_per_scenario: int,
    profile: NoiseProfile,
    fs_hz: int = 250,
    observation_s: float = 4.0,
    horizon_s: float = 30.0,
    variability: float = 0.2,
    seed_offset: int = 1000,
    noise_seed_offset: int = 900_000,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> tuple[list[MatrixRow], list[EpisodeResult], np.ndarray, np.ndarray, np.ndarray]:
    """Run the algorithm matrix with corrupted observation windows."""

    rows: list[MatrixRow] = []
    results: list[EpisodeResult] = []
    contexts = []
    reward_matrix = []
    acls_actions = []
    tasks = [
        {
            "scenario_index": scenario_index,
            "scenario": scenario.value,
            "patient_index": patient_index,
            "fs_hz": fs_hz,
            "observation_s": observation_s,
            "horizon_s": horizon_s,
            "variability": variability,
            "seed_offset": seed_offset,
            "noise_seed_offset": noise_seed_offset,
            "profile": profile,
            "weights": weights,
        }
        for scenario_index, scenario in enumerate(RhythmScenario)
        for patient_index in range(patients_per_scenario)
    ]
    worker_count = resolve_n_jobs(n_jobs, len(tasks))

    if worker_count == 1:
        patient_outputs = [_run_noisy_algorithm_patient(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            patient_outputs = list(executor.map(_run_noisy_algorithm_patient, tasks))

    for patient_rows, patient_results, context, patient_rewards, acls_action in patient_outputs:
        rows.extend(patient_rows)
        results.extend(patient_results)
        contexts.append(context)
        reward_matrix.append(patient_rewards)
        acls_actions.append(acls_action)

    return (
        rows,
        results,
        np.asarray(contexts, dtype=float),
        np.asarray(reward_matrix, dtype=float),
        np.asarray(acls_actions, dtype=int),
    )


def noise_ood_sweep(
    patients_per_scenario: int,
    profile_names: list[str] | None = None,
    train_fraction: float = 1.0,
    train_variability: float = 0.2,
    eval_variability: float = 0.2,
    horizon_s: float = 30.0,
    seed: int = 7,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
    progress_callback: Callable[..., None] | None = None,
) -> dict[str, Any]:
    """Train on clean synthetic episodes and evaluate under observation corruption."""

    if progress_callback:
        progress_callback(
            "noise_ood_sweep",
            "Building clean training matrix.",
            phase="clean_training",
            completed_profiles=0,
            total_profiles=0,
        )
    _, _, clean_contexts, clean_rewards, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        variability=train_variability,
        horizon_s=horizon_s,
        weights=weights,
        n_jobs=n_jobs,
    )
    model = LinUCB(n_actions=5, n_features=clean_contexts.shape[1], alpha=0.5)
    train_indices = _training_indices(len(clean_contexts), train_fraction, seed)
    for idx in train_indices:
        for action in range(5):
            model.update(action, clean_contexts[idx], clean_rewards[idx, action])

    profiles = get_noise_profiles(profile_names)
    profile_reports = []
    for profile_index, profile in enumerate(profiles, start=1):
        if progress_callback:
            progress_callback(
                "noise_ood_sweep",
                f"Evaluating noisy profile {profile_index}/{len(profiles)}: {profile.name}",
                phase="profile_eval",
                current_profile=profile.name,
                completed_profiles=profile_index - 1,
                total_profiles=len(profiles),
            )
        rows, _, contexts, rewards, acls_actions = run_noisy_algorithm_matrix(
            patients_per_scenario=patients_per_scenario,
            profile=profile,
            variability=eval_variability,
            horizon_s=horizon_s,
            weights=weights,
            n_jobs=n_jobs,
        )
        metric_matrices = metric_matrices_from_rows(rows)
        all_indices = np.arange(len(contexts))
        selector_actions = model.predict_many(contexts)
        oracle = oracle_actions(rewards)
        profile_reports.append(
            {
                "profile": profile.__dict__,
                "n_contexts": int(len(contexts)),
                "policies": {
                    "selector_linucb": evaluate_policy(
                        selector_actions,
                        rewards,
                        metric_matrices,
                        all_indices,
                    ),
                    "acls_rule": evaluate_policy(
                        acls_actions,
                        rewards,
                        metric_matrices,
                        all_indices,
                    ),
                    "oracle": evaluate_policy(
                        oracle,
                        rewards,
                        metric_matrices,
                        all_indices,
                    ),
                    "always_unsynchronized_defibrillation": evaluate_policy(
                        np.ones(len(contexts), dtype=int),
                        rewards,
                        metric_matrices,
                        all_indices,
                    ),
                    "always_adaptive": evaluate_policy(
                        np.full(len(contexts), 4, dtype=int),
                        rewards,
                        metric_matrices,
                        all_indices,
                    ),
                },
            }
        )
        if progress_callback:
            progress_callback(
                "noise_ood_sweep",
                f"Completed noisy profile {profile_index}/{len(profiles)}: {profile.name}",
                phase="profile_eval",
                current_profile=profile.name,
                completed_profiles=profile_index,
                total_profiles=len(profiles),
            )

    return {
        "patients_per_scenario": patients_per_scenario,
        "train_fraction": train_fraction,
        "train_variability": train_variability,
        "eval_variability": eval_variability,
        "horizon_s": horizon_s,
        "n_train_contexts": int(len(train_indices)),
        "profiles": profile_reports,
    }


def save_noise_ood_sweep(report: dict[str, Any], output_json: str | Path, output_csv: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    metrics = [
        "mean_reward",
        "oracle_gap",
        "success_rate",
        "mean_energy",
        "mean_time_s",
        "mean_safety_violations",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["profile", "policy", *metrics])
        writer.writeheader()
        for profile_report in report["profiles"]:
            profile_name = profile_report["profile"]["name"]
            for policy, values in profile_report["policies"].items():
                writer.writerow({"profile": profile_name, "policy": policy, **{metric: values[metric] for metric in metrics}})


def run_bootstrap_matrix_report(
    patients_per_scenario: int,
    n_bootstrap: int,
    horizon_s: float,
    seed: int = 7,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> list[BootstrapCI]:
    rows, _, _, _, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        horizon_s=horizon_s,
        weights=weights,
        n_jobs=n_jobs,
    )
    return bootstrap_matrix_ci(rows, n_bootstrap=n_bootstrap, seed=seed)


def _run_noisy_algorithm_patient(task: dict[str, Any]) -> tuple[list[MatrixRow], list[EpisodeResult], np.ndarray, list[float], int]:
    simulator = GoisSaviSimulator(fs_hz=int(task["fs_hz"]))
    algorithms = list(all_algorithms())
    scenario = RhythmScenario(str(task["scenario"]))
    seed = int(task["seed_offset"]) + int(task["scenario_index"]) * 10_000 + int(task["patient_index"])
    patient = sample_patient(scenario, seed=seed, variability=float(task["variability"]))
    trace = simulator.simulate(patient, float(task["observation_s"]))
    corrupted = corrupt_ecg(
        trace.ecg,
        trace.fs_hz,
        profile=task["profile"],
        seed=int(task["noise_seed_offset"]) + seed,
    )
    observation = make_observation(corrupted, trace.fs_hz)
    context = feature_vector(observation.features)
    acls_action = acls_rule_action(observation)
    weights = task["weights"]
    patient_rewards: list[float] = []
    rows: list[MatrixRow] = []
    results: list[EpisodeResult] = []

    for algorithm in algorithms:
        result = algorithm.run(
            patient,
            observation,
            simulator,
            horizon_s=float(task["horizon_s"]),
        )
        reward = episode_reward(result, weights)
        patient_rewards.append(reward)
        results.append(result)
        rows.append(
            MatrixRow(
                scenario=scenario,
                patient_seed=seed,
                action_id=result.action_id,
                algorithm=result.algorithm,
                reward=reward,
                success=result.success,
                energy=result.energy,
                time_to_termination_s=result.time_to_termination_s,
                safety_violations=result.safety_violations,
            )
        )
    return rows, results, context, patient_rewards, int(acls_action)


def _row_metric(row: MatrixRow, metric: str) -> float:
    if metric == "success":
        return float(row.success)
    if metric == "reward":
        return float(row.reward)
    if metric == "energy":
        return float(row.energy)
    if metric == "time_to_termination_s":
        return float(row.time_to_termination_s)
    if metric == "safety_violations":
        return float(row.safety_violations)
    raise ValueError(f"Unknown row metric: {metric}")


def _aggregate_policy_metrics(per_seed: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    by_policy: dict[str, dict[str, list[float]]] = {}
    for row in per_seed:
        for policy, metrics in row["policy_summary"].items():
            by_policy.setdefault(policy, {})
            for metric, value in metrics.items():
                by_policy[policy].setdefault(metric, []).append(float(value))

    aggregate: dict[str, dict[str, dict[str, float]]] = {}
    for policy, metrics in by_policy.items():
        aggregate[policy] = {}
        for metric, values in metrics.items():
            arr = np.asarray(values, dtype=float)
            aggregate[policy][metric] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n_seeds": int(len(arr)),
            }
    return aggregate


def _training_indices(n_contexts: int, train_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    indices = np.arange(n_contexts)
    rng.shuffle(indices)
    n_train = int(np.clip(round(train_fraction * n_contexts), 1, n_contexts))
    return np.sort(indices[:n_train])
