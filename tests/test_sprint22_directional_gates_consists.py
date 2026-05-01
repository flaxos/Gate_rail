"""Tests for Sprint 22 directional gates and typed train consists."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import (
    BuildLink,
    CreateSchedule,
    PreviewBuildLink,
    PreviewCreateSchedule,
    PreviewPurchaseTrain,
)
from gaterail.construction import DEFAULT_GATE_CAPACITY_PER_TICK, DEFAULT_GATE_POWER_REQUIRED
from gaterail.freight import advance_freight
from gaterail.models import FreightSchedule, FreightTrain, LinkMode, TrainConsist
from gaterail.scenarios import build_sprint8_scenario
from gaterail.snapshot import render_snapshot
from gaterail.transport import shortest_route


def test_default_frontier_scenario_uses_distinct_gate_hubs_for_core_and_ashfall() -> None:
    state = build_sprint8_scenario()

    core_link = state.links["gate_core_frontier"]
    outer_link = state.links["gate_frontier_outer"]
    frontier_gate_endpoints = [
        node_id
        for link in (core_link, outer_link)
        for node_id in (link.origin, link.destination)
        if state.nodes[node_id].world_id == "frontier"
    ]

    assert sorted(frontier_gate_endpoints) == ["frontier_gate", "frontier_outer_gate"]
    assert state.nodes["frontier_gate"].kind == state.nodes["frontier_outer_gate"].kind
    assert state.nodes["frontier_gate"].world_id == "frontier"
    assert state.nodes["frontier_outer_gate"].world_id == "frontier"
    assert shortest_route(state, "frontier_settlement", "outer_outpost") is not None


def test_directional_gate_routes_only_source_to_exit() -> None:
    state = build_sprint8_scenario()
    state.finance.cash = 50_000.0
    del state.links["gate_core_frontier"]

    result = state.apply_command(
        BuildLink(
            link_id="gate_core_frontier_oneway",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="core",
            bidirectional=False,
        )
    )

    assert result["ok"] is True
    assert result["directional"] is True
    assert shortest_route(state, "core_yard", "frontier_settlement") is not None
    assert shortest_route(state, "frontier_settlement", "core_yard") is None

    snapshot = render_snapshot(state)
    link = next(item for item in snapshot["links"] if item["id"] == "gate_core_frontier_oneway")
    assert link["directional"] is True
    assert link["source_node_id"] == "core_gate"
    assert link["exit_node_id"] == "frontier_gate"


def test_reciprocal_directional_gate_link_is_allowed_but_same_direction_duplicate_is_rejected() -> None:
    state = build_sprint8_scenario()
    state.finance.cash = 50_000.0
    del state.links["gate_core_frontier"]
    state.apply_command(
        BuildLink(
            link_id="gate_core_frontier_oneway",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="core",
            bidirectional=False,
        )
    )

    reverse_preview = state.apply_command(
        PreviewBuildLink(
            link_id="gate_frontier_core_oneway",
            origin="frontier_gate",
            destination="core_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="frontier",
            bidirectional=False,
        )
    )
    duplicate_preview = state.apply_command(
        PreviewBuildLink(
            link_id="gate_core_frontier_duplicate",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="core",
            bidirectional=False,
        )
    )

    assert reverse_preview["ok"] is True
    assert reverse_preview["reverse_available"] is True
    assert reverse_preview["reverse_link_id"] == "gate_core_frontier_oneway"
    assert duplicate_preview["ok"] is False
    assert "duplicate link endpoints" in str(duplicate_preview["reason"])


def test_invalid_train_consist_preview_is_rejected() -> None:
    state = build_sprint8_scenario()

    result = state.apply_command(
        PreviewPurchaseTrain(
            train_id="bad_train",
            name="Bad Train",
            node_id="core_yard",
            capacity=10,
            consist="not_real",
        )
    )

    assert result["ok"] is False
    assert "unknown train consist" in str(result["reason"])


def test_schedule_preview_requires_compatible_specialized_consist() -> None:
    state = build_sprint8_scenario()
    state.trains["electronics_shuttle"] = FreightTrain(
        id="electronics_shuttle",
        name="Electronics Shuttle",
        node_id="core_yard",
        capacity=10,
        consist=TrainConsist.PROTECTED,
    )

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="bad_ore_service",
            train_id="electronics_shuttle",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.ORE,
            units_per_departure=4,
            interval_ticks=6,
        )
    )

    assert result["ok"] is False
    assert "requires bulk_hopper consist" in str(result["reason"])


def test_matching_specialized_consist_can_create_schedule_for_specialized_cargo() -> None:
    state = build_sprint8_scenario()
    state.trains["ore_shuttle"] = FreightTrain(
        id="ore_shuttle",
        name="Ore Shuttle",
        node_id="frontier_mine",
        capacity=10,
        consist=TrainConsist.BULK_HOPPER,
    )

    result = state.apply_command(
        CreateSchedule(
            schedule_id="focused_ore_service",
            train_id="ore_shuttle",
            origin="frontier_mine",
            destination="core_yard",
            cargo_type=CargoType.ORE,
            units_per_departure=4,
            interval_ticks=6,
        )
    )

    assert result["ok"] is True
    assert result["required_consist"] == "bulk_hopper"
    assert result["train_consist"] == "bulk_hopper"


def test_runtime_blocks_wrong_specialized_consist_without_loading_cargo() -> None:
    state = build_sprint8_scenario()
    state.schedules.clear()
    state.nodes["frontier_mine"].inventory[CargoType.ORE] = 12
    state.trains["protected_shuttle"] = FreightTrain(
        id="protected_shuttle",
        name="Protected Shuttle",
        node_id="frontier_mine",
        capacity=8,
        consist=TrainConsist.PROTECTED,
    )
    state.schedules["bad_runtime_service"] = FreightSchedule(
        id="bad_runtime_service",
        train_id="protected_shuttle",
        origin="frontier_mine",
        destination="core_yard",
        cargo_type=CargoType.ORE,
        units_per_departure=4,
        interval_ticks=6,
        next_departure_tick=0,
    )

    report = advance_freight(state)

    assert state.trains["protected_shuttle"].cargo_units == 0
    assert state.nodes["frontier_mine"].inventory[CargoType.ORE] == 12
    assert any(
        "requires bulk_hopper consist" in str(event["reason"])
        for event in report["blocked"]
    )
