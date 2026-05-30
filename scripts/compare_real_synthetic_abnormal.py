from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.experiments import observe_patient  # noqa: E402
from vanderpol.scenarios import sample_patient  # noqa: E402
from vanderpol.simulator import GoisSaviSimulator  # noqa: E402
from vanderpol.types import RhythmScenario  # noqa: E402
from vanderpol.validation import FEATURE_KEYS  # noqa: E402


COMPARISON_GROUPS = {
    "svt_afl_vs_svt_flutter": {
        "real_labels": ("SVT", "AFL"),
        "synthetic_scenarios": ("svt_flutter",),
        "note": "Fast supraventricular tachyarrhythmia/flutter-like windows.",
    },
    "vt_vs_monomorphic_vt": {
        "real_labels": ("VT",),
        "synthetic_scenarios": ("monomorphic_vt",),
        "note": "MIT-BIH VT runs compared with synthetic regular wide-complex VT.",
    },
    "vf_vfl_vs_vf_like": {
        "real_labels": ("VF",),
        "synthetic_scenarios": ("vf_like",),
        "note": "MIT-BIH ventricular flutter/fibrillation labels compared with synthetic chaotic VF-like rhythm.",
    },
}

UNMATCHED_REAL_LABELS = (
    "AFIB",
    "VENTRICULAR_BIGEMINY",
    "VENTRICULAR_TRIGEMINY",
    "IVR",
    "NODAL",
)


@dataclass(frozen=True)
class FeatureRow:
    source: str
    group: str
    label: str
    record_name: str
    features: dict[str, float]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-csv", type=Path, default=Path("outputs/mitdb_abnormal_windows.csv"))
    parser.add_argument("--extra-real-csv", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/comparison"))
    parser.add_argument("--patients-per-scenario", type=int, default=200)
    parser.add_argument("--fs-hz", type=int, default=250)
    parser.add_argument("--observation-s", type=float, default=4.0)
    parser.add_argument("--variability", type=float, default=0.2)
    parser.add_argument("--seed-offset", type=int, default=150_000)
    args = parser.parse_args()

    manifest = run_comparison(
        real_csv=args.real_csv,
        extra_real_csvs=args.extra_real_csv,
        output_dir=args.output_dir,
        patients_per_scenario=args.patients_per_scenario,
        fs_hz=args.fs_hz,
        observation_s=args.observation_s,
        variability=args.variability,
        seed_offset=args.seed_offset,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


def run_comparison(
    *,
    real_csv: Path,
    extra_real_csvs: list[Path] | None = None,
    output_dir: Path,
    patients_per_scenario: int = 200,
    fs_hz: int = 250,
    observation_s: float = 4.0,
    variability: float = 0.2,
    seed_offset: int = 150_000,
) -> dict:
    real_csvs = [real_csv, *(extra_real_csvs or [])]
    real_rows = []
    for csv_path in real_csvs:
        if csv_path.exists():
            real_rows.extend(read_real_rows(csv_path))
    synthetic_rows = generate_synthetic_rows(
        patients_per_scenario=patients_per_scenario,
        fs_hz=fs_hz,
        observation_s=observation_s,
        variability=variability,
        seed_offset=seed_offset,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    distance_rows = build_distance_rows(real_rows, synthetic_rows)
    summary_rows = build_summary_rows(real_rows, synthetic_rows)
    unmatched_rows = build_unmatched_rows(real_rows)

    distance_csv = output_dir / "real_vs_synthetic_abnormal_feature_distances.csv"
    summary_csv = output_dir / "real_vs_synthetic_abnormal_group_summary.csv"
    unmatched_csv = output_dir / "real_abnormal_unmatched_labels.csv"
    write_csv(distance_csv, distance_rows)
    write_csv(summary_csv, summary_rows)
    write_csv(unmatched_csv, unmatched_rows)

    figures = {}
    try:
        figures["smd_heatmap"] = str(
            plot_metric_heatmap(
                distance_rows,
                metric="smd_abs",
                output_png=output_dir / "real_vs_synthetic_smd_heatmap.png",
                title="Real MIT-BIH vs Synthetic Abnormal ECG: Standardized Mean Difference",
            )
        )
        figures["ks_heatmap"] = str(
            plot_metric_heatmap(
                distance_rows,
                metric="ks_statistic",
                output_png=output_dir / "real_vs_synthetic_ks_heatmap.png",
                title="Real MIT-BIH vs Synthetic Abnormal ECG: KS Statistic",
            )
        )
        figures["pca_scatter"] = str(
            plot_pca_scatter(
                real_rows,
                synthetic_rows,
                output_png=output_dir / "real_vs_synthetic_feature_pca.png",
            )
        )
    except ImportError as exc:
        figures["warning"] = f"matplotlib unavailable: {exc}"

    manifest = {
        "status": "ok",
        "real_csv": str(real_csv),
        "real_csvs": [str(path) for path in real_csvs if path.exists()],
        "output_dir": str(output_dir),
        "patients_per_scenario": patients_per_scenario,
        "fs_hz": fs_hz,
        "observation_s": observation_s,
        "variability": variability,
        "seed_offset": seed_offset,
        "comparison_groups": COMPARISON_GROUPS,
        "unmatched_real_labels": UNMATCHED_REAL_LABELS,
        "n_real_rows": len(real_rows),
        "real_source_counts": source_counts(real_rows),
        "n_synthetic_rows": len(synthetic_rows),
        "distance_csv": str(distance_csv),
        "summary_csv": str(summary_csv),
        "unmatched_csv": str(unmatched_csv),
        "figures": figures,
        "interpretation": {
            "smd_abs": "0 is identical means; values above about 1 indicate large feature mean separation.",
            "ks_statistic": "0 is identical empirical distributions; 1 is completely separated.",
            "wasserstein_distance": "Average one-dimensional feature distance in original feature units.",
        },
    }
    manifest_path = output_dir / "real_vs_synthetic_abnormal_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def read_real_rows(path: Path) -> list[FeatureRow]:
    rows = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label = row["annotation_label"]
            group = real_label_to_group(label)
            dataset = row.get("dataset", "real").strip() or "real"
            features = {
                key: float(row[key])
                for key in FEATURE_KEYS
                if row.get(key) not in {None, ""}
            }
            rows.append(
                FeatureRow(
                    source=f"real_{dataset}",
                    group=group,
                    label=label,
                    record_name=row.get("record_name", ""),
                    features=features,
                )
            )
    return rows


def generate_synthetic_rows(
    patients_per_scenario: int,
    fs_hz: int,
    observation_s: float,
    variability: float,
    seed_offset: int,
) -> list[FeatureRow]:
    simulator = GoisSaviSimulator(fs_hz=fs_hz)
    rows = []
    scenarios = [RhythmScenario.SVT_FLUTTER, RhythmScenario.MONOMORPHIC_VT, RhythmScenario.VF_LIKE]
    for scenario_index, scenario in enumerate(scenarios):
        group = synthetic_scenario_to_group(scenario.value)
        for patient_index in range(patients_per_scenario):
            seed = seed_offset + scenario_index * 10_000 + patient_index
            _, observation, _ = observe_patient(
                simulator,
                scenario,
                seed=seed,
                observation_s=observation_s,
                variability=variability,
            )
            rows.append(
                FeatureRow(
                    source="synthetic",
                    group=group,
                    label=scenario.value,
                    record_name=str(seed),
                    features=dict(observation.features),
                )
            )
    return rows


def real_label_to_group(label: str) -> str:
    for group, config in COMPARISON_GROUPS.items():
        if label in config["real_labels"]:
            return group
    if label in UNMATCHED_REAL_LABELS:
        return f"unmatched_{label.lower()}"
    return "unmatched_other"


def synthetic_scenario_to_group(scenario: str) -> str:
    for group, config in COMPARISON_GROUPS.items():
        if scenario in config["synthetic_scenarios"]:
            return group
    return "unmatched_synthetic"


def build_distance_rows(real_rows: list[FeatureRow], synthetic_rows: list[FeatureRow]) -> list[dict]:
    rows = []
    for group, config in COMPARISON_GROUPS.items():
        real = [row for row in real_rows if row.group == group]
        synthetic = [row for row in synthetic_rows if row.group == group]
        if not real or not synthetic:
            continue
        for feature in FEATURE_KEYS:
            real_values = feature_values(real, feature)
            synthetic_values = feature_values(synthetic, feature)
            if len(real_values) == 0 or len(synthetic_values) == 0:
                continue
            real_mean = float(np.mean(real_values))
            synthetic_mean = float(np.mean(synthetic_values))
            real_std = float(np.std(real_values))
            synthetic_std = float(np.std(synthetic_values))
            pooled = float(np.sqrt(0.5 * (real_std**2 + synthetic_std**2)))
            smd = (synthetic_mean - real_mean) / (pooled + 1e-8)
            rows.append(
                {
                    "comparison_group": group,
                    "real_labels": ";".join(config["real_labels"]),
                    "synthetic_scenarios": ";".join(config["synthetic_scenarios"]),
                    "feature": feature,
                    "real_n": len(real_values),
                    "synthetic_n": len(synthetic_values),
                    "real_mean": real_mean,
                    "synthetic_mean": synthetic_mean,
                    "real_std": real_std,
                    "synthetic_std": synthetic_std,
                    "mean_difference_synthetic_minus_real": synthetic_mean - real_mean,
                    "smd": smd,
                    "smd_abs": abs(smd),
                    "ks_statistic": ks_statistic(real_values, synthetic_values),
                    "wasserstein_distance": wasserstein_distance(real_values, synthetic_values),
                    "note": config["note"],
                }
            )
    return rows


def build_summary_rows(real_rows: list[FeatureRow], synthetic_rows: list[FeatureRow]) -> list[dict]:
    rows = []
    source_groups = [
        (source, [row for row in real_rows if row.source == source])
        for source in sorted({row.source for row in real_rows})
    ]
    source_groups.append(("synthetic", synthetic_rows))
    for source, source_rows in source_groups:
        groups = sorted({row.group for row in source_rows})
        for group in groups:
            group_rows = [row for row in source_rows if row.group == group]
            labels = sorted({row.label for row in group_rows})
            base = {
                "source": source,
                "group": group,
                "labels": ";".join(labels),
                "n": len(group_rows),
            }
            for feature in FEATURE_KEYS:
                values = feature_values(group_rows, feature)
                base[f"{feature}_mean"] = float(np.mean(values)) if len(values) else float("nan")
                base[f"{feature}_std"] = float(np.std(values)) if len(values) else float("nan")
                base[f"{feature}_p10"] = float(np.quantile(values, 0.10)) if len(values) else float("nan")
                base[f"{feature}_p50"] = float(np.quantile(values, 0.50)) if len(values) else float("nan")
                base[f"{feature}_p90"] = float(np.quantile(values, 0.90)) if len(values) else float("nan")
            rows.append(dict(base))
    return rows


def build_unmatched_rows(real_rows: list[FeatureRow]) -> list[dict]:
    rows = []
    for label in UNMATCHED_REAL_LABELS:
        label_rows = [row for row in real_rows if row.label == label]
        if not label_rows:
            continue
        row = {
            "real_label": label,
            "n": len(label_rows),
            "reason": "No matched synthetic scenario is currently implemented.",
        }
        for feature in FEATURE_KEYS:
            values = feature_values(label_rows, feature)
            row[f"{feature}_mean"] = float(np.mean(values)) if len(values) else float("nan")
            row[f"{feature}_std"] = float(np.std(values)) if len(values) else float("nan")
        rows.append(row)
    return rows


def feature_values(rows: list[FeatureRow], feature: str) -> np.ndarray:
    values = [row.features.get(feature, np.nan) for row in rows]
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def source_counts(rows: list[FeatureRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.source] = counts.get(row.source, 0) + 1
    return dict(sorted(counts.items()))


def ks_statistic(a: np.ndarray, b: np.ndarray) -> float:
    a = np.sort(np.asarray(a, dtype=float))
    b = np.sort(np.asarray(b, dtype=float))
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    values = np.sort(np.concatenate([a, b]))
    cdf_a = np.searchsorted(a, values, side="right") / float(len(a))
    cdf_b = np.searchsorted(b, values, side="right") / float(len(b))
    return float(np.max(np.abs(cdf_a - cdf_b)))


def wasserstein_distance(a: np.ndarray, b: np.ndarray, n_quantiles: int = 512) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    qs = np.linspace(0.0, 1.0, n_quantiles)
    return float(np.mean(np.abs(np.quantile(a, qs) - np.quantile(b, qs))))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_metric_heatmap(rows: list[dict], metric: str, output_png: Path, title: str) -> Path:
    import matplotlib.pyplot as plt

    groups = list(COMPARISON_GROUPS)
    features = list(FEATURE_KEYS)
    matrix = np.full((len(groups), len(features)), np.nan, dtype=float)
    lookup = {(row["comparison_group"], row["feature"]): float(row[metric]) for row in rows}
    for y, group in enumerate(groups):
        for x, feature in enumerate(features):
            matrix[y, x] = lookup.get((group, feature), np.nan)

    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    im = ax.imshow(matrix, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(features)), labels=[feature.replace("_", "\n") for feature in features], fontsize=8)
    ax.set_yticks(range(len(groups)), labels=groups, fontsize=9)
    ax.set_title(title, fontsize=11)
    for y in range(len(groups)):
        for x in range(len(features)):
            value = matrix[y, x]
            if np.isfinite(value):
                ax.text(x, y, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=ax, label=metric)
    fig.tight_layout()
    fig.savefig(output_png, dpi=160)
    plt.close(fig)
    return output_png


def plot_pca_scatter(real_rows: list[FeatureRow], synthetic_rows: list[FeatureRow], output_png: Path) -> Path:
    import matplotlib.pyplot as plt

    rows = [
        row
        for row in [*real_rows, *synthetic_rows]
        if row.group in COMPARISON_GROUPS
    ]
    matrix = np.asarray(
        [[row.features.get(feature, np.nan) for feature in FEATURE_KEYS] for row in rows],
        dtype=float,
    )
    finite = np.isfinite(matrix).all(axis=1)
    rows = [row for row, keep in zip(rows, finite) if keep]
    matrix = matrix[finite]
    mean = np.mean(matrix, axis=0)
    std = np.std(matrix, axis=0) + 1e-8
    z = (matrix - mean) / std
    _, _, vt = np.linalg.svd(z, full_matrices=False)
    coords = z @ vt[:2].T

    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    colors = {
        "real_mitdb": "#2563eb",
        "real_cudb": "#16a34a",
        "synthetic": "#dc2626",
    }
    markers = {
        "svt_afl_vs_svt_flutter": "o",
        "vt_vs_monomorphic_vt": "s",
        "vf_vfl_vs_vf_like": "^",
    }
    sources = sorted({row.source for row in real_rows}) + ["synthetic"]
    for source in sources:
        for group in COMPARISON_GROUPS:
            indices = [
                idx
                for idx, row in enumerate(rows)
                if row.source == source and row.group == group
            ]
            if not indices:
                continue
            label = f"{source}: {group}"
            ax.scatter(
                coords[indices, 0],
                coords[indices, 1],
                s=18,
                alpha=0.55,
                c=colors.get(source, "#64748b"),
                marker=markers[group],
                label=label,
                edgecolors="none",
            )
    ax.axhline(0.0, color="#9ca3af", linewidth=0.8)
    ax.axvline(0.0, color="#9ca3af", linewidth=0.8)
    ax.set_title("Real MIT-BIH vs Synthetic Abnormal ECG Feature PCA")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_png, dpi=160)
    plt.close(fig)
    return output_png


if __name__ == "__main__":
    main()
