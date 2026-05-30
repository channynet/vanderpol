from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.validation import (
    FEATURE_KEYS,
    compare_feature_summaries,
    summarize_feature_dicts,
    synthetic_feature_summaries,
)


def _read_feature_csv(path: Path) -> list[dict[str, float]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append({key: float(row[key]) for key in FEATURE_KEYS if row.get(key) not in {None, ""}})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-csv", type=Path, required=True)
    parser.add_argument("--real-group", default="real_ecg")
    parser.add_argument("--patients-per-scenario", type=int, default=20)
    args = parser.parse_args()

    real_features = _read_feature_csv(args.real_csv)
    real_summary = summarize_feature_dicts(real_features, group=args.real_group)
    synthetic = synthetic_feature_summaries(patients_per_scenario=args.patients_per_scenario)
    comparisons = {
        summary.group: compare_feature_summaries(summary, real_summary)
        for summary in synthetic
    }
    print(
        json.dumps(
            {
                "real_summary": real_summary.__dict__,
                "synthetic_to_real_standardized_mean_gaps": comparisons,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
