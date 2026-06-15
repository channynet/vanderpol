from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static GitHub Pages dashboard from final_result artifacts.")
    parser.add_argument("--input-json", type=Path, default=Path("docs/final_result.json"))
    parser.add_argument("--input-md", type=Path, default=Path("docs/final_result.md"))
    parser.add_argument("--output", type=Path, default=Path("docs/dashboard/index.html"))
    args = parser.parse_args()

    output = generate_static_dashboard(args.input_json, args.input_md, args.output)
    print(json.dumps({"output": str(output)}, indent=2))


def generate_static_dashboard(input_json: Path, input_md: Path, output: Path) -> Path:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    markdown = input_md.read_text(encoding="utf-8") if input_md.exists() else ""
    bundle = {
        "exported_at": datetime.now(UTC).isoformat(),
        "final_result": payload,
        "final_markdown": markdown,
        "source_files": {
            "final_result_json": str(input_json),
            "final_result_markdown": str(input_md),
        },
    }
    embedded = json.dumps(bundle, ensure_ascii=True, sort_keys=True).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DASHBOARD_DATA__", embedded)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vanderpol Static Result Dashboard</title>
  <style>
    :root {
      --paper: #f8f8f3;
      --surface: #ffffff;
      --surface-soft: #f1f4ef;
      --ink: #25312c;
      --muted: #63716a;
      --line: #d9ded6;
      --teal: #24786a;
      --blue: #426d9c;
      --green: #3f7d45;
      --amber: #b27424;
      --red: #b84a43;
      --violet: #755f99;
      --shadow: 0 12px 30px rgba(37, 49, 44, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }
    a { color: var(--blue); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .shell { min-height: 100vh; display: grid; grid-template-columns: 248px minmax(0, 1fr); }
    .side {
      position: sticky;
      top: 0;
      height: 100vh;
      border-right: 1px solid var(--line);
      background: var(--surface);
      padding: 22px 18px;
      overflow: auto;
    }
    .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; }
    .brandMark {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      background: var(--teal);
      color: white;
      font-weight: 700;
    }
    .brand h1 { font-size: 17px; line-height: 1.2; margin: 0; }
    .brand p { margin: 2px 0 0; color: var(--muted); font-size: 12px; }
    .nav { display: grid; gap: 6px; }
    .nav button {
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      color: var(--muted);
      border-radius: 8px;
      padding: 10px 11px;
      text-align: left;
      cursor: pointer;
      font-size: 14px;
    }
    .nav button.active {
      color: var(--ink);
      background: var(--surface-soft);
      border-color: var(--line);
      font-weight: 700;
    }
    .sideLinks { display: grid; gap: 8px; margin-top: 22px; }
    .sideLinks a {
      display: block;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: var(--surface);
      color: var(--ink);
      font-size: 13px;
    }
    .main { min-width: 0; }
    .top {
      position: sticky;
      top: 0;
      z-index: 3;
      border-bottom: 1px solid var(--line);
      background: rgba(248, 248, 243, 0.94);
      backdrop-filter: blur(10px);
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .top h2 { margin: 0; font-size: 20px; }
    .top p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .topActions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
    .linkButton {
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 11px;
      background: var(--surface);
      color: var(--ink);
      font-size: 13px;
    }
    .content { padding: 24px; max-width: 1380px; }
    .view { display: none; }
    .view.active { display: block; }
    .grid { display: grid; gap: 16px; }
    .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .two { grid-template-columns: minmax(0, 1fr) minmax(360px, 0.72fr); align-items: start; }
    .three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: var(--shadow);
    }
    .card h3 { margin: 0 0 12px; font-size: 16px; }
    .card h4 { margin: 0 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; }
    .kpiValue { font-size: 26px; font-weight: 800; line-height: 1.1; }
    .kpiMeta { color: var(--muted); font-size: 12px; margin-top: 5px; }
    .guardrail {
      border-left: 5px solid var(--amber);
      background: #fff7e8;
      color: #6f4817;
      box-shadow: none;
    }
    .claimList { margin: 0; padding-left: 18px; color: var(--ink); }
    .claimList li { margin: 7px 0; }
    .tableWrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { background: var(--surface-soft); color: var(--muted); font-weight: 700; white-space: nowrap; }
    tr:last-child td { border-bottom: 0; }
    code {
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 2px 5px;
      font-family: Consolas, Menlo, monospace;
      font-size: 12px;
    }
    .barRows { display: grid; gap: 11px; }
    .barRow { display: grid; grid-template-columns: minmax(130px, 0.55fr) minmax(120px, 1fr) 72px; gap: 10px; align-items: center; font-size: 13px; }
    .barTrack { height: 12px; background: var(--surface-soft); border: 1px solid var(--line); border-radius: 999px; overflow: hidden; }
    .barFill { display: block; height: 100%; background: var(--teal); width: 0; }
    .barFill.blue { background: var(--blue); }
    .barFill.green { background: var(--green); }
    .barFill.amber { background: var(--amber); }
    .barFill.red { background: var(--red); }
    .barFill.violet { background: var(--violet); }
    .pill {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      background: var(--surface-soft);
      color: var(--ink);
      font-size: 12px;
      white-space: nowrap;
    }
    .filters { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
    input, select {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      padding: 9px 10px;
      min-height: 38px;
      font: inherit;
      font-size: 13px;
    }
    input { min-width: 260px; }
    .muted { color: var(--muted); }
    .small { font-size: 12px; }
    .metricSplit { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .metricBox { border: 1px solid var(--line); border-radius: 8px; padding: 11px; background: var(--surface-soft); }
    .metricBox b { display: block; font-size: 20px; margin-top: 3px; }
    .markdown {
      white-space: pre-wrap;
      font-family: Consolas, Menlo, monospace;
      font-size: 12px;
      line-height: 1.55;
      max-height: 72vh;
      overflow: auto;
      background: #1f2925;
      color: #f2f4ee;
      border-radius: 8px;
      padding: 16px;
    }
    .empty { color: var(--muted); padding: 18px; }
    @media (max-width: 1100px) {
      .shell { grid-template-columns: 1fr; }
      .side { position: relative; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }
      .nav { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .two, .three, .kpis { grid-template-columns: 1fr; }
      .top { position: relative; align-items: flex-start; flex-direction: column; }
      .topActions { justify-content: flex-start; }
    }
    @media (max-width: 640px) {
      .content, .top, .side { padding: 16px; }
      .nav { grid-template-columns: 1fr; }
      .barRow { grid-template-columns: 1fr; gap: 5px; }
      input { width: 100%; min-width: 0; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="brandMark">V</div>
        <div>
          <h1>Vanderpol</h1>
          <p>Static result dashboard</p>
        </div>
      </div>
      <nav class="nav" aria-label="Dashboard sections">
        <button type="button" data-view="overview" class="active">Overview</button>
        <button type="button" data-view="primary">Primary Run</button>
        <button type="button" data-view="versioned">Versioned AI</button>
        <button type="button" data-view="realism">Realism</button>
        <button type="button" data-view="runs">Run Inventory</button>
        <button type="button" data-view="markdown">Markdown</button>
      </nav>
      <div class="sideLinks">
        <a href="../final_result.md">final_result.md</a>
        <a href="../final_result.json">final_result.json</a>
        <a href="../final_result_runs.csv">final_result_runs.csv</a>
        <a href="../paper_all_data.md">paper_all_data.md</a>
      </div>
    </aside>
    <main class="main">
      <header class="top">
        <div>
          <h2>Vanderpol ECG Electrical-Stimulation Selector</h2>
          <p id="subtitle">Loading static snapshot</p>
        </div>
        <div class="topActions">
          <a class="linkButton" href="../final_result.md">Open Result</a>
          <a class="linkButton" href="../dashboard_results_share.md">Share Guide</a>
          <a class="linkButton" href="../../README.md">Repository README</a>
        </div>
      </header>
      <div class="content">
        <section id="view-overview" class="view active">
          <div id="overviewKpis" class="grid kpis"></div>
          <div class="grid two" style="margin-top:16px">
            <div class="card">
              <h3>Versioned Selector vs ACLS</h3>
              <div id="versionedRewardBars" class="barRows"></div>
            </div>
            <div class="card guardrail">
              <h3>Required Guardrail</h3>
              <p>This is a research simulator. External ECG data is used for observation realism and validation. Reward, treatment success, safety, and policy performance are simulator outcomes, not clinical endpoints.</p>
            </div>
          </div>
          <div class="grid two" style="margin-top:16px">
            <div class="card">
              <h3>Conclusion</h3>
              <p id="headline"></p>
              <ul id="claimList" class="claimList"></ul>
            </div>
            <div class="card">
              <h3>Primary Scenario Actions</h3>
              <div id="scenarioOverview"></div>
            </div>
          </div>
        </section>

        <section id="view-primary" class="view">
          <div class="grid two">
            <div class="card">
              <h3>Primary Run Metrics</h3>
              <div id="primaryPolicyBars" class="barRows"></div>
            </div>
            <div class="card">
              <h3>Primary Run Metadata</h3>
              <div id="primaryMeta" class="metricSplit"></div>
            </div>
          </div>
          <div class="card" style="margin-top:16px">
            <h3>Scenario-Level Final Actions</h3>
            <div id="primaryScenarios"></div>
          </div>
          <div class="card" style="margin-top:16px">
            <h3>Noise Robustness</h3>
            <div id="noiseSummary"></div>
          </div>
        </section>

        <section id="view-versioned" class="view">
          <div class="grid three" id="versionedKpis"></div>
          <div class="card" style="margin-top:16px">
            <h3>Versioned Run Table</h3>
            <div id="versionedRuns"></div>
          </div>
          <div class="card" style="margin-top:16px">
            <h3>Scenario Consensus</h3>
            <div id="scenarioConsensus"></div>
          </div>
        </section>

        <section id="view-realism" class="view">
          <div class="grid three" id="realismKpis"></div>
          <div class="card" style="margin-top:16px">
            <h3>Realism Validation By Version</h3>
            <div id="realismRuns"></div>
          </div>
        </section>

        <section id="view-runs" class="view">
          <div class="card">
            <h3>Paper-Ready Run Inventory</h3>
            <div class="filters">
              <input id="runSearch" type="search" placeholder="Search run id or preset">
              <select id="statusFilter"></select>
              <select id="presetFilter"></select>
            </div>
            <div id="runInventory"></div>
          </div>
        </section>

        <section id="view-markdown" class="view">
          <div class="card">
            <h3>Final Result Markdown Snapshot</h3>
            <div id="markdownSnapshot" class="markdown"></div>
          </div>
        </section>
      </div>
    </main>
  </div>
  <script id="dashboard-data" type="application/json">__DASHBOARD_DATA__</script>
  <script>
    const bundle = JSON.parse(document.getElementById('dashboard-data').textContent);
    const data = bundle.final_result || {};
    const primary = data.primary_run || {};
    const versioned = data.versioned_ai_model_results || {};
    const conclusion = versioned.conclusion || {};
    const evidence = conclusion.selector_evidence || {};
    const realismEvidence = conclusion.realism_evidence || {};
    const aggregate = versioned.aggregate || {};
    const realismAggregate = versioned.realism_aggregate || {};
    const policyNames = {
      selector_linucb: 'Selector LinUCB',
      acls_rule: 'ACLS-rule baseline',
      oracle: 'Oracle',
      always_synchronized_cardioversion: 'Always synchronized cardioversion',
      always_unsynchronized_defibrillation: 'Always unsynchronized defibrillation',
      always_atp: 'Always ATP',
      always_resonant_drift: 'Always resonant drift',
      always_adaptive: 'Always adaptive low-energy pacing'
    };
    const scenarioNames = {
      monomorphic_vt: 'Monomorphic VT',
      nsr: 'Normal sinus rhythm',
      polymorphic_vt: 'Polymorphic VT',
      svt_flutter: 'SVT/flutter',
      vf_like: 'VF-like'
    };

    function esc(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function num(value) {
      const n = Number(value);
      return Number.isFinite(n) ? n : null;
    }
    function fmt(value, digits = 3) {
      const n = num(value);
      return n === null ? '' : n.toFixed(digits);
    }
    function pct(value) {
      const n = num(value);
      return n === null ? '' : (n * 100).toFixed(1) + '%';
    }
    function width(value, maxValue) {
      const n = num(value);
      const m = num(maxValue) || 1;
      if (n === null) return 0;
      return Math.max(0, Math.min(100, (n / m) * 100));
    }
    function card(label, value, meta) {
      return `<div class="card"><h4>${esc(label)}</h4><div class="kpiValue">${esc(value)}</div><div class="kpiMeta">${esc(meta || '')}</div></div>`;
    }
    function metricBox(label, value, meta) {
      return `<div class="metricBox"><span class="small muted">${esc(label)}</span><b>${esc(value)}</b><span class="small muted">${esc(meta || '')}</span></div>`;
    }
    function barRows(rows, maxValue) {
      const colors = ['teal', 'blue', 'green', 'amber', 'red', 'violet'];
      return rows.map((row, index) => {
        const color = colors[index % colors.length];
        const fillClass = color === 'teal' ? '' : ` ${color}`;
        return `<div class="barRow"><span>${esc(row.label)}</span><span class="barTrack"><i class="barFill${fillClass}" style="width:${width(row.value, maxValue)}%"></i></span><strong>${fmt(row.value)}</strong></div>`;
      }).join('');
    }
    function table(headers, rows) {
      if (!rows.length) return '<div class="empty">No rows available.</div>';
      return `<div class="tableWrap"><table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
    }
    function policyMetricRows(metrics, includeAlways = false) {
      const order = includeAlways
        ? ['selector_linucb','acls_rule','oracle','always_synchronized_cardioversion','always_unsynchronized_defibrillation','always_atp','always_resonant_drift','always_adaptive']
        : ['selector_linucb','acls_rule','oracle'];
      return order
        .map(key => {
          const metric = metrics[key];
          if (!metric) return null;
          return { key, label: metric.policy || policyNames[key] || key, value: metric.mean_reward, metric };
        })
        .filter(Boolean);
    }

    function renderOverview() {
      const selectorDelta = fmt(evidence.reward_delta_vs_acls);
      document.getElementById('subtitle').textContent = `Static snapshot generated ${bundle.exported_at || data.generated_at || ''}`;
      document.getElementById('overviewKpis').innerHTML = [
        card('Primary run', primary.run_id || '', `${primary.patients_per_scenario || ''} patients/scenario`),
        card('Paper-ready runs', `${data.completed_run_count || 0}/${data.run_count || 0}`, 'completed / considered'),
        card('Selector delta', selectorDelta ? `+${selectorDelta}` : '', 'average reward vs ACLS'),
        card('Latest realism SMD', fmt(realismEvidence.latest_mean_smd_abs), realismEvidence.latest_run_id || '')
      ].join('');
      const selector = aggregate.selector_model_average || {};
      const acls = aggregate.acls_rule_average || {};
      const oracle = aggregate.oracle_average || {};
      const maxReward = Math.max(num(selector.mean_reward) || 0, num(acls.mean_reward) || 0, num(oracle.mean_reward) || 0, 100);
      document.getElementById('versionedRewardBars').innerHTML = barRows([
        { label: 'Selector LinUCB', value: selector.mean_reward },
        { label: 'ACLS-rule baseline', value: acls.mean_reward },
        { label: 'Oracle', value: oracle.mean_reward }
      ], maxReward);
      document.getElementById('headline').textContent = conclusion.headline || 'Consolidated final result is available.';
      const claims = conclusion.claims || [
        'The primary manuscript-facing run is selected by completed scale.',
        'Scenario-specific electrical treatment choices differ across rhythm classes.',
        'Clinical efficacy is not claimed.'
      ];
      document.getElementById('claimList').innerHTML = claims.map(item => `<li>${esc(item)}</li>`).join('');
      document.getElementById('scenarioOverview').innerHTML = scenarioTable(primary.scenario_winners || [], true);
    }

    function renderPrimary() {
      const metrics = primary.policy_metrics || {};
      const rows = policyMetricRows(metrics, true);
      const maxReward = Math.max(...rows.map(row => num(row.value) || 0), 100);
      document.getElementById('primaryPolicyBars').innerHTML = barRows(rows, maxReward);
      document.getElementById('primaryMeta').innerHTML = [
        metricBox('Preset', primary.preset || '', 'primary evidence run'),
        metricBox('Horizon', `${primary.horizon_s || ''} s`, 'simulation horizon'),
        metricBox('Noise profiles', primary.noise_profile_count || '', 'robustness profiles'),
        metricBox('Fallback configs', primary.fallback_config_count || '', 'threshold combinations')
      ].join('');
      document.getElementById('primaryScenarios').innerHTML = scenarioTable(primary.scenario_winners || [], false);
      const noiseRows = (primary.noise_summary || []).map(row =>
        `<tr><td>${esc(row.profile)}</td><td>${esc(policyNames[row.policy_id] || row.policy_id)}</td><td>${fmt(row.mean_reward)}</td><td>${fmt(row.oracle_gap)}</td><td>${pct(row.success_rate)}</td><td>${fmt(row.mean_safety_violations)}</td></tr>`
      );
      document.getElementById('noiseSummary').innerHTML = table(['Profile','Policy','Reward','Oracle gap','Success','Safety violations'], noiseRows);
    }

    function scenarioTable(items, compact) {
      const rows = items.map(row =>
        `<tr><td>${esc(scenarioNames[row.scenario] || row.scenario)}</td><td><code>${esc(row.best_algorithm || row.final_action || '')}</code></td><td>${fmt(row.mean_reward)}</td><td>${pct(row.success_rate)}</td>${compact ? '' : `<td>${fmt(row.mean_energy)}</td><td>${fmt(row.mean_time_s)}</td><td>${fmt(row.mean_safety_violations)}</td>`}</tr>`
      );
      const headers = compact
        ? ['Scenario','Action','Reward','Success']
        : ['Scenario','Action','Reward','Success','Energy','Time s','Safety violations'];
      return table(headers, rows);
    }

    function renderVersioned() {
      const selectorAvg = aggregate.selector_model_average || {};
      const aclsAvg = aggregate.acls_rule_average || {};
      const oracleAvg = aggregate.oracle_average || {};
      document.getElementById('versionedKpis').innerHTML = [
        card('Versioned runs', `${versioned.completed_run_count || 0}/${versioned.run_count || 0}`, 'completed / considered'),
        card('Selector beats ACLS', `${evidence.selector_beats_acls_count || 0}/${evidence.selector_comparable_run_count || 0}`, 'comparable runs'),
        card('Oracle gap', fmt(selectorAvg.oracle_gap), 'selector average'),
        card('Selector success', pct(selectorAvg.success_rate), 'versioned average'),
        card('ACLS success', pct(aclsAvg.success_rate), 'versioned average'),
        card('Oracle reward', fmt(oracleAvg.mean_reward), 'versioned average')
      ].join('');
      const runRows = (versioned.runs || []).map(run => {
        const selector = run.selector_model || {};
        const acls = run.acls_rule || {};
        const oracle = run.oracle || {};
        const realism = run.realism_comparison || {};
        return `<tr><td><code>${esc(run.run_id)}</code><br><span class="small muted">${esc(run.experiment || '')}</span></td><td>${esc(run.status || '')}</td><td>${fmt(selector.mean_reward)}</td><td>${fmt(acls.mean_reward)}</td><td>${fmt(oracle.mean_reward)}</td><td>${pct(selector.success_rate)}</td><td>${fmt(realism.mean_smd_abs)}</td><td>${fmt(realism.mean_ks_statistic)}</td></tr>`;
      });
      document.getElementById('versionedRuns').innerHTML = table(['Run','Status','Selector reward','ACLS reward','Oracle reward','Selector success','Mean SMD','Mean KS'], runRows);
      const consensusRows = (versioned.scenario_consensus || []).map(row =>
        `<tr><td>${esc(scenarioNames[row.scenario] || row.scenario)}</td><td><code>${esc(row.consensus_algorithm || '')}</code></td><td>${esc(row.agreement || '')}</td><td>${fmt(row.mean_reward)}</td><td>${pct(row.success_rate)}</td></tr>`
      );
      document.getElementById('scenarioConsensus').innerHTML = table(['Scenario','Consensus action','Agreement','Mean reward','Success'], consensusRows);
    }

    function renderRealism() {
      document.getElementById('realismKpis').innerHTML = [
        card('Realism runs', realismAggregate.realism_run_count || 0, 'with real-vs-synthetic comparison'),
        card('Average mean SMD', fmt(realismAggregate.mean_smd_abs), 'lower is better'),
        card('Average mean KS', fmt(realismAggregate.mean_ks_statistic), 'lower is better'),
        card('Latest run', realismEvidence.latest_run_id || '', realismEvidence.latest_worst_feature || ''),
        card('Latest SMD change', fmt(realismEvidence.mean_smd_abs_change), `${realismEvidence.first_run_id || ''} to ${realismEvidence.latest_run_id || ''}`),
        card('Unmatched labels', (realismEvidence.latest_unmatched_labels || []).length, 'latest validation')
      ].join('');
      const runRows = (versioned.runs || []).filter(run => run.realism_comparison).map(run => {
        const realism = run.realism_comparison || {};
        return `<tr><td><code>${esc(run.run_id)}</code></td><td>${fmt(realism.mean_smd_abs)}</td><td>${fmt(realism.mean_ks_statistic)}</td><td>${esc(realism.max_smd_group || '')}</td><td>${esc(realism.max_smd_feature || '')}</td><td>${fmt(realism.max_smd_abs)}</td><td>${esc((realism.unmatched_real_labels || []).join(', '))}</td></tr>`;
      });
      document.getElementById('realismRuns').innerHTML = table(['Run','Mean SMD','Mean KS','Worst group','Worst feature','Worst SMD','Unmatched labels'], runRows);
    }

    function renderRunFilters() {
      const runs = data.runs || [];
      const statuses = [...new Set(runs.map(run => run.status || '').filter(Boolean))].sort();
      const presets = [...new Set(runs.map(run => run.preset || '').filter(Boolean))].sort();
      document.getElementById('statusFilter').innerHTML = '<option value="">All statuses</option>' + statuses.map(item => `<option value="${esc(item)}">${esc(item)}</option>`).join('');
      document.getElementById('presetFilter').innerHTML = '<option value="">All presets</option>' + presets.map(item => `<option value="${esc(item)}">${esc(item)}</option>`).join('');
    }

    function renderRuns() {
      const query = (document.getElementById('runSearch').value || '').toLowerCase();
      const status = document.getElementById('statusFilter').value;
      const preset = document.getElementById('presetFilter').value;
      const rows = (data.runs || [])
        .filter(run => !status || run.status === status)
        .filter(run => !preset || run.preset === preset)
        .filter(run => {
          const haystack = `${run.run_id || ''} ${run.preset || ''} ${run.paper_dir || ''}`.toLowerCase();
          return !query || haystack.includes(query);
        })
        .sort((a, b) => (Number(b.patients_per_scenario || 0) - Number(a.patients_per_scenario || 0)) || String(a.run_id).localeCompare(String(b.run_id)))
        .map(run => `<tr><td><code>${esc(run.run_id)}</code></td><td>${esc(run.status || '')}</td><td>${esc(run.preset || '')}</td><td>${esc(run.patients_per_scenario || '')}</td><td>${esc(run.horizon_s || '')}</td><td>${esc(run.noise_profile_count || '')}</td><td>${esc(run.fallback_config_count || '')}</td></tr>`);
      document.getElementById('runInventory').innerHTML = table(['Run ID','Status','Preset','Patients/scenario','Horizon s','Noise profiles','Fallback configs'], rows);
    }

    function renderMarkdown() {
      document.getElementById('markdownSnapshot').textContent = bundle.final_markdown || 'No markdown snapshot embedded.';
    }

    function activate(view) {
      document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.view === view));
      document.querySelectorAll('.view').forEach(section => section.classList.toggle('active', section.id === `view-${view}`));
      if (location.hash.replace('#', '') !== view) history.replaceState(null, '', `#${view}`);
    }

    function boot() {
      renderOverview();
      renderPrimary();
      renderVersioned();
      renderRealism();
      renderRunFilters();
      renderRuns();
      renderMarkdown();
      document.querySelectorAll('.nav button').forEach(button => button.addEventListener('click', () => activate(button.dataset.view)));
      document.getElementById('runSearch').addEventListener('input', renderRuns);
      document.getElementById('statusFilter').addEventListener('change', renderRuns);
      document.getElementById('presetFilter').addEventListener('change', renderRuns);
      const initial = location.hash.replace('#', '') || 'overview';
      if (document.getElementById(`view-${initial}`)) activate(initial);
    }
    boot();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
