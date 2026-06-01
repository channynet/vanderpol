"""Read-only dashboard data helpers for experiment run directories."""

from __future__ import annotations

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
        progress = load_run_progress(run_dir)
        artifacts = load_run_artifacts(run_dir)
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
                "artifact_count": len(artifacts),
                "categories": _artifact_category_counts(artifacts),
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
          <div class="panel card dashboard-panel" id="panel-final"><div class="card-body"><h5 class="card-title mb-4">Final Results</h5><div class="guardrail">This page summarizes simulator evidence only. Do not interpret it as clinical efficacy.</div><div id="finalResults"></div></div></div>
          <div class="panel card dashboard-panel" id="panel-system"><div class="card-body"><h5 class="card-title mb-4">System</h5><h5 class="card-title mb-4">Run Storage</h5><div id="runStorageSystem" class="mb-6"></div><h5 class="card-title mt-6 mb-4">All Outputs</h5><div id="artifactSummary" class="artifactSummary"></div><div class="filterbar mb-4"><select id="artifactCategoryFilter"><option value="">All categories</option></select><select id="artifactStepFilter"><option value="">All steps</option></select><select id="artifactKindFilter"><option value="">All kinds</option></select><select id="artifactStatusFilter"><option value="">All status</option><option value="final">Final</option><option value="partial">Partial</option></select><input id="artifactSearch" class="form-control slim" placeholder="Search filename or path"></div><h5 class="card-title mt-6 mb-4">Image Gallery</h5><div id="imageGallery" class="gallery"></div><h5 class="card-title mt-6 mb-4">All Outputs By Step</h5><div id="artifacts"></div><h5 class="card-title mt-6 mb-4">Preview</h5><div id="artifactPreview" class="viewer"><span class="muted">Select an artifact preview button.</span></div><h5 class="card-title mt-6 mb-4">Live Scalar Metrics</h5><canvas id="chart" width="900" height="260"></canvas><h5 class="card-title mt-6 mb-4">Resource Diagnostics</h5><pre id="diagnostics">{}</pre><h5 class="card-title mt-6 mb-4">Provenance</h5><pre id="provenance">{}</pre></div></div>
        </div>
      </main>
    </div>
  </div>
</main>
<script>
let currentRun = null;
let activeTab = 'runs';
let latestProgress = null;
let latestArtifacts = [];
let latestRuns = [];
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
  selector_report: 'stage5 - AI가 파형 특징으로 치료 판단을 학습하는 단계',
  decision_boundary: 'stage5 - AI 판단 경계를 확인하는 단계',
  bootstrap_ci: 'stage5 - 최종 정답률의 불확실성을 계산하는 단계',
  selector_stability: 'stage5 - AI 학습 안정성을 확인하는 단계',
  noise_ood_sweep: 'stage6 - 노이즈가 들어온 파형에서 AI 판단을 점검하는 단계',
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
function stepLabel(name) {
  return STEP_LABELS[name] || name || '';
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
  const root = document.getElementById('runs');
  root.innerHTML = data.map(r => {
    const statusLine = [r.status || 'unknown', stepLabel(r.current_step) || ''].filter(Boolean).join(' - ');
    const cats = Object.entries(r.categories || {}).map(([k,v]) => `${k}:${v}`).join(' ');
    return `<button class="run ${r.run_id===currentRun?'active':''}" data-run="${esc(r.run_id)}"><b>${esc(r.display_name || r.run_id)}</b><br><span class="muted">id: ${esc(r.run_id)}</span><span class="muted runPath">${esc(r.run_dir || '')}</span><span class="muted">${esc(statusLine)}</span><br><span class="muted">${Number(r.artifact_count || 0)} outputs ${esc(cats)}</span><div class="runMiniProgress" aria-label="run progress"><div class="runMiniFill" style="width:${pct(r.display_progress_fraction || r.progress_fraction)}"></div></div></button>`;
  }).join('');
  root.querySelectorAll('button').forEach(b => b.onclick = () => { currentRun = b.dataset.run; lastArtifactRenderKey = ''; lastImportantRenderKey = ''; refresh(); });
  if (!currentRun && data[0]) { currentRun = data[0].run_id; }
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
  const hasFinal = names.has('final_results.html') || names.has('selector_report.json') || names.has('final_visual_summary.svg');
  const steps = [
    ['Run Settings', Boolean(p?.config), 'parameters'],
    ['Intermediate Results', hasIntermediate, 'waveforms and generated data'],
    ['AI Learning', names.has('selector_report.json'), stepLabel('selector_report')],
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
    reviewCardHTML(run, 'Intermediate Figures', ['phase2_mean_reward.png','phase2_success_rate.png','phase2_mean_time_s.png'], 'Per-scenario intermediate images before the final AI judgement is summarized.', ['reward_weights']),
    reviewCardHTML(run, 'Feature Extraction', ['selector_report.json','decision_boundary.png'], 'The ECG-derived features that become AI inputs before the final decision.', ['train_fraction','selector_seed','decision_grid_size'])
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
      const rows = ['selector_linucb','conservative_selector','acls_rule','oracle'].filter(k => policies[k]).map(k => {
        const m = policies[k];
        return `<tr><td>${esc(k)}</td><td>${Number(m.mean_reward).toFixed(3)}</td><td>${Number(m.oracle_gap).toFixed(3)}</td><td>${Number(m.success_rate).toFixed(3)}</td><td>${Number(m.mean_safety_violations).toFixed(3)}</td></tr>`;
      }).join('');
      headline = `<table><thead><tr><th>Policy</th><th>Reward</th><th>Oracle Gap</th><th>Success</th><th>Safety</th></tr></thead><tbody>${rows}</tbody></table>`;
    } catch {}
  }
  return `<div class="ux-grid"><div class="ux-card"><h6>AI Judgement Accuracy</h6>${headline}</div><div class="ux-card"><h6>Symptom-Level Final Decision</h6>${artifactPill(run, winners, winners?.name || 'winner table')} ${artifactPill(run, artifactByName(latestArtifacts, 'final_results.html', true), 'final_results.html')}<p class="muted mt-3">Estimated correctness when the selector receives waveform-derived features without being handed the disease label.</p></div><div class="ux-card"><h6>Waveform Analysis Weights</h6>${artifactPill(run, artifactByName(latestArtifacts, 'waveform_analysis_weights.svg', true), 'weights image')} ${artifactPill(run, artifactByName(latestArtifacts, 'decision_boundary.png'), 'decision boundary')}<p class="muted mt-3">Shows which extracted waveform features most influence treatment selection.</p></div><div class="ux-card"><h6>Robustness And Confidence</h6>${artifactPill(run, artifactByName(latestArtifacts, 'noise_ood_sweep.csv'), 'noise check')} ${artifactPill(run, artifactByName(latestArtifacts, 'bootstrap_matrix_ci.csv'), 'uncertainty')} ${artifactPill(run, artifactByName(latestArtifacts, 'selector_stability.json'), 'stability')}<p class="muted mt-3">Claims stay bounded to simulator evidence.</p></div></div>`;
}
function paperResultHTML(run) {
  const paperItems = latestArtifacts.filter(a => (a.relative_path || '').startsWith('paper_artifacts'));
  if (!paperItems.length) return '<p class="muted">No final result folder found for this run yet.</p>';
  const preferred = ['intermediate_results.html','intermediate_waveforms.svg','final_results.html','final_visual_summary.png','final_visual_summary.svg','waveform_analysis_weights.svg','policy_comparison.png','policy_comparison.svg','treatment_success_heatmap.png','treatment_success_heatmap.svg','visual_report.html'];
  return `<div class="ux-grid">${preferred.map(name => `<div class="ux-card"><h6>${esc(name)}</h6>${artifactPill(run, artifactByName(paperItems, name, true), name)}</div>`).join('')}</div>`;
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
  const selector = artifactByName(latestArtifacts, 'paper_selector_table.csv', true) || artifactByName(latestArtifacts, 'selector_report.csv');
  const winners = artifactByName(latestArtifacts, 'paper_algorithm_winners.csv', true) || artifactByName(latestArtifacts, 'phase2_matrix_summary.csv');
  const [selectorText, winnersText] = await Promise.all([
    artifactTextOrEmpty(run, selector),
    artifactTextOrEmpty(run, winners)
  ]);
  return `<div class="resultStack">
    <div class="resultGrid">
      ${resultBlock('Intermediate Results', `${artifactPill(run, intermediateDoc, 'intermediate_results.html')} ${artifactPill(run, waveform, 'waveform image')}<p class="muted mt-3">Run data generation and representative waveform preview.</p>`, run, intermediateDoc || waveform)}
      ${resultBlock('Final Results', `${artifactPill(run, finalDoc, 'final_results.html')} ${artifactPill(run, weights, 'feature weights')} ${artifactPill(run, heatmap, 'success heatmap')}<p class="muted mt-3">AI judgement accuracy and waveform-analysis weighting.</p>`, run, finalDoc || weights || heatmap)}
    </div>
    <div class="resultBlock"><h6>Intermediate Figures</h6>${figureResultsHTML(run)}</div>
    <div class="resultGrid">
      ${resultBlock('AI Judgement Summary', selector ? tableArtifactHTML(selector, selectorText, 80) : '', run, selector)}
      ${resultBlock('Symptom-Level Treatment Result', winners ? tableArtifactHTML(winners, winnersText, 80) : '', run, winners)}
    </div>
  </div>`;
}
async function renderImportantResults(run, force=false) {
  const importantNames = new Set([
    'intermediate_results.html','intermediate_waveforms.svg','final_results.html','visual_report.html',
    'waveform_analysis_weights.svg','treatment_success_heatmap.svg','treatment_success_heatmap.png',
    'paper_selector_table.csv','selector_report.csv',
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
    else if (line.startsWith('- ')) chunks.push(`<p>• ${mdInline(line.slice(2))}</p>`);
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
refresh().catch(showUiError);
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
