"""Tests for Sprint 19B/20A resource-backed power generation."""

from __future__ import annotations

from io import StringIO

import pytest

from gaterail.cli import run_cli
from gaterail.models import (
    DevelopmentTier,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    PowerPlant,
    PowerPlantKind,
    WorldState,
)
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.power import apply_power_plants
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _power_test_state(*, fuel_units: int = 1) -> GameState:
    """Build a gate that needs generated frontier power."""

    state = GameState()
    state.add_world(
        WorldState(
            id="core",
            name="Core",
            tier=DevelopmentTier.CORE_WORLD,
            power_available=200,
        )
    )
    state.add_world(
        WorldState(
            id="frontier",
            name="Frontier",
            tier=DevelopmentTier.OUTPOST,
            power_available=60,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Core Gate",
            world_id="core",
            kind=NodeKind.GATE_HUB,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Frontier Gate",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_plant",
            name="Frontier Thermal Plant",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"fuel": fuel_units} if fuel_units > 0 else {},
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_core_frontier",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=2,
            power_required=80,
            power_source_world_id="frontier",
        )
    )
    state.add_power_plant(
        PowerPlant(
            id="frontier_thermal",
            node_id="frontier_plant",
            kind=PowerPlantKind.THERMAL,
            inputs={"fuel": 1},
            power_output=30,
        )
    )
    return state


def test_power_plant_consumes_resource_and_powers_gate() -> None:
    simulation = TickSimulation(state=_power_test_state(fuel_units=1))

    report = simulation.step_tick()

    assert report["power_generation"]["generated"] == {"frontier": 30}
    assert report["power_generation"]["consumed"] == {"frontier_thermal": {"fuel": 1}}
    assert report["gates"]["gate_core_frontier"]["powered"] is True
    assert report["gates"]["gate_core_frontier"]["power_available"] == 90
    assert simulation.state.worlds["frontier"].power_generated_this_tick == 30
    assert simulation.state.nodes["frontier_plant"].resource_stock("fuel") == 0


def test_power_plant_missing_inputs_blocks_generation_and_gate() -> None:
    simulation = TickSimulation(state=_power_test_state(fuel_units=0))

    report = simulation.step_tick()

    assert report["power_generation"]["generated"] == {}
    assert report["power_generation"]["blocked"] == [
        {
            "plant": "frontier_thermal",
            "node": "frontier_plant",
            "world": "frontier",
            "kind": "thermal",
            "reason": "missing power plant inputs",
            "missing": {"fuel": 1},
            "power_output": 30,
        }
    ]
    assert simulation.state.power_plant_blocked == {"frontier_thermal": {"fuel": 1}}
    assert report["gates"]["gate_core_frontier"]["powered"] is False
    assert report["gates"]["gate_core_frontier"]["power_shortfall"] == 20


def test_power_plants_persist_and_snapshot() -> None:
    state = _power_test_state(fuel_units=2)

    apply_power_plants(state)
    restored = state_from_dict(state_to_dict(state))

    assert restored.power_plants["frontier_thermal"] == state.power_plants["frontier_thermal"]
    assert restored.worlds["frontier"].power_generated_this_tick == 30
    snapshot = render_snapshot(restored)
    frontier = next(world for world in snapshot["worlds"] if world["id"] == "frontier")
    assert frontier["power"]["generated"] == 30
    assert snapshot["power_generation"] == {"frontier": 30}
    assert snapshot["power_plants"] == [
        {
            "id": "frontier_thermal",
            "node_id": "frontier_plant",
            "world_id": "frontier",
            "kind": "thermal",
            "inputs": {"fuel": 1},
            "power_output": 30,
            "active": True,
            "missing": {},
        }
    ]
    plant_node = next(node for node in snapshot["nodes"] if node["id"] == "frontier_plant")
    assert plant_node["power_plants"] == ["frontier_thermal"]


def test_power_plant_validation_rejects_bad_inputs() -> None:
    state = _power_test_state(fuel_units=1)

    with pytest.raises(ValueError, match="power_output must be positive"):
        state.add_power_plant(
            PowerPlant(
                id="bad_output",
                node_id="frontier_plant",
                inputs={"fuel": 1},
                power_output=0,
            )
        )

    with pytest.raises(ValueError, match="unknown resource id"):
        state.add_power_plant(
            PowerPlant(
                id="bad_resource",
                node_id="frontier_plant",
                inputs={"not_real": 1},
                power_output=10,
            )
        )


def test_cli_sprint19b_reports_generated_power_and_gate_recovery() -> None:
    output = StringIO()

    result = run_cli(
        ["--scenario", "sprint19b", "--ticks", "1", "--report", "power,gates", "--no-summary"],
        output=output,
    )

    text = output.getvalue()
    assert result == 0
    assert "Power: generated frontier +40" in text
    assert "frontier_low_basin_thermal (carbon_feedstock 1)" in text
    assert "gate_frontier_outer powered by Brink Frontier draw 90" in text
