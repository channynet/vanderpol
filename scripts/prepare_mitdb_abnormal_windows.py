from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.annotations import (  # noqa: E402
    derive_rhythm_segments,
    iter_segment_windows,
    load_annotation_events,
)
from vanderpol.data.physionet import download_records  # noqa: E402
from vanderpol.data.wfdb_loader import ExternalDataError, WfdbMissingError, load_record  # noqa: E402
from vanderpol.features import classify_acls_features, make_observation  # noqa: E402
from vanderpol.validation import FEATURE_KEYS, label_counts, summarize_feature_dicts  # noqa: E402


SOURCE_URL = "https://archive.physionet.org/physiobank/database/html/mitdbdir/records.htm"

MITDB_ABNORMAL_RECORDS: dict[str, list[str]] = {
    "106": ["VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY", "VT"],
    "114": ["SVT"],
    "200": ["VENTRICULAR_BIGEMINY", "VT"],
    "201": ["SVT", "AFIB", "NODAL", "VENTRICULAR_TRIGEMINY"],
    "202": ["AFL", "AFIB"],
    "203": ["AFL", "AFIB", "VENTRICULAR_TRIGEMINY", "VT"],
    "205": ["VT"],
    "207": ["SVT", "VENTRICULAR_BIGEMINY", "IVR", "VT", "VF"],
    "209": ["SVT"],
    "210": ["AFIB", "VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY", "VT"],
    "213": ["VENTRICULAR_BIGEMINY", "VT"],
    "214": ["VENTRICULAR_TRIGEMINY", "VT"],
    "215": ["VT"],
    "217": ["AFIB", "PACED", "VENTRICULAR_BIGEMINY", "VT"],
    "219": ["AFIB", "VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY"],
    "220": ["SVT"],
    "221": ["AFIB", "VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY", "VT"],
    "222": ["ATRIAL_BIGEMINY", "SVT", "AFL", "AFIB", "NODAL"],
    "223": ["VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY", "VT"],
    "228": ["VENTRICULAR_BIGEMINY"],
    "230": ["PREEXCITATION"],
    "231": ["HEART_BLOCK_2"],
    "232": ["SINUS_BRADYCARDIA"],
    "233": ["VENTRICULAR_BIGEMINY", "VENTRICULAR_TRIGEMINY", "VT"],
    "234": ["SVT"],
}

DEFAULT_LABELS = (
    "SVT",
    "AFIB",
    "AFL",
    "VT",
    "VF",
    "VENTRICULAR_BIGEMINY",
    "VENTRICULAR_TRIGEMINY",
    "IVR",
    "NODAL",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/mitdb"))
    parser.add_argument("--records", nargs="*", default=None)
    parser.add_argument("--labels", nargs="*", default=list(DEFAULT_LABELS))
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-s", type=float, default=4.0)
    parser.add_argument("--stride-s", type=float, default=4.0)
    parser.add_argument("--max-windows-per-segment", type=int, default=5)
    parser.add_argument("--download-missing", action="store_true")
    parser.add_argument("--output-prefix", type=Path, default=Path("outputs/mitdb_abnormal_windows"))
    args = parser.parse_args()

    records = list(args.records or MITDB_ABNORMAL_RECORDS.keys())
    labels = {label.upper() for label in args.labels}
    if args.download_missing:
        _download_missing(args.root, records)

    try:
        payload = prepare_windows(
            root=args.root,
            records=records,
            labels=labels,
            channel=args.channel,
            window_s=args.window_s,
            stride_s=args.stride_s,
            max_windows_per_segment=args.max_windows_per_segment,
        )
    except (ExternalDataError, WfdbMissingError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return

    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    npz_path = output_prefix.with_suffix(".npz")
    json_path = output_prefix.with_suffix(".json")
    _write_csv(payload["rows"], csv_path)
    np.savez_compressed(
        npz_path,
        ecg=np.asarray(payload["windows"], dtype=float),
        labels=np.asarray([row["annotation_label"] for row in payload["rows"]]),
        records=np.asarray([row["record_name"] for row in payload["rows"]]),
        starts_s=np.asarray([row["window_start_s"] for row in payload["rows"]], dtype=float),
        fs_hz=np.asarray([row["fs_hz"] for row in payload["rows"]], dtype=int),
    )
    manifest = {
        key: value
        for key, value in payload.items()
        if key not in {"windows", "rows", "feature_dicts"}
    }
    manifest.update(
        {
            "status": "ok",
            "source_url": SOURCE_URL,
            "csv_path": str(csv_path),
            "npz_path": str(npz_path),
            "json_path": str(json_path),
        }
    )
    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


def prepare_windows(
    root: Path,
    records: list[str],
    labels: set[str],
    channel: int,
    window_s: float,
    stride_s: float,
    max_windows_per_segment: int,
) -> dict:
    rows: list[dict] = []
    windows: list[np.ndarray] = []
    feature_dicts: list[dict[str, float]] = []
    segment_counts: dict[str, int] = {}
    record_counts: dict[str, int] = {}

    for record_name in records:
        record = load_record(root, record_name, dataset="mitdb", channel=channel)
        events = load_annotation_events(root, record_name)
        segments = derive_rhythm_segments(events, record_length=len(record.signal))
        channel_name = (
            record.channel_names[channel]
            if channel < len(record.channel_names)
            else f"channel_{channel}"
        )
        for segment in segments:
            if segment.label not in labels:
                continue
            segment_counts[segment.label] = segment_counts.get(segment.label, 0) + 1
            count = 0
            for start_sample, window in iter_segment_windows(
                signal=record.signal,
                fs_hz=record.fs_hz,
                segment=segment,
                window_s=window_s,
                stride_s=stride_s,
                max_windows=max_windows_per_segment,
            ):
                observation = make_observation(window, record.fs_hz)
                row = {
                    "dataset": "mitdb",
                    "record_name": record_name,
                    "annotation_label": segment.label,
                    "segment_source": segment.source,
                    "segment_start_s": segment.start_sample / float(record.fs_hz),
                    "segment_end_s": segment.end_sample / float(record.fs_hz),
                    "segment_duration_s": segment.duration_s(record.fs_hz),
                    "window_start_s": start_sample / float(record.fs_hz),
                    "window_s": window_s,
                    "fs_hz": record.fs_hz,
                    "channel": channel_name,
                    "acls_label": classify_acls_features(observation.features),
                    **{key: observation.features.get(key, "") for key in FEATURE_KEYS},
                }
                rows.append(row)
                windows.append(np.asarray(window, dtype=float))
                feature_dicts.append(observation.features)
                record_counts[record_name] = record_counts.get(record_name, 0) + 1
                count += 1
            if count == 0:
                segment_counts[segment.label] -= 1

    if not rows:
        raise ExternalDataError("No MIT-BIH abnormal windows were extracted.")

    summary = summarize_feature_dicts(feature_dicts, group="mitdb_abnormal")
    annotation_counts: dict[str, int] = {}
    for row in rows:
        label = row["annotation_label"]
        annotation_counts[label] = annotation_counts.get(label, 0) + 1

    return {
        "dataset": "mitdb",
        "records_requested": records,
        "labels_requested": sorted(labels),
        "records_from_directory_page": MITDB_ABNORMAL_RECORDS,
        "n_windows": len(rows),
        "annotation_counts": dict(sorted(annotation_counts.items())),
        "segment_counts": dict(sorted((k, v) for k, v in segment_counts.items() if v > 0)),
        "record_counts": dict(sorted(record_counts.items())),
        "acls_label_counts": label_counts(feature_dicts),
        "summary": {
            "group": summary.group,
            "n": summary.n,
            "means": summary.means,
            "stds": summary.stds,
        },
        "rows": rows,
        "windows": windows,
        "feature_dicts": feature_dicts,
    }


def _download_missing(root: Path, records: list[str]) -> None:
    missing = []
    for record in records:
        expected = [root / f"{record}{ext}" for ext in (".hea", ".dat", ".atr")]
        if any((not path.exists()) or path.stat().st_size == 0 for path in expected):
            missing.append(record)
    if missing:
        download_records("mitdb", records=missing, destination=root)


def _write_csv(rows: list[dict], output_csv: Path) -> None:
    fields = [
        "dataset",
        "record_name",
        "annotation_label",
        "segment_source",
        "segment_start_s",
        "segment_end_s",
        "segment_duration_s",
        "window_start_s",
        "window_s",
        "fs_hz",
        "channel",
        "acls_label",
        *FEATURE_KEYS,
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


if __name__ == "__main__":
    main()
