"""Lore and terminology alignment checks for the Railgate Age framing."""

from __future__ import annotations

from pathlib import Path

from gaterail.cargo import cargo_catalog_payload
from gaterail.resources import resource_definition
from gaterail.scenarios import load_scenario, scenario_definitions
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_core_lore_terms_are_documented() -> None:
    text = "\n".join(
        [
            Path("README.md").read_text(encoding="utf-8"),
            Path("GAME_VISION.md").read_text(encoding="utf-8"),
        ]
    )

    for term in (
        "Horizon Artefact",
        "Horizon Event",
        "Railgate Age",
        "derivative aperture systems",
        "Transit Combines",
        "The first gate was a miracle. Railgates are a business model.",
    ):
        assert term in text


def test_aperture_control_components_are_player_facing_catalog_labels() -> None:
    cargo = next(item for item in cargo_catalog_payload() if item["id"] == "gate_components")

    assert cargo["name"] == "Aperture Control Components"
    assert resource_definition("gate_components").name == "Aperture Control Components"
    assert "Railgate" in resource_definition("gate_components").description


def test_scenarios_use_corporate_clients_and_railgate_infrastructure_names() -> None:
    state = load_scenario("sprint8")
    clients = {contract.client for contract in state.contracts.values()}
    definitions = {definition.key: definition for definition in scenario_definitions()}

    assert "Brink Extraction Combine" in clients
    assert "Vesta Industrial Combine" in clients
    assert "Ashfall Corridor Logistics" in clients
    assert state.nodes["core_gate"].name == "Vesta Railgate Anchor"
    assert state.nodes["frontier_gate"].name == "Brink Railgate Terminal"
    assert (
        state.nodes["frontier_gate_fabricator"].resource_recipe.id
        == "aperture_control_fabrication"
    )
    assert "Railgate" in definitions["sprint4"].title
    assert "Railgate" in definitions["sprint19"].description


def test_tutorial_payload_uses_railgate_age_language() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    tutorial = render_snapshot(simulation.state)["tutorial"]

    assert tutorial["title"] == "Railgate Age Tutorial Start"
    assert "Railgate corridor" in tutorial["summary"]
    assert tutorial["alerts"] == [
        {
            "kind": "tutorial",
            "message": "Tutorial active: move ore through the Brink-Cinder Railgate corridor.",
        }
    ]
