"""Per-tick network capacity, congestion, and disruption telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.models import (
    GameState,
    LinkMode,
    NetworkDisruption,
    NetworkLink,
    TrackSignal,
    TrainStatus,
)


@dataclass(frozen=True, slots=True)
class RouteReservation:
    """Result of attempting to reserve route capacity."""

    reserved: bool
    reason: str | None = None
    link_id: str | None = None


def reset_traffic_usage(state: GameState) -> None:
    """Clear per-tick link usage before dispatching new train movements."""

    state.link_usage_this_tick.clear()
    state.rail_block_reservations.clear()
    state.rail_block_blocked_this_tick.clear()


def active_signals_for_link(state: GameState, link_id: str) -> list[TrackSignal]:
    """Return active signals protecting one link block."""

    return sorted(
        [
            signal
            for signal in state.track_signals.values()
            if signal.link_id == link_id and signal.active
        ],
        key=lambda item: item.id,
    )


def signaled_rail_link_ids(state: GameState) -> list[str]:
    """Return rail links that currently have at least one active signal."""

    link_ids = {
        signal.link_id
        for signal in state.track_signals.values()
        if signal.active
        and signal.link_id in state.links
        and state.links[signal.link_id].mode == LinkMode.RAIL
    }
    return sorted(link_ids)


def active_disruptions_for_link(state: GameState, link_id: str) -> list[NetworkDisruption]:
    """Return disruptions currently affecting a link."""

    return sorted(
        [
            disruption
            for disruption in state.disruptions.values()
            if disruption.link_id == link_id and disruption.active_at(state.tick)
        ],
        key=lambda item: item.id,
    )


def effective_link_capacity(state: GameState, link: NetworkLink) -> tuple[int, list[NetworkDisruption]]:
    """Return current link capacity after active disruptions."""

    disruptions = active_disruptions_for_link(state, link.id)
    capacity = link.capacity_per_tick
    for disruption in disruptions:
        capacity = min(capacity, int(link.capacity_per_tick * disruption.capacity_multiplier))
    return max(0, capacity), disruptions


def _used_slots(state: GameState, link: NetworkLink) -> int:
    """Return current usage for a link, including legacy gate slot counters."""

    used = state.link_usage_this_tick.get(link.id, 0)
    if link.mode == LinkMode.GATE and link.id in state.gate_statuses:
        used = max(used, state.gate_statuses[link.id].slots_used)
    return used


def _capacity_block_reason(link: NetworkLink, disruptions: list[NetworkDisruption]) -> str:
    """Return a player-facing reason for a capacity failure."""

    if disruptions:
        reasons = ", ".join(disruption.reason for disruption in disruptions)
        return f"link {link.id} disrupted: {reasons}"
    if link.mode == LinkMode.GATE:
        return f"gate slots full on {link.id}"
    return f"traffic capacity full on {link.id}"


def _rail_block_occupiers(state: GameState, link_id: str, excluding_train_id: str | None = None) -> list[str]:
    """Return trains currently occupying or reserving a protected rail block."""

    occupiers: set[str] = set()
    for train in state.trains.values():
        if train.id == excluding_train_id:
            continue
        if train.status == TrainStatus.IN_TRANSIT and link_id in train.route_link_ids:
            occupiers.add(train.id)
    reserved_by = state.rail_block_reservations.get(link_id)
    if reserved_by is not None and reserved_by != excluding_train_id:
        occupiers.add(reserved_by)
    return sorted(occupiers)


def _signal_block_conflict(
    state: GameState,
    link: NetworkLink,
    train_id: str | None,
) -> RouteReservation | None:
    """Return a signal/block conflict for a link, if one exists."""

    if link.mode != LinkMode.RAIL:
        return None
    signals = active_signals_for_link(state, link.id)
    if not signals:
        return None
    occupiers = _rail_block_occupiers(state, link.id, excluding_train_id=train_id)
    if not occupiers:
        return None
    reason = f"signal block occupied on {link.id} by {', '.join(occupiers)}"
    state.rail_block_blocked_this_tick.append(
        {
            "link": link.id,
            "block": link.id,
            "train_id": train_id,
            "occupiers": occupiers,
            "signal_ids": [signal.id for signal in signals],
            "reason": reason,
        }
    )
    return RouteReservation(False, reason, link.id)


def _reserve_signal_blocks(
    state: GameState,
    links: list[NetworkLink],
    train_id: str | None,
) -> None:
    """Record this tick's protected rail-block reservations."""

    owner = train_id or "route"
    for link in links:
        if link.mode == LinkMode.RAIL and active_signals_for_link(state, link.id):
            state.rail_block_reservations[link.id] = owner


def reserve_route_capacity(
    state: GameState,
    link_ids: tuple[str, ...],
    train_id: str | None = None,
) -> RouteReservation:
    """Reserve one capacity slot on every link in a route."""

    links = [state.links[link_id] for link_id in link_ids]
    for link in links:
        if not link.active:
            return RouteReservation(False, f"link {link.id} inactive", link.id)
        if link.mode == LinkMode.GATE:
            status = state.gate_statuses.get(link.id)
            if status is None or not status.powered:
                return RouteReservation(False, f"gate {link.id} unpowered", link.id)

        signal_conflict = _signal_block_conflict(state, link, train_id)
        if signal_conflict is not None:
            return signal_conflict

        capacity, disruptions = effective_link_capacity(state, link)
        if _used_slots(state, link) >= capacity:
            return RouteReservation(False, _capacity_block_reason(link, disruptions), link.id)

    for link in links:
        state.link_usage_this_tick[link.id] = state.link_usage_this_tick.get(link.id, 0) + 1
        if link.mode == LinkMode.GATE and link.id in state.gate_statuses:
            state.gate_statuses[link.id].slots_used += 1
    _reserve_signal_blocks(state, links, train_id)
    return RouteReservation(True)


def build_signal_report(state: GameState) -> dict[str, object]:
    """Build report-safe signal and protected-block telemetry."""

    signals = {
        signal.id: {
            "link": signal.link_id,
            "node": signal.node_id,
            "kind": signal.kind.value,
            "active": signal.active,
            "block": signal.link_id,
        }
        for signal in sorted(state.track_signals.values(), key=lambda item: item.id)
    }
    blocks: dict[str, dict[str, object]] = {}
    for link_id in signaled_rail_link_ids(state):
        signal_ids = [signal.id for signal in active_signals_for_link(state, link_id)]
        occupiers = _rail_block_occupiers(state, link_id)
        blocks[link_id] = {
            "link": link_id,
            "block": link_id,
            "signal_ids": signal_ids,
            "occupied": bool(occupiers),
            "occupiers": occupiers,
            "reserved_by": state.rail_block_reservations.get(link_id),
        }
    return {
        "signals": signals,
        "blocks": blocks,
        "blocked": list(state.rail_block_blocked_this_tick),
    }


def build_traffic_report(state: GameState) -> dict[str, object]:
    """Build report-safe link pressure and disruption telemetry."""

    links: dict[str, dict[str, object]] = {}
    alerts: list[dict[str, object]] = []
    for link in sorted(state.links.values(), key=lambda item: item.id):
        capacity, disruptions = effective_link_capacity(state, link)
        used = _used_slots(state, link)
        remaining = max(0, capacity - used)
        pressure = 1.0 if capacity <= 0 and used > 0 else (used / capacity if capacity > 0 else 0.0)
        disruption_reasons = [disruption.reason for disruption in disruptions]
        congested = capacity > 0 and used >= capacity
        disrupted = bool(disruptions)
        status = {
            "mode": link.mode.value,
            "base_capacity": link.capacity_per_tick,
            "capacity": capacity,
            "used": used,
            "remaining": remaining,
            "pressure": round(pressure, 2),
            "congested": congested,
            "disrupted": disrupted,
            "disruption_reasons": disruption_reasons,
        }
        links[link.id] = status
        if disrupted:
            alerts.append(
                {
                    "link": link.id,
                    "severity": "blocked" if capacity == 0 else "degraded",
                    "reason": ", ".join(disruption_reasons),
                    "capacity": capacity,
                    "used": used,
                }
            )
        if congested:
            alerts.append(
                {
                    "link": link.id,
                    "severity": "congested",
                    "reason": "capacity exhausted",
                    "capacity": capacity,
                    "used": used,
                }
            )
    for event in state.rail_block_blocked_this_tick:
        link_id = str(event.get("link", "unknown"))
        alerts.append(
            {
                "link": link_id,
                "severity": "signal_blocked",
                "reason": str(event.get("reason", "signal block occupied")),
                "capacity": 1,
                "used": 1,
            }
        )
    return {
        "links": links,
        "alerts": alerts,
    }
