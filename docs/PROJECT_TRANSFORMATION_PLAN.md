# Project Transformation Plan: Digital Twin-Based Intelligent Enterprise Network Monitoring

**Target System:** Digital Twin-Based Intelligent Enterprise Network Monitoring  
**Academic Context:** University Subject Evaluation / Final Year Capstone Project  
**Author / Engineering Team:** College Project Team  
**Upstream Provenance:** Extended from `telecom-network-digital-twin` (v1.0.0, MIT License, Copyright 2026 Feng Dekai)

---

## 1. Executive Summary & Project Goal

The primary objective of this project is to transform an existing synthetic telecom-oriented digital twin into a sophisticated, realistic, and fully-featured **Intelligent Enterprise Network Digital Twin**. The system addresses the complexities of modern corporate infrastructure: campus and data-center network hierarchies, core business application dependencies (ERP, Database, Auth, DNS, Internal API), real-time telemetry streaming, graph-based root-cause analysis (RCA), predictive "What-If" failure simulation, and comprehensive blast-radius evaluation.

The project strictly follows our core design rules:
1. Preserve working upstream functionality through modular extensions and safe compatibility shims.
2. Avoid unnecessary heavy technologies or distributed frameworks (keeping deployment lightweight, deterministic, and self-contained).
3. Do not rely on external LLM calls for core diagnostics; retain classical machine learning, statistical methods, temporal reasoning, and graph algorithms.
4. Maintain full open-source attribution to the upstream author while clearly highlighting our novel contributions in code, models, UI, evaluation, and documentation.

---

## 2. Component Classification Matrix

Every major component of the existing repository is classified below into **KEEP**, **MODIFY**, **REMOVE**, **REPLACE**, or **NEW**, with complete engineering justification.

| Component / File | Classification | Rationale & Transformation Detail |
|---|---|---|
| `LICENSE` | **KEEP** | Original MIT License (Feng Dekai, 2026) must remain intact to honor open-source licensing and university ethics. |
| `src/telecom_twin/protocols.py` | **KEEP** | The management-plane telemetry protocol evaluation (Fixed Polling vs Adaptive Delta) is mathematically elegant, works perfectly, and provides valuable benchmark metrics for enterprise network management overhead. |
| `src/telecom_twin/robustness.py` | **KEEP** | The 4,860-trial Monte Carlo robustness benchmark testing topology vs temporal coherence under missing/false alarm noise is a core theoretical contribution that will be retained as an academic baseline. |
| `src/telecom_twin/models.py` | **MODIFY** | Expand domain records. Retain `NetworkNode`, `NetworkLink`, `TelemetrySample`, `Alarm`, but extend them with enterprise attributes (e.g. `interface_health`, `memory_percent`, `vlan_id`) and introduce new models: `EnterpriseService`, `ServiceDependency`, `WhatIfScenario`, `WhatIfResult`, `IncidentTimelineEvent`, `TwinSyncState`. |
| `src/telecom_twin/topology.py` | **MODIFY** | Retain deterministic generation logic, but adapt the structure into a believable enterprise campus & datacenter topology (Edge Gateway / Firewall, Core Switch Tier, Distribution Tier, Access Tier, and Enterprise Server Pods). Retain backward-compatible helper for legacy tests. |
| `src/telecom_twin/simulation.py` | **MODIFY** | Retain Gaussian & sinusoidal telemetry models, but enrich telemetry to encompass enterprise server workloads (CPU, Memory, Latency, Packet Loss, Throughput, Interface Health, Error Counts) and realistic multi-incident patterns. |
| `src/telecom_twin/online.py` | **MODIFY** | Upgrade `OnlineTwin` from a telecom replay into an Enterprise Digital Twin. Retain `RollingAnomalyDetector` (z-score), add severity levels (Warning/Critical), and track synchronization metrics: sync timestamp, telemetry staleness, node sync state, and state consistency. |
| `src/telecom_twin/root_cause.py` | **MODIFY** | Retain hierarchy-aware graph scoring; generalize it to support multi-layer enterprise dependencies (Link -> Switch -> Host -> Service Dependency Graph) with root-cause confidence. |
| `src/telecom_twin/multifault.py` | **MODIFY** | Upgrade synthetic "access node" impact to real enterprise service impact analysis. Compute blast-radius scores across services (ERP, DB, Auth, DNS, Internal API), business criticality, and affected network paths. |
| `src/telecom_twin/api.py` | **MODIFY** | Retain all existing REST/SSE endpoints for backward compatibility, while adding enterprise endpoints: `/api/v2/services`, `/api/v2/impact`, `/api/v2/whatif/simulate`, `/api/v2/replay/timeline`, `/api/v2/twin/sync-status`. |
| `src/telecom_twin/dashboard.py` | **REPLACE** | Replace the minimal single-pane telecom SVG view with a unified, state-of-the-art **Enterprise Network Operations Command Center** featuring 9 integrated views (Command Center, Live Twin, Topology, Incident Center, RCA, Service Impact, What-If Simulation, Incident Replay, and Evaluation/Stats). |
| `src/telecom_twin/cli.py` | **MODIFY** | Support new CLI commands: `enterprise-demo`, `whatif`, `evaluate-all`, `serve-enterprise`, while preserving legacy CLI arguments. |
| `pyproject.toml` | **MODIFY** | Update project metadata to reflect the new project title, university scope, and CLI scripts, while retaining existing dependencies and dev tools. |
| `README.md` | **MODIFY** | Completely rewrite the project README for the enterprise network digital twin, clearly defining problem statement, academic motivation, architecture, usage, evaluation results, limitations, and upstream attribution. |
| `docs/cv_summary.md` | **REPLACE** | Replace with `docs/PROJECT_PORTFOLIO_SUMMARY.md` presenting the enterprise digital twin college project. |
| `src/telecom_twin/whatif.py` | **NEW** | Standalone sandbox simulation engine that applies hypothetical scenarios (node failure, link cut, latency spike, traffic overload) against the twin state without perturbing the live monitored network, predicting blast radius and QoS degradation. |
| `src/telecom_twin/replay.py` | **NEW** | Incident timeline engine capturing states across lifecycle stages: `Normal -> Degradation -> Anomaly -> RCA -> Impact -> Remediation/Recovery`, enabling interactive step-by-step playback. |
| `src/telecom_twin/services.py` | **NEW** | Enterprise service catalog, dependency mapping, SLA tracking, and path-tracing engine linking infrastructure elements to business services (ERP, Database, DNS, Auth, Internal API). |
| `src/telecom_twin/evaluation.py` | **NEW** | Comprehensive academic evaluation harness computing precision, recall, F1, detection delay, RCA Top-1/Top-3 accuracy, blast-radius accuracy, twin synchronization delay, and what-if prediction error. |
| `tests/test_enterprise.py` | **NEW** | Test suite for enterprise topology, service dependencies, what-if simulations, incident replay, and sync metrics. |
| `tests/test_whatif.py` | **NEW** | Test suite verifying that what-if simulations are isolated, deterministic, and do not mutate the live twin state. |
| `UPSTREAM.md` | **NEW** | Detailed provenance and attribution document explicitly specifying what was inherited from upstream and what was created by our team. |
| `ARCHITECTURE.md` | **NEW** | Comprehensive architectural specification of the enterprise network digital twin. |
| `EXPERIMENTS.md` | **NEW** | Academic experimentation guide and empirical results documentation. |

---

## 3. Target Logical Architecture & Enterprise Topology

### 3.1 Network Tiering Model
```
                  [ External Users / Remote Offices ]
                                  │
                          [ Internet WAN ]
                                  │
                      ┌──────────────────────┐
                      │    Edge Gateways     │  (edge-gw-01, edge-gw-02)
                      │ (Firewall / Border)  │  20 Gbps active/standby
                      └──────────┬───────────┘
                                 │
                      ┌──────────┴───────────┐
                      │     Core Network     │  (core-sw-01, core-sw-02)
                      │    (Campus Spine)    │  40 Gbps redundant fabric
                      └──────────┬───────────┘
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
┌────────────────────────┐              ┌────────────────────────┐
│  Distribution Layer 1  │              │  Distribution Layer 2  │  (dist-sw-01, dist-sw-02)
│      (HQ Campus)       │              │     (Data Center)      │  10 Gbps uplinks
└────────────┬───────────┘              └────────────┬───────────┘
             │                                       │
     ┌───────┴───────┐                       ┌───────┴───────┐
     │               │                       │               │
┌─────────┐     ┌─────────┐             ┌─────────┐     ┌─────────┐
│ Access  │     │ Access  │             │ Server  │     │ Server  │ (acc-sw-01..04)
│ Switch1 │     │ Switch2 │             │ Leaf 1  │     │ Leaf 2  │ 1 Gbps access
└────┬────┘     └────┬────┘             └────┬────┘     └────┬────┘
     │               │                       │               │
[Workstations]  [Workstations]          ┌────┴────┐     ┌────┴────┐
[Engineering]   [Operations]            │App Pod 1│     │App Pod 2│
                                        │(ERP/API)│     │ (DB/DNS)│
```

### 3.2 Enterprise Application Service Catalog & Dependency Graph
```
           ┌──────────────┐
           │     DNS      │ (srv-dns: Core infrastructure service)
           └──────▲───────┘
                  │ depends-on
           ┌──────┴───────┐
           │     Auth     │ (srv-auth: SSO / Active Directory / Kerberos)
           └──────▲───────┘
                  │ depends-on
           ┌──────┴───────┐
           │   Database   │ (srv-db: Enterprise PostgreSQL / Cluster)
           └──────▲───────┘
                  │ depends-on
           ┌──────┴───────┐
           │ Internal API │ (srv-api: Microservices gateway & business logic)
           └──────▲───────┘
                  │ depends-on
           ┌──────┴───────┐
           │  ERP System  │ (srv-erp: Enterprise Resource Planning application)
           └──────────────┘
```

When an underlying network link or switch experiences packet loss or latency spikes, the degradation cascades through the network path to the host server, and propagates up the application dependency chain.

---

## 4. The 13 Core Pillars of the Target System

1. **Enterprise Network Digital Twin:** High-fidelity in-memory digital twin reflecting current topology, switch/router states, interface bandwidths, and node telemetry.
2. **Real-Time & Simulated Telemetry:** Realistic multi-metric telemetry (CPU, Memory, Latency, Loss, Jitter, Throughput, Interface Errors).
3. **Network Health Monitoring:** Continuous calculation of per-node, per-link, and overall enterprise health scores (0-100%).
4. **Intelligent Anomaly Detection:** Multivariate rolling statistical detection (z-score + EWMA + threshold checks) generating structured anomaly events with severity classification (Info, Warning, Critical).
5. **Topology-Aware Root-Cause Analysis:** Multi-layer graph traversal and temporal coherence ranking that pinpoints the root cause amidst cascading alarm storms.
6. **Enterprise Service Dependency Mapping:** Explicit mapping linking physical network nodes to server hosts, and server hosts to dependent business applications.
7. **Service Impact & Blast-Radius Analysis:** Deterministic calculation of affected network paths, downstream services, and enterprise business impact percentage upon fault occurrence.
8. **What-If Network Fault Simulation:** Isolated twin sandbox allowing network operators to model hypothetical failures (e.g., "What if `dist-sw-02` fails during peak hours?") and predict resulting latency and service downtime.
9. **Incident Replay Engine:** Chronological incident playback allowing operators to step through: Normal $\to$ Degradation $\to$ Anomaly Trigger $\to$ RCA Attribution $\to$ Service Impact $\to$ Remediation.
10. **Academic Evaluation Framework:** Rigorous empirical evaluation generating tables and charts for: Precision/Recall/F1, Detection Latency, Top-1/Top-3 RCA Accuracy, Blast Radius Precision/Recall, and What-If Prediction Error.
11. **Unified Enterprise Web Dashboard:** Modern, cohesive dark-theme operations dashboard with 9 tabbed views and responsive visual components.
12. **Clean REST & SSE API Layer:** Standardized FastAPI backend serving live snapshots, streaming SSE updates, and management endpoints.
13. **Automated Testing Suite:** 100% passing unit and integration tests covering all legacy and new functionality.

---

## 5. Phased Transformation Roadmap

### Phase 3 — Enterprise Refactor
- Define enterprise network models (`EnterpriseService`, `ServiceDependency`, `PathSegment`).
- Implement `enterprise_topology.py` modeling the Edge, Core, Distribution, Access, and Server Pod layout.
- Adapt telemetry generation to produce enterprise server load patterns.

### Phase 4 — Digital Twin Synchronization & State
- Enhance `OnlineTwin` with synchronization metadata (`sync_timestamp`, `telemetry_staleness`, `consistency_score`, `link_states`).
- Expose detailed health metrics per tier and per service.

### Phase 5 — Intelligence: Anomaly Detection & RCA
- Expand `RollingAnomalyDetector` to compute multi-metric anomaly confidence and severity (`warning`, `critical`).
- Upgrade RCA to handle service-layer root causes and cross-tier enterprise routing paths.

### Phase 6 — Service Impact & Blast Radius
- Implement `services.py` containing service-to-infrastructure dependency graph.
- Implement blast-radius calculator determining affected services, affected paths, and criticality scores.

### Phase 7 — What-If Fault Simulation
- Implement `whatif.py` executing hypothetical scenario simulations in a deep-copied digital twin sandbox.
- Predict latency deltas, packet loss increase, and degraded services without mutating live twin state.

### Phase 8 — Incident Replay Engine
- Implement `replay.py` recording snapshot history across lifecycle phases.
- Provide step-by-step playback controls (rewind, step forward, play, inspect).

### Phase 9 — Dashboard Transformation
- Overhaul `dashboard.py` into a unified Enterprise Operations Center with 9 dedicated views.
- Render interactive SVG network maps, application dependency diagrams, real-time telemetry charts, and what-if controls.

### Phase 10 — Evaluation Framework & Academic Benchmarks
- Implement `evaluation.py` producing reproducible benchmark metrics:
  - Anomaly detection: Precision, Recall, F1, Detection Delay.
  - RCA: Top-1 and Top-3 accuracy across enterprise failure scenarios.
  - Blast Radius: Precision and Recall of predicted affected services.
  - What-If: Predicted vs observed latency, throughput, and error.
- Export CSVs and Matplotlib figures for the project report.

### Phase 11 — Documentation & Upstream Attribution
- Author `README.md`, `ARCHITECTURE.md`, `EXPERIMENTS.md`, `UPSTREAM.md`.
- Retain `LICENSE` intact.

### Phase 12 — Quality Control & Verification
- Execute full test suite (`pytest`).
- Validate CLI commands and API endpoints.
- Ensure zero broken links, placeholders, or dead UI buttons.

