"""Economy primitives for resources, production, and demand."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from gaterail.cargo import CargoType
from gaterail.models import GameState, NetworkNode, NodeKind


class ResourceCategory(StrEnum):
    """High-level cargo families used by balancing and reporting."""

    BULK_SOLID = "bulk_solid"
    UTILITY = "utility"
    INDUSTRIAL = "industrial"
    CIVIL = "civil"
    ADVANCED = "advanced"


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    """Static definition for a resource in the fixed-tick backend."""

    cargo_type: CargoType
    category: ResourceCategory
    description: str


RESOURCE_DEFINITIONS: dict[CargoType, ResourceDefinition] = {
    CargoType.ORE: ResourceDefinition(CargoType.ORE, ResourceCategory.BULK_SOLID, "Raw mineral feedstock."),
    CargoType.CARBON_FEEDSTOCK: ResourceDefinition(
        CargoType.CARBON_FEEDSTOCK,
        ResourceCategory.BULK_SOLID,
        "Carbon-rich bulk material for fuel and industry.",
    ),
    CargoType.STONE: ResourceDefinition(CargoType.STONE, ResourceCategory.BULK_SOLID, "Aggregate and tunneling spoil."),
    CargoType.BIOMASS: ResourceDefinition(CargoType.BIOMASS, ResourceCategory.BULK_SOLID, "Organic bulk feedstock."),
    CargoType.WATER: ResourceDefinition(CargoType.WATER, ResourceCategory.UTILITY, "Water for life support and industry."),
    CargoType.FUEL: ResourceDefinition(CargoType.FUEL, ResourceCategory.UTILITY, "Portable fuel for industry and backup power."),
    CargoType.COOLANT: ResourceDefinition(CargoType.COOLANT, ResourceCategory.UTILITY, "Thermal control fluid."),
    CargoType.FOOD: ResourceDefinition(CargoType.FOOD, ResourceCategory.CIVIL, "Food supply for population centers."),
    CargoType.PASSENGERS: ResourceDefinition(CargoType.PASSENGERS, ResourceCategory.CIVIL, "Abstract population mobility."),
    CargoType.CONSUMER_GOODS: ResourceDefinition(
        CargoType.CONSUMER_GOODS,
        ResourceCategory.CIVIL,
        "Civilian quality-of-life goods.",
    ),
    CargoType.MEDICAL_SUPPLIES: ResourceDefinition(
        CargoType.MEDICAL_SUPPLIES,
        ResourceCategory.CIVIL,
        "Health and emergency supplies.",
    ),
    CargoType.MACHINERY: ResourceDefinition(CargoType.MACHINERY, ResourceCategory.INDUSTRIAL, "Heavy machinery."),
    CargoType.METAL: ResourceDefinition(CargoType.METAL, ResourceCategory.INDUSTRIAL, "Refined structural metal."),
    CargoType.PARTS: ResourceDefinition(CargoType.PARTS, ResourceCategory.INDUSTRIAL, "General industrial parts."),
    CargoType.ELECTRONICS: ResourceDefinition(
        CargoType.ELECTRONICS,
        ResourceCategory.INDUSTRIAL,
        "Control and automation hardware.",
    ),
    CargoType.CONSTRUCTION_MATERIALS: ResourceDefinition(
        CargoType.CONSTRUCTION_MATERIALS,
        ResourceCategory.INDUSTRIAL,
        "Bulk construction and repair materials.",
    ),
    CargoType.RESEARCH_EQUIPMENT: ResourceDefinition(
        CargoType.RESEARCH_EQUIPMENT,
        ResourceCategory.ADVANCED,
        "Specialized research equipment.",
    ),
    CargoType.REACTOR_PARTS: ResourceDefinition(
        CargoType.REACTOR_PARTS,
        ResourceCategory.ADVANCED,
        "High-value reactor maintenance parts.",
    ),
    CargoType.GATE_COMPONENTS: ResourceDefinition(
        CargoType.GATE_COMPONENTS,
        ResourceCategory.ADVANCED,
        "Precision components for gate construction.",
    ),
}


@dataclass(frozen=True, slots=True)
class DemandResult:
    """Per-tick consumption and shortage rollup."""

    consumed: dict[str, dict[CargoType, int]]
    shortages: dict[str, dict[CargoType, int]]


@dataclass(frozen=True, slots=True)
class SpecializationProfile:
    """Import/export identity for a world specialization."""

    id: str
    label: str
    imports: dict[CargoType, int] = field(default_factory=dict)
    exports: dict[CargoType, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProductionRecipe:
    """One specialization-driven production rule."""

    id: str
    specialization: str
    node_kind: NodeKind
    inputs: dict[CargoType, int] = field(default_factory=dict)
    outputs: dict[CargoType, int] = field(default_factory=dict)


SPECIALIZATION_PROFILES: dict[str, SpecializationProfile] = {
    "manufacturing": SpecializationProfile(
        id="manufacturing",
        label="Manufacturing Core",
        imports={
            CargoType.ORE: 2,
            CargoType.RESEARCH_EQUIPMENT: 1,
        },
        exports={
            CargoType.CONSTRUCTION_MATERIALS: 4,
            CargoType.PARTS: 2,
            CargoType.MEDICAL_SUPPLIES: 1,
        },
    ),
    "mining": SpecializationProfile(
        id="mining",
        label="Mining Frontier",
        imports={
            CargoType.FOOD: 2,
            CargoType.CONSTRUCTION_MATERIALS: 1,
            CargoType.MACHINERY: 1,
        },
        exports={CargoType.ORE: 6},
    ),
    "survey_outpost": SpecializationProfile(
        id="survey_outpost",
        label="Survey Outpost",
        imports={
            CargoType.FOOD: 1,
            CargoType.MEDICAL_SUPPLIES: 1,
            CargoType.PARTS: 1,
        },
        exports={CargoType.RESEARCH_EQUIPMENT: 1},
    ),
}


PRODUCTION_RECIPES: tuple[ProductionRecipe, ...] = (
    ProductionRecipe(
        id="ore_fabrication",
        specialization="manufacturing",
        node_kind=NodeKind.DEPOT,
        inputs={CargoType.ORE: 2},
        outputs={
            CargoType.CONSTRUCTION_MATERIALS: 4,
            CargoType.PARTS: 2,
            CargoType.MEDICAL_SUPPLIES: 1,
        },
    ),
    ProductionRecipe(
        id="deep_mine_boost",
        specialization="mining",
        node_kind=NodeKind.EXTRACTOR,
        inputs={CargoType.MACHINERY: 1},
        outputs={CargoType.ORE: 6},
    ),
    ProductionRecipe(
        id="field_research",
        specialization="survey_outpost",
        node_kind=NodeKind.SETTLEMENT,
        inputs={
            CargoType.MEDICAL_SUPPLIES: 1,
            CargoType.PARTS: 1,
        },
        outputs={CargoType.RESEARCH_EQUIPMENT: 1},
    ),
)


def _plain_cargo_map(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed maps to report-safe dictionaries."""

    return {
        cargo_type.value: units
        for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)
        if units > 0
    }


def _add_cargo(total: dict[CargoType, int], cargo_type: CargoType, units: int) -> None:
    """Accumulate cargo units."""

    if units > 0:
        total[cargo_type] = total.get(cargo_type, 0) + units


def _nodes_for_world(state: GameState, world_id: str) -> list[NetworkNode]:
    """Return stable nodes for a world."""

    return [node for node in sorted(state.nodes.values(), key=lambda item: item.id) if node.world_id == world_id]


def _target_node_for_recipe(state: GameState, world_id: str, recipe: ProductionRecipe) -> NetworkNode | None:
    """Find the node where a recipe should run."""

    nodes = _nodes_for_world(state, world_id)
    for node in nodes:
        if node.kind == recipe.node_kind:
            return node
    return nodes[0] if nodes else None


def _can_run_recipe(node: NetworkNode, recipe: ProductionRecipe) -> bool:
    """Return whether a node has the required recipe inputs."""

    return all(node.stock(cargo_type) >= units for cargo_type, units in recipe.inputs.items())


def _run_recipe(node: NetworkNode, recipe: ProductionRecipe) -> tuple[dict[CargoType, int], dict[CargoType, int]]:
    """Consume inputs and add outputs for one recipe batch."""

    consumed: dict[CargoType, int] = {}
    produced: dict[CargoType, int] = {}
    for cargo_type, units in recipe.inputs.items():
        removed = node.remove_inventory(cargo_type, units)
        _add_cargo(consumed, cargo_type, removed)
    for cargo_type, units in recipe.outputs.items():
        accepted = node.add_inventory(cargo_type, units)
        _add_cargo(produced, cargo_type, accepted)
    return consumed, produced


def specialization_profiles_for_state(state: GameState) -> dict[str, dict[str, object]]:
    """Return import/export profile data for all specialized worlds."""

    profiles: dict[str, dict[str, object]] = {}
    for world_id, world in sorted(state.worlds.items()):
        if world.specialization is None:
            continue
        profile = SPECIALIZATION_PROFILES.get(world.specialization)
        if profile is None:
            continue
        profiles[world_id] = {
            "label": profile.label,
            "specialization": profile.id,
            "imports": _plain_cargo_map(profile.imports),
            "exports": _plain_cargo_map(profile.exports),
        }
    return profiles


def apply_specialized_production(state: GameState) -> dict[str, object]:
    """Apply specialization-driven recipes and return report data."""

    profiles = specialization_profiles_for_state(state)
    report: dict[str, object] = {
        "profiles": profiles,
        "consumed": {},
        "produced": {},
        "blocked": [],
    }
    if not state.economic_identity_enabled:
        return report

    consumed_by_node: dict[str, dict[CargoType, int]] = {}
    produced_by_node: dict[str, dict[CargoType, int]] = {}
    blocked: list[dict[str, object]] = []

    for world_id, world in sorted(state.worlds.items()):
        if world.specialization is None:
            continue
        for recipe in PRODUCTION_RECIPES:
            if recipe.specialization != world.specialization:
                continue
            node = _target_node_for_recipe(state, world_id, recipe)
            if node is None:
                blocked.append({"world": world_id, "recipe": recipe.id, "reason": "no production node"})
                continue
            if not _can_run_recipe(node, recipe):
                missing = {
                    cargo_type: units - node.stock(cargo_type)
                    for cargo_type, units in recipe.inputs.items()
                    if node.stock(cargo_type) < units
                }
                blocked.append(
                    {
                        "world": world_id,
                        "node": node.id,
                        "recipe": recipe.id,
                        "reason": "missing inputs",
                        "missing": _plain_cargo_map(missing),
                    }
                )
                continue
            consumed, produced = _run_recipe(node, recipe)
            for cargo_type, units in consumed.items():
                _add_cargo(consumed_by_node.setdefault(node.id, {}), cargo_type, units)
            for cargo_type, units in produced.items():
                _add_cargo(produced_by_node.setdefault(node.id, {}), cargo_type, units)

    report["consumed"] = {
        node_id: _plain_cargo_map(cargo_map)
        for node_id, cargo_map in sorted(consumed_by_node.items())
    }
    report["produced"] = {
        node_id: _plain_cargo_map(cargo_map)
        for node_id, cargo_map in sorted(produced_by_node.items())
    }
    report["blocked"] = blocked
    return report


def apply_node_production(state: GameState) -> dict[str, dict[CargoType, int]]:
    """Apply one tick of node production."""

    produced: dict[str, dict[CargoType, int]] = {}
    for node_id, node in sorted(state.nodes.items()):
        for cargo_type, units in sorted(node.production.items(), key=lambda item: item[0].value):
            accepted = node.add_inventory(cargo_type, units)
            if accepted > 0:
                produced.setdefault(node_id, {})[cargo_type] = accepted
    return produced


def apply_node_demand(state: GameState) -> DemandResult:
    """Apply one tick of node demand and store shortages on state."""

    consumed: dict[str, dict[CargoType, int]] = {}
    shortages: dict[str, dict[CargoType, int]] = {}
    for node_id, node in sorted(state.nodes.items()):
        for cargo_type, required in sorted(node.demand.items(), key=lambda item: item[0].value):
            if required <= 0:
                continue
            removed = node.remove_inventory(cargo_type, required)
            if removed > 0:
                consumed.setdefault(node_id, {})[cargo_type] = removed
            deficit = required - removed
            if deficit > 0:
                shortages.setdefault(node_id, {})[cargo_type] = deficit
    state.shortages = shortages
    return DemandResult(consumed=consumed, shortages=shortages)
