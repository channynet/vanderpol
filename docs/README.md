# Documentation Index

This directory is now organized around one main path:

1. Read the project overview.
2. Check how data flows through the system.
3. Read the current `v001_full_pipeline` result.
4. Open the figure guide.
5. Use the next-work document to decide what to improve.

## Start Here

| File | Purpose |
| --- | --- |
| [`00_start_here.md`](00_start_here.md) | Current project status and the minimum set of files to read. |
| [`01_system_pipeline.md`](01_system_pipeline.md) | How ECG input becomes features, treatment episodes, reward, and selector evaluation. |
| [`02_data_usage.md`](02_data_usage.md) | Which datasets are used, which are only validation data, and which are synthetic. |
| [`03_v001_result_summary.md`](03_v001_result_summary.md) | Clean summary of the latest saved run. |
| [`04_v001_figure_guide.md`](04_v001_figure_guide.md) | What each generated figure means. |
| [`05_next_work.md`](05_next_work.md) | Prioritized fixes for the next version. |

## Design Documents

| File | Purpose |
| --- | --- |
| [`design/uiux_redesign.md`](design/uiux_redesign.md) | Korean UI/UX redesign plan for analysis workflow, menu structure, parameter iteration, review pages, and React migration roadmap. |
| [`design/observability_dashboard.md`](design/observability_dashboard.md) | Observability and local dashboard implementation contract. |

## Current Saved Run

The current baseline run is:

- `outputs/versioned_runs/v001_full_pipeline`

Most important files in that run:

| File | Purpose |
| --- | --- |
| `README.md` | Run-level entry point. |
| `STATUS_SNAPSHOT.md` | Frozen status snapshot after completion. |
| `RESULT_INTERPRETATION.md` | Main interpretation of the result. |
| `executive_summary.md` | Auto-generated run summary. |
| `process_visualizations/` | Step-by-step figures. |
| `paper_artifacts/` | Paper/presentation tables and summary files. |

## Older And Detailed Notes

The following files are still useful, but they are not the primary reading path:

| File | Role |
| --- | --- |
| `stage_status.md` | Older stage-by-stage implementation status. |
| `stage4_reporting.md` to `stage9_paper_artifacts.md` | Historical stage notes. |
| `data_requirements.md` | External data requirements. |
| `mitdb_abnormal_data.md` | MIT-BIH abnormal rhythm extraction notes. |
| `real_vs_synthetic_abnormal_validation.md` | Real vs synthetic abnormal ECG validation notes. |
| `results_summary.md`, `results_only.md`, `paper_all_data.md` | Earlier generated result summaries. |

## Current Headline

The current result is not yet an AI-over-ACLS result.

The honest conclusion is:

- The full simulation-to-selector pipeline works.
- Scenario-specific best algorithms differ, so the selector problem is meaningful.
- The current LinUCB selector beats fixed always-action baselines.
- The current LinUCB selector does not beat the ACLS-rule baseline.
- The biggest problems are decision-boundary collapse and noise sensitivity.
