"""JSON save/load support for deterministic GateRail playtests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gaterail.cargo import CargoType
from gaterail.models import (
    Contract,
    ContractKind,
    ContractStatus,
    DevelopmentTier,
    FinanceState,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    GameState,
    GatePowerStatus,
    LinkMode,
    NetworkDisruption,
    NetworkLink,
    NetworkNode,
    NodeKind,
    ProgressionTrend,
    TrainStatus,
    WorldState,
)
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
        specialization=data.get("specialization"),
        development_progress=int(data.get("development_progress", 0)),
        support_streak=int(data.get("support_streak", 0)),
        shortage_streak=int(data.get("shortage_streak", 0)),
        last_trend=ProgressionTrend(str(data.get("last_trend", ProgressionTrend.STALLED.value))),
    )


def _node_to_dict(node: NetworkNode) -> dict[str, object]:
    """Serialize a network node."""

    return {
        "id": node.id,
        "name": node.name,
        "world_id": node.world_id,
        "kind": node.kind.value,
        "inventory": _cargo_map_to_dict(node.inventory),
        "production": _cargo_map_to_dict(node.production),
        "demand": _cargo_map_to_dict(node.demand),
        "storage_capacity": node.storage_capacity,
        "transfer_limit_per_tick": node.transfer_limit_per_tick,
    }


def _node_from_dict(data: dict[str, Any]) -> NetworkNode:
    """Deserialize a network node."""

    return NetworkNode(
        id=str(data["id"]),
        name=str(data["name"]),
        world_id=str(data["world_id"]),
        kind=NodeKind(str(data["kind"])),
        inventory=_cargo_map_from_dict(data.get("inventory", {})),
        production=_cargo_map_from_dict(data.get("production", {})),
        demand=_cargo_map_from_dict(data.get("demand", {})),
        storage_capacity=int(data.get("storage_capacity", 1_000)),
        transfer_limit_per_tick=int(data.get("transfer_limit_per_tick", 24)),
    )


def _link_to_dict(link: NetworkLink) -> dict[str, object]:
    """Serialize a network link."""

    return {
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
    }


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


def state_to_dict(state: GameState) -> dict[str, object]:
    """Serialize game state to JSON-safe data."""

    return {
        "tick": state.tick,
        "worlds": [_world_to_dict(world) for world in sorted(state.worlds.values(), key=lambda item: item.id)],
        "nodes": [_node_to_dict(node) for node in sorted(state.nodes.values(), key=lambda item: item.id)],
        "links": [_link_to_dict(link) for link in sorted(state.links.values(), key=lambda item: item.id)],
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
    for node_data in data.get("nodes", []):
        state.add_node(_node_from_dict(node_data))
    for link_data in data.get("links", []):
        state.add_link(_link_from_dict(link_data))
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
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("save file root must be an object")
    return simulation_from_dict(data)
