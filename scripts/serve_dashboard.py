from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import request
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.dashboard import (  # noqa: E402
    artifact_response,
    compare_runs,
    dry_run_estimate,
    list_runs,
    load_failure,
    load_run_artifacts,
    load_run_diagnostics,
    load_run_events,
    load_run_metrics,
    load_run_progress,
    render_dashboard_html,
    tail_text,
)
from vanderpol.progress import append_jsonl, atomic_write_json, request_stop  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local read-only experiment dashboard.")
    parser.add_argument("--runs-dir", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    runs_dir = args.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    handler = _handler_factory(runs_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    _start_watcher(runs_dir)
    print(f"Serving Vanderpol dashboard at http://{args.host}:{args.port}/")
    print(f"Runs directory: {runs_dir}")
    server.serve_forever()


def _handler_factory(runs_dir: Path) -> type[BaseHTTPRequestHandler]:
    tailadmin_assets_dir = (
        Path(__file__).resolve().parents[1]
        / "vendor"
        / "tailwind-admin-template"
        / "tailwind-admin-html-free"
        / "dist"
        / "assets"
    ).resolve()

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            try:
                if path == "/":
                    _send_bytes(self, render_dashboard_html().encode("utf-8"), "text/html; charset=utf-8")
                elif path.startswith("/tailadmin-assets/"):
                    self._handle_tailadmin_asset(path, tailadmin_assets_dir)
                elif path == "/api/runs":
                    _send_json(self, list_runs(runs_dir))
                elif path.startswith("/api/runs/"):
                    self._handle_run_api(path, query)
                elif path == "/api/compare":
                    run_ids = _csv_query(query, "runs")
                    _send_json(self, compare_runs(run_ids, runs_dir))
                elif path == "/api/dry-run":
                    config_path = query.get("config", ["configs/bundle_smoke.json"])[0]
                    _send_json(self, dry_run_estimate(config_path))
                elif path == "/api/artifact":
                    self._handle_artifact(query)
                elif path == "/api/log":
                    self._handle_log(query)
                else:
                    _send_json(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)
            except FileNotFoundError as exc:
                _send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                _send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                _send_json(self, {"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                payload = self._read_json_body()
                if path.startswith("/api/runs/"):
                    self._handle_run_post(path, payload)
                elif path == "/api/start":
                    _send_json(self, _start_run(payload, runs_dir))
                else:
                    _send_json(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)
            except FileNotFoundError as exc:
                _send_json(self, {"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                _send_json(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except RuntimeError as exc:
                _send_json(self, {"error": str(exc)}, HTTPStatus.CONFLICT)
            except Exception as exc:
                _send_json(self, {"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _handle_run_api(self, path: str, query: dict[str, list[str]]) -> None:
            parts = path.split("/")
            if len(parts) < 4:
                raise ValueError("Missing run id.")
            run_id = unquote(parts[3])
            suffix = parts[4] if len(parts) >= 5 else "progress"
            run_dir = _safe_run_dir(runs_dir, run_id)
            if suffix == "progress":
                _send_json(self, load_run_progress(run_dir))
            elif suffix == "events":
                tail = int(query.get("tail", ["200"])[0])
                _send_json(self, load_run_events(run_dir, tail=tail))
            elif suffix == "metrics":
                _send_json(self, load_run_metrics(run_dir))
            elif suffix == "artifacts":
                _send_json(self, load_run_artifacts(run_dir))
            elif suffix == "failure":
                _send_json(self, load_failure(run_dir) or {})
            elif suffix == "diagnostics":
                _send_json(self, load_run_diagnostics(run_dir))
            else:
                _send_json(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)

        def _handle_run_post(self, path: str, payload: dict[str, Any]) -> None:
            parts = path.split("/")
            if len(parts) < 5:
                raise ValueError("Missing run action.")
            run_id = unquote(parts[3])
            action = parts[4]
            run_dir = _safe_run_dir(runs_dir, run_id)
            if action in {"stop", "pause"}:
                marker = request_stop(run_dir, reason=str(payload.get("reason") or action))
                _send_json(self, {"ok": True, "action": action, "marker": str(marker)})
            elif action == "resume":
                progress = load_run_progress(run_dir)
                config = progress.get("config") or {}
                if not config:
                    raise ValueError("No config found for selected run.")
                _send_json(self, _start_run({"run_id": run_id, "config": config, "resume": True}, runs_dir))
            else:
                _send_json(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)

        def _handle_artifact(self, query: dict[str, list[str]]) -> None:
            run_id = query.get("run", [None])[0]
            requested_path = query.get("path", [None])[0]
            if not run_id or not requested_path:
                raise ValueError("Missing run or path.")
            run_dir = _safe_run_dir(runs_dir, run_id)
            payload, mime = artifact_response(run_dir, unquote(requested_path))
            _send_bytes(self, payload, mime)

        def _handle_log(self, query: dict[str, list[str]]) -> None:
            run_id = query.get("run", [None])[0]
            requested_path = query.get("path", [None])[0]
            if not run_id or not requested_path:
                raise ValueError("Missing run or path.")
            run_dir = _safe_run_dir(runs_dir, run_id)
            path = _safe_file_in_run(run_dir, unquote(requested_path))
            tail = int(query.get("tail", ["200"])[0])
            _send_json(self, {"path": str(path), "text": tail_text(path, max_lines=tail)})

        def _handle_tailadmin_asset(self, path: str, asset_root: Path) -> None:
            relative = unquote(path.removeprefix("/tailadmin-assets/"))
            file_path = (asset_root / relative).resolve()
            if asset_root not in file_path.parents and file_path != asset_root:
                raise FileNotFoundError("Asset outside TailAdmin directory.")
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError(str(file_path))
            mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            _send_bytes(self, file_path.read_bytes(), mime)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object.")
            return payload

    return DashboardHandler


def _csv_query(query: dict[str, list[str]], name: str) -> list[str]:
    values: list[str] = []
    for raw in query.get(name, []):
        values.extend([item.strip() for item in raw.split(",") if item.strip()])
    return values


def _safe_run_dir(runs_dir: Path, run_id: str) -> Path:
    run_dir = (runs_dir / run_id).resolve()
    if runs_dir not in run_dir.parents and run_dir != runs_dir:
        raise FileNotFoundError("Run outside runs directory.")
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"Run not found: {run_id}")
    return run_dir


def _safe_file_in_run(run_dir: Path, requested_path: str) -> Path:
    path = Path(requested_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    if run_dir not in path.parents and path != run_dir:
        raise FileNotFoundError("File outside run directory.")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def _safe_run_id(value: str) -> str:
    run_id = value.strip()
    if not run_id or not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id):
        raise ValueError("Run id must contain only letters, numbers, dot, dash, or underscore.")
    return run_id


def _start_run(payload: dict[str, Any], runs_dir: Path) -> dict[str, Any]:
    run_id = _safe_run_id(str(payload.get("run_id") or time.strftime("run_%Y%m%d_%H%M%S")))
    if _run_is_active(run_id):
        raise RuntimeError(f"Run is already active: {run_id}")
    run_dir = (runs_dir / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path: Path
    if "config" in payload:
        config = payload["config"]
        if not isinstance(config, dict):
            raise ValueError("config must be an object.")
        config_path = run_dir / "launch_config.json"
        atomic_write_json(config, config_path)
    else:
        raw_config = payload.get("config_path") or "configs/bundle_smoke.json"
        config_path = Path(str(raw_config)).resolve()
        if not config_path.exists():
            raise FileNotFoundError(str(config_path))

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stdout_path = run_dir / f"dashboard_launch_{timestamp}_stdout.log"
    stderr_path = run_dir / f"dashboard_launch_{timestamp}_stderr.log"
    cmd = [
        sys.executable,
        "scripts/run_experiment_bundle.py",
        "--config",
        str(config_path),
        "--output-dir",
        str(runs_dir),
        "--run-id",
        run_id,
    ]
    if payload.get("resume"):
        cmd.append("--resume")

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(cmd, cwd=Path(__file__).resolve().parents[1], stdout=stdout, stderr=stderr, creationflags=flags)
    return {
        "ok": True,
        "run_id": run_id,
        "pid": proc.pid,
        "command": cmd,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def _run_is_active(run_id: str) -> bool:
    script = f"""
$items = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object {{ $_.CommandLine -like '*{run_id}*' -and $_.CommandLine -like '*run_experiment_bundle.py*' }}
if ($items) {{ 'true' }} else {{ 'false' }}
"""
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    return result.stdout.strip().lower() == "true"


def _start_watcher(runs_dir: Path) -> None:
    thread = threading.Thread(target=_watch_runs, args=(runs_dir,), name="run-stall-watcher", daemon=True)
    thread.start()


def _watch_runs(runs_dir: Path) -> None:
    notified: set[tuple[str, str]] = set()
    while True:
        try:
            for run in list_runs(runs_dir):
                run_id = str(run.get("run_id") or "")
                status = str(run.get("status") or "")
                if status not in {"completed", "failed", "stopped", "stalled"}:
                    continue
                key = (run_id, status)
                if key in notified:
                    continue
                notified.add(key)
                _notify_status(runs_dir, run_id, status, run)
        except Exception:
            pass
        time.sleep(60)


def _notify_status(runs_dir: Path, run_id: str, status: str, payload: dict[str, Any]) -> None:
    event = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_id": run_id, "status": status, "payload": payload}
    append_jsonl(runs_dir / "dashboard_notifications.jsonl", event)
    webhook = os.environ.get("VANDERPOL_NOTIFY_WEBHOOK")
    if not webhook:
        return
    body = json.dumps(event).encode("utf-8")
    try:
        req = request.Request(webhook, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def _send_json(handler: BaseHTTPRequestHandler, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
    body = json.dumps(_json_safe(payload), ensure_ascii=False, allow_nan=False).encode("utf-8")
    _send_bytes(handler, body, "application/json; charset=utf-8", status=status)


def _send_bytes(
    handler: BaseHTTPRequestHandler,
    payload: bytes,
    content_type: str,
    status: HTTPStatus = HTTPStatus.OK,
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(payload)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
        return None
    return value


if __name__ == "__main__":
    main()
