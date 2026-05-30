from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.reporting import decision_boundary_grid, save_decision_boundary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=8)
    parser.add_argument("--grid-size", type=int, default=60)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-png", type=Path, default=Path("outputs/figures/decision_boundary.png"))
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/decision_boundary.csv"))
    args = parser.parse_args()

    grid = decision_boundary_grid(
        patients_per_scenario=args.patients_per_scenario,
        grid_size=args.grid_size,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    save_decision_boundary(grid, args.output_png, args.output_csv)
    print(
        json.dumps(
            {
                "output_png": str(args.output_png),
                "output_csv": str(args.output_csv),
                "grid_size": args.grid_size,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
