from __future__ import annotations

import unittest

from vanderpol.features import classify_acls_features


class FeatureRuleTests(unittest.TestCase):
    def test_realistic_normal_narrow_complex_is_not_vf_by_entropy_alone(self) -> None:
        label = classify_acls_features(
            {
                "heart_rate_bpm": 95.0,
                "rr_cv": 0.12,
                "qrs_width_s": 0.08,
                "dominant_frequency_hz": 6.0,
                "spectral_entropy": 0.85,
                "sample_entropy": 0.3,
            }
        )
        self.assertEqual(label, "normal_or_sinus")

    def test_fast_chaotic_wide_signal_is_vf_like(self) -> None:
        label = classify_acls_features(
            {
                "heart_rate_bpm": 165.0,
                "rr_cv": 0.33,
                "qrs_width_s": 0.18,
                "dominant_frequency_hz": 7.5,
                "spectral_entropy": 0.45,
                "sample_entropy": 1.3,
            }
        )
        self.assertEqual(label, "vf_or_chaotic")


if __name__ == "__main__":
    unittest.main()
