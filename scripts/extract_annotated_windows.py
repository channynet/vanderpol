from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.annotations import extract_annotated_feature_rows
from vanderpol.data.wfdb_loader import ExternalDataError, WfdbMissingError
from vanderpol.features import classify_acls_features
from vanderpol.validation import FEATURE_KEYS, label_counts, summarize_feature_dicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="cudb")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--records", nargs="+", required=True)
    parser.add_argument("--labels", nargs="+", default=["VT", "VF"])
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-s", type=float, default=4.0)
    parser.add_argument("--stride-s", type=float, default=None)
    parser.add_argument("--max-windows-per-segment", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root or Path("data") / "raw" / args.dataset
    try:
        rows = extract_annotated_feature_rows(
            root=root,
            dataset=args.dataset,
            records=args.records,
            target_labels=args.labels,
            channel=args.channel,
            window_s=args.window_s,
            stride_s=args.stride_s,
            max_windows_per_segment=args.max_windows_per_segment,
        )
    except (ExternalDataError, WfdbMissingError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return

    feature_dicts = [row.features for row in rows]
    summary = summarize_feature_dicts(feature_dicts, group=f"{args.dataset}_annotated")
    payload = {
        "status": "ok",
        "dataset": args.dataset,
        "records": args.records,
        "requested_labels": args.labels,
        "n_windows": len(rows),
        "annotation_counts": _annotation_counts(rows),
        "acls_label_counts": label_counts(feature_dicts),
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
            fieldnames = [
                "dataset",
                "record_name",
                "annotation_label",
                "window_start_s",
                "channel",
                "acls_label",
                *FEATURE_KEYS,
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "dataset": row.dataset,
                        "record_name": row.record_name,
                        "annotation_label": row.annotation_label,
                        "window_start_s": row.window_start_s,
                        "channel": row.channel,
                        "acls_label": classify_acls_features(row.features),
                        **{key: row.features.get(key, "") for key in FEATURE_KEYS},
                    }
                )


def _annotation_counts(rows) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = row.annotation_label or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()
