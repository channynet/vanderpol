from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage5 import save_selector_stability, selector_stability_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=8)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 7, 13])
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/selector_stability.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/selector_stability.csv"))
    args = parser.parse_args()

    report = selector_stability_report(
        patients_per_scenario=args.patients_per_scenario,
        seeds=args.seeds,
        train_fraction=args.train_fraction,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_selector_stability(report, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "patients_per_scenario": args.patients_per_scenario,
                "seeds": args.seeds,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
