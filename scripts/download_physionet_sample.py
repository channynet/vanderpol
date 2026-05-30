from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.physionet import download_records, list_remote_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="mitdb", choices=["mitdb", "cudb", "challenge-2015", "ptb-xl"])
    parser.add_argument("--destination", type=Path, default=None)
    parser.add_argument("--records", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--list-only", action="store_true")
    args = parser.parse_args()

    if args.list_only:
        records = list_remote_records(args.dataset)
        print(json.dumps({"dataset": args.dataset, "records": records[: args.limit]}, indent=2))
        return

    destination = args.destination or Path("data") / "raw" / args.dataset
    downloaded = download_records(
        args.dataset,
        records=args.records,
        destination=destination,
        limit=None if args.records else args.limit,
    )
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "destination": str(destination),
                "files": [str(path) for path in downloaded],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
