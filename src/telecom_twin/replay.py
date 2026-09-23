"""Incident Replay Engine for Enterprise Network Digital Twin.

Replays simulated enterprise incidents through a realistic six-stage lifecycle:
NORMAL -> DEGRADATION -> ANOMALY -> RCA -> IMPACT -> RECOVERY.

Provides deterministic step-by-step playback, timestamp-based seeking, and
guarantees complete isolation without mutating live twin state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.impact import analyze_service_impact
from telecom_twin.models import (
    IncidentTimelineEvent,
    NetworkLink,
    NetworkNode,
)
from telecom_twin.services import EnterpriseServiceCatalog

LIFECYCLE_STAGES: tuple[str, ...] = (
    "NORMAL",
    "DEGRADATION",
    "ANOMALY",
    "RCA",
    "IMPACT",
    "RECOVERY",
)


@dataclass(frozen=True)
class IncidentScenarioConfig:
    """Configuration for an enterprise incident scenario replay."""

    scenario_id: str = "incident-replay-001"
    target_node_id: str = "core-sw-01"
    fault_type: str = "packet_loss"
    start_time_s: int = 30
    duration_s: int = 60
    ramp_s: int = 10
    severity: str = "CRITICAL"
    description: str = "Simulated enterprise incident replay"

    def to_dict(self) -> dict:
        return asdict(self)


def build_incident_timeline(
    config: IncidentScenarioConfig | None = None,
    nodes: list[NetworkNode] | None = None,
    links: list[NetworkLink] | None = None,
    catalog: EnterpriseServiceCatalog | None = None,
) -> tuple[IncidentTimelineEvent, ...]:
    """Construct a strictly monotonic 6-stage incident timeline.

    Stages:
    1. NORMAL: Nominal baseline telemetry, no alarms, no root cause, no impact.
    2. DEGRADATION: Incipient fault injection, metric drift, early indicators.
    3. ANOMALY: Statistically significant anomaly detection, active threshold alarms.
    4. RCA: Root cause analysis engine identifies origin fault component.
    5. IMPACT: Blast radius evaluated, affected enterprise services cataloged.
    6. RECOVERY: Fault cleared, telemetry returned to baseline, services healthy.

    Guarantees:
    - Strictly monotonic timestamps (t_i < t_{i+1}).
    - Root cause ID is None prior to RCA stage (never appears in NORMAL or DEGRADATION).
    - Affected services are empty prior to IMPACT stage.
    - RECOVERY stage succeeds IMPACT stage and clears active alarms.
    """
    if config is None:
        config = IncidentScenarioConfig()

    # Resolve topology and service catalog without mutating external inputs
    if nodes is None or links is None:
        topo_nodes, topo_links = generate_enterprise_topology()
        sim_nodes = list(topo_nodes) if nodes is None else list(nodes)
        sim_links = list(topo_links) if links is None else list(links)
    else:
        sim_nodes = list(nodes)
        sim_links = list(links)

    sim_catalog = (
        catalog if catalog is not None else EnterpriseServiceCatalog.create_default()
    )

    # Calculate actual service impact using topology and catalog
    impact_report = analyze_service_impact(
        nodes=sim_nodes,
        links=sim_links,
        catalog=sim_catalog,
        failed_nodes=[config.target_node_id],
    )
    all_affected = set(impact_report.directly_impacted_services) | set(
        impact_report.transitively_impacted_services
    )
    affected_services = tuple(sorted(all_affected))
    blast_radius = impact_report.blast_radius_percent

    # Generate strictly monotonic timestamps for the 6 stages
    t_normal = max(0, config.start_time_s - 15)
    t_degradation = config.start_time_s
    t_anomaly = config.start_time_s + max(1, config.ramp_s)
    t_rca = t_anomaly + 5
    t_impact = t_rca + 5
    t_recovery = max(t_impact + 10, config.start_time_s + config.duration_s + 10)

    # 1. NORMAL Stage
    event_normal = IncidentTimelineEvent(
        timestamp_s=t_normal,
        stage="NORMAL",
        description=(
            f"Nominal operating state. All {len(sim_nodes)} nodes healthy; "
            f"baseline metrics within SLA boundaries."
        ),
        active_alarms=(),
        root_cause_id=None,
        affected_services=(),
    )

    # 2. DEGRADATION Stage
    event_degradation = IncidentTimelineEvent(
        timestamp_s=t_degradation,
        stage="DEGRADATION",
        description=(
            f"Incipient performance degradation: {config.fault_type} beginning on "
            f"{config.target_node_id} (ramp duration {config.ramp_s}s)."
        ),
        active_alarms=(),
        root_cause_id=None,
        affected_services=(),
    )

    # 3. ANOMALY Stage
    fault_alarm = f"ALARM_{config.fault_type.upper()}_{config.target_node_id.upper()}"
    event_anomaly = IncidentTimelineEvent(
        timestamp_s=t_anomaly,
        stage="ANOMALY",
        description=(
            f"Anomaly detected: Telemetry threshold breach on {config.target_node_id}. "
            f"Z-score exceeds threshold 3.0."
        ),
        active_alarms=(fault_alarm, "ALARM_TELEMETRY_ANOMALY"),
        root_cause_id=None,
        affected_services=(),
    )

    # 4. RCA Stage
    event_rca = IncidentTimelineEvent(
        timestamp_s=t_rca,
        stage="RCA",
        description=(
            f"Root Cause Analysis identified origin component: {config.target_node_id} "
            f"(confidence 0.95) based on alarm clustering and topological correlation."
        ),
        active_alarms=(fault_alarm, "ALARM_TELEMETRY_ANOMALY"),
        root_cause_id=config.target_node_id,
        affected_services=(),
    )

    # 5. IMPACT Stage
    impact_alarms = (
        fault_alarm,
        "ALARM_TELEMETRY_ANOMALY",
        "ALARM_SERVICE_IMPACT_DEGRADED",
    )
    event_impact = IncidentTimelineEvent(
        timestamp_s=t_impact,
        stage="IMPACT",
        description=(
            f"Service impact analysis completed: {len(affected_services)} services "
            f"impacted ({', '.join(affected_services) if affected_services else 'None'}). "
            f"Blast radius: {blast_radius:.1f}%."
        ),
        active_alarms=impact_alarms,
        root_cause_id=config.target_node_id,
        affected_services=affected_services,
    )

    # 6. RECOVERY Stage
    event_recovery = IncidentTimelineEvent(
        timestamp_s=t_recovery,
        stage="RECOVERY",
        description=(
            f"Incident recovered. Telemetry on {config.target_node_id} returned to baseline. "
            f"All active alarms cleared and services restored."
        ),
        active_alarms=(),
        root_cause_id=None,
        affected_services=(),
    )

    return (
        event_normal,
        event_degradation,
        event_anomaly,
        event_rca,
        event_impact,
        event_recovery,
    )


class IncidentReplayer:
    """Stateful step-by-step incident replayer for digital twin post-mortems."""

    def __init__(
        self,
        timeline: tuple[IncidentTimelineEvent, ...] | list[IncidentTimelineEvent] | None = None,
        config: IncidentScenarioConfig | None = None,
    ) -> None:
        if timeline is not None:
            if len(timeline) == 0:
                raise ValueError("Timeline must contain at least one IncidentTimelineEvent.")
            for e in timeline:
                if not isinstance(e, IncidentTimelineEvent):
                    raise TypeError(f"Expected IncidentTimelineEvent, got {type(e)}")
            self._timeline: tuple[IncidentTimelineEvent, ...] = tuple(timeline)
        else:
            self._timeline = build_incident_timeline(config=config)

        self._current_index: int = 0

    @property
    def current_index(self) -> int:
        """Current zero-based index in the incident timeline."""
        return self._current_index

    @property
    def current_event(self) -> IncidentTimelineEvent:
        """Currently active event in replay playback."""
        return self._timeline[self._current_index]

    @property
    def total_events(self) -> int:
        """Total number of events in this incident replay."""
        return len(self._timeline)

    @property
    def is_finished(self) -> bool:
        """Whether the replay has reached the final event."""
        return self._current_index >= len(self._timeline) - 1

    def get_timeline(self) -> tuple[IncidentTimelineEvent, ...]:
        """Return the immutable timeline tuple."""
        return self._timeline

    def get_event_by_index(self, index: int) -> IncidentTimelineEvent:
        """Retrieve an event by its timeline index.

        Raises IndexError if index is out of bounds.
        """
        if index < 0 or index >= len(self._timeline):
            raise IndexError(
                f"Index {index} out of range for timeline with {len(self._timeline)} events"
            )
        return self._timeline[index]

    def get_event_by_timestamp(self, timestamp_s: float) -> IncidentTimelineEvent:
        """Find the active event at or immediately preceding a given timestamp.

        If timestamp precedes the first event, returns the first event.
        """
        if timestamp_s <= self._timeline[0].timestamp_s:
            return self._timeline[0]

        best = self._timeline[0]
        for event in self._timeline:
            if event.timestamp_s <= timestamp_s:
                best = event
            else:
                break
        return best

    def seek(self, index: int) -> IncidentTimelineEvent:
        """Seek playback directly to a given index."""
        if index < 0 or index >= len(self._timeline):
            raise IndexError(
                f"Cannot seek to index {index}: timeline length is {len(self._timeline)}"
            )
        self._current_index = index
        return self.current_event

    def next_step(self) -> IncidentTimelineEvent | None:
        """Advance playback by one step.

        Returns the new current event, or None if already at the end.
        """
        if self._current_index < len(self._timeline) - 1:
            self._current_index += 1
            return self.current_event
        return None

    def prev_step(self) -> IncidentTimelineEvent | None:
        """Step backward playback by one step.

        Returns the new current event, or None if already at the start.
        """
        if self._current_index > 0:
            self._current_index -= 1
            return self.current_event
        return None

    def reset(self) -> IncidentTimelineEvent:
        """Reset playback back to the first event."""
        self._current_index = 0
        return self.current_event

    def to_dict(self) -> dict:
        """Serialize current replay state to dictionary."""
        return {
            "current_index": self._current_index,
            "current_event": self.current_event.to_dict(),
            "total_events": self.total_events,
            "is_finished": self.is_finished,
            "timeline": [event.to_dict() for event in self._timeline],
        }


def replay_incident(
    config: IncidentScenarioConfig | None = None,
) -> IncidentReplayer:
    """Convenience factory function to instantiate an IncidentReplayer."""
    return IncidentReplayer(config=config)
