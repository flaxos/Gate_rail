"""Tests for Sprint 6 economic identity behavior."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.economy import specialization_profiles_for_state
from gaterail.scenarios import build_sprint6_scenario
from gaterail.simulation import TickSimulation


def test_sprint6_scenario_enables_economic_identity() -> None:
    state = build_sprint6_scenario()

    assert state.economic_identity_enabled
    assert state.links["gate_core_frontier"].capacity_per_tick == 2
    assert state.links["gate_frontier_outer"].capacity_per_tick == 2
    assert {"core_parts_to_ashfall", "ashfall_research_to_core"}.issubset(state.schedules)
    assert {"pioneer", "curie"}.issubset(state.trains)
    assert state.schedules["ashfall_medical_service"].units_per_departure == 4

    profiles = specialization_profiles_for_state(state)
    assert profiles["core"]["specialization"] == "manufacturing"
    assert profiles["frontier"]["specialization"] == "mining"
    assert profiles["outer"]["specialization"] == "survey_outpost"
    assert profiles["core"]["exports"]["parts"] == 2
    assert profiles["outer"]["exports"]["research_equipment"] == 1


def test_mining_boost_consumes_machinery_and_outputs_ore() -> None:
    simulation = TickSimulation.from_scenario("sprint6")

    report = simulation.step_tick()

    assert report["economy"]["produced"]["frontier_mine"]["ore"] == 6
    assert report["economy"]["consumed"]["frontier_mine"]["machinery"] == 1
    assert simulation.state.nodes["frontier_mine"].stock(CargoType.MACHINERY) == 2


def test_manufacturing_uses_frontier_ore_delivery_for_exports() -> None:
    simulation = TickSimulation.from_scenario("sprint6")

    reports = simulation.run_ticks(13)
    report = reports[-1]

    assert report["economy"]["produced"]["core_yard"] == {
        "construction_materials": 4,
        "medical_supplies": 1,
        "parts": 2,
    }
    assert report["economy"]["consumed"]["core_yard"] == {"ore": 2}


def test_survey_outpost_exports_research_after_supplies_arrive() -> None:
    simulation = TickSimulation.from_scenario("sprint6")

    reports = simulation.run_ticks(21)
    report = reports[-1]

    assert report["economy"]["produced"]["outer_outpost"] == {"research_equipment": 1}
    assert report["economy"]["consumed"]["outer_outpost"] == {
        "medical_supplies": 1,
        "parts": 1,
    }


def test_monthly_ledger_includes_specialized_output() -> None:
    simulation = TickSimulation.from_scenario("sprint6")

    simulation.run_ticks(30)

    assert len(simulation.monthly_reports) == 1
    ledger = simulation.monthly_reports[0]
    assert ledger["specialized_output"] == {
        "construction_materials": 24,
        "medical_supplies": 6,
        "ore": 18,
        "parts": 12,
        "research_equipment": 1,
    }
    assert ledger["cargo_moved"]["research_equipment"] == 1


def test_cli_sprint6_prints_economy_tables() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint6", "--ticks", "30"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Economy: Vesta Core manufacturing; Brink Frontier mining; Ashfall Spur survey_outpost" in text
    assert "Economy Profiles: Vesta Core imports ore 2, research_equipment 1" in text
    assert "Schedules: core_food_service food" in text
    assert "core_parts_to_ashfall parts" in text
    assert "Month 01 Operations Ledger" in text
    assert "Specialized Output\nCargo" in text
    assert "research_equipment" in text
