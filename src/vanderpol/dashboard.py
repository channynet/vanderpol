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
from .stage8 import load_bundle_config


def list_runs(runs_dir: str | Path = "outputs/runs") -> list[dict[str, Any]]:
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        return []
    rows = []
    for run_dir in sorted([path for path in runs_dir.iterdir() if path.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        progress = load_run_progress(run_dir)
        rows.append(
            {
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "status": progress.get("classification") or progress.get("run_status") or progress.get("status"),
                "current_step": progress.get("current_step"),
                "progress_fraction": progress.get("progress_fraction", 0.0),
                "display_progress_fraction": progress.get("display_progress_fraction", progress.get("progress_fraction", 0.0)),
                "heartbeat_at": progress.get("heartbeat_at") or progress.get("updated_at"),
                "updated_at": progress.get("updated_at") or progress.get("created_at_utc"),
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
  <link rel="shortcut icon" type="image/png" href="/tailadmin-assets/images/logos/favicon.png">
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
    .ta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem; }
    .ta-progress { height: 10px; background: var(--color-bordergray); border-radius: 999px; overflow: hidden; }
    .fill { height: 100%; background: var(--color-primary); width: 0; transition: width .35s ease; }
    .fill.alt { background: var(--color-success); }
    .run { display: block; width: 100%; text-align: left; border: 1px solid var(--color-border); background: var(--color-white); border-radius: var(--radius-md); padding: 10px 12px; margin-bottom: 8px; cursor: pointer; color: var(--color-link); }
    .run:hover, .run.active { background: var(--color-lightprimary); color: var(--color-primary); border-color: transparent; }
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
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--color-border); padding: 10px 8px; text-align: left; vertical-align: top; }
    .jsonTree details { margin-left: 12px; }
    .jsonTree summary { cursor: pointer; }
    .mdPreview { line-height: 1.5; max-width: 920px; }
    .missing { color: var(--color-error); }
    @media (max-width: 1299px) { .page-wrapper { margin-left: 0; } }
    @media (max-width: 768px) { .container { padding-inline: 16px; } .filterbar input { min-width: 100%; } }
  </style>
</head>
<body class="DEFAULT_THEME bg-white dark:bg-dark">
<main>
  <div id="main-wrapper" class="flex">
    <aside id="application-sidebar-brand" class="hs-overlay hs-overlay-open:translate-x-0 -translate-x-full xl:rtl:-translate-x-0 rtl:translate-x-full left-0 rtl:left-auto rtl:right-0 transform hidden xl:block xl:translate-x-0 xl:end-auto xl:bottom-0 fixed top-0 with-vertical left-sidebar transition-all duration-300 h-screen z-20 flex-shrink-0 border-r rtl:border-l rtl:border-r-0 w-[270px] border-border dark:border-darkborder bg-white dark:bg-dark">
      <div class="py-5 px-5 flex justify-between">
        <div class="brand-logo flex items-center justify-center">
          <a href="/" class="text-nowrap logo-img flex items-center gap-3">
            <img src="/tailadmin-assets/images/logos/logoIcon.svg" alt="Vanderpol" class="w-10 h-10">
            <span class="hide-menu text-lg font-semibold text-dark">Vanderpol</span>
          </a>
        </div>
      </div>
      <div class="scroll-sidebar" data-simplebar="">
        <div class="px-6 mt-8 mini-layout" data-te-sidenav-menu-ref>
          <nav id="tabs" class="hs-accordion-group w-full flex flex-col">
            <ul data-te-sidenav-menu-ref id="sidebarnav">
              <div class="caption"><i class="ti ti-dots nav-small-cap-icon"></i><span class="hide-menu">Dashboard</span></div>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link active activemenu" data-tab="overview"><i class="ti ti-layout-dashboard text-xl shrink-0"></i><span class="hide-menu shrink-0">Overview</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="timeline"><i class="ti ti-timeline-event text-xl shrink-0"></i><span class="hide-menu shrink-0">Timeline</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="deep"><i class="ti ti-activity-heartbeat text-xl shrink-0"></i><span class="hide-menu shrink-0">Deep Progress</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="outputs"><i class="ti ti-photo-scan text-xl shrink-0"></i><span class="hide-menu shrink-0">Outputs</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="metrics"><i class="ti ti-chart-line text-xl shrink-0"></i><span class="hide-menu shrink-0">Metrics</span></button></li>
              <div class="caption mt-8"><i class="ti ti-dots nav-small-cap-icon"></i><span class="hide-menu">Operations</span></div>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="settings"><i class="ti ti-adjustments text-xl shrink-0"></i><span class="hide-menu shrink-0">Settings</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="compare"><i class="ti ti-git-compare text-xl shrink-0"></i><span class="hide-menu shrink-0">Compare</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="diagnostics"><i class="ti ti-cpu text-xl shrink-0"></i><span class="hide-menu shrink-0">Diagnostics</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="control"><i class="ti ti-player-stop text-xl shrink-0"></i><span class="hide-menu shrink-0">Control</span></button></li>
              <li class="sidebar-item"><button type="button" class="sidebar-link dark-sidebar-link" data-tab="provenance"><i class="ti ti-fingerprint text-xl shrink-0"></i><span class="hide-menu shrink-0">Provenance</span></button></li>
            </ul>
          </nav>
          <div class="caption mt-8"><i class="ti ti-dots nav-small-cap-icon"></i><span class="hide-menu">Runs</span></div>
          <div id="runs" class="mt-3"></div>
          <div class="bg-lightprimary flex flex-col gap-3 rounded-lg p-5 mt-5">
            <div>
              <h5 class="text-base font-semibold mb-2 leading-tight">Dry Run Estimate</h5>
              <div class="inputRow">
                <input id="configPath" class="form-control slim" value="configs/bundle_smoke.json">
                <button id="estimate" class="btn btn-md">Estimate</button>
              </div>
            </div>
            <pre id="estimateOut">{}</pre>
          </div>
          <p class="text-xs text-bodytext mt-4">TailAdmin MIT template assets are served locally.</p>
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
          <div class="relative flex items-center justify-between bg-lightsecondary rounded-lg p-6 mb-6 overflow-hidden">
            <div class="flex items-center gap-3">
              <img src="/tailadmin-assets/images/profile/user-1.jpg" alt="run profile" class="w-[50px] h-[50px] rounded-full">
              <div class="flex flex-col gap-0.5">
                <h5 class="text-lg font-semibold">Experiment Dashboard</h5>
                <p id="title" class="text-link/80 dark:text-white/80">Select a run</p>
              </div>
            </div>
            <div class="hidden sm:block absolute right-8 bottom-0">
              <img src="/tailadmin-assets/images/background/customer-support-img.png" alt="support" class="w-[145px] h-[95px]">
            </div>
          </div>
          <div id="alert" class="banner"></div>

          <div class="panel active card dashboard-panel" id="panel-overview">
            <div class="card-body">
              <div class="ta-grid" id="stats"></div>
              <h5 class="card-title mt-6 mb-3">Step Progress</h5>
              <div class="ta-progress"><div class="fill" id="progressFill"></div></div>
              <p id="progressText" class="text-sm text-bodytext mt-2"></p>
              <h5 class="card-title mt-5 mb-3">Live Estimate</h5>
              <div class="ta-progress"><div class="fill alt" id="displayProgressFill"></div></div>
              <p id="activityText" class="text-sm text-bodytext mt-2"></p>
            </div>
          </div>

          <div class="panel card dashboard-panel" id="panel-timeline"><div class="card-body"><h5 class="card-title mb-4">Pipeline Timeline</h5><div id="steps"></div></div></div>
          <div class="panel card dashboard-panel" id="panel-deep"><div class="card-body"><h5 class="card-title mb-4">Deep Progress</h5><pre id="detail">{}</pre><h5 class="card-title mt-6 mb-4">Recent Events</h5><pre id="events"></pre><h5 class="card-title mt-6 mb-4">Failure Triage</h5><pre id="failure"></pre></div></div>
          <div class="panel card dashboard-panel" id="panel-outputs"><div class="card-body"><h5 class="card-title mb-4">Outputs</h5><div id="artifactSummary" class="artifactSummary"></div><div class="filterbar mb-4"><select id="artifactStepFilter"><option value="">All steps</option></select><select id="artifactKindFilter"><option value="">All kinds</option></select><select id="artifactStatusFilter"><option value="">All status</option><option value="final">Final</option><option value="partial">Partial</option></select><input id="artifactSearch" class="form-control slim" placeholder="Search filename or path"></div><h5 class="card-title mt-6 mb-4">Image Gallery</h5><div id="imageGallery" class="gallery"></div><h5 class="card-title mt-6 mb-4">Grouped Artifacts</h5><div id="artifacts"></div><h5 class="card-title mt-6 mb-4">Preview</h5><div id="artifactPreview" class="viewer"><span class="muted">Select an artifact preview button.</span></div></div></div>
          <div class="panel card dashboard-panel" id="panel-metrics"><div class="card-body"><h5 class="card-title mb-4">Live Scalar Metrics</h5><canvas id="chart" width="900" height="260"></canvas></div></div>
          <div class="panel card dashboard-panel" id="panel-settings"><div class="card-body"><h5 class="card-title mb-4">Parameters</h5><textarea id="configEditor" class="form-control">{}</textarea><div class="actions mt-4"><button class="btn-outline-primary" id="loadCurrentConfig">Load Current Run Config</button><button class="btn" id="dryRunEdited">Estimate Edited Config</button></div><pre id="editedEstimate" class="mt-4">{}</pre></div></div>
          <div class="panel card dashboard-panel" id="panel-compare"><div class="card-body"><h5 class="card-title mb-4">Run Compare</h5><div class="inputRow"><input id="compareRuns" class="form-control slim" placeholder="run_a,run_b"><button id="compareButton" class="btn">Compare</button></div><pre id="compareOut" class="mt-4">{}</pre></div></div>
          <div class="panel card dashboard-panel" id="panel-diagnostics"><div class="card-body"><h5 class="card-title mb-4">Resource Diagnostics</h5><pre id="diagnostics">{}</pre></div></div>
          <div class="panel card dashboard-panel" id="panel-control"><div class="card-body"><h5 class="card-title mb-4">Safe Controls</h5><p class="text-bodytext mb-4">Pause means safe stop at the next checkpoint. It does not suspend process memory.</p><div class="actions"><button class="btn-danger" id="stopRun">Request Safe Stop</button><button class="btn" id="resumeRun">Resume Selected Run</button></div><h5 class="card-title mt-6 mb-4">Start New Run</h5><div class="inputRow"><input id="newRunId" class="form-control slim" placeholder="new_run_id"><button class="btn" id="startRun">Start From Settings</button></div><pre id="controlOut" class="mt-4">{}</pre></div></div>
          <div class="panel card dashboard-panel" id="panel-provenance"><div class="card-body"><h5 class="card-title mb-4">Provenance</h5><pre id="provenance">{}</pre></div></div>
        </div>
      </main>
    </div>
  </div>
</main>
<script>
let currentRun = null;
let activeTab = 'overview';
let latestProgress = null;
let latestArtifacts = [];
let lastArtifactRenderKey = '';
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
function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll('#tabs button').forEach(b => {
    const selected = b.dataset.tab === tab;
    b.classList.toggle('active', selected);
    b.classList.toggle('activemenu', selected);
  });
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tab}`));
  if (tab === 'outputs' && currentRun) renderArtifacts(currentRun, true);
  refresh().catch(showUiError);
}
async function loadRuns() {
  const data = await getJSON('/api/runs');
  const root = document.getElementById('runs');
  root.innerHTML = data.map(r => `<button class="run ${r.run_id===currentRun?'active':''}" data-run="${esc(r.run_id)}"><b>${esc(r.run_id)}</b><br><span class="muted">${esc(r.status)} step ${pct(r.progress_fraction)} live ${pct(r.display_progress_fraction)} ${esc(r.current_step||'')}</span></button>`).join('');
  root.querySelectorAll('button').forEach(b => b.onclick = () => { currentRun = b.dataset.run; lastArtifactRenderKey = ''; refresh(); });
  if (!currentRun && data[0]) { currentRun = data[0].run_id; }
}
function statsHTML(p) {
  const progress = Number(p.progress_fraction || 0);
  const elapsed = Number(p.duration_s || 0);
  const eta = Number(p.estimated_remaining_s || 0);
  const nJobs = p.config ? p.config.n_jobs : '';
  const visuals = [
    ['bg-lightprimary', 'text-primary', '/tailadmin-assets/images/svgs/icon-user-male.svg'],
    ['bg-lightwarning', 'text-warning', '/tailadmin-assets/images/svgs/icon-briefcase.svg'],
    ['bg-lightinfo', 'text-info', '/tailadmin-assets/images/svgs/icon-mailbox.svg'],
    ['bg-lighterror', 'text-error', '/tailadmin-assets/images/svgs/icon-favorites.svg'],
    ['bg-lightsuccess', 'text-success', '/tailadmin-assets/images/svgs/icon-speech-bubble.svg'],
    ['bg-lightinfo', 'text-info', '/tailadmin-assets/images/svgs/icon-connect.svg']
  ];
  return [
    ['Status', p.classification || p.run_status || p.status],
    ['Current Step', p.current_step || ''],
    ['Step Progress', pct(p.progress_fraction)],
    ['Live Estimate', pct(p.display_progress_fraction)],
    ['N Jobs', nJobs || ''],
    ['Elapsed', fmtSeconds(elapsed)],
    ['ETA', fmtSeconds(eta) || ''],
    ['Step Elapsed', fmtSeconds(p.current_step_elapsed_s) || ''],
    ['Heartbeat Age', fmtSeconds(p.heartbeat_age_s) || '']
  ].map(([k,v], i) => {
    const [bg, text, icon] = visuals[i % visuals.length];
    return `<div class="card mb-0 shadow-none ${bg} w-full"><div class="card-body"><div class="text-center"><div class="flex justify-center"><img src="${icon}" width="50" height="50" class="mb-3" alt=""></div><p class="font-semibold ${text} mb-1">${esc(k)}</p><h5 class="text-lg font-semibold ${text} mb-0">${esc(v)}</h5></div></div></div>`;
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
    return `<tr><td>${esc(s.name)}</td><td>${esc(s.status)}</td><td>${esc(duration)}</td><td>${esc(s.message||'')}</td></tr>`;
  }).join('')}</tbody></table>`;
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
  const step = document.getElementById('artifactStepFilter')?.value || '';
  const kind = document.getElementById('artifactKindFilter')?.value || '';
  const status = document.getElementById('artifactStatusFilter')?.value || '';
  const q = (document.getElementById('artifactSearch')?.value || '').toLowerCase();
  return items.filter(a => {
    const hay = `${a.name || ''} ${a.relative_path || ''} ${a.path || ''}`.toLowerCase();
    return (!step || a.step === step) && (!kind || a.kind === kind) && (!status || a.status === status) && (!q || hay.includes(q));
  });
}
function populateArtifactFilters(items) {
  const stepEl = document.getElementById('artifactStepFilter');
  const kindEl = document.getElementById('artifactKindFilter');
  const oldStep = stepEl.value, oldKind = kindEl.value;
  const steps = [...new Set(items.map(a => a.step || 'unknown'))].sort();
  const kinds = [...new Set(items.map(a => a.kind || 'file'))].sort();
  stepEl.innerHTML = '<option value="">All steps</option>' + steps.map(v => `<option value="${attr(v)}">${esc(v)}</option>`).join('');
  kindEl.innerHTML = '<option value="">All kinds</option>' + kinds.map(v => `<option value="${attr(v)}">${esc(v)}</option>`).join('');
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
      <div class="card-body"><h6 class="font-semibold mb-1">${esc(a.name || '')}</h6><span class="muted">${esc(a.step || '')} - ${formatBytes(a.size_bytes)}</span></div>
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
    const body = `<table><thead><tr><th>Name</th><th>Kind</th><th>Status</th><th>Size</th><th>Updated</th><th>Action</th></tr></thead><tbody>${rows.map(a => {
      const url = artifactUrl(run, a);
      const missing = a.exists === false ? ' missing' : '';
      return `<tr class="${missing}"><td><a target="_blank" href="${attr(url)}">${esc(a.name || a.relative_path || a.path)}</a><br><span class="muted">${esc(a.relative_path || a.path)}</span></td><td>${esc(a.kind)}</td><td>${esc(a.status)}</td><td>${formatBytes(a.size_bytes)}</td><td>${esc(a.modified_at || a.created_at || '')}</td><td><button class="plain" data-preview="${attr(url)}" data-kind="${attr(a.kind)}" data-name="${attr(a.name || '')}" data-meta="${attr(a.relative_path || a.path)}">Preview</button></td></tr>`;
    }).join('')}</tbody></table>`;
    return `<div class="stepGroup"><div class="stepHeader"><b>${esc(step)}</b><span><span class="badge">${rows.length} files</span><span class="badge">${esc(counts)}</span></span></div><div class="stepBody">${body}</div></div>`;
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
function csvPreviewHTML(text) {
  const rows = parseCSV(text, 200);
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
  const html = esc(text.slice(0, 120000))
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\\n/g, '<br>');
  return `<div class="mdPreview">${html}</div>`;
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
  const [p, events, metrics, artifacts, failure] = await Promise.all([
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/progress`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/events?tail=60`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/metrics`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/artifacts`),
    getJSON(`/api/runs/${encodeURIComponent(currentRun)}/failure`).catch(() => null)
  ]);
  latestProgress = p;
  document.getElementById('title').textContent = currentRun;
  document.getElementById('stats').innerHTML = statsHTML(p);
  document.getElementById('progressFill').style.width = pct(p.progress_fraction);
  document.getElementById('displayProgressFill').style.width = pct(p.display_progress_fraction);
  document.getElementById('progressText').textContent = `${p.completed_steps || 0}/${p.total_steps || 0} bundle steps completed. This only changes when a large step finishes.`;
  document.getElementById('activityText').textContent = `Current step: ${p.current_step || '-'}; heartbeat age ${fmtSeconds(p.heartbeat_age_s) || 'n/a'}; step elapsed ${fmtSeconds(p.current_step_elapsed_s) || 'n/a'}; live source ${p.current_step_fraction_source || 'heartbeat'}.`;
  document.getElementById('steps').innerHTML = stepsHTML(p.steps || [], p.step_order || []);
  const detailEvent = [...events].reverse().find(e => e.event_type === 'step_progress');
  document.getElementById('detail').textContent = JSON.stringify(detailEvent?.detail || p.detail || {}, null, 2);
  if (!document.getElementById('configEditor').dataset.dirty) {
    document.getElementById('configEditor').value = JSON.stringify(p.config || {}, null, 2);
  }
  document.getElementById('provenance').textContent = JSON.stringify(p.provenance || {}, null, 2);
  document.getElementById('events').textContent = JSON.stringify(events.slice(-20), null, 2);
  latestArtifacts = artifacts;
  if (activeTab === 'outputs') renderArtifacts(currentRun);
  document.getElementById('failure').textContent = failure ? JSON.stringify(failure, null, 2) : 'No failure summary.';
  const alert = document.getElementById('alert');
  alert.className = 'banner';
  if (['failed','stalled'].includes(p.classification)) { alert.className = 'banner bad'; alert.textContent = `Run is ${p.classification}.`; }
  else if (p.classification === 'stale') { alert.className = 'banner warn'; alert.textContent = 'Heartbeat is stale.'; }
  drawChart(metrics);
  if (activeTab === 'diagnostics') {
    document.getElementById('diagnostics').textContent = JSON.stringify(await getJSON(`/api/runs/${encodeURIComponent(currentRun)}/diagnostics`), null, 2);
  }
}
function renderArtifacts(run, force=false) {
  const filterState = [
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
  document.querySelectorAll('[data-preview]').forEach(b => b.onclick = () => previewArtifact(b.dataset.preview, b.dataset.kind, b.dataset.name, b.dataset.meta));
}
window.addEventListener('error', event => showUiError(event.error || event.message));
window.addEventListener('unhandledrejection', event => showUiError(event.reason));
document.getElementById('refresh').onclick = () => refresh().catch(showUiError);
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => setTab(b.dataset.tab));
['artifactStepFilter','artifactKindFilter','artifactStatusFilter','artifactSearch'].forEach(id => {
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
document.getElementById('compareButton').onclick = async () => {
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
    item["exists"] = exists
    if exists:
        item["size_bytes"] = path.stat().st_size
        item["modified_at"] = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    else:
        item.setdefault("modified_at", None)
    return item


def _discover_artifacts(run_dir: Path) -> list[Path]:
    patterns = ["*.json", "*.csv", "*.md", "*.png", "*.html", "*.log", "*.txt"]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(run_dir.rglob(pattern))
    ignored = {"events.jsonl", "metrics.jsonl", "artifacts.jsonl"}
    return [path for path in paths if path.name not in ignored and path.is_file()]


def _infer_step_for_artifact(run_dir: Path, path: Path) -> str:
    try:
        rel = path.relative_to(run_dir)
    except ValueError:
        return ""
    first = rel.parts[0] if rel.parts else path.name
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
