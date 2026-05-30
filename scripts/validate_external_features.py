from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.wfdb_loader import (
    ExternalDataError,
    WfdbMissingError,
    discover_record_names,
    extract_feature_rows,
)
from vanderpol.features import classify_acls_features
from vanderpol.validation import FEATURE_KEYS, label_counts, summarize_feature_dicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="mitdb")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--records", nargs="*", default=None)
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-s", type=float, default=4.0)
    parser.add_argument("--stride-s", type=float, default=None)
    parser.add_argument("--max-windows-per-record", type=int, default=5)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root or Path("data") / "raw" / args.dataset
    try:
        rows = extract_feature_rows(
            root=root,
            dataset=args.dataset,
            records=args.records,
            channel=args.channel,
            window_s=args.window_s,
            stride_s=args.stride_s,
            max_windows_per_record=args.max_windows_per_record,
        )
    except WfdbMissingError as exc:
        print(
            json.dumps(
                {
                    "status": "missing_dependency",
                    "message": str(exc),
                    "next": "Install WFDB, then rerun this script.",
                },
                indent=2,
            )
        )
        return
    except ExternalDataError as exc:
        print(
            json.dumps(
                {
                    "status": "missing_data",
                    "message": str(exc),
                    "discovered_records": discover_record_names(root),
                    "next": (
                        "Download sample records with "
                        "`python scripts/download_physionet_sample.py --dataset "
                        f"{args.dataset} --limit 2`."
                    ),
                },
                indent=2,
            )
        )
        return

    feature_dicts = [row.features for row in rows]
    summary = summarize_feature_dicts(feature_dicts, group=args.dataset)
    payload = {
        "status": "ok",
        "dataset": args.dataset,
        "root": str(root),
        "n_windows": len(rows),
        "label_counts": label_counts(feature_dicts),
        "summary": {
            "group": summary.group,
            "n": summary.n,
            "means": summary.means,
            "stds": summary.stds,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = ["dataset", "record_name", "window_start_s", "channel", "acls_label", *FEATURE_KEYS]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "dataset": row.dataset,
                        "record_name": row.record_name,
                        "window_start_s": row.window_start_s,
                        "channel": row.channel,
                        "acls_label": classify_acls_features(row.features),
                        **{key: row.features.get(key, "") for key in FEATURE_KEYS},
                    }
                )


if __name__ == "__main__":
    main()
