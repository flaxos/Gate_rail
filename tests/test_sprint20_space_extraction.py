"""Tests for Sprint 20: Space Extraction and Collection Stations."""

from gaterail.commands import DispatchMiningMission, apply_player_command
from gaterail.models import (
    GameState,
    MiningMissionStatus,
    NetworkNode,
    NodeKind,
    SpaceSite,
    WorldState,
    DevelopmentTier,
)
from gaterail.persistence import simulation_from_dict, simulation_to_dict
from gaterail.simulation import TickSimulation


def test_mining_mission_lifecycle():
    """Test dispatch, transit, completion, and resource delivery of a mining mission."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="W1", tier=DevelopmentTier.CORE_WORLD))
    
    # Setup node
    node = NetworkNode(
        id="node_station_1",
        world_id="w1",
        name="Orbital Station",
        kind=NodeKind.SETTLEMENT,
        storage_capacity=1000,
    )
    state.add_node(node)
    
    # Setup SpaceSite
    site = SpaceSite(
        id="site_alpha",
        name="Alpha Asteroid",
        resource_id="mixed_ore",
        travel_ticks=5,
        base_yield=250,
    )
    state.add_space_site(site)
    
    # Dispatch via command
    command = DispatchMiningMission(
        mission_id="mission_1",
        site_id="site_alpha",
        launch_node_id="node_station_1",
        return_node_id="node_station_1",
    )
    
    result = apply_player_command(state, command)
    assert result["ok"], result.get("message")
    
    mission = state.mining_missions["mission_1"]
    assert mission.status == MiningMissionStatus.EN_ROUTE
    assert mission.ticks_remaining == 10  # travel_ticks * 2
    assert mission.expected_yield == 250
    
    sim = TickSimulation(state=state)
    
    # Advance ticks, but not enough to finish
    sim.run_ticks(5)
    
    mission = sim.state.mining_missions["mission_1"]
    assert mission.ticks_remaining == 5
    assert mission.status == MiningMissionStatus.EN_ROUTE
    assert "mixed_ore" not in sim.state.nodes["node_station_1"].resource_inventory
    
    # Advance the rest
    sim.run_ticks(5)
    
    mission = sim.state.mining_missions["mission_1"]
    assert mission.ticks_remaining == 0
    assert mission.status == MiningMissionStatus.COMPLETED
    
    # Verify resources arrived
    node = sim.state.nodes["node_station_1"]
    assert node.resource_inventory.get("mixed_ore", 0) == 250

def test_mining_mission_persistence():
    """Test save/load cycle maintains space sites and mining missions."""

    state = GameState()
    state.add_world(WorldState(id="w1", name="W1", tier=DevelopmentTier.CORE_WORLD))
    
    site = SpaceSite(
        id="site_beta",
        name="Beta Debris",
        resource_id="iron_rich_ore",
        travel_ticks=3,
        base_yield=100,
    )
    state.add_space_site(site)
    
    command = DispatchMiningMission(
        mission_id="mission_2",
        site_id="site_beta",
        launch_node_id="node_0",
        return_node_id="node_0",
    )
    
    # Fake a node for validation
    state.add_node(NetworkNode(id="node_0", world_id="w1", name="N", kind=NodeKind.SETTLEMENT))
    apply_player_command(state, command)
    
    sim = TickSimulation(state=state)
    sim.run_ticks(1)
    
    mission = sim.state.mining_missions["mission_2"]
    assert mission.ticks_remaining == 5
    
    save_data = simulation_to_dict(sim)
    loaded_sim = simulation_from_dict(save_data)
    
    loaded_state = loaded_sim.state
    assert "site_beta" in loaded_state.space_sites
    assert loaded_state.space_sites["site_beta"].resource_id == "iron_rich_ore"
    
    assert "mission_2" in loaded_state.mining_missions
    loaded_mission = loaded_state.mining_missions["mission_2"]
    assert loaded_mission.ticks_remaining == 5
    assert loaded_mission.status == MiningMissionStatus.EN_ROUTE
    assert loaded_mission.expected_yield == 100
