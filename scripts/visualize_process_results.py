from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


ACTION_LABELS = {
    "synchronized_cardioversion": "Sync CV",
    "unsynchronized_defibrillation": "Defib",
    "atp_burst_pacing": "ATP",
    "resonant_drift_pacing": "Drift",
    "adaptive_low_energy_pacing": "Adaptive",
}
POLICY_LABELS = {
    "selector_linucb": "Selector",
    "conservative_selector": "Conservative",
    "acls_rule": "ACLS",
    "oracle": "Oracle",
    "always_synchronized_cardioversion": "Always Sync CV",
    "always_unsynchronized_defibrillation": "Always Defib",
    "always_atp": "Always ATP",
    "always_resonant_drift": "Always Drift",
    "always_adaptive": "Always Adaptive",
}
PROFILE_ORDER = [
    "clean",
    "mild",
    "moderate",
    "severe",
    "real_estimated",
    "real_asystole",
    "real_bradycardia",
    "real_tachycardia",
    "real_ventricular_flutter_fib",
    "real_ventricular_tachycardia",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path, default=Path("outputs/versioned_runs/v001_full_pipeline"))
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    run_dir = args.run_dir
    output_dir = args.output_dir or run_dir / "process_visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, str] = {}
    outputs["pipeline_durations"] = str(plot_pipeline_durations(run_dir, output_dir))
    outputs["phase2_core_metrics"] = str(plot_phase2_core_metrics(run_dir, output_dir))
    outputs["calibration_checks"] = str(plot_calibration_checks(run_dir, output_dir))
    outputs["selector_policy_comparison"] = str(plot_selector_policy_comparison(run_dir, output_dir))
    outputs["decision_boundary_copy"] = str(copy_decision_boundary(run_dir, output_dir))
    outputs["bootstrap_reward_ci"] = str(plot_bootstrap_reward_ci(run_dir, output_dir))
    outputs["selector_stability"] = str(plot_selector_stability(run_dir, output_dir))
    outputs["noise_ood_robustness"] = str(plot_noise_robustness(run_dir, output_dir))
    outputs["fallback_sweep"] = str(plot_fallback_sweep(run_dir, output_dir))

    manifest = {
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "figures": outputs,
    }
    manifest_path = output_dir / "process_visualization_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_path = output_dir / "PROCESS_VISUALIZATION_INDEX.md"
    index_path.write_text(render_index(outputs), encoding="utf-8")
    print(json.dumps({**manifest, "manifest": str(manifest_path), "index": str(index_path)}, indent=2))


def plot_pipeline_durations(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = read_json(run_dir / "run_manifest.json")
    steps = manifest["steps"]
    names = [step["name"] for step in steps]
    minutes = [float(step["duration_s"]) / 60.0 for step in steps]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    bars = ax.barh(range(len(names)), minutes, color="#4f7cac")
    ax.set_yticks(range(len(names)), labels=names)
    ax.invert_yaxis()
    ax.set_xlabel("Duration (minutes)")
    ax.set_title("Pipeline Step Durations")
    ax.grid(axis="x", alpha=0.25)
    for bar, value in zip(bars, minutes):
        ax.text(value + max(minutes) * 0.01, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center")
    fig.tight_layout()
    path = output_dir / "00_pipeline_step_durations.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_phase2_core_metrics(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = read_csv(run_dir / "figures" / "phase2_matrix_summary.csv")
    scenarios = unique_in_order(row["scenario"] for row in rows)
    algorithms = unique_in_order(row["algorithm"] for row in rows)
    metrics = [
        ("success_rate", "Success Rate", ".2f"),
        ("mean_reward", "Mean Reward", ".1f"),
        ("mean_time_s", "Mean Time (s)", ".1f"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.0), constrained_layout=True)
    for ax, (metric, title, fmt) in zip(axes, metrics):
        matrix = matrix_from_rows(rows, scenarios, algorithms, metric)
        im = ax.imshow(matrix, aspect="auto", cmap="viridis")
        ax.set_title(title)
        ax.set_xticks(range(len(algorithms)), labels=[ACTION_LABELS.get(a, a) for a in algorithms], rotation=35, ha="right")
        ax.set_yticks(range(len(scenarios)), labels=scenarios)
        for y in range(matrix.shape[0]):
            for x in range(matrix.shape[1]):
                ax.text(x, y, format(matrix[y, x], fmt), ha="center", va="center", color="white", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    path = output_dir / "01_phase2_core_metric_heatmaps.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_calibration_checks(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report = read_json(run_dir / "calibration_report.json")
    checks = report["checks"]
    labels = [
        f"{item['scenario']}\n{ACTION_LABELS.get(item['algorithm'], item['algorithm'])}\n{item['metric']}"
        for item in checks
    ]
    values = np.asarray([float(item["value"]) for item in checks])
    mins = np.asarray([float(item["target_min"]) for item in checks])
    maxs = np.asarray([float(item["target_max"]) for item in checks])
    y = np.arange(len(checks))

    fig, ax = plt.subplots(figsize=(11, 6.0))
    ax.hlines(y, mins, maxs, color="#93a3b1", linewidth=7, alpha=0.85, label="Target range")
    colors = ["#2f855a" if item["status"] == "pass" else "#c53030" for item in checks]
    ax.scatter(values, y, s=70, color=colors, zorder=3, label="Observed value")
    ax.set_yticks(y, labels=labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Metric value")
    ax.set_title(f"Calibration Checks (pass rate {float(report.get('pass_rate', 0.0)):.2f})")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    path = output_dir / "02_calibration_target_ranges.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_selector_policy_comparison(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = read_csv(run_dir / "selector_report.csv")
    order = ["selector_linucb", "acls_rule", "oracle", "always_adaptive", "always_unsynchronized_defibrillation"]
    rows = [find_row(rows, "policy", item) for item in order if find_row(rows, "policy", item)]
    labels = [POLICY_LABELS.get(row["policy"], row["policy"]) for row in rows]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    for ax, metric, title, color in [
        (axes[0], "mean_reward", "Mean Reward", "#4f7cac"),
        (axes[1], "success_rate", "Success Rate", "#4e8f55"),
        (axes[2], "oracle_gap", "Oracle Gap", "#b9473f"),
    ]:
        values = [float(row[metric]) for row in rows]
        ax.bar(range(len(rows)), values, color=color)
        ax.set_title(title)
        ax.set_xticks(range(len(rows)), labels=labels, rotation=35, ha="right")
        ax.grid(axis="y", alpha=0.25)
        for idx, value in enumerate(values):
            ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    path = output_dir / "03_selector_policy_comparison.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def copy_decision_boundary(run_dir: Path, output_dir: Path) -> Path:
    source = run_dir / "figures" / "decision_boundary.png"
    target = output_dir / "04_decision_boundary_selector_vs_acls.png"
    shutil.copyfile(source, target)
    return target


def plot_bootstrap_reward_ci(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [row for row in read_csv(run_dir / "bootstrap_matrix_ci.csv") if row["metric"] == "reward"]
    best_by_scenario = {}
    for row in rows:
        scenario = row["scenario"]
        if scenario not in best_by_scenario or float(row["mean"]) > float(best_by_scenario[scenario]["mean"]):
            best_by_scenario[scenario] = row
    scenarios = sorted(best_by_scenario)
    labels = [f"{s}\n{ACTION_LABELS.get(best_by_scenario[s]['algorithm'], best_by_scenario[s]['algorithm'])}" for s in scenarios]
    means = np.asarray([float(best_by_scenario[s]["mean"]) for s in scenarios])
    lows = np.asarray([float(best_by_scenario[s]["ci_low"]) for s in scenarios])
    highs = np.asarray([float(best_by_scenario[s]["ci_high"]) for s in scenarios])

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.errorbar(
        range(len(scenarios)),
        means,
        yerr=np.vstack([means - lows, highs - means]),
        fmt="o",
        markersize=8,
        capsize=6,
        color="#4f7cac",
        ecolor="#6b7280",
    )
    ax.set_xticks(range(len(scenarios)), labels=labels)
    ax.set_ylabel("Mean reward with bootstrap CI")
    ax.set_title("Bootstrap CI For Best Reward By Scenario")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "05_bootstrap_best_reward_ci.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_selector_stability(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = read_csv(run_dir / "selector_stability.csv")
    policies = ["selector_linucb", "acls_rule", "oracle", "always_adaptive"]
    reward = {row["policy"]: row for row in rows if row["metric"] == "mean_reward"}
    success = {row["policy"]: row for row in rows if row["metric"] == "success_rate"}

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    for ax, data, title in [
        (axes[0], reward, "Reward Across Seeds"),
        (axes[1], success, "Success Rate Across Seeds"),
    ]:
        xs = np.arange(len(policies))
        means = np.asarray([float(data[p]["mean"]) for p in policies])
        stds = np.asarray([float(data[p]["std"]) for p in policies])
        ax.bar(xs, means, yerr=stds, capsize=5, color="#7a5aa6")
        ax.set_xticks(xs, labels=[POLICY_LABELS[p] for p in policies], rotation=25, ha="right")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    path = output_dir / "06_selector_stability_across_seeds.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_noise_robustness(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = read_csv(run_dir / "noise_ood_sweep.csv")
    policies = ["selector_linucb", "acls_rule", "oracle", "always_adaptive"]
    profiles = [p for p in PROFILE_ORDER if any(row["profile"] == p for row in rows)]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), constrained_layout=True)
    for ax, metric, title in [
        (axes[0], "mean_reward", "Reward Under Noise/OOD"),
        (axes[1], "success_rate", "Success Under Noise/OOD"),
    ]:
        for policy in policies:
            values = []
            used_profiles = []
            for profile in profiles:
                row = find_row_multi(rows, {"profile": profile, "policy": policy})
                if row:
                    values.append(float(row[metric]))
                    used_profiles.append(profile)
            ax.plot(used_profiles, values, marker="o", linewidth=2, label=POLICY_LABELS.get(policy, policy))
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=35)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean reward")
    axes[1].set_ylabel("Success rate")
    axes[0].legend(fontsize=8)
    path = output_dir / "07_noise_ood_robustness.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_fallback_sweep(run_dir: Path, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = read_csv(run_dir / "fallback_threshold_sweep.csv")
    profiles = [p for p in PROFILE_ORDER if any(row["profile"] == p for row in rows)]
    series = {
        "Best Conservative": [],
        "Selector": [],
        "ACLS": [],
        "Oracle": [],
    }
    for profile in profiles:
        conservative = [
            float(row["mean_reward"])
            for row in rows
            if row["profile"] == profile and row["policy"] == "conservative_selector"
        ]
        selector = [
            float(row["mean_reward"])
            for row in rows
            if row["profile"] == profile and row["policy"] == "selector_linucb"
        ]
        acls = [
            float(row["mean_reward"])
            for row in rows
            if row["profile"] == profile and row["policy"] == "acls_rule"
        ]
        oracle = [
            float(row["mean_reward"])
            for row in rows
            if row["profile"] == profile and row["policy"] == "oracle"
        ]
        series["Best Conservative"].append(max(conservative) if conservative else np.nan)
        series["Selector"].append(selector[0] if selector else np.nan)
        series["ACLS"].append(acls[0] if acls else np.nan)
        series["Oracle"].append(oracle[0] if oracle else np.nan)

    fig, ax = plt.subplots(figsize=(13.5, 5.2))
    for label, values in series.items():
        ax.plot(profiles, values, marker="o", linewidth=2, label=label)
    ax.set_title("Fallback Threshold Sweep: Best Conservative Selector By Profile")
    ax.set_ylabel("Mean reward")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    path = output_dir / "08_fallback_threshold_sweep.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def render_index(outputs: dict[str, str]) -> str:
    lines = [
        "# Process Visualization Index",
        "",
        "These figures visualize each completed pipeline process in `v001_full_pipeline`.",
        "",
        "| Process | Figure | Meaning |",
        "| --- | --- | --- |",
        f"| Pipeline progress | `{Path(outputs['pipeline_durations']).name}` | Which steps consumed most runtime. |",
        f"| Phase 2 algorithm matrix | `{Path(outputs['phase2_core_metrics']).name}` | Success, reward, and time by rhythm scenario and algorithm. |",
        f"| Calibration | `{Path(outputs['calibration_checks']).name}` | Whether simulated values fall inside configured target ranges. |",
        f"| Selector report | `{Path(outputs['selector_policy_comparison']).name}` | Selector vs ACLS vs oracle vs fixed-action baselines. |",
        f"| Decision boundary | `{Path(outputs['decision_boundary_copy']).name}` | Learned selector choices vs ACLS choices across QRS width and RR variability. |",
        f"| Bootstrap CI | `{Path(outputs['bootstrap_reward_ci']).name}` | Uncertainty intervals for the best reward in each scenario. |",
        f"| Selector stability | `{Path(outputs['selector_stability']).name}` | Reward and success variation across selector seeds. |",
        f"| Noise/OOD robustness | `{Path(outputs['noise_ood_robustness']).name}` | How reward and success change as noise increases. |",
        f"| Fallback sweep | `{Path(outputs['fallback_sweep']).name}` | Whether conservative fallback thresholds improve robustness. |",
        "",
        "Main visual conclusion: the pipeline works end-to-end, but the learned selector",
        "still trails the ACLS baseline in the main held-out report and degrades under",
        "moderate/severe noise.",
        "",
    ]
    return "\n".join(lines)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def unique_in_order(values: Iterable[str]) -> list[str]:
    out = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def matrix_from_rows(rows: list[dict[str, str]], scenarios: list[str], algorithms: list[str], metric: str) -> np.ndarray:
    lookup = {(row["scenario"], row["algorithm"]): float(row[metric]) for row in rows}
    matrix = np.zeros((len(scenarios), len(algorithms)), dtype=float)
    for y, scenario in enumerate(scenarios):
        for x, algorithm in enumerate(algorithms):
            matrix[y, x] = lookup[(scenario, algorithm)]
    return matrix


def find_row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
    for row in rows:
        if row.get(key) == value:
            return row
    return None


def find_row_multi(rows: list[dict[str, str]], values: dict[str, str]) -> dict[str, str] | None:
    for row in rows:
        if all(row.get(key) == value for key, value in values.items()):
            return row
    return None


if __name__ == "__main__":
    main()
