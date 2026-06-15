# Dashboard Results Sharing Guide

This file is the handoff map for sharing the dashboard results with someone
who does not have the local dashboard open.

## Share These First

| File | Use |
| --- | --- |
| [`dashboard/index.html`](dashboard/index.html) | Static dashboard snapshot for GitHub Pages or direct browser sharing. |
| [`final_result.md`](final_result.md) | Human-readable final result and main conclusion. |
| [`final_result.json`](final_result.json) | Machine-readable payload used by the dashboard final-result view. |
| [`final_result_runs.csv`](final_result_runs.csv) | Inventory of paper-ready runs included in the consolidated result. |
| [`paper_all_data.md`](paper_all_data.md) | Longer manuscript data compendium from the paper artifact set. |

## Current Dashboard Headline

- Primary evidence run: `stage9_n100_time2`.
- Consolidated run set: `71` paper-ready runs, `70` completed.
- Primary scale: `100` patients per scenario, `30.0` second horizon.
- Versioned AI selector comparison: `4` completed selector-evaluated runs.
- Selector-vs-ACLS result: selector reward beats ACLS reward in `3/4`
  comparable versioned runs and beats ACLS on average, but not consistently.
- Latest realism validation: `v004_existing_rhythm_realism_mitdb_cudb`,
  with residual real-vs-synthetic mismatch still too large for a clinical
  performance claim.

## What The Dashboard Shows

The local dashboard exposes these result surfaces:

| Dashboard area | Source |
| --- | --- |
| Runs | `outputs/runs/*` manifests and progress files. |
| Consolidated Final Result | `docs/final_result.md` and `docs/final_result.json`. |
| Paper Data | `docs/paper_all_data.md` plus selected paper artifacts. |
| Final Results | `outputs/versioned_runs/v001_*` through `v004_*` selector and realism artifacts. |
| Intermediate/System Results | Selected run artifacts under `outputs/runs/<run_id>/`. |

`outputs/` is intentionally ignored by Git, so GitHub sharing should rely on
the `docs/final_result.*` files unless the full run artifact folders are being
shared by another storage channel.

## Static GitHub Pages Dashboard

The static dashboard is generated at:

- [`dashboard/index.html`](dashboard/index.html)

It embeds the consolidated final result payload, so it works without the local
Python API server.

If GitHub Pages is configured to publish from the `docs/` folder on `main`, the
public URL is:

```text
https://channynet.github.io/vanderpol/dashboard/
```

## Rebuild The Shareable Files

Run this from the repository root:

```powershell
$env:PYTHONPATH='src'
python scripts/generate_final_result.py
python scripts/generate_static_dashboard.py
```

The command refreshes:

- `docs/dashboard/index.html`
- `docs/final_result.md`
- `docs/final_result.json`
- `docs/final_result_runs.csv`

## Open The Dashboard Locally

```powershell
$env:PYTHONPATH='src'
python scripts/serve_dashboard.py --runs-dir outputs/runs --port 8765
```

Then open:

- `http://127.0.0.1:8765/?tab=runs`
- `http://127.0.0.1:8765/?tab=paper`
- `http://127.0.0.1:8765/?tab=final`

Useful raw endpoints:

- `http://127.0.0.1:8765/api/final-result/raw`
- `http://127.0.0.1:8765/api/final-result`
- `http://127.0.0.1:8765/api/ai-model-runs`
- `http://127.0.0.1:8765/api/paper-compendium/raw`

## Suggested GitHub Scope

For a clean sharing commit, include:

- `README.md`
- `docs/README.md`
- `docs/00_start_here.md`
- `docs/current_run_snapshot.md`
- `docs/dashboard_results_share.md`
- `docs/dashboard/index.html`
- `docs/final_result.md`
- `docs/final_result.json`
- `docs/final_result_runs.csv`
- `scripts/generate_final_result.py`
- `scripts/generate_static_dashboard.py`
- `scripts/serve_dashboard.py`
- `src/vanderpol/dashboard.py`
- `tests/test_dashboard.py`
- `tests/test_static_dashboard.py`
- `configs/bundle_n20_ai_selector.json`

Do not include `outputs/` in the GitHub commit. It is ignored because the full
run artifacts are large and workspace-specific.

Also do not include `vendor/` unless the dashboard asset strategy is changed on
purpose. The current local `vendor/` folder is a large external UI template
cache, not a result artifact.

Suggested command sequence once GitHub CLI/auth is available:

```powershell
git checkout -b codex/share-dashboard-results
git add README.md docs/README.md docs/00_start_here.md docs/current_run_snapshot.md
git add docs/dashboard_results_share.md docs/dashboard/index.html docs/final_result.md docs/final_result.json docs/final_result_runs.csv
git add scripts/generate_final_result.py scripts/generate_static_dashboard.py scripts/serve_dashboard.py src/vanderpol/dashboard.py
git add tests/test_dashboard.py tests/test_static_dashboard.py
git add configs/bundle_n20_ai_selector.json
git commit -m "Publish static dashboard results"
git push -u origin codex/share-dashboard-results
```

## Required Guardrail

This project is a research simulator. External ECG data is used for observation
realism and validation. Reward, treatment success, safety, and policy
performance are simulator outcomes, not clinical endpoints.
