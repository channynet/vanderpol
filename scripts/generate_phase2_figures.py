from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.reporting import generate_phase2_heatmaps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patients-per-scenario", type=int, default=5)
    parser.add_argument("--horizon-s", type=float, default=30.0)
    parser.add_argument("--n-jobs", default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args()

    outputs = generate_phase2_heatmaps(
        patients_per_scenario=args.patients_per_scenario,
        output_dir=args.output_dir,
        horizon_s=args.horizon_s,
        n_jobs=args.n_jobs,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
