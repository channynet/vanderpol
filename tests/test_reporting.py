from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from vanderpol.reporting import (
    build_selector_report,
    decision_boundary_grid,
    generate_phase2_heatmaps,
    save_decision_boundary,
)


class ReportingTests(unittest.TestCase):
    def test_selector_report_smoke(self) -> None:
        report = build_selector_report(
            patients_per_scenario=1,
            train_fraction=0.6,
            horizon_s=3.0,
        )
        self.assertGreater(report.n_train, 0)
        self.assertGreater(report.n_eval, 0)
        self.assertIn("selector_linucb", report.policy_summary)
        self.assertTrue(np.isfinite(report.policy_summary["oracle"]["mean_reward"]))

    def test_decision_boundary_grid_smoke(self) -> None:
        grid = decision_boundary_grid(patients_per_scenario=1, grid_size=6, horizon_s=3.0)
        self.assertEqual(grid["selector"].shape, (6, 6))
        self.assertEqual(grid["acls"].shape, (6, 6))
        self.assertTrue(np.isin(grid["selector"], [0, 1, 2, 3, 4]).all())

    def test_generate_outputs_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            outputs = generate_phase2_heatmaps(
                patients_per_scenario=1,
                output_dir=output_dir,
                horizon_s=3.0,
            )
            self.assertTrue(Path(outputs["summary_csv"]).exists())
            self.assertTrue(Path(outputs["success_rate"]).exists())
            grid = decision_boundary_grid(patients_per_scenario=1, grid_size=4, horizon_s=3.0)
            png = output_dir / "boundary.png"
            csv = output_dir / "boundary.csv"
            save_decision_boundary(grid, png, csv)
            self.assertTrue(png.exists())
            self.assertTrue(csv.exists())


if __name__ == "__main__":
    unittest.main()
