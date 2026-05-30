"""Experiment orchestration helpers used by scripts and tests."""

from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np

from .algorithms import all_algorithms
from .features import feature_vector, make_observation
from .reward import RewardWeights, acls_rule_action, episode_reward
from .scenarios import sample_patient
from .simulator import GoisSaviSimulator
from .types import EpisodeResult, RhythmScenario


@dataclass(frozen=True)
class MatrixRow:
    scenario: RhythmScenario
    patient_seed: int
    action_id: int
    algorithm: str
    reward: float
    success: bool
    energy: float
    time_to_termination_s: float
    safety_violations: int


def observe_patient(
    simulator: GoisSaviSimulator,
    scenario: RhythmScenario | str,
    seed: int,
    observation_s: float = 4.0,
    variability: float = 0.2,
):
    patient = sample_patient(scenario, seed=seed, variability=variability)
    trace = simulator.simulate(patient, observation_s)
    observation = make_observation(trace.ecg, trace.fs_hz)
    return patient, observation, trace


def run_algorithm_matrix(
    patients_per_scenario: int = 3,
    fs_hz: int = 250,
    observation_s: float = 4.0,
    horizon_s: float = 30.0,
    variability: float = 0.2,
    seed_offset: int = 1000,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> tuple[list[MatrixRow], list[EpisodeResult], np.ndarray, np.ndarray, np.ndarray]:
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
            "patients_per_scenario": patients_per_scenario,
            "fs_hz": fs_hz,
            "observation_s": observation_s,
            "horizon_s": horizon_s,
            "variability": variability,
            "seed_offset": seed_offset,
            "weights": weights,
        }
        for scenario_index, scenario in enumerate(RhythmScenario)
        for patient_index in range(patients_per_scenario)
    ]
    worker_count = resolve_n_jobs(n_jobs, len(tasks))

    if worker_count == 1:
        patient_outputs = [_run_algorithm_patient(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            patient_outputs = list(executor.map(_run_algorithm_patient, tasks))

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


def resolve_n_jobs(n_jobs: int | str | None, n_tasks: int) -> int:
    """Resolve a user-facing worker setting into a bounded process count."""

    if n_tasks <= 1 or n_jobs is None:
        return 1
    if isinstance(n_jobs, str):
        value = n_jobs.strip().lower()
        if value in {"", "1", "false", "none"}:
            return 1
        if value in {"auto", "all"}:
            requested = os.cpu_count() or 1
        else:
            requested = int(value)
    else:
        requested = int(n_jobs)

    if requested == 0:
        requested = os.cpu_count() or 1
    elif requested < 0:
        requested = max(1, (os.cpu_count() or 1) + 1 + requested)
    return max(1, min(requested, n_tasks))


def _run_algorithm_patient(task: dict[str, Any]) -> tuple[list[MatrixRow], list[EpisodeResult], np.ndarray, list[float], int]:
    simulator = GoisSaviSimulator(fs_hz=int(task["fs_hz"]))
    algorithms = list(all_algorithms())
    scenario = RhythmScenario(str(task["scenario"]))
    seed = int(task["seed_offset"]) + int(task["scenario_index"]) * 10_000 + int(task["patient_index"])
    patient, observation, _ = observe_patient(
        simulator,
        scenario,
        seed=seed,
        observation_s=float(task["observation_s"]),
        variability=float(task["variability"]),
    )
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


def summarize_matrix(rows: list[MatrixRow]) -> dict[str, dict[str, float]]:
    grouped: dict[tuple[str, str], list[MatrixRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.scenario.value, row.algorithm)].append(row)

    summary: dict[str, dict[str, float]] = {}
    for (scenario, algorithm), group in grouped.items():
        key = f"{scenario}:{algorithm}"
        summary[key] = {
            "mean_reward": float(np.mean([row.reward for row in group])),
            "success_rate": float(np.mean([row.success for row in group])),
            "mean_energy": float(np.mean([row.energy for row in group])),
            "mean_time_s": float(np.mean([row.time_to_termination_s for row in group])),
            "mean_safety_violations": float(
                np.mean([row.safety_violations for row in group])
            ),
        }
    return summary
