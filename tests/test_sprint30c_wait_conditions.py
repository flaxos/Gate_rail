"""Tests for Sprint 30C train wait conditions."""

import pytest
from gaterail.cargo import CargoType
from gaterail.models import (
    DevelopmentTier,
    FreightOrder,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    StopAction,
    TrainStop,
    TrainStatus,
    WaitCondition,
    WorldState,
)
from gaterail.simulation import TickSimulation

def test_wait_until_full():
    """Verify that a train waits until its cargo capacity is reached."""
    
    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    state.add_node(NetworkNode(id="a", world_id="w1", name="Node A", kind=NodeKind.DEPOT, transfer_limit_per_tick=10))
    state.add_node(NetworkNode(id="b", world_id="w1", name="Node B", kind=NodeKind.DEPOT))
    state.add_link(NetworkLink(id="l1", origin="a", destination="b", mode=LinkMode.RAIL, travel_ticks=2, capacity_per_tick=4))
    
    # 50 units available at A. Train capacity is 30. Loader limit is 10.
    state.nodes["a"].add_inventory(CargoType.ORE, 50)
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="a", capacity=30))
    
    stops = (
        TrainStop(node_id="a", action=StopAction.PICKUP, cargo_type=CargoType.ORE, wait_condition=WaitCondition.FULL),
        TrainStop(node_id="b", action=StopAction.DELIVERY),
    )
    
    state.add_order(FreightOrder(
        id="o1",
        train_id="t1",
        origin="a",
        destination="b",
        cargo_type=CargoType.ORE,
        requested_units=30,
        train_stops=stops
    ))
    
    sim = TickSimulation(state=state)
    
    # Tick 1: Load 10. (Wait condition FULL: 10 < 30, so stay)
    sim.step_tick()
    train = state.trains["t1"]
    assert train.cargo_units == 10
    assert train.status == TrainStatus.IDLE
    assert train.node_id == "a"
    
    # Tick 2: Load 10 (total 20). Stay.
    sim.step_tick()
    assert train.cargo_units == 20
    assert train.status == TrainStatus.IDLE
    
    # Tick 3: Load 10 (total 30). condition met! Dispatch to B.
    sim.step_tick()
    assert train.cargo_units == 30
    assert train.status == TrainStatus.IN_TRANSIT
    assert train.destination == "b"

def test_wait_until_empty():
    """Verify that a train waits until its cargo is fully unloaded."""
    
    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    state.add_node(NetworkNode(id="a", world_id="w1", name="Node A", kind=NodeKind.DEPOT))
    state.add_node(NetworkNode(id="b", world_id="w1", name="Node B", kind=NodeKind.DEPOT, transfer_limit_per_tick=10))
    state.add_link(NetworkLink(id="l1", origin="a", destination="b", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    
    # Train starts with 30 units. Destination B unloader limit is 10.
    train = FreightTrain(id="t1", name="Train 1", node_id="a", capacity=50, cargo_type=CargoType.ORE, cargo_units=30)
    state.add_train(train)
    
    stops = (
        TrainStop(node_id="b", action=StopAction.DELIVERY, cargo_type=CargoType.ORE, wait_condition=WaitCondition.EMPTY),
    )
    
    state.add_order(FreightOrder(
        id="o1",
        train_id="t1",
        origin="a",
        destination="b",
        cargo_type=CargoType.ORE,
        requested_units=30,
        train_stops=stops
    ))
    
    sim = TickSimulation(state=state)
    
    # Tick 1: Dispatch to B
    sim.step_tick()
    assert train.status == TrainStatus.IN_TRANSIT
    
    # Tick 2: Arrive at B. Unload 10. (Wait condition EMPTY: 20 > 0, so stay)
    sim.step_tick()
    assert train.node_id == "b"
    assert train.cargo_units == 20
    assert train.status == TrainStatus.BLOCKED
    
    # Tick 3: Unload 10. (Wait condition EMPTY: 10 > 0, so stay)
    sim.step_tick()
    assert train.cargo_units == 10
    assert train.status == TrainStatus.BLOCKED
    
    # Tick 4: Unload 10. (Wait condition EMPTY: 0 == 0, condition met!)
    sim.step_tick()
    assert train.cargo_units == 0
    assert not state.orders["o1"].active

def test_wait_for_time():
    """Verify that a train waits at a stop for a fixed number of ticks."""
    
    state = GameState()
    state.add_world(WorldState(id="w1", name="World 1", tier=DevelopmentTier.OUTPOST))
    state.add_node(NetworkNode(id="a", world_id="w1", name="Node A", kind=NodeKind.DEPOT))
    state.add_node(NetworkNode(id="b", world_id="w1", name="Node B", kind=NodeKind.DEPOT))
    state.add_link(NetworkLink(id="l1", origin="a", destination="b", mode=LinkMode.RAIL, travel_ticks=1, capacity_per_tick=4))
    
    state.add_train(FreightTrain(id="t1", name="Train 1", node_id="a", capacity=100))
    
    # Stop at B for 3 ticks
    stops = (
        TrainStop(node_id="b", action=StopAction.PASSTHROUGH, wait_condition=WaitCondition.TIME, wait_ticks=3),
    )
    
    state.add_order(FreightOrder(
        id="o1",
        train_id="t1",
        origin="a",
        destination="b",
        cargo_type=CargoType.ORE,
        requested_units=1, # must be positive
        train_stops=stops
    ))
    
    sim = TickSimulation(state=state)
    
    # Tick 1: Dispatch to B
    sim.step_tick()
    assert state.trains["t1"].status == TrainStatus.IN_TRANSIT
    
    # Tick 2: Arrive at B. Set arrival_tick. (elapsed 0 < 3, stay)
    sim.step_tick()
    train = state.trains["t1"]
    assert train.node_id == "b"
    assert train.arrival_tick == 2
    assert train.status == TrainStatus.IDLE
    
    # Tick 3: elapsed 1 < 3. Stay.
    sim.step_tick()
    assert train.status == TrainStatus.IDLE
    
    # Tick 4: elapsed 2 < 3. Stay.
    sim.step_tick()
    assert train.status == TrainStatus.IDLE
    
    # Tick 5: elapsed 3 >= 3. Condition met!
    sim.step_tick()
    assert not state.orders["o1"].active
