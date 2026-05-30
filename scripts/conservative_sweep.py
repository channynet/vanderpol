from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.noise import get_noise_profiles
from vanderpol.stage6 import (
    conservative_noise_ood_sweep,
    load_noise_profile_from_stats,
    save_conservative_sweep,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=5)
    parser.add_argument("--profiles", nargs="+", default=["clean", "mild", "moderate", "severe"])
    parser.add_argument("--real-noise-stats", type=Path, default=None)
    parser.add_argument("--train-fraction", type=float, default=1.0)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--eval-variability", type=float, default=0.2)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/conservative_sweep.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/conservative_sweep.csv"))
    args = parser.parse_args()

    profiles = get_noise_profiles(args.profiles)
    if args.real_noise_stats is not None:
        profiles.append(load_noise_profile_from_stats(args.real_noise_stats))
    report = conservative_noise_ood_sweep(
        patients_per_scenario=args.patients_per_scenario,
        profiles=profiles,
        train_fraction=args.train_fraction,
        eval_variability=args.eval_variability,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_conservative_sweep(report, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "profiles": [profile.name for profile in profiles],
                "patients_per_scenario": args.patients_per_scenario,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
