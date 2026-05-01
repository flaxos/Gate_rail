"""Tests for Sprint 23 multi-stop routes and route debugging."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import CreateSchedule, PreviewCreateSchedule, command_from_dict
from gaterail.freight import advance_freight
from gaterail.gate import evaluate_gate_power
from gaterail.models import FreightTrain, TrainConsist
from gaterail.persistence import load_simulation, save_simulation
from gaterail.reporting import format_scenario_inspection
from gaterail.scenarios import build_sprint4_scenario, build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot
from gaterail.traffic import reset_traffic_usage


def test_preview_schedule_accepts_intermediate_stops_and_returns_route_segments() -> None:
    state = build_sprint8_scenario()

    result = state.apply_command(
        PreviewCreateSchedule(
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

    assert result["ok"] is True
    assert result["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]
    assert result["route_segments"] == [
        {
            "from_node_id": "core_yard",
            "to_node_id": "frontier_settlement",
            "ok": True,
            "reason": None,
            "travel_ticks": 6,
            "node_ids": ["core_yard", "core_gate", "frontier_gate", "frontier_settlement"],
            "link_ids": ["rail_core_yard_gate", "gate_core_frontier", "rail_frontier_gate_settlement"],
            "blocked_links": [],
        },
        {
            "from_node_id": "frontier_settlement",
            "to_node_id": "outer_outpost",
            "ok": True,
            "reason": None,
            "travel_ticks": 5,
            "node_ids": ["frontier_settlement", "frontier_outer_gate", "outer_gate", "outer_outpost"],
            "link_ids": ["rail_frontier_outer_gate_settlement", "gate_frontier_outer", "rail_outer_gate_outpost"],
            "blocked_links": [],
        },
    ]
    assert result["route_link_ids"] == [
        "rail_core_yard_gate",
        "gate_core_frontier",
        "rail_frontier_gate_settlement",
        "rail_frontier_outer_gate_settlement",
        "gate_frontier_outer",
        "rail_outer_gate_outpost",
    ]
    assert result["normalized_command"]["stops"] == ["frontier_settlement"]


def test_created_multi_stop_schedule_is_persisted_to_snapshot_and_used_for_dispatch() -> None:
    state = build_sprint8_scenario()
    state.schedules.clear()
    state.nodes["core_yard"].add_inventory(CargoType.FOOD, 8)
    evaluate_gate_power(state)
    reset_traffic_usage(state)

    result = state.apply_command(
        CreateSchedule(
            schedule_id="core_food_via_brink",
            train_id="atlas",
            origin="core_yard",
            stops=("frontier_settlement",),
            destination="outer_outpost",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
            next_departure_tick=1,
        )
    )
    state.tick = 1

    assert result["ok"] is True
    assert state.schedules["core_food_via_brink"].stops == ("frontier_settlement",)

    snapshot = render_snapshot(state)
    schedule_payload = next(item for item in snapshot["schedules"] if item["id"] == "core_food_via_brink")
    assert schedule_payload["stops"] == ["frontier_settlement"]
    assert schedule_payload["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]

    report = advance_freight(state)

    assert report["dispatches"][0]["links"] == result["route_link_ids"]
    assert state.trains["atlas"].route_node_ids == tuple(result["route_node_ids"])
    assert state.trains["atlas"].route_link_ids == tuple(result["route_link_ids"])


def test_invalid_multi_stop_preview_returns_segment_debug() -> None:
    state = build_sprint8_scenario()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="bad_stop",
            train_id="atlas",
            origin="core_yard",
            stops=("missing_node",),
            destination="outer_outpost",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is False
    assert result["validation_errors"] == [
        {"code": "unknown_stop", "reason": "unknown schedule stop: missing_node"}
    ]
    assert result["route_stop_ids"] == ["core_yard", "missing_node", "outer_outpost"]
    assert result["route_segments"] == [
        {
            "from_node_id": "core_yard",
            "to_node_id": "missing_node",
            "ok": False,
            "reason": "unknown node missing_node",
            "travel_ticks": 0,
            "node_ids": [],
            "link_ids": [],
            "blocked_links": [],
        },
        {
            "from_node_id": "missing_node",
            "to_node_id": "outer_outpost",
            "ok": False,
            "reason": "unknown node missing_node",
            "travel_ticks": 0,
            "node_ids": [],
            "link_ids": [],
            "blocked_links": [],
        },
    ]


def test_unpowered_gate_preview_exposes_blocked_link_debug() -> None:
    state = build_sprint4_scenario()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="ashfall_med_unpowered_debug",
            train_id="mercy",
            origin="frontier_settlement",
            destination="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            units_per_departure=1,
            interval_ticks=8,
        )
    )

    assert result["ok"] is False
    assert result["route_segments"][0]["ok"] is False
    assert result["route_segments"][0]["blocked_links"] == [
        {
            "link_id": "gate_frontier_outer",
            "mode": "gate",
            "severity": "blocked",
            "reason": "gate gate_frontier_outer unpowered",
        }
    ]


def test_consist_mismatch_preview_returns_structured_validation_error() -> None:
    state = build_sprint8_scenario()
    state.trains["protected_shuttle"] = FreightTrain(
        id="protected_shuttle",
        name="Protected Shuttle",
        node_id="frontier_mine",
        capacity=8,
        consist=TrainConsist.PROTECTED,
    )

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="bad_ore_consist",
            train_id="protected_shuttle",
            origin="frontier_mine",
            destination="core_yard",
            cargo_type=CargoType.ORE,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is False
    assert result["validation_errors"] == [
        {
            "code": "incompatible_consist",
            "reason": "schedule cargo ore requires bulk_hopper consist, train is protected",
        }
    ]


def test_command_from_dict_parses_schedule_stops() -> None:
    command = command_from_dict(
        {
            "type": "PreviewCreateSchedule",
            "schedule_id": "core_food_via_brink",
            "train_id": "atlas",
            "origin": "core_yard",
            "stops": ["frontier_settlement"],
            "destination": "outer_outpost",
            "cargo_type": "food",
            "units_per_departure": 4,
            "interval_ticks": 8,
        }
    )

    assert isinstance(command, PreviewCreateSchedule)
    assert command.stops == ("frontier_settlement",)


def test_inspection_prints_exact_multi_stop_schedule_path() -> None:
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

    text = format_scenario_inspection(state, {"schedules"})

    assert "core_yard->frontier_settlement->outer_outpost" in text


def test_save_load_preserves_multi_stop_schedule(tmp_path) -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    simulation.state.schedules.clear()
    simulation.state.apply_command(
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
    save_path = tmp_path / "multi_stop_save.json"

    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)

    assert loaded.state.schedules["core_food_via_brink"].stops == ("frontier_settlement",)
