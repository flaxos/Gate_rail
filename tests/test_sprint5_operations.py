"""Tests for Sprint 5 Stage 1 operations ledger behavior."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.scenarios import build_sprint5_scenario
from gaterail.simulation import TickSimulation


def test_sprint5_scenario_uses_recurring_schedules() -> None:
    state = build_sprint5_scenario()

    assert state.orders == {}
    assert set(state.schedules) == {
        "ashfall_medical_service",
        "core_food_service",
        "core_material_service",
        "frontier_ore_service",
    }
    assert state.links["gate_core_frontier"].capacity_per_tick == 1
    assert state.links["gate_frontier_outer"].capacity_per_tick == 1


def test_gate_slots_limit_due_schedules_on_same_day() -> None:
    simulation = TickSimulation.from_scenario("sprint5")

    report = simulation.step_tick()

    assert report["gates"]["gate_core_frontier"]["slots_used"] == 1
    assert report["gates"]["gate_core_frontier"]["slots_remaining"] == 0
    assert any(
        event["reason"] == "gate slots full on gate_core_frontier"
        for event in report["freight"]["blocked"]
    )
    assert report["finance"]["costs"] == 223.0
    assert report["finance"]["revenue"] == 0.0


def test_delivery_revenue_is_recorded_when_scheduled_train_arrives() -> None:
    simulation = TickSimulation.from_scenario("sprint5")

    report = simulation.run_ticks(6)[-1]

    assert report["finance"]["revenue"] == 60.0
    assert simulation.state.schedules["ashfall_medical_service"].delivered_units == 2
    assert simulation.state.nodes["outer_outpost"].stock(CargoType.MEDICAL_SUPPLIES) == 2


def test_monthly_ledger_summarizes_operations() -> None:
    simulation = TickSimulation.from_scenario("sprint5")

    simulation.run_ticks(30)

    assert len(simulation.monthly_reports) == 1
    ledger = simulation.monthly_reports[0]
    assert ledger["month"] == 1
    assert ledger["cargo_moved"]["food"] == 32
    assert ledger["cargo_moved"]["construction_materials"] == 20
    assert ledger["gate_use"]["gate_core_frontier"]["slots_used"] == 7
    assert ledger["finance"]["revenue"] == 1028.0
    assert ledger["finance"]["costs"] == 3248.0
    assert ledger["finance"]["net"] == -2220.0


def test_cli_sprint5_prints_monthly_table() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint5", "--ticks", "30"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Schedules: core_food_service food" in text
    assert "Month 01 Operations Ledger" in text
    assert "Finance\nRevenue | Costs" in text
    assert "Gate Use\nGate" in text
