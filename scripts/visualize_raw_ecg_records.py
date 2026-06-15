from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.data.annotations import (  # noqa: E402
    derive_rhythm_segments,
    load_annotation_events,
)
from vanderpol.data.wfdb_loader import (  # noqa: E402
    ExternalDataError,
    discover_record_names,
    load_record,
)


DATASETS = ("mitdb", "cudb", "challenge-2015")
SEGMENT_COLORS = {
    "N": "#a7c957",
    "VT": "#f4a261",
    "VF": "#e76f51",
    "SVT": "#2a9d8f",
    "AFIB": "#457b9d",
    "AFL": "#6d597a",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create per-record ECG waveform PNGs from local WFDB data.")
    parser.add_argument("--data-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/data_visualizations/raw_records"))
    parser.add_argument("--datasets", nargs="*", default=list(DATASETS), choices=DATASETS)
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-s", type=float, default=10.0)
    parser.add_argument("--max-records-per-dataset", type=int, default=None)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "data_root": str(args.data_root),
        "output_dir": str(args.output_dir),
        "window_s": args.window_s,
        "channel": args.channel,
        "datasets": {},
        "errors": [],
    }

    for dataset in args.datasets:
        dataset_root = args.data_root / dataset
        dataset_output = args.output_dir / dataset
        dataset_output.mkdir(parents=True, exist_ok=True)

        records = discover_record_names(dataset_root)
        if args.max_records_per_dataset is not None:
            records = records[: args.max_records_per_dataset]

        alarm_labels = load_alarm_labels(dataset_root) if dataset == "challenge-2015" else {}
        dataset_rows: list[dict[str, Any]] = []

        for record_name in records:
            try:
                record = load_record(dataset_root, record_name, dataset=dataset, channel=args.channel)
                label = alarm_labels.get(record_name)
                rhythm_segments = load_rhythm_segments(dataset_root, record_name, len(record.signal))
                channel_name = (
                    record.channel_names[args.channel]
                    if args.channel < len(record.channel_names)
                    else f"channel_{args.channel}"
                )
                image_path = plot_record_waveform(
                    record=record,
                    output_dir=dataset_output,
                    window_s=args.window_s,
                    alarm_label=label,
                    rhythm_segments=rhythm_segments,
                    channel_name=channel_name,
                )
                dataset_rows.append(
                    {
                        "record_name": record_name,
                        "duration_s": record.duration_s,
                        "fs_hz": record.fs_hz,
                        "channel": channel_name,
                        "label": label,
                        "image": str(image_path),
                    }
                )
            except Exception as exc:  # keep generating the rest of the dataset
                manifest["errors"].append(
                    {
                        "dataset": dataset,
                        "record_name": record_name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        overview_path = plot_dataset_overview(dataset, dataset_rows, dataset_output)
        manifest["datasets"][dataset] = {
            "root": str(dataset_root),
            "record_count": len(dataset_rows),
            "overview_image": str(overview_path) if overview_path else None,
            "records": dataset_rows,
        }

    manifest_path = args.output_dir / "raw_ecg_visualization_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    index_path = args.output_dir / "RAW_ECG_VISUALIZATION_INDEX.md"
    index_path.write_text(render_index(manifest), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "index": str(index_path), **manifest}, indent=2, ensure_ascii=False))


def load_alarm_labels(dataset_root: Path) -> dict[str, str]:
    path = dataset_root / "ALARMS"
    if not path.exists():
        return {}
    labels: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 3:
                continue
            truth = "true alarm" if parts[2] == "1" else "false alarm"
            labels[parts[0]] = f"{parts[1].replace('_', ' ')} ({truth})"
    return labels


def load_rhythm_segments(dataset_root: Path, record_name: str, record_length: int) -> list[Any]:
    try:
        events = load_annotation_events(dataset_root, record_name)
    except (ExternalDataError, FileNotFoundError):
        return []
    except Exception:
        return []
    return derive_rhythm_segments(events, record_length=record_length)


def plot_record_waveform(
    record: Any,
    output_dir: Path,
    window_s: float,
    alarm_label: str | None,
    rhythm_segments: list[Any],
    channel_name: str,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    window_n = min(len(record.signal), max(1, int(round(window_s * record.fs_hz))))
    signal = np.asarray(record.signal[:window_n], dtype=float)
    time_s = np.arange(window_n) / float(record.fs_hz)

    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.plot(time_s, signal, color="#243b53", linewidth=0.9)
    draw_rhythm_segments(ax, rhythm_segments, record.fs_hz, window_n)

    title_bits = [f"{record.dataset} / {record.record_name}", f"{channel_name}", f"{record.fs_hz} Hz"]
    if alarm_label:
        title_bits.append(alarm_label)
    ax.set_title(" | ".join(title_bits), fontsize=11)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ECG amplitude")
    ax.grid(True, alpha=0.25)
    ax.margins(x=0)
    fig.tight_layout()

    path = output_dir / f"{safe_name(record.record_name)}_waveform.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def draw_rhythm_segments(ax: Any, segments: list[Any], fs_hz: int, window_n: int) -> None:
    if not segments:
        return
    window_end_s = window_n / float(fs_hz)
    labelled: set[str] = set()
    for segment in segments:
        start_s = max(0.0, segment.start_sample / float(fs_hz))
        end_s = min(window_end_s, segment.end_sample / float(fs_hz))
        if end_s <= 0.0 or start_s >= window_end_s or end_s <= start_s:
            continue
        color = SEGMENT_COLORS.get(segment.label, "#8d99ae")
        label = segment.label if segment.label not in labelled else None
        labelled.add(segment.label)
        ax.axvspan(start_s, end_s, color=color, alpha=0.18, label=label)
    if labelled:
        ax.legend(loc="upper right", fontsize=8, frameon=True)


def plot_dataset_overview(dataset: str, rows: list[dict[str, Any]], output_dir: Path) -> Path | None:
    if not rows:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [row["record_name"] for row in rows]
    durations = [float(row["duration_s"]) for row in rows]
    fig_height = max(4.0, min(16.0, 0.26 * len(rows) + 2.0))
    fig, ax = plt.subplots(figsize=(10, fig_height))
    y = np.arange(len(rows))
    ax.barh(y, durations, color="#4f7cac")
    ax.set_yticks(y, labels=labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Duration (s)")
    ax.set_title(f"{dataset} record durations ({len(rows)} records)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "_dataset_record_durations.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def render_index(manifest: dict[str, Any]) -> str:
    lines = [
        "# Raw ECG Visualization Index",
        "",
        f"Source data root: `{manifest['data_root']}`",
        f"Window plotted per record: `{manifest['window_s']}` seconds",
        "",
        "| Dataset | Records visualized | Overview | Folder |",
        "| --- | ---: | --- | --- |",
    ]
    for dataset, info in manifest["datasets"].items():
        overview = Path(info["overview_image"]).name if info.get("overview_image") else ""
        lines.append(
            f"| {dataset} | {info['record_count']} | `{overview}` | `{Path(info['records'][0]['image']).parent if info['records'] else ''}` |"
        )
    if manifest["errors"]:
        lines.extend(["", "## Skipped Records", ""])
        for item in manifest["errors"]:
            lines.append(f"- `{item['dataset']}/{item['record_name']}`: {item['error']}")
    lines.append("")
    return "\n".join(lines)


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


if __name__ == "__main__":
    main()
