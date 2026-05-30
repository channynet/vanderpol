from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from vanderpol.experiments import run_algorithm_matrix
from vanderpol.noise import NoiseProfile, corrupt_ecg, get_noise_profiles
from vanderpol.stage5 import (
    bootstrap_matrix_ci,
    noise_ood_sweep,
    save_bootstrap_ci,
    save_noise_ood_sweep,
    save_selector_stability,
    selector_stability_report,
)


class Stage5Tests(unittest.TestCase):
    def test_noise_profile_changes_signal(self) -> None:
        ecg = np.sin(np.linspace(0.0, 2.0 * np.pi, 250))
        corrupted = corrupt_ecg(ecg, fs_hz=250, profile=NoiseProfile(name="x", gaussian_std=0.1), seed=1)
        self.assertEqual(corrupted.shape, ecg.shape)
        self.assertGreater(float(np.mean(np.abs(corrupted - ecg))), 0.0)
        self.assertEqual([profile.name for profile in get_noise_profiles(["clean", "mild"])], ["clean", "mild"])

    def test_bootstrap_ci_smoke(self) -> None:
        rows, _, _, _, _ = run_algorithm_matrix(patients_per_scenario=1, horizon_s=3.0)
        ci_rows = bootstrap_matrix_ci(rows, n_bootstrap=10, seed=1)
        self.assertGreater(len(ci_rows), 0)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "ci.csv"
            save_bootstrap_ci(ci_rows, output)
            self.assertTrue(output.exists())

    def test_selector_stability_smoke(self) -> None:
        report = selector_stability_report(
            patients_per_scenario=1,
            seeds=[1, 2],
            horizon_s=3.0,
        )
        self.assertIn("aggregate", report)
        self.assertIn("selector_linucb", report["aggregate"])
        with tempfile.TemporaryDirectory() as tmp:
            save_selector_stability(
                report,
                Path(tmp) / "stability.json",
                Path(tmp) / "stability.csv",
            )
            self.assertTrue((Path(tmp) / "stability.json").exists())

    def test_noise_ood_sweep_smoke(self) -> None:
        report = noise_ood_sweep(
            patients_per_scenario=1,
            profile_names=["clean", "mild"],
            horizon_s=3.0,
        )
        self.assertEqual(len(report["profiles"]), 2)
        self.assertIn("selector_linucb", report["profiles"][0]["policies"])
        with tempfile.TemporaryDirectory() as tmp:
            save_noise_ood_sweep(
                report,
                Path(tmp) / "noise.json",
                Path(tmp) / "noise.csv",
            )
            self.assertTrue((Path(tmp) / "noise.csv").exists())


if __name__ == "__main__":
    unittest.main()
