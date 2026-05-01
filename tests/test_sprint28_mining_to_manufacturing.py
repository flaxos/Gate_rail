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

    smelter = state.nodes["core_smelter"]
    assert smelter.recipe is not None
    assert smelter.recipe.inputs == {CargoType.ORE: 20}
    assert smelter.recipe.outputs == {CargoType.METAL: 20}

    yard = state.nodes["core_yard"]
    assert yard.recipe is not None
    assert yard.recipe.inputs == {CargoType.METAL: 10}
    assert yard.recipe.outputs[CargoType.PARTS] == 10

    parts_schedule = state.schedules["parts_to_frontier_settlement"]
    assert parts_schedule.cargo_type == CargoType.PARTS
    assert parts_schedule.active is False
    assert parts_schedule.origin == "core_yard"
    assert parts_schedule.destination == "frontier_settlement"

    contract = state.contracts["frontier_parts_upgrade"]
    assert contract.destination_node_id == "frontier_settlement"
    assert contract.cargo_type == CargoType.PARTS
    assert contract.target_units == 10
    assert contract.reward_cash >= 5_000

    assert state.nodes["frontier_spaceport"].stock(CargoType.FUEL) >= 30
    assert state.links["gate_frontier_core"].power_required == 80
    assert state.worlds["frontier"].base_power_margin >= 80


def test_mining_mission_haul_feeds_settlement_reward_loop_end_to_end() -> None:
    state = build_mining_to_manufacturing_scenario()
    simulation = TickSimulation(state=state)
    starting_cash = state.finance.cash
    starting_reputation = state.reputation

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

    smelted_metal = False
    built_parts = False
    activated_parts_delivery = False
    fulfilled_report: dict[str, object] | None = None

    for _ in range(90):
        report = simulation.step_tick()
        recipes = report["recipes"]
        smelted_metal = smelted_metal or recipes["produced"].get("core_smelter", {}).get("metal", 0) > 0
        built_parts = built_parts or recipes["produced"].get("core_yard", {}).get("parts", 0) > 0

        if not activated_parts_delivery and state.nodes["core_yard"].stock(CargoType.PARTS) >= 10:
            parts_activate = state.apply_command(
                command_from_dict(
                    {
                        "type": "SetScheduleEnabled",
                        "schedule_id": "parts_to_frontier_settlement",
                        "enabled": True,
                    }
                )
            )
            assert parts_activate["ok"] is True
            activated_parts_delivery = True

        if state.contracts["frontier_parts_upgrade"].status.value == "fulfilled":
            fulfilled_report = report
            break

    core_yard = state.nodes["core_yard"]
    contract = state.contracts["frontier_parts_upgrade"]

    assert smelted_metal, "ore never entered the smelting leg"
    assert built_parts, "smelted metal never became PARTS"
    assert activated_parts_delivery, "PARTS never became available for the settlement delivery"
    assert core_yard.stock(CargoType.PARTS) > 0, "manufacturing recipe never produced PARTS"
    assert core_yard.stock(CargoType.CONSTRUCTION_MATERIALS) > 0
    assert fulfilled_report is not None, "settlement contract was not fulfilled"
    assert fulfilled_report["contracts"]["fulfilled_this_tick"][0]["contract"] == "frontier_parts_upgrade"
    assert contract.delivered_units >= 10
    assert state.nodes["frontier_settlement"].stock(CargoType.PARTS) >= 10
    assert state.finance.cash > starting_cash
    assert state.reputation == starting_reputation + contract.reward_reputation
    assert state.nodes["frontier_collection"].stock(CargoType.ORE) < 60, (
        "ore should have been picked up by the train, not stuck at the collection station"
    )
    assert state.mining_missions["mission_loop"].status.value == "completed"
