from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage8 import generate_executive_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args()

    output = args.output_md or args.manifest.with_name("executive_summary.md")
    text = generate_executive_summary(args.manifest, output)
    print(text)


if __name__ == "__main__":
    main()
