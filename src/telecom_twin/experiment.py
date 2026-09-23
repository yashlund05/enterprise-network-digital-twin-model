"""Experiment orchestration and deterministic result artifacts."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from telecom_twin.protocols import compare_protocols
from telecom_twin.root_cause import evaluate_root_cause
from telecom_twin.simulation import generate_alarms, generate_telemetry
from telecom_twin.topology import generate_topology

matplotlib.use("Agg")


def write_rows(rows: list[dict], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def run_experiment(output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    nodes, links = generate_topology()
    samples = generate_telemetry(nodes)
    alarms = generate_alarms(samples)
    strategies = compare_protocols(samples)
    root_cause_rows = evaluate_root_cause(nodes, links)
    telemetry_path = write_rows([sample.to_dict() for sample in samples], output / "telemetry.csv")
    alarms_path = write_rows([alarm.to_dict() for alarm in alarms], output / "alarms.csv")
    protocol_path = write_rows(strategies, output / "protocol_comparison.csv")
    root_cause_path = write_rows(root_cause_rows, output / "root_cause_evaluation.csv")
    figure_path = plot_experiment(nodes, links, strategies, output / "figures" / "mvp_summary.png")
    return {
        "telemetry": telemetry_path,
        "alarms": alarms_path,
        "protocol_comparison": protocol_path,
        "root_cause_evaluation": root_cause_path,
        "figure": figure_path,
    }


def plot_experiment(nodes, links, strategies: list[dict], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    by_id = {node.node_id: node for node in nodes}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for link in links:
        source, target = by_id[link.source], by_id[link.target]
        axes[0].plot([source.x, target.x], [source.y, target.y], color="0.78", linewidth=0.8)
    colors = {"core": "#d62728", "aggregation": "#ff7f0e", "access": "#1f77b4"}
    for role, color in colors.items():
        subset = [node for node in nodes if node.role == role]
        axes[0].scatter(
            [node.x for node in subset],
            [node.y for node in subset],
            label=role,
            s=70 if role == "core" else 42,
            color=color,
            zorder=3,
        )
    axes[0].set_aspect("equal")
    axes[0].set(title="Synthetic three-tier topology", xlabel="normalized x", ylabel="normalized y")
    axes[0].legend()
    labels = [row["strategy"].replace("_", "\n") for row in strategies]
    message_values = [row["messages"] for row in strategies]
    byte_values = [row["transferred_bytes"] / 1000 for row in strategies]
    x_values = range(len(strategies))
    axes[1].bar([value - 0.18 for value in x_values], message_values, width=0.36, label="Messages")
    axes[1].bar([value + 0.18 for value in x_values], byte_values, width=0.36, label="Transferred kB")
    axes[1].set_xticks(list(x_values), labels)
    axes[1].set(title="Management-plane cost", ylabel="count / kB")
    axes[1].legend()
    for axis in axes:
        axis.grid(alpha=0.22)
    fig.suptitle("Synthetic telecom digital twin - deterministic MVP")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
