from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vanderpol.progress import append_jsonl, atomic_write_json, request_stop, utc_now
from vanderpol.stage8 import load_bundle_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Continuously run experiment bundles with small deterministic config mutations."
    )
    parser.add_argument("--base-config", type=Path, default=Path("configs/bundle_smoke.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--controller-dir", type=Path, default=Path("outputs/runs/codex_auto_mutation"))
    parser.add_argument("--run-prefix", default="codex_auto_mut")
    parser.add_argument("--start-iteration", type=int, default=None)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--delay-s", type=float, default=2.0)
    parser.add_argument("--poll-s", type=float, default=5.0)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--clear-stop", action="store_true")
    args = parser.parse_args()

    output_dir = (ROOT / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    controller_dir = (
        (ROOT / args.controller_dir).resolve()
        if not args.controller_dir.is_absolute()
        else args.controller_dir
    )
    config_dir = controller_dir / "configs"
    log_dir = controller_dir / "logs"
    state_path = controller_dir / "state.json"
    history_path = controller_dir / "history.jsonl"
    stop_path = controller_dir / "STOP"
    controller_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.clear_stop and stop_path.exists():
        stop_path.unlink()

    base_config = load_bundle_config(args.base_config)
    iteration = args.start_iteration or next_iteration(args.run_prefix, output_dir, state_path)
    max_iteration = None if args.max_iterations is None else iteration + args.max_iterations - 1

    write_state(
        state_path,
        status="running",
        pid=os.getpid(),
        controller_dir=str(controller_dir),
        stop_file=str(stop_path),
        iteration=iteration,
    )

    while True:
        if stop_path.exists():
            write_state(state_path, status="stopped", pid=os.getpid(), iteration=iteration)
            append_jsonl(history_path, event("runner_stopped", iteration=iteration, reason="STOP file exists"))
            return
        if max_iteration is not None and iteration > max_iteration:
            write_state(state_path, status="completed", pid=os.getpid(), iteration=iteration)
            append_jsonl(history_path, event("runner_completed", iteration=iteration))
            return

        run_id = f"{args.run_prefix}_{iteration:04d}"
        run_dir = output_dir / run_id
        config = mutate_config(base_config, iteration, n_jobs=args.n_jobs)
        config_path = config_dir / f"{run_id}.json"
        atomic_write_json(config, config_path)

        append_jsonl(
            history_path,
            event(
                "run_started",
                iteration=iteration,
                run_id=run_id,
                config_path=str(config_path),
                run_dir=str(run_dir),
                mutation_summary=mutation_summary(config),
            ),
            fsync=True,
        )
        exit_code = run_bundle(
            config_path=config_path,
            output_dir=output_dir,
            run_id=run_id,
            run_dir=run_dir,
            log_path=log_dir / f"{run_id}.log",
            state_path=state_path,
            stop_path=stop_path,
            poll_s=args.poll_s,
            iteration=iteration,
        )
        status = read_manifest_status(run_dir)
        append_jsonl(
            history_path,
            event(
                "run_finished",
                iteration=iteration,
                run_id=run_id,
                exit_code=exit_code,
                run_status=status,
                run_dir=str(run_dir),
            ),
            fsync=True,
        )
        write_state(
            state_path,
            status="running" if not stop_path.exists() else "stopping",
            pid=os.getpid(),
            iteration=iteration,
            last_run_id=run_id,
            last_exit_code=exit_code,
            last_run_status=status,
        )
        if stop_path.exists():
            write_state(state_path, status="stopped", pid=os.getpid(), iteration=iteration, last_run_id=run_id)
            return
        iteration += 1
        time.sleep(max(args.delay_s, 0.0))


def run_bundle(
    *,
    config_path: Path,
    output_dir: Path,
    run_id: str,
    run_dir: Path,
    log_path: Path,
    state_path: Path,
    stop_path: Path,
    poll_s: float,
    iteration: int,
) -> int:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT / "src") if not existing_pythonpath else f"{ROOT / 'src'}{os.pathsep}{existing_pythonpath}"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_experiment_bundle.py"),
        "--config",
        str(config_path),
        "--output-dir",
        str(output_dir),
        "--run-id",
        run_id,
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        stop_forwarded = False
        while process.poll() is None:
            write_state(
                state_path,
                status="running",
                pid=os.getpid(),
                child_pid=process.pid,
                iteration=iteration,
                current_run_id=run_id,
                current_run_dir=str(run_dir),
                current_log=str(log_path),
                stop_file=str(stop_path),
            )
            if stop_path.exists() and not stop_forwarded:
                request_stop(run_dir, reason="auto mutation runner STOP file requested")
                stop_forwarded = True
                write_state(
                    state_path,
                    status="stopping",
                    pid=os.getpid(),
                    child_pid=process.pid,
                    iteration=iteration,
                    current_run_id=run_id,
                    current_run_dir=str(run_dir),
                    stop_file=str(stop_path),
                )
            time.sleep(max(poll_s, 1.0))
        return int(process.returncode or 0)


def mutate_config(base: dict[str, Any], iteration: int, *, n_jobs: int) -> dict[str, Any]:
    cfg = dict(base)
    seed = int(base.get("selector_seed", 7)) + iteration * 11
    train_fraction_cycle = [0.60, 0.65, 0.70, 0.75, 0.80]
    horizon_cycle = [3.0, 3.5, 4.0, 4.5, 5.0]
    noise_cycle = [
        ["clean", "severe"],
        ["clean", "mild", "severe"],
        ["clean", "moderate", "severe"],
        ["mild", "moderate", "severe"],
    ]
    idx = iteration - 1

    cfg.update(
        {
            "preset": "codex_auto_mutation",
            "patients_per_scenario": 1 if iteration % 4 else 2,
            "horizon_s": horizon_cycle[idx % len(horizon_cycle)],
            "train_fraction": train_fraction_cycle[idx % len(train_fraction_cycle)],
            "selector_seed": seed,
            "selector_stability_seeds": [seed, seed + 1],
            "bootstrap_samples": 20 + 5 * (idx % 5),
            "decision_grid_size": 8 + 2 * (idx % 5),
            "noise_profiles": noise_cycle[idx % len(noise_cycle)],
            "fallback_min_sqi": sorted(
                {
                    round(0.32 + 0.02 * (idx % 8), 2),
                    round(0.42 + 0.02 * ((idx + 2) % 6), 2),
                }
            ),
            "fallback_entropy": [round(0.56 + 0.02 * (idx % 5), 2)],
            "fallback_rr_cv": [round(0.24 + 0.02 * (idx % 6), 2)],
            "reward_weights": {
                "success_bonus": 100.0,
                "time_weight": round(0.8 + 0.1 * (idx % 5), 2),
                "energy_weight": round(0.002 * (idx % 4), 4),
                "safety_weight": float(idx % 3),
            },
            "n_jobs": max(int(n_jobs), 1),
        }
    )
    return cfg


def mutation_summary(config: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "patients_per_scenario",
        "horizon_s",
        "train_fraction",
        "selector_seed",
        "bootstrap_samples",
        "decision_grid_size",
        "noise_profiles",
        "fallback_min_sqi",
        "fallback_entropy",
        "fallback_rr_cv",
        "reward_weights",
        "n_jobs",
    ]
    return {key: config.get(key) for key in keys}


def next_iteration(prefix: str, output_dir: Path, state_path: Path) -> int:
    state = load_json(state_path)
    if state and isinstance(state.get("iteration"), int):
        return int(state["iteration"]) + 1
    existing = []
    if output_dir.exists():
        for path in output_dir.glob(f"{prefix}_*"):
            suffix = path.name.removeprefix(f"{prefix}_")
            if suffix.isdigit():
                existing.append(int(suffix))
    return (max(existing) + 1) if existing else 1


def read_manifest_status(run_dir: Path) -> str:
    manifest = load_json(run_dir / "run_manifest.json")
    if not manifest:
        return "unknown"
    return str(manifest.get("run_status") or manifest.get("status") or "unknown")


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_state(path: Path, **payload: Any) -> None:
    previous = load_json(path) or {}
    merged = {**previous, **payload, "updated_at": utc_now()}
    atomic_write_json(merged, path)


def event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"event_type": event_type, "created_at": utc_now(), **payload}


if __name__ == "__main__":
    main()
