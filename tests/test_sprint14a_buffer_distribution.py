"""Tests for Sprint 14A depot/warehouse buffer distribution."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.economy import apply_buffer_distribution
from gaterail.models import (
    DevelopmentTier,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    WorldState,
)
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _world_with_buffer_and_settlement(
    *,
    buffer_kind: NodeKind = NodeKind.DEPOT,
    buffer_inventory: dict[CargoType, int] | None = None,
    settlement_demand: dict[CargoType, int] | None = None,
    settlement_inventory: dict[CargoType, int] | None = None,
    transfer_limit: int = 24,
    extra_settlements: list[dict] | None = None,
) -> GameState:
    """Build a one-world scenario with a buffer node railed to one or more settlements."""

    state = GameState()
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=10_000,
            stability=0.7,
            power_available=200,
            power_used=40,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Frontier Depot",
            world_id="frontier",
            kind=buffer_kind,
            inventory=dict(buffer_inventory or {}),
            storage_capacity=2_000,
            transfer_limit_per_tick=transfer_limit,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Frontier Settlement",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory=dict(settlement_inventory or {}),
            demand=dict(settlement_demand or {}),
            storage_capacity=500,
            transfer_limit_per_tick=24,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_depot_settlement",
            origin="frontier_depot",
            destination="frontier_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    for spec in extra_settlements or []:
        state.add_node(
            NetworkNode(
                id=spec["id"],
                name=spec.get("name", spec["id"]),
                world_id="frontier",
                kind=NodeKind.SETTLEMENT,
                demand=dict(spec.get("demand", {})),
                inventory=dict(spec.get("inventory", {})),
                storage_capacity=500,
                transfer_limit_per_tick=24,
            )
        )
        state.add_link(
            NetworkLink(
                id=f"rail_depot_{spec['id']}",
                origin="frontier_depot",
                destination=spec["id"],
                mode=LinkMode.RAIL,
                travel_ticks=2,
                capacity_per_tick=12,
            )
        )
    return state


def test_depot_pushes_cargo_to_neighbour_with_unmet_demand() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 50},
        settlement_demand={CargoType.FOOD: 5},
    )

    distribution = apply_buffer_distribution(state)

    settlement = state.nodes["frontier_settlement"]
    depot = state.nodes["frontier_depot"]
    assert settlement.stock(CargoType.FOOD) == 5
    assert depot.stock(CargoType.FOOD) == 45
    assert distribution == {
        "frontier_depot": {"frontier_settlement": {CargoType.FOOD: 5}}
    }
    assert state.buffer_distribution == distribution


def test_depot_only_fills_demand_deficit_not_surplus() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 50},
        settlement_demand={CargoType.FOOD: 5},
        settlement_inventory={CargoType.FOOD: 4},
    )

    apply_buffer_distribution(state)

    assert state.nodes["frontier_settlement"].stock(CargoType.FOOD) == 5
    assert state.nodes["frontier_depot"].stock(CargoType.FOOD) == 49


def test_depot_skips_neighbours_already_satisfied() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 50},
        settlement_demand={CargoType.FOOD: 5},
        settlement_inventory={CargoType.FOOD: 10},
    )

    distribution = apply_buffer_distribution(state)

    assert distribution == {}
    assert state.nodes["frontier_depot"].stock(CargoType.FOOD) == 50


def test_buffer_respects_transfer_limit_across_outflows() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 200, CargoType.MEDICAL_SUPPLIES: 200},
        settlement_demand={CargoType.FOOD: 30},
        transfer_limit=10,
        extra_settlements=[
            {"id": "frontier_outpost", "demand": {CargoType.MEDICAL_SUPPLIES: 30}}
        ],
    )

    apply_buffer_distribution(state)

    depot = state.nodes["frontier_depot"]
    settlement = state.nodes["frontier_settlement"]
    outpost = state.nodes["frontier_outpost"]
    pushed_food = settlement.stock(CargoType.FOOD)
    pushed_med = outpost.stock(CargoType.MEDICAL_SUPPLIES)
    # Outpost is alphabetically first among neighbours and consumes the entire
    # 10-unit budget on its medical_supplies demand.
    assert pushed_food == 0
    assert pushed_med == 10
    assert pushed_food + pushed_med == 10
    assert depot.stock(CargoType.FOOD) == 200
    assert depot.stock(CargoType.MEDICAL_SUPPLIES) == 190


def test_warehouse_kind_also_buffers() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_kind=NodeKind.WAREHOUSE,
        buffer_inventory={CargoType.FOOD: 20},
        settlement_demand={CargoType.FOOD: 4},
    )

    apply_buffer_distribution(state)

    assert state.nodes["frontier_settlement"].stock(CargoType.FOOD) == 4


def test_non_buffer_kinds_do_not_auto_feed() -> None:
    """An EXTRACTOR with cargo and a railed settlement neighbour does not auto-push."""

    state = GameState()
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink",
            tier=DevelopmentTier.OUTPOST,
            population=10_000,
            stability=0.7,
            power_available=200,
            power_used=40,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_mine",
            name="Frontier Mine",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            inventory={CargoType.ORE: 50},
            storage_capacity=1_000,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_industry",
            name="Frontier Industry",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            demand={CargoType.ORE: 5},
            storage_capacity=500,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_mine_industry",
            origin="frontier_mine",
            destination="frontier_industry",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )

    apply_buffer_distribution(state)

    assert state.nodes["frontier_industry"].stock(CargoType.ORE) == 0
    assert state.nodes["frontier_mine"].stock(CargoType.ORE) == 50
    assert state.buffer_distribution == {}


def test_buffer_does_not_cross_gate_links() -> None:
    """Cargo never auto-jumps a gate even if the gate hub has a settlement-side neighbour."""

    state = GameState()
    for world_id in ("core", "frontier"):
        state.add_world(
            WorldState(
                id=world_id,
                name=world_id.title(),
                tier=DevelopmentTier.FRONTIER_COLONY,
                population=10_000,
                stability=0.8,
                power_available=400,
                power_used=80,
            )
        )
    state.add_node(
        NetworkNode(
            id="core_depot",
            name="Core Depot",
            world_id="core",
            kind=NodeKind.DEPOT,
            inventory={CargoType.FOOD: 50},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Core Gate",
            world_id="core",
            kind=NodeKind.GATE_HUB,
            storage_capacity=200,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Frontier Gate",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=200,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Frontier Settlement",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            demand={CargoType.FOOD: 5},
            storage_capacity=500,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_core_yard_gate",
            origin="core_depot",
            destination="core_gate",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_core_frontier",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=2,
            power_required=20,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_gate_settlement",
            origin="frontier_gate",
            destination="frontier_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )

    apply_buffer_distribution(state)

    assert state.nodes["frontier_settlement"].stock(CargoType.FOOD) == 0
    assert state.nodes["core_depot"].stock(CargoType.FOOD) == 50


def test_buffer_runs_each_tick_in_full_simulation() -> None:
    """A depot keeps a railed settlement supplied across multiple ticks without any train."""

    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 100},
        settlement_demand={CargoType.FOOD: 3},
    )
    simulation = TickSimulation(state=state)

    reports = simulation.run_ticks(4)

    settlement = state.nodes["frontier_settlement"]
    depot = state.nodes["frontier_depot"]
    assert depot.stock(CargoType.FOOD) == 100 - (3 * 4)
    assert settlement.stock(CargoType.FOOD) == 0  # Consumed each tick.
    assert all(report["buffer_distribution"]["frontier_depot"]["frontier_settlement"]["food"] == 3 for report in reports)
    assert state.shortages == {}


def test_snapshot_exposes_buffer_fill_and_served_for_buffer_nodes_only() -> None:
    state = _world_with_buffer_and_settlement(
        buffer_inventory={CargoType.FOOD: 20},
        settlement_demand={CargoType.FOOD: 4},
    )
    apply_buffer_distribution(state)

    snapshot = render_snapshot(state)

    by_id = {node["id"]: node for node in snapshot["nodes"]}
    depot_node = by_id["frontier_depot"]
    settlement_node = by_id["frontier_settlement"]

    assert depot_node["buffer_fill_pct"] is not None
    assert depot_node["served_last_tick"] == {"frontier_settlement": {"food": 4}}

    assert settlement_node["buffer_fill_pct"] is None
    assert settlement_node["served_last_tick"] == {}
