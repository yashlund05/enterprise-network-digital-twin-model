from telecom_twin.robustness import (
    benchmark_metrics,
    descendant_distances,
    generate_timed_alarms,
    run_trials,
    summarize_trials,
)
from telecom_twin.root_cause import hierarchy_children
from telecom_twin.topology import generate_topology


def test_distances_follow_only_the_causal_hierarchy() -> None:
    _, links = generate_topology()
    distances = descendant_distances("core-02", hierarchy_children(links))
    assert distances["core-02"] == 0
    assert distances["aggregation-03"] == 1
    assert distances["access-07"] == 2
    assert "core-01" not in distances


def test_timed_alarm_generation_is_reproducible() -> None:
    nodes, links = generate_topology()
    first = generate_timed_alarms(
        "aggregation-03", nodes, links, missing_rate=0.4, false_alarm_count=2, seed=17
    )
    assert first == generate_timed_alarms(
        "aggregation-03", nodes, links, missing_rate=0.4, false_alarm_count=2, seed=17
    )
    assert len({alarm.node_id for alarm in first}) == len(first)


def test_single_access_alarm_can_be_completely_missing() -> None:
    nodes, links = generate_topology()
    alarms = generate_timed_alarms(
        "access-07", nodes, links, missing_rate=1.0, false_alarm_count=0, seed=3
    )
    assert alarms == []


def test_small_benchmark_has_expected_shape_and_finite_metrics() -> None:
    nodes, links = generate_topology()
    trials = run_trials(
        nodes,
        links,
        trials_per_root=2,
        missing_rates=(0.0, 0.4),
        false_alarm_counts=(0, 2),
    )
    assert len(trials) == 27 * 2 * 2 * 2
    summary = summarize_trials(trials)
    assert len(summary) == 3 * 2 * 2
    metrics = benchmark_metrics(summary)
    assert metrics["trial_count"] == len(trials)
    assert 0 <= metrics["temporal_macro_top1_accuracy"] <= 1
