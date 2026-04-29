"""Cargo definitions and metadata for GateRail."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CargoType(StrEnum):
    """Supported cargo categories."""

    FOOD = "food"
    PASSENGERS = "passengers"
    MACHINERY = "machinery"
    ORE = "ore"
    CARBON_FEEDSTOCK = "carbon_feedstock"
    STONE = "stone"
    BIOMASS = "biomass"
    WATER = "water"
    FUEL = "fuel"
    COOLANT = "coolant"
    METAL = "metal"
    PARTS = "parts"
    ELECTRONICS = "electronics"
    URANIUM = "uranium"
    CONSTRUCTION_MATERIALS = "construction_materials"
    CONSUMER_GOODS = "consumer_goods"
    MEDICAL_SUPPLIES = "medical_supplies"
    RESEARCH_EQUIPMENT = "research_equipment"
    REACTOR_PARTS = "reactor_parts"
    GATE_COMPONENTS = "gate_components"


from gaterail.models import TrainConsist


@dataclass(frozen=True, slots=True)
class CargoMetadata:
    """Static balancing data associated with a cargo type."""

    priority: int
    base_unit_revenue: float
    preferred_origin: str
    preferred_destination: str


CARGO_METADATA: dict[CargoType, CargoMetadata] = {
    CargoType.FOOD: CargoMetadata(
        priority=100,
        base_unit_revenue=11.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.PASSENGERS: CargoMetadata(
        priority=90,
        base_unit_revenue=15.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.MACHINERY: CargoMetadata(
        priority=80,
        base_unit_revenue=22.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.ORE: CargoMetadata(
        priority=70,
        base_unit_revenue=18.0,
        preferred_origin="Frontier",
        preferred_destination="Core",
    ),
    CargoType.CARBON_FEEDSTOCK: CargoMetadata(
        priority=65,
        base_unit_revenue=13.0,
        preferred_origin="Frontier",
        preferred_destination="Core",
    ),
    CargoType.STONE: CargoMetadata(
        priority=45,
        base_unit_revenue=7.0,
        preferred_origin="Frontier",
        preferred_destination="Frontier",
    ),
    CargoType.BIOMASS: CargoMetadata(
        priority=55,
        base_unit_revenue=9.0,
        preferred_origin="Frontier",
        preferred_destination="Core",
    ),
    CargoType.WATER: CargoMetadata(
        priority=85,
        base_unit_revenue=6.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.FUEL: CargoMetadata(
        priority=95,
        base_unit_revenue=20.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.COOLANT: CargoMetadata(
        priority=75,
        base_unit_revenue=16.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.METAL: CargoMetadata(
        priority=68,
        base_unit_revenue=19.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.PARTS: CargoMetadata(
        priority=78,
        base_unit_revenue=24.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.ELECTRONICS: CargoMetadata(
        priority=72,
        base_unit_revenue=32.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.URANIUM: CargoMetadata(
        priority=96,
        base_unit_revenue=48.0,
        preferred_origin="Frontier",
        preferred_destination="Core",
    ),
    CargoType.CONSTRUCTION_MATERIALS: CargoMetadata(
        priority=82,
        base_unit_revenue=14.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.CONSUMER_GOODS: CargoMetadata(
        priority=60,
        base_unit_revenue=18.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.MEDICAL_SUPPLIES: CargoMetadata(
        priority=88,
        base_unit_revenue=30.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.RESEARCH_EQUIPMENT: CargoMetadata(
        priority=50,
        base_unit_revenue=45.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.REACTOR_PARTS: CargoMetadata(
        priority=92,
        base_unit_revenue=55.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
    CargoType.GATE_COMPONENTS: CargoMetadata(
        priority=98,
        base_unit_revenue=70.0,
        preferred_origin="Core",
        preferred_destination="Frontier",
    ),
}


CARGO_CONSIST_MAP: dict[CargoType, TrainConsist] = {
    CargoType.ORE: TrainConsist.BULK_HOPPER,
    CargoType.STONE: TrainConsist.BULK_HOPPER,
    CargoType.CARBON_FEEDSTOCK: TrainConsist.BULK_HOPPER,
    CargoType.WATER: TrainConsist.LIQUID_TANKER,
    CargoType.FUEL: TrainConsist.LIQUID_TANKER,
    CargoType.COOLANT: TrainConsist.LIQUID_TANKER,
    CargoType.ELECTRONICS: TrainConsist.PROTECTED,
    CargoType.RESEARCH_EQUIPMENT: TrainConsist.PROTECTED,
    CargoType.REACTOR_PARTS: TrainConsist.PROTECTED,
    CargoType.GATE_COMPONENTS: TrainConsist.PROTECTED,
}


def metadata_for(cargo_type: CargoType) -> CargoMetadata:
    """Return static metadata for ``cargo_type``."""

    return CARGO_METADATA[cargo_type]


def required_consist_for(cargo_type: CargoType) -> TrainConsist:
    """Return the required TrainConsist for a given cargo, or GENERAL if none."""

    return CARGO_CONSIST_MAP.get(cargo_type, TrainConsist.GENERAL)
