# Current System Audit: Telecom Network Digital Twin

**Audit Date:** 2026-09-23  
**Target Repository:** `telecom-network-digital-twin` (v1.0.0)  
**Upstream Author:** Feng Dekai (FengDK666)  
**Audit Purpose:** Comprehensive architectural and operational baseline audit before executing the transformation into *Digital Twin-Based Intelligent Enterprise Network Monitoring*.

---

## 1. Directory Structure

```text
D:\telecom-network-digital-twin-main
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions workflow (Python 3.10, 3.12, ruff, pytest)
├── docs/
│   ├── architecture.md            # System architecture & API overview
│   ├── cv_summary.md              # Upstream author CV summary bullets
│   ├── experiment.md              # Management-protocol experiment documentation
│   ├── multi_fault.md             # Dual-fault correlation & downstream impact documentation
│   ├── online_twin.md             # Streaming replay & online rolling anomaly detection
│   └── root_cause.md              # Topology-aware & temporal root-cause localization
├── results/
│   ├── figures/
│   │   ├── live_twin_demo.gif     # Pre-rendered 20-frame GIF of live topology replay
│   │   ├── multi_fault_analysis.png # Dual-fault localization accuracy chart
│   │   ├── mvp_summary.png        # Topology diagram + protocol cost bar charts
│   │   ├── online_detection.png   # Latency curve & anomaly detection timestamps
│   │   └── root_cause_robustness.png # Top-1 accuracy across 3 roles & noise levels
│   ├── alarms.csv                 # 115 generated threshold alarms
│   ├── multi_fault_metrics.csv    # Dual-fault aggregate metrics (Jaccard, recall, exact match)
│   ├── multi_fault_summary.csv    # Grouped summary across noise conditions
│   ├── multi_fault_trials.csv     # 2,160 individual dual-fault trials
│   ├── online_anomalies.csv       # Online anomaly detections log
│   ├── online_detection_metrics.csv # Detection delay (1s) & false-event metrics
│   ├── protocol_comparison.csv    # Fixed polling vs adaptive delta comparison
│   ├── root_cause_evaluation.csv  # 3-scenario baseline RCA evaluation
│   ├── root_cause_robustness.csv  # Grouped summary of 4,860 single-fault trials
│   ├── root_cause_robustness_metrics.csv # Macro-averaged Top-1 and Top-3 metrics
│   ├── root_cause_trials.csv      # 4,860 individual trials
│   └── telemetry.csv              # 8,127 rows of 301s 1Hz synthetic node telemetry
├── scripts/
│   ├── api_smoke.sh               # Bash smoke test for FastAPI & SSE endpoints
│   └── verify.sh                  # Comprehensive verification pipeline script
├── src/
│   └── telecom_twin/
│       ├── __init__.py            # Package initialization (exports version '1.0.0')
│       ├── api.py                 # FastAPI backend with REST endpoints & SSE stream
│       ├── cli.py                 # Argparse CLI entrypoints (experiment, serve, benchmark, etc.)
│       ├── dashboard.py           # Dependency-free HTML/SVG/SSE browser dashboard
│       ├── demo.py                # Headless Matplotlib + Pillow GIF generator
│       ├── experiment.py          # Orchestrates baseline experiment & exports CSVs/PNG
│       ├── models.py              # Frozen dataclasses (NetworkNode, NetworkLink, TelemetrySample, Alarm)
│       ├── multifault.py          # Temporal clustering & dual-fault root cause localization
│       ├── online.py              # Thread-safe OnlineTwin replay & RollingAnomalyDetector
│       ├── protocols.py           # Fixed polling vs adaptive delta protocol simulation
│       ├── robustness.py          # Monte Carlo robustness benchmark (4,860 trials)
│       ├── root_cause.py          # Directed hierarchy graph RCA heuristic
│       ├── simulation.py          # Synthetic telemetry, fault injection, & threshold alarms
│       └── topology.py            # Deterministic 27-node 3-tier radial topology generator
├── tests/
│   ├── test_api.py                # FastAPI TestClient endpoint & dashboard tests (3 tests)
│   ├── test_demo.py               # GIF generation validity test (1 test)
│   ├── test_multifault.py         # Multi-fault correlation & benchmark test (4 tests)
│   ├── test_online.py             # Online replay, rolling detector, and artifact export (3 tests)
│   ├── test_protocols.py          # Polling vs adaptive protocol simulation (1 test)
│   ├── test_robustness.py         # Robustness trials, hierarchy distance, & metrics (4 tests)
│   ├── test_root_cause.py         # 3-scenario RCA, same-tier ring logic (4 tests)
│   ├── test_simulation.py         # Telemetry reproducibility & localized alarms (1 test)
│   └── test_topology.py           # 27-node connectivity & hierarchy verification (1 test)
├── CHANGELOG.md                   # v1.0.0 release notes
├── LICENSE                        # MIT License (Feng Dekai, 2026)
├── pyproject.toml                 # Packaging, build system, deps, ruff & pytest config
└── README.md                      # Comprehensive upstream documentation & academic summary
```

---

## 2. Backend Architecture

The backend is written entirely in Python (>=3.10) with standard library types (`dataclasses`, `collections`, `threading.Lock`, `argparse`, `math`, `random`, `csv`, `pathlib`) and minimal external dependencies:
- **`fastapi`** (`>=0.110,<1`): High-performance ASGI web framework.
- **`uvicorn`** (`>=0.27,<1`): ASGI web server.
- **`matplotlib`** (`>=3.5`) and **`pillow`** (`>=9`): Data visualization, chart rendering, and animated GIF creation.

### Module Call Graph & Data Flow:
```
[cli.py] ───> [api.py] ───> [dashboard.py] (Embedded HTML/JS)
   │             │
   │             ├───> [online.py] (OnlineTwin replay + RollingAnomalyDetector)
   │             │        │
   │             │        ├───> [topology.py] (generate_topology)
   │             │        └───> [simulation.py] (generate_telemetry)
   │             │
   │             ├───> [multifault.py] (correlate_root_causes, affected_services)
   │             │        ├───> [robustness.py] (rank_with_time, descendant_distances)
   │             │        └───> [root_cause.py] (hierarchy_children, descendants)
   │             │
   │             └───> [protocols.py] (compare_protocols)
   │
   ├───> [experiment.py] (run_experiment -> CSVs + mvp_summary.png)
   ├───> [robustness.py] (run_benchmark -> 4,860 trials + root_cause_robustness.png)
   ├───> [multifault.py] (run_multi_fault_benchmark -> 2,160 trials + multi_fault_analysis.png)
   └───> [demo.py] (export_demo_gif -> live_twin_demo.gif)
```

The modules are tightly coupled around deterministic in-memory state. In `api.py`, snapshots and experiments are generated at module import time, providing instant responses but static state across processes.

---

## 3. Frontend Architecture

- **Implementation:** Defined in `src/telecom_twin/dashboard.py` as a single raw Python string constant `DASHBOARD_HTML` containing HTML, CSS, and Vanilla JavaScript (29 lines, 3.5 KB).
- **Styling:** Dark theme (`#07111f` background, `#0e1d30` card surfaces, `#5eead4` teal accents, `#2563eb` primary buttons).
- **Topology Rendering:** Scalable Vector Graphics (`<svg id="topology" viewBox="0 0 700 560">`). Nodes and links are computed using normalized polar coordinate mapping:
  - `x = 350 + node.x * 270`
  - `y = 280 - node.y * 250`
  - Core: radius 13, purple (`#8b5cf6`)
  - Aggregation: radius 10, blue (`#0ea5e9`)
  - Access: radius 7, teal (`#14b8a6`)
  - Anomaly state: red pulse fill (`#ef4444`) with high-contrast border (`#fecaca`).
- **Telemetry Streaming:** Uses `EventSource('/live/stream?interval_ms=80')` to receive Server-Sent Events (SSE).
- **Control Features:** Single "Reset replay" button that issues a `POST /live/reset` and reconnects the SSE stream. An anomaly feed table lists the 20 most recent events (`t`, `Node`, `Metric`, `Score`).
- **Limitations:**
  - Hardcoded telecom node counts (`27`).
  - No interactive node inspection modal or detail sidebar.
  - No scenario injection controls from the UI (everything follows the pre-baked seed-28 timeline).
  - No what-if simulation, incident replay scrubber, or blast radius visualization views.

---

## 4. API Layer

Exposed via `fastapi` in `src/telecom_twin/api.py`:

| Endpoint | Method | Params / Query | Description |
|---|---|---|---|
| `/health` | GET | None | System status, data mode (`synthetic`), node count (`27`) |
| `/topology` | GET | None | Full list of nodes (id, role, region, x, y, capacity) and links (source, target, capacity, base latency) |
| `/telemetry/latest` | GET | `node_id: Optional[str]` | Latest 1-second telemetry sample(s) (cpu, latency, loss, throughput) |
| `/alarms` | GET | `limit: int = 100` (1..1000) | Sliding window of generated threshold alarms |
| `/experiments/protocols`| GET | None | Comparison summary between fixed polling and adaptive delta |
| `/experiments/root-cause`| GET | None | Results of the 3 canonical single-fault scenarios |
| `/experiments/multi-fault`| GET | None | Results of the 12 dual-fault scenarios |
| `/dashboard` | GET | None | Serves `dashboard.py:DASHBOARD_HTML` |
| `/live/state` | GET | None | Current snapshot of `OnlineTwin` (timestamp, nodes with status & telemetry, event counts) |
| `/live/reset` | POST | None | Resets simulation time to -1 and flushes anomaly history |
| `/live/step` | POST | `steps: int = 1` (1..301) | Advances the twin by N seconds and updates per-node state |
| `/live/events` | GET | `limit: int = 100` | Detector events emitted so far |
| `/live/stream` | GET | `interval_ms: int = 250` | Server-Sent Events (SSE) streaming live snapshots until complete |

---

## 5. Digital Twin Model & State Synchronization

- **Twin Abstraction:** Implemented in `src/telecom_twin/online.py` as class `OnlineTwin`.
- **State Representation:**
  - `nodes`: List of 27 `NetworkNode` objects.
  - `links`: List of 27 `NetworkLink` objects.
  - `latest`: Dictionary mapping `node_id -> TelemetrySample`.
  - `events`: Cumulative list of detected `AnomalyEvent` instances.
  - `current_anomalies`: List of `AnomalyEvent` instances triggered in the current frame.
- **Synchronization Model:**
  - Step-based discrete time simulation (`timestamp_s`: -1 to 300).
  - Protected by a Python threading `Lock` (`_lock`) for thread safety during concurrent HTTP requests and SSE generators.
  - `_frames`: Pre-indexed dictionary of `timestamp_s -> list[TelemetrySample]`.
- **Gaps for Enterprise Requirements:**
  - Lacks explicit twin sync quality indicators (e.g. telemetry staleness per node, clock skew, synchronization delay metric, twin-to-physical consistency verification).
  - Does not model link state dynamics (link congestion, link degradation, link failure) — only node telemetry is tracked.
  - Lacks application service state (ERP, API, Auth, Database, DNS) and host infrastructure mapping.

---

## 6. Topology Model

- **Implementation:** `src/telecom_twin/topology.py` (`generate_topology()`).
- **Structure:** Hierarchical 3-tier telecom topology arranged in polar coordinates:
  - **Core Tier:** 3 core nodes (`core-01`, `core-02`, `core-03`), 100 Gbps, connected in a redundant ring (3 links).
  - **Aggregation Tier:** 6 aggregation nodes (`aggregation-01` .. `aggregation-06`), 25 Gbps. Each pair is dual-homed to one core node (`aggregation_index // 2 + 1`).
  - **Access Tier:** 18 access nodes (`access-01` .. `access-18`), 1 Gbps. 3 access nodes connect to each aggregation node.
  - Total: 27 nodes and 27 undirected links.
- **Connectivity:** Validated by `topology_is_connected()` using breadth-first search.
- **Characteristics:** Strictly tree-like below the core ring. There are no cross-aggregation links, no enterprise server zones, no perimeter firewall/gateway, and no application hosts.

---

## 7. Telemetry Model

- **Implementation:** `src/telecom_twin/simulation.py` (`generate_telemetry()`).
- **Duration:** 301 seconds (t = 0 to 300 inclusive) at 1 Hz resolution.
- **Metrics Tracked:**
  - `cpu_percent`: Baseline 34.0% + sinusoidal phase oscillation + Gaussian noise (`σ = 1.1`).
  - `latency_ms`: Tier-specific baseline (`core=4.0`, `aggregation=9.0`, `access=17.0`) + sinusoidal drift + Gaussian noise (`σ = 0.45`).
  - `packet_loss_percent`: Baseline `0.08%` + Gaussian noise (`σ = 0.025`).
  - `throughput_mbps`: Tier-specific baseline (`core=42000`, `aggregation=7800`, `access=320`) modulated by phase.
- **Data Volume:** 27 nodes × 301 seconds = 8,127 `TelemetrySample` objects.
- **Protocol Simulation (`protocols.py`):**
  - **Fixed Polling:** Full sample every 10 seconds (160 bytes/sample).
  - **Adaptive Delta:** Threshold-triggered report (80 bytes/delta) when `|Δcpu| >= 8%`, `|Δlatency| >= 10ms`, or `|Δloss| >= 0.5%`, with a 30-second heartbeat fallback.

---

## 8. Anomaly Detection

- **Implementation:** `src/telecom_twin/online.py` (`RollingAnomalyDetector`).
- **Algorithm:** Per-node rolling one-sided z-score:
  $$\mu = \frac{1}{W} \sum x_i, \quad \sigma = \sqrt{\frac{1}{W} \sum (x_i - \mu)^2}$$
  $$z = \max\left(0, \frac{x - \mu}{\max(\sigma, 10^{-6})}\right)$$
- **Parameters:**
  - `window_size`: 60 samples.
  - `warmup`: 30 samples.
  - `threshold`: 5.0 standard deviations.
- **Trigger Rule:** Evaluated on `latency_ms`, `packet_loss_percent`, and `cpu_percent` *before* the current sample is appended to history. If $\max(z) \ge 5.0$, an `AnomalyEvent` is published with the dominant metric.
- **Strengths:** Purely statistical, no heavy ML runtime, fast execution, zero external ML dependencies.
- **Gaps:** Does not compute unified multivariate anomaly scores, does not classify severity (warning vs critical), does not maintain sliding multi-step confidence.

---

## 9. Root-Cause Analysis (RCA)

- **Implementation:**
  - `src/telecom_twin/root_cause.py`: Topology-aware candidate ranking.
  - `src/telecom_twin/robustness.py`: Temporal coherence ranking (`rank_with_time`).
  - `src/telecom_twin/multifault.py`: Multi-fault temporal clustering (`temporal_clusters` + `correlate_root_causes`).
- **Algorithmic Logic:**
  1. **Hierarchy Projection (`hierarchy_children`):** Filters links to directed cross-tier causal edges (`core -> aggregation -> access`). Same-tier core ring links are excluded from causal child sets.
  2. **Descendants (`descendants`):** BFS reaches all downstream nodes from a candidate root.
  3. **Coverage & Precision Scoring:**
     $$\text{recall} = \frac{|\text{observed} \cap \text{predicted}|}{|\text{observed}|}, \quad \text{precision} = \frac{|\text{observed} \cap \text{predicted}|}{|\text{predicted}|}$$
     $$\text{score}_{\text{topo}} = 0.72 \cdot \text{recall} + 0.28 \cdot \text{precision} + 0.08 \cdot \mathbb{I}(\text{candidate} \in \text{observed})$$
  4. **Temporal Coherence:**
     Assumes downstream alarms arrive with delay $t = t_0 + 3.0 \cdot d + \epsilon$. Inferred root origin times: $t_{0,i} = t_i - 3.0 \cdot d_i$.
     $$\text{coherence} = \exp\left(-\frac{\sqrt{\text{Var}(t_0)}}{2.5}\right)$$
     $$\text{score}_{\text{final}} = 0.82 \cdot \text{score}_{\text{topo}} + 0.18 \cdot \text{coherence}$$
- **Strengths:** Fully deterministic, explainable graph reasoning, mathematically sound and validated across 4,860 trials.
- **Gaps:** Only reasons over synthetic telecom hierarchy; does not incorporate service/application dependency topology or bidirectional dependency graphs.

---

## 10. Fault Injection

- **Single Incident Simulation (`simulation.py`):**
  - Target: `access-07`.
  - Window: $t = 123$s to $183$s (60-second duration).
  - Ramp profile: $6$-second linear ramp ($\min(1.0, \Delta t / 6.0)$).
  - Injected degradation: $+42\%$ CPU, $+105$ ms latency, $+4.8\%$ packet loss, $-42\%$ throughput.
- **Alarm Generation (`simulation.py`):**
  - Latency warning: $\ge 80.0$ ms (severity: `major`).
  - Loss warning: $\ge 2.0\%$ (severity: `critical`).
- **Multi-Fault Generator (`multifault.py`):**
  - Injects two separate cascades with configurable start times (e.g., 100s and 130s), missing alarm rates (0%, 20%, 40%), and false alarm counts (0, 2, 4).
- **Gaps:** Injections are statically defined in code; no interactive what-if API or user-driven fault injector exists.

---

## 11. Service Impact Logic

- **Implementation:** `src/telecom_twin/multifault.py` (`affected_services()`).
- **Logic:**
  ```python
  def affected_services(roots, nodes, links):
      children = hierarchy_children(links)
      access_ids = {node.node_id for node in nodes if node.role == "access"}
      impacted = set()
      for root in roots:
          impacted.update(descendants(root, children) & access_ids)
      return impacted
  ```
- **Limitation:** In the current implementation, "services" are simply leaf `access-*` network nodes. There is no concept of real enterprise software services (ERP, CRM, Authentication, Database, Internal API, DNS), service endpoints, service dependency chains, or business criticality.

---

## 12. Database & Storage

- **Runtime State:** Exclusively in-process memory (`dict`, `list`, `deque`).
- **Persistence / Artifact Storage:** Flat CSV files and Matplotlib PNG/GIF files written to the `results/` folder:
  - `telemetry.csv`, `alarms.csv`, `protocol_comparison.csv`, `root_cause_evaluation.csv`
  - `root_cause_trials.csv`, `root_cause_robustness.csv`, `root_cause_robustness_metrics.csv`
  - `multi_fault_trials.csv`, `multi_fault_summary.csv`, `multi_fault_metrics.csv`
  - `online_detection_metrics.csv`, `online_anomalies.csv`
- **Assessment:** Lightweight, version-controllable, perfectly reproducible, but lacks structured queries or dynamic scenario storage.

---

## 13. Tests & Verification

- **Framework:** `pytest` 8.4.2 + `pytest-cov`.
- **Test Suite Status:** 9 test files, 22 test cases.
- **Execution Result:** **22 passed in ~10 seconds** (100% pass rate).
- **Linter:** `ruff` configured with line length 100, target Python 3.10.

---

## 14. Configuration, Packaging & Deployment

- **Build Tool:** `setuptools>=68` configured in `pyproject.toml`.
- **CLI Entrypoint:** `telecom-twin = telecom_twin.cli:main`.
- **CI / CD:** `.github/workflows/ci.yml` tests on Ubuntu with Python 3.10 and 3.12, running `ruff check .`, `pytest -q`, and executing the CLI commands.
- **Docker:** No Dockerfile or docker-compose file currently exists in the repository.

---

## 15. CLI Capabilities

Defined in `src/telecom_twin/cli.py`:
- `telecom-twin experiment [--output-dir DIR]`
- `telecom-twin benchmark [--output-dir DIR] [--trials-per-root N]`
- `telecom-twin online-evaluation [--output-dir DIR]`
- `telecom-twin multi-fault-benchmark [--output-dir DIR] [--trials-per-scenario N]`
- `telecom-twin demo-gif [--output PATH]`
- `telecom-twin serve [--host HOST] [--port PORT]`

---

## 16. Existing Experiments & Benchmarks

1. **Protocol Comparison Experiment (`experiment.py`):**
   - 301 seconds, 27 nodes, 8,127 samples.
   - Fixed polling (10s) vs Adaptive delta (30s heartbeat).
   - Metrics: Message count (-63%), transferred kB (-81.5%), first detection delay (0s vs 4s), staleness (4.49s vs 13.38s).
2. **Single-Fault Robustness Benchmark (`robustness.py`):**
   - 4,860 trials across 27 nodes, 3 missing rates (0%, 20%, 40%), 3 false alarm counts (0, 2, 4), 20 trials.
   - Evaluates Top-1 and Top-3 accuracy of topology-only vs topology+temporal scoring.
3. **Online Anomaly Detection Evaluation (`online.py`):**
   - Evaluates streaming 1-second frames with `RollingAnomalyDetector`.
   - Metrics: 1s detection delay, 6 incident events, 0 false alarms.
4. **Multi-Fault Correlation Benchmark (`multifault.py`):**
   - 2,160 trials over 12 dual-fault scenarios (6 independent, 6 nested).
   - Compares Global Top-2 against Temporal Clustering Correlation.
   - Metrics: Exact match (63.19% vs 23.84%), root recall (79.84% vs 59.72%), service recall (94.32%), service Jaccard (84.19%).

---

## 17. Safe Extension Points & Transformation Surface

| Component | Upstream Status | Safe Extension Strategy |
|---|---|---|
| Domain Models (`models.py`) | Simple 4 dataclasses | Extend with `EnterpriseService`, `ServiceDependency`, `TwinSyncState`, `WhatIfScenario`, `IncidentReplay` |
| Topology (`topology.py`) | 3-tier telecom (core/agg/access) | Refactor into believable Enterprise Topology (Perimeter/Edge, Core, Distribution, Access, Application Server Pods) |
| Telemetry (`simulation.py`) | Synthetic telecom load | Add enterprise application telemetry (ERP latency, DB connections, API error rates, DNS query time) |
| Digital Twin (`online.py`) | 27-node in-memory replay | Enhance with twin health, synchronization latency, staleness tracking, consistency metrics |
| RCA (`root_cause.py`, `robustness.py`) | Directed hierarchy graph | Augment with multi-layer enterprise dependency graph (Physical Link -> Host Node -> Virtual Infrastructure -> Enterprise Service) |
| Service Impact (`multifault.py`) | Map roots to leaf access nodes | Implement true Service Blast Radius engine: affected links, paths, dependent applications, criticality levels |
| What-If Engine | Non-existent | **NEW module**: sandbox twin simulation predicting latency, loss, and service impact without touching live twin |
| Incident Replay | Basic frame stepping | **NEW module**: event timeline tracing Normal -> Degradation -> Anomaly -> RCA -> Impact -> Remediation |
| API (`api.py`) | 13 endpoints | Add enterprise routes (`/enterprise/*`, `/whatif/*`, `/replay/*`, `/services/*`) preserving existing routes |
| Dashboard (`dashboard.py`) | 1-page SVG telecom view | Upgrade into a comprehensive multi-view Enterprise Network Operations Command Center |
| Packaging & CI | `pyproject.toml` | Add new CLI commands, keep backward-compatible script aliases, keep original MIT license & attribution |

