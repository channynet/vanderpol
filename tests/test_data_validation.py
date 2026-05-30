from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vanderpol.data.physionet import PHYSIONET_DATASETS
from vanderpol.data.wfdb_loader import discover_record_names
from vanderpol.validation import (
    compare_feature_summaries,
    summarize_feature_dicts,
    synthetic_feature_summaries,
)


class DataValidationTests(unittest.TestCase):
    def test_discover_record_names_from_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "100.hea").write_text("placeholder", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "cu01.hea").write_text("placeholder", encoding="utf-8")
            self.assertEqual(discover_record_names(root), ["100", "cu01"])

    def test_physionet_manifest_has_expected_datasets(self) -> None:
        self.assertIn("mitdb", PHYSIONET_DATASETS)
        self.assertIn("cudb", PHYSIONET_DATASETS)
        self.assertIn(".hea", PHYSIONET_DATASETS["mitdb"].default_extensions)

    def test_feature_summary_and_comparison(self) -> None:
        left = summarize_feature_dicts(
            [
                {"heart_rate_bpm": 100.0, "rr_cv": 0.1},
                {"heart_rate_bpm": 120.0, "rr_cv": 0.2},
            ],
            group="left",
        )
        right = summarize_feature_dicts(
            [
                {"heart_rate_bpm": 110.0, "rr_cv": 0.1},
                {"heart_rate_bpm": 130.0, "rr_cv": 0.2},
            ],
            group="right",
        )
        gaps = compare_feature_summaries(left, right)
        self.assertIn("heart_rate_bpm", gaps)
        self.assertGreaterEqual(gaps["heart_rate_bpm"], 0.0)

    def test_synthetic_feature_summaries_smoke(self) -> None:
        summaries = synthetic_feature_summaries(patients_per_scenario=1)
        self.assertEqual(len(summaries), 5)
        self.assertTrue(all(summary.n == 1 for summary in summaries))


if __name__ == "__main__":
    unittest.main()
