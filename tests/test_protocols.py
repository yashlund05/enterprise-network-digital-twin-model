from telecom_twin.protocols import simulate_adaptive_delta, simulate_fixed_polling
from telecom_twin.simulation import generate_telemetry
from telecom_twin.topology import generate_topology


def test_adaptive_delta_reduces_cost_and_detects_faster() -> None:
    nodes, _ = generate_topology()
    samples = generate_telemetry(nodes)
    fixed = simulate_fixed_polling(samples)
    adaptive = simulate_adaptive_delta(samples)
    assert adaptive.messages < fixed.messages * 0.5
    assert adaptive.transferred_bytes < fixed.transferred_bytes * 0.3
    assert adaptive.first_detection_delay_s < fixed.first_detection_delay_s
    assert adaptive.alarm_episode_recall == 1.0
    assert fixed.alarm_episode_recall == 1.0
