from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vanderpol.stage9 import generate_paper_artifacts


class Stage9Tests(unittest.TestCase):
    def test_generate_paper_artifacts_from_bundle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            (run_dir / "figures").mkdir(parents=True)
            manifest_path = run_dir / "run_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "run_id": "unit-run",
                        "run_dir": str(run_dir),
                        "config": {
                            "preset": "unit",
                            "patients_per_scenario": 1,
                            "horizon_s": 3.0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "selector_report.json").write_text(
                json.dumps(
                    {
                        "policy_summary": {
                            "selector_linucb": {
                                "mean_reward": 9.0,
                                "oracle_gap": 1.0,
                                "success_rate": 0.5,
                                "mean_energy": 0.2,
                                "mean_time_s": 2.0,
                                "mean_safety_violations": 0.0,
                            },
                            "oracle": {
                                "mean_reward": 10.0,
                                "oracle_gap": 0.0,
                                "success_rate": 1.0,
                                "mean_energy": 0.1,
                                "mean_time_s": 1.0,
                                "mean_safety_violations": 0.0,
                            },
                        },
                        "feature_weights": {
                            "unsynchronized_defibrillation": {
                                "heart_rate_bpm": 1.0,
                                "rr_cv": 0.5,
                                "qrs_width_s": 0.25,
                                "dominant_frequency_hz": 0.1,
                                "spectral_entropy": 0.3,
                                "sample_entropy": 0.2,
                                "signal_quality": -0.1,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "calibration_report.json").write_text(
                json.dumps(
                    {
                        "pass_rate": 1.0,
                        "checks": [
                            {
                                "scenario": "vf_like",
                                "algorithm": "unsynchronized_defibrillation",
                                "metric": "success_rate",
                                "value": 1.0,
                                "target_min": 0.75,
                                "target_max": 1.0,
                                "status": "pass",
                                "source": "unit source",
                                "note": "unit note",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "figures" / "phase2_matrix_summary.csv").write_text(
                "scenario,algorithm,mean_reward,success_rate,mean_energy,mean_time_s,mean_safety_violations\n"
                "vf_like,unsynchronized_defibrillation,10,1,0.5,1,0\n"
                "vf_like,atp_burst_pacing,-1,0,0.1,3,1\n",
                encoding="utf-8",
            )
            (run_dir / "noise_ood_sweep.json").write_text(
                json.dumps(
                    {
                        "profiles": [
                            {
                                "profile": {"name": "clean"},
                                "n_contexts": 2,
                                "policies": {
                                    "selector_linucb": {
                                        "mean_reward": 9,
                                        "oracle_gap": 1,
                                        "success_rate": 1,
                                        "mean_energy": 0.2,
                                        "mean_time_s": 1.0,
                                        "mean_safety_violations": 0,
                                    }
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "fallback_threshold_sweep.json").write_text(
                json.dumps(
                    {
                        "configs": [
                            {
                                "config": {
                                    "min_signal_quality": 0.35,
                                    "high_entropy_threshold": 0.62,
                                    "high_rr_cv_threshold": 0.3,
                                },
                                "profiles": [
                                    {
                                        "profile": {"name": "clean"},
                                        "n_contexts": 2,
                                        "fallback_reasons": {"model": 2},
                                        "policies": {
                                            "conservative_selector": {
                                                "mean_reward": 9,
                                                "oracle_gap": 1,
                                                "success_rate": 1,
                                                "mean_energy": 0.2,
                                                "mean_time_s": 1.0,
                                                "mean_safety_violations": 0,
                                            }
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            citations = root / "citations.json"
            citations.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "unit",
                                "title": "Unit Source",
                                "type": "test",
                                "phase": "unit",
                                "url": "https://example.com",
                                "role": "test source",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            limitations = root / "limitations.json"
            limitations.write_text(
                json.dumps(
                    {
                        "limitations": [
                            {
                                "id": "sim",
                                "title": "Simulation-only",
                                "text": "Unit limitation.",
                                "mitigation": "Unit mitigation.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            artifact_manifest = generate_paper_artifacts(
                manifest_path,
                output_dir=root / "paper",
                citations_path=citations,
                limitations_path=limitations,
            )

            artifacts = artifact_manifest["artifacts"]
            self.assertTrue(Path(artifacts["paper_selector_table_csv"]).exists())
            self.assertTrue(Path(artifacts["paper_artifacts_manifest_json"]).exists())
            self.assertTrue(Path(artifacts["live_dashboard_html"]).exists())
            self.assertTrue(Path(artifacts["intermediate_results_html"]).exists())
            self.assertTrue(Path(artifacts["intermediate_waveforms_svg"]).exists())
            self.assertTrue(Path(artifacts["final_results_html"]).exists())
            self.assertTrue(Path(artifacts["waveform_analysis_weights_svg"]).exists())
            self.assertTrue(Path(artifacts["visual_report_html"]).exists())
            self.assertTrue(Path(artifacts["final_visual_summary_svg"]).exists())
            self.assertTrue(Path(artifacts["policy_comparison_svg"]).exists())
            self.assertTrue(Path(artifacts["treatment_success_heatmap_svg"]).exists())
            selector_table = Path(artifacts["paper_selector_table_md"]).read_text(encoding="utf-8")
            self.assertNotIn("Selector LinUCB", selector_table)
            self.assertIn("Oracle", selector_table)
            self.assertIn(
                "Intermediate Results",
                Path(artifacts["intermediate_results_html"]).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Final Results",
                Path(artifacts["final_results_html"]).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Simulation-only",
                Path(artifacts["limitations_md"]).read_text(encoding="utf-8"),
            )

    def test_missing_optional_inputs_emit_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "run_manifest.json"
            manifest_path.write_text(
                json.dumps({"run_id": "minimal", "run_dir": str(root), "config": {}}),
                encoding="utf-8",
            )
            artifact_manifest = generate_paper_artifacts(
                manifest_path,
                output_dir=root / "paper",
                citations_path=root / "missing_citations.json",
                limitations_path=root / "missing_limitations.json",
            )
            self.assertGreaterEqual(len(artifact_manifest["warnings"]), 4)
            self.assertTrue(Path(artifact_manifest["artifacts"]["paper_summary_md"]).exists())


if __name__ == "__main__":
    unittest.main()
