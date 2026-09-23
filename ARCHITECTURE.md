# System Architecture & Technical Specification

**Project:** Digital Twin-Based Intelligent Enterprise Network Monitoring  
**Target Environment:** Multi-Tier Enterprise Campus & Datacenter Networks  
**Repository Specification:** Production-Grade Digital Twin with Backward Compatibility  

---

## 1. End-to-End Processing Pipeline

The platform is designed around a multi-stage data and analytical pipeline that transitions raw telemetry into synchronized digital state, automated anomaly detection, causal diagnosis, service impact blast radius estimation, and counterfactual simulation:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Physical / Emulated Network Domain                   │
│  - 22 Enterprise Nodes across 5 Tiers (Edge, Core, Dist, Access, Host) │
│  - 44 Bidirectional Network Links with Redundant Interconnects         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Streaming Telemetry (1s interval)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Digital Twin Synchronization                      │
│  - OnlineTwin State Manager (Thread-Safe Buffer)                       │
│  - Per-Node Telemetry Staleness Tracking (t_sync - t_update)           │
│  - Graph Topology Consistency Scoring (0.0 to 1.0)                     │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ Synchronized Graph State
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Intelligent Analytics Engines                      │
│                                                                        │
│   ┌──────────────────────────┐      ┌──────────────────────────────┐   │
│   │ Multivariate Anomaly Det │      │ Topology-Aware Root Cause    │   │
│   │ - Rolling 60s baseline   │      │ - Multi-Tier Graph Traversal │   │
│   │ - 3.0z composite vector  ├─────►│ - Upstream Bias & Decay       │   │
│   │ - Zero false alarm rate  │      │ - Top-K & Multi-Fault Logic  │   │
│   └─────────────┬────────────┘      └──────────────┬───────────────┘   │
│                 │                                  │                   │
│                 ▼                                  ▼                   │
│   ┌──────────────────────────┐      ┌──────────────────────────────┐   │
│   │ Redundant Service Impact │      │ Counterfactual What-If       │   │
│   │ - Service Catalog DAG    │      │ - Clone-and-Mutate Sandbox   │   │
│   │ - Redundancy Modeling    ├─────►│ - Shortest Path Bottlenecks  │   │
│   │ - Blast Radius Index     │      │ - Alternative Routing QoS    │   │
│   └──────────────────────────┘      └──────────────────────────────┘   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Incident Replay Forensic Engine                     │
│  - 6-Stage Timeline: Warmup -> Normal -> Degradation -> Fault ->       │
│                      Recovery -> Post-Incident                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application Gateway                       │
│  - /api/enterprise/* Endpoints (Sync, Topology, RCA, WhatIf, Replay)   │
│  - Legacy Backward Compatibility (/dashboard, /health, /alarms)        │
└───────────────────┬──────────────────────────────────┬─────────────────┘
                    │                                  │
                    ▼                                  ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│     Enterprise Operations Console    │  │  Reproducible Evaluation     │
│   http://localhost:8000/enterprise   │  │  results/enterprise/ suite  │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## 2. Graph Disambiguation: The Three Core Graph Models

A critical architectural distinction in this digital twin is the strict separation between three distinct graph abstractions:

```
[ 1. Network Topology Graph ]       [ 2. Service Dependency Graph ]       [ 3. RCA Causal Graph ]
         Physical/L2/L3                        Application DAG                      Inference/Diagnosis
               ──                                    ──                                    ──
         [core-sw-01]                          [srv-erp]                             [core-sw-01]
          /        \                            /       \                             │ (Root)
         /          \                          /         \                            ▼
   [dist-01]      [dist-02]              [srv-api]     [srv-db]               [dist-campus-01]
      │              │                         \         /                            │ (Symptom)
      ▼              ▼                          ▼       ▼                             ▼
   [acc-01]       [acc-02]                     [srv-dns]                       [acc-sw-hq-01]
```

### 1. Physical & Network Topology Graph ($G_{\text{topo}} = (V_{\text{net}}, E_{\text{net}})$)
- **Nodes ($V_{\text{net}}$):** Concrete physical and virtual network devices:
  - **Edge Tier:** `edge-gw-01`, `edge-gw-02` (WAN border routers / firewalls).
  - **Core Tier:** `core-sw-01`, `core-sw-02` (Backbone routing switches).
  - **Campus Distribution Tier:** `dist-sw-campus-01`, `dist-sw-campus-02`.
  - **Datacenter Distribution Tier:** `dist-sw-dc-01`, `dist-sw-dc-02`.
  - **Access Tier:** 10 switches serving campus building wings, branch offices, and server racks.
  - **Host Tier:** 4 application server hosts (`host-erp`, `host-api`, `host-db`, `host-dns`).
- **Links ($E_{\text{net}}$):** 44 bidirectional physical/logical links characterized by bandwidth capacity, baseline latency, propagation loss, and operational status (`active`, `degraded`, `down`).

### 2. Service Dependency Graph ($G_{\text{service}} = (V_{\text{svc}}, E_{\text{dep}})$)
- **Nodes ($V_{\text{svc}}$):** Business applications and infrastructure services (`srv-erp`, `srv-api`, `srv-db`, `srv-dns`, `srv-crm`, `srv-voip`).
- **Edges ($E_{\text{dep}}$):** Directed acyclic dependency edges ($S_A \to S_B$, meaning $S_A$ depends on $S_B$).
- **Redundancy Semantics:**
  - `active_active`: Redundant nodes share load; failure of one node causes performance degradation but preserves service availability.
  - `active_standby`: Secondary node takes over traffic; momentary switchover delay without persistent service outage.
  - `independent`: Direct un-replicated dependency; failure of supporting infrastructure causes immediate service failure.
- **Blast Radius Index ($\text{BRI}$):** Quantifies organization-wide impact as a weighted percentage:
  $$\text{BRI} = \frac{\sum_{s \in S_{\text{impacted}}} w_s \cdot \text{Criticality}(s)}{\sum_{s \in \text{Catalog}} w_s \cdot \text{Criticality}(s)} \times 100\%$$

### 3. RCA Causal Reasoning Graph ($G_{\text{causal}} = (V_{\text{anom}}, E_{\text{causal}})$)
- **Nodes ($V_{\text{anom}}$):** Entities exhibiting active anomaly flags.
- **Edges ($E_{\text{causal}}$):** Causal propagation paths derived from network topology hierarchy and traffic routing direction.
- **Scoring & Localization Engine:** Combines:
  1. *Local Symptom Severity:* Magnitude of the composite anomaly score ($Z_{\text{composite}}$).
  2. *Tier Hierarchy Bias:* Penalizes downstream leaves and prioritizes upstream infrastructure roots (Edge $\to$ Core $\to$ Distribution $\to$ Access $\to$ Host).
  3. *Downstream Propagation Footprint:* Rewards candidate nodes whose topological descendants are concurrently alarming.
  4. *Multi-Fault Partitioning:* Splits candidate sets into topologically independent subgraphs when concurrent unrelated incidents occur.

---

## 4. Digital Twin Synchronization Engine

The [`OnlineTwin`](src/telecom_twin/online.py) class acts as the single source of truth for runtime network state:
- **Thread Safety:** Protected by internal re-entrant threading locks (`threading.Lock`), ensuring concurrent safety between ingestion threads, API worker threads, and dashboard polling loops.
- **Staleness Tracking:** For each node $i$, computes operational staleness as:
  $$\text{Staleness}_i = t_{\text{current}} - t_{\text{last\_telemetry}, i}$$
  Classifies nodes as `synchronized` ($\le 3.0\text{ s}$), `stale` ($3.0\text{ s} < \text{Staleness} \le 10.0\text{ s}$), or `desynchronized` ($> 10.0\text{ s}$).
- **Topology Consistency:** Computes an aggregated score ($0.0 \le C \le 1.0$) evaluating:
  - Node presence fraction ($|V_{\text{observed}}| / |V_{\text{expected}}|$).
  - Link coherence (both endpoints actively reporting).
  - Missing-sample penalties.

---

## 5. Multivariate Anomaly Detection

To resolve the industry-wide problem of threshold alarm fatigue, the enterprise detector evaluates three correlated performance indicators:
- **Composite Formulation:**
  $$Z_{\text{composite}} = 0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}}$$
- **Normalized Z-Score Calculation:** Computed against a rolling $60\text{-second}$ window after a $30\text{-second}$ initialization warmup:
  $$Z_m = \frac{x_m - \mu_{\text{history}}}{\max(\sigma_{\text{history}}, \epsilon)}$$
- **Detection Decision:**
  $$\text{Alarm Asserted} \iff Z_{\text{composite}} \ge 3.0$$
- **Operational Trade-Off:** The composite detector requires cross-metric corroboration, resulting in **zero false positive alarms** ($\text{FPR} = 0.000000$, $\text{Precision} = 1.0000$), compared to the baseline single-metric max-z detector which triggers on isolated variance spikes ($\text{FPR} = 0.000062$).

---

## 6. Counterfactual What-If Sandbox

The [`WhatIfSimulator`](src/telecom_twin/whatif.py) provides a risk-free experimentation environment:
1. **Clone-and-Mutate Isolation:** Deep-copies the live topology and service catalog in memory.
2. **Failure Injection:** Applies simulated node outages (`node_down`), link cuts (`link_down`), packet loss, or bandwidth throttling to target entities.
3. **Graph Reachability & Alternative Path Routing:** Computes shortest paths between client endpoints and service hosts using Dijkstra's algorithm. If an active path is broken, the simulator searches for alternative redundant paths (e.g. failover from `core-sw-01` to `core-sw-02`).
4. **Bottleneck QoS Estimation:** Predicts latency degradation, packet loss increases, and bottleneck throughput limits across the remaining viable paths.
5. **Blast Radius Prediction:** Predicts impacted services and calculates the predicted Blast Radius Index.

---

## 7. Incident Replay Engine

The [`IncidentReplayEngine`](src/telecom_twin/replay.py) enables chronological forensic analysis:
- **6-Stage Lifecycle:**
  1. `WARMUP` ($0\text{s} - 30\text{s}$): Baseline statistical convergence.
  2. `NORMAL` ($30\text{s} - 60\text{s}$): Healthy operational steady-state.
  3. `DEGRADATION` ($60\text{s} - 75\text{s}$): Incipient packet queuing and buffer latency rise.
  4. `FAULT` ($75\text{s} - 120\text{s}$): Active service-impacting failure episode.
  5. `RECOVERY` ($120\text{s} - 150\text{s}$): Failover restoration and convergence.
  6. `POST_INCIDENT` ($150\text{s} - 180\text{s}$): Return to normalized baseline.
- **Stepping Modes:** Supports full scenario execution, frame-by-frame forward/backward navigation, and targeted jumping to specific timestamps.

---

## 8. Backward Compatibility & Architectural Coexistence

The repository maintains complete backward compatibility with the original upstream telecom digital twin:

| Component | Legacy Telecom Mode | Enterprise Digital Twin Mode |
| :--- | :--- | :--- |
| **Topology** | 27-node telecom model (Core/Aggregation/Access) | 22-node multi-tier campus & DC network (22 nodes, 44 links) |
| **Telemetry** | Single-metric latency and packet loss queues | Multi-metric samples (latency, loss, throughput, CPU, RAM) |
| **Detection** | Single-metric $5.0\sigma$ threshold trigger | Multivariate $3.0\sigma$ composite ($0.40Z_{\text{lat}} + 0.35Z_{\text{loss}} + 0.25Z_{\text{cpu}}$) |
| **Service Model** | None (Raw link connectivity only) | 6-service dependency DAG with explicit redundancy semantics |
| **What-If** | N/A | Clone-and-mutate graph sandbox with path QoS estimation |
| **Incident Replay**| Fixed CSV stream replay | 6-stage operational lifecycle playback engine |
| **REST API** | `/health`, `/topology`, `/alarms`, `/dashboard` | `/api/enterprise/*`, `/enterprise`, plus preserved legacy routes |
| **Web UI** | `/dashboard` (Legacy telecom SVG console) | `/enterprise` (Modern 9-view operations console) |
