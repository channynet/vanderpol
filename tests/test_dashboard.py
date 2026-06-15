from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from vanderpol.dashboard import (
    artifact_response,
    compare_runs,
    dry_run_estimate,
    list_runs,
    load_ai_model_run_results,
    load_final_result,
    load_paper_compendium,
    load_run_artifacts,
    load_run_progress,
    load_run_storage,
    render_dashboard_html,
)
from vanderpol.progress import RunRecorder, atomic_write_json


class DashboardTests(unittest.TestCase):
    def test_dashboard_html_contains_workflow_shell_and_api_contracts(self) -> None:
        html = render_dashboard_html()
        for label in (
            "Run Workflow",
            "Run Settings",
            "Intermediate Results",
            "Final Results",
            "Versioned Run Results Across 4 Runs",
            "Run Selector",
            "Run Storage",
            "Consolidated Final Result",
            "Paper-ready runs",
            "Active or stalled runs",
            "Other folders and logs",
            "Paper Data",
            "Paper Data Compendium",
            "Intermediate / Final Results",
            "All Outputs",
            "All Outputs By Step",
            "System",
            "stage9 - 중간 결과와 최종 결과를 화면에 정리하는 단계",
        ):
            self.assertIn(label, html)
        for tab in ("runs", "method", "intermediate", "paper", "final", "system"):
            self.assertIn(f'data-tab="{tab}"', html)
            self.assertIn(f'id="panel-{tab}"', html)
        for endpoint in ("/api/runs", "/api/compare", "/api/dry-run", "/api/ai-model-runs", "/api/final-result", "/api/paper-compendium", "/api/artifact"):
            self.assertIn(endpoint, html)
        self.assertIn("artifactCategoryFilter", html)
        self.assertIn("aiModelRuns", html)
        self.assertIn("dashboardFinalResult", html)
        self.assertIn("finalResultSummaryHTML", html)
        self.assertIn("finalResult", html)
        self.assertIn("paperCompendium", html)
        self.assertIn("keyResults", html)
        self.assertIn("runGroupsHTML", html)
        self.assertIn("runMiniProgress", html)
        for removed_text in (
            "Analysis Workflow",
            "Intermediate Review",
            "Comprehensive Review",
            "Paper Result",
            "Paper Artifact Index",
            "Baseline Compare",
            "Data -> Method -> Analysis -> Review -> Paper.",
            "TailAdmin MIT template assets are served locally.",
            "customer-support-img.png",
            "user-1.jpg",
            "/tailadmin-assets/images/",
        ):
            self.assertNotIn(removed_text, html)

    def test_run_listing_progress_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            run_dir = runs_dir / "run-a"
            run_dir.mkdir()
            artifact = run_dir / "result.csv"
            artifact.write_bytes(b"name,value\nx,1\n")

            recorder = RunRecorder(run_dir, "run-a")
            recorder.write_current(
                {
                    "run_id": "run-a",
                    "run_status": "running",
                    "progress_fraction": 0.5,
                    "current_step": "selector_report",
                    "steps": [],
                }
            )
            recorder.artifact(artifact, step="selector_report")

            runs = list_runs(runs_dir)
            self.assertEqual(runs[0]["run_id"], "run-a")
            self.assertEqual(runs[0]["display_name"], "run-a")
            self.assertGreaterEqual(runs[0]["artifact_count"], 3)
            self.assertEqual(load_run_progress(run_dir)["classification"], "running")
            artifacts = load_run_artifacts(run_dir)
            self.assertTrue(any(item["path"] == str(artifact) for item in artifacts))
            self.assertTrue(any(item["category"] == "Tables" for item in artifacts))
            storage = load_run_storage(run_dir)
            self.assertEqual(storage["display_name"], "run-a")
            self.assertIn("Tables", storage["categories"])
            payload, mime = artifact_response(run_dir, str(artifact))
            self.assertEqual(payload, b"name,value\nx,1\n")
            self.assertIn(mime, {"text/csv", "application/vnd.ms-excel"})

    def test_load_paper_compendium_extracts_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paper_all_data.md"
            path.write_text(
                "\n".join(
                    [
                        "\ufeff# Stage 9 n20 Paper Data Compendium",
                        "",
                        "Run ID: `stage9_n20`",
                        "Source directory: `outputs/runs/stage9_n20/paper_artifacts`",
                        "",
                        "## Included Sections",
                        "",
                        "- Paper Summary: `outputs/runs/stage9_n20/paper_artifacts/paper_summary.md`",
                        "- Limitations And Guardrails: `outputs/runs/stage9_n20/paper_artifacts/limitations.md`",
                        "",
                        "---",
                        "",
                        "## Paper Summary",
                    ]
                ),
                encoding="utf-8",
            )

            compendium = load_paper_compendium(path)
            self.assertTrue(compendium["exists"])
            self.assertEqual(compendium["title"], "Stage 9 n20 Paper Data Compendium")
            self.assertEqual(compendium["run_id"], "stage9_n20")
            self.assertEqual(compendium["source_dir"], "outputs/runs/stage9_n20/paper_artifacts")
            self.assertEqual(compendium["sections"][0]["title"], "Paper Summary")
            self.assertIn("markdown", compendium)

            missing = load_paper_compendium(Path(tmp) / "missing.md")
            self.assertFalse(missing["exists"])

    def test_load_final_result_extracts_markdown_and_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            markdown = root / "final_result.md"
            payload = root / "final_result.json"
            markdown.write_text("# Consolidated Final Result\n\nFinal body.\n", encoding="utf-8")
            payload.write_text(json.dumps({"primary_run": {"run_id": "run-a"}, "run_count": 1}), encoding="utf-8")

            result = load_final_result(markdown, payload)
            self.assertTrue(result["exists"])
            self.assertEqual(result["title"], "Consolidated Final Result")
            self.assertEqual(result["payload"]["primary_run"]["run_id"], "run-a")

            missing = load_final_result(root / "missing.md", root / "missing.json")
            self.assertFalse(missing["exists"])

    def test_default_final_result_uses_repo_root_not_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "final_result.md").write_text("# Consolidated Final Result\n\nFinal body.\n", encoding="utf-8")
            (docs / "final_result.json").write_text(json.dumps({"primary_run": {"run_id": "repo-run"}}), encoding="utf-8")
            old_cwd = Path.cwd()
            try:
                os.chdir(other)
                with mock.patch("vanderpol.dashboard.REPO_ROOT", root):
                    result = load_final_result()
            finally:
                os.chdir(old_cwd)

            self.assertTrue(result["exists"])
            self.assertEqual(result["payload"]["primary_run"]["run_id"], "repo-run")
            self.assertEqual(Path(result["path"]).parent, docs)

    def test_load_ai_model_run_results_collects_versioned_selector_and_realism_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            run_dir = runs_dir / "v001_full_pipeline"
            paper_dir = run_dir / "paper_artifacts"
            paper_dir.mkdir(parents=True)
            atomic_write_json(
                {
                    "run_id": "v001_full_pipeline",
                    "run_status": "completed",
                    "progress_fraction": 1.0,
                    "config": {
                        "patients_per_scenario": 1,
                        "horizon_s": 4.0,
                        "train_fraction": 0.7,
                        "decision_grid_size": 12,
                        "selector_seed": 700,
                        "selector_stability_seeds": [700, 701],
                        "noise_profiles": ["clean", "severe"],
                        "fallback_min_sqi": [0.4],
                        "fallback_entropy": [0.6],
                        "fallback_rr_cv": [0.3],
                    },
                },
                run_dir / "run_manifest.json",
            )
            atomic_write_json(
                {
                    "policy_summary": {
                        "selector_linucb": {"mean_reward": 98.0, "oracle_gap": 0.0, "success_rate": 1.0, "mean_safety_violations": 0.0},
                        "acls_rule": {"mean_reward": 95.0, "oracle_gap": 3.0, "success_rate": 1.0},
                        "oracle": {"mean_reward": 98.0, "oracle_gap": 0.0, "success_rate": 1.0},
                    }
                },
                run_dir / "selector_report.json",
            )
            (paper_dir / "paper_algorithm_winners.csv").write_text(
                "scenario,best_algorithm,mean_reward,success_rate,mean_energy,mean_time_s,mean_safety_violations\n"
                "vf_like,unsynchronized_defibrillation,98.0,1.0,0.6,1.2,0.0\n",
                encoding="utf-8",
            )
            realism_dir = runs_dir / "v002_existing_rhythm_realism_tuning"
            comparison_dir = realism_dir / "comparison"
            comparison_dir.mkdir(parents=True)
            atomic_write_json(
                {
                    "experiment": "existing_rhythm_realism_tuning",
                    "parameters": {"patients_per_scenario": 200, "observation_s": 4.0},
                },
                realism_dir / "version_manifest.json",
            )
            atomic_write_json(
                {"status": "ok", "n_real_rows": 10, "n_synthetic_rows": 20},
                comparison_dir / "real_vs_synthetic_abnormal_manifest.json",
            )
            (comparison_dir / "real_vs_synthetic_abnormal_feature_distances.csv").write_text(
                "comparison_group,feature,smd_abs,ks_statistic\n"
                "vt_vs_monomorphic_vt,heart_rate_bpm,0.25,0.3\n"
                "vt_vs_monomorphic_vt,sample_entropy,1.5,0.8\n",
                encoding="utf-8",
            )

            result = load_ai_model_run_results(runs_dir, ["v001_full_pipeline", "v002_existing_rhythm_realism_tuning"])
            self.assertEqual(result["run_count"], 2)
            self.assertEqual(result["runs"][0]["selector_model"]["mean_reward"], 98.0)
            self.assertEqual(result["runs"][1]["realism_comparison"]["max_smd_feature"], "sample_entropy")
            self.assertEqual(result["scenario_consensus"][0]["consensus_algorithm"], "unsynchronized_defibrillation")
            self.assertEqual(result["aggregate"]["selector_model_successful_run_count"], 1)
            self.assertEqual(result["realism_aggregate"]["realism_run_count"], 1)
            self.assertIn("headline", result["conclusion"])
            self.assertEqual(result["conclusion"]["selector_evidence"]["reward_delta_vs_acls"], 3.0)
            self.assertEqual(result["conclusion"]["realism_evidence"]["latest_worst_feature"], "sample_entropy")

    def test_run_labels_are_used_as_display_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp)
            (runs_dir / "run_labels.json").write_text(json.dumps({"stage9_n100": "run1 - time0.5"}), encoding="utf-8")
            run_dir = runs_dir / "stage9_n100"
            run_dir.mkdir()
            RunRecorder(run_dir, "stage9_n100").write_current({"run_status": "completed", "progress_fraction": 1.0})

            runs = list_runs(runs_dir)
            self.assertEqual(runs[0]["display_name"], "run1 - time0.5")
            self.assertEqual(load_run_progress(run_dir)["display_name"], "run1 - time0.5")

    def test_artifact_response_rejects_outside_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run-a"
            run_dir.mkdir()
            outside = Path(tmp) / "outside.txt"
            outside.write_text("nope", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                artifact_response(run_dir, str(outside))

    def test_compare_runs_and_dry_run_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs_dir = Path(tmp) / "runs"
            run_dir = runs_dir / "run-a"
            run_dir.mkdir(parents=True)
            atomic_write_json(
                {
                    "run_id": "run-a",
                    "run_status": "completed",
                    "progress_fraction": 1.0,
                    "config": {"patients_per_scenario": 2},
                    "provenance": {"git": {"available": False}},
                },
                run_dir / "run_manifest.json",
            )
            RunRecorder(run_dir, "run-a").write_current({"run_status": "completed", "progress_fraction": 1.0})
            compared = compare_runs(["run-a"], runs_dir)
            self.assertEqual(compared["runs"][0]["status"], "completed")

            config_path = Path(tmp) / "bundle.json"
            config_path.write_text(
                json.dumps(
                    {
                        "patients_per_scenario": 3,
                        "noise_profiles": ["clean", "severe"],
                        "fallback_min_sqi": [0.35, 0.5],
                        "fallback_entropy": [0.62],
                        "fallback_rr_cv": [0.3],
                        "n_jobs": 6,
                    }
                ),
                encoding="utf-8",
            )
            estimate = dry_run_estimate(config_path)
            self.assertEqual(estimate["patients_per_scenario"], 3)
            self.assertEqual(estimate["n_jobs"], 6)
            self.assertEqual(estimate["rough_units"]["fallback_configs"], 2)


if __name__ == "__main__":
    unittest.main()
