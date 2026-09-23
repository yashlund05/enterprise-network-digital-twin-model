"""Communication-strategy simulation for synthetic management telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from telecom_twin.models import TelemetrySample
from telecom_twin.simulation import alarms_for_sample


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    messages: int
    transferred_bytes: int
    first_detection_delay_s: float
    alarm_episode_recall: float
    mean_staleness_s: float
    p95_staleness_s: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _group_samples(samples: list[TelemetrySample]) -> dict[str, list[TelemetrySample]]:
    grouped: dict[str, list[TelemetrySample]] = {}
    for sample in samples:
        grouped.setdefault(sample.node_id, []).append(sample)
    return grouped


def _ground_truth_start(samples: list[TelemetrySample]) -> int:
    return min(sample.timestamp_s for sample in samples if alarms_for_sample(sample))


def _summarize_updates(
    samples: list[TelemetrySample], updates: dict[str, list[TelemetrySample]], strategy: str, bytes_per_update: int
) -> StrategyResult:
    truth_start = _ground_truth_start(samples)
    detected = [
        sample.timestamp_s
        for node_updates in updates.values()
        for sample in node_updates
        if alarms_for_sample(sample)
    ]
    staleness = []
    grouped = _group_samples(samples)
    for node_id, node_samples in grouped.items():
        update_times = {sample.timestamp_s for sample in updates[node_id]}
        last_update = 0
        for sample in node_samples:
            if sample.timestamp_s in update_times:
                last_update = sample.timestamp_s
            staleness.append(sample.timestamp_s - last_update)
    ordered = sorted(staleness)
    percentile_index = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    message_count = sum(len(rows) for rows in updates.values())
    return StrategyResult(
        strategy,
        message_count,
        message_count * bytes_per_update,
        float(min(detected) - truth_start) if detected else float("inf"),
        1.0 if detected else 0.0,
        sum(staleness) / len(staleness),
        float(ordered[percentile_index]),
    )


def simulate_fixed_polling(
    samples: list[TelemetrySample], *, polling_interval_s: int = 10
) -> StrategyResult:
    grouped = _group_samples(samples)
    updates = {
        node_id: [sample for sample in rows if sample.timestamp_s % polling_interval_s == 0]
        for node_id, rows in grouped.items()
    }
    return _summarize_updates(samples, updates, "fixed_polling_10s", 160)


def simulate_adaptive_delta(
    samples: list[TelemetrySample], *, heartbeat_s: int = 30
) -> StrategyResult:
    grouped = _group_samples(samples)
    updates: dict[str, list[TelemetrySample]] = {}
    for node_id, rows in grouped.items():
        node_updates = [rows[0]]
        previous = rows[0]
        for sample in rows[1:]:
            changed = (
                abs(sample.cpu_percent - previous.cpu_percent) >= 8.0
                or abs(sample.latency_ms - previous.latency_ms) >= 10.0
                or abs(sample.packet_loss_percent - previous.packet_loss_percent) >= 0.5
                or sample.timestamp_s - previous.timestamp_s >= heartbeat_s
            )
            if changed:
                node_updates.append(sample)
                previous = sample
        updates[node_id] = node_updates
    return _summarize_updates(samples, updates, "adaptive_delta_30s", 80)


def compare_protocols(samples: list[TelemetrySample]) -> list[dict]:
    fixed = simulate_fixed_polling(samples)
    adaptive = simulate_adaptive_delta(samples)
    return [fixed.to_dict(), adaptive.to_dict()]
