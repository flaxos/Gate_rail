"""Tests for Sprint 2 freight movement across the fixed-tick graph."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.models import TrainStatus
from gaterail.scenarios import build_sprint2_scenario
from gaterail.simulation import TickSimulation


def test_sprint2_scenario_adds_trains_and_orders() -> None:
    state = build_sprint2_scenario()

    assert set(state.trains) == {"atlas", "civitas", "prospector"}
    assert set(state.orders) == {"food_to_brink", "materials_to_brink", "ore_to_core"}
    assert state.trains["atlas"].node_id == "core_yard"
    assert state.orders["food_to_brink"].requested_units == 20


def test_first_tick_loads_and_dispatches_ready_trains() -> None:
    simulation = TickSimulation.from_scenario("sprint2")

    report = simulation.step_tick()
    freight = report["freight"]

    assert [event["train"] for event in freight["dispatches"]] == ["Atlas", "Civitas", "Prospector"]
    assert simulation.state.trains["atlas"].status == TrainStatus.IN_TRANSIT
    assert simulation.state.trains["atlas"].cargo_units == 20
    assert simulation.state.trains["atlas"].remaining_ticks == 6
    assert simulation.state.nodes["core_yard"].stock(CargoType.FOOD) == 65
    assert simulation.state.nodes["frontier_mine"].stock(CargoType.ORE) == 0


def test_deliveries_reach_frontier_and_relieve_shortage_on_next_tick() -> None:
    simulation = TickSimulation.from_scenario("sprint2")

    reports = simulation.run_ticks(8)

    tick_7_freight = reports[6]["freight"]
    delivered_events = tick_7_freight["deliveries"]
    assert {event["cargo"] for event in delivered_events} == {"construction_materials", "food"}
    assert simulation.state.orders["food_to_brink"].active is False
    assert simulation.state.orders["materials_to_brink"].active is False
    assert reports[7]["shortages"] == {}
    assert simulation.state.nodes["frontier_settlement"].stock(CargoType.FOOD) == 18
    assert simulation.state.nodes["frontier_settlement"].stock(CargoType.CONSTRUCTION_MATERIALS) == 11


def test_long_ore_route_delivers_back_to_core_yard() -> None:
    simulation = TickSimulation.from_scenario("sprint2")

    reports = simulation.run_ticks(12)

    tick_11_deliveries = reports[10]["freight"]["deliveries"]
    assert tick_11_deliveries == [
        {
            "train": "Prospector",
            "node": "core_yard",
            "cargo": "ore",
            "units": 14,
            "order": "ore_to_core",
        }
    ]
    assert simulation.state.orders["ore_to_core"].delivered_units == 14
    assert simulation.state.orders["ore_to_core"].active is False


def test_cli_prints_freight_summary_and_delivery_events() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint2", "--ticks", "8"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "3 trains, 3 orders" in text
    assert "Freight: dispatch Atlas loaded 20 food" in text
    assert "Civitas delivered 12 construction_materials to frontier_settlement" in text
