from telecom_twin.simulation import generate_alarms, generate_telemetry
from telecom_twin.topology import generate_topology


def test_incident_is_reproducible_and_localized() -> None:
    nodes, _ = generate_topology()
    first = generate_telemetry(nodes)
    second = generate_telemetry(nodes)
    assert first == second
    alarms = generate_alarms(first)
    assert alarms
    assert {alarm.node_id for alarm in alarms} == {"access-07"}
    assert min(alarm.timestamp_s for alarm in alarms) > 123
    assert max(alarm.timestamp_s for alarm in alarms) <= 183
