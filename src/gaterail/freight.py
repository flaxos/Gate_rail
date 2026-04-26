"""Fixed-tick freight order and train movement execution."""

from __future__ import annotations

from gaterail.cargo import CargoType, metadata_for
from gaterail.economy import record_transfer
from gaterail.models import FreightOrder, FreightSchedule, FreightTrain, GameState, TrainStatus
from gaterail.traffic import reserve_route_capacity
from gaterail.transport import shortest_route


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


def _finish_order_if_complete(order: FreightOrder) -> None:
    """Deactivate one-shot orders when their requested volume has arrived."""

    if order.remaining_units <= 0:
        order.active = False


def _schedule_id_from_order_id(order_id: str | None) -> str | None:
    """Return schedule id encoded into a train order field."""

    if order_id is None or not order_id.startswith(SCHEDULE_ORDER_PREFIX):
        return None
    return order_id.removeprefix(SCHEDULE_ORDER_PREFIX)


def _attempt_unload(state: GameState, events: FreightReport, train: FreightTrain) -> None:
    """Unload arrived or storage-blocked cargo into the current node."""

    if train.cargo_type is None or train.cargo_units <= 0:
        train.status = TrainStatus.IDLE
        train.blocked_reason = None
        return

    destination = state.nodes[train.node_id]
    transfer_limit = max(0, destination.effective_inbound_rate())
    attempted = min(train.cargo_units, transfer_limit)
    accepted = destination.add_inventory(train.cargo_type, attempted)
    if accepted <= 0:
        _block_train(events, train, f"storage full at {destination.id}")
        return

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

    route = shortest_route(state, origin_id, destination_id)
    if route is None:
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": f"no route {origin_id}->{destination_id}",
            }
        )
        return False

    origin = state.nodes[origin_id]
    load_limit = max(0, origin.effective_outbound_rate())
    planned_units = min(train.capacity, requested_units, load_limit, origin.stock(cargo_type))
    if planned_units <= 0:
        events["blocked"].append(
            {
                "train": train.name,
                "order": service_id,
                "reason": f"no {cargo_type.value} at {origin.id}",
            }
        )
        return False

    reservation = reserve_route_capacity(state, route.link_ids)
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
            "links": list(route.link_ids),
            "order": service_id,
        }
    )
    return True


def _dispatch_order(state: GameState, events: FreightReport, order: FreightOrder) -> None:
    """Load and dispatch one order if its assigned train is ready."""

    if not order.active or order.remaining_units <= 0:
        order.active = False
        return

    _dispatch_trip(
        state,
        events,
        train=state.trains[order.train_id],
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
    dispatched = _dispatch_trip(
        state,
        events,
        train=state.trains[schedule.train_id],
        origin_id=schedule.origin,
        destination_id=schedule.destination,
        cargo_type=schedule.cargo_type,
        requested_units=schedule.units_per_departure,
        service_id=f"{SCHEDULE_ORDER_PREFIX}{schedule.id}",
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

    events: FreightReport = {
        "dispatches": [],
        "in_transit": [],
        "deliveries": [],
        "blocked": [],
        "queued": [],
        "trains": [],
    }
    _advance_active_trains(state, events)
    _dispatch_ready_orders(state, events)
    _dispatch_ready_schedules(state, events)
    events["trains"] = [_train_snapshot(train) for train in sorted(state.trains.values(), key=lambda item: item.id)]
    return events
