"""Tests for Sprint 19 resource-backed Railgate power support."""

from __future__ import annotations

from io import StringIO

import pytest

from gaterail.cli import run_cli
from gaterail.gate import evaluate_gate_power
from gaterail.models import GatePowerSupport
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.scenarios import build_sprint8_scenario, build_sprint19_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def test_resource_gate_support_powers_gate_after_components_are_fabricated() -> None:
    simulation = TickSimulation.from_scenario("sprint19")

    first = simulation.step_tick()
    simulation.run_ticks(2)
    fourth = simulation.step_tick()

    first_gate = first["gates"]["gate_frontier_outer"]
    assert first_gate["powered"] is False
    assert first_gate["power_shortfall"] == 30
    assert first_gate["support_missing"] == {"gate_components": 1}

    fourth_gate = fourth["gates"]["gate_frontier_outer"]
    assert fourth_gate["powered"] is True
    assert fourth_gate["base_power_required"] == 90
    assert fourth_gate["power_required"] == 50
    assert fourth_gate["resource_power_bonus"] == 40
    assert fourth_gate["support_missing"] == {}
    assert simulation.state.nodes["frontier_gate_fabricator"].resource_stock("gate_components") == 1


def test_resource_gate_support_persists_and_snapshots() -> None:
    simulation = TickSimulation.from_scenario("sprint19")
    simulation.run_ticks(4)

    restored = state_from_dict(state_to_dict(simulation.state))
    statuses = evaluate_gate_power(restored)

    assert "frontier_gate_component_support" in restored.gate_supports
    support = restored.gate_supports["frontier_gate_component_support"]
    assert support.inputs == {"gate_components": 1}
    assert statuses["gate_frontier_outer"].powered is True
    assert statuses["gate_frontier_outer"].resource_power_bonus == 40

    snapshot = render_snapshot(restored)
    link = next(item for item in snapshot["links"] if item["id"] == "gate_frontier_outer")
    assert link["effective_power_required"] == 50
    assert link["gate_support"] == {
        "id": "frontier_gate_component_support",
        "node_id": "frontier_gate_fabricator",
        "inputs": {"gate_components": 1},
        "missing": {},
        "power_bonus": 40,
        "base_power_required": 90,
        "effective_power_required": 50,
        "available": True,
    }


def test_cli_gate_report_shows_resource_support_recovery() -> None:
    output = StringIO()

    result = run_cli(
        ["--scenario", "sprint19", "--ticks", "4", "--report", "gates,resources", "--no-summary"],
        output=output,
    )

    text = output.getvalue()
    assert result == 0
    assert "gate_frontier_outer underpowered" in text
    assert "missing gate_components 1" in text
    assert "gate_frontier_outer powered" in text
    assert "supported by frontier_gate_fabricator bonus 40" in text


def test_gate_support_validation_rejects_non_gate_target() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="target link is not a gate"):
        state.add_gate_support(
            GatePowerSupport(
                id="bad_support",
                link_id="rail_frontier_smelter_fabricator",
                node_id="frontier_gate_fabricator",
                inputs={"gate_components": 1},
                power_bonus=40,
            )
        )


def test_gate_support_validation_rejects_unknown_resource_input() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="unknown resource id"):
        state.add_gate_support(
            GatePowerSupport(
                id="bad_support",
                link_id="gate_frontier_outer",
                node_id="frontier_gate_fabricator",
                inputs={"not_a_resource": 1},
                power_bonus=40,
            )
        )
