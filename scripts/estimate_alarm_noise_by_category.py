from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage7 import (
    estimate_noise_by_alarm_category,
    load_alarm_manifest,
    save_category_noise_stats,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/challenge-2015"))
    parser.add_argument("--manifest", type=Path, default=Path("outputs/challenge2015_balanced_manifest.csv"))
    parser.add_argument("--stride-s", type=float, default=10.0)
    parser.add_argument("--max-windows-per-record", type=int, default=4)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/challenge2015_category_noise.json"))
    args = parser.parse_args()

    rows = load_alarm_manifest(args.manifest)
    report = estimate_noise_by_alarm_category(
        root=args.root,
        alarm_rows=rows,
        stride_s=args.stride_s,
        max_windows_per_record=args.max_windows_per_record,
    )
    save_category_noise_stats(report, args.output_json)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "categories": {
                    key: {
                        "records": value["records"],
                        "n_windows": value["n_windows"],
                        "recommended_profile": value["recommended_profile"],
                    }
                    for key, value in report["categories"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
