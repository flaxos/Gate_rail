"""Sprint 28A: closed mining-to-manufacturing gameplay loop end-to-end."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.commands import command_from_dict
from gaterail.models import ConstructionStatus, NodeKind
from gaterail.scenarios import (
    build_mining_to_manufacturing_scenario,
    load_scenario,
    scenario_definitions,
)
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


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
    assert site.discovered is False

    schedule = state.schedules["ore_haul_to_core"]
    assert schedule.cargo_type == CargoType.ORE
    assert schedule.active is False
    assert schedule.origin == "frontier_collection"
    assert schedule.destination == "core_smelter"

    assert "frontier_extraction_yard" not in state.nodes
    assert state.nodes["frontier_depot"].stock(CargoType.CONSTRUCTION_MATERIALS) >= 250
    assert state.trains["constructor"].node_id == "frontier_depot"

    smelter = state.nodes["core_smelter"]
    assert smelter.recipe is not None
    assert smelter.recipe.inputs == {CargoType.ORE: 20}
    assert smelter.recipe.outputs == {CargoType.METAL: 20}

    yard = state.nodes["core_yard"]
    assert yard.pull_logic is False
    assert yard.recipe is not None
    assert yard.recipe.inputs == {CargoType.METAL: 10}
    assert yard.recipe.outputs[CargoType.PARTS] == 10

    metal_schedule = state.schedules["metal_to_assembly_yard"]
    assert metal_schedule.cargo_type == CargoType.METAL
    assert metal_schedule.active is False
    assert metal_schedule.origin == "core_smelter"
    assert metal_schedule.destination == "core_yard"

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
    assert state.contracts["frontier_colony_stabilization"].target_world_id == "frontier"

    assert state.nodes["frontier_depot"].stock(CargoType.FUEL) >= 30
    assert state.links["gate_frontier_core"].power_required == 80
    assert state.worlds["frontier"].base_power_margin >= 80


def _run_until(simulation: TickSimulation, predicate, *, max_ticks: int = 120) -> dict[str, object]:
    last_report: dict[str, object] = {}
    for _ in range(max_ticks):
        last_report = simulation.step_tick()
        if predicate():
            return last_report
    raise AssertionError("condition was not reached before tick limit")


def _survey_and_build_extraction_yard(state) -> None:
    survey_preview = state.apply_command(
        command_from_dict({"type": "PreviewSurveySpaceSite", "site_id": "site_brink_belt"})
    )
    assert survey_preview["ok"] is True
    assert survey_preview["normalized_command"] == {
        "type": "SurveySpaceSite",
        "site_id": "site_brink_belt",
    }
    survey = state.apply_command(command_from_dict(survey_preview["normalized_command"]))
    assert survey["ok"] is True
    assert state.space_sites["site_brink_belt"].discovered is True

    build = state.apply_command(
        command_from_dict(
            {
                "type": "BuildNode",
                "node_id": "frontier_extraction_yard",
                "world_id": "frontier",
                "kind": "orbital_yard",
                "name": "Brink Extraction Yard",
                "layout": {"x": -210.0, "y": -80.0},
            }
        )
    )
    assert build["ok"] is True
    assert build["cargo_required"] == {
        "construction_materials": 200,
        "electronics": 50,
        "parts": 50,
    }
    link = state.apply_command(
        command_from_dict(
            {
                "type": "BuildLink",
                "link_id": "rail_frontier_depot_extraction_yard",
                "origin": "frontier_depot",
                "destination": "frontier_extraction_yard",
                "mode": "rail",
                "travel_ticks": 2,
                "capacity_per_tick": 12,
            }
        )
    )
    assert link["ok"] is True


def _deliver_extraction_yard_construction(simulation: TickSimulation) -> None:
    state = simulation.state
    result = state.apply_command(
        command_from_dict(
            {
                "type": "DispatchOrder",
                "order_id": "build_frontier_extraction_yard",
                "train_id": "constructor",
                "origin": "frontier_depot",
                "destination": "frontier_extraction_yard",
                "cargo_type": "construction_materials",
                "requested_units": 330,
                "train_stops": [
                    {
                        "node_id": "frontier_depot",
                        "action": "pickup",
                        "cargo_type": "construction_materials",
                        "units": 200,
                    },
                    {
                        "node_id": "frontier_extraction_yard",
                        "action": "delivery",
                        "wait_condition": "empty",
                    },
                    {
                        "node_id": "frontier_depot",
                        "action": "pickup",
                        "cargo_type": "electronics",
                        "units": 50,
                    },
                    {
                        "node_id": "frontier_extraction_yard",
                        "action": "delivery",
                        "wait_condition": "empty",
                    },
                    {
                        "node_id": "frontier_depot",
                        "action": "pickup",
                        "cargo_type": "parts",
                        "units": 50,
                    },
                    {
                        "node_id": "frontier_extraction_yard",
                        "action": "delivery",
                        "wait_condition": "empty",
                    },
                    {
                        "node_id": "frontier_depot",
                        "action": "pickup",
                        "cargo_type": "fuel",
                        "units": 30,
                    },
                    {
                        "node_id": "frontier_extraction_yard",
                        "action": "delivery",
                        "wait_condition": "empty",
                    },
                ],
            }
        )
    )
    assert result["ok"] is True
    _run_until(
        simulation,
        lambda: (
            state.nodes["frontier_extraction_yard"].construction_project_id is None
            and state.nodes["frontier_extraction_yard"].stock(CargoType.FUEL) >= 24
        ),
        max_ticks=80,
    )


def test_vertical_loop_survey_and_construction_gate_block_mining() -> None:
    state = build_mining_to_manufacturing_scenario()

    blocked = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "mission_blocked",
                "site_id": "site_brink_belt",
                "launch_node_id": "frontier_extraction_yard",
                "return_node_id": "frontier_collection",
            }
        )
    )
    assert blocked["ok"] is False
    assert blocked["reason"] == "site_not_surveyed"
    assert "site_not_surveyed" in {
        item["code"] for item in render_snapshot(state)["vertical_loop"]["diagnostics"]
    }

    _survey_and_build_extraction_yard(state)

    construction_blocked = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "mission_blocked",
                "site_id": "site_brink_belt",
                "launch_node_id": "frontier_extraction_yard",
                "return_node_id": "frontier_collection",
            }
        )
    )
    assert construction_blocked["ok"] is False
    assert construction_blocked["reason"] == "extraction_under_construction"
    project = state.construction_projects["proj_frontier_extraction_yard"]
    assert project.status == ConstructionStatus.PENDING


def test_vertical_loop_construction_delivery_completes_extraction_yard() -> None:
    state = build_mining_to_manufacturing_scenario()
    simulation = TickSimulation(state=state)

    _survey_and_build_extraction_yard(state)
    _deliver_extraction_yard_construction(simulation)

    yard = state.nodes["frontier_extraction_yard"]
    assert yard.kind == NodeKind.ORBITAL_YARD
    assert yard.construction_project_id is None
    assert state.construction_projects["proj_frontier_extraction_yard"].status == ConstructionStatus.COMPLETED
    assert render_snapshot(state)["vertical_loop"]["steps"][1]["status"] == "complete"


def test_mining_mission_haul_feeds_settlement_reward_loop_end_to_end() -> None:
    state = build_mining_to_manufacturing_scenario()
    simulation = TickSimulation(state=state)
    starting_cash = state.finance.cash
    starting_reputation = state.reputation

    _survey_and_build_extraction_yard(state)
    _deliver_extraction_yard_construction(simulation)

    dispatch = state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_loop",
                "site_id": "site_brink_belt",
                "launch_node_id": "frontier_extraction_yard",
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
    delivered_metal = False
    built_parts = False
    activated_metal_delivery = False
    activated_parts_delivery = False
    fulfilled_report: dict[str, object] | None = None

    for _ in range(90):
        report = simulation.step_tick()
        recipes = report["recipes"]
        smelted_metal = smelted_metal or recipes["produced"].get("core_smelter", {}).get("metal", 0) > 0
        built_parts = built_parts or recipes["produced"].get("core_yard", {}).get("parts", 0) > 0

        if not activated_metal_delivery and state.nodes["core_smelter"].stock(CargoType.METAL) >= 10:
            metal_activate = state.apply_command(
                command_from_dict(
                    {
                        "type": "SetScheduleEnabled",
                        "schedule_id": "metal_to_assembly_yard",
                        "enabled": True,
                    }
                )
            )
            assert metal_activate["ok"] is True
            activated_metal_delivery = True

        delivered_metal = (
            delivered_metal
            or state.schedules["metal_to_assembly_yard"].delivered_units >= 10
        )

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
    assert activated_metal_delivery, "METAL never became available for the assembly delivery"
    assert delivered_metal, "processed METAL was not moved by train to the assembly yard"
    assert built_parts, "smelted metal never became PARTS"
    assert activated_parts_delivery, "PARTS never became available for the settlement delivery"
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

    _run_until(
        simulation,
        lambda: state.contracts["frontier_colony_stabilization"].status.value == "fulfilled",
        max_ticks=12,
    )
    loop_payload = render_snapshot(state)["vertical_loop"]
    assert loop_payload["active"] is False
    assert loop_payload["unlocked_problem"]["id"] == "frontier_machinery_supply"
    assert [step["status"] for step in loop_payload["steps"]][-2:] == ["complete", "active"]


def test_vertical_loop_snapshot_exposes_stable_blocker_diagnostics() -> None:
    state = build_mining_to_manufacturing_scenario()
    simulation = TickSimulation(state=state)

    simulation.step_tick()
    initial_codes = {
        item["code"] for item in render_snapshot(state)["vertical_loop"]["diagnostics"]
    }
    assert {
        "site_not_surveyed",
        "no_source_cargo",
        "colony_shortage",
        "recipe_input_missing",
    }.issubset(initial_codes)

    state.schedules["ore_haul_to_core"].active = True
    state.trains.pop("prospector")
    state.nodes["frontier_depot"].add_inventory(
        CargoType.STONE,
        state.nodes["frontier_depot"].effective_storage_capacity(),
    )
    state.nodes["frontier_warehouse"].add_inventory(
        CargoType.STONE,
        state.nodes["frontier_warehouse"].effective_storage_capacity(),
    )
    state.worlds["frontier"].power_available = 60

    blocked_codes = {
        item["code"] for item in render_snapshot(state)["vertical_loop"]["diagnostics"]
    }
    assert {
        "missing_train",
        "depot_full",
        "warehouse_full",
        "missing_power",
    }.issubset(blocked_codes)
