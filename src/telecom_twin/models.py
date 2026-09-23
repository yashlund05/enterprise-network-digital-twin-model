"""Domain records shared by topology, telemetry, alarms, and API layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class NetworkNode:
    node_id: str
    role: str
    region: str
    x: float
    y: float
    capacity_mbps: float
    tier: str | None = None
    memory_percent: float = 0.0
    interface_health: float = 1.0
    vlan_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NetworkLink:
    source: str
    target: str
    capacity_mbps: float
    base_latency_ms: float
    interface_health: float = 1.0
    vlan_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TelemetrySample:
    timestamp_s: int
    node_id: str
    cpu_percent: float
    latency_ms: float
    packet_loss_percent: float
    throughput_mbps: float
    memory_percent: float = 0.0
    interface_health: float = 1.0
    error_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LinkTelemetrySample:
    timestamp_s: int
    source: str
    target: str
    latency_ms: float
    packet_loss_percent: float
    throughput_mbps: float
    utilization_percent: float
    capacity_mbps: float
    link_status: str = "up"
    interface_health: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Alarm:
    timestamp_s: int
    node_id: str
    severity: str
    metric: str
    observed_value: float
    threshold: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EnterpriseService:
    service_id: str
    name: str
    tier: str
    host_node_id: str
    port: int
    criticality: str
    health_status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ServiceDependency:
    consumer_service_id: str
    provider_service_id: str
    dependency_type: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WhatIfScenario:
    scenario_id: str
    name: str
    target_type: str
    target_id: str
    failure_type: str
    parameter_value: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WhatIfResult:
    predicted_affected_nodes: tuple[str, ...]
    predicted_affected_links: tuple[str, ...]
    predicted_affected_services: tuple[str, ...]
    latency_delta_ms: float
    loss_delta_percent: float
    throughput_delta_mbps: float
    blast_radius_percent: float
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class IncidentTimelineEvent:
    timestamp_s: int
    stage: str
    description: str
    active_alarms: int | tuple[str, ...]
    root_cause_id: str | None
    affected_services: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TwinSyncState:
    sync_timestamp_s: int
    telemetry_staleness_s: float
    consistency_score: float
    node_sync_status: str | dict[str, str] = "synchronized"

    def to_dict(self) -> dict:
        return asdict(self)
