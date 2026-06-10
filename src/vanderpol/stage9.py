"""Stage 9: manuscript-ready artifacts from experiment bundle manifests."""

from __future__ import annotations

import csv
import html
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from .experiments import observe_patient
from .features import FEATURE_VECTOR_KEYS, classify_acls_features
from .simulator import GoisSaviSimulator
from .types import RhythmScenario


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
HIDDEN_RESULT_POLICIES = {
    "selector_linucb",
    "conservative_selector",
}
DISPLAY_POLICY_ORDER = [
    policy for policy in POLICY_ORDER if policy not in HIDDEN_RESULT_POLICIES
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

SCENARIO_LABELS = {
    "nsr": "Normal sinus rhythm",
    "svt_flutter": "SVT / flutter-like rhythm",
    "monomorphic_vt": "Monomorphic VT",
    "polymorphic_vt": "Polymorphic VT",
    "vf_like": "VF-like rhythm",
}

ACTION_LABELS = {
    "synchronized_cardioversion": "Synchronized cardioversion",
    "unsynchronized_defibrillation": "Unsynchronized defibrillation",
    "atp_burst_pacing": "ATP burst pacing",
    "resonant_drift_pacing": "Resonant drift pacing",
    "adaptive_low_energy_pacing": "Adaptive low-energy pacing",
}

METRIC_FIELDS = [
    "mean_reward",
    "oracle_gap",
    "success_rate",
    "mean_energy",
    "mean_time_s",
    "mean_safety_violations",
]


def generate_result_artifacts(
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
    citations_path: str | Path = "configs/citations.json",
    limitations_path: str | Path = "configs/limitations.json",
) -> dict[str, Any]:
    """Generate run-facing visual artifacts from a Stage 8 run."""

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
                "Policy Baseline Summary",
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
    matrix_rows: list[dict[str, Any]] = []
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
            matrix_rows=matrix_rows,
            noise=noise,
            fallback=fallback,
            artifacts=artifacts,
            warnings=warnings,
            limitations=limitations,
        ),
        encoding="utf-8",
    )
    visual_artifacts = generate_visual_artifacts(
        manifest=manifest,
        run_dir=run_dir,
        output_dir=output_dir,
        selector=selector,
        matrix_rows=matrix_rows,
        fallback=fallback,
        warnings=warnings,
    )
    artifacts.update(visual_artifacts)
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


def generate_paper_artifacts(
    manifest_path: str | Path,
    output_dir: str | Path | None = None,
    citations_path: str | Path = "configs/citations.json",
    limitations_path: str | Path = "configs/limitations.json",
) -> dict[str, Any]:
    """Backward-compatible alias for older callers."""

    return generate_result_artifacts(
        manifest_path=manifest_path,
        output_dir=output_dir,
        citations_path=citations_path,
        limitations_path=limitations_path,
    )


def selector_policy_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    policies = report.get("policy_summary", {})
    rows = []
    for name in _display_policy_keys(policies):
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
            if policy_id in HIDDEN_RESULT_POLICIES:
                continue
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
                if policy_id in HIDDEN_RESULT_POLICIES:
                    continue
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
        "# Intermediate And Final Result Summary",
        "",
        f"- Run ID: `{manifest.get('run_id', '')}`",
        f"- Preset: `{config.get('preset', 'custom')}`",
        f"- Patients per scenario: `{config.get('patients_per_scenario', '')}`",
        f"- Horizon: `{config.get('horizon_s', '')}` seconds",
        f"- Generated result files: `{len(artifacts)}`",
        "",
    ]

    if selector:
        policies = selector.get("policy_summary", {})
        lines.extend(["## Headline Policy Metrics", ""])
        for policy_id in _display_policy_keys(policies):
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


def generate_visual_artifacts(
    manifest: dict[str, Any],
    run_dir: Path,
    output_dir: Path,
    selector: dict[str, Any] | None,
    matrix_rows: list[dict[str, Any]],
    fallback: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, str]:
    """Generate intermediate and final human-facing result views."""

    output_dir.mkdir(parents=True, exist_ok=True)
    visual_report = output_dir / "visual_report.html"
    intermediate_report = output_dir / "intermediate_results.html"
    final_report = output_dir / "final_results.html"
    waveform_svg = output_dir / "intermediate_waveforms.svg"
    summary_svg = output_dir / "final_visual_summary.svg"
    policy_svg = output_dir / "policy_comparison.svg"
    heatmap_svg = output_dir / "treatment_success_heatmap.svg"
    weights_svg = output_dir / "waveform_analysis_weights.svg"

    winners = algorithm_winner_rows(matrix_rows)
    waveforms = build_waveform_previews(manifest.get("config", {}))
    waveform_svg.write_text(render_intermediate_waveforms_svg(waveforms), encoding="utf-8")
    summary_svg.write_text(render_final_summary_svg(manifest, selector, winners), encoding="utf-8")
    policy_svg.write_text(render_policy_comparison_svg(selector), encoding="utf-8")
    heatmap_svg.write_text(render_treatment_success_heatmap_svg(matrix_rows), encoding="utf-8")
    weights_svg.write_text(render_waveform_analysis_weights_svg(selector), encoding="utf-8")
    intermediate_report.write_text(
        render_intermediate_results_report(
            manifest=manifest,
            output_dir=output_dir,
            waveforms=waveforms,
            waveform_image=waveform_svg,
            warnings=warnings,
        ),
        encoding="utf-8",
    )
    final_report.write_text(
        render_final_results_report(
            manifest=manifest,
            output_dir=output_dir,
            selector=selector,
            winners=winners,
            fallback=fallback,
            warnings=warnings,
            images=[summary_svg, policy_svg, heatmap_svg, weights_svg],
        ),
        encoding="utf-8",
    )
    visual_report.write_text(
        render_visual_report(
            manifest=manifest,
            output_dir=output_dir,
            selector=selector,
            winners=winners,
            fallback=fallback,
            warnings=warnings,
            images=[waveform_svg, summary_svg, policy_svg, heatmap_svg, weights_svg],
        ),
        encoding="utf-8",
    )

    artifacts = {
        "visual_report_html": str(visual_report),
        "intermediate_results_html": str(intermediate_report),
        "final_results_html": str(final_report),
        "intermediate_waveforms_svg": str(waveform_svg),
        "final_visual_summary_svg": str(summary_svg),
        "policy_comparison_svg": str(policy_svg),
        "treatment_success_heatmap_svg": str(heatmap_svg),
        "waveform_analysis_weights_svg": str(weights_svg),
    }
    artifacts.update(_try_write_visual_pngs(selector, matrix_rows, winners, output_dir))
    return artifacts


def build_waveform_previews(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Create representative synthetic observation windows for the intermediate view."""

    simulator = GoisSaviSimulator(fs_hz=int(config.get("fs_hz", 250)))
    observation_s = float(config.get("observation_s", 4.0))
    seed_base = int(config.get("waveform_preview_seed", 42000))
    previews: list[dict[str, Any]] = []
    for idx, scenario in enumerate(RhythmScenario):
        patient, observation, trace = observe_patient(
            simulator,
            scenario,
            seed=seed_base + idx * 1000,
            observation_s=observation_s,
        )
        previews.append(
            {
                "scenario": scenario.value,
                "label": SCENARIO_LABELS.get(scenario.value, scenario.value),
                "time_s": trace.time_s,
                "ecg": trace.ecg,
                "features": observation.features,
                "acls_label": classify_acls_features(observation.features),
                "generation": {
                    "seed": patient.seed,
                    "sa_frequency_hz": patient.sa_frequency_hz,
                    "av_frequency_hz": patient.av_frequency_hz,
                    "hp_frequency_hz": patient.hp_frequency_hz,
                    "qrs_width_s": patient.qrs_width_s,
                    "noise_std": patient.noise_std,
                    "artifact_level": patient.artifact_level,
                    "irregularity": patient.irregularity,
                },
            }
        )
    return previews


def render_intermediate_results_report(
    manifest: dict[str, Any],
    output_dir: Path,
    waveforms: list[dict[str, Any]],
    waveform_image: Path,
    warnings: list[str],
) -> str:
    config = manifest.get("config", {})
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', '')))}</td>"
        f"<td>{html.escape(str(item.get('acls_label', '')))}</td>"
        f"<td>{_format_cell((item.get('features') or {}).get('heart_rate_bpm'))}</td>"
        f"<td>{_format_cell((item.get('features') or {}).get('rr_cv'))}</td>"
        f"<td>{_format_cell((item.get('features') or {}).get('qrs_width_s'))}</td>"
        f"<td>{_format_cell((item.get('features') or {}).get('spectral_entropy'))}</td>"
        f"<td>{_format_cell((item.get('features') or {}).get('signal_quality'))}</td>"
        "</tr>"
        for item in waveforms
    )
    generation_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label', '')))}</td>"
        f"<td>{_format_cell((item.get('generation') or {}).get('sa_frequency_hz'))}</td>"
        f"<td>{_format_cell((item.get('generation') or {}).get('av_frequency_hz'))}</td>"
        f"<td>{_format_cell((item.get('generation') or {}).get('hp_frequency_hz'))}</td>"
        f"<td>{_format_cell((item.get('generation') or {}).get('noise_std'))}</td>"
        f"<td>{_format_cell((item.get('generation') or {}).get('irregularity'))}</td>"
        "</tr>"
        for item in waveforms
    )
    warning_html = "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings) or "<li>None</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Intermediate Results</title>
  {_result_report_style()}
</head>
<body>
  <header>
    <h1>Intermediate Results</h1>
    <p>Run <code>{html.escape(str(manifest.get('run_id', '')))}</code> - patients per scenario <code>{html.escape(str(config.get('patients_per_scenario', '')))}</code></p>
  </header>
  <main>
    <h2>Representative Run Waveforms</h2>
    <figure>
      <img src="{_rel_link(output_dir, waveform_image)}" alt="intermediate waveforms">
      <figcaption>Representative synthetic ECG observation windows used to create run data.</figcaption>
    </figure>
    <h2>How The Data Was Made</h2>
    <p>Each run samples rhythm-specific patient parameters, simulates a Gois-Savi / Van der Pol oscillator trace, projects it into an ECG-like lead, then extracts a fixed feature vector for downstream policy checks.</p>
    <table>
      <thead><tr><th>Scenario</th><th>SA Hz</th><th>AV Hz</th><th>HP Hz</th><th>Noise</th><th>Irregularity</th></tr></thead>
      <tbody>{generation_rows}</tbody>
    </table>
    <h2>Observed Waveform Features</h2>
    <table>
      <thead><tr><th>Scenario</th><th>Feature label</th><th>HR bpm</th><th>RR CV</th><th>QRS width s</th><th>Entropy</th><th>Signal quality</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <h2>Warnings</h2>
    <ul>{warning_html}</ul>
  </main>
</body>
</html>
"""


def render_final_results_report(
    manifest: dict[str, Any],
    output_dir: Path,
    selector: dict[str, Any] | None,
    winners: list[dict[str, Any]],
    fallback: dict[str, Any] | None,
    warnings: list[str],
    images: list[Path],
) -> str:
    return render_visual_report(
        manifest=manifest,
        output_dir=output_dir,
        selector=selector,
        winners=winners,
        fallback=fallback,
        warnings=warnings,
        images=images,
        title="Final Results",
    )


def render_visual_report(
    manifest: dict[str, Any],
    output_dir: Path,
    selector: dict[str, Any] | None,
    winners: list[dict[str, Any]],
    fallback: dict[str, Any] | None,
    warnings: list[str],
    images: list[Path],
    title: str = "Intermediate And Final Results",
) -> str:
    config = manifest.get("config", {})
    policies = selector.get("policy_summary", {}) if selector else {}
    headline_cards = []
    for policy_id in _display_policy_keys(policies)[:4]:
        if policy_id not in policies:
            continue
        metrics = policies[policy_id]
        headline_cards.append(
            "<div class=\"metric-card\">"
            f"<span>{html.escape(POLICY_LABELS.get(policy_id, policy_id))}</span>"
            f"<strong>{_format_cell(metrics.get('success_rate'))}</strong>"
            f"<small>reward {_format_cell(metrics.get('mean_reward'))}, gap {_format_cell(metrics.get('oracle_gap'))}</small>"
            "</div>"
        )
    treatment_rows = "".join(
        "<tr>"
        f"<td>{html.escape(SCENARIO_LABELS.get(str(row.get('scenario')), str(row.get('scenario', ''))))}</td>"
        f"<td><strong>{html.escape(ACTION_LABELS.get(str(row.get('best_algorithm')), str(row.get('best_algorithm', ''))))}</strong></td>"
        f"<td>{_bar_html(_to_float(row.get('success_rate')))}</td>"
        f"<td>{_format_cell(row.get('mean_reward'))}</td>"
        f"<td>{_format_cell(row.get('mean_time_s'))}</td>"
        f"<td>{_format_cell(row.get('mean_safety_violations'))}</td>"
        "</tr>"
        for row in winners
    )
    image_html = "".join(
        "<figure>"
        f"<img src=\"{_rel_link(output_dir, image)}\" alt=\"{html.escape(image.stem)}\">"
        f"<figcaption>{html.escape(_visual_caption(image.stem))}</figcaption>"
        "</figure>"
        for image in images
        if image.exists()
    )
    fallback_html = _fallback_visual_summary(fallback)
    warning_html = "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings) or "<li>None</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  {_result_report_style()}
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p>Run <code>{html.escape(str(manifest.get('run_id', '')))}</code> - preset <code>{html.escape(str(config.get('preset', 'custom')))}</code> - patients per scenario <code>{html.escape(str(config.get('patients_per_scenario', '')))}</code></p>
    <div class="guardrail">Research simulator output only. The visualizations summarize model behavior inside this experiment and are not clinical treatment recommendations.</div>
    <div class="metric-grid">{''.join(headline_cards) or '<p>No selector summary is available yet.</p>'}</div>
  </header>
  <main>
    <h2>Visual Summary</h2>
    <div class="figure-grid">{image_html}</div>
    <h2>Symptom-Level Treatment Success</h2>
    <table>
      <thead><tr><th>Symptom / Rhythm</th><th>Model-supported treatment</th><th>Estimated success</th><th>Reward</th><th>Mean time s</th><th>Safety events</th></tr></thead>
      <tbody>{treatment_rows or '<tr><td colspan="6">No scenario matrix is available.</td></tr>'}</tbody>
    </table>
    <div class="section">
      <h2>Fallback Robustness</h2>
      {fallback_html}
    </div>
    <div class="section">
      <h2>Warnings</h2>
      <ul>{warning_html}</ul>
    </div>
  </main>
</body>
</html>
"""


def render_final_summary_svg(
    manifest: dict[str, Any],
    selector: dict[str, Any] | None,
    winners: list[dict[str, Any]],
) -> str:
    width, height = 1280, 760
    policies = selector.get("policy_summary", {}) if selector else {}
    elements = [
        _svg_rect(0, 0, width, height, "#f5f7fb"),
        _svg_text(44, 62, "Final Result Snapshot", 32, "#172033", weight="700"),
        _svg_text(44, 96, f"Run {manifest.get('run_id', '')} - simulator evidence only", 17, "#667085"),
        _svg_rect(44, 124, 1192, 74, "#fff7e6", stroke="#f0b429", radius=10),
        _svg_text(66, 153, "Guardrail", 17, "#92400e", weight="700"),
        _svg_text(66, 178, "These results visualize experimental model behavior, not clinical efficacy.", 18, "#92400e"),
    ]
    x = 44
    for policy_id in _display_policy_keys(policies)[:4]:
        if policy_id not in policies:
            continue
        metrics = policies[policy_id]
        elements.append(_svg_metric_card(x, 232, 276, 126, POLICY_LABELS.get(policy_id, policy_id), _format_cell(metrics.get("success_rate")), f"reward {_format_cell(metrics.get('mean_reward'))}"))
        x += 296
    y = 420
    elements.append(_svg_text(44, y - 34, "Symptom-level model-supported treatment", 22, "#172033", weight="700"))
    for idx, row in enumerate(winners[:5]):
        success = max(0.0, min(1.0, _to_float(row.get("success_rate"))))
        row_y = y + idx * 56
        elements.append(_svg_text(60, row_y + 26, SCENARIO_LABELS.get(str(row.get("scenario")), str(row.get("scenario", ""))), 17, "#172033", weight="700"))
        elements.append(_svg_text(340, row_y + 26, ACTION_LABELS.get(str(row.get("best_algorithm")), str(row.get("best_algorithm", ""))), 16, "#334155"))
        elements.append(_svg_rect(790, row_y + 8, 310, 18, "#e5e7eb", radius=9))
        elements.append(_svg_rect(790, row_y + 8, 310 * success, 18, _success_color(success), radius=9))
        elements.append(_svg_text(1120, row_y + 24, _format_percent(success), 16, "#172033", weight="700"))
    return _svg(width, height, elements)


def render_policy_comparison_svg(selector: dict[str, Any] | None) -> str:
    width, height = 960, 520
    policies = selector.get("policy_summary", {}) if selector else {}
    rows = [(policy_id, policies[policy_id]) for policy_id in _display_policy_keys(policies)[:8]]
    elements = [
        _svg_rect(0, 0, width, height, "#ffffff"),
        _svg_text(34, 46, "Policy Comparison", 26, "#172033", weight="700"),
        _svg_text(34, 76, "Success rate bars; labels include mean reward.", 15, "#667085"),
    ]
    max_bar = 520
    for idx, (policy_id, metrics) in enumerate(rows):
        y = 118 + idx * 45
        success = max(0.0, min(1.0, _to_float(metrics.get("success_rate"))))
        elements.append(_svg_text(34, y + 17, POLICY_LABELS.get(policy_id, policy_id), 14, "#172033"))
        elements.append(_svg_rect(330, y, max_bar, 20, "#e5e7eb", radius=10))
        elements.append(_svg_rect(330, y, max_bar * success, 20, _success_color(success), radius=10))
        elements.append(_svg_text(870, y + 16, f"{_format_percent(success)} - R {_format_cell(metrics.get('mean_reward'))}", 13, "#334155"))
    if not rows:
        elements.append(_svg_text(34, 140, "No selector report is available.", 18, "#667085"))
    return _svg(width, height, elements)


def render_treatment_success_heatmap_svg(matrix_rows: list[dict[str, Any]]) -> str:
    scenarios = list(SCENARIO_LABELS)
    algorithms = list(ACTION_LABELS)
    lookup = {
        (str(row.get("scenario")), str(row.get("algorithm"))): max(0.0, min(1.0, _to_float(row.get("success_rate"))))
        for row in matrix_rows
    }
    cell_w, cell_h = 142, 58
    left, top = 230, 112
    width = left + cell_w * len(algorithms) + 42
    height = top + cell_h * len(scenarios) + 58
    elements = [
        _svg_rect(0, 0, width, height, "#ffffff"),
        _svg_text(34, 46, "Treatment Success Heatmap", 26, "#172033", weight="700"),
        _svg_text(34, 76, "Rows are symptoms/rhythm scenarios; cells are simulator-estimated success rates.", 15, "#667085"),
    ]
    for col, algorithm in enumerate(algorithms):
        elements.append(_svg_text(left + col * cell_w + 6, top - 12, ACTION_LABELS[algorithm], 12, "#334155"))
    for row_idx, scenario in enumerate(scenarios):
        y = top + row_idx * cell_h
        elements.append(_svg_text(34, y + 34, SCENARIO_LABELS[scenario], 15, "#172033", weight="700"))
        for col, algorithm in enumerate(algorithms):
            x = left + col * cell_w
            value = lookup.get((scenario, algorithm))
            color = "#f8fafc" if value is None else _success_color(value)
            elements.append(_svg_rect(x, y, cell_w - 6, cell_h - 6, color, stroke="#ffffff", radius=6))
            elements.append(_svg_text(x + 12, y + 33, "n/a" if value is None else _format_percent(value), 15, "#172033", weight="700"))
    return _svg(width, height, elements)


def render_intermediate_waveforms_svg(waveforms: list[dict[str, Any]]) -> str:
    width = 1280
    row_h = 152
    top = 98
    left = 270
    plot_w = 900
    height = top + row_h * max(1, len(waveforms)) + 48
    elements = [
        _svg_rect(0, 0, width, height, "#ffffff"),
        _svg_text(34, 46, "Intermediate Waveform Preview", 26, "#172033", weight="700"),
        _svg_text(34, 76, "Representative synthetic ECG windows and extracted features.", 15, "#667085"),
    ]
    for idx, item in enumerate(waveforms):
        y0 = top + idx * row_h
        mid = y0 + 72
        elements.append(_svg_rect(28, y0 - 16, width - 56, row_h - 14, "#f8fafc", stroke="#d8dee8", radius=10))
        elements.append(_svg_text(48, y0 + 22, item.get("label", ""), 17, "#172033", weight="700"))
        features = item.get("features") or {}
        feature_note = (
            f"HR {_format_cell(features.get('heart_rate_bpm'))} bpm, "
            f"RR CV {_format_cell(features.get('rr_cv'))}, "
            f"QRS {_format_cell(features.get('qrs_width_s'))} s, "
            f"SQI {_format_cell(features.get('signal_quality'))}"
        )
        elements.append(_svg_text(48, y0 + 50, feature_note, 13, "#667085"))
        elements.append(_svg_text(48, y0 + 78, f"feature label: {item.get('acls_label', '')}", 13, "#334155"))
        elements.append(_svg_rect(left, y0 + 18, plot_w, 96, "#ffffff", stroke="#e5e7eb", radius=6))
        elements.append(_svg_line(left, mid, left + plot_w, mid, "#d8dee8"))
        elements.append(_svg_polyline(_waveform_points(item, left, y0 + 18, plot_w, 96), "#2563eb", width=1.4))
    return _svg(width, height, elements)


def render_waveform_analysis_weights_svg(selector: dict[str, Any] | None) -> str:
    weights = selector.get("feature_weights", {}) if selector else {}
    width, height = 1080, 560
    elements = [
        _svg_rect(0, 0, width, height, "#ffffff"),
        _svg_text(34, 46, "Waveform Analysis Weights", 26, "#172033", weight="700"),
        _svg_text(34, 76, "Learned LinUCB reward weights by ECG feature and treatment action.", 15, "#667085"),
    ]
    if not weights:
        elements.append(_svg_text(34, 145, "No feature weights are available. Re-run selector_report with the updated code.", 18, "#667085"))
        return _svg(width, height, elements)

    actions = [action for action in ACTION_LABELS if action in weights]
    features = [feature for feature in FEATURE_VECTOR_KEYS]
    left, top = 250, 120
    cell_w, cell_h = 140, 54
    values = [
        abs(_to_float(weights.get(action, {}).get(feature)))
        for action in actions
        for feature in features
    ]
    max_abs = max(values) if values else 1.0
    max_abs = max(max_abs, 1e-9)
    for col, feature in enumerate(features):
        label = feature.replace("_", "\n")
        elements.append(_svg_text(left + col * cell_w + 5, top - 14, label.replace("\n", " "), 11, "#334155"))
    for row_idx, action in enumerate(actions):
        y = top + row_idx * cell_h
        elements.append(_svg_text(34, y + 31, ACTION_LABELS.get(action, action), 14, "#172033", weight="700"))
        for col, feature in enumerate(features):
            x = left + col * cell_w
            value = _to_float(weights.get(action, {}).get(feature))
            strength = min(1.0, abs(value) / max_abs)
            color = _weight_color(value, strength)
            elements.append(_svg_rect(x, y, cell_w - 6, cell_h - 6, color, stroke="#ffffff", radius=6))
            elements.append(_svg_text(x + 9, y + 31, f"{value:.2f}", 13, "#172033", weight="700"))
    return _svg(width, height, elements)


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


def _bar_html(value: float) -> str:
    value = max(0.0, min(1.0, value))
    return (
        "<div class=\"bar\">"
        "<div class=\"track\">"
        f"<div class=\"fill\" style=\"width:{value * 100.0:.1f}%\"></div>"
        "</div>"
        f"<strong>{_format_percent(value)}</strong>"
        "</div>"
    )


def _result_report_style() -> str:
    return """<style>
    :root { color-scheme: light; --ink:#172033; --muted:#667085; --line:#d8dee8; --green:#15803d; --amber:#b7791f; }
    body { margin:0; font-family: Arial, sans-serif; color:var(--ink); background:#f5f7fb; }
    header { background:#ffffff; border-bottom:1px solid var(--line); padding:28px 36px; }
    main { padding:28px 36px 44px; }
    h1 { margin:0 0 8px; font-size:28px; }
    h2 { margin:30px 0 14px; font-size:20px; }
    p { color:var(--muted); }
    .guardrail { border-left:4px solid var(--amber); background:#fff7e6; padding:12px 14px; margin-top:14px; }
    .metric-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; margin-top:18px; }
    .metric-card { background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; }
    .metric-card span { display:block; color:var(--muted); font-size:12px; }
    .metric-card strong { display:block; margin:8px 0 4px; font-size:28px; }
    .metric-card small { color:var(--muted); }
    .figure-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:18px; }
    figure { background:#fff; border:1px solid var(--line); border-radius:8px; margin:0 0 18px; padding:14px; }
    img { width:100%; height:auto; display:block; }
    figcaption { margin-top:9px; color:var(--muted); font-size:13px; }
    table { width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); }
    th, td { border-bottom:1px solid var(--line); padding:10px; text-align:left; font-size:13px; }
    th { background:#eef2f8; }
    .bar { display:flex; align-items:center; gap:8px; min-width:150px; }
    .track { flex:1; height:10px; background:#e5e7eb; border-radius:999px; overflow:hidden; }
    .fill { height:100%; background:var(--green); }
    .section { margin-top:20px; }
    code { background:#eef2f8; padding:2px 5px; border-radius:4px; }
  </style>"""


def _fallback_visual_summary(report: dict[str, Any] | None) -> str:
    if not report:
        return "<p>No fallback sweep is available.</p>"
    best: dict[str, Any] | None = None
    for item in report.get("configs", []):
        config = item.get("config", {})
        for profile in item.get("profiles", []):
            metrics = (profile.get("policies", {}) or {}).get("conservative_selector")
            if not isinstance(metrics, dict):
                continue
            candidate = {
                "config": config,
                "profile": (profile.get("profile", {}) or {}).get("name", ""),
                "metrics": metrics,
                "fallback_reasons": profile.get("fallback_reasons", {}),
            }
            if best is None or _to_float(metrics.get("mean_reward")) > _to_float(best["metrics"].get("mean_reward")):
                best = candidate
    if best is None:
        return "<p>No conservative selector fallback result is available.</p>"
    cfg = best["config"]
    metrics = best["metrics"]
    reasons = _compact_dict(best.get("fallback_reasons", {}))
    return (
        "<table>"
        "<thead><tr><th>Profile</th><th>min SQI</th><th>entropy</th><th>RR CV</th><th>Success</th><th>Reward</th><th>Fallback reasons</th></tr></thead>"
        "<tbody><tr>"
        f"<td>{html.escape(str(best.get('profile', '')))}</td>"
        f"<td>{_format_cell(cfg.get('min_signal_quality'))}</td>"
        f"<td>{_format_cell(cfg.get('high_entropy_threshold'))}</td>"
        f"<td>{_format_cell(cfg.get('high_rr_cv_threshold'))}</td>"
        f"<td>{_bar_html(_to_float(metrics.get('success_rate')))}</td>"
        f"<td>{_format_cell(metrics.get('mean_reward'))}</td>"
        f"<td>{html.escape(reasons)}</td>"
        "</tr></tbody></table>"
    )


def _try_write_visual_pngs(
    selector: dict[str, Any] | None,
    matrix_rows: list[dict[str, Any]],
    winners: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        return {}

    artifacts: dict[str, str] = {}
    summary_path = output_dir / "final_visual_summary.png"
    heatmap_path = output_dir / "treatment_success_heatmap.png"
    policy_path = output_dir / "policy_comparison.png"

    policies = selector.get("policy_summary", {}) if selector else {}
    policy_ids = _display_policy_keys(policies)
    fig, axes = plt.subplots(2, 1, figsize=(11, 9), constrained_layout=True)
    if policy_ids:
        success_values = [_to_float(policies[policy].get("success_rate")) for policy in policy_ids]
        axes[0].barh([POLICY_LABELS.get(policy, policy) for policy in policy_ids], success_values, color="#4e8f55")
        axes[0].set_xlim(0, 1)
        axes[0].set_title("Policy success rate")
        axes[0].set_xlabel("Estimated success")
    else:
        axes[0].text(0.05, 0.5, "No selector summary", transform=axes[0].transAxes)
    if winners:
        axes[1].barh(
            [SCENARIO_LABELS.get(str(row.get("scenario")), str(row.get("scenario", ""))) for row in winners],
            [_to_float(row.get("success_rate")) for row in winners],
            color="#2563eb",
        )
        axes[1].set_xlim(0, 1)
        axes[1].set_title("Best treatment success by symptom/rhythm")
        axes[1].set_xlabel("Estimated success")
    else:
        axes[1].text(0.05, 0.5, "No scenario matrix", transform=axes[1].transAxes)
    fig.suptitle("Final Visual Summary", fontsize=16)
    fig.savefig(summary_path, dpi=180)
    plt.close(fig)
    artifacts["final_visual_summary_png"] = str(summary_path)

    if policy_ids:
        fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
        x = np.arange(len(policy_ids))
        ax.bar(x - 0.18, [_to_float(policies[policy].get("success_rate")) for policy in policy_ids], width=0.36, label="success", color="#4e8f55")
        ax.bar(x + 0.18, [_to_float(policies[policy].get("mean_reward")) / 100.0 for policy in policy_ids], width=0.36, label="reward / 100", color="#4f7cac")
        ax.set_xticks(x, [POLICY_LABELS.get(policy, policy) for policy in policy_ids], rotation=20, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_title("Policy comparison")
        ax.legend()
        fig.savefig(policy_path, dpi=180)
        plt.close(fig)
        artifacts["policy_comparison_png"] = str(policy_path)

    if matrix_rows:
        scenarios = list(SCENARIO_LABELS)
        algorithms = list(ACTION_LABELS)
        lookup = {(str(row.get("scenario")), str(row.get("algorithm"))): _to_float(row.get("success_rate")) for row in matrix_rows}
        matrix = np.asarray([[lookup.get((scenario, algorithm), np.nan) for algorithm in algorithms] for scenario in scenarios], dtype=float)
        fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
        image = ax.imshow(matrix, vmin=0, vmax=1, cmap="YlGnBu")
        ax.set_xticks(np.arange(len(algorithms)), [ACTION_LABELS[item] for item in algorithms], rotation=25, ha="right")
        ax.set_yticks(np.arange(len(scenarios)), [SCENARIO_LABELS[item] for item in scenarios])
        for y in range(matrix.shape[0]):
            for x in range(matrix.shape[1]):
                value = matrix[y, x]
                if not np.isnan(value):
                    ax.text(x, y, f"{value * 100:.0f}%", ha="center", va="center", color="#172033", fontsize=9)
        ax.set_title("Treatment success heatmap")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        fig.savefig(heatmap_path, dpi=180)
        plt.close(fig)
        artifacts["treatment_success_heatmap_png"] = str(heatmap_path)
    return artifacts


def _visual_caption(stem: str) -> str:
    return {
        "intermediate_waveforms": "Representative synthetic ECG waveforms used to build run data.",
        "final_visual_summary": "One-page visual summary of policy and symptom-level results.",
        "policy_comparison": "Policy-level comparison of estimated success and reward.",
        "treatment_success_heatmap": "Success-rate heatmap by symptom/rhythm and stimulation action.",
        "waveform_analysis_weights": "Learned ECG feature weights used by the selector.",
    }.get(stem, stem.replace("_", " ").title())


def _format_percent(value: float) -> str:
    if value == float("-inf"):
        return "n/a"
    return f"{value * 100.0:.1f}%"


def _success_color(value: float) -> str:
    if value >= 0.9:
        return "#86d39a"
    if value >= 0.7:
        return "#f2d16b"
    if value >= 0.45:
        return "#f0a867"
    return "#e97878"


def _weight_color(value: float, strength: float) -> str:
    strength = max(0.0, min(1.0, strength))
    if value >= 0:
        red = int(232 - 95 * strength)
        green = int(242 - 86 * strength)
        blue = int(248 - 105 * strength)
    else:
        red = int(248 - 82 * strength)
        green = int(232 - 111 * strength)
        blue = int(232 - 108 * strength)
    return f"rgb({red},{green},{blue})"


def _waveform_points(item: dict[str, Any], left: float, top: float, width: float, height: float) -> list[tuple[float, float]]:
    time_s = np.asarray(item.get("time_s", []), dtype=float)
    ecg = np.asarray(item.get("ecg", []), dtype=float)
    if len(time_s) == 0 or len(ecg) == 0:
        return []
    n = min(len(time_s), len(ecg))
    if n > 320:
        indices = np.linspace(0, n - 1, 320).astype(int)
        time_s = time_s[indices]
        ecg = ecg[indices]
    else:
        time_s = time_s[:n]
        ecg = ecg[:n]
    finite = np.isfinite(ecg)
    if not np.any(finite):
        return []
    ecg = np.nan_to_num(ecg, nan=0.0, posinf=0.0, neginf=0.0)
    centered = ecg - float(np.median(ecg))
    scale = float(np.percentile(np.abs(centered), 95))
    if scale <= 1e-9:
        scale = float(np.std(centered)) + 1e-9
    normalized = np.clip(centered / scale, -1.5, 1.5)
    span = float(time_s[-1] - time_s[0]) or 1.0
    return [
        (
            left + ((float(t) - float(time_s[0])) / span) * width,
            top + height / 2.0 - (float(value) / 1.5) * (height * 0.42),
        )
        for t, value in zip(time_s, normalized)
    ]


def _svg(width: int, height: int, elements: list[str]) -> str:
    return (
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" role=\"img\">"
        "<style>text{font-family:Arial,sans-serif}</style>"
        + "".join(elements)
        + "</svg>\n"
    )


def _svg_line(x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 1.0) -> str:
    return f"<line x1=\"{x1:.1f}\" y1=\"{y1:.1f}\" x2=\"{x2:.1f}\" y2=\"{y2:.1f}\" stroke=\"{html.escape(stroke)}\" stroke-width=\"{width:.1f}\"/>"


def _svg_polyline(points: list[tuple[float, float]], stroke: str, width: float = 1.0) -> str:
    if not points:
        return ""
    encoded = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f"<polyline points=\"{encoded}\" fill=\"none\" stroke=\"{html.escape(stroke)}\" stroke-width=\"{width:.1f}\" stroke-linejoin=\"round\" stroke-linecap=\"round\"/>"


def _svg_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str | None = None,
    radius: float = 0,
) -> str:
    stroke_attr = f" stroke=\"{html.escape(stroke)}\"" if stroke else ""
    return (
        f"<rect x=\"{x:.1f}\" y=\"{y:.1f}\" width=\"{width:.1f}\" height=\"{height:.1f}\" "
        f"rx=\"{radius:.1f}\" fill=\"{html.escape(fill)}\"{stroke_attr}/>"
    )


def _svg_text(
    x: float,
    y: float,
    text: Any,
    size: int,
    fill: str,
    weight: str = "400",
) -> str:
    return f"<text x=\"{x:.1f}\" y=\"{y:.1f}\" font-size=\"{size}\" font-weight=\"{weight}\" fill=\"{html.escape(fill)}\">{html.escape(str(text))}</text>"


def _svg_metric_card(x: float, y: float, width: float, height: float, title: str, value: str, note: str) -> str:
    return (
        _svg_rect(x, y, width, height, "#ffffff", stroke="#d8dee8", radius=12)
        + _svg_text(x + 18, y + 32, title, 15, "#667085")
        + _svg_text(x + 18, y + 78, value, 34, "#172033", weight="700")
        + _svg_text(x + 18, y + 108, note, 15, "#667085")
    )


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


def _display_policy_keys(mapping: dict[str, Any]) -> list[str]:
    return [
        key
        for key in _ordered_keys(mapping, DISPLAY_POLICY_ORDER)
        if key not in HIDDEN_RESULT_POLICIES
    ]


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
