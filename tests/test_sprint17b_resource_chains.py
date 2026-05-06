"""Tests for Sprint 17B resource-aware extraction and recipe chains."""

from __future__ import annotations

from io import StringIO

import pytest

from gaterail.cli import run_cli
from gaterail.models import (
    DevelopmentTier,
    GameState,
    NetworkNode,
    NodeKind,
    ResourceRecipe,
    ResourceRecipeKind,
    WorldState,
)
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.resource_chains import apply_resource_recipes
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_sprint8_resource_chain_extracts_smelts_and_fabricates_gate_components() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    first = simulation.step_tick()
    simulation.step_tick()
    third = simulation.step_tick()
    fourth = simulation.step_tick()

    assert first["resource_chains"]["extracted"]["frontier_ore_pit"] == {"iron_rich_ore": 6}
    assert first["resource_chains"]["recipes"]["produced"]["frontier_smelter"] == {"iron": 4}
    assert third["resource_chains"]["recipes"]["produced"]["frontier_semiconductor_line"] == {
        "semiconductors": 1
    }
    assert fourth["resource_chains"]["recipes"]["produced"]["frontier_gate_fabricator"] == {
        "gate_components": 1
    }

    fabricator = simulation.state.nodes["frontier_gate_fabricator"]
    assert fabricator.resource_stock("gate_components") == 1


def test_resource_recipe_blockers_are_recorded_and_snapshotted() -> None:
    state = GameState()
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_fabricator",
            name="Frontier Fabricator",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"iron": 2},
            resource_recipe=ResourceRecipe(
                id="aperture_control_fabrication",
                kind=ResourceRecipeKind.FABRICATION,
                inputs={"electronics": 1, "iron": 4},
                outputs={"gate_components": 1},
            ),
        )
    )

    result = apply_resource_recipes(state)

    assert result["blocked"] == [
        {
            "node": "frontier_fabricator",
            "recipe": "aperture_control_fabrication",
            "recipe_kind": "fabrication",
            "reason": "missing resource inputs",
            "missing": {"electronics": 1, "iron": 2},
        }
    ]
    assert state.resource_recipe_blocked == {"frontier_fabricator": {"electronics": 1, "iron": 2}}

    snapshot = render_snapshot(state)
    fabricator = next(node for node in snapshot["nodes"] if node["id"] == "frontier_fabricator")
    assert fabricator["resource_inventory"] == {"iron": 2}
    assert fabricator["resource_recipe"] == {
        "id": "aperture_control_fabrication",
        "kind": "fabrication",
        "inputs": {"electronics": 1, "iron": 4},
        "outputs": {"gate_components": 1},
    }
    assert fabricator["resource_recipe_blocked"] == {"electronics": 1, "iron": 2}


def test_resource_chain_state_persists_through_save_load() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    simulation.run_ticks(4)

    restored = state_from_dict(state_to_dict(simulation.state))

    fabricator = restored.nodes["frontier_gate_fabricator"]
    assert fabricator.resource_recipe is not None
    assert fabricator.resource_recipe.id == "aperture_control_fabrication"
    assert fabricator.resource_recipe.kind == ResourceRecipeKind.FABRICATION
    assert fabricator.resource_stock("gate_components") == 1
    assert restored.nodes["frontier_ore_pit"].resource_deposit_id == "frontier_north_ridge_iron"


def test_cli_resource_report_shows_processing_and_blockers() -> None:
    output = StringIO()

    result = run_cli(["--ticks", "4", "--report", "resources", "--no-summary"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Resources:" in text
    assert "frontier_smelter" in text
    assert "Resource Branches:" in text
    assert "gate_components 1" in text
    assert "blocked" in text


def test_node_resource_recipe_validation_rejects_unknown_resource() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="unknown resource id"):
        state.add_node(
            NetworkNode(
                id="bad_resource_recipe",
                name="Bad Resource Recipe",
                world_id="frontier",
                kind=NodeKind.INDUSTRY,
                resource_recipe=ResourceRecipe(
                    id="bad",
                    inputs={"not_a_resource": 1},
                    outputs={"iron": 1},
                ),
            )
        )
