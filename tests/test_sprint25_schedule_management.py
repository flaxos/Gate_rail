"""Tests for Sprint 25 schedule management and flow-control tooling."""

from __future__ import annotations

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.commands import (
    DeleteSchedule,
    PreviewDeleteSchedule,
    PreviewUpdateSchedule,
    UpdateSchedule,
    command_from_dict,
)
from gaterail.freight import advance_freight
from gaterail.gate import evaluate_gate_power
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_command_from_dict_parses_schedule_management_commands() -> None:
    preview = command_from_dict(
        {
            "type": "PreviewUpdateSchedule",
            "schedule_id": "core_food_service",
            "destination": "outer_outpost",
            "stops": ["frontier_settlement"],
            "cargo_type": "food",
            "units_per_departure": 6,
            "interval_ticks": 9,
            "active": False,
        }
    )
    update = command_from_dict(
        {
            "type": "UpdateSchedule",
            "schedule_id": "core_food_service",
            "stops": "frontier_settlement",
        }
    )
    preview_delete = command_from_dict(
        {"type": "PreviewDeleteSchedule", "schedule_id": "core_food_service"}
    )
    delete = command_from_dict({"type": "DeleteSchedule", "schedule_id": "core_food_service"})

    assert isinstance(preview, PreviewUpdateSchedule)
    assert preview.destination == "outer_outpost"
    assert preview.stops == ("frontier_settlement",)
    assert preview.cargo_type == CargoType.FOOD
    assert preview.active is False
    assert isinstance(update, UpdateSchedule)
    assert update.stops == ("frontier_settlement",)
    assert isinstance(preview_delete, PreviewDeleteSchedule)
    assert isinstance(delete, DeleteSchedule)


def test_preview_update_schedule_returns_normalized_edit_without_mutating_state() -> None:
    state = build_sprint8_scenario()
    original = state.schedules["core_food_service"]

    result = state.apply_command(
        PreviewUpdateSchedule(
            schedule_id="core_food_service",
            destination="outer_outpost",
            stops=("frontier_settlement",),
            units_per_departure=6,
            interval_ticks=9,
            active=False,
        )
    )

    assert result["ok"] is True
    assert result["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]
    assert result["route_segments"][0]["ok"] is True
    assert result["route_segments"][1]["ok"] is True
    assert result["normalized_command"] == {
        "type": "UpdateSchedule",
        "schedule_id": "core_food_service",
        "train_id": "atlas",
        "origin": "core_yard",
        "destination": "outer_outpost",
        "stops": ["frontier_settlement"],
        "cargo_type": "food",
        "units_per_departure": 6,
        "interval_ticks": 9,
        "next_departure_tick": 1,
        "priority": 100,
        "active": False,
        "return_to_origin": True,
    }
    assert original.destination == "frontier_settlement"
    assert original.stops == ()
    assert original.units_per_departure == 16
    assert original.interval_ticks == 8
    assert original.active is True


def test_update_schedule_persists_to_snapshot_flow_and_dispatch_route() -> None:
    state = build_sprint8_scenario()
    state.schedules.pop("core_material_service")
    state.schedules.pop("frontier_ore_service")
    state.schedules.pop("ashfall_medical_service")
    state.nodes["core_yard"].add_inventory(CargoType.FOOD, 8)
    evaluate_gate_power(state)

    result = state.apply_command(
        UpdateSchedule(
            schedule_id="core_food_service",
            destination="outer_outpost",
            stops=("frontier_settlement",),
            units_per_departure=4,
            interval_ticks=8,
            next_departure_tick=1,
        )
    )

    assert result["ok"] is True
    assert state.schedules["core_food_service"].destination == "outer_outpost"
    assert state.schedules["core_food_service"].stops == ("frontier_settlement",)

    snapshot = render_snapshot(state)
    schedule_payload = next(item for item in snapshot["schedules"] if item["id"] == "core_food_service")
    flow_payload = next(item for item in snapshot["cargo_flows"] if item["id"] == "schedule:core_food_service")
    assert schedule_payload["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]
    assert flow_payload["id"] == "schedule:core_food_service"
    assert flow_payload["route_stop_ids"] == ["core_yard", "frontier_settlement", "outer_outpost"]
    assert flow_payload["route_link_ids"] == result["route_link_ids"]

    state.tick = 1
    report = advance_freight(state)

    assert report["dispatches"][0]["route_stop_ids"] == [
        "core_yard",
        "frontier_settlement",
        "outer_outpost",
    ]
    assert report["dispatches"][0]["links"] == result["route_link_ids"]


def test_invalid_schedule_update_preview_returns_segment_debug() -> None:
    state = build_sprint8_scenario()
    state.worlds["frontier"].power_available = 60
    evaluate_gate_power(state)

    result = state.apply_command(
        PreviewUpdateSchedule(
            schedule_id="core_food_service",
            destination="outer_outpost",
            stops=("frontier_settlement",),
        )
    )

    assert result["ok"] is False
    assert result["validation_errors"] == [
        {
            "code": "invalid_path",
            "reason": "no route core_yard->frontier_settlement->outer_outpost",
        }
    ]
    assert result["route_segments"][1]["blocked_links"] == [
        {
            "link_id": "gate_frontier_outer",
            "mode": "gate",
            "severity": "blocked",
            "reason": "gate gate_frontier_outer unpowered",
        }
    ]


def test_delete_schedule_preview_and_delete_are_safe() -> None:
    state = build_sprint8_scenario()

    preview = state.apply_command(PreviewDeleteSchedule("core_food_service"))
    result = state.apply_command(DeleteSchedule("core_food_service"))
    snapshot = render_snapshot(state)

    assert preview["ok"] is True
    assert preview["normalized_command"] == {
        "type": "DeleteSchedule",
        "schedule_id": "core_food_service",
    }
    assert result["ok"] is True
    assert "core_food_service" not in state.schedules
    assert "schedule:core_food_service" not in {flow["id"] for flow in snapshot["cargo_flows"]}


def test_delete_schedule_preview_rejects_active_schedule_trip() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    simulation.step_tick()

    result = simulation.state.apply_command(PreviewDeleteSchedule("core_food_service"))

    assert result["ok"] is False
    assert result["reason"] == "schedule_in_active_trip"
    assert "core_food_service" in simulation.state.schedules


def test_bridge_applies_schedule_update_and_delete_commands() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    updated = handle_bridge_message(
        simulation,
        {
            "commands": [
                {
                    "type": "UpdateSchedule",
                    "schedule_id": "core_food_service",
                    "destination": "outer_outpost",
                    "stops": ["frontier_settlement"],
                    "units_per_departure": 4,
                    "interval_ticks": 8,
                    "next_departure_tick": 1,
                }
            ],
            "ticks": 0,
        },
    )
    deleted = handle_bridge_message(
        simulation,
        {
            "commands": [{"type": "DeleteSchedule", "schedule_id": "core_food_service"}],
            "ticks": 0,
        },
    )

    assert updated["bridge"]["command_results"][0]["ok"] is True
    assert updated["bridge"]["command_results"][0]["route_stop_ids"] == [
        "core_yard",
        "frontier_settlement",
        "outer_outpost",
    ]
    assert deleted["bridge"]["command_results"][0]["ok"] is True
    assert all(schedule["id"] != "core_food_service" for schedule in deleted["schedules"])


def test_godot_schedule_management_contracts_are_wired() -> None:
    bridge_script = open("godot/scripts/gate_rail_bridge.gd", encoding="utf-8").read()
    main_script = open("godot/scripts/main.gd", encoding="utf-8").read()

    for token in ("preview_update_schedule", "update_schedule", "delete_schedule"):
        assert token in bridge_script
    for token in ("PreviewUpdateSchedule", "UpdateSchedule", "DeleteSchedule", "cargo_flows"):
        assert token in main_script
