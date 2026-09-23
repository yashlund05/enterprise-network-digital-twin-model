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

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NetworkLink:
    source: str
    target: str
    capacity_mbps: float
    base_latency_ms: float

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
