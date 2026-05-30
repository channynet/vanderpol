from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from vanderpol.progress import (
    GracefulStopRequested,
    RunRecorder,
    atomic_write_json,
    check_stop_requested,
    classify_snapshot,
    fold_events,
    load_json,
    load_jsonl,
    request_stop,
)


class ProgressTests(unittest.TestCase):
    def test_atomic_write_and_load_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "progress.json"
            atomic_write_json({"run_id": "r1", "value": 3}, path)
            self.assertEqual(load_json(path)["value"], 3)

    def test_event_fold_distinguishes_skipped_and_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run-a"
            recorder = RunRecorder(run_dir, "run-a")
            recorder.event("run_started", status="running")
            recorder.event("step_started", step="calibration_report", status="running")
            recorder.event("step_done", step="calibration_report", status="skipped")
            recorder.event("run_stopped", status="stopped")

            snapshot = fold_events(load_jsonl(recorder.events_path), "run-a", run_dir)
            self.assertEqual(snapshot["classification"], "stopped")
            self.assertEqual(snapshot["steps"][0]["status"], "skipped")

    def test_current_progress_and_bad_metric_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run-b"
            recorder = RunRecorder(run_dir, "run-b")
            recorder.write_current({"run_status": "running", "progress_fraction": 0.25})
            recorder.metric("selector_report", "selector.mean_reward", math.nan)

            snapshot = load_json(run_dir / "current_progress.json")
            self.assertEqual(snapshot["classification"], "running")
            metrics = load_jsonl(recorder.metrics_path)
            self.assertIsNone(metrics[0]["value"])
            self.assertEqual(metrics[0]["bad_value"], "nan")
            self.assertTrue(any(event["event_type"] == "warning" for event in load_jsonl(recorder.events_path)))

    def test_stop_request_marker_raises_graceful_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            request_stop(run_dir, reason="test")
            with self.assertRaises(GracefulStopRequested):
                check_stop_requested(run_dir)

    def test_classify_stale_snapshot(self) -> None:
        snapshot = {"status": "running", "heartbeat_at": "2020-01-01T00:00:00+00:00"}
        self.assertEqual(classify_snapshot(snapshot, now_s=1_700_000_000), "stalled")


if __name__ == "__main__":
    unittest.main()
