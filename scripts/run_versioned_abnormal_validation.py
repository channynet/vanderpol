from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_real_synthetic_abnormal import run_comparison  # noqa: E402
from vanderpol.versioning import create_versioned_run_dir, write_version_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-csv", type=Path, default=Path("outputs/mitdb_abnormal_windows.csv"))
    parser.add_argument("--cudb-csv", type=Path, default=Path("outputs/cudb_annotated_vt_vf.csv"))
    parser.add_argument("--skip-cudb", action="store_true")
    parser.add_argument("--version-root", type=Path, default=Path("outputs/versioned_runs"))
    parser.add_argument("--label", default="real_vs_synthetic_abnormal_validation")
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument("--patients-per-scenario", type=int, default=200)
    parser.add_argument("--fs-hz", type=int, default=250)
    parser.add_argument("--observation-s", type=float, default=4.0)
    parser.add_argument("--variability", type=float, default=0.2)
    parser.add_argument("--seed-offset", type=int, default=150_000)
    args = parser.parse_args()

    run_dir = create_versioned_run_dir(
        root=args.version_root,
        label=args.label,
        version=args.version,
    )
    comparison_dir = run_dir / "comparison"
    extra_real_csvs = []
    if not args.skip_cudb and args.cudb_csv.exists():
        extra_real_csvs.append(args.cudb_csv)
    parameters = {
        "real_csv": str(args.real_csv),
        "extra_real_csvs": [str(path) for path in extra_real_csvs],
        "patients_per_scenario": args.patients_per_scenario,
        "fs_hz": args.fs_hz,
        "observation_s": args.observation_s,
        "variability": args.variability,
        "seed_offset": args.seed_offset,
    }
    manifest = run_comparison(
        real_csv=args.real_csv,
        extra_real_csvs=extra_real_csvs,
        output_dir=comparison_dir,
        patients_per_scenario=args.patients_per_scenario,
        fs_hz=args.fs_hz,
        observation_s=args.observation_s,
        variability=args.variability,
        seed_offset=args.seed_offset,
    )
    version_manifest = write_version_manifest(
        run_dir,
        experiment=args.label,
        parameters=parameters,
        outputs={
            "comparison_manifest": str(comparison_dir / "real_vs_synthetic_abnormal_manifest.json"),
            "comparison_dir": str(comparison_dir),
        },
    )
    summary = render_summary(run_dir, manifest, version_manifest)
    summary_path = run_dir / "README.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "version_manifest": str(version_manifest),
                "summary_path": str(summary_path),
                "comparison_manifest": str(comparison_dir / "real_vs_synthetic_abnormal_manifest.json"),
                "status": manifest["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def render_summary(run_dir: Path, manifest: dict, version_manifest: Path) -> str:
    return "\n".join(
        [
            "# Versioned Result",
            "",
            f"- Run directory: `{run_dir}`",
            f"- Version manifest: `{version_manifest}`",
            f"- Real ECG rows: `{manifest['n_real_rows']}`",
            f"- Real source counts: `{manifest.get('real_source_counts', {})}`",
            f"- Synthetic rows: `{manifest['n_synthetic_rows']}`",
            f"- Comparison output directory: `{manifest['output_dir']}`",
            "",
            "## Main Files",
            "",
            f"- Distance table: `{manifest['distance_csv']}`",
            f"- Group summary: `{manifest['summary_csv']}`",
            f"- Unmatched real labels: `{manifest['unmatched_csv']}`",
            f"- SMD heatmap: `{manifest['figures'].get('smd_heatmap', '')}`",
            f"- KS heatmap: `{manifest['figures'].get('ks_heatmap', '')}`",
            f"- PCA plot: `{manifest['figures'].get('pca_scatter', '')}`",
            "",
        ]
    )


if __name__ == "__main__":
    main()
