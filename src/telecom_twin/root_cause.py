"""Topology-aware synthetic alarm propagation and root-cause ranking."""

from __future__ import annotations

import random
from dataclasses import dataclass

from telecom_twin.models import NetworkLink, NetworkNode


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
