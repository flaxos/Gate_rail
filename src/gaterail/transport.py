"""Transport graph helpers for rail and gate routing."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from gaterail.models import GameState, LinkMode


@dataclass(frozen=True, slots=True)
class Route:
    """Resolved route through the network graph."""

    node_ids: tuple[str, ...]
    link_ids: tuple[str, ...]
    travel_ticks: int
    gate_power_required: int


def shortest_route(
    state: GameState,
    origin: str,
    destination: str,
    allowed_modes: set[LinkMode] | None = None,
    require_operational: bool = True,
) -> Route | None:
    """Find the lowest-travel-time route between two nodes."""

    if origin not in state.nodes or destination not in state.nodes:
        return None
    if origin == destination:
        return Route(node_ids=(origin,), link_ids=(), travel_ticks=0, gate_power_required=0)

    queue: list[tuple[int, str, tuple[str, ...], tuple[str, ...], int]] = [
        (0, origin, (origin,), (), 0)
    ]
    best_cost: dict[str, int] = {origin: 0}

    while queue:
        travel_ticks, node_id, node_path, link_path, gate_power = heappop(queue)
        if node_id == destination:
            return Route(
                node_ids=node_path,
                link_ids=link_path,
                travel_ticks=travel_ticks,
                gate_power_required=gate_power,
            )

        if require_operational:
            links = state.links_from(node_id)
        else:
            links = sorted(
                [
                    link
                    for link in state.links.values()
                    if link.active and link.connects(node_id)
                ],
                key=lambda item: item.id,
            )
        for link in links:
            if allowed_modes is not None and link.mode not in allowed_modes:
                continue
            next_node = link.other_end(node_id)
            if next_node is None:
                continue
            next_cost = travel_ticks + link.travel_ticks
            if next_cost >= best_cost.get(next_node, 1_000_000_000):
                continue
            best_cost[next_node] = next_cost
            heappush(
                queue,
                (
                    next_cost,
                    next_node,
                    node_path + (next_node,),
                    link_path + (link.id,),
                    gate_power + link.power_required,
                ),
            )
    return None
