"""Tests for Sprint 15A gate-link preview and construction."""

from __future__ import annotations

import pytest

from gaterail.commands import BuildLink, PreviewBuildLink, command_from_dict
from gaterail.construction import (
    DEFAULT_GATE_CAPACITY_PER_TICK,
    DEFAULT_GATE_POWER_REQUIRED,
    DEFAULT_GATE_TRAVEL_TICKS,
    link_build_cost,
)
from gaterail.models import LinkMode, NetworkNode, NodeKind
from gaterail.scenarios import build_sprint8_scenario
from gaterail.snapshot import render_snapshot
from gaterail.transport import shortest_route


def _state_with_extra_gate_hub() -> object:
    state = build_sprint8_scenario()
    state.finance.cash = 50_000.0
    state.add_node(
        NetworkNode(
            id="frontier_aux_gate",
            name="Frontier Auxiliary Gate",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=1_500,
        )
    )
    return state


def test_command_from_dict_defaults_gate_link_power_capacity_and_travel() -> None:
    command = command_from_dict(
        {
            "type": "PreviewBuildLink",
            "link_id": "gate_core_frontier_aux",
            "origin": "core_gate",
            "destination": "frontier_aux_gate",
            "mode": "gate",
        }
    )

    assert isinstance(command, PreviewBuildLink)
    assert command.mode == LinkMode.GATE
    assert command.travel_ticks is None
    assert command.capacity_per_tick == DEFAULT_GATE_CAPACITY_PER_TICK
    assert command.power_required == DEFAULT_GATE_POWER_REQUIRED


def test_preview_gate_link_returns_cost_power_context_and_normalized_command() -> None:
    state = _state_with_extra_gate_hub()
    starting_cash = state.finance.cash

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_core_frontier_aux",
            origin="core_gate",
            destination="frontier_aux_gate",
            mode=LinkMode.GATE,
            travel_ticks=None,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="core",
        )
    )

    assert result["ok"] is True
    assert result["mode"] == "gate"
    assert result["cost"] == pytest.approx(link_build_cost(LinkMode.GATE, DEFAULT_GATE_TRAVEL_TICKS))
    assert result["build_time"] == 2
    assert result["travel_ticks"] == DEFAULT_GATE_TRAVEL_TICKS
    assert result["capacity_per_tick"] == DEFAULT_GATE_CAPACITY_PER_TICK
    assert result["power_required"] == DEFAULT_GATE_POWER_REQUIRED
    assert result["power_source_world_id"] == "core"
    assert result["origin_world_id"] == "core"
    assert result["destination_world_id"] == "frontier"
    assert result["powered_if_built"] is True
    assert result["normalized_command"] == {
        "type": "BuildLink",
        "link_id": "gate_core_frontier_aux",
        "origin": "core_gate",
        "destination": "frontier_aux_gate",
        "mode": "gate",
        "travel_ticks": DEFAULT_GATE_TRAVEL_TICKS,
        "capacity_per_tick": DEFAULT_GATE_CAPACITY_PER_TICK,
        "bidirectional": True,
        "power_required": DEFAULT_GATE_POWER_REQUIRED,
        "power_source_world_id": "core",
    }
    assert "gate_core_frontier_aux" not in state.links
    assert state.finance.cash == starting_cash


def test_build_gate_link_creates_interworld_route_and_snapshot_context() -> None:
    state = _state_with_extra_gate_hub()

    result = state.apply_command(
        BuildLink(
            link_id="gate_core_frontier_aux",
            origin="core_gate",
            destination="frontier_aux_gate",
            mode=LinkMode.GATE,
            travel_ticks=None,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="core",
        )
    )

    assert result["ok"] is True
    assert result["powered_if_built"] is True
    assert result["power_shortfall"] == 0
    link = state.links["gate_core_frontier_aux"]
    assert link.mode == LinkMode.GATE
    assert link.travel_ticks == DEFAULT_GATE_TRAVEL_TICKS
    assert link.capacity_per_tick == DEFAULT_GATE_CAPACITY_PER_TICK
    assert link.power_required == DEFAULT_GATE_POWER_REQUIRED
    assert link.power_source_world_id == "core"

    route = shortest_route(state, "frontier_aux_gate", "core_yard")
    assert route is not None
    assert "gate_core_frontier_aux" in route.link_ids

    snapshot = render_snapshot(state)
    link_snapshot = next(link for link in snapshot["links"] if link["id"] == "gate_core_frontier_aux")
    assert link_snapshot["mode"] == "gate"
    assert link_snapshot["powered"] is True
    assert link_snapshot["power_required"] == DEFAULT_GATE_POWER_REQUIRED


def test_gate_link_rejects_non_gate_hub_endpoint() -> None:
    state = build_sprint8_scenario()

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_core_settlement",
            origin="core_gate",
            destination="frontier_settlement",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
        )
    )

    assert result["ok"] is False
    assert "gate_hub endpoints" in str(result["reason"])


def test_gate_link_rejects_same_world_gate_hubs() -> None:
    state = build_sprint8_scenario()
    state.add_node(
        NetworkNode(
            id="frontier_aux_gate",
            name="Frontier Auxiliary Gate",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
        )
    )

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_frontier_local",
            origin="frontier_gate",
            destination="frontier_aux_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
        )
    )

    assert result["ok"] is False
    assert "different worlds" in str(result["reason"])


def test_gate_preview_surfaces_power_shortfall_without_rejecting_build() -> None:
    state = _state_with_extra_gate_hub()
    state.worlds["frontier"].power_available = 70
    state.worlds["frontier"].power_used = 40

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_frontier_core_aux",
            origin="frontier_aux_gate",
            destination="core_gate",
            mode=LinkMode.GATE,
            capacity_per_tick=DEFAULT_GATE_CAPACITY_PER_TICK,
            power_required=DEFAULT_GATE_POWER_REQUIRED,
            power_source_world_id="frontier",
        )
    )

    assert result["ok"] is True
    assert result["powered_if_built"] is False
    assert result["power_available"] == 30
    assert result["power_shortfall"] == 50
