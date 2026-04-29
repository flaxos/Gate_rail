"""Tests for Sprint 21D internal facility wiring flow."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.facilities import apply_facility_components
from gaterail.models import (
    DevelopmentTier,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    GameState,
    InternalConnection,
    NetworkNode,
    NodeKind,
    PortDirection,
    WorldState,
)
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.snapshot import render_snapshot


def _state() -> GameState:
    state = GameState()
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=10_000,
            stability=0.8,
            power_available=400,
            power_used=40,
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
    return state


def _bay_output() -> FacilityComponent:
    return FacilityComponent(
        id="bay-1",
        kind=FacilityComponentKind.STORAGE_BAY,
        capacity=80,
        ports={
            "ore_out": FacilityPort(
                id="ore_out",
                direction=PortDirection.OUTPUT,
                cargo_type=CargoType.ORE,
                rate=2,
            )
        },
    )


def _factory_input_output() -> FacilityComponent:
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
            ),
            "parts_out": FacilityPort(
                id="parts_out",
                direction=PortDirection.OUTPUT,
                cargo_type=CargoType.PARTS,
                rate=1,
            ),
        },
    )


def test_connection_moves_cargo_into_factory_input_port_before_processing() -> None:
    state = _state()
    smelter = state.nodes["frontier_smelter"]
    smelter.facility = Facility(
        components={
            "bay-1": _bay_output(),
            "fab-1": FacilityComponent(
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
            ),
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

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 1
    assert result["connection_transfers"] == [
        {
            "node": "frontier_smelter",
            "connection": "wire-1",
            "source_component": "bay-1",
            "source_port": "ore_out",
            "destination_component": "fab-1",
            "destination_port": "ore_in",
            "cargo": "ore",
            "units": 2,
        }
    ]
    assert smelter.facility.components["fab-1"].port_inventory == {}


def test_factory_output_port_can_wire_into_storage_input_same_tick() -> None:
    state = _state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 2}
    smelter.facility = Facility(
        components={
            "fab-1": _factory_input_output(),
            "bay-1": FacilityComponent(
                id="bay-1",
                kind=FacilityComponentKind.STORAGE_BAY,
                capacity=80,
                ports={
                    "parts_in": FacilityPort(
                        id="parts_in",
                        direction=PortDirection.INPUT,
                        cargo_type=CargoType.PARTS,
                        rate=1,
                    )
                },
            ),
        },
        connections={
            "wire-ore": InternalConnection(
                id="wire-ore",
                source_component_id="bay-1",
                source_port_id="parts_in",
                destination_component_id="fab-1",
                destination_port_id="ore_in",
            ),
            "wire-parts": InternalConnection(
                id="wire-parts",
                source_component_id="fab-1",
                source_port_id="parts_out",
                destination_component_id="bay-1",
                destination_port_id="parts_in",
            ),
        },
    )
    smelter.facility.connections.pop("wire-ore")

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 0
    assert result["blocked"] == [
        {
            "node": "frontier_smelter",
            "component": "fab-1",
            "reason": "open input ports",
            "open_inputs": ["ore_in"],
        }
    ]

    smelter.facility.connections["wire-ore"] = InternalConnection(
        id="wire-ore",
        source_component_id="bay-1",
        source_port_id="parts_in",
        destination_component_id="fab-1",
        destination_port_id="ore_in",
    )
    smelter.facility.components["bay-1"].ports["ore_out"] = FacilityPort(
        id="ore_out",
        direction=PortDirection.OUTPUT,
        cargo_type=CargoType.ORE,
        rate=2,
    )
    smelter.facility.connections["wire-ore"] = InternalConnection(
        id="wire-ore",
        source_component_id="bay-1",
        source_port_id="ore_out",
        destination_component_id="fab-1",
        destination_port_id="ore_in",
    )

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 0
    assert smelter.stock(CargoType.PARTS) == 1
    assert [event["connection"] for event in result["connection_transfers"]] == [
        "wire-ore",
        "wire-parts",
    ]


def test_full_output_port_blocks_factory_without_consuming_inputs() -> None:
    state = _state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 2}
    smelter.facility = Facility(
        components={
            "fab-1": FacilityComponent(
                id="fab-1",
                kind=FacilityComponentKind.FACTORY_BLOCK,
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 1},
                ports={
                    "parts_out": FacilityPort(
                        id="parts_out",
                        direction=PortDirection.OUTPUT,
                        cargo_type=CargoType.PARTS,
                        rate=1,
                        capacity=1,
                    )
                },
                port_inventory={"parts_out": {CargoType.PARTS: 1}},
            )
        }
    )

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 0
    assert result["blocked"] == [
        {
            "node": "frontier_smelter",
            "component": "fab-1",
            "reason": "output ports full",
            "missing_capacity": {"parts": 1},
        }
    ]
    assert state.facility_blocked == {"frontier_smelter": ["fab-1"]}


def test_port_inventory_round_trips_and_snapshots() -> None:
    state = _state()
    smelter = state.nodes["frontier_smelter"]
    smelter.facility = Facility(
        components={
            "fab-1": FacilityComponent(
                id="fab-1",
                kind=FacilityComponentKind.FACTORY_BLOCK,
                ports={
                    "parts_out": FacilityPort(
                        id="parts_out",
                        direction=PortDirection.OUTPUT,
                        cargo_type=CargoType.PARTS,
                        rate=2,
                    )
                },
                port_inventory={"parts_out": {CargoType.PARTS: 2}},
            )
        }
    )

    restored = state_from_dict(state_to_dict(state))
    restored_component = restored.nodes["frontier_smelter"].facility.components["fab-1"]

    assert restored_component.port_inventory == {"parts_out": {CargoType.PARTS: 2}}
    snapshot = render_snapshot(restored)
    node_payload = {node["id"]: node for node in snapshot["nodes"]}["frontier_smelter"]
    component_payload = node_payload["facility"]["components"][0]
    assert component_payload["ports"][0]["inventory"] == {"parts": 2}
