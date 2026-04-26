"""Tests for Sprint 12 construction commands."""

from __future__ import annotations

import json
from io import StringIO

import pytest

from gaterail.bridge import handle_bridge_message
from gaterail.cli import run_cli
from gaterail.commands import BuildLink, BuildNode, DemolishLink, PurchaseTrain, UpgradeNode, command_from_dict
from gaterail.construction import link_build_cost, node_build_cost, node_upgrade_cost, train_purchase_cost
from gaterail.models import LinkMode, NodeKind
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.transport import shortest_route


def test_build_node_creates_node_and_charges_cash() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    result = state.apply_command(
        BuildNode(
            node_id="frontier_north_depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier North Depot",
        )
    )

    assert result["ok"] is True
    assert result["target_id"] == "frontier_north_depot"
    node = state.nodes["frontier_north_depot"]
    assert node.kind == NodeKind.DEPOT
    assert node.world_id == "frontier"
    assert node.storage_capacity == 2_000
    assert node.transfer_limit_per_tick == 36
    assert state.finance.cash == pytest.approx(starting_cash - node_build_cost(NodeKind.DEPOT))
    assert state.finance.costs_total == pytest.approx(node_build_cost(NodeKind.DEPOT))


def test_build_node_overrides_storage_and_transfer_defaults() -> None:
    state = build_sprint8_scenario()

    state.apply_command(
        BuildNode(
            node_id="frontier_yard",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            name="Frontier Yard",
            storage_capacity=500,
            transfer_limit_per_tick=12,
        )
    )

    node = state.nodes["frontier_yard"]
    assert node.storage_capacity == 500
    assert node.transfer_limit_per_tick == 12


def test_build_node_supports_warehouse_defaults() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash

    result = state.apply_command(
        BuildNode(
            node_id="frontier_warehouse",
            world_id="frontier",
            kind=NodeKind.WAREHOUSE,
            name="Frontier Warehouse",
        )
    )

    assert result["ok"] is True
    node = state.nodes["frontier_warehouse"]
    assert node.kind == NodeKind.WAREHOUSE
    assert node.storage_capacity == 4_000
    assert node.transfer_limit_per_tick == 48
    assert state.finance.cash == pytest.approx(starting_cash - node_build_cost(NodeKind.WAREHOUSE))


def test_build_node_rejects_unknown_world() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="unknown world"):
        state.apply_command(
            BuildNode(
                node_id="ghost_yard",
                world_id="phantom",
                kind=NodeKind.DEPOT,
                name="Ghost Yard",
            )
        )
    assert "ghost_yard" not in state.nodes


def test_build_node_rejects_duplicate_node_id() -> None:
    state = build_sprint8_scenario()
    existing_id = next(iter(state.nodes))

    with pytest.raises(ValueError, match="duplicate node id"):
        state.apply_command(
            BuildNode(
                node_id=existing_id,
                world_id="frontier",
                kind=NodeKind.DEPOT,
                name="Conflict",
            )
        )


def test_build_node_rejects_insufficient_cash() -> None:
    state = build_sprint8_scenario()
    state.finance.cash = 100.0

    with pytest.raises(ValueError, match="insufficient cash"):
        state.apply_command(
            BuildNode(
                node_id="frontier_industrial",
                world_id="frontier",
                kind=NodeKind.INDUSTRY,
                name="Frontier Industrial",
            )
        )
    assert "frontier_industrial" not in state.nodes
    assert state.finance.cash == 100.0


def test_command_from_dict_parses_build_node() -> None:
    command = command_from_dict(
        {
            "type": "BuildNode",
            "node_id": "outer_relay",
            "world_id": "outer",
            "kind": "depot",
            "name": "Outer Relay",
            "storage_capacity": 1500,
        }
    )

    assert isinstance(command, BuildNode)
    assert command.kind == NodeKind.DEPOT
    assert command.world_id == "outer"
    assert command.storage_capacity == 1500
    assert command.transfer_limit_per_tick is None


def test_command_from_dict_parses_warehouse_node() -> None:
    command = command_from_dict(
        {
            "type": "BuildNode",
            "node_id": "frontier_warehouse",
            "world_id": "frontier",
            "kind": "warehouse",
            "name": "Frontier Warehouse",
        }
    )

    assert isinstance(command, BuildNode)
    assert command.kind == NodeKind.WAREHOUSE


def test_stdio_bridge_round_trips_build_node_through_snapshot() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    snapshot = handle_bridge_message(
        simulation,
        {
            "command": {
                "type": "BuildNode",
                "node_id": "frontier_industrial",
                "world_id": "frontier",
                "kind": "industry",
                "name": "Frontier Industrial",
            },
            "ticks": 0,
        },
    )

    assert snapshot["bridge"]["ok"] is True
    assert snapshot["bridge"]["command_results"][0]["ok"] is True
    node_ids = {node["id"] for node in snapshot["nodes"]}
    assert "frontier_industrial" in node_ids
    built = next(node for node in snapshot["nodes"] if node["id"] == "frontier_industrial")
    assert built["kind"] == "industry"
    assert built["world_id"] == "frontier"


def test_stdio_bridge_reports_build_node_validation_errors() -> None:
    input_stream = StringIO(
        json.dumps(
            {
                "command": {
                    "type": "BuildNode",
                    "node_id": "ghost",
                    "world_id": "phantom",
                    "kind": "depot",
                    "name": "Ghost",
                },
                "ticks": 0,
            }
        )
        + "\n"
    )
    output_stream = StringIO()

    result = run_cli(["--stdio"], input_stream=input_stream, output=output_stream)

    frame = json.loads(output_stream.getvalue())
    assert result == 0
    assert frame["bridge"]["ok"] is False
    assert "unknown world" in frame["bridge"]["error"]


def test_build_link_creates_link_and_charges_cash() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    cost = link_build_cost(LinkMode.RAIL, 4)

    result = state.apply_command(
        BuildLink(
            link_id="new_rail_link",
            origin="frontier_mine",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
            travel_ticks=4,
            capacity_per_tick=12,
        )
    )

    assert result["ok"] is True
    assert result["target_id"] == "new_rail_link"
    link = state.links["new_rail_link"]
    assert link.mode == LinkMode.RAIL
    assert link.travel_ticks == 4
    assert link.capacity_per_tick == 12
    assert link.build_cost == cost
    assert link.build_time == 8
    assert state.finance.cash == pytest.approx(starting_cash - cost)


def test_build_link_rejects_cross_world_rail() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="within one world"):
        state.apply_command(
            BuildLink(
                link_id="cross_world_rail",
                origin="core_yard",
                destination="frontier_settlement",
                mode=LinkMode.RAIL,
                travel_ticks=1,
                capacity_per_tick=12,
            )
        )

    assert "cross_world_rail" not in state.links


def test_build_link_rejects_self_link() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="must be different"):
        state.apply_command(
            BuildLink(
                link_id="self_loop",
                origin="core_yard",
                destination="core_yard",
                mode=LinkMode.RAIL,
                travel_ticks=1,
                capacity_per_tick=12,
            )
        )


def test_build_link_rejects_duplicate_endpoint_pair() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="duplicate link endpoints"):
        state.apply_command(
            BuildLink(
                link_id="parallel_core_gate",
                origin="core_gate",
                destination="core_yard",
                mode=LinkMode.RAIL,
                travel_ticks=3,
                capacity_per_tick=24,
            )
        )


def test_build_link_rejects_gate_mode_until_gate_construction_sprint() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="rail links only"):
        state.apply_command(
            BuildLink(
                link_id="new_gate_link",
                origin="core_gate",
                destination="frontier_gate",
                mode=LinkMode.GATE,
                travel_ticks=1,
                capacity_per_tick=4,
                power_required=100,
            )
        )


def test_build_link_can_change_shortest_route() -> None:
    state = build_sprint8_scenario()
    before = shortest_route(state, "frontier_mine", "frontier_gate")
    assert before is not None
    assert before.travel_ticks == 6

    state.apply_command(
        BuildLink(
            link_id="rail_frontier_mine_gate_direct",
            origin="frontier_mine",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=18,
        )
    )

    after = shortest_route(state, "frontier_mine", "frontier_gate")
    assert after is not None
    assert after.travel_ticks == 1
    assert after.link_ids == ("rail_frontier_mine_gate_direct",)


def test_built_link_metadata_persists() -> None:
    state = build_sprint8_scenario()
    state.apply_command(
        BuildLink(
            link_id="rail_frontier_mine_gate_direct",
            origin="frontier_mine",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
            travel_ticks=4,
            capacity_per_tick=18,
        )
    )

    restored = state_from_dict(state_to_dict(state))

    link = restored.links["rail_frontier_mine_gate_direct"]
    assert link.build_cost == pytest.approx(link_build_cost(LinkMode.RAIL, 4))
    assert link.build_time == 8


def test_demolish_link_removes_link() -> None:
    state = build_sprint8_scenario()
    target_link = next(iter(state.links))

    result = state.apply_command(DemolishLink(link_id=target_link))

    assert result["ok"] is True
    assert target_link not in state.links


def test_purchase_train_creates_train_and_charges_cash() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    cost = train_purchase_cost(200)
    node_id = next(iter(state.nodes))

    result = state.apply_command(
        PurchaseTrain(
            train_id="new_train_1",
            name="New Freight",
            node_id=node_id,
            capacity=200,
        )
    )

    assert result["ok"] is True
    assert "new_train_1" in state.trains
    train = state.trains["new_train_1"]
    assert train.capacity == 200
    assert state.finance.cash == pytest.approx(starting_cash - cost)


def test_purchase_train_rejects_unknown_node() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="unknown train node"):
        state.apply_command(
            PurchaseTrain(
                train_id="lost_train",
                name="Lost Train",
                node_id="missing_node",
                capacity=20,
            )
        )


def test_purchase_train_rejects_non_positive_capacity() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="capacity must be positive"):
        state.apply_command(
            PurchaseTrain(
                train_id="bad_train",
                name="Bad Train",
                node_id="core_yard",
                capacity=0,
            )
        )


def test_upgrade_node_increases_capacity_and_charges_cash() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    node_id = next(iter(state.nodes))
    node = state.nodes[node_id]
    initial_storage = node.storage_capacity
    initial_transfer = node.transfer_limit_per_tick
    cost = node_upgrade_cost(1000, 10)

    result = state.apply_command(
        UpgradeNode(
            node_id=node_id,
            storage_capacity_increase=1000,
            transfer_limit_increase=10,
        )
    )

    assert result["ok"] is True
    assert node.storage_capacity == initial_storage + 1000
    assert node.transfer_limit_per_tick == initial_transfer + 10
    assert state.finance.cash == pytest.approx(starting_cash - cost)


def test_upgrade_node_rejects_negative_increases_without_charging_cash() -> None:
    state = build_sprint8_scenario()
    starting_cash = state.finance.cash
    node = state.nodes["core_yard"]
    initial_storage = node.storage_capacity
    initial_transfer = node.transfer_limit_per_tick

    with pytest.raises(ValueError, match="cannot be negative"):
        state.apply_command(
            UpgradeNode(
                node_id="core_yard",
                storage_capacity_increase=-100,
                transfer_limit_increase=0,
            )
        )

    assert node.storage_capacity == initial_storage
    assert node.transfer_limit_per_tick == initial_transfer
    assert state.finance.cash == starting_cash


def test_upgrade_node_rejects_noop_upgrade() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="must increase"):
        state.apply_command(
            UpgradeNode(
                node_id="core_yard",
                storage_capacity_increase=0,
                transfer_limit_increase=0,
            )
        )


def test_command_from_dict_parses_build_link() -> None:
    command = command_from_dict(
        {
            "type": "BuildLink",
            "link_id": "test_link",
            "origin": "node_a",
            "destination": "node_b",
            "mode": "rail",
            "travel_ticks": 5,
            "capacity_per_tick": 20,
        }
    )

    assert isinstance(command, BuildLink)
    assert command.mode == LinkMode.RAIL
    assert command.travel_ticks == 5
