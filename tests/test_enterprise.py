import math
from dataclasses import FrozenInstanceError

import pytest

from telecom_twin.models import (
    EnterpriseService,
    IncidentTimelineEvent,
    NetworkLink,
    NetworkNode,
    ServiceDependency,
    TwinSyncState,
    WhatIfResult,
    WhatIfScenario,
)


def test_network_node_backward_compatibility_and_defaults() -> None:
    # 6 positional arguments as used across the legacy codebase
    node = NetworkNode("core-01", "core", "synthetic-central", 0.0, 0.0, 100000.0)
    assert node.node_id == "core-01"
    assert node.role == "core"
    assert node.region == "synthetic-central"
    assert node.x == 0.0
    assert node.y == 0.0
    assert node.capacity_mbps == 100000.0

    # Verify enterprise default attributes
    assert node.tier is None
    assert node.memory_percent == 0.0
    assert node.interface_health == 1.0
    assert node.vlan_id is None

    # Verify explicit enterprise attributes
    ent_node = NetworkNode(
        "edge-gw-01",
        "gateway",
        "dmz",
        -0.5,
        0.8,
        20000.0,
        tier="edge",
        memory_percent=42.5,
        interface_health=0.98,
        vlan_id=10,
    )
    assert ent_node.tier == "edge"
    assert ent_node.memory_percent == 42.5
    assert ent_node.interface_health == 0.98
    assert ent_node.vlan_id == 10

    # Immutability
    with pytest.raises(FrozenInstanceError):
        node.role = "access"  # type: ignore[misc]

    # Serialization
    serialized = node.to_dict()
    assert isinstance(serialized, dict)
    assert serialized["node_id"] == "core-01"
    assert serialized["memory_percent"] == 0.0


def test_network_link_backward_compatibility_and_defaults() -> None:
    # 4 positional arguments as used across legacy codebase
    link = NetworkLink("core-01", "core-02", 100000.0, 1.0)
    assert link.source == "core-01"
    assert link.target == "core-02"
    assert link.capacity_mbps == 100000.0
    assert link.base_latency_ms == 1.0

    # Defaults
    assert link.interface_health == 1.0
    assert link.vlan_id is None

    # Explicit values
    ent_link = NetworkLink(
        "dist-01", "acc-01", 10000.0, 2.5, interface_health=0.95, vlan_id=100
    )
    assert ent_link.interface_health == 0.95
    assert ent_link.vlan_id == 100

    # Immutability
    with pytest.raises(FrozenInstanceError):
        link.capacity_mbps = 50000.0  # type: ignore[misc]

    # Serialization
    serialized = link.to_dict()
    assert serialized["source"] == "core-01"
    assert serialized["interface_health"] == 1.0


def test_enterprise_service_model() -> None:
    service = EnterpriseService(
        service_id="srv-erp",
        name="Enterprise Resource Planning",
        tier="application",
        host_node_id="acc-01",
        port=8443,
        criticality="tier-1",
        health_status="healthy",
    )
    assert service.service_id == "srv-erp"
    assert service.name == "Enterprise Resource Planning"
    assert service.port == 8443

    with pytest.raises(FrozenInstanceError):
        service.health_status = "degraded"  # type: ignore[misc]

    data = service.to_dict()
    assert data["service_id"] == "srv-erp"
    assert data["criticality"] == "tier-1"


def test_service_dependency_model() -> None:
    dep = ServiceDependency(
        consumer_service_id="srv-erp",
        provider_service_id="srv-db",
        dependency_type="critical",
    )
    assert dep.consumer_service_id == "srv-erp"
    assert dep.provider_service_id == "srv-db"
    assert dep.dependency_type == "critical"

    with pytest.raises(FrozenInstanceError):
        dep.dependency_type = "optional"  # type: ignore[misc]

    data = dep.to_dict()
    assert data["consumer_service_id"] == "srv-erp"


def test_whatif_scenario_model() -> None:
    scenario = WhatIfScenario(
        scenario_id="scenario-node-down",
        name="Core Switch 01 Failure",
        target_type="node",
        target_id="core-01",
        failure_type="down",
        parameter_value=1.0,
    )
    assert scenario.scenario_id == "scenario-node-down"
    assert scenario.target_type == "node"
    assert scenario.target_id == "core-01"

    with pytest.raises(FrozenInstanceError):
        scenario.parameter_value = 0.5  # type: ignore[misc]

    data = scenario.to_dict()
    assert data["failure_type"] == "down"


def test_whatif_result_model() -> None:
    result = WhatIfResult(
        predicted_affected_nodes=("acc-01", "acc-02"),
        predicted_affected_links=(("dist-01", "acc-01"),),
        predicted_affected_services=("srv-erp",),
        latency_delta_ms=35.5,
        loss_delta_percent=2.4,
        throughput_delta_mbps=-1200.0,
        blast_radius_percent=18.5,
        severity="major",
    )
    assert result.predicted_affected_nodes == ("acc-01", "acc-02")
    assert result.latency_delta_ms == 35.5
    assert result.severity == "major"

    with pytest.raises(FrozenInstanceError):
        result.severity = "critical"  # type: ignore[misc]

    data = result.to_dict()
    assert data["blast_radius_percent"] == 18.5


def test_incident_timeline_event_model() -> None:
    event = IncidentTimelineEvent(
        timestamp_s=124,
        stage="anomaly",
        description="Packet loss spike detected on access-07",
        active_alarms=2,
        root_cause_id="access-07",
        affected_services=("srv-dns",),
    )
    assert event.timestamp_s == 124
    assert event.stage == "anomaly"
    assert event.root_cause_id == "access-07"

    with pytest.raises(FrozenInstanceError):
        event.stage = "recovery"  # type: ignore[misc]

    data = event.to_dict()
    assert data["timestamp_s"] == 124
    assert data["root_cause_id"] == "access-07"


def test_twin_sync_state_model() -> None:
    state = TwinSyncState(
        sync_timestamp_s=150,
        telemetry_staleness_s=0.45,
        consistency_score=0.99,
    )
    assert state.sync_timestamp_s == 150
    assert state.telemetry_staleness_s == 0.45
    assert state.consistency_score == 0.99
    assert state.node_sync_status == "synchronized"

    with pytest.raises(FrozenInstanceError):
        state.consistency_score = 0.8  # type: ignore[misc]

    data = state.to_dict()
    assert data["node_sync_status"] == "synchronized"


def test_enterprise_topology_node_count_and_expected_ids() -> None:
    from telecom_twin.enterprise_topology import (
        ACCESS_NODE_IDS,
        CORE_NODE_IDS,
        DISTRIBUTION_NODE_IDS,
        EDGE_NODE_IDS,
        HOST_NODE_IDS,
        generate_enterprise_topology,
    )

    nodes, links = generate_enterprise_topology()

    # Exact expected node count (22) and link count (44)
    assert len(nodes) == 22
    assert len(links) == 44

    node_ids = {node.node_id for node in nodes}
    expected_ids = set(
        EDGE_NODE_IDS
        + CORE_NODE_IDS
        + DISTRIBUTION_NODE_IDS
        + ACCESS_NODE_IDS
        + HOST_NODE_IDS
    )
    assert node_ids == expected_ids


def test_enterprise_topology_tier_assignments() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology

    nodes, _ = generate_enterprise_topology()
    by_tier: dict[str, list[str]] = {}
    for node in nodes:
        by_tier.setdefault(node.tier, []).append(node.node_id)

    assert set(by_tier["edge"]) == {"edge-gw-01", "edge-gw-02"}
    assert set(by_tier["core"]) == {"core-sw-01", "core-sw-02"}
    assert set(by_tier["distribution"]) == {
        "dist-sw-campus-01",
        "dist-sw-campus-02",
        "dist-sw-dc-01",
        "dist-sw-dc-02",
    }
    assert set(by_tier["access"]) == {
        "acc-sw-hq-01",
        "acc-sw-hq-02",
        "acc-sw-hq-03",
        "acc-sw-hq-04",
        "acc-sw-dc-01",
        "acc-sw-dc-02",
        "acc-sw-dc-03",
        "acc-sw-dc-04",
    }
    assert set(by_tier["application"]) == {
        "host-erp",
        "host-api",
        "host-db",
        "host-dns",
        "host-auth",
        "host-mon",
    }


def test_enterprise_topology_connectivity_and_determinism() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.topology import topology_is_connected

    first_nodes, first_links = generate_enterprise_topology()
    second_nodes, second_links = generate_enterprise_topology()

    # Determinism
    assert first_nodes == second_nodes
    assert first_links == second_links

    # Connectivity
    assert topology_is_connected(first_nodes, first_links)


def test_enterprise_topology_no_duplicate_links() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology

    _, links = generate_enterprise_topology()
    seen_pairs: set[frozenset[str]] = set()
    for link in links:
        pair = frozenset([link.source, link.target])
        assert pair not in seen_pairs, f"Duplicate link detected between {link.source} and {link.target}"
        seen_pairs.add(pair)
    assert len(seen_pairs) == len(links)


def test_enterprise_topology_redundancy() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology

    nodes, links = generate_enterprise_topology()
    adjacency: dict[str, set[str]] = {node.node_id: set() for node in nodes}
    for link in links:
        adjacency[link.source].add(link.target)
        adjacency[link.target].add(link.source)

    # Edge redundancy: edge-gw-01 and edge-gw-02 interconnected and both connected to both core switches
    assert "edge-gw-02" in adjacency["edge-gw-01"]
    assert "core-sw-01" in adjacency["edge-gw-01"]
    assert "core-sw-02" in adjacency["edge-gw-01"]
    assert "core-sw-01" in adjacency["edge-gw-02"]
    assert "core-sw-02" in adjacency["edge-gw-02"]

    # Core redundancy: core-sw-01 and core-sw-02 interconnected
    assert "core-sw-02" in adjacency["core-sw-01"]

    # Distribution redundancy: all distribution switches connect to both core switches
    for dist in (
        "dist-sw-campus-01",
        "dist-sw-campus-02",
        "dist-sw-dc-01",
        "dist-sw-dc-02",
    ):
        assert "core-sw-01" in adjacency[dist]
        assert "core-sw-02" in adjacency[dist]

    # Application hosts: each host is connected to at least 2 access switches
    for host in (
        "host-erp",
        "host-api",
        "host-db",
        "host-dns",
        "host-auth",
        "host-mon",
    ):
        connected_switches = [
            neighbor for neighbor in adjacency[host] if neighbor.startswith("acc-sw-")
        ]
        assert len(connected_switches) >= 2, f"Host {host} lacks redundant switch connectivity"


def test_topology_module_reexports_enterprise_generator() -> None:
    from telecom_twin.topology import generate_enterprise_topology, generate_topology

    ent_nodes, ent_links = generate_enterprise_topology()
    assert len(ent_nodes) == 22
    assert len(ent_links) == 44
    legacy_nodes, legacy_links = generate_topology()
    assert len(legacy_nodes) == 27
    assert len(legacy_links) == 27


def test_enterprise_telemetry_generation_structure_and_bounds() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.simulation import EnterpriseTelemetry, generate_enterprise_telemetry

    nodes, links = generate_enterprise_topology()
    duration = 10
    telemetry = generate_enterprise_telemetry(nodes, links, duration_s=duration, seed=42)

    assert isinstance(telemetry, EnterpriseTelemetry)
    assert len(telemetry.node_telemetry) == len(nodes) * (duration + 1)
    assert len(telemetry.link_telemetry) == len(links) * (duration + 1)

    # Verify all expected nodes receive telemetry
    observed_nodes = {s.node_id for s in telemetry.node_telemetry}
    assert observed_nodes == {n.node_id for n in nodes}

    # Verify all expected links receive telemetry
    observed_links = {(s.source, s.target) for s in telemetry.link_telemetry}
    assert observed_links == {(l.source, l.target) for l in links}

    # Verify physical sanity bounds
    for s in telemetry.node_telemetry:
        assert 0.0 <= s.cpu_percent <= 100.0
        assert 0.0 <= s.memory_percent <= 100.0
        assert 0.0 <= s.packet_loss_percent <= 100.0
        assert s.latency_ms >= 0.0
        assert s.throughput_mbps >= 0.0
        assert 0.0 <= s.interface_health <= 1.0
        assert s.error_count >= 0

    for l in telemetry.link_telemetry:
        assert l.latency_ms >= 0.0
        assert 0.0 <= l.packet_loss_percent <= 100.0
        assert l.throughput_mbps >= 0.0
        assert 0.0 <= l.utilization_percent <= 100.0
        assert l.capacity_mbps > 0.0
        assert l.link_status in ("up", "down")
        assert 0.0 <= l.interface_health <= 1.0


def test_enterprise_telemetry_determinism_and_seed_variation() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.simulation import generate_enterprise_telemetry

    nodes, links = generate_enterprise_topology()

    # Same seed -> identical output
    first = generate_enterprise_telemetry(nodes, links, duration_s=5, seed=77)
    second = generate_enterprise_telemetry(nodes, links, duration_s=5, seed=77)
    assert first.node_telemetry == second.node_telemetry
    assert first.link_telemetry == second.link_telemetry

    # Different seed -> bounded variation
    third = generate_enterprise_telemetry(nodes, links, duration_s=5, seed=99)
    assert first.node_telemetry != third.node_telemetry


def test_enterprise_telemetry_tier_and_host_profile_differences() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.simulation import generate_enterprise_telemetry

    nodes, links = generate_enterprise_topology()
    telemetry = generate_enterprise_telemetry(nodes, links, duration_s=20, seed=42)

    by_node: dict[str, list] = {}
    for s in telemetry.node_telemetry:
        by_node.setdefault(s.node_id, []).append(s)

    # 1. Edge vs Core latency: Edge should have higher latency (WAN/perimeter) than internal Core spine
    edge_lat = sum(s.latency_ms for s in by_node["edge-gw-01"]) / len(by_node["edge-gw-01"])
    core_lat = sum(s.latency_ms for s in by_node["core-sw-01"]) / len(by_node["core-sw-01"])
    assert edge_lat > 5.0
    assert core_lat < 2.0

    # 2. Host profile differentiation:
    # DB host should have higher memory utilization than DNS host
    db_mem = sum(s.memory_percent for s in by_node["host-db"]) / len(by_node["host-db"])
    dns_mem = sum(s.memory_percent for s in by_node["host-dns"]) / len(by_node["host-dns"])
    assert db_mem > 65.0
    assert dns_mem < 30.0

    # ERP host should have substantial CPU and memory
    erp_cpu = sum(s.cpu_percent for s in by_node["host-erp"]) / len(by_node["host-erp"])
    erp_mem = sum(s.memory_percent for s in by_node["host-erp"]) / len(by_node["host-erp"])
    assert erp_cpu > 40.0
    assert erp_mem > 55.0


def test_enterprise_telemetry_fault_scenarios_and_transitions() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.simulation import EnterpriseFaultScenario, generate_enterprise_telemetry

    nodes, links = generate_enterprise_topology()

    # Inject CPU saturation on host-api from t=20 to t=40 (ramp 5s)
    scenario = EnterpriseFaultScenario(
        target_id="host-api",
        failure_type="cpu_saturation",
        start_s=20,
        end_s=40,
        severity=1.0,
        ramp_s=5,
    )
    telemetry = generate_enterprise_telemetry(
        nodes, links, duration_s=60, seed=42, scenarios=[scenario]
    )

    api_samples = [s for s in telemetry.node_telemetry if s.node_id == "host-api"]
    sample_by_t = {s.timestamp_s: s for s in api_samples}

    # NORMAL state (t=10): normal baseline CPU (~48%)
    assert sample_by_t[10].cpu_percent < 60.0

    # DEGRADING state (t=22): ramping up
    assert sample_by_t[22].cpu_percent > sample_by_t[10].cpu_percent

    # FAULT state (t=30): saturated peak
    assert sample_by_t[30].cpu_percent > 85.0

    # RECOVERY / POST-RECOVERY state (t=55): recovered back to normal
    assert sample_by_t[55].cpu_percent < 60.0


def test_enterprise_telemetry_node_and_link_down_scenarios() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.simulation import EnterpriseFaultScenario, generate_enterprise_telemetry

    nodes, links = generate_enterprise_topology()

    scenarios = [
        EnterpriseFaultScenario(
            target_id="acc-sw-hq-01",
            failure_type="node_down",
            start_s=15,
            end_s=35,
            severity=1.0,
            ramp_s=2,
        ),
        EnterpriseFaultScenario(
            target_id="edge-gw-01->core-sw-01",
            failure_type="link_down",
            start_s=15,
            end_s=35,
            severity=1.0,
            ramp_s=2,
        ),
    ]

    telemetry = generate_enterprise_telemetry(
        nodes, links, duration_s=50, seed=42, scenarios=scenarios
    )

    # Check node down at peak (t=25)
    sw_samples = {s.timestamp_s: s for s in telemetry.node_telemetry if s.node_id == "acc-sw-hq-01"}
    fault_node = sw_samples[25]
    assert fault_node.interface_health == 0.0
    assert fault_node.packet_loss_percent == 100.0
    assert fault_node.throughput_mbps == 0.0

    # Check link down at peak (t=25)
    link_samples = [
        l for l in telemetry.link_telemetry
        if l.source == "edge-gw-01" and l.target == "core-sw-01"
    ]
    link_by_t = {l.timestamp_s: l for l in link_samples}
    fault_link = link_by_t[25]
    assert fault_link.link_status == "down"
    assert fault_link.interface_health == 0.0
    assert fault_link.throughput_mbps == 0.0
    assert fault_link.packet_loss_percent == 100.0


def test_enterprise_online_twin_initialization_and_topology() -> None:
    from telecom_twin.online import OnlineTwin

    # Requirement 1 & 2: initialization succeeds and enterprise topology is loaded
    twin = OnlineTwin(mode="enterprise", duration_s=10)
    assert twin.mode == "enterprise"
    assert len(twin.nodes) == 22
    assert len(twin.links) == 44

    snapshot = twin.snapshot()
    assert snapshot["mode"] == "enterprise"
    assert snapshot["node_count"] == 22
    assert snapshot["link_count"] == 44
    assert snapshot["sync_timestamp_s"] == 0 or snapshot["sync_timestamp_s"] == -1


def test_enterprise_online_twin_telemetry_snapshot_and_state_matching() -> None:
    from telecom_twin.models import LinkTelemetrySample, TelemetrySample
    from telecom_twin.online import OnlineTwin

    twin = OnlineTwin(mode="enterprise", duration_s=10)

    sample_node = TelemetrySample(
        timestamp_s=5,
        node_id="core-sw-01",
        cpu_percent=33.5,
        latency_ms=0.9,
        packet_loss_percent=0.002,
        throughput_mbps=15000.0,
        memory_percent=31.0,
        interface_health=1.0,
        error_count=0,
    )
    sample_link = LinkTelemetrySample(
        timestamp_s=5,
        source="core-sw-01",
        target="core-sw-02",
        latency_ms=0.45,
        packet_loss_percent=0.001,
        throughput_mbps=8500.0,
        utilization_percent=21.25,
        capacity_mbps=40000.0,
        link_status="up",
        interface_health=1.0,
    )

    # Requirements 3, 4, 5, 6: snapshot updates twin state, nodes, links, and sync timestamp
    twin.apply_telemetry_snapshot([sample_node], [sample_link], timestamp_s=5)

    assert twin.sync_timestamp_s == 5
    assert twin.latest["core-sw-01"] == sample_node
    assert twin.latest_links[("core-sw-01", "core-sw-02")] == sample_link

    snapshot = twin.snapshot()
    node_state = next(n for n in snapshot["nodes"] if n["node_id"] == "core-sw-01")
    assert node_state["telemetry"]["cpu_percent"] == 33.5

    link_state = next(
        l for l in snapshot["links"]
        if l["source"] == "core-sw-01" and l["target"] == "core-sw-02"
    )
    assert link_state["telemetry"]["throughput_mbps"] == 8500.0


def test_enterprise_online_twin_staleness_and_sync_status() -> None:
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import OnlineTwin

    twin = OnlineTwin(mode="enterprise", duration_s=20)

    # Apply updates at different timestamps to test synchronized, stale, and missing
    # Twin current sync time will be t = 10
    sample_sync = TelemetrySample(10, "edge-gw-01", 30.0, 5.0, 0.0, 5000.0)      # staleness = 0s -> synchronized (<= 2s)
    sample_stale = TelemetrySample(6, "edge-gw-02", 30.0, 5.0, 0.0, 5000.0)      # staleness = 4s -> stale (2s < s <= 5s)
    sample_old = TelemetrySample(2, "core-sw-01", 30.0, 5.0, 0.0, 5000.0)        # staleness = 8s -> missing (> 5s)
    # core-sw-02 will not receive any update -> missing (inf)

    twin.apply_node_telemetry([sample_old], timestamp_s=2)
    twin.apply_node_telemetry([sample_stale], timestamp_s=6)
    twin.apply_node_telemetry([sample_sync], timestamp_s=10)

    # Requirements 7, 8, 9: staleness and sync statuses
    staleness = twin.get_node_staleness()
    assert staleness["edge-gw-01"] == 0.0
    assert staleness["edge-gw-02"] == 4.0
    assert staleness["core-sw-01"] == 8.0
    assert math.isinf(staleness["core-sw-02"])

    sync_status = twin.get_node_sync_status()
    assert sync_status["edge-gw-01"] == "synchronized"
    assert sync_status["edge-gw-02"] == "stale"
    assert sync_status["core-sw-01"] == "missing"
    assert sync_status["core-sw-02"] == "missing"


def test_enterprise_online_twin_consistency_score() -> None:
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import OnlineTwin

    # Requirement 10: Complete valid enterprise twin produces complete consistency score (1.0)
    twin = OnlineTwin(mode="enterprise", duration_s=5)
    perfect_score = twin.get_topology_consistency()
    assert perfect_score == 1.0

    # Requirement 11: Incomplete topology or unexpected unknown telemetry lowers consistency
    nodes, links = generate_enterprise_topology()
    # Missing half the nodes
    partial_nodes = nodes[:10]
    incomplete_twin = OnlineTwin(mode="enterprise", nodes=partial_nodes, links=links)
    lower_score = incomplete_twin.get_topology_consistency()
    assert lower_score < perfect_score

    # Unknown phantom node in telemetry lowers consistency
    phantom_sample = TelemetrySample(5, "phantom-switch-99", 50.0, 10.0, 0.0, 1000.0)
    twin.apply_node_telemetry(phantom_sample)
    penalized_score = twin.get_topology_consistency()
    assert penalized_score < perfect_score


def test_enterprise_online_twin_immutability_and_determinism() -> None:
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import OnlineTwin

    # Requirement 12: Applying telemetry does not mutate source objects
    original_sample = TelemetrySample(3, "host-erp", 50.0, 2.0, 0.0, 1000.0)
    twin = OnlineTwin(mode="enterprise", duration_s=10)
    twin.apply_node_telemetry(original_sample)
    assert original_sample.cpu_percent == 50.0
    assert original_sample.node_id == "host-erp"

    # Requirement 13: Deterministic inputs produce identical sync state
    twin_a = OnlineTwin(mode="enterprise", duration_s=10, seed=42)
    twin_b = OnlineTwin(mode="enterprise", duration_s=10, seed=42)

    twin_a.advance(5)
    twin_b.advance(5)

    assert twin_a.get_sync_state() == twin_b.get_sync_state()
    assert twin_a.get_node_staleness() == twin_b.get_node_staleness()
    assert twin_a.get_node_sync_status() == twin_b.get_node_sync_status()



