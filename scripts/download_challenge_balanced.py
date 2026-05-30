from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage7 import (
    alarm_type_counts,
    download_balanced_challenge_sample,
    ensure_challenge_metadata,
    load_alarm_metadata,
    save_alarm_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/challenge-2015"))
    parser.add_argument("--per-category", type=int, default=1)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument("--truth", choices=["any", "true", "false"], default="any")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--manifest", type=Path, default=Path("outputs/challenge2015_balanced_manifest.csv"))
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()

    alarms_path, _ = ensure_challenge_metadata(args.root)
    rows = load_alarm_metadata(alarms_path)
    if args.list_only:
        print(json.dumps(alarm_type_counts(rows), indent=2, sort_keys=True))
        return

    selected, downloaded = download_balanced_challenge_sample(
        root=args.root,
        per_category=args.per_category,
        categories=args.categories,
        truth=args.truth,
        seed=args.seed,
    )
    save_alarm_manifest(selected, args.manifest)
    print(
        json.dumps(
            {
                "manifest": str(args.manifest),
                "selected": [row.__dict__ for row in selected],
                "downloaded_files": [str(path) for path in downloaded],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
