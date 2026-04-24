"""Stable render snapshots for Stage 2 clients."""

from __future__ import annotations

from gaterail.gate import preview_gate_power
from gaterail.models import Contract, ContractKind, GameState, LinkMode
from gaterail.traffic import effective_link_capacity


SNAPSHOT_VERSION = 1


def _cargo_map(mapping: object) -> dict[str, int]:
    """Convert cargo-keyed inventory maps to JSON-safe dictionaries."""

    if not isinstance(mapping, dict):
        return {}
    return {
        str(cargo.value if hasattr(cargo, "value") else cargo): int(units)
        for cargo, units in sorted(
            mapping.items(),
            key=lambda item: str(item[0].value if hasattr(item[0], "value") else item[0]),
        )
        if int(units) > 0
    }


def _world_position(index: int) -> dict[str, int]:
    """Return deterministic galaxy-scale coordinates owned by the Python sim."""

    return {"x": 360 * index, "y": 0}


def _contract_progress(contract: Contract) -> tuple[str, str, int]:
    """Return render labels and current progress for a contract."""

    if contract.kind == ContractKind.CARGO_DELIVERY:
        cargo = contract.cargo_type.value if contract.cargo_type is not None else "unknown"
        destination = contract.destination_node_id or "unknown"
        return cargo, destination, contract.delivered_units
    if contract.kind == ContractKind.FRONTIER_SUPPORT:
        return "support", f"world:{contract.target_world_id}", contract.progress
    if contract.kind == ContractKind.GATE_RECOVERY:
        return "powered", f"link:{contract.target_link_id}", contract.progress
    return "unknown", "unknown", contract.progress


def render_snapshot(state: GameState) -> dict[str, object]:
    """Return a compact, stable JSON snapshot for render clients."""

    gate_statuses = state.gate_statuses if state.gate_statuses else preview_gate_power(state)
    world_ids = sorted(state.worlds)
    world_index = {world_id: index for index, world_id in enumerate(world_ids)}

    worlds = []
    for world_id in world_ids:
        world = state.worlds[world_id]
        worlds.append(
            {
                "id": world.id,
                "name": world.name,
                "tier": int(world.tier),
                "tier_name": world.tier.name.lower(),
                "population": world.population,
                "stability": round(world.stability, 3),
                "specialization": world.specialization,
                "power": {
                    "available": world.power_available,
                    "used": world.power_used,
                    "gate_used": world.gate_power_used,
                    "margin": world.power_margin,
                },
                "progression": {
                    "progress": world.development_progress,
                    "support_streak": world.support_streak,
                    "shortage_streak": world.shortage_streak,
                    "trend": world.last_trend.value,
                },
                "position": _world_position(world_index[world_id]),
            }
        )

    nodes = [
        {
            "id": node.id,
            "name": node.name,
            "world_id": node.world_id,
            "kind": node.kind.value,
            "inventory": _cargo_map(node.inventory),
            "demand": _cargo_map(node.demand),
            "production": _cargo_map(node.production),
            "storage": {
                "used": node.total_inventory(),
                "capacity": node.storage_capacity,
            },
        }
        for node in sorted(state.nodes.values(), key=lambda item: item.id)
    ]

    links = []
    for link in sorted(state.links.values(), key=lambda item: item.id):
        capacity, disruptions = effective_link_capacity(state, link)
        gate_status = gate_statuses.get(link.id)
        links.append(
            {
                "id": link.id,
                "origin": link.origin,
                "destination": link.destination,
                "mode": link.mode.value,
                "travel_ticks": link.travel_ticks,
                "capacity": capacity,
                "base_capacity": link.capacity_per_tick,
                "active": link.active,
                "bidirectional": link.bidirectional,
                "power_required": link.power_required,
                "powered": None if link.mode != LinkMode.GATE or gate_status is None else gate_status.powered,
                "slots_used": 0 if gate_status is None else gate_status.slots_used,
                "disrupted": bool(disruptions),
                "disruption_reasons": [disruption.reason for disruption in disruptions],
            }
        )

    trains = [
        {
            "id": train.id,
            "name": train.name,
            "node_id": train.node_id,
            "status": train.status.value,
            "destination": train.destination,
            "capacity": train.capacity,
            "cargo": None if train.cargo_type is None else train.cargo_type.value,
            "cargo_units": train.cargo_units,
            "remaining_ticks": train.remaining_ticks,
            "route_node_ids": list(train.route_node_ids),
            "route_link_ids": list(train.route_link_ids),
            "order_id": train.order_id,
            "blocked_reason": train.blocked_reason,
        }
        for train in sorted(state.trains.values(), key=lambda item: item.id)
    ]

    schedules = [
        {
            "id": schedule.id,
            "train_id": schedule.train_id,
            "origin": schedule.origin,
            "destination": schedule.destination,
            "cargo": schedule.cargo_type.value,
            "units_per_departure": schedule.units_per_departure,
            "interval_ticks": schedule.interval_ticks,
            "next_departure_tick": schedule.next_departure_tick,
            "active": schedule.active,
            "trips_dispatched": schedule.trips_dispatched,
            "trips_completed": schedule.trips_completed,
            "delivered_units": schedule.delivered_units,
        }
        for schedule in sorted(state.schedules.values(), key=lambda item: item.id)
    ]

    orders = [
        {
            "id": order.id,
            "train_id": order.train_id,
            "origin": order.origin,
            "destination": order.destination,
            "cargo": order.cargo_type.value,
            "requested_units": order.requested_units,
            "delivered_units": order.delivered_units,
            "remaining_units": order.remaining_units,
            "priority": order.priority,
            "active": order.active,
        }
        for order in sorted(state.orders.values(), key=lambda item: item.id)
    ]

    contracts = []
    for contract in sorted(state.contracts.values(), key=lambda item: item.id):
        cargo, destination, progress = _contract_progress(contract)
        contracts.append(
            {
                "id": contract.id,
                "kind": contract.kind.value,
                "title": contract.title,
                "client": contract.client,
                "cargo": cargo,
                "destination": destination,
                "progress": progress,
                "target": contract.target_units,
                "due_tick": contract.due_tick,
                "status": contract.status.value,
                "reward_cash": round(contract.reward_cash, 2),
                "penalty_cash": round(contract.penalty_cash, 2),
                "reward_reputation": contract.reward_reputation,
                "penalty_reputation": contract.penalty_reputation,
                "resolved_tick": contract.resolved_tick,
            }
        )

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "tick": state.tick,
        "finance": state.finance.snapshot(),
        "reputation": state.reputation,
        "worlds": worlds,
        "nodes": nodes,
        "links": links,
        "trains": trains,
        "schedules": schedules,
        "orders": orders,
        "contracts": contracts,
    }
