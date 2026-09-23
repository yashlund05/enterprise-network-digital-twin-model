"""What-If / Counterfactual Enterprise Digital Twin Simulation Engine.

Provides an isolated sandbox simulator for hypothetical network faults, QoS
degradations, and traffic changes without mutating live twin state, topology,
telemetry, or service catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.impact import (
    DEFAULT_CLIENT_INGRESS_NODES,
    ServiceImpactAnalyzer,
    build_network_graph,
    compute_blast_radius_index,
)
from telecom_twin.models import (
    NetworkLink,
    NetworkNode,
    WhatIfResult,
    WhatIfScenario,
)
from telecom_twin.online import OnlineTwin
from telecom_twin.services import EnterpriseServiceCatalog


@dataclass(frozen=True)
class ScenarioComparison:
    """Detailed before-and-after comparison between baseline and counterfactual state."""

    scenario: WhatIfScenario
    result: WhatIfResult
    baseline_metrics: dict[str, float]
    counterfactual_metrics: dict[str, float]
    deltas: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario.to_dict(),
            "result": self.result.to_dict(),
            "baseline_metrics": dict(self.baseline_metrics),
            "counterfactual_metrics": dict(self.counterfactual_metrics),
            "deltas": dict(self.deltas),
        }


def _parse_link_target(target_id: str | tuple[str, str]) -> tuple[str, str] | None:
    """Parse link identifier string or tuple into (source, target) tuple."""
    if isinstance(target_id, tuple) and len(target_id) == 2:
        return target_id[0].strip(), target_id[1].strip()
    if "<->" in target_id:
        u, v = target_id.split("<->", 1)
        return u.strip(), v.strip()
    if "--" in target_id:
        u, v = target_id.split("--", 1)
        return u.strip(), v.strip()
    return None


class WhatIfSimulator:
    """Isolated, deterministic counterfactual digital twin simulator.

    Simulates hypothetical scenarios:
    1. node failure / node down
    2. link failure / link down
    3. node latency spike
    4. link latency spike
    5. node packet loss spike
    6. link packet loss spike
    7. bandwidth throttling / reduction
    8. traffic / utilization surge
    """

    def __init__(
        self,
        nodes: list[NetworkNode] | None = None,
        links: list[NetworkLink] | None = None,
        catalog: EnterpriseServiceCatalog | None = None,
        mode: str = "enterprise",
    ):
        self.mode = mode
        if nodes is None or links is None:
            default_nodes, default_links = generate_enterprise_topology()
            self._nodes = list(nodes) if nodes is not None else default_nodes
            self._links = list(links) if links is not None else default_links
        else:
            self._nodes = list(nodes)
            self._links = list(links)

        self._catalog = catalog if catalog is not None else EnterpriseServiceCatalog()
        self._baseline_graph = build_network_graph(self._nodes, self._links)
        self._impact_analyzer = ServiceImpactAnalyzer(
            self._nodes, self._links, self._catalog
        )

    @property
    def nodes(self) -> list[NetworkNode]:
        """Return an immutable copy of baseline nodes."""
        return list(self._nodes)

    @property
    def links(self) -> list[NetworkLink]:
        """Return an immutable copy of baseline links."""
        return list(self._links)

    @property
    def catalog(self) -> EnterpriseServiceCatalog:
        """Return the service catalog."""
        return self._catalog

    def _compute_path_metrics(
        self, graph: nx.Graph
    ) -> tuple[float, float, float, set[str]]:
        """Compute average latency, loss, throughput, and reachable hosts from ingress."""
        latencies: list[float] = []
        losses: list[float] = []
        throughputs: list[float] = []
        reachable_hosts: set[str] = set()

        services = self._catalog.get_all_services()
        hosts = {s.host_node_id for s in services}

        for ingress in DEFAULT_CLIENT_INGRESS_NODES:
            if ingress not in graph:
                continue
            for host in hosts:
                if host not in graph:
                    continue
                if nx.has_path(graph, ingress, host):
                    reachable_hosts.add(host)
                    try:
                        path = nx.shortest_path(
                            graph, ingress, host, weight="base_latency_ms"
                        )
                        path_lat = 0.0
                        path_loss_prob = 1.0
                        min_cap = float("inf")
                        for i in range(len(path) - 1):
                            u, v = path[i], path[i + 1]
                            edge_data = graph[u][v]
                            path_lat += edge_data.get("base_latency_ms", 1.0)
                            edge_loss = edge_data.get("packet_loss_percent", 0.01) / 100.0
                            path_loss_prob *= (1.0 - edge_loss)
                            min_cap = min(min_cap, edge_data.get("capacity_mbps", 1000.0))

                        latencies.append(path_lat)
                        losses.append((1.0 - path_loss_prob) * 100.0)
                        if min_cap < float("inf"):
                            throughputs.append(min_cap)
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        avg_thru = sum(throughputs) / len(throughputs) if throughputs else 0.0
        return avg_lat, avg_loss, avg_thru, reachable_hosts

    def simulate(
        self,
        scenario: WhatIfScenario,
        *,
        twin: OnlineTwin | None = None,
    ) -> WhatIfResult:
        """Execute counterfactual simulation in an isolated sandbox.

        GUARANTEE: Neither twin, source topology, nor service catalog are modified.
        """
        comparison = self.compare(scenario, twin=twin)
        return comparison.result

    def compare(
        self,
        scenario: WhatIfScenario,
        *,
        twin: OnlineTwin | None = None,
    ) -> ScenarioComparison:
        """Run simulation and return detailed before/after comparison metrics."""
        # 1. Baseline metrics in isolated copy
        base_graph = self._baseline_graph.copy()
        base_lat, base_loss, base_thru, base_hosts = self._compute_path_metrics(base_graph)

        # 2. Build isolated sandbox counterfactual graph
        sim_graph = self._baseline_graph.copy()

        target_type = scenario.target_type.lower()
        failure_type = scenario.failure_type.lower()
        target_id = scenario.target_id
        val = scenario.parameter_value

        predicted_affected_nodes: list[str] = []
        predicted_affected_links: list[str] = []
        is_node_failure = False
        is_link_failure = False

        # Apply counterfactual perturbation strictly inside sandbox
        if target_type == "node" or failure_type in ("node_failure", "node_down"):
            if failure_type in ("node_failure", "node_down", "failure", "down"):
                if target_id in sim_graph:
                    for neighbor in list(sim_graph.neighbors(target_id)):
                        predicted_affected_links.append(f"{target_id}<->{neighbor}")
                    sim_graph.remove_node(target_id)
                predicted_affected_nodes.append(target_id)
                is_node_failure = True
            elif "latency" in failure_type:
                # Node latency spike: increases latency on incident links
                predicted_affected_nodes.append(target_id)
                if target_id in sim_graph:
                    for neighbor in list(sim_graph.neighbors(target_id)):
                        sim_graph[target_id][neighbor]["base_latency_ms"] = (
                            sim_graph[target_id][neighbor].get("base_latency_ms", 1.0) + val
                        )
                        predicted_affected_links.append(f"{target_id}<->{neighbor}")
            elif "loss" in failure_type or "packet" in failure_type:
                # Node loss spike
                predicted_affected_nodes.append(target_id)
                if target_id in sim_graph:
                    for neighbor in list(sim_graph.neighbors(target_id)):
                        sim_graph[target_id][neighbor]["packet_loss_percent"] = (
                            sim_graph[target_id][neighbor].get("packet_loss_percent", 0.0) + val
                        )
                        predicted_affected_links.append(f"{target_id}<->{neighbor}")
            elif "bandwidth" in failure_type or "throttl" in failure_type:
                predicted_affected_nodes.append(target_id)
                if target_id in sim_graph:
                    for neighbor in list(sim_graph.neighbors(target_id)):
                        cur_cap = sim_graph[target_id][neighbor].get("capacity_mbps", 1000.0)
                        sim_graph[target_id][neighbor]["capacity_mbps"] = max(1.0, cur_cap - val)
                        predicted_affected_links.append(f"{target_id}<->{neighbor}")
            elif "traffic" in failure_type or "surge" in failure_type:
                predicted_affected_nodes.append(target_id)
                if target_id in sim_graph:
                    # Traffic surge causes capacity reduction and congestion latency
                    for neighbor in list(sim_graph.neighbors(target_id)):
                        cur_lat = sim_graph[target_id][neighbor].get("base_latency_ms", 1.0)
                        sim_graph[target_id][neighbor]["base_latency_ms"] = cur_lat + (val * 0.1)
                        predicted_affected_links.append(f"{target_id}<->{neighbor}")

        elif target_type == "link" or failure_type in ("link_failure", "link_down"):
            parsed = _parse_link_target(target_id)
            if parsed:
                u, v = parsed
                link_key = f"{u}<->{v}"
                predicted_affected_links.append(link_key)
                if failure_type in ("link_failure", "link_down", "failure", "down"):
                    if sim_graph.has_edge(u, v):
                        sim_graph.remove_edge(u, v)
                    is_link_failure = True
                elif "latency" in failure_type:
                    if sim_graph.has_edge(u, v):
                        sim_graph[u][v]["base_latency_ms"] = (
                            sim_graph[u][v].get("base_latency_ms", 1.0) + val
                        )
                elif "loss" in failure_type or "packet" in failure_type:
                    if sim_graph.has_edge(u, v):
                        sim_graph[u][v]["packet_loss_percent"] = (
                            sim_graph[u][v].get("packet_loss_percent", 0.0) + val
                        )
                elif "bandwidth" in failure_type or "throttl" in failure_type:
                    if sim_graph.has_edge(u, v):
                        cur_cap = sim_graph[u][v].get("capacity_mbps", 1000.0)
                        sim_graph[u][v]["capacity_mbps"] = max(1.0, cur_cap - val)
                elif "traffic" in failure_type or "surge" in failure_type:
                    if sim_graph.has_edge(u, v):
                        cur_lat = sim_graph[u][v].get("base_latency_ms", 1.0)
                        sim_graph[u][v]["base_latency_ms"] = cur_lat + (val * 0.1)

        # 3. Counterfactual path metrics
        sim_lat, sim_loss, sim_thru, sim_hosts = self._compute_path_metrics(sim_graph)

        lat_delta = round(max(0.0, sim_lat - base_lat), 2)
        loss_delta = round(max(0.0, sim_loss - base_loss), 2)
        thru_delta = round(sim_thru - base_thru, 2)

        # If localized perturbation was rerouted around, preserve direct parameter delta
        if "latency" in failure_type and lat_delta == 0.0:
            lat_delta = round(float(val), 2)
        if ("loss" in failure_type or "packet" in failure_type) and loss_delta == 0.0:
            loss_delta = round(float(val), 2)
        if ("throttle" in failure_type or "bandwidth" in failure_type) and thru_delta == 0.0:
            thru_delta = -round(float(val), 2)

        # 4. Service Impact Analysis using ServiceImpactAnalyzer
        if is_node_failure:
            impact_rep = self._impact_analyzer.analyze(failed_nodes=[target_id])
            affected_services = sorted(
                set(impact_rep.directly_impacted_services)
                | set(impact_rep.transitively_impacted_services)
            )
            blast_radius_percent = impact_rep.blast_radius_percent
        elif is_link_failure and parsed:
            impact_rep = self._impact_analyzer.analyze(failed_links=[parsed])
            affected_services = sorted(
                set(impact_rep.directly_impacted_services)
                | set(impact_rep.transitively_impacted_services)
            )
            blast_radius_percent = impact_rep.blast_radius_percent
        else:
            # QoS degradation: identify services whose primary paths cross affected elements
            affected_services_set: set[str] = set()
            for s in self._catalog.get_all_services():
                paths = self._impact_analyzer.get_service_paths(s.service_id)
                for p in paths:
                    if target_id in p:
                        affected_services_set.add(s.service_id)
            affected_services = sorted(affected_services_set)
            if affected_services:
                _, bri_pct = compute_blast_radius_index(affected_services, self._catalog)
                # Weighted by degradation severity
                scale = min(1.0, (lat_delta / 50.0) + (loss_delta / 10.0) + (thru_delta / 5000.0))
                blast_radius_percent = round(bri_pct * max(0.20, scale), 2)
            else:
                blast_radius_percent = 0.0

        # 5. Deterministic Severity Classification
        if blast_radius_percent >= 50.0 or (is_node_failure and target_id.startswith("host-")):
            severity = "CRITICAL"
        elif blast_radius_percent >= 20.0 or loss_delta >= 10.0:
            severity = "HIGH"
        elif blast_radius_percent > 0.0 or lat_delta >= 10.0 or loss_delta >= 1.0 or thru_delta >= 1000.0:
            severity = "MODERATE"
        else:
            severity = "LOW"

        result = WhatIfResult(
            predicted_affected_nodes=tuple(sorted(predicted_affected_nodes)),
            predicted_affected_links=tuple(sorted(predicted_affected_links)),
            predicted_affected_services=tuple(affected_services),
            latency_delta_ms=lat_delta,
            loss_delta_percent=loss_delta,
            throughput_delta_mbps=thru_delta,
            blast_radius_percent=blast_radius_percent,
            severity=severity,
        )

        comparison = ScenarioComparison(
            scenario=scenario,
            result=result,
            baseline_metrics={
                "latency_ms": round(base_lat, 2),
                "loss_percent": round(base_loss, 2),
                "throughput_mbps": round(base_thru, 2),
                "reachable_hosts_count": float(len(base_hosts)),
            },
            counterfactual_metrics={
                "latency_ms": round(sim_lat, 2),
                "loss_percent": round(sim_loss, 2),
                "throughput_mbps": round(sim_thru, 2),
                "reachable_hosts_count": float(len(sim_hosts)),
            },
            deltas={
                "latency_delta_ms": lat_delta,
                "loss_delta_percent": loss_delta,
                "throughput_delta_mbps": thru_delta,
                "lost_hosts_count": float(len(base_hosts - sim_hosts)),
            },
        )

        return comparison


def simulate_what_if(
    scenario: WhatIfScenario,
    nodes: list[NetworkNode] | None = None,
    links: list[NetworkLink] | None = None,
    catalog: EnterpriseServiceCatalog | None = None,
    *,
    twin: OnlineTwin | None = None,
) -> WhatIfResult:
    """Functional convenience wrapper for WhatIfSimulator.simulate."""
    simulator = WhatIfSimulator(nodes=nodes, links=links, catalog=catalog)
    return simulator.simulate(scenario, twin=twin)
