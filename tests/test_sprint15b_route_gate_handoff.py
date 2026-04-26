"""Tests for Sprint 15B route preview gate-handoff context."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import CreateSchedule, PreviewCreateSchedule
from gaterail.gate import evaluate_gate_power
from gaterail.scenarios import build_sprint4_scenario, build_sprint8_scenario


def test_preview_schedule_includes_gate_handoff_context() -> None:
    state = build_sprint8_scenario()
    evaluate_gate_power(state)

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="core_food_gate_preview",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is True
    assert result["gate_link_ids"] == ["gate_core_frontier"]
    assert result["route_warnings"] == []
    handoff = result["gate_handoffs"][0]
    assert handoff["link_id"] == "gate_core_frontier"
    assert handoff["from_world_id"] == "core"
    assert handoff["to_world_id"] == "frontier"
    assert handoff["powered"] is True
    assert handoff["slot_capacity"] == 2


def test_preview_schedule_warns_when_gate_slots_are_saturated() -> None:
    state = build_sprint8_scenario()
    evaluate_gate_power(state)
    status = state.gate_statuses["gate_core_frontier"]
    status.slots_used = status.slot_capacity

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="core_food_gate_hot",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is True
    assert result["gate_handoffs"][0]["slots_used"] == result["gate_handoffs"][0]["slot_capacity"]
    assert result["gate_handoffs"][0]["pressure"] == 1.0
    assert result["route_warnings"] == [
        {
            "link_id": "gate_core_frontier",
            "severity": "congested",
            "reason": "gate slots full on gate_core_frontier",
        }
    ]


def test_preview_schedule_warns_when_gate_is_degraded_by_disruption() -> None:
    state = build_sprint8_scenario()
    state.tick = 13
    evaluate_gate_power(state)

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="ashfall_med_gate_degraded",
            train_id="atlas",
            origin="core_yard",
            destination="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is True
    warning = next(
        warning for warning in result["route_warnings"] if warning["link_id"] == "gate_frontier_outer"
    )
    assert warning["severity"] == "degraded"
    assert warning["reason"] == "gate alignment throttling"
    handoff = next(
        handoff for handoff in result["gate_handoffs"] if handoff["link_id"] == "gate_frontier_outer"
    )
    assert handoff["slot_capacity"] == 1
    assert handoff["base_capacity"] == 2
    assert handoff["disrupted"] is True


def test_invalid_preview_schedule_reports_unpowered_gate_handoff() -> None:
    state = build_sprint4_scenario()

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="ashfall_med_unpowered",
            train_id="mercy",
            origin="frontier_settlement",
            destination="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            units_per_departure=1,
            interval_ticks=8,
        )
    )

    assert result["ok"] is False
    assert "no route frontier_settlement->outer_outpost" in result["reason"]
    assert result["gate_link_ids"] == ["gate_frontier_outer"]
    assert result["route_warnings"] == [
        {
            "link_id": "gate_frontier_outer",
            "severity": "blocked",
            "reason": "gate gate_frontier_outer unpowered",
        }
    ]
    assert result["gate_handoffs"][0]["powered"] is False
    assert result["gate_handoffs"][0]["power_shortfall"] > 0


def test_create_schedule_returns_same_gate_handoff_context_as_preview() -> None:
    state = build_sprint8_scenario()
    evaluate_gate_power(state)

    result = state.apply_command(
        CreateSchedule(
            schedule_id="core_food_gate_created",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=4,
            interval_ticks=8,
        )
    )

    assert result["ok"] is True
    assert result["gate_link_ids"] == ["gate_core_frontier"]
    assert result["gate_handoffs"][0]["from_world_name"] == "Vesta Core"
    assert result["gate_handoffs"][0]["to_world_name"] == "Brink Frontier"
