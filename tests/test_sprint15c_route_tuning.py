"""Tests for Sprint 15C route unit/interval tuning contract."""

from __future__ import annotations

import pytest

from gaterail.cargo import CargoType
from gaterail.commands import CreateSchedule, PreviewCreateSchedule, PurchaseTrain
from gaterail.scenarios import build_sprint8_scenario


def _frontier_route_state() -> object:
    state = build_sprint8_scenario()
    state.apply_command(
        PurchaseTrain(
            train_id="frontier_shuttle",
            name="Frontier Shuttle",
            node_id="frontier_gate",
            capacity=12,
        )
    )
    return state


def test_preview_create_schedule_preserves_player_tuned_units_and_interval() -> None:
    state = _frontier_route_state()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="frontier_food_loop_tuned",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=5,
            interval_ticks=11,
        )
    )

    assert result["ok"] is True
    assert result["normalized_command"]["units_per_departure"] == 5
    assert result["normalized_command"]["interval_ticks"] == 11
    assert "frontier_food_loop_tuned" not in state.schedules


def test_create_schedule_records_player_tuned_units_and_interval() -> None:
    state = _frontier_route_state()

    result = state.apply_command(
        CreateSchedule(
            schedule_id="frontier_food_loop_tuned",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=5,
            interval_ticks=11,
        )
    )

    assert result["ok"] is True
    schedule = state.schedules["frontier_food_loop_tuned"]
    assert schedule.units_per_departure == 5
    assert schedule.interval_ticks == 11


@pytest.mark.parametrize(
    ("units", "interval", "message"),
    [
        (0, 4, "units_per_departure must be positive"),
        (5, 0, "interval_ticks must be positive"),
        (13, 4, "units_per_departure cannot exceed train capacity"),
    ],
)
def test_preview_create_schedule_rejects_invalid_tuned_values(
    units: int,
    interval: int,
    message: str,
) -> None:
    state = _frontier_route_state()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="frontier_bad_tuning",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=units,
            interval_ticks=interval,
        )
    )

    assert result["ok"] is False
    assert message in str(result["reason"])
    assert "frontier_bad_tuning" not in state.schedules
