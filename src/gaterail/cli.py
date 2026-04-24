"""CLI module for GateRail."""

from __future__ import annotations

import argparse
import random

from gaterail.reporting import print_day_report, print_inspection
from gaterail.scenarios import default_scenario


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gaterail", description="GateRail simulation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run simulation days")
    run_parser.add_argument("--days", type=int, default=30, help="Days to run (default: 30)")
    run_parser.add_argument("--quiet", action="store_true", help="Suppress per-day output")
    run_parser.add_argument("--verbose", action="store_true", help="Emit per-day reports")
    run_parser.add_argument("--seed", type=int, default=None, help="Optional random seed")

    subparsers.add_parser("inspect", help="Inspect starting/default scenario state")

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    """Execute CLI workflow."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    seed = getattr(args, "seed", None)
    if seed is not None:
        random.seed(seed)

    scenario = default_scenario()
    simulation = scenario.create_simulation()

    if args.command == "inspect":
        print(f"scenario={scenario.name}")
        print_inspection(simulation)
        return 0

    days = max(0, args.days)
    should_emit_day_reports = args.verbose or not args.quiet

    days_executed = 0
    for _ in range(days):
        if simulation.status != "running":
            break
        report = simulation.run_day()
        days_executed += 1
        if should_emit_day_reports:
            print_day_report(simulation, report)

    print(
        f"run_complete scenario={scenario.name!r} days_executed={days_executed} "
        f"final_status={simulation.status} cash={simulation.finance.cash:.2f} debt={simulation.finance.debt:.2f}"
    )
    return 0
