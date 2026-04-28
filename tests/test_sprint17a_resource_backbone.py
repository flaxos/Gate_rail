"""Tests for Sprint 17A resource catalog, deposits, and rail alignment data."""

from __future__ import annotations

from io import StringIO

import pytest

from gaterail.cli import run_cli
from gaterail.commands import BuildLink, BuildNode, PreviewBuildLink, command_from_dict
from gaterail.models import LinkMode, NetworkLink, NodeKind, TrackPoint
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.resources import ResourceCategory, resource_definition, resource_definitions
from gaterail.scenarios import build_sprint8_scenario
from gaterail.snapshot import render_snapshot


def test_resource_catalog_separates_elements_from_legacy_cargo() -> None:
    catalog = {definition.id: definition for definition in resource_definitions()}

    assert len(catalog) >= 20
    assert catalog["iron"].category == ResourceCategory.REFINED_ELEMENT
    assert catalog["iron"].symbol == "Fe"
    assert catalog["hydrogen"].atomic_number == 1
    assert catalog["helium_3"].isotope == "3"
    assert catalog["semiconductors"].category == ResourceCategory.MANUFACTURED_GOOD
    assert catalog["semiconductors"].cargo_type.value == "electronics"
    assert resource_definition("gate_reactive_isotope").discovered_by_default is False


def test_scenario_snapshot_exposes_resource_deposits_and_catalog() -> None:
    state = build_sprint8_scenario()

    snapshot = render_snapshot(state)

    resource_ids = {resource["id"] for resource in snapshot["resources"]}
    assert {"iron_rich_ore", "silicon", "gate_components"} <= resource_ids

    deposits = {deposit["id"]: deposit for deposit in snapshot["resource_deposits"]}
    north_ridge = deposits["frontier_north_ridge_iron"]
    assert north_ridge["world_id"] == "frontier"
    assert north_ridge["resource_id"] == "iron_rich_ore"
    assert north_ridge["grade"] == 0.74
    assert north_ridge["yield_per_tick"] == 6
    assert north_ridge["resource"]["category"] == "raw_source"

    frontier = next(world for world in snapshot["worlds"] if world["id"] == "frontier")
    assert "frontier_north_ridge_iron" in frontier["deposits"]


def test_resource_deposits_and_track_alignment_persist() -> None:
    state = build_sprint8_scenario()

    restored = state_from_dict(state_to_dict(state))

    assert restored.resource_deposits["frontier_silica_flats"].resource_id == "silica_sand"
    link = restored.links["rail_frontier_mine_settlement"]
    assert link.alignment == (
        TrackPoint(-78.0, 192.0),
        TrackPoint(-14.0, 154.0),
        TrackPoint(62.0, 106.0),
    )


def test_cli_inspection_can_focus_resource_deposits() -> None:
    output = StringIO()

    result = run_cli(["--inspect", "--report", "resources"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Resource Deposits" in text
    assert "Brink Frontier" in text
    assert "iron_rich_ore" in text
    assert "frontier_north_ridge_iron" not in text


def test_build_link_accepts_curved_alignment_without_changing_preview_state() -> None:
    state = build_sprint8_scenario()
    state.apply_command(
        BuildNode(
            node_id="frontier_curve_west",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier Curve West",
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.apply_command(
        BuildNode(
            node_id="frontier_curve_east",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            name="Frontier Curve East",
            layout_x=100.0,
            layout_y=0.0,
        )
    )

    preview = state.apply_command(
        PreviewBuildLink(
            link_id="rail_frontier_curved",
            origin="frontier_curve_west",
            destination="frontier_curve_east",
            mode=LinkMode.RAIL,
            alignment=(TrackPoint(50.0, 50.0),),
        )
    )

    assert preview["ok"] is True
    assert preview["travel_ticks"] == 3
    assert preview["normalized_command"]["alignment"] == [{"x": 50.0, "y": 50.0}]
    assert "rail_frontier_curved" not in state.links

    command = command_from_dict(
        {
            "type": "BuildLink",
            "link_id": "rail_frontier_curved",
            "origin": "frontier_curve_west",
            "destination": "frontier_curve_east",
            "mode": "rail",
            "alignment": {"points": [{"x": 50.0, "y": 50.0}]},
        }
    )
    assert isinstance(command, BuildLink)

    result = state.apply_command(command)

    assert result["ok"] is True
    assert state.links["rail_frontier_curved"].alignment == (TrackPoint(50.0, 50.0),)
    snapshot = render_snapshot(state)
    snapshot_link = next(link for link in snapshot["links"] if link["id"] == "rail_frontier_curved")
    assert snapshot_link["alignment"] == [{"x": 50.0, "y": 50.0}]


def test_gate_link_preview_rejects_track_alignment() -> None:
    state = build_sprint8_scenario()

    result = state.apply_command(
        PreviewBuildLink(
            link_id="gate_with_track_points",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            alignment=(TrackPoint(10.0, 10.0),),
        )
    )

    assert result["ok"] is False
    assert "only supported on rail" in str(result["reason"])


def test_state_rejects_nonfinite_track_alignment_points() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="finite"):
        state.add_link(
            NetworkLink(
                id="rail_bad_alignment",
                origin="frontier_mine",
                destination="frontier_gate",
                mode=LinkMode.RAIL,
                travel_ticks=1,
                capacity_per_tick=1,
                alignment=(TrackPoint(float("nan"), 0.0),),
            )
        )
