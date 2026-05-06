"""Tests for Sprint 30B multi-stop train orders and skip-on-empty logic."""

import pytest
from gaterail.cargo import CargoType
from gaterail.commands import DispatchOrder, PreviewCreateSchedule, UpdateSchedule, command_from_dict
from gaterail.persistence import load_simulation, save_simulation
from gaterail.models import (
    DevelopmentTier,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    StopAction,
    TrainStop,
    TrainStatus,
    WorldState,
)
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot

def test_multistop_order_dispatch():
    """Verify that a train can process multiple stops in a single order."""
    
    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    
    # A -> B -> C
    state.add_node(NetworkNode(id="a", world_id="w1", name="Node A", kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_node(NetworkNode(id="b", world_id="w1", name="Node B", kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_node(NetworkNode(id="c", world_id="w1", name="Node C", kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    
    # Connect them
    state.add_link(NetworkLink(id="l1", origin="a", destination="b", mode=LinkMode.RAIL, travel_ticks=2, capacity_per_tick=4))
    state.add_link(NetworkLink(id="l2", origin="b", destination="c", mode=LinkMode.RAIL, travel_ticks=2, capacity_per_tick=4))
    
    # Add cargo at A
    state.nodes["a"].add_inventory(CargoType.ORE, 50)
    
    # Purchase train at A
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="a", capacity=100))
    
    # Define multi-stop order
    stops = (
        TrainStop(node_id="a", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=50),
        TrainStop(node_id="b", action=StopAction.PASSTHROUGH),
        TrainStop(node_id="c", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=50),
    )
    
    state.add_order(FreightOrder(
        id="o1",
        train_id="t1",
        origin="a",
        destination="c",
        cargo_type=CargoType.ORE,
        requested_units=50,
        train_stops=stops
    ))
    
    sim = TickSimulation(state=state)
    
    # Tick 1: Dispatch from A to A (Immediate pickup)
    sim.step_tick()
    train = state.trains["t1"]
    
    # EXPECTED BEHAVIOR: Train picks up at A, then dispatches to B
    assert train.cargo_units == 50
    assert train.destination == "b"
    assert train.current_stop_index == 1
    
    # Wait for arrival at B
    sim.run_ticks(train.remaining_ticks)
    assert train.node_id == "b"
    
    # Tick: Process B (passthrough) and dispatch to C
    sim.step_tick()
    assert train.destination == "c"
    assert train.current_stop_index == 2
    
    # Wait for arrival at C
    sim.run_ticks(train.remaining_ticks)
    assert train.node_id == "c"
    
    # Tick: Process C (delivery)
    sim.step_tick()
    assert state.nodes["c"].stock(CargoType.ORE) == 50
    assert train.cargo_units == 0
    assert not state.orders["o1"].active

def test_skip_empty_origin():
    """Verify that a pickup stop is skipped if the node is empty."""
    
    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    state.add_node(NetworkNode(id="a", world_id="w1", name="Node A", kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_node(NetworkNode(id="b", world_id="w1", name="Node B", kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_link(NetworkLink(id="l1", origin="a", destination="b", mode=LinkMode.RAIL, travel_ticks=2, capacity_per_tick=4))
    
    # No cargo at A
    
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="a", capacity=100))
    
    stops = (
        TrainStop(node_id="a", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=50),
        TrainStop(node_id="b", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=50),
    )
    
    state.add_order(FreightOrder(
        id="o1",
        train_id="t1",
        origin="a",
        destination="b",
        cargo_type=CargoType.ORE,
        requested_units=50,
        train_stops=stops
    ))
    
    sim = TickSimulation(state=state)
    
    # Tick 1: Try to pickup at A. Empty, so skip to B.
    sim.step_tick()
    train = state.trains["t1"]
    
    assert train.cargo_units == 0
    assert train.destination == "b"
    assert train.current_stop_index == 1


def test_transfer_to_warehouse_does_not_count_as_final_delivery():
    """A transfer stop should stage cargo without satisfying the order."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    state.add_node(NetworkNode(id="mine", world_id="w1", name="Mine", kind=NodeKind.EXTRACTOR, transfer_limit_per_tick=100))
    state.add_node(NetworkNode(id="warehouse", world_id="w1", name="Warehouse", kind=NodeKind.WAREHOUSE, transfer_limit_per_tick=100))
    state.add_node(NetworkNode(id="factory", world_id="w1", name="Factory", kind=NodeKind.INDUSTRY, transfer_limit_per_tick=100))
    state.add_link(NetworkLink(id="mine_to_warehouse", origin="mine", destination="warehouse", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_link(NetworkLink(id="warehouse_to_factory", origin="warehouse", destination="factory", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.nodes["mine"].add_inventory(CargoType.ORE, 40)
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="mine", capacity=40))

    stops = (
        TrainStop(node_id="mine", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="warehouse", action=StopAction.TRANSFER, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="warehouse", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="factory", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=40),
    )
    state.add_order(FreightOrder(
        id="ore_via_warehouse",
        train_id="t1",
        origin="mine",
        destination="factory",
        cargo_type=CargoType.ORE,
        requested_units=40,
        train_stops=stops,
    ))

    sim = TickSimulation(state=state)

    sim.step_tick()
    assert state.trains["t1"].destination == "warehouse"

    sim.step_tick()
    assert state.trains["t1"].destination == "factory"
    assert state.orders["ore_via_warehouse"].delivered_units == 0
    assert state.orders["ore_via_warehouse"].active is True

    sim.step_tick()
    assert state.nodes["factory"].stock(CargoType.ORE) == 40
    assert state.orders["ore_via_warehouse"].delivered_units == 40
    assert state.orders["ore_via_warehouse"].active is False


def test_dispatch_order_json_round_trips_train_stops_to_snapshot():
    """One-shot order commands must carry ordered stops through the backend."""

    command = command_from_dict(
        {
            "type": "DispatchOrder",
            "order_id": "manual_ore_route",
            "train_id": "t1",
            "origin": "mine",
            "destination": "factory",
            "cargo_type": "ore",
            "requested_units": 40,
            "train_stops": [
                {
                    "node_id": "mine",
                    "action": "pickup",
                    "cargo_type": "ore",
                    "units": 40,
                },
                {
                    "node_id": "warehouse",
                    "action": "transfer",
                    "cargo_type": "ore",
                    "units": 40,
                },
                {
                    "node_id": "factory",
                    "action": "delivery",
                    "cargo_type": "ore",
                    "units": 40,
                    "wait_condition": "empty",
                },
            ],
        }
    )

    assert isinstance(command, DispatchOrder)
    assert command.train_stops[1].action == StopAction.TRANSFER
    assert command.train_stops[2].wait_condition.value == "empty"

    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    for node_id in ("mine", "warehouse", "factory"):
        state.add_node(NetworkNode(id=node_id, world_id="w1", name=node_id, kind=NodeKind.DEPOT))
    state.add_link(NetworkLink(id="mine_to_warehouse", origin="mine", destination="warehouse", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_link(NetworkLink(id="warehouse_to_factory", origin="warehouse", destination="factory", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="mine", capacity=40))

    result = state.apply_command(command)
    snapshot = render_snapshot(state)
    order_payload = next(order for order in snapshot["orders"] if order["id"] == "manual_ore_route")

    assert result["ok"] is True
    assert order_payload["train_stops"] == [
        {
            "node_id": "mine",
            "action": "pickup",
            "cargo_type": "ore",
            "units": 40,
            "wait_condition": "none",
            "wait_ticks": 0,
        },
        {
            "node_id": "warehouse",
            "action": "transfer",
            "cargo_type": "ore",
            "units": 40,
            "wait_condition": "none",
            "wait_ticks": 0,
        },
        {
            "node_id": "factory",
            "action": "delivery",
            "cargo_type": "ore",
            "units": 40,
            "wait_condition": "empty",
            "wait_ticks": 0,
        },
    ]


def test_update_schedule_persists_ordered_train_stops_to_snapshot():
    """Schedule editing must persist backend train-stop lists."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    for node_id in ("mine", "warehouse", "factory"):
        state.add_node(NetworkNode(id=node_id, world_id="w1", name=node_id, kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_link(NetworkLink(id="mine_to_warehouse", origin="mine", destination="warehouse", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_link(NetworkLink(id="warehouse_to_factory", origin="warehouse", destination="factory", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="mine", capacity=40))
    state.add_schedule(
        FreightSchedule(
            id="ore_service",
            train_id="t1",
            origin="mine",
            destination="factory",
            cargo_type=CargoType.ORE,
            units_per_departure=40,
            interval_ticks=10,
            active=False,
        )
    )
    train_stops = (
        TrainStop(node_id="mine", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="warehouse", action=StopAction.TRANSFER, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="factory", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=40),
    )

    result = state.apply_command(
        UpdateSchedule(
            schedule_id="ore_service",
            train_stops=train_stops,
        )
    )
    schedule_payload = next(
        schedule for schedule in render_snapshot(state)["schedules"]
        if schedule["id"] == "ore_service"
    )

    assert result["ok"] is True
    assert state.schedules["ore_service"].train_stops == train_stops
    assert schedule_payload["route_stop_ids"] == ["mine", "warehouse", "factory"]
    assert [stop["action"] for stop in schedule_payload["train_stops"]] == [
        "pickup",
        "transfer",
        "delivery",
    ]


def test_schedule_preview_routes_through_ordered_train_stops():
    """Train stops are real route waypoints, not just UI metadata."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    for node_id in ("mine", "warehouse", "factory"):
        state.add_node(NetworkNode(id=node_id, world_id="w1", name=node_id, kind=NodeKind.DEPOT, transfer_limit_per_tick=100))
    state.add_link(NetworkLink(id="mine_to_warehouse", origin="mine", destination="warehouse", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_link(NetworkLink(id="warehouse_to_factory", origin="warehouse", destination="factory", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="mine", capacity=40))

    train_stops = (
        TrainStop(node_id="mine", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="warehouse", action=StopAction.TRANSFER, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="warehouse", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="factory", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=40),
    )

    result = state.apply_command(
        PreviewCreateSchedule(
            schedule_id="ore_via_warehouse",
            train_id="t1",
            origin="mine",
            destination="factory",
            cargo_type=CargoType.ORE,
            units_per_departure=40,
            interval_ticks=10,
            train_stops=train_stops,
        )
    )

    assert result["ok"] is True
    assert result["route_stop_ids"] == ["mine", "warehouse", "factory"]
    assert result["route_link_ids"] == ["mine_to_warehouse", "warehouse_to_factory"]
    assert result["normalized_command"]["train_stops"][1]["action"] == "transfer"


def test_train_stops_survive_save_load(tmp_path):
    """Ordered stops are part of save data for schedules and one-shot orders."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    for node_id in ("mine", "factory"):
        state.add_node(NetworkNode(id=node_id, world_id="w1", name=node_id, kind=NodeKind.DEPOT))
    state.add_link(NetworkLink(id="mine_to_factory", origin="mine", destination="factory", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="mine", capacity=40))
    stops = (
        TrainStop(node_id="mine", action=StopAction.PICKUP, cargo_type=CargoType.ORE, units=40),
        TrainStop(node_id="factory", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, units=40),
    )
    state.add_schedule(
        FreightSchedule(
            id="ore_schedule",
            train_id="t1",
            origin="mine",
            destination="factory",
            cargo_type=CargoType.ORE,
            units_per_departure=40,
            interval_ticks=10,
            train_stops=stops,
        )
    )
    state.add_order(
        FreightOrder(
            id="ore_order",
            train_id="t1",
            origin="mine",
            destination="factory",
            cargo_type=CargoType.ORE,
            requested_units=40,
            train_stops=stops,
        )
    )

    save_path = tmp_path / "train_stops.json"
    save_simulation(TickSimulation(state=state), save_path)
    loaded = load_simulation(save_path).state

    assert loaded.schedules["ore_schedule"].train_stops == stops
    assert loaded.orders["ore_order"].train_stops == stops
