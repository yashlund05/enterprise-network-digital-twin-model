# Enterprise Digital Twin Experimental Evaluation

This document details the reproducible evaluation framework, scenario suite, ground-truth methodology, mathematical metric definitions, and baseline comparisons for the **Digital Twin-Based Intelligent Enterprise Network Monitoring** platform.

---

## 1. Experimental Overview & Architecture

The evaluation framework objectively benchmarks the digital twin platform across five core modules:
1. **Multivariate Anomaly Detection:** Evaluating the rolling composite z-score detector against a single-metric max-z baseline.
2. **Root Cause Analysis (RCA):** Assessing topological and dependency-aware candidate ranking under single and multi-fault scenarios.
3. **Service Impact Prediction:** Validating client path reachability and transitive service degradation forecasts.
4. **Counterfactual What-If Simulation:** Measuring prediction fidelity of isolated hypothetical fault sandboxing against simulated telemetry.
5. **Digital Twin Synchronization:** Evaluating virtual twin state tracking across nominal, delayed, and partially missing telemetry streams.

All benchmarks are **deterministic**, **locally executable**, **reproducible via fixed seeds**, and evaluated against **independently constructed oracle ground truth**.

---

## 2. Evaluation Scenario Suite

The benchmark exercises **15 deterministic scenarios** across a 22-node, 44-link enterprise network hosting 6 core business services (`srv-dns`, `srv-auth`, `srv-db`, `srv-api`, `srv-erp`, `srv-monitoring`).

### Single-Node Scenarios (13 Scenarios)

| Scenario ID | Target Node | Tier | Injected Fault Type | Severity / Value | Oracle Impacted Services |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `sc-01-edge-gw-01-down` | `edge-gw-01` | Edge | `node_down` | 1.0 (Down) | All 6 services (WAN ingress path broken) |
| `sc-02-core-sw-01-loss` | `core-sw-01` | Core | `packet_loss` | 8.5% loss | All 6 services (inter-tier backbone degraded) |
| `sc-03-core-sw-02-lat` | `core-sw-02` | Core | `latency_spike` | +85.0 ms | All 6 services (transit queuing delay) |
| `sc-04-dist-campus-01-cpu`| `dist-sw-campus-01` | Distribution | `cpu_saturation` | 98.0% CPU | All 6 services (campus distribution overload) |
| `sc-05-dist-campus-02-throttle`| `dist-sw-campus-02` | Distribution | `bandwidth_throttling` | 500 Mbps cap | All 6 services (QoS policing bottleneck) |
| `sc-06-dist-dc-01-down` | `dist-sw-dc-01` | Distribution | `node_down` | 1.0 (Down) | All 6 services (DC spine redundancy lost) |
| `sc-07-dist-dc-02-loss` | `dist-sw-dc-02` | Distribution | `packet_loss` | 8.5% loss | All 6 services (DC spine optical error) |
| `sc-08-acc-hq-01-mem` | `acc-sw-hq-01` | Access | `memory_saturation` | 99.0% RAM | All 6 services (HQ ingress access bottleneck) |
| `sc-09-acc-dc-01-lat` | `acc-sw-dc-01` | Access | `latency_spike` | +85.0 ms | `srv-api`, `srv-erp`, `srv-monitoring` |
| `sc-10-host-erp-down` | `host-erp` | Host | `node_down` | 1.0 (Down) | `srv-erp` |
| `sc-11-host-api-cpu` | `host-api` | Host | `cpu_saturation` | 98.0% CPU | `srv-api`, `srv-erp` (ERP depends on API) |
| `sc-12-host-db-mem` | `host-db` | Host | `memory_saturation` | 99.0% RAM | `srv-db`, `srv-api`, `srv-erp` (API/ERP depend on DB) |
| `sc-13-host-dns-down` | `host-dns` | Host | `node_down` | 1.0 (Down) | All 6 services (All services depend on DNS) |

### Multi-Fault Scenarios (2 Scenarios)

| Scenario ID | Injected Targets | Fault Combination | Causal Category |
| :--- | :--- | :--- | :--- |
| `sc-14-multi-campus-dist-acc` | `dist-sw-campus-01`, `acc-sw-hq-01` | CPU Saturation + Packet Loss | Related Upstream + Downstream Cascading Fault |
| `sc-15-multi-campus-dc` | `host-dns`, `acc-sw-hq-02` | Node Crash + Latency Spike | Concurrent Independent Datacenter + Campus Fault |

---

## 3. Ground-Truth Methodology

Ground truth is generated independently from the prediction engines and strictly adheres to the following principles:

1. **Independent Oracle Representation:** Ground truth is never computed as *"whatever the algorithm returns"*. For every scenario, the injected entity and physical graph state are defined a priori.
2. **Reachability Oracle for Service Impact:**
   - The oracle constructs an operational network graph by removing the injected failed node(s) or links from the 22-node topology.
   - All standard client ingress endpoints (`edge-gw-01`, `edge-gw-02`, `acc-sw-hq-01`, `acc-sw-hq-02`, `acc-sw-hq-03`, `acc-sw-hq-04`) are evaluated for reachability to each service's hosting node.
   - If an ingress path is severed, the service is flagged as directly impacted.
   - Transitive consumer dependencies are propagated using the Directed Acyclic Graph (DAG) defined in `EnterpriseServiceCatalog`.
3. **Temporal Fault Windows for Anomaly Detection:**
   - The fault injection interval $[t_{\text{start}}, t_{\text{end}} + t_{\text{ramp}}]$ defines the exact ground-truth positive window on the affected entity.

---

## 4. Mathematical Metric Definitions

### 4.1 Anomaly Detection
Evaluated at the **Node $\times$ Timestep** level ($t \in [30, 180]$ across 22 nodes):
- **True Positive ($TP$):** Detector flags an anomaly on an affected node during the active fault window.
- **False Positive ($FP$):** Detector flags an anomaly outside the fault window or on an unaffected node.
- **False Negative ($FN$):** An affected node during an active fault window is not flagged.
- **True Negative ($TN$):** Normal node-timesteps correctly unflagged.

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{False Positive Rate (FPR)} = \frac{FP}{FP + TN}$$

$$\text{Detection Delay} = \min(t_{\text{detected}}) - t_{\text{fault\_start}} \quad (\text{for } t_{\text{detected}} \ge t_{\text{fault\_start}})$$

### 4.2 Root Cause Analysis (RCA)
- **Top-1 Accuracy:** Fraction of single-fault scenarios where the known injected root cause is ranked first ($\text{rank} = 1$).
- **Top-3 Accuracy:** Fraction of single-fault scenarios where the known root cause appears within the top 3 candidates ($\text{rank} \le 3$).
- **Mean Reciprocal Rank (MRR):**
  $$\text{MRR} = \frac{1}{N} \sum_{i=1}^{N} \frac{1}{\text{rank}_i}$$
- **Multi-Fault Identification Rate:** Fraction of multi-fault scenarios where the multi-fault flag is asserted and both injected root causes appear in the diagnostic candidate set.

### 4.3 Service Impact & Blast Radius (Model-Consistency Validation)
Comparing predicted impacted service set $S_{\text{pred}}$ against oracle ground truth set $S_{\text{gt}}$:
- **Validation Nature:** Because both `ServiceImpactAnalyzer` and the evaluation oracle share the underlying enterprise topology graph and service catalog DAG, these metrics represent **model-consistency validation** (mathematical verification of graph reachability and redundancy rules) rather than empirical field probes.
- **Jaccard Similarity:**
  $$J(S_{\text{pred}}, S_{\text{gt}}) = \frac{|S_{\text{pred}} \cap S_{\text{gt}}|}{|S_{\text{pred}} \cup S_{\text{gt}}|}$$
- **Blast Radius MAE:**
  $$\text{MAE}_{\text{BRI}} = \frac{1}{N} \sum_{i=1}^{N} |\text{BRI}_{\text{pred}, i} - \text{BRI}_{\text{gt}, i}|$$

### 4.4 What-If Counterfactual Validation
Comparing sandbox predicted metric deltas ($\Delta_{\text{pred}}$) against observed simulated deltas ($\Delta_{\text{obs}}$) on the target entity:
- **Units:** Latency in milliseconds ($\text{ms}$), Packet Loss in percent ($\%$), Throughput in megabits per second ($\text{Mbps}$).
- **Modeling Scope Difference:** What-If simulation predicts end-to-end client service path bottleneck QoS and path rerouting across the graph, whereas the simulation fault generator injects localized per-device telemetry on the failed physical node itself (e.g., setting device latency to 999.0 ms and throughput to 0.0 Mbps during a `node_down` condition).
$$\text{MAE}_{\text{latency}} = \frac{1}{N} \sum |\Delta_{\text{lat, pred}} - \Delta_{\text{lat, obs}}| \quad (\text{ms})$$
$$\text{MAE}_{\text{loss}} = \frac{1}{N} \sum |\Delta_{\text{loss, pred}} - \Delta_{\text{loss, obs}}| \quad (\%)$$
$$\text{MAE}_{\text{throughput}} = \frac{1}{N} \sum |\Delta_{\text{thru, pred}} - \Delta_{\text{thru, obs}}| \quad (\text{Mbps})$$

### 4.5 Digital Twin Synchronization
- **Deterministic Execution:** Twin synchronization is evaluated deterministically across nominal ingestion, a 5.0-second telemetry lag, and 20% dropped telemetry (5 nodes withholding updates).
- **Telemetry Staleness:** Difference between twin current clock and latest node telemetry timestamp:
  $$\text{Staleness}_i = t_{\text{sync}} - t_{\text{last\_update}, i}$$
- **Topology Consistency:** Composite score evaluating node coverage, link coherence, and telemetry endpoint validity ($0.0 \le C \le 1.0$).

---

## 5. Anomaly Detection & Baseline Comparison

Evaluation is conducted at both the **Point-Wise ($Node \times Timestep$)** level across all monitored nodes and the **Incident Level** across all evaluated failure scenarios.

### Point-Wise vs Incident-Level Comparative Summary

| Metric Level | Metric | Enterprise Composite (3.0z) | Baseline Legacy Max-Z (5.0z) | Architectural Trade-Off |
| :--- | :--- | :--- | :--- | :--- |
| **Point-Wise** | **Precision** | **1.0000** | 0.9725 | Enterprise eliminates all false positives (0 FP vs 3 FP) |
| **Point-Wise** | **Recall** | 0.0784 | **0.0945** | Baseline flags isolated single-metric spikes |
| **Point-Wise** | **F1 Score** | 0.1455 | **0.1722** | Baseline achieves higher point-wise F1 (+0.0267) |
| **Point-Wise** | **False Positive Rate** | **0.000000** | 0.000062 | Enterprise achieves zero false positive rate |
| **Incident** | **Detection Rate** | **86.7% (13/15)** | **86.7% (13/15)** | Identical incident-level detection rate |
| **Incident** | **Mean Detection Delay** | **16.87 s** | **16.87 s** | Identical mean detection delay (1.0s detected, 120s timeout) |

#### Trade-Off Analysis
1. **Point-Wise ($Node \times Timestep$):** The baseline single-metric detector achieves a higher point-wise recall (0.0945 vs 0.0784) and higher point-wise F1 score (0.1722 vs 0.1455) because any single extreme spike exceeding $5.0\sigma$ triggers an alert. However, this produces false alarms during nominal operation ($FPR = 0.000062$, Precision = $0.9725$). In contrast, the enterprise composite detector enforces cross-metric corroboration ($0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}} \ge 3.0$), achieving perfect precision ($1.0000$) and zero false positives ($FPR = 0.000000$), at the expected cost of lower point-wise recall during transient single-metric deviations.
2. **Incident-Level Detection:** At the operational incident level, both detectors identify **13 of 15 scenarios (86.7%)** with an identical mean detection delay of **16.87 seconds**. The enterprise composite formulation thus eliminates operational alarm fatigue without degrading incident detection coverage.

### Per-Scenario Anomaly Detection Breakdown

| Scenario ID | Fault Type | Root Cause | Detected | Detection Time (s) | Detection Delay (s) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sc-01-edge-gw-01-down` | `node_down` | `edge-gw-01` | **Yes** | 61.0 s | 1.0 s | Multi-metric failure detected immediately at t=61.0s |
| `sc-02-core-sw-01-loss` | `packet_loss` | `core-sw-01` | **Yes** | 61.0 s | 1.0 s | Core transit loss detected at t=61.0s |
| `sc-03-core-sw-02-lat` | `latency_spike` | `core-sw-02` | **Yes** | 61.0 s | 1.0 s | Forwarding latency spike detected at t=61.0s |
| `sc-04-dist-campus-01-cpu` | `cpu_saturation` | `dist-sw-campus-01` | **Yes** | 61.0 s | 1.0 s | Control plane saturation detected at t=61.0s |
| `sc-05-dist-campus-02-throttle` | `bandwidth_throttling` | `dist-sw-campus-02` | **Yes** | 61.0 s | 1.0 s | Bandwidth throttling detected at t=61.0s |
| `sc-06-dist-dc-01-down` | `node_down` | `dist-sw-dc-01` | **Yes** | 61.0 s | 1.0 s | Hardware outage detected at t=61.0s |
| `sc-07-dist-dc-02-loss` | `packet_loss` | `dist-sw-dc-02` | **Yes** | 61.0 s | 1.0 s | Packet loss anomaly detected at t=61.0s |
| `sc-08-acc-hq-01-mem` | `memory_saturation` | `acc-sw-hq-01` | **No** | N/A | > 120.0 s (Timeout) | Isolated memory exhaustion; composite z-score does not incorporate memory without correlated CPU/latency |
| `sc-09-acc-dc-01-lat` | `latency_spike` | `acc-sw-dc-01` | **Yes** | 61.0 s | 1.0 s | Forwarding latency spike detected at t=61.0s |
| `sc-10-host-erp-down` | `node_down` | `host-erp` | **Yes** | 61.0 s | 1.0 s | Hardware outage detected at t=61.0s |
| `sc-11-host-api-cpu` | `cpu_saturation` | `host-api` | **Yes** | 61.0 s | 1.0 s | Control plane saturation detected at t=61.0s |
| `sc-12-host-db-mem` | `memory_saturation` | `host-db` | **No** | N/A | > 120.0 s (Timeout) | Isolated memory exhaustion; composite z-score does not incorporate memory without correlated CPU/latency |
| `sc-13-host-dns-down` | `node_down` | `host-dns` | **Yes** | 61.0 s | 1.0 s | Hardware outage detected at t=61.0s |
| `sc-14-multi-campus-dist-acc` | `cpu_saturation` | `dist-sw-campus-01, acc-sw-hq-01` | **Yes** | 61.0 s | 1.0 s | Cascading control plane overload detected at t=61.0s |
| `sc-15-multi-campus-dc` | `node_down` | `host-dns, acc-sw-hq-02` | **Yes** | 61.0 s | 1.0 s | Multi-tier concurrent node failure detected at t=61.0s |

*Root Cause Detection Breakdown:*
- **Forwarding & Compute Faults (13/15 detected):** All scenarios featuring packet loss, latency, interface policing, or CPU saturation are flagged within 1.0 second ($t = 61.0\text{ s}$).
- **Isolated Memory Saturation (2/15 undetected):** Scenarios `sc-08` and `sc-12` represent isolated RAM exhaustion. Because the 3-variable composite z-score ($0.40 Z_{\text{lat}} + 0.35 Z_{\text{loss}} + 0.25 Z_{\text{cpu}}$) deliberately excludes memory (to prevent benign OS buffer allocation from triggering network alarms), isolated memory spikes do not cross the $3.0\sigma$ threshold.

---

## 6. Reproducibility & Execution

The evaluation suite can be executed via CLI, REST API, or the web dashboard.

### CLI Execution
```bash
telecom-twin enterprise-evaluation --output-dir results/enterprise --seed 42
```

### API Execution
```bash
curl -X POST "http://localhost:8000/api/enterprise/evaluation/run?seed=42"
curl -X GET "http://localhost:8000/api/enterprise/evaluation"
```

### Generated Artifacts
Execution generates the following files in `results/enterprise/`:
- `anomaly_metrics.csv`
- `rca_metrics.csv`
- `service_impact_metrics.csv`
- `whatif_metrics.csv`
- `twin_sync_metrics.csv`
- `scenario_results.csv`
- `evaluation_summary.json`
- `evaluation_report.md`
- Figures: `anomaly_detection_summary.png`, `detection_delay_dist.png`, `rca_accuracy_summary.png`, `service_impact_metrics.png`, `whatif_prediction_vs_observed.png`, `twin_sync_staleness.png`

---

## 7. Simulator & Oracle Limitations

- **Synthetic Telemetry Profiles:** Telemetry distributions are generated using statistical Gaussian and sinusoidal workload models. They reflect modeled enterprise behavior rather than physical hardware packet captures.
- **Topology Scale:** Evaluated on a canonical 22-node multi-tier topology representing typical campus and datacenter enterprise networks.
- **Reachability Oracle Assumptions:** Service reachability assumes standard shortest-path routing over operational links. BGP convergence times or asymmetric routing loops are not simulated at the packet level.
