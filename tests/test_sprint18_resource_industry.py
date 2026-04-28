"""Tests for Sprint 18 typed resource industry chains."""

from __future__ import annotations

from io import StringIO

from gaterail.cli import run_cli
from gaterail.models import ResourceRecipeKind
from gaterail.persistence import state_from_dict
from gaterail.resource_chains import resource_branch_pressure
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_default_chain_has_typed_refining_electronics_semiconductor_and_fabrication() -> None:
    state = build_sprint8_scenario()

    assert state.nodes["frontier_smelter"].resource_recipe.kind == ResourceRecipeKind.SMELTING
    assert state.nodes["frontier_silicon_refiner"].resource_recipe.kind == ResourceRecipeKind.REFINING
    assert (
        state.nodes["frontier_electronics_assembler"].resource_recipe.kind
        == ResourceRecipeKind.ELECTRONICS_ASSEMBLY
    )
    assert state.nodes["frontier_semiconductor_line"].resource_recipe.kind == ResourceRecipeKind.SEMICONDUCTOR
    assert state.nodes["frontier_gate_fabricator"].resource_recipe.kind == ResourceRecipeKind.FABRICATION

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    assert by_id["frontier_semiconductor_line"]["resource_recipe"]["kind"] == "semiconductor"
    assert by_id["frontier_gate_fabricator"]["resource_recipe"]["inputs"] == {
        "iron": 4,
        "semiconductors": 1,
    }


def test_silicon_electronics_semiconductor_chain_feeds_gate_components() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    reports = simulation.run_ticks(4)

    assert reports[0]["resource_chains"]["recipes"]["produced"]["frontier_silicon_refiner"] == {
        "silicon": 3
    }
    assert reports[1]["resource_chains"]["recipes"]["produced"]["frontier_electronics_assembler"] == {
        "electronics": 2
    }
    assert reports[2]["resource_chains"]["recipes"]["produced"]["frontier_semiconductor_line"] == {
        "semiconductors": 1
    }
    assert reports[3]["resource_chains"]["recipes"]["produced"]["frontier_gate_fabricator"] == {
        "gate_components": 1
    }


def test_resource_branch_pressure_surfaces_industry_yard_warnings() -> None:
    state = build_sprint8_scenario()

    pressure = {entry["node"]: entry for entry in resource_branch_pressure(state)}

    assert pressure["frontier_silicon_refiner"]["severity"] == "branch"
    assert pressure["frontier_silicon_refiner"]["degree"] == 4
    assert pressure["frontier_silicon_refiner"]["recipe_kind"] == "refining"
    assert "rail_frontier_silicon_semiconductor" in pressure["frontier_silicon_refiner"]["resource_links"]

    snapshot = render_snapshot(state)
    snapshot_pressure = {entry["node"]: entry for entry in snapshot["resource_branch_pressure"]}
    assert snapshot_pressure["frontier_semiconductor_line"]["recipe_kind"] == "semiconductor"


def test_cli_resource_inspection_lists_recipe_kinds_and_branch_pressure() -> None:
    output = StringIO()

    result = run_cli(["--inspect", "--report", "resources"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Resource Chain Nodes" in text
    assert "semiconductor_lithography [semiconductor]" in text
    assert "Resource Branch Pressure" in text
    assert "frontier_silicon_refiner" in text


def test_resource_recipe_load_without_kind_defaults_to_generic() -> None:
    state = state_from_dict(
        {
            "worlds": [
                {
                    "id": "frontier",
                    "name": "Brink Frontier",
                    "tier": 0,
                }
            ],
            "nodes": [
                {
                    "id": "legacy_refiner",
                    "name": "Legacy Refiner",
                    "world_id": "frontier",
                    "kind": "industry",
                    "resource_recipe": {
                        "id": "legacy_recipe",
                        "inputs": {"silica_sand": 1},
                        "outputs": {"silicon": 1},
                    },
                }
            ],
        }
    )

    assert state.nodes["legacy_refiner"].resource_recipe.kind == ResourceRecipeKind.GENERIC
