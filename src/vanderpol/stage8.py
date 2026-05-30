"""Stage 8: final experiment bundle runner and executive summary."""

from __future__ import annotations

import csv
import json
import platform
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

from .calibration import run_calibration_matrix
from .noise import get_noise_profiles
from .progress import (
    GracefulStopRequested,
    RunRecorder,
    atomic_write_json,
    check_stop_requested,
    collect_provenance,
)
from .reporting import (
    build_selector_report,
    decision_boundary_grid,
    generate_phase2_heatmaps,
    save_decision_boundary,
    save_selector_report,
)
from .reward import RewardWeights
from .stage5 import (
    noise_ood_sweep,
    run_bootstrap_matrix_report,
    save_bootstrap_ci,
    save_noise_ood_sweep,
    save_selector_stability,
    selector_stability_report,
)
from .stage6 import load_noise_profile_from_stats
from .stage7 import (
    fallback_threshold_sweep,
    load_profiles_from_category_stats,
    save_threshold_sweep,
)


@dataclass(frozen=True)
class BundleStep:
    name: str
    status: str
    duration_s: float
    outputs: list[str]
    message: str = ""


def default_bundle_config(preset: str = "smoke") -> dict[str, Any]:
    if preset == "smoke":
        return {
            "preset": "smoke",
            "patients_per_scenario": 1,
            "horizon_s": 3.0,
            "train_fraction": 0.7,
            "selector_seed": 7,
            "selector_stability_seeds": [1, 7],
            "bootstrap_samples": 20,
            "decision_grid_size": 8,
            "noise_profiles": ["clean", "severe"],
            "fallback_min_sqi": [0.35, 0.50],
            "fallback_entropy": [0.62],
            "fallback_rr_cv": [0.30],
            "real_noise_stats": "outputs/real_noise_stats.json",
            "calibration_config": "configs/calibration.json",
            "n_jobs": 1,
        }
    if preset == "full":
        return {
            "preset": "full",
            "patients_per_scenario": 100,
            "horizon_s": 30.0,
            "train_fraction": 0.7,
            "selector_seed": 7,
            "selector_stability_seeds": [1, 7, 13, 21, 42],
            "bootstrap_samples": 1000,
            "decision_grid_size": 80,
            "noise_profiles": ["clean", "mild", "moderate", "severe"],
            "fallback_min_sqi": [0.30, 0.35, 0.42, 0.50],
            "fallback_entropy": [0.55, 0.62, 0.70],
            "fallback_rr_cv": [0.25, 0.30, 0.40],
            "real_noise_stats": "outputs/real_noise_stats.json",
            "category_noise_stats": "outputs/challenge2015_category_noise.json",
            "calibration_config": "configs/calibration.json",
            "n_jobs": 1,
        }
    raise ValueError("preset must be `smoke` or `full`")


def load_bundle_config(path: str | Path | None = None, preset: str = "smoke") -> dict[str, Any]:
    config = default_bundle_config(preset)
    if path is not None:
        with Path(path).open("r", encoding="utf-8") as handle:
            override = json.load(handle)
        config.update(override)
    return config


def run_experiment_bundle(
    config: dict[str, Any],
    output_dir: str | Path,
    run_id: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    if run_id is None:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    steps: list[BundleStep] = []
    started = time.perf_counter()

    patients = int(config["patients_per_scenario"])
    horizon = float(config["horizon_s"])
    n_jobs = config.get("n_jobs", 1)
    weights = _reward_weights_from_config(config)
    recorder = RunRecorder(run_dir, run_id)
    provenance = collect_provenance(config, command_line=sys.argv)

    step_fns: list[tuple[str, list[str], Callable[[], list[str] | dict[str, str] | str]]] = [
        (
            "phase2_figures",
            expected_step_outputs("phase2_figures", run_dir),
            lambda: generate_phase2_heatmaps(
                patients_per_scenario=patients,
                output_dir=run_dir / "figures",
                horizon_s=horizon,
                weights=weights,
                n_jobs=n_jobs,
            ),
        ),
        (
            "calibration_report",
            expected_step_outputs("calibration_report", run_dir),
            lambda: _write_json(
                run_calibration_matrix(
                    patients_per_scenario=patients,
                    target_path=config.get("calibration_config", "configs/calibration.json"),
                    horizon_s=horizon,
                    weights=weights,
                    n_jobs=n_jobs,
                ),
                run_dir / "calibration_report.json",
            ),
        ),
        (
            "selector_report",
            expected_step_outputs("selector_report", run_dir),
            lambda: _selector_report_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
        (
            "decision_boundary",
            expected_step_outputs("decision_boundary", run_dir),
            lambda: _decision_boundary_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
        (
            "bootstrap_ci",
            expected_step_outputs("bootstrap_ci", run_dir),
            lambda: _bootstrap_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
        (
            "selector_stability",
            expected_step_outputs("selector_stability", run_dir),
            lambda: _selector_stability_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
        (
            "noise_ood_sweep",
            expected_step_outputs("noise_ood_sweep", run_dir),
            lambda: _noise_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
        (
            "fallback_threshold_sweep",
            expected_step_outputs("fallback_threshold_sweep", run_dir),
            lambda: _fallback_outputs(config, run_dir, patients, horizon, weights, n_jobs),
        ),
    ]
    enabled_steps = set(config.get("enabled_steps") or [name for name, _, _ in step_fns])
    enabled_order = [name for name, _, _ in step_fns if name in enabled_steps]

    def emit_step_progress(step: str, message: str = "", **detail: Any) -> None:
        check_stop_requested(run_dir)
        recorder.progress(step=step, message=message, **detail)
        snapshot = _base_manifest(
            run_id=run_id,
            run_dir=run_dir,
            config=config,
            started=started,
            step_order=enabled_order,
            steps=steps,
            run_status="running",
            current_step=step,
            provenance=provenance,
        )
        recorder.write_current(snapshot)

    manifest = _base_manifest(
        run_id=run_id,
        run_dir=run_dir,
        config=config,
        started=started,
        step_order=enabled_order,
        steps=steps,
        run_status="running",
        provenance=provenance,
    )
    recorder.event("run_started", status="running", message="Experiment bundle started.", fsync=True)
    _write_progress_files(manifest, run_dir, recorder)

    for name, expected_outputs, fn in step_fns:
        check_stop_requested(run_dir)
        if name not in enabled_steps:
            continue
        if resume and _outputs_complete(expected_outputs):
            step = BundleStep(
                name=name,
                status="skipped",
                duration_s=0.0,
                outputs=expected_outputs,
                message="Reused existing outputs",
            )
            steps.append(step)
            _record_step_outputs(recorder, name, expected_outputs)
            recorder.event(
                "step_done",
                step=name,
                status="skipped",
                message=step.message,
                outputs=expected_outputs,
            )
            manifest = _base_manifest(
                run_id=run_id,
                run_dir=run_dir,
                config=config,
                started=started,
                step_order=enabled_order,
                steps=steps,
                run_status="running",
                provenance=provenance,
            )
            _write_progress_files(manifest, run_dir, recorder)
            continue

        manifest = _base_manifest(
            run_id=run_id,
            run_dir=run_dir,
            config=config,
            started=started,
            step_order=enabled_order,
            steps=steps,
            run_status="running",
            current_step=name,
            provenance=provenance,
        )
        recorder.event("step_started", step=name, status="running", message=f"Started {name}.")
        _write_progress_files(manifest, run_dir, recorder)
        heartbeat = _step_heartbeat(
            run_id=run_id,
            run_dir=run_dir,
            config=config,
            started=started,
            step_order=enabled_order,
            steps=steps,
            current_step=name,
            recorder=recorder,
            provenance=provenance,
        )
        if name == "noise_ood_sweep":
            step = _run_step(
                name,
                lambda: _noise_outputs(config, run_dir, patients, horizon, weights, n_jobs, emit_step_progress),
                recorder,
                heartbeat=heartbeat,
            )
        elif name == "fallback_threshold_sweep":
            step = _run_step(
                name,
                lambda: _fallback_outputs(config, run_dir, patients, horizon, weights, n_jobs, emit_step_progress),
                recorder,
                heartbeat=heartbeat,
            )
        else:
            step = _run_step(name, fn, recorder, heartbeat=heartbeat)
        steps.append(step)
        if step.status in {"ok", "skipped"}:
            _record_step_outputs(recorder, name, step.outputs)
            recorder.event("step_done", step=name, status=step.status, outputs=step.outputs)
        manifest = _base_manifest(
            run_id=run_id,
            run_dir=run_dir,
            config=config,
            started=started,
            step_order=enabled_order,
            steps=steps,
            run_status="running",
            provenance=provenance,
        )
        _write_progress_files(manifest, run_dir, recorder)
        if step.status not in {"ok", "skipped"}:
            break

    if any(step.status == "stopped" for step in steps):
        run_status = "stopped"
    else:
        run_status = "completed" if all(step.status in {"ok", "skipped"} for step in steps) else "failed"
    manifest = _base_manifest(
        run_id=run_id,
        run_dir=run_dir,
        config=config,
        started=started,
        step_order=enabled_order,
        steps=steps,
        run_status=run_status,
        provenance=provenance,
    )
    manifest_path = run_dir / "run_manifest.json"
    _write_json(manifest, manifest_path)
    summary_path = run_dir / "executive_summary.md"
    generate_executive_summary(manifest_path, summary_path)
    manifest["manifest_path"] = str(manifest_path)
    manifest["summary_path"] = str(summary_path)
    terminal_event = "run_done" if run_status == "completed" else "run_stopped" if run_status == "stopped" else "run_failed"
    recorder.event(terminal_event, status=run_status, message=f"Run {run_status}.", fsync=True)
    recorder.notify(terminal_event, {"status": run_status, "run_dir": str(run_dir)}, config)
    _write_progress_files(manifest, run_dir, recorder)
    return manifest


def generate_executive_summary(
    manifest_path: str | Path,
    output_md: str | Path,
) -> str:
    manifest_path = Path(manifest_path)
    output_md = Path(output_md)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    run_dir = Path(manifest["run_dir"])
    selector = _read_json_if_exists(run_dir / "selector_report.json")
    calibration = _read_json_if_exists(run_dir / "calibration_report.json")
    stability = _read_json_if_exists(run_dir / "selector_stability.json")

    lines = [
        "# Executive Summary",
        "",
        f"- Run ID: `{manifest['run_id']}`",
        f"- Preset: `{manifest['config'].get('preset', 'custom')}`",
        f"- Patients per scenario: `{manifest['config'].get('patients_per_scenario')}`",
        f"- Horizon: `{manifest['config'].get('horizon_s')}` seconds",
        f"- Duration: `{manifest.get('duration_s', 0.0):.2f}` seconds",
        "",
        "## Status",
        "",
    ]
    for step in manifest["steps"]:
        lines.append(f"- `{step['name']}`: {step['status']} ({step['duration_s']:.2f}s)")

    if calibration:
        lines.extend(
            [
                "",
                "## Calibration",
                "",
                f"- Pass rate: `{calibration.get('pass_rate', 0.0):.2f}`",
                f"- Checks: `{len(calibration.get('checks', []))}`",
            ]
        )

    if selector:
        policies = selector.get("policy_summary", {})
        lines.extend(["", "## Selector", ""])
        for name in ("selector_linucb", "acls_rule", "oracle"):
            if name in policies:
                item = policies[name]
                lines.append(
                    f"- `{name}`: reward `{item['mean_reward']:.2f}`, "
                    f"oracle gap `{item['oracle_gap']:.2f}`, success `{item['success_rate']:.2f}`"
                )

    if stability:
        aggregate = stability.get("aggregate", {})
        selector_reward = aggregate.get("selector_linucb", {}).get("mean_reward")
        if selector_reward:
            lines.extend(
                [
                    "",
                    "## Stability",
                    "",
                    f"- Selector mean reward across seeds: `{selector_reward['mean']:.2f}` +/- `{selector_reward['std']:.2f}`",
                ]
            )

    lines.extend(
        [
            "",
            "## Outputs",
            "",
        ]
    )
    for step in manifest["steps"]:
        for output in step.get("outputs", []):
            lines.append(f"- `{output}`")

    text = "\n".join(lines) + "\n"
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(text, encoding="utf-8")
    return text


def environment_snapshot() -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "matplotlib", "wfdb", "pandas", "scipy", "torch"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def expected_step_outputs(name: str, run_dir: str | Path) -> list[str]:
    run_dir = Path(run_dir)
    outputs = {
        "phase2_figures": [
            run_dir / "figures" / "phase2_matrix_summary.csv",
            run_dir / "figures" / "phase2_success_rate.png",
            run_dir / "figures" / "phase2_mean_energy.png",
            run_dir / "figures" / "phase2_mean_time_s.png",
            run_dir / "figures" / "phase2_mean_safety_violations.png",
            run_dir / "figures" / "phase2_mean_reward.png",
        ],
        "calibration_report": [run_dir / "calibration_report.json"],
        "selector_report": [run_dir / "selector_report.json", run_dir / "selector_report.csv"],
        "decision_boundary": [run_dir / "figures" / "decision_boundary.png", run_dir / "decision_boundary.csv"],
        "bootstrap_ci": [run_dir / "bootstrap_matrix_ci.csv"],
        "selector_stability": [run_dir / "selector_stability.json", run_dir / "selector_stability.csv"],
        "noise_ood_sweep": [run_dir / "noise_ood_sweep.json", run_dir / "noise_ood_sweep.csv"],
        "fallback_threshold_sweep": [
            run_dir / "fallback_threshold_sweep.json",
            run_dir / "fallback_threshold_sweep.csv",
            run_dir / "fallback_threshold_sweep.partial.json",
            run_dir / "fallback_threshold_sweep.partial.csv",
        ],
    }
    if name not in outputs:
        raise ValueError(f"Unknown bundle step: {name}")
    return [str(path) for path in outputs[name]]


def inspect_bundle_progress(
    run_dir: str | Path,
    config: dict[str, Any] | None = None,
    write_files: bool = False,
) -> dict[str, Any]:
    """Return a progress snapshot, inferring completed steps from files if needed."""

    run_dir = Path(run_dir)
    manifest_path = run_dir / "run_manifest.json"
    manifest = _read_json_if_exists(manifest_path)
    if manifest is None:
        manifest = {
            "run_id": run_dir.name,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "duration_s": 0.0,
            "run_dir": str(run_dir),
            "config": config or {},
            "environment": environment_snapshot(),
            "steps": [],
            "step_order": _enabled_step_order(config or {}),
            "run_status": "partial",
        }
    elif config:
        merged = dict(manifest.get("config", {}))
        merged.update(config)
        manifest["config"] = merged

    step_order = manifest.get("step_order") or _enabled_step_order(manifest.get("config", {}))
    existing = {step["name"]: step for step in manifest.get("steps", [])}
    inferred_steps = []
    current_step = manifest.get("current_step")
    found_first_incomplete = False
    for name in step_order:
        expected_outputs = expected_step_outputs(name, run_dir)
        prior = existing.get(name)
        if prior and prior.get("status") in {"ok", "skipped", "failed"}:
            inferred_steps.append(prior)
            continue
        if _outputs_complete(expected_outputs):
            inferred_steps.append(
                BundleStep(
                    name=name,
                    status="ok",
                    duration_s=0.0,
                    outputs=expected_outputs,
                    message="Inferred from existing outputs",
                ).__dict__
            )
        else:
            is_running_manifest = manifest.get("run_status") == "running"
            status = "running" if is_running_manifest and current_step == name and not found_first_incomplete else "pending"
            if not found_first_incomplete and not current_step:
                status = "pending"
                current_step = name
            found_first_incomplete = True
            message = "Awaiting outputs"
            if name == "fallback_threshold_sweep":
                partial_path = run_dir / "fallback_threshold_sweep.partial.json"
                if partial_path.exists():
                    partial = _read_json_if_exists(partial_path) or {}
                    completed_configs = partial.get("completed_configs", len(partial.get("configs", [])))
                    total_configs = partial.get("total_configs", "")
                    completed_profiles = partial.get("completed_profiles", 0)
                    total_profiles = partial.get("total_profiles", 0)
                    partial_message = partial.get("message", "")
                    if total_profiles:
                        message = (
                            f"{partial.get('run_status', 'running')}: profiles "
                            f"{completed_profiles}/{total_profiles}; configs {completed_configs}/{total_configs}"
                        )
                    else:
                        message = f"Checkpointed configs {completed_configs}/{total_configs}"
                    if partial_message:
                        message = f"{message}. {partial_message}"
            inferred_steps.append(
                BundleStep(
                    name=name,
                    status=status,
                    duration_s=0.0,
                    outputs=[path for path in expected_outputs if Path(path).exists()],
                    message=message,
                ).__dict__
            )

    completed = sum(1 for step in inferred_steps if step["status"] in {"ok", "skipped"})
    if completed == len(step_order):
        run_status = "completed"
        current_step = None
    elif manifest.get("run_status") == "running":
        run_status = "running"
    else:
        run_status = "partial"

    snapshot = dict(manifest)
    snapshot.update(
        {
            "run_dir": str(run_dir),
            "steps": inferred_steps,
            "step_order": step_order,
            "run_status": run_status,
            "current_step": current_step,
            "completed_steps": completed,
            "total_steps": len(step_order),
            "progress_fraction": (completed / len(step_order)) if step_order else 0.0,
            "manifest_path": str(run_dir / "run_manifest.json"),
            "progress_json_path": str(run_dir / "run_progress.json"),
            "progress_md_path": str(run_dir / "run_progress.md"),
        }
    )
    if write_files:
        _write_progress_files(snapshot, run_dir)
    return snapshot


def render_progress_markdown(manifest: dict[str, Any]) -> str:
    completed = int(manifest.get("completed_steps", _count_completed(manifest.get("steps", []))))
    total = int(manifest.get("total_steps", len(manifest.get("step_order", []))))
    fraction = float(manifest.get("progress_fraction", (completed / total) if total else 0.0))
    lines = [
        "# Run Progress",
        "",
        f"- Run ID: `{manifest.get('run_id', '')}`",
        f"- Status: `{manifest.get('run_status', '')}`",
        f"- Progress: `{completed}/{total}` ({fraction * 100.0:.1f}%)",
        f"- Current step: `{manifest.get('current_step') or ''}`",
        f"- Run directory: `{manifest.get('run_dir', '')}`",
        "",
        "| Step | Status | Duration s | Outputs | Message |",
        "| --- | --- | --- | --- | --- |",
    ]
    for step in manifest.get("steps", []):
        outputs = len(step.get("outputs", []))
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.get("name", "")),
                    str(step.get("status", "")),
                    f"{float(step.get('duration_s', 0.0)):.2f}",
                    str(outputs),
                    str(step.get("message", "")).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Live Commands",
            "",
            f"- Refresh progress: `python scripts/show_run_progress.py {manifest.get('run_dir', '')}`",
            f"- Generate current paper artifacts: `python scripts/generate_live_report.py {manifest.get('run_dir', '')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _base_manifest(
    run_id: str,
    run_dir: Path,
    config: dict[str, Any],
    started: float,
    step_order: list[str],
    steps: list[BundleStep],
    run_status: str,
    current_step: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    completed = sum(1 for step in steps if step.status in {"ok", "skipped"})
    total = len(step_order)
    manifest_path = run_dir / "run_manifest.json"
    progress_json = run_dir / "run_progress.json"
    progress_md = run_dir / "run_progress.md"
    return {
        "run_id": run_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "duration_s": float(time.perf_counter() - started),
        "run_dir": str(run_dir),
        "config": config,
        "environment": environment_snapshot(),
        "provenance": provenance,
        "step_order": step_order,
        "steps": [step.__dict__ for step in steps],
        "run_status": run_status,
        "current_step": current_step,
        "completed_steps": completed,
        "total_steps": total,
        "progress_fraction": (completed / total) if total else 0.0,
        "manifest_path": str(manifest_path),
        "progress_json_path": str(progress_json),
        "progress_md_path": str(progress_md),
    }


def _write_progress_files(
    manifest: dict[str, Any],
    run_dir: Path,
    recorder: RunRecorder | None = None,
) -> None:
    _write_json(manifest, run_dir / "run_manifest.json")
    _write_json(manifest, run_dir / "run_progress.json")
    if recorder is None:
        recorder = RunRecorder(run_dir, str(manifest.get("run_id", Path(run_dir).name)))
    recorder.write_current(manifest)
    progress_md = run_dir / "run_progress.md"
    progress_md.parent.mkdir(parents=True, exist_ok=True)
    progress_md.write_text(render_progress_markdown(manifest), encoding="utf-8")


def _step_heartbeat(
    run_id: str,
    run_dir: Path,
    config: dict[str, Any],
    started: float,
    step_order: list[str],
    steps: list[BundleStep],
    current_step: str,
    recorder: RunRecorder,
    provenance: dict[str, Any],
) -> Callable[[], None]:
    def beat() -> None:
        recorder.progress(
            step=current_step,
            message=f"Running {current_step}.",
            phase="step_running",
        )
        snapshot = _base_manifest(
            run_id=run_id,
            run_dir=run_dir,
            config=config,
            started=started,
            step_order=step_order,
            steps=steps,
            run_status="running",
            current_step=current_step,
            provenance=provenance,
        )
        recorder.write_current(snapshot)

    return beat


def _enabled_step_order(config: dict[str, Any]) -> list[str]:
    all_steps = [
        "phase2_figures",
        "calibration_report",
        "selector_report",
        "decision_boundary",
        "bootstrap_ci",
        "selector_stability",
        "noise_ood_sweep",
        "fallback_threshold_sweep",
    ]
    enabled = set(config.get("enabled_steps") or all_steps)
    return [name for name in all_steps if name in enabled]


def _outputs_complete(paths: list[str]) -> bool:
    required = [path for path in paths if ".partial." not in path]
    return bool(required) and all(Path(path).exists() for path in required)


def _count_completed(steps: list[dict[str, Any]]) -> int:
    return sum(1 for step in steps if step.get("status") in {"ok", "skipped"})


def _run_step(
    name: str,
    fn: Callable[[], list[str] | dict[str, str] | str],
    recorder: RunRecorder | None = None,
    heartbeat: Callable[[], None] | None = None,
    heartbeat_interval_s: float = 30.0,
) -> BundleStep:
    start = time.perf_counter()
    stop_heartbeat = threading.Event()
    heartbeat_thread: threading.Thread | None = None
    if heartbeat is not None:
        def run_heartbeat() -> None:
            while not stop_heartbeat.wait(heartbeat_interval_s):
                try:
                    heartbeat()
                except Exception as exc:
                    if recorder is not None:
                        recorder.event("warning", step=name, status="warning", message=f"Heartbeat failed: {exc}")

        heartbeat_thread = threading.Thread(target=run_heartbeat, name=f"{name}-heartbeat", daemon=True)
        heartbeat_thread.start()
    try:
        result = fn()
        outputs = _normalize_outputs(result)
        return BundleStep(name=name, status="ok", duration_s=float(time.perf_counter() - start), outputs=outputs)
    except GracefulStopRequested as exc:
        if recorder is not None:
            recorder.event("step_progress", step=name, status="stopped", message=str(exc), fsync=True)
        return BundleStep(
            name=name,
            status="stopped",
            duration_s=float(time.perf_counter() - start),
            outputs=[],
            message=str(exc),
        )
    except Exception as exc:
        if recorder is not None:
            recorder.failure_summary(name, exc)
            recorder.event("step_failed", step=name, status="failed", message=str(exc), fsync=True)
        return BundleStep(
            name=name,
            status="failed",
            duration_s=float(time.perf_counter() - start),
            outputs=[],
            message=str(exc),
        )
    finally:
        stop_heartbeat.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=1.0)


def _reward_weights_from_config(config: dict[str, Any]) -> RewardWeights:
    raw = config.get("reward_weights") or {}
    return RewardWeights(
        success_bonus=float(raw.get("success_bonus", RewardWeights.success_bonus)),
        energy_weight=float(raw.get("energy_weight", RewardWeights.energy_weight)),
        time_weight=float(raw.get("time_weight", RewardWeights.time_weight)),
        safety_weight=float(raw.get("safety_weight", RewardWeights.safety_weight)),
    )


def _selector_report_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
) -> list[str]:
    report = build_selector_report(
        patients_per_scenario=patients,
        train_fraction=float(config.get("train_fraction", 0.7)),
        seed=int(config.get("selector_seed", 7)),
        horizon_s=horizon,
        weights=weights,
        n_jobs=n_jobs,
    )
    json_path = run_dir / "selector_report.json"
    csv_path = run_dir / "selector_report.csv"
    save_selector_report(report, json_path, csv_path)
    return [str(json_path), str(csv_path)]


def _decision_boundary_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
) -> list[str]:
    grid = decision_boundary_grid(
        patients_per_scenario=patients,
        grid_size=int(config.get("decision_grid_size", 60)),
        horizon_s=horizon,
        weights=weights,
        n_jobs=n_jobs,
    )
    png_path = run_dir / "figures" / "decision_boundary.png"
    csv_path = run_dir / "decision_boundary.csv"
    save_decision_boundary(grid, png_path, csv_path)
    return [str(png_path), str(csv_path)]


def _bootstrap_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
) -> list[str]:
    rows = run_bootstrap_matrix_report(
        patients_per_scenario=patients,
        n_bootstrap=int(config.get("bootstrap_samples", 200)),
        horizon_s=horizon,
        seed=int(config.get("selector_seed", 7)),
        weights=weights,
        n_jobs=n_jobs,
    )
    output = run_dir / "bootstrap_matrix_ci.csv"
    save_bootstrap_ci(rows, output)
    return [str(output)]


def _selector_stability_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
) -> list[str]:
    report = selector_stability_report(
        patients_per_scenario=patients,
        seeds=config.get("selector_stability_seeds", [1, 7, 13]),
        train_fraction=float(config.get("train_fraction", 0.7)),
        horizon_s=horizon,
        weights=weights,
        n_jobs=n_jobs,
    )
    json_path = run_dir / "selector_stability.json"
    csv_path = run_dir / "selector_stability.csv"
    save_selector_stability(report, json_path, csv_path)
    return [str(json_path), str(csv_path)]


def _noise_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
    progress_callback: Callable[..., None] | None = None,
) -> list[str]:
    report = noise_ood_sweep(
        patients_per_scenario=patients,
        profile_names=config.get("noise_profiles", ["clean", "severe"]),
        train_fraction=float(config.get("train_fraction", 1.0)),
        horizon_s=horizon,
        weights=weights,
        n_jobs=n_jobs,
        progress_callback=progress_callback,
    )
    json_path = run_dir / "noise_ood_sweep.json"
    csv_path = run_dir / "noise_ood_sweep.csv"
    save_noise_ood_sweep(report, json_path, csv_path)
    return [str(json_path), str(csv_path)]


def _fallback_outputs(
    config: dict[str, Any],
    run_dir: Path,
    patients: int,
    horizon: float,
    weights: RewardWeights,
    n_jobs: int | str | None,
    progress_callback: Callable[..., None] | None = None,
) -> list[str]:
    profiles = get_noise_profiles(config.get("noise_profiles", ["severe"]))
    real_stats = config.get("real_noise_stats")
    if real_stats and Path(real_stats).exists():
        profiles.append(load_noise_profile_from_stats(real_stats))
    category_stats = config.get("category_noise_stats")
    if category_stats and Path(category_stats).exists():
        profiles.extend(load_profiles_from_category_stats(category_stats))
    partial_json = run_dir / "fallback_threshold_sweep.partial.json"
    partial_csv = run_dir / "fallback_threshold_sweep.partial.csv"
    report = fallback_threshold_sweep(
        patients_per_scenario=patients,
        profiles=profiles,
        min_sqi_values=[float(value) for value in config.get("fallback_min_sqi", [0.35, 0.42])],
        entropy_values=[float(value) for value in config.get("fallback_entropy", [0.62])],
        rr_cv_values=[float(value) for value in config.get("fallback_rr_cv", [0.30])],
        horizon_s=horizon,
        train_fraction=float(config.get("train_fraction", 1.0)),
        checkpoint_json=partial_json,
        checkpoint_csv=partial_csv,
        resume=True,
        weights=weights,
        n_jobs=n_jobs,
        progress_callback=progress_callback,
    )
    json_path = run_dir / "fallback_threshold_sweep.json"
    csv_path = run_dir / "fallback_threshold_sweep.csv"
    save_threshold_sweep(report, json_path, csv_path)
    return [str(json_path), str(csv_path), str(partial_json), str(partial_csv)]


def _record_step_outputs(recorder: RunRecorder, step: str, outputs: list[str]) -> None:
    for output in outputs:
        path = Path(output)
        status = "partial" if ".partial." in path.name else "final"
        if path.exists():
            recorder.artifact(path, step=step, status=status)
    _record_metrics_from_outputs(recorder, step, outputs)


def _record_metrics_from_outputs(recorder: RunRecorder, step: str, outputs: list[str]) -> None:
    for output in outputs:
        path = Path(output)
        if not path.exists() or path.suffix.lower() != ".json":
            continue
        payload = _read_json_if_exists(path)
        if not payload:
            continue
        if step == "selector_report":
            _record_policy_summary_metrics(recorder, step, payload.get("policy_summary", {}))
        elif step == "selector_stability":
            aggregate = payload.get("aggregate", {})
            for policy, metrics in aggregate.items():
                for metric_name, values in metrics.items():
                    mean = values.get("mean") if isinstance(values, dict) else None
                    if mean is not None:
                        recorder.metric(step, f"{policy}.{metric_name}.mean", float(mean))
        elif step == "noise_ood_sweep":
            for idx, profile in enumerate(payload.get("profiles", [])):
                profile_name = profile.get("profile", {}).get("name", f"profile_{idx}")
                _record_policy_summary_metrics(
                    recorder,
                    step,
                    profile.get("policies", {}),
                    prefix=f"{profile_name}.",
                    x=idx,
                    x_name="profile_index",
                )
        elif step == "fallback_threshold_sweep":
            configs = payload.get("configs", [])
            for cfg_idx, config_report in enumerate(configs):
                for profile in config_report.get("profiles", []):
                    profile_name = profile.get("profile", {}).get("name", "profile")
                    _record_policy_summary_metrics(
                        recorder,
                        step,
                        profile.get("policies", {}),
                        prefix=f"config_{cfg_idx}.{profile_name}.",
                        x=cfg_idx,
                        x_name="config_index",
                    )


def _record_policy_summary_metrics(
    recorder: RunRecorder,
    step: str,
    policy_summary: dict[str, Any],
    prefix: str = "",
    x: int | float | None = None,
    x_name: str | None = None,
) -> None:
    for policy, metrics in policy_summary.items():
        if not isinstance(metrics, dict):
            continue
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                recorder.metric(step, f"{prefix}{policy}.{metric_name}", float(value), x=x, x_name=x_name)


def _write_json(payload: dict[str, Any], output: str | Path) -> str:
    output = Path(output)
    atomic_write_json(payload, output)
    return str(output)


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_outputs(result: list[str] | dict[str, str] | str) -> list[str]:
    if isinstance(result, str):
        return [result]
    if isinstance(result, dict):
        return [str(value) for value in result.values()]
    return [str(value) for value in result]
