"""Tests for Sprint 4 Railgate power pressure and expansion routing."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.gate import evaluate_gate_power
from gaterail.scenarios import build_sprint4_scenario
from gaterail.simulation import TickSimulation
from gaterail.transport import shortest_route


def test_underpowered_expansion_gate_blocks_route() -> None:
    state = build_sprint4_scenario()

    route = shortest_route(state, "frontier_settlement", "outer_outpost")
    statuses = evaluate_gate_power(state)

    assert route is None
    assert statuses["gate_core_frontier"].powered is True
    assert statuses["gate_frontier_outer"].powered is False
    assert statuses["gate_frontier_outer"].power_shortfall == 40
    assert state.worlds["core"].gate_power_used == 80
    assert state.worlds["frontier"].gate_power_used == 0


def test_powering_frontier_gate_makes_expansion_route_available() -> None:
    state = build_sprint4_scenario()
    state.worlds["frontier"].power_available = 160

    statuses = evaluate_gate_power(state)
    route = shortest_route(state, "frontier_settlement", "outer_outpost")

    assert statuses["gate_frontier_outer"].powered is True
    assert state.worlds["frontier"].gate_power_used == 90
    assert state.worlds["frontier"].power_margin == 10
    assert route is not None
    assert route.link_ids == (
        "rail_frontier_outer_gate_settlement",
        "gate_frontier_outer",
        "rail_outer_gate_outpost",
    )
    assert route.travel_ticks == 5
    assert route.gate_power_required == 90


def test_underpowered_gate_blocks_assigned_freight_order() -> None:
    simulation = TickSimulation.from_scenario("sprint4")

    report = simulation.step_tick()
    blocked = report["freight"]["blocked"]

    assert report["network"]["powered_gate_links"] == 1
    assert report["network"]["unpowered_gate_links"] == 1
    assert report["gates"]["gate_frontier_outer"]["power_shortfall"] == 40
    assert {
        "train": "Mercy",
        "order": "meds_to_ashfall",
        "reason": "no route frontier_settlement->outer_outpost",
    } in blocked
    assert simulation.state.nodes["frontier_settlement"].stock(CargoType.MEDICAL_SUPPLIES) == 8
    assert report["progression"]["outer"]["trend"] == "regressing"


def test_powered_expansion_gate_dispatches_medical_train() -> None:
    state = build_sprint4_scenario()
    state.worlds["frontier"].power_available = 160
    simulation = TickSimulation(state=state)

    report = simulation.step_tick()
    dispatches = report["freight"]["dispatches"]

    assert report["network"]["powered_gate_links"] == 2
    assert any(event["train"] == "Mercy" for event in dispatches)
    assert simulation.state.trains["mercy"].remaining_ticks == 5
    assert simulation.state.nodes["frontier_settlement"].stock(CargoType.MEDICAL_SUPPLIES) == 4


def test_cli_sprint4_prints_gate_bottleneck() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint4", "--ticks", "1"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "3 worlds, 8 nodes, 6 rail links, 2 Railgate links, 4 trains, 4 orders" in text
    assert "gate_frontier_outer underpowered" in text
    assert "Mercy: no route frontier_settlement->outer_outpost" in text
