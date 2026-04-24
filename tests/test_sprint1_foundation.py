"""Tests for the Sprint 1 fixed-tick simulation foundation."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.models import LinkMode
from gaterail.scenarios import build_sprint1_scenario
from gaterail.simulation import TickSimulation
from gaterail.transport import shortest_route


def test_sprint1_scenario_contains_world_graph_with_rail_and_gate_links() -> None:
    state = build_sprint1_scenario()

    assert set(state.worlds) == {"core", "frontier"}
    assert len(state.nodes) == 5
    assert len(state.links_by_mode(LinkMode.RAIL)) == 3
    assert len(state.links_by_mode(LinkMode.GATE)) == 1

    route = shortest_route(state, "core_yard", "frontier_settlement")

    assert route is not None
    assert route.node_ids == ("core_yard", "core_gate", "frontier_gate", "frontier_settlement")
    assert route.link_ids == (
        "rail_core_yard_gate",
        "gate_core_frontier",
        "rail_frontier_gate_settlement",
    )
    assert route.travel_ticks == 6
    assert route.gate_power_required == 80


def test_tick_runner_applies_production_and_demand_deterministically() -> None:
    first = TickSimulation.from_scenario("sprint1")
    second = TickSimulation.from_scenario("sprint1")

    first_reports = first.run_ticks(3)
    second_reports = second.run_ticks(3)

    assert first_reports == second_reports
    assert first.state.tick == 3
    assert first.state.nodes["core_yard"].stock(CargoType.FOOD) == 95
    assert first.state.nodes["core_yard"].stock(CargoType.MACHINERY) == 43
    assert first.state.nodes["frontier_mine"].stock(CargoType.ORE) == 22
    assert first.state.nodes["frontier_settlement"].stock(CargoType.FOOD) == 0
    assert first_reports[-1]["shortages"] == {}


def test_tick_runner_records_shortage_after_local_stock_runs_out() -> None:
    simulation = TickSimulation.from_scenario("sprint1")

    final_report = simulation.run_ticks(4)[-1]

    assert final_report["shortages"] == {
        "frontier_settlement": {
            "construction_materials": 1,
            "food": 2,
        }
    }


def test_cli_runs_sprint1_scenario_and_prints_tick_reports() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint1", "--ticks", "2"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Scenario: 2 worlds, 5 nodes, 3 rail links, 1 gate links" in text
    assert "Tick 0001" in text
    assert "Tick 0002" in text
    assert "gate power 80" in text
