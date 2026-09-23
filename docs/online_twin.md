# Online digital twin

Phase 4 turns the deterministic batch telemetry into a testable online replay.
It remains entirely synthetic and does not connect to an operator network.

## Detection method

Each node owns a rolling history of its last 60 samples. After a 30-sample
warm-up, the detector computes one-sided z-scores for latency, packet loss, and
CPU against the history *before* appending the current sample. An event is
created when the largest score is at least 5.0. One-sided scoring deliberately
targets upward degradation and does not treat low load as anomalous.

The same configuration is applied to every node. No node identifier, incident
time, or static alarm threshold is used by the detector. The evaluation labels
events only after detection: events on `access-07` from 123 through 183 s are
counted as incident events, and all others as non-incident events.

## Reproducible result

The command below exports metrics, all anomaly events, and a timeline figure:

```bash
telecom-twin online-evaluation --output-dir results
```

For the declared seed-28 replay, the first event occurs at 124 s, giving a
one-second detection delay. Six events occur during the declared incident and
none outside it. These results describe one controlled synthetic workload, not
the detector's expected behavior on real network telemetry.

## API behavior

- `POST /live/reset` clears current state and detector histories.
- `POST /live/step` advances one or more complete one-second frames.
- `GET /live/state` reads a coherent current snapshot.
- `GET /live/events` reads recent detector output.
- `GET /live/stream` advances and publishes snapshots over SSE.
- `GET /dashboard` provides a small browser visualization.

The engine is thread-safe within one Python process. It intentionally does not
implement persistence, authentication, backpressure, multi-worker coordination,
or delivery guarantees.
