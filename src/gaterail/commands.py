"""Player command contract for Stage 2 clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from gaterail.cargo import CargoType
from gaterail.models import FreightOrder


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


PlayerCommand: TypeAlias = SetScheduleEnabled | DispatchOrder | CancelOrder


def _command_type(data: dict[str, Any]) -> str:
    """Read the command type from a JSON-style command object."""

    raw_type = data.get("type") or data.get("command")
    if raw_type is None:
        raise ValueError("command missing type")
    return str(raw_type)


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
    raise ValueError(f"unknown command type: {command_type}")


def command_result(command_type: str, *, ok: bool, message: str, target_id: str | None = None) -> dict[str, object]:
    """Return a JSON-safe command result."""

    return {
        "ok": ok,
        "type": command_type,
        "target_id": target_id,
        "message": message,
    }


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

    raise TypeError(f"unsupported player command: {type(command).__name__}")
