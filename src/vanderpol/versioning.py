"""Utilities for storing experiment outputs in versioned folders."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VERSION_RE = re.compile(r"^v(?P<index>\d{3,})(?:_|$)")


def sanitize_label(label: str) -> str:
    """Return a filesystem-friendly experiment label."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", label.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned or "experiment"


def next_version_index(root: str | Path) -> int:
    """Return the next integer version index under a version root."""
    root = Path(root)
    if not root.exists():
        return 1
    indices = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        match = VERSION_RE.match(child.name)
        if match:
            indices.append(int(match.group("index")))
    return max(indices, default=0) + 1


def create_versioned_run_dir(
    root: str | Path = "outputs/versioned_runs",
    label: str = "experiment",
    version: int | None = None,
) -> Path:
    """Create and return a new run directory like ``v001_label``."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    version = next_version_index(root) if version is None else int(version)
    safe_label = sanitize_label(label)
    base = root / f"v{version:03d}_{safe_label}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base.name}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def write_version_manifest(
    run_dir: str | Path,
    *,
    experiment: str,
    parameters: dict[str, Any],
    outputs: dict[str, Any] | None = None,
) -> Path:
    """Write a small manifest documenting what a versioned folder contains."""
    run_dir = Path(run_dir)
    manifest = {
        "experiment": experiment,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "run_dir": str(run_dir),
        "parameters": parameters,
        "outputs": outputs or {},
    }
    path = run_dir / "version_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
