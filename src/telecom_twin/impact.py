"""Enterprise Service Impact and Blast Radius Evaluation Engine.

Provides deterministic path tracing, redundancy-aware reachability analysis,
transitive dependency propagation, and Blast Radius Index (BRI) calculation
for enterprise digital twins.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.models import NetworkLink, NetworkNode, WhatIfResult
from telecom_twin.services import EnterpriseServiceCatalog

# Deterministic criticality weights for modeled Blast Radius Index calculation
DEFAULT_CRITICALITY_WEIGHTS: dict[str, float] = {
    "tier-1": 3.0,
    "tier-2": 2.0,
    "tier-3": 1.0,
}

# Standard user and WAN entry points into the enterprise network
DEFAULT_CLIENT_INGRESS_NODES: tuple[str, ...] = (
    "edge-gw-01",
    "edge-gw-02",
    "acc-sw-hq-01",
    "acc-sw-hq-02",
    "acc-sw-hq-03",
    "acc-sw-hq-04",
)


@dataclass(frozen=True)
class ServiceImpactReport:
    """Structured result of a deterministic enterprise service impact analysis."""

    directly_affected_nodes: tuple[str, ...]
    directly_affected_links: tuple[tuple[str, str], ...]
    affected_paths: tuple[tuple[str, ...], ...]
    directly_impacted_services: tuple[str, ...]
    transitively_impacted_services: tuple[str, ...]
    service_statuses: dict[str, str]
    blast_radius_index: float
    blast_radius_percent: float
    overall_severity: str

    def to_dict(self) -> dict:
        return {
            "directly_affected_nodes": list(self.directly_affected_nodes),
            "directly_affected_links": [list(link) for link in self.directly_affected_links],
            "affected_paths": [list(path) for path in self.affected_paths],
            "directly_impacted_services": list(self.directly_impacted_services),
            "transitively_impacted_services": list(self.transitively_impacted_services),
            "service_statuses": dict(self.service_statuses),
            "blast_radius_index": self.blast_radius_index,
            "blast_radius_percent": self.blast_radius_percent,
            "overall_severity": self.overall_severity,
        }

    def to_what_if_result(self) -> WhatIfResult:
        """Convert into standard WhatIfResult domain model."""
        all_impacted = sorted(
            set(self.directly_impacted_services) | set(self.transitively_impacted_services)
        )
        affected_links_str = tuple(
            f"{src}<->{dst}" for src, dst in self.directly_affected_links
        )
        return WhatIfResult(
            predicted_affected_nodes=self.directly_affected_nodes,
            predicted_affected_links=affected_links_str,
            predicted_affected_services=tuple(all_impacted),
            latency_delta_ms=0.0,
            loss_delta_percent=0.0,
            throughput_delta_mbps=0.0,
            blast_radius_percent=self.blast_radius_percent,
            severity=self.overall_severity,
        )


def build_network_graph(nodes: list[NetworkNode], links: list[NetworkLink]) -> nx.Graph:
    """Build an undirected NetworkX graph from enterprise network nodes and links."""
    graph = nx.Graph()
    for node in nodes:
        graph.add_node(
            node.node_id,
            role=node.role,
            tier=node.tier,
            capacity_mbps=node.capacity_mbps,
            region=node.region,
        )
    for link in links:
        graph.add_edge(
            link.source,
            link.target,
            capacity_mbps=link.capacity_mbps,
            base_latency_ms=link.base_latency_ms,
            vlan_id=link.vlan_id,
            interface_health=link.interface_health,
        )
    return graph


def compute_blast_radius_index(
    impacted_service_ids: set[str] | list[str],
    catalog: EnterpriseServiceCatalog,
    criticality_weights: dict[str, float] | None = None,
) -> tuple[float, float]:
    """Calculate Blast Radius Index (BRI) as normalized ratio [0.0, 1.0] and percentage.

    Formula:
        BRI = sum(weight of impacted services) / sum(weight of all services)
    """
    weights = criticality_weights or DEFAULT_CRITICALITY_WEIGHTS
    all_services = catalog.get_all_services()
    if not all_services:
        return 0.0, 0.0

    total_weight = sum(weights.get(s.criticality, 1.0) for s in all_services)
    if total_weight <= 0.0:
        return 0.0, 0.0

    impacted_set = set(impacted_service_ids)
    impacted_weight = sum(
        weights.get(s.criticality, 1.0)
        for s in all_services
        if s.service_id in impacted_set
    )
    bri = round(min(1.0, max(0.0, impacted_weight / total_weight)), 4)
    bri_percent = round(bri * 100.0, 2)
    return bri, bri_percent


class ServiceImpactAnalyzer:
    """Deterministic redundancy-aware service impact and blast radius analyzer."""

    def __init__(
        self,
        nodes: list[NetworkNode] | None = None,
        links: list[NetworkLink] | None = None,
        catalog: EnterpriseServiceCatalog | None = None,
        *,
        ingress_nodes: tuple[str, ...] | None = None,
        criticality_weights: dict[str, float] | None = None,
    ):
        if nodes is None or links is None:
            default_nodes, default_links = generate_enterprise_topology()
            self._nodes = list(nodes) if nodes is not None else default_nodes
            self._links = list(links) if links is not None else default_links
        else:
            self._nodes = list(nodes)
            self._links = list(links)

        self._catalog = catalog if catalog is not None else EnterpriseServiceCatalog()
        self._ingress_nodes = (
            ingress_nodes if ingress_nodes is not None else DEFAULT_CLIENT_INGRESS_NODES
        )
        self._criticality_weights = (
            criticality_weights
            if criticality_weights is not None
            else DEFAULT_CRITICALITY_WEIGHTS
        )
        self._baseline_graph = build_network_graph(self._nodes, self._links)

    @property
    def catalog(self) -> EnterpriseServiceCatalog:
        return self._catalog

    def get_service_paths(self, service_id: str) -> list[list[str]]:
        """Compute all primary shortest paths from ingress nodes to the service host."""
        service = self._catalog.get_service(service_id)
        if not service:
            return []
        host = service.host_node_id
        paths: list[list[str]] = []
        for ingress in self._ingress_nodes:
            if ingress == host:
                continue
            if nx.has_path(self._baseline_graph, ingress, host):
                try:
                    paths.extend(nx.all_shortest_paths(self._baseline_graph, ingress, host))
                except nx.NetworkXNoPath:
                    continue
        return paths

    def analyze(
        self,
        failed_nodes: list[str] | set[str] | None = None,
        failed_links: list[tuple[str, str]] | set[tuple[str, str]] | None = None,
    ) -> ServiceImpactReport:
        """Perform deterministic redundancy-aware impact analysis.

        Steps:
        1. Identify directly affected infrastructure elements (nodes & links).
        2. Trace broken baseline network paths.
        3. Evaluate physical host reachability across redundant paths.
        4. Distinguish direct host/path impact from transitive dependency impact.
        5. Propagate dependency impacts along consumer -> provider relationships.
        6. Compute Blast Radius Index based on configured criticality weights.
        """
        failed_node_set: set[str] = set(failed_nodes or ())
        failed_link_set: set[frozenset[str]] = {
            frozenset([u, v]) for u, v in (failed_links or ())
        }

        # 1. Directly affected infrastructure
        directly_affected_nodes = tuple(
            sorted(failed_node_set & set(self._baseline_graph.nodes()))
        )
        directly_affected_links_set = {
            tuple(sorted([u, v]))
            for u, v in self._baseline_graph.edges()
            if frozenset([u, v]) in failed_link_set
        }
        directly_affected_links = tuple(
            sorted(directly_affected_links_set, key=lambda pair: (pair[0], pair[1]))
        )

        # 2. Build operational network subgraph
        op_graph = self._baseline_graph.copy()
        for node in directly_affected_nodes:
            if node in op_graph:
                op_graph.remove_node(node)
        for u, v in directly_affected_links:
            if op_graph.has_edge(u, v):
                op_graph.remove_edge(u, v)

        # 3. Trace affected network paths and evaluate direct service impact
        affected_paths_list: list[tuple[str, ...]] = []
        service_statuses: dict[str, str] = {}
        directly_impacted_services: set[str] = set()

        alive_ingress = [
            n for n in self._ingress_nodes if n in op_graph
        ]

        all_services = self._catalog.get_all_services()

        for service in all_services:
            host = service.host_node_id

            # Direct host failure
            if host in failed_node_set or host not in op_graph:
                service_statuses[service.service_id] = "unavailable"
                directly_impacted_services.add(service.service_id)
                continue

            # Trace baseline paths for broken elements
            baseline_paths = self.get_service_paths(service.service_id)
            broken_paths = []
            for path in baseline_paths:
                # Check if path intersects failed nodes or links
                nodes_in_path = set(path)
                links_in_path = {
                    frozenset([path[i], path[i + 1]]) for i in range(len(path) - 1)
                }
                if (nodes_in_path & failed_node_set) or (links_in_path & failed_link_set):
                    broken_paths.append(tuple(path))
            affected_paths_list.extend(broken_paths)

            # Redundancy-aware reachability check in operational graph
            if not alive_ingress:
                # All external ingress nodes failed
                service_statuses[service.service_id] = "unavailable"
                directly_impacted_services.add(service.service_id)
                continue

            reachable_ingress_count = sum(
                1 for ingress in alive_ingress if nx.has_path(op_graph, ingress, host)
            )

            if reachable_ingress_count == 0:
                # Complete network partition to host
                service_statuses[service.service_id] = "unavailable"
                directly_impacted_services.add(service.service_id)
            elif reachable_ingress_count < len(alive_ingress) or broken_paths:
                # Redundant paths exist, but redundancy is reduced or partial partition
                service_statuses[service.service_id] = "degraded"
                directly_impacted_services.add(service.service_id)
            else:
                # Fully reachable with no interrupted baseline paths
                service_statuses[service.service_id] = "healthy"

        # 4. Transitive dependency impact propagation
        transitively_impacted_services: set[str] = set()

        # Propagate unavailable dependencies
        for s_id in list(directly_impacted_services):
            if service_statuses.get(s_id) == "unavailable":
                consumers = self._catalog.get_transitive_consumers(s_id)
                for consumer_id in consumers:
                    transitively_impacted_services.add(consumer_id)
                    service_statuses[consumer_id] = "unavailable"

        # Propagate degraded dependencies
        for s_id in list(directly_impacted_services):
            if service_statuses.get(s_id) == "degraded":
                consumers = self._catalog.get_transitive_consumers(s_id)
                for consumer_id in consumers:
                    if service_statuses.get(consumer_id) == "healthy":
                        transitively_impacted_services.add(consumer_id)
                        service_statuses[consumer_id] = "degraded"

        # Only count services as transitive if they were not already directly impacted
        actual_transitive = transitively_impacted_services - directly_impacted_services

        # 5. Compute Blast Radius Index
        all_impacted = directly_impacted_services | transitively_impacted_services
        bri, bri_percent = compute_blast_radius_index(
            all_impacted, self._catalog, self._criticality_weights
        )

        # 6. Overall severity
        statuses = set(service_statuses.values())
        if "unavailable" in statuses:
            overall_severity = "critical"
        elif "degraded" in statuses:
            overall_severity = "warning"
        else:
            overall_severity = "normal"

        return ServiceImpactReport(
            directly_affected_nodes=directly_affected_nodes,
            directly_affected_links=directly_affected_links,
            affected_paths=tuple(sorted(set(affected_paths_list))),
            directly_impacted_services=tuple(sorted(directly_impacted_services)),
            transitively_impacted_services=tuple(sorted(actual_transitive)),
            service_statuses=service_statuses,
            blast_radius_index=bri,
            blast_radius_percent=bri_percent,
            overall_severity=overall_severity,
        )


def analyze_service_impact(
    nodes: list[NetworkNode] | None = None,
    links: list[NetworkLink] | None = None,
    catalog: EnterpriseServiceCatalog | None = None,
    *,
    failed_nodes: list[str] | set[str] | None = None,
    failed_links: list[tuple[str, str]] | set[tuple[str, str]] | None = None,
    ingress_nodes: tuple[str, ...] | None = None,
    criticality_weights: dict[str, float] | None = None,
) -> ServiceImpactReport:
    """Convenience functional wrapper for ServiceImpactAnalyzer.analyze."""
    analyzer = ServiceImpactAnalyzer(
        nodes=nodes,
        links=links,
        catalog=catalog,
        ingress_nodes=ingress_nodes,
        criticality_weights=criticality_weights,
    )
    return analyzer.analyze(failed_nodes=failed_nodes, failed_links=failed_links)
