# Upstream Attribution & Provenance

## Original Project & Licensing

This project, **Digital Twin-Based Intelligent Enterprise Network Monitoring**, is adapted and substantially extended from the open-source telecom digital twin project:

- **Original Author:** Feng Dekai
- **Original Repository / Work:** Telecom Network Digital Twin (`telecom-network-digital-twin`)
- **License:** MIT License (Copyright © 2026 Feng Dekai)

The original MIT License is preserved in its entirety in the root [`LICENSE`](LICENSE) file. In accordance with the MIT License, this attribution document documents the origins of the codebase and delineates what was inherited versus what was developed for this project.

---

## Architecture & Codebase Provenance

We gratefully acknowledge the foundational architecture provided by the upstream implementation. Below is an itemized breakdown of inherited components versus new and extended capabilities:

### Inherited from Upstream
1. **Core Simulation Foundation:** The discrete-event queueing model, basic packet delivery physics, and initial 27-node telecom network topology generator (`telecom_twin/simulation.py`, `telecom_twin/models.py`).
2. **Legacy Telemetry Stream:** Single-metric rolling-window telemetry buffer and baseline maximum z-score threshold detection (`telecom_twin/online.py`).
3. **Legacy Heuristics:** Initial rule-based symptom matching for single telecom nodes (`telecom_twin/root_cause.py`).
4. **Base REST API & UI Scaffold:** Initial FastAPI application layout, legacy endpoint routing, and static telecom topology dashboard (`telecom_twin/api.py`, `telecom_twin/dashboard.py`).
5. **Project Packaging:** Base `pyproject.toml` packaging layout and initial command-line interface entrypoints (`telecom_twin/cli.py`).

### Implemented & Extended for this Project
1. **Enterprise Domain Models (`models.py`):**
   - Hierarchical architectural tiers (`edge`, `core`, `distribution`, `access`, `host`).
   - Enterprise service dependency graph models with redundancy semantics (`active_active`, `active_standby`, `independent`).
   - Extended multi-metric enterprise telemetry samples incorporating latency, packet loss, throughput, CPU, and memory.
2. **Canonical 22-Node / 44-Link Enterprise Topology (`enterprise_topology.py`):**
   - Realistic multi-tier enterprise campus and datacenter network topology with redundant distribution and core interconnects.
3. **Enterprise Telemetry Generation Engine (`enterprise_telemetry.py`):**
   - Synthetic statistical generation covering the full incident lifecycle ($\text{Warmup} \to \text{Normal} \to \text{Degradation} \to \text{Fault} \to \text{Recovery}$) with deterministic Gaussian and diurnal traffic variations.
4. **Digital Twin Synchronization Engine (`online.py`):**
   - Thread-safe real-time state synchronization, per-node staleness calculation, and topology consistency scoring (`OnlineTwin`).
5. **Multivariate Composite Anomaly Detection (`online.py`):**
   - Composite z-score formulation ($0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}} \ge 3.0$) that eliminates false positive alarms while maintaining robust incident detection.
6. **Enterprise Service Catalog & Blast Radius Analysis (`services.py`):**
   - Redundancy-aware service impact analysis, DAG topological sort, transitive dependency tracking, and quantitative Blast Radius Index ($\text{BRI}$).
7. **Topology-Aware Root Cause Analysis (`root_cause.py`):**
   - Causal graph traversal incorporating upstream tier penalties, symptom correlation, and concurrent multi-fault diagnosis.
8. **Counterfactual What-If Simulation Sandbox (`whatif.py`):**
   - Isolated clone-and-mutate sandbox modeling path rerouting, bottleneck capacity reduction, and SLA degradation.
9. **Incident Replay Engine (`replay.py`):**
   - Step-by-step 6-stage operational incident playback for post-mortem forensics and operator training.
10. **Enterprise REST API & CLI Integration (`api.py`, `cli.py`):**
    - Production REST endpoints (`/api/enterprise/*`) and CLI subcommands (`whatif-sim`, `enterprise-evaluation`).
11. **Unified Enterprise Operations Web Dashboard (`enterprise_dashboard.py`):**
    - Single-page 9-view operations console at `/enterprise` providing interactive topology visualization, real-time telemetry charts, RCA exploration, What-If simulation, replay timeline, and evaluation reports.
12. **Reproducible Evaluation Framework (`evaluation.py`, `results/enterprise/`):**
    - Deterministic 15-scenario benchmark with modeled ground truth, automated artifact generation, and formal academic reporting.

---

## MIT License Acknowledgement

The upstream codebase is licensed under the MIT License:
```text
MIT License
Copyright (c) 2026 Feng Dekai
```
All original copyright notices and permission terms remain in full force.
