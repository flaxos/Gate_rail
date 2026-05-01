"""Tests for Phase 4 active warehouse stock targets and push/pull logic."""

from gaterail.cargo import CargoType
from gaterail.economy import apply_buffer_distribution
from gaterail.models import DevelopmentTier, GameState, LinkMode, NetworkLink, NetworkNode, NodeKind, WorldState


def test_warehouse_pulls_to_stock_target() -> None:
    """A warehouse with pull logic and a stock target pulls from a neighbour."""
    state = GameState(tick=1)
    state.add_world(WorldState(id="test", name="Test", tier=DevelopmentTier.FRONTIER_COLONY))
    
    producer = NetworkNode(
        id="producer",
        name="Producer",
        world_id="test",
        kind=NodeKind.INDUSTRY,
        inventory={CargoType.PARTS: 100},
        transfer_limit_per_tick=50,
    )
    
    warehouse = NetworkNode(
        id="wh",
        name="Warehouse",
        world_id="test",
        kind=NodeKind.WAREHOUSE,
        inventory={CargoType.PARTS: 10},
        stock_targets={CargoType.PARTS: 40},
        transfer_limit_per_tick=50,
        pull_logic=True,
        push_logic=False,
    )
    
    link = NetworkLink("l1", "producer", "wh", LinkMode.RAIL, travel_ticks=1, capacity_per_tick=10)
    
    state.add_node(producer)
    state.add_node(warehouse)
    state.add_link(link)
    
    apply_buffer_distribution(state)
    
    assert warehouse.stock(CargoType.PARTS) == 40
    assert producer.stock(CargoType.PARTS) == 70


def test_warehouse_priority_respects_higher_priority_targets() -> None:
    """A warehouse only pulls from another warehouse if its priority is higher."""
    state = GameState(tick=1)
    state.add_world(WorldState(id="test", name="Test", tier=DevelopmentTier.FRONTIER_COLONY))
    
    wh_high = NetworkNode(
        id="wh_high",
        name="High Priority",
        world_id="test",
        kind=NodeKind.WAREHOUSE,
        inventory={CargoType.PARTS: 50},
        stock_targets={CargoType.PARTS: 50},
        buffer_priority=10,
        transfer_limit_per_tick=50,
        pull_logic=True,
    )
    
    wh_low = NetworkNode(
        id="wh_low",
        name="Low Priority",
        world_id="test",
        kind=NodeKind.WAREHOUSE,
        inventory={CargoType.PARTS: 0},
        stock_targets={CargoType.PARTS: 40},
        buffer_priority=1,
        transfer_limit_per_tick=50,
        pull_logic=True,
    )
    
    link = NetworkLink("l1", "wh_high", "wh_low", LinkMode.RAIL, travel_ticks=1, capacity_per_tick=10)
    
    state.add_node(wh_high)
    state.add_node(wh_low)
    state.add_link(link)
    
    apply_buffer_distribution(state)
    
    # Low priority should NOT be able to pull from high priority's protected stock target
    assert wh_low.stock(CargoType.PARTS) == 0
    assert wh_high.stock(CargoType.PARTS) == 50
    
    # Now give High Priority surplus
    wh_high.add_inventory(CargoType.PARTS, 20)
    apply_buffer_distribution(state)
    
    # High priority pushes or low priority pulls the surplus
    assert wh_low.stock(CargoType.PARTS) == 20
    assert wh_high.stock(CargoType.PARTS) == 50


def test_warehouse_pushes_surplus_only() -> None:
    """A warehouse pushing to meet demand preserves its stock target."""
    state = GameState(tick=1)
    state.add_world(WorldState(id="test", name="Test", tier=DevelopmentTier.FRONTIER_COLONY))
    
    warehouse = NetworkNode(
        id="wh",
        name="Warehouse",
        world_id="test",
        kind=NodeKind.WAREHOUSE,
        inventory={CargoType.PARTS: 60},
        stock_targets={CargoType.PARTS: 50},
        transfer_limit_per_tick=50,
        push_logic=True,
    )
    
    consumer = NetworkNode(
        id="consumer",
        name="Consumer",
        world_id="test",
        kind=NodeKind.SETTLEMENT,
        demand={CargoType.PARTS: 100},
    )
    
    link = NetworkLink("l1", "wh", "consumer", LinkMode.RAIL, travel_ticks=1, capacity_per_tick=10)
    
    state.add_node(warehouse)
    state.add_node(consumer)
    state.add_link(link)
    
    apply_buffer_distribution(state)
    
    # Should only push the 10 surplus units
    assert consumer.stock(CargoType.PARTS) == 10
    assert warehouse.stock(CargoType.PARTS) == 50
