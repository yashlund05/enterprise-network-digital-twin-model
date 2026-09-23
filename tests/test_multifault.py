from pathlib import Path

from telecom_twin.multifault import (
    SCENARIOS,
    affected_services,
    correlate_root_causes,
    generate_multi_fault_alarms,
    run_multi_fault_benchmark,
    run_multi_fault_trials,
)
from telecom_twin.topology import generate_topology


def test_service_impact_follows_hierarchy() -> None:
    nodes, links = generate_topology()
    assert affected_services(("access-02",), nodes, links) == {"access-02"}
    assert affected_services(("aggregation-01",), nodes, links) == {
        "access-01",
        "access-02",
        "access-03",
    }
    assert len(affected_services(("core-01",), nodes, links)) == 6


def test_temporal_correlation_finds_clean_independent_pair() -> None:
    nodes, links = generate_topology()
    scenario = SCENARIOS[2]
    alarms = generate_multi_fault_alarms(
        scenario, nodes, links, missing_rate=0.0, false_alarm_count=0, seed=10
    )
    assert set(correlate_root_causes(alarms, nodes, links)) == set(scenario.roots)


def test_multi_fault_trials_are_deterministic() -> None:
    nodes, links = generate_topology()
    first = run_multi_fault_trials(
        nodes,
        links,
        trials_per_scenario=1,
        missing_rates=(0.0,),
        false_alarm_counts=(0,),
    )
    second = run_multi_fault_trials(
        nodes,
        links,
        trials_per_scenario=1,
        missing_rates=(0.0,),
        false_alarm_counts=(0,),
    )
    assert first == second
    assert len(first) == len(SCENARIOS)


def test_multi_fault_benchmark_exports_artifacts(tmp_path: Path) -> None:
    outputs = run_multi_fault_benchmark(tmp_path, trials_per_scenario=1)
    assert set(outputs) == {"trials", "summary", "metrics", "figure"}
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
