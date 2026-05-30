"""Treatment calibration targets and reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .experiments import MatrixRow, run_algorithm_matrix, summarize_matrix
from .reward import RewardWeights


@dataclass(frozen=True)
class CalibrationTarget:
    algorithm: str
    scenario: str
    metric: str
    min_value: float
    max_value: float
    source: str
    note: str


def load_calibration_targets(path: str | Path) -> list[CalibrationTarget]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [
        CalibrationTarget(
            algorithm=str(item["algorithm"]),
            scenario=str(item["scenario"]),
            metric=str(item["metric"]),
            min_value=float(item["min"]),
            max_value=float(item["max"]),
            source=str(item.get("source", "")),
            note=str(item.get("note", "")),
        )
        for item in payload["targets"]
    ]


def calibration_report(
    rows: list[MatrixRow],
    targets: list[CalibrationTarget],
) -> dict[str, Any]:
    summary = summarize_matrix(rows)
    derived = _derived_metrics(summary)
    checks = []
    for target in targets:
        key = f"{target.scenario}:{target.algorithm}"
        value = _lookup_metric(summary, derived, key, target.metric)
        status = "missing"
        if value is not None:
            status = "pass" if target.min_value <= value <= target.max_value else "fail"
        checks.append(
            {
                "algorithm": target.algorithm,
                "scenario": target.scenario,
                "metric": target.metric,
                "value": value,
                "target_min": target.min_value,
                "target_max": target.max_value,
                "status": status,
                "source": target.source,
                "note": target.note,
            }
        )
    return {
        "summary": summary,
        "derived_metrics": derived,
        "checks": checks,
        "pass_rate": float(np.mean([check["status"] == "pass" for check in checks]))
        if checks
        else 0.0,
    }


def run_calibration_matrix(
    patients_per_scenario: int,
    target_path: str | Path,
    fs_hz: int = 250,
    observation_s: float = 4.0,
    horizon_s: float = 30.0,
    variability: float = 0.2,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
) -> dict[str, Any]:
    targets = load_calibration_targets(target_path)
    rows, _, _, _, _ = run_algorithm_matrix(
        patients_per_scenario=patients_per_scenario,
        fs_hz=fs_hz,
        observation_s=observation_s,
        horizon_s=horizon_s,
        variability=variability,
        weights=weights,
        n_jobs=n_jobs,
    )
    return calibration_report(rows, targets)


def _lookup_metric(
    summary: dict[str, dict[str, float]],
    derived: dict[str, float],
    key: str,
    metric: str,
) -> float | None:
    derived_key = f"{key}:{metric}"
    if derived_key in derived:
        return derived[derived_key]
    if key not in summary:
        return None
    return summary[key].get(metric)


def _derived_metrics(summary: dict[str, dict[str, float]]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for scenario in {
        key.split(":", 1)[0]
        for key in summary
    }:
        def value(algorithm: str, metric: str) -> float | None:
            row = summary.get(f"{scenario}:{algorithm}")
            return row.get(metric) if row else None

        defib_energy = value("unsynchronized_defibrillation", "mean_energy")
        if defib_energy and defib_energy > 0:
            for algorithm in (
                "atp_burst_pacing",
                "resonant_drift_pacing",
                "adaptive_low_energy_pacing",
            ):
                energy = value(algorithm, "mean_energy")
                if energy is not None:
                    metrics[f"{scenario}:{algorithm}:energy_ratio_vs_unsync_defibrillation"] = float(
                        energy / defib_energy
                    )
    return metrics
