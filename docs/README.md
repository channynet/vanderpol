# Documentation Index

This directory is now organized around one main path:

1. Read the project overview.
2. Check how data flows through the system.
3. Read the consolidated dashboard result.
4. Open the versioned baseline result and figure guide when you need detail.
5. Use the next-work document to decide what to improve.

## Start Here

| File | Purpose |
| --- | --- |
| [`00_start_here.md`](00_start_here.md) | Current project status and the minimum set of files to read. |
| [`final_result.md`](final_result.md) | Consolidated dashboard-facing final result across paper-ready runs. |
| [`dashboard_results_share.md`](dashboard_results_share.md) | How to share dashboard results through docs or GitHub. |
| [`final_result_runs.csv`](final_result_runs.csv) | Paper-ready run inventory used by the consolidated result. |
| [`01_system_pipeline.md`](01_system_pipeline.md) | How ECG input becomes features, treatment episodes, reward, and selector evaluation. |
| [`02_data_usage.md`](02_data_usage.md) | Which datasets are used, which are only validation data, and which are synthetic. |
| [`03_v001_result_summary.md`](03_v001_result_summary.md) | Clean summary of the first preserved versioned baseline run. |
| [`04_v001_figure_guide.md`](04_v001_figure_guide.md) | What each generated figure means. |
| [`05_next_work.md`](05_next_work.md) | Prioritized fixes for the next version. |

## Design Documents

| File | Purpose |
| --- | --- |
| [`design/uiux_redesign.md`](design/uiux_redesign.md) | Korean UI/UX redesign plan for analysis workflow, menu structure, parameter iteration, review pages, and React migration roadmap. |
| [`design/observability_dashboard.md`](design/observability_dashboard.md) | Observability and local dashboard implementation contract. |

## Current Shared Result

The current consolidated dashboard result is:

- [`final_result.md`](final_result.md)
- Primary evidence run: `outputs/runs/stage9_n100_time2`
- Run set: `71` paper-ready runs, `70` completed
- Scale: `100` patients per scenario, `30.0` second horizon

The first preserved versioned baseline remains:

- `outputs/versioned_runs/v001_full_pipeline`

Most important files in the versioned baseline:

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

The consolidated result supports scenario-specific electrical treatment choices
in the simulator.

The honest conclusion is:

- The primary manuscript-facing run is `stage9_n100_time2`, not the one-patient
  mutation runs.
- Versioned AI selector runs beat ACLS on average and in `3/4` comparable runs,
  but not consistently enough for an AI-over-ACLS claim.
- Scenario-specific best algorithms differ, so the selector problem is meaningful.
- Real-vs-synthetic ECG mismatch remains a major limitation.
- Reward, success, and safety are simulator outcomes, not clinical endpoints.
