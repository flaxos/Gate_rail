"""Stable render snapshots for Stage 2 clients."""

from __future__ import annotations

from math import cos, pi, sin

from gaterail.cargo import cargo_catalog_payload
from gaterail.economy import BUFFER_NODE_KINDS
from gaterail.facilities import facility_summary
from gaterail.gate import preview_gate_power
from gaterail.models import (
    ConstructionStatus,
    Contract,
    ContractKind,
    FacilityBlockReason,
    GameState,
    LinkMode,
    NodeKind,
)
from gaterail.resource_chains import resource_branch_pressure
from gaterail.resources import resource_catalog_payload, resource_deposit_to_dict
from gaterail.traffic import active_signals_for_link, build_signal_report, effective_link_capacity
from gaterail.transport import route_through_stops


SNAPSHOT_VERSION = 1
SCHEDULE_ORDER_PREFIX = "schedule:"


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


def _scenario_catalog_payload() -> list[dict[str, object]]:
    """Return backend-owned built-in scenario metadata for clients."""

    from gaterail.scenarios import DEFAULT_SCENARIO, scenario_definitions

    return [
        {
            "key": definition.key,
            "aliases": list(definition.aliases),
            "title": definition.title,
            "description": definition.description,
            "default": definition.key == DEFAULT_SCENARIO,
        }
        for definition in scenario_definitions()
    ]


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


def _world_position(index: int, total: int) -> dict[str, int]:
    """Return deterministic galaxy-scale coordinates owned by the Python sim."""

    if total <= 1:
        return {"x": 0, "y": 0}
    radius = 420
    angle = (-pi / 2.0) + ((2.0 * pi * index) / total)
    return {"x": int(round(cos(angle) * radius)), "y": int(round(sin(angle) * radius))}


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


def _reverse_link_id_for(state: GameState, link: object) -> str | None:
    """Return an existing link that supports reverse traversal for ``link``."""

    origin = getattr(link, "origin", None)
    destination = getattr(link, "destination", None)
    mode = getattr(link, "mode", None)
    link_id = getattr(link, "id", None)
    endpoints = {origin, destination}
    for candidate in sorted(state.links.values(), key=lambda item: item.id):
        if candidate.id == link_id or candidate.mode != mode:
            continue
        if candidate.bidirectional and {candidate.origin, candidate.destination} == endpoints:
            return candidate.id
        if candidate.origin == destination and candidate.destination == origin:
            return candidate.id
    return None


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


def _tutorial_six_worlds_payload(state: GameState) -> dict[str, object] | None:
    """Return backend-owned tutorial loop progress for the six-world starter save."""

    required_schedules = {
        "tutorial_ore_to_cinder",
        "tutorial_metal_to_atlas",
        "tutorial_parts_to_helix",
    }
    if not required_schedules.issubset(state.schedules) or "helix_parts_tutorial" not in state.contracts:
        return None

    ore_schedule = state.schedules["tutorial_ore_to_cinder"]
    metal_schedule = state.schedules["tutorial_metal_to_atlas"]
    parts_schedule = state.schedules["tutorial_parts_to_helix"]
    parts_contract = state.contracts["helix_parts_tutorial"]
    cinder_smelter = state.nodes.get("cinder_smelter")
    atlas_factory = state.nodes.get("atlas_factory")
    parts_cargo = parts_contract.cargo_type or parts_schedule.cargo_type

    cinder_ore = 0 if cinder_smelter is None else cinder_smelter.stock(ore_schedule.cargo_type)
    cinder_metal = 0 if cinder_smelter is None else cinder_smelter.stock(metal_schedule.cargo_type)
    atlas_metal = 0 if atlas_factory is None else atlas_factory.stock(metal_schedule.cargo_type)
    atlas_parts = 0 if atlas_factory is None else atlas_factory.stock(parts_cargo)
    contract_parts = int(parts_contract.delivered_units)
    ore_progress = max(
        int(ore_schedule.delivered_units),
        cinder_ore,
        cinder_metal,
        atlas_metal,
        atlas_parts,
        contract_parts,
    )
    metal_progress = max(
        int(metal_schedule.delivered_units),
        atlas_metal,
        atlas_parts,
        contract_parts,
    )
    parts_progress = max(int(parts_schedule.delivered_units), contract_parts)
    if parts_progress >= int(parts_contract.target_units) or atlas_parts >= int(parts_contract.target_units):
        metal_progress = max(metal_progress, 10)
        ore_progress = max(ore_progress, 20)
    elif metal_progress >= 10:
        ore_progress = max(ore_progress, 20)

    steps: list[dict[str, object]] = [
        {
            "id": "mine_ore",
            "label": "Mine ore for Cinder Forge",
            "cargo": ore_schedule.cargo_type.value,
            "origin": ore_schedule.origin,
            "destination": ore_schedule.destination,
            "schedule_id": ore_schedule.id,
            "delivered": ore_progress,
            "target": 20,
            "dispatch": {
                "train_id": ore_schedule.train_id,
                "origin": ore_schedule.origin,
                "destination": ore_schedule.destination,
                "cargo": ore_schedule.cargo_type.value,
                "requested_units": 20,
            },
        },
        {
            "id": "smelt_metal",
            "label": "Smelt metal for Atlas Yards",
            "cargo": metal_schedule.cargo_type.value,
            "origin": metal_schedule.origin,
            "destination": metal_schedule.destination,
            "schedule_id": metal_schedule.id,
            "delivered": metal_progress,
            "target": 10,
            "dispatch": {
                "train_id": metal_schedule.train_id,
                "origin": metal_schedule.origin,
                "destination": metal_schedule.destination,
                "cargo": metal_schedule.cargo_type.value,
                "requested_units": 10,
            },
        },
        {
            "id": "deliver_parts",
            "label": "Deliver parts to Helix Reach",
            "cargo": parts_cargo.value,
            "origin": parts_schedule.origin,
            "destination": parts_contract.destination_node_id or parts_schedule.destination,
            "schedule_id": parts_schedule.id,
            "contract_id": parts_contract.id,
            "delivered": parts_progress,
            "target": int(parts_contract.target_units),
            "reward_cash": round(parts_contract.reward_cash, 2),
            "reward_reputation": int(parts_contract.reward_reputation),
            "dispatch": {
                "train_id": parts_schedule.train_id,
                "origin": parts_schedule.origin,
                "destination": parts_contract.destination_node_id or parts_schedule.destination,
                "cargo": parts_schedule.cargo_type.value,
                "requested_units": int(parts_contract.target_units),
            },
        },
    ]

    active_index: int | None = None
    for index, step in enumerate(steps):
        complete = int(step["delivered"]) >= int(step["target"])
        if step["id"] == "deliver_parts" and parts_contract.status.value == "fulfilled":
            complete = True
        if complete:
            step["status"] = "complete"
        elif active_index is None:
            step["status"] = "active"
            active_index = index
        else:
            step["status"] = "pending"

    all_complete = all(str(step.get("status", "")) == "complete" for step in steps)
    if all_complete:
        alerts = [
            {
                "kind": "tutorial",
                "message": "Tutorial loop complete: Helix paid for delivered parts.",
            }
        ]
        current_step_id = None
        next_action = None
    else:
        active_step = steps[active_index or 0]
        current_step_id = str(active_step["id"])
        next_action = {
            "kind": "manual_dispatch",
            "label": "Set up a manual freight order",
        }
        alert_messages = {
            "mine_ore": "Tutorial active: move ore from Brink Mines to Cinder Forge.",
            "smelt_metal": "Tutorial active: smelt ore into metal and move it to Atlas Yards.",
            "deliver_parts": "Tutorial active: build parts at Atlas Yards and ship them to Helix Reach.",
        }
        alerts = [
            {
                "kind": "tutorial",
                "message": alert_messages.get(current_step_id, "Tutorial active."),
            }
        ]

    return {
        "id": "tutorial_six_worlds",
        "title": "Six-World Tutorial Start",
        "summary": "Mine ore, smelt metal, build parts, and ship them to Helix for a payout.",
        "active": not all_complete,
        "current_step_id": current_step_id,
        "steps": steps,
        "alerts": alerts,
        "next_action": next_action,
    }


def _cargo_flow_payloads(state: GameState) -> list[dict[str, object]]:
    """Return route-level cargo flow visualisation payloads."""

    in_transit_by_schedule: dict[str, int] = {}
    train_count_by_schedule: dict[str, int] = {}
    for train in state.trains.values():
        order_id = train.order_id or ""
        if not order_id.startswith(SCHEDULE_ORDER_PREFIX):
            continue
        schedule_id = order_id.removeprefix(SCHEDULE_ORDER_PREFIX)
        in_transit_by_schedule[schedule_id] = (
            in_transit_by_schedule.get(schedule_id, 0) + int(train.cargo_units)
        )
        train_count_by_schedule[schedule_id] = train_count_by_schedule.get(schedule_id, 0) + 1

    flows: list[dict[str, object]] = []
    for schedule in sorted(state.schedules.values(), key=lambda item: item.id):
        route = route_through_stops(
            state,
            schedule.origin,
            schedule.stops,
            schedule.destination,
            require_operational=False,
        )
        route_stop_ids = [schedule.origin, *schedule.stops, schedule.destination]
        flows.append(
            {
                "id": f"{SCHEDULE_ORDER_PREFIX}{schedule.id}",
                "service_type": "schedule",
                "schedule_id": schedule.id,
                "train_id": schedule.train_id,
                "active": schedule.active,
                "cargo": schedule.cargo_type.value,
                "route_stop_ids": route_stop_ids,
                "route_node_ids": [] if route is None else list(route.node_ids),
                "route_link_ids": [] if route is None else list(route.link_ids),
                "route_travel_ticks": 0 if route is None else route.travel_ticks,
                "route_valid": route is not None,
                "units_per_departure": schedule.units_per_departure,
                "interval_ticks": schedule.interval_ticks,
                "next_departure_tick": schedule.next_departure_tick,
                "delivered_units": schedule.delivered_units,
                "in_transit_units": in_transit_by_schedule.get(schedule.id, 0),
                "trips_dispatched": schedule.trips_dispatched,
                "trips_completed": schedule.trips_completed,
                "trains_in_transit": train_count_by_schedule.get(schedule.id, 0),
            }
        )
    return flows


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
                "power_available": world.power_available,
                "power_used": world.power_used,
                "power_pressure": (
                    round(world.power_used / world.power_available, 3)
                    if world.power_available > 0
                    else 0.0
                ),
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
                "position": _world_position(world_index[world_id], len(world_ids)),
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
        node_power_required = (
            int(node.facility.power_required()) if node.facility is not None else 0
        )
        overlay_pip: dict[str, str] | None = None
        if facility_blocked_payload:
            block_reason = next(
                (
                    entry.get("reason")
                    for entry in state.facility_block_entries
                    if isinstance(entry, dict) and entry.get("node") == node.id
                ),
                None,
            )
            reason_value = (
                block_reason.value if hasattr(block_reason, "value") else str(block_reason)
            )
            overlay_pip = {
                "layer": "facility_block_layer",
                "severity": "warn",
                "label": reason_value.replace("_", " ") if reason_value else "blocked",
            }
        elif node.outpost_kind is not None:
            project = (
                state.construction_projects.get(node.construction_project_id)
                if node.construction_project_id
                else None
            )
            if project is None or project.status != ConstructionStatus.COMPLETED:
                overlay_pip = {
                    "layer": "outpost_layer",
                    "severity": "info",
                    "label": "outpost in construction",
                }
        elif node_power_required > 0:
            overlay_pip = {
                "layer": "power_layer",
                "severity": "info",
                "label": "power draw",
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
                "outpost_kind": node.outpost_kind.value if node.outpost_kind else None,
                "power_required": node_power_required,
                "overlay_pip": overlay_pip,
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
        reverse_link_id = _reverse_link_id_for(state, link)
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
                "directional": not link.bidirectional,
                "source_node_id": link.origin,
                "exit_node_id": link.destination,
                "reverse_available": link.bidirectional or reverse_link_id is not None,
                "reverse_link_id": reverse_link_id,
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
            "stops": list(schedule.stops),
            "route_stop_ids": [schedule.origin, *schedule.stops, schedule.destination],
            "cargo": schedule.cargo_type.value,
            "units_per_departure": schedule.units_per_departure,
            "interval_ticks": schedule.interval_ticks,
            "next_departure_tick": schedule.next_departure_tick,
            "priority": schedule.priority,
            "active": schedule.active,
            "return_to_origin": schedule.return_to_origin,
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
        "scenario_catalog": _scenario_catalog_payload(),
        "cargo_catalog": cargo_catalog_payload(),
        "tutorial": _tutorial_six_worlds_payload(state),
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
                "cargo_type": site.cargo_type.value if site.cargo_type is not None else None,
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
                "reserved_power": mission.reserved_power,
                "fuel_consumed": mission.fuel_consumed,
                "projected_yield": mission.expected_yield,
            }
            for mission in sorted(state.mining_missions.values(), key=lambda item: item.id)
        ],
        "worlds": worlds,
        "nodes": nodes,
        "links": links,
        "trains": trains,
        "schedules": schedules,
        "cargo_flows": _cargo_flow_payloads(state),
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
        "outposts": _outposts_payload(state),
    }


def _outposts_payload(state: GameState) -> list[dict[str, object]]:
    """Render top-level outposts: pending, active, and completed (promoted)."""

    payload: list[dict[str, object]] = []
    for node in sorted(state.nodes.values(), key=lambda item: item.id):
        if node.outpost_kind is None:
            continue
        project = (
            state.construction_projects.get(node.construction_project_id)
            if node.construction_project_id
            else None
        )
        required = project.required_cargo if project else {}
        delivered = project.delivered_cargo if project else {}
        remaining = project.remaining_cargo if project else {}
        required_total = sum(int(v) for v in required.values())
        delivered_total = sum(int(v) for v in delivered.values())
        progress_fraction = (
            delivered_total / required_total if required_total > 0 else 1.0
        )
        top_needs = [
            {"cargo": cargo.value if hasattr(cargo, "value") else str(cargo), "units": int(units)}
            for cargo, units in sorted(
                remaining.items(), key=lambda item: (-int(item[1]), str(item[0]))
            )[:3]
            if int(units) > 0
        ]
        payload.append(
            {
                "id": node.id,
                "kind": node.kind.value,
                "outpost_kind": node.outpost_kind.value,
                "construction_status": project.status.value if project else "completed",
                "required_cargo": _cargo_map(required),
                "delivered_cargo": _cargo_map(delivered),
                "remaining_cargo": _cargo_map(remaining),
                "progress_fraction": progress_fraction,
                "top_needs": top_needs,
                "world_id": node.world_id,
            }
        )
    return payload
