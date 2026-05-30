from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.calibration import run_calibration_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/calibration.json"))
    parser.add_argument("--patients-per-scenario", type=int, default=10)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = run_calibration_matrix(
        patients_per_scenario=args.patients_per_scenario,
        target_path=args.config,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
