"""Sprint 31: tutorial vertical slice from local logistics to Railgate expansion."""

from __future__ import annotations

from pathlib import Path

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.commands import PreviewBuildLink, command_from_dict
from gaterail.models import ConstructionStatus, LinkMode
from gaterail.persistence import load_simulation, save_simulation
from gaterail.scenarios import load_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _run_until(simulation: TickSimulation, predicate, *, max_ticks: int = 220) -> None:
    for _ in range(max_ticks):
        simulation.run_ticks(1)
        if predicate():
            return
    raise AssertionError("condition was not reached before tick limit")


def _apply(state, payload: dict[str, object]) -> dict[str, object]:
    result = state.apply_command(command_from_dict(payload))
    assert result["ok"] is True, result
    return result


def _enable(state, schedule_id: str) -> None:
    _apply(
        state,
        {
            "type": "SetScheduleEnabled",
            "schedule_id": schedule_id,
            "enabled": True,
        },
    )


def _complete_gate_component_and_gate_build(simulation: TickSimulation) -> None:
    state = simulation.state
    for schedule_id in (
        "tutorial_ore_to_cinder",
        "tutorial_metal_to_atlas",
        "tutorial_parts_to_helix",
        "tutorial_parts_to_gateworks",
        "tutorial_electronics_to_gateworks",
        "tutorial_components_to_gate",
    ):
        _enable(state, schedule_id)

    _run_until(
        simulation,
        lambda: state.construction_projects["proj_atlas_outbound_gate"].status
        == ConstructionStatus.COMPLETED,
        max_ticks=180,
    )


def _complete_full_tutorial_slice(simulation: TickSimulation) -> None:
    state = simulation.state
    _complete_gate_component_and_gate_build(simulation)
    _apply(state, {"type": "SurveySpaceSite", "site_id": "site_sable_reach"})
    _apply(
        state,
        {
            "type": "BuildLink",
            "link_id": "gate_atlas_sable",
            "origin": "atlas_outbound_gate",
            "destination": "sable_gate_anchor",
            "mode": "gate",
            "travel_ticks": 1,
            "capacity_per_tick": 4,
            "power_required": 80,
            "power_source_world_id": "atlas",
        },
    )
    _enable(state, "tutorial_starter_to_sable")
    _run_until(
        simulation,
        lambda: (
            state.contracts["helix_parts_tutorial"].status.value == "fulfilled"
            and state.contracts["sable_starter_cargo"].status.value == "fulfilled"
        ),
        max_ticks=160,
    )


def test_tutorial_scenario_seeds_connected_gate_deployment_slice() -> None:
    state = load_scenario("tutorial_six_worlds")

    assert "sable" in state.worlds
    assert "site_sable_reach" in state.space_sites
    assert state.space_sites["site_sable_reach"].discovered is False
    assert "gate_atlas_sable" not in state.links

    gate_node = state.nodes["atlas_outbound_gate"]
    project = state.construction_projects[gate_node.construction_project_id]
    assert gate_node.kind.value == "gate_hub"
    assert project.required_cargo == {CargoType.GATE_COMPONENTS: 4}
    assert project.status == ConstructionStatus.PENDING

    gateworks = state.nodes["atlas_gate_component_line"]
    assert gateworks.recipe is not None
    assert gateworks.recipe.inputs == {
        CargoType.PARTS: 8,
        CargoType.ELECTRONICS: 4,
    }
    assert gateworks.recipe.outputs == {CargoType.GATE_COMPONENTS: 4}

    starter_schedule = state.schedules["tutorial_starter_to_sable"]
    assert starter_schedule.active is False
    assert starter_schedule.origin == "atlas_depot"
    assert starter_schedule.destination == "sable_settlement"
    assert starter_schedule.cargo_type == CargoType.CONSTRUCTION_MATERIALS
    assert state.contracts["sable_starter_cargo"].destination_node_id == "sable_settlement"


def test_gate_link_preview_blocks_until_outbound_gate_project_is_complete() -> None:
    state = load_scenario("tutorial_six_worlds")

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_atlas_sable",
            origin="atlas_outbound_gate",
            destination="sable_gate_anchor",
            mode=LinkMode.GATE,
            capacity_per_tick=4,
            power_required=80,
            power_source_world_id="atlas",
        )
    )

    assert result["ok"] is False
    assert result["reason"] == "gate_endpoint_under_construction"
    assert result["construction_project_id"] == "proj_atlas_outbound_gate"

    state.construction_projects["proj_atlas_outbound_gate"].status = ConstructionStatus.COMPLETED
    state.nodes["atlas_outbound_gate"].construction_project_id = None
    unsurveyed = state.apply_command(
        PreviewBuildLink(
            link_id="gate_atlas_sable",
            origin="atlas_outbound_gate",
            destination="sable_gate_anchor",
            mode=LinkMode.GATE,
            capacity_per_tick=4,
            power_required=80,
            power_source_world_id="atlas",
        )
    )

    assert unsurveyed["ok"] is False
    assert unsurveyed["reason"] == "destination_not_surveyed"
    assert unsurveyed["site_id"] == "site_sable_reach"

    state.space_sites["site_sable_reach"].discovered = True
    ready = state.apply_command(
        PreviewBuildLink(
            link_id="gate_atlas_sable",
            origin="atlas_outbound_gate",
            destination="sable_gate_anchor",
            mode=LinkMode.GATE,
            capacity_per_tick=4,
            power_required=80,
            power_source_world_id="atlas",
        )
    )
    assert ready["ok"] is True


def test_tutorial_snapshot_exposes_backend_owned_actions_and_blockers() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    tutorial = render_snapshot(simulation.state)["tutorial"]

    assert tutorial["next_action"] == {
        "kind": "command",
        "label": "Activate ore haul",
        "command": {
            "type": "SetScheduleEnabled",
            "schedule_id": "tutorial_ore_to_cinder",
            "enabled": True,
        },
    }
    assert [step["id"] for step in tutorial["steps"]] == [
        "mine_ore",
        "smelt_metal",
        "deliver_parts",
        "manufacture_gate_components",
        "deploy_outbound_gate",
        "survey_destination",
        "establish_gate_corridor",
        "send_starter_freight",
    ]
    blocker_codes = {item["code"] for item in tutorial["blockers"]}
    assert {
        "destination_not_surveyed",
        "gate_not_built",
        "gate_connection_incomplete",
    }.issubset(blocker_codes)


def test_connected_tutorial_loop_reaches_second_world_and_completes() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    state = simulation.state

    _complete_full_tutorial_slice(simulation)

    assert state.links["gate_atlas_sable"].mode == LinkMode.GATE
    assert state.space_sites["site_sable_reach"].discovered is True
    assert state.construction_projects["proj_atlas_outbound_gate"].status == ConstructionStatus.COMPLETED
    assert state.nodes["sable_settlement"].stock(CargoType.CONSTRUCTION_MATERIALS) >= 40
    assert state.schedules["tutorial_components_to_gate"].delivered_units >= 4
    assert state.schedules["tutorial_starter_to_sable"].delivered_units >= 40

    tutorial = render_snapshot(state)["tutorial"]
    assert tutorial["active"] is False
    assert tutorial["next_action"] is None
    assert all(step["status"] == "complete" for step in tutorial["steps"])


def test_bridge_can_drive_tutorial_next_action_command() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    snapshot = handle_bridge_message(
        simulation,
        {"scenario": "tutorial_six_worlds", "ticks": 0},
    )

    action = snapshot["tutorial"]["next_action"]
    assert action["kind"] == "command"
    updated = handle_bridge_message(
        simulation,
        {"commands": [action["command"]], "ticks": 0},
    )

    assert updated["bridge"]["command_results"][0]["target_id"] == "tutorial_ore_to_cinder"
    schedules = {item["id"]: item for item in updated["schedules"]}
    assert schedules["tutorial_ore_to_cinder"]["active"] is True


def test_bridge_next_actions_can_complete_the_tutorial_slice() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    snapshot = render_snapshot(simulation.state)

    for _ in range(140):
        tutorial = snapshot["tutorial"]
        if not tutorial["active"]:
            break
        action = tutorial["next_action"]
        if action["kind"] == "step_ticks":
            message = {"ticks": int(action.get("ticks", 1))}
        elif action["kind"] == "command":
            message = {"commands": [action["command"]], "ticks": int(action.get("ticks", 0))}
        elif action["kind"] == "commands":
            message = {"commands": action["commands"], "ticks": int(action.get("ticks", 0))}
        else:
            raise AssertionError(f"unsupported tutorial action: {action}")
        snapshot = handle_bridge_message(simulation, message)

    assert snapshot["tutorial"]["active"] is False
    assert simulation.state.contracts["sable_starter_cargo"].status.value == "fulfilled"


def test_tutorial_save_load_preserves_gate_expansion_state(tmp_path) -> None:
    save_path = tmp_path / "tutorial_vertical_slice.json"
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")

    _complete_full_tutorial_slice(simulation)
    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)

    assert loaded.state.space_sites["site_sable_reach"].discovered is True
    assert "gate_atlas_sable" in loaded.state.links
    assert loaded.state.construction_projects["proj_atlas_outbound_gate"].status == ConstructionStatus.COMPLETED
    assert loaded.state.contracts["sable_starter_cargo"].status.value == "fulfilled"
    assert render_snapshot(loaded.state)["tutorial"]["active"] is False


def test_godot_tutorial_controls_execute_backend_commands_without_local_rules() -> None:
    main_script = Path("godot/scripts/main.gd").read_text(encoding="utf-8")
    local_script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert 'action_kind in ["step_ticks", "command", "commands"]' in main_script
    assert 'GateRailBridge.send_message({"commands": commands' in main_script
    assert 'str(_tutorial_next_action.get("kind", ""))' in main_script
    assert '"SurveySpaceSite"' in local_script
    assert '"PreviewSurveySpaceSite"' in local_script
