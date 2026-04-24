"""World development and tier progression rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from gaterail.cargo import CargoType
from gaterail.models import DevelopmentTier, GameState, ProgressionTrend, WorldState


@dataclass(frozen=True, slots=True)
class TierRequirement:
    """Requirements to move from one world tier to the next."""

    target_tier: DevelopmentTier
    supported_ticks_required: int
    stability_required: float
    power_margin_required: int
    stockpile_required: dict[CargoType, int] = field(default_factory=dict)


TIER_REQUIREMENTS: dict[DevelopmentTier, TierRequirement] = {
    DevelopmentTier.OUTPOST: TierRequirement(
        target_tier=DevelopmentTier.FRONTIER_COLONY,
        supported_ticks_required=4,
        stability_required=0.70,
        power_margin_required=0,
        stockpile_required={
            CargoType.FOOD: 4,
            CargoType.CONSTRUCTION_MATERIALS: 2,
        },
    ),
    DevelopmentTier.FRONTIER_COLONY: TierRequirement(
        target_tier=DevelopmentTier.INDUSTRIAL_COLONY,
        supported_ticks_required=8,
        stability_required=0.82,
        power_margin_required=60,
        stockpile_required={
            CargoType.FOOD: 20,
            CargoType.CONSTRUCTION_MATERIALS: 20,
            CargoType.MACHINERY: 8,
        },
    ),
    DevelopmentTier.INDUSTRIAL_COLONY: TierRequirement(
        target_tier=DevelopmentTier.DEVELOPED_WORLD,
        supported_ticks_required=12,
        stability_required=0.90,
        power_margin_required=120,
        stockpile_required={
            CargoType.FOOD: 40,
            CargoType.PARTS: 20,
            CargoType.ELECTRONICS: 12,
            CargoType.MEDICAL_SUPPLIES: 10,
        },
    ),
    DevelopmentTier.DEVELOPED_WORLD: TierRequirement(
        target_tier=DevelopmentTier.CORE_WORLD,
        supported_ticks_required=16,
        stability_required=0.96,
        power_margin_required=240,
        stockpile_required={
            CargoType.CONSUMER_GOODS: 80,
            CargoType.RESEARCH_EQUIPMENT: 20,
            CargoType.REACTOR_PARTS: 12,
            CargoType.GATE_COMPONENTS: 8,
        },
    ),
}


def _tier_name(tier: DevelopmentTier) -> str:
    """Return stable lowercase tier names for reports."""

    return tier.name.lower()


def _world_inventory(state: GameState, world_id: str) -> dict[CargoType, int]:
    """Aggregate all node inventory on a world."""

    inventory: dict[CargoType, int] = {}
    for node in state.nodes.values():
        if node.world_id != world_id:
            continue
        for cargo_type, units in node.inventory.items():
            inventory[cargo_type] = inventory.get(cargo_type, 0) + units
    return inventory


def _world_shortages(state: GameState, world_id: str) -> dict[CargoType, int]:
    """Aggregate current tick shortages on a world."""

    shortages: dict[CargoType, int] = {}
    for node_id, node_shortages in state.shortages.items():
        node = state.nodes[node_id]
        if node.world_id != world_id:
            continue
        for cargo_type, units in node_shortages.items():
            shortages[cargo_type] = shortages.get(cargo_type, 0) + units
    return shortages


def _stockpile_deficits(
    inventory: dict[CargoType, int],
    requirement: TierRequirement,
) -> dict[CargoType, int]:
    """Return missing stockpile units for a requirement."""

    deficits: dict[CargoType, int] = {}
    for cargo_type, required in requirement.stockpile_required.items():
        deficit = required - inventory.get(cargo_type, 0)
        if deficit > 0:
            deficits[cargo_type] = deficit
    return deficits


def _plain_cargo_map(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed maps to report-safe dictionaries."""

    return {cargo_type.value: units for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)}


def _build_bottlenecks(
    shortages: dict[CargoType, int],
    stockpile_deficits: dict[CargoType, int],
    power_deficit: int,
    stability_deficit: float,
) -> list[str]:
    """Build compact bottleneck labels for terminal reports."""

    bottlenecks: list[str] = []
    for cargo_type, units in sorted(shortages.items(), key=lambda item: item[0].value):
        bottlenecks.append(f"shortage {cargo_type.value} {units}")
    for cargo_type, units in sorted(stockpile_deficits.items(), key=lambda item: item[0].value):
        bottlenecks.append(f"stockpile {cargo_type.value} short {units}")
    if power_deficit > 0:
        bottlenecks.append(f"power margin short {power_deficit}")
    if stability_deficit > 0:
        bottlenecks.append(f"stability short {stability_deficit:.2f}")
    return bottlenecks


def _max_tier_report(world: WorldState) -> dict[str, object]:
    """Build a report for worlds with no remaining tier requirement."""

    world.last_trend = ProgressionTrend.MAX_TIER
    return {
        "name": world.name,
        "tier": int(world.tier),
        "tier_name": _tier_name(world.tier),
        "next_tier": None,
        "trend": world.last_trend.value,
        "stability": round(world.stability, 3),
        "development_progress": world.development_progress,
        "support_streak": world.support_streak,
        "shortage_streak": world.shortage_streak,
        "supported_ticks_required": 0,
        "promotion_ready": False,
        "promoted_to": None,
        "bottlenecks": [],
        "shortages": {},
        "stockpile_deficits": {},
    }


def _apply_world_progression(
    state: GameState,
    world_id: str,
    world: WorldState,
    requirement: TierRequirement,
) -> dict[str, object]:
    """Apply one tick of progression rules to a single world."""

    inventory = _world_inventory(state, world_id)
    shortages = _world_shortages(state, world_id)
    stockpile_deficits = _stockpile_deficits(inventory, requirement)
    power_deficit = max(0, requirement.power_margin_required - world.power_margin)
    logistics_supported = not shortages and not stockpile_deficits and power_deficit == 0

    if shortages:
        world.support_streak = 0
        world.shortage_streak += 1
        world.development_progress = max(0, world.development_progress - 1)
        world.stability = max(0.0, world.stability - 0.01)
        world.last_trend = ProgressionTrend.REGRESSING
    elif logistics_supported:
        world.support_streak += 1
        world.shortage_streak = 0
        world.development_progress = min(
            requirement.supported_ticks_required,
            world.development_progress + 1,
        )
        world.stability = min(1.0, world.stability + 0.035)
        world.last_trend = ProgressionTrend.IMPROVING
    else:
        world.support_streak = 0
        world.shortage_streak = 0
        world.last_trend = ProgressionTrend.STALLED

    stability_deficit = max(0.0, requirement.stability_required - world.stability)
    promotion_ready = (
        logistics_supported
        and world.support_streak >= requirement.supported_ticks_required
        and world.development_progress >= requirement.supported_ticks_required
        and stability_deficit <= 0.0
    )
    promoted_to: str | None = None
    if promotion_ready:
        world.tier = requirement.target_tier
        promoted_to = _tier_name(requirement.target_tier)
        world.development_progress = 0
        world.support_streak = 0
        world.shortage_streak = 0
        world.last_trend = ProgressionTrend.PROMOTED

    bottlenecks = _build_bottlenecks(shortages, stockpile_deficits, power_deficit, stability_deficit)
    return {
        "name": world.name,
        "tier": int(world.tier),
        "tier_name": _tier_name(world.tier),
        "next_tier": None if promoted_to is not None else _tier_name(requirement.target_tier),
        "trend": world.last_trend.value,
        "stability": round(world.stability, 3),
        "development_progress": world.development_progress,
        "support_streak": world.support_streak,
        "shortage_streak": world.shortage_streak,
        "supported_ticks_required": requirement.supported_ticks_required,
        "promotion_ready": promotion_ready,
        "promoted_to": promoted_to,
        "bottlenecks": bottlenecks,
        "shortages": _plain_cargo_map(shortages),
        "stockpile_deficits": _plain_cargo_map(stockpile_deficits),
    }


def apply_world_progression(state: GameState) -> dict[str, dict[str, object]]:
    """Apply one tick of world progression and return report data."""

    reports: dict[str, dict[str, object]] = {}
    for world_id, world in sorted(state.worlds.items()):
        requirement = TIER_REQUIREMENTS.get(world.tier)
        if requirement is None:
            reports[world_id] = _max_tier_report(world)
            continue
        reports[world_id] = _apply_world_progression(state, world_id, world, requirement)
    return reports
