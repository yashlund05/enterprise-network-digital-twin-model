from telecom_twin.root_cause import (
    build_scenarios,
    evaluate_root_cause,
    hierarchy_children,
    rank_root_causes,
)
from telecom_twin.topology import generate_topology


def test_scenarios_are_deterministic_and_include_noise() -> None:
    nodes, links = generate_topology()
    first = build_scenarios(nodes, links)
    assert first == build_scenarios(nodes, links)
    assert [scenario.root_cause for scenario in first] == [
        "access-07",
        "aggregation-03",
        "core-02",
    ]
    assert len(first[2].observed_alarms) != len(first[2].affected_nodes)


def test_same_tier_core_ring_is_not_a_causal_parent_edge() -> None:
    _, links = generate_topology()
    children = hierarchy_children(links)
    assert "core-02" not in children["core-01"]
    assert "aggregation-01" in children["core-01"]


def test_empty_alarm_set_returns_deterministic_no_evidence_ranking() -> None:
    nodes, links = generate_topology()
    ranking = rank_root_causes((), nodes, links)
    assert len(ranking) == len(nodes)
    assert all(row["score"] == 0 for row in ranking)


def test_topology_aware_root_cause_finds_all_three_roots() -> None:
    nodes, links = generate_topology()
    rows = evaluate_root_cause(nodes, links)
    assert len(rows) == 3
    assert all(row["top1_correct"] == 1.0 for row in rows)
    assert all(row["top3_correct"] == 1.0 for row in rows)
