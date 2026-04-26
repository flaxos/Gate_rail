"""Tests for Sprint 13D polish: route cargo override and preview cancellation."""

from __future__ import annotations

import pytest

from gaterail.cargo import CargoType
from gaterail.commands import (
    CreateSchedule,
    PreviewBuildLink,
    PreviewBuildNode,
    PreviewCreateSchedule,
    PreviewPurchaseTrain,
    PurchaseTrain,
)
from gaterail.models import LinkMode, NodeKind
from gaterail.scenarios import build_sprint8_scenario


def _purchased_state() -> object:
    state = build_sprint8_scenario()
    state.apply_command(
        PurchaseTrain(
            train_id="frontier_shuttle",
            name="Frontier Shuttle",
            node_id="frontier_gate",
            capacity=8,
        )
    )
    return state


def test_preview_create_schedule_passes_player_chosen_cargo_through() -> None:
    state = _purchased_state()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="frontier_med_loop",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            units_per_departure=4,
            interval_ticks=4,
        )
    )

    assert result["ok"] is True
    assert result["normalized_command"]["cargo_type"] == "medical_supplies"
    assert "frontier_med_loop" not in state.schedules


@pytest.mark.parametrize(
    "cargo",
    [
        CargoType.FOOD,
        CargoType.MEDICAL_SUPPLIES,
        CargoType.CONSTRUCTION_MATERIALS,
    ],
)
def test_create_schedule_records_player_chosen_cargo(cargo: CargoType) -> None:
    state = _purchased_state()

    state.apply_command(
        CreateSchedule(
            schedule_id=f"frontier_loop_{cargo.value}",
            train_id="frontier_shuttle",
            origin="frontier_gate",
            destination="frontier_settlement",
            cargo_type=cargo,
            units_per_departure=4,
            interval_ticks=4,
        )
    )

    schedule = state.schedules[f"frontier_loop_{cargo.value}"]
    assert schedule.cargo_type == cargo


def test_invalid_node_preview_does_not_mutate_state_and_repeat_preview_works() -> None:
    """Cancellation contract: an invalid preview leaves no state, and the player can
    immediately retry with a valid preview without manual cleanup."""

    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    starting_node_count = len(state.nodes)

    bad_result = state.apply_command(
        PreviewBuildNode(
            node_id="ghost",
            world_id="phantom",
            kind=NodeKind.DEPOT,
            name="Ghost",
        )
    )
    assert bad_result["ok"] is False
    assert "ghost" not in state.nodes
    assert state.finance.cash == starting_cash
    assert len(state.nodes) == starting_node_count

    good_result = state.apply_command(
        PreviewBuildNode(
            node_id="frontier_extra_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier Extra Depot",
        )
    )
    assert good_result["ok"] is True
    assert "frontier_extra_depot" not in state.nodes
    assert state.finance.cash == starting_cash


def test_invalid_link_preview_followed_by_valid_link_preview_leaves_state_clean() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    starting_link_count = len(state.links)

    bad_result = state.apply_command(
        PreviewBuildLink(
            link_id="ghost_rail",
            origin="frontier_gate",
            destination="outer_outpost",
            mode=LinkMode.RAIL,
        )
    )
    assert bad_result["ok"] is False
    assert "ghost_rail" not in state.links
    assert state.finance.cash == starting_cash
    assert len(state.links) == starting_link_count

    good_result = state.apply_command(
        PreviewBuildLink(
            link_id="frontier_extra_rail",
            origin="frontier_mine",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
        )
    )
    assert good_result["ok"] is True
    assert "frontier_extra_rail" not in state.links


def test_invalid_train_preview_does_not_mutate_state() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    bad_result = state.apply_command(
        PreviewPurchaseTrain(
            train_id="ghost_train",
            name="Ghost",
            node_id="phantom_node",
            capacity=8,
        )
    )

    assert bad_result["ok"] is False
    assert "ghost_train" not in state.trains
    assert state.finance.cash == starting_cash
