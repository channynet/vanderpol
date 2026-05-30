from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.experiments import run_algorithm_matrix, summarize_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=3)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows, _, _, _, _ = run_algorithm_matrix(
        patients_per_scenario=args.patients_per_scenario,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    summary = summarize_matrix(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].__dict__.keys()))
            writer.writeheader()
            for row in rows:
                data = row.__dict__.copy()
                data["scenario"] = row.scenario.value
                writer.writerow(data)


if __name__ == "__main__":
    main()
