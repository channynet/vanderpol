"""WFDB annotation helpers for rhythm-aware ECG window sampling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from ..features import make_observation
from .wfdb_loader import (
    ExternalDataError,
    ExternalFeatureRow,
    load_record,
    require_wfdb,
)


@dataclass(frozen=True)
class AnnotationEvent:
    sample: int
    symbol: str
    aux_note: str = ""

    @property
    def rhythm_label(self) -> str | None:
        return clean_rhythm_label(self.aux_note)


@dataclass(frozen=True)
class RhythmSegment:
    label: str
    start_sample: int
    end_sample: int
    source: str

    def duration_s(self, fs_hz: int) -> float:
        return (self.end_sample - self.start_sample) / float(fs_hz)


def clean_rhythm_label(aux_note: str | None) -> str | None:
    if not aux_note:
        return None
    cleaned = aux_note.replace("\x00", "").strip()
    if cleaned.startswith("("):
        cleaned = cleaned[1:]
    cleaned = cleaned.strip().upper()
    aliases = {
        "N": "N",
        "NSR": "N",
        "NORMAL": "N",
        "AB": "ATRIAL_BIGEMINY",
        "B": "VENTRICULAR_BIGEMINY",
        "BII": "HEART_BLOCK_2",
        "VT": "VT",
        "IVR": "IVR",
        "NOD": "NODAL",
        "P": "PACED",
        "PREX": "PREEXCITATION",
        "SBR": "SINUS_BRADYCARDIA",
        "T": "VENTRICULAR_TRIGEMINY",
        "VFL": "VF",
        "VF": "VF",
        "VFIB": "VF",
        "AFIB": "AFIB",
        "AFL": "AFL",
        "SVTA": "SVT",
        "SVT": "SVT",
    }
    return aliases.get(cleaned)


def load_annotation_events(
    root: str | Path,
    record_name: str,
    extension: str = "atr",
) -> list[AnnotationEvent]:
    wfdb = require_wfdb()
    root = Path(root)
    record_path = root / record_name
    if not record_path.with_suffix(".hea").exists():
        matches = list(root.rglob(f"{record_name}.hea"))
        if not matches:
            raise ExternalDataError(f"Cannot find WFDB header for record `{record_name}` in {root}.")
        record_path = matches[0].with_suffix("")

    annotation = wfdb.rdann(str(record_path), extension)
    return [
        AnnotationEvent(sample=int(sample), symbol=str(symbol), aux_note=str(aux or ""))
        for sample, symbol, aux in zip(annotation.sample, annotation.symbol, annotation.aux_note)
    ]


def derive_rhythm_segments(
    events: Iterable[AnnotationEvent],
    record_length: int,
) -> list[RhythmSegment]:
    """Derive rhythm segments from WFDB rhythm notes and CUDB-style brackets."""

    ordered = sorted(events, key=lambda event: event.sample)
    segments: list[RhythmSegment] = []

    rhythm_markers = [
        event for event in ordered if event.rhythm_label is not None
    ]
    for idx, event in enumerate(rhythm_markers):
        label = event.rhythm_label
        if label is None:
            continue
        end = (
            rhythm_markers[idx + 1].sample
            if idx + 1 < len(rhythm_markers)
            else record_length
        )
        if end > event.sample:
            segments.append(
                RhythmSegment(
                    label=label,
                    start_sample=event.sample,
                    end_sample=min(end, record_length),
                    source="aux_note",
                )
            )

    vf_start: int | None = None
    for event in ordered:
        if event.symbol == "[":
            vf_start = event.sample
        elif event.symbol == "]" and vf_start is not None and event.sample > vf_start:
            segments.append(
                RhythmSegment(
                    label="VF",
                    start_sample=vf_start,
                    end_sample=min(event.sample, record_length),
                    source="bracket",
                )
            )
            vf_start = None

    return _dedupe_segments(segments)


def extract_annotated_feature_rows(
    root: str | Path,
    dataset: str,
    records: Iterable[str],
    target_labels: Iterable[str],
    channel: int = 0,
    annotation_extension: str = "atr",
    window_s: float = 4.0,
    stride_s: float | None = None,
    max_windows_per_segment: int = 3,
) -> list[ExternalFeatureRow]:
    """Extract feature rows from windows selected by rhythm annotations."""

    labels = {label.upper() for label in target_labels}
    rows: list[ExternalFeatureRow] = []
    for record_name in records:
        record = load_record(root, record_name, dataset=dataset, channel=channel)
        events = load_annotation_events(root, record_name, extension=annotation_extension)
        segments = derive_rhythm_segments(events, record_length=len(record.signal))
        channel_name = (
            record.channel_names[channel]
            if channel < len(record.channel_names)
            else f"channel_{channel}"
        )
        for segment in segments:
            if segment.label not in labels:
                continue
            for start_sample, window in iter_segment_windows(
                signal=record.signal,
                fs_hz=record.fs_hz,
                segment=segment,
                window_s=window_s,
                stride_s=stride_s,
                max_windows=max_windows_per_segment,
            ):
                rows.append(
                    ExternalFeatureRow(
                        dataset=dataset,
                        record_name=record_name,
                        window_start_s=start_sample / float(record.fs_hz),
                        channel=channel_name,
                        features=make_observation(window, record.fs_hz).features,
                        annotation_label=segment.label,
                    )
                )
    if not rows:
        target_text = ", ".join(sorted(labels))
        raise ExternalDataError(f"No annotated windows found for labels: {target_text}.")
    return rows


def iter_segment_windows(
    signal: np.ndarray,
    fs_hz: int,
    segment: RhythmSegment,
    window_s: float = 4.0,
    stride_s: float | None = None,
    max_windows: int = 3,
) -> Iterable[tuple[int, np.ndarray]]:
    window_n = int(round(window_s * fs_hz))
    if window_n <= 0:
        raise ValueError("window_s must be positive")
    stride_n = int(round((stride_s or window_s) * fs_hz))
    stride_n = max(1, stride_n)
    max_start = max(0, len(signal) - window_n)

    if segment.end_sample - segment.start_sample < window_n:
        center = (segment.start_sample + segment.end_sample) // 2
        start = int(np.clip(center - window_n // 2, 0, max_start))
        yield start, signal[start : start + window_n]
        return

    count = 0
    first = int(np.clip(segment.start_sample, 0, max_start))
    last = min(segment.end_sample - window_n, max_start)
    for start in range(first, last + 1, stride_n):
        if count >= max_windows:
            break
        yield start, signal[start : start + window_n]
        count += 1


def _dedupe_segments(segments: list[RhythmSegment]) -> list[RhythmSegment]:
    seen: set[tuple[str, int, int, str]] = set()
    deduped: list[RhythmSegment] = []
    for segment in sorted(segments, key=lambda item: (item.start_sample, item.end_sample, item.label)):
        key = (
            segment.label,
            int(segment.start_sample),
            int(segment.end_sample),
            segment.source,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(segment)
    return deduped
