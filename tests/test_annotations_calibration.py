from __future__ import annotations

import unittest

from vanderpol.calibration import calibration_report, load_calibration_targets
from vanderpol.data.annotations import (
    AnnotationEvent,
    RhythmSegment,
    clean_rhythm_label,
    derive_rhythm_segments,
    iter_segment_windows,
)
from vanderpol.experiments import MatrixRow
from vanderpol.types import RhythmScenario


class AnnotationCalibrationTests(unittest.TestCase):
    def test_clean_rhythm_label(self) -> None:
        self.assertEqual(clean_rhythm_label("(VF\x00"), "VF")
        self.assertEqual(clean_rhythm_label("(VT"), "VT")
        self.assertEqual(clean_rhythm_label("(N"), "N")
        self.assertEqual(clean_rhythm_label("(SVTA"), "SVT")
        self.assertEqual(clean_rhythm_label("(AFIB"), "AFIB")
        self.assertEqual(clean_rhythm_label("(AFL"), "AFL")
        self.assertEqual(clean_rhythm_label("(B"), "VENTRICULAR_BIGEMINY")
        self.assertEqual(clean_rhythm_label("(T"), "VENTRICULAR_TRIGEMINY")
        self.assertEqual(clean_rhythm_label("(VFL"), "VF")
        self.assertEqual(clean_rhythm_label("(IVR"), "IVR")
        self.assertEqual(clean_rhythm_label("(NOD"), "NODAL")
        self.assertIsNone(clean_rhythm_label(""))

    def test_derive_segments_from_aux_and_brackets(self) -> None:
        events = [
            AnnotationEvent(100, "+", "(VT"),
            AnnotationEvent(200, "+", "(N"),
            AnnotationEvent(300, "[", ""),
            AnnotationEvent(450, "]", ""),
        ]
        segments = derive_rhythm_segments(events, record_length=500)
        labels = [(segment.label, segment.start_sample, segment.end_sample) for segment in segments]
        self.assertIn(("VT", 100, 200), labels)
        self.assertIn(("N", 200, 500), labels)
        self.assertIn(("VF", 300, 450), labels)

    def test_short_segment_window_is_centered_with_context(self) -> None:
        signal = list(range(1000))
        segment = RhythmSegment(label="VT", start_sample=450, end_sample=500, source="test")
        windows = list(iter_segment_windows(signal, fs_hz=250, segment=segment, window_s=4.0))
        self.assertEqual(len(windows), 1)
        self.assertEqual(len(windows[0][1]), 1000)

    def test_calibration_targets_load_and_report(self) -> None:
        targets = load_calibration_targets("configs/calibration.json")
        self.assertGreaterEqual(len(targets), 1)
        rows = [
            MatrixRow(
                scenario=RhythmScenario.NSR,
                patient_seed=1,
                action_id=4,
                algorithm="adaptive_low_energy_pacing",
                reward=100.0,
                success=True,
                energy=0.0,
                time_to_termination_s=0.0,
                safety_violations=0,
            )
        ]
        report = calibration_report(rows, targets)
        self.assertIn("checks", report)


if __name__ == "__main__":
    unittest.main()
