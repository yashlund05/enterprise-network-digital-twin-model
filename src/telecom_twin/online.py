"""Digital twin synchronization and telemetry replay engine.

Conceptual Distinctions:
1. Physical / Monitored Network State: The ground-truth operational condition
   of physical switches, routers, links, and hosts (e.g. actual CPU load, line errors,
   cable cuts, or hardware faults).
2. Digital Twin State: The software replica's in-memory model of topology,
   attributes, virtual device parameters, and active anomaly events.
3. Synchronization State: The quality, timeliness, and fidelity of alignment
   between telemetry updates and the digital twin (sync timestamp, telemetry staleness,
   node sync status, and topology representation consistency).
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

import matplotlib

from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.models import (
    LinkTelemetrySample,
    NetworkLink,
    NetworkNode,
    TelemetrySample,
    TwinSyncState,
)
from telecom_twin.simulation import generate_enterprise_telemetry, generate_telemetry
from telecom_twin.topology import generate_topology

matplotlib.use("Agg")
import matplotlib.pyplot as plt

STALENESS_SYNCHRONIZED_THRESHOLD_S = 2.0
STALENESS_STALE_THRESHOLD_S = 5.0


@dataclass(frozen=True)
class AnomalyEvent:
    timestamp_s: int
    node_id: str
    score: float
    latency_z: float
    loss_z: float
    cpu_z: float
    metric: str
    composite_z: float = 0.0
    severity: str = "CRITICAL"
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(data.get("evidence"), tuple):
            data["evidence"] = list(data["evidence"])
        return data


class RollingAnomalyDetector:
    """Per-node rolling z-score detector evaluated before baseline updates.

    Supports two operational modes:
    - 'legacy': Replicates original v1.0.0 telecom behavior using single-metric
      maximum threshold comparison (default threshold: 5.0).
    - 'enterprise': Multivariate anomaly scoring across enterprise telemetry metrics
      (latency, packet loss, CPU utilization) using a weighted composite z-score,
      ordered severity tiers (NORMAL, INFO, WARNING, CRITICAL), and triggered
      component evidence extraction.

    Mathematical Specifications:
    - Composite z-score formula:
        Z_composite = 0.40 * Z_latency + 0.35 * Z_loss + 0.25 * Z_cpu
    - Ordered severity mapping:
        NORMAL:   Z_composite < 3.0
        INFO:     3.0 <= Z_composite < 4.0
        WARNING:  4.0 <= Z_composite < 5.0
        CRITICAL: Z_composite >= 5.0
    - Warmup handling: First (warmup - 1) samples for each node return None.
    - Zero/near-zero variance safety: When variance < min_std (1e-6) and delta < min_std,
      z-score returns 0.0 without division by zero, NaN, or infinity.
    - Temporal recovery: One-sided z-score (max(0, delta / std)) immediately drops to 0.0
      when metric values recover to or below the baseline mean.
    """

    def __init__(
        self,
        *,
        window_size: int = 60,
        warmup: int = 30,
        threshold: float | None = None,
        mode: str = "legacy",
    ):
        if not 2 <= warmup <= window_size:
            raise ValueError("warmup must be between 2 and window_size")
        if threshold is not None and threshold <= 0:
            raise ValueError("threshold must be positive")
        self.window_size = window_size
        self.warmup = warmup
        self.mode = mode
        if threshold is None:
            self.threshold = 3.0 if mode == "enterprise" else 5.0
        else:
            self.threshold = threshold
        self._history: dict[str, deque[TelemetrySample]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    @staticmethod
    def _z(value: float, baseline: list[float], min_std: float = 1e-6) -> float:
        if not baseline or math.isnan(value) or math.isinf(value):
            return 0.0
        clean_baseline = [v for v in baseline if not (math.isnan(v) or math.isinf(v))]
        if not clean_baseline:
            return 0.0
        mean = sum(clean_baseline) / len(clean_baseline)
        variance = sum((item - mean) ** 2 for item in clean_baseline) / len(clean_baseline)
        std = math.sqrt(max(0.0, variance))
        delta = value - mean
        if delta <= 0.0:
            return 0.0
        if std < min_std:
            if delta < min_std:
                return 0.0
            return max(0.0, delta / min_std)
        z = delta / std
        if math.isnan(z) or math.isinf(z):
            return 0.0
        return max(0.0, z)

    @staticmethod
    def compute_composite_score(
        latency_z: float,
        loss_z: float,
        cpu_z: float,
    ) -> float:
        """Compute the weighted enterprise composite anomaly score.

        Z_composite = 0.40 * Z_latency + 0.35 * Z_loss + 0.25 * Z_cpu
        """
        score = 0.40 * latency_z + 0.35 * loss_z + 0.25 * cpu_z
        return round(max(0.0, score), 6)

    @staticmethod
    def severity_for_score(score: float) -> str:
        """Map composite z-score to ordered severity category."""
        if score >= 5.0:
            return "CRITICAL"
        if score >= 4.0:
            return "WARNING"
        if score >= 3.0:
            return "INFO"
        return "NORMAL"

    @staticmethod
    def extract_evidence(
        latency_z: float,
        loss_z: float,
        cpu_z: float,
        threshold: float = 3.0,
    ) -> tuple[str, ...]:
        """Identify triggered components exceeding the component threshold."""
        evidence: list[str] = []
        if latency_z >= threshold:
            evidence.append("latency anomaly")
        if loss_z >= threshold:
            evidence.append("packet loss anomaly")
        if cpu_z >= threshold:
            evidence.append("cpu anomaly")
        return tuple(evidence)

    def evaluate_sample(self, sample: TelemetrySample) -> AnomalyEvent | None:
        """Evaluate a sample against rolling baseline history without mutating history."""
        history = self._history[sample.node_id]
        if len(history) < self.warmup:
            return None

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
        metric, dominant_score = max(scores.items(), key=lambda item: item[1])

        if self.mode == "legacy":
            composite_z = self.compute_composite_score(latency_z, loss_z, cpu_z)
            if dominant_score >= self.threshold:
                return AnomalyEvent(
                    timestamp_s=sample.timestamp_s,
                    node_id=sample.node_id,
                    score=round(dominant_score, 6),
                    latency_z=round(latency_z, 6),
                    loss_z=round(loss_z, 6),
                    cpu_z=round(cpu_z, 6),
                    metric=metric,
                    composite_z=composite_z,
                    severity="CRITICAL",
                    evidence=self.extract_evidence(latency_z, loss_z, cpu_z),
                )
            return None

        composite_z = self.compute_composite_score(latency_z, loss_z, cpu_z)
        severity = self.severity_for_score(composite_z)
        evidence = self.extract_evidence(latency_z, loss_z, cpu_z)

        return AnomalyEvent(
            timestamp_s=sample.timestamp_s,
            node_id=sample.node_id,
            score=composite_z,
            latency_z=round(latency_z, 6),
            loss_z=round(loss_z, 6),
            cpu_z=round(cpu_z, 6),
            metric=metric,
            composite_z=composite_z,
            severity=severity,
            evidence=evidence,
        )

    def observe(self, sample: TelemetrySample) -> AnomalyEvent | None:
        """Observe sample, evaluate against history, and update rolling baseline."""
        history = self._history[sample.node_id]
        event = self.evaluate_sample(sample)
        history.append(sample)
        if event is None:
            return None
        if self.mode == "enterprise" and (event.composite_z < self.threshold or event.severity == "NORMAL"):
            return None
        return event


class OnlineTwin:
    """Thread-safe digital twin synchronization and replay engine.

    Supports two operational modes:
    - 'legacy': Synthetic telecom network replay matching original v1.0.0 behavior.
    - 'enterprise': Multi-tier enterprise network digital twin with real-time
      synchronization tracking, per-node staleness calculation, and topology
      consistency scoring.
    """

    def __init__(
        self,
        *,
        duration_s: int = 300,
        seed: int = 28,
        mode: str = "legacy",
        nodes: list[NetworkNode] | None = None,
        links: list[NetworkLink] | None = None,
    ):
        self.mode = mode
        self.duration_s = duration_s
        self.seed = seed
        self._lock = Lock()

        if mode == "enterprise":
            if nodes is None or links is None:
                default_nodes, default_links = generate_enterprise_topology()
                self.nodes = list(nodes) if nodes is not None else default_nodes
                self.links = list(links) if links is not None else default_links
            else:
                self.nodes = list(nodes)
                self.links = list(links)

            self._expected_node_ids = {node.node_id for node in self.nodes}
            self._expected_links = {frozenset([l.source, l.target]) for l in self.links}

            enterprise_data = generate_enterprise_telemetry(
                self.nodes, self.links, duration_s=duration_s, seed=seed
            )
            self._frames: dict[int, list[TelemetrySample]] = defaultdict(list)
            for sample in enterprise_data.node_telemetry:
                self._frames[sample.timestamp_s].append(sample)

            self._link_frames: dict[int, list[LinkTelemetrySample]] = defaultdict(list)
            for l_sample in enterprise_data.link_telemetry:
                self._link_frames[l_sample.timestamp_s].append(l_sample)

        else:
            if nodes is None or links is None:
                self.nodes, self.links = generate_topology()
            else:
                self.nodes = list(nodes)
                self.links = list(links)
            self._expected_node_ids = {node.node_id for node in self.nodes}
            self._expected_links = {frozenset([l.source, l.target]) for l in self.links}

            samples = generate_telemetry(self.nodes, duration_s=duration_s, seed=seed)
            self._frames = defaultdict(list)
            for sample in samples:
                self._frames[sample.timestamp_s].append(sample)
            self._link_frames = defaultdict(list)

        self.reset()

    def reset(self) -> dict:
        with getattr(self, "_lock", Lock()):
            self.timestamp_s = -1
            self.sync_timestamp_s = -1
            self.latest: dict[str, TelemetrySample] = {}
            self.latest_links: dict[tuple[str, str], LinkTelemetrySample] = {}
            self.last_node_update: dict[str, int] = {}
            self.last_link_update: dict[tuple[str, str], int] = {}
            self.unknown_telemetry_nodes: set[str] = set()
            self.events: list[AnomalyEvent] = []
            self.current_anomalies: list[AnomalyEvent] = []
            self.detector = RollingAnomalyDetector(mode=self.mode)
            if self.mode == "enterprise":
                return self._enterprise_snapshot_unlocked()
            return self._snapshot_unlocked()

    def advance(self, steps: int = 1) -> dict:
        if steps < 1:
            raise ValueError("steps must be positive")
        with self._lock:
            for _ in range(steps):
                if self.timestamp_s >= self.duration_s:
                    break
                self.timestamp_s += 1
                self.sync_timestamp_s = self.timestamp_s
                self.current_anomalies = []
                for sample in self._frames[self.timestamp_s]:
                    self.latest[sample.node_id] = sample
                    self.last_node_update[sample.node_id] = self.timestamp_s
                    event = self.detector.observe(sample)
                    if event is not None:
                        self.events.append(event)
                        self.current_anomalies.append(event)
                if self.mode == "enterprise":
                    for l_sample in self._link_frames[self.timestamp_s]:
                        self.latest_links[(l_sample.source, l_sample.target)] = l_sample
                        self.last_link_update[(l_sample.source, l_sample.target)] = self.timestamp_s
            if self.mode == "enterprise":
                return self._enterprise_snapshot_unlocked()
            return self._snapshot_unlocked()

    def apply_node_telemetry(
        self,
        samples: list[TelemetrySample] | TelemetrySample,
        *,
        timestamp_s: int | None = None,
    ) -> None:
        """Apply a node telemetry update to the digital twin virtual state."""
        sample_list = [samples] if isinstance(samples, TelemetrySample) else samples
        with self._lock:
            for sample in sample_list:
                t = timestamp_s if timestamp_s is not None else sample.timestamp_s
                self.latest[sample.node_id] = sample
                self.last_node_update[sample.node_id] = t
                self.sync_timestamp_s = max(self.sync_timestamp_s, t)
                self.timestamp_s = max(self.timestamp_s, t)
                if sample.node_id not in self._expected_node_ids:
                    self.unknown_telemetry_nodes.add(sample.node_id)

    def apply_link_telemetry(
        self,
        samples: list[LinkTelemetrySample] | LinkTelemetrySample,
        *,
        timestamp_s: int | None = None,
    ) -> None:
        """Apply a link telemetry update to the digital twin virtual state."""
        sample_list = [samples] if isinstance(samples, LinkTelemetrySample) else samples
        with self._lock:
            for sample in sample_list:
                t = timestamp_s if timestamp_s is not None else sample.timestamp_s
                self.latest_links[(sample.source, sample.target)] = sample
                self.last_link_update[(sample.source, sample.target)] = t
                self.sync_timestamp_s = max(self.sync_timestamp_s, t)
                self.timestamp_s = max(self.timestamp_s, t)

    def apply_telemetry_snapshot(
        self,
        node_samples: list[TelemetrySample],
        link_samples: list[LinkTelemetrySample] | None = None,
        *,
        timestamp_s: int | None = None,
    ) -> dict:
        """Atomically apply a complete enterprise telemetry snapshot."""
        self.apply_node_telemetry(node_samples, timestamp_s=timestamp_s)
        if link_samples:
            self.apply_link_telemetry(link_samples, timestamp_s=timestamp_s)
        return self.snapshot()

    def get_node_staleness(self) -> dict[str, float]:
        """Return per-node telemetry staleness in seconds relative to current twin time."""
        with self._lock:
            return self._calculate_node_staleness_unlocked()

    def _calculate_node_staleness_unlocked(self) -> dict[str, float]:
        current_t = max(0, self.sync_timestamp_s)
        staleness = {}
        for node in self.nodes:
            if node.node_id in self.last_node_update:
                last_t = self.last_node_update[node.node_id]
                staleness[node.node_id] = max(0.0, float(current_t - last_t))
            else:
                staleness[node.node_id] = float("inf")
        return staleness

    def get_node_sync_status(self) -> dict[str, str]:
        """Return synchronization status for each node ('synchronized', 'stale', or 'missing')."""
        with self._lock:
            return self._calculate_node_sync_status_unlocked()

    def _calculate_node_sync_status_unlocked(self) -> dict[str, str]:
        staleness_map = self._calculate_node_staleness_unlocked()
        status_map = {}
        for node_id, staleness in staleness_map.items():
            if math.isinf(staleness):
                status_map[node_id] = "missing"
            elif staleness <= STALENESS_SYNCHRONIZED_THRESHOLD_S:
                status_map[node_id] = "synchronized"
            elif staleness <= STALENESS_STALE_THRESHOLD_S:
                status_map[node_id] = "stale"
            else:
                status_map[node_id] = "missing"
        return status_map

    def get_topology_consistency(self) -> float:
        """Compute topology representation consistency score (0.0 to 1.0)."""
        with self._lock:
            return self._calculate_topology_consistency_unlocked()

    def _calculate_topology_consistency_unlocked(self) -> float:
        if not self.nodes:
            return 0.0

        present_node_ids = [n.node_id for n in self.nodes]
        unique_present_nodes = set(present_node_ids)

        duplicate_penalty = len(present_node_ids) - len(unique_present_nodes)
        expected_total_nodes = max(1, len(self._expected_node_ids))
        node_coverage = len(unique_present_nodes & self._expected_node_ids) / expected_total_nodes
        if duplicate_penalty > 0:
            node_coverage = max(0.0, node_coverage - 0.20 * duplicate_penalty)
        node_coherence = max(0.0, min(1.0, node_coverage))

        if self.links:
            valid_links = [
                l for l in self.links
                if l.source in unique_present_nodes and l.target in unique_present_nodes
            ]
            present_link_pairs = {frozenset([l.source, l.target]) for l in self.links}
            expected_total_links = max(1, len(self._expected_links))
            link_coverage = len(present_link_pairs & self._expected_links) / expected_total_links
            link_endpoint_validity = len(valid_links) / len(self.links)
            link_coherence = max(0.0, min(1.0, 0.5 * link_coverage + 0.5 * link_endpoint_validity))
        else:
            link_coherence = 1.0 if not self._expected_links else 0.0

        total_reported = len(self.latest) + len(self.unknown_telemetry_nodes)
        if total_reported > 0:
            unknown_count = len(self.unknown_telemetry_nodes)
            telemetry_validity = max(0.0, 1.0 - (unknown_count / total_reported))
        else:
            telemetry_validity = 1.0

        consistency = 0.40 * node_coherence + 0.35 * link_coherence + 0.25 * telemetry_validity
        return round(max(0.0, min(1.0, consistency)), 4)

    def get_sync_state(self) -> TwinSyncState:
        """Return the current TwinSyncState dataclass."""
        with self._lock:
            return self._calculate_sync_state_unlocked()

    def _calculate_sync_state_unlocked(self) -> TwinSyncState:
        staleness_map = self._calculate_node_staleness_unlocked()
        finite_staleness = [s for s in staleness_map.values() if not math.isinf(s)]
        mean_staleness = sum(finite_staleness) / len(finite_staleness) if finite_staleness else 0.0

        sync_status_map = self._calculate_node_sync_status_unlocked()
        statuses = set(sync_status_map.values())
        if not statuses or statuses == {"synchronized"}:
            overall_status = "synchronized"
        elif "missing" in statuses:
            overall_status = "missing"
        else:
            overall_status = "stale"

        consistency = self._calculate_topology_consistency_unlocked()

        return TwinSyncState(
            sync_timestamp_s=max(0, self.sync_timestamp_s),
            telemetry_staleness_s=round(mean_staleness, 4),
            consistency_score=consistency,
            node_sync_status=overall_status,
        )

    def snapshot(self) -> dict:
        with self._lock:
            if self.mode == "enterprise":
                return self._enterprise_snapshot_unlocked()
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

    def _enterprise_snapshot_unlocked(self) -> dict:
        sync_state = self._calculate_sync_state_unlocked()
        staleness_map = self._calculate_node_staleness_unlocked()
        sync_status_map = self._calculate_node_sync_status_unlocked()

        anomaly_nodes = {event.node_id for event in self.current_anomalies}
        node_states = []
        for node in sorted(self.nodes, key=lambda item: item.node_id):
            sample = self.latest.get(node.node_id)
            staleness = staleness_map.get(node.node_id, float("inf"))
            node_states.append(
                {
                    **node.to_dict(),
                    "status": "anomaly" if node.node_id in anomaly_nodes else "normal",
                    "telemetry": sample.to_dict() if sample else None,
                    "staleness_s": staleness if not math.isinf(staleness) else None,
                    "sync_status": sync_status_map.get(node.node_id, "missing"),
                }
            )

        link_states = []
        for link in self.links:
            link_key = (link.source, link.target)
            rev_key = (link.target, link.source)
            l_sample = self.latest_links.get(link_key) or self.latest_links.get(rev_key)
            link_states.append(
                {
                    **link.to_dict(),
                    "telemetry": l_sample.to_dict() if l_sample else None,
                    "status": l_sample.link_status if l_sample else "up",
                }
            )

        return {
            "mode": "enterprise",
            "timestamp_s": self.timestamp_s,
            "sync_timestamp_s": max(0, self.sync_timestamp_s),
            "duration_s": self.duration_s,
            "complete": self.timestamp_s >= self.duration_s,
            "node_count": len(self.nodes),
            "link_count": len(self.links),
            "anomaly_count": len(self.events),
            "active_anomaly_count": len(self.current_anomalies),
            "sync_state": sync_state.to_dict(),
            "consistency_score": sync_state.consistency_score,
            "telemetry_staleness_s": sync_state.telemetry_staleness_s,
            "node_sync_status": sync_status_map,
            "nodes": node_states,
            "links": link_states,
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
