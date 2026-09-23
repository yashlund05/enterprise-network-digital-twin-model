# Digital Twin-Based Intelligent Enterprise Network Monitoring

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Test Suite](https://img.shields.io/badge/tests-167%20passed-brightgreen.svg)]()

A reproducible, simulator-based digital twin platform for intelligent enterprise network monitoring, root cause localization, redundancy-aware service impact analysis, and counterfactual What-If simulation.

---

## 1. Problem Statement

Modern enterprise campus and datacenter networks are complex multi-tier topologies supporting distributed business applications, VoIP telephony, ERP systems, and secure boundary gateways. When network degradation or hardware failures occur:
- **Alert Fatigue:** Monitoring systems generate flood waves of redundant symptom alarms across downstream devices.
- **Hidden Root Causes:** Diagnosing the true origin of an incident requires correlating multi-hop topological relationships, protocol behaviors, and cross-tier dependencies.
- **Unclear Blast Radius:** Network engineers lack immediate visibility into which business services are degraded versus protected by redundancy mechanisms (such as active/standby firewalls or multi-homed links).
- **Risky Change Validation:** Operational interventions and routing changes are traditionally tested directly in production due to the lack of an isolated, counterfactual sandbox.

---

## 2. Project Objective

The primary objective of this project is to build an intelligent, software-defined **Digital Twin** for enterprise networks that:
1. Maintains a **synchronized state model** of physical network infrastructure and dependency relationships.
2. Performs **multivariate composite anomaly detection** that eliminates false positives while detecting true operational incidents.
3. Automatically computes **top-ranked root causes** across multi-tier topologies.
4. Evaluates **business service impact** and calculates a quantitative **Blast Radius Index (BRI)** considering redundancy failovers.
5. Provides an isolated **counterfactual What-If simulation sandbox** for evaluating failure scenarios without production risk.
6. Delivers an interactive **unified operations console** and a **reproducible evaluation framework** benchmarked against modeled ground truth.

---

## 3. Why a Digital Twin?

A digital twin provides a software reflection of the physical infrastructure, capturing both operational state and structural dependencies:
- **Decoupled Telemetry Ingestion:** The twin buffers, synchronizes, and normalizes telemetry streams asynchronously, tracking telemetry staleness and topological consistency.
- **Graph-Centric Intelligence:** Algorithms for anomaly detection, root cause localization, and blast radius estimation run on the twin's live graph rather than querying distributed physical devices directly.
- **Counterfactual Experimentation:** The twin graph can be cloned and mutated in-memory to execute What-If failure simulations and predict alternative routing QoS without impacting the operational network.

---

## 4. Enterprise Architecture

The platform models a canonical multi-tier enterprise network comprising **22 nodes**, **44 bidirectional links**, and **6 critical services**:

```
                       [ External Ingress / WAN ]
                                   │
                    ┌──────────────┴──────────────┐
              [edge-gw-01]                  [edge-gw-02]         (Tier 1: Edge)
                    │        \          /        │
                    │          \      /          │
              [core-sw-01] ════════════════ [core-sw-02]         (Tier 2: Core Backbone)
               /        \                    /        \
              /          \                  /          \
     [dist-sw-campus-01] [dist-sw-campus-02] [dist-sw-dc-01] [dist-sw-dc-02]  (Tier 3: Distribution)
          /         \        /        \          /        \      /      \
    [acc-hq-01] [acc-hq-02] [acc-branch-01] [acc-dc-01]  [acc-dc-02] [acc-dc-03] (Tier 4: Access)
                                                 │             │          │
                                            [host-erp]    [host-api]  [host-db] [host-dns] (Tier 5: Hosts)
```

- **Architectural Tiers:** Edge Boundary (2), Core Backbone (2), Campus Distribution (2), Datacenter Distribution (2), Access Switching (10), and Application Hosts (4).
- **Service Dependency Graph:** Models enterprise applications (`srv-erp`, `srv-api`, `srv-db`, `srv-dns`, `srv-crm`, `srv-voip`) with explicit redundancy semantics (`active_active`, `active_standby`, `independent`).

---

## 5. Core Features

- **Digital Twin Synchronization:** Thread-safe ingestion tracking per-node staleness ($t_{\text{sync}} - t_{\text{last\_update}}$) and topology consistency scoring.
- **Multivariate Composite Anomaly Detection:** Rolling-window evaluation combining latency ($40\%$), packet loss ($35\%$), and CPU utilization ($25\%$) against a $3.0\sigma$ threshold to eliminate false positives.
- **Topology-Aware Root Cause Analysis (RCA):** Graph traversal incorporating upstream tier penalties, symptom correlation, and concurrent multi-fault diagnosis.
- **Redundancy-Aware Service Impact:** Traverses the service catalog DAG to identify directly versus transitively affected applications and computes the quantitative Blast Radius Index ($\text{BRI}$).
- **Counterfactual What-If Sandbox:** Clones the network state to simulate node/link failures, predicting end-to-end path latency deltas, packet loss, bottleneck throughput, and service disruption.
- **Incident Replay Engine:** Chronological 6-stage lifecycle playback ($\text{Warmup} \to \text{Normal} \to \text{Degradation} \to \text{Fault} \to \text{Recovery} \to \text{Post-Incident}$) for post-mortem forensics.
- **Unified Web Operations Console:** Single-page 9-view dashboard at `/enterprise` with real-time SVG topology visualization, Chart.js telemetry plots, and interactive controls.
- **Reproducible Evaluation Suite:** Deterministic 15-scenario benchmark with automated CSV, figure, JSON summary, and Markdown report generation.

---

## 6. System Architecture

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 Simulated Enterprise Physical Network                  │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Telemetry Samples (1s interval)
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                   Online Digital Twin Engine                           │
  │  - Thread-Safe Synchronization Buffer    - Per-Node Staleness Tracking │
  │  - Topology Consistency Scoring          - Graph State Management      │
  └──────────┬────────────────────────┬─────────────────────────┬──────────┘
             │                        │                         │
             ▼                        ▼                         ▼
  ┌───────────────────────┐┌───────────────────────┐┌───────────────────────┐
  │  Anomaly Detection    ││  Root Cause Analysis  ││    Service Impact     │
  │  - Multivariate Z     ││  - Causal Traversal   ││  - Dependency DAG     │
  │  - Zero False Alarm   ││  - Tier Penalty       ││  - Redundancy Model   │
  │  - Window: 60s        ││  - Top-K Candidate    ││  - Blast Radius (BRI) │
  └───────────────────────┘└───────────────────────┘└───────────────────────┘
             │                        │                         │
             └────────────────────────┼─────────────────────────┘
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │           What-If Sandbox & Incident Replay Engine                     │
  │  - Clone-and-Mutate Graph Sandbox        - 6-Stage Timeline Forensic   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        FastAPI REST Layer                              │
  │  - Endpoints: /api/enterprise/*          - Legacy: /dashboard, /health │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
  │   Enterprise Web Dashboard      │   │  Reproducible Evaluation Suite  │
  │   http://localhost:8000/enterprise│  │  results/enterprise/ artifacts │
  └─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 7. Technology Stack

- **Core Language:** Python 3.10+
- **Graph Modeling & Traversal:** NetworkX
- **API Framework:** FastAPI, Uvicorn, Starlette
- **Data Validation & Schemas:** Pydantic
- **Visualization & Artifacts:** Matplotlib, HTML5/CSS3, Chart.js, SVG
- **Quality Assurance & Verification:** Pytest, Pytest-Cov, Ruff

---

## 8. Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/example/telecom-network-digital-twin.git
cd telecom-network-digital-twin

# Create and activate virtual environment
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install package with all dependencies
pip install -e .
```

---

## 9. Running the Application

Start the unified enterprise API and dashboard server:

```bash
telecom-twin serve --host 127.0.0.1 --port 8000
```

Access the web interfaces:
- **Enterprise Operations Dashboard:** [http://127.0.0.1:8000/enterprise](http://127.0.0.1:8000/enterprise)
- **Interactive REST API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Legacy Telecom Dashboard (Preserved):** [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

---

## 10. CLI Usage Examples

The CLI provides subcommands for running simulations, inspections, and evaluations:

```bash
# Display top-level help and available commands
telecom-twin --help

# Inspect the canonical enterprise topology
telecom-twin inspect-topology

# Run a What-If failure simulation on Core Switch 01
telecom-twin whatif-sim --target-type node --target-id core-sw-01 --failure-type node_down

# Execute the deterministic 15-scenario evaluation suite
telecom-twin enterprise-evaluation --output-dir results/enterprise --seed 42
```

---

## 11. What-If Counterfactual Simulation Example

Simulating the failure of an active backbone node (`core-sw-01`) outputs the predicted alternative routing impact:

```bash
telecom-twin whatif-sim --target-type node --target-id core-sw-01 --failure-type node_down
```

```text
============================================================
WHAT-IF COUNTERFACTUAL SIMULATION RESULT
============================================================
Scenario ID:         cli-whatif-001
Target:              core-sw-01 (node)
Failure Type:        node_down (value: 1.0)
Predicted Severity:  CRITICAL
Blast Radius:        100.0%
Latency Delta:       +0.00 ms
Loss Delta:          +0.00%
Throughput Delta:    0.00 Mbps
Affected Nodes:      core-sw-01
Affected Links:      core-sw-01<->core-sw-02, core-sw-01<->dist-sw-campus-01, core-sw-01<->dist-sw-campus-02, core-sw-01<->dist-sw-dc-01, core-sw-01<->dist-sw-dc-02, core-sw-01<->edge-gw-01, core-sw-01<->edge-gw-02
Affected Services:   srv-api, srv-auth, srv-db, srv-dns, srv-erp, srv-monitoring
============================================================
```

*Explanation:* Simulating an outage on `core-sw-01` identifies the impacted transit links and assesses downstream business application vulnerability across the multi-tier enterprise topology.

---

## 12. Evaluation Methodology & Measured Results

The platform includes a deterministic benchmark evaluating **15 scenarios** (13 single-node failures across all tiers and fault types, plus 2 multi-fault scenarios) against modeled ground truth.

### Anomaly Detection & Baseline Comparison

Evaluation compares the **Enterprise Multivariate Composite Detector** against a **Single-Metric Max-Z Baseline**:

| Evaluation Level | Metric | Enterprise Composite ($3.0\sigma$) | Baseline Legacy Max-Z ($5.0\sigma$) | Architectural Trade-Off |
| :--- | :--- | :--- | :--- | :--- |
| **Point-Wise** ($Node \times Timestep$) | **Precision** | **1.0000** | 0.9725 | Enterprise achieves zero false positives (0 FP vs 3 FP) |
| **Point-Wise** ($Node \times Timestep$) | **Recall** | 0.0784 | **0.0945** | Baseline triggers on single-metric deviations |
| **Point-Wise** ($Node \times Timestep$) | **$F_1$ Score** | 0.1455 | **0.1722** | Baseline achieves higher point-wise $F_1$ (+0.0267) |
| **Point-Wise** ($Node \times Timestep$) | **False Positive Rate** | **0.000000** | 0.000062 | Enterprise completely eliminates false alarms |
| **Incident** (Scenario Level) | **Detection Rate** | **86.7% (13/15)** | **86.7% (13/15)** | Identical incident-level detection coverage |
| **Incident** (Scenario Level) | **Mean Detection Delay** | **16.87 s** | **16.87 s** | Identical mean delay (1.0s detected, 120s timeout) |

> [!NOTE]
> **Performance Trade-Off:** The baseline single-metric detector achieves higher point-wise recall and $F_1$ score because any single metric deviation flags an alert. However, this creates false alarms ($FPR = 0.000062$). The enterprise detector requires cross-metric corroboration ($0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}} \ge 3.0$), achieving perfect precision ($1.0000$) and zero false positives ($FPR = 0.000000$) while matching the baseline at the incident level ($86.7\%$ detected).

### Summary of System Capabilities

| Capability | Metric | Value | Evaluation Basis |
| :--- | :--- | :--- | :--- |
| **Root Cause Analysis (RCA)** | Top-1 Accuracy | **84.6%** (11/13 single) | Evaluated against known injected causal roots |
| **Root Cause Analysis (RCA)** | Top-3 Accuracy | **84.6%** | Evaluated against known injected causal roots |
| **Root Cause Analysis (RCA)** | Mean Reciprocal Rank (MRR) | **0.8462** | Mean reciprocal candidate rank |
| **Root Cause Analysis (RCA)** | Multi-Fault Detection Rate | **50.0%** (1/2 multi) | Both injected roots identified in candidate set |
| **Service Impact Prediction** | Service Precision | **1.0000** | **Model-Consistency Validation** (Graph reachability) |
| **Service Impact Prediction** | Service Recall | **1.0000** | **Model-Consistency Validation** (Dependency DAG) |
| **Service Impact Prediction** | Blast Radius Index MAE | **0.00%** | **Model-Consistency Validation** (Redundancy rules) |
| **What-If Simulation** | Latency Delta MAE | **312.96 ms** | Simulator-Based Validation (Multi-hop path vs device fault) |
| **What-If Simulation** | Packet Loss Delta MAE | **31.36%** | Simulator-Based Validation |
| **What-If Simulation** | Throughput Delta MAE | **3,542.08 Mbps** | Simulator-Based Validation |
| **What-If Simulation** | Service Impact Jaccard | **0.9103** | Topological service impact fidelity |
| **Twin Synchronization** | Nominal Mean Staleness | **0.00 s** | Deterministic simulation run (100% sync) |
| **Twin Synchronization** | Delayed Case (5s lag) | **6.00 s** | Deterministic lag simulation run |
| **Twin Synchronization** | Missing Case (20% drop) | **5.68 s** | Deterministic missing-node simulation run |

---

## 13. Limitations & Academic Scope

- **Synthetic Topology:** Evaluated on a canonical 22-node enterprise campus/DC topology rather than a live multi-thousand node production enterprise.
- **Modeled Ground Truth:** Evaluation baselines reflect algorithmic graph reachability and statistical telemetry generation rather than live physical network packet probes.
- **Model-Consistency Validation:** Service impact metrics verify internal algorithmic graph consistency between the analyzer and the service catalog DAG.
- **Scope Distinction in What-If:** What-If MAE reflects the architectural difference between multi-hop end-to-end client path bottleneck modeling versus localized device telemetry fault injection (e.g., $999\text{ ms}$ on physical node down).

---

## 14. Project Structure

```
telecom-network-digital-twin/
├── src/
│   └── telecom_twin/
│       ├── __init__.py                # Package version and export definitions
│       ├── models.py                  # Enterprise domain models, enums, dataclasses
│       ├── enterprise_topology.py     # Canonical 22-node / 44-link enterprise network
│       ├── enterprise_telemetry.py    # Statistical multi-tier telemetry generator
│       ├── services.py                # Service catalog DAG and blast radius analyzer
│       ├── root_cause.py              # Topology-aware causal RCA engine
│       ├── whatif.py                  # Counterfactual What-If simulation sandbox
│       ├── replay.py                  # 6-stage operational incident replay engine
│       ├── online.py                  # OnlineTwin state synchronization & anomaly detector
│       ├── api.py                     # Unified FastAPI application and enterprise routing
│       ├── cli.py                     # Command-line interface subcommands
│       ├── enterprise_dashboard.py    # 9-view operations console web application
│       ├── evaluation.py              # Reproducible 15-scenario evaluation framework
│       ├── simulation.py              # Legacy discrete-event queueing model (preserved)
│       └── dashboard.py               # Legacy telecom dashboard (preserved)
├── tests/
│   ├── test_enterprise.py            # Comprehensive enterprise test suite (145 tests)
│   ├── test_api.py                   # Legacy API endpoint tests
│   ├── test_simulation.py            # Legacy queueing model tests
│   └── ...                           # Total: 167 automated unit & integration tests
├── results/
│   └── enterprise/                   # Generated evaluation artifacts (CSVs, figures, JSON)
├── docs/
│   ├── ARCHITECTURE.md               # Detailed system and graph architecture document
│   ├── EXPERIMENTS.md                # Formal experiment methodology and benchmark report
│   ├── DEMO.md                       # Step-by-step professor demonstration guide
│   └── FINAL_VERIFICATION.md         # Final pre-submission verification checklist
├── UPSTREAM.md                       # Provenance and upstream attribution document
├── LICENSE                           # MIT License
├── pyproject.toml                    # Build metadata and package configuration
└── README.md                         # This file
```

---

## 15. Testing & Verification

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run tests with coverage summary
pytest --cov=telecom_twin

# Check code formatting and style
ruff check .
```

---

## 16. Upstream Attribution & License

This project is adapted and substantially extended from the open-source telecom digital twin project by **Feng Dekai**.
- For detailed provenance, inherited modules, and novel contributions, see [`UPSTREAM.md`](UPSTREAM.md).
- Licensed under the [MIT License](LICENSE). Copyright © 2026 Feng Dekai and Project Contributors.
