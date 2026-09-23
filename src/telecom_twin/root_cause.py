"""Topology-aware synthetic alarm propagation and root-cause ranking."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import networkx as nx

from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.impact import ServiceImpactAnalyzer, build_network_graph
from telecom_twin.models import Alarm, NetworkLink, NetworkNode
from telecom_twin.online import AnomalyEvent
from telecom_twin.services import EnterpriseServiceCatalog


@dataclass(frozen=True)
class FaultScenario:
    scenario_id: str
    root_cause: str
    affected_nodes: tuple[str, ...]
    observed_alarms: tuple[str, ...]


def hierarchy_children(links: list[NetworkLink]) -> dict[str, set[str]]:
    """Keep only cross-tier causal edges; same-tier links provide redundancy."""
    children: dict[str, set[str]] = {}
    tier = {"core": 0, "aggregation": 1, "access": 2}
    for link in links:
        source_role = link.source.split("-", maxsplit=1)[0]
        target_role = link.target.split("-", maxsplit=1)[0]
        if tier[source_role] < tier[target_role]:
            children.setdefault(link.source, set()).add(link.target)
    return children


def descendants(node_id: str, children: dict[str, set[str]]) -> set[str]:
    result = {node_id}
    frontier = list(children.get(node_id, set()))
    while frontier:
        node = frontier.pop()
        if node in result:
            continue
        result.add(node)
        frontier.extend(children.get(node, set()))
    return result


def build_scenarios(
    nodes: list[NetworkNode], links: list[NetworkLink], *, seed: int = 91
) -> list[FaultScenario]:
    """Create repeatable access, aggregation, and core faults with alarm noise."""
    randomizer = random.Random(seed)
    children = hierarchy_children(links)
    node_ids = {node.node_id for node in nodes}
    roots = ("access-07", "aggregation-03", "core-02")
    scenarios = []
    for index, root in enumerate(roots, start=1):
        affected = sorted(descendants(root, children))
        observed = [node for node in affected if node == root or randomizer.random() > 0.18]
        false_candidates = sorted(node_ids - set(affected))
        observed.extend(randomizer.sample(false_candidates, k=index - 1))
        scenarios.append(
            FaultScenario(
                f"scenario-{index:02d}", root, tuple(affected), tuple(sorted(set(observed)))
            )
        )
    return scenarios


def rank_root_causes(
    observed_alarms: tuple[str, ...], nodes: list[NetworkNode], links: list[NetworkLink]
) -> list[dict[str, float | str]]:
    """Rank candidates using explained alarms, missing coverage, and overreach."""
    observed = set(observed_alarms)
    children = hierarchy_children(links)
    rows = []
    for node in nodes:
        predicted = descendants(node.node_id, children)
        explained = len(observed & predicted)
        precision = explained / len(predicted)
        recall = explained / len(observed) if observed else 0.0
        root_bonus = 0.08 if node.node_id in observed else 0.0
        score = 0.72 * recall + 0.28 * precision + root_bonus
        rows.append(
            {
                "candidate": node.node_id,
                "score": score,
                "explained_alarm_fraction": recall,
                "predicted_affected_precision": precision,
            }
        )
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["candidate"])))


def evaluate_root_cause(nodes: list[NetworkNode], links: list[NetworkLink]) -> list[dict]:
    rows = []
    for scenario in build_scenarios(nodes, links):
        ranking = rank_root_causes(scenario.observed_alarms, nodes, links)
        ranked_ids = [str(row["candidate"]) for row in ranking]
        rank = ranked_ids.index(scenario.root_cause) + 1
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "root_cause": scenario.root_cause,
                "affected_node_count": len(scenario.affected_nodes),
                "observed_alarm_count": len(scenario.observed_alarms),
                "predicted_root": ranked_ids[0],
                "true_root_rank": rank,
                "top1_correct": float(rank == 1),
                "top3_correct": float(rank <= 3),
                "top_score": ranking[0]["score"],
            }
        )
    return rows


# ==============================================================================
# Enterprise Root Cause Analysis (Phase 6)
# ==============================================================================

DEFAULT_RCA_WEIGHTS: dict[str, float] = {
    "temporal": 0.30,
    "topology": 0.35,
    "anomaly": 0.15,
    "service_impact": 0.20,
}

ENTERPRISE_TIER_RANKS: dict[str, int] = {
    "edge": 0,
    "core": 1,
    "distribution": 2,
    "access": 3,
    "application": 4,
    "host": 4,
}


@dataclass(frozen=True)
class EnterpriseRCACandidate:
    """Structured representation of an enterprise root-cause candidate hypothesis."""

    candidate_id: str
    candidate_type: str  # "node" or "link"
    confidence: float    # Normalized RCA confidence score in [0.0, 1.0]
    rank: int            # 1-indexed deterministic rank
    supporting_evidence: tuple[str, ...]
    affected_nodes: tuple[str, ...]
    affected_services: tuple[str, ...]
    temporal_evidence: dict[str, float | str]
    topology_evidence: dict[str, float | str | int | bool]

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "confidence": round(self.confidence, 4),
            "rank": self.rank,
            "supporting_evidence": list(self.supporting_evidence),
            "affected_nodes": list(self.affected_nodes),
            "affected_services": list(self.affected_services),
            "temporal_evidence": dict(self.temporal_evidence),
            "topology_evidence": dict(self.topology_evidence),
        }


@dataclass(frozen=True)
class EnterpriseRCAReport:
    """Comprehensive incident diagnosis report containing ranked candidates."""

    candidates: tuple[EnterpriseRCACandidate, ...]
    analyzed_anomalies_count: int
    incident_timestamp_s: int
    root_cause_candidate_id: str | None
    multi_fault_detected: bool

    def to_dict(self) -> dict:
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "analyzed_anomalies_count": self.analyzed_anomalies_count,
            "incident_timestamp_s": self.incident_timestamp_s,
            "root_cause_candidate_id": self.root_cause_candidate_id,
            "multi_fault_detected": self.multi_fault_detected,
        }


def build_enterprise_causal_graph(
    nodes: list[NetworkNode], links: list[NetworkLink]
) -> nx.DiGraph:
    """Build directed causal graph orienting cross-tier edges from upstream to downstream.

    Same-tier peer links (e.g. core-01 <-> core-02, edge-01 <-> edge-02) provide
    redundancy rather than causal hierarchy and are excluded from causal propagation edges.
    """
    node_tier_map = {
        node.node_id: ENTERPRISE_TIER_RANKS.get(node.tier or node.role, 3)
        for node in nodes
    }
    causal_graph = nx.DiGraph()
    for node in nodes:
        causal_graph.add_node(
            node.node_id,
            role=node.role,
            tier=node.tier,
            rank=node_tier_map.get(node.node_id, 3),
        )

    for link in links:
        source_rank = node_tier_map.get(link.source, 3)
        target_rank = node_tier_map.get(link.target, 3)
        if source_rank < target_rank:
            causal_graph.add_edge(link.source, link.target, capacity_mbps=link.capacity_mbps)
        elif target_rank < source_rank:
            causal_graph.add_edge(link.target, link.source, capacity_mbps=link.capacity_mbps)

    return causal_graph


class EnterpriseRootCauseAnalyzer:
    """Deterministic, redundancy-aware enterprise root-cause analysis engine.

    Combines temporal anomaly progression, topological hierarchy, anomaly strength,
    and modeled enterprise service impact into normalized root-cause confidence scores.
    """

    def __init__(
        self,
        nodes: list[NetworkNode] | None = None,
        links: list[NetworkLink] | None = None,
        catalog: EnterpriseServiceCatalog | None = None,
        impact_analyzer: ServiceImpactAnalyzer | None = None,
        *,
        weights: dict[str, float] | None = None,
    ):
        if nodes is None or links is None:
            default_nodes, default_links = generate_enterprise_topology()
            self._nodes = list(nodes) if nodes is not None else default_nodes
            self._links = list(links) if links is not None else default_links
        else:
            self._nodes = list(nodes)
            self._links = list(links)

        self._catalog = catalog if catalog is not None else EnterpriseServiceCatalog()
        self._impact_analyzer = (
            impact_analyzer
            if impact_analyzer is not None
            else ServiceImpactAnalyzer(self._nodes, self._links, self._catalog)
        )
        self._weights = dict(weights or DEFAULT_RCA_WEIGHTS)
        self._causal_graph = build_enterprise_causal_graph(self._nodes, self._links)
        self._network_graph = build_network_graph(self._nodes, self._links)
        self._node_map = {n.node_id: n for n in self._nodes}

    @property
    def causal_graph(self) -> nx.DiGraph:
        """Return an immutable copy of the directed causal graph."""
        return self._causal_graph.copy()

    @staticmethod
    def _normalize_anomalies(
        anomalies: list[Any] | tuple[Any, ...],
    ) -> dict[str, dict[str, Any]]:
        """Extract a structured per-node summary from diverse anomaly inputs."""
        summary: dict[str, dict[str, Any]] = {}
        for item in anomalies:
            if isinstance(item, AnomalyEvent):
                node_id = item.node_id
                t = item.timestamp_s
                score = item.composite_z if item.composite_z > 0.0 else item.score
                severity = item.severity
                raw_ev = list(item.evidence)
            elif isinstance(item, Alarm):
                node_id = item.node_id
                t = item.timestamp_s
                score = 5.0 if item.severity.lower() == "critical" else 3.5
                severity = item.severity.upper()
                raw_ev = [f"{item.metric} alarm"]
            elif isinstance(item, dict):
                node_id = str(item.get("node_id") or item.get("node"))
                t = int(item.get("timestamp_s", item.get("timestamp", 0)))
                score = float(item.get("composite_z", item.get("score", 3.0)))
                severity = str(item.get("severity", "WARNING")).upper()
                raw_data = item.get("evidence", [])
                raw_ev = list(raw_data) if isinstance(raw_data, (list, tuple)) else [str(raw_data)]
            elif isinstance(item, str):
                node_id = item
                t = 0
                score = 4.0
                severity = "WARNING"
                raw_ev = ["observed anomaly"]
            else:
                continue

            if node_id not in summary:
                summary[node_id] = {
                    "node_id": node_id,
                    "first_seen": t,
                    "last_seen": t,
                    "max_score": score,
                    "worst_severity": severity,
                    "evidence": set(raw_ev),
                }
            else:
                entry = summary[node_id]
                entry["first_seen"] = min(entry["first_seen"], t)
                entry["last_seen"] = max(entry["last_seen"], t)
                entry["max_score"] = max(entry["max_score"], score)
                if severity == "CRITICAL" or entry["worst_severity"] != "CRITICAL":
                    entry["worst_severity"] = severity
                entry["evidence"].update(raw_ev)
        return summary

    def analyze(
        self,
        anomalies: list[Any] | tuple[Any, ...],
        *,
        failed_links: list[tuple[str, str]] | None = None,
        observed_impacted_services: list[str] | set[str] | None = None,
    ) -> EnterpriseRCAReport:
        """Perform comprehensive, deterministic Enterprise Root Cause Analysis."""
        node_anomalies = self._normalize_anomalies(anomalies)
        if not node_anomalies and not failed_links:
            return EnterpriseRCAReport(
                candidates=(),
                analyzed_anomalies_count=0,
                incident_timestamp_s=0,
                root_cause_candidate_id=None,
                multi_fault_detected=False,
            )

        incident_timestamp_s = (
            min(entry["first_seen"] for entry in node_anomalies.values())
            if node_anomalies
            else 0
        )

        # 1. Candidate Generation
        candidate_ids: set[str] = set(node_anomalies.keys())
        # Add upstream parents in causal graph
        for node_id in list(candidate_ids):
            if node_id in self._causal_graph:
                candidate_ids.update(self._causal_graph.predecessors(node_id))

        # Add link endpoints
        if failed_links:
            for u, v in failed_links:
                candidate_ids.add(u)
                candidate_ids.add(v)

        # Filter candidates to known nodes
        candidate_nodes = sorted(candidate_ids & set(self._node_map.keys()))

        # Determine observed impacted services
        if observed_impacted_services is not None:
            observed_services = set(observed_impacted_services)
        else:
            # Derive from hosts that exhibited anomalies
            observed_services = set()
            for node_id in node_anomalies:
                services_on_host = self._catalog.get_services_by_host(node_id)
                for s in services_on_host:
                    observed_services.add(s.service_id)

        # Precompute all primary shortest paths from ingress to hosts
        all_service_paths: dict[str, list[list[str]]] = {}
        for s in self._catalog.get_all_services():
            all_service_paths[s.service_id] = self._impact_analyzer.get_service_paths(s.service_id)

        # Track which baseline paths intersect observed anomalous nodes
        affected_paths_set: set[tuple[str, ...]] = set()
        for paths in all_service_paths.values():
            for p in paths:
                if any(step in node_anomalies for step in p):
                    affected_paths_set.add(tuple(p))

        candidates_data: list[dict[str, Any]] = []

        # 2. Evidence Scoring for Each Candidate
        for cand_id in candidate_nodes:
            cand_node = self._node_map[cand_id]
            is_anomalous = cand_id in node_anomalies
            anom_info = node_anomalies.get(cand_id)

            # A. Temporal Evidence
            if is_anomalous and anom_info is not None:
                t_cand = anom_info["first_seen"]
                delta_origin = t_cand - incident_timestamp_s

                # Check temporal precedence against downstream symptoms
                downstream_nodes = (
                    set(nx.descendants(self._causal_graph, cand_id))
                    if cand_id in self._causal_graph
                    else set()
                )
                downstream_symptoms = sorted(downstream_nodes & set(node_anomalies.keys()))

                if downstream_symptoms:
                    lead_count = sum(
                        1
                        for d in downstream_symptoms
                        if t_cand <= node_anomalies[d]["first_seen"] + 1.0
                    )
                    precedence_ratio = lead_count / len(downstream_symptoms)
                    time_leads = [
                        node_anomalies[d]["first_seen"] - t_cand for d in downstream_symptoms
                    ]
                    avg_time_lead = sum(time_leads) / len(time_leads)
                    s_temporal = min(
                        1.0,
                        0.50 * max(0.0, 1.0 - delta_origin / 30.0) + 0.50 * precedence_ratio,
                    )
                    if avg_time_lead > 0.0:
                        temp_msg = (
                            f"anomaly observed {round(avg_time_lead, 1)} s before downstream alarms"
                        )
                    else:
                        temp_msg = f"earliest anomaly signal at t={t_cand} s"
                else:
                    s_temporal = max(0.0, 1.0 - delta_origin / 30.0)
                    temp_msg = f"anomaly observed at t={t_cand} s"
            else:
                t_cand = incident_timestamp_s
                s_temporal = 0.50
                temp_msg = "inferred structural candidate without direct anomaly"

            # B. Topology Evidence
            if cand_id in self._causal_graph:
                downstream_all = set(nx.descendants(self._causal_graph, cand_id)) | {cand_id}
            else:
                downstream_all = {cand_id}

            explained_anomalies = sorted(downstream_all & set(node_anomalies.keys()))
            recall = len(explained_anomalies) / max(1, len(node_anomalies))
            precision = len(explained_anomalies) / max(1, len(downstream_all))

            paths_with_cand = sum(1 for p in affected_paths_set if cand_id in p)
            if affected_paths_set:
                path_relevance = paths_with_cand / len(affected_paths_set)
            else:
                path_relevance = 0.5 if cand_id in self._network_graph else 0.0

            # Upstream structural bonus for explaining multiple symptoms
            tier_rank = ENTERPRISE_TIER_RANKS.get(cand_node.tier or cand_node.role, 3)
            upstream_bonus = 0.12 if (tier_rank <= 2 and len(explained_anomalies) >= 2) else 0.0

            s_topology = min(
                1.0,
                0.40 * recall + 0.30 * precision + 0.30 * path_relevance + upstream_bonus,
            )

            if len(explained_anomalies) > 1 and cand_id != explained_anomalies[0]:
                topo_msg = (
                    f"upstream node explaining {len(explained_anomalies)} downstream symptoms "
                    f"({', '.join(explained_anomalies[:3])})"
                )
            elif len(explained_anomalies) == 1 and explained_anomalies[0] == cand_id:
                topo_msg = "local anomaly without downstream propagation"
            else:
                topo_msg = f"explains {len(explained_anomalies)} observed symptoms"

            if paths_with_cand > 0:
                topo_path_msg = f"lies on {paths_with_cand} affected client-to-service paths"
            else:
                topo_path_msg = "not located on primary affected service paths"

            # C. Anomaly Strength Evidence
            if is_anomalous and anom_info is not None:
                max_z = anom_info["max_score"]
                worst_sev = anom_info["worst_severity"]
                if worst_sev == "CRITICAL" or max_z >= 5.0:
                    s_anomaly = min(1.0, 0.90 + 0.02 * min(5.0, max_z - 5.0))
                elif worst_sev == "WARNING" or max_z >= 4.0:
                    s_anomaly = 0.75
                elif worst_sev == "INFO" or max_z >= 3.0:
                    s_anomaly = 0.60
                else:
                    s_anomaly = 0.40
                anom_msg = f"peak composite z-score {round(max_z, 2)} ({worst_sev})"
            else:
                max_z = 0.0
                worst_sev = "NORMAL"
                s_anomaly = 0.20
                anom_msg = "no direct anomaly telemetry on candidate"

            # D. Service-Impact Evidence
            impact_res = self._impact_analyzer.analyze(failed_nodes=[cand_id])
            modeled_services = sorted(
                set(impact_res.directly_impacted_services)
                | set(impact_res.transitively_impacted_services)
            )

            if observed_services:
                explained_services = sorted(set(modeled_services) & observed_services)
                if explained_services:
                    imp_recall = len(explained_services) / max(1, len(observed_services))
                    imp_precision = len(explained_services) / max(1, len(modeled_services))
                    s_impact = min(1.0, 0.70 * imp_recall + 0.30 * imp_precision)
                    impact_msg = (
                        f"explains {len(explained_services)} impacted services "
                        f"({', '.join(explained_services[:3])})"
                    )
                else:
                    s_impact = 0.10
                    impact_msg = "does not explain observed service disruptions"
            else:
                if impact_res.overall_severity in ("normal", "warning"):
                    s_impact = 0.80
                    impact_msg = "redundant paths keep enterprise services operational"
                else:
                    s_impact = 0.50
                    impact_msg = "no active service outage observed"

            # E. Redundancy Awareness
            op_graph = self._network_graph.copy()
            if cand_id in op_graph:
                op_graph.remove_node(cand_id)
            alive_ingress = [
                i for i in self._impact_analyzer._ingress_nodes if i != cand_id and i in op_graph
            ]
            all_hosts = [
                s.host_node_id
                for s in self._catalog.get_all_services()
                if s.host_node_id in op_graph
            ]
            hosts_reachable = all(
                any(nx.has_path(op_graph, ing, h) for ing in alive_ingress)
                for h in all_hosts
            ) if alive_ingress and all_hosts else False

            if hosts_reachable and cand_node.tier != "application":
                redundancy_maintained = True
                redundancy_msg = "alternate core/distribution path remained available; services maintained connectivity"
            else:
                redundancy_maintained = False
                redundancy_msg = "no alternate redundant path; failure severs client reachability"

            # Combined Confidence Score
            total_confidence = (
                self._weights["temporal"] * s_temporal
                + self._weights["topology"] * s_topology
                + self._weights["anomaly"] * s_anomaly
                + self._weights["service_impact"] * s_impact
            )
            confidence = round(min(1.0, max(0.0, total_confidence)), 4)

            # Assemble clean supporting evidence strings
            evidence_items = [temp_msg, topo_msg, topo_path_msg, anom_msg, impact_msg, redundancy_msg]
            supporting_evidence = tuple(ev for ev in evidence_items if ev)

            candidates_data.append(
                {
                    "candidate_id": cand_id,
                    "candidate_type": "node",
                    "confidence": confidence,
                    "supporting_evidence": supporting_evidence,
                    "affected_nodes": tuple(explained_anomalies),
                    "affected_services": tuple(modeled_services),
                    "temporal_evidence": {
                        "first_seen_s": t_cand,
                        "time_since_incident_start_s": round(t_cand - incident_timestamp_s, 2),
                        "score": round(s_temporal, 4),
                        "detail": temp_msg,
                    },
                    "topology_evidence": {
                        "tier": cand_node.tier,
                        "explained_symptom_count": len(explained_anomalies),
                        "paths_with_candidate": paths_with_cand,
                        "redundancy_maintained": redundancy_maintained,
                        "score": round(s_topology, 4),
                        "detail": topo_msg,
                    },
                }
            )

        # 3. Deterministic Sorting & Rank Assignment
        candidates_data.sort(key=lambda item: (-item["confidence"], item["candidate_id"]))

        # 4. Multi-Fault Detection
        # Check if the top candidates explain mutually disjoint subsets of anomalies
        multi_fault = False
        if len(candidates_data) >= 2:
            top_1 = candidates_data[0]
            top_2 = candidates_data[1]
            if top_1["confidence"] >= 0.50 and top_2["confidence"] >= 0.50:
                s1 = set(top_1["affected_nodes"])
                s2 = set(top_2["affected_nodes"])
                # If neither explains the other and their symptoms are disjoint
                is_connected_in_causal = (
                    top_1["candidate_id"] in self._causal_graph
                    and top_2["candidate_id"] in self._causal_graph
                    and (
                        nx.has_path(self._causal_graph, top_1["candidate_id"], top_2["candidate_id"])
                        or nx.has_path(self._causal_graph, top_2["candidate_id"], top_1["candidate_id"])
                    )
                )
                if not is_connected_in_causal and len(s1 & s2) == 0 and len(s1) > 0 and len(s2) > 0:
                    multi_fault = True

        ranked_candidates = tuple(
            EnterpriseRCACandidate(
                candidate_id=c["candidate_id"],
                candidate_type=c["candidate_type"],
                confidence=c["confidence"],
                rank=idx + 1,
                supporting_evidence=c["supporting_evidence"],
                affected_nodes=c["affected_nodes"],
                affected_services=c["affected_services"],
                temporal_evidence=c["temporal_evidence"],
                topology_evidence=c["topology_evidence"],
            )
            for idx, c in enumerate(candidates_data)
        )

        root_id = ranked_candidates[0].candidate_id if ranked_candidates else None

        return EnterpriseRCAReport(
            candidates=ranked_candidates,
            analyzed_anomalies_count=len(node_anomalies),
            incident_timestamp_s=incident_timestamp_s,
            root_cause_candidate_id=root_id,
            multi_fault_detected=multi_fault,
        )


def analyze_enterprise_root_cause(
    anomalies: list[Any] | tuple[Any, ...],
    nodes: list[NetworkNode] | None = None,
    links: list[NetworkLink] | None = None,
    catalog: EnterpriseServiceCatalog | None = None,
    *,
    failed_links: list[tuple[str, str]] | None = None,
    observed_impacted_services: list[str] | set[str] | None = None,
    weights: dict[str, float] | None = None,
) -> EnterpriseRCAReport:
    """Convenience functional wrapper for EnterpriseRootCauseAnalyzer.analyze."""
    analyzer = EnterpriseRootCauseAnalyzer(
        nodes=nodes,
        links=links,
        catalog=catalog,
        weights=weights,
    )
    return analyzer.analyze(
        anomalies,
        failed_links=failed_links,
        observed_impacted_services=observed_impacted_services,
    )

