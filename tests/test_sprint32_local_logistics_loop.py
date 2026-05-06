"""Sprint 32: bottom-up local logistics tutorial loop."""

from __future__ import annotations

from pathlib import Path

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.commands import (
    CreateSchedule,
    SetScheduleEnabled,
    command_from_dict,
)
from gaterail.models import (
    ConstructionStatus,
    DevelopmentTier,
    FreightOrder,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    OperationalAreaState,
    OperationalEntityType,
    OperationalPlacedEntity,
    StopAction,
    TrackSignal,
    TrackSignalKind,
    TrainStatus,
    TrainStop,
    TransferLinkKind,
    WaitCondition,
    WorldState,
)
from gaterail.persistence import load_simulation, save_simulation
from gaterail.scenarios import load_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _apply(state, payload: dict[str, object]) -> dict[str, object]:
    result = state.apply_command(command_from_dict(payload))
    assert result["ok"] is True, result
    return result


def _run_until(simulation: TickSimulation, predicate, *, max_ticks: int = 240) -> None:
    for _ in range(max_ticks):
        simulation.run_ticks(1)
        if predicate():
            return
    raise AssertionError("condition was not reached before tick limit")


def _run_next_actions(simulation: TickSimulation, *, max_actions: int = 160) -> dict[str, object]:
    snapshot = render_snapshot(simulation.state)
    for _ in range(max_actions):
        tutorial = snapshot["tutorial"]
        if not tutorial["active"]:
            return snapshot
        action = tutorial["next_action"]
        if action["kind"] == "step_ticks":
            snapshot = handle_bridge_message(
                simulation,
                {"ticks": int(action.get("ticks", 1))},
            )
        elif action["kind"] == "command":
            snapshot = handle_bridge_message(
                simulation,
                {
                    "commands": [action["command"]],
                    "ticks": int(action.get("ticks", 0)),
                },
            )
        elif action["kind"] == "commands":
            snapshot = handle_bridge_message(
                simulation,
                {
                    "commands": action["commands"],
                    "ticks": int(action.get("ticks", 0)),
                },
            )
        else:
            raise AssertionError(f"unsupported tutorial action: {action}")
    raise AssertionError("tutorial did not complete through backend next actions")


def _first_free_operational_cell(area: dict[str, object]) -> tuple[int, int]:
    grid = area["grid"]
    assert isinstance(grid, dict)
    occupied: set[tuple[int, int]] = set()
    for entity in area["entities"]:
        assert isinstance(entity, dict)
        for cell in entity.get("occupied_cells", []):
            assert isinstance(cell, dict)
            occupied.add((int(cell["x"]), int(cell["y"])))
    for y in range(int(grid["height"])):
        for x in range(int(grid["width"])):
            if (x, y) not in occupied:
                return x, y
    raise AssertionError("operational area has no free cells")


def _free_adjacent_cell(state, area_id: str, entity_id: str) -> tuple[int, int, str]:
    render_snapshot(state)
    area = state.operational_areas[area_id]
    anchor = area.entities[entity_id]
    occupied = area.occupied_cells()
    candidates = [
        (anchor.x - 1, anchor.y, "west"),
        (anchor.x + anchor.footprint_size()[0], anchor.y, "east"),
        (anchor.x, anchor.y - 1, "north"),
        (anchor.x, anchor.y + anchor.footprint_size()[1], "south"),
    ]
    for x, y, side in candidates:
        if x < 0 or y < 0 or x >= area.width or y >= area.height:
            continue
        if (x, y, anchor.z) not in occupied:
            return x, y, side
    raise AssertionError(f"no free adjacent cell near {entity_id}")


def _local_rail_signal_state(*, with_signal: bool = True) -> GameState:
    state = GameState()
    state.add_world(
        WorldState(
            id="atlas",
            name="Atlas",
            tier=DevelopmentTier.DEVELOPED_WORLD,
            power_available=100,
        )
    )
    for node_id, name, kind in (
        ("origin_yard", "Origin Yard", NodeKind.DEPOT),
        ("destination_yard", "Destination Yard", NodeKind.WAREHOUSE),
        ("branch_yard", "Branch Yard", NodeKind.WAREHOUSE),
    ):
        state.add_node(
            NetworkNode(
                id=node_id,
                name=name,
                world_id="atlas",
                kind=kind,
                inventory={CargoType.FOOD: 100} if node_id == "origin_yard" else {},
                storage_capacity=1_000,
                transfer_limit_per_tick=100,
            )
        )
    state.add_link(
        NetworkLink(
            id="rail_origin_destination",
            origin="origin_yard",
            destination="destination_yard",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=2,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_origin_branch",
            origin="origin_yard",
            destination="branch_yard",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=2,
        )
    )
    if with_signal:
        state.add_track_signal(
            TrackSignal(
                id="origin_departure_stop",
                link_id="rail_origin_destination",
                kind=TrackSignalKind.STOP,
                node_id="origin_yard",
            )
        )
    state.add_train(FreightTrain(id="train_a", name="Atlas", node_id="origin_yard", capacity=10))
    state.add_train(FreightTrain(id="train_b", name="Boreas", node_id="origin_yard", capacity=10))
    for order_id, train_id, priority in (("order_a", "train_a", 200), ("order_b", "train_b", 100)):
        state.add_order(
            FreightOrder(
                id=order_id,
                train_id=train_id,
                origin="origin_yard",
                destination="destination_yard",
                cargo_type=CargoType.FOOD,
                requested_units=10,
                priority=priority,
            )
        )
    area = OperationalAreaState(id="atlas:local", world_id="atlas", width=24, height=16, cell_size=24)
    area.entities["origin_yard:station"] = OperationalPlacedEntity(
        id="origin_yard:station",
        entity_type=OperationalEntityType.STATION_PLATFORM,
        world_id="atlas",
        x=2,
        y=8,
        width=2,
        height=2,
        owner_node_id="origin_yard",
        input_ports=("rail_in",),
        output_ports=("rail_out",),
    )
    area.entities["destination_yard:station"] = OperationalPlacedEntity(
        id="destination_yard:station",
        entity_type=OperationalEntityType.STATION_PLATFORM,
        world_id="atlas",
        x=14,
        y=8,
        width=2,
        height=2,
        owner_node_id="destination_yard",
        input_ports=("rail_in",),
        output_ports=("rail_out",),
    )
    area.entities["branch_yard:station"] = OperationalPlacedEntity(
        id="branch_yard:station",
        entity_type=OperationalEntityType.STATION_PLATFORM,
        world_id="atlas",
        x=8,
        y=2,
        width=2,
        height=2,
        owner_node_id="branch_yard",
        input_ports=("rail_in",),
        output_ports=("rail_out",),
    )
    area.entities["rail_origin_destination:track"] = OperationalPlacedEntity(
        id="rail_origin_destination:track",
        entity_type=OperationalEntityType.TRACK_SEGMENT,
        world_id="atlas",
        x=4,
        y=9,
        link_id="rail_origin_destination",
        path_cells=((4, 9, 0), (5, 9, 0), (6, 9, 0), (7, 9, 0), (8, 9, 0), (9, 9, 0), (10, 9, 0), (11, 9, 0), (12, 9, 0), (13, 9, 0)),
        input_ports=("origin_yard",),
        output_ports=("destination_yard",),
    )
    area.entities["rail_origin_branch:track"] = OperationalPlacedEntity(
        id="rail_origin_branch:track",
        entity_type=OperationalEntityType.TRACK_SEGMENT,
        world_id="atlas",
        x=4,
        y=7,
        link_id="rail_origin_branch",
        path_cells=((4, 7, 0), (5, 7, 0), (6, 6, 0), (7, 5, 0)),
        input_ports=("origin_yard",),
        output_ports=("branch_yard",),
    )
    state.operational_areas[area.id] = area
    return state


def test_local_logistics_tutorial_loads_with_physical_gaps() -> None:
    state = load_scenario("tutorial_local_logistics")

    assert state.nodes["atlas_local_mine"].requires_facility_handling is True
    assert state.nodes["atlas_local_refinery"].requires_facility_handling is True
    assert state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS] == 40
    assert "rail_atlas_local_mine_refinery" not in state.links
    assert "local_ore_to_refinery" not in state.schedules
    gateworks_components = state.nodes["atlas_gateworks"].facility.components
    assert gateworks_components["gateworks_machinery_fabricator"].outputs == {
        CargoType.MACHINERY: 4
    }
    assert gateworks_components["gateworks_fabricator"].inputs == {
        CargoType.METAL: 10,
        CargoType.MACHINERY: 4,
    }

    tutorial = render_snapshot(state)["tutorial"]
    assert tutorial["id"] == "tutorial_local_logistics"
    assert tutorial["current_step_id"] == "connect_mine_storage"
    assert tutorial["next_action"]["kind"] == "command"
    assert tutorial["next_action"]["command"]["type"] == "local.connect_entities"
    blocker_codes = {item["code"] for item in tutorial["blockers"]}
    assert {
        "transfer_link_missing",
        "track_missing",
        "missing_loader",
        "missing_unloader",
        "route_missing",
        "gate_not_built",
        "destination_not_surveyed",
        "gate_connection_incomplete",
    }.issubset(blocker_codes)


def test_operational_grid_initialises_for_tutorial_local_logistics() -> None:
    state = load_scenario("tutorial_local_logistics")

    snapshot = render_snapshot(state)
    areas = {area["world_id"]: area for area in snapshot["operational_areas"]}
    atlas = areas["atlas"]

    assert "atlas:local" in state.operational_areas
    assert atlas["grid"]["kind"] == "local_grid"
    assert atlas["grid"]["has_cell_occupancy"] is True
    assert atlas["grid"]["width"] >= 1
    assert atlas["grid"]["height"] >= 1
    assert atlas["entities"]
    assert all("cell" in entity for entity in atlas["entities"])
    assert all("occupied_cells" in entity for entity in atlas["entities"])
    assert all("entity_type" in entity for entity in atlas["entities"])


def test_local_list_build_options_returns_expected_entities() -> None:
    state = load_scenario("tutorial_local_logistics")

    result = state.apply_command(
        command_from_dict(
            {
                "type": "local.list_build_options",
                "operational_area_id": "atlas:local",
            }
        )
    )

    assert result["ok"] is True
    entity_types = {option["entity_type"] for option in result["build_options"]}
    assert {
        "extractor",
        "track_segment",
        "station_platform",
        "loader",
        "unloader",
        "hopper",
        "storage",
        "transfer_link",
        "refinery",
        "factory",
        "railgate_terminal",
    }.issubset(entity_types)


def test_local_place_entity_validates_occupancy_and_consumes_costs() -> None:
    state = load_scenario("tutorial_local_logistics")
    area = render_snapshot(state)["operational_areas"][0]
    if area["world_id"] != "atlas":
        area = next(item for item in render_snapshot(state)["operational_areas"] if item["world_id"] == "atlas")
    x, y = _first_free_operational_cell(area)
    start_cash = state.finance.cash
    start_parts = state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS]

    result = state.apply_command(
        command_from_dict(
            {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "entity_id": "mine_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": x,
                "y": y,
                "rotation": 0,
                "rate": 20,
                "power_required": 4,
                "construction_cargo": {"construction_materials": 4},
            }
        )
    )

    assert result["ok"] is True, result
    assert state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS] == start_parts - 4
    assert state.finance.cash < start_cash
    assert "mine_loader" in state.nodes["atlas_local_mine"].facility.components

    outside = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_id": "outside_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": -1,
                "y": y,
            }
        )
    )
    assert outside["ok"] is False
    assert outside["reason"] == "outside_grid"

    overlap = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_id": "overlap_unloader",
                "entity_type": "unloader",
                "owner_node_id": "atlas_local_mine",
                "x": x,
                "y": y,
            }
        )
    )
    assert overlap["ok"] is False
    assert overlap["reason"] == "occupied_cells"


def test_local_track_validation_normalized_command_can_be_committed() -> None:
    state = load_scenario("tutorial_local_logistics")

    result = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_preview_commit",
                "origin_node_id": "atlas_local_mine",
                "destination_node_id": "atlas_local_refinery",
                "x": 18,
                "y": 13,
                "rotation": 90,
            }
        )
    )

    assert result["ok"] is True, result
    normalized = result["normalized_command"]
    assert normalized["type"] == "local.place_entity"
    assert normalized["origin_node_id"] == "atlas_local_mine"
    assert normalized["destination_node_id"] == "atlas_local_refinery"

    placed = state.apply_command(command_from_dict(normalized))

    assert placed["ok"] is True, placed
    assert "rail_preview_commit" in state.links
    assert "rail_preview_commit:track" in state.operational_areas["atlas:local"].entities


def test_local_track_path_cells_are_validated_persisted_and_snapshotted(tmp_path) -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state
    render_snapshot(state)
    area = state.operational_areas["atlas:local"]
    y = area.height - 2
    path_cells = [{"x": 8, "y": y}, {"x": 9, "y": y}, {"x": 10, "y": y}]

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_path_preview",
                "origin_node_id": "atlas_local_mine",
                "destination_node_id": "atlas_local_refinery",
                "x": 8,
                "y": y,
                "rotation": 0,
                "path_cells": path_cells,
            }
        )
    )

    assert preview["ok"] is True, preview
    assert preview["entity"]["path_cells"] == [{"x": 8, "y": y, "z": 0}, {"x": 9, "y": y, "z": 0}, {"x": 10, "y": y, "z": 0}]
    normalized = preview["normalized_command"]
    assert normalized["path_cells"] == path_cells

    placed = state.apply_command(command_from_dict(normalized))

    assert placed["ok"] is True, placed
    entity = state.operational_areas["atlas:local"].entities["rail_path_preview:track"]
    assert entity.path_cells == ((8, y, 0), (9, y, 0), (10, y, 0))
    assert entity.occupied_cells() == entity.path_cells

    overlap = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_path_overlap",
                "origin_node_id": "atlas_local_mine",
                "destination_node_id": "atlas_local_refinery",
                "x": 9,
                "y": y,
                "path_cells": [{"x": 9, "y": y}, {"x": 11, "y": y}],
            }
        )
    )
    assert overlap["ok"] is False
    assert overlap["reason"] == "occupied_cells"
    assert overlap["occupied_cells"][0]["entity_id"] == "rail_path_preview:track"

    save_path = tmp_path / "track_path_cells.json"
    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)
    assert loaded.state.operational_areas["atlas:local"].entities["rail_path_preview:track"].path_cells == entity.path_cells


def test_local_platform_side_and_port_adjacency_preview_contract() -> None:
    state = load_scenario("tutorial_local_logistics")
    x, y, side = _free_adjacent_cell(state, "atlas:local", "atlas_local_mine:station")

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_id": "adjacent_mine_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": x,
                "y": y,
                "platform_side": side,
                "adjacent_to_entity_id": "atlas_local_mine:station",
                "adjacent_port_id": "rail_out",
                "construction_cargo": {"construction_materials": 4},
            }
        )
    )

    assert preview["ok"] is True, preview
    entity = preview["entity"]
    assert entity["platform_side"] == side
    assert entity["adjacency"] == {
        "entity_id": "atlas_local_mine:station",
        "port_id": "rail_out",
        "side": side,
    }
    assert preview["normalized_command"]["platform_side"] == side
    assert preview["normalized_command"]["adjacent_to_entity_id"] == "atlas_local_mine:station"

    not_adjacent = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_id": "distant_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": state.operational_areas["atlas:local"].width - 1,
                "y": state.operational_areas["atlas:local"].height - 1,
                "platform_side": side,
                "adjacent_to_entity_id": "atlas_local_mine:station",
                "adjacent_port_id": "rail_out",
                "construction_cargo": {"construction_materials": 4},
            }
        )
    )
    assert not_adjacent["ok"] is False
    assert not_adjacent["reason"] == "not_port_adjacent"

    invalid_side = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_placement",
                "operational_area_id": "atlas:local",
                "entity_id": "bad_side_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": x,
                "y": y,
                "platform_side": "upstage",
                "adjacent_to_entity_id": "atlas_local_mine:station",
                "construction_cargo": {"construction_materials": 4},
            }
        )
    )
    assert invalid_side["ok"] is False
    assert invalid_side["reason"] == "invalid_platform_side"


def test_specialized_transfer_link_profiles_are_backend_authoritative() -> None:
    state = load_scenario("tutorial_local_logistics")

    options = state.apply_command(
        command_from_dict(
            {
                "type": "local.list_build_options",
                "operational_area_id": "atlas:local",
            }
        )
    )

    profiles = {item["link_type"]: item for item in options["transfer_link_profiles"]}
    assert profiles["hopper"]["cargo_classes"] == ["bulk"]
    assert profiles["pipe"]["cargo_classes"] == ["fluid"]
    assert profiles["conveyor"]["cargo_classes"] == ["general"]

    pipe_ore = state.apply_command(
        command_from_dict(
            {
                "type": "local.connect_entities",
                "operational_area_id": "atlas:local",
                "owner_node_id": "atlas_local_mine",
                "connection_id": "pipe_should_reject_ore",
                "source_component_id": "mine_head",
                "source_port_id": "ore_out",
                "destination_component_id": "mine_storage",
                "destination_port_id": "ore_in",
                "link_type": "pipe",
            }
        )
    )
    assert pipe_ore["ok"] is False
    assert pipe_ore["reason"] == "invalid_connection"
    assert "pipe cannot move ore" in pipe_ore["message"]

    hopper_ore = state.apply_command(
        command_from_dict(
            {
                "type": "local.connect_entities",
                "operational_area_id": "atlas:local",
                "owner_node_id": "atlas_local_mine",
                "connection_id": "hopper_can_move_ore",
                "source_component_id": "mine_head",
                "source_port_id": "ore_out",
                "destination_component_id": "mine_storage",
                "destination_port_id": "ore_in",
                "link_type": "hopper",
            }
        )
    )

    assert hopper_ore["ok"] is True, hopper_ore
    assert hopper_ore["transfer_profile"]["link_type"] == "hopper"
    assert hopper_ore["transfer_profile"]["cargo_classes"] == ["bulk"]
    assert hopper_ore["entity"]["link_type"] == "hopper"


def test_local_rail_diagnostics_use_path_cells_signals_and_reservations() -> None:
    simulation = TickSimulation(state=_local_rail_signal_state())

    report = simulation.step_tick()
    snapshot = render_snapshot(simulation.state)

    assert report["signals"]["blocked"][0]["train_id"] == "train_b"
    local_rail = snapshot["local_rail"]
    rail_link = local_rail["links"]["rail_origin_destination"]
    assert rail_link["operational_area_id"] == "atlas:local"
    assert rail_link["entity_id"] == "rail_origin_destination:track"
    assert rail_link["path_cells"][0] == {"x": 4, "y": 9, "z": 0}
    assert rail_link["path_cells"][-1] == {"x": 13, "y": 9, "z": 0}
    assert rail_link["signal_ids"] == ["origin_departure_stop"]
    assert rail_link["block"]["signal_ids"] == ["origin_departure_stop"]
    assert rail_link["block"]["reserved_by"] == "train_a"
    assert rail_link["block"]["occupiers"] == ["train_a"]
    assert rail_link["trains"] == ["train_a"]
    assert rail_link["blocked_events"] == report["signals"]["blocked"]

    atlas = next(area for area in snapshot["operational_areas"] if area["id"] == "atlas:local")
    track_entity = next(entity for entity in atlas["entities"] if entity["id"] == "rail_origin_destination:track")
    assert track_entity["rail_diagnostics"]["block"]["reserved_by"] == "train_a"
    assert track_entity["rail_diagnostics"]["blocked_events"][0]["train_id"] == "train_b"


def test_local_rail_switch_diagnostics_are_abstract_backend_state() -> None:
    snapshot = render_snapshot(_local_rail_signal_state())

    switches = snapshot["local_rail"]["switches"]
    origin_switch = next(item for item in switches if item["node_id"] == "origin_yard")
    assert origin_switch["kind"] == "station_throat"
    assert origin_switch["operational_area_id"] == "atlas:local"
    assert origin_switch["link_ids"] == ["rail_origin_branch", "rail_origin_destination"]
    assert origin_switch["path_entity_ids"] == ["rail_origin_branch:track", "rail_origin_destination:track"]


def test_local_track_signal_tooling_places_real_backend_signal() -> None:
    state = _local_rail_signal_state(with_signal=False)

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_signal",
                "operational_area_id": "atlas:local",
                "track_entity_id": "rail_origin_destination:track",
                "signal_id": "origin_departure_stop",
                "kind": "stop",
            }
        )
    )

    assert preview["ok"] is True, preview
    assert preview["normalized_command"] == {
        "type": "local.place_signal",
        "operational_area_id": "atlas:local",
        "track_entity_id": "rail_origin_destination:track",
        "signal_id": "origin_departure_stop",
        "kind": "stop",
        "node_id": "origin_yard",
        "active": True,
    }
    assert preview["track_signal_command"] == {
        "type": "BuildTrackSignal",
        "signal_id": "origin_departure_stop",
        "link_id": "rail_origin_destination",
        "kind": "stop",
        "node_id": "origin_yard",
        "active": True,
    }

    placed = state.apply_command(command_from_dict(preview["normalized_command"]))

    assert placed["ok"] is True, placed
    assert state.track_signals["origin_departure_stop"].link_id == "rail_origin_destination"
    assert placed["entity"]["rail_diagnostics"]["signal_ids"] == ["origin_departure_stop"]
    snapshot = render_snapshot(state)
    assert snapshot["local_rail"]["links"]["rail_origin_destination"]["signal_ids"] == ["origin_departure_stop"]


def test_local_signal_tooling_rejects_non_track_entities_and_duplicate_ids() -> None:
    state = _local_rail_signal_state()

    non_track = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_signal",
                "operational_area_id": "atlas:local",
                "track_entity_id": "origin_yard:station",
                "signal_id": "station_signal",
            }
        )
    )
    duplicate = state.apply_command(
        command_from_dict(
            {
                "type": "local.validate_signal",
                "operational_area_id": "atlas:local",
                "track_entity_id": "rail_origin_destination:track",
                "signal_id": "origin_departure_stop",
            }
        )
    )

    assert non_track["ok"] is False
    assert non_track["reason"] == "not_track_entity"
    assert duplicate["ok"] is False
    assert duplicate["reason"] == "duplicate_track_signal_id"


def test_local_switch_route_control_persists_to_snapshot_and_save_load(tmp_path) -> None:
    simulation = TickSimulation(state=_local_rail_signal_state())
    simulation.step_tick()

    result = simulation.state.apply_command(
        command_from_dict(
            {
                "type": "local.set_switch_route",
                "operational_area_id": "atlas:local",
                "node_id": "origin_yard",
                "selected_link_id": "rail_origin_destination",
            }
        )
    )

    assert result["ok"] is True, result
    assert result["switch"]["selected_link_id"] == "rail_origin_destination"
    assert result["switch"]["selected_path_entity_id"] == "rail_origin_destination:track"
    assert result["switch"]["selected_route"]["reserved_by"] == "train_a"
    assert result["switch"]["selected_route"]["signal_ids"] == ["origin_departure_stop"]
    snapshot = render_snapshot(simulation.state)
    origin_switch = next(item for item in snapshot["local_rail"]["switches"] if item["node_id"] == "origin_yard")
    assert origin_switch["selected_link_id"] == "rail_origin_destination"
    assert origin_switch["selected_route"]["reserved_by"] == "train_a"

    save_path = tmp_path / "local_switch_route.json"
    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)
    loaded_switch = next(item for item in render_snapshot(loaded.state)["local_rail"]["switches"] if item["node_id"] == "origin_yard")

    assert loaded.state.local_switch_routes["atlas:local:origin_yard:switch"] == "rail_origin_destination"
    assert loaded_switch["selected_link_id"] == "rail_origin_destination"


def test_local_switch_route_control_rejects_links_outside_switch() -> None:
    state = _local_rail_signal_state()

    result = state.apply_command(
        command_from_dict(
            {
                "type": "local.set_switch_route",
                "operational_area_id": "atlas:local",
                "node_id": "origin_yard",
                "selected_link_id": "missing_link",
            }
        )
    )

    assert result["ok"] is False
    assert result["reason"] == "invalid_switch_route"


def test_local_rotate_delete_and_save_load_preserve_operational_grid(tmp_path) -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state
    atlas = next(area for area in render_snapshot(state)["operational_areas"] if area["world_id"] == "atlas")
    x, y = _first_free_operational_cell(atlas)

    _apply(
        state,
        {
            "type": "local.place_entity",
            "operational_area_id": "atlas:local",
            "entity_id": "mine_loader",
            "entity_type": "loader",
            "owner_node_id": "atlas_local_mine",
            "x": x,
            "y": y,
            "construction_cargo": {"construction_materials": 4},
        },
    )
    _apply(
        state,
        {
            "type": "local.rotate_entity",
            "operational_area_id": "atlas:local",
            "entity_id": "mine_loader",
            "rotation": 90,
        },
    )

    assert state.operational_areas["atlas:local"].entities["mine_loader"].rotation == 90

    save_path = tmp_path / "local_grid.json"
    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)
    loaded_area = loaded.state.operational_areas["atlas:local"]
    assert loaded_area.entities["mine_loader"].x == x
    assert loaded_area.entities["mine_loader"].rotation == 90

    delete = loaded.state.apply_command(
        command_from_dict(
            {
                "type": "local.delete_entity",
                "operational_area_id": "atlas:local",
                "entity_id": "mine_loader",
            }
        )
    )
    assert delete["ok"] is True
    assert "mine_loader" not in loaded.state.operational_areas["atlas:local"].entities
    assert "mine_loader" not in loaded.state.nodes["atlas_local_mine"].facility.components


def test_local_connect_entities_moves_cargo_only_after_transfer_link_exists() -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state

    simulation.run_ticks(2)
    assert state.nodes["atlas_local_mine"].stock(CargoType.ORE) == 0
    assert "wire_mine_head_to_storage" not in state.nodes["atlas_local_mine"].facility.connections

    atlas = next(area for area in render_snapshot(state)["operational_areas"] if area["world_id"] == "atlas")
    x, y = _first_free_operational_cell(atlas)
    _apply(
        state,
        {
            "type": "local.connect_entities",
            "operational_area_id": "atlas:local",
            "connection_id": "wire_mine_head_to_storage",
            "owner_node_id": "atlas_local_mine",
            "source_component_id": "mine_head",
            "source_port_id": "ore_out",
            "destination_component_id": "mine_storage",
            "destination_port_id": "ore_in",
            "link_type": "conveyor",
            "x": x,
            "y": y,
        },
    )
    simulation.run_ticks(2)

    assert state.nodes["atlas_local_mine"].stock(CargoType.ORE) > 0
    assert "wire_mine_head_to_storage" in state.nodes["atlas_local_mine"].facility.connections


def test_local_facility_build_consumes_starter_construction_parts() -> None:
    state = load_scenario("tutorial_local_logistics")
    start_parts = state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS]
    start_cash = state.finance.cash

    _apply(
        state,
        {
            "type": "BuildFacilityComponent",
            "component_id": "mine_loader",
            "node_id": "atlas_local_mine",
            "kind": "loader",
            "rate": 20,
            "power_required": 4,
            "construction_cargo": {"construction_materials": 4},
        },
    )

    assert state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS] == start_parts - 4
    assert state.finance.cash < start_cash
    snapshot = render_snapshot(state)
    assert snapshot["construction_inventory"]["construction_materials"] == start_parts - 4


def test_insufficient_construction_parts_blocks_local_facility_build() -> None:
    state = load_scenario("tutorial_local_logistics")
    state.construction_inventory = {}

    result = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewBuildFacilityComponent",
                "component_id": "mine_loader",
                "node_id": "atlas_local_mine",
                "kind": "loader",
                "rate": 20,
                "power_required": 4,
                "construction_cargo": {"construction_materials": 4},
            }
        )
    )

    assert result["ok"] is False
    assert "insufficient construction parts" in result["message"]
    assert result["reason"] == result["message"]


def test_strict_local_station_needs_loader_before_train_can_load() -> None:
    state = load_scenario("tutorial_local_logistics")
    _apply(
        state,
        {
            "type": "BuildInternalConnection",
            "node_id": "atlas_local_mine",
            "connection_id": "wire_mine_head_to_storage",
            "source_component_id": "mine_head",
            "source_port_id": "ore_out",
            "destination_component_id": "mine_storage",
            "destination_port_id": "ore_in",
        },
    )
    _apply(
        state,
        {
            "type": "BuildLink",
            "link_id": "rail_atlas_local_mine_refinery",
            "origin": "atlas_local_mine",
            "destination": "atlas_local_refinery",
            "mode": "rail",
            "travel_ticks": 1,
            "capacity_per_tick": 12,
        },
    )
    state.apply_command(
        CreateSchedule(
            schedule_id="local_ore_to_refinery",
            train_id="local_ore_runner",
            origin="atlas_local_mine",
            destination="atlas_local_refinery",
            cargo_type=CargoType.ORE,
            units_per_departure=20,
            interval_ticks=6,
            train_stops=(
                TrainStop(
                    node_id="atlas_local_mine",
                    action=StopAction.PICKUP,
                    cargo_type=CargoType.ORE,
                    units=20,
                    wait_condition=WaitCondition.FULL,
                ),
                TrainStop(
                    node_id="atlas_local_refinery",
                    action=StopAction.DELIVERY,
                    cargo_type=CargoType.ORE,
                    units=20,
                    wait_condition=WaitCondition.EMPTY,
                ),
            ),
        )
    )

    simulation = TickSimulation(state=state)
    simulation.run_ticks(3)

    train = state.trains["local_ore_runner"]
    assert train.status == TrainStatus.BLOCKED
    assert train.blocked_reason == "missing_loader"
    assert state.schedules["local_ore_to_refinery"].delivered_units == 0
    blockers = {item["code"] for item in render_snapshot(state)["tutorial"]["blockers"]}
    assert "missing_loader" in blockers


def test_local_next_actions_build_connect_automate_and_scale_to_sable() -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state

    final_snapshot = _run_next_actions(simulation)

    assert final_snapshot["tutorial"]["active"] is False
    assert state.schedules["local_ore_to_refinery"].delivered_units >= 20
    assert state.schedules["local_metal_to_gateworks"].delivered_units >= 20
    assert state.schedules["local_components_to_gate"].delivered_units >= 4
    assert (
        state.construction_projects["proj_atlas_local_outbound_gate"].status
        == ConstructionStatus.COMPLETED
    )
    assert state.links["gate_atlas_local_sable"].mode.value == "gate"
    assert state.space_sites["site_sable_reach"].discovered is True
    assert state.nodes["sable_settlement"].stock(CargoType.CONSTRUCTION_MATERIALS) >= 40
    assert state.contracts["local_sable_starter_cargo"].status.value == "fulfilled"


def test_local_logistics_snapshot_exposes_contract_for_godot() -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    snapshot = render_snapshot(simulation.state)
    nodes = {node["id"]: node for node in snapshot["nodes"]}

    mine = nodes["atlas_local_mine"]
    assert mine["requires_facility_handling"] is True
    assert mine["facility"]["components"]
    assert mine["facility"]["connections"] == []
    assert mine["loader_summary"]["effective_loader_rate"] == 0

    loop = snapshot["vertical_loop"]
    assert loop["id"] == "tutorial_local_logistics"
    assert loop["current_step_id"] == "connect_mine_storage"
    assert any(item["code"] == "transfer_link_missing" for item in loop["diagnostics"])
    assert any(flow["schedule_id"].startswith("local_") for flow in snapshot["cargo_flows"]) is False


def test_operational_area_snapshot_exposes_backend_local_entities() -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    snapshot = render_snapshot(simulation.state)

    areas = {area["world_id"]: area for area in snapshot["operational_areas"]}
    atlas = areas["atlas"]
    assert atlas["grid"]["kind"] == "local_grid"
    assert atlas["grid"]["cell_size"] == 24
    assert atlas["grid"]["has_cell_occupancy"] is True
    assert atlas["grid"]["width"] > 0
    assert atlas["grid"]["height"] > 0

    entities = atlas["entities"]
    kinds = {entity["kind"] for entity in entities}
    entity_types = {entity["entity_type"] for entity in entities}
    assert {
        "extractor",
        "rail_track",
        "station_platform",
        "loader",
        "unloader",
        "hopper",
        "warehouse",
        "transfer_link",
        "refinery",
        "factory",
        "railgate_terminal",
    }.issubset(kinds)
    assert "track_segment" in entity_types

    gateworks_transfer_links = [
        entity
        for entity in entities
        if entity["kind"] == "transfer_link"
        and entity.get("owner_node_id") == "atlas_gateworks"
    ]
    assert gateworks_transfer_links
    assert {entity["link_type"] for entity in gateworks_transfer_links} == {"conveyor"}
    assert all("position" in entity for entity in entities)
    assert all("cell" in entity for entity in entities)
    assert all("occupied_cells" in entity for entity in entities)
    assert all("blocked_reasons" in entity for entity in entities)


def test_transfer_link_type_is_backend_state_and_persists(tmp_path) -> None:
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state

    _apply(
        state,
        {
            "type": "BuildInternalConnection",
            "node_id": "atlas_local_mine",
            "connection_id": "wire_mine_head_to_storage",
            "source_component_id": "mine_head",
            "source_port_id": "ore_out",
            "destination_component_id": "mine_storage",
            "destination_port_id": "ore_in",
            "link_type": "conveyor",
        },
    )

    connection = state.nodes["atlas_local_mine"].facility.connections["wire_mine_head_to_storage"]
    assert connection.link_type == TransferLinkKind.CONVEYOR

    snapshot = render_snapshot(state)
    nodes = {node["id"]: node for node in snapshot["nodes"]}
    assert nodes["atlas_local_mine"]["facility"]["connections"][0]["link_type"] == "conveyor"

    save_path = tmp_path / "transfer_link.json"
    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)
    loaded_connection = (
        loaded.state.nodes["atlas_local_mine"].facility.connections["wire_mine_head_to_storage"]
    )
    assert loaded_connection.link_type == TransferLinkKind.CONVEYOR


def test_local_tutorial_save_load_preserves_facilities_routes_and_gate_state(tmp_path) -> None:
    save_path = tmp_path / "local_tutorial.json"
    simulation = TickSimulation.from_scenario("tutorial_local_logistics")
    state = simulation.state

    # Drive the first half far enough to have facility wiring, schedules, and train state.
    for _ in range(8):
        tutorial = render_snapshot(state)["tutorial"]
        action = tutorial["next_action"]
        if action["kind"] == "step_ticks":
            simulation.run_ticks(int(action.get("ticks", 1)))
        elif action["kind"] == "command":
            _apply(state, action["command"])
            simulation.run_ticks(int(action.get("ticks", 0)))
        elif action["kind"] == "commands":
            for command in action["commands"]:
                _apply(state, command)
            simulation.run_ticks(int(action.get("ticks", 0)))

    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)
    loaded_state = loaded.state

    assert loaded_state.nodes["atlas_local_mine"].requires_facility_handling is True
    assert "wire_mine_head_to_storage" in loaded_state.nodes["atlas_local_mine"].facility.connections
    assert "local_ore_to_refinery" in loaded_state.schedules
    assert "rail_atlas_local_mine_refinery" in loaded_state.links
    assert "local_ore_runner" in loaded_state.trains
    assert loaded_state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS] < 40
    loaded_snapshot = render_snapshot(loaded_state)
    assert loaded_snapshot["tutorial"]["id"] == "tutorial_local_logistics"
    assert (
        loaded_snapshot["construction_inventory"]["construction_materials"]
        == loaded_state.construction_inventory[CargoType.CONSTRUCTION_MATERIALS]
    )
    loaded_areas = {area["world_id"]: area for area in loaded_snapshot["operational_areas"]}
    assert loaded_areas["atlas"]["entities"]


def test_bridge_can_complete_local_logistics_tutorial_from_next_actions() -> None:
    simulation = TickSimulation.from_scenario("sprint8")
    snapshot = handle_bridge_message(
        simulation,
        {"scenario": "tutorial_local_logistics", "ticks": 0},
    )
    assert snapshot["tutorial"]["id"] == "tutorial_local_logistics"

    final_snapshot = _run_next_actions(simulation)

    assert final_snapshot["tutorial"]["active"] is False
    assert simulation.state.contracts["local_sable_starter_cargo"].status.value == "fulfilled"


def test_godot_local_region_exposes_backend_tutorial_action_control() -> None:
    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert "func _add_tutorial_action_controls" in script
    assert '_latest_snapshot.get("tutorial"' in script
    assert 'GateRailBridge.send_message({"commands": commands' in script
    assert '"BuildFacilityComponent"' in script
    assert 'snapshot.get("operational_areas"' in script
    assert "_world_operational_entities" in script
    assert "_draw_operational_entities" in script
    assert '"local.place_entity"' in script
    assert '"local.connect_entities"' in script
