from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage8 import inspect_bundle_progress, load_bundle_config, render_progress_markdown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--preset", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--watch", type=float, default=0.0, help="Refresh interval in seconds.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args()

    config = load_bundle_config(args.config, preset=args.preset) if args.config else None
    while True:
        snapshot = inspect_bundle_progress(args.run_dir, config=config, write_files=True)
        if args.json:
            print(json.dumps(snapshot, indent=2, sort_keys=True))
        else:
            print(render_progress_markdown(snapshot))
        if args.watch <= 0:
            break
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
