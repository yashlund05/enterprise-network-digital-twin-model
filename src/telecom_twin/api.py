"""FastAPI read API over a deterministic in-memory digital-twin snapshot."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from telecom_twin.dashboard import DASHBOARD_HTML
from telecom_twin.multifault import run_multi_fault_trials
from telecom_twin.online import OnlineTwin
from telecom_twin.protocols import compare_protocols
from telecom_twin.root_cause import evaluate_root_cause
from telecom_twin.simulation import generate_alarms, generate_telemetry
from telecom_twin.topology import generate_topology

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

app = FastAPI(
    title="Synthetic Telecom Network Digital Twin",
    version="1.0.0",
    description="Reproducible synthetic data only; not connected to an operator network.",
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
