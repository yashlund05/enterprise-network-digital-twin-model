"""Monte Carlo robustness benchmark for topology-aware root-cause ranking."""

from __future__ import annotations

import csv
import math
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from telecom_twin.models import NetworkLink, NetworkNode
from telecom_twin.root_cause import hierarchy_children, rank_root_causes

matplotlib.use("Agg")


@dataclass(frozen=True)
class TimedAlarm:
    node_id: str
    timestamp_s: float


def descendant_distances(root: str, children: dict[str, set[str]]) -> dict[str, int]:
    """Return downstream hop distance including zero for the candidate root."""
    distances = {root: 0}
    frontier = deque([root])
    while frontier:
        node = frontier.popleft()
        for child in children.get(node, set()):
            if child not in distances:
                distances[child] = distances[node] + 1
                frontier.append(child)
    return distances


def generate_timed_alarms(
    root: str,
    nodes: list[NetworkNode],
    links: list[NetworkLink],
    *,
    missing_rate: float,
    false_alarm_count: int,
    seed: int,
) -> list[TimedAlarm]:
    """Generate causal downstream alarms plus controlled missing and false alarms."""
    randomizer = random.Random(seed)
    children = hierarchy_children(links)
    distances = descendant_distances(root, children)
    observed = [
        TimedAlarm(node_id, 100.0 + 3.0 * depth + randomizer.uniform(-0.45, 0.45))
        for node_id, depth in sorted(distances.items())
        if randomizer.random() >= missing_rate
    ]
    unaffected = sorted({node.node_id for node in nodes} - set(distances))
    for node_id in randomizer.sample(unaffected, k=min(false_alarm_count, len(unaffected))):
        observed.append(TimedAlarm(node_id, randomizer.uniform(96.0, 112.0)))
    return sorted(observed, key=lambda alarm: (alarm.timestamp_s, alarm.node_id))


def rank_with_time(
    alarms: list[TimedAlarm], nodes: list[NetworkNode], links: list[NetworkLink]
) -> list[dict[str, float | str]]:
    """Add propagation-time coherence to the existing topology evidence score."""
    observed_ids = tuple(sorted({alarm.node_id for alarm in alarms}))
    timestamps = {alarm.node_id: alarm.timestamp_s for alarm in alarms}
    children = hierarchy_children(links)
    topology = {str(row["candidate"]): row for row in rank_root_causes(observed_ids, nodes, links)}
    rows = []
    for node in nodes:
        distances = descendant_distances(node.node_id, children)
        explained = [node_id for node_id in observed_ids if node_id in distances]
        origin_estimates = [timestamps[node_id] - 3.0 * distances[node_id] for node_id in explained]
        if len(origin_estimates) >= 2:
            mean = sum(origin_estimates) / len(origin_estimates)
            variance = sum((value - mean) ** 2 for value in origin_estimates) / len(origin_estimates)
            coherence = math.exp(-math.sqrt(variance) / 2.5)
        elif origin_estimates:
            coherence = 0.55
        else:
            coherence = 0.0
        baseline = topology[node.node_id]
        score = 0.82 * float(baseline["score"]) + 0.18 * coherence
        rows.append(
            {
                **baseline,
                "temporal_coherence": coherence,
                "score": score,
            }
        )
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["candidate"])))


def run_trials(
    nodes: list[NetworkNode],
    links: list[NetworkLink],
    *,
    trials_per_root: int = 20,
    missing_rates: tuple[float, ...] = (0.0, 0.2, 0.4),
    false_alarm_counts: tuple[int, ...] = (0, 2, 4),
) -> list[dict[str, float | int | str]]:
    """Run a balanced-by-reporting-stratum deterministic benchmark matrix."""
    rows = []
    for node_index, node in enumerate(nodes):
        for missing_rate in missing_rates:
            for false_alarm_count in false_alarm_counts:
                for trial in range(trials_per_root):
                    seed = 100000 * node_index + 10000 * int(missing_rate * 10) + 100 * false_alarm_count + trial
                    alarms = generate_timed_alarms(
                        node.node_id,
                        nodes,
                        links,
                        missing_rate=missing_rate,
                        false_alarm_count=false_alarm_count,
                        seed=seed,
                    )
                    observed_ids = tuple(sorted({alarm.node_id for alarm in alarms}))
                    topology_ids = [
                        str(row["candidate"])
                        for row in rank_root_causes(observed_ids, nodes, links)
                    ]
                    temporal_ids = [str(row["candidate"]) for row in rank_with_time(alarms, nodes, links)]
                    topology_rank = topology_ids.index(node.node_id) + 1
                    temporal_rank = temporal_ids.index(node.node_id) + 1
                    rows.append(
                        {
                            "root_role": node.role,
                            "root_cause": node.node_id,
                            "missing_rate": missing_rate,
                            "false_alarm_count": false_alarm_count,
                            "trial": trial,
                            "observed_alarm_count": len(alarms),
                            "topology_rank": topology_rank,
                            "temporal_rank": temporal_rank,
                        }
                    )
    return rows


def summarize_trials(rows: list[dict]) -> list[dict[str, float | int | str]]:
    groups: dict[tuple[str, float, int], list[dict]] = {}
    for row in rows:
        key = (str(row["root_role"]), float(row["missing_rate"]), int(row["false_alarm_count"]))
        groups.setdefault(key, []).append(row)
    summaries = []
    for (role, missing_rate, false_alarm_count), group in sorted(groups.items()):
        count = len(group)
        summaries.append(
            {
                "root_role": role,
                "missing_rate": missing_rate,
                "false_alarm_count": false_alarm_count,
                "trial_count": count,
                "topology_top1_accuracy": sum(row["topology_rank"] == 1 for row in group) / count,
                "temporal_top1_accuracy": sum(row["temporal_rank"] == 1 for row in group) / count,
                "topology_top3_accuracy": sum(row["topology_rank"] <= 3 for row in group) / count,
                "temporal_top3_accuracy": sum(row["temporal_rank"] <= 3 for row in group) / count,
            }
        )
    return summaries


def benchmark_metrics(summary: list[dict]) -> dict[str, float]:
    """Macro-average roles so the access tier cannot dominate the headline metric."""
    by_role: dict[str, list[dict]] = {}
    for row in summary:
        by_role.setdefault(str(row["root_role"]), []).append(row)

    def macro(metric: str) -> float:
        role_means = [
            sum(float(row[metric]) for row in role_rows) / len(role_rows)
            for role_rows in by_role.values()
        ]
        return sum(role_means) / len(role_means)

    maximum_missing_rate = max(float(row["missing_rate"]) for row in summary)
    maximum_false_alarm_count = max(int(row["false_alarm_count"]) for row in summary)
    worst = [
        row
        for row in summary
        if float(row["missing_rate"]) == maximum_missing_rate
        and int(row["false_alarm_count"]) == maximum_false_alarm_count
    ]
    return {
        "trial_count": sum(int(row["trial_count"]) for row in summary),
        "topology_macro_top1_accuracy": macro("topology_top1_accuracy"),
        "temporal_macro_top1_accuracy": macro("temporal_top1_accuracy"),
        "topology_macro_top3_accuracy": macro("topology_top3_accuracy"),
        "temporal_macro_top3_accuracy": macro("temporal_top3_accuracy"),
        "topology_worst_noise_macro_top1": sum(float(row["topology_top1_accuracy"]) for row in worst) / len(worst),
        "temporal_worst_noise_macro_top1": sum(float(row["temporal_top1_accuracy"]) for row in worst) / len(worst),
    }


def write_rows(rows: list[dict], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def plot_benchmark(summary: list[dict], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True, constrained_layout=True)
    for axis, role in zip(axes, ("access", "aggregation", "core"), strict=True):
        subset = [row for row in summary if row["root_role"] == role]
        for false_count, color in zip((0, 2, 4), ("#2ca02c", "#ff7f0e", "#d62728"), strict=True):
            line = sorted(
                (row for row in subset if int(row["false_alarm_count"]) == false_count),
                key=lambda row: float(row["missing_rate"]),
            )
            axis.plot(
                [100 * float(row["missing_rate"]) for row in line],
                [float(row["temporal_top1_accuracy"]) for row in line],
                "o-",
                color=color,
                label=f"{false_count} false alarms",
            )
            axis.plot(
                [100 * float(row["missing_rate"]) for row in line],
                [float(row["topology_top1_accuracy"]) for row in line],
                "--",
                color=color,
                alpha=0.65,
            )
        axis.set(title=f"{role.capitalize()} roots", xlabel="Missing alarms (%)", ylim=(-0.03, 1.03))
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Top-1 accuracy")
    axes[2].legend(fontsize=8, title="Solid: temporal\nDashed: topology")
    fig.suptitle("Root-cause robustness - 4,860 deterministic trials")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_benchmark(output_dir: str | Path, *, trials_per_root: int = 20) -> dict[str, Path]:
    from telecom_twin.topology import generate_topology

    output = Path(output_dir)
    nodes, links = generate_topology()
    trials = run_trials(nodes, links, trials_per_root=trials_per_root)
    summary = summarize_trials(trials)
    metrics = benchmark_metrics(summary)
    return {
        "trials": write_rows(trials, output / "root_cause_trials.csv"),
        "summary": write_rows(summary, output / "root_cause_robustness.csv"),
        "metrics": write_rows(
            [{"metric": key, "value": value} for key, value in metrics.items()],
            output / "root_cause_robustness_metrics.csv",
        ),
        "figure": plot_benchmark(summary, output / "figures" / "root_cause_robustness.png"),
    }
