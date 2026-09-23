# Multi-fault correlation and service impact

Phase 5 tests whether the digital twin can separate two alarm cascades and
reason about their combined downstream impact. All nodes, alarms, timestamps,
and service identifiers are synthetic.

## Scenario matrix

The benchmark declares six independent fault pairs on separate branches and
six nested pairs where one fault is downstream of the other. The first cascade
starts at 100 s and the second at 130 s. Each causal hop adds three seconds plus
seeded jitter. The matrix applies three missing-alarm rates, three false-alarm
counts, and 20 trials to each pair:

```text
12 scenarios × 3 missing rates × 3 false-alarm counts × 20 trials = 2,160
```

## Correlation and localization

Alarms are sorted by timestamp and split when consecutive alarms are more than
12 seconds apart. The split does not use root labels. The topology-and-time
ranker selects the strongest candidate in each cluster. If missing alarms leave
fewer than two distinct cluster roots, the global ranking supplies remaining
candidates. This fallback makes the expected two-fault assumption explicit.

The baseline instead applies one global ranking and takes its first two
candidates. Exact match requires both predicted roots and no substitutions;
root recall gives partial credit when one of two roots is correct.

## Service-impact model

Access nodes represent synthetic service endpoints. A fault impacts all access
descendants in the hierarchy; an access fault affects only itself. Predicted
impact is the union of descendants for both predicted roots. Recall measures
coverage of truly impacted services, while Jaccard also penalizes overprediction.

Across the full balanced benchmark, temporal correlation improves exact root
pair match from 23.84% to 63.19% and root recall from 59.72% to 79.84%. Service
recall is 94.32% and service Jaccard is 84.19%.

## Interpretation limits

The experiment assumes exactly two fault starts separated by 30 seconds. The
fixed gap can merge incidents when false alarms bridge the windows or split a
long cascade when timing assumptions fail. Nested service sets overlap, making
service recall easier than exact root identification; therefore the repository
reports both recall and Jaccard. No real service inventory, subscriber data,
severity weighting, or financial impact is represented.
