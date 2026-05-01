"""Sprint 28A: closed mining-to-manufacturing gameplay loop end-to-end."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import command_from_dict
from gaterail.scenarios import (
    build_mining_to_manufacturing_scenario,
    load_scenario,
    scenario_definitions,
)
from gaterail.simulation import TickSimulation


def test_mining_to_manufacturing_scenario_is_registered() -> None:
    keys = {definition.key for definition in scenario_definitions()}
    aliases = {alias for definition in scenario_definitions() for alias in definition.aliases}

    assert "mining_to_manufacturing" in keys
    assert "mining_loop" in aliases
    assert load_scenario("mining_loop").space_sites["site_brink_belt"].cargo_type == CargoType.ORE


def test_mining_to_manufacturing_scenario_seeds_the_full_loop() -> None:
    state = build_mining_to_manufacturing_scenario()

    assert state.economic_identity_enabled is True
    assert state.worlds["core"].specialization == "manufacturing"
    assert state.worlds["frontier"].specialization == "mining"

    site = state.space_sites["site_brink_belt"]
    assert site.cargo_type == CargoType.ORE
    assert site.base_yield == 60

    schedule = state.schedules["ore_haul_to_core"]
    assert schedule.cargo_type == CargoType.ORE
    assert schedule.active is False
    assert schedule.origin == "frontier_collection"
    assert schedule.destination == "core_yard"

    assert state.nodes["frontier_spaceport"].stock(CargoType.FUEL) >= 30
    assert state.links["gate_frontier_core"].power_required == 80
    assert state.worlds["frontier"].base_power_margin >= 80


def test_mining_mission_haul_feeds_manufacturing_recipe_end_to_end() -> None:
    state = build_mining_to_manufacturing_scenario()
    simulation = TickSimulation(state=state)

    dispatch = state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_loop",
                "site_id": "site_brink_belt",
                "launch_node_id": "frontier_spaceport",
                "return_node_id": "frontier_collection",
            }
        )
    )
    assert dispatch["ok"] is True

    activate = state.apply_command(
        command_from_dict(
            {
                "type": "SetScheduleEnabled",
                "schedule_id": "ore_haul_to_core",
                "enabled": True,
            }
        )
    )
    assert activate["ok"] is True

    for _ in range(40):
        simulation.step_tick()
        if state.nodes["core_yard"].stock(CargoType.PARTS) > 0:
            break

    core_yard = state.nodes["core_yard"]
    assert core_yard.stock(CargoType.PARTS) > 0, "manufacturing recipe never produced PARTS"
    assert core_yard.stock(CargoType.CONSTRUCTION_MATERIALS) > 0
    assert state.nodes["frontier_collection"].stock(CargoType.ORE) < 60, (
        "ore should have been picked up by the train, not stuck at the collection station"
    )
    assert state.mining_missions["mission_loop"].status.value == "completed"
