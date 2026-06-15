from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import mimetypes
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.dashboard import (  # noqa: E402
    compare_runs,
    dry_run_estimate,
    list_runs,
    load_ai_model_run_results,
    load_failure,
    load_final_result,
    load_paper_compendium,
    load_run_artifacts,
    load_run_diagnostics,
    load_run_events,
    load_run_metrics,
    load_run_progress,
    load_run_storage,
    render_dashboard_html,
)


DEFAULT_THEME_CSS = Path("vendor/tailwind-admin-template/tailwind-admin-html-free/dist/assets/css/theme.css")
DEFAULT_TABLER_CSS = Path("vendor/tailwind-admin-template/tailwind-admin-html-free/dist/assets/fonts/icons/tabler-icons/tabler-icons.css")
DEFAULT_TABLER_WOFF2 = Path("vendor/tailwind-admin-template/tailwind-admin-html-free/dist/assets/fonts/icons/tabler-icons/fonts/tabler-icons.woff2")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static copy of the local dashboard for GitHub Pages.")
    parser.add_argument("--input-json", type=Path, default=Path("docs/final_result.json"))
    parser.add_argument("--input-md", type=Path, default=Path("docs/final_result.md"))
    parser.add_argument("--runs-dir", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--versioned-runs-dir", type=Path, default=Path("outputs/versioned_runs"))
    parser.add_argument("--paper-compendium", type=Path, default=Path("docs/paper_all_data.md"))
    parser.add_argument("--output", type=Path, default=Path("docs/dashboard/index.html"))
    parser.add_argument("--max-embedded-artifact-bytes", type=int, default=450_000)
    args = parser.parse_args()

    output = generate_static_dashboard(
        args.input_json,
        args.input_md,
        args.output,
        runs_dir=args.runs_dir,
        versioned_runs_dir=args.versioned_runs_dir,
        paper_compendium=args.paper_compendium,
        max_embedded_artifact_bytes=args.max_embedded_artifact_bytes,
    )
    print(json.dumps({"output": str(output)}, indent=2))


def generate_static_dashboard(
    input_json: Path,
    input_md: Path,
    output: Path,
    *,
    runs_dir: Path = Path("outputs/runs"),
    versioned_runs_dir: Path = Path("outputs/versioned_runs"),
    paper_compendium: Path = Path("docs/paper_all_data.md"),
    max_embedded_artifact_bytes: int = 450_000,
) -> Path:
    snapshot = build_static_snapshot(
        input_json=input_json,
        input_md=input_md,
        runs_dir=runs_dir,
        versioned_runs_dir=versioned_runs_dir,
        paper_compendium=paper_compendium,
        max_embedded_artifact_bytes=max_embedded_artifact_bytes,
    )
    html = render_dashboard_html()
    html = _inline_tailadmin_assets(html)
    html = _patch_dashboard_for_static(html, snapshot)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def build_static_snapshot(
    *,
    input_json: Path,
    input_md: Path,
    runs_dir: Path,
    versioned_runs_dir: Path,
    paper_compendium: Path,
    max_embedded_artifact_bytes: int,
) -> dict[str, Any]:
    final_payload = _load_json_file(input_json) or {}
    final_markdown = _read_text(input_md)
    final_result_api = _safe_call(
        lambda: load_final_result(input_md.resolve(), input_json.resolve()),
        {
            "schema_version": 1,
            "exists": bool(final_payload or final_markdown),
            "path": str(input_md),
            "json_path": str(input_json),
            "title": "Consolidated Final Result",
            "markdown": final_markdown,
            "payload": final_payload,
            "size_bytes": input_md.stat().st_size if input_md.exists() else None,
            "modified_at": None,
        },
    )
    paper_compendium_api = _safe_call(lambda: load_paper_compendium(paper_compendium.resolve()), {"exists": False, "markdown": ""})
    ai_model_runs = final_payload.get("versioned_ai_model_results") or _safe_call(lambda: load_ai_model_run_results(versioned_runs_dir), {})
    runs = _versioned_runs_for_dashboard(ai_model_runs, versioned_runs_dir) or _runs_from_final_result(final_payload)

    run_payloads: dict[str, dict[str, Any]] = {}
    artifact_data_urls: dict[str, str] = {}
    artifact_meta: dict[str, dict[str, Any]] = {}

    for run in runs:
        run_id = str(run.get("run_id") or "")
        if not run_id:
            continue
        run_dir = versioned_runs_dir / run_id
        if run_dir.exists():
            payload = _run_payload(run_dir)
            run_payloads[run_id] = payload
            if run_id == str((final_payload.get("primary_run") or {}).get("run_id") or "") or run_id == runs[0].get("run_id"):
                _embed_artifacts(run_id, payload.get("artifacts") or [], artifact_data_urls, artifact_meta, max_embedded_artifact_bytes)
            _embed_image_artifacts(run_id, payload.get("artifacts") or [], artifact_data_urls, artifact_meta, max_embedded_artifact_bytes)
        else:
            run_payloads[run_id] = _placeholder_run_payload(run)

    for versioned_run in ai_model_runs.get("runs") or []:
        run_id = str(versioned_run.get("run_id") or "")
        for artifact in (versioned_run.get("artifacts") or {}).values():
            if isinstance(artifact, dict):
                _embed_artifact(run_id, artifact, artifact_data_urls, artifact_meta, max_embedded_artifact_bytes)

    default_compare = _safe_call(lambda: compare_runs([str(r.get("run_id")) for r in runs[:4] if r.get("run_id")], versioned_runs_dir), {})
    default_dry_run = _safe_call(lambda: dry_run_estimate("configs/bundle_smoke.json"), {})

    return {
        "schema_version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        "mode": "static-dashboard-snapshot",
        "runs": runs,
        "run_payloads": run_payloads,
        "final_result": final_result_api,
        "final_markdown": final_markdown,
        "paper_compendium": paper_compendium_api,
        "paper_markdown": str(paper_compendium_api.get("markdown") or ""),
        "ai_model_runs": ai_model_runs,
        "compare": default_compare,
        "dry_run": default_dry_run,
        "artifact_data_urls": artifact_data_urls,
        "artifact_meta": artifact_meta,
        "source_files": {
            "final_result_json": str(input_json),
            "final_result_markdown": str(input_md),
            "paper_compendium": str(paper_compendium),
            "runs_dir": str(runs_dir),
            "versioned_runs_dir": str(versioned_runs_dir),
        },
    }


def _run_payload(run_dir: Path) -> dict[str, Any]:
    return {
        "progress": _safe_call(lambda: load_run_progress(run_dir), {"run_id": run_dir.name, "run_dir": str(run_dir)}),
        "events": _safe_call(lambda: load_run_events(run_dir, tail=60), []),
        "metrics": _safe_call(lambda: load_run_metrics(run_dir)[-500:], []),
        "artifacts": _safe_call(lambda: load_run_artifacts(run_dir), []),
        "failure": _safe_call(lambda: load_failure(run_dir) or {}, {}),
        "diagnostics": {},
        "storage": _safe_call(lambda: load_run_storage(run_dir), {}),
    }


def _placeholder_run_payload(run: dict[str, Any]) -> dict[str, Any]:
    progress = {
        "schema_version": 1,
        "run_id": run.get("run_id"),
        "display_name": run.get("display_name") or run.get("run_id"),
        "run_dir": run.get("run_dir"),
        "classification": run.get("status") or "unknown",
        "status": run.get("status") or "unknown",
        "current_step": run.get("current_step"),
        "progress_fraction": run.get("progress_fraction") or 0,
        "display_progress_fraction": run.get("display_progress_fraction") or run.get("progress_fraction") or 0,
        "steps": [],
        "step_order": [],
        "config": {},
    }
    storage = {
        "schema_version": 1,
        "run_id": run.get("run_id"),
        "display_name": run.get("display_name") or run.get("run_id"),
        "run_dir": run.get("run_dir"),
        "status": run.get("status") or "unknown",
        "artifact_count": run.get("artifact_count") or 0,
        "categories": run.get("categories") or {},
        "important_files": [],
    }
    return {
        "progress": progress,
        "events": [],
        "metrics": [],
        "artifacts": [],
        "failure": {},
        "diagnostics": {},
        "storage": storage,
    }


def _embed_artifacts(
    run_id: str,
    artifacts: list[dict[str, Any]],
    artifact_data_urls: dict[str, str],
    artifact_meta: dict[str, dict[str, Any]],
    max_bytes: int,
) -> None:
    for artifact in artifacts:
        _embed_artifact(run_id, artifact, artifact_data_urls, artifact_meta, max_bytes)


def _embed_image_artifacts(
    run_id: str,
    artifacts: list[dict[str, Any]],
    artifact_data_urls: dict[str, str],
    artifact_meta: dict[str, dict[str, Any]],
    max_bytes: int,
) -> None:
    for artifact in artifacts:
        if _is_image_artifact(artifact):
            _embed_artifact(run_id, artifact, artifact_data_urls, artifact_meta, max_bytes)


def _embed_artifact(
    run_id: str,
    artifact: dict[str, Any],
    artifact_data_urls: dict[str, str],
    artifact_meta: dict[str, dict[str, Any]],
    max_bytes: int,
) -> None:
    path_value = artifact.get("path")
    if not path_value:
        return
    key = _artifact_key(run_id, str(path_value))
    path = Path(str(path_value))
    if not path.is_absolute():
        path = path.resolve()
    if not path.exists() or not path.is_file():
        artifact_meta[key] = {"embedded": False, "reason": "missing", "path": str(path_value)}
        return
    size = path.stat().st_size
    if size > max_bytes:
        artifact_meta[key] = {"embedded": False, "reason": "too_large", "path": str(path_value), "size_bytes": size}
        return
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    artifact_data_urls[key] = f"data:{mime};base64,{encoded}"
    artifact_meta[key] = {"embedded": True, "path": str(path_value), "size_bytes": size, "mime": mime}


def _artifact_key(run_id: str, path: str) -> str:
    return f"{run_id}\u001f{path}"


def _is_image_artifact(artifact: dict[str, Any]) -> bool:
    kind = str(artifact.get("kind") or "").lower()
    name = str(artifact.get("name") or artifact.get("path") or "").lower()
    return kind in {"png", "jpg", "jpeg", "svg"} or name.endswith((".png", ".jpg", ".jpeg", ".svg"))


def _inline_tailadmin_assets(html: str) -> str:
    theme_css = _read_text(DEFAULT_THEME_CSS)
    tabler_css = _inline_tabler_css(DEFAULT_TABLER_CSS, DEFAULT_TABLER_WOFF2)
    html = html.replace(
        '  <link rel="stylesheet" href="/tailadmin-assets/fonts/icons/tabler-icons/tabler-icons.css">\n',
        f"  <style id=\"static-tabler-icons\">\n{tabler_css}\n  </style>\n",
    )
    html = html.replace(
        '  <link rel="stylesheet" href="/tailadmin-assets/css/theme.css">\n',
        f"  <style id=\"static-tailadmin-theme\">\n{theme_css}\n  </style>\n",
    )
    html = html.replace('<a href="/" class="text-nowrap logo-img flex items-center gap-3">', '<a href="./" class="text-nowrap logo-img flex items-center gap-3">')
    return html


def _inline_tabler_css(css_path: Path, font_path: Path) -> str:
    css = _read_text(css_path)
    marker = ".ti {"
    rest = css[css.find(marker) :] if marker in css else css
    if font_path.exists():
        encoded_font = base64.b64encode(font_path.read_bytes()).decode("ascii")
        font_face = (
            '@font-face { font-family: "tabler-icons"; font-style: normal; font-weight: 400; '
            f'src: url("data:font/woff2;base64,{encoded_font}") format("woff2"); }}\n'
        )
        return font_face + rest
    return css


def _patch_dashboard_for_static(html: str, snapshot: dict[str, Any]) -> str:
    embedded = json.dumps(snapshot, ensure_ascii=True, sort_keys=True).replace("</", "<\\/")
    shim = STATIC_SHIM
    fragments = _static_initial_fragments(snapshot)
    html = html.replace("</head>", "  <style>.staticNotice{display:none}</style>\n</head>")
    html = html.replace('<span class="hide-menu shrink-0">Runs</span>', '<span class="hide-menu shrink-0">Versioned Runs</span>', 1)
    html = html.replace('<p id="title" class="text-link/80 dark:text-white/80 mt-1">Select a run</p>', '<p id="title" class="text-link/80 dark:text-white/80 mt-1">Versioned run results</p>')
    html = html.replace('class="sidebar-link dark-sidebar-link active activemenu" data-tab="runs"', 'class="sidebar-link dark-sidebar-link" data-tab="runs"', 1)
    html = html.replace('class="sidebar-link dark-sidebar-link" data-tab="final"', 'class="sidebar-link dark-sidebar-link active activemenu" data-tab="final"', 1)
    html = html.replace('<div class="panel active dashboard-panel" id="panel-runs">', '<div class="panel dashboard-panel" id="panel-runs">')
    html = html.replace('<div class="panel card dashboard-panel" id="panel-final">', '<div class="panel card dashboard-panel active" id="panel-final">')
    html = html.replace("Selected Run Results", "Versioned Run Artifact Details")
    html = html.replace("Versioned run evidence first, selected-run details second.", "All versioned run evidence is shown first; artifact details are read-only.")
    html = html.replace(
        '<div id="alert" class="banner"></div>',
        '<div id="alert" class="banner"></div>\n'
        f'{fragments["headline"]}',
    )
    html = html.replace(
        '<div id="dashboardFinalResult"><span class="muted">Loading consolidated final result...</span></div>',
        f'<div id="dashboardFinalResult">{fragments["final_summary"]}</div>',
    )
    html = html.replace(
        '<div id="finalResult"><span class="muted">Open this tab to load the consolidated final result.</span></div>',
        f'<div id="finalResult">{fragments["final_result"]}</div>',
    )
    html = html.replace(
        '<div id="aiModelRuns"><span class="muted">Open this tab to load versioned run results.</span></div>',
        f'<div id="aiModelRuns">{fragments["ai_model_runs"]}</div>',
    )
    html = html.replace(
        '<div id="paperCompendium"><span class="muted">Open this tab to load the paper data compendium.</span></div>',
        f'<div id="paperCompendium">{fragments["paper_compendium"]}</div>',
    )
    html = html.replace("<script>\nlet currentRun = null;", f'<script id="static-dashboard-data" type="application/json">{embedded}</script>\n<script>\n{shim}\nlet currentRun = null;')
    html = html.replace("|| 'runs';", "|| 'final';")
    html = re.sub(
        r"async function getJSON\(url\) \{ const res = await fetch\(url\); if \(!res\.ok\) throw new Error\(url \+ ' ' \+ res\.status\); return await res\.json\(\); \}",
        "async function getJSON(url) { return await staticGetJSON(url); }",
        html,
    )
    html = re.sub(
        r"async function postJSON\(url, payload\) \{.*?return data;\n\}",
        "async function postJSON(url, payload) { return await staticPostJSON(url, payload); }",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"function artifactUrl\(run, artifact\) \{\n  return `/api/artifact\?run=\$\{encodeURIComponent\(run\)\}&path=\$\{encodeURIComponent\(artifact\.path\)\}`;\n\}",
        "function artifactUrl(run, artifact) {\n  return staticArtifactUrl(run, artifact);\n}",
        html,
    )
    html = html.replace("setInterval(() => refresh().catch(showUiError), 3000);", "setInterval(() => refresh().catch(showUiError), 15000);")
    return html


def _static_initial_fragments(snapshot: dict[str, Any]) -> dict[str, str]:
    final_result = snapshot.get("final_result") or {}
    payload = final_result.get("payload") or {}
    primary = payload.get("primary_run") or {}
    ai_model_runs = snapshot.get("ai_model_runs") or payload.get("versioned_ai_model_results") or {}
    paper = snapshot.get("paper_compendium") or {}
    return {
        "headline": _static_headline_html(payload, ai_model_runs),
        "final_summary": _static_final_summary_html(final_result),
        "final_result": _static_final_result_html(final_result),
        "ai_model_runs": _static_ai_model_runs_html(ai_model_runs, snapshot),
        "paper_compendium": _static_paper_compendium_html(paper),
    }


def _static_headline_html(payload: dict[str, Any], ai_model_runs: dict[str, Any]) -> str:
    primary = payload.get("primary_run") or {}
    conclusion = ai_model_runs.get("conclusion") or {}
    evidence = conclusion.get("selector_evidence") or {}
    realism = conclusion.get("realism_evidence") or {}
    return f"""
          <div class="card mb-4" id="staticFinalConclusion"><div class="card-body">
            <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
              <div>
                <h5 class="card-title mb-1">Static Final Dashboard Snapshot</h5>
                <p class="text-sm text-bodytext">Final conclusions are embedded in this HTML for GitHub Pages sharing.</p>
              </div>
              <span class="badge">read-only snapshot</span>
            </div>
            <div class="guardrail">This is a research-simulator result. Reward, success, and safety are simulator outcomes, not clinical endpoints.</div>
            <div class="resultGrid">
              <div class="resultBlock"><h6>Final Conclusion</h6><p><b>{_h(conclusion.get("headline") or "Consolidated final result is available.")}</b></p><p>The manuscript-facing primary run is <code>{_h(primary.get("run_id"))}</code>, selected from {_h(payload.get("run_count"))} paper-ready runs because it has the largest completed evaluation scale.</p></div>
              <div class="resultBlock"><h6>Selector Evidence</h6><table class="miniTable"><tbody><tr><td>Runs beating ACLS</td><td>{_h(_ratio(evidence.get("selector_beats_acls_count"), evidence.get("selector_comparable_run_count")))}</td></tr><tr><td>Selector reward avg</td><td>{_fmt(evidence.get("selector_reward"))}</td></tr><tr><td>ACLS reward avg</td><td>{_fmt(evidence.get("acls_reward"))}</td></tr><tr><td>Reward delta vs ACLS</td><td>{_fmt(evidence.get("reward_delta_vs_acls"))}</td></tr><tr><td>Selector oracle gap avg</td><td>{_fmt(evidence.get("selector_oracle_gap"))}</td></tr></tbody></table></div>
              <div class="resultBlock"><h6>Realism Evidence</h6><table class="miniTable"><tbody><tr><td>Latest realism run</td><td><code>{_h(realism.get("latest_run_id"))}</code></td></tr><tr><td>Latest mean SMD</td><td>{_fmt(realism.get("latest_mean_smd_abs"))}</td></tr><tr><td>Latest mean KS</td><td>{_fmt(realism.get("latest_mean_ks_statistic"))}</td></tr><tr><td>Worst feature</td><td>{_h(realism.get("latest_worst_group"))} / {_h(realism.get("latest_worst_feature"))}</td></tr></tbody></table></div>
            </div>
          </div></div>
"""


def _static_final_summary_html(final_result: dict[str, Any]) -> str:
    if not final_result.get("exists"):
        return '<div class="resultBlock"><h6>Consolidated Final Result</h6><p class="missing">docs/final_result.md is not available.</p></div>'
    payload = final_result.get("payload") or {}
    primary = payload.get("primary_run") or {}
    policies = primary.get("policy_metrics") or {}
    oracle = policies.get("oracle") or {}
    acls = policies.get("acls_rule") or {}
    calibration = primary.get("calibration") or {}
    cards = [
        ("Primary run", primary.get("run_id")),
        ("Runs considered", payload.get("run_count")),
        ("Completed runs", payload.get("completed_run_count")),
        ("Oracle reward", _fmt(oracle.get("mean_reward"))),
        ("ACLS reward", _fmt(acls.get("mean_reward"))),
        ("Calibration pass", _ratio(calibration.get("passed"), calibration.get("checks"))),
    ]
    card_html = _ta_cards(cards)
    winner_rows = "".join(_scenario_row(row) for row in primary.get("scenario_winners") or [])
    return f"""<div class="resultStack">
    <div class="ta-grid">{card_html}</div>
    <div class="resultBlock"><div class="previewHead"><div><b>Scenario-Level Final Actions</b><br><span class="previewMeta">{_h(final_result.get("modified_at"))}</span></div><div class="actions"><a class="plain" target="_blank" href="../final_result.md">Open Markdown</a><a class="plain" href="#paper">Paper Data</a></div></div><div class="csvWrap"><table><thead><tr><th>Scenario</th><th>Final action</th><th>Reward</th><th>Success</th><th>Time</th><th>Safety</th></tr></thead><tbody>{winner_rows}</tbody></table></div></div>
  </div>"""


def _static_final_result_html(final_result: dict[str, Any]) -> str:
    if not final_result.get("exists"):
        return '<div class="resultBlock"><h6>Consolidated Final Result</h6><p class="missing">docs/final_result.md is not available.</p></div>'
    payload = final_result.get("payload") or {}
    primary = payload.get("primary_run") or {}
    markdown_preview = _markdown_preview(final_result.get("markdown") or "")
    return f"""<div class="resultStack">
    <div class="resultGrid">
      <div class="resultBlock paperMeta"><h6>{_h(final_result.get("title") or "Consolidated Final Result")}</h6><table class="miniTable"><tbody><tr><td>Primary run</td><td><code>{_h(primary.get("run_id"))}</code></td></tr><tr><td>Runs considered</td><td>{_h(payload.get("run_count"))}</td></tr><tr><td>Completed runs</td><td>{_h(payload.get("completed_run_count"))}</td></tr><tr><td>Patients/scenario</td><td>{_h(primary.get("patients_per_scenario"))}</td></tr><tr><td>Horizon</td><td>{_h(primary.get("horizon_s"))} s</td></tr><tr><td>File</td><td><code>{_h(final_result.get("path"))}</code></td></tr></tbody></table><div class="actions mt-3"><a class="plain" target="_blank" href="../final_result.md">Open Markdown</a></div></div>
      <div class="resultBlock"><h6>Selection Rule</h6><p>{_h(payload.get("selection_rule") or "No selection rule recorded.")}</p><p class="muted">One-patient mutation runs are kept as checks, not as the manuscript primary result.</p></div>
    </div>
    <div class="resultBlock"><div class="previewHead"><div><b>Final Result Markdown</b><br><span class="previewMeta">{_h(final_result.get("modified_at"))}</span></div><a class="plain" target="_blank" href="../final_result.md">Open</a></div>{markdown_preview}</div>
  </div>"""


def _static_ai_model_runs_html(data: dict[str, Any], snapshot: dict[str, Any]) -> str:
    if not data or not data.get("runs"):
        return '<div class="resultBlock"><h6>Versioned Run Results Across 4 Runs</h6><p class="muted">No versioned run payload is available.</p></div>'
    aggregate = data.get("aggregate") or {}
    realism_aggregate = data.get("realism_aggregate") or {}
    conclusion = data.get("conclusion") or {}
    selector_avg = aggregate.get("selector_model_average") or {}
    requested = data.get("requested_run_ids") or []
    attention = aggregate.get("selector_model_attention_runs") or []
    cards = _ta_cards(
        [
            ("Versioned runs", f"{data.get('run_count') or 0}/{len(requested) or len(data.get('runs') or [])}"),
            ("Completed", data.get("completed_run_count") or 0),
            ("Selector runs", aggregate.get("selector_model_run_count") or 0),
            ("Selector success", _fmt(selector_avg.get("success_rate"))),
            ("Realism runs", realism_aggregate.get("realism_run_count") or 0),
            ("Mean SMD / KS", f"{_fmt(realism_aggregate.get('mean_smd_abs'))} / {_fmt(realism_aggregate.get('mean_ks_statistic'))}"),
            ("Worst mismatch", f"{realism_aggregate.get('worst_run_id')}: {realism_aggregate.get('worst_feature')}" if realism_aggregate.get("worst_run_id") else "none"),
            ("Attention runs", ", ".join(attention) if attention else "none"),
        ]
    )
    run_rows = "".join(_versioned_run_row(run) for run in data.get("runs") or [])
    scenario_rows = "".join(_scenario_consensus_row(row) for row in data.get("scenario_consensus") or [])
    image_gallery = _static_versioned_image_gallery_html(data, snapshot)
    return f"""<div class="resultStack">
    {_static_versioned_conclusion_html(conclusion)}
    <div class="ta-grid">{cards}</div>
    {image_gallery}
    <div class="resultBlock"><h6>Versioned Run Summary</h6><div class="csvWrap"><table><thead><tr><th>Run</th><th>Experiment</th><th>Patients</th><th>Horizon / obs</th><th>Selector reward</th><th>Selector gap</th><th>Selector success</th><th>ACLS reward</th><th>Oracle reward</th><th>Mean SMD</th><th>Mean KS</th><th>Worst feature</th></tr></thead><tbody>{run_rows}</tbody></table></div></div>
    <div class="resultBlock"><h6>Scenario Winners From Selector Runs</h6><div class="csvWrap"><table><thead><tr><th>Scenario</th><th>Consensus action</th><th>Agreement</th><th>Avg reward</th><th>Avg success</th><th>Per-run action</th></tr></thead><tbody>{scenario_rows or '<tr><td colspan="6"><span class="muted">No selector winner tables are present in these versioned runs.</span></td></tr>'}</tbody></table></div></div>
  </div>"""


def _static_versioned_conclusion_html(conclusion: dict[str, Any]) -> str:
    if not conclusion or not conclusion.get("headline"):
        return ""
    selector = conclusion.get("selector_evidence") or {}
    realism = conclusion.get("realism_evidence") or {}
    selector_run_ids = conclusion.get("selector_run_ids") or ([conclusion.get("selector_run_id")] if conclusion.get("selector_run_id") else [])
    return f"""<div class="resultBlock"><h6>AI Model Analysis Conclusion</h6><p><b>{_h(conclusion.get("headline"))}</b></p>
    <div class="resultGrid">
      <div><h6>Selector Evidence</h6><table class="miniTable"><tbody><tr><td>Selector runs</td><td><code>{_h(", ".join(selector_run_ids))}</code></td></tr><tr><td>Runs beating ACLS</td><td>{_h(_ratio(selector.get("selector_beats_acls_count"), selector.get("selector_comparable_run_count")))}</td></tr><tr><td>Selector reward avg</td><td>{_fmt(selector.get("selector_reward"))}</td></tr><tr><td>ACLS reward avg</td><td>{_fmt(selector.get("acls_reward"))}</td></tr><tr><td>Reward delta vs ACLS</td><td>{_fmt(selector.get("reward_delta_vs_acls"))}</td></tr><tr><td>Selector success avg</td><td>{_fmt(selector.get("selector_success_rate"))}</td></tr><tr><td>ACLS success avg</td><td>{_fmt(selector.get("acls_success_rate"))}</td></tr><tr><td>Selector oracle gap avg</td><td>{_fmt(selector.get("selector_oracle_gap"))}</td></tr><tr><td>Oracle reward avg</td><td>{_fmt(selector.get("oracle_reward"))}</td></tr></tbody></table></div>
      <div><h6>Realism Evidence</h6><table class="miniTable"><tbody><tr><td>Latest realism run</td><td><code>{_h(realism.get("latest_run_id"))}</code></td></tr><tr><td>Mean SMD change</td><td>{_fmt(realism.get("mean_smd_abs_change"))}</td></tr><tr><td>Mean KS change</td><td>{_fmt(realism.get("mean_ks_statistic_change"))}</td></tr><tr><td>Latest worst feature</td><td>{_h(realism.get("latest_worst_group"))} / {_h(realism.get("latest_worst_feature"))}</td></tr><tr><td>Latest worst SMD</td><td>{_fmt(realism.get("latest_worst_smd_abs"))}</td></tr><tr><td>Rows</td><td>{_h(realism.get("latest_real_rows"))} real / {_h(realism.get("latest_synthetic_rows"))} synthetic</td></tr></tbody></table></div>
    </div>
    <div class="resultGrid mt-3"><div><h6>Claims To Use</h6>{_bullet_list(conclusion.get("claims") or [])}</div><div><h6>Limits</h6>{_bullet_list(conclusion.get("limitations") or [])}</div><div><h6>Next Analysis</h6>{_bullet_list(conclusion.get("next_steps") or [])}</div></div></div>"""


def _static_versioned_image_gallery_html(data: dict[str, Any], snapshot: dict[str, Any]) -> str:
    run_payloads = snapshot.get("run_payloads") or {}
    data_urls = snapshot.get("artifact_data_urls") or {}
    groups: list[str] = []
    total_images = 0
    for run in data.get("runs") or []:
        run_id = str(run.get("run_id") or "")
        artifacts = (run_payloads.get(run_id) or {}).get("artifacts") or []
        images = [artifact for artifact in artifacts if _is_image_artifact(artifact)]
        if not images:
            continue
        total_images += len(images)
        cards = []
        for artifact in images:
            key = _artifact_key(run_id, str(artifact.get("path") or ""))
            src = data_urls.get(key)
            name = artifact.get("name") or Path(str(artifact.get("path") or "")).name
            relative = artifact.get("relative_path") or artifact.get("path") or ""
            if src:
                media = f'<img src="{_h(src)}" loading="lazy" alt="{_h(name)}">'
            else:
                media = '<div class="missing" style="padding:16px">image not embedded</div>'
            cards.append(
                f"""<div class="inlineFigure">
                  {media}
                  <span class="caption"><b>{_h(name)}</b><br><span class="muted">{_h(relative)}</span></span>
                </div>"""
            )
        groups.append(
            f"""<div class="resultBlock">
              <div class="previewHead"><div><b>{_h(run_id)}</b><br><span class="previewMeta">{len(images)} image artifacts</span></div><span class="badge">versioned</span></div>
              <div class="figureGrid">{''.join(cards)}</div>
            </div>"""
        )
    if not groups:
        return '<div class="resultBlock"><h6>Versioned Image Gallery</h6><p class="muted">No versioned image artifacts are embedded in this static snapshot.</p></div>'
    return f"""<div class="resultBlock">
      <div class="previewHead"><div><h6>Versioned Image Gallery</h6><span class="previewMeta">{total_images} image artifacts across versioned runs</span></div><span class="badge">embedded images</span></div>
    </div>
    {''.join(groups)}"""


def _static_paper_compendium_html(data: dict[str, Any]) -> str:
    if not data or not data.get("exists"):
        return '<div class="resultBlock"><h6>Paper Data Compendium</h6><p class="missing">docs/paper_all_data.md is not available.</p></div>'
    sections = data.get("sections") or []
    rows = "".join(f"<tr><td>{_h(section.get('title'))}</td><td><code>{_h(section.get('path'))}</code></td></tr>" for section in sections)
    section_rows = f'<div class="csvWrap paperSections"><table><thead><tr><th>Section</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<p class="muted">No section index was found in the compendium.</p>'
    return f"""<div class="resultStack">
    <div class="resultGrid">
      <div class="resultBlock paperMeta"><h6>{_h(data.get("title") or "Paper Data Compendium")}</h6><table class="miniTable"><tbody><tr><td>Run ID</td><td><code>{_h(data.get("run_id"))}</code></td></tr><tr><td>Source</td><td><code>{_h(data.get("source_dir"))}</code></td></tr><tr><td>File</td><td><code>{_h(data.get("path"))}</code></td></tr><tr><td>Updated</td><td>{_h(data.get("modified_at"))}</td></tr><tr><td>Size</td><td>{_h(data.get("size_bytes"))} B</td></tr></tbody></table><div class="actions mt-3"><a class="plain" target="_blank" href="../paper_all_data.md">Open Markdown</a></div></div>
      <div class="resultBlock"><h6>Included Sections</h6>{section_rows}</div>
    </div>
    <div class="resultBlock"><div class="previewHead"><div><b>Compiled Manuscript Notes</b><br><span class="previewMeta">{len(sections)} sections from the paper artifact set</span></div><a class="plain" target="_blank" href="../paper_all_data.md">Open</a></div>{_markdown_preview(data.get("markdown") or "")}</div>
  </div>"""


def _ta_cards(items: list[tuple[str, Any]]) -> str:
    styles = [
        ("bg-lightprimary", "text-primary"),
        ("bg-lightsuccess", "text-success"),
        ("bg-lightinfo", "text-info"),
        ("bg-lightwarning", "text-warning"),
        ("bg-lighterror", "text-error"),
        ("bg-lightinfo", "text-info"),
    ]
    out = []
    for index, (key, value) in enumerate(items):
        bg, text = styles[index % len(styles)]
        out.append(f'<div class="card mb-0 shadow-none {bg} w-full"><div class="card-body"><p class="font-semibold {text} mb-1">{_h(key)}</p><h5 class="text-lg font-semibold {text} mb-0">{_h(value)}</h5></div></div>')
    return "".join(out)


def _scenario_row(row: dict[str, Any]) -> str:
    return f"<tr><td>{_h(row.get('scenario'))}</td><td><code>{_h(row.get('best_algorithm') or row.get('final_action'))}</code></td><td>{_fmt(row.get('mean_reward'))}</td><td>{_fmt(row.get('success_rate'))}</td><td>{_fmt(row.get('mean_time_s'))}</td><td>{_fmt(row.get('mean_safety_violations'))}</td></tr>"


def _versioned_run_row(run: dict[str, Any]) -> str:
    cfg = run.get("config") or {}
    selector = run.get("selector_model") or {}
    acls = run.get("acls_rule") or {}
    oracle = run.get("oracle") or {}
    realism = run.get("realism_comparison") or {}
    if not run.get("exists", True):
        return f"<tr class=\"missing\"><td><code>{_h(run.get('run_id'))}</code></td><td colspan=\"11\">missing run directory</td></tr>"
    return f"<tr><td><code>{_h(run.get('run_id'))}</code><br><span class=\"muted\">{_h(run.get('status'))}</span></td><td>{_h(run.get('experiment') or cfg.get('preset'))}</td><td>{_h(cfg.get('patients_per_scenario'))}</td><td>{_h(cfg.get('horizon_s'))}</td><td>{_fmt(selector.get('mean_reward'))}</td><td>{_fmt(selector.get('oracle_gap'))}</td><td>{_fmt(selector.get('success_rate'))}</td><td>{_fmt(acls.get('mean_reward'))}</td><td>{_fmt(oracle.get('mean_reward'))}</td><td>{_fmt(realism.get('mean_smd_abs'))}</td><td>{_fmt(realism.get('mean_ks_statistic'))}</td><td>{_h(realism.get('max_smd_feature'))}</td></tr>"


def _scenario_consensus_row(row: dict[str, Any]) -> str:
    per_run = " | ".join(f"{item.get('run_id')}: {item.get('algorithm')}" for item in row.get("per_run") or [])
    return f"<tr><td>{_h(row.get('scenario'))}</td><td><code>{_h(row.get('consensus_algorithm'))}</code></td><td>{_h(row.get('agreement'))}</td><td>{_fmt(row.get('mean_reward'))}</td><td>{_fmt(row.get('success_rate'))}</td><td><span class=\"muted\">{_h(per_run)}</span></td></tr>"


def _markdown_preview(text: str) -> str:
    # Keep this intentionally simple; the live dashboard JS will enhance it after load.
    return f'<div class="mdPreview"><pre>{_h(text[:120_000])}</pre></div>'


def _bullet_list(items: list[Any]) -> str:
    return "".join(f'<p class="mdBullet"><span class="muted">- </span>{_h(item)}</p>' for item in items)


def _ratio(left: Any, right: Any) -> str:
    if left is None or right is None or right == "":
        return ""
    return f"{left}/{right}"


def _fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:.{digits}f}"


def _h(value: Any) -> str:
    return html_lib.escape("" if value is None else str(value), quote=True)


STATIC_SHIM = r"""
window.__STATIC_DASHBOARD__ = JSON.parse(document.getElementById('static-dashboard-data').textContent);
window.__STATIC_NATIVE_FETCH__ = window.fetch.bind(window);
function staticClone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}
function staticPathParts(url) {
  const parsed = new URL(url, window.location.href);
  return { parsed, path: parsed.pathname.replace(/\/$/, '') || '/' };
}
async function staticGetJSON(url) {
  const { parsed, path } = staticPathParts(url);
  const data = window.__STATIC_DASHBOARD__;
  if (path === '/api/runs') return staticClone(data.runs || []);
  if (path === '/api/compare') return staticClone(data.compare || {});
  if (path === '/api/dry-run') return staticClone(data.dry_run || {});
  if (path === '/api/ai-model-runs') return staticClone(data.ai_model_runs || {});
  if (path === '/api/final-result') return staticClone(data.final_result || {});
  if (path === '/api/paper-compendium') return staticClone(data.paper_compendium || {});
  if (path.startsWith('/api/runs/')) {
    const parts = path.split('/').map(decodeURIComponent);
    const runId = parts[3];
    const suffix = parts[4] || 'progress';
    const payload = (data.run_payloads || {})[runId] || {};
    if (suffix === 'progress') return staticClone(payload.progress || {});
    if (suffix === 'events') return staticClone(payload.events || []);
    if (suffix === 'metrics') return staticClone(payload.metrics || []);
    if (suffix === 'artifacts') return staticClone(payload.artifacts || []);
    if (suffix === 'failure') return staticClone(payload.failure || {});
    if (suffix === 'diagnostics') return staticClone(payload.diagnostics || {});
    if (suffix === 'storage') return staticClone(payload.storage || {});
  }
  throw new Error(url + ' static 404');
}
async function staticPostJSON(url, payload) {
  return {
    ok: false,
    static_snapshot: true,
    message: 'This GitHub Pages dashboard is a read-only static snapshot.',
    requested_url: url,
    payload: payload || {}
  };
}
function staticArtifactKey(run, artifactOrPath) {
  const path = typeof artifactOrPath === 'string' ? artifactOrPath : (artifactOrPath && artifactOrPath.path);
  return `${run}\u001f${path || ''}`;
}
function staticArtifactUrl(run, artifact) {
  const data = window.__STATIC_DASHBOARD__;
  const key = staticArtifactKey(run, artifact);
  const embedded = (data.artifact_data_urls || {})[key];
  if (embedded) return embedded;
  const meta = (data.artifact_meta || {})[key] || {};
  const message = meta.reason === 'too_large'
    ? `Artifact omitted from static snapshot because it is too large (${meta.size_bytes || 0} bytes).`
    : 'Artifact is not embedded in this static snapshot.';
  return `data:text/plain;charset=utf-8,${encodeURIComponent(message)}`;
}
window.fetch = async function staticFetch(url, options) {
  if (String(url).startsWith('data:')) return window.__STATIC_NATIVE_FETCH__(url, options);
  const method = String((options && options.method) || 'GET').toUpperCase();
  const { parsed, path } = staticPathParts(String(url));
  const data = window.__STATIC_DASHBOARD__;
  if (method !== 'GET') {
    return new Response(JSON.stringify(await staticPostJSON(String(url), {})), {status: 200, headers: {'Content-Type': 'application/json'}});
  }
  if (path === '/api/final-result/raw') {
    return new Response(data.final_markdown || '', {status: 200, headers: {'Content-Type': 'text/markdown; charset=utf-8'}});
  }
  if (path === '/api/paper-compendium/raw') {
    return new Response(data.paper_markdown || '', {status: 200, headers: {'Content-Type': 'text/markdown; charset=utf-8'}});
  }
  if (path === '/api/artifact') {
    const runId = parsed.searchParams.get('run') || '';
    const artifactPath = parsed.searchParams.get('path') || '';
    const artifactUrl = (data.artifact_data_urls || {})[staticArtifactKey(runId, artifactPath)];
    if (artifactUrl) return window.__STATIC_NATIVE_FETCH__(artifactUrl);
    return new Response('Artifact is not embedded in this static snapshot.', {status: 200, headers: {'Content-Type': 'text/plain; charset=utf-8'}});
  }
  try {
    const payload = await staticGetJSON(String(url));
    return new Response(JSON.stringify(payload), {status: 200, headers: {'Content-Type': 'application/json; charset=utf-8'}});
  } catch (err) {
    return new Response(JSON.stringify({error: String(err && err.message || err)}), {status: 404, headers: {'Content-Type': 'application/json; charset=utf-8'}});
  }
};
"""


def _safe_call(factory, default):
    try:
        return factory()
    except Exception:
        return default


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _runs_from_final_result(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run in payload.get("runs") or []:
        run_id = str(run.get("run_id") or "")
        if not run_id:
            continue
        rows.append(
            {
                "run_id": run_id,
                "display_name": run_id,
                "run_dir": run.get("run_dir") or "",
                "status": run.get("status") or "unknown",
                "current_step": None,
                "progress_fraction": 1.0 if run.get("status") == "completed" else 0.0,
                "display_progress_fraction": 1.0 if run.get("status") == "completed" else 0.0,
                "artifact_count": 0,
                "categories": {"Final Results": 1},
            }
        )
    return rows


def _versioned_runs_for_dashboard(ai_model_runs: dict[str, Any], versioned_runs_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in ai_model_runs.get("runs") or []:
        run_id = str(run.get("run_id") or "")
        if not run_id:
            continue
        run_dir = versioned_runs_dir / run_id
        artifact_count = 0
        categories: dict[str, int] = {}
        if run_dir.exists():
            artifacts = _safe_call(lambda: load_run_artifacts(run_dir), [])
            artifact_count = len(artifacts)
            categories = _simple_artifact_categories(artifacts)
        else:
            artifact_map = run.get("artifacts") or {}
            artifact_count = sum(1 for artifact in artifact_map.values() if isinstance(artifact, dict) and artifact.get("exists"))
            categories = {"Final Results": artifact_count} if artifact_count else {}
        progress_fraction = 1.0 if run.get("status") in {"completed", "ok"} else 0.0
        rows.append(
            {
                "run_id": run_id,
                "display_name": run.get("display_name") or run_id,
                "run_dir": str(run_dir),
                "status": run.get("status") or "unknown",
                "current_step": "versioned_result",
                "progress_fraction": progress_fraction,
                "display_progress_fraction": progress_fraction,
                "heartbeat_at": run.get("updated_at"),
                "updated_at": run.get("updated_at"),
                "artifact_count": artifact_count,
                "categories": categories or {"Final Results": 1},
            }
        )
    return rows


def _simple_artifact_categories(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    categories: dict[str, int] = {}
    for artifact in artifacts:
        category = str(artifact.get("category") or "Other")
        categories[category] = categories.get(category, 0) + 1
    return dict(sorted(categories.items()))


if __name__ == "__main__":
    main()
