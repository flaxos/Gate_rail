"""Data-driven resource definitions for industry and extraction planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from gaterail.cargo import CargoType


class ResourceCategory(StrEnum):
    """High-level resource groups used by industry progression."""

    RAW_SOURCE = "raw_source"
    REFINED_ELEMENT = "refined_element"
    INDUSTRIAL_MATERIAL = "industrial_material"
    MANUFACTURED_GOOD = "manufactured_good"
    ADVANCED_SYSTEM = "advanced_system"
    EXOTIC = "exotic"


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    """Static metadata for an extractable, refined, or manufactured resource."""

    id: str
    name: str
    category: ResourceCategory
    description: str
    cargo_type: CargoType | None = None
    symbol: str | None = None
    atomic_number: int | None = None
    isotope: str | None = None
    rarity: str = "common"
    discovered_by_default: bool = True
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResourceDeposit:
    """A surveyed natural deposit on one world."""

    id: str
    world_id: str
    resource_id: str
    name: str
    grade: float = 1.0
    yield_per_tick: int = 0
    discovered: bool = True
    remaining_estimate: int | None = None


RESOURCE_DEFINITIONS: dict[str, ResourceDefinition] = {
    "mixed_ore": ResourceDefinition(
        id="mixed_ore",
        name="Mixed Ore",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="Unsorted metal-bearing ore suitable for early smelting.",
        tags=("ore", "starter"),
    ),
    "iron_rich_ore": ResourceDefinition(
        id="iron_rich_ore",
        name="Iron-rich Ore",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="High-ferrous ore body that can support dedicated iron output.",
        tags=("ore", "iron"),
    ),
    "copper_sulfide_ore": ResourceDefinition(
        id="copper_sulfide_ore",
        name="Copper Sulfide Ore",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="Copper-bearing ore for conductive materials and electronics.",
        tags=("ore", "copper"),
    ),
    "bauxite": ResourceDefinition(
        id="bauxite",
        name="Bauxite",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="Aluminum-bearing ore for light structural parts.",
        tags=("ore", "aluminum"),
    ),
    "silica_sand": ResourceDefinition(
        id="silica_sand",
        name="Silica Sand",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.STONE,
        description="Silicon feedstock for glass, ceramics, and wafers.",
        tags=("silicon", "wafer"),
    ),
    "carbon_feedstock": ResourceDefinition(
        id="carbon_feedstock",
        name="Carbon Feedstock",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.CARBON_FEEDSTOCK,
        description="Organic or mineral carbon source for fuel, polymers, and composites.",
        tags=("carbon", "fuel"),
    ),
    "water_ice": ResourceDefinition(
        id="water_ice",
        name="Water Ice",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.WATER,
        description="Frozen water source for coolant, life support, and electrolysis.",
        tags=("water", "coolant", "space"),
    ),
    "fissile_ore": ResourceDefinition(
        id="fissile_ore",
        name="Fissile Ore",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="Low-grade radioactive ore for reactor fuel chains.",
        rarity="uncommon",
        tags=("power", "reactor"),
    ),
    "rare_earth_concentrate": ResourceDefinition(
        id="rare_earth_concentrate",
        name="Rare Earth Concentrate",
        category=ResourceCategory.RAW_SOURCE,
        cargo_type=CargoType.ORE,
        description="Magnet and precision-electronics source material.",
        rarity="uncommon",
        tags=("electronics", "advanced"),
    ),
    "iron": ResourceDefinition(
        id="iron",
        name="Iron",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined structural metal.",
        symbol="Fe",
        atomic_number=26,
        tags=("metal", "structural"),
    ),
    "copper": ResourceDefinition(
        id="copper",
        name="Copper",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined conductive metal.",
        symbol="Cu",
        atomic_number=29,
        tags=("metal", "conductor"),
    ),
    "aluminum": ResourceDefinition(
        id="aluminum",
        name="Aluminum",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined lightweight structural metal.",
        symbol="Al",
        atomic_number=13,
        tags=("metal", "structural"),
    ),
    "silicon": ResourceDefinition(
        id="silicon",
        name="Silicon",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined semiconductor element.",
        symbol="Si",
        atomic_number=14,
        tags=("wafer", "electronics"),
    ),
    "carbon": ResourceDefinition(
        id="carbon",
        name="Carbon",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined carbon for composites, fuel, and advanced materials.",
        symbol="C",
        atomic_number=6,
        tags=("composite", "fuel"),
    ),
    "hydrogen": ResourceDefinition(
        id="hydrogen",
        name="Hydrogen",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Light element refined from water or volatile ice for fuel chemistry.",
        symbol="H",
        atomic_number=1,
        tags=("fuel", "chemistry"),
    ),
    "oxygen": ResourceDefinition(
        id="oxygen",
        name="Oxygen",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined oxidizer and life-support element.",
        symbol="O",
        atomic_number=8,
        tags=("life_support", "chemistry"),
    ),
    "nitrogen": ResourceDefinition(
        id="nitrogen",
        name="Nitrogen",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Atmospheric and chemical feedstock for habitats and industry.",
        symbol="N",
        atomic_number=7,
        tags=("life_support", "chemistry"),
    ),
    "lithium": ResourceDefinition(
        id="lithium",
        name="Lithium",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Light metal for batteries, coolant chemistry, and fusion support.",
        symbol="Li",
        atomic_number=3,
        rarity="uncommon",
        tags=("power", "battery"),
    ),
    "cobalt": ResourceDefinition(
        id="cobalt",
        name="Cobalt",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined specialty metal for high-performance alloys and electronics.",
        symbol="Co",
        atomic_number=27,
        rarity="uncommon",
        tags=("alloy", "electronics"),
    ),
    "uranium": ResourceDefinition(
        id="uranium",
        name="Uranium",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined fissile element for reactor fuel fabrication.",
        symbol="U",
        atomic_number=92,
        rarity="uncommon",
        tags=("power", "reactor"),
    ),
    "thorium": ResourceDefinition(
        id="thorium",
        name="Thorium",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Refined fertile reactor material for later power chains.",
        symbol="Th",
        atomic_number=90,
        rarity="uncommon",
        tags=("power", "reactor"),
    ),
    "helium_3": ResourceDefinition(
        id="helium_3",
        name="Helium-3",
        category=ResourceCategory.REFINED_ELEMENT,
        description="Rare fusion isotope expected from gas pockets or remote mining.",
        symbol="He",
        atomic_number=2,
        isotope="3",
        rarity="rare",
        tags=("fusion", "space", "power"),
    ),
    "fuel": ResourceDefinition(
        id="fuel",
        name="Fuel",
        category=ResourceCategory.INDUSTRIAL_MATERIAL,
        cargo_type=CargoType.FUEL,
        description="Portable energy carrier for trains, plants, and remote worksites.",
        tags=("power", "logistics"),
    ),
    "coolant": ResourceDefinition(
        id="coolant",
        name="Coolant",
        category=ResourceCategory.INDUSTRIAL_MATERIAL,
        cargo_type=CargoType.COOLANT,
        description="Industrial heat-transfer medium for reactors and processors.",
        tags=("power", "processing"),
    ),
    "steel": ResourceDefinition(
        id="steel",
        name="Steel",
        category=ResourceCategory.INDUSTRIAL_MATERIAL,
        cargo_type=CargoType.METAL,
        description="Bulk structural alloy made from iron and carbon.",
        tags=("metal", "structural"),
    ),
    "ceramics": ResourceDefinition(
        id="ceramics",
        name="Ceramics",
        category=ResourceCategory.INDUSTRIAL_MATERIAL,
        cargo_type=CargoType.CONSTRUCTION_MATERIALS,
        description="Heat-resistant processed silicates for plants, rail works, and Railgate anchor hardware.",
        tags=("heat", "construction", "railgate"),
    ),
    "parts": ResourceDefinition(
        id="parts",
        name="Parts",
        category=ResourceCategory.MANUFACTURED_GOOD,
        cargo_type=CargoType.PARTS,
        description="Machined parts used by industry blocks and construction crews.",
        tags=("factory", "construction"),
    ),
    "electronics": ResourceDefinition(
        id="electronics",
        name="Electronics",
        category=ResourceCategory.MANUFACTURED_GOOD,
        cargo_type=CargoType.ELECTRONICS,
        description="Control boards, sensors, and industrial automation assemblies.",
        tags=("factory", "control"),
    ),
    "semiconductors": ResourceDefinition(
        id="semiconductors",
        name="Semiconductors",
        category=ResourceCategory.MANUFACTURED_GOOD,
        cargo_type=CargoType.ELECTRONICS,
        description="Wafer and chip output for advanced plants and Railgate control systems.",
        rarity="uncommon",
        tags=("wafer", "advanced", "railgate"),
    ),
    "reactor_parts": ResourceDefinition(
        id="reactor_parts",
        name="Reactor Assemblies",
        category=ResourceCategory.ADVANCED_SYSTEM,
        cargo_type=CargoType.REACTOR_PARTS,
        description="Specialized assemblies for plant upgrades and Railgate power support.",
        rarity="uncommon",
        tags=("power", "advanced", "railgate"),
    ),
    "gate_components": ResourceDefinition(
        id="gate_components",
        name="Aperture Control Components",
        category=ResourceCategory.ADVANCED_SYSTEM,
        cargo_type=CargoType.GATE_COMPONENTS,
        description="Precision control frames, field lenses, and alignment electronics used to stabilize route-bound Railgate apertures.",
        rarity="rare",
        tags=("railgate", "aperture", "advanced"),
    ),
    "gate_reactive_isotope": ResourceDefinition(
        id="gate_reactive_isotope",
        name="Horizon-reactive Isotope",
        category=ResourceCategory.EXOTIC,
        description="Undiscovered exotic isotope theorized from post-Horizon Event aperture research.",
        rarity="exotic",
        discovered_by_default=False,
        tags=("horizon", "railgate", "exotic", "research"),
    ),
    "null_lattice_crystal": ResourceDefinition(
        id="null_lattice_crystal",
        name="Null-lattice Crystal",
        category=ResourceCategory.EXOTIC,
        description="Theoretical crystalline resource sought by Transit Combines beyond surveyed corridors.",
        rarity="exotic",
        discovered_by_default=False,
        tags=("space", "corridor", "exotic", "research"),
    ),
}


def resource_definition(resource_id: str) -> ResourceDefinition:
    """Return one resource definition by stable id."""

    try:
        return RESOURCE_DEFINITIONS[resource_id]
    except KeyError as exc:
        raise KeyError(f"unknown resource id: {resource_id}") from exc


def resource_definitions() -> tuple[ResourceDefinition, ...]:
    """Return all resource definitions in deterministic order."""

    return tuple(RESOURCE_DEFINITIONS[resource_id] for resource_id in sorted(RESOURCE_DEFINITIONS))


def resource_definition_to_dict(definition: ResourceDefinition) -> dict[str, object]:
    """Serialize resource definition metadata for snapshots and reports."""

    payload: dict[str, object] = {
        "id": definition.id,
        "name": definition.name,
        "category": definition.category.value,
        "description": definition.description,
        "cargo_type": None if definition.cargo_type is None else definition.cargo_type.value,
        "symbol": definition.symbol,
        "atomic_number": definition.atomic_number,
        "isotope": definition.isotope,
        "rarity": definition.rarity,
        "discovered_by_default": definition.discovered_by_default,
        "tags": list(definition.tags),
    }
    return payload


def resource_catalog_payload() -> list[dict[str, object]]:
    """Return the full resource catalog as JSON-safe data."""

    return [resource_definition_to_dict(definition) for definition in resource_definitions()]


def resource_deposit_to_dict(deposit: ResourceDeposit, *, include_resource: bool = False) -> dict[str, object]:
    """Serialize one resource deposit."""

    payload: dict[str, object] = {
        "id": deposit.id,
        "world_id": deposit.world_id,
        "resource_id": deposit.resource_id,
        "name": deposit.name,
        "grade": round(float(deposit.grade), 3),
        "yield_per_tick": int(deposit.yield_per_tick),
        "discovered": deposit.discovered,
        "remaining_estimate": deposit.remaining_estimate,
    }
    if include_resource:
        definition = resource_definition(deposit.resource_id)
        payload["resource"] = resource_definition_to_dict(definition)
    return payload
