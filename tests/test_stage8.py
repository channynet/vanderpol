from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vanderpol.stage8 import (
    default_bundle_config,
    environment_snapshot,
    generate_executive_summary,
    inspect_bundle_progress,
    load_bundle_config,
    render_progress_markdown,
    run_experiment_bundle,
)


class Stage8Tests(unittest.TestCase):
    def test_default_and_environment(self) -> None:
        config = default_bundle_config("smoke")
        self.assertEqual(config["preset"], "smoke")
        self.assertIn("python", environment_snapshot())

    def test_load_config_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"patients_per_scenario": 2}', encoding="utf-8")
            config = load_bundle_config(path, preset="smoke")
            self.assertEqual(config["patients_per_scenario"], 2)
            self.assertEqual(config["preset"], "smoke")

    def test_bundle_smoke_outputs_manifest_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = default_bundle_config("smoke")
            config.update(
                {
                    "patients_per_scenario": 1,
                    "horizon_s": 2.0,
                    "bootstrap_samples": 5,
                    "decision_grid_size": 4,
                    "noise_profiles": ["clean"],
                    "fallback_min_sqi": [0.35],
                    "selector_stability_seeds": [1],
                    "real_noise_stats": str(Path(tmp) / "missing.json"),
                    "enabled_steps": ["calibration_report", "selector_report"],
                }
            )
            manifest = run_experiment_bundle(config, output_dir=Path(tmp), run_id="test-run")
            self.assertTrue(Path(manifest["manifest_path"]).exists())
            self.assertTrue(Path(manifest["progress_md_path"]).exists())
            self.assertTrue(Path(manifest["summary_path"]).exists())
            self.assertTrue(all(step["status"] == "ok" for step in manifest["steps"]))
            summary = generate_executive_summary(manifest["manifest_path"], Path(tmp) / "summary.md")
            self.assertIn("Executive Summary", summary)

    def test_progress_infers_partial_run_and_resume_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = default_bundle_config("smoke")
            config.update(
                {
                    "patients_per_scenario": 1,
                    "horizon_s": 2.0,
                    "enabled_steps": ["calibration_report"],
                }
            )
            run_dir = Path(tmp) / "resume-run"
            run_experiment_bundle(config, output_dir=Path(tmp), run_id="resume-run")
            snapshot = inspect_bundle_progress(run_dir, config=config, write_files=True)
            self.assertEqual(snapshot["completed_steps"], 1)
            self.assertIn("Run Progress", render_progress_markdown(snapshot))

            resumed = run_experiment_bundle(
                config,
                output_dir=Path(tmp),
                run_id="resume-run",
                resume=True,
            )
            self.assertEqual(resumed["steps"][0]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
