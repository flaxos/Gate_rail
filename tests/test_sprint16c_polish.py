"""Tests for Sprint 16C facility polish and Sprint 21B preview surfaces."""

from __future__ import annotations

import json
from io import StringIO

from gaterail.bridge import handle_bridge_message
from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.commands import (
    BuildFacilityComponent,
    DemolishFacilityComponent,
    PreviewBuildFacilityComponent,
    PreviewDemolishFacilityComponent,
)
from gaterail.construction import facility_component_build_cost
from gaterail.facilities import apply_facility_components
from gaterail.freight import advance_freight
from gaterail.models import (
    DevelopmentTier,
    Facility,
    FacilityBlockReason,
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
from gaterail.persistence import save_simulation, state_from_dict, state_to_dict
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _uranium() -> CargoType:
    return CargoType("uranium")


def _world(
    *,
    world_id: str = "frontier",
    name: str = "Brink Frontier",
    tier: DevelopmentTier = DevelopmentTier.OUTPOST,
    power_available: int = 100,
    power_used: int = 0,
    stability: float = 0.82,
    support_streak: int = 0,
    development_progress: int = 0,
) -> WorldState:
    return WorldState(
        id=world_id,
        name=name,
        tier=tier,
        population=10_000,
        stability=stability,
        power_available=power_available,
        power_used=power_used,
        support_streak=support_streak,
        development_progress=development_progress,
    )


def _two_node_state(*, world: WorldState | None = None) -> GameState:
    state = GameState()
    state.add_world(world or _world())
    state.add_node(
        NetworkNode(
            id="frontier_yard",
            name="Frontier Yard",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={CargoType.ORE: 30},
            storage_capacity=200,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_smelter",
            name="Frontier Smelter",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            inventory={},
            storage_capacity=200,
            transfer_limit_per_tick=24,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_yard_smelter",
            origin="frontier_yard",
            destination="frontier_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=24,
        )
    )
    return state


def _port(
    port_id: str,
    direction: PortDirection,
    cargo_type: CargoType | None,
    *,
    rate: int,
    capacity: int = 0,
) -> FacilityPort:
    return FacilityPort(
        id=port_id,
        direction=direction,
        cargo_type=cargo_type,
        rate=rate,
        capacity=capacity,
    )


def _component(
    component_id: str,
    kind: FacilityComponentKind,
    *,
    ports: dict[str, FacilityPort] | None = None,
    port_inventory: dict[str, dict[CargoType, int]] | None = None,
    capacity: int = 0,
    rate: int = 0,
    power_required: int = 0,
    power_provided: int = 0,
    inputs: dict[CargoType, int] | None = None,
    outputs: dict[CargoType, int] | None = None,
    train_capacity: int = 0,
    concurrent_loading_limit: int = 1,
    stored_charge: int = 0,
    discharge_per_tick: int = 0,
) -> FacilityComponent:
    return FacilityComponent(
        id=component_id,
        kind=kind,
        ports=dict(ports or {}),
        port_inventory=dict(port_inventory or {}),
        capacity=capacity,
        rate=rate,
        power_required=power_required,
        power_provided=power_provided,
        inputs=dict(inputs or {}),
        outputs=dict(outputs or {}),
        train_capacity=train_capacity,
        concurrent_loading_limit=concurrent_loading_limit,
        stored_charge=stored_charge,
        discharge_per_tick=discharge_per_tick,
    )


def test_specialized_kinds_preview_defaults_and_build_surface_snapshot() -> None:
    state = _two_node_state()

    preview = state.apply_command(
        PreviewBuildFacilityComponent(
            component_id="fab-1",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.FABRICATOR,
        )
    )

    assert preview["ok"] is True
    assert preview["cost"] == facility_component_build_cost(FacilityComponentKind.FABRICATOR)
    assert preview["cargo_cost"] == {}
    assert [port["direction"] for port in preview["default_ports"]] == ["input", "output"]
    assert preview["normalized_command"]["ports"] == preview["default_ports"]

    state.apply_command(
        BuildFacilityComponent(
            component_id="smelter-1",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.SMELTER,
            inputs={CargoType.ORE: 2},
            outputs={CargoType.METAL: 1},
            ports=(),
        )
    )
    state.apply_command(
        BuildFacilityComponent(
            component_id="fab-2",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.FABRICATOR,
            inputs={CargoType.METAL: 1},
            outputs={CargoType.PARTS: 1},
            ports=(
                _port("custom_in", PortDirection.INPUT, CargoType.METAL, rate=2),
                _port("custom_out", PortDirection.OUTPUT, CargoType.PARTS, rate=1),
            ),
        )
    )

    facility = state.nodes["frontier_smelter"].facility
    assert facility is not None
    assert facility.components["smelter-1"].kind == FacilityComponentKind.SMELTER
    assert sorted(facility.components["smelter-1"].ports) == ["in_smelter-1", "out_smelter-1"]
    assert sorted(facility.components["fab-2"].ports) == ["custom_in", "custom_out"]

    snapshot = render_snapshot(state)
    node = next(item for item in snapshot["nodes"] if item["id"] == "frontier_smelter")
    component_payload = {
        component["id"]: component
        for component in node["facility"]["components"]
    }
    assert component_payload["smelter-1"]["kind"] == "smelter"


def test_structured_block_reasons_survive_results_and_snapshots() -> None:
    state = _two_node_state()
    smelter = state.nodes["frontier_smelter"]
    smelter.facility = Facility(
        components={
            "fab-1": _component(
                "fab-1",
                FacilityComponentKind.FACTORY_BLOCK,
                inputs={CargoType.ORE: 2},
                outputs={CargoType.PARTS: 1},
                ports={
                    "ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=2),
                    "parts_out": _port("parts_out", PortDirection.OUTPUT, CargoType.PARTS, rate=1),
                },
            )
        }
    )

    first = apply_facility_components(state)

    assert first["blocked"][0]["reason"] == FacilityBlockReason.OPEN_INPUT_PORTS
    assert first["blocked"][0]["kind"] == FacilityComponentKind.FACTORY_BLOCK.value
    assert first["blocked"][0]["detail"] == {"open_inputs": ["ore_in"]}
    assert state.facility_block_entries == first["blocked"]

    smelter.facility.connections["wire-1"] = InternalConnection(
        id="wire-1",
        source_component_id="fab-1",
        source_port_id="parts_out",
        destination_component_id="fab-1",
        destination_port_id="ore_in",
    )
    second = apply_facility_components(state)

    assert second["blocked"][0]["reason"] == FacilityBlockReason.MISSING_INPUTS
    assert second["blocked"][0]["detail"] == {"missing": {"ore": 2}}
    snapshot = render_snapshot(state)
    node = next(item for item in snapshot["nodes"] if item["id"] == "frontier_smelter")
    assert node["facility_block_entries"][0]["reason"] == "missing_inputs"
    assert snapshot["facility_blocked_entries"][0]["reason"] == "missing_inputs"


def test_loader_and_platform_limits_drive_freight_reports_and_snapshot_summary() -> None:
    state = _two_node_state()
    yard = state.nodes["frontier_yard"]
    yard.inventory = {CargoType.ORE: 30}
    yard.facility = Facility(
        components={
            "loader-1": _component("loader-1", FacilityComponentKind.LOADER, rate=10),
            "platform-1": _component(
                "platform-1",
                FacilityComponentKind.PLATFORM,
                train_capacity=1,
                concurrent_loading_limit=1,
            ),
        }
    )
    for train_id in ("atlas", "pioneer"):
        state.add_train(FreightTrain(id=train_id, name=train_id.title(), node_id="frontier_yard", capacity=50))
    state.add_order(
        FreightOrder(
            id="ore_run_a",
            train_id="atlas",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            requested_units=30,
        )
    )
    state.add_order(
        FreightOrder(
            id="ore_run_b",
            train_id="pioneer",
            origin="frontier_yard",
            destination="frontier_smelter",
            cargo_type=CargoType.ORE,
            requested_units=30,
        )
    )

    freight = advance_freight(state)

    assert state.nodes["frontier_yard"].stock(CargoType.ORE) == 20
    assert state.trains["atlas"].cargo_units == 10
    assert state.trains["pioneer"].status == TrainStatus.BLOCKED
    assert freight["loader_capped"] == [
        {
            "node": "frontier_yard",
            "train": "Atlas",
            "cargo": "ore",
            "requested_units": 30,
            "loaded_units": 10,
            "effective_loader_rate": 10,
        }
    ]
    assert freight["freight_blocked"] == [
        {
            "node": "frontier_yard",
            "train": "Pioneer",
            "reason": "platform_capacity",
            "direction": "load",
        }
    ]

    snapshot = render_snapshot(state)
    node = next(item for item in snapshot["nodes"] if item["id"] == "frontier_yard")
    assert node["loader_summary"] == {
        "effective_loader_rate": 10,
        "effective_unloader_rate": 24,
        "platform_queue_depth": 1,
    }


def test_facility_power_module_adds_world_power_and_reactor_blocks_without_fuel() -> None:
    state = _two_node_state(world=_world(power_available=100))
    yard = state.nodes["frontier_yard"]
    yard.facility = Facility(
        components={
            "power-1": _component(
                "power-1",
                FacilityComponentKind.POWER_MODULE,
                power_provided=80,
            ),
            "reactor-1": _component(
                "reactor-1",
                FacilityComponentKind.REACTOR,
                power_provided=250,
                inputs={_uranium(): 1},
            ),
        }
    )
    simulation = TickSimulation(state=state)

    simulation.step_tick()

    world = simulation.state.worlds["frontier"]
    assert world.power_available == 180
    assert simulation.state.facility_power_contribution == {"frontier": 80}
    assert simulation.state.facility_block_entries == [
        {
            "node": "frontier_yard",
            "component": "reactor-1",
            "kind": "reactor",
            "reason": "power_shortfall",
            "detail": {"missing": {"uranium": 1}, "power_provided": 250},
        }
    ]

    simulation.state.nodes["frontier_yard"].inventory[_uranium()] = 1
    simulation.step_tick()
    assert simulation.state.worlds["frontier"].power_available == 430
    assert simulation.state.nodes["frontier_yard"].stock(_uranium()) == 0

    simulation.state.nodes["frontier_yard"].facility.components.pop("power-1")
    simulation.state.nodes["frontier_yard"].facility.components.pop("reactor-1")
    simulation.step_tick()
    assert simulation.state.worlds["frontier"].power_available == 100


def test_capacitor_bank_discharges_under_world_shortfall() -> None:
    state = _two_node_state(world=_world(power_available=20, power_used=40))
    state.nodes["frontier_yard"].facility = Facility(
        components={
            "cap-1": _component(
                "cap-1",
                FacilityComponentKind.CAPACITOR_BANK,
                stored_charge=40,
                discharge_per_tick=10,
            )
        }
    )
    simulation = TickSimulation(state=state)

    simulation.step_tick()
    assert simulation.state.worlds["frontier"].power_available == 30
    assert simulation.state.nodes["frontier_yard"].facility.components["cap-1"].stored_charge == 30
    simulation.step_tick()
    assert simulation.state.worlds["frontier"].power_available == 30
    assert simulation.state.nodes["frontier_yard"].facility.components["cap-1"].stored_charge == 20
    simulation.step_tick()
    simulation.step_tick()
    assert simulation.state.nodes["frontier_yard"].facility.components["cap-1"].stored_charge == 0
    simulation.step_tick()
    assert simulation.state.worlds["frontier"].power_available == 20


def test_demolish_preview_and_apply_refund_cargo_drop_and_connection_cleanup() -> None:
    state = _two_node_state(world=_world(power_available=100))
    smelter = state.nodes["frontier_smelter"]
    smelter.storage_capacity = 5
    state.finance.cash = 10_000.0
    build = state.apply_command(
        BuildFacilityComponent(
            component_id="smelter-1",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.SMELTER,
            inputs={CargoType.ORE: 2},
            outputs={CargoType.METAL: 1},
            ports=(
                _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=2),
                _port("metal_out", PortDirection.OUTPUT, CargoType.METAL, rate=4, capacity=20),
            ),
        )
    )
    state.apply_command(
        BuildFacilityComponent(
            component_id="bay-1",
            node_id="frontier_smelter",
            kind=FacilityComponentKind.STORAGE_BAY,
            capacity=10,
            ports=(
                _port("ore_out", PortDirection.OUTPUT, CargoType.ORE, rate=2),
            ),
        )
    )
    facility = smelter.facility
    assert facility is not None
    facility.components["smelter-1"].port_inventory = {"metal_out": {CargoType.METAL: 12}}
    facility.connections["wire-1"] = InternalConnection(
        id="wire-1",
        source_component_id="bay-1",
        source_port_id="ore_out",
        destination_component_id="smelter-1",
        destination_port_id="ore_in",
    )

    before = json.dumps(state_to_dict(state), sort_keys=True)
    preview = state.apply_command(
        PreviewDemolishFacilityComponent(
            node_id="frontier_smelter",
            component_id="smelter-1",
        )
    )
    after = json.dumps(state_to_dict(state), sort_keys=True)

    assert before == after
    assert build["cost"] == 2800.0
    assert preview["refund"] == 1400.0
    assert preview["cargo_returned"] == {"metal": 5}
    assert preview["cargo_dropped"] == {"metal": 7}
    assert preview["connections_removed"] == ["wire-1"]

    demolish = state.apply_command(
        DemolishFacilityComponent(
            node_id="frontier_smelter",
            component_id="smelter-1",
        )
    )

    assert demolish["refund"] == preview["refund"]
    assert demolish["cargo_returned"] == preview["cargo_returned"]
    assert demolish["cargo_dropped"] == preview["cargo_dropped"]
    assert demolish["connections_removed"] == preview["connections_removed"]
    assert state.finance.cash == 7_100.0
    assert smelter.inventory == {CargoType.METAL: 5}
    assert "smelter-1" not in facility.components
    assert facility.connections == {}


def test_demolish_results_are_deterministic_and_clear_blocked_state() -> None:
    base = _two_node_state()
    node = base.nodes["frontier_smelter"]
    node.facility = Facility(
        components={
            "smelter-1": _component(
                "smelter-1",
                FacilityComponentKind.SMELTER,
                inputs={CargoType.ORE: 2},
                outputs={CargoType.METAL: 1},
                ports={
                    "ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=2),
                    "metal_out": _port(
                        "metal_out",
                        PortDirection.OUTPUT,
                        CargoType.METAL,
                        rate=1,
                        capacity=1,
                    ),
                },
                port_inventory={"metal_out": {CargoType.METAL: 1}},
            )
        }
    )
    apply_facility_components(base)

    left = state_from_dict(state_to_dict(base))
    right = state_from_dict(state_to_dict(base))
    left_result = left.apply_command(DemolishFacilityComponent("frontier_smelter", "smelter-1"))
    right_result = right.apply_command(DemolishFacilityComponent("frontier_smelter", "smelter-1"))
    assert left_result == right_result

    apply_facility_components(left)
    assert left.facility_block_entries == []


def test_persistence_round_trips_all_new_facility_fields() -> None:
    state = _two_node_state(world=_world(power_available=100))
    state.nodes["frontier_yard"].facility = Facility(
        components={
            "warehouse-1": _component("warehouse-1", FacilityComponentKind.WAREHOUSE_BAY, capacity=300),
            "extractor-1": _component(
                "extractor-1",
                FacilityComponentKind.EXTRACTOR_HEAD,
                outputs={CargoType.ORE: 1},
                ports={"ore_out": _port("ore_out", PortDirection.OUTPUT, CargoType.ORE, rate=6)},
            ),
            "crusher-1": _component("crusher-1", FacilityComponentKind.CRUSHER, inputs={CargoType.ORE: 1}, outputs={CargoType.ORE: 1}),
            "sorter-1": _component("sorter-1", FacilityComponentKind.SORTER, inputs={CargoType.ORE: 1}, outputs={CargoType.ORE: 1}),
            "smelter-1": _component("smelter-1", FacilityComponentKind.SMELTER, inputs={CargoType.ORE: 1}, outputs={CargoType.METAL: 1}),
            "refinery-1": _component("refinery-1", FacilityComponentKind.REFINERY, inputs={CargoType.FUEL: 1}, outputs={CargoType.COOLANT: 1}),
            "chem-1": _component("chem-1", FacilityComponentKind.CHEMICAL_PROCESSOR, inputs={CargoType.WATER: 1}, outputs={CargoType.COOLANT: 1}),
        }
    )
    state.nodes["frontier_smelter"].facility = Facility(
        components={
            "fab-1": _component("fab-1", FacilityComponentKind.FABRICATOR, inputs={CargoType.METAL: 1}, outputs={CargoType.PARTS: 1}),
            "ea-1": _component("ea-1", FacilityComponentKind.ELECTRONICS_ASSEMBLER, inputs={CargoType.PARTS: 1}, outputs={CargoType.ELECTRONICS: 1}),
            "semi-1": _component("semi-1", FacilityComponentKind.SEMICONDUCTOR_LINE, inputs={CargoType.ELECTRONICS: 1}, outputs={CargoType.ELECTRONICS: 1}),
            "reactor-1": _component("reactor-1", FacilityComponentKind.REACTOR, inputs={_uranium(): 1}, power_provided=250),
            "cap-1": _component("cap-1", FacilityComponentKind.CAPACITOR_BANK, stored_charge=40, discharge_per_tick=10),
            "platform-1": _component("platform-1", FacilityComponentKind.PLATFORM, train_capacity=2, concurrent_loading_limit=1),
            "power-1": _component("power-1", FacilityComponentKind.POWER_MODULE, power_provided=80),
        }
    )
    state.facility_block_entries = [
        {
            "node": "frontier_smelter",
            "component": "reactor-1",
            "kind": "reactor",
            "reason": "power_shortfall",
            "detail": {"missing": {"uranium": 1}, "power_provided": 250},
        }
    ]
    state.facility_power_contribution = {"frontier": 80}

    original = json.dumps(state_to_dict(state), sort_keys=True)
    restored = state_from_dict(state_to_dict(state))
    round_tripped = json.dumps(state_to_dict(restored), sort_keys=True)

    assert round_tripped == original
    snapshot = render_snapshot(restored)
    node = next(item for item in snapshot["nodes"] if item["id"] == "frontier_smelter")
    components = {component["id"]: component for component in node["facility"]["components"]}
    assert components["power-1"]["power_provided"] == 80
    assert components["platform-1"]["train_capacity"] == 2
    assert components["cap-1"]["stored_charge"] == 40
    assert components["cap-1"]["discharge_per_tick"] == 10


def test_bridge_preview_unknown_kind_returns_non_error_command_result() -> None:
    snapshot = handle_bridge_message(
        TickSimulation(state=_two_node_state()),
        {
            "command": {
                "type": "PreviewBuildFacilityComponent",
                "component_id": "mystery-1",
                "node_id": "frontier_smelter",
                "kind": "not_a_real_kind",
            },
            "ticks": 0,
        },
    )

    assert snapshot["bridge"]["ok"] is True
    assert snapshot["bridge"]["command_results"] == [
        {
            "ok": False,
            "type": "PreviewBuildFacilityComponent",
            "target_id": "mystery-1",
            "message": "unknown facility component kind: not_a_real_kind",
        }
    ]


def test_cli_facilities_report_lists_new_kinds_and_reason_codes(tmp_path) -> None:
    simulation = TickSimulation(state=_two_node_state())
    node = simulation.state.nodes["frontier_smelter"]
    node.facility = Facility(
        components={
            "smelter-1": _component(
                "smelter-1",
                FacilityComponentKind.SMELTER,
                power_required=12,
                power_provided=0,
                inputs={CargoType.ORE: 2},
                outputs={CargoType.METAL: 1},
                ports={"ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=2)},
            ),
            "power-1": _component(
                "power-1",
                FacilityComponentKind.POWER_MODULE,
                power_provided=80,
            ),
        }
    )
    apply_facility_components(simulation.state)
    save_path = tmp_path / "facility_report.json"
    save_simulation(simulation, save_path)

    output = StringIO()
    result = run_cli(
        ["--load", str(save_path), "--inspect", "--report", "facilities"],
        output=output,
    )

    text = output.getvalue()
    assert result == 0
    assert "Facility Components" in text
    assert "smelter" in text
    assert "power_module" in text
    assert "open_input_ports" in text
    assert "power_provided" in text


def test_mixed_kind_chain_remains_deterministic_across_connection_order() -> None:
    def build_state(*, reverse_connections: bool) -> GameState:
        state = _two_node_state()
        node = state.nodes["frontier_yard"]
        node.inventory = {}
        components = {
            "extractor": _component(
                "extractor",
                FacilityComponentKind.EXTRACTOR_HEAD,
                outputs={CargoType.ORE: 1},
                ports={"ore_out": _port("ore_out", PortDirection.OUTPUT, CargoType.ORE, rate=1)},
            ),
            "crusher": _component(
                "crusher",
                FacilityComponentKind.CRUSHER,
                inputs={CargoType.ORE: 1},
                outputs={CargoType.ORE: 1},
                ports={
                    "ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=1),
                    "ore_out": _port("ore_out", PortDirection.OUTPUT, CargoType.ORE, rate=1),
                },
            ),
            "sorter": _component(
                "sorter",
                FacilityComponentKind.SORTER,
                inputs={CargoType.ORE: 1},
                outputs={CargoType.ORE: 1},
                ports={
                    "ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=1),
                    "ore_out": _port("ore_out", PortDirection.OUTPUT, CargoType.ORE, rate=1),
                },
            ),
            "smelter": _component(
                "smelter",
                FacilityComponentKind.SMELTER,
                inputs={CargoType.ORE: 1},
                outputs={CargoType.METAL: 1},
                ports={
                    "ore_in": _port("ore_in", PortDirection.INPUT, CargoType.ORE, rate=1),
                    "metal_out": _port("metal_out", PortDirection.OUTPUT, CargoType.METAL, rate=1),
                },
            ),
            "fabricator": _component(
                "fabricator",
                FacilityComponentKind.FABRICATOR,
                inputs={CargoType.METAL: 1},
                outputs={CargoType.PARTS: 1},
                ports={
                    "metal_in": _port("metal_in", PortDirection.INPUT, CargoType.METAL, rate=1),
                },
            ),
        }
        connections = [
            InternalConnection("wire-1", "extractor", "ore_out", "crusher", "ore_in"),
            InternalConnection("wire-2", "crusher", "ore_out", "sorter", "ore_in"),
            InternalConnection("wire-3", "sorter", "ore_out", "smelter", "ore_in"),
            InternalConnection("wire-4", "smelter", "metal_out", "fabricator", "metal_in"),
        ]
        if reverse_connections:
            connections.reverse()
        node.facility = Facility(
            components=components,
            connections={connection.id: connection for connection in connections},
        )
        return state

    left = build_state(reverse_connections=False)
    right = build_state(reverse_connections=True)
    for _ in range(5):
        apply_facility_components(left)
        apply_facility_components(right)

    assert left.nodes["frontier_yard"].stock(CargoType.PARTS) == 1
    assert left.nodes["frontier_yard"].inventory == right.nodes["frontier_yard"].inventory
    assert left.nodes["frontier_yard"].facility.components["fabricator"].port_inventory == right.nodes["frontier_yard"].facility.components["fabricator"].port_inventory


def test_reactor_power_gates_world_promotion_until_fueled() -> None:
    state = GameState()
    state.add_world(
        _world(
            tier=DevelopmentTier.FRONTIER_COLONY,
            power_available=20,
            stability=0.82,
            support_streak=7,
            development_progress=7,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Frontier Settlement",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory={
                CargoType.FOOD: 20,
                CargoType.CONSTRUCTION_MATERIALS: 20,
                CargoType.MACHINERY: 8,
            },
            storage_capacity=500,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_reactor",
            name="Frontier Reactor",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=200,
            transfer_limit_per_tick=24,
            facility=Facility(
                components={
                    "reactor-1": _component(
                        "reactor-1",
                        FacilityComponentKind.REACTOR,
                        power_provided=250,
                        inputs={_uranium(): 1},
                    )
                }
            ),
        )
    )
    simulation = TickSimulation(state=state)

    first = simulation.step_tick()
    assert first["progression"]["frontier"]["promoted_to"] is None
    assert simulation.state.worlds["frontier"].tier == DevelopmentTier.FRONTIER_COLONY

    simulation.state.nodes["frontier_reactor"].inventory[_uranium()] = 1
    second = simulation.step_tick()
    assert second["progression"]["frontier"]["promoted_to"] == "industrial_colony"
    assert simulation.state.worlds["frontier"].tier == DevelopmentTier.INDUSTRIAL_COLONY
