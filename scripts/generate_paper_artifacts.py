from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage9 import generate_paper_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--citations", type=Path, default=Path("configs/citations.json"))
    parser.add_argument("--limitations", type=Path, default=Path("configs/limitations.json"))
    args = parser.parse_args()

    artifact_manifest = generate_paper_artifacts(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        citations_path=args.citations,
        limitations_path=args.limitations,
    )
    print(json.dumps(artifact_manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
