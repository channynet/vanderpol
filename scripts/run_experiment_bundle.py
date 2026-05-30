from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage8 import load_bundle_config, run_experiment_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--preset", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    config = load_bundle_config(args.config, preset=args.preset)
    manifest = run_experiment_bundle(
        config,
        output_dir=args.output_dir,
        run_id=args.run_id,
        resume=args.resume,
    )
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "run_dir": manifest["run_dir"],
                "manifest_path": manifest["manifest_path"],
                "progress_md_path": manifest["progress_md_path"],
                "summary_path": manifest["summary_path"],
                "failed_steps": [
                    step["name"]
                    for step in manifest["steps"]
                    if step["status"] not in {"ok", "skipped"}
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
