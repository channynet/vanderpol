"""WFDB-backed ECG loading utilities.

The functions in this module keep WFDB optional. The synthetic simulator and
core tests should run without external-data dependencies, while real ECG
validation can opt in by installing the `external-data` extra.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from ..features import make_observation
from ..types import ObservationWindow


class ExternalDataError(RuntimeError):
    """Raised when real ECG data cannot be loaded."""


class WfdbMissingError(ExternalDataError):
    """Raised when the optional WFDB dependency is not installed."""


@dataclass(frozen=True)
class ExternalECGRecord:
    dataset: str
    record_name: str
    signal: np.ndarray
    fs_hz: int
    channel_names: tuple[str, ...]
    comments: tuple[str, ...] = ()

    @property
    def duration_s(self) -> float:
        return float(len(self.signal) / self.fs_hz)


@dataclass(frozen=True)
class ExternalFeatureRow:
    dataset: str
    record_name: str
    window_start_s: float
    channel: str
    features: dict[str, float]
    annotation_label: str | None = None


def require_wfdb():
    try:
        import wfdb  # type: ignore
    except ImportError as exc:
        raise WfdbMissingError(
            "WFDB is not installed. Install the external-data extra or run "
            "`python -m pip install wfdb` in an environment that supports it."
        ) from exc
    return wfdb


def discover_record_names(root: str | Path) -> list[str]:
    """Discover WFDB records from local `.hea` files."""

    root = Path(root)
    if not root.exists():
        return []
    return sorted(path.with_suffix("").name for path in root.rglob("*.hea"))


def load_record(
    root: str | Path,
    record_name: str,
    dataset: str,
    channel: int = 0,
) -> ExternalECGRecord:
    """Load one local WFDB record and return one ECG channel."""

    wfdb = require_wfdb()
    root = Path(root)
    record_path = root / record_name
    if not record_path.with_suffix(".hea").exists():
        matches = list(root.rglob(f"{record_name}.hea"))
        if not matches:
            raise ExternalDataError(f"Cannot find WFDB header for record `{record_name}` in {root}.")
        record_path = matches[0].with_suffix("")

    record = wfdb.rdrecord(str(record_path))
    if record.p_signal is None:
        raise ExternalDataError(f"Record `{record_name}` has no physical signal.")
    if channel >= record.p_signal.shape[1]:
        raise ExternalDataError(
            f"Record `{record_name}` has {record.p_signal.shape[1]} channels; "
            f"channel {channel} is unavailable."
        )

    names = tuple(str(name) for name in getattr(record, "sig_name", ()) or ())
    signal = np.asarray(record.p_signal[:, channel], dtype=float)
    fs_hz = int(round(float(record.fs)))
    return ExternalECGRecord(
        dataset=dataset,
        record_name=record_name,
        signal=signal,
        fs_hz=fs_hz,
        channel_names=names,
        comments=tuple(getattr(record, "comments", ()) or ()),
    )


def iter_observation_windows(
    record: ExternalECGRecord,
    window_s: float = 4.0,
    stride_s: float | None = None,
    max_windows: int | None = None,
) -> Iterable[tuple[float, ObservationWindow]]:
    """Yield fixed-length observation windows from an ECG record."""

    if stride_s is None:
        stride_s = window_s
    window_n = int(round(window_s * record.fs_hz))
    stride_n = max(1, int(round(stride_s * record.fs_hz)))
    if window_n <= 0:
        raise ValueError("window_s must be positive")
    count = 0
    for start in range(0, max(0, len(record.signal) - window_n + 1), stride_n):
        if max_windows is not None and count >= max_windows:
            break
        segment = record.signal[start : start + window_n]
        yield start / float(record.fs_hz), make_observation(segment, record.fs_hz)
        count += 1


def extract_feature_rows(
    root: str | Path,
    dataset: str,
    records: Iterable[str] | None = None,
    channel: int = 0,
    window_s: float = 4.0,
    stride_s: float | None = None,
    max_windows_per_record: int | None = None,
) -> list[ExternalFeatureRow]:
    """Load local WFDB records and compute hand-crafted ECG features."""

    root = Path(root)
    record_names = list(records or discover_record_names(root))
    if not record_names:
        raise ExternalDataError(f"No local WFDB records found in {root}.")

    rows: list[ExternalFeatureRow] = []
    for record_name in record_names:
        record = load_record(root, record_name, dataset=dataset, channel=channel)
        channel_name = (
            record.channel_names[channel]
            if channel < len(record.channel_names)
            else f"channel_{channel}"
        )
        for start_s, observation in iter_observation_windows(
            record,
            window_s=window_s,
            stride_s=stride_s,
            max_windows=max_windows_per_record,
        ):
            rows.append(
                ExternalFeatureRow(
                    dataset=dataset,
                    record_name=record_name,
                    window_start_s=start_s,
                    channel=channel_name,
                    features=observation.features,
                )
            )
    return rows
