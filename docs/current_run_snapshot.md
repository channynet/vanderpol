# Current Result Snapshot

Current dashboard-facing result:

- `docs/final_result.md`
- `docs/final_result.json`
- `docs/final_result_runs.csv`

Primary evidence run:

- `outputs/runs/stage9_n100_time2`
- `100` patients per scenario
- `30.0` second horizon
- `4` noise profiles
- `12` fallback threshold configurations

Consolidated run set:

- `71` paper-ready runs considered
- `70` completed

Primary policy summary:

- ACLS rule reward: `66.045`
- ACLS rule success: `0.813`
- Oracle reward: `93.974`
- Oracle success: `0.980`

Versioned AI selector summary:

- Versioned runs considered: `4`
- Selector reward beats ACLS reward in `3/4` comparable runs
- Average selector reward: `87.625`
- Average ACLS rule reward: `75.901`
- Average oracle reward: `98.311`
- Latest realism validation run: `v004_existing_rhythm_realism_mitdb_cudb`

Use `docs/dashboard_results_share.md` as the handoff guide for GitHub or
document-based sharing.
