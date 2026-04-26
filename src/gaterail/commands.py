"""Player command contract for Stage 2 clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from gaterail.cargo import CargoType
from gaterail.construction import (
    DEFAULT_RAIL_CAPACITY_PER_TICK,
    link_build_cost,
    link_build_time,
    node_build_cost,
    node_default_storage,
    node_default_transfer,
    node_upgrade_cost,
    train_purchase_cost,
    travel_ticks_from_layout_distance,
)
from gaterail.models import FreightOrder, FreightSchedule, FreightTrain, LinkMode, NetworkLink, NetworkNode, NodeKind
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
        link_command = BuildLink if command_type == "BuildLink" else PreviewBuildLink
        return link_command(
            link_id=str(data["link_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            mode=LinkMode(str(data.get("mode", LinkMode.RAIL.value))),
            travel_ticks=_optional_int(data.get("travel_ticks")),
            capacity_per_tick=int(data.get("capacity_per_tick", DEFAULT_RAIL_CAPACITY_PER_TICK)),
            power_required=int(data.get("power_required", 0)),
            power_source_world_id=None if power_world is None else str(power_world),
            bidirectional=bool(data.get("bidirectional", True)),
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
    raise ValueError(f"unknown command type: {command_type}")


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


def _validate_build_link(state: object, command: BuildLink | PreviewBuildLink) -> tuple[int, int, float, int]:
    """Validate and normalize a rail link build command."""

    if command.link_id in state.links:
        raise ValueError(f"duplicate link id: {command.link_id}")
    if command.mode != LinkMode.RAIL:
        raise ValueError("BuildLink currently supports rail links only")
    if command.origin == command.destination:
        raise ValueError("link origin and destination must be different")
    if command.origin not in state.nodes:
        raise ValueError(f"unknown link origin: {command.origin}")
    if command.destination not in state.nodes:
        raise ValueError(f"unknown link destination: {command.destination}")
    origin_world_id = state.nodes[command.origin].world_id
    destination_world_id = state.nodes[command.destination].world_id
    if origin_world_id != destination_world_id:
        raise ValueError("rail links must stay within one world")
    travel_ticks = command.travel_ticks
    if travel_ticks is None:
        travel_ticks = _layout_travel_ticks_for_nodes(state, command.origin, command.destination) or 4
    if travel_ticks <= 0:
        raise ValueError("link travel_ticks must be positive")
    if command.capacity_per_tick <= 0:
        raise ValueError("link capacity_per_tick must be positive")
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
    return travel_ticks, command.capacity_per_tick, cost, build_time


def _link_build_payload(
    command: BuildLink | PreviewBuildLink,
    *,
    travel_ticks: int,
    capacity_per_tick: int,
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
    if command.power_required:
        payload["power_required"] = command.power_required
    if command.power_source_world_id is not None:
        payload["power_source_world_id"] = command.power_source_world_id
    return payload


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
            travel_ticks, capacity_per_tick, cost, build_time = _validate_build_link(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.link_id, exc)
        normalized_command = _link_build_payload(
            command,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
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
        )

    if isinstance(command, BuildLink):
        travel_ticks, capacity_per_tick, cost, build_time = _validate_build_link(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, f"{command.mode.value} link", cost))
        link = NetworkLink(
            id=command.link_id,
            origin=command.origin,
            destination=command.destination,
            mode=command.mode,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=command.power_required,
            power_source_world_id=command.power_source_world_id,
            bidirectional=command.bidirectional,
            build_cost=cost,
            build_time=build_time,
        )
        state.add_link(link)
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
            return _preview_error(command.type, command.schedule_id, exc)
        normalized_command = _schedule_payload(command, next_departure_tick=next_departure_tick)
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
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"created schedule {command.schedule_id}",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
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
