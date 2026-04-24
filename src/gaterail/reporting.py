"""Reporting and human-readable simulation output for GateRail."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.schedule import ScheduleResult
from gaterail.simulation import Simulation


def _cargo_counts(stockpile: dict[CargoType, int]) -> str:
    return ", ".join(f"{cargo_type.name.lower()}={stockpile.get(cargo_type, 0)}" for cargo_type in CargoType)


def _warnings_for_day(simulation: Simulation, day_report: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    schedule_result = day_report.get("schedule_result")
    if isinstance(schedule_result, ScheduleResult) and schedule_result.skipped:
        warnings.extend(schedule_result.skipped)

    if simulation.finance.cash < 0:
        warnings.append("Company cash is negative.")
    if simulation.finance.debt > simulation.finance.cash * 10 and simulation.finance.debt > 0:
        warnings.append("Debt level is very high relative to cash.")
    if simulation.gate.condition < 0.25:
        warnings.append("Gate condition is critical.")
    if simulation.colony.morale < 0.3:
        warnings.append("Colony morale is critically low.")
    if simulation.status == "failed":
        reason = day_report.get("reason", "unknown")
        warnings.append(f"Simulation failed: {reason}")
    return warnings


def format_day_report(simulation: Simulation, day_report: dict[str, object]) -> str:
    """Format one-day summary including requested operational fields."""

    schedule_result = day_report.get("schedule_result")
    executed_count = 0
    delayed_count = 0
    if isinstance(schedule_result, ScheduleResult):
        executed_count = len(schedule_result.executed)
        delayed_count = len(schedule_result.skipped)

    warnings = _warnings_for_day(simulation, day_report)
    warnings_text = "; ".join(warnings) if warnings else "none"

    return (
        f"day={simulation.day} "
        f"cash={simulation.finance.cash:.2f} "
        f"debt={simulation.finance.debt:.2f} "
        f"gate_usage={simulation.gate.slots_used_today}/{simulation.gate.max_slots_per_day} "
        f"gate_condition={simulation.gate.condition:.2%} "
        f"colony_population={simulation.colony.population} "
        f"colony_morale={simulation.colony.morale:.2f} "
        f"world_core=[{_cargo_counts(simulation.world.inventories['Core'])}] "
        f"world_frontier=[{_cargo_counts(simulation.world.inventories['Frontier'])}] "
        f"completed_trains={executed_count} "
        f"delayed_trains={delayed_count} "
        f"warnings={warnings_text}"
    )


def print_day_report(simulation: Simulation, day_report: dict[str, object]) -> None:
    """Print one-line report for a completed simulation day."""

    print(format_day_report(simulation, day_report))


def print_inspection(simulation: Simulation) -> None:
    """Print scenario/simulation state snapshot for inspect command."""

    print("scenario_state")
    print(f"day={simulation.day}")
    print(f"status={simulation.status}")
    print(f"cash={simulation.finance.cash:.2f}")
    print(f"debt={simulation.finance.debt:.2f}")
    print(f"gate_condition={simulation.gate.condition:.2%}")
    print(f"gate_wear={simulation.gate.wear:.2f}")
    print(f"colony_population={simulation.colony.population}")
    print(f"colony_morale={simulation.colony.morale:.2f}")
    print(f"core_stockpile=[{_cargo_counts(simulation.world.inventories['Core'])}]")
    print(f"frontier_stockpile=[{_cargo_counts(simulation.world.inventories['Frontier'])}]")
