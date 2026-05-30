from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.reporting import build_selector_report, save_selector_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=8)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/selector_report.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/selector_report.csv"))
    args = parser.parse_args()

    report = build_selector_report(
        patients_per_scenario=args.patients_per_scenario,
        train_fraction=args.train_fraction,
        seed=args.seed,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_selector_report(report, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "n_train": report.n_train,
                "n_eval": report.n_eval,
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "policy_summary": report.policy_summary,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
