"""Tests for Sprint 13A construction preview and local layout metadata."""

from __future__ import annotations

import pytest

from gaterail.bridge import handle_bridge_message
from gaterail.commands import (
    BuildLink,
    BuildNode,
    PreviewBuildLink,
    PreviewBuildNode,
    command_from_dict,
)
from gaterail.construction import link_build_cost, node_build_cost
from gaterail.models import LinkMode, NodeKind
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_command_from_dict_parses_preview_build_node_with_layout() -> None:
    command = command_from_dict(
        {
            "type": "PreviewBuildNode",
            "node_id": "frontier_south_depot",
            "world_id": "frontier",
            "kind": "depot",
            "name": "Frontier South Depot",
            "layout": {"x": 42.5, "y": 99.25},
        }
    )

    assert isinstance(command, PreviewBuildNode)
    assert command.kind == NodeKind.DEPOT
    assert command.layout_x == 42.5
    assert command.layout_y == 99.25


def test_preview_build_node_returns_cost_without_mutating_state() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    result = state.apply_command(
        PreviewBuildNode(
            node_id="frontier_south_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier South Depot",
            layout_x=42.5,
            layout_y=99.25,
        )
    )

    assert result["ok"] is True
    assert result["target_id"] == "frontier_south_depot"
    assert result["cost"] == pytest.approx(node_build_cost(NodeKind.DEPOT))
    assert result["layout"] == {"x": 42.5, "y": 99.25}
    assert result["normalized_command"] == {
        "type": "BuildNode",
        "node_id": "frontier_south_depot",
        "world_id": "frontier",
        "kind": "depot",
        "name": "Frontier South Depot",
        "storage_capacity": 2_000,
        "transfer_limit_per_tick": 36,
        "layout": {"x": 42.5, "y": 99.25},
    }
    assert "frontier_south_depot" not in state.nodes
    assert state.finance.cash == starting_cash


def test_invalid_build_node_preview_returns_result_without_raising() -> None:
    state = build_sprint8_scenario()
    existing_id = next(iter(state.nodes))

    result = state.apply_command(
        PreviewBuildNode(
            node_id=existing_id,
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Conflict",
        )
    )

    assert result["ok"] is False
    assert result["target_id"] == existing_id
    assert "duplicate node id" in str(result["reason"])


def test_build_node_layout_persists_through_save_and_snapshot() -> None:
    state = build_sprint8_scenario()

    state.apply_command(
        BuildNode(
            node_id="frontier_south_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier South Depot",
            layout_x=42.5,
            layout_y=99.25,
        )
    )

    restored = state_from_dict(state_to_dict(state))
    restored_node = restored.nodes["frontier_south_depot"]
    assert restored_node.layout_x == 42.5
    assert restored_node.layout_y == 99.25

    snapshot = render_snapshot(restored)
    snapshot_node = next(node for node in snapshot["nodes"] if node["id"] == "frontier_south_depot")
    assert snapshot_node["layout"] == {"x": 42.5, "y": 99.25}


def test_preview_build_link_returns_backend_cost_without_mutating_state() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    result = state.apply_command(
        PreviewBuildLink(
            link_id="rail_frontier_mine_gate_direct",
            origin="frontier_mine",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
            travel_ticks=4,
            capacity_per_tick=24,
        )
    )

    assert result["ok"] is True
    assert result["cost"] == pytest.approx(link_build_cost(LinkMode.RAIL, 4))
    assert result["build_time"] == 8
    assert result["travel_ticks"] == 4
    assert result["normalized_command"] == {
        "type": "BuildLink",
        "link_id": "rail_frontier_mine_gate_direct",
        "origin": "frontier_mine",
        "destination": "frontier_gate",
        "mode": "rail",
        "travel_ticks": 4,
        "capacity_per_tick": 24,
        "bidirectional": True,
    }
    assert "rail_frontier_mine_gate_direct" not in state.links
    assert state.finance.cash == starting_cash


def test_invalid_build_link_preview_stays_inside_bridge_command_results() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    snapshot = handle_bridge_message(
        simulation,
        {
            "command": {
                "type": "PreviewBuildLink",
                "link_id": "cross_world_rail",
                "origin": "core_yard",
                "destination": "frontier_settlement",
                "mode": "rail",
            },
            "ticks": 0,
        },
    )

    assert snapshot["bridge"]["ok"] is True
    result = snapshot["bridge"]["command_results"][0]
    assert result["ok"] is False
    assert result["target_id"] == "cross_world_rail"
    assert "within one world" in str(result["reason"])
    link_ids = {link["id"] for link in snapshot["links"]}
    assert "cross_world_rail" not in link_ids


def test_build_link_can_derive_travel_ticks_from_persisted_layout() -> None:
    state = build_sprint8_scenario()
    state.apply_command(
        BuildNode(
            node_id="frontier_west_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier West Depot",
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.apply_command(
        BuildNode(
            node_id="frontier_east_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier East Depot",
            layout_x=120.0,
            layout_y=0.0,
        )
    )

    result = state.apply_command(
        BuildLink(
            link_id="rail_frontier_west_east",
            origin="frontier_west_depot",
            destination="frontier_east_depot",
            mode=LinkMode.RAIL,
        )
    )

    assert result["ok"] is True
    assert result["travel_ticks"] == 2
    link = state.links["rail_frontier_west_east"]
    assert link.travel_ticks == 2
    assert link.build_cost == pytest.approx(link_build_cost(LinkMode.RAIL, 2))
