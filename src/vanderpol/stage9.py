"""Stage 9: manuscript-ready artifacts from experiment bundle manifests."""

from __future__ import annotations

import csv
import html
import json
import os
from pathlib import Path
from typing import Any


POLICY_ORDER = [
    "selector_linucb",
    "conservative_selector",
    "acls_rule",
    "oracle",
    "always_synchronized_cardioversion",
    "always_unsynchronized_defibrillation",
    "always_atp",
    "always_resonant_drift",
    "always_adaptive",
]

POLICY_LABELS = {
    "selector_linucb": "Selector LinUCB",
    "conservative_selector": "Conservative selector",
    "acls_rule": "ACLS-rule baseline",
    "oracle": "Oracle",
    "always_synchronized_cardioversion": "Always synchronized cardioversion",
    "always_unsynchronized_defibrillation": "Always unsynchronized defibrillation",
    "always_atp": "Always ATP",
    "always_resonant_drift": "Always resonant drift",
    "always_adaptive": "Always adaptive low-energy pacing",
}

METRIC_FIELDS = [
    "mean_reward",
    "oracle_gap",
    "success_rate",
    "mean_energy",
    "mean_time_s",
    "mean_safety_violations",
]


def generate_paper_artifacts(
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
    citations_path: str | Path = "configs/citations.json",
    limitations_path: str | Path = "configs/limitations.json",
) -> dict[str, Any]:
    """Generate manuscript-facing CSV/Markdown artifacts from a Stage 8 run."""

    manifest_path = Path(manifest_path)
    manifest = _read_json(manifest_path)
    run_dir = Path(manifest.get("run_dir", manifest_path.parent))
    if output_dir is None:
        output_dir = run_dir / "paper_artifacts"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, str] = {}
    warnings: list[str] = []

    selector = _read_json_if_exists(run_dir / "selector_report.json")
    if selector:
        rows = selector_policy_rows(selector)
        artifacts.update(
            _write_table_pair(
                rows,
                output_dir / "paper_selector_table.csv",
                output_dir / "paper_selector_table.md",
                "Selector Policy Summary",
            )
        )
    else:
        warnings.append("selector_report.json not found")

    calibration = _read_json_if_exists(run_dir / "calibration_report.json")
    if calibration:
        rows = calibration_rows(calibration)
        artifacts.update(
            _write_table_pair(
                rows,
                output_dir / "paper_calibration_table.csv",
                output_dir / "paper_calibration_table.md",
                "Calibration Checks",
            )
        )
    else:
        warnings.append("calibration_report.json not found")

    matrix_path = run_dir / "figures" / "phase2_matrix_summary.csv"
    if matrix_path.exists():
        matrix_rows = _read_csv(matrix_path)
        artifacts.update(
            _write_table_pair(
                matrix_rows,
                output_dir / "paper_algorithm_matrix_table.csv",
                output_dir / "paper_algorithm_matrix_table.md",
                "Algorithm By Scenario Matrix",
            )
        )
        winner_rows = algorithm_winner_rows(matrix_rows)
        artifacts.update(
            _write_table_pair(
                winner_rows,
                output_dir / "paper_algorithm_winners.csv",
                output_dir / "paper_algorithm_winners.md",
                "Best Algorithm By Scenario",
            )
        )
    else:
        warnings.append("figures/phase2_matrix_summary.csv not found")

    noise = _read_json_if_exists(run_dir / "noise_ood_sweep.json")
    if noise:
        rows = noise_rows(noise)
        artifacts.update(
            _write_table_pair(
                rows,
                output_dir / "paper_noise_robustness_table.csv",
                output_dir / "paper_noise_robustness_table.md",
                "Noise And OOD Robustness",
            )
        )
    else:
        warnings.append("noise_ood_sweep.json not found")

    fallback = _read_json_if_exists(run_dir / "fallback_threshold_sweep.json")
    if fallback:
        rows = fallback_rows(fallback)
        artifacts.update(
            _write_table_pair(
                rows,
                output_dir / "paper_fallback_sweep_table.csv",
                output_dir / "paper_fallback_sweep_table.md",
                "Conservative Fallback Threshold Sweep",
            )
        )
    else:
        warnings.append("fallback_threshold_sweep.json not found")

    citations = _read_json_if_exists(citations_path) or {"sources": []}
    limitations = _read_json_if_exists(limitations_path) or {"limitations": []}
    citations_md = output_dir / "citations.md"
    limitations_md = output_dir / "limitations.md"
    citations_md.write_text(render_citations(citations), encoding="utf-8")
    limitations_md.write_text(render_limitations(limitations), encoding="utf-8")
    artifacts["citations_md"] = str(citations_md)
    artifacts["limitations_md"] = str(limitations_md)

    dashboard_html = output_dir / "live_dashboard.html"
    artifacts["live_dashboard_html"] = str(dashboard_html)

    summary_md = output_dir / "paper_summary.md"
    artifact_manifest_path = output_dir / "paper_artifacts_manifest.json"
    artifacts["paper_summary_md"] = str(summary_md)
    artifacts["paper_artifacts_manifest_json"] = str(artifact_manifest_path)
    summary_md.write_text(
        render_paper_summary(
            manifest=manifest,
            selector=selector,
            calibration=calibration,
            matrix_rows=_read_csv(matrix_path) if matrix_path.exists() else [],
            noise=noise,
            fallback=fallback,
            artifacts=artifacts,
            warnings=warnings,
            limitations=limitations,
        ),
        encoding="utf-8",
    )
    dashboard_html.write_text(
        render_live_dashboard(
            manifest=manifest,
            run_dir=run_dir,
            output_dir=output_dir,
            artifacts=artifacts,
            warnings=warnings,
        ),
        encoding="utf-8",
    )

    artifact_manifest = {
        "manifest_path": str(manifest_path),
        "run_id": manifest.get("run_id"),
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "artifacts": artifacts,
        "warnings": warnings,
        "source_counts": {
            "citations": len(citations.get("sources", [])),
            "limitations": len(limitations.get("limitations", [])),
        },
    }
    artifact_manifest_path.write_text(
        json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact_manifest


def selector_policy_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    policies = report.get("policy_summary", {})
    rows = []
    for name in _ordered_keys(policies, POLICY_ORDER):
        metrics = policies[name]
        row = {"policy": POLICY_LABELS.get(name, name), "policy_id": name}
        row.update({field: metrics.get(field) for field in METRIC_FIELDS})
        rows.append(row)
    return rows


def calibration_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for check in report.get("checks", []):
        rows.append(
            {
                "scenario": check.get("scenario", ""),
                "algorithm": check.get("algorithm", ""),
                "metric": check.get("metric", ""),
                "value": check.get("value"),
                "target_min": check.get("target_min"),
                "target_max": check.get("target_max"),
                "status": check.get("status", ""),
                "source": check.get("source", ""),
                "note": check.get("note", ""),
            }
        )
    return rows


def algorithm_winner_rows(matrix_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in matrix_rows:
        grouped.setdefault(str(row.get("scenario", "")), []).append(row)

    winners = []
    for scenario, rows in sorted(grouped.items()):
        if not rows:
            continue
        best = max(rows, key=lambda row: _to_float(row.get("mean_reward")))
        winners.append(
            {
                "scenario": scenario,
                "best_algorithm": best.get("algorithm", ""),
                "mean_reward": best.get("mean_reward"),
                "success_rate": best.get("success_rate"),
                "mean_energy": best.get("mean_energy"),
                "mean_time_s": best.get("mean_time_s"),
                "mean_safety_violations": best.get("mean_safety_violations"),
            }
        )
    return winners


def noise_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in report.get("profiles", []):
        profile = item.get("profile", {})
        profile_name = profile.get("name", "")
        n_contexts = item.get("n_contexts", "")
        for policy_id, metrics in item.get("policies", {}).items():
            row = {
                "profile": profile_name,
                "policy": POLICY_LABELS.get(policy_id, policy_id),
                "policy_id": policy_id,
                "n_contexts": n_contexts,
            }
            row.update({field: metrics.get(field) for field in METRIC_FIELDS})
            rows.append(row)
    return rows


def fallback_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in report.get("configs", []):
        config = item.get("config", {})
        for profile_item in item.get("profiles", []):
            profile = profile_item.get("profile", {})
            fallback_reasons = _compact_dict(profile_item.get("fallback_reasons", {}))
            for policy_id, metrics in profile_item.get("policies", {}).items():
                row = {
                    "min_signal_quality": config.get("min_signal_quality"),
                    "high_entropy_threshold": config.get("high_entropy_threshold"),
                    "high_rr_cv_threshold": config.get("high_rr_cv_threshold"),
                    "profile": profile.get("name", ""),
                    "policy": POLICY_LABELS.get(policy_id, policy_id),
                    "policy_id": policy_id,
                    "n_contexts": profile_item.get("n_contexts", ""),
                    "fallback_reasons": fallback_reasons,
                }
                row.update({field: metrics.get(field) for field in METRIC_FIELDS})
                rows.append(row)
    return rows


def render_citations(payload: dict[str, Any]) -> str:
    lines = ["# Evidence And Data Sources", ""]
    sources = payload.get("sources", [])
    if not sources:
        lines.append("No citation metadata configured.")
        return "\n".join(lines) + "\n"
    for source in sources:
        title = source.get("title", source.get("id", "untitled source"))
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"- ID: `{source.get('id', '')}`")
        lines.append(f"- Type: `{source.get('type', '')}`")
        lines.append(f"- Phase: `{source.get('phase', '')}`")
        lines.append(f"- URL: {source.get('url', '')}")
        lines.append(f"- Role: {source.get('role', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_limitations(payload: dict[str, Any]) -> str:
    lines = ["# Limitations And Guardrails", ""]
    limitations = payload.get("limitations", [])
    if not limitations:
        lines.append("No limitation metadata configured.")
        return "\n".join(lines) + "\n"
    for item in limitations:
        lines.append(f"## {item.get('title', item.get('id', 'Limitation'))}")
        lines.append("")
        lines.append(item.get("text", ""))
        mitigation = item.get("mitigation", "")
        if mitigation:
            lines.append("")
            lines.append(f"Mitigation: {mitigation}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_paper_summary(
    manifest: dict[str, Any],
    selector: dict[str, Any] | None,
    calibration: dict[str, Any] | None,
    matrix_rows: list[dict[str, Any]],
    noise: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
    artifacts: dict[str, str],
    warnings: list[str],
    limitations: dict[str, Any],
) -> str:
    config = manifest.get("config", {})
    lines = [
        "# Paper Artifact Summary",
        "",
        f"- Run ID: `{manifest.get('run_id', '')}`",
        f"- Preset: `{config.get('preset', 'custom')}`",
        f"- Patients per scenario: `{config.get('patients_per_scenario', '')}`",
        f"- Horizon: `{config.get('horizon_s', '')}` seconds",
        f"- Generated artifacts: `{len(artifacts)}`",
        "",
    ]

    if selector:
        policies = selector.get("policy_summary", {})
        lines.extend(["## Headline Selector Metrics", ""])
        for policy_id in ("selector_linucb", "conservative_selector", "acls_rule", "oracle"):
            if policy_id in policies:
                metrics = policies[policy_id]
                lines.append(
                    f"- {POLICY_LABELS.get(policy_id, policy_id)}: "
                    f"reward `{_format_cell(metrics.get('mean_reward'))}`, "
                    f"oracle gap `{_format_cell(metrics.get('oracle_gap'))}`, "
                    f"success `{_format_cell(metrics.get('success_rate'))}`"
                )
        lines.append("")

    if calibration:
        lines.extend(
            [
                "## Calibration",
                "",
                f"- Pass rate: `{_format_cell(calibration.get('pass_rate'))}`",
                f"- Checks: `{len(calibration.get('checks', []))}`",
                "",
            ]
        )

    winners = algorithm_winner_rows(matrix_rows)
    if winners:
        lines.extend(["## Scenario Winners", ""])
        for row in winners:
            lines.append(
                f"- `{row['scenario']}`: `{row['best_algorithm']}` "
                f"(reward `{_format_cell(row.get('mean_reward'))}`)"
            )
        lines.append("")

    if noise:
        lines.extend(
            [
                "## Robustness Coverage",
                "",
                f"- Noise profiles: `{len(noise.get('profiles', []))}`",
                "",
            ]
        )
    if fallback:
        lines.extend(
            [
                "## Fallback Sweep Coverage",
                "",
                f"- Threshold configs: `{len(fallback.get('configs', []))}`",
                "",
            ]
        )

    limit_items = limitations.get("limitations", [])
    if limit_items:
        lines.extend(["## Required Guardrails", ""])
        for item in limit_items[:4]:
            lines.append(f"- {item.get('title', item.get('id', 'Limitation'))}")
        lines.append("")

    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(["## Artifact Index", ""])
    for name, path in sorted(artifacts.items()):
        lines.append(f"- `{name}`: `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def render_live_dashboard(
    manifest: dict[str, Any],
    run_dir: Path,
    output_dir: Path,
    artifacts: dict[str, str],
    warnings: list[str],
) -> str:
    config = manifest.get("config", {})
    steps = manifest.get("steps", [])
    completed = manifest.get("completed_steps")
    total = manifest.get("total_steps")
    if completed is None:
        completed = sum(1 for step in steps if step.get("status") in {"ok", "skipped"})
    if total is None:
        total = len(manifest.get("step_order", [])) or len(steps)
    progress = (float(completed) / float(total) * 100.0) if total else 0.0
    figures = [
        run_dir / "figures" / "phase2_success_rate.png",
        run_dir / "figures" / "phase2_mean_reward.png",
        run_dir / "figures" / "phase2_mean_energy.png",
        run_dir / "figures" / "phase2_mean_time_s.png",
        run_dir / "figures" / "phase2_mean_safety_violations.png",
        run_dir / "figures" / "decision_boundary.png",
    ]
    existing_figures = [path for path in figures if path.exists()]
    rows = []
    for step in steps:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(step.get('name', '')))}</td>"
            f"<td>{html.escape(str(step.get('status', '')))}</td>"
            f"<td>{float(step.get('duration_s', 0.0)):.2f}</td>"
            f"<td>{len(step.get('outputs', []))}</td>"
            f"<td>{html.escape(str(step.get('message', '')))}</td>"
            "</tr>"
        )
    warning_html = "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings)
    artifact_links = "".join(
        f"<li><a href=\"{_rel_link(output_dir, Path(path))}\">{html.escape(name)}</a></li>"
        for name, path in sorted(artifacts.items())
        if Path(path).exists() and Path(path) != output_dir / "live_dashboard.html"
    )
    figure_html = "".join(
        "<figure>"
        f"<img src=\"{_rel_link(output_dir, path)}\" alt=\"{html.escape(path.stem)}\">"
        f"<figcaption>{html.escape(path.stem)}</figcaption>"
        "</figure>"
        for path in existing_figures
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Vanderpol Run Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
    .bar {{ width: 100%; height: 16px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }}
    .fill {{ width: {progress:.1f}%; height: 100%; background: #2563eb; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px 8px; text-align: left; font-size: 13px; }}
    th {{ background: #f3f4f6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    figure {{ margin: 0; border: 1px solid #d1d5db; padding: 8px; }}
    img {{ max-width: 100%; height: auto; display: block; }}
    figcaption {{ margin-top: 6px; font-size: 13px; color: #4b5563; }}
    code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h1>Vanderpol Run Dashboard</h1>
  <p>Run <code>{html.escape(str(manifest.get('run_id', '')))}</code>, preset <code>{html.escape(str(config.get('preset', 'custom')))}</code>.</p>
  <p>Status <code>{html.escape(str(manifest.get('run_status', '')))}</code>, progress <code>{completed}/{total}</code> ({progress:.1f}%).</p>
  <div class="bar"><div class="fill"></div></div>
  <h2>Steps</h2>
  <table>
    <thead><tr><th>Step</th><th>Status</th><th>Duration s</th><th>Outputs</th><th>Message</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Figures</h2>
  <div class="grid">{figure_html or '<p>No figures are available yet.</p>'}</div>
  <h2>Artifacts</h2>
  <ul>{artifact_links}</ul>
  <h2>Warnings</h2>
  <ul>{warning_html or '<li>None</li>'}</ul>
</body>
</html>
"""


def _write_table_pair(
    rows: list[dict[str, Any]],
    csv_path: Path,
    md_path: Path,
    title: str,
) -> dict[str, str]:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, csv_path)
    md_path.write_text(_markdown_table(title, rows), encoding="utf-8")
    stem = csv_path.stem
    return {f"{stem}_csv": str(csv_path), f"{stem}_md": str(md_path)}


def _write_csv(rows: list[dict[str, Any]], output: Path) -> None:
    fieldnames = _fieldnames(rows)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _markdown_table(title: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("No rows available.")
        return "\n".join(lines) + "\n"
    headers = _fieldnames(rows)
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(header)) for header in headers) + " |")
    return "\n".join(lines) + "\n"


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    fields = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _ordered_keys(mapping: dict[str, Any], preferred: list[str]) -> list[str]:
    seen = set()
    output = []
    for key in preferred:
        if key in mapping:
            output.append(key)
            seen.add(key)
    output.extend(sorted(key for key in mapping if key not in seen))
    return output


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return text.replace("|", "\\|")
    return f"{number:.3f}"


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


def _compact_dict(value: dict[str, Any]) -> str:
    if not value:
        return ""
    return "; ".join(f"{key}={value[key]}" for key in sorted(value))


def _rel_link(base: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=base)).as_posix()


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    return _read_json(path)
