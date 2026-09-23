# Enterprise Digital Twin: Demonstration Guide

**Project:** Digital Twin-Based Intelligent Enterprise Network Monitoring  
**Target Audience:** Academic Reviewers, Evaluators, and Engineering Demonstrations  
**Estimated Demo Duration:** 10–15 minutes  

---

## Prerequisites & Setup

Ensure the virtual environment is activated and the package is installed in editable mode:

```bash
# Activate your virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Verify test suite is green
pytest -q
```

---

## Demonstration Walkthrough

### Step 1: Start the Enterprise Server

Launch the unified enterprise backend and dashboard:

```bash
telecom-twin serve --host 127.0.0.1 --port 8000
```

Verify output indicates Uvicorn is running:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

### Step 2: Open the Enterprise Dashboard

Open your browser and navigate to:
```text
http://localhost:8000/enterprise
```
*(Note: The legacy telecom dashboard remains available at `http://localhost:8000/dashboard` for backward compatibility demonstration).*

---

### Step 3: View 1 — Command Center Overview

- **What to show:**
  - The real-time metric cards displaying **22 Monitored Nodes**, **44 Links**, **6 Active Services**, **Twin Synchronization Status** (100% Synchronized, Mean Staleness $0.0\text{ s}$), and **Active Anomalies**.
  - Highlight the synchronized digital clock and health status badges.

---

### Step 4: View 2 — Network Topology (22 Nodes, 44 Links)

- **What to show:**
  - Click on the **Network Topology** tab.
  - Show the 5 architectural tiers laid out hierarchically:
    1. **Edge Tier:** `edge-gw-01`, `edge-gw-02`
    2. **Core Tier:** `core-sw-01`, `core-sw-02`
    3. **Distribution Tier:** Campus Distribution (`dist-sw-campus-01/02`) and Datacenter Distribution (`dist-sw-dc-01/02`)
    4. **Access Tier:** 10 campus, branch, and rack access switches
    5. **Host Tier:** Application servers (`host-erp`, `host-api`, `host-db`, `host-dns`)
  - Click any node (e.g. `core-sw-01`) to inspect its properties, connected links, and real-time operational status.

---

### Step 5: View 3 — Live Telemetry & Digital Twin Synchronization

- **What to show:**
  - Click on the **Telemetry & Sync** tab.
  - Explain the digital twin's role: continuously buffering and synchronizing multi-metric streams (Latency, Packet Loss, Throughput, CPU, Memory).
  - Observe the per-node staleness table: all nodes report staleness $< 3.0\text{ s}$ with topology consistency score of $1.0000$.

---

### Step 6: View 4 — Anomaly Detection

- **What to show:**
  - Click on the **Anomaly Detection** tab.
  - Highlight the **Multivariate Composite Z-Score Formulation**:
    $$Z_{\text{composite}} = 0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}} \ge 3.0$$
  - Point out that this multi-metric corroboration achieves **zero false positives** ($\text{FPR} = 0.000000$), completely eliminating alarm fatigue compared to isolated single-metric spikes.

---

### Step 7: View 5 — Root Cause Analysis (RCA)

- **What to show:**
  - Click on the **Root Cause Analysis** tab.
  - Inspect the diagnostic candidate table. Explain the causal graph ranking algorithm:
    - Combines local anomaly severity with upstream tier bias and downstream symptom propagation footprint.
    - Demonstrates **84.6% Top-1 accuracy** and **0.8462 Mean Reciprocal Rank (MRR)**.

---

### Step 8: View 6 — Service Dependency & Blast Radius

- **What to show:**
  - Click on the **Service Impact** tab.
  - Show the 6 enterprise business applications: `srv-erp`, `srv-api`, `srv-db`, `srv-dns`, `srv-crm`, `srv-voip`.
  - Explain redundancy awareness:
    - Active/Active paths gracefully degrade performance without complete service drops.
    - Active/Standby firewalls fail over to preserve availability.
    - Core DNS failure transitively cascades across all 6 applications.
  - Highlight the quantitative **Blast Radius Index (BRI)**.

---

### Step 9: View 7 — Counterfactual What-If Sandbox

- **What to show:**
  - Click on the **What-If Simulation** tab.
  - Configure a simulation:
    - **Target Type:** `node`
    - **Target Node:** `core-sw-01`
    - **Failure Type:** `node_down`
  - Click **Run What-If Simulation**.
  - **Show the result:**
    - The twin clones the network graph in memory and tests alternative shortest path routing.
    - Traffic reroutes through `core-sw-02` (failover available).
    - Result shows estimated $+12.5\text{ ms}$ latency increase, $-1500\text{ Mbps}$ bottleneck capacity reduction, and impacted services (`srv-erp`, `srv-crm`, `srv-api`).
  - Demonstrate that production state is completely unaffected.

---

### Step 10: View 8 — Operational Incident Replay

- **What to show:**
  - Click on the **Incident Replay** tab.
  - Show the 6-stage operational incident timeline:
    `WARMUP` $\to$ `NORMAL` $\to$ `DEGRADATION` $\to$ `FAULT` $\to$ `RECOVERY` $\to$ `POST-INCIDENT`.
  - Click **Play** or step through the timeline to demonstrate post-mortem incident playback.

---

### Step 11: View 9 — Reproducible Evaluation & Artifacts

- **What to show:**
  - Click on the **Evaluation & Stats** tab.
  - Show the completed evaluation dashboard with the 5 capability panels:
    1. **Anomaly Detection (Point-Wise vs Incident):** Perfect precision ($1.0000$), zero false alarms, $86.7\%$ incident detection rate.
    2. **Root Cause Analysis:** $84.6\%$ Top-1 accuracy, $0.8462$ MRR.
    3. **Service Impact (Model-Consistency Validation):** $1.0000$ Jaccard similarity and $0.00\%$ blast radius error.
    4. **What-If Simulation (Bottleneck QoS Validation):** Latency MAE $312.96\text{ ms}$, Throughput MAE $3,542\text{ Mbps}$, Service Jaccard $0.9103$.
    5. **Digital Twin Synchronization:** $0.00\text{ s}$ nominal staleness, $100\%$ synchronized nodes.
  - Point to the generated artifacts table and show that all reports and figures reside in `results/enterprise/`.

---

## Verified CLI Commands for Live Terminal Demonstrations

In a terminal, you can also run these standalone commands:

```bash
# 1. Display CLI top-level subcommands
telecom-twin --help

# 2. Run What-If simulation from command line
telecom-twin whatif-sim --target-type node --target-id core-sw-01 --failure-type node_down

# 3. View the markdown academic report
cat results/enterprise/evaluation_report.md
```
