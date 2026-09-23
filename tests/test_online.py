from pathlib import Path

import pytest

from telecom_twin.online import OnlineTwin, RollingAnomalyDetector, export_online_evaluation


def test_online_twin_replay_detects_declared_incident() -> None:
    twin = OnlineTwin()
    initial = twin.snapshot()
    assert initial["timestamp_s"] == -1
    assert all(node["telemetry"] is None for node in initial["nodes"])
    final = twin.run_to_completion()
    assert final["complete"] is True
    assert final["timestamp_s"] == 300
    target = [event for event in twin.events if event.node_id == "access-07"]
    assert target
    assert min(event.timestamp_s for event in target) <= 125


def test_online_replay_is_deterministic_and_validates_inputs() -> None:
    first = OnlineTwin()
    second = OnlineTwin()
    first.run_to_completion()
    second.run_to_completion()
    assert first.events == second.events
    with pytest.raises(ValueError):
        first.advance(0)
    with pytest.raises(ValueError):
        RollingAnomalyDetector(window_size=10, warmup=11)


def test_online_evaluation_exports_portable_artifacts(tmp_path: Path) -> None:
    outputs = export_online_evaluation(tmp_path)
    assert set(outputs) == {"metrics", "events", "figure"}
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
    metrics = outputs["metrics"].read_text(encoding="utf-8")
    assert "detection_delay_s" in metrics
    assert "false_events_per_1000_node_seconds" in metrics
