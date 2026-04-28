"""Tests for Sprint 16B facility editing commands."""

from __future__ import annotations

import pytest

from gaterail.cargo import CargoType
from gaterail.commands import (
    BuildInternalConnection,
    DemolishFacilityComponent,
    PreviewBuildInternalConnection,
    PreviewDemolishFacilityComponent,
    PreviewRemoveInternalConnection,
    RemoveInternalConnection,
    command_from_dict,
)
from gaterail.facilities import apply_facility_components
from gaterail.models import (
    DevelopmentTier,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FreightSchedule,
    FreightTrain,
    GameState,
    InternalConnection,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    PortDirection,
    WorldState,
)


def _world() -> WorldState:
    return WorldState(
        id="frontier",
        name="Brink Frontier",
        tier=DevelopmentTier.OUTPOST,
        population=10_000,
        stability=0.8,
        power_available=400,
        power_used=40,
    )


def _state() -> GameState:
    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_yard",
            name="Frontier Yard",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={CargoType.ORE: 100},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_smelter",
            name="Frontier Smelter",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            inventory={CargoType.ORE: 4},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_yard_smelter",
            origin="frontier_yard",
            destination="frontier_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    return state


def _loader(component_id: str, rate: int) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.LOADER,
        rate=rate,
    )


def _storage_bay(component_id: str, capacity: int) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.STORAGE_BAY,
        capacity=capacity,
    )


def _factory_with_ore_port() -> FacilityComponent:
    return FacilityComponent(
        id="fab-1",
        kind=FacilityComponentKind.FACTORY_BLOCK,
        inputs={CargoType.ORE: 2},
        outputs={CargoType.PARTS: 1},
        ports={
            "ore_in": FacilityPort(
                id="ore_in",
                direction=PortDirection.INPUT,
                cargo_type=CargoType.ORE,
                rate=2,
            )
        },
    )


def _bay_with_ore_output() -> FacilityComponent:
    return FacilityComponent(
        id="bay-1",
        kind=FacilityComponentKind.STORAGE_BAY,
        capacity=40,
        ports={
            "ore_out": FacilityPort(
                id="ore_out",
                direction=PortDirection.OUTPUT,
                cargo_type=CargoType.ORE,
                rate=2,
            )
        },
    )


def test_command_from_dict_parses_facility_editing_commands() -> None:
    demolish = command_from_dict(
        {
            "type": "PreviewDemolishFacilityComponent",
            "node_id": "frontier_yard",
            "component_id": "loader-fast",
        }
    )
    build_connection = command_from_dict(
        {
            "type": "BuildInternalConnection",
            "node_id": "frontier_smelter",
            "connection_id": "wire-1",
            "source_component_id": "bay-1",
            "source_port_id": "ore_out",
            "destination_component_id": "fab-1",
            "destination_port_id": "ore_in",
        }
    )
    remove_connection = command_from_dict(
        {
            "type": "RemoveInternalConnection",
            "node_id": "frontier_smelter",
            "connection_id": "wire-1",
        }
    )

    assert isinstance(demolish, PreviewDemolishFacilityComponent)
    assert demolish.component_id == "loader-fast"
    assert isinstance(build_connection, BuildInternalConnection)
    assert build_connection.destination_port_id == "ore_in"
    assert isinstance(remove_connection, RemoveInternalConnection)
    assert remove_connection.connection_id == "wire-1"


def test_preview_demolish_facility_component_does_not_mutate_state() -> None:
    state = _state()
    state.nodes["frontier_yard"].facility = Facility(
        components={"loader-fast": _loader("loader-fast", rate=8)}
    )

    result = state.apply_command(
        PreviewDemolishFacilityComponent(
            node_id="frontier_yard",
            component_id="loader-fast",
        )
    )

    assert result["ok"] is True
    assert result["normalized_command"] == {
        "type": "DemolishFacilityComponent",
        "node_id": "frontier_yard",
        "component_id": "loader-fast",
    }
    assert "loader-fast" in state.nodes["frontier_yard"].facility.components


def test_demolish_facility_component_removes_component() -> None:
    state = _state()
    state.nodes["frontier_yard"].facility = Facility(
        components={"loader-fast": _loader("loader-fast", rate=8)}
    )

    result = state.apply_command(
        DemolishFacilityComponent(
            node_id="frontier_yard",
            component_id="loader-fast",
        )
    )

    assert result["ok"] is True
    assert state.nodes["frontier_yard"].facility.components == {}


def test_demolish_component_rejects_orphaned_internal_connection() -> None:
    state = _state()
    state.nodes["frontier_smelter"].facility = Facility(
        components={
            "bay-1": _bay_with_ore_output(),
            "fab-1": _factory_with_ore_port(),
        },
        connections={
            "wire-1": InternalConnection(
                id="wire-1",
                source_component_id="bay-1",
                source_port_id="ore_out",
                destination_component_id="fab-1",
                destination_port_id="ore_in",
            )
        },
    )

    preview = state.apply_command(
        PreviewDemolishFacilityComponent(
            node_id="frontier_smelter",
            component_id="bay-1",
        )
    )

    assert preview["ok"] is False
    assert "remove internal connections first" in preview["message"]
    with pytest.raises(ValueError, match="remove internal connections first"):
        state.apply_command(
            DemolishFacilityComponent(
                node_id="frontier_smelter",
                component_id="bay-1",
            )
        )


def test_demolish_loader_rejects_when_active_schedule_would_exceed_future_rate() -> None:
    state = _state()
    state.nodes["frontier_yard"].facility = Facility(
        components={
            "loader-fast": _loader("loader-fast", rate=8),
            "loader-slow": _loader("loader-slow", rate=3),
        }
    )
    state.add_train(
        FreightTrain(
            id="atlas",
            name="Atlas",
            node_id="frontier_yard",
            capacity=12,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="ore_service",
            train_id="atlas",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            units_per_departure=6,
            interval_ticks=10,
            next_departure_tick=1,
            active=True,
        )
    )

    preview = state.apply_command(
        PreviewDemolishFacilityComponent(
            node_id="frontier_yard",
            component_id="loader-fast",
        )
    )

    assert preview["ok"] is False
    assert "active schedules exceed future rate 3" in preview["message"]
    assert "ore_service" in preview["message"]


def test_demolish_storage_bay_reclamps_future_add_inventory_capacity() -> None:
    state = _state()
    yard = state.nodes["frontier_yard"]
    yard.inventory = {CargoType.ORE: 15}
    yard.facility = Facility(
        components={
            "bay-large": _storage_bay("bay-large", capacity=80),
            "bay-small": _storage_bay("bay-small", capacity=20),
        }
    )

    state.apply_command(
        DemolishFacilityComponent(
            node_id="frontier_yard",
            component_id="bay-large",
        )
    )

    assert yard.effective_storage_capacity() == 20
    assert yard.add_inventory(CargoType.ORE, 10) == 5
    assert yard.stock(CargoType.ORE) == 20


def test_build_internal_connection_validates_and_mutates_facility() -> None:
    state = _state()
    state.nodes["frontier_smelter"].facility = Facility(
        components={
            "bay-1": _bay_with_ore_output(),
            "fab-1": _factory_with_ore_port(),
        }
    )

    preview = state.apply_command(
        PreviewBuildInternalConnection(
            node_id="frontier_smelter",
            connection_id="wire-1",
            source_component_id="bay-1",
            source_port_id="ore_out",
            destination_component_id="fab-1",
            destination_port_id="ore_in",
        )
    )

    assert preview["ok"] is True
    assert state.nodes["frontier_smelter"].facility.connections == {}

    result = state.apply_command(
        BuildInternalConnection(
            node_id="frontier_smelter",
            connection_id="wire-1",
            source_component_id="bay-1",
            source_port_id="ore_out",
            destination_component_id="fab-1",
            destination_port_id="ore_in",
        )
    )

    assert result["ok"] is True
    assert set(state.nodes["frontier_smelter"].facility.connections) == {"wire-1"}


def test_build_internal_connection_rejects_mismatched_port_direction() -> None:
    state = _state()
    state.nodes["frontier_smelter"].facility = Facility(
        components={
            "bay-1": _bay_with_ore_output(),
            "fab-1": _factory_with_ore_port(),
        }
    )

    result = state.apply_command(
        PreviewBuildInternalConnection(
            node_id="frontier_smelter",
            connection_id="wire-1",
            source_component_id="fab-1",
            source_port_id="ore_in",
            destination_component_id="bay-1",
            destination_port_id="ore_out",
        )
    )

    assert result["ok"] is False
    assert "source port must be an output" in result["message"]


def test_removing_connection_blocks_factory_block_with_open_input_port() -> None:
    state = _state()
    smelter = state.nodes["frontier_smelter"]
    smelter.facility = Facility(
        components={
            "bay-1": _bay_with_ore_output(),
            "fab-1": _factory_with_ore_port(),
        },
        connections={
            "wire-1": InternalConnection(
                id="wire-1",
                source_component_id="bay-1",
                source_port_id="ore_out",
                destination_component_id="fab-1",
                destination_port_id="ore_in",
            )
        },
    )

    first = apply_facility_components(state)

    assert first["blocked"] == []
    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 1

    preview = state.apply_command(
        PreviewRemoveInternalConnection(
            node_id="frontier_smelter",
            connection_id="wire-1",
        )
    )
    assert preview["ok"] is True
    assert "wire-1" in smelter.facility.connections

    state.apply_command(
        RemoveInternalConnection(
            node_id="frontier_smelter",
            connection_id="wire-1",
        )
    )
    second = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 1
    assert state.facility_blocked == {"frontier_smelter": ["fab-1"]}
    assert second["blocked"] == [
        {
            "node": "frontier_smelter",
            "component": "fab-1",
            "reason": "open input ports",
            "open_inputs": ["ore_in"],
        }
    ]
