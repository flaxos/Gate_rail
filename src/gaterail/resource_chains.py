"""Resource-catalog extraction, local movement, and recipe processing."""

from __future__ import annotations

from gaterail.economy import record_transfer
from gaterail.models import GameState, LinkMode, NetworkNode, ResourceRecipe
from gaterail.resources import resource_definition


def _plain_resource_map(mapping: dict[str, int]) -> dict[str, int]:
    """Return a deterministic report-safe resource map."""

    return {
        resource_id: int(units)
        for resource_id, units in sorted(mapping.items())
        if int(units) > 0
    }


def _add_resource(total: dict[str, int], resource_id: str, units: int) -> None:
    """Accumulate resource units."""

    if units > 0:
        total[resource_id] = total.get(resource_id, 0) + units


def _nodes_for_resource_distribution(state: GameState, node: NetworkNode) -> list[NetworkNode]:
    """Return same-world rail neighbours that can pull resource inputs."""

    neighbours: dict[str, NetworkNode] = {}
    for link in state.links_from(node.id, mode=LinkMode.RAIL):
        other_id = link.other_end(node.id)
        if other_id is None or other_id == node.id:
            continue
        other = state.nodes.get(other_id)
        if other is None or other.world_id != node.world_id:
            continue
        if not _effective_resource_pull_demand(other):
            continue
        neighbours[other.id] = other
    return [neighbours[node_id] for node_id in sorted(neighbours)]


def _effective_resource_pull_demand(node: NetworkNode) -> dict[str, int]:
    """Combine declared resource demand and resource recipe inputs."""

    combined: dict[str, int] = dict(node.resource_demand)
    if node.resource_recipe is not None:
        for resource_id, units in node.resource_recipe.inputs.items():
            combined[resource_id] = combined.get(resource_id, 0) + units
    return combined


def apply_resource_extraction(state: GameState) -> dict[str, dict[str, int]]:
    """Extract deposit-backed and direct resource production into node inventories."""

    produced_by_node: dict[str, dict[str, int]] = {}
    for node_id, node in sorted(state.nodes.items()):
        if node.construction_project_id is not None:
            continue
        production: dict[str, int] = dict(node.resource_production)
        if node.resource_deposit_id is not None:
            deposit = state.resource_deposits[node.resource_deposit_id]
            if deposit.discovered and deposit.yield_per_tick > 0:
                production[deposit.resource_id] = production.get(deposit.resource_id, 0) + deposit.yield_per_tick
        for resource_id, units in sorted(production.items()):
            resource_definition(resource_id)
            accepted = node.add_resource_inventory(resource_id, units)
            if accepted > 0:
                _add_resource(produced_by_node.setdefault(node_id, {}), resource_id, accepted)
    return {
        node_id: _plain_resource_map(resource_map)
        for node_id, resource_map in sorted(produced_by_node.items())
    }


def apply_resource_distribution(state: GameState) -> dict[str, dict[str, dict[str, int]]]:
    """Move local resource units to neighbouring nodes with unmet resource inputs."""

    distribution: dict[str, dict[str, dict[str, int]]] = {}
    for node_id, node in sorted(state.nodes.items()):
        if node.construction_project_id is not None:
            continue
        if node.total_resource_inventory() <= 0:
            continue
        budget = node.effective_outbound_rate()
        if budget <= 0:
            continue
        for neighbour in _nodes_for_resource_distribution(state, node):
            if budget <= 0:
                break
            pull_demand = _effective_resource_pull_demand(neighbour)
            for resource_id, required in sorted(pull_demand.items()):
                if budget <= 0:
                    break
                if required <= 0:
                    continue
                deficit = required - neighbour.resource_stock(resource_id)
                if deficit <= 0:
                    continue
                available = node.resource_stock(resource_id)
                if available <= 0:
                    continue
                push = min(deficit, available, budget)
                if push <= 0:
                    continue
                removed = node.remove_resource_inventory(resource_id, push)
                if removed <= 0:
                    continue
                accepted = neighbour.add_resource_inventory(resource_id, removed)
                if accepted < removed:
                    node.add_resource_inventory(resource_id, removed - accepted)
                if accepted <= 0:
                    continue
                budget -= accepted
                record_transfer(state, node.id, accepted)
                record_transfer(state, neighbour.id, accepted)
                per_node = distribution.setdefault(node_id, {})
                per_neighbour = per_node.setdefault(neighbour.id, {})
                per_neighbour[resource_id] = per_neighbour.get(resource_id, 0) + accepted
    return distribution


def _resource_chain_node(node: NetworkNode) -> bool:
    """Return whether a node participates in the resource-chain layer."""

    return (
        bool(node.resource_inventory)
        or bool(node.resource_production)
        or bool(node.resource_demand)
        or node.resource_recipe is not None
        or node.resource_deposit_id is not None
    )


def resource_branch_pressure(state: GameState) -> list[dict[str, object]]:
    """Return simple local rail pressure warnings for resource-chain clusters."""

    chain_node_ids = {
        node_id
        for node_id, node in state.nodes.items()
        if _resource_chain_node(node)
    }
    pressure: list[dict[str, object]] = []
    for node_id in sorted(chain_node_ids):
        node = state.nodes[node_id]
        resource_links: list[str] = []
        neighbours: list[str] = []
        for link in state.links_from(node_id, mode=LinkMode.RAIL):
            other_id = link.other_end(node_id)
            if other_id is None or other_id not in chain_node_ids:
                continue
            resource_links.append(link.id)
            neighbours.append(other_id)
        degree = len(resource_links)
        if degree < 2:
            continue
        severity = "branch" if degree >= 3 else "watch"
        if node.resource_recipe is not None and len(node.resource_recipe.inputs) >= 2:
            severity = "branch"
        pressure.append(
            {
                "node": node.id,
                "name": node.name,
                "degree": degree,
                "severity": severity,
                "resource_links": sorted(resource_links),
                "neighbours": sorted(neighbours),
                "recipe": None if node.resource_recipe is None else node.resource_recipe.id,
                "recipe_kind": None if node.resource_recipe is None else node.resource_recipe.kind.value,
            }
        )
    return pressure


def _missing_resource_inputs(node: NetworkNode, recipe: ResourceRecipe) -> dict[str, int]:
    """Return recipe resource shortfalls for one node."""

    return {
        resource_id: units - node.resource_stock(resource_id)
        for resource_id, units in recipe.inputs.items()
        if node.resource_stock(resource_id) < units
    }


def apply_resource_recipes(state: GameState) -> dict[str, object]:
    """Run per-node resource recipes and record blocked resource chains."""

    consumed_by_node: dict[str, dict[str, int]] = {}
    produced_by_node: dict[str, dict[str, int]] = {}
    blocked_entries: list[dict[str, object]] = []
    blocked_by_node: dict[str, dict[str, int]] = {}

    for node_id, node in sorted(state.nodes.items()):
        if node.construction_project_id is not None:
            continue
        recipe = node.resource_recipe
        if recipe is None:
            continue
        missing = _missing_resource_inputs(node, recipe)
        if missing:
            plain_missing = _plain_resource_map(missing)
            blocked_entries.append(
                {
                    "node": node_id,
                    "recipe": recipe.id,
                    "recipe_kind": recipe.kind.value,
                    "reason": "missing resource inputs",
                    "missing": plain_missing,
                }
            )
            blocked_by_node[node_id] = dict(missing)
            continue
        for resource_id, units in recipe.inputs.items():
            removed = node.remove_resource_inventory(resource_id, units)
            _add_resource(consumed_by_node.setdefault(node_id, {}), resource_id, removed)
        for resource_id, units in recipe.outputs.items():
            accepted = node.add_resource_inventory(resource_id, units)
            _add_resource(produced_by_node.setdefault(node_id, {}), resource_id, accepted)

    state.resource_recipe_blocked = blocked_by_node
    return {
        "consumed": {
            node_id: _plain_resource_map(resource_map)
            for node_id, resource_map in sorted(consumed_by_node.items())
        },
        "produced": {
            node_id: _plain_resource_map(resource_map)
            for node_id, resource_map in sorted(produced_by_node.items())
        },
        "blocked": blocked_entries,
    }
