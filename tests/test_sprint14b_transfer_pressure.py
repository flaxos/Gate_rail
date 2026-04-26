"""Tests for Sprint 14B transfer-limit pressure visibility."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.economy import (
    SATURATION_THRESHOLD,
    apply_buffer_distribution,
    update_transfer_saturation_streaks,
)
from gaterail.models import (
    DevelopmentTier,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    TrainStatus,
    WorldState,
)
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _world() -> WorldState:
    return WorldState(
        id="frontier",
        name="Brink Frontier",
        tier=DevelopmentTier.OUTPOST,
        population=10_000,
        stability=0.7,
        power_available=200,
        power_used=40,
    )


def _depot_with_settlement(
    *,
    depot_inventory: dict[CargoType, int] | None = None,
    settlement_demand: dict[CargoType, int] | None = None,
    transfer_limit: int = 24,
) -> GameState:
    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Frontier Depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory=dict(depot_inventory or {}),
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
    return state


def test_buffer_distribution_records_transfer_on_both_ends() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 50},
        settlement_demand={CargoType.FOOD: 8},
        transfer_limit=10,
    )

    apply_buffer_distribution(state)

    assert state.transfer_used_this_tick["frontier_depot"] == 8
    assert state.transfer_used_this_tick["frontier_settlement"] == 8


def test_train_unload_records_transfer_on_destination() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 0},
        settlement_demand={},
        transfer_limit=24,
    )
    state.trains["shuttle"] = FreightTrain(
        id="shuttle",
        name="Brink Shuttle",
        node_id="frontier_settlement",
        capacity=20,
        status=TrainStatus.IN_TRANSIT,
        cargo_type=CargoType.FOOD,
        cargo_units=12,
        destination="frontier_settlement",
        route_node_ids=("frontier_depot", "frontier_settlement"),
        route_link_ids=("rail_depot_settlement",),
        remaining_ticks=1,
    )
    simulation = TickSimulation(state=state)

    simulation.step_tick()

    assert state.transfer_used_this_tick.get("frontier_settlement", 0) == 12


def test_dispatch_records_transfer_on_origin() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 50},
        settlement_demand={},
        transfer_limit=24,
    )
    state.trains["shuttle"] = FreightTrain(
        id="shuttle",
        name="Brink Shuttle",
        node_id="frontier_depot",
        capacity=20,
        status=TrainStatus.IDLE,
    )
    from gaterail.models import FreightOrder

    state.add_order(
        FreightOrder(
            id="order_food",
            train_id="shuttle",
            origin="frontier_depot",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            requested_units=15,
        )
    )

    simulation = TickSimulation(state=state)
    simulation.step_tick()

    # 15 units load into the train at the depot — depot side records the loaded
    # outflow even though the buffer phase will also push 0 (no demand).
    used = state.transfer_used_this_tick.get("frontier_depot", 0)
    assert used >= 15


def test_saturation_streak_increments_when_at_or_above_threshold() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 200},
        settlement_demand={CargoType.FOOD: 50},
        transfer_limit=10,
    )

    simulation = TickSimulation(state=state)
    simulation.step_tick()
    simulation.step_tick()

    # Depot pushes 10 each tick (full budget). 10/10 = 1.0 >= threshold.
    assert state.transfer_saturation_streak["frontier_depot"] == 2


def test_saturation_streak_resets_when_idle() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 200},
        settlement_demand={CargoType.FOOD: 50},
        transfer_limit=10,
    )

    simulation = TickSimulation(state=state)
    simulation.step_tick()
    assert state.transfer_saturation_streak.get("frontier_depot", 0) == 1

    # Drain the depot so next tick has nothing to push.
    state.nodes["frontier_depot"].inventory.clear()
    simulation.step_tick()

    assert "frontier_depot" not in state.transfer_saturation_streak


def test_saturation_threshold_is_inclusive_at_95_percent() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 200},
        settlement_demand={CargoType.FOOD: 19},
        transfer_limit=20,
    )

    apply_buffer_distribution(state)
    update_transfer_saturation_streaks(state)

    # 19/20 = 0.95 — exactly at threshold counts as saturated.
    assert state.transfer_used_this_tick["frontier_depot"] == 19
    assert 19 / 20 >= SATURATION_THRESHOLD
    assert state.transfer_saturation_streak["frontier_depot"] == 1


def test_snapshot_exposes_transfer_pressure_fields() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 200},
        settlement_demand={CargoType.FOOD: 50},
        transfer_limit=10,
    )
    simulation = TickSimulation(state=state)
    simulation.step_tick()
    simulation.step_tick()

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    depot = by_id["frontier_depot"]

    assert depot["transfer_limit"] == 10
    assert depot["transfer_used"] == 10
    assert depot["transfer_pressure"] == 1.0
    assert depot["saturation_streak"] == 2

    settlement = by_id["frontier_settlement"]
    assert settlement["transfer_limit"] == 24
    # Settlement consumes the food on demand each tick, so its inbound transfer
    # tally for the most recent tick reflects the buffer push of 10 units.
    assert settlement["transfer_used"] == 10
    assert settlement["transfer_pressure"] == round(10 / 24, 3)


def test_snapshot_pressure_zero_when_idle() -> None:
    state = _depot_with_settlement(
        depot_inventory={CargoType.FOOD: 0},
        settlement_demand={},
        transfer_limit=24,
    )
    simulation = TickSimulation(state=state)
    simulation.step_tick()

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    assert by_id["frontier_depot"]["transfer_used"] == 0
    assert by_id["frontier_depot"]["transfer_pressure"] == 0.0
    assert by_id["frontier_depot"]["saturation_streak"] == 0
