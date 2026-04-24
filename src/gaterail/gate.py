"""Wormhole gate power and slot logic for the tick simulation."""

from __future__ import annotations

from gaterail.models import GameState, GatePowerStatus, LinkMode, NetworkLink


def _gate_status_for_link(
    state: GameState,
    link: NetworkLink,
    allocated_by_world: dict[str, int],
) -> GatePowerStatus:
    """Resolve one gate's power status against current allocations."""

    source_world_id = state.link_power_source_world_id(link)
    source_world = state.worlds[source_world_id]
    allocated = allocated_by_world.get(source_world_id, 0)
    power_available = max(0, source_world.base_power_margin - allocated)
    powered = link.active and power_available >= link.power_required
    power_shortfall = 0 if powered else max(0, link.power_required - power_available)
    if powered:
        allocated_by_world[source_world_id] = allocated + link.power_required
    return GatePowerStatus(
        link_id=link.id,
        source_world_id=source_world_id,
        source_world_name=source_world.name,
        power_required=link.power_required,
        power_available=power_available,
        power_shortfall=power_shortfall,
        powered=powered,
        active=link.active,
        slot_capacity=link.capacity_per_tick,
    )


def preview_gate_power(state: GameState) -> dict[str, GatePowerStatus]:
    """Return gate power status without mutating world reservations."""

    allocated_by_world: dict[str, int] = {}
    statuses: dict[str, GatePowerStatus] = {}
    for link in state.links_by_mode(LinkMode.GATE):
        statuses[link.id] = _gate_status_for_link(state, link, allocated_by_world)
    return statuses


def evaluate_gate_power(state: GameState) -> dict[str, GatePowerStatus]:
    """Resolve powered gates and reserve their power for the current tick."""

    for world in state.worlds.values():
        world.gate_power_used = 0
    statuses = preview_gate_power(state)
    for status in statuses.values():
        if status.powered:
            state.worlds[status.source_world_id].gate_power_used += status.power_required
    state.gate_statuses = statuses
    return statuses


def reserve_gate_slots(state: GameState, link_ids: tuple[str, ...]) -> tuple[bool, str | None]:
    """Reserve one slot on every gate link in a route."""

    gate_links = [
        state.links[link_id]
        for link_id in link_ids
        if state.links[link_id].mode == LinkMode.GATE
    ]
    for link in gate_links:
        status = state.gate_statuses.get(link.id)
        if status is None or not status.powered:
            return False, f"gate {link.id} unpowered"
        if status.slots_remaining <= 0:
            return False, f"gate slots full on {link.id}"
    for link in gate_links:
        state.gate_statuses[link.id].slots_used += 1
    return True, None
