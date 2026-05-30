from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage5 import run_bootstrap_matrix_report, save_bootstrap_ci


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=10)
    parser.add_argument("--n-bootstrap", type=int, default=200)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/bootstrap_matrix_ci.csv"))
    args = parser.parse_args()

    rows = run_bootstrap_matrix_report(
        patients_per_scenario=args.patients_per_scenario,
        n_bootstrap=args.n_bootstrap,
        horizon_s=args.horizon_s,
        seed=args.seed,
        n_jobs=args.n_jobs,
    )
    save_bootstrap_ci(rows, args.output_csv)
    print(
        json.dumps(
            {
                "output_csv": str(args.output_csv),
                "n_rows": len(rows),
                "patients_per_scenario": args.patients_per_scenario,
                "n_bootstrap": args.n_bootstrap,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
