"""FastAPI read API over a deterministic in-memory digital-twin snapshot."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from telecom_twin.dashboard import DASHBOARD_HTML
from telecom_twin.enterprise_topology import generate_enterprise_topology
from telecom_twin.models import WhatIfScenario
from telecom_twin.multifault import run_multi_fault_trials
from telecom_twin.online import OnlineTwin
from telecom_twin.protocols import compare_protocols
from telecom_twin.replay import IncidentReplayer, IncidentScenarioConfig, build_incident_timeline
from telecom_twin.root_cause import evaluate_root_cause
from telecom_twin.services import EnterpriseServiceCatalog
from telecom_twin.simulation import generate_alarms, generate_telemetry
from telecom_twin.topology import generate_topology
from telecom_twin.whatif import WhatIfSimulator

nodes, links = generate_topology()
samples = generate_telemetry(nodes)
alarms = generate_alarms(samples)
protocol_results = compare_protocols(samples)
root_cause_results = evaluate_root_cause(nodes, links)
online_twin = OnlineTwin()
multi_fault_results = run_multi_fault_trials(
    nodes,
    links,
    trials_per_scenario=1,
    missing_rates=(0.2,),
    false_alarm_counts=(2,),
)

# Canonical enterprise domain singletons for integration endpoints
enterprise_nodes, enterprise_links = generate_enterprise_topology()
enterprise_catalog = EnterpriseServiceCatalog.create_default()
enterprise_twin = OnlineTwin(mode="enterprise")
enterprise_twin.advance(1)
whatif_simulator = WhatIfSimulator()

app = FastAPI(
    title="Digital Twin Network Monitoring API",
    version="2.0.0",
    description="Deterministic Synthetic and Enterprise Digital Twin Network Monitoring API.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "data_mode": "synthetic", "node_count": len(nodes)}


@app.get("/topology")
def topology() -> dict:
    return {
        "nodes": [node.to_dict() for node in nodes],
        "links": [link.to_dict() for link in links],
    }


@app.get("/telemetry/latest")
def latest_telemetry(node_id: str | None = Query(default=None)) -> list[dict]:
    latest = {sample.node_id: sample for sample in samples}
    if node_id is not None:
        return [latest[node_id].to_dict()] if node_id in latest else []
    return [latest[key].to_dict() for key in sorted(latest)]


@app.get("/alarms")
def alarm_feed(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
    return [alarm.to_dict() for alarm in alarms[-limit:]]


@app.get("/experiments/protocols")
def protocol_experiment() -> list[dict]:
    return protocol_results


@app.get("/experiments/root-cause")
def root_cause_experiment() -> list[dict]:
    return root_cause_results


@app.get("/experiments/multi-fault")
def multi_fault_experiment() -> list[dict]:
    return multi_fault_results


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/live/state")
def live_state() -> dict:
    return online_twin.snapshot()


@app.post("/live/reset")
def live_reset() -> dict:
    return online_twin.reset()


@app.post("/live/step")
def live_step(steps: int = Query(default=1, ge=1, le=301)) -> dict:
    return online_twin.advance(steps)


@app.get("/live/events")
def live_events(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
    return [event.to_dict() for event in online_twin.events[-limit:]]


@app.get("/live/stream")
async def live_stream(interval_ms: int = Query(default=250, ge=20, le=5000)) -> StreamingResponse:
    async def event_source():
        while True:
            state = online_twin.advance()
            yield f"data: {json.dumps(state, separators=(',', ':'))}\n\n"
            if state["complete"]:
                break
            await asyncio.sleep(interval_ms / 1000)

    return StreamingResponse(event_source(), media_type="text/event-stream")


# ==============================================================================
# Enterprise Network Digital Twin Endpoints (Phase 8)
# ==============================================================================

VALID_FAILURE_TYPES: dict[str, set[str]] = {
    "node": {
        "node_down",
        "node_failure",
        "down",
        "failure",
        "latency_spike",
        "latency",
        "packet_loss",
        "loss",
        "bandwidth_throttling",
        "traffic_surge",
    },
    "link": {
        "link_down",
        "link_failure",
        "down",
        "failure",
        "link_latency",
        "latency_spike",
        "latency",
        "packet_loss",
        "loss",
        "bandwidth_throttling",
    },
}


class WhatIfSimulateRequest(BaseModel):
    """Payload schema for counterfactual What-If simulation requests."""

    scenario_id: str | None = None
    name: str | None = None
    target_type: str = Field(default="node", description="Target type: 'node' or 'link'")
    target_id: str = Field(..., description="Target node/link ID (e.g. 'core-sw-01')")
    failure_type: str = Field(default="node_down", description="Failure or degradation type")
    parameter_value: float = Field(default=1.0, ge=0.0, description="Perturbation parameter value")


@app.get("/api/enterprise/topology")
def get_enterprise_topology() -> dict:
    """Return canonical enterprise topology with deterministic node and link ordering."""
    nodes_data = [n.to_dict() for n in sorted(enterprise_nodes, key=lambda x: x.node_id)]
    links_data = [
        l.to_dict() for l in sorted(enterprise_links, key=lambda x: (x.source, x.target))
    ]
    return {
        "nodes": nodes_data,
        "links": links_data,
        "node_count": len(nodes_data),
        "link_count": len(links_data),
    }


@app.get("/api/enterprise/services")
def get_enterprise_services() -> dict:
    """Return all enterprise catalog services and their consumer->provider dependencies."""
    all_services = enterprise_catalog.get_all_services()
    all_deps = enterprise_catalog.dependencies

    services_data = [s.to_dict() for s in all_services]
    deps_data = [d.to_dict() for d in all_deps]

    for s in services_data:
        s_id = s["service_id"]
        s["dependencies"] = [
            d["provider_service_id"]
            for d in deps_data
            if d["consumer_service_id"] == s_id
        ]
        s["dependents"] = [
            d["consumer_service_id"]
            for d in deps_data
            if d["provider_service_id"] == s_id
        ]

    return {
        "services": services_data,
        "dependencies": deps_data,
        "service_count": len(services_data),
        "dependency_count": len(deps_data),
    }


@app.get("/api/enterprise/health")
def get_enterprise_health() -> dict:
    """Return deterministic current enterprise health and tier status snapshot."""
    tiers = ("edge", "core", "distribution", "access", "host")
    tier_health = {}
    for tier in tiers:
        tier_nodes = [n for n in enterprise_nodes if n.tier == tier]
        tier_health[tier] = {
            "status": "healthy",
            "node_count": len(tier_nodes),
            "healthy_nodes": len(tier_nodes),
        }

    all_services = enterprise_catalog.get_all_services()
    service_health = {s.service_id: s.health_status for s in all_services}
    active_anomalies = [a.to_dict() for a in enterprise_twin.current_anomalies]
    active_alarms = [ev.description for ev in enterprise_twin.current_anomalies]
    impacted_services = [
        s.service_id for s in all_services if s.health_status != "healthy"
    ]

    overall_health = (
        "healthy" if not active_anomalies and not impacted_services else "degraded"
    )

    return {
        "overall_health": overall_health,
        "health_by_tier": tier_health,
        "service_health": service_health,
        "active_anomalies": active_anomalies,
        "active_alarms": active_alarms,
        "impacted_services": impacted_services,
    }


@app.get("/api/enterprise/twin/sync")
def get_enterprise_twin_sync() -> dict:
    """Expose twin synchronization metrics and per-node staleness status."""
    sync_state = enterprise_twin.get_sync_state()
    node_status = enterprise_twin.get_node_sync_status()
    node_staleness = enterprise_twin.get_node_staleness()

    sanitized_staleness = {
        nid: (None if val == float("inf") else round(val, 4))
        for nid, val in node_staleness.items()
    }

    overall_status = (
        sync_state.node_sync_status
        if isinstance(sync_state.node_sync_status, str)
        else "synchronized"
    )

    return {
        "sync_timestamp_s": sync_state.sync_timestamp_s,
        "telemetry_staleness_s": sync_state.telemetry_staleness_s,
        "consistency_score": sync_state.consistency_score,
        "overall_sync_status": overall_status,
        "node_sync_status": node_status,
        "node_staleness_s": sanitized_staleness,
    }


@app.post("/api/enterprise/whatif/simulate")
def simulate_whatif(req: WhatIfSimulateRequest) -> dict:
    """Execute counterfactual What-If simulation inside an isolated sandbox."""
    target_type = req.target_type.strip().lower()
    if target_type not in ("node", "link"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_type '{req.target_type}'. Must be 'node' or 'link'.",
        )

    known_nodes = {n.node_id for n in enterprise_nodes}
    if target_type == "node":
        if req.target_id not in known_nodes:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown enterprise node '{req.target_id}'. Known nodes: {sorted(known_nodes)}",
            )
    else:
        # Link validation: format must be u<->v or u--v with known endpoints
        target_str = req.target_id.strip()
        endpoints = None
        if "<->" in target_str:
            u, v = target_str.split("<->", 1)
            endpoints = (u.strip(), v.strip())
        elif "--" in target_str:
            u, v = target_str.split("--", 1)
            endpoints = (u.strip(), v.strip())

        if not endpoints or endpoints[0] not in known_nodes or endpoints[1] not in known_nodes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid or unknown enterprise link '{req.target_id}'. "
                    "Expected format 'nodeA<->nodeB' connecting known nodes."
                ),
            )

    failure_type = req.failure_type.strip().lower()
    allowed_failures = VALID_FAILURE_TYPES.get(target_type, set())
    if failure_type not in allowed_failures:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid failure_type '{req.failure_type}' for target_type '{target_type}'. "
                f"Valid failure types: {sorted(allowed_failures)}"
            ),
        )

    if req.parameter_value < 0.0:
        raise HTTPException(
            status_code=400,
            detail="parameter_value must be non-negative.",
        )
    if "loss" in failure_type and req.parameter_value > 100.0:
        raise HTTPException(
            status_code=400,
            detail="Packet loss parameter cannot exceed 100.0%.",
        )

    scenario = WhatIfScenario(
        scenario_id=req.scenario_id or f"sim-{req.target_id}",
        name=req.name or f"What-If {failure_type} on {req.target_id}",
        target_type=target_type,
        target_id=req.target_id,
        failure_type=failure_type,
        parameter_value=float(req.parameter_value),
    )

    result = whatif_simulator.simulate(scenario)

    return {
        "scenario": scenario.to_dict(),
        "result": result.to_dict(),
        "predicted_affected_nodes": list(result.predicted_affected_nodes),
        "predicted_affected_links": list(result.predicted_affected_links),
        "predicted_affected_services": list(result.predicted_affected_services),
        "latency_delta_ms": result.latency_delta_ms,
        "loss_delta_percent": result.loss_delta_percent,
        "throughput_delta_mbps": result.throughput_delta_mbps,
        "blast_radius_percent": result.blast_radius_percent,
        "severity": result.severity,
    }


@app.get("/api/enterprise/replay/timeline")
def get_enterprise_replay_timeline(
    target_node_id: str = Query(default="core-sw-01"),
    fault_type: str = Query(default="packet_loss"),
    start_time_s: int = Query(default=30, ge=0),
    duration_s: int = Query(default=60, ge=1),
    ramp_s: int = Query(default=10, ge=1),
) -> dict:
    """Return deterministic 6-stage incident replay timeline."""
    known_nodes = {n.node_id for n in enterprise_nodes}
    if target_node_id not in known_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target_node_id '{target_node_id}'. Known nodes: {sorted(known_nodes)}",
        )

    config = IncidentScenarioConfig(
        target_node_id=target_node_id,
        fault_type=fault_type,
        start_time_s=start_time_s,
        duration_s=duration_s,
        ramp_s=ramp_s,
    )
    timeline = build_incident_timeline(config)
    return {
        "config": config.to_dict(),
        "total_events": len(timeline),
        "stages": [e.stage for e in timeline],
        "timeline": [e.to_dict() for e in timeline],
    }


@app.get("/api/enterprise/replay/step")
def get_enterprise_replay_step(
    index: int = Query(default=0),
    target_node_id: str = Query(default="core-sw-01"),
    fault_type: str = Query(default="packet_loss"),
    start_time_s: int = Query(default=30, ge=0),
    duration_s: int = Query(default=60, ge=1),
    ramp_s: int = Query(default=10, ge=1),
) -> dict:
    """Return a single timeline event from the incident replay by step index."""
    known_nodes = {n.node_id for n in enterprise_nodes}
    if target_node_id not in known_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target_node_id '{target_node_id}'.",
        )

    config = IncidentScenarioConfig(
        target_node_id=target_node_id,
        fault_type=fault_type,
        start_time_s=start_time_s,
        duration_s=duration_s,
        ramp_s=ramp_s,
    )
    replayer = IncidentReplayer(config=config)
    try:
        event = replayer.get_event_by_index(index)
    except IndexError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Index {index} out of bounds for timeline with {replayer.total_events} events "
                f"(valid range: 0 to {replayer.total_events - 1})."
            ),
        )

    return {
        "index": index,
        "total_events": replayer.total_events,
        "is_first": index == 0,
        "is_last": index == replayer.total_events - 1,
        "event": event.to_dict(),
    }


@app.get("/api/enterprise/evaluation")
def get_enterprise_evaluation() -> dict:
    """Report availability of enterprise evaluation framework (scheduled for Phase 10)."""
    return {
        "status": "evaluation_not_available",
        "message": (
            "Enterprise evaluation framework is not yet implemented. "
            "Formal benchmarking metrics (precision, recall, F1, SLA impact) "
            "will be implemented in Phase 10."
        ),
        "available_metrics": [],
    }

