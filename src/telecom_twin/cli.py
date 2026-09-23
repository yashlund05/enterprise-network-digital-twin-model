"""Command-line entry points."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from telecom_twin.demo import export_demo_gif
from telecom_twin.experiment import run_experiment
from telecom_twin.multifault import run_multi_fault_benchmark
from telecom_twin.online import export_online_evaluation
from telecom_twin.robustness import run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Digital twin network operations and monitoring CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Legacy commands
    experiment = subparsers.add_parser("experiment", help="Run baseline protocol experiments")
    experiment.add_argument("--output-dir", type=Path, default=Path("results"))

    serve = subparsers.add_parser("serve", help="Start legacy synthetic telecom API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    benchmark = subparsers.add_parser("benchmark", help="Run topology and RCA robustness benchmark")
    benchmark.add_argument("--output-dir", type=Path, default=Path("results"))
    benchmark.add_argument("--trials-per-root", type=int, default=20)

    online = subparsers.add_parser("online-evaluation", help="Run online anomaly detector evaluation")
    online.add_argument("--output-dir", type=Path, default=Path("results"))

    multifault = subparsers.add_parser(
        "multi-fault-benchmark", help="Run multi-fault RCA benchmark trials"
    )
    multifault.add_argument("--output-dir", type=Path, default=Path("results"))
    multifault.add_argument("--trials-per-scenario", type=int, default=20)

    demo = subparsers.add_parser("demo-gif", help="Export animated simulation demo GIF")
    demo.add_argument(
        "--output", type=Path, default=Path("results/figures/live_twin_demo.gif")
    )

    # Phase 8: Enterprise commands
    ent_serve = subparsers.add_parser(
        "enterprise-serve", help="Start enterprise digital twin FastAPI server"
    )
    ent_serve.add_argument("--host", default="127.0.0.1", help="Server host address")
    ent_serve.add_argument("--port", type=int, default=8000, help="Server port")

    whatif = subparsers.add_parser(
        "whatif-sim", help="Run deterministic counterfactual What-If simulation"
    )
    whatif.add_argument(
        "--target-type",
        choices=["node", "link"],
        default="node",
        help="Target element type (node or link)",
    )
    whatif.add_argument(
        "--target-id",
        type=str,
        required=True,
        help="Target node or link identifier (e.g. 'core-sw-01' or 'core-sw-01<->dist-sw-dc-01')",
    )
    whatif.add_argument(
        "--failure-type",
        type=str,
        default="node_down",
        help="Failure or degradation type (e.g. node_down, latency_spike, packet_loss)",
    )
    whatif.add_argument(
        "--parameter-value",
        type=float,
        default=1.0,
        help="Perturbation magnitude (e.g. latency in ms, loss in %)",
    )
    whatif.add_argument(
        "--scenario-id",
        type=str,
        default="cli-whatif-001",
        help="Custom scenario identifier",
    )

    ent_eval = subparsers.add_parser(
        "enterprise-evaluation",
        help="Enterprise evaluation engine status and benchmarking (Phase 10)",
    )
    ent_eval.add_argument("--output-dir", type=Path, default=Path("results"))

    args = parser.parse_args(argv)

    if args.command == "experiment":
        for name, path in run_experiment(args.output_dir).items():
            print(f"{name}: {path}")
        return 0

    if args.command == "serve":
        uvicorn.run("telecom_twin.api:app", host=args.host, port=args.port)
        return 0

    if args.command == "benchmark":
        for name, path in run_benchmark(
            args.output_dir, trials_per_root=args.trials_per_root
        ).items():
            print(f"{name}: {path}")
        return 0

    if args.command == "online-evaluation":
        for name, path in export_online_evaluation(args.output_dir).items():
            print(f"{name}: {path}")
        return 0

    if args.command == "multi-fault-benchmark":
        for name, path in run_multi_fault_benchmark(
            args.output_dir, trials_per_scenario=args.trials_per_scenario
        ).items():
            print(f"{name}: {path}")
        return 0

    if args.command == "demo-gif":
        print(f"gif: {export_demo_gif(args.output)}")
        return 0

    if args.command == "enterprise-serve":
        uvicorn.run("telecom_twin.api:app", host=args.host, port=args.port)
        return 0

    if args.command == "whatif-sim":
        from telecom_twin.enterprise_topology import generate_enterprise_topology
        from telecom_twin.models import WhatIfScenario
        from telecom_twin.whatif import WhatIfSimulator

        nodes, _links = generate_enterprise_topology()
        known_nodes = {n.node_id for n in nodes}

        # Validation
        if args.target_type == "node" and args.target_id not in known_nodes:
            print(
                f"Error: Unknown enterprise node '{args.target_id}'. Known nodes: {sorted(known_nodes)}",
                file=sys.stderr,
            )
            return 1

        if args.target_type == "link":
            target_str = args.target_id.strip()
            endpoints = None
            if "<->" in target_str:
                u, v = target_str.split("<->", 1)
                endpoints = (u.strip(), v.strip())
            elif "--" in target_str:
                u, v = target_str.split("--", 1)
                endpoints = (u.strip(), v.strip())
            if not endpoints or endpoints[0] not in known_nodes or endpoints[1] not in known_nodes:
                print(
                    f"Error: Invalid enterprise link '{args.target_id}'. Endpoints must be known nodes.",
                    file=sys.stderr,
                )
                return 1

        if args.parameter_value < 0:
            print("Error: --parameter-value must be non-negative.", file=sys.stderr)
            return 1

        scenario = WhatIfScenario(
            scenario_id=args.scenario_id,
            name=f"CLI What-If {args.failure_type} on {args.target_id}",
            target_type=args.target_type,
            target_id=args.target_id,
            failure_type=args.failure_type,
            parameter_value=float(args.parameter_value),
        )

        simulator = WhatIfSimulator()
        result = simulator.simulate(scenario)

        print("=" * 60)
        print("WHAT-IF COUNTERFACTUAL SIMULATION RESULT")
        print("=" * 60)
        print(f"Scenario ID:         {scenario.scenario_id}")
        print(f"Target:              {scenario.target_id} ({scenario.target_type})")
        print(f"Failure Type:        {scenario.failure_type} (value: {scenario.parameter_value})")
        print(f"Predicted Severity:  {result.severity}")
        print(f"Blast Radius:        {result.blast_radius_percent:.1f}%")
        print(f"Latency Delta:       +{result.latency_delta_ms:.2f} ms")
        print(f"Loss Delta:          +{result.loss_delta_percent:.2f}%")
        print(f"Throughput Delta:    {result.throughput_delta_mbps:.2f} Mbps")
        affected_nodes_str = ", ".join(result.predicted_affected_nodes) if result.predicted_affected_nodes else "None"
        print(f"Affected Nodes:      {affected_nodes_str}")
        affected_links_str = ", ".join(result.predicted_affected_links) if result.predicted_affected_links else "None"
        print(f"Affected Links:      {affected_links_str}")
        affected_services_str = ", ".join(result.predicted_affected_services) if result.predicted_affected_services else "None"
        print(f"Affected Services:   {affected_services_str}")
        print("=" * 60)
        return 0

    if args.command == "enterprise-evaluation":
        print("Enterprise Evaluation Engine: NOT YET AVAILABLE")
        print(
            "Formal evaluation framework (precision, recall, F1, SLA impact) "
            "will be implemented in Phase 10."
        )
        print("No synthetic or fabricated metrics generated.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
