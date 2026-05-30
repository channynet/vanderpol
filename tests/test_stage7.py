from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vanderpol.noise import NoiseProfile
from vanderpol.stage7 import (
    AlarmMetadata,
    alarm_type_counts,
    fallback_threshold_sweep,
    load_alarm_manifest,
    load_alarm_metadata,
    save_alarm_manifest,
    save_threshold_sweep,
    select_balanced_alarms,
)


class Stage7Tests(unittest.TestCase):
    def test_alarm_metadata_parse_and_balance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ALARMS"
            path.write_text(
                "\n".join(
                    [
                        "v100s,Ventricular_Tachycardia,0",
                        "v101l,Ventricular_Tachycardia,1",
                        "a103l,Asystole,0",
                        "a104s,Asystole,1",
                    ]
                ),
                encoding="utf-8",
            )
            rows = load_alarm_metadata(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(alarm_type_counts(rows)["Asystole"]["total"], 2)
            selected = select_balanced_alarms(rows, per_category=1, seed=1)
            self.assertEqual(len(selected), 2)

    def test_alarm_manifest_roundtrip(self) -> None:
        rows = [AlarmMetadata("x", "Asystole", False)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.csv"
            save_alarm_manifest(rows, path)
            loaded = load_alarm_manifest(path)
            self.assertEqual(loaded, rows)

    def test_threshold_sweep_smoke(self) -> None:
        report = fallback_threshold_sweep(
            patients_per_scenario=1,
            profiles=[NoiseProfile(name="clean")],
            min_sqi_values=[0.35],
            entropy_values=[0.62],
            rr_cv_values=[0.30],
            horizon_s=3.0,
        )
        self.assertEqual(len(report["configs"]), 1)
        with tempfile.TemporaryDirectory() as tmp:
            save_threshold_sweep(report, Path(tmp) / "sweep.json", Path(tmp) / "sweep.csv")
            self.assertTrue((Path(tmp) / "sweep.csv").exists())


if __name__ == "__main__":
    unittest.main()
