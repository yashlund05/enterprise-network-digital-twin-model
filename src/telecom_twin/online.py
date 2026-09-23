"""Deterministic online replay, rolling anomaly detection, and evaluation."""

from __future__ import annotations

import csv
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telecom_twin.models import TelemetrySample
from telecom_twin.simulation import generate_telemetry
from telecom_twin.topology import generate_topology


@dataclass(frozen=True)
class AnomalyEvent:
    timestamp_s: int
    node_id: str
    score: float
    latency_z: float
    loss_z: float
    cpu_z: float
    metric: str

    def to_dict(self) -> dict:
        return asdict(self)


class RollingAnomalyDetector:
    """Per-node rolling z-score detector evaluated before baseline updates."""

    def __init__(self, *, window_size: int = 60, warmup: int = 30, threshold: float = 5.0):
        if not 2 <= warmup <= window_size:
            raise ValueError("warmup must be between 2 and window_size")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self.window_size = window_size
        self.warmup = warmup
        self.threshold = threshold
        self._history: dict[str, deque[TelemetrySample]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    @staticmethod
    def _z(value: float, baseline: list[float]) -> float:
        mean = sum(baseline) / len(baseline)
        variance = sum((item - mean) ** 2 for item in baseline) / len(baseline)
        return max(0.0, (value - mean) / max(math.sqrt(variance), 1e-6))

    def observe(self, sample: TelemetrySample) -> AnomalyEvent | None:
        history = self._history[sample.node_id]
        event = None
        if len(history) >= self.warmup:
            latency_z = self._z(sample.latency_ms, [row.latency_ms for row in history])
            loss_z = self._z(
                sample.packet_loss_percent,
                [row.packet_loss_percent for row in history],
            )
            cpu_z = self._z(sample.cpu_percent, [row.cpu_percent for row in history])
            scores = {
                "latency_ms": latency_z,
                "packet_loss_percent": loss_z,
                "cpu_percent": cpu_z,
            }
            metric, score = max(scores.items(), key=lambda item: item[1])
            if score >= self.threshold:
                event = AnomalyEvent(
                    sample.timestamp_s,
                    sample.node_id,
                    round(score, 6),
                    round(latency_z, 6),
                    round(loss_z, 6),
                    round(cpu_z, 6),
                    metric,
                )
        history.append(sample)
        return event


class OnlineTwin:
    """Thread-safe replay engine exposing the latest synthetic twin state."""

    def __init__(self, *, duration_s: int = 300, seed: int = 28):
        self.nodes, self.links = generate_topology()
        samples = generate_telemetry(self.nodes, duration_s=duration_s, seed=seed)
        self._frames: dict[int, list[TelemetrySample]] = defaultdict(list)
        for sample in samples:
            self._frames[sample.timestamp_s].append(sample)
        self.duration_s = duration_s
        self._lock = Lock()
        self.reset()

    def reset(self) -> dict:
        with getattr(self, "_lock", Lock()):
            self.timestamp_s = -1
            self.latest: dict[str, TelemetrySample] = {}
            self.events: list[AnomalyEvent] = []
            self.current_anomalies: list[AnomalyEvent] = []
            self.detector = RollingAnomalyDetector()
            return self._snapshot_unlocked()

    def advance(self, steps: int = 1) -> dict:
        if steps < 1:
            raise ValueError("steps must be positive")
        with self._lock:
            for _ in range(steps):
                if self.timestamp_s >= self.duration_s:
                    break
                self.timestamp_s += 1
                self.current_anomalies = []
                for sample in self._frames[self.timestamp_s]:
                    self.latest[sample.node_id] = sample
                    event = self.detector.observe(sample)
                    if event is not None:
                        self.events.append(event)
                        self.current_anomalies.append(event)
            return self._snapshot_unlocked()

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> dict:
        anomaly_nodes = {event.node_id for event in self.current_anomalies}
        node_states = []
        for node in sorted(self.nodes, key=lambda item: item.node_id):
            sample = self.latest.get(node.node_id)
            node_states.append(
                {
                    **node.to_dict(),
                    "status": "anomaly" if node.node_id in anomaly_nodes else "normal",
                    "telemetry": sample.to_dict() if sample else None,
                }
            )
        return {
            "timestamp_s": self.timestamp_s,
            "duration_s": self.duration_s,
            "complete": self.timestamp_s >= self.duration_s,
            "node_count": len(self.nodes),
            "anomaly_count": len(self.events),
            "active_anomaly_count": len(self.current_anomalies),
            "nodes": node_states,
            "recent_events": [event.to_dict() for event in self.events[-20:]],
        }

    def run_to_completion(self) -> dict:
        return self.advance(self.duration_s + 1)


def evaluate_online_detection() -> tuple[dict[str, float | int], list[AnomalyEvent]]:
    twin = OnlineTwin()
    twin.run_to_completion()
    target_events = [
        event
        for event in twin.events
        if event.node_id == "access-07" and 123 <= event.timestamp_s <= 183
    ]
    false_events = [event for event in twin.events if event not in target_events]
    first_detection = min(event.timestamp_s for event in target_events)
    metrics: dict[str, float | int] = {
        "samples_processed": 27 * 301,
        "incident_start_s": 123,
        "first_detection_s": first_detection,
        "detection_delay_s": first_detection - 123,
        "true_anomaly_events": len(target_events),
        "false_anomaly_events": len(false_events),
        "node_seconds": 27 * 301,
        "false_events_per_1000_node_seconds": round(len(false_events) / (27 * 301) * 1000, 6),
    }
    return metrics, twin.events


def export_online_evaluation(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(exist_ok=True)
    metrics, events = evaluate_online_detection()
    metrics_path = output_dir / "online_detection_metrics.csv"
    events_path = output_dir / "online_anomalies.csv"
    figure_path = figure_dir / "online_detection.png"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerows(metrics.items())
    with events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(AnomalyEvent.__annotations__), lineterminator="\n")
        writer.writeheader()
        writer.writerows(event.to_dict() for event in events)

    nodes, _ = generate_topology()
    samples = [row for row in generate_telemetry(nodes) if row.node_id == "access-07"]
    times = [row.timestamp_s for row in samples]
    latency = [row.latency_ms for row in samples]
    detection_times = [event.timestamp_s for event in events if event.node_id == "access-07"]
    fig, axis = plt.subplots(figsize=(10, 4.8))
    axis.plot(times, latency, color="#2563eb", linewidth=1.8, label="access-07 latency")
    axis.axvspan(123, 183, color="#f97316", alpha=0.15, label="injected incident")
    axis.scatter(
        detection_times,
        [latency[timestamp] for timestamp in detection_times],
        color="#dc2626",
        s=20,
        label="online detections",
        zorder=3,
    )
    axis.set(xlabel="Simulation time (s)", ylabel="Latency (ms)", title="Online anomaly detection replay")
    axis.grid(alpha=0.25)
    axis.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)
    return {"metrics": metrics_path, "events": events_path, "figure": figure_path}
