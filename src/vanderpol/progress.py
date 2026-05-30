"""Run observability helpers for long-running experiment bundles."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import request


SCHEMA_VERSION = 1
DEFAULT_STALE_AFTER_S = 5 * 60
DEFAULT_STALLED_AFTER_S = 15 * 60


class GracefulStopRequested(RuntimeError):
    """Raised when a checkpoint-safe stop request has been observed."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_write_json(payload: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path: str | Path, payload: dict[str, Any], fsync: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())


def load_json(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def load_jsonl(path: str | Path, tail: int | None = None) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if tail is not None and tail >= 0:
        lines = lines[-tail:]
    events = []
    for line in lines:
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def sha256_file(path: str | Path, max_bytes: int | None = None) -> str | None:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    read_total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            read_total += len(chunk)
            if max_bytes is not None and read_total >= max_bytes:
                return None
    return digest.hexdigest()


def artifact_kind(path: str | Path) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"csv", "json", "png", "jpg", "jpeg", "md", "html", "txt", "log"}:
        return suffix
    return suffix or "file"


def is_bad_number(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


def collect_provenance(config: dict[str, Any], command_line: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": utc_now(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "command_line": command_line or sys.argv,
        "resolved_config": config,
        "git": _git_snapshot(),
        "packages": _package_snapshot(),
    }


def classify_snapshot(
    snapshot: dict[str, Any],
    now_s: float | None = None,
    stale_after_s: int = DEFAULT_STALE_AFTER_S,
    stalled_after_s: int = DEFAULT_STALLED_AFTER_S,
) -> str:
    status = str(snapshot.get("status") or snapshot.get("run_status") or "").lower()
    if status in {"completed", "failed", "stopped"}:
        return status
    heartbeat = snapshot.get("heartbeat_at") or snapshot.get("updated_at") or snapshot.get("created_at_utc")
    if not heartbeat:
        return "unknown"
    age = _age_seconds(str(heartbeat), now_s=now_s)
    if age is None:
        return status or "unknown"
    if age >= stalled_after_s:
        return "stalled"
    if age >= stale_after_s:
        return "stale"
    return status or "running"


def fold_events(events: list[dict[str, Any]], run_id: str, run_dir: str | Path) -> dict[str, Any]:
    steps: dict[str, dict[str, Any]] = {}
    latest: dict[str, Any] | None = None
    run_status = "unknown"
    current_step = None
    for event in events:
        latest = event
        event_type = event.get("event_type")
        step = event.get("step")
        if event_type == "run_started":
            run_status = "running"
        elif event_type == "run_done":
            run_status = "completed"
            current_step = None
        elif event_type == "run_stopped":
            run_status = "stopped"
            current_step = None
        elif event_type == "run_failed":
            run_status = "failed"
            current_step = None
        elif event_type in {"step_started", "step_progress"} and step:
            run_status = "running"
            current_step = str(step)
            item = steps.setdefault(str(step), {"name": str(step)})
            item.update(
                {
                    "status": "running",
                    "message": event.get("message", ""),
                    "updated_at": event.get("created_at"),
                    "detail": event.get("detail", {}),
                }
            )
        elif event_type == "step_done" and step:
            item = steps.setdefault(str(step), {"name": str(step)})
            item.update(
                {
                    "status": event.get("status") or "ok",
                    "message": event.get("message", ""),
                    "updated_at": event.get("created_at"),
                    "outputs": event.get("outputs", []),
                }
            )
        elif event_type == "step_failed" and step:
            run_status = "failed"
            item = steps.setdefault(str(step), {"name": str(step)})
            item.update(
                {
                    "status": "failed",
                    "message": event.get("message", ""),
                    "updated_at": event.get("created_at"),
                }
            )
    step_list = list(steps.values())
    completed = sum(1 for step in step_list if step.get("status") in {"ok", "skipped"})
    total = len(step_list)
    heartbeat = latest.get("created_at") if latest else None
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": run_status,
        "run_status": run_status,
        "current_step": current_step,
        "heartbeat_at": heartbeat,
        "updated_at": heartbeat,
        "completed_steps": completed,
        "total_steps": total,
        "progress_fraction": (completed / total) if total else 0.0,
        "steps": step_list,
    }
    snapshot["classification"] = classify_snapshot(snapshot)
    return snapshot


def check_stop_requested(run_dir: str | Path) -> None:
    if (Path(run_dir) / "STOP_REQUESTED").exists():
        raise GracefulStopRequested("Stop requested; exiting after current checkpoint.")


def request_stop(run_dir: str | Path, reason: str = "") -> Path:
    path = Path(run_dir) / "STOP_REQUESTED"
    path.write_text(json.dumps({"created_at": utc_now(), "reason": reason}) + "\n", encoding="utf-8")
    return path


@dataclass
class RunRecorder:
    run_dir: Path
    run_id: str

    def __init__(self, run_dir: str | Path, run_id: str):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    @property
    def events_path(self) -> Path:
        return self.run_dir / "events.jsonl"

    @property
    def metrics_path(self) -> Path:
        return self.run_dir / "metrics.jsonl"

    @property
    def artifacts_path(self) -> Path:
        return self.run_dir / "artifacts.jsonl"

    def event(
        self,
        event_type: str,
        step: str | None = None,
        status: str | None = None,
        message: str = "",
        detail: dict[str, Any] | None = None,
        fsync: bool = False,
        **extra: Any,
    ) -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "event_type": event_type,
            "created_at": utc_now(),
            "step": step,
            "status": status,
            "message": message,
            "detail": detail or {},
            **extra,
        }
        append_jsonl(self.events_path, payload, fsync=fsync)
        return payload

    def progress(
        self,
        step: str,
        message: str = "",
        status: str = "running",
        fsync: bool = False,
        **detail: Any,
    ) -> dict[str, Any]:
        return self.event(
            "step_progress",
            step=step,
            status=status,
            message=message,
            detail=detail,
            fsync=fsync,
        )

    def metric(
        self,
        step: str,
        name: str,
        value: float,
        x: int | float | None = None,
        x_name: str | None = None,
        unit: str | None = None,
    ) -> dict[str, Any]:
        numeric_value = float(value)
        bad_value = is_bad_number(numeric_value)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "created_at": utc_now(),
            "step": step,
            "name": name,
            "value": None if bad_value else numeric_value,
            "bad_value": repr(numeric_value) if bad_value else None,
            "x": x,
            "x_name": x_name,
            "unit": unit,
        }
        append_jsonl(self.metrics_path, payload)
        if bad_value:
            self.event("warning", step=step, status="warning", message=f"Bad metric value: {name}={value}")
        return payload

    def artifact(self, path: str | Path, step: str, status: str = "final", hash_final: bool = True) -> dict[str, Any]:
        path = Path(path)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "created_at": utc_now(),
            "step": step,
            "path": str(path),
            "kind": artifact_kind(path),
            "status": status,
            "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            "sha256": sha256_file(path) if hash_final and status == "final" and path.exists() and path.is_file() else None,
        }
        append_jsonl(self.artifacts_path, payload)
        self.event("artifact_written", step=step, status=status, message=str(path), artifact=payload)
        return payload

    def write_current(self, snapshot: dict[str, Any]) -> None:
        now = utc_now()
        enriched = {
            "schema_version": SCHEMA_VERSION,
            **snapshot,
        }
        enriched["heartbeat_at"] = now
        enriched["updated_at"] = now
        enriched["status"] = snapshot.get("run_status", snapshot.get("status", "unknown"))
        enriched["classification"] = classify_snapshot(enriched)
        atomic_write_json(enriched, self.run_dir / "current_progress.json")

    def failure_summary(self, step: str | None, exc: BaseException, stderr_tail: str = "") -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "created_at": utc_now(),
            "step": step,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-80:],
            "stderr_tail": stderr_tail.splitlines()[-80:] if stderr_tail else [],
            "last_events": load_jsonl(self.events_path, tail=20),
        }
        atomic_write_json(payload, self.run_dir / "failure_summary.json")
        return payload

    def notify(self, event_type: str, payload: dict[str, Any], config: dict[str, Any]) -> None:
        webhook = _notification_webhook(config)
        if not webhook:
            return
        body = json.dumps({"event_type": event_type, "run_id": self.run_id, **payload}).encode("utf-8")
        try:
            req = request.Request(webhook, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with request.urlopen(req, timeout=10):
                pass
        except Exception as exc:  # pragma: no cover - network behavior varies.
            self.event("warning", status="warning", message=f"Notification failed: {exc}")


def _git_snapshot() -> dict[str, Any]:
    def run_git(args: list[str]) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5)
        except Exception:
            return None

    inside = run_git(["rev-parse", "--is-inside-work-tree"])
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"available": False}
    commit = run_git(["rev-parse", "HEAD"])
    status = run_git(["status", "--short"])
    return {
        "available": True,
        "commit": commit.stdout.strip() if commit and commit.returncode == 0 else None,
        "dirty": bool(status and status.stdout.strip()),
        "status_short": status.stdout.splitlines() if status and status.returncode == 0 else [],
    }


def _package_snapshot() -> dict[str, str | None]:
    try:
        from importlib import metadata
    except Exception:
        return {}
    packages = {}
    for name in ("numpy", "matplotlib", "wfdb", "pandas", "scipy", "torch"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return packages


def _notification_webhook(config: dict[str, Any]) -> str | None:
    notifications = config.get("notifications") or {}
    return notifications.get("webhook_url") or os.environ.get("VANDERPOL_NOTIFY_WEBHOOK")


def _age_seconds(value: str, now_s: float | None = None) -> float | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (now_s or time.time()) - parsed.timestamp()
