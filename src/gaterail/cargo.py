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
}


def metadata_for(cargo_type: CargoType) -> CargoMetadata:
    """Return static metadata for ``cargo_type``."""

    return CARGO_METADATA[cargo_type]
