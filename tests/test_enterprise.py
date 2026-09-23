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


# ==============================================================================
# Phase 4B: Enterprise Anomaly Detection Unit Tests
# ==============================================================================


def test_enterprise_anomaly_detector_initialization() -> None:
    """Requirement 1: Enterprise detector initializes correctly."""
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise")
    assert det.mode == "enterprise"
    assert det.threshold == 3.0
    assert det.window_size == 60
    assert det.warmup == 30

    custom_det = RollingAnomalyDetector(mode="enterprise", window_size=50, warmup=20, threshold=4.0)
    assert custom_det.mode == "enterprise"
    assert custom_det.threshold == 4.0
    assert custom_det.window_size == 50
    assert custom_det.warmup == 20

    # Validation errors
    with pytest.raises(ValueError):
        RollingAnomalyDetector(mode="enterprise", window_size=10, warmup=15)
    with pytest.raises(ValueError):
        RollingAnomalyDetector(mode="enterprise", threshold=-1.0)


def test_enterprise_anomaly_detector_warmup() -> None:
    """Requirement 2: Warm-up period behaves sensibly (returns None during warmup)."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node_id = "core-sw-01"

    # First 30 observations (t=0..29) must return None as baseline history builds up
    for t in range(30):
        sample = TelemetrySample(t, node_id, 25.0, 2.0, 0.01, 1000.0)
        event = det.observe(sample)
        assert event is None

    # 31st observation (t=30) has len(history) == 30 >= warmup; now evaluated
    sample_31 = TelemetrySample(30, node_id, 25.0, 2.0, 0.01, 1000.0)
    evaluated = det.evaluate_sample(sample_31)
    assert evaluated is not None
    assert evaluated.severity == "NORMAL"


def test_enterprise_anomaly_detector_normal_baseline() -> None:
    """Requirement 3: Normal enterprise baseline does not continuously trigger critical anomalies."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node_id = "dist-sw-dc-01"

    # Normal operational samples with realistic slight jitter
    anomalies = []
    for t in range(80):
        jitter = (t % 5 - 2) * 0.02
        sample = TelemetrySample(t, node_id, 30.0 + jitter * 2, 2.5 + jitter, 0.02 + abs(jitter) * 0.01, 500.0)
        event = det.observe(sample)
        if event is not None:
            anomalies.append(event)

    # In steady-state normal operation, no spurious critical anomalies
    assert len(anomalies) == 0


def test_enterprise_anomaly_detector_single_metric_latency_fault() -> None:
    """Requirement 4: A latency-only fault produces elevated latency evidence."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "host-erp"

    # Establish baseline
    for t in range(35):
        jitter = (t % 3) * 0.05
        det.observe(TelemetrySample(t, node, 20.0, 2.0 + jitter, 0.01, 1000.0))

    # Inject sharp latency spike
    spike_sample = TelemetrySample(35, node, 20.0, 25.0, 0.01, 1000.0)
    event = det.observe(spike_sample)

    assert event is not None
    assert event.node_id == node
    assert event.latency_z >= 3.0
    assert "latency anomaly" in event.evidence
    assert "packet loss anomaly" not in event.evidence
    assert "cpu anomaly" not in event.evidence
    assert event.metric == "latency_ms"


def test_enterprise_anomaly_detector_single_metric_loss_fault() -> None:
    """Requirement 5: A packet-loss fault produces elevated loss evidence."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "edge-gw-01"

    # Establish baseline
    for t in range(35):
        det.observe(TelemetrySample(t, node, 25.0, 3.0, 0.02 + (t % 2) * 0.01, 800.0))

    # Inject packet loss fault
    loss_sample = TelemetrySample(35, node, 25.0, 3.0, 12.0, 800.0)
    event = det.observe(loss_sample)

    assert event is not None
    assert event.node_id == node
    assert event.loss_z >= 3.0
    assert "packet loss anomaly" in event.evidence
    assert "latency anomaly" not in event.evidence
    assert "cpu anomaly" not in event.evidence
    assert event.metric == "packet_loss_percent"


def test_enterprise_anomaly_detector_single_metric_cpu_fault() -> None:
    """Requirement 6: A CPU-saturation fault produces elevated CPU evidence."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "host-db"

    # Establish baseline
    for t in range(35):
        det.observe(TelemetrySample(t, node, 30.0 + (t % 3) * 0.5, 2.0, 0.01, 1000.0))

    # Inject CPU saturation fault
    cpu_sample = TelemetrySample(35, node, 98.0, 2.0, 0.01, 1000.0)
    event = det.observe(cpu_sample)

    assert event is not None
    assert event.node_id == node
    assert event.cpu_z >= 3.0
    assert "cpu anomaly" in event.evidence
    assert "latency anomaly" not in event.evidence
    assert "packet loss anomaly" not in event.evidence
    assert event.metric == "cpu_percent"


def test_enterprise_anomaly_detector_multi_metric_vs_single_metric() -> None:
    """Requirement 7: Multi-metric fault produces higher composite score than single-metric fault."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det_single = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    det_multi = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "dist-sw-dc-01"

    # Establish identical baselines
    for t in range(35):
        jitter = (t % 3) * 0.05
        sample = TelemetrySample(t, node, 25.0 + jitter, 2.0 + jitter, 0.01 + jitter * 0.01, 1000.0)
        det_single.observe(sample)
        det_multi.observe(sample)

    # In det_single, inject only latency fault
    single_sample = TelemetrySample(35, node, 25.0, 20.0, 0.01, 1000.0)
    single_event = det_single.observe(single_sample)

    # In det_multi, inject combined latency + loss + cpu fault
    multi_sample = TelemetrySample(35, node, 92.0, 20.0, 8.0, 1000.0)
    multi_event = det_multi.observe(multi_sample)

    assert single_event is not None
    assert multi_event is not None
    assert multi_event.composite_z > single_event.composite_z
    assert len(multi_event.evidence) > len(single_event.evidence)
    assert "latency anomaly" in multi_event.evidence
    assert "packet loss anomaly" in multi_event.evidence
    assert "cpu anomaly" in multi_event.evidence


def test_enterprise_anomaly_detector_severity_boundaries() -> None:
    """Requirement 8: Severity boundaries work exactly (below 3 -> normal, 3.0 -> info, 4.0 -> warning, 5.0 -> critical)."""
    from telecom_twin.online import RollingAnomalyDetector

    # below 3 -> NORMAL
    assert RollingAnomalyDetector.severity_for_score(0.0) == "NORMAL"
    assert RollingAnomalyDetector.severity_for_score(1.5) == "NORMAL"
    assert RollingAnomalyDetector.severity_for_score(2.9999) == "NORMAL"

    # 3.0 <= Z < 4.0 -> INFO
    assert RollingAnomalyDetector.severity_for_score(3.0) == "INFO"
    assert RollingAnomalyDetector.severity_for_score(3.5) == "INFO"
    assert RollingAnomalyDetector.severity_for_score(3.9999) == "INFO"

    # 4.0 <= Z < 5.0 -> WARNING
    assert RollingAnomalyDetector.severity_for_score(4.0) == "WARNING"
    assert RollingAnomalyDetector.severity_for_score(4.5) == "WARNING"
    assert RollingAnomalyDetector.severity_for_score(4.9999) == "WARNING"

    # Z >= 5.0 -> CRITICAL
    assert RollingAnomalyDetector.severity_for_score(5.0) == "CRITICAL"
    assert RollingAnomalyDetector.severity_for_score(7.2) == "CRITICAL"
    assert RollingAnomalyDetector.severity_for_score(50.0) == "CRITICAL"


def test_enterprise_anomaly_detector_temporal_recovery() -> None:
    """Requirement 9: Recovery telemetry causes anomaly state to return toward normal."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "host-api"

    # Baseline: 35 samples
    for t in range(35):
        det.observe(TelemetrySample(t, node, 20.0, 2.0, 0.01, 1000.0))

    # Injected fault at t=35..39
    fault_events = []
    for t in range(35, 40):
        ev = det.observe(TelemetrySample(t, node, 90.0, 30.0, 10.0, 1000.0))
        if ev is not None:
            fault_events.append(ev)
    assert len(fault_events) > 0

    # At t=40, metrics recover back to baseline
    recovered_sample = TelemetrySample(40, node, 20.0, 2.0, 0.01, 1000.0)
    recovery_event = det.observe(recovered_sample)
    # The detector immediately transitions out of anomalous state
    assert recovery_event is None

    evaluated = det.evaluate_sample(recovered_sample)
    assert evaluated is not None
    assert evaluated.severity == "NORMAL"
    assert evaluated.composite_z == 0.0


def test_enterprise_anomaly_detector_zero_variance_and_numerical_safety() -> None:
    """Requirement 10: Zero-variance and extreme inputs produce no NaN, Inf, or ZeroDivisionError."""
    import math

    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "static-device"

    # Constant metrics with zero variance
    for t in range(35):
        sample = TelemetrySample(t, node, 10.0, 1.0, 0.0, 100.0)
        det.observe(sample)

    # Same constant metric
    safe_sample = TelemetrySample(35, node, 10.0, 1.0, 0.0, 100.0)
    evaluated = det.evaluate_sample(safe_sample)
    assert evaluated is not None
    assert evaluated.composite_z == 0.0
    assert not math.isnan(evaluated.composite_z)
    assert not math.isinf(evaluated.composite_z)

    # Static helper handles NaN, Inf, and empty cleanly
    assert RollingAnomalyDetector._z(float("nan"), [1.0, 2.0, 3.0]) == 0.0
    assert RollingAnomalyDetector._z(float("inf"), [1.0, 2.0, 3.0]) == 0.0
    assert RollingAnomalyDetector._z(5.0, []) == 0.0
    assert RollingAnomalyDetector._z(5.0, [float("nan"), float("inf")]) == 0.0


def test_enterprise_anomaly_detector_determinism() -> None:
    """Requirement 11: Same input sequence gives identical anomaly outputs."""
    from telecom_twin.models import TelemetrySample
    from telecom_twin.online import RollingAnomalyDetector

    det_1 = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    det_2 = RollingAnomalyDetector(mode="enterprise", warmup=30, window_size=60)
    node = "core-sw-02"

    events_1 = []
    events_2 = []
    for t in range(60):
        val = 2.0 if t < 35 else 25.0
        s1 = TelemetrySample(t, node, 20.0, val, 0.01, 1000.0)
        s2 = TelemetrySample(t, node, 20.0, val, 0.01, 1000.0)
        e1 = det_1.observe(s1)
        e2 = det_2.observe(s2)
        if e1 is not None:
            events_1.append(e1)
        if e2 is not None:
            events_2.append(e2)

    assert events_1 == events_2
    assert len(events_1) > 0


def test_enterprise_online_twin_detector_integration() -> None:
    """OnlineTwin enterprise mode integrates RollingAnomalyDetector with enterprise features."""
    from telecom_twin.online import OnlineTwin

    twin = OnlineTwin(mode="enterprise", duration_s=150, seed=42)
    assert twin.detector.mode == "enterprise"
    assert twin.detector.threshold == 3.0

    # Advance through simulation
    twin.advance(100)
    assert twin.timestamp_s == 99

    # Verify event structure when anomalies occur
    for ev in twin.events:
        assert hasattr(ev, "composite_z")
        assert hasattr(ev, "severity")
        assert hasattr(ev, "evidence")
        assert ev.severity in ("INFO", "WARNING", "CRITICAL")
        assert isinstance(ev.evidence, tuple)


# ==============================================================================
# Phase 5A & 5B: Enterprise Service Catalog & Impact Analysis Unit Tests
# ==============================================================================


def test_enterprise_service_catalog_all_six_services() -> None:
    """Requirement 1: All six required enterprise services exist with correct metadata."""
    from telecom_twin.services import EnterpriseServiceCatalog, build_default_service_catalog

    catalog = EnterpriseServiceCatalog()
    services = catalog.get_all_services()
    assert len(services) == 6

    expected_ids = {
        "srv-dns",
        "srv-auth",
        "srv-db",
        "srv-api",
        "srv-erp",
        "srv-monitoring",
    }
    actual_ids = {s.service_id for s in services}
    assert actual_ids == expected_ids

    # Check names
    service_map = {s.service_id: s for s in services}
    assert service_map["srv-dns"].name == "Enterprise DNS"
    assert service_map["srv-auth"].name == "Enterprise Authentication / SSO"
    assert service_map["srv-db"].name == "Enterprise PostgreSQL Database"
    assert service_map["srv-api"].name == "Internal API Gateway"
    assert service_map["srv-erp"].name == "Enterprise ERP"
    assert service_map["srv-monitoring"].name == "Network & System Monitoring"

    # Default function works identically
    raw_services, raw_deps = build_default_service_catalog()
    assert len(raw_services) == 6
    assert len(raw_deps) == 7


def test_enterprise_service_catalog_unique_ids() -> None:
    """Requirement 2: Service IDs and names are unique."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()
    services = catalog.get_all_services()

    ids = [s.service_id for s in services]
    assert len(ids) == len(set(ids))

    names = [s.name for s in services]
    assert len(names) == len(set(names))


def test_enterprise_service_catalog_host_node_mapping() -> None:
    """Requirement 3: Host-node IDs map to actual enterprise topology nodes."""
    from telecom_twin.enterprise_topology import HOST_NODE_IDS
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()
    for service in catalog.get_all_services():
        assert service.host_node_id in HOST_NODE_IDS

    # Specific canonical mappings
    assert catalog.get_service("srv-dns").host_node_id == "host-dns"
    assert catalog.get_service("srv-auth").host_node_id == "host-auth"
    assert catalog.get_service("srv-db").host_node_id == "host-db"
    assert catalog.get_service("srv-api").host_node_id == "host-api"
    assert catalog.get_service("srv-erp").host_node_id == "host-erp"
    assert catalog.get_service("srv-monitoring").host_node_id == "host-mon"


def test_enterprise_service_catalog_dependency_validation() -> None:
    """Requirement 4: Dependency references are validated against registered services."""
    from telecom_twin.models import EnterpriseService, ServiceDependency
    from telecom_twin.services import EnterpriseServiceCatalog

    # Valid catalog passes
    catalog = EnterpriseServiceCatalog()
    catalog.validate_dependencies()

    # Invalid consumer
    bad_dep_1 = ServiceDependency("unknown-consumer", "srv-dns", "sync")
    with pytest.raises(ValueError, match="unknown consumer"):
        EnterpriseServiceCatalog(dependencies=[bad_dep_1])

    # Invalid provider
    s1 = EnterpriseService("s1", "S1", "tier-1", "host-dns", 80, "tier-1", "healthy")
    bad_dep_2 = ServiceDependency("s1", "unknown-provider", "sync")
    with pytest.raises(ValueError, match="unknown provider"):
        EnterpriseServiceCatalog(services=[s1], dependencies=[bad_dep_2])


def test_enterprise_service_catalog_dependency_direction() -> None:
    """Requirement 5: Dependency direction is strictly consumer -> provider."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()
    graph = catalog.graph

    # srv-api -> srv-auth
    assert graph.has_edge("srv-api", "srv-auth")
    assert not graph.has_edge("srv-auth", "srv-api")

    # srv-api -> srv-db
    assert graph.has_edge("srv-api", "srv-db")
    assert not graph.has_edge("srv-db", "srv-api")

    # srv-erp -> srv-api, srv-db, srv-auth
    assert graph.has_edge("srv-erp", "srv-api")
    assert graph.has_edge("srv-erp", "srv-db")
    assert graph.has_edge("srv-erp", "srv-auth")

    # srv-auth -> srv-dns, srv-db -> srv-dns
    assert graph.has_edge("srv-auth", "srv-dns")
    assert graph.has_edge("srv-db", "srv-dns")
    assert not graph.has_edge("srv-dns", "srv-auth")
    assert not graph.has_edge("srv-dns", "srv-db")


def test_enterprise_service_catalog_is_acyclic() -> None:
    """Requirement 6: The dependency graph is acyclic."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()
    assert catalog.is_acyclic() is True
    assert catalog.detect_cycles() == []


def test_enterprise_service_catalog_direct_dependency_traversal() -> None:
    """Requirement 7: Direct dependency traversal works accurately."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()

    # Direct dependencies of consumer
    assert catalog.get_direct_dependencies("srv-api") == ["srv-auth", "srv-db"]
    assert catalog.get_direct_dependencies("srv-erp") == ["srv-api", "srv-auth", "srv-db"]
    assert catalog.get_direct_dependencies("srv-auth") == ["srv-dns"]
    assert catalog.get_direct_dependencies("srv-db") == ["srv-dns"]
    assert catalog.get_direct_dependencies("srv-dns") == []
    assert catalog.get_direct_dependencies("srv-monitoring") == []

    # Direct consumers of provider
    assert catalog.get_direct_consumers("srv-dns") == ["srv-auth", "srv-db"]
    assert catalog.get_direct_consumers("srv-api") == ["srv-erp"]
    assert catalog.get_direct_consumers("srv-erp") == []


def test_enterprise_service_catalog_transitive_dependency_traversal() -> None:
    """Requirement 8: Transitive dependency traversal works accurately."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog = EnterpriseServiceCatalog()

    # ERP transitively depends on API, DB, Auth, and DNS
    erp_deps = catalog.get_transitive_dependencies("srv-erp")
    assert erp_deps == {"srv-api", "srv-auth", "srv-db", "srv-dns"}

    # Consumers that depend on DNS (all 4 core services depend on DNS!)
    dns_consumers = catalog.get_transitive_consumers("srv-dns")
    assert dns_consumers == {"srv-auth", "srv-db", "srv-api", "srv-erp"}

    # Consumers that depend on API
    api_consumers = catalog.get_transitive_consumers("srv-api")
    assert api_consumers == {"srv-erp"}

    # Monitoring has no consumers and no dependencies
    assert catalog.get_transitive_consumers("srv-monitoring") == set()
    assert catalog.get_transitive_dependencies("srv-monitoring") == set()


def test_enterprise_infrastructure_valid_paths_to_service_hosts() -> None:
    """Requirement 9: Valid paths exist from enterprise network into service hosts."""
    from telecom_twin.impact import ServiceImpactAnalyzer

    analyzer = ServiceImpactAnalyzer()
    for service in analyzer.catalog.get_all_services():
        paths = analyzer.get_service_paths(service.service_id)
        assert len(paths) > 0
        for path in paths:
            # Each path must start at an ingress node and end at the service host
            assert path[0] in analyzer._ingress_nodes
            assert path[-1] == service.host_node_id
            assert len(path) >= 4  # ingress -> dist -> access -> host


def test_enterprise_infrastructure_service_host_mapping_determinism() -> None:
    """Requirement 10: Service host mapping is deterministic."""
    from telecom_twin.services import EnterpriseServiceCatalog

    catalog_1 = EnterpriseServiceCatalog()
    catalog_2 = EnterpriseServiceCatalog()

    for host in ("host-erp", "host-api", "host-db", "host-dns", "host-auth", "host-mon"):
        res_1 = catalog_1.get_services_by_host(host)
        res_2 = catalog_2.get_services_by_host(host)
        assert res_1 == res_2
        assert len(res_1) == 1


def test_enterprise_infrastructure_path_redundancy() -> None:
    """Requirement 11: Path calculation handles redundant connectivity correctly."""
    from telecom_twin.impact import ServiceImpactAnalyzer

    analyzer = ServiceImpactAnalyzer()
    erp_paths = analyzer.get_service_paths("srv-erp")

    # There should be multiple shortest paths from campus access switches and edge gateways to host-erp
    assert len(erp_paths) >= 6
    spine_switches_used = {
        node for path in erp_paths for node in path if node.startswith("core-sw-")
    }
    # Both core spines should be utilized across redundant paths
    assert "core-sw-01" in spine_switches_used
    assert "core-sw-02" in spine_switches_used


def test_enterprise_service_impact_dns_failure_propagation() -> None:
    """Requirement 12: DNS failure propagates to Auth/DB/API/ERP as expected."""
    from telecom_twin.impact import analyze_service_impact

    # Fail host-dns
    report = analyze_service_impact(failed_nodes=["host-dns"])

    # Directly impacted: srv-dns
    assert "srv-dns" in report.directly_impacted_services

    # Transitively impacted: srv-auth, srv-db, srv-api, srv-erp
    expected_transitive = {"srv-auth", "srv-db", "srv-api", "srv-erp"}
    assert set(report.transitively_impacted_services) == expected_transitive

    # Monitoring is unaffected
    assert report.service_statuses["srv-monitoring"] == "healthy"

    # All 5 affected services are unavailable
    for s_id in ("srv-dns", "srv-auth", "srv-db", "srv-api", "srv-erp"):
        assert report.service_statuses[s_id] == "unavailable"


def test_enterprise_service_impact_api_failure_propagation() -> None:
    """Requirement 13: API failure impacts ERP but does not falsely impact DNS."""
    from telecom_twin.impact import analyze_service_impact

    report = analyze_service_impact(failed_nodes=["host-api"])

    # Direct: srv-api
    assert report.directly_impacted_services == ("srv-api",)

    # Transitive: srv-erp
    assert report.transitively_impacted_services == ("srv-erp",)

    # Provider dependencies of API (DNS, DB, Auth) must NOT be impacted
    assert report.service_statuses["srv-dns"] == "healthy"
    assert report.service_statuses["srv-auth"] == "healthy"
    assert report.service_statuses["srv-db"] == "healthy"
    assert report.service_statuses["srv-monitoring"] == "healthy"


def test_enterprise_service_impact_redundant_core_failure() -> None:
    """Requirement 14: A single redundant core failure does not automatically make services unavailable."""
    from telecom_twin.impact import analyze_service_impact

    # Fail only core-sw-01 (core-sw-02 remains online)
    report = analyze_service_impact(failed_nodes=["core-sw-01"])

    assert report.directly_affected_nodes == ("core-sw-01",)
    assert len(report.affected_paths) > 0

    # No service should be marked unavailable because alternate path through core-sw-02 exists!
    for s_id, status in report.service_statuses.items():
        assert status != "unavailable", f"Service {s_id} falsely declared unavailable despite core redundancy"
        assert status in ("healthy", "degraded")

    # Severity should be warning (degraded redundancy), not critical
    assert report.overall_severity == "warning"


def test_enterprise_service_impact_host_failure_marks_unavailable() -> None:
    """Requirement 15: A true service-host failure marks the corresponding service unavailable."""
    from telecom_twin.impact import analyze_service_impact

    report = analyze_service_impact(failed_nodes=["host-erp"])

    assert "srv-erp" in report.directly_impacted_services
    assert report.service_statuses["srv-erp"] == "unavailable"
    assert report.overall_severity == "critical"


def test_enterprise_service_impact_direct_vs_transitive_distinction() -> None:
    """Requirement 16: Direct and transitive impact are distinguished correctly."""
    from telecom_twin.impact import analyze_service_impact

    report = analyze_service_impact(failed_nodes=["host-auth"])

    # Directly impacted: srv-auth
    assert report.directly_impacted_services == ("srv-auth",)

    # Transitively impacted: API and ERP
    assert set(report.transitively_impacted_services) == {"srv-api", "srv-erp"}

    # Sets must be disjoint
    direct_set = set(report.directly_impacted_services)
    transitive_set = set(report.transitively_impacted_services)
    assert len(direct_set & transitive_set) == 0


def test_enterprise_service_impact_blast_radius_calculation() -> None:
    """Requirement 17: Blast Radius Index is calculated correctly as ratio [0, 1] and percent."""
    from telecom_twin.impact import analyze_service_impact

    # Baseline with no failures
    normal_report = analyze_service_impact()
    assert normal_report.blast_radius_index == 0.0
    assert normal_report.blast_radius_percent == 0.0
    assert normal_report.overall_severity == "normal"

    # DNS failure impacts 5 out of 6 services (weights: 5 * 3.0 = 15.0; total: 5 * 3.0 + 2.0 = 17.0)
    dns_report = analyze_service_impact(failed_nodes=["host-dns"])
    expected_bri = round(15.0 / 17.0, 4)  # ~0.8824
    assert dns_report.blast_radius_index == expected_bri
    assert dns_report.blast_radius_percent == round(expected_bri * 100.0, 2)

    # API failure impacts API and ERP (weights: 3.0 + 3.0 = 6.0; total = 17.0)
    api_report = analyze_service_impact(failed_nodes=["host-api"])
    expected_api_bri = round(6.0 / 17.0, 4)  # ~0.3529
    assert api_report.blast_radius_index == expected_api_bri
    assert api_report.blast_radius_percent == round(expected_api_bri * 100.0, 2)


def test_enterprise_service_impact_criticality_weights() -> None:
    """Requirement 18: Service criticality weights affect BRI correctly."""
    from telecom_twin.impact import analyze_service_impact

    custom_weights = {"tier-1": 10.0, "tier-2": 1.0, "tier-3": 1.0}
    # DNS failure with custom weights: 5 * 10.0 = 50.0; total = 50.0 + 1.0 = 51.0
    report = analyze_service_impact(
        failed_nodes=["host-dns"], criticality_weights=custom_weights
    )
    expected_bri = round(50.0 / 51.0, 4)  # ~0.9804
    assert report.blast_radius_index == expected_bri


def test_enterprise_service_impact_determinism() -> None:
    """Requirement 19: Same topology + same failures gives identical impact output."""
    from telecom_twin.impact import analyze_service_impact

    report_a = analyze_service_impact(failed_nodes=["dist-sw-dc-01"], failed_links=[("edge-gw-01", "core-sw-01")])
    report_b = analyze_service_impact(failed_nodes=["dist-sw-dc-01"], failed_links=[("edge-gw-01", "core-sw-01")])

    assert report_a == report_b
    assert report_a.to_dict() == report_b.to_dict()

    what_if = report_a.to_what_if_result()
    assert what_if.blast_radius_percent == report_a.blast_radius_percent
    assert what_if.severity == report_a.overall_severity


def test_enterprise_service_impact_immutability() -> None:
    """Requirement 20: Input topology and dependency graph are not mutated."""
    from telecom_twin.enterprise_topology import generate_enterprise_topology
    from telecom_twin.impact import ServiceImpactAnalyzer
    from telecom_twin.services import EnterpriseServiceCatalog

    nodes, links = generate_enterprise_topology()
    catalog = EnterpriseServiceCatalog()

    orig_node_count = len(nodes)
    orig_link_count = len(links)
    orig_service_count = len(catalog.get_all_services())
    orig_dep_graph_nodes = len(catalog.graph.nodes())

    analyzer = ServiceImpactAnalyzer(nodes=nodes, links=links, catalog=catalog)
    analyzer.analyze(failed_nodes=["core-sw-01", "host-erp"], failed_links=[("edge-gw-01", "core-sw-01")])

    assert len(nodes) == orig_node_count
    assert len(links) == orig_link_count
    assert len(catalog.get_all_services()) == orig_service_count
    assert len(catalog.graph.nodes()) == orig_dep_graph_nodes





