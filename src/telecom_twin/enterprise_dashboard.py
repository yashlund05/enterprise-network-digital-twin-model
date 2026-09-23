"""Dedicated browser dashboard for the Enterprise Network Digital Twin.

Provides a unified operations center interface with 9 functional views:
1. Command Center
2. Live Digital Twin
3. Network Topology
4. Incident Center
5. Root Cause Analysis
6. Service Impact
7. What-If Simulation
8. Incident Replay
9. Evaluation & Statistics
"""

ENTERPRISE_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Enterprise Network Operations Center | Digital Twin</title>
  <style>
    :root {
      --bg-darker: #070d18;
      --bg-dark: #0d1527;
      --bg-card: #131f37;
      --bg-card-hover: #182846;
      --border: #233554;
      --border-accent: #334e77;
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --primary: #38bdf8;
      --primary-dim: #0284c7;
      --healthy: #10b981;
      --healthy-bg: rgba(16, 185, 129, 0.15);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --critical: #ef4444;
      --critical-bg: rgba(239, 68, 68, 0.15);
      --info: #6366f1;
      --info-bg: rgba(99, 102, 241, 0.15);
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      background: var(--bg-darker);
      color: var(--text);
      font-family: var(--font);
      font-size: 14px;
      line-height: 1.5;
    }

    /* Header */
    header {
      background: var(--bg-dark);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .header-titles h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .header-titles p {
      margin: 2px 0 0 0;
      font-size: 11px;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 600;
    }
    .header-status {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
    }
    .status-healthy { background: var(--healthy-bg); color: var(--healthy); border: 1px solid rgba(16,185,129,0.3); }
    .status-warning { background: var(--warning-bg); color: var(--warning); border: 1px solid rgba(245,158,11,0.3); }
    .status-critical { background: var(--critical-bg); color: var(--critical); border: 1px solid rgba(239,68,68,0.3); }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: currentColor;
    }

    /* Tabs Navigation */
    nav.tab-nav {
      background: var(--bg-dark);
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    nav.tab-nav::-webkit-scrollbar { display: none; }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 12px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid transparent;
      white-space: nowrap;
      transition: all 0.15s ease;
    }
    .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.02); }
    .tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
      background: rgba(56, 189, 248, 0.05);
    }
    .tab-badge {
      background: var(--border);
      color: var(--text);
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 10px;
      font-weight: 700;
    }

    /* Main Container */
    main {
      padding: 24px;
      max-width: 1600px;
      margin: 0 auto;
    }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Common Card & Grid System */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }
    .kpi-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      font-weight: 600;
    }
    .kpi-value {
      font-size: 26px;
      font-weight: 700;
      margin: 6px 0 2px 0;
      color: #fff;
      font-family: var(--mono);
    }
    .kpi-sub {
      font-size: 12px;
      color: var(--text-dim);
    }

    .grid-2col {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }
    .grid-equal {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }
    @media (max-width: 1050px) {
      .grid-2col, .grid-equal { grid-template-columns: 1fr; }
    }

    .panel {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 20px;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }
    .panel-title {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Tables */
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }
    table.data-table th {
      background: rgba(0,0,0,0.2);
      color: var(--text-muted);
      font-weight: 600;
      padding: 9px 12px;
      border-bottom: 1px solid var(--border);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    table.data-table td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(35, 53, 84, 0.4);
      color: var(--text);
    }
    table.data-table tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }
    .code-cell { font-family: var(--mono); font-size: 12px; }

    /* Forms & Controls */
    .form-group {
      margin-bottom: 14px;
    }
    .form-group label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--text-muted);
    }
    .form-control {
      width: 100%;
      background: var(--bg-dark);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: #fff;
      padding: 8px 12px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.15s ease;
    }
    .form-control:focus {
      border-color: var(--primary);
    }
    .btn-primary {
      background: var(--primary-dim);
      border: 1px solid var(--primary);
      color: #fff;
      padding: 9px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s ease;
    }
    .btn-primary:hover {
      background: var(--primary);
      color: #000;
    }
    .btn-secondary {
      background: var(--border);
      border: 1px solid var(--border-accent);
      color: var(--text);
      padding: 7px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-secondary:hover {
      background: var(--border-accent);
      color: #fff;
    }

    /* SVG Topology Visualizer */
    .topo-canvas-container {
      background: #080f1d;
      border: 1px solid var(--border);
      border-radius: 10px;
      position: relative;
      overflow: hidden;
    }
    svg#topo-svg {
      width: 100%;
      height: 580px;
      display: block;
    }
    .topo-link {
      stroke: #223a5e;
      stroke-width: 1.5;
      transition: stroke 0.2s, stroke-width 0.2s;
    }
    .topo-link.affected {
      stroke: #ef4444;
      stroke-width: 3;
      stroke-dasharray: 6 3;
    }
    .topo-node {
      cursor: pointer;
      transition: all 0.2s;
    }
    .topo-node circle {
      stroke-width: 2;
      transition: all 0.2s;
    }
    .topo-node:hover circle {
      stroke: #fff !important;
      stroke-width: 3;
    }
    .topo-node text {
      font-family: var(--mono);
      font-size: 10px;
      fill: #cbd5e1;
      pointer-events: none;
      text-anchor: middle;
      font-weight: 600;
    }
    .topo-tier-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      fill: #475569;
    }

    /* Replay Stepper */
    .stepper {
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: relative;
      margin: 20px 0 30px 0;
    }
    .stepper-step {
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      z-index: 2;
      cursor: pointer;
    }
    .step-circle {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--bg-card);
      border: 2px solid var(--border);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 13px;
      transition: all 0.2s;
    }
    .stepper-step.active .step-circle {
      background: var(--primary);
      border-color: #fff;
      color: #000;
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.5);
    }
    .stepper-step.completed .step-circle {
      background: var(--healthy);
      border-color: var(--healthy);
      color: #000;
    }
    .step-label {
      font-size: 11px;
      font-weight: 600;
      margin-top: 8px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .stepper-step.active .step-label {
      color: var(--primary);
      font-weight: 700;
    }

    /* Alerts and Notices */
    .notice-box {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border);
      border-left: 4px solid var(--primary);
      padding: 14px 18px;
      border-radius: 6px;
      margin-bottom: 20px;
    }
    .notice-box.warning { border-left-color: var(--warning); }
    .notice-box.critical { border-left-color: var(--critical); }
    .notice-box.healthy { border-left-color: var(--healthy); }

    .empty-state {
      padding: 40px;
      text-align: center;
      color: var(--text-dim);
    }
    .empty-state h4 {
      margin: 0 0 6px 0;
      color: var(--text-muted);
      font-size: 15px;
    }
  </style>
</head>
<body>

  <!-- Top Bar -->
  <header>
    <div class="header-titles">
      <h1>
        <span style="color:var(--primary);">⯌</span> Enterprise Network Operations Center
      </h1>
      <p>Digital Twin-Based Intelligent Enterprise Network Monitoring</p>
    </div>
    <div class="header-status">
      <div id="badge-twin-sync" class="status-badge status-healthy">
        <span class="pulse-dot"></span>
        <span id="label-twin-sync">Twin: Synchronized (1.00)</span>
      </div>
      <div id="badge-net-health" class="status-badge status-healthy">
        <span class="pulse-dot"></span>
        <span id="label-net-health">Network: Healthy</span>
      </div>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <nav class="tab-nav">
    <button class="tab-btn active" onclick="switchTab('cmd-center')">
      Command Center
    </button>
    <button class="tab-btn" onclick="switchTab('live-twin')">
      Live Digital Twin <span class="tab-badge" id="badge-node-count">22</span>
    </button>
    <button class="tab-btn" onclick="switchTab('topology')">
      Network Topology
    </button>
    <button class="tab-btn" onclick="switchTab('incidents')">
      Incident Center <span class="tab-badge" id="badge-incident-count">0</span>
    </button>
    <button class="tab-btn" onclick="switchTab('rca')">
      Root Cause Analysis
    </button>
    <button class="tab-btn" onclick="switchTab('service-impact')">
      Service Impact <span class="tab-badge">6</span>
    </button>
    <button class="tab-btn" onclick="switchTab('what-if')">
      What-If Simulation
    </button>
    <button class="tab-btn" onclick="switchTab('replay')">
      Incident Replay
    </button>
    <button class="tab-btn" onclick="switchTab('evaluation')">
      Evaluation & Stats
    </button>
  </nav>

  <main>

    <!-- VIEW 1: COMMAND CENTER -->
    <div id="tab-cmd-center" class="tab-pane active">
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Network Health</div>
          <div class="kpi-value" id="kpi-health-status" style="color:var(--healthy);">HEALTHY</div>
          <div class="kpi-sub">0 degraded tiers detected</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Twin Synchronization</div>
          <div class="kpi-value" id="kpi-sync-score">100%</div>
          <div class="kpi-sub" id="kpi-sync-staleness">Staleness: 0.00s</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Active Incidents</div>
          <div class="kpi-value" id="kpi-incidents-count">0</div>
          <div class="kpi-sub">0 critical · 0 warnings</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Anomalous Nodes</div>
          <div class="kpi-value" id="kpi-anomalies-count">0</div>
          <div class="kpi-sub">Out of 22 monitored nodes</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Services at Risk</div>
          <div class="kpi-value" id="kpi-services-risk">0 / 6</div>
          <div class="kpi-sub">All catalog services operational</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Blast Radius</div>
          <div class="kpi-value" id="kpi-blast-radius">0.0%</div>
          <div class="kpi-sub">Baseline normal state</div>
        </div>
      </div>

      <div class="grid-2col">
        <section class="panel">
          <div class="panel-header">
            <h3 class="panel-title">Health by Network Tier</h3>
            <span class="status-badge status-healthy">All 5 Tiers Operational</span>
          </div>
          <div id="tier-health-bars" style="display:flex; flex-direction:column; gap:12px;">
            <!-- Rendered dynamically -->
            <div style="color:var(--text-dim); text-align:center;">Loading tier health...</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h3 class="panel-title">Service Catalog Health</h3>
            <span class="code-cell" style="color:var(--text-dim);">6 registered</span>
          </div>
          <table class="data-table">
            <thead>
              <tr><th>Service</th><th>Host</th><th>Criticality</th><th>Status</th></tr>
            </thead>
            <tbody id="cmd-services-table">
              <tr><td colspan="4" style="text-align:center; color:var(--text-dim);">Loading services...</td></tr>
            </tbody>
          </table>
        </section>
      </div>

      <section class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Active Alarm & Anomaly Feed</h3>
          <button class="btn-secondary" onclick="fetchHealthData()">Refresh Feed</button>
        </div>
        <div id="cmd-alarms-container">
          <div class="empty-state">
            <h4>NO ACTIVE ALARMS DETECTED</h4>
            <p>All enterprise network telemetry is currently within configured SLA baseline boundaries.</p>
          </div>
        </div>
      </section>
    </div>

    <!-- VIEW 2: LIVE DIGITAL TWIN -->
    <div id="tab-live-twin" class="tab-pane">
      <div class="notice-box">
        <strong>ARCHITECTURAL NOTE:</strong> Virtual representation of the physical network.
        <span style="color:var(--primary);">Network Health</span> evaluates telemetry SLAs, while
        <span style="color:var(--healthy);">Twin Synchronization</span> measures model convergence and telemetry staleness.
      </div>

      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Synchronized Node Telemetry Snapshot</h3>
          <div style="display:flex; gap:10px;">
            <input type="text" id="live-search" class="form-control" style="width:220px;" placeholder="Search node or tier..." oninput="filterLiveTable()">
            <button class="btn-secondary" onclick="fetchTwinState()">Poll Now</button>
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Node ID</th><th>Tier</th><th>Role</th><th>Latency</th><th>Packet Loss</th>
              <th>Throughput</th><th>Sync State</th><th>Status</th>
            </tr>
          </thead>
          <tbody id="live-nodes-tbody">
            <tr><td colspan="8" style="text-align:center; color:var(--text-dim);">Streaming synchronized twin telemetry...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VIEW 3: NETWORK TOPOLOGY -->
    <div id="tab-topology" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Canonical Enterprise Multi-Tier Topology (22 Nodes · 44 Links)</h3>
          <div style="display:flex; gap:10px;">
            <button class="btn-secondary" onclick="resetTopoHighlights()">Reset Highlights</button>
            <button class="btn-secondary" onclick="loadTopology()">Reload Topology</button>
          </div>
        </div>
        <div class="topo-canvas-container">
          <svg id="topo-svg" viewBox="0 0 1000 650"></svg>
        </div>
        <div style="margin-top:10px; display:flex; gap:20px; font-size:12px; color:var(--text-muted); justify-content:center;">
          <span><span style="color:#38bdf8;">●</span> Edge Tier</span>
          <span><span style="color:#a855f7;">●</span> Core Spine Tier</span>
          <span><span style="color:#0ea5e9;">●</span> Distribution Tier</span>
          <span><span style="color:#14b8a6;">●</span> Access Tier</span>
          <span><span style="color:#f59e0b;">●</span> Service Host Tier</span>
        </div>
      </div>

      <!-- Node Click Inspector -->
      <div id="topo-inspector" class="panel" style="display:none;">
        <div class="panel-header">
          <h3 class="panel-title" id="inspector-node-id">Node Inspector</h3>
          <button class="btn-secondary" onclick="document.getElementById('topo-inspector').style.display='none'">Close</button>
        </div>
        <div id="inspector-content" class="grid-equal"></div>
      </div>
    </div>

    <!-- VIEW 4: INCIDENT CENTER -->
    <div id="tab-incidents" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Enterprise Incident & Alarm Feed</h3>
          <div style="display:flex; gap:10px;">
            <select id="incident-filter-sev" class="form-control" style="width:140px;" onchange="renderIncidents()">
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="NORMAL">Normal</option>
            </select>
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr><th>Timestamp</th><th>Severity</th><th>Origin Node</th><th>Anomaly Metric</th><th>Z-Score</th><th>Evidence</th><th>Status</th></tr>
          </thead>
          <tbody id="incidents-tbody">
            <tr><td colspan="7" style="text-align:center; color:var(--text-dim);">No active enterprise incidents detected.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VIEW 5: ROOT CAUSE ANALYSIS -->
    <div id="tab-rca" class="tab-pane">
      <div class="notice-box">
        <strong>TOPOLOGICAL & TEMPORAL RCA ENGINE:</strong> Correlates alarm clustering, propagation delays,
        and shortest-path dependency coverage across the 5-tier topology to isolate fault origins.
      </div>
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Root Cause Analysis Diagnostic Candidates</h3>
          <span class="status-badge status-healthy" id="rca-status-badge">RCA Engine Ready</span>
        </div>
        <div id="rca-candidates-container">
          <div class="empty-state">
            <h4>NO ROOT CAUSE CANDIDATES ACTIVE</h4>
            <p>RCA triggers automatically when multi-signal threshold anomalies exceed significance thresholds.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- VIEW 6: SERVICE IMPACT -->
    <div id="tab-service-impact" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Enterprise Service Catalog & Dependency Graph</h3>
          <span class="status-badge status-healthy">6 Services Monitored</span>
        </div>
        <div class="grid-equal" id="services-cards-grid">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Consumer → Provider Dependency Mapping</h3>
        </div>
        <table class="data-table">
          <thead>
            <tr><th>Consumer Service</th><th>Dependency Type</th><th>Provider Service</th><th>Impact Status</th></tr>
          </thead>
          <tbody id="dependencies-tbody">
            <tr><td colspan="4" style="text-align:center; color:var(--text-dim);">Loading dependencies...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VIEW 7: WHAT-IF SIMULATION -->
    <div id="tab-what-if" class="tab-pane">
      <div class="grid-2col">
        <section class="panel">
          <div class="panel-header">
            <h3 class="panel-title">Counterfactual Scenario Builder</h3>
            <span class="code-cell" style="color:var(--primary);">Isolated Sandbox</span>
          </div>
          <form id="whatif-form" onsubmit="runWhatIfSimulation(event)">
            <div class="form-group">
              <label for="whatif-target-type">Target Element Type</label>
              <select id="whatif-target-type" class="form-control" onchange="updateWhatIfTargets()">
                <option value="node">Network Node</option>
                <option value="link">Network Link</option>
              </select>
            </div>
            <div class="form-group">
              <label for="whatif-target-id">Target Element ID</label>
              <select id="whatif-target-id" class="form-control">
                <!-- Dynamically populated from actual topology -->
              </select>
            </div>
            <div class="form-group">
              <label for="whatif-failure-type">Failure / Perturbation Mode</label>
              <select id="whatif-failure-type" class="form-control">
                <option value="node_down">Node Total Failure (node_down)</option>
                <option value="latency_spike">Node Latency Spike (latency_spike)</option>
                <option value="packet_loss">Node Packet Loss Spike (packet_loss)</option>
                <option value="bandwidth_throttling">Bandwidth Throttling (bandwidth_throttling)</option>
                <option value="traffic_surge">Ingress Traffic Surge (traffic_surge)</option>
              </select>
            </div>
            <div class="form-group">
              <label for="whatif-param-val">Parameter Magnitude</label>
              <input type="number" id="whatif-param-val" class="form-control" value="1.0" step="0.5" min="0">
              <small style="color:var(--text-dim);">Latency in ms, loss in %, or capacity reduction</small>
            </div>
            <button type="submit" class="btn-primary" style="width:100%; justify-content:center; margin-top:8px;">
              ⚡ SIMULATE SCENARIO
            </button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h3 class="panel-title">Predicted Impact & Blast Radius</h3>
            <span id="whatif-severity-badge" class="status-badge status-healthy">Baseline</span>
          </div>
          <div id="whatif-result-view">
            <div class="empty-state">
              <h4>READY FOR SCENARIO EXECUTION</h4>
              <p>Select target infrastructure and perturbation mode, then click Simulate.</p>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- VIEW 8: INCIDENT REPLAY -->
    <div id="tab-replay" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Six-Stage Incident Post-Mortem Playback</h3>
          <div style="display:flex; gap:8px;">
            <select id="replay-target-node" class="form-control" style="width:160px;" onchange="loadReplayTimeline()">
              <option value="core-sw-01">core-sw-01 (Spine)</option>
              <option value="dist-sw-dc-01">dist-sw-dc-01 (Dist)</option>
              <option value="host-erp">host-erp (App)</option>
            </select>
            <button class="btn-secondary" onclick="loadReplayTimeline()">Generate Timeline</button>
          </div>
        </div>

        <!-- Stepper -->
        <div class="stepper" id="replay-stepper">
          <div class="stepper-step active" onclick="seekReplayStep(0)">
            <div class="step-circle">1</div>
            <div class="step-label">Normal</div>
          </div>
          <div class="stepper-step" onclick="seekReplayStep(1)">
            <div class="step-circle">2</div>
            <div class="step-label">Degradation</div>
          </div>
          <div class="stepper-step" onclick="seekReplayStep(2)">
            <div class="step-circle">3</div>
            <div class="step-label">Anomaly</div>
          </div>
          <div class="stepper-step" onclick="seekReplayStep(3)">
            <div class="step-circle">4</div>
            <div class="step-label">RCA</div>
          </div>
          <div class="stepper-step" onclick="seekReplayStep(4)">
            <div class="step-circle">5</div>
            <div class="step-label">Impact</div>
          </div>
          <div class="stepper-step" onclick="seekReplayStep(5)">
            <div class="step-circle">6</div>
            <div class="step-label">Recovery</div>
          </div>
        </div>

        <div style="display:flex; justify-content:center; gap:12px; margin-bottom:24px;">
          <button class="btn-secondary" onclick="prevReplayStep()">◄ Previous</button>
          <button class="btn-secondary" onclick="resetReplay()">↺ Reset</button>
          <button class="btn-primary" onclick="nextReplayStep()">Next Step ►</button>
        </div>

        <div id="replay-event-card" class="panel" style="background:var(--bg-dark); border-color:var(--border-accent);">
          <div style="text-align:center; color:var(--text-dim);">Loading replay timeline...</div>
        </div>
      </div>
    </div>

    <!-- VIEW 9: EVALUATION & STATS -->
    <div id="tab-evaluation" class="tab-pane">
      <div class="notice-box warning">
        <strong>HONEST REPORTING STATUS:</strong> The formal Phase 10 evaluation framework has not yet been executed.
        In compliance with project integrity principles, no fake precision, recall, accuracy, or F1 scores are fabricated.
      </div>
      <div class="panel">
        <div class="panel-header">
          <h3 class="panel-title">Academic Benchmarking Roadmap</h3>
          <span class="status-badge status-warning">Phase 10 Pending</span>
        </div>
        <div class="grid-equal">
          <div class="panel" style="background:var(--bg-dark);">
            <h4 style="margin:0 0 10px 0; color:var(--primary);">Anomaly Detection Metrics</h4>
            <p style="color:var(--text-muted); font-size:13px;">
              Will benchmark Precision, Recall, F1, and Detection Latency across multi-fault scenarios and false alarm injection.
            </p>
          </div>
          <div class="panel" style="background:var(--bg-dark);">
            <h4 style="margin:0 0 10px 0; color:var(--primary);">Root Cause Analysis Accuracy</h4>
            <p style="color:var(--text-muted); font-size:13px;">
              Will evaluate Top-1 and Top-3 candidate correctness under temporal delay and missing telemetry conditions.
            </p>
          </div>
          <div class="panel" style="background:var(--bg-dark);">
            <h4 style="margin:0 0 10px 0; color:var(--primary);">Service Blast Radius Reliability</h4>
            <p style="color:var(--text-muted); font-size:13px;">
              Evaluates Jaccard similarity between predicted affected services and simulated degradation across DAG dependencies.
            </p>
          </div>
          <div class="panel" style="background:var(--bg-dark);">
            <h4 style="margin:0 0 10px 0; color:var(--primary);">Counterfactual Prediction Error</h4>
            <p style="color:var(--text-muted); font-size:13px;">
              Quantifies Mean Absolute Error (MAE) between What-If sandbox predictions and actual fault-injection runs.
            </p>
          </div>
        </div>
      </div>
    </div>

  </main>

  <script>
    // Global Application State
    let topologyData = null;
    let servicesData = null;
    let replayEvents = [];
    let currentReplayIdx = 0;
    let pollInterval = null;

    // View Navigation
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (activeBtn) activeBtn.classList.add('active');

      const targetPane = document.getElementById('tab-' + tabId);
      if (targetPane) targetPane.classList.add('active');

      if (tabId === 'topology' && topologyData) {
        renderTopology(topologyData);
      }
    }

    // 1. Fetch Topology & Services
    async function loadTopology() {
      try {
        const res = await fetch('/api/enterprise/topology');
        if (!res.ok) throw new Error('Topology fetch failed');
        topologyData = await res.json();
        document.getElementById('badge-node-count').textContent = topologyData.node_count;
        renderTopology(topologyData);
        populateWhatIfTargets();
      } catch (err) {
        console.error('Failed to load topology:', err);
      }
    }

    async function loadServices() {
      try {
        const res = await fetch('/api/enterprise/services');
        if (!res.ok) throw new Error('Services fetch failed');
        servicesData = await res.json();
        renderServicesTable(servicesData.services);
        renderServicesCards(servicesData.services);
        renderDependenciesTable(servicesData.dependencies);
      } catch (err) {
        console.error('Failed to load services:', err);
      }
    }

    // 2. Fetch Health & Twin Sync
    async function fetchHealthData() {
      try {
        const res = await fetch('/api/enterprise/health');
        if (!res.ok) return;
        const h = await res.json();

        // Update KPIs
        const isHealthy = h.overall_health === 'healthy';
        const healthEl = document.getElementById('kpi-health-status');
        healthEl.textContent = h.overall_health.toUpperCase();
        healthEl.style.color = isHealthy ? 'var(--healthy)' : 'var(--critical)';

        document.getElementById('label-net-health').textContent = 'Network: ' + (isHealthy ? 'Healthy' : 'Degraded');
        document.getElementById('badge-net-health').className = 'status-badge ' + (isHealthy ? 'status-healthy' : 'status-critical');

        document.getElementById('kpi-anomalies-count').textContent = h.active_anomalies.length;
        document.getElementById('kpi-incidents-count').textContent = h.active_alarms.length;
        document.getElementById('badge-incident-count').textContent = h.active_alarms.length;
        document.getElementById('kpi-services-risk').textContent = h.impacted_services.length + ' / 6';

        renderTierHealth(h.health_by_tier);
        renderAlarmsFeed(h.active_alarms);
      } catch (err) {
        console.error('Error fetching health data:', err);
      }
    }

    async function fetchTwinSync() {
      try {
        const res = await fetch('/api/enterprise/twin/sync');
        if (!res.ok) return;
        const s = await res.json();

        document.getElementById('kpi-sync-score').textContent = (s.consistency_score * 100).toFixed(0) + '%';
        const staleness = s.telemetry_staleness_s !== null ? s.telemetry_staleness_s.toFixed(2) + 's' : '0.00s';
        document.getElementById('kpi-sync-staleness').textContent = 'Staleness: ' + staleness;
        document.getElementById('label-twin-sync').textContent = 'Twin: ' + s.overall_sync_status + ' (' + s.consistency_score.toFixed(2) + ')';
      } catch (err) {
        console.error('Error fetching twin sync:', err);
      }
    }

    async function fetchTwinState() {
      try {
        const res = await fetch('/api/enterprise/twin/state');
        if (!res.ok) return;
        const state = await res.json();
        renderLiveNodesTable(state.nodes);
      } catch (err) {
        console.error('Error fetching live twin state:', err);
      }
    }

    // Render Helpers
    function renderTierHealth(tiers) {
      const c = document.getElementById('tier-health-bars');
      if (!tiers) return;
      let html = '';
      for (const [tier, info] of Object.entries(tiers)) {
        html += `
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span style="text-transform:capitalize; font-weight:600;">${tier} Tier</span>
              <span style="color:var(--healthy);">${info.healthy_nodes} / ${info.node_count} nodes operational</span>
            </div>
            <div style="height:6px; background:var(--bg-dark); border-radius:3px; overflow:hidden;">
              <div style="width:100%; height:100%; background:var(--healthy);"></div>
            </div>
          </div>
        `;
      }
      c.innerHTML = html;
    }

    function renderServicesTable(services) {
      const tbody = document.getElementById('cmd-services-table');
      if (!services) return;
      tbody.innerHTML = services.map(s => `
        <tr>
          <td style="font-weight:600;">${s.name}</td>
          <td class="code-cell">${s.host_node_id}</td>
          <td><span class="status-badge status-info">${s.criticality}</span></td>
          <td><span class="status-badge status-${s.health_status === 'healthy' ? 'healthy' : 'critical'}">${s.health_status}</span></td>
        </tr>
      `).join('');
    }

    function renderServicesCards(services) {
      const container = document.getElementById('services-cards-grid');
      if (!services) return;
      container.innerHTML = services.map(s => `
        <div class="panel" style="background:var(--bg-dark);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <h4 style="margin:0; font-size:15px; color:#fff;">${s.name}</h4>
            <span class="status-badge status-healthy">${s.health_status}</span>
          </div>
          <div style="font-size:12px; color:var(--text-muted); line-height:1.6;">
            <div><strong>Service ID:</strong> <span class="code-cell">${s.service_id}</span></div>
            <div><strong>Host Pod:</strong> <span class="code-cell">${s.host_node_id}</span> (Port ${s.port})</div>
            <div><strong>Criticality:</strong> ${s.criticality} · Tier: ${s.tier}</div>
            <div><strong>Direct Dependencies:</strong> ${s.dependencies && s.dependencies.length ? s.dependencies.join(', ') : 'Root Infrastructure'}</div>
          </div>
        </div>
      `).join('');
    }

    function renderDependenciesTable(deps) {
      const tbody = document.getElementById('dependencies-tbody');
      if (!deps) return;
      tbody.innerHTML = deps.map(d => `
        <tr>
          <td class="code-cell" style="font-weight:600;">${d.consumer_service_id}</td>
          <td><span style="color:var(--text-dim);">depends on (synchronous) →</span></td>
          <td class="code-cell" style="color:var(--primary);">${d.provider_service_id}</td>
          <td><span class="status-badge status-healthy">Operational</span></td>
        </tr>
      `).join('');
    }

    function renderAlarmsFeed(alarms) {
      const c = document.getElementById('cmd-alarms-container');
      if (!alarms || alarms.length === 0) {
        c.innerHTML = `
          <div class="empty-state">
            <h4>NO ACTIVE ALARMS DETECTED</h4>
            <p>All enterprise network telemetry is currently within configured SLA baseline boundaries.</p>
          </div>
        `;
        return;
      }
      c.innerHTML = alarms.map(a => `
        <div class="notice-box critical" style="display:flex; justify-content:space-between; align-items:center;">
          <div><strong>ALERT:</strong> ${a}</div>
          <span class="status-badge status-critical">Active Alarm</span>
        </div>
      `).join('');
    }

    function renderLiveNodesTable(nodes) {
      const tbody = document.getElementById('live-nodes-tbody');
      if (!nodes) return;
      tbody.innerHTML = nodes.map(n => {
        const tel = n.telemetry || { cpu_percent: 0, latency_ms: 0, packet_loss_percent: 0, throughput_mbps: 0 };
        return `
          <tr>
            <td class="code-cell" style="font-weight:600;">${n.node_id}</td>
            <td style="text-transform:capitalize;">${n.tier}</td>
            <td style="color:var(--text-muted);">${n.role}</td>
            <td class="code-cell">${tel.latency_ms ? tel.latency_ms.toFixed(1) + ' ms' : '1.0 ms'}</td>
            <td class="code-cell">${tel.packet_loss_percent ? tel.packet_loss_percent.toFixed(2) + '%' : '0.00%'}</td>
            <td class="code-cell">${tel.throughput_mbps ? tel.throughput_mbps.toFixed(0) + ' Mbps' : '1000 Mbps'}</td>
            <td><span class="status-badge status-healthy">Synchronized</span></td>
            <td><span class="status-badge status-healthy">Normal</span></td>
          </tr>
        `;
      }).join('');
    }

    function filterLiveTable() {
      const q = document.getElementById('live-search').value.toLowerCase();
      const rows = document.querySelectorAll('#live-nodes-tbody tr');
      rows.forEach(r => {
        r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    }

    // 3. Topology Renderer (SVG)
    function renderTopology(data) {
      const svg = document.getElementById('topo-svg');
      if (!svg || !data) return;

      const byId = Object.fromEntries(data.nodes.map(n => [n.node_id, n]));
      let html = '';

      // Tier Labels
      html += `<text class="topo-tier-label" x="50" y="80">Edge Tier</text>`;
      html += `<text class="topo-tier-label" x="50" y="200">Core Spine Tier</text>`;
      html += `<text class="topo-tier-label" x="50" y="320">Distribution Tier</text>`;
      html += `<text class="topo-tier-label" x="50" y="450">Access Tier</text>`;
      html += `<text class="topo-tier-label" x="50" y="580">Application Host Tier</text>`;

      // Links
      for (const l of data.links) {
        const u = byId[l.source];
        const v = byId[l.target];
        if (!u || !v) continue;
        const x1 = 500 + u.x * 460;
        const y1 = 325 - u.y * 300;
        const x2 = 500 + v.x * 460;
        const y2 = 325 - v.y * 300;
        const linkKey = `${l.source}<->${l.target}`;
        html += `<line id="link-${linkKey}" class="topo-link" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
      }

      // Nodes
      for (const n of data.nodes) {
        const cx = 500 + n.x * 460;
        const cy = 325 - n.y * 300;
        let color = '#38bdf8';
        let r = 10;
        if (n.tier === 'core') { color = '#a855f7'; r = 14; }
        else if (n.tier === 'distribution') { color = '#0ea5e9'; r = 12; }
        else if (n.tier === 'access') { color = '#14b8a6'; r = 10; }
        else if (n.tier === 'host') { color = '#f59e0b'; r = 11; }

        html += `
          <g class="topo-node" id="node-${n.node_id}" onclick="inspectNode('${n.node_id}')">
            <circle cx="${cx}" cy="${cy}" r="${r}" fill="#0f172a" stroke="${color}" stroke-width="2.5">
              <title>${n.node_id} (${n.tier})</title>
            </circle>
            <text x="${cx}" y="${cy + r + 12}">${n.node_id}</text>
          </g>
        `;
      }

      svg.innerHTML = html;
    }

    function inspectNode(nodeId) {
      if (!topologyData) return;
      const node = topologyData.nodes.find(n => n.node_id === nodeId);
      if (!node) return;

      const inspector = document.getElementById('topo-inspector');
      inspector.style.display = 'block';
      document.getElementById('inspector-node-id').textContent = 'Node Inspector: ' + node.node_id;

      const incidentLinks = topologyData.links.filter(l => l.source === nodeId || l.target === nodeId);

      document.getElementById('inspector-content').innerHTML = `
        <div>
          <h4>Specifications</h4>
          <p><strong>Tier:</strong> ${node.tier.toUpperCase()}</p>
          <p><strong>Role:</strong> ${node.role}</p>
          <p><strong>Capacity:</strong> ${node.capacity_mbps} Mbps</p>
          <p><strong>Region:</strong> ${node.region}</p>
        </div>
        <div>
          <h4>Connected Links (${incidentLinks.length})</h4>
          <ul style="padding-left:16px; font-family:var(--mono); font-size:12px;">
            ${incidentLinks.map(l => `<li>${l.source} ↔ ${l.target} (${l.capacity_mbps} Mbps, ${l.base_latency_ms} ms)</li>`).join('')}
          </ul>
        </div>
      `;
    }

    function resetTopoHighlights() {
      document.querySelectorAll('.topo-link').forEach(l => l.classList.remove('affected'));
      document.querySelectorAll('.topo-node circle').forEach(c => c.setAttribute('fill', '#0f172a'));
    }

    // 4. What-If Scenario Execution
    function populateWhatIfTargets() {
      const type = document.getElementById('whatif-target-type').value;
      const targetSel = document.getElementById('whatif-target-id');
      if (!topologyData) return;

      if (type === 'node') {
        targetSel.innerHTML = topologyData.nodes.map(n => `<option value="${n.node_id}">${n.node_id} (${n.tier})</option>`).join('');
      } else {
        targetSel.innerHTML = topologyData.links.map(l => `<option value="${l.source}<->${l.target}">${l.source} ↔ ${l.target}</option>`).join('');
      }
    }

    function updateWhatIfTargets() {
      populateWhatIfTargets();
    }

    async function runWhatIfSimulation(e) {
      e.preventDefault();
      const targetType = document.getElementById('whatif-target-type').value;
      const targetId = document.getElementById('whatif-target-id').value;
      const failureType = document.getElementById('whatif-failure-type').value;
      const paramVal = parseFloat(document.getElementById('whatif-param-val').value) || 1.0;

      const resultBox = document.getElementById('whatif-result-view');
      resultBox.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">Simulating counterfactual scenario in isolated sandbox...</div>';

      try {
        const res = await fetch('/api/enterprise/whatif/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_type: targetType,
            target_id: targetId,
            failure_type: failureType,
            parameter_value: paramVal
          })
        });

        if (!res.ok) {
          const err = await res.json();
          resultBox.innerHTML = `<div class="notice-box critical"><strong>Error:</strong> ${err.detail || 'Simulation failed'}</div>`;
          return;
        }

        const data = await res.json();
        renderWhatIfResult(data);
      } catch (err) {
        resultBox.innerHTML = `<div class="notice-box critical"><strong>Connection Error:</strong> ${err.message}</div>`;
      }
    }

    function renderWhatIfResult(d) {
      const res = d.result;
      const sevColor = res.severity === 'CRITICAL' ? 'var(--critical)' : res.severity === 'HIGH' ? 'var(--warning)' : 'var(--primary)';
      document.getElementById('whatif-severity-badge').textContent = res.severity;
      document.getElementById('whatif-severity-badge').className = 'status-badge ' + (res.severity === 'CRITICAL' ? 'status-critical' : 'status-warning');

      const html = `
        <div style="margin-bottom:16px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
            <div>
              <span class="kpi-label">Predicted Severity</span>
              <div style="font-size:22px; font-weight:700; color:${sevColor};">${res.severity}</div>
            </div>
            <div>
              <span class="kpi-label">Blast Radius</span>
              <div style="font-size:22px; font-weight:700; color:#fff;">${res.blast_radius_percent.toFixed(1)}%</div>
            </div>
            <div>
              <span class="kpi-label">Latency Impact</span>
              <div style="font-size:22px; font-weight:700; color:#fff;">+${res.latency_delta_ms.toFixed(1)} ms</div>
            </div>
          </div>

          <div style="background:var(--bg-dark); padding:12px; border-radius:6px; margin-bottom:12px;">
            <div style="font-size:12px; margin-bottom:6px;"><strong>Impacted Services (${res.predicted_affected_services.length}):</strong></div>
            <div style="color:var(--warning); font-size:13px;">
              ${res.predicted_affected_services.length ? res.predicted_affected_services.join(', ') : 'None — Alternate paths preserved reachability'}
            </div>
          </div>

          <div style="background:var(--bg-dark); padding:12px; border-radius:6px;">
            <div style="font-size:12px; margin-bottom:6px;"><strong>Isolated Infrastructure:</strong></div>
            <div style="color:var(--text-muted); font-size:12px;">
              Nodes: ${res.predicted_affected_nodes.join(', ') || 'None'}<br>
              Links: ${res.predicted_affected_links.join(', ') || 'None'}
            </div>
          </div>
        </div>
      `;
      document.getElementById('whatif-result-view').innerHTML = html;
    }

    // 5. Incident Replay
    async function loadReplayTimeline() {
      const targetNode = document.getElementById('replay-target-node').value;
      try {
        const res = await fetch(`/api/enterprise/replay/timeline?target_node_id=${targetNode}`);
        if (!res.ok) throw new Error('Replay timeline error');
        const data = await res.json();
        replayEvents = data.timeline;
        currentReplayIdx = 0;
        updateReplayDisplay();
      } catch (err) {
        console.error('Failed to load replay timeline:', err);
      }
    }

    function updateReplayDisplay() {
      if (!replayEvents.length) return;
      const ev = replayEvents[currentReplayIdx];

      // Update Stepper
      const steps = document.querySelectorAll('.stepper-step');
      steps.forEach((s, idx) => {
        s.className = 'stepper-step ' + (idx === currentReplayIdx ? 'active' : idx < currentReplayIdx ? 'completed' : '');
      });

      // Update Card
      const card = document.getElementById('replay-event-card');
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <span class="status-badge status-primary" style="font-size:14px; text-transform:uppercase;">Stage ${currentReplayIdx + 1}: ${ev.stage}</span>
          <span class="code-cell" style="color:var(--primary); font-size:13px;">Simulation Time: t = ${ev.timestamp_s}s</span>
        </div>
        <p style="font-size:15px; color:#fff; line-height:1.6; margin:0 0 16px 0;">
          ${ev.description}
        </p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
          <div>
            <strong>Active Alarms:</strong>
            <div style="color:${ev.active_alarms.length ? 'var(--critical)' : 'var(--text-dim)'}; margin-top:4px;">
              ${ev.active_alarms.length ? ev.active_alarms.join('<br>') : 'None (Nominal)'}
            </div>
          </div>
          <div>
            <strong>RCA Root Cause Identified:</strong>
            <div style="color:${ev.root_cause_id ? 'var(--warning)' : 'var(--text-dim)'}; margin-top:4px;">
              ${ev.root_cause_id || 'Not Yet Isolated'}
            </div>
          </div>
        </div>
      `;
    }

    function seekReplayStep(idx) {
      currentReplayIdx = idx;
      updateReplayDisplay();
    }

    function nextReplayStep() {
      if (currentReplayIdx < replayEvents.length - 1) {
        currentReplayIdx++;
        updateReplayDisplay();
      }
    }

    function prevReplayStep() {
      if (currentReplayIdx > 0) {
        currentReplayIdx--;
        updateReplayDisplay();
      }
    }

    function resetReplay() {
      currentReplayIdx = 0;
      updateReplayDisplay();
    }

    async function fetchEvaluationStatus() {
      try {
        const res = await fetch('/api/enterprise/evaluation');
        if (!res.ok) return;
        const d = await res.json();
        const el = document.getElementById('eval-status-desc');
        if (el && d.message) el.textContent = d.message;
      } catch (err) {
        console.error('Error fetching evaluation status:', err);
      }
    }

    // App Initialization
    async function init() {
      await loadTopology();
      await loadServices();
      await fetchHealthData();
      await fetchTwinSync();
      await fetchTwinState();
      await loadReplayTimeline();
      await fetchEvaluationStatus();

      // Background polling
      pollInterval = setInterval(() => {
        fetchHealthData();
        fetchTwinSync();
      }, 4000);
    }

    init();
  </script>
</body>
</html>
"""
