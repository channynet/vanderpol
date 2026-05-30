from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage5 import noise_ood_sweep, save_noise_ood_sweep


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=5)
    parser.add_argument("--profiles", nargs="+", default=["clean", "mild", "moderate", "severe"])
    parser.add_argument("--train-fraction", type=float, default=1.0)
    parser.add_argument("--train-variability", type=float, default=0.2)
    parser.add_argument("--eval-variability", type=float, default=0.2)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/noise_ood_sweep.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/noise_ood_sweep.csv"))
    args = parser.parse_args()

    report = noise_ood_sweep(
        patients_per_scenario=args.patients_per_scenario,
        profile_names=args.profiles,
        train_fraction=args.train_fraction,
        train_variability=args.train_variability,
        eval_variability=args.eval_variability,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_noise_ood_sweep(report, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "profiles": args.profiles,
                "patients_per_scenario": args.patients_per_scenario,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
