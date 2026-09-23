from telecom_twin.topology import generate_topology, topology_is_connected


def test_topology_is_deterministic_connected_and_hierarchical() -> None:
    nodes, links = generate_topology()
    assert len(nodes) == 27
    assert len(links) == 27
    assert topology_is_connected(nodes, links)
    roles = [node.role for node in nodes]
    assert roles.count("core") == 3
    assert roles.count("aggregation") == 6
    assert roles.count("access") == 18
    assert all(node.region.startswith("synthetic-") for node in nodes)
