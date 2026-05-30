"""Stage 7: balanced Challenge 2015 sampling and fallback threshold sweeps."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np

from .bandit import LinUCB, oracle_actions
from .data.physionet import download_dataset_file, download_records
from .noise import NoiseProfile, get_noise_profiles
from .reporting import evaluate_policy, metric_matrices_from_rows
from .reward import RewardWeights
from .stage6 import (
    ConservativeFallbackConfig,
    conservative_action,
    conservative_noise_ood_sweep,
    estimate_real_noise_stats,
    load_noise_profile_from_stats,
    _reconstruct_noisy_observations,
    _training_indices,
    save_real_noise_stats,
)
from .stage5 import run_noisy_algorithm_matrix


@dataclass(frozen=True)
class AlarmMetadata:
    record_name: str
    alarm_type: str
    is_true_alarm: bool


def ensure_challenge_metadata(root: str | Path) -> tuple[Path, Path]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    alarms = root / "ALARMS"
    records = root / "RECORDS"
    if not alarms.exists():
        download_dataset_file("challenge-2015", "ALARMS", root)
    if not records.exists():
        download_dataset_file("challenge-2015", "RECORDS", root)
    return alarms, records


def load_alarm_metadata(path: str | Path) -> list[AlarmMetadata]:
    rows: list[AlarmMetadata] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        rows.append(
            AlarmMetadata(
                record_name=parts[0],
                alarm_type=parts[1],
                is_true_alarm=parts[2] == "1",
            )
        )
    return rows


def alarm_type_counts(rows: Iterable[AlarmMetadata]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = counts.setdefault(row.alarm_type, {"total": 0, "true": 0, "false": 0})
        bucket["total"] += 1
        bucket["true" if row.is_true_alarm else "false"] += 1
    return dict(sorted(counts.items()))


def select_balanced_alarms(
    rows: Iterable[AlarmMetadata],
    per_category: int,
    categories: list[str] | None = None,
    truth: str = "any",
    seed: int = 7,
) -> list[AlarmMetadata]:
    rng = np.random.default_rng(seed)
    rows = list(rows)
    selected_categories = set(categories or sorted({row.alarm_type for row in rows}))
    output: list[AlarmMetadata] = []
    for category in sorted(selected_categories):
        candidates = [row for row in rows if row.alarm_type == category]
        if truth == "true":
            candidates = [row for row in candidates if row.is_true_alarm]
        elif truth == "false":
            candidates = [row for row in candidates if not row.is_true_alarm]
        elif truth != "any":
            raise ValueError("truth must be one of: any, true, false")
        if not candidates:
            continue
        order = rng.permutation(len(candidates))
        for idx in order[:per_category]:
            output.append(candidates[int(idx)])
    return output


def download_balanced_challenge_sample(
    root: str | Path,
    per_category: int = 1,
    categories: list[str] | None = None,
    truth: str = "any",
    seed: int = 7,
) -> tuple[list[AlarmMetadata], list[Path]]:
    root = Path(root)
    alarms_path, _ = ensure_challenge_metadata(root)
    rows = load_alarm_metadata(alarms_path)
    selected = select_balanced_alarms(
        rows,
        per_category=per_category,
        categories=categories,
        truth=truth,
        seed=seed,
    )
    downloaded = download_records(
        "challenge-2015",
        records=[row.record_name for row in selected],
        destination=root,
    )
    return selected, downloaded


def save_alarm_manifest(rows: list[AlarmMetadata], output_csv: str | Path) -> None:
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_name", "alarm_type", "is_true_alarm"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "record_name": row.record_name,
                    "alarm_type": row.alarm_type,
                    "is_true_alarm": int(row.is_true_alarm),
                }
            )


def load_alarm_manifest(path: str | Path) -> list[AlarmMetadata]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            AlarmMetadata(
                record_name=row["record_name"],
                alarm_type=row["alarm_type"],
                is_true_alarm=str(row["is_true_alarm"]).lower() in {"1", "true", "yes"},
            )
            for row in reader
        ]


def estimate_noise_by_alarm_category(
    root: str | Path,
    alarm_rows: list[AlarmMetadata],
    channel: int = 0,
    window_s: float = 4.0,
    stride_s: float = 10.0,
    max_windows_per_record: int = 4,
) -> dict[str, Any]:
    root = Path(root)
    grouped: dict[str, list[str]] = {}
    for row in alarm_rows:
        if (root / f"{row.record_name}.hea").exists():
            grouped.setdefault(row.alarm_type, []).append(row.record_name)

    categories: dict[str, Any] = {}
    for alarm_type, records in sorted(grouped.items()):
        stats = estimate_real_noise_stats(
            root=root,
            dataset=f"challenge-2015:{alarm_type}",
            records=records,
            channel=channel,
            window_s=window_s,
            stride_s=stride_s,
            max_windows_per_record=max_windows_per_record,
        )
        categories[alarm_type] = {
            "records": records,
            "n_windows": stats.n_windows,
            "feature_means": stats.feature_means,
            "feature_stds": stats.feature_stds,
            "feature_quantiles": stats.feature_quantiles,
            "acls_label_counts": stats.acls_label_counts,
            "recommended_profile": {
                **stats.recommended_profile.__dict__,
                "name": f"real_{_slug(alarm_type)}",
            },
        }
    return {"dataset": "challenge-2015", "categories": categories}


def save_category_noise_stats(report: dict[str, Any], output_json: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_profiles_from_category_stats(path: str | Path) -> list[NoiseProfile]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    profiles = []
    for item in payload.get("categories", {}).values():
        profiles.append(NoiseProfile(**item["recommended_profile"]))
    return profiles


def fallback_threshold_sweep(
    patients_per_scenario: int,
    profiles: list[NoiseProfile],
    min_sqi_values: list[float],
    entropy_values: list[float],
    rr_cv_values: list[float],
    horizon_s: float = 30.0,
    train_fraction: float = 1.0,
    eval_variability: float = 0.2,
    checkpoint_json: str | Path | None = None,
    checkpoint_csv: str | Path | None = None,
    resume: bool = False,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
    progress_callback: Callable[..., None] | None = None,
) -> dict[str, Any]:
    total_configs = len(min_sqi_values) * len(entropy_values) * len(rr_cv_values)
    configs = []
    done_keys: set[tuple[float, float, float]] = set()
    if resume and checkpoint_json and Path(checkpoint_json).exists():
        with Path(checkpoint_json).open("r", encoding="utf-8") as handle:
            partial = json.load(handle)
        configs = list(partial.get("configs", []))
        done_keys = {_config_key(item.get("config", {})) for item in configs}

    if checkpoint_json:
        if progress_callback:
            progress_callback(
                "fallback_threshold_sweep",
                "Building reusable noisy policy matrices before threshold evaluation.",
                phase="precomputing_profiles",
                completed_profiles=0,
                total_profiles=len(profiles),
                completed_configs=len(configs),
                total_configs=total_configs,
            )
        save_threshold_sweep(
            _threshold_sweep_payload(
                patients_per_scenario=patients_per_scenario,
                horizon_s=horizon_s,
                train_fraction=train_fraction,
                eval_variability=eval_variability,
                configs=configs,
                total_configs=total_configs,
                run_status="precomputing_profiles",
                message="Building reusable noisy policy matrices before threshold evaluation.",
            ),
            checkpoint_json,
            checkpoint_csv or Path(checkpoint_json).with_suffix(".csv"),
        )
    base = _precompute_fallback_base(
        patients_per_scenario=patients_per_scenario,
        profiles=profiles,
        train_fraction=train_fraction,
        eval_variability=eval_variability,
        horizon_s=horizon_s,
        checkpoint_json=checkpoint_json,
        checkpoint_csv=checkpoint_csv,
        existing_configs=configs,
        total_configs=total_configs,
        weights=weights,
        n_jobs=n_jobs,
        progress_callback=progress_callback,
    )
    for min_sqi in min_sqi_values:
        for entropy in entropy_values:
            for rr_cv in rr_cv_values:
                key = (float(min_sqi), float(entropy), float(rr_cv))
                if key in done_keys:
                    continue
                if progress_callback:
                    progress_callback(
                        "fallback_threshold_sweep",
                        f"Evaluating fallback config {len(configs) + 1}/{total_configs}.",
                        phase="evaluating_configs",
                        completed_profiles=len(profiles),
                        total_profiles=len(profiles),
                        completed_configs=len(configs),
                        total_configs=total_configs,
                        current_config={
                            "min_signal_quality": float(min_sqi),
                            "high_entropy_threshold": float(entropy),
                            "high_rr_cv_threshold": float(rr_cv),
                        },
                    )
                config = ConservativeFallbackConfig(
                    min_signal_quality=float(min_sqi),
                    high_entropy_threshold=float(entropy),
                    high_rr_cv_threshold=float(rr_cv),
                )
                report = _evaluate_fallback_config(
                    base=base,
                    config=config,
                )
                configs.append(
                    {
                        "config": config.__dict__,
                        "profiles": report["profiles"],
                    }
                )
                if checkpoint_json:
                    save_threshold_sweep(
                        _threshold_sweep_payload(
                            patients_per_scenario=patients_per_scenario,
                            horizon_s=horizon_s,
                            train_fraction=train_fraction,
                            eval_variability=eval_variability,
                            configs=configs,
                            total_configs=total_configs,
                            run_status="running",
                            message="Evaluating fallback threshold grid.",
                        ),
                        checkpoint_json,
                        checkpoint_csv or Path(checkpoint_json).with_suffix(".csv"),
                    )
                if progress_callback:
                    progress_callback(
                        "fallback_threshold_sweep",
                        f"Completed fallback config {len(configs)}/{total_configs}.",
                        phase="evaluating_configs",
                        completed_profiles=len(profiles),
                        total_profiles=len(profiles),
                        completed_configs=len(configs),
                        total_configs=total_configs,
                    )
    return _threshold_sweep_payload(
        patients_per_scenario=patients_per_scenario,
        horizon_s=horizon_s,
        train_fraction=train_fraction,
        eval_variability=eval_variability,
        configs=configs,
        total_configs=total_configs,
        run_status="completed",
        message="Fallback threshold sweep completed.",
    )


def _threshold_sweep_payload(
    patients_per_scenario: int,
    horizon_s: float,
    train_fraction: float,
    eval_variability: float,
    configs: list[dict[str, Any]],
    total_configs: int,
    run_status: str,
    message: str = "",
    completed_profiles: int = 0,
    total_profiles: int = 0,
) -> dict[str, Any]:
    return {
        "patients_per_scenario": patients_per_scenario,
        "horizon_s": horizon_s,
        "train_fraction": train_fraction,
        "eval_variability": eval_variability,
        "completed_configs": len(configs),
        "total_configs": total_configs,
        "completed_profiles": completed_profiles,
        "total_profiles": total_profiles,
        "run_status": run_status,
        "message": message,
        "configs": configs,
    }


def _precompute_fallback_base(
    patients_per_scenario: int,
    profiles: list[NoiseProfile],
    train_fraction: float,
    eval_variability: float,
    horizon_s: float,
    train_variability: float = 0.2,
    seed: int = 7,
    checkpoint_json: str | Path | None = None,
    checkpoint_csv: str | Path | None = None,
    existing_configs: list[dict[str, Any]] | None = None,
    total_configs: int = 0,
    weights: RewardWeights = RewardWeights(),
    n_jobs: int | str | None = 1,
    progress_callback: Callable[..., None] | None = None,
) -> dict[str, Any]:
    from .experiments import run_algorithm_matrix

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

    profile_data = []
    for profile_index, profile in enumerate(profiles, start=1):
        if progress_callback:
            progress_callback(
                "fallback_threshold_sweep",
                f"Precomputing profile {profile_index}/{len(profiles)}: {profile.name}",
                phase="precomputing_profiles",
                current_profile=profile.name,
                completed_profiles=profile_index - 1,
                total_profiles=len(profiles),
                completed_configs=len(existing_configs or []),
                total_configs=total_configs,
            )
        rows, _, contexts, rewards, acls_actions = run_noisy_algorithm_matrix(
            patients_per_scenario=patients_per_scenario,
            profile=profile,
            variability=eval_variability,
            horizon_s=horizon_s,
            weights=weights,
            n_jobs=n_jobs,
        )
        observations = _reconstruct_noisy_observations(
            patients_per_scenario=patients_per_scenario,
            profile=profile,
            variability=eval_variability,
        )
        model_actions = model.predict_many(contexts)
        metric_matrices = metric_matrices_from_rows(rows)
        indices = np.arange(len(contexts))
        profile_data.append(
            {
                "profile": profile.__dict__,
                "n_contexts": int(len(contexts)),
                "observations": observations,
                "model_actions": model_actions,
                "metric_matrices": metric_matrices,
                "indices": indices,
                "rewards": rewards,
                "acls_actions": acls_actions,
                "oracle_actions": oracle_actions(rewards),
            }
        )
        if checkpoint_json:
            save_threshold_sweep(
                _threshold_sweep_payload(
                    patients_per_scenario=patients_per_scenario,
                    horizon_s=horizon_s,
                    train_fraction=train_fraction,
                    eval_variability=eval_variability,
                    configs=existing_configs or [],
                    total_configs=total_configs,
                    run_status="precomputing_profiles",
                    message=f"Precomputed profile {profile_index}/{len(profiles)}: {profile.name}",
                    completed_profiles=profile_index,
                    total_profiles=len(profiles),
                ),
                checkpoint_json,
                checkpoint_csv or Path(checkpoint_json).with_suffix(".csv"),
            )
        if progress_callback:
            progress_callback(
                "fallback_threshold_sweep",
                f"Precomputed profile {profile_index}/{len(profiles)}: {profile.name}",
                phase="precomputing_profiles",
                current_profile=profile.name,
                completed_profiles=profile_index,
                total_profiles=len(profiles),
                completed_configs=len(existing_configs or []),
                total_configs=total_configs,
            )
    return {
        "patients_per_scenario": patients_per_scenario,
        "train_fraction": train_fraction,
        "train_variability": train_variability,
        "eval_variability": eval_variability,
        "horizon_s": horizon_s,
        "n_train_contexts": int(len(train_indices)),
        "profiles": profile_data,
    }


def _evaluate_fallback_config(base: dict[str, Any], config: ConservativeFallbackConfig) -> dict[str, Any]:
    reports = []
    for item in base["profiles"]:
        conservative = []
        fallback_reasons: dict[str, int] = {}
        for action, observation in zip(item["model_actions"], item["observations"]):
            final_action, reason = conservative_action(int(action), observation, config)
            conservative.append(final_action)
            fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1

        reports.append(
            {
                "profile": item["profile"],
                "n_contexts": item["n_contexts"],
                "fallback_reasons": dict(sorted(fallback_reasons.items())),
                "policies": {
                    "selector_linucb": evaluate_policy(
                        item["model_actions"],
                        item["rewards"],
                        item["metric_matrices"],
                        item["indices"],
                    ),
                    "conservative_selector": evaluate_policy(
                        np.asarray(conservative, dtype=int),
                        item["rewards"],
                        item["metric_matrices"],
                        item["indices"],
                    ),
                    "acls_rule": evaluate_policy(
                        item["acls_actions"],
                        item["rewards"],
                        item["metric_matrices"],
                        item["indices"],
                    ),
                    "oracle": evaluate_policy(
                        item["oracle_actions"],
                        item["rewards"],
                        item["metric_matrices"],
                        item["indices"],
                    ),
                },
            }
        )
    return {
        "patients_per_scenario": base["patients_per_scenario"],
        "train_fraction": base["train_fraction"],
        "train_variability": base["train_variability"],
        "eval_variability": base["eval_variability"],
        "horizon_s": base["horizon_s"],
        "fallback_config": config.__dict__,
        "n_train_contexts": base["n_train_contexts"],
        "profiles": reports,
    }


def _config_key(config: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(config.get("min_signal_quality", 0.0)),
        float(config.get("high_entropy_threshold", 0.0)),
        float(config.get("high_rr_cv_threshold", 0.0)),
    )


def save_threshold_sweep(report: dict[str, Any], output_json: str | Path, output_csv: str | Path) -> None:
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "min_signal_quality",
        "high_entropy_threshold",
        "high_rr_cv_threshold",
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
        for config_report in report["configs"]:
            config = config_report["config"]
            for profile_report in config_report["profiles"]:
                profile_name = profile_report["profile"]["name"]
                for policy, metrics in profile_report["policies"].items():
                    writer.writerow(
                        {
                            "min_signal_quality": config["min_signal_quality"],
                            "high_entropy_threshold": config["high_entropy_threshold"],
                            "high_rr_cv_threshold": config["high_rr_cv_threshold"],
                            "profile": profile_name,
                            "policy": policy,
                            **metrics,
                        }
                    )


def _slug(value: str) -> str:
    return value.lower().replace("/", "_").replace("-", "_").replace(" ", "_")
