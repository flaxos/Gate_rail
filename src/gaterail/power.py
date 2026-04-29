"""Resource-backed world power generation."""

from __future__ import annotations

from gaterail.models import GameState, PowerPlant


def _plain_resource_map(mapping: dict[str, int]) -> dict[str, int]:
    """Return stable positive resource maps for power reports."""

    return {
        resource_id: int(units)
        for resource_id, units in sorted(mapping.items())
        if int(units) > 0
    }


def _plant_missing_inputs(state: GameState, plant: PowerPlant) -> dict[str, int]:
    """Return missing resource units for one plant."""

    node = state.nodes[plant.node_id]
    return {
        resource_id: units - node.resource_stock(resource_id)
        for resource_id, units in plant.inputs.items()
        if node.resource_stock(resource_id) < units
    }


def reset_power_generation(state: GameState) -> None:
    """Clear transient generated-power state before applying plants."""

    for world in state.worlds.values():
        world.power_generated_this_tick = 0
    state.power_generation_this_tick = {}
    state.power_plant_blocked = {}


def apply_power_plants(state: GameState) -> dict[str, object]:
    """Consume resource inputs and add generated power to owning worlds."""

    reset_power_generation(state)
    consumed_by_plant: dict[str, dict[str, int]] = {}
    generated_by_world: dict[str, int] = {}
    plant_entries: dict[str, dict[str, object]] = {}
    blocked_entries: list[dict[str, object]] = []

    for plant_id, plant in sorted(state.power_plants.items()):
        node = state.nodes[plant.node_id]
        world = state.worlds[node.world_id]
        entry = {
            "id": plant.id,
            "node": node.id,
            "world": world.id,
            "kind": plant.kind.value,
            "active": plant.active,
            "inputs": _plain_resource_map(plant.inputs),
            "power_output": plant.power_output,
            "generated": 0,
            "missing": {},
        }
        plant_entries[plant_id] = entry
        if not plant.active:
            continue

        missing = _plant_missing_inputs(state, plant)
        if missing:
            plain_missing = _plain_resource_map(missing)
            entry["missing"] = plain_missing
            state.power_plant_blocked[plant_id] = dict(missing)
            blocked_entries.append(
                {
                    "plant": plant.id,
                    "node": node.id,
                    "world": world.id,
                    "kind": plant.kind.value,
                    "reason": "missing power plant inputs",
                    "missing": plain_missing,
                    "power_output": plant.power_output,
                }
            )
            continue

        consumed: dict[str, int] = {}
        for resource_id, units in plant.inputs.items():
            removed = node.remove_resource_inventory(resource_id, units)
            if removed > 0:
                consumed[resource_id] = removed
        if consumed:
            consumed_by_plant[plant_id] = _plain_resource_map(consumed)
        world.power_generated_this_tick += plant.power_output
        state.power_generation_this_tick[world.id] = world.power_generated_this_tick
        generated_by_world[world.id] = world.power_generated_this_tick
        entry["generated"] = plant.power_output

    return {
        "generated": {
            world_id: int(power)
            for world_id, power in sorted(generated_by_world.items())
            if int(power) > 0
        },
        "consumed": {
            plant_id: resource_map
            for plant_id, resource_map in sorted(consumed_by_plant.items())
        },
        "plants": plant_entries,
        "blocked": blocked_entries,
    }
