"""Tests for Sprint 16A facility-layer foundation."""

from __future__ import annotations

import pytest

from gaterail.cargo import CargoType
from gaterail.commands import (
    BuildFacilityComponent,
    PreviewBuildFacilityComponent,
    command_from_dict,
)
from gaterail.construction import facility_component_build_cost
from gaterail.facilities import apply_facility_components, facility_summary
from gaterail.freight import advance_freight
from gaterail.models import (
    DevelopmentTier,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FreightOrder,
    FreightTrain,
    GameState,
    InternalConnection,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    PortDirection,
    TrainStatus,
    WorldState,
)
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


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


def _two_node_state() -> GameState:
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


def _loader(component_id: str = "loader-1", rate: int = 4) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.LOADER,
        rate=rate,
    )


def _unloader(component_id: str = "unloader-1", rate: int = 3) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.UNLOADER,
        rate=rate,
    )


def _storage_bay(component_id: str = "bay-1", capacity: int = 100) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.STORAGE_BAY,
        capacity=capacity,
    )


def _factory_block(
    component_id: str = "fab-1",
    inputs: dict[CargoType, int] | None = None,
    outputs: dict[CargoType, int] | None = None,
) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=FacilityComponentKind.FACTORY_BLOCK,
        inputs=dict(inputs or {}),
        outputs=dict(outputs or {}),
    )


# -- Effective-rate plumbing -------------------------------------------------


def test_loader_rate_caps_train_load_per_tick() -> None:
    """A LOADER rate=4 caps how many units a 20-cap train can pick up this tick."""

    state = _two_node_state()
    state.nodes["frontier_yard"].facility = Facility(
        components={"loader-1": _loader(rate=4)}
    )
    state.add_train(
        FreightTrain(
            id="atlas",
            name="Atlas",
            node_id="frontier_yard",
            capacity=20,
        )
    )
    state.add_order(
        FreightOrder(
            id="ore_run",
            train_id="atlas",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            requested_units=20,
        )
    )

    advance_freight(state)

    train = state.trains["atlas"]
    assert train.status == TrainStatus.IN_TRANSIT
    assert train.cargo_units == 4
    assert state.nodes["frontier_yard"].stock(CargoType.ORE) == 96


def test_unloader_rate_caps_train_unload_per_tick() -> None:
    """An UNLOADER rate=3 leaves a partially-loaded train BLOCKED at the destination."""

    state = _two_node_state()
    state.nodes["frontier_smelter"].facility = Facility(
        components={"unloader-1": _unloader(rate=3)}
    )
    state.add_train(
        FreightTrain(
            id="atlas",
            name="Atlas",
            node_id="frontier_smelter",
            capacity=10,
            cargo_type=CargoType.ORE,
            cargo_units=10,
            status=TrainStatus.IN_TRANSIT,
            destination="frontier_smelter",
            remaining_ticks=1,
        )
    )

    advance_freight(state)

    train = state.trains["atlas"]
    assert state.nodes["frontier_smelter"].stock(CargoType.ORE) == 3
    assert train.cargo_units == 7
    assert train.status == TrainStatus.BLOCKED
    assert "unload limit" in (train.blocked_reason or "")


def test_storage_bay_overrides_node_storage_capacity() -> None:
    """A STORAGE_BAY of capacity 100 overrides the raw 2000 storage_capacity field."""

    state = _two_node_state()
    yard = state.nodes["frontier_yard"]
    yard.inventory = {}
    yard.facility = Facility(components={"bay-1": _storage_bay(capacity=100)})

    accepted = yard.add_inventory(CargoType.ORE, 250)

    assert accepted == 100
    assert yard.stock(CargoType.ORE) == 100
    assert yard.effective_storage_capacity() == 100


def test_facility_overrides_fall_back_to_raw_fields_when_no_components() -> None:
    """A facility with no bays/loaders/unloaders does not override raw rates."""

    state = _two_node_state()
    yard = state.nodes["frontier_yard"]
    yard.facility = Facility(components={"platform-1": FacilityComponent(
        id="platform-1", kind=FacilityComponentKind.PLATFORM,
    )})

    assert yard.effective_storage_capacity() == 2_000
    assert yard.effective_outbound_rate() == 24
    assert yard.effective_inbound_rate() == 24


# -- Factory-block flow -------------------------------------------------------


def test_factory_block_consumes_inputs_and_produces_outputs() -> None:
    """A FACTORY_BLOCK with ore→parts recipe runs once per tick."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 6}
    smelter.facility = Facility(
        components={
            "fab-1": _factory_block(
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 3},
            )
        }
    )

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 4
    assert smelter.stock(CargoType.PARTS) == 3
    assert result["consumed"] == {"frontier_smelter": {"ore": 2}}
    assert result["produced"] == {"frontier_smelter": {"parts": 3}}
    assert result["blocked"] == []
    assert state.facility_blocked == {}


def test_factory_block_blocked_when_inputs_missing() -> None:
    """Missing inputs flag the component as blocked without consuming anything."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 1}
    smelter.facility = Facility(
        components={
            "fab-1": _factory_block(
                inputs={CargoType.ORE: 2, CargoType.METAL: 1},
                outputs={CargoType.PARTS: 3},
            )
        }
    )

    result = apply_facility_components(state)

    assert smelter.stock(CargoType.ORE) == 1
    assert smelter.stock(CargoType.PARTS) == 0
    assert result["consumed"] == {}
    assert result["produced"] == {}
    assert state.facility_blocked == {"frontier_smelter": ["fab-1"]}
    assert result["blocked"] == [
        {
            "node": "frontier_smelter",
            "component": "fab-1",
            "reason": "missing inputs",
            "missing": {"metal": 1, "ore": 1},
        }
    ]


def test_factory_block_output_clamped_by_storage_bay_capacity() -> None:
    """Outputs respect the facility-derived storage cap (not the raw 2000)."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 4}
    smelter.facility = Facility(
        components={
            "bay-1": _storage_bay(capacity=5),
            "fab-1": _factory_block(
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 10},
            ),
        }
    )

    apply_facility_components(state)

    # 4 ORE - 2 = 2 ORE remaining; bay capacity 5 - 2 ORE = 3 PARTS slots free.
    assert smelter.stock(CargoType.ORE) == 2
    assert smelter.stock(CargoType.PARTS) == 3


def test_facility_phase_runs_in_full_simulation_tick() -> None:
    """The facility phase appears between recipes and demand and reports rollups."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {CargoType.ORE: 4}
    smelter.facility = Facility(
        components={
            "fab-1": _factory_block(
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 3},
            )
        }
    )

    simulation = TickSimulation(state=state)
    report = simulation.step_tick()

    phase_order = report["phase_order"]
    assert "facility_components" in phase_order
    assert phase_order.index("facility_components") > phase_order.index("node_recipes")
    assert phase_order.index("facility_components") < phase_order.index("node_demand")
    assert report["facilities"]["produced"] == {"frontier_smelter": {"parts": 3}}
    assert report["facilities"]["consumed"] == {"frontier_smelter": {"ore": 2}}


# -- Snapshot / persistence ---------------------------------------------------


def test_snapshot_exposes_facility_payload_and_blocked() -> None:
    """Per-node snapshot block surfaces facility, facility_blocked, and effective rates."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.inventory = {}
    smelter.facility = Facility(
        components={
            "bay-1": _storage_bay(capacity=120),
            "loader-1": _loader(rate=6),
            "unloader-1": _unloader(rate=4),
            "fab-1": _factory_block(
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 1},
            ),
        }
    )
    apply_facility_components(state)

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    smelter_payload = by_id["frontier_smelter"]

    assert smelter_payload["facility"] is not None
    assert {component["id"] for component in smelter_payload["facility"]["components"]} == {
        "bay-1",
        "loader-1",
        "unloader-1",
        "fab-1",
    }
    assert smelter_payload["facility"]["storage_capacity_override"] == 120
    assert smelter_payload["facility"]["loader_rate_override"] == 6
    assert smelter_payload["facility"]["unloader_rate_override"] == 4
    assert smelter_payload["storage"]["capacity"] == 120
    assert smelter_payload["storage"]["base_capacity"] == 2_000
    assert smelter_payload["transfer_limit"] == 6
    assert smelter_payload["base_transfer_limit"] == 24
    assert smelter_payload["effective_inbound_rate"] == 4
    assert smelter_payload["effective_outbound_rate"] == 6
    assert smelter_payload["facility_blocked"] == ["fab-1"]


def test_snapshot_facility_null_for_nodes_without_facility() -> None:
    state = _two_node_state()
    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}

    assert by_id["frontier_yard"]["facility"] is None
    assert by_id["frontier_yard"]["facility_blocked"] == []
    assert by_id["frontier_yard"]["transfer_limit"] == 24
    assert by_id["frontier_yard"]["base_transfer_limit"] == 24
    assert by_id["frontier_yard"]["storage"]["capacity"] == 2_000
    assert by_id["frontier_yard"]["storage"]["base_capacity"] == 2_000


def test_facility_round_trips_through_persistence() -> None:
    """state_to_dict→state_from_dict preserves components, ports, and connections."""

    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.facility = Facility(
        components={
            "bay-1": _storage_bay(capacity=80),
            "fab-1": FacilityComponent(
                id="fab-1",
                kind=FacilityComponentKind.FACTORY_BLOCK,
                ports={
                    "in_ore": FacilityPort(
                        id="in_ore",
                        direction=PortDirection.INPUT,
                        cargo_type=CargoType.ORE,
                        rate=2,
                    ),
                    "out_parts": FacilityPort(
                        id="out_parts",
                        direction=PortDirection.OUTPUT,
                        cargo_type=CargoType.PARTS,
                        rate=1,
                    ),
                },
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 1},
                power_required=15,
            ),
        },
        connections={
            "wire-1": InternalConnection(
                id="wire-1",
                source_component_id="bay-1",
                source_port_id="bay_out",
                destination_component_id="fab-1",
                destination_port_id="in_ore",
            )
        },
    )

    restored = state_from_dict(state_to_dict(state))
    restored_facility = restored.nodes["frontier_smelter"].facility

    assert restored_facility is not None
    assert set(restored_facility.components) == {"bay-1", "fab-1"}
    fab = restored_facility.components["fab-1"]
    assert fab.kind == FacilityComponentKind.FACTORY_BLOCK
    assert fab.inputs == {CargoType.ORE: 2}
    assert fab.outputs == {CargoType.PARTS: 1}
    assert fab.power_required == 15
    assert set(fab.ports) == {"in_ore", "out_parts"}
    assert fab.ports["in_ore"].direction == PortDirection.INPUT
    assert fab.ports["in_ore"].cargo_type == CargoType.ORE
    assert restored_facility.connections["wire-1"].source_component_id == "bay-1"
    assert restored_facility.connections["wire-1"].destination_port_id == "in_ore"


def test_facility_summary_reports_overrides_and_power() -> None:
    facility = Facility(
        components={
            "bay-1": _storage_bay(capacity=50),
            "loader-1": _loader(rate=8),
            "fab-1": FacilityComponent(
                id="fab-1",
                kind=FacilityComponentKind.FACTORY_BLOCK,
                power_required=20,
            ),
        }
    )

    summary = facility_summary(facility)

    assert summary["storage_capacity_override"] == 50
    assert summary["loader_rate_override"] == 8
    assert summary["unloader_rate_override"] is None
    assert summary["power_required"] == 20
    assert [component["id"] for component in summary["components"]] == [
        "bay-1",
        "fab-1",
        "loader-1",
    ]


# -- Build commands -----------------------------------------------------------


def test_build_facility_component_installs_component_and_charges_cash() -> None:
    state = _two_node_state()
    starting_cash = state.finance.cash

    result = state.apply_command(
        BuildFacilityComponent(
            component_id="loader-1",
            node_id="frontier_yard",
            kind=FacilityComponentKind.LOADER,
            rate=6,
            power_required=10,
        )
    )

    assert result["ok"] is True
    yard = state.nodes["frontier_yard"]
    assert yard.facility is not None
    assert "loader-1" in yard.facility.components
    component = yard.facility.components["loader-1"]
    assert component.kind == FacilityComponentKind.LOADER
    assert component.rate == 6
    assert component.power_required == 10
    expected_cost = facility_component_build_cost(FacilityComponentKind.LOADER)
    assert state.finance.cash == pytest.approx(starting_cash - expected_cost)
    assert yard.effective_outbound_rate() == 6


def test_build_facility_component_persists_ports_and_connections() -> None:
    state = _two_node_state()

    result = state.apply_command(
        BuildFacilityComponent(
            component_id="fab-1",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.FACTORY_BLOCK,
            inputs={CargoType.ORE: 2},
            outputs={CargoType.PARTS: 1},
            ports=(
                FacilityPort(
                    id="in_ore",
                    direction=PortDirection.INPUT,
                    cargo_type=CargoType.ORE,
                    rate=2,
                ),
                FacilityPort(
                    id="out_parts",
                    direction=PortDirection.OUTPUT,
                    cargo_type=CargoType.PARTS,
                    rate=1,
                ),
            ),
            connections=(
                InternalConnection(
                    id="wire-1",
                    source_component_id="bay-1",
                    source_port_id="bay_out",
                    destination_component_id="fab-1",
                    destination_port_id="in_ore",
                ),
            ),
        )
    )

    assert result["ok"] is True
    facility = state.nodes["frontier_smelter"].facility
    assert facility is not None
    component = facility.components["fab-1"]
    assert set(component.ports) == {"in_ore", "out_parts"}
    assert facility.connections["wire-1"].source_component_id == "bay-1"


def test_build_facility_component_rejects_duplicate_component_id() -> None:
    state = _two_node_state()
    state.apply_command(
        BuildFacilityComponent(
            component_id="bay-1",
            node_id="frontier_yard",
            kind=FacilityComponentKind.STORAGE_BAY,
            capacity=80,
        )
    )

    with pytest.raises(ValueError, match="duplicate component id"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="bay-1",
                node_id="frontier_yard",
                kind=FacilityComponentKind.STORAGE_BAY,
                capacity=40,
            )
        )


def test_build_facility_component_rejects_zero_capacity_storage_bay() -> None:
    state = _two_node_state()

    with pytest.raises(ValueError, match="storage_bay capacity"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="bay-bad",
                node_id="frontier_yard",
                kind=FacilityComponentKind.STORAGE_BAY,
            )
        )


def test_build_facility_component_rejects_zero_rate_loader() -> None:
    state = _two_node_state()

    with pytest.raises(ValueError, match="loader rate"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="loader-bad",
                node_id="frontier_yard",
                kind=FacilityComponentKind.LOADER,
            )
        )


def test_build_facility_component_rejects_factory_block_without_inputs_or_outputs() -> None:
    state = _two_node_state()

    with pytest.raises(ValueError, match="factory_block requires"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="fab-empty",
                node_id="frontier_smelter",
                kind=FacilityComponentKind.FACTORY_BLOCK,
            )
        )


def test_build_facility_component_rejects_unknown_node() -> None:
    state = _two_node_state()

    with pytest.raises(ValueError, match="unknown node"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="loader-1",
                node_id="ghost",
                kind=FacilityComponentKind.LOADER,
                rate=4,
            )
        )


def test_build_facility_component_rejects_insufficient_cash() -> None:
    state = _two_node_state()
    state.finance.cash = 50.0

    with pytest.raises(ValueError, match="insufficient cash"):
        state.apply_command(
            BuildFacilityComponent(
                component_id="loader-1",
                node_id="frontier_yard",
                kind=FacilityComponentKind.LOADER,
                rate=4,
            )
        )


def test_preview_build_facility_component_does_not_mutate_state() -> None:
    state = _two_node_state()
    starting_cash = state.finance.cash

    result = state.apply_command(
        PreviewBuildFacilityComponent(
            component_id="bay-1",
            node_id="frontier_yard",
            kind=FacilityComponentKind.STORAGE_BAY,
            capacity=120,
        )
    )

    assert result["ok"] is True
    assert result["cost"] == facility_component_build_cost(FacilityComponentKind.STORAGE_BAY)
    assert result["normalized_command"]["type"] == "BuildFacilityComponent"
    assert result["normalized_command"]["capacity"] == 120
    assert state.finance.cash == starting_cash
    assert state.nodes["frontier_yard"].facility is None


def test_preview_build_facility_component_reports_invalid_when_node_missing() -> None:
    state = _two_node_state()

    result = state.apply_command(
        PreviewBuildFacilityComponent(
            component_id="bay-1",
            node_id="ghost",
            kind=FacilityComponentKind.STORAGE_BAY,
            capacity=80,
        )
    )

    assert result["ok"] is False
    assert "unknown node" in result["message"]


def test_preview_build_facility_component_reports_insufficient_cash() -> None:
    state = _two_node_state()
    state.finance.cash = 100.0

    result = state.apply_command(
        PreviewBuildFacilityComponent(
            component_id="bay-1",
            node_id="frontier_yard",
            kind=FacilityComponentKind.STORAGE_BAY,
            capacity=120,
        )
    )

    assert result["ok"] is False
    assert "insufficient cash" in result["message"]
    assert result["cost"] == facility_component_build_cost(FacilityComponentKind.STORAGE_BAY)
    assert state.nodes["frontier_yard"].facility is None


def test_command_from_dict_parses_build_facility_component() -> None:
    command = command_from_dict(
        {
            "type": "BuildFacilityComponent",
            "component_id": "fab-1",
            "node_id": "frontier_smelter",
            "kind": "factory_block",
            "inputs": {"ore": 2},
            "outputs": {"parts": 1},
            "power_required": 12,
            "ports": [
                {
                    "id": "in_ore",
                    "direction": "input",
                    "cargo_type": "ore",
                    "rate": 2,
                }
            ],
            "connections": [
                {
                    "id": "wire-1",
                    "source_component_id": "bay-1",
                    "source_port_id": "bay_out",
                    "destination_component_id": "fab-1",
                    "destination_port_id": "in_ore",
                }
            ],
        }
    )

    assert isinstance(command, BuildFacilityComponent)
    assert command.kind == FacilityComponentKind.FACTORY_BLOCK
    assert command.inputs == {CargoType.ORE: 2}
    assert command.outputs == {CargoType.PARTS: 1}
    assert command.power_required == 12
    assert command.ports[0].cargo_type == CargoType.ORE
    assert command.connections[0].destination_port_id == "in_ore"


# -- Exit criterion: change components to fix a depot bottleneck --------------


def test_loader_upgrade_resolves_depot_bottleneck_without_changing_rail() -> None:
    """Sprint 16 exit criterion: a slow loader caps throughput; replacing it removes the cap.

    No links change between the two phases — only a facility component is
    swapped out — yet the throughput per tick rises from 4 to 12.
    """

    state = _two_node_state()
    state.nodes["frontier_yard"].facility = Facility(
        components={"loader-slow": _loader(component_id="loader-slow", rate=4)}
    )
    state.add_train(
        FreightTrain(
            id="atlas",
            name="Atlas",
            node_id="frontier_yard",
            capacity=20,
        )
    )
    state.add_order(
        FreightOrder(
            id="ore_run_1",
            train_id="atlas",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            requested_units=20,
        )
    )

    advance_freight(state)
    bottlenecked_load = state.trains["atlas"].cargo_units
    assert bottlenecked_load == 4

    # Reset train to idle at origin and swap the slow loader for a fast one.
    state.trains["atlas"].status = TrainStatus.IDLE
    state.trains["atlas"].cargo_type = None
    state.trains["atlas"].cargo_units = 0
    state.trains["atlas"].destination = None
    state.trains["atlas"].route_node_ids = ()
    state.trains["atlas"].route_link_ids = ()
    state.trains["atlas"].remaining_ticks = 0
    state.trains["atlas"].order_id = None
    state.trains["atlas"].blocked_reason = None
    state.orders["ore_run_1"].active = False

    yard_facility = state.nodes["frontier_yard"].facility
    assert yard_facility is not None
    yard_facility.components.pop("loader-slow")
    yard_facility.components["loader-fast"] = _loader(
        component_id="loader-fast",
        rate=12,
    )

    state.add_order(
        FreightOrder(
            id="ore_run_2",
            train_id="atlas",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            requested_units=20,
        )
    )

    advance_freight(state)

    assert state.trains["atlas"].cargo_units == 12
