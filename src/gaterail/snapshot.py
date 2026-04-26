"""Stable render snapshots for Stage 2 clients."""

from __future__ import annotations

from gaterail.economy import BUFFER_NODE_KINDS
from gaterail.facilities import facility_summary
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


def _node_layout(node: object) -> dict[str, float] | None:
    """Return node-local layout metadata when the backend owns it."""

    layout_x = getattr(node, "layout_x", None)
    layout_y = getattr(node, "layout_y", None)
    if layout_x is None or layout_y is None:
        return None
    return {"x": round(float(layout_x), 3), "y": round(float(layout_y), 3)}


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

    nodes = []
    # Count trains per link for utilisation
    trains_per_link: dict[str, int] = {}
    for train in state.trains.values():
        for link_id in train.route_link_ids:
            trains_per_link[link_id] = trains_per_link.get(link_id, 0) + 1

    for node in sorted(state.nodes.values(), key=lambda item: item.id):
        node_shortages = state.shortages.get(node.id, {})
        used = node.total_inventory()
        effective_capacity = node.effective_storage_capacity()
        capacity = max(1, effective_capacity)
        transfer_used = int(state.transfer_used_this_tick.get(node.id, 0))
        effective_transfer = int(node.effective_combined_rate())
        transfer_pressure = (
            round(transfer_used / effective_transfer, 3) if effective_transfer > 0 else 0.0
        )
        saturation_streak = int(state.transfer_saturation_streak.get(node.id, 0))
        if node.recipe is None:
            recipe_payload: dict[str, dict[str, int]] | None = None
        else:
            recipe_payload = {
                "inputs": _cargo_map(node.recipe.inputs),
                "outputs": _cargo_map(node.recipe.outputs),
            }
        recipe_blocked_payload = _cargo_map(state.recipe_blocked.get(node.id, {}))
        if node.facility is None:
            facility_payload: dict[str, object] | None = None
        else:
            facility_payload = facility_summary(node.facility)
        facility_blocked_payload = list(state.facility_blocked.get(node.id, []))
        is_buffer = node.kind in BUFFER_NODE_KINDS
        if is_buffer:
            buffer_fill_pct: float | None = round(used / capacity, 3)
            served_source = state.buffer_distribution.get(node.id, {})
            served_last_tick: dict[str, dict[str, int]] = {
                target_id: {
                    cargo.value: int(units)
                    for cargo, units in sorted(cargo_map.items(), key=lambda item: item[0].value)
                    if int(units) > 0
                }
                for target_id, cargo_map in sorted(served_source.items())
                if cargo_map
            }
        else:
            buffer_fill_pct = None
            served_last_tick = {}
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "world_id": node.world_id,
                "kind": node.kind.value,
                "inventory": _cargo_map(node.inventory),
                "demand": _cargo_map(node.demand),
                "production": _cargo_map(node.production),
                "storage": {
                    "used": used,
                    "capacity": effective_capacity,
                    "base_capacity": node.storage_capacity,
                },
                "pressure": round(used / capacity, 3),
                "shortages": _cargo_map(node_shortages),
                "transfer_limit": effective_transfer,
                "base_transfer_limit": node.transfer_limit_per_tick,
                "transfer_used": transfer_used,
                "transfer_pressure": transfer_pressure,
                "effective_inbound_rate": int(node.effective_inbound_rate()),
                "effective_outbound_rate": int(node.effective_outbound_rate()),
                "saturation_streak": saturation_streak,
                "buffer_fill_pct": buffer_fill_pct,
                "served_last_tick": served_last_tick,
                "recipe": recipe_payload,
                "recipe_blocked": recipe_blocked_payload,
                "facility": facility_payload,
                "facility_blocked": facility_blocked_payload,
                "layout": _node_layout(node),
            }
        )

    links = []
    for link in sorted(state.links.values(), key=lambda item: item.id):
        capacity, disruptions = effective_link_capacity(state, link)
        gate_status = gate_statuses.get(link.id)
        trains_on_link = trains_per_link.get(link.id, 0)
        utilisation = round(trains_on_link / max(1, link.capacity_per_tick), 3)
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
                "charge_pct": 1.0 if gate_status is None else gate_status.charge_pct,
                "next_activation_tick": None if gate_status is None else gate_status.next_activation_tick,
                "slot_cargo": {} if gate_status is None else _cargo_map(gate_status.slot_cargo),
                "build_cost": round(link.build_cost, 2),
                "build_time": link.build_time,
                "disrupted": bool(disruptions),
                "disruption_reasons": [disruption.reason for disruption in disruptions],
                "utilisation": utilisation,
                "trains_on_link": trains_on_link,
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
