import math
import random
from dataclasses import asdict, dataclass
from typing import NamedTuple

from telecom_twin.models import (
    Alarm,
    LinkTelemetrySample,
    NetworkLink,
    NetworkNode,
    TelemetrySample,
)

LATENCY_WARNING_MS = 80.0
LOSS_WARNING_PERCENT = 2.0


def generate_telemetry(
    nodes: list[NetworkNode],
    *,
    duration_s: int = 300,
    seed: int = 28,
    incident_node: str = "access-07",
    incident_start_s: int = 123,
    incident_end_s: int = 183,
) -> list[TelemetrySample]:
    """Generate reproducible metrics with one declared congestion incident."""
    randomizer = random.Random(seed)
    rows: list[TelemetrySample] = []
    role_latency = {"core": 4.0, "aggregation": 9.0, "access": 17.0}
    role_throughput = {"core": 42000.0, "aggregation": 7800.0, "access": 320.0}
    for timestamp in range(duration_s + 1):
        for node_index, node in enumerate(nodes):
            phase = timestamp / 24.0 + node_index * 0.37
            cpu = 34.0 + 8.0 * math.sin(phase) + randomizer.gauss(0.0, 1.1)
            latency = role_latency[node.role] + 1.8 * math.sin(phase / 1.7) + randomizer.gauss(0.0, 0.45)
            packet_loss = max(0.0, 0.08 + randomizer.gauss(0.0, 0.025))
            throughput = role_throughput[node.role] * (0.74 + 0.08 * math.sin(phase / 2.0))
            if node.node_id == incident_node and incident_start_s <= timestamp <= incident_end_s:
                elapsed = timestamp - incident_start_s
                ramp = min(1.0, elapsed / 6.0)
                cpu += 42.0 * ramp
                latency += 105.0 * ramp
                packet_loss += 4.8 * ramp
                throughput *= 1.0 - 0.42 * ramp
            rows.append(
                TelemetrySample(
                    timestamp,
                    node.node_id,
                    round(max(0.0, min(100.0, cpu)), 6),
                    round(max(0.0, latency), 6),
                    round(max(0.0, packet_loss), 6),
                    round(max(0.0, throughput), 6),
                )
            )
    return rows


def alarms_for_sample(sample: TelemetrySample) -> list[Alarm]:
    alarms = []
    if sample.latency_ms >= LATENCY_WARNING_MS:
        alarms.append(
            Alarm(
                sample.timestamp_s,
                sample.node_id,
                "major",
                "latency_ms",
                sample.latency_ms,
                LATENCY_WARNING_MS,
            )
        )
    if sample.packet_loss_percent >= LOSS_WARNING_PERCENT:
        alarms.append(
            Alarm(
                sample.timestamp_s,
                sample.node_id,
                "critical",
                "packet_loss_percent",
                sample.packet_loss_percent,
                LOSS_WARNING_PERCENT,
            )
        )
    return alarms


def generate_alarms(samples: list[TelemetrySample]) -> list[Alarm]:
    return [alarm for sample in samples for alarm in alarms_for_sample(sample)]


@dataclass(frozen=True)
class EnterpriseFaultScenario:
    target_id: str
    failure_type: str
    start_s: int = 100
    end_s: int = 180
    severity: float = 1.0
    ramp_s: int = 10
    target_type: str = "node"

    def to_dict(self) -> dict:
        return asdict(self)


class EnterpriseTelemetry(NamedTuple):
    node_telemetry: list[TelemetrySample]
    link_telemetry: list[LinkTelemetrySample]


ENTERPRISE_NODE_PROFILES = {
    "edge": {
        "cpu": 38.0,
        "memory": 42.0,
        "latency": 9.5,
        "loss": 0.04,
        "throughput_ratio": 0.35,
        "cpu_sigma": 1.2,
        "mem_sigma": 0.8,
        "lat_sigma": 0.6,
        "throughput_var": 0.16,
    },
    "core": {
        "cpu": 24.0,
        "memory": 28.0,
        "latency": 0.8,
        "loss": 0.004,
        "throughput_ratio": 0.45,
        "cpu_sigma": 0.8,
        "mem_sigma": 0.5,
        "lat_sigma": 0.08,
        "throughput_var": 0.06,
    },
    "distribution-campus": {
        "cpu": 30.0,
        "memory": 34.0,
        "latency": 2.2,
        "loss": 0.015,
        "throughput_ratio": 0.32,
        "cpu_sigma": 1.1,
        "mem_sigma": 0.7,
        "lat_sigma": 0.20,
        "throughput_var": 0.12,
    },
    "distribution-dc": {
        "cpu": 35.0,
        "memory": 38.0,
        "latency": 1.1,
        "loss": 0.008,
        "throughput_ratio": 0.50,
        "cpu_sigma": 1.0,
        "mem_sigma": 0.6,
        "lat_sigma": 0.10,
        "throughput_var": 0.08,
    },
    "access-campus": {
        "cpu": 26.0,
        "memory": 29.0,
        "latency": 3.4,
        "loss": 0.025,
        "throughput_ratio": 0.35,
        "cpu_sigma": 1.5,
        "mem_sigma": 0.9,
        "lat_sigma": 0.35,
        "throughput_var": 0.22,
    },
    "access-dc": {
        "cpu": 28.0,
        "memory": 32.0,
        "latency": 1.4,
        "loss": 0.010,
        "throughput_ratio": 0.42,
        "cpu_sigma": 1.2,
        "mem_sigma": 0.7,
        "lat_sigma": 0.15,
        "throughput_var": 0.10,
    },
    "host-erp": {
        "cpu": 55.0,
        "memory": 68.0,
        "latency": 1.8,
        "loss": 0.008,
        "throughput_ratio": 0.20,
        "cpu_sigma": 2.0,
        "mem_sigma": 1.2,
        "lat_sigma": 0.18,
        "throughput_var": 0.10,
    },
    "host-api": {
        "cpu": 48.0,
        "memory": 52.0,
        "latency": 1.5,
        "loss": 0.008,
        "throughput_ratio": 0.32,
        "cpu_sigma": 2.2,
        "mem_sigma": 1.0,
        "lat_sigma": 0.22,
        "throughput_var": 0.18,
    },
    "host-db": {
        "cpu": 56.0,
        "memory": 78.0,
        "latency": 1.1,
        "loss": 0.005,
        "throughput_ratio": 0.25,
        "cpu_sigma": 1.8,
        "mem_sigma": 1.5,
        "lat_sigma": 0.12,
        "throughput_var": 0.12,
    },
    "host-dns": {
        "cpu": 14.0,
        "memory": 20.0,
        "latency": 0.5,
        "loss": 0.004,
        "throughput_ratio": 0.22,
        "cpu_sigma": 0.7,
        "mem_sigma": 0.4,
        "lat_sigma": 0.06,
        "throughput_var": 0.08,
    },
    "host-auth": {
        "cpu": 22.0,
        "memory": 27.0,
        "latency": 0.8,
        "loss": 0.005,
        "throughput_ratio": 0.28,
        "cpu_sigma": 1.0,
        "mem_sigma": 0.5,
        "lat_sigma": 0.09,
        "throughput_var": 0.12,
    },
    "host-mon": {
        "cpu": 42.0,
        "memory": 48.0,
        "latency": 1.4,
        "loss": 0.008,
        "throughput_ratio": 0.48,
        "cpu_sigma": 1.6,
        "mem_sigma": 0.9,
        "lat_sigma": 0.14,
        "throughput_var": 0.08,
    },
}


def _get_node_profile(node: NetworkNode | None) -> dict[str, float]:
    if node is None:
        return ENTERPRISE_NODE_PROFILES["access-campus"]
    if node.node_id in ENTERPRISE_NODE_PROFILES:
        return ENTERPRISE_NODE_PROFILES[node.node_id]
    tier = node.tier or node.role
    if tier == "distribution":
        if "campus" in node.region or "campus" in node.node_id:
            return ENTERPRISE_NODE_PROFILES["distribution-campus"]
        return ENTERPRISE_NODE_PROFILES["distribution-dc"]
    if tier == "access":
        if "campus" in node.region or "hq" in node.node_id:
            return ENTERPRISE_NODE_PROFILES["access-campus"]
        return ENTERPRISE_NODE_PROFILES["access-dc"]
    if tier in ENTERPRISE_NODE_PROFILES:
        return ENTERPRISE_NODE_PROFILES[tier]
    if node.role in ENTERPRISE_NODE_PROFILES:
        return ENTERPRISE_NODE_PROFILES[node.role]
    return ENTERPRISE_NODE_PROFILES["access-campus"]


def _calculate_fault_factor(scenario: EnterpriseFaultScenario, timestamp: int) -> float:
    start = scenario.start_s
    end = scenario.end_s
    ramp = max(1, scenario.ramp_s)
    if timestamp < start:
        return 0.0
    if timestamp < start + ramp:
        return (timestamp - start) / ramp * scenario.severity
    if timestamp <= end:
        return 1.0 * scenario.severity
    if timestamp <= end + ramp:
        return max(0.0, (1.0 - (timestamp - end) / ramp)) * scenario.severity
    return 0.0


def _matches_link(target_id: str, source: str, target: str) -> bool:
    clean = target_id.replace(" ", "")
    variants = {
        f"{source}->{target}",
        f"{target}->{source}",
        f"{source}--{target}",
        f"{target}--{source}",
        f"{source}:{target}",
        f"{target}:{source}",
    }
    return clean in variants


def generate_enterprise_telemetry(
    nodes: list[NetworkNode],
    links: list[NetworkLink] | None = None,
    *,
    duration_s: int = 300,
    seed: int = 42,
    scenarios: list[EnterpriseFaultScenario] | EnterpriseFaultScenario | None = None,
) -> EnterpriseTelemetry | list[TelemetrySample]:
    """Generate realistic, deterministic enterprise telemetry for nodes and links.

    Supports tier-differentiated baseline behavior, application server workload
    profiles, and multi-state fault scenarios (normal -> degrading -> fault -> recovery).
    """
    randomizer = random.Random(seed)
    node_rows: list[TelemetrySample] = []
    link_rows: list[LinkTelemetrySample] = []

    scenario_list: list[EnterpriseFaultScenario] = []
    if scenarios is not None:
        if isinstance(scenarios, EnterpriseFaultScenario):
            scenario_list = [scenarios]
        else:
            scenario_list = list(scenarios)

    node_by_id = {node.node_id: node for node in nodes}

    for timestamp in range(duration_s + 1):
        # 1. Generate node telemetry
        for node_index, node in enumerate(nodes):
            profile = _get_node_profile(node)
            phase = timestamp / 20.0 + node_index * 0.42

            cpu = profile["cpu"] + 4.0 * math.sin(phase) + randomizer.gauss(0.0, profile["cpu_sigma"])
            mem = profile["memory"] + 2.0 * math.sin(phase / 1.5) + randomizer.gauss(0.0, profile["mem_sigma"])
            lat = profile["latency"] + 0.5 * math.sin(phase / 1.8) + randomizer.gauss(0.0, profile["lat_sigma"])
            loss = max(0.001, profile["loss"] + randomizer.gauss(0.0, profile["loss"] * 0.2))

            tp_ratio = profile["throughput_ratio"] * (1.0 + profile["throughput_var"] * math.sin(phase / 2.5))
            throughput = node.capacity_mbps * max(0.02, min(0.95, tp_ratio))
            interface_health = node.interface_health
            error_count = 0

            # Apply active scenarios targeting this node
            for sc in scenario_list:
                if sc.target_id == node.node_id:
                    factor = _calculate_fault_factor(sc, timestamp)
                    if factor > 0.0:
                        ftype = sc.failure_type.lower()
                        if "cpu" in ftype:
                            cpu += (98.0 - cpu) * factor
                            lat += 25.0 * factor
                        elif "memory" in ftype:
                            mem += (99.0 - mem) * factor
                            error_count += int(15 * factor)
                        elif "latency" in ftype:
                            lat += 85.0 * factor
                        elif "loss" in ftype:
                            loss += 8.5 * factor
                            throughput *= max(0.05, 1.0 - 0.6 * factor)
                        elif "bandwidth" in ftype or "throttle" in ftype:
                            throughput *= max(0.1, 1.0 - 0.75 * factor)
                            lat += 35.0 * factor
                        elif "down" in ftype:
                            if factor >= 0.8:
                                cpu = 0.0
                                mem = 0.0
                                loss = 100.0
                                throughput = 0.0
                                lat = 999.0
                                interface_health = 0.0
                                error_count += int(50 * factor)
                            else:
                                interface_health = max(0.0, 1.0 - factor)
                                loss += 100.0 * factor
                                throughput *= max(0.0, 1.0 - factor)
                                error_count += int(25 * factor)

            node_rows.append(
                TelemetrySample(
                    timestamp,
                    node.node_id,
                    round(max(0.0, min(100.0, cpu)), 4),
                    round(max(0.0, lat), 4),
                    round(max(0.0, min(100.0, loss)), 4),
                    round(max(0.0, throughput), 4),
                    memory_percent=round(max(0.0, min(100.0, mem)), 4),
                    interface_health=round(max(0.0, min(1.0, interface_health)), 4),
                    error_count=max(0, error_count),
                )
            )

        # 2. Generate link telemetry if links are provided
        if links is not None:
            for link_index, link in enumerate(links):
                src_node = node_by_id.get(link.source)
                tgt_node = node_by_id.get(link.target)
                src_prof = _get_node_profile(src_node)
                tgt_prof = _get_node_profile(tgt_node)

                phase = timestamp / 20.0 + link_index * 0.31
                link_cap = link.capacity_mbps
                base_lat = link.base_latency_ms + 0.15 * math.sin(phase / 1.6) + randomizer.gauss(0.0, 0.05)
                base_loss = max(0.001, (src_prof["loss"] + tgt_prof["loss"]) / 2.0 + randomizer.gauss(0.0, 0.002))

                avg_ratio = (src_prof["throughput_ratio"] + tgt_prof["throughput_ratio"]) / 2.0
                link_tp = link_cap * avg_ratio * (0.85 + 0.12 * math.sin(phase / 2.2))
                link_status = "up"
                link_health = link.interface_health

                # Apply active scenarios targeting this link
                for sc in scenario_list:
                    if _matches_link(sc.target_id, link.source, link.target):
                        factor = _calculate_fault_factor(sc, timestamp)
                        if factor > 0.0:
                            ftype = sc.failure_type.lower()
                            if "latency" in ftype:
                                base_lat += 65.0 * factor
                            elif "loss" in ftype:
                                base_loss += 12.0 * factor
                                link_tp *= max(0.05, 1.0 - 0.7 * factor)
                            elif "bandwidth" in ftype or "throttle" in ftype:
                                eff_cap = link_cap * max(0.1, 1.0 - 0.8 * factor)
                                link_tp = min(link_tp, eff_cap)
                                base_lat += 20.0 * factor
                            elif "down" in ftype:
                                if factor >= 0.8:
                                    link_status = "down"
                                    link_health = 0.0
                                    link_tp = 0.0
                                    base_loss = 100.0
                                    base_lat = 999.0
                                else:
                                    link_health = max(0.0, 1.0 - factor)
                                    base_loss += 100.0 * factor
                                    link_tp *= max(0.0, 1.0 - factor)

                link_util = (link_tp / max(1.0, link_cap)) * 100.0

                link_rows.append(
                    LinkTelemetrySample(
                        timestamp,
                        link.source,
                        link.target,
                        round(max(0.0, base_lat), 4),
                        round(max(0.0, min(100.0, base_loss)), 4),
                        round(max(0.0, link_tp), 4),
                        round(max(0.0, min(100.0, link_util)), 4),
                        capacity_mbps=round(max(0.0, link_cap), 4),
                        link_status=link_status,
                        interface_health=round(max(0.0, min(1.0, link_health)), 4),
                    )
                )

    if links is None:
        return node_rows
    return EnterpriseTelemetry(node_telemetry=node_rows, link_telemetry=link_rows)

