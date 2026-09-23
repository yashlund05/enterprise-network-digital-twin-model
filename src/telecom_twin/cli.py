"""Command-line entry points."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from telecom_twin.demo import export_demo_gif
from telecom_twin.experiment import run_experiment
from telecom_twin.multifault import run_multi_fault_benchmark
from telecom_twin.online import export_online_evaluation
from telecom_twin.robustness import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic telecom network digital twin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    experiment = subparsers.add_parser("experiment")
    experiment.add_argument("--output-dir", type=Path, default=Path("results"))
    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    benchmark = subparsers.add_parser("benchmark")
    benchmark.add_argument("--output-dir", type=Path, default=Path("results"))
    benchmark.add_argument("--trials-per-root", type=int, default=20)
    online = subparsers.add_parser("online-evaluation")
    online.add_argument("--output-dir", type=Path, default=Path("results"))
    multifault = subparsers.add_parser("multi-fault-benchmark")
    multifault.add_argument("--output-dir", type=Path, default=Path("results"))
    multifault.add_argument("--trials-per-scenario", type=int, default=20)
    demo = subparsers.add_parser("demo-gif")
    demo.add_argument(
        "--output", type=Path, default=Path("results/figures/live_twin_demo.gif")
    )
    args = parser.parse_args()
    if args.command == "experiment":
        for name, path in run_experiment(args.output_dir).items():
            print(f"{name}: {path}")
        return
    if args.command == "benchmark":
        for name, path in run_benchmark(
            args.output_dir, trials_per_root=args.trials_per_root
        ).items():
            print(f"{name}: {path}")
        return
    if args.command == "online-evaluation":
        for name, path in export_online_evaluation(args.output_dir).items():
            print(f"{name}: {path}")
        return
    if args.command == "multi-fault-benchmark":
        for name, path in run_multi_fault_benchmark(
            args.output_dir, trials_per_scenario=args.trials_per_scenario
        ).items():
            print(f"{name}: {path}")
        return
    if args.command == "demo-gif":
        print(f"gif: {export_demo_gif(args.output)}")
        return
    uvicorn.run("telecom_twin.api:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
