"""Multi-fault alarm correlation and synthetic service-impact analysis."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telecom_twin.models import NetworkLink, NetworkNode
from telecom_twin.robustness import TimedAlarm, descendant_distances, rank_with_time
from telecom_twin.root_cause import descendants, hierarchy_children
from telecom_twin.topology import generate_topology


@dataclass(frozen=True)
class MultiFaultScenario:
    scenario_id: str
    scenario_kind: str
    roots: tuple[str, str]
    start_times_s: tuple[float, float] = (100.0, 130.0)


SCENARIOS = (
    MultiFaultScenario("independent-01", "independent", ("access-02", "access-07")),
    MultiFaultScenario("independent-02", "independent", ("access-02", "aggregation-03")),
    MultiFaultScenario("independent-03", "independent", ("aggregation-01", "aggregation-04")),
    MultiFaultScenario("independent-04", "independent", ("core-01", "access-12")),
    MultiFaultScenario("independent-05", "independent", ("core-01", "core-03")),
    MultiFaultScenario("independent-06", "independent", ("aggregation-02", "access-16")),
    MultiFaultScenario("nested-01", "nested", ("aggregation-01", "access-02")),
    MultiFaultScenario("nested-02", "nested", ("core-01", "aggregation-01")),
    MultiFaultScenario("nested-03", "nested", ("core-01", "access-03")),
    MultiFaultScenario("nested-04", "nested", ("core-02", "aggregation-04")),
    MultiFaultScenario("nested-05", "nested", ("aggregation-05", "access-14")),
    MultiFaultScenario("nested-06", "nested", ("core-03", "access-18")),
)


def affected_services(
    roots: tuple[str, ...], nodes: list[NetworkNode], links: list[NetworkLink]
) -> set[str]:
    """Map root causes to synthetic access-service endpoints downstream."""
    children = hierarchy_children(links)
    access_ids = {node.node_id for node in nodes if node.role == "access"}
    impacted: set[str] = set()
    for root in roots:
        impacted.update(descendants(root, children) & access_ids)
    return impacted


def generate_multi_fault_alarms(
    scenario: MultiFaultScenario,
    nodes: list[NetworkNode],
    links: list[NetworkLink],
    *,
    missing_rate: float,
    false_alarm_count: int,
    seed: int,
) -> list[TimedAlarm]:
    """Generate two temporally separated causal alarm cascades plus noise."""
    randomizer = random.Random(seed)
    children = hierarchy_children(links)
    causal_nodes: set[str] = set()
    alarms: list[TimedAlarm] = []
    for root, start_time in zip(scenario.roots, scenario.start_times_s, strict=True):
        distances = descendant_distances(root, children)
        causal_nodes.update(distances)
        alarms.extend(
            TimedAlarm(
                node_id,
                start_time + 3.0 * distance + randomizer.uniform(-0.45, 0.45),
            )
            for node_id, distance in sorted(distances.items())
            if randomizer.random() >= missing_rate
        )
    unaffected = sorted({node.node_id for node in nodes} - causal_nodes)
    for node_id in randomizer.sample(
        unaffected, k=min(false_alarm_count, len(unaffected))
    ):
        center = randomizer.choice(scenario.start_times_s)
        alarms.append(TimedAlarm(node_id, center + randomizer.uniform(-2.0, 8.0)))
    return sorted(alarms, key=lambda alarm: (alarm.timestamp_s, alarm.node_id))


def temporal_clusters(alarms: list[TimedAlarm], *, gap_s: float = 12.0) -> list[list[TimedAlarm]]:
    """Group alarms into incident windows using only timestamp gaps."""
    if not alarms:
        return []
    ordered = sorted(alarms, key=lambda alarm: (alarm.timestamp_s, alarm.node_id))
    clusters = [[ordered[0]]]
    for alarm in ordered[1:]:
        if alarm.timestamp_s - clusters[-1][-1].timestamp_s > gap_s:
            clusters.append([])
        clusters[-1].append(alarm)
    return clusters


def correlate_root_causes(
    alarms: list[TimedAlarm],
    nodes: list[NetworkNode],
    links: list[NetworkLink],
    *,
    expected_faults: int = 2,
) -> list[str]:
    """Rank one cause per temporal incident cluster, then return unique causes."""
    candidates: list[tuple[float, str]] = []
    for cluster in temporal_clusters(alarms):
        ranking = rank_with_time(cluster, nodes, links)
        if ranking:
            top = ranking[0]
            evidence_weight = min(1.0, len(cluster) / 3.0)
            candidates.append((float(top["score"]) * evidence_weight, str(top["candidate"])))
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) == expected_faults:
            break
    if len(selected) < expected_faults:
        global_ranking = rank_with_time(alarms, nodes, links)
        for row in global_ranking:
            candidate = str(row["candidate"])
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) == expected_faults:
                break
    return selected


def _set_metrics(expected: set[str], predicted: set[str]) -> tuple[float, float]:
    recall = len(expected & predicted) / len(expected)
    union = expected | predicted
    jaccard = len(expected & predicted) / len(union) if union else 1.0
    return recall, jaccard


def run_multi_fault_trials(
    nodes: list[NetworkNode],
    links: list[NetworkLink],
    *,
    trials_per_scenario: int = 20,
    missing_rates: tuple[float, ...] = (0.0, 0.2, 0.4),
    false_alarm_counts: tuple[int, ...] = (0, 2, 4),
) -> list[dict]:
    rows = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        true_roots = set(scenario.roots)
        true_services = affected_services(scenario.roots, nodes, links)
        for missing_rate in missing_rates:
            for false_alarm_count in false_alarm_counts:
                for trial in range(trials_per_scenario):
                    seed = (
                        scenario_index * 100000
                        + int(missing_rate * 10) * 10000
                        + false_alarm_count * 100
                        + trial
                    )
                    alarms = generate_multi_fault_alarms(
                        scenario,
                        nodes,
                        links,
                        missing_rate=missing_rate,
                        false_alarm_count=false_alarm_count,
                        seed=seed,
                    )
                    global_roots = [
                        str(row["candidate"])
                        for row in rank_with_time(alarms, nodes, links)[:2]
                    ]
                    correlated_roots = correlate_root_causes(alarms, nodes, links)
                    global_recall, _ = _set_metrics(true_roots, set(global_roots))
                    correlated_recall, _ = _set_metrics(true_roots, set(correlated_roots))
                    predicted_services = affected_services(
                        tuple(correlated_roots), nodes, links
                    )
                    service_recall, service_jaccard = _set_metrics(
                        true_services, predicted_services
                    )
                    rows.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "scenario_kind": scenario.scenario_kind,
                            "true_roots": ";".join(scenario.roots),
                            "missing_rate": missing_rate,
                            "false_alarm_count": false_alarm_count,
                            "trial": trial,
                            "observed_alarm_count": len(alarms),
                            "global_predicted_roots": ";".join(global_roots),
                            "correlated_predicted_roots": ";".join(correlated_roots),
                            "global_root_recall": global_recall,
                            "correlated_root_recall": correlated_recall,
                            "global_exact_match": float(set(global_roots) == true_roots),
                            "correlated_exact_match": float(
                                set(correlated_roots) == true_roots
                            ),
                            "true_service_count": len(true_services),
                            "predicted_service_count": len(predicted_services),
                            "service_recall": service_recall,
                            "service_jaccard": service_jaccard,
                        }
                    )
    return rows


def summarize_multi_fault_trials(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, float, int], list[dict]] = {}
    for row in rows:
        key = (
            str(row["scenario_kind"]),
            float(row["missing_rate"]),
            int(row["false_alarm_count"]),
        )
        groups.setdefault(key, []).append(row)
    summary = []
    for (kind, missing_rate, false_count), group in sorted(groups.items()):
        count = len(group)
        summary.append(
            {
                "scenario_kind": kind,
                "missing_rate": missing_rate,
                "false_alarm_count": false_count,
                "trial_count": count,
                "global_exact_match": sum(row["global_exact_match"] for row in group)
                / count,
                "correlated_exact_match": sum(
                    row["correlated_exact_match"] for row in group
                )
                / count,
                "global_root_recall": sum(row["global_root_recall"] for row in group)
                / count,
                "correlated_root_recall": sum(
                    row["correlated_root_recall"] for row in group
                )
                / count,
                "service_recall": sum(row["service_recall"] for row in group) / count,
                "service_jaccard": sum(row["service_jaccard"] for row in group) / count,
            }
        )
    return summary


def multi_fault_metrics(summary: list[dict]) -> dict[str, float]:
    def mean(metric: str, subset: list[dict] = summary) -> float:
        return sum(float(row[metric]) for row in subset) / len(subset)

    worst_missing = max(float(row["missing_rate"]) for row in summary)
    worst_false = max(int(row["false_alarm_count"]) for row in summary)
    worst = [
        row
        for row in summary
        if float(row["missing_rate"]) == worst_missing
        and int(row["false_alarm_count"]) == worst_false
    ]
    return {
        "trial_count": sum(int(row["trial_count"]) for row in summary),
        "global_exact_match": mean("global_exact_match"),
        "correlated_exact_match": mean("correlated_exact_match"),
        "global_root_recall": mean("global_root_recall"),
        "correlated_root_recall": mean("correlated_root_recall"),
        "service_recall": mean("service_recall"),
        "service_jaccard": mean("service_jaccard"),
        "worst_noise_correlated_exact_match": mean("correlated_exact_match", worst),
        "worst_noise_service_recall": mean("service_recall", worst),
    }


def _write_rows(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def plot_multi_fault(summary: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for axis, kind in zip(axes, ("independent", "nested"), strict=True):
        subset = [row for row in summary if row["scenario_kind"] == kind]
        labels = ["0% / 0", "20% / 2", "40% / 4"]
        settings = [(0.0, 0), (0.2, 2), (0.4, 4)]
        selected = [
            next(
                row
                for row in subset
                if row["missing_rate"] == missing and row["false_alarm_count"] == false
            )
            for missing, false in settings
        ]
        x_values = list(range(len(selected)))
        axis.bar(
            [value - 0.18 for value in x_values],
            [row["global_exact_match"] for row in selected],
            width=0.36,
            label="Global Top-2",
            color="#94a3b8",
        )
        axis.bar(
            [value + 0.18 for value in x_values],
            [row["correlated_exact_match"] for row in selected],
            width=0.36,
            label="Temporal correlation",
            color="#2563eb",
        )
        axis.plot(
            x_values,
            [row["service_recall"] for row in selected],
            "o-",
            color="#ea580c",
            label="Service recall",
        )
        axis.set_xticks(x_values, labels)
        axis.set(
            title=f"{kind.capitalize()} fault pairs",
            xlabel="Missing alarms / false alarms",
            ylim=(0.0, 1.05),
        )
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Accuracy / recall")
    axes[1].legend(fontsize=8, loc="lower left")
    fig.suptitle("Dual-fault localization and downstream service impact")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_multi_fault_benchmark(
    output_dir: str | Path, *, trials_per_scenario: int = 20
) -> dict[str, Path]:
    output = Path(output_dir)
    nodes, links = generate_topology()
    trials = run_multi_fault_trials(
        nodes, links, trials_per_scenario=trials_per_scenario
    )
    summary = summarize_multi_fault_trials(trials)
    metrics = multi_fault_metrics(summary)
    return {
        "trials": _write_rows(trials, output / "multi_fault_trials.csv"),
        "summary": _write_rows(summary, output / "multi_fault_summary.csv"),
        "metrics": _write_rows(
            [{"metric": key, "value": value} for key, value in metrics.items()],
            output / "multi_fault_metrics.csv",
        ),
        "figure": plot_multi_fault(summary, output / "figures" / "multi_fault_analysis.png"),
    }
