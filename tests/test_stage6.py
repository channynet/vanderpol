from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vanderpol.features import make_observation
from vanderpol.noise import NoiseProfile
from vanderpol.stage6 import (
    conservative_action,
    conservative_noise_ood_sweep,
    load_noise_profile_from_stats,
    recommend_noise_profile,
    save_conservative_sweep,
    save_real_noise_stats,
    RealNoiseStats,
)


class Stage6Tests(unittest.TestCase):
    def test_recommend_noise_profile(self) -> None:
        profile = recommend_noise_profile(
            means={"signal_quality": 0.45, "spectral_entropy": 0.7, "sample_entropy": 0.6},
            stds={"rr_cv": 0.2},
            quantiles={},
        )
        self.assertEqual(profile.name, "real_estimated")
        self.assertGreater(profile.gaussian_std, 0.03)

    def test_conservative_action_fallbacks(self) -> None:
        normal = make_observation([0.0, 1.0, 0.0, -1.0] * 100, fs_hz=100)
        features = dict(normal.features)
        features.update({"heart_rate_bpm": 80.0, "rr_cv": 0.1, "qrs_width_s": 0.08, "signal_quality": 0.8})
        normal = type(normal)(normal.ecg, normal.fs_hz, normal.duration_s, features)
        action, reason = conservative_action(1, normal)
        self.assertEqual(action, 4)
        self.assertEqual(reason, "normal_withhold")

        noisy_features = dict(features)
        noisy_features.update({"heart_rate_bpm": 180.0, "rr_cv": 0.4, "qrs_width_s": 0.16, "signal_quality": 0.1})
        noisy = type(normal)(normal.ecg, normal.fs_hz, normal.duration_s, noisy_features)
        action, reason = conservative_action(2, noisy)
        self.assertNotEqual(reason, "model")

    def test_conservative_sweep_and_profile_io(self) -> None:
        report = conservative_noise_ood_sweep(
            patients_per_scenario=1,
            profiles=[NoiseProfile(name="clean")],
            horizon_s=3.0,
        )
        self.assertIn("conservative_selector", report["profiles"][0]["policies"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            save_conservative_sweep(report, tmp_path / "sweep.json", tmp_path / "sweep.csv")
            stats = RealNoiseStats(
                dataset="x",
                n_windows=1,
                feature_means={},
                feature_stds={},
                feature_quantiles={},
                acls_label_counts={},
                recommended_profile=NoiseProfile(name="real_estimated", gaussian_std=0.1),
            )
            save_real_noise_stats(stats, tmp_path / "stats.json")
            loaded = load_noise_profile_from_stats(tmp_path / "stats.json")
            self.assertEqual(loaded.name, "real_estimated")
            self.assertTrue((tmp_path / "sweep.csv").exists())


if __name__ == "__main__":
    unittest.main()
