"""Command-line interface for GateRail."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO


from gaterail.persistence import load_simulation, save_simulation
from gaterail.reporting import (
    format_monthly_report,
    format_scenario_inspection,
    format_state_summary,
    format_tick_report,
)
from gaterail.scenarios import DEFAULT_SCENARIO, scenario_definitions
from gaterail.simulation import TickSimulation


REPORT_SECTIONS = frozenset(
    {
        "all",
        "cargo",
        "contracts",
        "economy",
        "finance",
        "freight",
        "gates",
        "production",
        "progression",
        "schedules",
        "shortages",
        "stockpiles",
        "traffic",
    }
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Run the GateRail fixed-tick playtest prototype.")
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List built-in scenarios and exit.",
    )
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO,
        help=f"Built-in scenario to run. Default: {DEFAULT_SCENARIO}.",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print scenario setup details and exit without advancing time.",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of fixed simulation ticks to run. Default: 5.",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        metavar="SECTION",
        help=(
            "Comma-separated report sections to print. "
            "Use all, cargo, contracts, economy, finance, freight, gates, production, "
            "progression, schedules, shortages, stockpiles, or traffic."
        ),
    )
    parser.add_argument(
        "--load",
        type=Path,
        help="Load a saved tick simulation JSON file instead of starting a scenario.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Save the simulation JSON file after inspection or after running ticks.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip the initial scenario summary.",
    )
    return parser


def _parse_report_sections(values: Sequence[str], parser: argparse.ArgumentParser) -> frozenset[str] | None:
    """Parse comma-separated report section filters."""

    if not values:
        return None
    sections: set[str] = set()
    for value in values:
        for token in value.split(","):
            section = token.strip().lower()
            if not section:
                continue
            if section not in REPORT_SECTIONS:
                parser.error(f"unknown report section: {section}")
            if section == "all":
                return None
            sections.add(section)
    return frozenset(sections) if sections else None


def _format_scenario_catalog() -> str:
    """Format built-in scenario metadata for the CLI."""

    lines = ["Built-in scenarios:"]
    for definition in scenario_definitions():
        aliases = ", ".join(definition.aliases) if definition.aliases else "-"
        default_marker = " default" if definition.key == DEFAULT_SCENARIO else ""
        lines.append(
            f"{definition.key}{default_marker}: {definition.title} "
            f"(aliases: {aliases}) - {definition.description}"
        )
    return "\n".join(lines)


def run_cli(argv: Sequence[str] | None = None, output: TextIO | None = None) -> int:
    """Execute CLI workflow."""

    stream = sys.stdout if output is None else output
    parser = build_parser()
    args = parser.parse_args(argv)
    report_sections = _parse_report_sections(args.report, parser)

    if args.list_scenarios:
        stream.write(_format_scenario_catalog())
        stream.write("\n")
        return 0

    if args.load is not None:
        try:
            simulation = load_simulation(args.load)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    else:
        try:
            simulation = TickSimulation.from_scenario(args.scenario)
        except ValueError as exc:
            parser.error(str(exc))

    if args.inspect:
        stream.write(format_scenario_inspection(simulation.state, sections=report_sections))
        stream.write("\n")
        if args.save is not None:
            try:
                save_simulation(simulation, args.save)
            except OSError as exc:
                parser.error(str(exc))
            stream.write(f"Saved simulation to {args.save}\n")
        return 0

    if not args.no_summary:
        stream.write(format_state_summary(simulation.state))
        stream.write("\n\n")

    previous_monthly_count = len(simulation.monthly_reports)
    for report in simulation.run_ticks(args.ticks):
        stream.write(format_tick_report(report, sections=report_sections))
        stream.write("\n\n")
    for monthly_report in simulation.monthly_reports[previous_monthly_count:]:
        stream.write(format_monthly_report(monthly_report, sections=report_sections))
        stream.write("\n\n")
    if args.save is not None:
        try:
            save_simulation(simulation, args.save)
        except OSError as exc:
            parser.error(str(exc))
        stream.write(f"Saved simulation to {args.save}\n")
    return 0
