"""Read-only dashboard data helpers for experiment run directories."""

from __future__ import annotations

import csv
import mimetypes
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .progress import (
    SCHEMA_VERSION,
    classify_snapshot,
    fold_events,
    load_json,
    load_jsonl,
)
from .stage8 import friendly_step_name, load_bundle_config


RUN_LABELS_FILE = "run_labels.json"
PAPER_COMPENDIUM_FILE = "docs/paper_all_data.md"
FINAL_RESULT_FILE = "docs/final_result.md"
FINAL_RESULT_JSON_FILE = "docs/final_result.json"
DEFAULT_AI_MODEL_RUN_IDS = (
    "v001_full_pipeline",
    "v002_existing_rhythm_realism_tuning",
    "v003_existing_rhythm_realism_tuning_pass2",
    "v004_existing_rhythm_realism_mitdb_cudb",
)
ARTIFACT_SUFFIXES = {".json", ".jsonl", ".csv", ".md", ".png", ".jpg", ".jpeg", ".html", ".log", ".txt"}
REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def list_runs(runs_dir: str | Path = "outputs/runs") -> list[dict[str, Any]]:
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        return []
    labels = _load_run_labels(runs_dir)
    rows = []
    for run_dir in sorted(
        [path for path in runs_dir.iterdir() if path.is_dir() and not path.name.startswith("_")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        progress = _load_run_progress_summary(run_dir)
        artifact_summary = _summarize_run_artifacts(run_dir)
        rows.append(
            {
                "run_id": run_dir.name,
                "display_name": _run_display_name(run_dir, progress, labels),
                "run_dir": str(run_dir),
                "status": progress.get("classification") or progress.get("run_status") or progress.get("status"),
                "current_step": progress.get("current_step"),
                "progress_fraction": progress.get("progress_fraction", 0.0),
                "display_progress_fraction": progress.get("display_progress_fraction", progress.get("progress_fraction", 0.0)),
                "heartbeat_at": progress.get("heartbeat_at") or progress.get("updated_at"),
                "updated_at": progress.get("updated_at") or progress.get("created_at_utc"),
                "artifact_count": artifact_summary["count"],
                "categories": artifact_summary["categories"],
            }
        )
    return rows


def load_run_progress(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    snapshot = load_json(run_dir / "current_progress.json")
    if snapshot is None:
        snapshot = load_json(run_dir / "run_progress.json")
    if snapshot is None:
        events = load_jsonl(run_dir / "events.jsonl")
        snapshot = fold_events(events, run_id=run_dir.name, run_dir=run_dir) if events else {}
    snapshot.setdefault("schema_version", SCHEMA_VERSION)
    snapshot.setdefault("run_id", run_dir.name)
    snapshot.setdefault("run_dir", str(run_dir))
    snapshot["display_name"] = _run_display_name(run_dir, snapshot)
    snapshot["step_labels"] = {
        name: friendly_step_name(str(name))
        for name in snapshot.get("step_order", [])
    }
    if snapshot.get("current_step"):
        snapshot["current_step_label"] = snapshot.get("current_step_label") or friendly_step_name(str(snapshot["current_step"]))
    for step in snapshot.get("steps", []):
        if isinstance(step, dict) and step.get("name"):
            step["display_name"] = step.get("display_name") or friendly_step_name(str(step["name"]))
    snapshot["classification"] = classify_snapshot(snapshot)
    _attach_latest_detail(snapshot, run_dir)
    _attach_progress_estimates(snapshot, run_dir)
    return snapshot


def _load_run_progress_summary(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    snapshot = load_json(run_dir / "current_progress.json")
    if snapshot is None:
        snapshot = load_json(run_dir / "run_progress.json")
    if snapshot is None:
        snapshot = load_json(run_dir / "run_manifest.json")
    if snapshot is None:
        snapshot = {}
    snapshot.setdefault("schema_version", SCHEMA_VERSION)
    snapshot.setdefault("run_id", run_dir.name)
    snapshot.setdefault("run_dir", str(run_dir))
    snapshot["display_name"] = _run_display_name(run_dir, snapshot)
    if snapshot.get("current_step"):
        snapshot["current_step_label"] = snapshot.get("current_step_label") or friendly_step_name(str(snapshot["current_step"]))
    snapshot["classification"] = classify_snapshot(snapshot)
    snapshot["display_progress_fraction"] = snapshot.get("display_progress_fraction", snapshot.get("progress_fraction", 0.0))
    return snapshot


def load_run_events(run_dir: str | Path, tail: int = 200) -> list[dict[str, Any]]:
    return load_jsonl(Path(run_dir) / "events.jsonl", tail=tail)


def load_run_metrics(run_dir: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(Path(run_dir) / "metrics.jsonl")


def load_run_artifacts(run_dir: str | Path) -> list[dict[str, Any]]:
    run_dir = Path(run_dir)
    artifacts = load_jsonl(run_dir / "artifacts.jsonl")
    deduped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for artifact in artifacts:
        item = _enrich_artifact(artifact, run_dir)
        deduped[(item.get("resolved_path"), item.get("status"))] = item
    enriched = list(deduped.values())
    seen = {artifact.get("resolved_path") for artifact in enriched}
    for path in _discover_artifacts(run_dir):
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        enriched.append(
            _enrich_artifact(
                {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_dir.name,
                    "step": _infer_step_for_artifact(run_dir, path),
                    "path": str(path),
                    "kind": path.suffix.lower().lstrip(".") or "file",
                    "status": "partial" if ".partial." in path.name else "final",
                    "size_bytes": path.stat().st_size if path.is_file() else None,
                    "created_at": None,
                },
                run_dir,
            )
        )
    return sorted(
        enriched,
        key=lambda item: (
            str(item.get("step", "")),
            str(item.get("status", "")) != "final",
            str(item.get("kind", "")),
            str(item.get("relative_path", "")),
        ),
    )


def load_failure(run_dir: str | Path) -> dict[str, Any] | None:
    return load_json(Path(run_dir) / "failure_summary.json")


def load_run_diagnostics(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    progress = load_run_progress(run_dir)
    run_id = str(progress.get("run_id") or run_dir.name)
    diagnostics = _process_diagnostics(run_id)
    diagnostics["heartbeat_age_s"] = _age_seconds(progress.get("heartbeat_at") or progress.get("updated_at"))
    diagnostics["current_step_elapsed_s"] = progress.get("current_step_elapsed_s")
    diagnostics["n_jobs"] = (progress.get("config") or {}).get("n_jobs")
    return diagnostics


def load_run_storage(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    progress = load_run_progress(run_dir)
    artifacts = load_run_artifacts(run_dir)
    important_files = [
        "run_manifest.json",
        "run_progress.json",
        "current_progress.json",
        "events.jsonl",
        "metrics.jsonl",
        "artifacts.jsonl",
        "failure_summary.json",
    ]
    files = []
    for name in important_files:
        path = run_dir / name
        files.append(
            {
                "name": name,
                "path": str(path),
                "relative_path": name,
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        grouped.setdefault(str(artifact.get("category") or "Other"), []).append(artifact)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": progress.get("run_id") or run_dir.name,
        "display_name": progress.get("display_name") or run_dir.name,
        "run_dir": str(run_dir),
        "status": progress.get("classification"),
        "current_step": progress.get("current_step"),
        "artifact_count": len(artifacts),
        "categories": _artifact_category_counts(artifacts),
        "important_files": files,
        "artifacts_by_category": grouped,
    }


def load_paper_compendium(path: str | Path = PAPER_COMPENDIUM_FILE) -> dict[str, Any]:
    path = _resolve_repo_path(path)
    if not path.exists() or not path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "exists": False,
            "path": str(path),
            "title": "Paper Data Compendium",
            "run_id": None,
            "source_dir": None,
            "sections": [],
            "markdown": "",
            "size_bytes": None,
            "modified_at": None,
        }

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    stat = path.stat()
    return {
        "schema_version": SCHEMA_VERSION,
        "exists": True,
        "path": str(path),
        "title": _paper_compendium_title(text),
        "run_id": _paper_compendium_value(text, "Run ID:"),
        "source_dir": _paper_compendium_value(text, "Source directory:"),
        "sections": _paper_compendium_sections(text),
        "markdown": text,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def load_final_result(
    markdown_path: str | Path = FINAL_RESULT_FILE,
    json_path: str | Path = FINAL_RESULT_JSON_FILE,
) -> dict[str, Any]:
    markdown_path = _resolve_repo_path(markdown_path)
    json_path = _resolve_repo_path(json_path)
    if not markdown_path.exists() or not markdown_path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "exists": False,
            "path": str(markdown_path),
            "json_path": str(json_path),
            "title": "Consolidated Final Result",
            "markdown": "",
            "payload": {},
            "size_bytes": None,
            "modified_at": None,
        }
    text = markdown_path.read_text(encoding="utf-8-sig", errors="replace")
    stat = markdown_path.stat()
    payload = load_json(json_path) or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "exists": True,
        "path": str(markdown_path),
        "json_path": str(json_path),
        "title": _paper_compendium_title(text),
        "markdown": text,
        "payload": payload,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def load_ai_model_run_results(
    runs_dir: str | Path = "outputs/versioned_runs",
    run_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    runs_dir = Path(runs_dir)
    selected_run_ids = list(run_ids or DEFAULT_AI_MODEL_RUN_IDS)
    runs = [_ai_model_run_summary(runs_dir / run_id) for run_id in selected_run_ids]
    available_runs = [run for run in runs if run.get("exists")]
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "Versioned Run Results Across 4 Runs",
        "source_dir": str(runs_dir),
        "requested_run_ids": selected_run_ids,
        "run_count": len(available_runs),
        "completed_run_count": sum(1 for run in available_runs if run.get("status") in {"completed", "ok"}),
        "runs": runs,
        "aggregate": _ai_model_aggregate(available_runs),
        "realism_aggregate": _realism_aggregate(available_runs),
        "scenario_consensus": _ai_model_scenario_consensus(available_runs),
        "conclusion": _versioned_run_conclusion(available_runs),
    }


def tail_text(path: str | Path, max_lines: int = 200) -> str:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-max_lines:])


def compare_runs(run_ids: list[str], runs_dir: str | Path = "outputs/runs") -> dict[str, Any]:
    runs_dir = Path(runs_dir)
    rows = []
    for run_id in run_ids:
        run_dir = runs_dir / run_id
        progress = load_run_progress(run_dir)
        manifest = load_json(run_dir / "run_manifest.json") or {}
        rows.append(
            {
                "run_id": run_id,
                "display_name": _run_display_name(run_dir, progress),
                "status": progress.get("classification"),
                "progress_fraction": progress.get("progress_fraction"),
                "display_progress_fraction": progress.get("display_progress_fraction"),
                "current_step": progress.get("current_step"),
                "duration_s": manifest.get("duration_s"),
                "config": manifest.get("config", {}),
                "provenance": manifest.get("provenance", {}),
                "key_metrics": _latest_key_metrics(run_dir),
            }
        )
    return {"schema_version": SCHEMA_VERSION, "runs": rows}


def dry_run_estimate(config_path: str | Path) -> dict[str, Any]:
    config = load_bundle_config(config_path)
    patients = int(config.get("patients_per_scenario", 1))
    scenarios = 5
    algorithms = 5
    profiles = len(config.get("noise_profiles", []))
    fallback_profiles = profiles
    if config.get("real_noise_stats"):
        fallback_profiles += 1
    if config.get("category_noise_stats"):
        # Category count may vary by file; n10 currently contains six categories in local runs.
        fallback_profiles += 6
    fallback_configs = (
        len(config.get("fallback_min_sqi", []))
        * len(config.get("fallback_entropy", []))
        * len(config.get("fallback_rr_cv", []))
    )
    patient_blocks = patients * scenarios
    return {
        "schema_version": SCHEMA_VERSION,
        "config_path": str(config_path),
        "patients_per_scenario": patients,
        "n_jobs": config.get("n_jobs", 1),
        "rough_units": {
            "patient_blocks_per_matrix": patient_blocks,
            "episode_rows_per_matrix": patient_blocks * algorithms,
            "noise_profiles": profiles,
            "fallback_profiles": fallback_profiles,
            "fallback_configs": fallback_configs,
        },
        "note": "Rough unit count only; duration estimate becomes reliable after more event history exists.",
    }


def render_dashboard_html() -> str:
    return """<!doctype html>
<html lang="en" dir="ltr" data-color-theme="Blue_Theme" class="light selected" data-layout="vertical" data-boxed-layout="boxed" data-card="shadow" data-sidebartype="full">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vanderpol Runs</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/tailadmin-assets/fonts/icons/tabler-icons/tabler-icons.css">
  <link rel="stylesheet" href="/tailadmin-assets/css/theme.css">
  <style>
    body { min-height: 100vh; }
    .dashboard-main { background: var(--color-lightgray); min-height: calc(100vh - 73px); }
    button.sidebar-link { background: transparent; border: 0; cursor: pointer; text-align: left; }
    #sidebarnav .sidebar-item .sidebar-link.active { background: var(--color-lightprimary); color: var(--color-primary); }
    #sidebarnav .sidebar-item .sidebar-link.active i { color: var(--color-primary); }
    .panel { display: none; }
    .panel.active { display: block; }
    .workflow { display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 8px; margin-bottom: 1rem; }
    .workflowStep { border: 1px solid var(--color-border); background: var(--color-white); border-radius: var(--radius-md); padding: 10px 12px; font-size: 12px; color: var(--color-bodytext); }
    .workflowStep.ready { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-lightprimary); }
    .workflowStep b { display: block; color: var(--color-dark); font-size: 13px; margin-bottom: 2px; }
    .ta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem; }
    .ux-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
    .ux-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-white); padding: 14px; }
    .ux-card h6 { font-weight: 700; margin: 0 0 8px; color: var(--color-dark); }
    .ux-card ul { margin: 8px 0 0 18px; padding: 0; }
    .ux-card li { margin: 3px 0; }
    .ux-split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 420px); gap: 1rem; align-items: start; }
    .guardrail { border-left: 4px solid var(--color-warning); background: var(--color-lightwarning); border-radius: var(--radius-md); padding: 12px 14px; color: var(--color-warning); margin-bottom: 1rem; }
    .miniTable td:first-child { color: var(--color-bodytext); width: 38%; }
    .ta-progress { height: 10px; background: var(--color-bordergray); border-radius: 999px; overflow: hidden; }
    .fill { height: 100%; background: var(--color-primary); width: 0; transition: width .35s ease; }
    .fill.alt { background: var(--color-success); }
    .run { display: block; width: 100%; text-align: left; border: 1px solid var(--color-border); background: var(--color-white); border-radius: var(--radius-md); padding: 10px 12px; margin-bottom: 8px; cursor: pointer; color: var(--color-link); }
    .run:hover, .run.active { background: var(--color-lightprimary); color: var(--color-primary); border-color: transparent; }
    .runSelectorGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
    .runSelectorGrid .run { margin-bottom: 0; min-height: 112px; }
    .runGroup { margin-bottom: 1.25rem; }
    .runGroupHeader { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin: 0 0 10px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border); }
    .runGroupHeader h6 { margin: 0; font-weight: 700; color: var(--color-dark); }
    .runGroupHeader p { margin: 2px 0 0; }
    .runGroupCount { white-space: nowrap; }
    .runMiniProgress { height: 4px; border-radius: 999px; background: var(--color-bordergray); overflow: hidden; margin-top: 8px; }
    .runMiniFill { height: 100%; background: var(--color-primary); }
    .runPath { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .storageGrid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(260px, .8fr); gap: 1rem; }
    .resultStack { display: grid; gap: 1rem; }
    .resultGrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
    .resultBlock { border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-white); padding: 14px; overflow: hidden; }
    .resultBlock h6 { font-weight: 700; margin: 0 0 10px; color: var(--color-dark); }
    .figureGrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
    .inlineFigure { border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-white); overflow: hidden; }
    .inlineFigure img { width: 100%; aspect-ratio: 16 / 10; object-fit: contain; background: var(--color-lightgray); border-bottom: 1px solid var(--color-border); }
    .inlineFigure .caption { padding: 10px 12px; display: block; }
    .muted { color: var(--color-bodytext); font-size: 12px; }
    .banner { display: none; border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 1rem; }
    .banner.bad { display: block; color: var(--color-error); background: var(--color-lighterror); }
    .banner.warn { display: block; color: var(--color-warning); background: var(--color-lightwarning); }
    .form-control.slim { padding-block: 8px; }
    textarea { width: 100%; min-height: 280px; font-family: Consolas, ui-monospace, monospace; font-size: 12px; }
    pre { background: #111c2d; color: #e5edf7; border-radius: var(--radius-md); padding: 12px; overflow: auto; max-height: 320px; font-family: Consolas, ui-monospace, monospace; font-size: 12px; }
    canvas { width: 100%; height: 240px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-white); }
    .actions, .filterbar, .inputRow { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
    .inputRow input { min-width: 0; flex: 1; }
    .btn-danger { background: var(--color-error); color: var(--color-white); border-radius: var(--radius-md); padding: 8px 16px; font-weight: 500; }
    .plain { border: 1px solid var(--color-primary); border-radius: var(--radius-md); color: var(--color-primary); display: inline-block; padding: 8px 12px; text-decoration: none; }
    .plain:hover { background: var(--color-primary); color: var(--color-white); }
    .viewer { min-height: 320px; border: 1px solid var(--color-border); border-radius: var(--radius-md); overflow: auto; background: var(--color-white); padding: 16px; }
    .viewer img { max-width: 100%; height: auto; }
    .viewer iframe { width: 100%; min-height: 560px; border: 0; }
    .artifactSummary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin: 8px 0 18px; }
    .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin: 8px 0 18px; }
    .thumb { cursor: pointer; }
    .thumb img { width: 100%; aspect-ratio: 16 / 10; object-fit: contain; background: var(--color-lightgray); border-bottom: 1px solid var(--color-border); }
    .stepGroup { border: 1px solid var(--color-border); border-radius: var(--radius-md); margin: 10px 0; overflow: hidden; background: var(--color-white); }
    .stepHeader { display: flex; justify-content: space-between; gap: 10px; background: var(--color-lightgray); padding: 12px 14px; border-bottom: 1px solid var(--color-border); cursor: pointer; }
    .stepBody { padding: 0 14px 14px; }
    .badge { display: inline-block; border-radius: 999px; padding: 3px 9px; font-size: 12px; background: var(--color-lightprimary); color: var(--color-primary); margin-right: 4px; }
    .previewHead { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
    .previewMeta { color: var(--color-bodytext); font-size: 12px; }
    .csvWrap { overflow: auto; max-height: 580px; border: 1px solid var(--color-border); border-radius: var(--radius-md); }
    .csvWrap table { min-width: 100%; font-size: 12px; white-space: nowrap; }
    .csvWrap th { position: sticky; top: 0; background: var(--color-lightgray); z-index: 1; }
    .decisionTable { overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); }
    .decisionTable table { min-width: 760px; font-size: 13px; }
    .decisionTable th { background: var(--color-lightgray); }
    .decisionTable td strong { color: var(--color-dark); }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--color-border); padding: 10px 8px; text-align: left; vertical-align: top; }
    .jsonTree details { margin-left: 12px; }
    .jsonTree summary { cursor: pointer; }
    .mdPreview { line-height: 1.5; max-width: 920px; }
    .mdBullet { margin: 6px 0; }
    .paperMeta code { white-space: normal; word-break: break-word; }
    .paperSections { max-height: 260px; }
    .missing { color: var(--color-error); }
    @media (max-width: 1299px) { .page-wrapper { margin-left: 0; } }
    @media (max-width: 980px) { .workflow { grid-template-columns: repeat(2, minmax(0, 1fr)); } .ux-split, .storageGrid { grid-template-columns: 1fr; } }
    @media (max-width: 768px) { .container { padding-inline: 16px; } .filterbar input { min-width: 100%; } .workflow { grid-template-columns: 1fr; } }
  </style>
</head>
<body class="DEFAULT_THEME bg-white dark:bg-dark">
<main>
  <div id="main-wrapper" class="flex">
    <aside id="application-sidebar-brand" class="hs-overlay hs-overlay-open:translate-x-0 -translate-x-full xl:rtl:-translate-x-0 rtl:translate-x-full left-0 rtl:left-auto rtl:right-0 transform hidden xl:block xl:translate-x-0 xl:end-auto xl:bottom-0 fixed top-0 with-vertical left-sidebar transition-all duration-300 h-screen z-20 flex-shrink-0 border-r rtl:border-l rtl:border-r-0 w-[270px] border-border dark:border-darkborder bg-white dark:bg-dark">
      <div class="py-5 px-5 flex justify-between">
        <div class="brand-logo flex items-center justify-center">
          <a href="/" class="text-nowrap logo-img flex items-center gap-3">
            <span class="inline-flex h-9 w-9 items-center justify-center rounded-full bg-lightprimary text-primary font-semibold">V</span>
            <span class="hide-menu text-lg font-semibold text-dark">Vanderpol</span>
          </a>
        </div>
      </div>
      <div class="scroll-sidebar" data-simplebar="">
        <div class="px-6 mt-8 mini-layout" data-te-sidenav-menu-ref>
          <nav id="tabs" class="hs-accordion-group w-full flex flex-col">
            <ul data-te-sidenav-menu-ref id="sidebarnav">
              <div class="caption"><i class="ti ti-dots nav-small-cap-icon"></i><span class="hide-menu">Run Workflow</span></div>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link active activemenu" data-tab="runs"><i class="ti ti-folders text-xl shrink-0"></i><span class="hide-menu shrink-0">Runs</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="intermediate"><i class="ti ti-chart-dots text-xl shrink-0"></i><span class="hide-menu shrink-0">Intermediate Results</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="paper"><i class="ti ti-notebook text-xl shrink-0"></i><span class="hide-menu shrink-0">Paper Data</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="final"><i class="ti ti-presentation-analytics text-xl shrink-0"></i><span class="hide-menu shrink-0">Final Results</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="method"><i class="ti ti-adjustments text-xl shrink-0"></i><span class="hide-menu shrink-0">Run Settings</span></button></li>
              <div class="caption mt-8"><i class="ti ti-dots nav-small-cap-icon"></i><span class="hide-menu">Support</span></div>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="system"><i class="ti ti-tool text-xl shrink-0"></i><span class="hide-menu shrink-0">System</span></button></li>
            </ul>
          </nav>
        </div>
      </div>
    </aside>
    <div class="page-wrapper w-full" role="main">
      <header class="sticky top-header top-0 inset-x-0 z-10 flex flex-wrap md:justify-start md:flex-nowrap text-sm bg-white dark:bg-dark">
        <div class="with-vertical w-full">
          <div class="w-full mx-auto px-4 lg:py-4 py-3 lg:px-4" aria-label="Global">
            <div class="relative md:flex md:items-center md:justify-between">
              <div class="flex justify-between items-center w-full">
                <div class="flex items-center gap-3">
                  <div class="relative xl:hidden">
                    <a class="text-2xl icon-hover cursor-pointer text-link dark:text-darklink sidebartoggler h-10 w-10 hover:text-primary light-dark-hoverbg flex justify-center items-center rounded-full" data-hs-overlay="#application-sidebar-brand" aria-controls="application-sidebar-brand" aria-label="Toggle navigation">
                      <i class="ti ti-menu-2"></i>
                    </a>
                  </div>
                  <form class="relative hidden lg:flex">
                    <input type="text" class="form-control ps-10" placeholder="Search runs or artifacts">
                    <i class="ti ti-search absolute inset-y-0 flex items-center text-lg ms-3"></i>
                  </form>
                </div>
                <div class="icon-nav items-center gap-2 flex">
                  <span id="clock" class="badge-md bg-lightprimary rounded-full text-primary"></span>
                  <button id="refresh" class="btn">Refresh</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>
      <main class="dashboard-main max-w-full pt-6">
        <div class="container full-container py-5">
          <div class="relative bg-lightsecondary rounded-lg p-6 mb-6 overflow-hidden">
            <h5 class="text-lg font-semibold">Experiment Dashboard</h5>
            <p id="title" class="text-link/80 dark:text-white/80 mt-1">Select a run</p>
          </div>
          <div id="alert" class="banner"></div>

          <div id="workflowSteps" class="workflow"></div>

          <div class="panel active dashboard-panel" id="panel-runs">
            <div class="card mb-4"><div class="card-body">
              <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
                <div>
                  <h5 class="card-title mb-1">Run Selector</h5>
                  <p class="text-sm text-bodytext">Current run context</p>
                </div>
              </div>
              <div id="runs" class="runSelectorGrid"></div>
            </div></div>
            <div class="card mb-4"><div class="card-body">
              <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
                <div>
                  <h5 class="card-title mb-1">Consolidated Final Result</h5>
                  <p class="text-sm text-bodytext">Manuscript-facing result from completed paper-ready runs</p>
                </div>
                <button class="btn" id="reloadDashboardFinalResult">Reload Final Result</button>
              </div>
              <div id="dashboardFinalResult"><span class="muted">Loading consolidated final result...</span></div>
            </div></div>
            <div class="card mb-4"><div class="card-body">
              <h5 class="card-title mb-4">Run Storage</h5>
              <div id="runStorage"></div>
            </div></div>
            <div class="card mb-4"><div class="card-body">
              <h5 class="card-title mb-4">Intermediate / Final Results</h5>
              <div id="keyResults"><span class="muted">Select a run.</span></div>
            </div></div>
            <div class="ux-split">
              <div class="card"><div class="card-body">
                <h5 class="card-title mb-4">Run Snapshot</h5>
                <div class="ta-grid" id="stats"></div>
                <h5 class="card-title mt-6 mb-3">Step Progress</h5>
                <div class="ta-progress"><div class="fill" id="progressFill"></div></div>
                <p id="progressText" class="text-sm text-bodytext mt-2"></p>
                <h5 class="card-title mt-5 mb-3">Live Estimate</h5>
                <div class="ta-progress"><div class="fill alt" id="displayProgressFill"></div></div>
                <p id="activityText" class="text-sm text-bodytext mt-2"></p>
              </div></div>
              <div class="card"><div class="card-body">
                <h5 class="card-title mb-4">Current Stage</h5>
                <div id="stageGuide"><span class="muted">Select a run.</span></div>
              </div></div>
            </div>
          </div>

          <div class="panel card dashboard-panel" id="panel-data">
            <div class="card-body">
              <h5 class="card-title mb-4">Data</h5>
              <div class="guardrail">Research simulator only. External ECG is used for observation realism, validation, and noise stress testing, not direct treatment-outcome labels.</div>
              <div class="ux-grid">
                <div class="ux-card"><h6>Synthetic Scenarios</h6><ul><li><code>nsr</code></li><li><code>svt_flutter</code></li><li><code>monomorphic_vt</code></li><li><code>polymorphic_vt</code></li><li><code>vf_like</code></li></ul></div>
                <div class="ux-card"><h6>External ECG Role</h6><ul><li>MIT-BIH: morphology validation</li><li>CUDB: VT/VF waveform validation</li><li>Challenge 2015: noisy alarm-like ECG robustness</li><li>PTB-XL: future encoder pretraining</li></ul></div>
                <div class="ux-card"><h6>Calibration Sources</h6><ul><li>AHA ACLS tachyarrhythmia/shockable rhythm anchors</li><li>ICD/ATP VT literature anchors</li><li>Resonant-drift simulation references</li><li>Safety default for normal rhythm withhold</li></ul></div>
                <div class="ux-card"><h6>Feature Window</h6><ul><li>4-second ECG observation</li><li>heart rate, RR variability, QRS proxy</li><li>dominant frequency and entropy</li><li>signal quality estimate</li></ul></div>
              </div>
            </div>
          </div>

          <div class="panel card dashboard-panel" id="panel-method">
            <div class="card-body">
              <h5 class="card-title mb-4">Run Settings</h5>
              <div class="ux-grid mb-4" id="methodGroups"></div>
              <h5 class="card-title mt-6 mb-3">Dry Run Estimate</h5>
              <div class="inputRow"><input id="configPath" class="form-control slim" value="configs/bundle_smoke.json"><button id="estimate" class="btn btn-md">Estimate</button></div>
              <pre id="estimateOut" class="mt-4">{}</pre>
              <h5 class="card-title mt-6 mb-3">Draft Config</h5>
              <textarea id="configEditor" class="form-control">{}</textarea>
              <div class="actions mt-4"><button class="btn-outline-primary" id="loadCurrentConfig">Load Current Run Config</button><button class="btn" id="dryRunEdited">Estimate Edited Config</button></div>
              <pre id="editedEstimate" class="mt-4">{}</pre>
            </div>
          </div>

          <div class="panel card dashboard-panel" id="panel-analysis"><div class="card-body"><h5 class="card-title mb-4">Analysis Run</h5><div id="steps"></div><h5 class="card-title mt-6 mb-4">Deep Progress</h5><pre id="detail">{}</pre><h5 class="card-title mt-6 mb-4">Recent Events</h5><pre id="events"></pre><h5 class="card-title mt-6 mb-4">Failure Triage</h5><pre id="failure"></pre><h5 class="card-title mt-6 mb-4">Safe Controls</h5><p class="text-bodytext mb-4">Pause means safe stop at the next checkpoint. It does not suspend process memory.</p><div class="actions"><button class="btn-danger" id="stopRun">Request Safe Stop</button><button class="btn" id="resumeRun">Resume Selected Run</button></div><h5 class="card-title mt-6 mb-4">Start New Run</h5><div class="inputRow"><input id="newRunId" class="form-control slim" placeholder="new_run_id"><button class="btn" id="startRun">Start From Settings</button></div><pre id="controlOut" class="mt-4">{}</pre></div></div>
          <div class="panel card dashboard-panel" id="panel-intermediate"><div class="card-body"><h5 class="card-title mb-4">Intermediate Results</h5><div id="intermediateReview" class="ux-grid"></div></div></div>
          <div class="panel card dashboard-panel" id="panel-paper"><div class="card-body"><div class="flex flex-wrap items-start justify-between gap-3 mb-4"><div><h5 class="card-title mb-1">Consolidated Final Result</h5><p class="text-sm text-bodytext">Consolidated conclusion from completed paper-ready runs, followed by the manuscript data compendium.</p></div><button class="btn" id="reloadPaperCompendium">Reload</button></div><div class="guardrail">Paper data is generated from simulator artifacts. Keep the clinical guardrails visible when moving this into a draft.</div><div id="finalResult"><span class="muted">Open this tab to load the consolidated final result.</span></div><h5 class="card-title mt-6 mb-4">Paper Data Compendium</h5><div id="paperCompendium"><span class="muted">Open this tab to load the paper data compendium.</span></div></div></div>
          <div class="panel card dashboard-panel" id="panel-final"><div class="card-body"><div class="flex flex-wrap items-start justify-between gap-3 mb-4"><div><h5 class="card-title mb-1">Final Results</h5><p class="text-sm text-bodytext">Versioned run evidence first, selected-run details second.</p></div><button class="btn" id="reloadAiModelRuns">Reload Versioned Runs</button></div><div class="guardrail">This page summarizes simulator evidence only. Do not interpret it as clinical efficacy.</div><div id="aiModelRuns"><span class="muted">Open this tab to load versioned run results.</span></div><h5 class="card-title mt-6 mb-4">Selected Run Results</h5><div id="finalResults"></div></div></div>
          <div class="panel card dashboard-panel" id="panel-system"><div class="card-body"><h5 class="card-title mb-4">System</h5><h5 class="card-title mb-4">Run Storage</h5><div id="runStorageSystem" class="mb-6"></div><h5 class="card-title mt-6 mb-4">All Outputs</h5><div id="artifactSummary" class="artifactSummary"></div><div class="filterbar mb-4"><select id="artifactCategoryFilter"><option value="">All categories</option></select><select id="artifactStepFilter"><option value="">All steps</option></select><select id="artifactKindFilter"><option value="">All kinds</option></select><select id="artifactStatusFilter"><option value="">All status</option><option value="final">Final</option><option value="partial">Partial</option></select><input id="artifactSearch" class="form-control slim" placeholder="Search filename or path"></div><h5 class="card-title mt-6 mb-4">Image Gallery</h5><div id="imageGallery" class="gallery"></div><h5 class="card-title mt-6 mb-4">All Outputs By Step</h5><div id="artifacts"></div><h5 class="card-title mt-6 mb-4">Preview</h5><div id="artifactPreview" class="viewer"><span class="muted">Select an artifact preview button.</span></div><h5 class="card-title mt-6 mb-4">Live Scalar Metrics</h5><canvas id="chart" width="900" height="260"></canvas><h5 class="card-title mt-6 mb-4">Resource Diagnostics</h5><pre id="diagnostics">{}</pre><h5 class="card-title mt-6 mb-4">Provenance</h5><pre id="provenance">{}</pre></div></div>
        </div>
      </main>
    </div>
  </div>
</main>
<script>
let currentRun = null;
let activeTab = initialTab();
let latestProgress = null;
let latestArtifacts = [];
let latestRuns = [];
let latestPaperCompendium = null;
let latestFinalResult = null;
let latestAiModelRuns = null;
let lastArtifactRenderKey = '';
let lastImportantRenderKey = '';
const SCENARIO_LABELS = {
  nsr: 'Normal sinus rhythm',
  svt_flutter: 'SVT / flutter-like rhythm',
  monomorphic_vt: 'Monomorphic VT',
  polymorphic_vt: 'Polymorphic VT',
  vf_like: 'VF-like rhythm'
};
const ACTION_LABELS = {
  synchronized_cardioversion: 'Synchronized cardioversion',
  unsynchronized_defibrillation: 'Unsynchronized defibrillation',
  atp_burst_pacing: 'ATP burst pacing',
  resonant_drift_pacing: 'Resonant drift pacing',
  adaptive_low_energy_pacing: 'Adaptive low-energy pacing'
};
const STEP_LABELS = {
  phase2_figures: 'stage2 - run별 중간 성능 그림을 만드는 단계',
  calibration_report: 'stage3 - 데이터 생성 기준을 검증하는 단계',
  selector_report: 'stage5 - 파형 특징으로 치료 선택 정책을 학습하는 단계',
  decision_boundary: 'stage5 - 치료 선택 경계를 확인하는 단계',
  bootstrap_ci: 'stage5 - 최종 정답률의 불확실성을 계산하는 단계',
  selector_stability: 'stage5 - 치료 선택 정책의 안정성을 확인하는 단계',
  noise_ood_sweep: 'stage6 - 노이즈가 들어온 파형에서 치료 선택을 점검하는 단계',
  fallback_threshold_sweep: 'stage7 - 낮은 품질 파형의 보수 판단 기준을 찾는 단계',
  paper_artifacts: 'stage9 - 중간 결과와 최종 결과를 화면에 정리하는 단계'
};
async function getJSON(url) { const res = await fetch(url); if (!res.ok) throw new Error(url + ' ' + res.status); return await res.json(); }
async function postJSON(url, payload) {
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload || {})});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || (url + ' ' + res.status));
  return data;
}
function pct(v) { return ((Number(v || 0) * 100).toFixed(1)) + '%'; }
function esc(v) { return String(v ?? '').replace(/[&<>]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[s])); }
function attr(v) { return esc(v).replace(/"/g, '&quot;'); }
function showUiError(err) {
  const alert = document.getElementById('alert');
  if (!alert) return;
  alert.className = 'banner bad';
  alert.textContent = `UI error: ${err?.message || err}`;
}
function fmtSeconds(v) {
  const n = Number(v || 0);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n < 90) return n.toFixed(0) + 's';
  if (n < 7200) return (n / 60).toFixed(1) + 'm';
  return (n / 3600).toFixed(1) + 'h';
}
function fmtMetric(v, digits=3) {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : '';
}
function stepLabel(name) {
  return STEP_LABELS[name] || name || '';
}
function initialTab() {
  const raw = new URLSearchParams(window.location.search).get('tab') || window.location.hash.replace(/^#/, '') || 'runs';
  return ['runs', 'method', 'intermediate', 'paper', 'final', 'system'].includes(raw) ? raw : 'runs';
}
function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll('#tabs button').forEach(b => {
    const selected = b.dataset.tab === tab;
    b.classList.toggle('active', selected);
    b.classList.toggle('activemenu', selected);
  });
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tab}`));
  if (tab === 'system' && currentRun) renderArtifacts(currentRun, true);
  refresh().catch(showUiError);
}
async function loadRuns() {
  const data = await getJSON('/api/runs');
  latestRuns = data;
  if (currentRun && !data.some(r => r.run_id === currentRun)) currentRun = null;
  if (!currentRun && data[0]) currentRun = preferredInitialRun(data).run_id;
  const root = document.getElementById('runs');
  root.innerHTML = runGroupsHTML(data);
  root.querySelectorAll('.run').forEach(b => b.onclick = () => { currentRun = b.dataset.run; lastArtifactRenderKey = ''; lastImportantRenderKey = ''; refresh(); });
}
function runGroupsHTML(data) {
  const groups = [
    ['paper', 'Paper-ready runs', 'Final result and manuscript artifacts are present.'],
    ['active', 'Active or stalled runs', 'Runs that are still running, stale, or need attention.'],
    ['completed', 'Completed runs', 'Finished runs without a paper artifact bundle.'],
    ['stopped', 'Failed or stopped runs', 'Runs that ended before normal completion.'],
    ['other', 'Other folders and logs', 'Utility folders or runs without progress metadata.']
  ];
  const grouped = Object.fromEntries(groups.map(([key]) => [key, []]));
  (data || []).forEach(run => grouped[runGroupKey(run)].push(run));
  return groups
    .filter(([key]) => grouped[key].length)
    .map(([key, title, description]) => {
      const rows = grouped[key];
      return `<section class="runGroup" data-run-group="${attr(key)}"><div class="runGroupHeader"><div><h6>${esc(title)}</h6><p class="muted">${esc(description)}</p></div><span class="badge runGroupCount">${rows.length} runs</span></div><div class="runSelectorGrid">${rows.map(runCardHTML).join('')}</div></section>`;
    })
    .join('') || '<p class="muted">No runs found.</p>';
}
function runGroupKey(run) {
  const status = String(run.status || 'unknown').toLowerCase();
  const categories = run.categories || {};
  if (categories['Final Results']) return 'paper';
  if (['running', 'stale', 'stalled'].includes(status)) return 'active';
  if (status === 'completed') return 'completed';
  if (['failed', 'stopped'].includes(status)) return 'stopped';
  return 'other';
}
function runCardHTML(r) {
  const statusLine = [r.status || 'unknown', stepLabel(r.current_step) || ''].filter(Boolean).join(' - ');
  const cats = Object.entries(r.categories || {}).map(([k,v]) => `${k}:${v}`).join(' ');
  return `<button class="run ${r.run_id===currentRun?'active':''}" data-run="${esc(r.run_id)}"><b>${esc(r.display_name || r.run_id)}</b><br><span class="muted">id: ${esc(r.run_id)}</span><span class="muted runPath">${esc(r.run_dir || '')}</span><span class="muted">${esc(statusLine)}</span><br><span class="muted">${Number(r.artifact_count || 0)} outputs ${esc(cats)}</span><div class="runMiniProgress" aria-label="run progress"><div class="runMiniFill" style="width:${pct(r.display_progress_fraction || r.progress_fraction)}"></div></div></button>`;
}
function preferredInitialRun(data) {
  return data.find(r => (r.categories || {})['Final Results'] && r.status === 'completed')
    || data.find(r => (r.categories || {})['Final Results'])
    || data.find(r => r.status && r.status !== 'unknown')
    || data[0];
}
function selectedRunMeta() {
  return latestRuns.find(r => r.run_id === currentRun) || {};
}
function statsHTML(p) {
  const progress = Number(p.progress_fraction || 0);
  const elapsed = Number(p.duration_s || 0);
  const eta = Number(p.estimated_remaining_s || 0);
  const nJobs = p.config ? p.config.n_jobs : '';
  const visuals = [
    ['bg-lightprimary', 'text-primary'],
    ['bg-lightwarning', 'text-warning'],
    ['bg-lightinfo', 'text-info'],
    ['bg-lighterror', 'text-error'],
    ['bg-lightsuccess', 'text-success'],
    ['bg-lightinfo', 'text-info']
  ];
  return [
    ['Status', p.classification || p.run_status || p.status],
    ['Current Step', p.current_step_label || stepLabel(p.current_step) || ''],
    ['Step Progress', pct(p.progress_fraction)],
    ['Live Estimate', pct(p.display_progress_fraction)],
    ['N Jobs', nJobs || ''],
    ['Elapsed', fmtSeconds(elapsed)],
    ['ETA', fmtSeconds(eta) || ''],
    ['Step Elapsed', fmtSeconds(p.current_step_elapsed_s) || ''],
    ['Heartbeat Age', fmtSeconds(p.heartbeat_age_s) || '']
  ].map(([k,v], i) => {
    const [bg, text] = visuals[i % visuals.length];
    return `<div class="card mb-0 shadow-none ${bg} w-full"><div class="card-body"><p class="font-semibold ${text} mb-1">${esc(k)}</p><h5 class="text-lg font-semibold ${text} mb-0">${esc(v)}</h5></div></div>`;
  }).join('');
}
function stepsHTML(steps, order) {
  const rows = steps || [];
  const byName = Object.fromEntries(rows.map(s => [s.name, s]));
  const names = order && order.length ? order : rows.map(s => s.name);
  if (!names.length) return '<p class="muted">No steps yet.</p>';
  return `<table><thead><tr><th>Step</th><th>Status</th><th>Duration</th><th>Message</th></tr></thead><tbody>${names.map(name => {
    const s = byName[name] || {name, status: 'pending', duration_s: '', message: ''};
    const duration = Number.isFinite(Number(s.duration_s)) && s.duration_s !== '' ? Number(s.duration_s).toFixed(1) : '';
    return `<tr><td>${esc(s.display_name || stepLabel(s.name))}<br><span class="muted">${esc(s.name)}</span></td><td>${esc(s.status)}</td><td>${esc(duration)}</td><td>${esc(s.message||'')}</td></tr>`;
  }).join('')}</tbody></table>`;
}
function workflowHTML(p, artifacts) {
  const names = new Set((artifacts || []).map(a => a.name || ''));
  const hasIntermediate = names.has('intermediate_results.html') || names.has('intermediate_waveforms.svg') || names.has('phase2_matrix_summary.csv');
  const hasFinal = names.has('final_results.html') || names.has('final_visual_summary.svg');
  const steps = [
    ['Run Settings', Boolean(p?.config), 'parameters'],
    ['Intermediate Results', hasIntermediate, 'waveforms and generated data'],
    ['Final Results', hasFinal, 'accuracy and feature weights']
  ];
  return steps.map(([label, ready, meta]) => `<div class="workflowStep ${ready ? 'ready' : ''}"><b>${esc(label)}</b>${esc(meta)}</div>`).join('');
}
function methodGroupsHTML(config) {
  const c = config || {};
  const group = (title, rows) => `<div class="ux-card"><h6>${esc(title)}</h6><table class="miniTable"><tbody>${rows.map(([k,v]) => `<tr><td>${esc(k)}</td><td>${esc(Array.isArray(v) ? v.join(', ') : (v ?? ''))}</td></tr>`).join('')}</tbody></table></div>`;
  return [
    group('Scale', [['patients', c.patients_per_scenario], ['horizon_s', c.horizon_s], ['n_jobs', c.n_jobs]]),
    group('Selector', [['train_fraction', c.train_fraction], ['selector_seed', c.selector_seed], ['stability_seeds', c.selector_stability_seeds]]),
    group('Uncertainty', [['bootstrap_samples', c.bootstrap_samples], ['decision_grid_size', c.decision_grid_size]]),
    group('Noise / Fallback', [['noise_profiles', c.noise_profiles], ['fallback_min_sqi', c.fallback_min_sqi], ['fallback_entropy', c.fallback_entropy], ['fallback_rr_cv', c.fallback_rr_cv]]),
    group('Reward / Calibration', [['reward_weights', c.reward_weights ? JSON.stringify(c.reward_weights) : 'default'], ['calibration_config', c.calibration_config]])
  ].join('');
}
function runStorageHTML(storage) {
  if (!storage || !storage.run_id) return '<p class="muted">Select a run to inspect its storage.</p>';
  const important = (storage.important_files || []).map(f => {
    const state = f.exists ? formatBytes(f.size_bytes) : 'missing';
    return `<tr><td>${esc(f.name)}</td><td><span class="${f.exists ? '' : 'missing'}">${esc(state)}</span></td><td><span class="muted runPath">${esc(f.path || '')}</span></td></tr>`;
  }).join('');
  const categories = Object.entries(storage.categories || {}).map(([k,v]) => `<span class="badge">${esc(k)} ${esc(v)}</span>`).join('') || '<span class="muted">No outputs.</span>';
  return `<div class="storageGrid">
    <div class="ux-card"><h6>${esc(storage.display_name || storage.run_id)}</h6><table class="miniTable"><tbody><tr><td>Run ID</td><td>${esc(storage.run_id)}</td></tr><tr><td>Status</td><td>${esc(storage.status || '')}</td></tr><tr><td>Folder</td><td><span class="runPath">${esc(storage.run_dir || '')}</span></td></tr><tr><td>Outputs</td><td>${Number(storage.artifact_count || 0)}</td></tr></tbody></table><p class="mt-3">${categories}</p></div>
    <div class="ux-card"><h6>Run Data Files</h6><table class="miniTable"><tbody>${important}</tbody></table></div>
  </div>`;
}
function artifactByName(items, name, preferPaper=false) {
  const matches = (items || []).filter(a => a.name === name);
  if (!matches.length) return null;
  if (preferPaper) return matches.find(a => (a.relative_path || '').startsWith('paper_artifacts')) || matches[0];
  return matches.find(a => !(a.relative_path || '').includes('.partial.')) || matches[0];
}
function artifactPill(run, artifact, label) {
  if (!artifact) return '<span class="badge missing">missing</span>';
  const url = artifactUrl(run, artifact);
  return `<a class="plain" target="_blank" href="${attr(url)}">${esc(label || artifact.name)}</a>`;
}
function reviewCardHTML(run, title, names, question, params=[]) {
  const found = names.map(name => artifactByName(latestArtifacts, name)).filter(Boolean);
  const links = names.map(name => artifactPill(run, artifactByName(latestArtifacts, name), name)).join(' ');
  return `<div class="ux-card"><h6>${esc(title)}</h6><p class="muted">${esc(question)}</p><p>${links}</p>${params.length ? `<p>${params.map(p => `<span class="badge">${esc(p)}</span>`).join('')}</p>` : ''}<p class="muted">${found.length}/${names.length} expected artifacts found.</p></div>`;
}
function intermediateReviewHTML(run) {
  return [
    reviewCardHTML(run, 'Representative Waveforms', ['intermediate_waveforms.svg','intermediate_results.html'], 'Approximate waveform preview for each generated rhythm scenario.', ['waveform_preview_seed','observation_s']),
    reviewCardHTML(run, 'Data Generation', ['calibration_report.json','phase2_matrix_summary.csv'], 'How the synthetic run data was sampled, simulated, calibrated, and summarized.', ['patients_per_scenario','horizon_s','calibration_config']),
    reviewCardHTML(run, 'Intermediate Figures', ['phase2_mean_reward.png','phase2_success_rate.png','phase2_mean_time_s.png'], 'Per-scenario intermediate images before final policy checks.', ['reward_weights'])
  ].join('');
}
async function textArtifact(run, name, preferPaper=false) {
  const artifact = artifactByName(latestArtifacts, name, preferPaper);
  if (!artifact) return '';
  return await (await fetch(artifactUrl(run, artifact))).text();
}
async function finalResultsHTML(run) {
  const selectorText = await textArtifact(run, 'selector_report.json').catch(() => '');
  const winners = artifactByName(latestArtifacts, 'paper_algorithm_winners.csv', true) || artifactByName(latestArtifacts, 'phase2_matrix_summary.csv');
  let headline = '<p class="muted">selector_report.json is not available yet.</p>';
  if (selectorText) {
    try {
      const policies = JSON.parse(selectorText).policy_summary || {};
      const rows = ['acls_rule','oracle'].filter(k => policies[k]).map(k => {
        const m = policies[k];
        return `<tr><td>${esc(k)}</td><td>${Number(m.mean_reward).toFixed(3)}</td><td>${Number(m.oracle_gap).toFixed(3)}</td><td>${Number(m.success_rate).toFixed(3)}</td><td>${Number(m.mean_safety_violations).toFixed(3)}</td></tr>`;
      }).join('');
      headline = `<table><thead><tr><th>Policy</th><th>Reward</th><th>Oracle Gap</th><th>Success</th><th>Safety</th></tr></thead><tbody>${rows}</tbody></table>`;
    } catch {}
  }
  return `<div class="ux-grid"><div class="ux-card"><h6>Policy Baselines</h6>${headline}</div><div class="ux-card"><h6>Symptom-Level Final Decision</h6>${artifactPill(run, winners, winners?.name || 'winner table')} ${artifactPill(run, artifactByName(latestArtifacts, 'final_results.html', true), 'final_results.html')}<p class="muted mt-3">Estimated treatment success from the scenario-by-algorithm matrix.</p></div><div class="ux-card"><h6>Waveform Analysis Weights</h6>${artifactPill(run, artifactByName(latestArtifacts, 'waveform_analysis_weights.svg', true), 'weights image')} ${artifactPill(run, artifactByName(latestArtifacts, 'decision_boundary.png'), 'decision boundary')}<p class="muted mt-3">Shows which extracted waveform features influence treatment selection.</p></div><div class="ux-card"><h6>Robustness And Confidence</h6>${artifactPill(run, artifactByName(latestArtifacts, 'noise_ood_sweep.csv'), 'noise check')} ${artifactPill(run, artifactByName(latestArtifacts, 'bootstrap_matrix_ci.csv'), 'uncertainty')} ${artifactPill(run, artifactByName(latestArtifacts, 'selector_stability.json'), 'stability')}<p class="muted mt-3">Claims stay bounded to simulator evidence.</p></div></div>`;
}
async function loadAiModelRuns(force=false) {
  if (latestAiModelRuns && !force) return latestAiModelRuns;
  latestAiModelRuns = await getJSON('/api/ai-model-runs');
  return latestAiModelRuns;
}
async function renderAiModelRuns(force=false) {
  const root = document.getElementById('aiModelRuns');
  if (!root) return;
  root.innerHTML = '<span class="muted">Loading AI model results across four runs...</span>';
  root.innerHTML = aiModelRunsHTML(await loadAiModelRuns(force));
}
function aiModelRunsHTML(data) {
  if (!data || !data.runs) {
    return '<div class="resultBlock"><h6>Versioned Run Results Across 4 Runs</h6><p class="muted">No versioned run payload is available.</p></div>';
  }
  const runs = data.runs || [];
  const aggregate = data.aggregate || {};
  const realismAggregate = data.realism_aggregate || {};
  const conclusion = data.conclusion || {};
  const selectorAvg = aggregate.selector_model_average || {};
  const requested = data.requested_run_ids || [];
  const attention = aggregate.selector_model_attention_runs || [];
  const cards = [
    ['Versioned runs', `${data.run_count || 0}/${requested.length || runs.length}`],
    ['Completed', data.completed_run_count || 0],
    ['Selector runs', aggregate.selector_model_run_count || 0],
    ['Selector success', fmtMetric(selectorAvg.success_rate)],
    ['Realism runs', realismAggregate.realism_run_count || 0],
    ['Mean SMD / KS', `${fmtMetric(realismAggregate.mean_smd_abs)} / ${fmtMetric(realismAggregate.mean_ks_statistic)}`],
    ['Worst mismatch', realismAggregate.worst_run_id ? `${realismAggregate.worst_run_id}: ${realismAggregate.worst_feature}` : 'none'],
    ['Attention runs', attention.length ? attention.join(', ') : 'none']
  ].map(([k,v], i) => {
    const styles = [['bg-lightprimary','text-primary'],['bg-lightsuccess','text-success'],['bg-lightinfo','text-info'],['bg-lightwarning','text-warning'],['bg-lighterror','text-error'],['bg-lightinfo','text-info']];
    const [bg, text] = styles[i % styles.length];
    return `<div class="card mb-0 shadow-none ${bg} w-full"><div class="card-body"><p class="font-semibold ${text} mb-1">${esc(k)}</p><h5 class="text-lg font-semibold ${text} mb-0">${esc(v)}</h5></div></div>`;
  }).join('');
  const runRows = runs.map(run => {
    if (!run.exists) return `<tr class="missing"><td><code>${esc(run.run_id)}</code></td><td colspan="12">missing run directory</td></tr>`;
    const cfg = run.config || {};
    const selector = run.selector_model || {};
    const acls = run.acls_rule || {};
    const oracle = run.oracle || {};
    const realism = run.realism_comparison || {};
    return `<tr><td><code>${esc(run.run_id)}</code><br><span class="muted">${esc(run.status || '')}</span></td><td>${esc(run.experiment || cfg.preset || '')}</td><td>${esc(cfg.patients_per_scenario || '')}</td><td>${esc(cfg.horizon_s || '')}</td><td>${fmtMetric(selector.mean_reward)}</td><td>${fmtMetric(selector.oracle_gap)}</td><td>${fmtMetric(selector.success_rate)}</td><td>${fmtMetric(acls.mean_reward)}</td><td>${fmtMetric(oracle.mean_reward)}</td><td>${fmtMetric(realism.mean_smd_abs)}</td><td>${fmtMetric(realism.mean_ks_statistic)}</td><td>${esc(realism.max_smd_feature || '')}</td><td>${aiModelArtifactLinks(run)}</td></tr>`;
  }).join('');
  const scenarioRows = (data.scenario_consensus || []).map(row => {
    const perRun = (row.per_run || []).map(item => `${item.run_id}: ${item.algorithm}`).join(' | ');
    return `<tr><td>${esc(SCENARIO_LABELS[row.scenario] || row.scenario)}</td><td><code>${esc(row.consensus_algorithm || '')}</code></td><td>${esc(row.agreement || '')}</td><td>${fmtMetric(row.mean_reward)}</td><td>${fmtMetric(row.success_rate)}</td><td><span class="muted">${esc(perRun)}</span></td></tr>`;
  }).join('');
  return `<div class="resultStack">
    ${versionedConclusionHTML(conclusion)}
    <div class="ta-grid">${cards}</div>
    <div class="resultBlock"><h6>Versioned Run Summary</h6><div class="csvWrap"><table><thead><tr><th>Run</th><th>Experiment</th><th>Patients</th><th>Horizon / obs</th><th>Selector reward</th><th>Selector gap</th><th>Selector success</th><th>ACLS reward</th><th>Oracle reward</th><th>Mean SMD</th><th>Mean KS</th><th>Worst feature</th><th>Artifacts</th></tr></thead><tbody>${runRows}</tbody></table></div></div>
    <div class="resultBlock"><h6>Scenario Winners From Selector Runs</h6><div class="csvWrap"><table><thead><tr><th>Scenario</th><th>Consensus action</th><th>Agreement</th><th>Avg reward</th><th>Avg success</th><th>Per-run action</th></tr></thead><tbody>${scenarioRows || '<tr><td colspan="6"><span class="muted">No selector winner tables are present in these versioned runs.</span></td></tr>'}</tbody></table></div></div>
    <div class="resultGrid">${runs.filter(run => run.exists).map(aiModelRunDetailHTML).join('')}</div>
  </div>`;
}
function versionedConclusionHTML(conclusion) {
  if (!conclusion || !conclusion.headline) return '';
  const selector = conclusion.selector_evidence || {};
  const realism = conclusion.realism_evidence || {};
  const selectorRunIds = conclusion.selector_run_ids || (conclusion.selector_run_id ? [conclusion.selector_run_id] : []);
  const selectorRunLabel = selectorRunIds.join(', ');
  const selectorBeatCount = selector.selector_beats_acls_count == null || selector.selector_comparable_run_count == null ? '' : `${selector.selector_beats_acls_count} / ${selector.selector_comparable_run_count}`;
  const list = items => (items || []).map(item => `<p class="mdBullet"><span class="muted">- </span>${esc(item)}</p>`).join('');
  return `<div class="resultBlock"><h6>AI Model Analysis Conclusion</h6><p><b>${esc(conclusion.headline)}</b></p>
    <div class="resultGrid">
      <div><h6>Selector Evidence</h6><table class="miniTable"><tbody><tr><td>Selector runs</td><td><code>${esc(selectorRunLabel)}</code></td></tr><tr><td>Runs beating ACLS</td><td>${esc(selectorBeatCount)}</td></tr><tr><td>Selector reward avg</td><td>${fmtMetric(selector.selector_reward)}</td></tr><tr><td>ACLS reward avg</td><td>${fmtMetric(selector.acls_reward)}</td></tr><tr><td>Reward delta vs ACLS</td><td>${fmtMetric(selector.reward_delta_vs_acls)}</td></tr><tr><td>Selector success avg</td><td>${fmtMetric(selector.selector_success_rate)}</td></tr><tr><td>ACLS success avg</td><td>${fmtMetric(selector.acls_success_rate)}</td></tr><tr><td>Selector oracle gap avg</td><td>${fmtMetric(selector.selector_oracle_gap)}</td></tr><tr><td>Oracle reward avg</td><td>${fmtMetric(selector.oracle_reward)}</td></tr></tbody></table></div>
      <div><h6>Realism Evidence</h6><table class="miniTable"><tbody><tr><td>Latest realism run</td><td><code>${esc(realism.latest_run_id || '')}</code></td></tr><tr><td>Mean SMD change</td><td>${fmtMetric(realism.mean_smd_abs_change)}</td></tr><tr><td>Mean KS change</td><td>${fmtMetric(realism.mean_ks_statistic_change)}</td></tr><tr><td>Latest worst feature</td><td>${esc(realism.latest_worst_group || '')} / ${esc(realism.latest_worst_feature || '')}</td></tr><tr><td>Latest worst SMD</td><td>${fmtMetric(realism.latest_worst_smd_abs)}</td></tr><tr><td>Rows</td><td>${esc(realism.latest_real_rows || '')} real / ${esc(realism.latest_synthetic_rows || '')} synthetic</td></tr></tbody></table></div>
    </div>
    <div class="resultGrid mt-3"><div><h6>Claims To Use</h6>${list(conclusion.claims)}</div><div><h6>Limits</h6>${list(conclusion.limitations)}</div><div><h6>Next Analysis</h6>${list(conclusion.next_steps)}</div></div></div>`;
}
function aiModelArtifactLinks(run) {
  return [
    ['selector_report', 'selector'],
    ['algorithm_winners', 'winners'],
    ['algorithm_matrix', 'matrix'],
    ['feature_weights', 'weights'],
    ['success_heatmap', 'heatmap'],
    ['distance_table', 'distance'],
    ['smd_heatmap', 'smd'],
    ['ks_heatmap', 'ks'],
    ['pca_plot', 'pca'],
    ['interpretation', 'notes']
  ].map(([key, label]) => aiModelArtifactLink(run, key, label)).join(' ');
}
function aiModelArtifactLink(run, key, label) {
  const artifact = (run.artifacts || {})[key];
  if (!artifact || !artifact.exists) return `<span class="badge missing">${esc(label)} missing</span>`;
  const url = `/api/artifact?run=${encodeURIComponent(run.run_id)}&path=${encodeURIComponent(artifact.path)}`;
  return `<a class="plain" target="_blank" href="${attr(url)}">${esc(label)}</a>`;
}
function aiModelRunDetailHTML(run) {
  const winners = (run.scenario_winners || []).map(row => `<tr><td>${esc(SCENARIO_LABELS[row.scenario] || row.scenario)}</td><td><code>${esc(row.best_algorithm || row.final_action || '')}</code></td><td>${fmtMetric(row.mean_reward)}</td><td>${fmtMetric(row.success_rate)}</td><td>${fmtMetric(row.mean_safety_violations)}</td></tr>`).join('');
  const selector = run.selector_model || {};
  const realism = run.realism_comparison || {};
  const stability = run.selector_stability || {};
  const rewardStability = stability.mean_reward || {};
  const winnerTable = winners ? `<div class="csvWrap mt-3"><table><thead><tr><th>Scenario</th><th>Winner</th><th>Reward</th><th>Success</th><th>Safety</th></tr></thead><tbody>${winners}</tbody></table></div>` : '<p class="muted mt-3">No selector winner table in this versioned run.</p>';
  const realismRows = realism.distance_rows ? `<table class="miniTable mt-3"><tbody><tr><td>Real rows</td><td>${esc(realism.n_real_rows || '')}</td></tr><tr><td>Synthetic rows</td><td>${esc(realism.n_synthetic_rows || '')}</td></tr><tr><td>Mean SMD</td><td>${fmtMetric(realism.mean_smd_abs)}</td></tr><tr><td>Mean KS</td><td>${fmtMetric(realism.mean_ks_statistic)}</td></tr><tr><td>Worst SMD</td><td>${fmtMetric(realism.max_smd_abs)} ${esc(realism.max_smd_group || '')} / ${esc(realism.max_smd_feature || '')}</td></tr></tbody></table>` : '';
  return `<div class="resultBlock"><h6>${esc(run.run_id)}</h6><table class="miniTable"><tbody><tr><td>Experiment</td><td>${esc(run.experiment || '')}</td></tr><tr><td>Selector reward</td><td>${fmtMetric(selector.mean_reward)}</td></tr><tr><td>Selector gap</td><td>${fmtMetric(selector.oracle_gap)}</td></tr><tr><td>Selector success</td><td>${fmtMetric(selector.success_rate)}</td></tr><tr><td>Stability reward</td><td>${rewardStability.mean !== undefined ? `${fmtMetric(rewardStability.mean)} +/- ${fmtMetric(rewardStability.std)}` : ''}</td></tr></tbody></table>${realismRows}<div class="actions mt-3">${aiModelArtifactLinks(run)}</div>${winnerTable}</div>`;
}
function paperResultHTML(run) {
  const paperItems = latestArtifacts.filter(a => (a.relative_path || '').startsWith('paper_artifacts'));
  if (!paperItems.length) return '<p class="muted">No final result folder found for this run yet.</p>';
  const preferred = ['intermediate_results.html','intermediate_waveforms.svg','final_results.html','final_visual_summary.png','final_visual_summary.svg','waveform_analysis_weights.svg','policy_comparison.png','policy_comparison.svg','treatment_success_heatmap.png','treatment_success_heatmap.svg','visual_report.html'];
  return `<div class="ux-grid">${preferred.map(name => `<div class="ux-card"><h6>${esc(name)}</h6>${artifactPill(run, artifactByName(paperItems, name, true), name)}</div>`).join('')}</div>`;
}
async function loadPaperCompendium(force=false) {
  if (latestPaperCompendium && !force) return latestPaperCompendium;
  latestPaperCompendium = await getJSON('/api/paper-compendium');
  return latestPaperCompendium;
}
async function loadFinalResult(force=false) {
  if (latestFinalResult && !force) return latestFinalResult;
  latestFinalResult = await getJSON('/api/final-result');
  return latestFinalResult;
}
async function renderDashboardFinalResult(force=false) {
  const root = document.getElementById('dashboardFinalResult');
  if (!root) return;
  if (!latestFinalResult || force) root.innerHTML = '<span class="muted">Loading consolidated final result...</span>';
  root.innerHTML = finalResultSummaryHTML(await loadFinalResult(force));
}
async function renderPaperCompendium(force=false) {
  const finalRoot = document.getElementById('finalResult');
  const compendiumRoot = document.getElementById('paperCompendium');
  if (finalRoot) finalRoot.innerHTML = '<span class="muted">Loading consolidated final result...</span>';
  if (compendiumRoot) compendiumRoot.innerHTML = '<span class="muted">Loading paper data compendium...</span>';
  const [finalResult, compendium] = await Promise.all([loadFinalResult(force), loadPaperCompendium(force)]);
  if (finalRoot) finalRoot.innerHTML = finalResultHTML(finalResult);
  if (compendiumRoot) compendiumRoot.innerHTML = paperCompendiumHTML(compendium);
}
function finalResultSummaryHTML(data) {
  if (!data || !data.exists) {
    return `<div class="resultBlock"><h6>Consolidated Final Result</h6><p class="missing">docs/final_result.md is not available.</p><p class="muted">${esc(data?.path || '')}</p></div>`;
  }
  const payload = data.payload || {};
  const primary = payload.primary_run || {};
  const policies = primary.policy_metrics || {};
  const oracle = policies.oracle || {};
  const acls = policies.acls_rule || {};
  const calibration = primary.calibration || {};
  const winners = primary.scenario_winners || [];
  const cards = [
    ['Primary run', primary.run_id || ''],
    ['Runs considered', `${payload.run_count || 0}`],
    ['Completed runs', `${payload.completed_run_count || 0}`],
    ['Oracle reward', fmtMetric(oracle.mean_reward)],
    ['ACLS reward', fmtMetric(acls.mean_reward)],
    ['Calibration pass', calibration.checks ? `${calibration.passed || 0}/${calibration.checks}` : '']
  ].map(([k,v], i) => {
    const styles = [['bg-lightprimary','text-primary'],['bg-lightsuccess','text-success'],['bg-lightinfo','text-info'],['bg-lightwarning','text-warning'],['bg-lighterror','text-error'],['bg-lightinfo','text-info']];
    const [bg, text] = styles[i % styles.length];
    return `<div class="card mb-0 shadow-none ${bg} w-full"><div class="card-body"><p class="font-semibold ${text} mb-1">${esc(k)}</p><h5 class="text-lg font-semibold ${text} mb-0">${esc(v)}</h5></div></div>`;
  }).join('');
  const winnerRows = winners.map(row => `<tr><td>${esc(SCENARIO_LABELS[row.scenario] || row.scenario || '')}</td><td><code>${esc(row.best_algorithm || row.final_action || '')}</code></td><td>${fmtMetric(row.mean_reward)}</td><td>${fmtMetric(row.success_rate)}</td><td>${fmtMetric(row.mean_time_s)}</td><td>${fmtMetric(row.mean_safety_violations)}</td></tr>`).join('');
  return `<div class="resultStack">
    <div class="ta-grid">${cards}</div>
    <div class="resultBlock"><div class="previewHead"><div><b>Scenario-Level Final Actions</b><br><span class="previewMeta">${esc(data.modified_at || '')}</span></div><div class="actions"><a class="plain" target="_blank" href="/api/final-result/raw">Open Markdown</a><a class="plain" href="?tab=paper">Paper Data</a></div></div><div class="csvWrap"><table><thead><tr><th>Scenario</th><th>Final action</th><th>Reward</th><th>Success</th><th>Time</th><th>Safety</th></tr></thead><tbody>${winnerRows}</tbody></table></div></div>
  </div>`;
}
function finalResultHTML(data) {
  if (!data || !data.exists) {
    return `<div class="resultBlock"><h6>Consolidated Final Result</h6><p class="missing">docs/final_result.md is not available.</p><p class="muted">${esc(data?.path || '')}</p></div>`;
  }
  const payload = data.payload || {};
  const primary = payload.primary_run || {};
  return `<div class="resultStack">
    <div class="resultGrid">
      <div class="resultBlock paperMeta"><h6>${esc(data.title || 'Consolidated Final Result')}</h6><table class="miniTable"><tbody><tr><td>Primary run</td><td><code>${esc(primary.run_id || '')}</code></td></tr><tr><td>Runs considered</td><td>${esc(payload.run_count || '')}</td></tr><tr><td>Completed runs</td><td>${esc(payload.completed_run_count || '')}</td></tr><tr><td>Patients/scenario</td><td>${esc(primary.patients_per_scenario || '')}</td></tr><tr><td>Horizon</td><td>${esc(primary.horizon_s || '')} s</td></tr><tr><td>File</td><td><code>${esc(data.path || '')}</code></td></tr></tbody></table><div class="actions mt-3"><a class="plain" target="_blank" href="/api/final-result/raw">Open Markdown</a></div></div>
      <div class="resultBlock"><h6>Selection Rule</h6><p>${esc(payload.selection_rule || 'No selection rule recorded.')}</p><p class="muted">One-patient mutation runs are kept as checks, not as the manuscript primary result.</p></div>
    </div>
    <div class="resultBlock"><div class="previewHead"><div><b>Final Result Markdown</b><br><span class="previewMeta">${esc(data.modified_at || '')}</span></div><a class="plain" target="_blank" href="/api/final-result/raw">Open</a></div>${markdownPreviewHTML(data.markdown || '')}</div>
  </div>`;
}
function paperCompendiumHTML(data) {
  if (!data || !data.exists) {
    return `<div class="resultBlock"><h6>Paper Data Compendium</h6><p class="missing">docs/paper_all_data.md is not available.</p><p class="muted">${esc(data?.path || '')}</p></div>`;
  }
  const sections = data.sections || [];
  const sectionRows = sections.length
    ? `<div class="csvWrap paperSections"><table><thead><tr><th>Section</th><th>Source</th></tr></thead><tbody>${sections.map(section => `<tr><td>${esc(section.title)}</td><td><code>${esc(section.path)}</code></td></tr>`).join('')}</tbody></table></div>`
    : '<p class="muted">No section index was found in the compendium.</p>';
  return `<div class="resultStack">
    <div class="resultGrid">
      <div class="resultBlock paperMeta"><h6>${esc(data.title || 'Paper Data Compendium')}</h6><table class="miniTable"><tbody><tr><td>Run ID</td><td><code>${esc(data.run_id || '')}</code></td></tr><tr><td>Source</td><td><code>${esc(data.source_dir || '')}</code></td></tr><tr><td>File</td><td><code>${esc(data.path || '')}</code></td></tr><tr><td>Updated</td><td>${esc(data.modified_at || '')}</td></tr><tr><td>Size</td><td>${formatBytes(data.size_bytes)}</td></tr></tbody></table><div class="actions mt-3"><a class="plain" target="_blank" href="/api/paper-compendium/raw">Open Markdown</a></div></div>
      <div class="resultBlock"><h6>Included Sections</h6>${sectionRows}</div>
    </div>
    <div class="resultBlock"><div class="previewHead"><div><b>Compiled Manuscript Notes</b><br><span class="previewMeta">${esc(sections.length)} sections from the paper artifact set</span></div><a class="plain" target="_blank" href="/api/paper-compendium/raw">Open</a></div>${markdownPreviewHTML(data.markdown || '')}</div>
  </div>`;
}
function artifactLinkActions(run, artifact) {
  if (!artifact) return '';
  const url = artifactUrl(run, artifact);
  return `<div class="actions mt-3"><a class="plain" target="_blank" href="${attr(url)}">Open</a><button class="plain" data-preview="${attr(url)}" data-kind="${attr(artifact.kind)}" data-name="${attr(artifact.name || '')}" data-meta="${attr(artifact.relative_path || artifact.path)}">Preview</button></div>`;
}
async function artifactTextOrEmpty(run, artifact) {
  if (!artifact) return '';
  try {
    return await (await fetch(artifactUrl(run, artifact))).text();
  } catch {
    return '';
  }
}
function resultBlock(title, body, run, artifact) {
  const missing = artifact ? '' : '<p class="muted">Required artifact is not available yet.</p>';
  return `<div class="resultBlock"><h6>${esc(title)}</h6>${body || missing}${artifactLinkActions(run, artifact)}</div>`;
}
function figureResultsHTML(run) {
  const figures = [
    ['Reward Heatmap', artifactByName(latestArtifacts, 'phase2_mean_reward.png')],
    ['Success Rate', artifactByName(latestArtifacts, 'phase2_success_rate.png')],
    ['Decision Boundary', artifactByName(latestArtifacts, 'decision_boundary.png')],
    ['Mean Time', artifactByName(latestArtifacts, 'phase2_mean_time_s.png')],
    ['Safety Violations', artifactByName(latestArtifacts, 'phase2_mean_safety_violations.png')]
  ].filter(([, artifact]) => artifact);
  if (!figures.length) return '<p class="muted">No key figures available yet.</p>';
  return `<div class="figureGrid">${figures.map(([title, artifact]) => {
    const url = artifactUrl(run, artifact);
    return `<div class="inlineFigure"><img src="${url}" loading="lazy"><span class="caption"><b>${esc(title)}</b><br><span class="muted">${esc(artifact.relative_path || artifact.path)}</span></span>${artifactLinkActions(run, artifact)}</div>`;
  }).join('')}</div>`;
}
function tableArtifactHTML(artifact, text, maxRows=80) {
  if (!artifact || !text) return '';
  if (artifact.kind === 'csv') return csvPreviewHTML(text, maxRows);
  if (artifact.kind === 'md') return markdownPreviewHTML(text);
  if (artifact.kind === 'json') return jsonPreviewHTML(text);
  return `<pre>${esc(text.slice(0, 120000))}</pre>`;
}
async function importantResultsHTML(run) {
  const intermediateDoc = artifactByName(latestArtifacts, 'intermediate_results.html', true);
  const waveform = artifactByName(latestArtifacts, 'intermediate_waveforms.svg', true);
  const finalDoc = artifactByName(latestArtifacts, 'final_results.html', true) || artifactByName(latestArtifacts, 'visual_report.html', true);
  const weights = artifactByName(latestArtifacts, 'waveform_analysis_weights.svg', true);
  const heatmap = artifactByName(latestArtifacts, 'treatment_success_heatmap.svg', true) || artifactByName(latestArtifacts, 'treatment_success_heatmap.png', true);
  const winners = artifactByName(latestArtifacts, 'paper_algorithm_winners.csv', true) || artifactByName(latestArtifacts, 'phase2_matrix_summary.csv');
  const winnersText = await artifactTextOrEmpty(run, winners);
  return `<div class="resultStack">
    <div class="resultGrid">
      ${resultBlock('Intermediate Results', `${artifactPill(run, intermediateDoc, 'intermediate_results.html')} ${artifactPill(run, waveform, 'waveform image')}<p class="muted mt-3">Run data generation and representative waveform preview.</p>`, run, intermediateDoc || waveform)}
      ${resultBlock('Final Results', `${artifactPill(run, finalDoc, 'final_results.html')} ${artifactPill(run, weights, 'feature weights')} ${artifactPill(run, heatmap, 'success heatmap')}<p class="muted mt-3">Treatment matrix and waveform-analysis outputs.</p>`, run, finalDoc || weights || heatmap)}
    </div>
    <div class="resultBlock"><h6>Intermediate Figures</h6>${figureResultsHTML(run)}</div>
    <div class="resultGrid">
      ${resultBlock('Symptom-Level Treatment Result', winners ? tableArtifactHTML(winners, winnersText, 80) : '', run, winners)}
    </div>
  </div>`;
}
async function renderImportantResults(run, force=false) {
  const importantNames = new Set([
    'intermediate_results.html','intermediate_waveforms.svg','final_results.html','visual_report.html',
    'waveform_analysis_weights.svg','treatment_success_heatmap.svg','treatment_success_heatmap.png',
    'paper_algorithm_winners.csv','phase2_matrix_summary.csv','paper_noise_robustness_table.csv',
    'noise_ood_sweep.csv','paper_fallback_sweep_table.csv','fallback_threshold_sweep.csv',
    'phase2_mean_reward.png','phase2_success_rate.png','decision_boundary.png',
    'phase2_mean_time_s.png','phase2_mean_safety_violations.png'
  ]);
  const state = latestArtifacts
    .filter(a => importantNames.has(a.name))
    .map(a => `${a.name}:${a.resolved_path || a.path}:${a.size_bytes || ''}:${a.modified_at || ''}`)
    .join('|');
  const renderKey = `${run}|${state}`;
  if (!force && renderKey === lastImportantRenderKey) return;
  lastImportantRenderKey = renderKey;
  const html = await importantResultsHTML(run);
  document.getElementById('keyResults').innerHTML = html;
  const finalRoot = document.getElementById('finalResults');
  if (finalRoot && activeTab === 'final') {
    finalRoot.innerHTML = await finalResultsHTML(run);
  }
  bindPreviewButtons();
}
function formatBytes(value) {
  const n = Number(value || 0);
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / (1024 * 1024)).toFixed(1) + ' MB';
}
function artifactUrl(run, artifact) {
  return `/api/artifact?run=${encodeURIComponent(run)}&path=${encodeURIComponent(artifact.path)}`;
}
function filteredArtifacts(items) {
  const category = document.getElementById('artifactCategoryFilter')?.value || '';
  const step = document.getElementById('artifactStepFilter')?.value || '';
  const kind = document.getElementById('artifactKindFilter')?.value || '';
  const status = document.getElementById('artifactStatusFilter')?.value || '';
  const q = (document.getElementById('artifactSearch')?.value || '').toLowerCase();
  return items.filter(a => {
    const hay = `${a.name || ''} ${a.relative_path || ''} ${a.path || ''}`.toLowerCase();
    return (!category || a.category === category) && (!step || a.step === step) && (!kind || a.kind === kind) && (!status || a.status === status) && (!q || hay.includes(q));
  });
}
function populateArtifactFilters(items) {
  const categoryEl = document.getElementById('artifactCategoryFilter');
  const stepEl = document.getElementById('artifactStepFilter');
  const kindEl = document.getElementById('artifactKindFilter');
  const oldCategory = categoryEl.value;
  const oldStep = stepEl.value, oldKind = kindEl.value;
  const categories = [...new Set(items.map(a => a.category || 'Other'))].sort();
  const steps = [...new Set(items.map(a => a.step || 'unknown'))].sort();
  const kinds = [...new Set(items.map(a => a.kind || 'file'))].sort();
  categoryEl.innerHTML = '<option value="">All categories</option>' + categories.map(v => `<option value="${attr(v)}">${esc(v)}</option>`).join('');
  stepEl.innerHTML = '<option value="">All steps</option>' + steps.map(v => `<option value="${attr(v)}">${esc(stepLabel(v))}</option>`).join('');
  kindEl.innerHTML = '<option value="">All kinds</option>' + kinds.map(v => `<option value="${attr(v)}">${esc(v)}</option>`).join('');
  categoryEl.value = categories.includes(oldCategory) ? oldCategory : '';
  stepEl.value = steps.includes(oldStep) ? oldStep : '';
  kindEl.value = kinds.includes(oldKind) ? oldKind : '';
}
function artifactSummaryHTML(items) {
  const images = items.filter(a => ['png','jpg','jpeg'].includes(a.kind)).length;
  const tables = items.filter(a => a.kind === 'csv').length;
  const partial = items.filter(a => a.status === 'partial').length;
  const totalBytes = items.reduce((acc, a) => acc + Number(a.size_bytes || 0), 0);
  const visuals = [
    ['bg-lightprimary', 'text-primary', 'ti-files'],
    ['bg-lightinfo', 'text-info', 'ti-photo'],
    ['bg-lightsuccess', 'text-success', 'ti-table'],
    ['bg-lightwarning', 'text-warning', 'ti-progress'],
    ['bg-lighterror', 'text-error', 'ti-database']
  ];
  return [
    ['Files', items.length],
    ['Images', images],
    ['CSV Tables', tables],
    ['Partial', partial],
    ['Total Size', formatBytes(totalBytes)]
  ].map(([k,v], i) => {
    const [bg, text, icon] = visuals[i % visuals.length];
    return `<div class="card mb-0 shadow-none ${bg} w-full"><div class="card-body"><div class="flex items-center gap-3"><span class="rounded-full bg-white h-11 w-11 flex items-center justify-center ${text}"><i class="ti ${icon} text-xl"></i></span><div><p class="font-semibold ${text} mb-1">${esc(k)}</p><h5 class="text-lg font-semibold ${text} mb-0">${esc(v)}</h5></div></div></div></div>`;
  }).join('');
}
function imageGalleryHTML(items, run) {
  const images = items.filter(a => ['png','jpg','jpeg'].includes(a.kind));
  if (!images.length) return '<p class="muted">No images for this filter.</p>';
  return images.map(a => {
    const url = artifactUrl(run, a);
    return `<div class="thumb card" data-preview="${attr(url)}" data-kind="${attr(a.kind)}" data-name="${attr(a.name || '')}" data-meta="${attr(a.relative_path || a.path)}">
      <img src="${url}" loading="lazy">
      <div class="card-body"><h6 class="font-semibold mb-1">${esc(a.name || '')}</h6><span class="muted">${esc(stepLabel(a.step))} - ${formatBytes(a.size_bytes)}</span></div>
    </div>`;
  }).join('');
}
function artifactsHTML(items, run) {
  if (!items.length) return '<p class="muted">No artifacts yet.</p>';
  const groups = new Map();
  items.forEach(a => {
    const step = a.step || 'unknown';
    if (!groups.has(step)) groups.set(step, []);
    groups.get(step).push(a);
  });
  return [...groups.entries()].map(([step, rows]) => {
    const counts = [...new Set(rows.map(a => a.kind))].map(kind => `${kind}:${rows.filter(a => a.kind === kind).length}`).join(' ');
    const body = `<table><thead><tr><th>Name</th><th>Category</th><th>Kind</th><th>Status</th><th>Size</th><th>Updated</th><th>Action</th></tr></thead><tbody>${rows.map(a => {
      const url = artifactUrl(run, a);
      const missing = a.exists === false ? ' missing' : '';
      return `<tr class="${missing}"><td><a target="_blank" href="${attr(url)}">${esc(a.name || a.relative_path || a.path)}</a><br><span class="muted">${esc(a.relative_path || a.path)}</span></td><td>${esc(a.category || '')}</td><td>${esc(a.kind)}</td><td>${esc(a.status)}</td><td>${formatBytes(a.size_bytes)}</td><td>${esc(a.modified_at || a.created_at || '')}</td><td><button class="plain" data-preview="${attr(url)}" data-kind="${attr(a.kind)}" data-name="${attr(a.name || '')}" data-meta="${attr(a.relative_path || a.path)}">Preview</button></td></tr>`;
    }).join('')}</tbody></table>`;
    return `<div class="stepGroup"><div class="stepHeader"><b>${esc(stepLabel(step))}</b><span><span class="badge">${rows.length} files</span><span class="badge">${esc(counts)}</span></span></div><div class="stepBody">${body}</div></div>`;
  }).join('');
}
async function previewArtifact(url, kind, name='', meta='') {
  const root = document.getElementById('artifactPreview');
  root.innerHTML = '<span class="muted">Loading preview...</span>';
  const head = `<div class="previewHead"><div><b>${esc(name || 'Artifact')}</b><br><span class="previewMeta">${esc(meta || '')}</span></div><a class="plain" target="_blank" href="${url}">Open</a></div>`;
  if (['png','jpg','jpeg'].includes(kind)) {
    root.innerHTML = head + `<img src="${url}">`;
  } else if (kind === 'html') {
    root.innerHTML = head + `<iframe src="${url}"></iframe>`;
  } else {
    const text = await (await fetch(url)).text();
    if (kind === 'csv') root.innerHTML = head + csvPreviewHTML(text);
    else if (kind === 'json') root.innerHTML = head + jsonPreviewHTML(text);
    else if (kind === 'md') root.innerHTML = head + markdownPreviewHTML(text);
    else root.innerHTML = head + `<pre>${esc(text.slice(0, 120000))}</pre>`;
  }
}
function parseCSV(text, maxRows=200) {
  const rows = [];
  let row = [], cell = '', quote = false;
  for (let i = 0; i < text.length && rows.length < maxRows + 1; i++) {
    const ch = text[i], next = text[i+1];
    if (quote && ch === '"' && next === '"') { cell += '"'; i++; continue; }
    if (ch === '"') { quote = !quote; continue; }
    if (!quote && ch === ',') { row.push(cell); cell = ''; continue; }
    if (!quote && (ch === '\\n' || ch === '\\r')) {
      if (ch === '\\r' && next === '\\n') i++;
      row.push(cell); rows.push(row); row = []; cell = ''; continue;
    }
    cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
function csvPreviewHTML(text, maxRows=200) {
  const rows = parseCSV(text, maxRows);
  if (!rows.length) return '<p class="muted">Empty CSV.</p>';
  const headers = rows[0];
  const body = rows.slice(1);
  const allLines = text.split(/\\r?\\n/).filter(Boolean).length;
  const numeric = headers.map((h, idx) => {
    const vals = body.map(r => Number(r[idx])).filter(Number.isFinite);
    if (!vals.length) return null;
    const min = Math.min(...vals), max = Math.max(...vals), avg = vals.reduce((a,b)=>a+b,0)/vals.length;
    return `<span class="badge">${esc(h)} min ${min.toFixed(3)} avg ${avg.toFixed(3)} max ${max.toFixed(3)}</span>`;
  }).filter(Boolean).slice(0, 6).join(' ');
  return `<div class="previewMeta">${allLines} rows - ${headers.length} columns - showing first ${body.length} rows</div>${numeric ? `<p>${numeric}</p>` : ''}<div class="csvWrap"><table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${body.map(r => `<tr>${headers.map((_, i) => `<td>${esc(r[i] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function jsonPreviewHTML(text) {
  try {
    const data = JSON.parse(text);
    return `<div class="jsonTree">${jsonNode(data, 'root')}</div>`;
  } catch {
    return `<pre>${esc(text.slice(0, 120000))}</pre>`;
  }
}
function jsonNode(value, label) {
  if (value && typeof value === 'object') {
    const entries = Array.isArray(value) ? value.map((v,i)=>[i,v]) : Object.entries(value);
    const summary = `${esc(label)} ${Array.isArray(value) ? `[${entries.length}]` : `{${entries.length}}`}`;
    return `<details open><summary>${summary}</summary>${entries.slice(0, 200).map(([k,v]) => jsonNode(v, k)).join('')}${entries.length > 200 ? '<div class="muted">truncated</div>' : ''}</details>`;
  }
  return `<div><span class="muted">${esc(label)}:</span> ${esc(JSON.stringify(value))}</div>`;
}
function markdownPreviewHTML(text) {
  const lines = text.slice(0, 120000).split(/\\r?\\n/);
  const chunks = [];
  for (let i = 0; i < lines.length;) {
    if (isMarkdownTableAt(lines, i)) {
      const headers = splitMarkdownRow(lines[i]);
      i += 2;
      const body = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        body.push(splitMarkdownRow(lines[i]));
        i++;
      }
      chunks.push(`<div class="csvWrap"><table><thead><tr>${headers.map(h => `<th>${mdInline(h)}</th>`).join('')}</tr></thead><tbody>${body.map(row => `<tr>${headers.map((_, idx) => `<td>${mdInline(row[idx] || '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    const line = lines[i];
    if (!line.trim()) { chunks.push('<br>'); i++; continue; }
    if (line.startsWith('### ')) chunks.push(`<h3>${mdInline(line.slice(4))}</h3>`);
    else if (line.startsWith('## ')) chunks.push(`<h2>${mdInline(line.slice(3))}</h2>`);
    else if (line.startsWith('# ')) chunks.push(`<h2>${mdInline(line.slice(2))}</h2>`);
    else if (line.startsWith('- ')) chunks.push(`<p class="mdBullet"><span class="muted">- </span>${mdInline(line.slice(2))}</p>`);
    else chunks.push(`<p>${mdInline(line)}</p>`);
    i++;
  }
  return `<div class="mdPreview">${chunks.join('')}</div>`;
}
function mdInline(value) {
  return esc(value)
    .replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}
function isMarkdownTableAt(lines, idx) {
  return Boolean(lines[idx] && lines[idx].trim().startsWith('|') && lines[idx + 1] && /^\\s*\\|?[\\s:-]+\\|[\\s|:-]+\\|?\\s*$/.test(lines[idx + 1]));
}
function splitMarkdownRow(line) {
  return line.trim().replace(/^\\|/, '').replace(/\\|$/, '').split('|').map(cell => cell.trim());
}
function drawChart(metrics) {
  const c = document.getElementById('chart'), ctx = c.getContext('2d');
  ctx.clearRect(0,0,c.width,c.height);
  const filtered = metrics.filter(m => /mean_reward|success_rate|oracle_gap/.test(m.name || '')).slice(-80);
  ctx.strokeStyle = '#d8dde5'; ctx.beginPath(); ctx.moveTo(40,15); ctx.lineTo(40,230); ctx.lineTo(880,230); ctx.stroke();
  if (!filtered.length) { ctx.fillStyle='#687386'; ctx.fillText('No scalar metrics yet', 50, 50); return; }
  const names = [...new Set(filtered.map(m => m.name))].slice(0, 5);
  const colors = ['#2563eb','#177245','#b42318','#7a5aa6','#c08a2d'];
  names.forEach((name, ni) => {
    const vals = filtered.filter(m => m.name === name).map((m, i) => ({x: Number(m.x ?? i), y: Number(m.value)})).filter(p => Number.isFinite(p.y));
    if (vals.length < 1) return;
    const ys = vals.map(v => v.y), min = Math.min(...ys), max = Math.max(...ys), span = max-min || 1;
    ctx.strokeStyle = colors[ni % colors.length]; ctx.beginPath();
    vals.forEach((v, i) => { const x = 50 + i * (810 / Math.max(1, vals.length-1)); const y = 220 - ((v.y-min)/span) * 190; if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
    ctx.stroke(); ctx.fillStyle = colors[ni % colors.length]; ctx.fillText(name, 50, 22 + ni*16);
  });
}
async function refresh() {
  document.getElementById('clock').textContent = new Date().toLocaleString();
  await loadRuns();
  if (activeTab === 'runs') {
    await renderDashboardFinalResult();
  }
  if (activeTab === 'paper') {
    await renderPaperCompendium();
  }
  if (activeTab === 'final') {
    await renderAiModelRuns();
  }
  if (!currentRun) return;
  const [p, events, metrics, artifacts, failure, storage] = await Promise.all([
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/progress`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/events?tail=60`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/metrics`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/artifacts`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/failure`).catch(() => null),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/storage`)
  ]);
  latestProgress = p;
  document.getElementById('title').textContent = `${p.display_name || selectedRunMeta().display_name || currentRun} (${currentRun})`;
  document.getElementById('runStorage').innerHTML = runStorageHTML(storage);
  document.getElementById('runStorageSystem').innerHTML = runStorageHTML(storage);
  document.getElementById('workflowSteps').innerHTML = workflowHTML(p, artifacts);
  document.getElementById('stageGuide').innerHTML = `<div class="ux-card"><h6>${esc(p.current_step_label || stepLabel(p.current_step) || 'No active stage')}</h6><p class="muted">${esc(p.current_step || '')}</p><p>${p.estimated_remaining_s ? `ETA ${esc(fmtSeconds(p.estimated_remaining_s))}` : 'ETA is learned from run history as steps progress.'}</p></div>`;
  document.getElementById('methodGroups').innerHTML = methodGroupsHTML(p.config || {});
  document.getElementById('stats').innerHTML = statsHTML(p);
  document.getElementById('progressFill').style.width = pct(p.progress_fraction);
  document.getElementById('displayProgressFill').style.width = pct(p.display_progress_fraction);
  document.getElementById('progressText').textContent = `${p.completed_steps || 0}/${p.total_steps || 0} bundle steps completed. This only changes when a large step finishes.`;
  document.getElementById('activityText').textContent = `Current step: ${p.current_step_label || stepLabel(p.current_step) || '-'}; heartbeat age ${fmtSeconds(p.heartbeat_age_s) || 'n/a'}; step elapsed ${fmtSeconds(p.current_step_elapsed_s) || 'n/a'}; live source ${p.current_step_fraction_source || 'heartbeat'}.`;
  document.getElementById('steps').innerHTML = stepsHTML(p.steps || [], p.step_order || []);
  const detailEvent = [...events].reverse().find(e => e.event_type === 'step_progress');
  document.getElementById('detail').textContent = JSON.stringify(detailEvent?.detail || p.detail || {}, null, 2);
  if (!document.getElementById('configEditor').dataset.dirty) {
    document.getElementById('configEditor').value = JSON.stringify(p.config || {}, null, 2);
  }
  document.getElementById('provenance').textContent = JSON.stringify(p.provenance || {}, null, 2);
  document.getElementById('events').textContent = JSON.stringify(events.slice(-20), null, 2);
  latestArtifacts = artifacts;
  await renderImportantResults(currentRun);
  document.getElementById('intermediateReview').innerHTML = intermediateReviewHTML(currentRun);
  if (activeTab === 'final') {
    document.getElementById('finalResults').innerHTML = await finalResultsHTML(currentRun);
    bindPreviewButtons();
  }
  if (activeTab === 'system') renderArtifacts(currentRun);
  document.getElementById('failure').textContent = failure ? JSON.stringify(failure, null, 2) : 'No failure summary.';
  const alert = document.getElementById('alert');
  alert.className = 'banner';
  if (['failed','stalled'].includes(p.classification)) { alert.className = 'banner bad'; alert.textContent = `Run is ${p.classification}.`; }
  else if (p.classification === 'stale') { alert.className = 'banner warn'; alert.textContent = 'Heartbeat is stale.'; }
  drawChart(metrics);
  if (activeTab === 'system') {
    document.getElementById('diagnostics').textContent = JSON.stringify(await getJSON(`/api/runs/${encodeURIComponent(currentRun)}/diagnostics`), null, 2);
  }
}
function renderArtifacts(run, force=false) {
  const filterState = [
    document.getElementById('artifactCategoryFilter')?.value || '',
    document.getElementById('artifactStepFilter')?.value || '',
    document.getElementById('artifactKindFilter')?.value || '',
    document.getElementById('artifactStatusFilter')?.value || '',
    document.getElementById('artifactSearch')?.value || ''
  ].join('|');
  const dataState = latestArtifacts.map(a => `${a.resolved_path || a.path}:${a.size_bytes || ''}:${a.modified_at || ''}:${a.status || ''}`).join('|');
  const renderKey = `${run}|${filterState}|${dataState}`;
  if (!force && renderKey === lastArtifactRenderKey) return;
  lastArtifactRenderKey = renderKey;
  populateArtifactFilters(latestArtifacts);
  const items = filteredArtifacts(latestArtifacts);
  document.getElementById('artifactSummary').innerHTML = artifactSummaryHTML(items);
  document.getElementById('imageGallery').innerHTML = imageGalleryHTML(items, run);
  document.getElementById('artifacts').innerHTML = artifactsHTML(items, run);
  bindPreviewButtons();
}
function bindPreviewButtons() {
  document.querySelectorAll('[data-preview]').forEach(b => b.onclick = () => previewArtifact(b.dataset.preview, b.dataset.kind, b.dataset.name, b.dataset.meta));
}
window.addEventListener('error', event => showUiError(event.error || event.message));
window.addEventListener('unhandledrejection', event => showUiError(event.reason));
document.getElementById('refresh').onclick = () => refresh().catch(showUiError);
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => setTab(b.dataset.tab));
document.getElementById('reloadDashboardFinalResult').onclick = () => renderDashboardFinalResult(true).catch(showUiError);
document.getElementById('reloadPaperCompendium').onclick = () => renderPaperCompendium(true).catch(showUiError);
document.getElementById('reloadAiModelRuns').onclick = () => renderAiModelRuns(true).catch(showUiError);
['artifactCategoryFilter','artifactStepFilter','artifactKindFilter','artifactStatusFilter','artifactSearch'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', () => renderArtifacts(currentRun, true));
  if (el) el.addEventListener('change', () => renderArtifacts(currentRun, true));
});
document.getElementById('estimate').onclick = async () => {
  const path = document.getElementById('configPath').value;
  document.getElementById('estimateOut').textContent = JSON.stringify(await getJSON(`/api/dry-run?config=${encodeURIComponent(path)}`), null, 2);
};
document.getElementById('configEditor').addEventListener('input', e => e.target.dataset.dirty = '1');
document.getElementById('loadCurrentConfig').onclick = () => {
  document.getElementById('configEditor').value = JSON.stringify(latestProgress?.config || {}, null, 2);
  delete document.getElementById('configEditor').dataset.dirty;
};
document.getElementById('dryRunEdited').onclick = async () => {
  const cfg = JSON.parse(document.getElementById('configEditor').value || '{}');
  document.getElementById('editedEstimate').textContent = JSON.stringify({patients_per_scenario: cfg.patients_per_scenario, n_jobs: cfg.n_jobs, fallback_configs: (cfg.fallback_min_sqi||[]).length * (cfg.fallback_entropy||[]).length * (cfg.fallback_rr_cv||[]).length}, null, 2);
};
const compareButton = document.getElementById('compareButton');
if (compareButton) compareButton.onclick = async () => {
  const runs = document.getElementById('compareRuns').value || currentRun || '';
  document.getElementById('compareOut').textContent = JSON.stringify(await getJSON(`/api/compare?runs=${encodeURIComponent(runs)}`), null, 2);
};
document.getElementById('stopRun').onclick = async () => {
  if (!currentRun || !confirm(`Request safe stop for ${currentRun}?`)) return;
  document.getElementById('controlOut').textContent = JSON.stringify(await postJSON(`/api/runs/${encodeURIComponent(currentRun)}/stop`, {reason:'dashboard'}), null, 2);
};
document.getElementById('resumeRun').onclick = async () => {
  if (!currentRun) return;
  document.getElementById('controlOut').textContent = JSON.stringify(await postJSON(`/api/runs/${encodeURIComponent(currentRun)}/resume`, {}), null, 2);
};
document.getElementById('startRun').onclick = async () => {
  const runId = document.getElementById('newRunId').value;
  const cfg = JSON.parse(document.getElementById('configEditor').value || '{}');
  document.getElementById('controlOut').textContent = JSON.stringify(await postJSON('/api/start', {run_id: runId, config: cfg, resume: false}), null, 2);
};
setInterval(() => refresh().catch(showUiError), 3000);
if (activeTab === 'runs') refresh().catch(showUiError);
else setTab(activeTab);
</script>
</body>
</html>"""


def artifact_response(run_dir: str | Path, requested_path: str) -> tuple[bytes, str]:
    run_dir = Path(run_dir).resolve()
    path = Path(requested_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    if run_dir not in path.parents and path != run_dir:
        raise FileNotFoundError("Artifact outside run directory.")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path.read_bytes(), mime


def _load_run_labels(runs_dir: Path) -> dict[str, str]:
    payload = load_json(runs_dir / RUN_LABELS_FILE) or {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(value, str)}


def _summarize_run_artifacts(run_dir: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    seen: set[str] = set()

    def add(path: Path, kind: str | None = None) -> None:
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        category = _artifact_category_for_summary(path, (kind or path.suffix.lower().lstrip(".") or "file").lower())
        counts[category] = counts.get(category, 0) + 1

    for artifact in load_jsonl(run_dir / "artifacts.jsonl"):
        raw_path = artifact.get("path")
        if not raw_path:
            continue
        path = Path(str(raw_path))
        add(path, str(artifact.get("kind") or path.suffix.lower().lstrip(".") or "file"))

    for path in _discover_artifacts_shallow(run_dir):
        add(path)

    return {"count": len(seen), "categories": dict(sorted(counts.items()))}


def _artifact_category_for_summary(path: Path, kind: str) -> str:
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    if "paper_artifacts" in parts or "paper_artifacts_live" in parts:
        return "Final Results"
    if "figures" in parts or kind in {"png", "jpg", "jpeg"}:
        return "Figures"
    if kind == "csv":
        return "Tables"
    if kind in {"log", "txt"} or name.endswith("_stdout.log") or name.endswith("_stderr.log"):
        return "Logs"
    if name in {"run_manifest.json", "run_progress.json", "current_progress.json", "events.jsonl", "metrics.jsonl", "artifacts.jsonl"}:
        return "Run Metadata"
    if kind in {"json", "jsonl"}:
        return "Reports"
    if kind in {"md", "html"}:
        return "Documents"
    return "Other"


def _discover_artifacts_shallow(run_dir: Path) -> list[Path]:
    paths: list[Path] = []
    folders = [run_dir]
    for folder_name in ("paper_artifacts", "paper_artifacts_live", "figures", "logs", "configs"):
        folder = run_dir / folder_name
        if folder.exists() and folder.is_dir():
            folders.append(folder)
    for folder in folders:
        try:
            children = list(folder.iterdir())
        except OSError:
            continue
        paths.extend(path for path in children if path.is_file() and path.suffix.lower() in ARTIFACT_SUFFIXES)
    return paths


def _paper_compendium_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or "Paper Data Compendium"
    return "Paper Data Compendium"


def _paper_compendium_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix).strip()
            if value.startswith("`") and value.endswith("`"):
                return value[1:-1]
            return value or None
    return None


def _paper_compendium_sections(text: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    in_section_index = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Included Sections":
            in_section_index = True
            continue
        if in_section_index and (stripped == "---" or stripped.startswith("## ")):
            break
        if not in_section_index or not stripped.startswith("- "):
            continue
        label, _, raw_path = stripped[2:].partition(":")
        section_path = raw_path.strip()
        if section_path.startswith("`") and section_path.endswith("`"):
            section_path = section_path[1:-1]
        sections.append({"title": label.strip(), "path": section_path})
    return sections


def _ai_model_run_summary(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    if not run_dir.exists() or not run_dir.is_dir():
        return {
            "run_id": run_id,
            "exists": False,
            "status": "missing",
            "run_dir": str(run_dir),
            "display_name": run_id,
            "experiment": None,
            "config": {},
            "selector_model": {},
            "acls_rule": {},
            "oracle": {},
            "policies": {},
            "scenario_winners": [],
            "noise_robustness": [],
            "realism_comparison": {},
            "artifacts": {},
        }

    progress = _load_run_progress_summary(run_dir)
    manifest = load_json(run_dir / "run_manifest.json") or {}
    version_manifest = load_json(run_dir / "version_manifest.json") or {}
    comparison_manifest = load_json(run_dir / "comparison" / "real_vs_synthetic_abnormal_manifest.json") or {}
    config = progress.get("config") or manifest.get("config") or version_manifest.get("parameters") or {}
    selector_report = load_json(run_dir / "selector_report.json") or {}
    policy_summary = selector_report.get("policy_summary") if isinstance(selector_report, dict) else {}
    if not isinstance(policy_summary, dict):
        policy_summary = {}

    paper_dir = run_dir / "paper_artifacts"
    scenario_winners = _read_csv_rows(paper_dir / "paper_algorithm_winners.csv")
    noise_robustness = _read_csv_rows(paper_dir / "paper_noise_robustness_table.csv")
    realism_comparison = _realism_comparison_summary(run_dir, version_manifest, comparison_manifest)
    artifacts = {
        "selector_report": _artifact_file_summary(run_dir / "selector_report.json"),
        "selector_stability": _artifact_file_summary(run_dir / "selector_stability.json"),
        "algorithm_winners": _artifact_file_summary(paper_dir / "paper_algorithm_winners.csv"),
        "algorithm_matrix": _artifact_file_summary(paper_dir / "paper_algorithm_matrix_table.csv"),
        "noise_robustness": _artifact_file_summary(paper_dir / "paper_noise_robustness_table.csv"),
        "feature_weights": _artifact_file_summary(paper_dir / "waveform_analysis_weights.svg"),
        "policy_comparison": _artifact_file_summary(paper_dir / "policy_comparison.png"),
        "success_heatmap": _artifact_file_summary(paper_dir / "treatment_success_heatmap.png"),
        "final_results": _artifact_file_summary(paper_dir / "final_results.html"),
        "distance_table": _artifact_file_summary(run_dir / "comparison" / "real_vs_synthetic_abnormal_feature_distances.csv"),
        "group_summary": _artifact_file_summary(run_dir / "comparison" / "real_vs_synthetic_abnormal_group_summary.csv"),
        "unmatched_labels": _artifact_file_summary(run_dir / "comparison" / "real_abnormal_unmatched_labels.csv"),
        "smd_heatmap": _artifact_file_summary(run_dir / "comparison" / "real_vs_synthetic_smd_heatmap.png"),
        "ks_heatmap": _artifact_file_summary(run_dir / "comparison" / "real_vs_synthetic_ks_heatmap.png"),
        "pca_plot": _artifact_file_summary(run_dir / "comparison" / "real_vs_synthetic_feature_pca.png"),
        "interpretation": _artifact_file_summary(run_dir / "RESULT_INTERPRETATION.md"),
        "readme": _artifact_file_summary(run_dir / "README.md"),
    }
    progress_status = progress.get("classification") or progress.get("run_status") or progress.get("status")
    if progress_status == "unknown":
        progress_status = None
    status = (
        progress_status
        or comparison_manifest.get("status")
        or version_manifest.get("status")
        or ("completed" if manifest else None)
        or ("ok" if realism_comparison else None)
        or ("ok" if version_manifest else "unknown")
    )

    return {
        "run_id": run_id,
        "exists": True,
        "status": status,
        "run_dir": str(run_dir),
        "display_name": _run_display_name(run_dir, progress),
        "experiment": version_manifest.get("experiment") or config.get("preset") or manifest.get("run_id"),
        "updated_at": progress.get("updated_at") or manifest.get("updated_at") or manifest.get("created_at_utc") or version_manifest.get("created_at_utc"),
        "duration_s": manifest.get("duration_s") or progress.get("duration_s"),
        "config": _ai_model_config_summary(config),
        "selector_model": _policy_metric_summary(policy_summary.get("selector_linucb")),
        "acls_rule": _policy_metric_summary(policy_summary.get("acls_rule")),
        "oracle": _policy_metric_summary(policy_summary.get("oracle")),
        "policies": {str(key): _policy_metric_summary(value) for key, value in policy_summary.items() if isinstance(value, dict)},
        "scenario_winners": scenario_winners,
        "noise_robustness": noise_robustness,
        "realism_comparison": realism_comparison,
        "selector_stability": _selector_stability_summary(load_json(run_dir / "selector_stability.json") or {}),
        "artifacts": artifacts,
    }


def _ai_model_config_summary(config: dict[str, Any]) -> dict[str, Any]:
    fallback_configs = (
        len(config.get("fallback_min_sqi") or [])
        * len(config.get("fallback_entropy") or [])
        * len(config.get("fallback_rr_cv") or [])
    )
    return {
        "preset": config.get("preset"),
        "patients_per_scenario": config.get("patients_per_scenario"),
        "horizon_s": config.get("horizon_s") or config.get("observation_s"),
        "train_fraction": config.get("train_fraction"),
        "selector_seed": config.get("selector_seed"),
        "selector_stability_seeds": config.get("selector_stability_seeds") or [],
        "decision_grid_size": config.get("decision_grid_size"),
        "bootstrap_samples": config.get("bootstrap_samples"),
        "noise_profiles": config.get("noise_profiles") or [],
        "fallback_config_count": fallback_configs,
        "real_csv": config.get("real_csv"),
        "extra_real_csvs": config.get("extra_real_csvs") or [],
        "fs_hz": config.get("fs_hz"),
        "variability": config.get("variability"),
        "reward_weights": config.get("reward_weights") or {},
    }


def _policy_metric_summary(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    fields = (
        "mean_reward",
        "oracle_gap",
        "success_rate",
        "mean_energy",
        "mean_time_s",
        "mean_safety_violations",
    )
    summary: dict[str, float] = {}
    for field in fields:
        value = _as_float(raw.get(field))
        if value is not None:
            summary[field] = value
    return summary


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): _coerce_csv_value(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _coerce_csv_value(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return int(number)
    return number


def _artifact_file_summary(path: Path) -> dict[str, Any]:
    exists = path.exists() and path.is_file()
    return {
        "name": path.name,
        "path": str(path.resolve() if exists else path),
        "exists": exists,
        "kind": path.suffix.lower().lstrip(".") or "file",
        "size_bytes": path.stat().st_size if exists else None,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat() if exists else None,
    }


def _realism_comparison_summary(
    run_dir: Path,
    version_manifest: dict[str, Any],
    comparison_manifest: dict[str, Any],
) -> dict[str, Any]:
    distance_path = run_dir / "comparison" / "real_vs_synthetic_abnormal_feature_distances.csv"
    rows = _read_csv_rows(distance_path)
    smd_values = [value for value in (_as_float(row.get("smd_abs")) for row in rows) if value is not None]
    ks_values = [value for value in (_as_float(row.get("ks_statistic")) for row in rows) if value is not None]
    max_smd_row = max(rows, key=lambda row: _as_float(row.get("smd_abs")) or -1.0, default={})
    max_ks_row = max(rows, key=lambda row: _as_float(row.get("ks_statistic")) or -1.0, default={})
    groups = sorted({str(row.get("comparison_group")) for row in rows if row.get("comparison_group")})
    if not rows and not comparison_manifest:
        return {}
    return {
        "status": comparison_manifest.get("status") or ("ok" if rows else "unknown"),
        "experiment": version_manifest.get("experiment"),
        "n_real_rows": comparison_manifest.get("n_real_rows"),
        "n_synthetic_rows": comparison_manifest.get("n_synthetic_rows"),
        "real_source_counts": comparison_manifest.get("real_source_counts") or {},
        "unmatched_real_labels": comparison_manifest.get("unmatched_real_labels") or [],
        "comparison_groups": groups,
        "distance_rows": len(rows),
        "mean_smd_abs": sum(smd_values) / len(smd_values) if smd_values else None,
        "max_smd_abs": _as_float(max_smd_row.get("smd_abs")),
        "max_smd_feature": max_smd_row.get("feature"),
        "max_smd_group": max_smd_row.get("comparison_group"),
        "mean_ks_statistic": sum(ks_values) / len(ks_values) if ks_values else None,
        "max_ks_statistic": _as_float(max_ks_row.get("ks_statistic")),
        "max_ks_feature": max_ks_row.get("feature"),
        "max_ks_group": max_ks_row.get("comparison_group"),
    }


def _selector_stability_summary(payload: dict[str, Any]) -> dict[str, Any]:
    aggregate = payload.get("aggregate") if isinstance(payload, dict) else {}
    selector = aggregate.get("selector_linucb") if isinstance(aggregate, dict) else {}
    if not isinstance(selector, dict):
        return {}
    metrics: dict[str, Any] = {}
    for name in ("mean_reward", "oracle_gap", "success_rate", "mean_safety_violations"):
        raw = selector.get(name)
        if isinstance(raw, dict):
            metrics[name] = {key: value for key, value in raw.items() if key in {"mean", "std", "min", "max", "n_seeds"}}
    return metrics


def _realism_aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    realism_runs = [run for run in runs if run.get("realism_comparison")]
    smd_values = [
        value
        for value in (_as_float((run.get("realism_comparison") or {}).get("mean_smd_abs")) for run in realism_runs)
        if value is not None
    ]
    ks_values = [
        value
        for value in (_as_float((run.get("realism_comparison") or {}).get("mean_ks_statistic")) for run in realism_runs)
        if value is not None
    ]
    max_smd_runs = [
        run
        for run in realism_runs
        if _as_float((run.get("realism_comparison") or {}).get("max_smd_abs")) is not None
    ]
    worst = max(
        max_smd_runs,
        key=lambda run: _as_float((run.get("realism_comparison") or {}).get("max_smd_abs")) or -1.0,
        default=None,
    )
    worst_summary = worst.get("realism_comparison") if worst else {}
    return {
        "realism_run_count": len(realism_runs),
        "mean_smd_abs": sum(smd_values) / len(smd_values) if smd_values else None,
        "mean_ks_statistic": sum(ks_values) / len(ks_values) if ks_values else None,
        "worst_run_id": worst.get("run_id") if worst else None,
        "worst_smd_abs": worst_summary.get("max_smd_abs") if isinstance(worst_summary, dict) else None,
        "worst_feature": worst_summary.get("max_smd_feature") if isinstance(worst_summary, dict) else None,
        "worst_group": worst_summary.get("max_smd_group") if isinstance(worst_summary, dict) else None,
    }


def _versioned_run_conclusion(runs: list[dict[str, Any]]) -> dict[str, Any]:
    selector_runs = [run for run in runs if run.get("selector_model")]
    selector_run_ids = [str(run.get("run_id") or "") for run in selector_runs if run.get("run_id")]
    selector_average = _average_policy_metrics([run.get("selector_model") or {} for run in selector_runs])
    acls_average = _average_policy_metrics([run.get("acls_rule") or {} for run in selector_runs])
    oracle_average = _average_policy_metrics([run.get("oracle") or {} for run in selector_runs])
    selector_reward = _as_float(selector_average.get("mean_reward"))
    acls_reward = _as_float(acls_average.get("mean_reward"))
    oracle_reward = _as_float(oracle_average.get("mean_reward"))
    selector_success = _as_float(selector_average.get("success_rate"))
    acls_success = _as_float(acls_average.get("success_rate"))
    selector_gap = _as_float(selector_average.get("oracle_gap"))
    acls_gap = _as_float(acls_average.get("oracle_gap"))

    selector_comparable_run_count = 0
    selector_beats_acls_count = 0
    for run in selector_runs:
        run_selector_reward = _as_float((run.get("selector_model") or {}).get("mean_reward"))
        run_acls_reward = _as_float((run.get("acls_rule") or {}).get("mean_reward"))
        if run_selector_reward is None or run_acls_reward is None:
            continue
        selector_comparable_run_count += 1
        if run_selector_reward > run_acls_reward:
            selector_beats_acls_count += 1

    reward_delta_vs_acls = None
    success_delta_vs_acls = None
    verdict = "insufficient_selector_evidence"
    headline = "AI selector conclusion is not available from the versioned runs."
    if selector_reward is not None and acls_reward is not None:
        reward_delta_vs_acls = selector_reward - acls_reward
        if selector_reward > acls_reward:
            if selector_comparable_run_count and selector_beats_acls_count == selector_comparable_run_count:
                verdict = "selector_consistently_exceeds_acls"
                headline = (
                    f"Across {len(selector_runs)} selector-evaluated versioned runs, "
                    "the learned selector exceeds the ACLS-rule baseline on average and in every comparable run."
                )
            else:
                verdict = "selector_exceeds_acls_on_average"
                headline = (
                    f"Across {len(selector_runs)} selector-evaluated versioned runs, "
                    "the learned selector exceeds the ACLS-rule baseline on average, but not consistently."
                )
        else:
            verdict = "selector_underperforms_acls"
            headline = (
                f"Across {len(selector_runs)} selector-evaluated versioned runs, "
                "the learned selector should not be claimed to outperform the ACLS-rule baseline yet."
            )
    if selector_success is not None and acls_success is not None:
        success_delta_vs_acls = selector_success - acls_success

    fixed_policy_groups: dict[str, list[dict[str, Any]]] = {}
    for run in selector_runs:
        for key, value in (run.get("policies") or {}).items():
            if key.startswith("always_") and isinstance(value, dict) and value.get("mean_reward") is not None:
                fixed_policy_groups.setdefault(key, []).append(value)
    best_fixed_key = None
    best_fixed_metrics: dict[str, Any] = {}
    if fixed_policy_groups:
        fixed_policy_averages = {
            key: _average_policy_metrics(values)
            for key, values in fixed_policy_groups.items()
        }
        best_fixed_key, best_fixed_metrics = max(
            fixed_policy_averages.items(),
            key=lambda item: _as_float(item[1].get("mean_reward")) or float("-inf"),
        )

    realism_runs = [run for run in runs if run.get("realism_comparison")]
    realism_runs_sorted = sorted(realism_runs, key=lambda run: str(run.get("run_id") or ""))
    first_realism = realism_runs_sorted[0] if realism_runs_sorted else {}
    last_realism = realism_runs_sorted[-1] if realism_runs_sorted else {}
    first_summary = first_realism.get("realism_comparison") or {}
    last_summary = last_realism.get("realism_comparison") or {}
    first_smd = _as_float(first_summary.get("mean_smd_abs"))
    last_smd = _as_float(last_summary.get("mean_smd_abs"))
    first_ks = _as_float(first_summary.get("mean_ks_statistic"))
    last_ks = _as_float(last_summary.get("mean_ks_statistic"))

    realism_summary = {
        "first_run_id": first_realism.get("run_id"),
        "latest_run_id": last_realism.get("run_id"),
        "first_mean_smd_abs": first_smd,
        "latest_mean_smd_abs": last_smd,
        "mean_smd_abs_change": (last_smd - first_smd) if first_smd is not None and last_smd is not None else None,
        "first_mean_ks_statistic": first_ks,
        "latest_mean_ks_statistic": last_ks,
        "mean_ks_statistic_change": (last_ks - first_ks) if first_ks is not None and last_ks is not None else None,
        "latest_worst_feature": last_summary.get("max_smd_feature"),
        "latest_worst_group": last_summary.get("max_smd_group"),
        "latest_worst_smd_abs": last_summary.get("max_smd_abs"),
        "latest_unmatched_labels": last_summary.get("unmatched_real_labels") or [],
        "latest_real_rows": last_summary.get("n_real_rows"),
        "latest_synthetic_rows": last_summary.get("n_synthetic_rows"),
    }

    claims = [
        f"{len(selector_runs)} versioned run(s) include full AI selector outputs for treatment-selection analysis.",
        "The versioned full-pipeline results support a treatment-selection problem with nontrivial scenario-specific winners.",
        "The current LinUCB selector is evaluated against the ACLS-rule baseline, fixed-action baselines, and oracle policy.",
        "The oracle gap shows that better state representation or learning could still improve the model.",
        "The realism tuning versions reduce real-vs-synthetic mismatch, but residual feature mismatch remains too large for a clinical-performance claim.",
    ]
    limitations = [
        "Do not claim AI superiority over ACLS from these versioned results.",
        "Reward, success, and safety are simulator outcomes, not clinical endpoints.",
        "The latest realism comparison still has large sample-entropy mismatch and unmatched real rhythm labels.",
    ]
    next_steps = [
        "Improve noise-aware and morphology-aware features before claiming selector robustness.",
        "Add or map currently unmatched abnormal rhythm labels before broadening conclusions.",
        "Evaluate a stronger supervised oracle-label classifier or richer model against ACLS and LinUCB.",
    ]

    return {
        "headline": headline,
        "verdict": verdict,
        "selector_run_id": selector_run_ids[0] if selector_run_ids else None,
        "selector_run_ids": selector_run_ids,
        "selector_run_count": len(selector_runs),
        "selector_evidence": {
            "selector_reward": selector_reward,
            "selector_success_rate": selector_success,
            "selector_oracle_gap": selector_gap,
            "acls_reward": acls_reward,
            "acls_success_rate": acls_success,
            "acls_oracle_gap": acls_gap,
            "oracle_reward": oracle_reward,
            "reward_delta_vs_acls": reward_delta_vs_acls,
            "success_delta_vs_acls": success_delta_vs_acls,
            "selector_comparable_run_count": selector_comparable_run_count,
            "selector_beats_acls_count": selector_beats_acls_count,
            "best_always_policy": best_fixed_key,
            "best_always_policy_reward": _as_float(best_fixed_metrics.get("mean_reward")),
        },
        "realism_evidence": realism_summary,
        "claims": claims,
        "limitations": limitations,
        "next_steps": next_steps,
    }


def _ai_model_aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    selector_runs = [run for run in runs if run.get("selector_model")]
    return {
        "selector_model_average": _average_policy_metrics([run.get("selector_model") or {} for run in runs]),
        "acls_rule_average": _average_policy_metrics([run.get("acls_rule") or {} for run in runs]),
        "oracle_average": _average_policy_metrics([run.get("oracle") or {} for run in runs]),
        "selector_model_run_count": len(selector_runs),
        "selector_model_perfect_oracle_gap_count": sum(
            1 for run in selector_runs if _as_float((run.get("selector_model") or {}).get("oracle_gap")) == 0.0
        ),
        "selector_model_successful_run_count": sum(
            1 for run in selector_runs if (_as_float((run.get("selector_model") or {}).get("success_rate")) or 0.0) >= 1.0
        ),
        "selector_model_attention_runs": [
            run.get("run_id")
            for run in selector_runs
            if (_as_float((run.get("selector_model") or {}).get("success_rate")) or 0.0) < 1.0
            or (_as_float((run.get("selector_model") or {}).get("oracle_gap")) or 0.0) > 0.0
        ],
    }


def _average_policy_metrics(metrics_list: list[dict[str, Any]]) -> dict[str, float]:
    fields = (
        "mean_reward",
        "oracle_gap",
        "success_rate",
        "mean_energy",
        "mean_time_s",
        "mean_safety_violations",
    )
    averages: dict[str, float] = {}
    for field in fields:
        values = [
            value
            for value in (_as_float(metrics.get(field)) for metrics in metrics_list if isinstance(metrics, dict))
            if value is not None
        ]
        if values:
            averages[field] = sum(values) / len(values)
    return averages


def _ai_model_scenario_consensus(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        for row in run.get("scenario_winners") or []:
            scenario = str(row.get("scenario") or "")
            if not scenario:
                continue
            grouped.setdefault(scenario, []).append(
                {
                    "run_id": run.get("run_id"),
                    "algorithm": row.get("best_algorithm") or row.get("final_action") or row.get("algorithm"),
                    "mean_reward": _as_float(row.get("mean_reward")),
                    "success_rate": _as_float(row.get("success_rate")),
                }
            )

    order = ["monomorphic_vt", "nsr", "polymorphic_vt", "svt_flutter", "vf_like"]
    rows: list[dict[str, Any]] = []
    for scenario in sorted(grouped, key=lambda item: (order.index(item) if item in order else len(order), item)):
        entries = grouped[scenario]
        counts: dict[str, int] = {}
        for entry in entries:
            algorithm = str(entry.get("algorithm") or "")
            counts[algorithm] = counts.get(algorithm, 0) + 1
        consensus_algorithm = max(counts.items(), key=lambda item: (item[1], item[0]))[0] if counts else ""
        reward_values = [value for value in (_as_float(entry.get("mean_reward")) for entry in entries) if value is not None]
        success_values = [value for value in (_as_float(entry.get("success_rate")) for entry in entries) if value is not None]
        rows.append(
            {
                "scenario": scenario,
                "consensus_algorithm": consensus_algorithm,
                "agreement": f"{counts.get(consensus_algorithm, 0)}/{len(entries)}",
                "algorithm_counts": dict(sorted(counts.items())),
                "mean_reward": sum(reward_values) / len(reward_values) if reward_values else None,
                "success_rate": sum(success_values) / len(success_values) if success_values else None,
                "per_run": entries,
            }
        )
    return rows


def _run_display_name(run_dir: Path, snapshot: dict[str, Any] | None = None, labels: dict[str, str] | None = None) -> str:
    run_id = run_dir.name
    labels = labels if labels is not None else _load_run_labels(run_dir.parent)
    if run_id in labels:
        return labels[run_id]
    config = (snapshot or {}).get("config") or {}
    reward_weights = config.get("reward_weights") if isinstance(config, dict) else None
    time_weight = None
    if isinstance(reward_weights, dict) and "time_weight" in reward_weights:
        time_weight = reward_weights.get("time_weight")
    if time_weight is not None:
        return f"{run_id} - time{_compact_number(time_weight)}"
    return run_id


def _compact_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return ("%g" % number)


def _enrich_artifact(artifact: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    item = dict(artifact)
    path = Path(str(item.get("path") or ""))
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    try:
        relative = str(path.relative_to(run_dir.resolve()))
    except ValueError:
        relative = path.name
    exists = path.exists() and path.is_file()
    item["path"] = str(path)
    item["resolved_path"] = str(path)
    item["relative_path"] = relative
    item["name"] = path.name
    item["kind"] = str(item.get("kind") or path.suffix.lower().lstrip(".") or "file").lower()
    item["status"] = item.get("status") or ("partial" if ".partial." in path.name else "final")
    item["category"] = str(item.get("category") or _artifact_category(run_dir, path, item["kind"]))
    item["exists"] = exists
    if exists:
        item["size_bytes"] = path.stat().st_size
        item["modified_at"] = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    else:
        item.setdefault("modified_at", None)
    return item


def _discover_artifacts(run_dir: Path) -> list[Path]:
    patterns = ["*.json", "*.jsonl", "*.csv", "*.md", "*.png", "*.jpg", "*.jpeg", "*.html", "*.log", "*.txt"]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(run_dir.rglob(pattern))
    return [path for path in paths if path.is_file()]


def _artifact_category(run_dir: Path, path: Path, kind: str) -> str:
    try:
        rel = path.relative_to(run_dir)
    except ValueError:
        rel = Path(path.name)
    name = path.name.lower()
    first = rel.parts[0].lower() if rel.parts else ""
    if first == "paper_artifacts":
        return "Final Results"
    if first == "figures" or kind in {"png", "jpg", "jpeg"}:
        return "Figures"
    if kind == "csv":
        return "Tables"
    if kind in {"log", "txt"} or name.endswith("_stdout.log") or name.endswith("_stderr.log"):
        return "Logs"
    if name in {"run_manifest.json", "run_progress.json", "current_progress.json", "events.jsonl", "metrics.jsonl", "artifacts.jsonl"}:
        return "Run Metadata"
    if kind in {"json", "jsonl"}:
        return "Reports"
    if kind in {"md", "html"}:
        return "Documents"
    return "Other"


def _artifact_category_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        category = str(artifact.get("category") or "Other")
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _infer_step_for_artifact(run_dir: Path, path: Path) -> str:
    try:
        rel = path.relative_to(run_dir)
    except ValueError:
        return ""
    first = rel.parts[0] if rel.parts else path.name
    if first == "paper_artifacts":
        return "paper_artifacts"
    if first == "figures":
        return "phase2_figures"
    if "noise_ood" in path.name:
        return "noise_ood_sweep"
    if "fallback_threshold" in path.name:
        return "fallback_threshold_sweep"
    if "selector" in path.name:
        return "selector_report"
    if "calibration" in path.name:
        return "calibration_report"
    if "bootstrap" in path.name:
        return "bootstrap_ci"
    return first


def _attach_latest_detail(snapshot: dict[str, Any], run_dir: Path) -> None:
    events = load_jsonl(run_dir / "events.jsonl", tail=100)
    for event in reversed(events):
        if event.get("event_type") == "step_progress":
            snapshot["detail"] = event.get("detail", {})
            snapshot["heartbeat_at"] = event.get("created_at", snapshot.get("heartbeat_at"))
            break


def _attach_progress_estimates(snapshot: dict[str, Any], run_dir: Path) -> None:
    events = load_jsonl(run_dir / "events.jsonl", tail=500)
    current_step = snapshot.get("current_step")
    step_started_at = None
    for event in reversed(events):
        if event.get("event_type") == "step_started" and event.get("step") == current_step:
            step_started_at = event.get("created_at")
            break

    elapsed = _age_seconds(step_started_at)
    heartbeat_age = _age_seconds(snapshot.get("heartbeat_at") or snapshot.get("updated_at"))
    snapshot["current_step_started_at"] = step_started_at
    snapshot["current_step_elapsed_s"] = elapsed
    snapshot["heartbeat_age_s"] = heartbeat_age

    detail = snapshot.get("detail") or {}
    current_fraction = _detail_fraction(detail)
    snapshot["current_step_fraction"] = current_fraction
    snapshot["current_step_fraction_source"] = "detail" if current_fraction is not None else None

    total = int(snapshot.get("total_steps") or len(snapshot.get("step_order") or []) or 0)
    coarse = float(snapshot.get("progress_fraction") or 0.0)
    if (
        current_fraction is None
        and snapshot.get("classification") == "running"
        and isinstance(elapsed, (int, float))
        and elapsed > 0
    ):
        average = _completed_average_duration(snapshot)
        if average:
            current_fraction = min(0.95, float(elapsed) / (float(elapsed) + average))
            snapshot["current_step_fraction"] = current_fraction
            snapshot["current_step_fraction_source"] = "elapsed_estimate"
    if total > 0 and current_fraction is not None and snapshot.get("classification") == "running":
        snapshot["display_progress_fraction"] = min(0.999, coarse + (current_fraction / total))
    else:
        snapshot["display_progress_fraction"] = coarse

    snapshot["estimated_remaining_s"] = _estimate_remaining_seconds(snapshot)


def _detail_fraction(detail: dict[str, Any]) -> float | None:
    if not isinstance(detail, dict):
        return None
    phase = str(detail.get("phase") or "")
    completed_profiles = _as_float(detail.get("completed_profiles"))
    total_profiles = _as_float(detail.get("total_profiles"))
    completed_configs = _as_float(detail.get("completed_configs"))
    total_configs = _as_float(detail.get("total_configs"))
    if phase == "precomputing_profiles" and total_profiles:
        return max(0.0, min(0.25, 0.25 * (completed_profiles or 0.0) / total_profiles))
    if phase == "evaluating_configs" and total_configs:
        return max(0.25, min(0.95, 0.25 + 0.70 * (completed_configs or 0.0) / total_configs))
    if total_configs:
        return max(0.0, min(0.95, (completed_configs or 0.0) / total_configs))
    if total_profiles:
        return max(0.0, min(0.95, (completed_profiles or 0.0) / total_profiles))
    return None


def _estimate_remaining_seconds(snapshot: dict[str, Any]) -> float | None:
    if snapshot.get("classification") != "running":
        return 0.0
    total = int(snapshot.get("total_steps") or len(snapshot.get("step_order") or []) or 0)
    average = _completed_average_duration(snapshot)
    if not average or total <= 0:
        return None
    completed = int(snapshot.get("completed_steps") or 0)
    pending_after_current = max(0, total - completed - 1)
    current_elapsed = float(snapshot.get("current_step_elapsed_s") or 0.0)
    current_fraction = snapshot.get("current_step_fraction")
    if isinstance(current_fraction, (int, float)) and current_fraction > 0:
        current_remaining = max(0.0, current_elapsed * (1.0 - float(current_fraction)) / float(current_fraction))
    else:
        current_remaining = max(0.0, average - current_elapsed)
    return current_remaining + pending_after_current * average


def _completed_average_duration(snapshot: dict[str, Any]) -> float | None:
    steps = snapshot.get("steps") or []
    completed_durations = [
        float(step.get("duration_s"))
        for step in steps
        if step.get("status") in {"ok", "skipped"} and isinstance(step.get("duration_s"), (int, float)) and float(step.get("duration_s")) > 0
    ]
    if not completed_durations:
        return None
    return sum(completed_durations) / len(completed_durations)


def _process_diagnostics(run_id: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"platform": os.name, "processes": [], "worker_count": 0, "cpu_time_s_total": None, "memory_bytes_total": None}
    script = r"""
$items = @()
$cim = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"
foreach ($p in $cim) {
  $gp = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
  if ($gp) {
    $items += [pscustomobject]@{
      pid = $p.ProcessId
      ppid = $p.ParentProcessId
      command = $p.CommandLine
      cpu_time_s = $gp.CPU
      memory_bytes = $gp.WorkingSet64
      start_time = if ($gp.StartTime) { $gp.StartTime.ToString("o") } else { $null }
    }
  }
}
$items | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return {"platform": "windows", "error": str(exc), "processes": [], "worker_count": 0}
    if result.returncode != 0 or not result.stdout.strip():
        return {"platform": "windows", "error": result.stderr.strip(), "processes": [], "worker_count": 0}
    try:
        payload = __import__("json").loads(result.stdout)
    except Exception as exc:
        return {"platform": "windows", "error": str(exc), "processes": [], "worker_count": 0}
    processes = payload if isinstance(payload, list) else [payload]
    by_parent: dict[int, list[dict[str, Any]]] = {}
    by_pid: dict[int, dict[str, Any]] = {}
    roots: list[int] = []
    for proc in processes:
        pid = int(proc.get("pid") or 0)
        ppid = int(proc.get("ppid") or 0)
        by_pid[pid] = proc
        by_parent.setdefault(ppid, []).append(proc)
        if run_id in str(proc.get("command") or ""):
            roots.append(pid)
    selected: dict[int, dict[str, Any]] = {}
    stack = roots[:]
    while stack:
        pid = stack.pop()
        if pid in selected:
            continue
        proc = by_pid.get(pid)
        if not proc:
            continue
        selected[pid] = proc
        stack.extend(int(child.get("pid") or 0) for child in by_parent.get(pid, []))
    rows = sorted(selected.values(), key=lambda item: int(item.get("pid") or 0))
    return {
        "platform": "windows",
        "root_pids": roots,
        "processes": rows,
        "worker_count": max(0, len(rows) - len(roots)),
        "cpu_time_s_total": sum(float(proc.get("cpu_time_s") or 0.0) for proc in rows),
        "memory_bytes_total": sum(int(proc.get("memory_bytes") or 0) for proc in rows),
    }


def _age_seconds(value: Any) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return time.time() - parsed.timestamp()


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _latest_key_metrics(run_dir: Path) -> dict[str, float]:
    latest: dict[str, float] = {}
    for metric in load_jsonl(run_dir / "metrics.jsonl"):
        name = metric.get("name")
        value = metric.get("value")
        if isinstance(name, str) and isinstance(value, (int, float)):
            latest[name] = float(value)
    return latest
