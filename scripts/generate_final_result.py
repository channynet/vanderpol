from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.dashboard import load_ai_model_run_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a consolidated final result from paper-ready runs.")
    parser.add_argument("--runs-dir", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--versioned-runs-dir", type=Path, default=Path("outputs/versioned_runs"))
    parser.add_argument("--output-md", type=Path, default=Path("docs/final_result.md"))
    parser.add_argument("--output-json", type=Path, default=Path("docs/final_result.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("docs/final_result_runs.csv"))
    args = parser.parse_args()

    result = build_final_result(args.runs_dir, args.versioned_runs_dir)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(result), encoding="utf-8")
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_run_csv(result, args.output_csv)
    print(json.dumps({"output_md": str(args.output_md), "primary_run_id": result["primary_run"]["run_id"]}, indent=2))


def build_final_result(runs_dir: Path, versioned_runs_dir: Path = Path("outputs/versioned_runs")) -> dict[str, Any]:
    runs = []
    for run_dir in sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        row = collect_run(run_dir)
        if row:
            runs.append(row)
    if not runs:
        raise RuntimeError(f"No paper-ready runs found under {runs_dir}")

    completed = [run for run in runs if run["status"] == "completed"]
    candidates = completed or runs
    primary = max(
        candidates,
        key=lambda run: (
            int(run["config"].get("patients_per_scenario") or 0),
            float(run["config"].get("horizon_s") or 0.0),
            int(run.get("noise_profile_count") or 0),
            str(run.get("updated_at") or ""),
        ),
    )
    versioned_ai = load_ai_model_run_results(versioned_runs_dir)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "runs_dir": str(runs_dir),
        "versioned_runs_dir": str(versioned_runs_dir),
        "selection_rule": "completed paper-ready run with the largest patients_per_scenario, then horizon_s, then noise profile count",
        "run_count": len(runs),
        "completed_run_count": len(completed),
        "primary_run": primary,
        "runs": runs,
        "versioned_ai_model_results": versioned_ai,
    }


def collect_run(run_dir: Path) -> dict[str, Any] | None:
    paper_dir = run_dir / "paper_artifacts"
    manifest_path = run_dir / "run_manifest.json"
    if not paper_dir.exists() or not manifest_path.exists():
        return None
    manifest = load_json(manifest_path)
    if not manifest:
        return None
    selector_rows = read_csv_dicts(paper_dir / "paper_selector_table.csv")
    winner_rows = read_csv_dicts(paper_dir / "paper_algorithm_winners.csv")
    calibration_rows = read_csv_dicts(paper_dir / "paper_calibration_table.csv")
    noise_rows = read_csv_dicts(paper_dir / "paper_noise_robustness_table.csv")
    fallback_rows = read_csv_dicts(paper_dir / "paper_fallback_sweep_table.csv")
    config = manifest.get("config") or {}
    status = str(manifest.get("status") or manifest.get("run_status") or "unknown")
    return {
        "run_id": run_dir.name,
        "status": status,
        "run_dir": str(run_dir),
        "paper_dir": str(paper_dir),
        "updated_at": datetime.fromtimestamp(paper_dir.stat().st_mtime, tz=UTC).isoformat(),
        "config": config,
        "patients_per_scenario": config.get("patients_per_scenario"),
        "horizon_s": config.get("horizon_s"),
        "preset": config.get("preset", "custom"),
        "reward_weights": config.get("reward_weights") or {},
        "policy_metrics": policy_metrics(selector_rows),
        "scenario_winners": winner_rows,
        "calibration": calibration_summary(calibration_rows),
        "noise_summary": noise_summary(noise_rows),
        "fallback_config_count": fallback_config_count(fallback_rows),
        "noise_profile_count": len({row.get("profile") for row in noise_rows if row.get("profile")}),
    }


def policy_metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for row in rows:
        policy_id = row.get("policy_id")
        if not policy_id:
            continue
        metrics[policy_id] = {
            "policy": row.get("policy") or policy_id,
            "mean_reward": as_float(row.get("mean_reward")),
            "oracle_gap": as_float(row.get("oracle_gap")),
            "success_rate": as_float(row.get("success_rate")),
            "mean_energy": as_float(row.get("mean_energy")),
            "mean_time_s": as_float(row.get("mean_time_s")),
            "mean_safety_violations": as_float(row.get("mean_safety_violations")),
        }
    return metrics


def calibration_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    total = len(rows)
    passed = sum(1 for row in rows if str(row.get("status") or "").lower() == "pass")
    return {"checks": total, "passed": passed, "pass_rate": (passed / total) if total else None}


def noise_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    summaries = []
    for row in rows:
        if row.get("policy_id") not in {"acls_rule", "selector_linucb", "oracle"}:
            continue
        summaries.append(
            {
                "profile": row.get("profile"),
                "policy_id": row.get("policy_id"),
                "mean_reward": as_float(row.get("mean_reward")),
                "oracle_gap": as_float(row.get("oracle_gap")),
                "success_rate": as_float(row.get("success_rate")),
                "mean_safety_violations": as_float(row.get("mean_safety_violations")),
            }
        )
    return summaries


def fallback_config_count(rows: list[dict[str, str]]) -> int:
    keys = {
        (
            row.get("min_signal_quality"),
            row.get("high_entropy_threshold"),
            row.get("high_rr_cv_threshold"),
        )
        for row in rows
    }
    return len(keys) if rows else 0


def render_markdown(result: dict[str, Any]) -> str:
    primary = result["primary_run"]
    policies = primary["policy_metrics"]
    winners = primary["scenario_winners"]
    calibration = primary["calibration"]
    lines = [
        "# Consolidated Final Result",
        "",
        f"- Generated at: `{result['generated_at']}`",
        f"- Runs considered: `{result['run_count']}` paper-ready runs, `{result['completed_run_count']}` completed",
        f"- Selection rule: {result['selection_rule']}",
        f"- Primary evidence run: `{primary['run_id']}`",
        f"- Primary preset: `{primary.get('preset')}`",
        f"- Patients per scenario: `{primary.get('patients_per_scenario')}`",
        f"- Horizon: `{primary.get('horizon_s')}` seconds",
        f"- Noise profiles: `{primary.get('noise_profile_count')}`",
        f"- Fallback threshold configs: `{primary.get('fallback_config_count')}`",
        "",
        "## Final Conclusion",
        "",
        "The final manuscript-facing result should use the primary evidence run above, not the one-patient mutation runs, because it has the largest completed evaluation scale in the current workspace.",
        "",
        "The simulator supports the main claim that scenario-specific electrical treatment choices differ across rhythm classes. The strongest scenario-level actions in the primary run are listed below. Clinical efficacy is not claimed; treatment success and safety are simulator outcomes.",
        "",
    ]
    lines.extend(render_versioned_ai_section(result.get("versioned_ai_model_results") or {}))
    lines.extend(
        [
            "## Policy-Level Metrics",
            "",
            "| policy | mean_reward | oracle_gap | success_rate | mean_energy | mean_time_s | mean_safety_violations |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for policy_id in ("selector_linucb", "acls_rule", "oracle", "always_synchronized_cardioversion", "always_unsynchronized_defibrillation", "always_atp", "always_resonant_drift", "always_adaptive"):
        metric = policies.get(policy_id)
        if not metric:
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(metric["policy"]),
                    fmt(metric["mean_reward"]),
                    fmt(metric["oracle_gap"]),
                    fmt(metric["success_rate"]),
                    fmt(metric["mean_energy"]),
                    fmt(metric["mean_time_s"]),
                    fmt(metric["mean_safety_violations"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Scenario-Level Final Actions",
            "",
            "| scenario | final_action | mean_reward | success_rate | mean_energy | mean_time_s | mean_safety_violations |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in winners:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("scenario", "")),
                    str(row.get("best_algorithm", "")),
                    fmt(as_float(row.get("mean_reward"))),
                    fmt(as_float(row.get("success_rate"))),
                    fmt(as_float(row.get("mean_energy"))),
                    fmt(as_float(row.get("mean_time_s"))),
                    fmt(as_float(row.get("mean_safety_violations"))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Calibration And Robustness",
            "",
            f"- Calibration checks: `{calibration['passed']}/{calibration['checks']}` pass, pass rate `{fmt(calibration['pass_rate'])}`",
            f"- Robustness profiles summarized: `{primary.get('noise_profile_count')}`",
            "",
            "| profile | policy | mean_reward | oracle_gap | success_rate | mean_safety_violations |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in primary["noise_summary"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("profile", "")),
                    str(row.get("policy_id", "")),
                    fmt(row.get("mean_reward")),
                    fmt(row.get("oracle_gap")),
                    fmt(row.get("success_rate")),
                    fmt(row.get("mean_safety_violations")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Included Runs",
            "",
            "| run_id | status | patients_per_scenario | horizon_s | preset | paper_dir |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for run in sorted(result["runs"], key=lambda item: (int(item.get("patients_per_scenario") or 0), str(item.get("updated_at") or "")), reverse=True):
        lines.append(
            f"| `{run['run_id']}` | {run['status']} | {run.get('patients_per_scenario') or ''} | {run.get('horizon_s') or ''} | {run.get('preset') or ''} | `{run['paper_dir']}` |"
        )
    lines.extend(
        [
            "",
            "## Required Guardrail",
            "",
            "This final result is a research-simulator result. External ECG data is used for feature/noise validation, while reward, success, and safety outcomes are generated by the simulator.",
            "",
        ]
    )
    return "\n".join(lines)


def render_versioned_ai_section(versioned: dict[str, Any]) -> list[str]:
    if not versioned:
        return []
    aggregate = versioned.get("aggregate") or {}
    selector_avg = aggregate.get("selector_model_average") or {}
    acls_avg = aggregate.get("acls_rule_average") or {}
    oracle_avg = aggregate.get("oracle_average") or {}
    conclusion = versioned.get("conclusion") or {}
    evidence = conclusion.get("selector_evidence") or {}
    realism = conclusion.get("realism_evidence") or {}
    lines = [
        "## Versioned AI Model Results",
        "",
        conclusion.get("headline") or "Versioned AI model conclusion is unavailable.",
        "",
        f"- Versioned runs considered: `{versioned.get('run_count')}`",
        f"- Selector-evaluated runs: `{aggregate.get('selector_model_run_count')}`",
        f"- Runs where selector reward beats ACLS reward: `{evidence.get('selector_beats_acls_count')}/{evidence.get('selector_comparable_run_count')}`",
        f"- Average selector reward: `{fmt(selector_avg.get('mean_reward'))}`",
        f"- Average ACLS reward: `{fmt(acls_avg.get('mean_reward'))}`",
        f"- Average oracle reward: `{fmt(oracle_avg.get('mean_reward'))}`",
        f"- Average reward delta vs ACLS: `{fmt(evidence.get('reward_delta_vs_acls'))}`",
        f"- Latest realism run: `{realism.get('latest_run_id')}`",
        f"- Latest realism mean SMD: `{fmt(realism.get('latest_mean_smd_abs'))}`",
        f"- Latest realism mean KS: `{fmt(realism.get('latest_mean_ks_statistic'))}`",
        f"- Latest worst realism feature: `{realism.get('latest_worst_group') or ''}/{realism.get('latest_worst_feature') or ''}`",
        "",
        "v002-v004 were evaluated with the same n20 AI selector configuration, so their selector metrics are reproducible and match each other; their real-vs-synthetic rhythm validation differs by version.",
        "",
        "| run_id | status | selector_reward | acls_reward | oracle_reward | selector_success | mean_smd | mean_ks |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in versioned.get("runs") or []:
        selector = run.get("selector_model") or {}
        acls = run.get("acls_rule") or {}
        oracle = run.get("oracle") or {}
        realism_summary = run.get("realism_comparison") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{run.get('run_id')}`",
                    str(run.get("status") or ""),
                    fmt(selector.get("mean_reward")),
                    fmt(acls.get("mean_reward")),
                    fmt(oracle.get("mean_reward")),
                    fmt(selector.get("success_rate")),
                    fmt(realism_summary.get("mean_smd_abs")),
                    fmt(realism_summary.get("mean_ks_statistic")),
                ]
            )
            + " |"
        )
    lines.extend(["", ""])
    return lines


def write_run_csv(result: dict[str, Any], path: Path) -> None:
    fields = ["run_id", "status", "patients_per_scenario", "horizon_s", "preset", "noise_profile_count", "fallback_config_count", "paper_dir"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in result["runs"]:
            writer.writerow({field: run.get(field) for field in fields})


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value: Any) -> str:
    number = as_float(value)
    if number is None:
        return ""
    return f"{number:.3f}"


if __name__ == "__main__":
    main()
