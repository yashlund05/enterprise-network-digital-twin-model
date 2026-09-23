"""Deterministic hierarchical telecom topology generation."""

from __future__ import annotations

import math

from telecom_twin.models import NetworkLink, NetworkNode


def generate_topology() -> tuple[list[NetworkNode], list[NetworkLink]]:
    """Build a three-tier synthetic topology with no real operator identifiers."""
    nodes: list[NetworkNode] = []
    links: list[NetworkLink] = []
    for index in range(3):
        angle = 2 * math.pi * index / 3 + math.pi / 2
        nodes.append(
            NetworkNode(
                f"core-{index + 1:02d}",
                "core",
                "synthetic-central",
                0.24 * math.cos(angle),
                0.24 * math.sin(angle),
                100000.0,
            )
        )
    for index in range(3):
        links.append(NetworkLink(f"core-{index + 1:02d}", f"core-{(index + 1) % 3 + 1:02d}", 100000.0, 1.0))

    for aggregation_index in range(6):
        angle = 2 * math.pi * aggregation_index / 6 + math.pi / 2
        aggregation_id = f"aggregation-{aggregation_index + 1:02d}"
        core_id = f"core-{aggregation_index // 2 + 1:02d}"
        nodes.append(
            NetworkNode(
                aggregation_id,
                "aggregation",
                f"synthetic-zone-{aggregation_index + 1}",
                0.56 * math.cos(angle),
                0.56 * math.sin(angle),
                25000.0,
            )
        )
        links.append(NetworkLink(core_id, aggregation_id, 25000.0, 3.0))
        for local_index in range(3):
            access_index = aggregation_index * 3 + local_index + 1
            offset = (local_index - 1) * 0.10
            access_angle = angle + offset
            access_id = f"access-{access_index:02d}"
            nodes.append(
                NetworkNode(
                    access_id,
                    "access",
                    f"synthetic-zone-{aggregation_index + 1}",
                    0.92 * math.cos(access_angle),
                    0.92 * math.sin(access_angle),
                    1000.0,
                )
            )
            links.append(NetworkLink(aggregation_id, access_id, 1000.0, 8.0))
    return nodes, links


def topology_is_connected(nodes: list[NetworkNode], links: list[NetworkLink]) -> bool:
    adjacency = {node.node_id: set() for node in nodes}
    for link in links:
        adjacency[link.source].add(link.target)
        adjacency[link.target].add(link.source)
    visited: set[str] = set()
    frontier = [nodes[0].node_id]
    while frontier:
        node = frontier.pop()
        if node in visited:
            continue
        visited.add(node)
        frontier.extend(adjacency[node] - visited)
    return len(visited) == len(nodes)
