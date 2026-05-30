from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.noise import get_noise_profiles
from vanderpol.stage6 import load_noise_profile_from_stats
from vanderpol.stage7 import (
    fallback_threshold_sweep,
    load_profiles_from_category_stats,
    save_threshold_sweep,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=2)
    parser.add_argument("--profiles", nargs="*", default=["severe"])
    parser.add_argument("--real-noise-stats", type=Path, default=None)
    parser.add_argument("--category-noise-stats", type=Path, default=None)
    parser.add_argument("--min-sqi", type=float, nargs="+", default=[0.35, 0.42])
    parser.add_argument("--entropy", type=float, nargs="+", default=[0.62])
    parser.add_argument("--rr-cv", type=float, nargs="+", default=[0.30])
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/fallback_threshold_sweep.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/fallback_threshold_sweep.csv"))
    args = parser.parse_args()

    profiles = get_noise_profiles(args.profiles) if args.profiles else []
    if args.real_noise_stats is not None:
        profiles.append(load_noise_profile_from_stats(args.real_noise_stats))
    if args.category_noise_stats is not None:
        profiles.extend(load_profiles_from_category_stats(args.category_noise_stats))

    report = fallback_threshold_sweep(
        patients_per_scenario=args.patients_per_scenario,
        profiles=profiles,
        min_sqi_values=args.min_sqi,
        entropy_values=args.entropy,
        rr_cv_values=args.rr_cv,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_threshold_sweep(report, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "n_configs": len(report["configs"]),
                "profiles": [profile.name for profile in profiles],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
