"""Reporting utilities for phase matrix, selector, and decision-boundary figures."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .algorithms import all_algorithms
from .bandit import LinUCB, mean_oracle_gap, oracle_actions
from .experiments import MatrixRow, run_algorithm_matrix, summarize_matrix
from .features import feature_vector
from .reward import RewardWeights, acls_rule_action
from .types import ObservationWindow, RhythmScenario


SCENARIO_ORDER = tuple(scenario.value for scenario in RhythmScenario)
ALGORITHM_ORDER = tuple(algorithm.name for algorithm in all_algorithms())
ACTION_LABELS = {
    0: "Sync CV",
    1: "Defib",
    2: "ATP",
    3: "Drift",
    4: "Adaptive",
}


@dataclass(frozen=True)
class SelectorReport:
    n_train: int
    n_eval: int
    policy_summary: dict[str, dict[str, float]]
    train_indices: list[int]
    eval_indices: list[int]


def matrix_for_metric(
    rows: list[MatrixRow],
    metric: str,
) -> np.ndarray:
    summary = summarize_matrix(rows)
    matrix = np.full((len(SCENARIO_ORDER), len(ALGORITHM_ORDER)), np.nan, dtype=float)
    for scenario_idx, scenario in enumerate(SCENARIO_ORDER):
        for action_idx, algorithm in enumerate(ALGORITHM_ORDER):
            key = f"{scenario}:{algorithm}"
            if key in summary and metric in summary[key]:
                matrix[scenario_idx, action_idx] = summary[key][metric]
    return matrix


def metric_matrices_from_rows(rows: list[MatrixRow], n_actions: int = 5) -> dict[str, np.ndarray]:
    if len(rows) % n_actions != 0:
        raise ValueError("Expected rows to contain one contiguous block per patient.")
    n_contexts = len(rows) // n_actions
    metrics = {
        "reward": np.zeros((n_contexts, n_actions), dtype=float),
        "success": np.zeros((n_contexts, n_actions), dtype=float),
        "energy": np.zeros((n_contexts, n_actions), dtype=float),
        "time_to_termination_s": np.zeros((n_contexts, n_actions), dtype=float),
        "safety_violations": np.zeros((n_contexts, n_actions), dtype=float),
    }
    for idx, row in enumerate(rows):
        context_idx = idx // n_actions
        action_idx = row.action_id
        metrics["reward"][context_idx, action_idx] = row.reward
        metrics["success"][context_idx, action_idx] = float(row.success)
        metrics["energy"][context_idx, action_idx] = row.energy
        metrics["time_to_termination_s"][context_idx, action_idx] = row.time_to_termination_s
        metrics["safety_violations"][context_idx, action_idx] = row.safety_violations
    return metrics


def save_matrix_csv(
    rows: list[MatrixRow],
    output: str | Path,
    metrics: tuple[str, ...] = (
        "mean_reward",
        "success_rate",
        "mean_energy",
        "mean_time_s",
        "mean_safety_violations",
    ),
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_matrix(rows)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario", "algorithm", *metrics],
        )
        writer.writeheader()
        for scenario in SCENARIO_ORDER:
            for algorithm in ALGORITHM_ORDER:
                key = f"{scenario}:{algorithm}"
                row = {"scenario": scenario, "algorithm": algorithm}
                row.update({metric: summary.get(key, {}).get(metric, "") for metric in metrics})
                writer.writerow(row)


def save_heatmap(
    matrix: np.ndarray,
    output: str | Path,
    title: str,
    colorbar_label: str,
    fmt: str = ".2f",
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5.8), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_title(title)
    ax.set_xlabel("Algorithm")
    ax.set_ylabel("Scenario")
    ax.set_xticks(np.arange(len(ALGORITHM_ORDER)), [ACTION_LABELS[i] for i in range(len(ALGORITHM_ORDER))])
    ax.set_yticks(np.arange(len(SCENARIO_ORDER)), SCENARIO_ORDER)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", rotation_mode="anchor")

    for y in range(matrix.shape[0]):
        for x in range(matrix.shape[1]):
            value = matrix[y, x]
            if np.isfinite(value):
                ax.text(x, y, format(value, fmt), ha="center", va="center", color="white", fontsize=8)

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(colorbar_label)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def generate_phase2_heatmaps(
    patients_per_scenario: int,
    output_dir: str | Path,
    horizon_s: float = 30.0,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> dict[str, str]:
    rows, _, _, _, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        horizon_s=horizon_s,
        weights=weights,
        n_jobs=n_jobs,
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_matrix_csv(rows, output_dir / "phase2_matrix_summary.csv")

    specs = {
        "success_rate": ("Success Rate", "success rate", ".2f"),
        "mean_energy": ("Mean Energy", "dimensionless energy", ".3f"),
        "mean_time_s": ("Mean Time To Termination", "seconds", ".1f"),
        "mean_safety_violations": ("Mean Safety Violations", "count", ".2f"),
        "mean_reward": ("Mean Reward", "reward", ".1f"),
    }
    outputs: dict[str, str] = {
        "summary_csv": str(output_dir / "phase2_matrix_summary.csv")
    }
    for metric, (title, colorbar, fmt) in specs.items():
        path = output_dir / f"phase2_{metric}.png"
        save_heatmap(matrix_for_metric(rows, metric), path, title, colorbar, fmt=fmt)
        outputs[metric] = str(path)
    return outputs


def build_selector_report(
    patients_per_scenario: int,
    train_fraction: float = 0.7,
    seed: int = 7,
    horizon_s: float = 30.0,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> SelectorReport:
    rows, _, contexts, reward_matrix, acls_actions = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        horizon_s=horizon_s,
        weights=weights,
        n_jobs=n_jobs,
    )
    metrics = metric_matrices_from_rows(rows)
    n_contexts = len(contexts)
    rng = np.random.default_rng(seed)
    indices = np.arange(n_contexts)
    rng.shuffle(indices)
    split = int(np.clip(round(train_fraction * n_contexts), 1, n_contexts))
    train_indices = np.sort(indices[:split])
    eval_indices = np.sort(indices[split:]) if split < n_contexts else np.sort(indices)

    model = LinUCB(n_actions=5, n_features=contexts.shape[1], alpha=0.5)
    for idx in train_indices:
        for action in range(5):
            model.update(action, contexts[idx], reward_matrix[idx, action])

    selector_actions = model.predict_many(contexts)
    oracle = oracle_actions(reward_matrix)
    policies = {
        "selector_linucb": selector_actions,
        "acls_rule": acls_actions,
        "oracle": oracle,
        "always_synchronized_cardioversion": np.zeros(n_contexts, dtype=int),
        "always_unsynchronized_defibrillation": np.ones(n_contexts, dtype=int),
        "always_atp": np.full(n_contexts, 2, dtype=int),
        "always_resonant_drift": np.full(n_contexts, 3, dtype=int),
        "always_adaptive": np.full(n_contexts, 4, dtype=int),
    }
    summary = {
        name: evaluate_policy(actions, reward_matrix, metrics, eval_indices)
        for name, actions in policies.items()
    }
    return SelectorReport(
        n_train=int(len(train_indices)),
        n_eval=int(len(eval_indices)),
        policy_summary=summary,
        train_indices=[int(idx) for idx in train_indices],
        eval_indices=[int(idx) for idx in eval_indices],
    )


def evaluate_policy(
    actions: np.ndarray,
    reward_matrix: np.ndarray,
    metric_matrices: dict[str, np.ndarray],
    indices: np.ndarray,
) -> dict[str, float]:
    selected = actions[indices]
    rewards = reward_matrix[indices, selected]
    return {
        "mean_reward": float(np.mean(rewards)),
        "oracle_gap": mean_oracle_gap(selected, reward_matrix[indices]),
        "success_rate": float(np.mean(metric_matrices["success"][indices, selected])),
        "mean_energy": float(np.mean(metric_matrices["energy"][indices, selected])),
        "mean_time_s": float(np.mean(metric_matrices["time_to_termination_s"][indices, selected])),
        "mean_safety_violations": float(np.mean(metric_matrices["safety_violations"][indices, selected])),
    }


def save_selector_report(
    report: SelectorReport,
    output_json: str | Path,
    output_csv: str | Path | None = None,
) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(
            {
                "n_train": report.n_train,
                "n_eval": report.n_eval,
                "train_indices": report.train_indices,
                "eval_indices": report.eval_indices,
                "policy_summary": report.policy_summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if output_csv is not None:
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
            writer = csv.DictWriter(handle, fieldnames=["policy", *metrics])
            writer.writeheader()
            for policy, values in report.policy_summary.items():
                writer.writerow({"policy": policy, **{metric: values[metric] for metric in metrics}})


def decision_boundary_grid(
    patients_per_scenario: int,
    grid_size: int = 60,
    seed: int = 7,
    horizon_s: float = 30.0,
    heart_rate_bpm: float = 180.0,
    dominant_frequency_hz: float = 3.0,
    spectral_entropy: float = 0.4,
    sample_entropy: float = 0.8,
    signal_quality: float = 0.7,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> dict[str, Any]:
    _, _, contexts, reward_matrix, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        horizon_s=horizon_s,
        weights=weights,
        n_jobs=n_jobs,
    )
    model = LinUCB(n_actions=5, n_features=contexts.shape[1], alpha=0.5)
    for idx in range(len(contexts)):
        for action in range(5):
            model.update(action, contexts[idx], reward_matrix[idx, action])

    qrs_values = np.linspace(0.06, 0.20, grid_size)
    rr_cv_values = np.linspace(0.0, 0.60, grid_size)
    selector = np.zeros((grid_size, grid_size), dtype=int)
    acls = np.zeros((grid_size, grid_size), dtype=int)

    for y, rr_cv in enumerate(rr_cv_values):
        for x, qrs_width in enumerate(qrs_values):
            features = {
                "heart_rate_bpm": heart_rate_bpm,
                "rr_cv": float(rr_cv),
                "regularity": float(1.0 / (1.0 + rr_cv)),
                "qrs_width_s": float(qrs_width),
                "dominant_frequency_hz": dominant_frequency_hz,
                "spectral_entropy": spectral_entropy,
                "sample_entropy": sample_entropy,
                "signal_quality": signal_quality,
            }
            selector[y, x] = model.select(feature_vector(features))
            observation = ObservationWindow(
                ecg=np.array([], dtype=float),
                fs_hz=250,
                duration_s=0.0,
                features=features,
            )
            acls[y, x] = acls_rule_action(observation)

    return {
        "qrs_values": qrs_values,
        "rr_cv_values": rr_cv_values,
        "selector": selector,
        "acls": acls,
    }


def save_decision_boundary(
    grid: dict[str, Any],
    output_png: str | Path,
    output_csv: str | Path | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.colors as mcolors
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    cmap = mcolors.ListedColormap(["#2f6f9f", "#b9473f", "#4e8f55", "#7a5aa6", "#c08a2d"])
    bounds = np.arange(-0.5, 5.5, 1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    qrs = grid["qrs_values"]
    rr = grid["rr_cv_values"]
    extent = [float(qrs[0]), float(qrs[-1]), float(rr[0]), float(rr[-1])]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    panels = [("Learned Selector", grid["selector"]), ("ACLS Rule Baseline", grid["acls"])]
    for ax, (title, values) in zip(axes, panels):
        ax.imshow(values, origin="lower", aspect="auto", extent=extent, cmap=cmap, norm=norm)
        ax.axvline(0.12, color="white", linestyle="--", linewidth=1.2)
        ax.set_title(title)
        ax.set_xlabel("QRS width proxy (s)")
        ax.set_ylabel("RR coefficient of variation")

    patches = [
        mpatches.Patch(color=cmap(action), label=ACTION_LABELS[action])
        for action in range(5)
    ]
    fig.legend(handles=patches, loc="outside lower center", ncols=5)
    fig.savefig(output_png, dpi=180)
    plt.close(fig)

    if output_csv is not None:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["qrs_width_s", "rr_cv", "selector_action", "acls_action"],
            )
            writer.writeheader()
            for y, rr_value in enumerate(rr):
                for x, qrs_value in enumerate(qrs):
                    writer.writerow(
                        {
                            "qrs_width_s": float(qrs_value),
                            "rr_cv": float(rr_value),
                            "selector_action": int(grid["selector"][y, x]),
                            "acls_action": int(grid["acls"][y, x]),
                        }
                    )
