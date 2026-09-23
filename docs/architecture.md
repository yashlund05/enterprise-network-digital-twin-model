# Architecture

The first phase uses a deterministic in-memory digital-twin snapshot:

1. `topology.py` creates synthetic core, aggregation, and access nodes.
2. `simulation.py` generates one-second node telemetry and injects one declared
   access-node congestion episode.
3. The alarm engine evaluates latency and packet-loss thresholds.
4. `protocols.py` replays the same telemetry through fixed polling and adaptive
   delta/heartbeat strategies.
5. `api.py` exposes a read-only FastAPI interface over the generated snapshot.
6. `experiment.py` writes portable CSV files and a deterministic PNG.
7. `robustness.py` generates timed noisy fault trials, performs balanced
   evaluation, and exports a role-stratified accuracy figure.
8. `online.py` replays telemetry by simulation timestamp, maintains the latest
   per-node state, applies rolling anomaly detection, and exports evaluation artifacts.
9. `dashboard.py` contains a dependency-free HTML/JavaScript topology view that
   consumes the live state through REST and Server-Sent Events (SSE).
10. `multifault.py` correlates time-separated alarm cascades, ranks a root per
    incident window, and maps root sets to downstream synthetic service endpoints.

The API and experiment paths call the same topology, simulation, alarm, and
protocol functions. There is no duplicate hidden implementation for the demo.

## API routes

- `GET /health`
- `GET /topology`
- `GET /telemetry/latest?node_id=access-07`
- `GET /alarms?limit=100`
- `GET /experiments/protocols`
- `GET /experiments/root-cause`
- `GET /experiments/multi-fault`
- `GET /dashboard`
- `GET /live/state`
- `POST /live/reset`
- `POST /live/step?steps=1`
- `GET /live/events?limit=100`
- `GET /live/stream?interval_ms=250`

FastAPI supplies an OpenAPI document and interactive documentation at `/docs`.
The API runs on loopback by default and does not include authentication because
it exposes only deterministic synthetic data.

## Online execution model

`OnlineTwin` groups the deterministic source samples into one-second frames.
Advancing a frame updates all 27 nodes atomically under a lock, evaluates each
sample against the node's prior rolling baseline, and then publishes a coherent
snapshot. SSE clients receive one JSON snapshot per frame. The replay stops at
300 s instead of looping, so repeated tests have an unambiguous terminal state.

This design demonstrates online state transitions and streaming API behavior
without claiming a distributed or hard-real-time architecture. The same engine
backs manual REST stepping, SSE streaming, tests, and the exported evaluation.

## Multi-fault analysis path

The multi-fault benchmark constructs two causal alarm cascades from the same
hierarchy used by single-fault ranking. A timestamp-gap correlator partitions
the combined feed without access to the true labels. Each partition is ranked
with the existing topology-and-propagation-time model, preserving one root per
incident window. The union of downstream access descendants provides a simple
service-impact set for recall and Jaccard evaluation.

This is intentionally transparent and deterministic. It is not an event-bus
implementation, a learned correlator, or a probabilistic graphical model.
