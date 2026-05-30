from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vanderpol.versioning import (
    create_versioned_run_dir,
    next_version_index,
    sanitize_label,
    write_version_manifest,
)


class VersioningTests(unittest.TestCase):
    def test_create_versioned_run_dir_increments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = create_versioned_run_dir(root, "real vs synthetic")
            second = create_versioned_run_dir(root, "real vs synthetic")
            self.assertEqual(first.name, "v001_real_vs_synthetic")
            self.assertEqual(second.name, "v002_real_vs_synthetic")
            self.assertEqual(next_version_index(root), 3)

    def test_sanitize_label_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "v001_test"
            run_dir.mkdir()
            self.assertEqual(sanitize_label("  ECG result #1  "), "ECG_result_1")
            manifest = write_version_manifest(
                run_dir,
                experiment="test",
                parameters={"patients": 2},
                outputs={"csv": "result.csv"},
            )
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["experiment"], "test")
            self.assertEqual(data["parameters"]["patients"], 2)


if __name__ == "__main__":
    unittest.main()
