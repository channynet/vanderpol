"""Hand-crafted ECG features and ACLS-style rhythm labels."""

from __future__ import annotations

import numpy as np

from .types import ObservationWindow


FEATURE_VECTOR_KEYS = (
    "heart_rate_bpm",
    "rr_cv",
    "qrs_width_s",
    "dominant_frequency_hz",
    "spectral_entropy",
    "sample_entropy",
    "signal_quality",
)

FEATURE_VECTOR_SCALES = (240.0, 1.0, 0.22, 12.0, 1.0, 2.5, 1.0)


def make_observation(ecg: np.ndarray, fs_hz: int) -> ObservationWindow:
    duration_s = float(len(ecg) / fs_hz)
    features = extract_features(ecg, fs_hz)
    return ObservationWindow(
        ecg=np.asarray(ecg, dtype=float),
        fs_hz=int(fs_hz),
        duration_s=duration_s,
        features=features,
    )


def extract_features(ecg: np.ndarray, fs_hz: int) -> dict[str, float]:
    ecg = np.asarray(ecg, dtype=float)
    finite_ratio = float(np.isfinite(ecg).mean()) if len(ecg) else 0.0
    ecg = np.nan_to_num(ecg, nan=0.0, posinf=0.0, neginf=0.0)
    norm = _robust_normalize(ecg)
    peaks = detect_r_peaks(norm, fs_hz)
    rr = np.diff(peaks) / float(fs_hz) if len(peaks) >= 2 else np.array([])

    hr = float(60.0 / np.mean(rr)) if len(rr) else 0.0
    rr_cv = float(np.std(rr) / (np.mean(rr) + 1e-8)) if len(rr) else 1.0
    qrs_width = estimate_qrs_width(norm, peaks, fs_hz)
    dominant_frequency = estimate_dominant_frequency(norm, fs_hz)
    spectral_entropy = estimate_spectral_entropy(norm, fs_hz)
    sample_entropy = estimate_sample_entropy(norm)
    signal_quality = estimate_signal_quality(norm, finite_ratio)

    return {
        "heart_rate_bpm": hr,
        "rr_cv": rr_cv,
        "regularity": float(1.0 / (1.0 + rr_cv)),
        "qrs_width_s": qrs_width,
        "dominant_frequency_hz": dominant_frequency,
        "spectral_entropy": spectral_entropy,
        "sample_entropy": sample_entropy,
        "signal_quality": signal_quality,
        "num_peaks": float(len(peaks)),
    }


def detect_r_peaks(ecg: np.ndarray, fs_hz: int) -> np.ndarray:
    if len(ecg) < 3:
        return np.array([], dtype=int)
    detection = np.abs(ecg)
    threshold = max(0.35, float(np.median(detection) + 0.75 * np.std(detection)))
    candidates = np.flatnonzero(
        (detection[1:-1] > detection[:-2])
        & (detection[1:-1] >= detection[2:])
        & (detection[1:-1] > threshold)
    ) + 1

    refractory = max(1, int(round(0.22 * fs_hz)))
    selected: list[int] = []
    for idx in candidates:
        if not selected or idx - selected[-1] >= refractory:
            selected.append(int(idx))
        elif detection[idx] > detection[selected[-1]]:
            selected[-1] = int(idx)
    return np.asarray(selected, dtype=int)


def estimate_qrs_width(ecg: np.ndarray, peaks: np.ndarray, fs_hz: int) -> float:
    if len(peaks) == 0:
        return 0.18
    detection = np.abs(ecg)
    widths = []
    search = max(2, int(round(0.16 * fs_hz)))
    for peak in peaks:
        left = max(0, int(peak) - search)
        right = min(len(ecg), int(peak) + search + 1)
        local = detection[left:right]
        if len(local) < 3:
            continue
        height = detection[peak]
        baseline = float(np.percentile(local, 20))
        half = baseline + 0.5 * (height - baseline)
        above = np.flatnonzero(local >= half)
        if len(above):
            widths.append((above[-1] - above[0] + 1) / float(fs_hz))
    if not widths:
        return 0.18
    return float(np.clip(np.median(widths), 0.04, 0.22))


def estimate_dominant_frequency(ecg: np.ndarray, fs_hz: int) -> float:
    if len(ecg) < 4:
        return 0.0
    windowed = (ecg - np.mean(ecg)) * np.hanning(len(ecg))
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    freqs = np.fft.rfftfreq(len(ecg), d=1.0 / fs_hz)
    mask = (freqs >= 0.5) & (freqs <= 20.0)
    if not np.any(mask) or np.max(spectrum[mask]) <= 0.0:
        return 0.0
    return float(freqs[mask][np.argmax(spectrum[mask])])


def estimate_spectral_entropy(ecg: np.ndarray, fs_hz: int) -> float:
    if len(ecg) < 4:
        return 1.0
    spectrum = np.abs(np.fft.rfft(ecg - np.mean(ecg))) ** 2
    freqs = np.fft.rfftfreq(len(ecg), d=1.0 / fs_hz)
    mask = (freqs >= 0.5) & (freqs <= 30.0)
    power = spectrum[mask]
    total = float(np.sum(power))
    if total <= 1e-12:
        return 1.0
    prob = power / total
    entropy = -float(np.sum(prob * np.log(prob + 1e-12)))
    return float(entropy / np.log(len(prob) + 1e-12))


def estimate_sample_entropy(ecg: np.ndarray, m: int = 2) -> float:
    if len(ecg) > 450:
        ecg = ecg[:: max(1, len(ecg) // 450)]
    if len(ecg) < m + 3:
        return 0.0
    r = 0.2 * np.std(ecg)
    if r <= 1e-12:
        return 0.0

    def count_matches(order: int) -> int:
        vectors = np.array([ecg[i : i + order] for i in range(len(ecg) - order + 1)])
        count = 0
        for i in range(len(vectors) - 1):
            distance = np.max(np.abs(vectors[i + 1 :] - vectors[i]), axis=1)
            count += int(np.sum(distance <= r))
        return count

    a = count_matches(m + 1)
    b = count_matches(m)
    if a == 0 or b == 0:
        return 2.5
    return float(-np.log(a / b))


def estimate_signal_quality(ecg: np.ndarray, finite_ratio: float) -> float:
    clipped = float(np.mean(np.abs(ecg) > 4.5))
    dynamic = float(np.percentile(ecg, 95) - np.percentile(ecg, 5))
    dynamic_score = np.clip(dynamic / 3.0, 0.0, 1.0)
    quality = finite_ratio * (1.0 - clipped) * dynamic_score
    return float(np.clip(quality, 0.0, 1.0))


def classify_acls_features(features: dict[str, float]) -> str:
    hr = features.get("heart_rate_bpm", 0.0)
    rr_cv = features.get("rr_cv", 1.0)
    qrs = features.get("qrs_width_s", 0.18)
    entropy = features.get("spectral_entropy", 1.0)
    sample_entropy = features.get("sample_entropy", 0.0)
    dom = features.get("dominant_frequency_hz", 0.0)

    if hr < 120.0 and qrs < 0.12 and rr_cv < 0.35:
        return "normal_or_sinus"
    if dom >= 5.0 and (
        sample_entropy >= 1.2 or (hr >= 130.0 and entropy >= 0.55 and rr_cv >= 0.22)
    ):
        return "vf_or_chaotic"
    if hr >= 150.0 and qrs >= 0.12 and (rr_cv >= 0.30 or entropy >= 0.36):
        return "irregular_wide_tachycardia"
    if hr >= 150.0 and qrs >= 0.12 and rr_cv < 0.30:
        return "regular_wide_tachycardia"
    if hr >= 150.0 and qrs >= 0.12:
        return "irregular_wide_tachycardia"
    if hr >= 150.0 and qrs < 0.12 and rr_cv < 0.22:
        return "regular_narrow_tachycardia"
    if hr >= 150.0:
        return "irregular_narrow_tachycardia"
    return "indeterminate"


def feature_vector(features: dict[str, float]) -> np.ndarray:
    raw = np.array([features.get(key, 0.0) for key in FEATURE_VECTOR_KEYS], dtype=float)
    scale = np.array(FEATURE_VECTOR_SCALES, dtype=float)
    return np.clip(raw / scale, 0.0, 3.0)


def _robust_normalize(ecg: np.ndarray) -> np.ndarray:
    centered = ecg - np.median(ecg)
    scale = np.percentile(np.abs(centered), 95)
    if scale <= 1e-8:
        scale = np.std(centered) + 1e-8
    return centered / scale
