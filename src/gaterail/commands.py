"""Player command contract for Stage 2 clients."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, TypeAlias

from gaterail.cargo import CargoType
from gaterail.construction import (
    DEFAULT_GATE_CAPACITY_PER_TICK,
    DEFAULT_GATE_POWER_REQUIRED,
    DEFAULT_GATE_TRAVEL_TICKS,
    DEFAULT_RAIL_CAPACITY_PER_TICK,
    facility_component_build_cost,
    link_build_cost,
    link_build_time,
    node_build_cost,
    node_default_storage,
    node_default_transfer,
    node_upgrade_cost,
    train_purchase_cost,
    travel_ticks_from_layout_distance,
)
from gaterail.models import (
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    InternalConnection,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    PortDirection,
    TrackPoint,
)
from gaterail.traffic import effective_link_capacity
from gaterail.transport import shortest_route


@dataclass(frozen=True, slots=True)
class SetScheduleEnabled:
    """Enable or disable an existing recurring schedule."""

    schedule_id: str
    enabled: bool
    type: Literal["SetScheduleEnabled"] = "SetScheduleEnabled"


@dataclass(frozen=True, slots=True)
class DispatchOrder:
    """Create a one-shot freight order for dispatch by the simulation loop."""

    order_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    requested_units: int
    priority: int = 100
    type: Literal["DispatchOrder"] = "DispatchOrder"


@dataclass(frozen=True, slots=True)
class CancelOrder:
    """Cancel a pending one-shot freight order."""

    order_id: str
    type: Literal["CancelOrder"] = "CancelOrder"


@dataclass(frozen=True, slots=True)
class BuildNode:
    """Construct a logistics node on an existing world."""

    node_id: str
    world_id: str
    kind: NodeKind
    name: str
    storage_capacity: int | None = None
    transfer_limit_per_tick: int | None = None
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["BuildNode"] = "BuildNode"


@dataclass(frozen=True, slots=True)
class PreviewBuildNode:
    """Preview a logistics node build without mutating state."""

    node_id: str
    world_id: str
    kind: NodeKind
    name: str
    storage_capacity: int | None = None
    transfer_limit_per_tick: int | None = None
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["PreviewBuildNode"] = "PreviewBuildNode"


@dataclass(frozen=True, slots=True)
class BuildLink:
    """Construct a transport link between two nodes."""

    link_id: str
    origin: str
    destination: str
    mode: LinkMode
    travel_ticks: int | None = None
    capacity_per_tick: int = DEFAULT_RAIL_CAPACITY_PER_TICK
    power_required: int = 0
    power_source_world_id: str | None = None
    bidirectional: bool = True
    alignment: tuple[TrackPoint, ...] = ()
    type: Literal["BuildLink"] = "BuildLink"


@dataclass(frozen=True, slots=True)
class PreviewBuildLink:
    """Preview a transport link build without mutating state."""

    link_id: str
    origin: str
    destination: str
    mode: LinkMode = LinkMode.RAIL
    travel_ticks: int | None = None
    capacity_per_tick: int = DEFAULT_RAIL_CAPACITY_PER_TICK
    power_required: int = 0
    power_source_world_id: str | None = None
    bidirectional: bool = True
    alignment: tuple[TrackPoint, ...] = ()
    type: Literal["PreviewBuildLink"] = "PreviewBuildLink"


@dataclass(frozen=True, slots=True)
class DemolishLink:
    """Demolish an existing transport link."""

    link_id: str
    type: Literal["DemolishLink"] = "DemolishLink"


@dataclass(frozen=True, slots=True)
class PurchaseTrain:
    """Purchase a new freight train."""

    train_id: str
    name: str
    node_id: str
    capacity: int
    type: Literal["PurchaseTrain"] = "PurchaseTrain"


@dataclass(frozen=True, slots=True)
class PreviewPurchaseTrain:
    """Preview a freight-train purchase without mutating state."""

    train_id: str
    name: str
    node_id: str
    capacity: int
    type: Literal["PreviewPurchaseTrain"] = "PreviewPurchaseTrain"


@dataclass(frozen=True, slots=True)
class CreateSchedule:
    """Create a recurring freight route schedule."""

    schedule_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    units_per_departure: int
    interval_ticks: int
    next_departure_tick: int | None = None
    priority: int = 100
    active: bool = True
    return_to_origin: bool = True
    type: Literal["CreateSchedule"] = "CreateSchedule"


@dataclass(frozen=True, slots=True)
class PreviewCreateSchedule:
    """Preview a recurring freight route schedule without mutating state."""

    schedule_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    units_per_departure: int
    interval_ticks: int
    next_departure_tick: int | None = None
    priority: int = 100
    active: bool = True
    return_to_origin: bool = True
    type: Literal["PreviewCreateSchedule"] = "PreviewCreateSchedule"


@dataclass(frozen=True, slots=True)
class UpgradeNode:
    """Upgrade an existing node's storage and transfer capacity."""

    node_id: str
    storage_capacity_increase: int
    transfer_limit_increase: int
    type: Literal["UpgradeNode"] = "UpgradeNode"


@dataclass(frozen=True, slots=True)
class BuildFacilityComponent:
    """Install a facility component on an existing node."""

    component_id: str
    node_id: str
    kind: FacilityComponentKind
    capacity: int = 0
    rate: int = 0
    power_required: int = 0
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    ports: tuple[FacilityPort, ...] = ()
    connections: tuple[InternalConnection, ...] = ()
    type: Literal["BuildFacilityComponent"] = "BuildFacilityComponent"


@dataclass(frozen=True, slots=True)
class PreviewBuildFacilityComponent:
    """Preview a facility component install without mutating state."""

    component_id: str
    node_id: str
    kind: FacilityComponentKind
    capacity: int = 0
    rate: int = 0
    power_required: int = 0
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    ports: tuple[FacilityPort, ...] = ()
    connections: tuple[InternalConnection, ...] = ()
    type: Literal["PreviewBuildFacilityComponent"] = "PreviewBuildFacilityComponent"


@dataclass(frozen=True, slots=True)
class DemolishFacilityComponent:
    """Remove an existing facility component from a node."""

    node_id: str
    component_id: str
    type: Literal["DemolishFacilityComponent"] = "DemolishFacilityComponent"


@dataclass(frozen=True, slots=True)
class PreviewDemolishFacilityComponent:
    """Preview facility-component demolition without mutating state."""

    node_id: str
    component_id: str
    type: Literal["PreviewDemolishFacilityComponent"] = "PreviewDemolishFacilityComponent"


@dataclass(frozen=True, slots=True)
class BuildInternalConnection:
    """Create a connection between two ports inside one facility."""

    node_id: str
    connection_id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str
    type: Literal["BuildInternalConnection"] = "BuildInternalConnection"


@dataclass(frozen=True, slots=True)
class PreviewBuildInternalConnection:
    """Preview an internal facility connection without mutating state."""

    node_id: str
    connection_id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str
    type: Literal["PreviewBuildInternalConnection"] = "PreviewBuildInternalConnection"


@dataclass(frozen=True, slots=True)
class RemoveInternalConnection:
    """Remove an existing internal facility connection."""

    node_id: str
    connection_id: str
    type: Literal["RemoveInternalConnection"] = "RemoveInternalConnection"


@dataclass(frozen=True, slots=True)
class PreviewRemoveInternalConnection:
    """Preview removing an internal facility connection."""

    node_id: str
    connection_id: str
    type: Literal["PreviewRemoveInternalConnection"] = "PreviewRemoveInternalConnection"


PlayerCommand: TypeAlias = (
    SetScheduleEnabled
    | DispatchOrder
    | CancelOrder
    | BuildNode
    | PreviewBuildNode
    | BuildLink
    | PreviewBuildLink
    | DemolishLink
    | PurchaseTrain
    | PreviewPurchaseTrain
    | CreateSchedule
    | PreviewCreateSchedule
    | UpgradeNode
    | BuildFacilityComponent
    | PreviewBuildFacilityComponent
    | DemolishFacilityComponent
    | PreviewDemolishFacilityComponent
    | BuildInternalConnection
    | PreviewBuildInternalConnection
    | RemoveInternalConnection
    | PreviewRemoveInternalConnection
)


def _command_type(data: dict[str, Any]) -> str:
    """Read the command type from a JSON-style command object."""

    raw_type = data.get("type") or data.get("command")
    if raw_type is None:
        raise ValueError("command missing type")
    return str(raw_type)


def _optional_int(value: object) -> int | None:
    """Parse optional integer command fields."""

    return None if value is None else int(value)


def _optional_float(value: object) -> float | None:
    """Parse optional float command fields."""

    return None if value is None else float(value)


def _layout_fields(data: dict[str, Any]) -> tuple[float | None, float | None]:
    """Read optional local-world layout fields from a command object."""

    layout = data.get("layout")
    if isinstance(layout, dict):
        return _optional_float(layout.get("x")), _optional_float(layout.get("y"))
    return _optional_float(data.get("layout_x")), _optional_float(data.get("layout_y"))


def _track_point_from_payload(data: object) -> TrackPoint:
    """Parse one local rail-alignment point from a command payload."""

    if isinstance(data, dict):
        return TrackPoint(x=float(data["x"]), y=float(data["y"]))
    if isinstance(data, (list, tuple)) and len(data) >= 2:
        return TrackPoint(x=float(data[0]), y=float(data[1]))
    raise ValueError("alignment points must be objects with x/y or two-item arrays")


def _alignment_fields(data: dict[str, Any]) -> tuple[TrackPoint, ...]:
    """Read optional local rail alignment metadata from a command object."""

    raw_alignment = data.get("alignment")
    if raw_alignment is None:
        raw_alignment = data.get("waypoints")
    if raw_alignment is None:
        raw_alignment = data.get("control_points")
    if raw_alignment is None:
        return ()
    if isinstance(raw_alignment, dict):
        raw_alignment = raw_alignment.get("points", [])
    if not isinstance(raw_alignment, (list, tuple)):
        raise ValueError("alignment must be a list of points")
    return tuple(_track_point_from_payload(point) for point in raw_alignment)


def command_from_dict(data: dict[str, Any]) -> PlayerCommand:
    """Build a player command from JSON-safe data."""

    command_type = _command_type(data)
    if command_type == "SetScheduleEnabled":
        return SetScheduleEnabled(
            schedule_id=str(data["schedule_id"]),
            enabled=bool(data["enabled"]),
        )
    if command_type == "DispatchOrder":
        return DispatchOrder(
            order_id=str(data["order_id"]),
            train_id=str(data["train_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            cargo_type=CargoType(str(data["cargo_type"])),
            requested_units=int(data["requested_units"]),
            priority=int(data.get("priority", 100)),
        )
    if command_type == "CancelOrder":
        return CancelOrder(order_id=str(data["order_id"]))
    if command_type in {"BuildNode", "PreviewBuildNode"}:
        storage = data.get("storage_capacity")
        transfer = data.get("transfer_limit_per_tick")
        layout_x, layout_y = _layout_fields(data)
        node_command = BuildNode if command_type == "BuildNode" else PreviewBuildNode
        return node_command(
            node_id=str(data["node_id"]),
            world_id=str(data["world_id"]),
            kind=NodeKind(str(data["kind"])),
            name=str(data["name"]),
            storage_capacity=None if storage is None else int(storage),
            transfer_limit_per_tick=None if transfer is None else int(transfer),
            layout_x=layout_x,
            layout_y=layout_y,
        )
    if command_type in {"BuildLink", "PreviewBuildLink"}:
        power_world = data.get("power_source_world_id")
        mode = LinkMode(str(data.get("mode", LinkMode.RAIL.value)))
        default_capacity = (
            DEFAULT_GATE_CAPACITY_PER_TICK
            if mode == LinkMode.GATE
            else DEFAULT_RAIL_CAPACITY_PER_TICK
        )
        default_power = DEFAULT_GATE_POWER_REQUIRED if mode == LinkMode.GATE else 0
        link_command = BuildLink if command_type == "BuildLink" else PreviewBuildLink
        return link_command(
            link_id=str(data["link_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            mode=mode,
            travel_ticks=_optional_int(data.get("travel_ticks")),
            capacity_per_tick=int(data.get("capacity_per_tick", default_capacity)),
            power_required=int(data.get("power_required", default_power)),
            power_source_world_id=None if power_world is None else str(power_world),
            bidirectional=bool(data.get("bidirectional", True)),
            alignment=_alignment_fields(data),
        )
    if command_type == "DemolishLink":
        return DemolishLink(link_id=str(data["link_id"]))
    if command_type in {"PurchaseTrain", "PreviewPurchaseTrain"}:
        train_command = PurchaseTrain if command_type == "PurchaseTrain" else PreviewPurchaseTrain
        return train_command(
            train_id=str(data["train_id"]),
            name=str(data["name"]),
            node_id=str(data["node_id"]),
            capacity=int(data["capacity"]),
        )
    if command_type in {"CreateSchedule", "PreviewCreateSchedule"}:
        next_departure = data.get("next_departure_tick")
        schedule_command = CreateSchedule if command_type == "CreateSchedule" else PreviewCreateSchedule
        return schedule_command(
            schedule_id=str(data["schedule_id"]),
            train_id=str(data["train_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            cargo_type=CargoType(str(data["cargo_type"])),
            units_per_departure=int(data["units_per_departure"]),
            interval_ticks=int(data["interval_ticks"]),
            next_departure_tick=None if next_departure is None else int(next_departure),
            priority=int(data.get("priority", 100)),
            active=bool(data.get("active", True)),
            return_to_origin=bool(data.get("return_to_origin", True)),
        )
    if command_type == "UpgradeNode":
        return UpgradeNode(
            node_id=str(data["node_id"]),
            storage_capacity_increase=int(data["storage_capacity_increase"]),
            transfer_limit_increase=int(data["transfer_limit_increase"]),
        )
    if command_type in {"BuildFacilityComponent", "PreviewBuildFacilityComponent"}:
        ports_payload = data.get("ports", []) or []
        connections_payload = data.get("connections", []) or []
        ports = tuple(_facility_port_from_dict(item) for item in ports_payload)
        connections = tuple(_internal_connection_from_dict(item) for item in connections_payload)
        inputs_data = data.get("inputs")
        outputs_data = data.get("outputs")
        component_command = (
            BuildFacilityComponent
            if command_type == "BuildFacilityComponent"
            else PreviewBuildFacilityComponent
        )
        return component_command(
            component_id=str(data["component_id"]),
            node_id=str(data["node_id"]),
            kind=FacilityComponentKind(str(data["kind"])),
            capacity=int(data.get("capacity", 0)),
            rate=int(data.get("rate", 0)),
            power_required=int(data.get("power_required", 0)),
            inputs=None if inputs_data is None else _facility_cargo_map_from_dict(inputs_data),
            outputs=None if outputs_data is None else _facility_cargo_map_from_dict(outputs_data),
            ports=ports,
            connections=connections,
        )
    if command_type in {"DemolishFacilityComponent", "PreviewDemolishFacilityComponent"}:
        component_command = (
            DemolishFacilityComponent
            if command_type == "DemolishFacilityComponent"
            else PreviewDemolishFacilityComponent
        )
        return component_command(
            node_id=str(data["node_id"]),
            component_id=str(data["component_id"]),
        )
    if command_type in {"BuildInternalConnection", "PreviewBuildInternalConnection"}:
        connection_command = (
            BuildInternalConnection
            if command_type == "BuildInternalConnection"
            else PreviewBuildInternalConnection
        )
        return connection_command(
            node_id=str(data["node_id"]),
            connection_id=str(data["connection_id"]),
            source_component_id=str(data["source_component_id"]),
            source_port_id=str(data["source_port_id"]),
            destination_component_id=str(data["destination_component_id"]),
            destination_port_id=str(data["destination_port_id"]),
        )
    if command_type in {"RemoveInternalConnection", "PreviewRemoveInternalConnection"}:
        connection_command = (
            RemoveInternalConnection
            if command_type == "RemoveInternalConnection"
            else PreviewRemoveInternalConnection
        )
        return connection_command(
            node_id=str(data["node_id"]),
            connection_id=str(data["connection_id"]),
        )
    raise ValueError(f"unknown command type: {command_type}")


def _facility_cargo_map_from_dict(data: object) -> dict[CargoType, int]:
    """Parse cargo→units maps in facility command payloads."""

    if not isinstance(data, dict):
        return {}
    return {CargoType(str(cargo)): int(units) for cargo, units in data.items()}


def _facility_port_from_dict(data: dict[str, Any]) -> FacilityPort:
    """Parse a FacilityPort spec from a JSON command payload."""

    cargo_type = data.get("cargo_type")
    return FacilityPort(
        id=str(data["id"]),
        direction=PortDirection(str(data["direction"])),
        cargo_type=None if cargo_type is None else CargoType(str(cargo_type)),
        rate=int(data.get("rate", 0)),
        capacity=int(data.get("capacity", 0)),
    )


def _internal_connection_from_dict(data: dict[str, Any]) -> InternalConnection:
    """Parse an InternalConnection spec from a JSON command payload."""

    return InternalConnection(
        id=str(data["id"]),
        source_component_id=str(data["source_component_id"]),
        source_port_id=str(data["source_port_id"]),
        destination_component_id=str(data["destination_component_id"]),
        destination_port_id=str(data["destination_port_id"]),
    )


def command_result(
    command_type: str,
    *,
    ok: bool,
    message: str,
    target_id: str | None = None,
    **extra: object,
) -> dict[str, object]:
    """Return a JSON-safe command result."""

    result: dict[str, object] = {
        "ok": ok,
        "type": command_type,
        "target_id": target_id,
        "message": message,
    }
    result.update(extra)
    return result


def _duplicate_link_between(state: object, origin: str, destination: str, mode: LinkMode) -> str | None:
    """Return an existing link id with the same mode and endpoints."""

    endpoints = {origin, destination}
    for link in state.links.values():
        if link.mode == mode and {link.origin, link.destination} == endpoints:
            return link.id
    return None


def _node_layout_payload(layout_x: float | None, layout_y: float | None) -> dict[str, float] | None:
    """Return JSON-safe node layout payload."""

    if layout_x is None and layout_y is None:
        return None
    if layout_x is None or layout_y is None:
        raise ValueError("layout requires both x and y")
    return {"x": round(layout_x, 3), "y": round(layout_y, 3)}


def _validate_build_node(state: object, command: BuildNode | PreviewBuildNode) -> tuple[float, int, int, dict[str, float] | None]:
    """Validate and normalize a node build command."""

    if command.world_id not in state.worlds:
        raise ValueError(f"unknown world: {command.world_id}")
    if command.node_id in state.nodes:
        raise ValueError(f"duplicate node id: {command.node_id}")
    if not command.name.strip():
        raise ValueError("node name cannot be empty")
    cost = node_build_cost(command.kind)
    storage = command.storage_capacity if command.storage_capacity is not None else node_default_storage(command.kind)
    transfer = command.transfer_limit_per_tick if command.transfer_limit_per_tick is not None else node_default_transfer(command.kind)
    if storage <= 0:
        raise ValueError("storage_capacity must be positive")
    if transfer <= 0:
        raise ValueError("transfer_limit_per_tick must be positive")
    layout = _node_layout_payload(command.layout_x, command.layout_y)
    return cost, storage, transfer, layout


def _node_build_payload(
    command: BuildNode | PreviewBuildNode,
    *,
    storage: int,
    transfer: int,
    layout: dict[str, float] | None,
) -> dict[str, object]:
    """Return a normalized BuildNode command payload."""

    payload: dict[str, object] = {
        "type": "BuildNode",
        "node_id": command.node_id,
        "world_id": command.world_id,
        "kind": command.kind.value,
        "name": command.name,
        "storage_capacity": storage,
        "transfer_limit_per_tick": transfer,
    }
    if layout is not None:
        payload["layout"] = layout
    return payload


def _layout_travel_ticks_for_nodes(state: object, origin: str, destination: str) -> int | None:
    """Estimate travel ticks from persisted node layout when available."""

    origin_node = state.nodes[origin]
    destination_node = state.nodes[destination]
    if (
        origin_node.layout_x is None
        or origin_node.layout_y is None
        or destination_node.layout_x is None
        or destination_node.layout_y is None
    ):
        return None
    dx = destination_node.layout_x - origin_node.layout_x
    dy = destination_node.layout_y - origin_node.layout_y
    return travel_ticks_from_layout_distance((dx * dx + dy * dy) ** 0.5)


def _alignment_travel_ticks_for_nodes(
    state: object,
    origin: str,
    destination: str,
    alignment: tuple[TrackPoint, ...],
) -> int | None:
    """Estimate travel ticks from endpoint layout plus authored rail alignment."""

    if not alignment:
        return None
    origin_node = state.nodes[origin]
    destination_node = state.nodes[destination]
    if (
        origin_node.layout_x is None
        or origin_node.layout_y is None
        or destination_node.layout_x is None
        or destination_node.layout_y is None
    ):
        return None
    points = (
        TrackPoint(origin_node.layout_x, origin_node.layout_y),
        *alignment,
        TrackPoint(destination_node.layout_x, destination_node.layout_y),
    )
    distance = 0.0
    for start, end in zip(points, points[1:]):
        dx = end.x - start.x
        dy = end.y - start.y
        distance += (dx * dx + dy * dy) ** 0.5
    return travel_ticks_from_layout_distance(distance)


def _validate_track_alignment(alignment: tuple[TrackPoint, ...]) -> None:
    """Validate local rail-alignment metadata."""

    for point in alignment:
        if not isfinite(point.x) or not isfinite(point.y):
            raise ValueError("alignment points must be finite numbers")


def _track_alignment_payload(alignment: tuple[TrackPoint, ...]) -> list[dict[str, float]]:
    """Return a normalized alignment payload for command previews."""

    return [{"x": round(point.x, 3), "y": round(point.y, 3)} for point in alignment]


def _validate_build_link(
    state: object,
    command: BuildLink | PreviewBuildLink,
) -> tuple[int, int, int, str | None, float, int]:
    """Validate and normalize a transport link build command."""

    if command.link_id in state.links:
        raise ValueError(f"duplicate link id: {command.link_id}")
    if command.origin == command.destination:
        raise ValueError("link origin and destination must be different")
    if command.origin not in state.nodes:
        raise ValueError(f"unknown link origin: {command.origin}")
    if command.destination not in state.nodes:
        raise ValueError(f"unknown link destination: {command.destination}")
    if command.capacity_per_tick <= 0:
        raise ValueError("link capacity_per_tick must be positive")
    if command.power_required < 0:
        raise ValueError("link power_required cannot be negative")
    _validate_track_alignment(command.alignment)

    origin_world_id = state.nodes[command.origin].world_id
    destination_world_id = state.nodes[command.destination].world_id

    if command.mode == LinkMode.RAIL:
        if origin_world_id != destination_world_id:
            raise ValueError("rail links must stay within one world")
        travel_ticks = command.travel_ticks
        if travel_ticks is None:
            travel_ticks = (
                _alignment_travel_ticks_for_nodes(
                    state,
                    command.origin,
                    command.destination,
                    command.alignment,
                )
                or _layout_travel_ticks_for_nodes(state, command.origin, command.destination)
                or 4
            )
        power_required = 0
        power_source_world_id = None
    elif command.mode == LinkMode.GATE:
        if command.alignment:
            raise ValueError("track alignment is only supported on rail links")
        if origin_world_id == destination_world_id:
            raise ValueError("gate links must connect different worlds")
        origin_kind = state.nodes[command.origin].kind
        destination_kind = state.nodes[command.destination].kind
        if origin_kind != NodeKind.GATE_HUB or destination_kind != NodeKind.GATE_HUB:
            raise ValueError("gate links require gate_hub endpoints")
        travel_ticks = command.travel_ticks if command.travel_ticks is not None else DEFAULT_GATE_TRAVEL_TICKS
        power_required = (
            command.power_required
            if command.power_required > 0
            else DEFAULT_GATE_POWER_REQUIRED
        )
        power_source_world_id = command.power_source_world_id or origin_world_id
        if power_source_world_id not in state.worlds:
            raise ValueError(f"unknown gate power source: {power_source_world_id}")
        if power_source_world_id not in {origin_world_id, destination_world_id}:
            raise ValueError("gate power source must be one of the endpoint worlds")
    else:
        raise ValueError(f"unsupported link mode: {command.mode.value}")

    if travel_ticks <= 0:
        raise ValueError("link travel_ticks must be positive")
    duplicate_link_id = _duplicate_link_between(
        state,
        command.origin,
        command.destination,
        command.mode,
    )
    if duplicate_link_id is not None:
        raise ValueError(f"duplicate link endpoints: {duplicate_link_id}")
    cost = link_build_cost(command.mode, travel_ticks)
    build_time = link_build_time(travel_ticks)
    return travel_ticks, command.capacity_per_tick, power_required, power_source_world_id, cost, build_time


def _link_build_payload(
    command: BuildLink | PreviewBuildLink,
    *,
    travel_ticks: int,
    capacity_per_tick: int,
    power_required: int,
    power_source_world_id: str | None,
) -> dict[str, object]:
    """Return a normalized BuildLink command payload."""

    payload: dict[str, object] = {
        "type": "BuildLink",
        "link_id": command.link_id,
        "origin": command.origin,
        "destination": command.destination,
        "mode": command.mode.value,
        "travel_ticks": travel_ticks,
        "capacity_per_tick": capacity_per_tick,
        "bidirectional": command.bidirectional,
    }
    if power_required:
        payload["power_required"] = power_required
    if power_source_world_id is not None:
        payload["power_source_world_id"] = power_source_world_id
    if command.alignment:
        payload["alignment"] = _track_alignment_payload(command.alignment)
    return payload


def _gate_preview_payload(
    state: object,
    command: BuildLink | PreviewBuildLink,
    *,
    power_required: int,
    power_source_world_id: str | None,
) -> dict[str, object]:
    """Return UI-friendly gate context for previews and build results."""

    if command.mode != LinkMode.GATE:
        return {}
    if power_source_world_id is None:
        raise ValueError("gate power source is required")

    from gaterail.gate import preview_gate_power

    origin_world_id = state.nodes[command.origin].world_id
    destination_world_id = state.nodes[command.destination].world_id
    origin_world = state.worlds[origin_world_id]
    destination_world = state.worlds[destination_world_id]
    power_world = state.worlds[power_source_world_id]
    existing_statuses = preview_gate_power(state)
    allocated_power = sum(
        status.power_required
        for status in existing_statuses.values()
        if status.link_id != command.link_id
        and status.powered
        and status.source_world_id == power_source_world_id
    )
    power_available = max(0, power_world.base_power_margin - allocated_power)
    power_shortfall = max(0, power_required - power_available)
    return {
        "origin_world_id": origin_world_id,
        "origin_world_name": origin_world.name,
        "destination_world_id": destination_world_id,
        "destination_world_name": destination_world.name,
        "power_required": power_required,
        "power_source_world_id": power_source_world_id,
        "power_source_world_name": power_world.name,
        "power_available": power_available,
        "power_shortfall": power_shortfall,
        "powered_if_built": power_shortfall == 0,
    }


def _validate_purchase_train(state: object, command: PurchaseTrain | PreviewPurchaseTrain) -> float:
    """Validate and price a train purchase command."""

    if command.train_id in state.trains:
        raise ValueError(f"duplicate train id: {command.train_id}")
    if command.node_id not in state.nodes:
        raise ValueError(f"unknown train node: {command.node_id}")
    if not command.name.strip():
        raise ValueError("train name cannot be empty")
    if command.capacity <= 0:
        raise ValueError("train capacity must be positive")
    return train_purchase_cost(command.capacity)


def _train_purchase_payload(command: PurchaseTrain | PreviewPurchaseTrain) -> dict[str, object]:
    """Return a normalized PurchaseTrain command payload."""

    return {
        "type": "PurchaseTrain",
        "train_id": command.train_id,
        "name": command.name,
        "node_id": command.node_id,
        "capacity": command.capacity,
    }


def _effective_next_departure_tick(state: object, command: CreateSchedule | PreviewCreateSchedule) -> int:
    """Return the normalized next departure tick for a schedule command."""

    if command.next_departure_tick is None:
        return int(state.tick) + 1
    return command.next_departure_tick


def _validate_create_schedule(
    state: object,
    command: CreateSchedule | PreviewCreateSchedule,
) -> tuple[int, object]:
    """Validate a recurring schedule and resolve its current route."""

    if command.schedule_id in state.schedules:
        raise ValueError(f"duplicate schedule id: {command.schedule_id}")
    if command.train_id not in state.trains:
        raise ValueError(f"unknown schedule train: {command.train_id}")
    if command.origin not in state.nodes:
        raise ValueError(f"unknown schedule origin: {command.origin}")
    if command.destination not in state.nodes:
        raise ValueError(f"unknown schedule destination: {command.destination}")
    if command.origin == command.destination:
        raise ValueError("schedule origin and destination must be different")
    if command.units_per_departure <= 0:
        raise ValueError("schedule units_per_departure must be positive")
    if command.interval_ticks <= 0:
        raise ValueError("schedule interval_ticks must be positive")
    train = state.trains[command.train_id]
    if not train.idle:
        raise ValueError(f"schedule train {command.train_id} is not idle")
    if train.node_id != command.origin:
        raise ValueError(f"schedule train {command.train_id} is at {train.node_id}, not {command.origin}")
    if command.units_per_departure > train.capacity:
        raise ValueError("schedule units_per_departure cannot exceed train capacity")
    next_departure_tick = _effective_next_departure_tick(state, command)
    if next_departure_tick <= state.tick:
        raise ValueError("schedule next_departure_tick must be in the future")
    route = shortest_route(state, command.origin, command.destination)
    if route is None:
        raise ValueError(f"no route {command.origin}->{command.destination}")
    if route.travel_ticks <= 0:
        raise ValueError("schedule route must have positive travel time")
    return next_departure_tick, route


def _schedule_payload(
    command: CreateSchedule | PreviewCreateSchedule,
    *,
    next_departure_tick: int,
) -> dict[str, object]:
    """Return a normalized CreateSchedule command payload."""

    return {
        "type": "CreateSchedule",
        "schedule_id": command.schedule_id,
        "train_id": command.train_id,
        "origin": command.origin,
        "destination": command.destination,
        "cargo_type": command.cargo_type.value,
        "units_per_departure": command.units_per_departure,
        "interval_ticks": command.interval_ticks,
        "next_departure_tick": next_departure_tick,
        "priority": command.priority,
        "active": command.active,
        "return_to_origin": command.return_to_origin,
    }


def _used_slots_for_route_context(state: object, link: NetworkLink, gate_status: object | None) -> int:
    """Return current slot pressure for route preview context."""

    used = int(state.link_usage_this_tick.get(link.id, 0))
    if gate_status is not None:
        used = max(used, int(getattr(gate_status, "slots_used", 0)))
    return used


def _route_context_payload(state: object, route: object) -> dict[str, object]:
    """Return schedule-preview route context focused on gate handoffs."""

    from gaterail.gate import preview_gate_power

    gate_statuses = state.gate_statuses if state.gate_statuses else preview_gate_power(state)
    gate_link_ids: list[str] = []
    gate_handoffs: list[dict[str, object]] = []
    route_warnings: list[dict[str, object]] = []
    node_ids = tuple(route.node_ids)

    for index, link_id in enumerate(route.link_ids):
        link = state.links[link_id]
        if link.mode != LinkMode.GATE:
            continue
        gate_link_ids.append(link.id)
        from_node_id = node_ids[index] if index < len(node_ids) else link.origin
        to_node_id = node_ids[index + 1] if index + 1 < len(node_ids) else link.destination
        from_world = state.worlds[state.nodes[from_node_id].world_id]
        to_world = state.worlds[state.nodes[to_node_id].world_id]
        status = gate_statuses.get(link.id)
        powered = bool(status.powered) if status is not None else state.link_operational(link)
        power_shortfall = int(getattr(status, "power_shortfall", 0)) if status is not None else 0
        capacity, disruptions = effective_link_capacity(state, link)
        used = _used_slots_for_route_context(state, link, status)
        remaining = max(0, capacity - used)
        pressure = round(used / capacity, 3) if capacity > 0 else (1.0 if used > 0 else 0.0)
        disruption_reasons = [disruption.reason for disruption in disruptions]

        warnings: list[dict[str, object]] = []
        if not powered:
            warnings.append(
                {
                    "severity": "blocked",
                    "reason": f"gate {link.id} unpowered",
                }
            )
        if disruptions:
            warnings.append(
                {
                    "severity": "blocked" if capacity == 0 else "degraded",
                    "reason": ", ".join(disruption_reasons),
                }
            )
        if capacity > 0 and used >= capacity:
            warnings.append(
                {
                    "severity": "congested",
                    "reason": f"gate slots full on {link.id}",
                }
            )
        elif capacity > 0 and pressure >= 0.75:
            warnings.append(
                {
                    "severity": "hot",
                    "reason": f"gate {link.id} at {int(round(pressure * 100))}% slot pressure",
                }
            )

        gate_handoff = {
            "link_id": link.id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "from_world_id": from_world.id,
            "from_world_name": from_world.name,
            "to_world_id": to_world.id,
            "to_world_name": to_world.name,
            "powered": powered,
            "power_required": link.power_required,
            "power_shortfall": power_shortfall,
            "slots_used": used,
            "slot_capacity": capacity,
            "base_capacity": link.capacity_per_tick,
            "slots_remaining": remaining,
            "pressure": pressure,
            "disrupted": bool(disruptions),
            "disruption_reasons": disruption_reasons,
            "warnings": warnings,
        }
        gate_handoffs.append(gate_handoff)
        for warning in warnings:
            route_warnings.append({"link_id": link.id, **warning})

    return {
        "gate_link_ids": gate_link_ids,
        "gate_handoffs": gate_handoffs,
        "route_warnings": route_warnings,
    }


def _structural_route_context_for_failed_schedule(
    state: object,
    command: PreviewCreateSchedule,
) -> dict[str, object]:
    """Return route context for previews blocked by gate power/capacity state."""

    if command.origin not in state.nodes or command.destination not in state.nodes:
        return {}
    if command.origin == command.destination:
        return {}
    route = shortest_route(
        state,
        command.origin,
        command.destination,
        require_operational=False,
    )
    if route is None or route.travel_ticks <= 0:
        return {}
    context = _route_context_payload(state, route)
    if not context["gate_handoffs"]:
        return {}
    return {
        "route_travel_ticks": route.travel_ticks,
        "route_node_ids": list(route.node_ids),
        "route_link_ids": list(route.link_ids),
        **context,
    }


def _preview_error(command_type: str, target_id: str, exc: ValueError) -> dict[str, object]:
    """Return a non-mutating invalid preview result."""

    reason = str(exc)
    return command_result(
        command_type,
        ok=False,
        target_id=target_id,
        message=reason,
        reason=reason,
    )


def _cash_available(state: object, cost: float) -> bool:
    """Return whether the player can afford a construction cost."""

    return state.finance.cash >= cost


def _insufficient_cash_message(state: object, label: str, cost: float) -> str:
    """Return a consistent insufficient-cash validation message."""

    return f"insufficient cash for {label}: need {cost:.0f}, have {state.finance.cash:.0f}"


def _validate_facility_component(
    state: object,
    command: BuildFacilityComponent | PreviewBuildFacilityComponent,
) -> tuple[float, dict[CargoType, int], dict[CargoType, int], tuple[FacilityPort, ...], tuple[InternalConnection, ...]]:
    """Validate a facility component install and return its normalized fields."""

    if command.node_id not in state.nodes:
        raise ValueError(f"unknown node: {command.node_id}")
    if not command.component_id.strip():
        raise ValueError("component id cannot be empty")
    node = state.nodes[command.node_id]
    facility = node.facility
    if facility is not None and command.component_id in facility.components:
        raise ValueError(f"duplicate component id: {command.component_id}")
    if command.capacity < 0:
        raise ValueError("component capacity cannot be negative")
    if command.rate < 0:
        raise ValueError("component rate cannot be negative")
    if command.power_required < 0:
        raise ValueError("component power_required cannot be negative")
    inputs = dict(command.inputs or {})
    outputs = dict(command.outputs or {})
    _validate_facility_cargo_quantities(inputs, "input")
    _validate_facility_cargo_quantities(outputs, "output")
    if command.kind == FacilityComponentKind.STORAGE_BAY and command.capacity <= 0:
        raise ValueError("storage_bay capacity must be positive")
    if command.kind == FacilityComponentKind.LOADER and command.rate <= 0:
        raise ValueError("loader rate must be positive")
    if command.kind == FacilityComponentKind.UNLOADER and command.rate <= 0:
        raise ValueError("unloader rate must be positive")
    if command.kind == FacilityComponentKind.FACTORY_BLOCK and not (inputs or outputs):
        raise ValueError("factory_block requires at least one input or output")
    seen_port_ids: set[str] = set()
    for port in command.ports:
        if not port.id.strip():
            raise ValueError("port id cannot be empty")
        if port.id in seen_port_ids:
            raise ValueError(f"duplicate port id on component: {port.id}")
        seen_port_ids.add(port.id)
        if port.rate < 0:
            raise ValueError(f"port {port.id} rate cannot be negative")
        if port.capacity < 0:
            raise ValueError(f"port {port.id} capacity cannot be negative")
    component = FacilityComponent(
        id=command.component_id,
        kind=command.kind,
        ports={port.id: port for port in command.ports},
        capacity=int(command.capacity),
        rate=int(command.rate),
        power_required=int(command.power_required),
        inputs=dict(inputs),
        outputs=dict(outputs),
    )
    _validate_inline_facility_connections(node, component, command.connections)
    cost = facility_component_build_cost(command.kind)
    return cost, inputs, outputs, command.ports, command.connections


def _validate_facility_cargo_quantities(mapping: dict[CargoType, int], label: str) -> None:
    """Validate that component cargo flow quantities are positive."""

    for cargo_type, units in mapping.items():
        if units <= 0:
            raise ValueError(f"{label} units for {cargo_type.value} must be positive")


def _validate_inline_facility_connections(
    node: NetworkNode,
    component: FacilityComponent,
    connections: tuple[InternalConnection, ...],
) -> None:
    """Validate connections bundled into a component build against a prospective facility."""

    if not connections:
        return
    facility = Facility(
        components={} if node.facility is None else dict(node.facility.components),
        connections={} if node.facility is None else dict(node.facility.connections),
    )
    facility.components[component.id] = component
    for connection in connections:
        if (
            connection.source_component_id != component.id
            and connection.destination_component_id != component.id
        ):
            raise ValueError("inline connection must reference the component being built")
        _validate_internal_connection(facility, connection)
        facility.connections[connection.id] = connection


def _facility_component_payload(
    command: BuildFacilityComponent | PreviewBuildFacilityComponent,
    *,
    inputs: dict[CargoType, int],
    outputs: dict[CargoType, int],
    ports: tuple[FacilityPort, ...],
    connections: tuple[InternalConnection, ...],
) -> dict[str, object]:
    """Return a normalized BuildFacilityComponent command payload."""

    return {
        "type": "BuildFacilityComponent",
        "component_id": command.component_id,
        "node_id": command.node_id,
        "kind": command.kind.value,
        "capacity": int(command.capacity),
        "rate": int(command.rate),
        "power_required": int(command.power_required),
        "inputs": {cargo.value: int(units) for cargo, units in sorted(inputs.items(), key=lambda item: item[0].value)},
        "outputs": {cargo.value: int(units) for cargo, units in sorted(outputs.items(), key=lambda item: item[0].value)},
        "ports": [
            {
                "id": port.id,
                "direction": port.direction.value,
                "cargo_type": None if port.cargo_type is None else port.cargo_type.value,
                "rate": int(port.rate),
                "capacity": int(port.capacity),
            }
            for port in ports
        ],
        "connections": [
            {
                "id": connection.id,
                "source_component_id": connection.source_component_id,
                "source_port_id": connection.source_port_id,
                "destination_component_id": connection.destination_component_id,
                "destination_port_id": connection.destination_port_id,
            }
            for connection in connections
        ],
    }


def _require_facility(state: object, node_id: str) -> tuple[NetworkNode, Facility]:
    """Return a node's facility, raising a command-facing validation error."""

    if node_id not in state.nodes:
        raise ValueError(f"unknown node: {node_id}")
    node = state.nodes[node_id]
    if node.facility is None:
        raise ValueError(f"node {node_id} has no facility")
    return node, node.facility


def _require_facility_component(
    state: object,
    node_id: str,
    component_id: str,
) -> tuple[NetworkNode, Facility, FacilityComponent]:
    """Return a facility component, raising validation errors for missing pieces."""

    node, facility = _require_facility(state, node_id)
    if component_id not in facility.components:
        raise ValueError(f"unknown facility component: {component_id}")
    return node, facility, facility.components[component_id]


def _connections_referencing_component(facility: Facility, component_id: str) -> list[str]:
    """Return internal connection ids that would be orphaned by removing a component."""

    return sorted(
        connection.id
        for connection in facility.connections.values()
        if connection.source_component_id == component_id
        or connection.destination_component_id == component_id
    )


def _rate_after_component_removal(
    node: NetworkNode,
    facility: Facility,
    component: FacilityComponent,
) -> int | None:
    """Return the relevant effective node rate after removing one component."""

    remaining = [
        item
        for item in facility.components.values()
        if item.id != component.id and item.kind == component.kind
    ]
    if component.kind == FacilityComponentKind.LOADER:
        if remaining:
            return sum(max(0, item.rate) for item in remaining)
        return int(node.transfer_limit_per_tick)
    if component.kind == FacilityComponentKind.UNLOADER:
        if remaining:
            return sum(max(0, item.rate) for item in remaining)
        return int(node.transfer_limit_per_tick)
    return None


def _schedule_conflicts_after_component_removal(
    state: object,
    node: NetworkNode,
    component: FacilityComponent,
    future_rate: int | None,
) -> list[str]:
    """Return active schedule ids whose required rate would exceed a future cap."""

    if future_rate is None:
        return []
    if component.kind == FacilityComponentKind.LOADER:
        current_rate = int(node.effective_outbound_rate())
        relevant = lambda schedule: schedule.origin == node.id
    elif component.kind == FacilityComponentKind.UNLOADER:
        current_rate = int(node.effective_inbound_rate())
        relevant = lambda schedule: schedule.destination == node.id
    else:
        return []
    if future_rate >= current_rate:
        return []
    return sorted(
        schedule.id
        for schedule in state.schedules.values()
        if schedule.active
        and relevant(schedule)
        and schedule.units_per_departure > future_rate
    )


def _validate_demolish_facility_component(
    state: object,
    command: DemolishFacilityComponent | PreviewDemolishFacilityComponent,
) -> tuple[NetworkNode, Facility, FacilityComponent, int | None]:
    """Validate component demolition and return the component plus future rate."""

    node, facility, component = _require_facility_component(
        state,
        command.node_id,
        command.component_id,
    )
    referencing = _connections_referencing_component(facility, command.component_id)
    if referencing:
        raise ValueError(
            f"cannot demolish component {command.component_id}; remove internal connections first: "
            + ", ".join(referencing)
        )
    future_rate = _rate_after_component_removal(node, facility, component)
    conflicts = _schedule_conflicts_after_component_removal(state, node, component, future_rate)
    if conflicts:
        raise ValueError(
            f"cannot demolish {component.kind.value} {component.id}; active schedules exceed future rate "
            f"{future_rate}: "
            + ", ".join(conflicts)
        )
    return node, facility, component, future_rate


def _demolish_facility_component_payload(
    command: DemolishFacilityComponent | PreviewDemolishFacilityComponent,
) -> dict[str, object]:
    """Return a normalized component-demolition command payload."""

    return {
        "type": "DemolishFacilityComponent",
        "node_id": command.node_id,
        "component_id": command.component_id,
    }


def _connection_from_command(
    command: BuildInternalConnection | PreviewBuildInternalConnection,
) -> InternalConnection:
    """Build an InternalConnection value from a build-connection command."""

    return InternalConnection(
        id=command.connection_id,
        source_component_id=command.source_component_id,
        source_port_id=command.source_port_id,
        destination_component_id=command.destination_component_id,
        destination_port_id=command.destination_port_id,
    )


def _connection_payload(connection: InternalConnection, command_type: str = "BuildInternalConnection") -> dict[str, object]:
    """Return a normalized internal-connection command payload."""

    return {
        "type": command_type,
        "connection_id": connection.id,
        "source_component_id": connection.source_component_id,
        "source_port_id": connection.source_port_id,
        "destination_component_id": connection.destination_component_id,
        "destination_port_id": connection.destination_port_id,
    }


def _validate_build_internal_connection(
    state: object,
    command: BuildInternalConnection | PreviewBuildInternalConnection,
) -> tuple[NetworkNode, Facility, InternalConnection]:
    """Validate one internal facility connection."""

    node, facility = _require_facility(state, command.node_id)
    connection = _connection_from_command(command)
    _validate_internal_connection(facility, connection)
    return node, facility, connection


def _validate_internal_connection(facility: Facility, connection: InternalConnection) -> None:
    """Validate one internal connection against a facility layout."""

    if not connection.id.strip():
        raise ValueError("connection id cannot be empty")
    if connection.id in facility.connections:
        raise ValueError(f"duplicate connection id: {connection.id}")
    if connection.source_component_id == connection.destination_component_id:
        raise ValueError("internal connection source and destination components must differ")
    if connection.source_component_id not in facility.components:
        raise ValueError(f"unknown source component: {connection.source_component_id}")
    if connection.destination_component_id not in facility.components:
        raise ValueError(f"unknown destination component: {connection.destination_component_id}")

    source_component = facility.components[connection.source_component_id]
    destination_component = facility.components[connection.destination_component_id]
    source_port = source_component.ports.get(connection.source_port_id)
    if source_port is None:
        raise ValueError(f"unknown source port: {connection.source_port_id}")
    destination_port = destination_component.ports.get(connection.destination_port_id)
    if destination_port is None:
        raise ValueError(f"unknown destination port: {connection.destination_port_id}")
    if source_port.direction != PortDirection.OUTPUT:
        raise ValueError("internal connection source port must be an output")
    if destination_port.direction != PortDirection.INPUT:
        raise ValueError("internal connection destination port must be an input")
    if (
        source_port.cargo_type is not None
        and destination_port.cargo_type is not None
        and source_port.cargo_type != destination_port.cargo_type
    ):
        raise ValueError("internal connection cargo types must match")

    destination_endpoint = (connection.destination_component_id, connection.destination_port_id)
    for existing in facility.connections.values():
        if (existing.destination_component_id, existing.destination_port_id) == destination_endpoint:
            raise ValueError(f"destination port already connected: {connection.destination_port_id}")


def _validate_remove_internal_connection(
    state: object,
    command: RemoveInternalConnection | PreviewRemoveInternalConnection,
) -> tuple[NetworkNode, Facility, InternalConnection]:
    """Validate internal facility connection removal."""

    node, facility = _require_facility(state, command.node_id)
    if command.connection_id not in facility.connections:
        raise ValueError(f"unknown internal connection: {command.connection_id}")
    return node, facility, facility.connections[command.connection_id]


def apply_player_command(state: object, command: PlayerCommand) -> dict[str, object]:
    """Apply one player command to a GameState-like object."""

    if isinstance(command, SetScheduleEnabled):
        schedule = state.schedules.get(command.schedule_id)
        if schedule is None:
            raise ValueError(f"unknown schedule: {command.schedule_id}")
        schedule.active = command.enabled
        state_label = "enabled" if command.enabled else "disabled"
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"schedule {command.schedule_id} {state_label}",
        )

    if isinstance(command, DispatchOrder):
        order = FreightOrder(
            id=command.order_id,
            train_id=command.train_id,
            origin=command.origin,
            destination=command.destination,
            cargo_type=command.cargo_type,
            requested_units=command.requested_units,
            priority=command.priority,
        )
        state.add_order(order)
        return command_result(
            command.type,
            ok=True,
            target_id=command.order_id,
            message=f"order {command.order_id} queued",
        )

    if isinstance(command, CancelOrder):
        order = state.orders.get(command.order_id)
        if order is None:
            raise ValueError(f"unknown order: {command.order_id}")
        if not order.active:
            return command_result(
                command.type,
                ok=True,
                target_id=command.order_id,
                message=f"order {command.order_id} already inactive",
            )
        for train in state.trains.values():
            if train.order_id == command.order_id:
                raise ValueError(f"cannot cancel in-flight order: {command.order_id}")
        order.active = False
        return command_result(
            command.type,
            ok=True,
            target_id=command.order_id,
            message=f"order {command.order_id} cancelled",
        )

    if isinstance(command, PreviewBuildNode):
        try:
            cost, storage, transfer, layout = _validate_build_node(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.node_id, exc)
        normalized_command = _node_build_payload(command, storage=storage, transfer=transfer, layout=layout)
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, command.kind.value, cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.node_id,
                message=reason,
                reason=reason,
                cost=cost,
                build_time=0,
                storage_capacity=storage,
                transfer_limit_per_tick=transfer,
                layout=layout,
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=f"valid {command.kind.value} preview for {cost:.0f}",
            cost=cost,
            build_time=0,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            layout=layout,
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildNode):
        cost, storage, transfer, layout = _validate_build_node(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, command.kind.value, cost))
        node = NetworkNode(
            id=command.node_id,
            name=command.name,
            world_id=command.world_id,
            kind=command.kind,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            layout_x=command.layout_x,
            layout_y=command.layout_y,
        )
        state.add_node(node)
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=f"built {command.kind.value} {command.node_id} for {cost:.0f}",
            cost=cost,
            build_time=0,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            layout=layout,
        )

    if isinstance(command, PreviewBuildLink):
        try:
            (
                travel_ticks,
                capacity_per_tick,
                power_required,
                power_source_world_id,
                cost,
                build_time,
            ) = _validate_build_link(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.link_id, exc)
        normalized_command = _link_build_payload(
            command,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        gate_context = _gate_preview_payload(
            state,
            command,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, f"{command.mode.value} link", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.link_id,
                message=reason,
                reason=reason,
                cost=cost,
                build_time=build_time,
                travel_ticks=travel_ticks,
                capacity_per_tick=capacity_per_tick,
                normalized_command=normalized_command,
                mode=command.mode.value,
                **gate_context,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"valid {command.mode.value} link preview for {cost:.0f}",
            cost=cost,
            build_time=build_time,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            normalized_command=normalized_command,
            mode=command.mode.value,
            **gate_context,
        )

    if isinstance(command, BuildLink):
        (
            travel_ticks,
            capacity_per_tick,
            power_required,
            power_source_world_id,
            cost,
            build_time,
        ) = _validate_build_link(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, f"{command.mode.value} link", cost))
        link = NetworkLink(
            id=command.link_id,
            origin=command.origin,
            destination=command.destination,
            mode=command.mode,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
            bidirectional=command.bidirectional,
            build_cost=cost,
            build_time=build_time,
            alignment=command.alignment,
        )
        state.add_link(link)
        gate_context = _gate_preview_payload(
            state,
            command,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"built {command.mode.value} link {command.link_id} for {cost:.0f}",
            cost=cost,
            build_time=build_time,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            mode=command.mode.value,
            **gate_context,
        )

    if isinstance(command, DemolishLink):
        if command.link_id not in state.links:
            raise ValueError(f"unknown link id: {command.link_id}")
        for train in state.trains.values():
            if command.link_id in train.route_link_ids:
                raise ValueError(f"cannot demolish link in active train route: {command.link_id}")
        del state.links[command.link_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"demolished link {command.link_id}",
        )

    if isinstance(command, PreviewPurchaseTrain):
        try:
            cost = _validate_purchase_train(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.train_id, exc)
        normalized_command = _train_purchase_payload(command)
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, "train", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.train_id,
                message=reason,
                reason=reason,
                cost=cost,
                capacity=command.capacity,
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.train_id,
            message=f"valid train preview for {cost:.0f}",
            cost=cost,
            capacity=command.capacity,
            normalized_command=normalized_command,
        )

    if isinstance(command, PurchaseTrain):
        cost = _validate_purchase_train(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, "train", cost))
        train = FreightTrain(
            id=command.train_id,
            name=command.name,
            node_id=command.node_id,
            capacity=command.capacity,
        )
        state.add_train(train)
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.train_id,
            message=f"purchased train {command.train_id} for {cost:.0f}",
            cost=cost,
            capacity=command.capacity,
        )

    if isinstance(command, PreviewCreateSchedule):
        try:
            next_departure_tick, route = _validate_create_schedule(state, command)
        except ValueError as exc:
            result = _preview_error(command.type, command.schedule_id, exc)
            result.update(_structural_route_context_for_failed_schedule(state, command))
            return result
        normalized_command = _schedule_payload(command, next_departure_tick=next_departure_tick)
        route_context = _route_context_payload(state, route)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"valid schedule preview over {route.travel_ticks} ticks",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            normalized_command=normalized_command,
            **route_context,
        )

    if isinstance(command, CreateSchedule):
        next_departure_tick, route = _validate_create_schedule(state, command)
        schedule = FreightSchedule(
            id=command.schedule_id,
            train_id=command.train_id,
            origin=command.origin,
            destination=command.destination,
            cargo_type=command.cargo_type,
            units_per_departure=command.units_per_departure,
            interval_ticks=command.interval_ticks,
            next_departure_tick=next_departure_tick,
            priority=command.priority,
            active=command.active,
            return_to_origin=command.return_to_origin,
        )
        state.add_schedule(schedule)
        route_context = _route_context_payload(state, route)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"created schedule {command.schedule_id}",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            **route_context,
        )

    if isinstance(command, PreviewBuildFacilityComponent):
        try:
            cost, inputs, outputs, ports, connections = _validate_facility_component(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.component_id, exc)
        normalized_command = _facility_component_payload(
            command,
            inputs=inputs,
            outputs=outputs,
            ports=ports,
            connections=connections,
        )
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, f"{command.kind.value} component", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.component_id,
                message=reason,
                reason=reason,
                cost=cost,
                node_id=command.node_id,
                kind=command.kind.value,
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"valid {command.kind.value} component preview for {cost:.0f}",
            cost=cost,
            node_id=command.node_id,
            kind=command.kind.value,
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildFacilityComponent):
        cost, inputs, outputs, ports, connections = _validate_facility_component(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, f"{command.kind.value} component", cost))
        node = state.nodes[command.node_id]
        if node.facility is None:
            node.facility = Facility()
        component = FacilityComponent(
            id=command.component_id,
            kind=command.kind,
            ports={port.id: port for port in ports},
            capacity=int(command.capacity),
            rate=int(command.rate),
            power_required=int(command.power_required),
            inputs=dict(inputs),
            outputs=dict(outputs),
        )
        node.facility.components[component.id] = component
        for connection in connections:
            if connection.id in node.facility.connections:
                raise ValueError(f"duplicate connection id: {connection.id}")
            node.facility.connections[connection.id] = connection
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"installed {command.kind.value} component {command.component_id} for {cost:.0f}",
            cost=cost,
            node_id=command.node_id,
            kind=command.kind.value,
        )

    if isinstance(command, PreviewDemolishFacilityComponent):
        try:
            _, _, component, future_rate = _validate_demolish_facility_component(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.component_id, exc)
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"valid demolition preview for {component.kind.value} {component.id}",
            node_id=command.node_id,
            kind=component.kind.value,
            future_rate=future_rate,
            normalized_command=_demolish_facility_component_payload(command),
        )

    if isinstance(command, DemolishFacilityComponent):
        _, facility, component, future_rate = _validate_demolish_facility_component(state, command)
        del facility.components[command.component_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"demolished {component.kind.value} component {component.id}",
            node_id=command.node_id,
            kind=component.kind.value,
            future_rate=future_rate,
        )

    if isinstance(command, PreviewBuildInternalConnection):
        try:
            _, _, connection = _validate_build_internal_connection(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.connection_id, exc)
        normalized_command = _connection_payload(connection)
        normalized_command["node_id"] = command.node_id
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"valid internal connection preview for {connection.id}",
            node_id=command.node_id,
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildInternalConnection):
        _, facility, connection = _validate_build_internal_connection(state, command)
        facility.connections[connection.id] = connection
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"built internal connection {connection.id}",
            node_id=command.node_id,
            **_connection_payload(connection),
        )

    if isinstance(command, PreviewRemoveInternalConnection):
        try:
            _, _, connection = _validate_remove_internal_connection(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.connection_id, exc)
        normalized_command = _connection_payload(connection, command_type="RemoveInternalConnection")
        normalized_command["node_id"] = command.node_id
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"valid internal connection removal preview for {connection.id}",
            node_id=command.node_id,
            normalized_command=normalized_command,
        )

    if isinstance(command, RemoveInternalConnection):
        _, facility, connection = _validate_remove_internal_connection(state, command)
        del facility.connections[command.connection_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"removed internal connection {connection.id}",
            node_id=command.node_id,
            **_connection_payload(connection, command_type="RemoveInternalConnection"),
        )

    if isinstance(command, UpgradeNode):
        if command.node_id not in state.nodes:
            raise ValueError(f"unknown node id: {command.node_id}")
        if command.storage_capacity_increase < 0:
            raise ValueError("storage_capacity_increase cannot be negative")
        if command.transfer_limit_increase < 0:
            raise ValueError("transfer_limit_increase cannot be negative")
        if command.storage_capacity_increase == 0 and command.transfer_limit_increase == 0:
            raise ValueError("upgrade must increase storage or transfer capacity")
        node = state.nodes[command.node_id]
        cost = node_upgrade_cost(command.storage_capacity_increase, command.transfer_limit_increase)
        if state.finance.cash < cost:
            raise ValueError(
                f"insufficient cash for upgrade: need {cost:.0f}, have {state.finance.cash:.0f}"
            )
        node.storage_capacity += command.storage_capacity_increase
        node.transfer_limit_per_tick += command.transfer_limit_increase
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=f"upgraded node {command.node_id} for {cost:.0f}",
        )

    raise TypeError(f"unsupported player command: {type(command).__name__}")
