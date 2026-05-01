"""Space extraction and collection station logistics."""

from __future__ import annotations

from gaterail.models import GameState, MiningMission, MiningMissionStatus, NetworkNode, SpaceSite


MISSION_FUEL_PER_TRAVEL_TICK = 6
MISSION_POWER_PER_TRAVEL_TICK = 3


def mission_fuel_required(site: SpaceSite) -> int:
    """Return the deterministic launch-fuel requirement for one site."""

    return max(0, int(site.travel_ticks) * MISSION_FUEL_PER_TRAVEL_TICK)


def mission_power_required(site: SpaceSite) -> int:
    """Return the deterministic world-power reservation for one site."""

    return max(0, int(site.travel_ticks) * MISSION_POWER_PER_TRAVEL_TICK)


def mission_return_capacity(node: NetworkNode) -> int:
    """Return current free storage on one mission return node."""

    return max(0, node.effective_storage_capacity() - node.total_inventory())


def _release_reserved_power(state: GameState, mission: MiningMission) -> None:
    """Release one mission's reserved power exactly once."""

    if mission.reserved_power <= 0:
        return
    launch_node = state.nodes.get(mission.launch_node_id)
    if launch_node is None:
        mission.reserved_power = 0
        return
    world = state.worlds.get(launch_node.world_id)
    if world is None:
        mission.reserved_power = 0
        return
    world.power_used = max(0, world.power_used - mission.reserved_power)
    mission.reserved_power = 0


def advance_mining_missions(state: GameState) -> dict[str, object]:
    """Advance fixed-tick mining missions."""

    active_count = 0
    completed = 0
    failed = 0
    returned_resources: dict[str, int] = {}
    dropped_units: list[dict[str, int | str]] = []

    for mission in sorted(state.mining_missions.values(), key=lambda item: item.id):
        if mission.status == MiningMissionStatus.FAILED:
            if mission.reserved_power > 0:
                _release_reserved_power(state, mission)
                failed += 1
            continue
        if mission.status == MiningMissionStatus.COMPLETED:
            if mission.reserved_power > 0:
                _release_reserved_power(state, mission)
            continue
        if mission.status not in (
            MiningMissionStatus.EN_ROUTE,
            MiningMissionStatus.MINING,
            MiningMissionStatus.RETURNING,
        ):
            continue

        mission.ticks_remaining -= 1

        if mission.ticks_remaining <= 0:
            site = state.space_sites.get(mission.site_id)
            node = state.nodes.get(mission.return_node_id)
            if not site or not node:
                mission.status = MiningMissionStatus.FAILED
                _release_reserved_power(state, mission)
                failed += 1
                continue

            mission.status = MiningMissionStatus.COMPLETED
            resource_id = site.resource_id
            delivered = node.add_resource_inventory(resource_id, mission.expected_yield)
            dropped = max(0, mission.expected_yield - delivered)
            if delivered > 0:
                returned_resources[resource_id] = returned_resources.get(resource_id, 0) + delivered
            if dropped > 0:
                dropped_units.append(
                    {
                        "mission_id": mission.id,
                        "dropped_units": dropped,
                    }
                )
            _release_reserved_power(state, mission)
            completed += 1
        else:
            active_count += 1

    return {
        "active": active_count,
        "completed_this_tick": completed,
        "failed_this_tick": failed,
        "returned_resources": returned_resources,
        "dropped_units": dropped_units,
    }
