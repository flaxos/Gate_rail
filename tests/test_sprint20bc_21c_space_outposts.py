"""Tests for Sprint 20B/C space loop closure and Sprint 21C overlays."""

from __future__ import annotations

import json
from io import StringIO

import pytest

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.commands import BuildNode, PreviewBuildLink, command_from_dict
from gaterail.construction import (
    apply_construction_projects,
    outpost_build_cargo,
    outpost_build_cost,
    outpost_duration_estimate_ticks,
)
from gaterail.models import (
    ConstructionProject,
    ConstructionStatus,
    DevelopmentTier,
    Facility,
    FacilityBlockReason,
    FacilityComponent,
    FacilityComponentKind,
    GameState,
    LinkMode,
    MiningMissionStatus,
    NetworkNode,
    NodeKind,
    OutpostKind,
    SpaceSite,
    WorldState,
)
from gaterail.persistence import save_simulation, state_from_dict, state_to_dict
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot
from gaterail.space import advance_mining_missions


def _world(
    *,
    world_id: str = "w1",
    name: str = "Brink Frontier",
    power_available: int = 200,
    power_used: int = 50,
) -> WorldState:
    return WorldState(
        id=world_id,
        name=name,
        tier=DevelopmentTier.OUTPOST,
        population=12_000,
        power_available=power_available,
        power_used=power_used,
    )


def _node(
    node_id: str,
    kind: NodeKind,
    *,
    world_id: str = "w1",
    name: str | None = None,
    storage_capacity: int = 1_000,
    transfer_limit_per_tick: int = 24,
    layout_x: float | None = None,
    layout_y: float | None = None,
    inventory: dict[CargoType, int] | None = None,
    facility: Facility | None = None,
    outpost_kind: OutpostKind | None = None,
) -> NetworkNode:
    return NetworkNode(
        id=node_id,
        name=node_id if name is None else name,
        world_id=world_id,
        kind=kind,
        storage_capacity=storage_capacity,
        transfer_limit_per_tick=transfer_limit_per_tick,
        layout_x=layout_x,
        layout_y=layout_y,
        inventory=dict(inventory or {}),
        facility=facility,
        outpost_kind=outpost_kind,
    )


def _space_state(*, launch_fuel: int = 100) -> GameState:
    state = GameState()
    state.finance.cash = 50_000.0
    state.add_world(_world())
    state.add_node(
        _node(
            "orbital_yard",
            NodeKind.ORBITAL_YARD,
            storage_capacity=3_000,
            transfer_limit_per_tick=24,
            inventory={CargoType.FUEL: launch_fuel},
        )
    )
    state.add_node(
        _node(
            "collection_station",
            NodeKind.COLLECTION_STATION,
            storage_capacity=500,
            transfer_limit_per_tick=36,
            inventory={CargoType.FOOD: 300},
        )
    )
    state.add_node(_node("surface_settlement", NodeKind.SETTLEMENT))
    state.add_node(_node("industry_pad", NodeKind.INDUSTRY))
    state.add_node(
        _node(
            "frontier_depot",
            NodeKind.DEPOT,
            storage_capacity=2_000,
            transfer_limit_per_tick=36,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        _node(
            "frontier_warehouse",
            NodeKind.WAREHOUSE,
            storage_capacity=4_000,
            transfer_limit_per_tick=48,
            layout_x=200.0,
            layout_y=0.0,
        )
    )
    state.add_space_site(
        SpaceSite(
            id="site_alpha",
            name="Alpha Belt",
            resource_id="mixed_ore",
            travel_ticks=5,
            base_yield=500,
        )
    )
    return state


def _preview_build_outpost(state: GameState, outpost_kind: str = "outpost_frontier") -> dict[str, object]:
    return state.apply_command(
        command_from_dict(
            {
                "type": "PreviewBuildOutpost",
                "world_id": "w1",
                "outpost_kind": outpost_kind,
                "layout": {"x": 100.0, "y": 100.0},
            }
        )
    )


def _build_outpost(state: GameState, outpost_kind: str = "outpost_frontier") -> tuple[dict[str, object], NetworkNode, ConstructionProject]:
    preview = _preview_build_outpost(state, outpost_kind)
    assert preview["ok"] is True
    result = state.apply_command(command_from_dict(preview["normalized_command"]))
    assert result["ok"] is True
    node = state.nodes[result["target_id"]]
    project = state.construction_projects[node.construction_project_id]
    return result, node, project


def _partial_outpost_state() -> tuple[GameState, NetworkNode, ConstructionProject]:
    state = _space_state()
    _, node, project = _build_outpost(state, "outpost_frontier")
    node.add_inventory(CargoType.CONSTRUCTION_MATERIALS, 50)
    apply_construction_projects(state)
    return state, node, project


def test_build_node_supports_orbital_yard_defaults_and_snapshot_kind() -> None:
    state = GameState()
    state.finance.cash = 50_000.0
    state.add_world(_world())

    result = state.apply_command(
        BuildNode(
            node_id="orbital_yard_built",
            world_id="w1",
            kind=NodeKind.ORBITAL_YARD,
            name="Orbital Yard Built",
        )
    )

    assert result["ok"] is True
    node = state.nodes["orbital_yard_built"]
    assert node.kind == NodeKind.ORBITAL_YARD
    assert node.storage_capacity == 3_000
    assert node.transfer_limit_per_tick == 24

    snapshot = render_snapshot(state)
    snapshot_node = next(item for item in snapshot["nodes"] if item["id"] == "orbital_yard_built")
    assert snapshot_node["kind"] == "orbital_yard"


def test_mining_mission_preview_validates_kinds_fuel_power_and_return_capacity() -> None:
    state = _space_state()

    invalid_launch = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "m_invalid_launch",
                "site_id": "site_alpha",
                "launch_node_id": "surface_settlement",
                "return_node_id": "collection_station",
            }
        )
    )
    assert invalid_launch["ok"] is False
    assert invalid_launch["reason"] == "invalid_launch_kind"

    invalid_return = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "m_invalid_return",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "industry_pad",
            }
        )
    )
    assert invalid_return["ok"] is False
    assert invalid_return["reason"] == "invalid_return_kind"

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "m_valid",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 30,
            }
        )
    )
    assert preview["ok"] is True
    assert preview["fuel_required"] == 30
    assert preview["fuel_available"] == 100
    assert preview["power_required"] == 30
    assert preview["power_available"] == 150
    assert preview["power_shortfall_if_dispatched"] == 0
    assert preview["return_capacity_estimate"] == 200

    dry_state = _space_state(launch_fuel=20)
    dry_preview = dry_state.apply_command(
        command_from_dict(
            {
                "type": "PreviewDispatchMiningMission",
                "mission_id": "m_dry",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 30,
            }
        )
    )
    assert dry_preview["ok"] is False
    assert dry_preview["reason"] == "insufficient_fuel"

    dry_dispatch = dry_state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "m_dry",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 30,
            }
        )
    )
    assert dry_dispatch["ok"] is False
    assert dry_dispatch["reason"] == "insufficient_fuel"


def test_dispatch_mining_mission_spends_fuel_reserves_power_and_caps_delivery() -> None:
    state = _space_state()

    dispatch = state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_alpha",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 30,
            }
        )
    )

    assert dispatch["ok"] is True
    assert state.nodes["orbital_yard"].stock(CargoType.FUEL) == 70
    assert state.worlds["w1"].power_used == 80

    mission = state.mining_missions["mission_alpha"]
    assert mission.status == MiningMissionStatus.EN_ROUTE
    assert mission.reserved_power == 30
    assert mission.fuel_consumed == 30

    snapshot = render_snapshot(state)
    snapshot_mission = next(item for item in snapshot["mining_missions"] if item["id"] == "mission_alpha")
    assert snapshot_mission["reserved_power"] == 30
    assert snapshot_mission["fuel_consumed"] == 30
    assert snapshot_mission["projected_yield"] == 500

    mission.ticks_remaining = 1
    report = advance_mining_missions(state)

    assert mission.status == MiningMissionStatus.COMPLETED
    assert state.worlds["w1"].power_used == 50
    assert state.nodes["collection_station"].resource_inventory == {"mixed_ore": 200}
    assert report["dropped_units"] == [{"mission_id": "mission_alpha", "dropped_units": 300}]


def test_failed_mission_releases_reserved_power_without_refunding_fuel() -> None:
    state = _space_state()
    state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_fail",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 15,
            }
        )
    )

    mission = state.mining_missions["mission_fail"]
    mission.status = MiningMissionStatus.FAILED
    report = advance_mining_missions(state)

    assert report["failed_this_tick"] == 1
    assert state.worlds["w1"].power_used == 50
    assert state.nodes["orbital_yard"].stock(CargoType.FUEL) == 70


def test_build_outpost_preview_build_link_block_and_completion_promotion() -> None:
    state = _space_state()

    preview = _preview_build_outpost(state, "outpost_frontier")

    assert preview["ok"] is True
    assert preview["cost"] == pytest.approx(outpost_build_cost(OutpostKind.OUTPOST_FRONTIER))
    assert preview["cargo_required"] == {
        cargo.value: units
        for cargo, units in outpost_build_cargo(OutpostKind.OUTPOST_FRONTIER).items()
    }
    assert preview["duration_estimate_ticks"] == outpost_duration_estimate_ticks(OutpostKind.OUTPOST_FRONTIER)

    build_result = state.apply_command(command_from_dict(preview["normalized_command"]))
    assert build_result["ok"] is True

    outpost = state.nodes[build_result["target_id"]]
    project = state.construction_projects[outpost.construction_project_id]
    assert outpost.kind == NodeKind.OUTPOST
    assert outpost.outpost_kind == OutpostKind.OUTPOST_FRONTIER
    assert project.status == ConstructionStatus.PENDING

    blocked_link = state.apply_command(
        PreviewBuildLink(
            link_id="rail_depot_outpost",
            origin="frontier_depot",
            destination=outpost.id,
            mode=LinkMode.RAIL,
        )
    )
    assert blocked_link["ok"] is False
    assert blocked_link["reason"] == "outpost_not_operational"

    project.required_cargo = {CargoType.CONSTRUCTION_MATERIALS: 100}
    project.delivered_cargo = {}
    outpost.inventory = {CargoType.CONSTRUCTION_MATERIALS: 100}
    progress = apply_construction_projects(state)

    assert progress[project.id] == {"construction_materials": 100}
    assert project.status == ConstructionStatus.COMPLETED
    assert outpost.kind == NodeKind.EXTRACTOR
    assert outpost.construction_project_id is None

    promoted_link = state.apply_command(
        PreviewBuildLink(
            link_id="rail_depot_promoted_outpost",
            origin="frontier_depot",
            destination=outpost.id,
            mode=LinkMode.RAIL,
        )
    )
    assert promoted_link["ok"] is True


def test_cancel_outpost_refunds_half_cash_and_delivered_cargo_to_nearest_refund_node() -> None:
    state, outpost, project = _partial_outpost_state()
    starting_cash = state.finance.cash

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewCancelOutpost",
                "outpost_id": outpost.id,
            }
        )
    )

    assert preview["ok"] is True
    assert preview["refund_cash"] == pytest.approx(outpost_build_cost(OutpostKind.OUTPOST_FRONTIER) * 0.5)
    assert preview["refund_cargo"] == {"construction_materials": 25}
    assert preview["refund_node_id"] == "frontier_depot"

    result = state.apply_command(
        command_from_dict(
            {
                "type": "CancelOutpost",
                "outpost_id": outpost.id,
            }
        )
    )

    assert result["ok"] is True
    assert result["refund_cash"] == preview["refund_cash"]
    assert result["refund_cargo"] == preview["refund_cargo"]
    assert result["refund_dropped"] == {}
    assert preview["refund_dropped"] == {}
    assert outpost.id not in state.nodes
    assert project.id not in state.construction_projects
    assert state.nodes["frontier_depot"].stock(CargoType.CONSTRUCTION_MATERIALS) == 25
    assert state.finance.cash == pytest.approx(starting_cash + preview["refund_cash"])


def test_cancel_outpost_caps_refund_at_refund_node_storage_capacity() -> None:
    state, outpost, project = _partial_outpost_state()
    refund_node = state.nodes["frontier_depot"]
    capacity = refund_node.effective_storage_capacity()
    refund_node.add_inventory(CargoType.CONSTRUCTION_MATERIALS, capacity - 10)
    starting_stock = refund_node.stock(CargoType.CONSTRUCTION_MATERIALS)
    starting_cash = state.finance.cash

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewCancelOutpost",
                "outpost_id": outpost.id,
            }
        )
    )

    assert preview["ok"] is True
    assert preview["refund_cargo"] == {"construction_materials": 10}
    assert preview["refund_dropped"] == {"construction_materials": 15}

    result = state.apply_command(
        command_from_dict(
            {
                "type": "CancelOutpost",
                "outpost_id": outpost.id,
            }
        )
    )

    assert result["ok"] is True
    assert result["refund_cargo"] == {"construction_materials": 10}
    assert result["refund_dropped"] == {"construction_materials": 15}
    assert refund_node.stock(CargoType.CONSTRUCTION_MATERIALS) == starting_stock + 10
    assert refund_node.total_inventory() == capacity
    assert state.finance.cash == pytest.approx(starting_cash + result["refund_cash"])


def test_outpost_save_load_round_trip_matches_unsaved_completion_path() -> None:
    state = _space_state()
    _, outpost, project = _build_outpost(state, "outpost_frontier")
    outpost.add_inventory(CargoType.CONSTRUCTION_MATERIALS, 120)
    outpost.add_inventory(CargoType.ELECTRONICS, 30)
    apply_construction_projects(state)

    direct = state
    restored = state_from_dict(state_to_dict(state))

    for candidate in (direct, restored):
        node = candidate.nodes[outpost.id]
        candidate_project = next(
            item
            for item in candidate.construction_projects.values()
            if item.target_node_id == outpost.id
        )
        for cargo, units in candidate_project.remaining_cargo.items():
            node.add_inventory(cargo, units)
        apply_construction_projects(candidate)

    assert json.dumps(state_to_dict(restored), sort_keys=True) == json.dumps(
        state_to_dict(direct),
        sort_keys=True,
    )


def test_bridge_handles_unknown_outpost_kind_without_top_level_error() -> None:
    snapshot = handle_bridge_message(
        TickSimulation(state=_space_state()),
        {
            "command": {
                "type": "PreviewBuildOutpost",
                "world_id": "w1",
                "outpost_kind": "not_real",
                "layout": {"x": 100.0, "y": 100.0},
            },
            "ticks": 0,
        },
    )

    assert snapshot["bridge"]["ok"] is True
    assert snapshot["bridge"]["command_results"] == [
        {
            "ok": False,
            "type": "PreviewBuildOutpost",
            "target_id": "outpost_1",
            "message": "unknown outpost kind: not_real",
            "reason": "unknown_outpost_kind",
        }
    ]


def test_snapshot_exposes_outposts_overlay_pips_top_needs_and_power_pressure() -> None:
    state = _space_state()
    _, outpost, project = _build_outpost(state, "outpost_frontier")
    outpost.add_inventory(CargoType.CONSTRUCTION_MATERIALS, 50)
    apply_construction_projects(state)

    state.add_node(
        _node(
            "blocked_factory",
            NodeKind.INDUSTRY,
            facility=Facility(
                components={
                    "fab-1": FacilityComponent(
                        id="fab-1",
                        kind=FacilityComponentKind.FACTORY_BLOCK,
                        inputs={CargoType.ORE: 2},
                        outputs={CargoType.PARTS: 1},
                    )
                }
            ),
        )
    )
    state.facility_blocked = {"blocked_factory": ["fab-1"]}
    state.facility_block_entries = [
        {
            "node": "blocked_factory",
            "component": "fab-1",
            "kind": "factory_block",
            "reason": FacilityBlockReason.MISSING_INPUTS,
            "detail": {"missing": {"ore": 2}},
        }
    ]
    state.add_node(
        _node(
            "power_factory",
            NodeKind.INDUSTRY,
            facility=Facility(
                components={
                    "smelter-1": FacilityComponent(
                        id="smelter-1",
                        kind=FacilityComponentKind.SMELTER,
                        power_required=20,
                        inputs={CargoType.ORE: 2},
                        outputs={CargoType.METAL: 1},
                    )
                }
            ),
        )
    )

    snapshot = render_snapshot(state)
    world = next(item for item in snapshot["worlds"] if item["id"] == "w1")
    assert world["power_available"] == 200
    assert world["power_used"] == 50
    assert world["power_pressure"] == pytest.approx(0.25)

    blocked_node = next(item for item in snapshot["nodes"] if item["id"] == "blocked_factory")
    assert blocked_node["overlay_pip"] == {
        "layer": "facility_block_layer",
        "severity": "warn",
        "label": "missing inputs",
    }

    power_node = next(item for item in snapshot["nodes"] if item["id"] == "power_factory")
    assert power_node["power_required"] == 20
    assert power_node["overlay_pip"]["layer"] == "power_layer"

    outpost_entry = next(item for item in snapshot["outposts"] if item["id"] == outpost.id)
    assert outpost_entry["construction_status"] == ConstructionStatus.ACTIVE.value
    assert outpost_entry["progress_fraction"] == pytest.approx(50 / sum(project.required_cargo.values()))
    assert {item["cargo"] for item in outpost_entry["top_needs"]} == {
        "construction_materials",
        "food",
        "water",
    }

    outpost_node = next(item for item in snapshot["nodes"] if item["id"] == outpost.id)
    assert outpost_node["overlay_pip"]["layer"] == "outpost_layer"


def test_cli_space_and_outposts_reports_list_sites_missions_and_outpost_progress(tmp_path) -> None:
    state = _space_state()
    _, pending_outpost, pending_project = _build_outpost(state, "outpost_frontier")
    pending_outpost.add_inventory(CargoType.CONSTRUCTION_MATERIALS, 50)
    apply_construction_projects(state)

    _, active_outpost, active_project = _build_outpost(state, "outpost_mining_hub")
    for cargo, units in active_project.required_cargo.items():
        active_outpost.add_inventory(cargo, units)
    apply_construction_projects(state)

    state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_cli",
                "site_id": "site_alpha",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
                "fuel_input": 30,
                "power_input": 15,
            }
        )
    )

    save_path = tmp_path / "space_outposts.json"
    save_simulation(TickSimulation(state=state), save_path)

    output = StringIO()
    result = run_cli(
        ["--load", str(save_path), "--inspect", "--report", "space"],
        output=output,
    )
    text = output.getvalue()

    assert result == 0
    assert "Space Sites" in text
    assert "Mining Missions" in text
    assert "Outposts" in text
    assert "site_alpha" in text
    assert "mission_cli" in text
    assert "reserved_power" in text
    assert pending_outpost.id in text
    assert active_outpost.id in text
    assert "completed (active)" in text
    assert "orbital_yard" in text

    outposts_output = StringIO()
    alias_result = run_cli(
        ["--load", str(save_path), "--inspect", "--report", "outposts"],
        output=outposts_output,
    )
    alias_text = outposts_output.getvalue()

    assert alias_result == 0
    assert "Outposts" in alias_text
    assert "Space Sites" not in alias_text
    assert pending_outpost.id in alias_text
    assert active_outpost.id in alias_text
