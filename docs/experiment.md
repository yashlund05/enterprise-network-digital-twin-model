# Protocol-strategy experiment

The experiment uses one common 301-second, 27-node telemetry sequence. The
fixed strategy sends a full sample for every node every ten seconds and assumes
160 bytes per update. The adaptive strategy sends an 80-byte delta when CPU,
latency, or packet loss changes beyond declared thresholds, plus a heartbeat
at least every 30 seconds.

## Metrics

- **Messages** and **transferred bytes** measure modeled management-plane cost.
- **First detection delay** is measured from the first ground-truth threshold
  crossing to the first transmitted threshold-crossing sample.
- **Alarm episode recall** indicates whether the single injected episode was
  observed at least once.
- **Staleness** measures time since the most recently transmitted sample for
  each node at every simulation second.

The adaptive strategy reduces messages by 63.0% and modeled bytes by 81.5%,
while detecting the incident four seconds earlier than fixed polling. Its mean
staleness increases from 4.49 to 13.38 seconds and P95 staleness from 9 to 27
seconds. These results apply only to the included deterministic workload and
declared message-size assumptions.
