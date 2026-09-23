from fastapi.testclient import TestClient

from telecom_twin.api import app


def test_api_exposes_synthetic_snapshot() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "data_mode": "synthetic", "node_count": 27}
    topology = client.get("/topology").json()
    assert len(topology["nodes"]) == 27
    assert len(topology["links"]) == 27
    assert len(client.get("/telemetry/latest").json()) == 27
    assert len(client.get("/experiments/protocols").json()) == 2
    assert len(client.get("/experiments/root-cause").json()) == 3
    assert len(client.get("/experiments/multi-fault").json()) == 12


def test_latest_telemetry_unknown_node_returns_empty_list() -> None:
    client = TestClient(app)
    assert client.get("/telemetry/latest", params={"node_id": "not-real"}).json() == []


def test_live_twin_rest_endpoints_and_dashboard() -> None:
    client = TestClient(app)
    reset = client.post("/live/reset")
    assert reset.status_code == 200
    assert reset.json()["timestamp_s"] == -1
    stepped = client.post("/live/step", params={"steps": 31}).json()
    assert stepped["timestamp_s"] == 30
    assert len(stepped["nodes"]) == 27
    assert all(node["telemetry"] is not None for node in stepped["nodes"])
    assert client.get("/live/events").status_code == 200
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Telecom Network Digital Twin" in dashboard.text
    client.post("/live/step", params={"steps": 270})
    stream = client.get("/live/stream", params={"interval_ms": 20})
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert stream.text.startswith("data: ")
