"""Sprint 26 save/load bridge and playtest scenario coverage."""

from __future__ import annotations

from pathlib import Path

from gaterail.bridge import handle_bridge_message, iter_stdio_snapshots
from gaterail.cli import run_cli
from gaterail.models import ResourceRecipeKind
from gaterail.simulation import TickSimulation


def test_bridge_can_save_and_reload_current_simulation(tmp_path) -> None:
    save_path = tmp_path / "bridge_round_trip.json"
    simulation = TickSimulation.from_scenario("sprint8")

    saved_snapshot = handle_bridge_message(
        simulation,
        {"ticks": 3, "save_path": str(save_path)},
    )
    handle_bridge_message(simulation, {"ticks": 5})
    loaded_snapshot = handle_bridge_message(
        simulation,
        {"ticks": 0, "load_path": str(save_path)},
    )

    assert save_path.exists()
    assert saved_snapshot["tick"] == 3
    assert saved_snapshot["bridge"]["saved_path"] == str(save_path)
    assert simulation.state.tick == 3
    assert loaded_snapshot["tick"] == 3
    assert loaded_snapshot["bridge"]["loaded_path"] == str(save_path)
    assert "core_food_service" in simulation.state.schedules


def test_bridge_can_reset_to_named_playtest_scenario() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    handle_bridge_message(simulation, {"ticks": 4})

    snapshot = handle_bridge_message(
        simulation,
        {"scenario": "early_build", "ticks": 0},
    )

    assert snapshot["tick"] == 0
    assert simulation.state.tick == 0
    assert snapshot["bridge"]["loaded_scenario"] == "early_build"
    assert {world["id"] for world in snapshot["worlds"]} == {"core", "frontier"}
    assert len(snapshot["schedules"]) == 1


def test_bridge_reports_missing_save_file_with_readable_error(tmp_path) -> None:
    missing_path = tmp_path / "missing_save.json"
    simulation = TickSimulation.from_scenario("sprint8")

    frame = next(iter_stdio_snapshots(simulation, [f'{{"load_path":"{missing_path}"}}\n']))

    assert frame["bridge"]["ok"] is False
    assert f"save file not found: {missing_path}" in frame["bridge"]["error"]
    assert simulation.state.tick == 0


def test_sprint26_scenarios_cover_early_build_and_large_industrial_worlds() -> None:
    early = TickSimulation.from_scenario("early_build").state
    expanded = TickSimulation.from_scenario("industrial_expansion").state

    assert len(early.worlds) == 2
    assert len(early.nodes) <= 7
    assert len(early.links) <= 6
    assert len(early.schedules) == 1
    assert early.finance.cash < expanded.finance.cash
    assert early.schedules["starter_food_service"].active is False

    recipe_kinds = {
        node.resource_recipe.kind
        for node in expanded.nodes.values()
        if node.resource_recipe is not None
    }
    assert len(expanded.worlds) >= 5
    assert len(expanded.nodes) >= 24
    assert len(expanded.links) >= 28
    assert len(expanded.schedules) >= 9
    assert len(expanded.resource_deposits) >= 10
    assert len(expanded.power_plants) >= 3
    assert len(expanded.gate_supports) >= 2
    assert ResourceRecipeKind.SMELTING in recipe_kinds
    assert ResourceRecipeKind.ELECTRONICS_ASSEMBLY in recipe_kinds
    assert ResourceRecipeKind.SEMICONDUCTOR in recipe_kinds
    assert any(schedule.stops for schedule in expanded.schedules.values())


def test_cli_lists_sprint26_playtest_scenario_types() -> None:
    from io import StringIO

    output = StringIO()

    result = run_cli(["--list-scenarios"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "early_build:" in text
    assert "aliases: early, starter, new_game" in text
    assert "industrial_expansion:" in text
    assert "aliases: industrial, expanded, large_industry" in text


def test_godot_save_load_and_scenario_controls_are_wired() -> None:
    bridge_script = Path("godot/scripts/gate_rail_bridge.gd").read_text(encoding="utf-8")
    main_script = Path("godot/scripts/main.gd").read_text(encoding="utf-8")

    assert "var last_save_path" in bridge_script
    assert "func normalize_save_path(" in bridge_script
    assert "func save_game(" in bridge_script
    assert '"save_path"' in bridge_script
    assert "func load_game(" in bridge_script
    assert '"load_path"' in bridge_script
    assert "func load_scenario(" in bridge_script
    assert '"scenario"' in bridge_script

    assert "_save_path_edit" in main_script
    assert "GateRailBridge.last_save_path" in main_script
    assert "GateRailBridge.normalize_save_path" in main_script
    assert "_scenario_select" in main_script
    assert "_on_save_game_pressed" in main_script
    assert "_on_load_game_pressed" in main_script
    assert "_on_load_scenario_pressed" in main_script
