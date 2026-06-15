from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_static_dashboard import generate_static_dashboard


class StaticDashboardTests(unittest.TestCase):
    def test_generate_static_dashboard_embeds_result_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_json = root / "final_result.json"
            input_md = root / "final_result.md"
            output = root / "dashboard" / "index.html"
            input_json.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-15T00:00:00+00:00",
                        "run_count": 1,
                        "completed_run_count": 1,
                        "primary_run": {
                            "run_id": "stage9_n100_time2",
                            "patients_per_scenario": 100,
                            "horizon_s": 30.0,
                            "policy_metrics": {"oracle": {"mean_reward": 99.0, "success_rate": 1.0}},
                            "scenario_winners": [],
                        },
                        "runs": [{"run_id": "stage9_n100_time2", "status": "completed", "preset": "n100"}],
                        "versioned_ai_model_results": {
                            "run_count": 1,
                            "completed_run_count": 1,
                            "aggregate": {
                                "selector_model_average": {"mean_reward": 90.0, "success_rate": 0.9, "oracle_gap": 9.0},
                                "acls_rule_average": {"mean_reward": 80.0, "success_rate": 0.8},
                                "oracle_average": {"mean_reward": 99.0},
                            },
                            "conclusion": {
                                "headline": "Selector exceeds ACLS on average.",
                                "selector_evidence": {"reward_delta_vs_acls": 10.0},
                                "realism_evidence": {"latest_mean_smd_abs": 0.5},
                            },
                            "realism_aggregate": {},
                            "runs": [],
                            "scenario_consensus": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            input_md.write_text("# Final\n\nAvoid closing script: </script>\n", encoding="utf-8")

            generate_static_dashboard(
                input_json,
                input_md,
                output,
                runs_dir=root / "missing-runs",
                versioned_runs_dir=root / "missing-versioned-runs",
                paper_compendium=root / "missing-paper.md",
            )

            html = output.read_text(encoding="utf-8")
            self.assertIn("Vanderpol Runs", html)
            self.assertIn("Experiment Dashboard", html)
            self.assertIn("static-dashboard-data", html)
            self.assertIn("staticArtifactUrl", html)
            self.assertIn("stage9_n100_time2", html)
            self.assertIn("<\\/script>", html)
            self.assertIn("static-tailadmin-theme", html)


if __name__ == "__main__":
    unittest.main()
