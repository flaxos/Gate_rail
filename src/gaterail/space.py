"""Space extraction and collection station logistics."""

from __future__ import annotations

from gaterail.models import GameState, MiningMissionStatus


def advance_mining_missions(state: GameState) -> dict[str, object]:
    """Advance fixed-tick mining missions."""

    active_count = 0
    completed = 0
    failed = 0
    returned_resources: dict[str, int] = {}

    for mission in state.mining_missions.values():
        if mission.status not in (
            MiningMissionStatus.EN_ROUTE,
            MiningMissionStatus.MINING,
            MiningMissionStatus.RETURNING,
        ):
            continue

        mission.ticks_remaining -= 1

        if mission.ticks_remaining <= 0:
            mission.status = MiningMissionStatus.COMPLETED
            
            site = state.space_sites.get(mission.site_id)
            node = state.nodes.get(mission.return_node_id)
            
            if not site or not node:
                mission.status = MiningMissionStatus.FAILED
                failed += 1
                continue

            resource_id = site.resource_id
            delivered = node.add_resource_inventory(resource_id, mission.expected_yield)
            
            if delivered > 0:
                returned_resources[resource_id] = returned_resources.get(resource_id, 0) + delivered
            
            completed += 1
        else:
            active_count += 1

    return {
        "active": active_count,
        "completed_this_tick": completed,
        "failed_this_tick": failed,
        "returned_resources": returned_resources,
    }
