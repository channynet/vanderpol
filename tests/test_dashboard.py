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
)
from vanderpol.progress import RunRecorder, atomic_write_json


class DashboardTests(unittest.TestCase):
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
            self.assertEqual(load_run_progress(run_dir)["classification"], "running")
            artifacts = load_run_artifacts(run_dir)
            self.assertTrue(any(item["path"] == str(artifact) for item in artifacts))
            payload, mime = artifact_response(run_dir, str(artifact))
            self.assertEqual(payload, b"name,value\nx,1\n")
            self.assertIn(mime, {"text/csv", "application/vnd.ms-excel"})

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
