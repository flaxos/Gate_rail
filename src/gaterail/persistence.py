"""JSON save/load support for deterministic GateRail playtests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaterail.cargo import CargoType
from gaterail.models import (
    ConstructionProject,
    ConstructionStatus,
    Contract,
    ContractKind,
    ContractStatus,
    DevelopmentTier,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FinanceState,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    GameState,
    GatePowerStatus,
    GatePowerSupport,
    InternalConnection,
    LinkMode,
    MiningMission,
    MiningMissionStatus,
    NetworkDisruption,
    NetworkLink,
    NetworkNode,
    NodeKind,
    NodeRecipe,
    OutpostKind,
    PortDirection,
    PowerPlant,
    PowerPlantKind,
    ProgressionTrend,
    ResourceRecipe,
    ResourceRecipeKind,
    SpaceSite,
    TrackPoint,
    TrackSignal,
    TrackSignalKind,
    TrainConsist,
    TrainStatus,
    WorldState,
)
from gaterail.resources import ResourceDeposit
from gaterail.simulation import TickSimulation


SAVE_FORMAT = "gaterail.tick_simulation"
SAVE_VERSION = 1


def _cargo_key(cargo_type: CargoType | None) -> str | None:
    """Convert an optional cargo enum to a JSON-safe key."""

    return None if cargo_type is None else cargo_type.value


def _cargo_map_to_dict(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert a cargo-keyed map to stable JSON data."""

    return {
        cargo_type.value: int(units)
        for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)
    }


def _cargo_map_from_dict(mapping: object) -> dict[CargoType, int]:
    """Convert JSON cargo maps back to model keys."""

    if not isinstance(mapping, dict):
        return {}
    return {CargoType(str(cargo)): int(units) for cargo, units in mapping.items()}


def _resource_map_to_dict(mapping: dict[str, int]) -> dict[str, int]:
    """Convert a resource-id-keyed map to stable JSON data."""

    return {
        str(resource_id): int(units)
        for resource_id, units in sorted(mapping.items())
    }


def _resource_map_from_dict(mapping: object) -> dict[str, int]:
    """Convert JSON resource maps back to resource-id keys."""

    if not isinstance(mapping, dict):
        return {}
    return {str(resource_id): int(units) for resource_id, units in mapping.items()}


def _world_to_dict(world: WorldState) -> dict[str, object]:
    """Serialize a world."""

    return {
        "id": world.id,
        "name": world.name,
        "tier": int(world.tier),
        "population": world.population,
        "stability": world.stability,
        "power_available": world.power_available,
        "power_used": world.power_used,
        "gate_power_used": world.gate_power_used,
        "power_generated_this_tick": world.power_generated_this_tick,
        "specialization": world.specialization,
        "development_progress": world.development_progress,
        "support_streak": world.support_streak,
        "shortage_streak": world.shortage_streak,
        "last_trend": world.last_trend.value,
    }


def _world_from_dict(data: dict[str, Any]) -> WorldState:
    """Deserialize a world."""

    return WorldState(
        id=str(data["id"]),
        name=str(data["name"]),
        tier=DevelopmentTier(int(data["tier"])),
        population=int(data.get("population", 0)),
        stability=float(data.get("stability", 1.0)),
        power_available=int(data.get("power_available", 0)),
        power_used=int(data.get("power_used", 0)),
        gate_power_used=int(data.get("gate_power_used", 0)),
        power_generated_this_tick=int(data.get("power_generated_this_tick", 0)),
        specialization=data.get("specialization"),
        development_progress=int(data.get("development_progress", 0)),
        support_streak=int(data.get("support_streak", 0)),
        shortage_streak=int(data.get("shortage_streak", 0)),
        last_trend=ProgressionTrend(str(data.get("last_trend", ProgressionTrend.STALLED.value))),
    )


def _recipe_to_dict(recipe: NodeRecipe | None) -> dict[str, object] | None:
    """Serialize an optional NodeRecipe."""

    if recipe is None:
        return None
    return {
        "inputs": _cargo_map_to_dict(recipe.inputs),
        "outputs": _cargo_map_to_dict(recipe.outputs),
    }


def _recipe_from_dict(data: object) -> NodeRecipe | None:
    """Deserialize an optional NodeRecipe."""

    if not isinstance(data, dict):
        return None
    return NodeRecipe(
        inputs=_cargo_map_from_dict(data.get("inputs", {})),
        outputs=_cargo_map_from_dict(data.get("outputs", {})),
    )


def _resource_recipe_to_dict(recipe: ResourceRecipe | None) -> dict[str, object] | None:
    """Serialize an optional ResourceRecipe."""

    if recipe is None:
        return None
    return {
        "id": recipe.id,
        "kind": recipe.kind.value,
        "inputs": _resource_map_to_dict(recipe.inputs),
        "outputs": _resource_map_to_dict(recipe.outputs),
    }


def _resource_recipe_from_dict(data: object) -> ResourceRecipe | None:
    """Deserialize an optional ResourceRecipe."""

    if not isinstance(data, dict):
        return None
    return ResourceRecipe(
        id=str(data["id"]),
        kind=ResourceRecipeKind(str(data.get("kind", ResourceRecipeKind.GENERIC.value))),
        inputs=_resource_map_from_dict(data.get("inputs", {})),
        outputs=_resource_map_from_dict(data.get("outputs", {})),
    )


def _port_to_dict(port: FacilityPort) -> dict[str, object]:
    """Serialize a facility port."""

    return {
        "id": port.id,
        "direction": port.direction.value,
        "cargo_type": None if port.cargo_type is None else port.cargo_type.value,
        "rate": int(port.rate),
        "capacity": int(port.capacity),
    }


def _port_from_dict(data: dict[str, Any]) -> FacilityPort:
    """Deserialize a facility port."""

    cargo_type = data.get("cargo_type")
    return FacilityPort(
        id=str(data["id"]),
        direction=PortDirection(str(data["direction"])),
        cargo_type=None if cargo_type is None else CargoType(str(cargo_type)),
        rate=int(data.get("rate", 0)),
        capacity=int(data.get("capacity", 0)),
    )


def _component_to_dict(component: FacilityComponent) -> dict[str, object]:
    """Serialize a facility component."""

    return {
        "id": component.id,
        "kind": component.kind.value,
        "ports": [_port_to_dict(port) for port in sorted(component.ports.values(), key=lambda item: item.id)],
        "port_inventory": {
            port_id: _cargo_map_to_dict(cargo_map)
            for port_id, cargo_map in sorted(component.port_inventory.items())
            if cargo_map
        },
        "capacity": int(component.capacity),
        "rate": int(component.rate),
        "power_required": int(component.power_required),
        "power_provided": int(component.power_provided),
        "train_capacity": int(component.train_capacity),
        "concurrent_loading_limit": int(component.concurrent_loading_limit),
        "stored_charge": int(component.stored_charge),
        "discharge_per_tick": int(component.discharge_per_tick),
        "build_cost": float(component.build_cost),
        "inputs": _cargo_map_to_dict(component.inputs),
        "outputs": _cargo_map_to_dict(component.outputs),
    }


def _component_from_dict(data: dict[str, Any]) -> FacilityComponent:
    """Deserialize a facility component."""

    ports: dict[str, FacilityPort] = {}
    for port_data in data.get("ports", []):
        port = _port_from_dict(port_data)
        ports[port.id] = port
    port_inventory_data = data.get("port_inventory", {})
    port_inventory: dict[str, dict[CargoType, int]] = {}
    if isinstance(port_inventory_data, dict):
        for port_id, cargo_map in port_inventory_data.items():
            parsed = _cargo_map_from_dict(cargo_map)
            if parsed:
                port_inventory[str(port_id)] = parsed
    return FacilityComponent(
        id=str(data["id"]),
        kind=FacilityComponentKind(str(data["kind"])),
        ports=ports,
        port_inventory=port_inventory,
        capacity=int(data.get("capacity", 0)),
        rate=int(data.get("rate", 0)),
        power_required=int(data.get("power_required", 0)),
        power_provided=int(data.get("power_provided", 0)),
        inputs=_cargo_map_from_dict(data.get("inputs", {})),
        outputs=_cargo_map_from_dict(data.get("outputs", {})),
        train_capacity=int(data.get("train_capacity", 0)),
        concurrent_loading_limit=int(data.get("concurrent_loading_limit", 1)),
        stored_charge=int(data.get("stored_charge", 0)),
        discharge_per_tick=int(data.get("discharge_per_tick", 0)),
        build_cost=float(data.get("build_cost", 0.0)),
    )


def _connection_to_dict(connection: InternalConnection) -> dict[str, object]:
    """Serialize an internal facility connection."""

    return {
        "id": connection.id,
        "source_component_id": connection.source_component_id,
        "source_port_id": connection.source_port_id,
        "destination_component_id": connection.destination_component_id,
        "destination_port_id": connection.destination_port_id,
    }


def _connection_from_dict(data: dict[str, Any]) -> InternalConnection:
    """Deserialize an internal facility connection."""

    return InternalConnection(
        id=str(data["id"]),
        source_component_id=str(data["source_component_id"]),
        source_port_id=str(data["source_port_id"]),
        destination_component_id=str(data["destination_component_id"]),
        destination_port_id=str(data["destination_port_id"]),
    )


def _facility_to_dict(facility: Facility | None) -> dict[str, object] | None:
    """Serialize a facility, or return None if absent."""

    if facility is None:
        return None
    return {
        "components": [
            _component_to_dict(component)
            for component in sorted(facility.components.values(), key=lambda item: item.id)
        ],
        "connections": [
            _connection_to_dict(connection)
            for connection in sorted(facility.connections.values(), key=lambda item: item.id)
        ],
    }


def _facility_from_dict(data: object) -> Facility | None:
    """Deserialize a facility, or return None if absent."""

    if not isinstance(data, dict):
        return None
    components: dict[str, FacilityComponent] = {}
    for component_data in data.get("components", []):
        component = _component_from_dict(component_data)
        components[component.id] = component
    connections: dict[str, InternalConnection] = {}
    for connection_data in data.get("connections", []):
        connection = _connection_from_dict(connection_data)
        connections[connection.id] = connection
    return Facility(components=components, connections=connections)


def _node_to_dict(node: NetworkNode) -> dict[str, object]:
    """Serialize a network node."""

    return {
        "id": node.id,
        "name": node.name,
        "world_id": node.world_id,
        "kind": node.kind.value,
        "outpost_kind": None if node.outpost_kind is None else node.outpost_kind.value,
        "inventory": _cargo_map_to_dict(node.inventory),
        "production": _cargo_map_to_dict(node.production),
        "demand": _cargo_map_to_dict(node.demand),
        "resource_inventory": _resource_map_to_dict(node.resource_inventory),
        "resource_production": _resource_map_to_dict(node.resource_production),
        "resource_demand": _resource_map_to_dict(node.resource_demand),
        "storage_capacity": node.storage_capacity,
        "transfer_limit_per_tick": node.transfer_limit_per_tick,
        "layout_x": node.layout_x,
        "layout_y": node.layout_y,
        "recipe": _recipe_to_dict(node.recipe),
        "resource_recipe": _resource_recipe_to_dict(node.resource_recipe),
        "resource_deposit_id": node.resource_deposit_id,
        "facility": _facility_to_dict(node.facility),
        "construction_project_id": node.construction_project_id,
        "stock_targets": _cargo_map_to_dict(node.stock_targets),
        "buffer_priority": node.buffer_priority,
        "push_logic": node.push_logic,
        "pull_logic": node.pull_logic,
    }


def _node_from_dict(data: dict[str, Any]) -> NetworkNode:
    """Deserialize a network node."""

    return NetworkNode(
        id=str(data["id"]),
        name=str(data["name"]),
        world_id=str(data["world_id"]),
        kind=NodeKind(str(data["kind"])),
        outpost_kind=(
            None if data.get("outpost_kind") is None else OutpostKind(str(data["outpost_kind"]))
        ),
        inventory=_cargo_map_from_dict(data.get("inventory", {})),
        production=_cargo_map_from_dict(data.get("production", {})),
        demand=_cargo_map_from_dict(data.get("demand", {})),
        resource_inventory=_resource_map_from_dict(data.get("resource_inventory", {})),
        resource_production=_resource_map_from_dict(data.get("resource_production", {})),
        resource_demand=_resource_map_from_dict(data.get("resource_demand", {})),
        storage_capacity=int(data.get("storage_capacity", 1_000)),
        transfer_limit_per_tick=int(data.get("transfer_limit_per_tick", 24)),
        layout_x=None if data.get("layout_x") is None else float(data["layout_x"]),
        layout_y=None if data.get("layout_y") is None else float(data["layout_y"]),
        recipe=_recipe_from_dict(data.get("recipe")),
        resource_recipe=_resource_recipe_from_dict(data.get("resource_recipe")),
        resource_deposit_id=(
            None if data.get("resource_deposit_id") is None else str(data["resource_deposit_id"])
        ),
        facility=_facility_from_dict(data.get("facility")),
        construction_project_id=data.get("construction_project_id"),
        stock_targets=_cargo_map_from_dict(data.get("stock_targets", {})),
        buffer_priority=int(data.get("buffer_priority", 0)),
        push_logic=bool(data.get("push_logic", True)),
        pull_logic=bool(data.get("pull_logic", True)),
    )


def _construction_project_to_dict(project: ConstructionProject) -> dict[str, object]:
    """Serialize a staged construction project."""

    return {
        "id": project.id,
        "target_node_id": project.target_node_id,
        "required_cargo": _cargo_map_to_dict(project.required_cargo),
        "delivered_cargo": _cargo_map_to_dict(project.delivered_cargo),
        "status": project.status.value,
        "cash_cost": float(project.cash_cost),
    }


def _construction_project_from_dict(data: dict[str, Any]) -> ConstructionProject:
    """Deserialize a staged construction project."""

    return ConstructionProject(
        id=str(data["id"]),
        target_node_id=str(data["target_node_id"]),
        required_cargo=_cargo_map_from_dict(data.get("required_cargo", {})),
        delivered_cargo=_cargo_map_from_dict(data.get("delivered_cargo", {})),
        status=ConstructionStatus(str(data.get("status", ConstructionStatus.PENDING.value))),
        cash_cost=float(data.get("cash_cost", 0.0)),
    )


def _track_point_to_dict(point: TrackPoint) -> dict[str, float]:
    """Serialize a local rail-alignment point."""

    return {"x": float(point.x), "y": float(point.y)}


def _track_point_from_dict(data: object) -> TrackPoint:
    """Deserialize a local rail-alignment point."""

    if not isinstance(data, dict):
        raise ValueError("track alignment points must be objects")
    return TrackPoint(x=float(data["x"]), y=float(data["y"]))


def _track_signal_to_dict(signal: TrackSignal) -> dict[str, object]:
    """Serialize a rail signal."""

    return {
        "id": signal.id,
        "link_id": signal.link_id,
        "kind": signal.kind.value,
        "node_id": signal.node_id,
        "active": signal.active,
    }


def _track_signal_from_dict(data: dict[str, Any]) -> TrackSignal:
    """Deserialize a rail signal."""

    return TrackSignal(
        id=str(data["id"]),
        link_id=str(data["link_id"]),
        kind=TrackSignalKind(str(data.get("kind", TrackSignalKind.STOP.value))),
        node_id=None if data.get("node_id") is None else str(data["node_id"]),
        active=bool(data.get("active", True)),
    )


def _resource_deposit_to_dict(deposit: ResourceDeposit) -> dict[str, object]:
    """Serialize a resource deposit."""

    return {
        "id": deposit.id,
        "world_id": deposit.world_id,
        "resource_id": deposit.resource_id,
        "name": deposit.name,
        "grade": float(deposit.grade),
        "yield_per_tick": int(deposit.yield_per_tick),
        "discovered": deposit.discovered,
        "remaining_estimate": deposit.remaining_estimate,
    }


def _resource_deposit_from_dict(data: dict[str, Any]) -> ResourceDeposit:
    """Deserialize a resource deposit."""

    return ResourceDeposit(
        id=str(data["id"]),
        world_id=str(data["world_id"]),
        resource_id=str(data["resource_id"]),
        name=str(data["name"]),
        grade=float(data.get("grade", 1.0)),
        yield_per_tick=int(data.get("yield_per_tick", 0)),
        discovered=bool(data.get("discovered", True)),
        remaining_estimate=(
            None if data.get("remaining_estimate") is None else int(data["remaining_estimate"])
        ),
    )


def _space_site_to_dict(site: SpaceSite) -> dict[str, object]:
    """Serialize a space site."""

    return {
        "id": site.id,
        "name": site.name,
        "resource_id": site.resource_id,
        "travel_ticks": site.travel_ticks,
        "base_yield": site.base_yield,
        "discovered": site.discovered,
        "cargo_type": site.cargo_type.value if site.cargo_type is not None else None,
    }


def _space_site_from_dict(data: dict[str, Any]) -> SpaceSite:
    """Deserialize a space site."""

    raw_cargo = data.get("cargo_type")
    cargo_type = CargoType(raw_cargo) if raw_cargo else None
    return SpaceSite(
        id=str(data["id"]),
        name=str(data["name"]),
        resource_id=str(data["resource_id"]),
        travel_ticks=int(data["travel_ticks"]),
        base_yield=int(data["base_yield"]),
        discovered=bool(data.get("discovered", True)),
        cargo_type=cargo_type,
    )


def _mining_mission_to_dict(mission: MiningMission) -> dict[str, object]:
    """Serialize a mining mission."""

    return {
        "id": mission.id,
        "site_id": mission.site_id,
        "launch_node_id": mission.launch_node_id,
        "return_node_id": mission.return_node_id,
        "status": mission.status.value,
        "ticks_remaining": mission.ticks_remaining,
        "fuel_input": mission.fuel_input,
        "power_input": mission.power_input,
        "expected_yield": mission.expected_yield,
        "reserved_power": mission.reserved_power,
        "fuel_consumed": mission.fuel_consumed,
    }


def _mining_mission_from_dict(data: dict[str, Any]) -> MiningMission:
    """Deserialize a mining mission."""

    return MiningMission(
        id=str(data["id"]),
        site_id=str(data["site_id"]),
        launch_node_id=str(data["launch_node_id"]),
        return_node_id=str(data["return_node_id"]),
        status=MiningMissionStatus(str(data.get("status", MiningMissionStatus.PREPARING.value))),
        ticks_remaining=int(data["ticks_remaining"]),
        fuel_input=int(data.get("fuel_input", 0)),
        power_input=int(data.get("power_input", 0)),
        expected_yield=int(data["expected_yield"]),
        reserved_power=int(data.get("reserved_power", 0)),
        fuel_consumed=int(data.get("fuel_consumed", data.get("fuel_input", 0))),
    )


def _gate_support_to_dict(support: GatePowerSupport) -> dict[str, object]:
    """Serialize a gate power support rule."""

    return {
        "id": support.id,
        "link_id": support.link_id,
        "node_id": support.node_id,
        "inputs": _resource_map_to_dict(support.inputs),
        "power_bonus": int(support.power_bonus),
        "active": support.active,
    }


def _gate_support_from_dict(data: dict[str, Any]) -> GatePowerSupport:
    """Deserialize a gate power support rule."""

    return GatePowerSupport(
        id=str(data["id"]),
        link_id=str(data["link_id"]),
        node_id=str(data["node_id"]),
        inputs=_resource_map_from_dict(data.get("inputs", {})),
        power_bonus=int(data.get("power_bonus", 0)),
        active=bool(data.get("active", True)),
    )


def _power_plant_to_dict(plant: PowerPlant) -> dict[str, object]:
    """Serialize a power plant."""

    return {
        "id": plant.id,
        "node_id": plant.node_id,
        "kind": plant.kind.value,
        "inputs": _resource_map_to_dict(plant.inputs),
        "power_output": int(plant.power_output),
        "active": plant.active,
    }


def _power_plant_from_dict(data: dict[str, Any]) -> PowerPlant:
    """Deserialize a power plant."""

    return PowerPlant(
        id=str(data["id"]),
        node_id=str(data["node_id"]),
        kind=PowerPlantKind(str(data.get("kind", PowerPlantKind.THERMAL.value))),
        inputs=_resource_map_from_dict(data.get("inputs", {})),
        power_output=int(data.get("power_output", 0)),
        active=bool(data.get("active", True)),
    )


def _link_to_dict(link: NetworkLink) -> dict[str, object]:
    """Serialize a network link."""

    payload: dict[str, object] = {
        "id": link.id,
        "origin": link.origin,
        "destination": link.destination,
        "mode": link.mode.value,
        "travel_ticks": link.travel_ticks,
        "capacity_per_tick": link.capacity_per_tick,
        "power_required": link.power_required,
        "power_source_world_id": link.power_source_world_id,
        "active": link.active,
        "bidirectional": link.bidirectional,
        "build_cost": link.build_cost,
        "build_time": link.build_time,
    }
    if link.alignment:
        payload["alignment"] = [_track_point_to_dict(point) for point in link.alignment]
    return payload


def _link_from_dict(data: dict[str, Any]) -> NetworkLink:
    """Deserialize a network link."""

    return NetworkLink(
        id=str(data["id"]),
        origin=str(data["origin"]),
        destination=str(data["destination"]),
        mode=LinkMode(str(data["mode"])),
        travel_ticks=int(data["travel_ticks"]),
        capacity_per_tick=int(data["capacity_per_tick"]),
        power_required=int(data.get("power_required", 0)),
        power_source_world_id=data.get("power_source_world_id"),
        active=bool(data.get("active", True)),
        bidirectional=bool(data.get("bidirectional", True)),
        build_cost=float(data.get("build_cost", 0.0)),
        build_time=int(data.get("build_time", 0)),
        alignment=tuple(_track_point_from_dict(point) for point in data.get("alignment", [])),
    )


def _disruption_to_dict(disruption: NetworkDisruption) -> dict[str, object]:
    """Serialize a network disruption."""

    return {
        "id": disruption.id,
        "link_id": disruption.link_id,
        "start_tick": disruption.start_tick,
        "end_tick": disruption.end_tick,
        "capacity_multiplier": disruption.capacity_multiplier,
        "reason": disruption.reason,
    }


def _disruption_from_dict(data: dict[str, Any]) -> NetworkDisruption:
    """Deserialize a network disruption."""

    return NetworkDisruption(
        id=str(data["id"]),
        link_id=str(data["link_id"]),
        start_tick=int(data["start_tick"]),
        end_tick=int(data["end_tick"]),
        capacity_multiplier=float(data.get("capacity_multiplier", 0.0)),
        reason=str(data.get("reason", "maintenance")),
    )


def _train_to_dict(train: FreightTrain) -> dict[str, object]:
    """Serialize a freight train."""

    return {
        "id": train.id,
        "name": train.name,
        "node_id": train.node_id,
        "capacity": train.capacity,
        "consist": train.consist.value,
        "cargo_type": _cargo_key(train.cargo_type),
        "cargo_units": train.cargo_units,
        "status": train.status.value,
        "destination": train.destination,
        "route_node_ids": list(train.route_node_ids),
        "route_link_ids": list(train.route_link_ids),
        "remaining_ticks": train.remaining_ticks,
        "order_id": train.order_id,
        "blocked_reason": train.blocked_reason,
        "dispatch_cost": train.dispatch_cost,
        "variable_cost_per_unit": train.variable_cost_per_unit,
        "revenue_modifier": train.revenue_modifier,
    }


def _train_from_dict(data: dict[str, Any]) -> FreightTrain:
    """Deserialize a freight train."""

    cargo_type = data.get("cargo_type")
    return FreightTrain(
        id=str(data["id"]),
        name=str(data["name"]),
        node_id=str(data["node_id"]),
        capacity=int(data["capacity"]),
        consist=TrainConsist(str(data.get("consist", TrainConsist.GENERAL.value))),
        cargo_type=None if cargo_type is None else CargoType(str(cargo_type)),
        cargo_units=int(data.get("cargo_units", 0)),
        status=TrainStatus(str(data.get("status", TrainStatus.IDLE.value))),
        destination=data.get("destination"),
        route_node_ids=tuple(str(item) for item in data.get("route_node_ids", [])),
        route_link_ids=tuple(str(item) for item in data.get("route_link_ids", [])),
        remaining_ticks=int(data.get("remaining_ticks", 0)),
        order_id=data.get("order_id"),
        blocked_reason=data.get("blocked_reason"),
        dispatch_cost=float(data.get("dispatch_cost", 60.0)),
        variable_cost_per_unit=float(data.get("variable_cost_per_unit", 1.0)),
        revenue_modifier=float(data.get("revenue_modifier", 1.0)),
    )


def _order_to_dict(order: FreightOrder) -> dict[str, object]:
    """Serialize a freight order."""

    return {
        "id": order.id,
        "train_id": order.train_id,
        "origin": order.origin,
        "destination": order.destination,
        "cargo_type": order.cargo_type.value,
        "requested_units": order.requested_units,
        "priority": order.priority,
        "delivered_units": order.delivered_units,
        "active": order.active,
    }


def _order_from_dict(data: dict[str, Any]) -> FreightOrder:
    """Deserialize a freight order."""

    return FreightOrder(
        id=str(data["id"]),
        train_id=str(data["train_id"]),
        origin=str(data["origin"]),
        destination=str(data["destination"]),
        cargo_type=CargoType(str(data["cargo_type"])),
        requested_units=int(data["requested_units"]),
        priority=int(data.get("priority", 100)),
        delivered_units=int(data.get("delivered_units", 0)),
        active=bool(data.get("active", True)),
    )


def _schedule_to_dict(schedule: FreightSchedule) -> dict[str, object]:
    """Serialize a freight schedule."""

    return {
        "id": schedule.id,
        "train_id": schedule.train_id,
        "origin": schedule.origin,
        "destination": schedule.destination,
        "stops": list(schedule.stops),
        "cargo_type": schedule.cargo_type.value,
        "units_per_departure": schedule.units_per_departure,
        "interval_ticks": schedule.interval_ticks,
        "next_departure_tick": schedule.next_departure_tick,
        "priority": schedule.priority,
        "active": schedule.active,
        "return_to_origin": schedule.return_to_origin,
        "delivered_units": schedule.delivered_units,
        "trips_completed": schedule.trips_completed,
        "trips_dispatched": schedule.trips_dispatched,
    }


def _schedule_from_dict(data: dict[str, Any]) -> FreightSchedule:
    """Deserialize a freight schedule."""

    return FreightSchedule(
        id=str(data["id"]),
        train_id=str(data["train_id"]),
        origin=str(data["origin"]),
        destination=str(data["destination"]),
        stops=tuple(str(item) for item in data.get("stops", [])),
        cargo_type=CargoType(str(data["cargo_type"])),
        units_per_departure=int(data["units_per_departure"]),
        interval_ticks=int(data["interval_ticks"]),
        next_departure_tick=int(data.get("next_departure_tick", 1)),
        priority=int(data.get("priority", 100)),
        active=bool(data.get("active", True)),
        return_to_origin=bool(data.get("return_to_origin", True)),
        delivered_units=int(data.get("delivered_units", 0)),
        trips_completed=int(data.get("trips_completed", 0)),
        trips_dispatched=int(data.get("trips_dispatched", 0)),
    )


def _gate_status_to_dict(status: GatePowerStatus) -> dict[str, object]:
    """Serialize a gate power status."""

    return {
        "link_id": status.link_id,
        "source_world_id": status.source_world_id,
        "source_world_name": status.source_world_name,
        "power_required": status.power_required,
        "power_available": status.power_available,
        "power_shortfall": status.power_shortfall,
        "powered": status.powered,
        "active": status.active,
        "slot_capacity": status.slot_capacity,
        "slots_used": status.slots_used,
        "charge_pct": status.charge_pct,
        "next_activation_tick": status.next_activation_tick,
        "slot_cargo": _cargo_map_to_dict(status.slot_cargo),
        "base_power_required": (
            status.power_required if status.base_power_required is None else status.base_power_required
        ),
        "resource_power_bonus": status.resource_power_bonus,
        "support_id": status.support_id,
        "support_node_id": status.support_node_id,
        "support_inputs": _resource_map_to_dict(status.support_inputs),
        "support_missing": _resource_map_to_dict(status.support_missing),
    }


def _gate_status_from_dict(data: dict[str, Any]) -> GatePowerStatus:
    """Deserialize a gate power status."""

    return GatePowerStatus(
        link_id=str(data["link_id"]),
        source_world_id=str(data["source_world_id"]),
        source_world_name=str(data["source_world_name"]),
        power_required=int(data["power_required"]),
        power_available=int(data["power_available"]),
        power_shortfall=int(data["power_shortfall"]),
        powered=bool(data["powered"]),
        active=bool(data["active"]),
        slot_capacity=int(data["slot_capacity"]),
        slots_used=int(data.get("slots_used", 0)),
        charge_pct=float(data.get("charge_pct", 1.0)),
        next_activation_tick=(
            None if data.get("next_activation_tick") is None else int(data["next_activation_tick"])
        ),
        slot_cargo=_cargo_map_from_dict(data.get("slot_cargo", {})),
        base_power_required=(
            None if data.get("base_power_required") is None else int(data["base_power_required"])
        ),
        resource_power_bonus=int(data.get("resource_power_bonus", 0)),
        support_id=None if data.get("support_id") is None else str(data["support_id"]),
        support_node_id=None if data.get("support_node_id") is None else str(data["support_node_id"]),
        support_inputs=_resource_map_from_dict(data.get("support_inputs", {})),
        support_missing=_resource_map_from_dict(data.get("support_missing", {})),
    )


def _contract_to_dict(contract: Contract) -> dict[str, object]:
    """Serialize a contract."""

    return {
        "id": contract.id,
        "kind": contract.kind.value,
        "title": contract.title,
        "destination_node_id": contract.destination_node_id,
        "cargo_type": None if contract.cargo_type is None else contract.cargo_type.value,
        "target_world_id": contract.target_world_id,
        "target_link_id": contract.target_link_id,
        "target_units": contract.target_units,
        "due_tick": contract.due_tick,
        "reward_cash": contract.reward_cash,
        "penalty_cash": contract.penalty_cash,
        "reward_reputation": contract.reward_reputation,
        "penalty_reputation": contract.penalty_reputation,
        "client": contract.client,
        "delivered_units": contract.delivered_units,
        "progress": contract.progress,
        "status": contract.status.value,
        "resolved_tick": contract.resolved_tick,
    }


def _contract_from_dict(data: dict[str, Any]) -> Contract:
    """Deserialize a contract."""

    cargo_type_value = data.get("cargo_type")
    return Contract(
        id=str(data["id"]),
        kind=ContractKind(str(data.get("kind", ContractKind.CARGO_DELIVERY.value))),
        title=str(data.get("title", data["id"])),
        destination_node_id=(
            None if data.get("destination_node_id") is None else str(data["destination_node_id"])
        ),
        cargo_type=None if cargo_type_value is None else CargoType(str(cargo_type_value)),
        target_world_id=(
            None if data.get("target_world_id") is None else str(data["target_world_id"])
        ),
        target_link_id=(
            None if data.get("target_link_id") is None else str(data["target_link_id"])
        ),
        target_units=int(data["target_units"]),
        due_tick=int(data["due_tick"]),
        reward_cash=float(data.get("reward_cash", 0.0)),
        penalty_cash=float(data.get("penalty_cash", 0.0)),
        reward_reputation=int(data.get("reward_reputation", 0)),
        penalty_reputation=int(data.get("penalty_reputation", 0)),
        client=data.get("client"),
        delivered_units=int(data.get("delivered_units", 0)),
        progress=int(data.get("progress", 0)),
        status=ContractStatus(str(data.get("status", ContractStatus.ACTIVE.value))),
        resolved_tick=(
            None if data.get("resolved_tick") is None else int(data["resolved_tick"])
        ),
    )


def _finance_to_dict(finance: FinanceState) -> dict[str, float]:
    """Serialize finance state."""

    return {
        "cash": finance.cash,
        "revenue_total": finance.revenue_total,
        "costs_total": finance.costs_total,
        "revenue_this_tick": finance.revenue_this_tick,
        "costs_this_tick": finance.costs_this_tick,
    }


def _finance_from_dict(data: object) -> FinanceState:
    """Deserialize finance state."""

    if not isinstance(data, dict):
        return FinanceState()
    return FinanceState(
        cash=float(data.get("cash", 10_000.0)),
        revenue_total=float(data.get("revenue_total", 0.0)),
        costs_total=float(data.get("costs_total", 0.0)),
        revenue_this_tick=float(data.get("revenue_this_tick", 0.0)),
        costs_this_tick=float(data.get("costs_this_tick", 0.0)),
    )


def _json_safe_value(value: object) -> object:
    """Return a deterministic JSON-safe copy of transient diagnostic payloads."""

    if isinstance(value, dict):
        return {
            str(key.value if hasattr(key, "value") else key): _json_safe_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0].value if hasattr(pair[0], "value") else pair[0]),
            )
        }
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _facility_block_entry_to_dict(entry: object) -> dict[str, object]:
    """Serialize one structured facility block entry."""

    if not isinstance(entry, dict):
        return {}
    return {
        "node": str(entry.get("node", "")),
        "component": str(entry.get("component", "")),
        "kind": str(entry.get("kind", "")),
        "reason": str(entry.get("reason").value if hasattr(entry.get("reason"), "value") else entry.get("reason", "")),
        "detail": _json_safe_value(entry.get("detail", {})),
    }


def _facility_block_entries_from_dict(data: object) -> list[dict[str, object]]:
    """Deserialize structured facility block entries."""

    if not isinstance(data, list):
        return []
    entries: list[dict[str, object]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        entries.append(
            {
                "node": str(entry.get("node", "")),
                "component": str(entry.get("component", "")),
                "kind": str(entry.get("kind", "")),
                "reason": str(entry.get("reason", "")),
                "detail": _json_safe_value(entry.get("detail", {})),
            }
        )
    return entries


def state_to_dict(state: GameState) -> dict[str, object]:
    """Serialize game state to JSON-safe data."""

    return {
        "tick": state.tick,
        "worlds": [_world_to_dict(world) for world in sorted(state.worlds.values(), key=lambda item: item.id)],
        "resource_deposits": [
            _resource_deposit_to_dict(deposit)
            for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id)
        ],
        "space_sites": [
            _space_site_to_dict(site)
            for site in sorted(state.space_sites.values(), key=lambda item: item.id)
        ],
        "mining_missions": [
            _mining_mission_to_dict(mission)
            for mission in sorted(state.mining_missions.values(), key=lambda item: item.id)
        ],
        "gate_supports": [
            _gate_support_to_dict(support)
            for support in sorted(state.gate_supports.values(), key=lambda item: item.id)
        ],
        "power_plants": [
            _power_plant_to_dict(plant)
            for plant in sorted(state.power_plants.values(), key=lambda item: item.id)
        ],
        "nodes": [_node_to_dict(node) for node in sorted(state.nodes.values(), key=lambda item: item.id)],
        "links": [_link_to_dict(link) for link in sorted(state.links.values(), key=lambda item: item.id)],
        "track_signals": [
            _track_signal_to_dict(signal)
            for signal in sorted(state.track_signals.values(), key=lambda item: item.id)
        ],
        "construction_projects": [
            _construction_project_to_dict(project)
            for project in sorted(state.construction_projects.values(), key=lambda item: item.id)
        ],
        "trains": [_train_to_dict(train) for train in sorted(state.trains.values(), key=lambda item: item.id)],
        "orders": [_order_to_dict(order) for order in sorted(state.orders.values(), key=lambda item: item.id)],
        "schedules": [
            _schedule_to_dict(schedule)
            for schedule in sorted(state.schedules.values(), key=lambda item: item.id)
        ],
        "disruptions": [
            _disruption_to_dict(disruption)
            for disruption in sorted(state.disruptions.values(), key=lambda item: item.id)
        ],
        "shortages": {
            node_id: _cargo_map_to_dict(cargo_map)
            for node_id, cargo_map in sorted(state.shortages.items())
        },
        "gate_statuses": [
            _gate_status_to_dict(status)
            for status in sorted(state.gate_statuses.values(), key=lambda item: item.link_id)
        ],
        "link_usage_this_tick": {
            link_id: int(used)
            for link_id, used in sorted(state.link_usage_this_tick.items())
        },
        "power_generation_this_tick": {
            world_id: int(power)
            for world_id, power in sorted(state.power_generation_this_tick.items())
        },
        "facility_block_entries": [
            payload
            for payload in (
                _facility_block_entry_to_dict(entry)
                for entry in state.facility_block_entries
            )
            if payload
        ],
        "facility_power_contribution": {
            world_id: int(power)
            for world_id, power in sorted(state.facility_power_contribution.items())
        },
        "rail_block_reservations": {
            link_id: str(train_id)
            for link_id, train_id in sorted(state.rail_block_reservations.items())
        },
        "finance": _finance_to_dict(state.finance),
        "contracts": [
            _contract_to_dict(contract)
            for contract in sorted(state.contracts.values(), key=lambda item: item.id)
        ],
        "reputation": state.reputation,
        "month_length": state.month_length,
        "economic_identity_enabled": state.economic_identity_enabled,
    }


def state_from_dict(data: dict[str, Any]) -> GameState:
    """Deserialize game state from JSON-safe data."""

    state = GameState(
        tick=int(data.get("tick", 0)),
        finance=_finance_from_dict(data.get("finance")),
        reputation=int(data.get("reputation", 0)),
        month_length=int(data.get("month_length", 30)),
        economic_identity_enabled=bool(data.get("economic_identity_enabled", False)),
    )
    for world_data in data.get("worlds", []):
        state.add_world(_world_from_dict(world_data))
    for deposit_data in data.get("resource_deposits", []):
        state.add_resource_deposit(_resource_deposit_from_dict(deposit_data))
    for site_data in data.get("space_sites", []):
        state.add_space_site(_space_site_from_dict(site_data))
    for node_data in data.get("nodes", []):
        state.add_node(_node_from_dict(node_data))
    for project_data in data.get("construction_projects", []):
        state.add_construction_project(_construction_project_from_dict(project_data))
    for mission_data in data.get("mining_missions", []):
        state.add_mining_mission(_mining_mission_from_dict(mission_data))
    for link_data in data.get("links", []):
        state.add_link(_link_from_dict(link_data))
    for signal_data in data.get("track_signals", []):
        state.add_track_signal(_track_signal_from_dict(signal_data))
    for support_data in data.get("gate_supports", []):
        state.add_gate_support(_gate_support_from_dict(support_data))
    for plant_data in data.get("power_plants", []):
        state.add_power_plant(_power_plant_from_dict(plant_data))
    for train_data in data.get("trains", []):
        state.add_train(_train_from_dict(train_data))
    for order_data in data.get("orders", []):
        state.add_order(_order_from_dict(order_data))
    for schedule_data in data.get("schedules", []):
        state.add_schedule(_schedule_from_dict(schedule_data))
    for disruption_data in data.get("disruptions", []):
        state.add_disruption(_disruption_from_dict(disruption_data))
    for contract_data in data.get("contracts", []):
        state.add_contract(_contract_from_dict(contract_data))
    shortages = data.get("shortages", {})
    if isinstance(shortages, dict):
        state.shortages = {
            str(node_id): _cargo_map_from_dict(cargo_map)
            for node_id, cargo_map in shortages.items()
        }
    for status_data in data.get("gate_statuses", []):
        status = _gate_status_from_dict(status_data)
        state.gate_statuses[status.link_id] = status
    link_usage = data.get("link_usage_this_tick", {})
    if isinstance(link_usage, dict):
        state.link_usage_this_tick = {
            str(link_id): int(used)
            for link_id, used in link_usage.items()
        }
    power_generation = data.get("power_generation_this_tick", {})
    if isinstance(power_generation, dict):
        state.power_generation_this_tick = {
            str(world_id): int(power)
            for world_id, power in power_generation.items()
        }
    state.facility_block_entries = _facility_block_entries_from_dict(
        data.get("facility_block_entries", [])
    )
    state.facility_blocked = {}
    for entry in state.facility_block_entries:
        node_id = str(entry.get("node", ""))
        component_id = str(entry.get("component", ""))
        if not node_id or not component_id:
            continue
        state.facility_blocked.setdefault(node_id, []).append(component_id)
    state.facility_blocked = {
        node_id: sorted(set(component_ids))
        for node_id, component_ids in sorted(state.facility_blocked.items())
    }
    facility_power = data.get("facility_power_contribution", {})
    if isinstance(facility_power, dict):
        state.facility_power_contribution = {
            str(world_id): int(power)
            for world_id, power in facility_power.items()
        }
    rail_block_reservations = data.get("rail_block_reservations", {})
    if isinstance(rail_block_reservations, dict):
        state.rail_block_reservations = {
            str(link_id): str(train_id)
            for link_id, train_id in rail_block_reservations.items()
        }
    return state


def simulation_to_dict(simulation: TickSimulation) -> dict[str, object]:
    """Serialize a tick simulation save file."""

    return {
        "format": SAVE_FORMAT,
        "version": SAVE_VERSION,
        "status": simulation.status,
        "state": state_to_dict(simulation.state),
        "reports": simulation.reports,
        "monthly_reports": simulation.monthly_reports,
    }


def simulation_from_dict(data: dict[str, Any]) -> TickSimulation:
    """Deserialize a tick simulation save file."""

    if data.get("format") != SAVE_FORMAT:
        raise ValueError("not a GateRail tick simulation save")
    if int(data.get("version", 0)) != SAVE_VERSION:
        raise ValueError(f"unsupported GateRail save version: {data.get('version')}")
    simulation = TickSimulation(
        state=state_from_dict(data["state"]),
        status=str(data.get("status", "running")),
    )
    reports = data.get("reports", [])
    monthly_reports = data.get("monthly_reports", [])
    simulation.reports = list(reports) if isinstance(reports, list) else []
    simulation.monthly_reports = list(monthly_reports) if isinstance(monthly_reports, list) else []
    return simulation


def save_simulation(simulation: TickSimulation, path: str | Path) -> None:
    """Write a simulation save file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(simulation_to_dict(simulation), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_simulation(path: str | Path) -> TickSimulation:
    """Read a simulation save file."""

    source = Path(path)
    if not source.exists():
        raise ValueError(f"save file not found: {source}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("save file root must be an object")
    return simulation_from_dict(data)
