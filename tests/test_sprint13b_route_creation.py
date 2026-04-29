"""Tests for Sprint 13B train purchase and schedule creation previews."""

from __future__ import annotations

import pytest

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.commands import (
    CreateSchedule,
    PreviewCreateSchedule,
    PreviewPurchaseTrain,
    PurchaseTrain,
    command_from_dict,
)
from gaterail.construction import train_purchase_cost
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_command_from_dict_parses_train_and_schedule_previews() -> None:
    train_command = command_from_dict(
        {
            "type": "PreviewPurchaseTrain",
            "train_id": "frontier_shuttle",
            "name": "Frontier Shuttle",
            "node_id": "frontier_gate",
            "capacity": 8,
        }
    )
    schedule_command = command_from_dict(
        {
            "type": "PreviewCreateSchedule",
            "schedule_id": "frontier_food_loop",
            "train_id": "frontier_shuttle",
            "origin": "frontier_gate",
            "destination": "frontier_settlement",
            "cargo_type": "food",
            "units_per_departure": 8,
            "interval_ticks": 4,
        }
    )

    assert isinstance(train_command, PreviewPurchaseTrain)
    assert train_command.capacity == 8
    assert isinstance(schedule_command, PreviewCreateSchedule)
    assert schedule_command.cargo_type == CargoType.FOOD


def test_preview_purchase_train_returns_cost_without_mutating_state() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    result = state.apply_command(
        PreviewPurchaseTrain(
            train_id="frontier_shuttle",
            name="Frontier Shuttle",
            node_id="frontier_gate",
            capacity=8,
        )
    )

    assert result["ok"] is True
    assert result["cost"] == pytest.approx(train_purchase_cost(8))
    assert result["normalized_command"] == {
        "type": "PurchaseTrain",
        "train_id": "frontier_shuttle",
        "name": "Frontier Shuttle",
        "node_id": "frontier_gate",
        "capacity": 8,
        "consist": "general",
    }
    assert "frontier_shuttle" not in state.trains
    assert state.finance.cash == starting_cash


def test_create_schedule_from_purchased_train_uses_existing_route() -> None:
    state = build_sprint8_scenario()
    state.apply_command(
        PurchaseTrain(
            train_id="frontier_shuttle",
            name="Frontier Shuttle",
            node_id="frontier_gate",
            capacity=8,
        )
    )

    result = state.apply_command(
        CreateSchedule(
            schedule_id="frontier_food_loop",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=8,
            interval_ticks=4,
        )
    )

    assert result["ok"] is True
    assert result["route_travel_ticks"] == 2
    schedule = state.schedules["frontier_food_loop"]
    assert schedule.train_id == "frontier_shuttle"
    assert schedule.origin == "frontier_gate"
    assert schedule.destination == "frontier_settlement"
    assert schedule.next_departure_tick == state.tick + 1

    snapshot = render_snapshot(state)
    snapshot_schedule = next(schedule for schedule in snapshot["schedules"] if schedule["id"] == "frontier_food_loop")
    assert snapshot_schedule["cargo"] == "food"


def test_preview_create_schedule_returns_route_without_mutating_state() -> None:
    state = build_sprint8_scenario()
    state.apply_command(
        PurchaseTrain(
            train_id="frontier_shuttle",
            name="Frontier Shuttle",
            node_id="frontier_gate",
            capacity=8,
        )
    )

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="frontier_food_loop",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=8,
            interval_ticks=4,
        )
    )

    assert result["ok"] is True
    assert result["route_travel_ticks"] == 2
    assert result["route_link_ids"] == ["rail_frontier_gate_settlement"]
    assert result["normalized_command"]["type"] == "CreateSchedule"
    assert "frontier_food_loop" not in state.schedules


def test_invalid_schedule_preview_stays_inside_bridge_command_results() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    snapshot = handle_bridge_message(
        simulation,
        {
            "command": {
                "type": "PreviewCreateSchedule",
                "schedule_id": "bad_schedule",
                "train_id": "atlas",
                "origin": "frontier_gate",
                "destination": "frontier_settlement",
                "cargo_type": "food",
                "units_per_departure": 8,
                "interval_ticks": 4,
            },
            "ticks": 0,
        },
    )

    assert snapshot["bridge"]["ok"] is True
    result = snapshot["bridge"]["command_results"][0]
    assert result["ok"] is False
    assert "not frontier_gate" in str(result["reason"])
    assert "bad_schedule" not in simulation.state.schedules
