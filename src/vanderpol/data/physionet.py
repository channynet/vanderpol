"""Small PhysioNet download helpers for WFDB record files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlretrieve


class DownloadError(RuntimeError):
    """Raised when a PhysioNet file cannot be downloaded."""


@dataclass(frozen=True)
class PhysioNetDataset:
    key: str
    slug: str
    version: str
    default_extensions: tuple[str, ...]

    @property
    def base_url(self) -> str:
        return f"https://physionet.org/files/{self.slug}/{self.version}"


PHYSIONET_DATASETS: dict[str, PhysioNetDataset] = {
    "mitdb": PhysioNetDataset(
        key="mitdb",
        slug="mitdb",
        version="1.0.0",
        default_extensions=(".hea", ".dat", ".atr"),
    ),
    "cudb": PhysioNetDataset(
        key="cudb",
        slug="cudb",
        version="1.0.0",
        default_extensions=(".hea", ".dat", ".atr"),
    ),
    "challenge-2015": PhysioNetDataset(
        key="challenge-2015",
        slug="challenge-2015",
        version="1.0.0",
        default_extensions=(".hea", ".mat"),
    ),
    "ptb-xl": PhysioNetDataset(
        key="ptb-xl",
        slug="ptb-xl",
        version="1.0.3",
        default_extensions=(".hea", ".dat"),
    ),
}


def list_remote_records(dataset_key: str) -> list[str]:
    dataset = _dataset(dataset_key)
    url = _records_url(dataset)
    try:
        with urlopen(url, timeout=30) as response:
            text = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DownloadError(f"Could not read {url}: {exc}") from exc
    return [line.strip() for line in text.splitlines() if line.strip()]


def download_records(
    dataset_key: str,
    records: list[str] | None,
    destination: str | Path,
    limit: int | None = None,
    extensions: tuple[str, ...] | None = None,
) -> list[Path]:
    """Download selected WFDB files from PhysioNet.

    This intentionally avoids the WFDB package so data can be fetched before the
    optional reader dependency is installed.
    """

    dataset = _dataset(dataset_key)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    selected = list(records or list_remote_records(dataset_key))
    if limit is not None:
        selected = selected[:limit]
    exts = extensions or dataset.default_extensions

    downloaded: list[Path] = []
    for record in selected:
        for ext in exts:
            remote = f"{_record_base_url(dataset)}/{record}{ext}"
            local = destination / f"{record}{ext}"
            local.parent.mkdir(parents=True, exist_ok=True)
            try:
                urlretrieve(remote, local)
            except (HTTPError, URLError, TimeoutError) as exc:
                if ext in {".atr", ".al"}:
                    continue
                raise DownloadError(f"Could not download {remote}: {exc}") from exc
            downloaded.append(local)
    return downloaded


def download_dataset_file(
    dataset_key: str,
    filename: str,
    destination: str | Path,
) -> Path:
    dataset = _dataset(dataset_key)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    remote = f"{_record_base_url(dataset)}/{filename}"
    local = destination / filename
    try:
        urlretrieve(remote, local)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DownloadError(f"Could not download {remote}: {exc}") from exc
    return local


def _dataset(dataset_key: str) -> PhysioNetDataset:
    try:
        return PHYSIONET_DATASETS[dataset_key]
    except KeyError as exc:
        known = ", ".join(sorted(PHYSIONET_DATASETS))
        raise DownloadError(f"Unknown dataset `{dataset_key}`. Known: {known}.") from exc


def _record_base_url(dataset: PhysioNetDataset) -> str:
    if dataset.key == "challenge-2015":
        return f"{dataset.base_url}/training"
    return dataset.base_url


def _records_url(dataset: PhysioNetDataset) -> str:
    return f"{_record_base_url(dataset)}/RECORDS"
