"""Tests for the Sprint 9 Stage 2 bridge contract."""

from __future__ import annotations

import json
from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.commands import CancelOrder, DispatchOrder, SetScheduleEnabled, command_from_dict
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import SNAPSHOT_VERSION, render_snapshot


def test_render_snapshot_is_versioned_and_separate_from_rich_reports() -> None:
    state = build_sprint8_scenario()

    snapshot = render_snapshot(state)

    assert snapshot["snapshot_version"] == SNAPSHOT_VERSION == 1
    assert snapshot["tick"] == 0
    assert snapshot["finance"]["cash"] == 10_000.0
    assert snapshot["reputation"] == 0
    assert {world["id"] for world in snapshot["worlds"]} == {"core", "frontier", "outer"}
    assert {contract["id"] for contract in snapshot["contracts"]} == {
        "ashfall_medical_lifeline",
        "brink_food_relief",
        "core_ore_quota",
    }
    assert "phase_order" not in snapshot
    assert "freight" not in snapshot


def test_apply_command_toggles_schedule_enabled_state() -> None:
    state = build_sprint8_scenario()

    disable_result = state.apply_command(SetScheduleEnabled("core_food_service", False))
    enable_result = state.apply_command(SetScheduleEnabled("core_food_service", True))

    assert disable_result["ok"] is True
    assert enable_result["ok"] is True
    assert state.schedules["core_food_service"].active is True


def test_apply_command_dispatches_and_cancels_pending_order() -> None:
    state = build_sprint8_scenario()

    dispatch_result = state.apply_command(
        DispatchOrder(
            order_id="manual_food_run",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            requested_units=5,
            priority=120,
        )
    )
    cancel_result = state.apply_command(CancelOrder("manual_food_run"))

    assert dispatch_result == {
        "ok": True,
        "type": "DispatchOrder",
        "target_id": "manual_food_run",
        "message": "order manual_food_run queued",
    }
    assert cancel_result["ok"] is True
    assert state.orders["manual_food_run"].active is False


def test_command_from_dict_parses_stage2_json_commands() -> None:
    command = command_from_dict(
        {
            "type": "DispatchOrder",
            "order_id": "manual_parts",
            "train_id": "pioneer",
            "origin": "core_yard",
            "destination": "outer_outpost",
            "cargo_type": "parts",
            "requested_units": 2,
            "priority": 140,
        }
    )

    assert isinstance(command, DispatchOrder)
    assert command.cargo_type == CargoType.PARTS
    assert command.requested_units == 2
    assert command.priority == 140


def test_stdio_bridge_steps_and_emits_json_snapshots() -> None:
    input_stream = StringIO(
        json.dumps({"ticks": 0})
        + "\n"
        + json.dumps(
            {
                "commands": [
                    {
                        "type": "SetScheduleEnabled",
                        "schedule_id": "core_food_service",
                        "enabled": False,
                    }
                ],
                "ticks": 1,
            }
        )
        + "\n"
    )
    output_stream = StringIO()

    result = run_cli(["--stdio"], input_stream=input_stream, output=output_stream)

    lines = [json.loads(line) for line in output_stream.getvalue().splitlines()]
    assert result == 0
    assert len(lines) == 2
    assert lines[0]["snapshot_version"] == 1
    assert lines[0]["tick"] == 0
    assert lines[1]["tick"] == 1
    assert lines[1]["bridge"]["ok"] is True
    assert lines[1]["bridge"]["stepped_ticks"] == 1
    assert lines[1]["bridge"]["command_results"][0]["target_id"] == "core_food_service"
    schedules = {schedule["id"]: schedule for schedule in lines[1]["schedules"]}
    assert schedules["core_food_service"]["active"] is False


def test_stdio_bridge_can_queue_manual_order_without_stepping() -> None:
    input_stream = StringIO(
        json.dumps(
            {
                "command": {
                    "type": "DispatchOrder",
                    "order_id": "manual_meds",
                    "train_id": "mercy",
                    "origin": "frontier_settlement",
                    "destination": "outer_outpost",
                    "cargo_type": "medical_supplies",
                    "requested_units": 2,
                },
                "ticks": 0,
            }
        )
        + "\n"
    )
    output_stream = StringIO()

    result = run_cli(["--stdio"], input_stream=input_stream, output=output_stream)

    snapshot = json.loads(output_stream.getvalue())
    assert result == 0
    assert snapshot["tick"] == 0
    assert snapshot["bridge"]["command_results"][0]["message"] == "order manual_meds queued"
    assert any(order["id"] == "manual_meds" and order["active"] for order in snapshot["orders"])


def test_stdio_bridge_reports_command_errors_as_json_frames() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    input_stream = StringIO(
        json.dumps(
            {
                "command": {
                    "type": "SetScheduleEnabled",
                    "schedule_id": "missing_schedule",
                    "enabled": False,
                },
                "ticks": 1,
            }
        )
        + "\n"
    )
    output_stream = StringIO()

    from gaterail.bridge import run_stdio_bridge

    result = run_stdio_bridge(simulation, input_stream=input_stream, output_stream=output_stream)

    frame = json.loads(output_stream.getvalue())
    assert result == 0
    assert frame["snapshot_version"] == 1
    assert frame["bridge"]["ok"] is False
    assert "unknown schedule" in frame["bridge"]["error"]
    assert simulation.state.tick == 0
