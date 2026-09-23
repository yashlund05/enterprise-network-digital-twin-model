"""Deterministic enterprise network topology generation with multi-tier redundancy."""

from __future__ import annotations

from telecom_twin.models import NetworkLink, NetworkNode

# Canonical node identifiers across the 5 tiers and enterprise host layer
EDGE_NODE_IDS = ("edge-gw-01", "edge-gw-02")
CORE_NODE_IDS = ("core-sw-01", "core-sw-02")
DISTRIBUTION_NODE_IDS = (
    "dist-sw-campus-01",
    "dist-sw-campus-02",
    "dist-sw-dc-01",
    "dist-sw-dc-02",
)
ACCESS_NODE_IDS = (
    "acc-sw-hq-01",
    "acc-sw-hq-02",
    "acc-sw-hq-03",
    "acc-sw-hq-04",
    "acc-sw-dc-01",
    "acc-sw-dc-02",
    "acc-sw-dc-03",
    "acc-sw-dc-04",
)
HOST_NODE_IDS = (
    "host-erp",
    "host-api",
    "host-db",
    "host-dns",
    "host-auth",
    "host-mon",
)

ALL_ENTERPRISE_NODE_IDS = (
    EDGE_NODE_IDS
    + CORE_NODE_IDS
    + DISTRIBUTION_NODE_IDS
    + ACCESS_NODE_IDS
    + HOST_NODE_IDS
)


def generate_enterprise_topology() -> tuple[list[NetworkNode], list[NetworkLink]]:
    """Build a deterministic, connected, redundant enterprise network topology.

    Architecture:
        Internet / WAN
              |
          Edge Tier          (2 Border Gateways / Firewalls, HA Mesh)
              |
          Core Tier          (2 Spine Switches, MLAG / VPC Interconnect)
              |
      Distribution Tier      (2 Campus Dist + 2 DC Dist Switches)
              |
         Access Tier         (4 Campus Access + 4 DC Leaf Switches)
              |
    Enterprise Host Layer    (6 Business Application / Infrastructure Pods)
    """
    nodes: list[NetworkNode] = []
    links: list[NetworkLink] = []

    # 1. Edge Tier (y = 0.80)
    nodes.append(
        NetworkNode(
            node_id="edge-gw-01",
            role="edge",
            region="perimeter-dmz",
            x=-0.28,
            y=0.80,
            capacity_mbps=20000.0,
            tier="edge",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=10,
        )
    )
    nodes.append(
        NetworkNode(
            node_id="edge-gw-02",
            role="edge",
            region="perimeter-dmz",
            x=0.28,
            y=0.80,
            capacity_mbps=20000.0,
            tier="edge",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=10,
        )
    )

    # 2. Core Tier (y = 0.42)
    nodes.append(
        NetworkNode(
            node_id="core-sw-01",
            role="core",
            region="campus-spine",
            x=-0.32,
            y=0.42,
            capacity_mbps=40000.0,
            tier="core",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=1,
        )
    )
    nodes.append(
        NetworkNode(
            node_id="core-sw-02",
            role="core",
            region="campus-spine",
            x=0.32,
            y=0.42,
            capacity_mbps=40000.0,
            tier="core",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=1,
        )
    )

    # 3. Distribution Tier (y = 0.05)
    # Campus distribution (HQ)
    nodes.append(
        NetworkNode(
            node_id="dist-sw-campus-01",
            role="distribution",
            region="campus-dist",
            x=-0.72,
            y=0.05,
            capacity_mbps=10000.0,
            tier="distribution",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=20,
        )
    )
    nodes.append(
        NetworkNode(
            node_id="dist-sw-campus-02",
            role="distribution",
            region="campus-dist",
            x=-0.24,
            y=0.05,
            capacity_mbps=10000.0,
            tier="distribution",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=20,
        )
    )
    # Data Center distribution
    nodes.append(
        NetworkNode(
            node_id="dist-sw-dc-01",
            role="distribution",
            region="dc-dist",
            x=0.24,
            y=0.05,
            capacity_mbps=25000.0,
            tier="distribution",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=30,
        )
    )
    nodes.append(
        NetworkNode(
            node_id="dist-sw-dc-02",
            role="distribution",
            region="dc-dist",
            x=0.72,
            y=0.05,
            capacity_mbps=25000.0,
            tier="distribution",
            memory_percent=0.0,
            interface_health=1.0,
            vlan_id=30,
        )
    )

    # 4. Access Tier (y = -0.40)
    # Campus HQ access switches
    campus_access_configs = [
        ("acc-sw-hq-01", -0.84, 100),
        ("acc-sw-hq-02", -0.60, 101),
        ("acc-sw-hq-03", -0.36, 102),
        ("acc-sw-hq-04", -0.12, 103),
    ]
    for node_id, x_pos, vlan in campus_access_configs:
        nodes.append(
            NetworkNode(
                node_id=node_id,
                role="access",
                region="campus-hq",
                x=x_pos,
                y=-0.40,
                capacity_mbps=1000.0,
                tier="access",
                memory_percent=0.0,
                interface_health=1.0,
                vlan_id=vlan,
            )
        )

    # Data Center leaf switches
    dc_access_configs = [
        ("acc-sw-dc-01", 0.12, 200),
        ("acc-sw-dc-02", 0.36, 201),
        ("acc-sw-dc-03", 0.60, 202),
        ("acc-sw-dc-04", 0.84, 203),
    ]
    for node_id, x_pos, vlan in dc_access_configs:
        nodes.append(
            NetworkNode(
                node_id=node_id,
                role="access",
                region="dc-leaf",
                x=x_pos,
                y=-0.40,
                capacity_mbps=10000.0,
                tier="access",
                memory_percent=0.0,
                interface_health=1.0,
                vlan_id=vlan,
            )
        )

    # 5. Enterprise Application Hosts (y = -0.80)
    host_configs = [
        ("host-erp", "dc-pod-erp", 0.10, 10000.0, 200),
        ("host-api", "dc-pod-api", 0.25, 10000.0, 200),
        ("host-db", "dc-pod-db", 0.40, 10000.0, 201),
        ("host-dns", "dc-pod-infra", 0.55, 1000.0, 202),
        ("host-auth", "dc-pod-infra", 0.70, 1000.0, 202),
        ("host-mon", "dc-pod-ops", 0.85, 10000.0, 203),
    ]
    for node_id, region, x_pos, cap, vlan in host_configs:
        nodes.append(
            NetworkNode(
                node_id=node_id,
                role="host",
                region=region,
                x=x_pos,
                y=-0.80,
                capacity_mbps=cap,
                tier="application",
                memory_percent=0.0,
                interface_health=1.0,
                vlan_id=vlan,
            )
        )

    # Links Definition with Redundancy:

    # A. Edge HA Link
    links.append(
        NetworkLink(
            source="edge-gw-01",
            target="edge-gw-02",
            capacity_mbps=20000.0,
            base_latency_ms=0.5,
            interface_health=1.0,
            vlan_id=10,
        )
    )

    # B. Edge to Core Cross-Connect (Full mesh between 2 Edge and 2 Core)
    edge_nodes = ("edge-gw-01", "edge-gw-02")
    core_nodes = ("core-sw-01", "core-sw-02")
    for edge in edge_nodes:
        for core in core_nodes:
            links.append(
                NetworkLink(
                    source=edge,
                    target=core,
                    capacity_mbps=20000.0,
                    base_latency_ms=0.8,
                    interface_health=1.0,
                    vlan_id=1,
                )
            )

    # C. Core Spine Interconnect (Inter-chassis link)
    links.append(
        NetworkLink(
            source="core-sw-01",
            target="core-sw-02",
            capacity_mbps=40000.0,
            base_latency_ms=0.4,
            interface_health=1.0,
            vlan_id=1,
        )
    )

    # D. Core to Distribution Cross-Connect
    # Campus distribution to core (10 Gbps)
    campus_dist_nodes = ("dist-sw-campus-01", "dist-sw-campus-02")
    for dist in campus_dist_nodes:
        for core in core_nodes:
            links.append(
                NetworkLink(
                    source=core,
                    target=dist,
                    capacity_mbps=10000.0,
                    base_latency_ms=1.2,
                    interface_health=1.0,
                    vlan_id=20,
                )
            )

    # Data center distribution to core (25 Gbps)
    dc_dist_nodes = ("dist-sw-dc-01", "dist-sw-dc-02")
    for dist in dc_dist_nodes:
        for core in core_nodes:
            links.append(
                NetworkLink(
                    source=core,
                    target=dist,
                    capacity_mbps=25000.0,
                    base_latency_ms=0.6,
                    interface_health=1.0,
                    vlan_id=30,
                )
            )

    # E. Distribution Peer Links
    links.append(
        NetworkLink(
            source="dist-sw-campus-01",
            target="dist-sw-campus-02",
            capacity_mbps=10000.0,
            base_latency_ms=0.8,
            interface_health=1.0,
            vlan_id=20,
        )
    )
    links.append(
        NetworkLink(
            source="dist-sw-dc-01",
            target="dist-sw-dc-02",
            capacity_mbps=25000.0,
            base_latency_ms=0.5,
            interface_health=1.0,
            vlan_id=30,
        )
    )

    # F. Campus Distribution to Access Links (Dual-homed: each access to both campus dists)
    for node_id, _, vlan in campus_access_configs:
        for dist in campus_dist_nodes:
            links.append(
                NetworkLink(
                    source=dist,
                    target=node_id,
                    capacity_mbps=1000.0,
                    base_latency_ms=1.5,
                    interface_health=1.0,
                    vlan_id=vlan,
                )
            )

    # G. DC Distribution to DC Access Links (Dual-homed: each DC leaf to both DC dists)
    for node_id, _, vlan in dc_access_configs:
        for dist in dc_dist_nodes:
            links.append(
                NetworkLink(
                    source=dist,
                    target=node_id,
                    capacity_mbps=10000.0,
                    base_latency_ms=0.7,
                    interface_health=1.0,
                    vlan_id=vlan,
                )
            )

    # H. DC Access to Application Hosts (Dual-homed attachments)
    host_attachments = [
        ("host-erp", "acc-sw-dc-01", "acc-sw-dc-02", 10000.0, 200),
        ("host-api", "acc-sw-dc-01", "acc-sw-dc-02", 10000.0, 200),
        ("host-db", "acc-sw-dc-02", "acc-sw-dc-03", 10000.0, 201),
        ("host-dns", "acc-sw-dc-03", "acc-sw-dc-04", 1000.0, 202),
        ("host-auth", "acc-sw-dc-03", "acc-sw-dc-04", 1000.0, 202),
        ("host-mon", "acc-sw-dc-04", "acc-sw-dc-01", 10000.0, 203),
    ]
    for host_id, sw_a, sw_b, cap, vlan in host_attachments:
        links.append(
            NetworkLink(
                source=sw_a,
                target=host_id,
                capacity_mbps=cap,
                base_latency_ms=0.2,
                interface_health=1.0,
                vlan_id=vlan,
            )
        )
        links.append(
            NetworkLink(
                source=sw_b,
                target=host_id,
                capacity_mbps=cap,
                base_latency_ms=0.2,
                interface_health=1.0,
                vlan_id=vlan,
            )
        )

    return nodes, links
