"""Tests for Sprint 24 cargo flow visualisation payloads."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import CreateSchedule
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_snapshot_exposes_schedule_cargo_flows_per_route_and_type() -> None:
    state = build_sprint8_scenario()

    snapshot = render_snapshot(state)
    flows = {flow["id"]: flow for flow in snapshot["cargo_flows"]}

    flow = flows["schedule:core_food_service"]
    assert flow["service_type"] == "schedule"
    assert flow["schedule_id"] == "core_food_service"
    assert flow["cargo"] == "food"
    assert flow["route_stop_ids"] == ["core_yard", "frontier_settlement"]
    assert flow["route_link_ids"] == ["rail_core_yard_gate", "gate_core_frontier", "rail_frontier_gate_settlement"]
    assert flow["units_per_departure"] == 16
    assert flow["delivered_units"] == 0
    assert flow["in_transit_units"] == 0
    assert flow["active"] is True


def test_snapshot_flow_preserves_multi_stop_route_sequence() -> None:
    state = build_sprint8_scenario()
    state.schedules.clear()
    state.apply_command(
        CreateSchedule(
            schedule_id="core_food_via_brink",
            train_id="atlas",
            origin="core_yard",
            stops=("frontier_settlement",),
            destination="outer_outpost",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    snapshot = render_snapshot(state)
    flow = snapshot["cargo_flows"][0]

    assert flow["id"] == "schedule:core_food_via_brink"
    assert flow["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]
    assert flow["route_link_ids"] == [
        "rail_core_yard_gate",
        "gate_core_frontier",
        "rail_frontier_gate_settlement",
        "rail_frontier_outer_gate_settlement",
        "gate_frontier_outer",
        "rail_outer_gate_outpost",
    ]


def test_snapshot_flow_reports_in_transit_units() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    simulation.step_tick()
    snapshot = render_snapshot(simulation.state)
    flows = {flow["id"]: flow for flow in snapshot["cargo_flows"]}

    assert flows["schedule:core_food_service"]["in_transit_units"] == 16
