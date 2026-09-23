"""Generate a compact GIF from the real online digital-twin replay."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from telecom_twin.online import OnlineTwin


def export_demo_gif(destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    twin = OnlineTwin()
    by_id = {node.node_id: node for node in twin.nodes}
    frames: list[Image.Image] = []
    frame_times = list(range(0, 121, 15)) + list(range(123, 136, 2)) + [150, 183, 195, 225, 255, 300]
    previous = -1
    for timestamp in frame_times:
        twin.advance(timestamp - previous)
        previous = timestamp
        snapshot = twin.snapshot()
        active = {event.node_id for event in twin.current_anomalies}
        fig, axis = plt.subplots(figsize=(8.4, 5.2), facecolor="#07111f")
        axis.set_facecolor("#091727")
        for link in twin.links:
            source, target = by_id[link.source], by_id[link.target]
            axis.plot(
                [source.x, target.x],
                [source.y, target.y],
                color="#294562",
                linewidth=1.2,
                zorder=1,
            )
        for role, color, size in (
            ("core", "#8b5cf6", 150),
            ("aggregation", "#0ea5e9", 105),
            ("access", "#14b8a6", 60),
        ):
            nodes = [node for node in twin.nodes if node.role == role and node.node_id not in active]
            axis.scatter(
                [node.x for node in nodes],
                [node.y for node in nodes],
                color=color,
                s=size,
                edgecolor="#b8c9dc",
                linewidth=0.7,
                label=role,
                zorder=2,
            )
        active_nodes = [by_id[node_id] for node_id in active]
        if active_nodes:
            axis.scatter(
                [node.x for node in active_nodes],
                [node.y for node in active_nodes],
                color="#ef4444",
                s=145,
                edgecolor="#fecaca",
                linewidth=2.2,
                label="active anomaly",
                zorder=4,
            )
        target = by_id["access-07"]
        sample = twin.latest.get("access-07")
        latency = sample.latency_ms if sample else 0.0
        axis.annotate(
            f"access-07  {latency:.1f} ms",
            (target.x, target.y),
            xytext=(10, -24),
            textcoords="offset points",
            color="#f8fafc",
            fontsize=8,
            arrowprops={"arrowstyle": "-", "color": "#94a3b8"},
        )
        state = "INCIDENT" if 123 <= timestamp <= 183 else "NORMAL"
        state_color = "#fb923c" if state == "INCIDENT" else "#5eead4"
        axis.text(
            0.02,
            0.97,
            f"t = {timestamp:03d} s   {state}",
            transform=axis.transAxes,
            va="top",
            color=state_color,
            fontsize=13,
            fontweight="bold",
        )
        axis.text(
            0.02,
            0.91,
            f"cumulative detections: {snapshot['anomaly_count']}",
            transform=axis.transAxes,
            va="top",
            color="#cbd5e1",
            fontsize=9,
        )
        axis.set_title(
            "Streaming Telecom Network Digital Twin",
            color="#f8fafc",
            fontsize=17,
            pad=12,
        )
        axis.set_aspect("equal")
        axis.set_xlim(-1.08, 1.08)
        axis.set_ylim(-1.05, 1.05)
        axis.axis("off")
        legend = axis.legend(loc="lower left", frameon=False, ncol=2, fontsize=8)
        for text in legend.get_texts():
            text.set_color("#cbd5e1")
        fig.canvas.draw()
        width, height = fig.canvas.get_width_height()
        frame = Image.frombytes(
            "RGBA", (width, height), bytes(fig.canvas.buffer_rgba())
        ).convert("RGB")
        frames.append(frame)
        plt.close(fig)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=280,
        loop=0,
        optimize=True,
    )
    return path
