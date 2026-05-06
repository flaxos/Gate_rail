"""Fixed-tick freight order and train movement execution."""

from __future__ import annotations

from gaterail.cargo import CargoType, consist_can_carry, metadata_for, required_consist_for
from gaterail.economy import record_transfer
from gaterail.models import (
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    GameState,
    StopAction,
    TrainStatus,
    TrainStop,
    WaitCondition,
)
from gaterail.traffic import reserve_route_capacity
from gaterail.transport import route_through_stops


FreightReport = dict[str, list[dict[str, object]]]
SCHEDULE_ORDER_PREFIX = "schedule:"


def _train_snapshot(train: FreightTrain) -> dict[str, object]:
    """Return stable report data for a train."""

    return {
        "id": train.id,
        "name": train.name,
        "status": train.status.value,
        "node": train.node_id,
        "destination": train.destination,
        "cargo": None if train.cargo_type is None else train.cargo_type.value,
        "units": train.cargo_units,
        "remaining_ticks": train.remaining_ticks,
        "order": train.order_id,
        "blocked_reason": train.blocked_reason,
    }


def _block_train(events: FreightReport, train: FreightTrain, reason: str) -> None:
    """Mark a train blocked and record a report event."""

    train.status = TrainStatus.BLOCKED
    train.blocked_reason = reason
    events["blocked"].append({"train": train.name, "reason": reason})


def _reset_empty_blocked_trains(state: GameState) -> None:
    """Let empty blocked trains retry dispatch checks on a later tick."""

    for train in state.trains.values():
        if train.status == TrainStatus.BLOCKED and train.cargo_units <= 0:
            train.status = TrainStatus.IDLE
            train.blocked_reason = None


def _platform_limit_for_node(state: GameState, node_id: str) -> int | None:
    """Return the active platform concurrency limit for a node, if any."""

    facility = state.nodes[node_id].facility
    if facility is None:
        return None
    return facility.platform_concurrent_loading_limit()


def _platform_has_room(state: GameState, node_id: str) -> bool:
    """Return whether a node has platform room for another load/unload operation."""

    limit = _platform_limit_for_node(state, node_id)
    if limit is None:
        return True
    return int(state.platform_loading_this_tick.get(node_id, 0)) < limit


def _reserve_platform_slot(state: GameState, node_id: str) -> None:
    """Record one load/unload operation against platform concurrency."""

    if _platform_limit_for_node(state, node_id) is None:
        return
    state.platform_loading_this_tick[node_id] = int(state.platform_loading_this_tick.get(node_id, 0)) + 1


def _block_for_platform_capacity(
    state: GameState,
    events: FreightReport,
    train: FreightTrain,
    *,
    node_id: str,
    direction: str,
) -> None:
    """Block a train because all facility platform slots are occupied this tick."""

    train.status = TrainStatus.BLOCKED
    train.blocked_reason = "platform_capacity"
    state.platform_queue_depth_this_tick[node_id] = int(
        state.platform_queue_depth_this_tick.get(node_id, 0)
    ) + 1
    event = {
        "node": node_id,
        "train": train.name,
        "reason": "platform_capacity",
        "direction": direction,
    }
    events["freight_blocked"].append(event)
    events["blocked"].append({"train": train.name, "reason": "platform_capacity"})


def _remaining_loader_capacity(state: GameState, node_id: str) -> tuple[int, int]:
    """Return total and remaining loader capacity for a node this tick."""

    node = state.nodes[node_id]
    total = max(0, node.effective_outbound_rate())
    if node.facility is None or node.facility.loader_rate_override() is None:
        return total, total
    used = int(state.freight_loader_used_this_tick.get(node_id, 0))
    return total, max(0, total - used)


def _remaining_unloader_capacity(state: GameState, node_id: str) -> tuple[int, int]:
    """Return total and remaining unloader capacity for a node this tick."""

    node = state.nodes[node_id]
    total = max(0, node.effective_inbound_rate())
    if node.facility is None or node.facility.unloader_rate_override() is None:
        return total, total
    used = int(state.freight_unloader_used_this_tick.get(node_id, 0))
    return total, max(0, total - used)


def _uses_loader_budget(state: GameState, node_id: str) -> bool:
    """Return whether loader capacity should be shared across the tick."""

    node = state.nodes[node_id]
    return node.facility is not None and node.facility.loader_rate_override() is not None


def _uses_unloader_budget(state: GameState, node_id: str) -> bool:
    """Return whether unloader capacity should be shared across the tick."""

    node = state.nodes[node_id]
    return node.facility is not None and node.facility.unloader_rate_override() is not None


def _strict_loader_missing(state: GameState, node_id: str) -> bool:
    """Return whether a strict local node has no explicit loader component."""

    node = state.nodes[node_id]
    return (
        node.requires_facility_handling
        and (node.facility is None or node.facility.loader_rate_override() is None)
    )


def _strict_unloader_missing(state: GameState, node_id: str) -> bool:
    """Return whether a strict local node has no explicit unloader component."""

    node = state.nodes[node_id]
    return (
        node.requires_facility_handling
        and (node.facility is None or node.facility.unloader_rate_override() is None)
    )


def _finish_order_if_complete(order: FreightOrder) -> None:
    """Deactivate one-shot orders when their requested volume has arrived."""

    if order.remaining_units <= 0:
        order.active = False


def _schedule_id_from_order_id(order_id: str | None) -> str | None:
    """Return schedule id encoded into a train order field."""

    if order_id is None or not order_id.startswith(SCHEDULE_ORDER_PREFIX):
        return None
    return order_id.removeprefix(SCHEDULE_ORDER_PREFIX)


def _train_stops_for_service(
    state: GameState, service_id: str | None
) -> tuple[TrainStop, ...]:
    """Return the train_stops list for an active order or schedule, if any."""

    if service_id is None:
        return ()
    schedule_id = _schedule_id_from_order_id(service_id)
    if schedule_id is not None and schedule_id in state.schedules:
        return state.schedules[schedule_id].train_stops
    if service_id in state.orders:
        return state.orders[service_id].train_stops
    return ()


def _service_cargo_type(
    state: GameState, service_id: str
) -> CargoType | None:
    """Return the headline cargo_type for an order or schedule by id."""

    schedule_id = _schedule_id_from_order_id(service_id)
    if schedule_id is not None and schedule_id in state.schedules:
        return state.schedules[schedule_id].cargo_type
    if service_id in state.orders:
        return state.orders[service_id].cargo_type
    return None


def _is_wait_satisfied(state: GameState, train: FreightTrain, stop: TrainStop) -> bool:
    """Return whether the train has met this stop's wait condition."""

    if stop.wait_condition == WaitCondition.NONE:
        return True
    if stop.wait_condition == WaitCondition.FULL:
        return train.cargo_units >= train.capacity
    if stop.wait_condition == WaitCondition.EMPTY:
        return train.cargo_units <= 0
    if stop.wait_condition == WaitCondition.TIME:
        if train.arrival_tick is None:
            return False
        return state.tick - train.arrival_tick >= stop.wait_ticks
    return True


def _attempt_unload(state: GameState, events: FreightReport, train: FreightTrain) -> None:
    """Unload arrived or storage-blocked cargo into the current node."""

    if _train_stops_for_service(state, train.order_id):
        _process_multistop_at_node(state, events, train)
        return

    if train.cargo_type is None or train.cargo_units <= 0:
        train.status = TrainStatus.IDLE
        train.blocked_reason = None
        return

    destination = state.nodes[train.node_id]
    if not _platform_has_room(state, destination.id):
        _block_for_platform_capacity(
            state,
            events,
            train,
            node_id=destination.id,
            direction="unload",
        )
        return

    _effective_unloader_rate, remaining_unloader_rate = _remaining_unloader_capacity(
        state,
        destination.id,
    )
    attempted = min(train.cargo_units, remaining_unloader_rate)
    if attempted <= 0:
        if _strict_unloader_missing(state, destination.id):
            _block_train(events, train, f"missing unloader at {destination.id}")
            train.blocked_reason = "missing_unloader"
            events["freight_blocked"].append(
                {
                    "node": destination.id,
                    "train": train.name,
                    "reason": "missing_unloader",
                    "direction": "unload",
                }
            )
        else:
            _block_train(events, train, f"unload limit reached at {destination.id}")
        return
    accepted = destination.add_inventory(train.cargo_type, attempted)
    if accepted <= 0:
        _block_train(events, train, f"storage full at {destination.id}")
        return

    if _uses_unloader_budget(state, destination.id):
        state.freight_unloader_used_this_tick[destination.id] = (
            int(state.freight_unloader_used_this_tick.get(destination.id, 0)) + accepted
        )
    _reserve_platform_slot(state, destination.id)
    record_transfer(state, destination.id, accepted)
    train.cargo_units -= accepted
    order_id = train.order_id
    schedule_id = _schedule_id_from_order_id(order_id)
    if schedule_id is not None and schedule_id in state.schedules:
        state.schedules[schedule_id].delivered_units += accepted
    elif order_id is not None and order_id in state.orders:
        order = state.orders[order_id]
        order.delivered_units += accepted
        _finish_order_if_complete(order)
    state.finance.record_revenue(
        accepted * metadata_for(train.cargo_type).base_unit_revenue * train.revenue_modifier
    )

    events["deliveries"].append(
        {
            "train": train.name,
            "node": destination.id,
            "cargo": train.cargo_type.value,
            "units": accepted,
            "order": order_id,
        }
    )

    if train.cargo_units > 0:
        _block_train(events, train, f"unload limit reached at {destination.id}")
        return

    if schedule_id is not None and schedule_id in state.schedules:
        schedule = state.schedules[schedule_id]
        schedule.trips_completed += 1
        schedule.next_departure_tick = state.tick + schedule.interval_ticks
        if schedule.return_to_origin:
            train.node_id = schedule.origin

    train.status = TrainStatus.IDLE
    train.destination = None
    train.route_node_ids = ()
    train.route_link_ids = ()
    train.order_id = None
    train.cargo_type = None
    train.blocked_reason = None


def _advance_active_trains(state: GameState, events: FreightReport) -> None:
    """Move in-transit trains one tick and unload arrivals."""

    for train in sorted(state.trains.values(), key=lambda item: item.id):
        if train.status == TrainStatus.BLOCKED and train.cargo_units > 0:
            _attempt_unload(state, events, train)
            continue

        if train.status != TrainStatus.IN_TRANSIT:
            continue

        train.remaining_ticks = max(0, train.remaining_ticks - 1)
        if train.remaining_ticks > 0:
            events["in_transit"].append(
                {
                    "train": train.name,
                    "destination": train.destination,
                    "remaining_ticks": train.remaining_ticks,
                }
            )
            continue

        if train.destination is None:
            _block_train(events, train, "missing destination")
            continue
        train.node_id = train.destination
        train.arrival_tick = state.tick
        _attempt_unload(state, events, train)


def _dispatch_trip(
    state: GameState,
    events: FreightReport,
    *,
    train: FreightTrain,
    origin_id: str,
    destination_id: str,
    cargo_type: CargoType,
    requested_units: int,
    service_id: str,
    stops: tuple[str, ...] = (),
) -> bool:
    """Load and dispatch one train trip."""

    if not train.idle:
        return False
    if train.node_id != origin_id:
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": f"train at {train.node_id}, not {origin_id}",
            }
        )
        return False

    if not consist_can_carry(train.consist, cargo_type):
        required_consist = required_consist_for(cargo_type)
        reason = (
            f"cargo {cargo_type.value} requires {required_consist.value} consist, "
            f"train is {train.consist.value}"
        )
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": reason,
            }
        )
        train.status = TrainStatus.BLOCKED
        train.blocked_reason = "incompatible_consist"
        return False

    route = route_through_stops(state, origin_id, stops, destination_id)
    if route is None:
        route_stop_ids = (origin_id, *stops, destination_id)
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": f"no route {'->'.join(route_stop_ids)}",
            }
        )
        return False

    origin = state.nodes[origin_id]
    if not _platform_has_room(state, origin_id):
        _block_for_platform_capacity(
            state,
            events,
            train,
            node_id=origin_id,
            direction="load",
        )
        return False

    effective_loader_rate, remaining_loader_rate = _remaining_loader_capacity(state, origin_id)
    uncapped_units = min(train.capacity, requested_units, origin.stock(cargo_type))
    planned_units = min(uncapped_units, remaining_loader_rate)
    if planned_units <= 0:
        missing_loader = _strict_loader_missing(state, origin.id)
        reason = (
            f"missing loader at {origin.id}"
            if missing_loader
            else (
                f"loader capacity reached at {origin.id}"
                if uncapped_units > 0
                else f"no {cargo_type.value} at {origin.id}"
            )
        )
        events["blocked"].append({"train": train.name, "order": service_id, "reason": reason})
        if missing_loader:
            train.status = TrainStatus.BLOCKED
            train.blocked_reason = "missing_loader"
            events["freight_blocked"].append(
                {
                    "node": origin_id,
                    "train": train.name,
                    "reason": "missing_loader",
                    "direction": "load",
                }
            )
        elif uncapped_units > 0:
            train.status = TrainStatus.BLOCKED
            train.blocked_reason = "loader_capacity"
            events["freight_blocked"].append(
                {
                    "node": origin_id,
                    "train": train.name,
                    "reason": "loader_capacity",
                    "direction": "load",
                }
            )
        return False

    reservation = reserve_route_capacity(state, route.link_ids, train_id=train.id)
    if not reservation.reserved:
        reason = reservation.reason or "route capacity unavailable"
        event = {
            "train": train.name,
            "order": service_id,
            "reason": reason,
        }
        events["blocked"].append(event)
        events["queued"].append(
            {
                "train": train.name,
                "order": service_id,
                "origin": origin_id,
                "destination": destination_id,
                "link": reservation.link_id,
                "reason": reason,
            }
        )
        return False

    loaded = origin.remove_inventory(cargo_type, planned_units)
    record_transfer(state, origin.id, loaded)
    if _uses_loader_budget(state, origin_id):
        state.freight_loader_used_this_tick[origin_id] = (
            int(state.freight_loader_used_this_tick.get(origin_id, 0)) + loaded
        )
    _reserve_platform_slot(state, origin_id)
    if _uses_loader_budget(state, origin_id) and loaded < uncapped_units and loaded == remaining_loader_rate:
        events["loader_capped"].append(
            {
                "node": origin_id,
                "train": train.name,
                "cargo": cargo_type.value,
                "requested_units": requested_units,
                "loaded_units": loaded,
                "effective_loader_rate": effective_loader_rate,
            }
        )

    train.status = TrainStatus.IN_TRANSIT
    train.cargo_type = cargo_type
    train.cargo_units = loaded
    train.destination = destination_id
    train.route_node_ids = route.node_ids
    train.route_link_ids = route.link_ids
    train.remaining_ticks = route.travel_ticks
    train.order_id = service_id
    train.blocked_reason = None
    state.finance.record_cost(train.dispatch_cost + (loaded * train.variable_cost_per_unit))
    events["dispatches"].append(
        {
            "train": train.name,
            "origin": origin_id,
            "destination": destination_id,
            "cargo": cargo_type.value,
            "units": loaded,
            "travel_ticks": route.travel_ticks,
            "route_stop_ids": [origin_id, *stops, destination_id],
            "links": list(route.link_ids),
            "order": service_id,
        }
    )
    return True


def _finish_multistop_service(
    state: GameState, train: FreightTrain, service_id: str
) -> None:
    """Mark a multi-stop order/schedule complete and reset the train."""

    schedule_id = _schedule_id_from_order_id(service_id)
    if schedule_id is not None and schedule_id in state.schedules:
        schedule = state.schedules[schedule_id]
        schedule.trips_completed += 1
        schedule.next_departure_tick = state.tick + schedule.interval_ticks
        if schedule.return_to_origin:
            train.node_id = schedule.origin
    elif service_id in state.orders:
        order = state.orders[service_id]
        order.active = False

    train.status = TrainStatus.IDLE
    train.destination = None
    train.route_node_ids = ()
    train.route_link_ids = ()
    train.order_id = None
    train.cargo_type = None
    train.blocked_reason = None
    train.current_stop_index = 0
    train.arrival_tick = None


def _execute_pickup_at_stop(
    state: GameState,
    events: FreightReport,
    train: FreightTrain,
    stop: TrainStop,
    fallback_cargo: CargoType | None,
) -> tuple[bool, int]:
    """Try to load cargo at a pickup stop. Returns (proceeded, units_loaded).

    proceeded=False means the train is blocked this tick (platform/loader cap)
    and should not advance — the caller should return immediately.
    """

    cargo_type = stop.cargo_type or train.cargo_type or fallback_cargo
    if cargo_type is None:
        return True, 0

    if not _platform_has_room(state, stop.node_id):
        _block_for_platform_capacity(
            state, events, train, node_id=stop.node_id, direction="load"
        )
        return False, 0

    origin = state.nodes[stop.node_id]
    effective_loader_rate, remaining_loader_rate = _remaining_loader_capacity(
        state, stop.node_id
    )
    available_in_train = max(0, train.capacity - train.cargo_units)
    requested = stop.units if stop.units > 0 else available_in_train
    uncapped = min(available_in_train, requested, origin.stock(cargo_type))
    planned = min(uncapped, remaining_loader_rate)

    if planned <= 0:
        if _strict_loader_missing(state, stop.node_id):
            train.status = TrainStatus.BLOCKED
            train.blocked_reason = "missing_loader"
            events["blocked"].append(
                {
                    "train": train.name,
                    "order": train.order_id,
                    "reason": f"missing loader at {stop.node_id}",
                }
            )
            events["freight_blocked"].append(
                {
                    "node": stop.node_id,
                    "train": train.name,
                    "reason": "missing_loader",
                    "direction": "load",
                }
            )
            return False, 0
        if uncapped > 0:
            train.status = TrainStatus.BLOCKED
            train.blocked_reason = "loader_capacity"
            events["freight_blocked"].append(
                {
                    "node": stop.node_id,
                    "train": train.name,
                    "reason": "loader_capacity",
                    "direction": "load",
                }
            )
            return False, 0
        return True, 0

    loaded = origin.remove_inventory(cargo_type, planned)
    record_transfer(state, stop.node_id, loaded)
    if _uses_loader_budget(state, stop.node_id):
        state.freight_loader_used_this_tick[stop.node_id] = (
            int(state.freight_loader_used_this_tick.get(stop.node_id, 0)) + loaded
        )
    _reserve_platform_slot(state, stop.node_id)
    if (
        _uses_loader_budget(state, stop.node_id)
        and loaded < uncapped
        and loaded == remaining_loader_rate
    ):
        events["loader_capped"].append(
            {
                "node": stop.node_id,
                "train": train.name,
                "cargo": cargo_type.value,
                "requested_units": requested,
                "loaded_units": loaded,
                "effective_loader_rate": effective_loader_rate,
            }
        )
    train.cargo_type = cargo_type
    train.cargo_units += loaded
    state.finance.record_cost(loaded * train.variable_cost_per_unit)
    return True, loaded


def _execute_delivery_at_stop(
    state: GameState,
    events: FreightReport,
    train: FreightTrain,
    stop: TrainStop,
    service_id: str,
) -> tuple[bool, bool]:
    """Try to unload cargo at a delivery/transfer stop.

    Returns (proceeded, all_unloaded). proceeded=False means platform-blocked.
    all_unloaded=False means partial unload — caller should mark BLOCKED so the
    train retries next tick.
    """

    if train.cargo_type is None or train.cargo_units <= 0:
        return True, True

    destination = state.nodes[stop.node_id]
    if not _platform_has_room(state, stop.node_id):
        _block_for_platform_capacity(
            state, events, train, node_id=stop.node_id, direction="unload"
        )
        return False, False

    _effective, remaining_unloader_rate = _remaining_unloader_capacity(
        state, stop.node_id
    )
    attempted = min(train.cargo_units, remaining_unloader_rate)
    if attempted <= 0:
        if _strict_unloader_missing(state, stop.node_id):
            train.status = TrainStatus.BLOCKED
            train.blocked_reason = "missing_unloader"
            events["blocked"].append(
                {
                    "train": train.name,
                    "order": service_id,
                    "reason": f"missing unloader at {stop.node_id}",
                }
            )
            events["freight_blocked"].append(
                {
                    "node": stop.node_id,
                    "train": train.name,
                    "reason": "missing_unloader",
                    "direction": "unload",
                }
            )
            return False, False
        return True, False

    accepted = destination.add_inventory(train.cargo_type, attempted)
    if accepted <= 0:
        return True, False

    if _uses_unloader_budget(state, stop.node_id):
        state.freight_unloader_used_this_tick[stop.node_id] = (
            int(state.freight_unloader_used_this_tick.get(stop.node_id, 0)) + accepted
        )
    _reserve_platform_slot(state, stop.node_id)
    record_transfer(state, stop.node_id, accepted)
    train.cargo_units -= accepted

    if stop.action == StopAction.DELIVERY:
        schedule_id = _schedule_id_from_order_id(service_id)
        if schedule_id is not None and schedule_id in state.schedules:
            state.schedules[schedule_id].delivered_units += accepted
        elif service_id in state.orders:
            order = state.orders[service_id]
            order.delivered_units += accepted

        state.finance.record_revenue(
            accepted * metadata_for(train.cargo_type).base_unit_revenue * train.revenue_modifier
        )

    events["deliveries"].append(
        {
            "train": train.name,
            "node": stop.node_id,
            "cargo": train.cargo_type.value,
            "units": accepted,
            "order": service_id,
        }
    )

    if train.cargo_units > 0:
        return True, False
    train.cargo_type = None
    return True, True


def _dispatch_to_stop(
    state: GameState,
    events: FreightReport,
    train: FreightTrain,
    *,
    service_id: str,
    next_stop: TrainStop,
    cargo_type: CargoType | None,
) -> bool:
    """Reserve a route from train.node_id to next_stop and put the train IN_TRANSIT."""

    route = route_through_stops(state, train.node_id, (), next_stop.node_id)
    if route is None:
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": f"no route {train.node_id}->{next_stop.node_id}",
            }
        )
        return False

    reservation = reserve_route_capacity(state, route.link_ids, train_id=train.id)
    if not reservation.reserved:
        reason = reservation.reason or "route capacity unavailable"
        events["blocked"].append(
            {"train": train.name, "order": service_id, "reason": reason}
        )
        events["queued"].append(
            {
                "train": train.name,
                "order": service_id,
                "origin": train.node_id,
                "destination": next_stop.node_id,
                "link": reservation.link_id,
                "reason": reason,
            }
        )
        return False

    train.status = TrainStatus.IN_TRANSIT
    train.destination = next_stop.node_id
    train.route_node_ids = route.node_ids
    train.route_link_ids = route.link_ids
    train.remaining_ticks = route.travel_ticks
    train.order_id = service_id
    train.blocked_reason = None
    train.arrival_tick = None
    state.finance.record_cost(train.dispatch_cost)
    events["dispatches"].append(
        {
            "train": train.name,
            "origin": train.node_id,
            "destination": next_stop.node_id,
            "cargo": cargo_type.value if cargo_type is not None else None,
            "units": train.cargo_units,
            "travel_ticks": route.travel_ticks,
            "route_stop_ids": [train.node_id, next_stop.node_id],
            "links": list(route.link_ids),
            "order": service_id,
        }
    )
    return True


def _process_multistop_at_node(
    state: GameState, events: FreightReport, train: FreightTrain
) -> None:
    """Process the current stop in a train's multi-stop service.

    Handles pickup/delivery/transfer/passthrough at the train's current node,
    walks past stops whose work is done, and dispatches the train to the next
    stop when ready.
    """

    service_id = train.order_id
    if service_id is None:
        train.status = TrainStatus.IDLE
        train.blocked_reason = None
        return

    train_stops = _train_stops_for_service(state, service_id)
    if not train_stops:
        train.status = TrainStatus.IDLE
        return

    cargo_type = _service_cargo_type(state, service_id)

    while train.current_stop_index < len(train_stops):
        stop = train_stops[train.current_stop_index]
        if stop.node_id != train.node_id:
            break  # need to travel to this stop next

        if stop.action == StopAction.PICKUP:
            origin = state.nodes[stop.node_id]
            stop_cargo = stop.cargo_type or cargo_type or train.cargo_type
            had_stock_before = (
                origin.stock(stop_cargo) > 0 if stop_cargo is not None else False
            )
            proceeded, _loaded = _execute_pickup_at_stop(
                state, events, train, stop, cargo_type
            )
            if not proceeded:
                return

            if (
                stop.wait_condition == WaitCondition.NONE
                and not had_stock_before
                and train.cargo_units == 0
            ):
                # Skip empty-origin pickups when not waiting for a fill.
                train.current_stop_index += 1
                train.arrival_tick = None
                continue

            if not _is_wait_satisfied(state, train, stop):
                if stop.wait_condition == WaitCondition.TIME and train.arrival_tick is None:
                    train.arrival_tick = state.tick
                train.status = TrainStatus.IDLE
                train.blocked_reason = None
                return

        elif stop.action in (StopAction.DELIVERY, StopAction.TRANSFER):
            proceeded, all_unloaded = _execute_delivery_at_stop(
                state, events, train, stop, service_id
            )
            if not proceeded:
                return
            if not _is_wait_satisfied(state, train, stop):
                if stop.wait_condition == WaitCondition.EMPTY and not all_unloaded:
                    _block_train(
                        events, train, f"unload limit reached at {stop.node_id}"
                    )
                    return
                if stop.wait_condition == WaitCondition.TIME and train.arrival_tick is None:
                    train.arrival_tick = state.tick
                train.status = TrainStatus.IDLE
                train.blocked_reason = None
                return
            if not all_unloaded:
                _block_train(events, train, f"unload limit reached at {stop.node_id}")
                return

        elif stop.action == StopAction.PASSTHROUGH:
            if not _is_wait_satisfied(state, train, stop):
                if stop.wait_condition == WaitCondition.TIME and train.arrival_tick is None:
                    train.arrival_tick = state.tick
                train.status = TrainStatus.IDLE
                train.blocked_reason = None
                return

        train.current_stop_index += 1
        train.arrival_tick = None

    if train.current_stop_index >= len(train_stops):
        _finish_multistop_service(state, train, service_id)
        return

    next_stop = train_stops[train.current_stop_index]
    if not _dispatch_to_stop(
        state, events, train, service_id=service_id, next_stop=next_stop, cargo_type=cargo_type
    ):
        if train.status == TrainStatus.IN_TRANSIT:
            return
        if train.status != TrainStatus.BLOCKED:
            train.status = TrainStatus.IDLE


def _dispatch_order(state: GameState, events: FreightReport, order: FreightOrder) -> None:
    """Load and dispatch one order if its assigned train is ready."""

    if not order.active or order.remaining_units <= 0:
        order.active = False
        return

    train = state.trains[order.train_id]
    if order.train_stops:
        if train.status != TrainStatus.IDLE:
            return
        if not consist_can_carry(train.consist, order.cargo_type):
            _block_train(events, train, "incompatible_consist")
            return
        train.order_id = order.id
        _process_multistop_at_node(state, events, train)
        return

    _dispatch_trip(
        state,
        events,
        train=train,
        origin_id=order.origin,
        destination_id=order.destination,
        cargo_type=order.cargo_type,
        requested_units=order.remaining_units,
        service_id=order.id,
    )


def _dispatch_ready_orders(state: GameState, events: FreightReport) -> None:
    """Dispatch idle assigned trains in deterministic priority order."""

    orders = sorted(state.orders.values(), key=lambda item: (-item.priority, item.id))
    for order in orders:
        _dispatch_order(state, events, order)


def _dispatch_schedule(state: GameState, events: FreightReport, schedule: FreightSchedule) -> None:
    """Dispatch one recurring schedule when due."""

    if not schedule.active or state.tick < schedule.next_departure_tick:
        return
    train = state.trains[schedule.train_id]
    service_id = f"{SCHEDULE_ORDER_PREFIX}{schedule.id}"
    if schedule.train_stops:
        if train.status != TrainStatus.IDLE:
            return
        if not consist_can_carry(train.consist, schedule.cargo_type):
            _block_train(events, train, "incompatible_consist")
            return
        train.order_id = service_id
        before_status = train.status
        _process_multistop_at_node(state, events, train)
        if train.status == TrainStatus.IN_TRANSIT and before_status == TrainStatus.IDLE:
            schedule.trips_dispatched += 1
        return
    dispatched = _dispatch_trip(
        state,
        events,
        train=train,
        origin_id=schedule.origin,
        destination_id=schedule.destination,
        cargo_type=schedule.cargo_type,
        requested_units=schedule.units_per_departure,
        service_id=service_id,
        stops=schedule.stops,
    )
    if dispatched:
        schedule.trips_dispatched += 1


def _dispatch_ready_schedules(state: GameState, events: FreightReport) -> None:
    """Dispatch due recurring schedules in deterministic priority order."""

    schedules = sorted(state.schedules.values(), key=lambda item: (-item.priority, item.id))
    for schedule in schedules:
        _dispatch_schedule(state, events, schedule)


def advance_freight(state: GameState) -> FreightReport:
    """Advance all train movement and dispatch ready freight orders."""

    _reset_empty_blocked_trains(state)
    state.platform_loading_this_tick = {}
    state.platform_queue_depth_this_tick = {}
    state.freight_loader_used_this_tick = {}
    state.freight_unloader_used_this_tick = {}
    events: FreightReport = {
        "dispatches": [],
        "in_transit": [],
        "deliveries": [],
        "blocked": [],
        "queued": [],
        "loader_capped": [],
        "freight_blocked": [],
        "trains": [],
    }
    _advance_active_trains(state, events)
    _dispatch_ready_orders(state, events)
    _dispatch_ready_schedules(state, events)
    events["trains"] = [_train_snapshot(train) for train in sorted(state.trains.values(), key=lambda item: item.id)]
    return events
