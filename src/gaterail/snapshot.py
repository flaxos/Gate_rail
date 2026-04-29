"""Stable render snapshots for Stage 2 clients."""

from __future__ import annotations

from gaterail.economy import BUFFER_NODE_KINDS
from gaterail.facilities import facility_summary
from gaterail.gate import preview_gate_power
from gaterail.models import Contract, ContractKind, FacilityBlockReason, GameState, LinkMode
from gaterail.resource_chains import resource_branch_pressure
from gaterail.resources import resource_catalog_payload, resource_deposit_to_dict
from gaterail.traffic import active_signals_for_link, build_signal_report, effective_link_capacity


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


def _resource_map(mapping: object) -> dict[str, int]:
    """Convert resource-id inventory maps to JSON-safe dictionaries."""

    if not isinstance(mapping, dict):
        return {}
    return {
        str(resource_id): int(units)
        for resource_id, units in sorted(mapping.items())
        if int(units) > 0
    }


def _plain_json_value(value: object) -> object:
    """Convert enum-like values inside diagnostic payloads to JSON-safe values."""

    if isinstance(value, dict):
        return {
            str(key.value if hasattr(key, "value") else key): _plain_json_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0].value if hasattr(pair[0], "value") else pair[0]),
            )
        }
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _facility_block_entry_payload(entry: object) -> dict[str, object]:
    """Return a stable snapshot payload for one facility block entry."""

    if not isinstance(entry, dict):
        return {}
    reason = entry.get("reason")
    reason_value = reason.value if isinstance(reason, FacilityBlockReason) else str(reason)
    return {
        "node": str(entry.get("node", "")),
        "component": str(entry.get("component", "")),
        "kind": str(entry.get("kind", "")),
        "reason": reason_value,
        "detail": _plain_json_value(entry.get("detail", {})),
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


def _track_alignment(link: object) -> list[dict[str, float]]:
    """Return JSON-safe rail-alignment metadata for a link."""

    return [
        {"x": round(float(point.x), 3), "y": round(float(point.y), 3)}
        for point in getattr(link, "alignment", ())
    ]


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
    signal_report = build_signal_report(state)
    rail_blocks = signal_report.get("blocks", {})
    if not isinstance(rail_blocks, dict):
        rail_blocks = {}
    power_plants_by_node: dict[str, list[str]] = {}
    for plant in state.power_plants.values():
        power_plants_by_node.setdefault(plant.node_id, []).append(plant.id)
    world_ids = sorted(state.worlds)
    world_index = {world_id: index for index, world_id in enumerate(world_ids)}

    worlds = []
    for world_id in world_ids:
        world = state.worlds[world_id]
        deposit_ids = [
            deposit.id
            for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id)
            if deposit.world_id == world_id
        ]
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
                    "generated": world.power_generated_this_tick,
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
                "deposits": deposit_ids,
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
        if node.resource_recipe is None:
            resource_recipe_payload: dict[str, object] | None = None
        else:
            resource_recipe_payload = {
                "id": node.resource_recipe.id,
                "kind": node.resource_recipe.kind.value,
                "inputs": _resource_map(node.resource_recipe.inputs),
                "outputs": _resource_map(node.resource_recipe.outputs),
            }
        recipe_blocked_payload = _cargo_map(state.recipe_blocked.get(node.id, {}))
        resource_recipe_blocked_payload = _resource_map(state.resource_recipe_blocked.get(node.id, {}))
        if node.facility is None:
            facility_payload: dict[str, object] | None = None
        else:
            facility_payload = facility_summary(node.facility)
        facility_blocked_payload = list(state.facility_blocked.get(node.id, []))
        facility_block_entries_payload = [
            payload
            for payload in (
                _facility_block_entry_payload(entry)
                for entry in state.facility_block_entries
                if isinstance(entry, dict) and entry.get("node") == node.id
            )
            if payload
        ]
        loader_summary_payload = {
            "effective_loader_rate": int(node.effective_outbound_rate()),
            "effective_unloader_rate": int(node.effective_inbound_rate()),
            "platform_queue_depth": int(state.platform_queue_depth_this_tick.get(node.id, 0)),
        }
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
                "resource_inventory": _resource_map(node.resource_inventory),
                "demand": _cargo_map(node.demand),
                "production": _cargo_map(node.production),
                "resource_demand": _resource_map(node.resource_demand),
                "resource_production": _resource_map(node.resource_production),
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
                "resource_recipe": resource_recipe_payload,
                "resource_recipe_blocked": resource_recipe_blocked_payload,
                "resource_deposit_id": node.resource_deposit_id,
                "facility": facility_payload,
                "facility_blocked": facility_blocked_payload,
                "facility_block_entries": facility_block_entries_payload,
                "loader_summary": loader_summary_payload,
                "power_plants": sorted(power_plants_by_node.get(node.id, [])),
                "construction_project_id": node.construction_project_id,
                "layout": _node_layout(node),
            }
        )

    links = []
    for link in sorted(state.links.values(), key=lambda item: item.id):
        capacity, disruptions = effective_link_capacity(state, link)
        gate_status = gate_statuses.get(link.id)
        link_signals = active_signals_for_link(state, link.id)
        block_payload = rail_blocks.get(link.id)
        if gate_status is None or gate_status.support_id is None:
            gate_support_payload: dict[str, object] | None = None
        else:
            gate_support_payload = {
                "id": gate_status.support_id,
                "node_id": gate_status.support_node_id,
                "inputs": _resource_map(gate_status.support_inputs),
                "missing": _resource_map(gate_status.support_missing),
                "power_bonus": gate_status.resource_power_bonus,
                "base_power_required": (
                    gate_status.power_required
                    if gate_status.base_power_required is None
                    else gate_status.base_power_required
                ),
                "effective_power_required": gate_status.power_required,
                "available": not gate_status.support_missing and gate_status.resource_power_bonus > 0,
            }
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
                "effective_power_required": (
                    link.power_required if gate_status is None else gate_status.power_required
                ),
                "gate_support": gate_support_payload,
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
                "alignment": _track_alignment(link),
                "signals": [signal.id for signal in link_signals],
                "rail_block": block_payload,
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
            "consist": train.consist.value,
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
        "resources": resource_catalog_payload(),
        "resource_deposits": [
            resource_deposit_to_dict(deposit, include_resource=True)
            for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id)
        ],
        "resource_branch_pressure": resource_branch_pressure(state),
        "facility_blocked_entries": [
            payload
            for payload in (
                _facility_block_entry_payload(entry)
                for entry in state.facility_block_entries
            )
            if payload
        ],
        "track_signals": [
            {"id": signal_id, **payload}
            for signal_id, payload in sorted(signal_report["signals"].items())
        ],
        "rail_blocks": [
            block
            for _, block in sorted(rail_blocks.items())
        ],
        "power_generation": {
            world_id: int(power)
            for world_id, power in sorted(state.power_generation_this_tick.items())
        },
        "power_plants": [
            {
                "id": plant.id,
                "node_id": plant.node_id,
                "world_id": state.nodes[plant.node_id].world_id,
                "kind": plant.kind.value,
                "inputs": _resource_map(plant.inputs),
                "power_output": plant.power_output,
                "active": plant.active,
                "missing": _resource_map(state.power_plant_blocked.get(plant.id, {})),
            }
            for plant in sorted(state.power_plants.values(), key=lambda item: item.id)
        ],
        "space_sites": [
            {
                "id": site.id,
                "name": site.name,
                "resource_id": site.resource_id,
                "travel_ticks": site.travel_ticks,
                "base_yield": site.base_yield,
                "discovered": site.discovered,
            }
            for site in sorted(state.space_sites.values(), key=lambda item: item.id)
        ],
        "mining_missions": [
            {
                "id": mission.id,
                "site_id": mission.site_id,
                "launch_node_id": mission.launch_node_id,
                "return_node_id": mission.return_node_id,
                "status": mission.status.value,
                "ticks_remaining": mission.ticks_remaining,
                "fuel_input": mission.fuel_input,
                "power_input": mission.power_input,
                "expected_yield": mission.expected_yield,
            }
            for mission in sorted(state.mining_missions.values(), key=lambda item: item.id)
        ],
        "worlds": worlds,
        "nodes": nodes,
        "links": links,
        "trains": trains,
        "schedules": schedules,
        "orders": orders,
        "contracts": contracts,
        "construction_projects": [
            {
                "id": project.id,
                "target_node_id": project.target_node_id,
                "required_cargo": _cargo_map(project.required_cargo),
                "delivered_cargo": _cargo_map(project.delivered_cargo),
                "status": project.status.value,
            }
            for project in sorted(state.construction_projects.values(), key=lambda item: item.id)
        ],
    }
