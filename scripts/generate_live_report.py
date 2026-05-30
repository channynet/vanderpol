from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage8 import inspect_bundle_progress, load_bundle_config
from vanderpol.stage9 import generate_paper_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--preset", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    config = load_bundle_config(args.config, preset=args.preset) if args.config else None
    snapshot = inspect_bundle_progress(args.run_dir, config=config, write_files=True)
    manifest_path = Path(snapshot["manifest_path"])
    artifact_manifest = generate_paper_artifacts(
        manifest_path=manifest_path,
        output_dir=args.output_dir or (args.run_dir / "paper_artifacts_live"),
    )
    print(json.dumps(artifact_manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
