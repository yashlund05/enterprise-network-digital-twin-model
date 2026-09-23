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
