"""Synthetic telemetry, incident injection, and alarm generation."""

from __future__ import annotations

import math
import random

from telecom_twin.models import Alarm, NetworkNode, TelemetrySample

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
