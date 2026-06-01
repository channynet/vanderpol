from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vanderpol.dashboard import (
    artifact_response,
    compare_runs,
    dry_run_estimate,
    list_runs,
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
            "Run Selector",
            "Run Storage",
            "Intermediate / Final Results",
            "All Outputs",
            "All Outputs By Step",
            "System",
            "stage9 - 중간 결과와 최종 결과를 화면에 정리하는 단계",
        ):
            self.assertIn(label, html)
        for tab in ("runs", "method", "intermediate", "final", "system"):
            self.assertIn(f'data-tab="{tab}"', html)
            self.assertIn(f'id="panel-{tab}"', html)
        for endpoint in ("/api/runs", "/api/compare", "/api/dry-run", "/api/artifact"):
            self.assertIn(endpoint, html)
        self.assertIn("artifactCategoryFilter", html)
        self.assertIn("keyResults", html)
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
