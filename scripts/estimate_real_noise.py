from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vanderpol.stage6 import estimate_real_noise_stats, save_real_noise_stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="challenge-2015")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--records", nargs="+", required=True)
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--window-s", type=float, default=4.0)
    parser.add_argument("--stride-s", type=float, default=30.0)
    parser.add_argument("--max-windows-per-record", type=int, default=8)
    parser.add_argument("--output-json", type=Path, default=Path("outputs/real_noise_stats.json"))
    args = parser.parse_args()

    root = args.root or Path("data") / "raw" / args.dataset
    stats = estimate_real_noise_stats(
        root=root,
        dataset=args.dataset,
        records=args.records,
        channel=args.channel,
        window_s=args.window_s,
        stride_s=args.stride_s,
        max_windows_per_record=args.max_windows_per_record,
    )
    save_real_noise_stats(stats, args.output_json)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "dataset": stats.dataset,
                "n_windows": stats.n_windows,
                "acls_label_counts": stats.acls_label_counts,
                "recommended_profile": stats.recommended_profile.__dict__,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
