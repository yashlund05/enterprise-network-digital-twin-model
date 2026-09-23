# Topology-aware root-cause localization

Three deterministic fault scenarios exercise different hierarchy levels:
`access-07`, `aggregation-03`, and `core-02`. An affected set contains the root
and all of its downstream descendants. Seeded observation noise removes some
downstream alarms and adds zero, one, or two false alarms by scenario.

Every node is ranked as a possible cause. The score combines the fraction of
observed alarms explained by its downstream impact, precision of the predicted
impact set, and a small bonus when the candidate itself is observed. This is a
transparent heuristic, not a trained model.

The true root is ranked first in all three included cases. The evaluation is
deliberately small and synthetic; future work should add simultaneous faults,
time ordering, recovery behavior, and larger randomized scenario sets.

## Robustness benchmark

The Phase 3 benchmark runs every one of the 27 nodes as a root cause. It crosses
three missing-alarm rates, three false-alarm counts, and 20 seeded repeats,
producing 4,860 trial rows. A completely missing access alarm is allowed; the
generator never forces ground-truth evidence back into the observation.

Topology-only scoring is compared with a temporal extension. True downstream
alarms are generated at the root time plus three seconds per hierarchy hop and
small jitter. For each candidate, inferred root times should agree; their
dispersion is converted into a temporal-coherence score.

Metrics are macro-averaged across access, aggregation, and core roles. This
prevents the 18 access nodes from dominating the six aggregation and three core
nodes. Temporal information improves macro Top-1 from 69.56% to 74.75% and
macro Top-3 from 84.66% to 87.85%. In the hardest 40%-missing/four-false-alarm
condition, macro Top-1 improves from 41.39% to 53.70%.

Access-root Top-1 remains only 12.78% in that hardest condition. A leaf cause
has one causal alarm; if it is missing, unrelated false alarms can dominate.
This is an observable identifiability limit, not merely an implementation bug.
