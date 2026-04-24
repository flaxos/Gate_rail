"""Per-tick network capacity, congestion, and disruption telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.models import GameState, LinkMode, NetworkDisruption, NetworkLink


@dataclass(frozen=True, slots=True)
class RouteReservation:
    """Result of attempting to reserve route capacity."""

    reserved: bool
    reason: str | None = None
    link_id: str | None = None


def reset_traffic_usage(state: GameState) -> None:
    """Clear per-tick link usage before dispatching new train movements."""

    state.link_usage_this_tick.clear()


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


def reserve_route_capacity(state: GameState, link_ids: tuple[str, ...]) -> RouteReservation:
    """Reserve one capacity slot on every link in a route."""

    links = [state.links[link_id] for link_id in link_ids]
    for link in links:
        if not link.active:
            return RouteReservation(False, f"link {link.id} inactive", link.id)
        if link.mode == LinkMode.GATE:
            status = state.gate_statuses.get(link.id)
            if status is None or not status.powered:
                return RouteReservation(False, f"gate {link.id} unpowered", link.id)

        capacity, disruptions = effective_link_capacity(state, link)
        if _used_slots(state, link) >= capacity:
            return RouteReservation(False, _capacity_block_reason(link, disruptions), link.id)

    for link in links:
        state.link_usage_this_tick[link.id] = state.link_usage_this_tick.get(link.id, 0) + 1
        if link.mode == LinkMode.GATE and link.id in state.gate_statuses:
            state.gate_statuses[link.id].slots_used += 1
    return RouteReservation(True)


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
    return {
        "links": links,
        "alerts": alerts,
    }
