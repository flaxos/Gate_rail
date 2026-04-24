"""World and planetary inventory state for GateRail."""

from __future__ import annotations

from dataclasses import dataclass, field

from gaterail.cargo import CargoType


DEFAULT_LOCATIONS: tuple[str, str] = ("Core", "Frontier")


@dataclass(slots=True)
class World:
    """Global simulation state for cargo supply and production."""

    inventories: dict[str, dict[CargoType, int]] = field(default_factory=dict)
    production_rates: dict[str, dict[CargoType, int]] = field(default_factory=dict)
    day: int = 0

    def __post_init__(self) -> None:
        for location in DEFAULT_LOCATIONS:
            self.inventories.setdefault(location, {})
            self.production_rates.setdefault(location, {})
            for cargo_type in CargoType:
                self.inventories[location].setdefault(cargo_type, 0)
                self.production_rates[location].setdefault(cargo_type, 0)

    @classmethod
    def default(cls) -> World:
        """Build a baseline world configuration."""

        inventories = {
            "Core": {
                CargoType.FOOD: 140,
                CargoType.PASSENGERS: 90,
                CargoType.MACHINERY: 55,
                CargoType.ORE: 20,
            },
            "Frontier": {
                CargoType.FOOD: 35,
                CargoType.PASSENGERS: 10,
                CargoType.MACHINERY: 5,
                CargoType.ORE: 120,
            },
        }
        production_rates = {
            "Core": {
                CargoType.FOOD: 30,
                CargoType.PASSENGERS: 24,
                CargoType.MACHINERY: 14,
                CargoType.ORE: 0,
            },
            "Frontier": {
                CargoType.FOOD: 6,
                CargoType.PASSENGERS: 2,
                CargoType.MACHINERY: 1,
                CargoType.ORE: 30,
            },
        }
        return cls(inventories=inventories, production_rates=production_rates)

    def reset_day(self) -> None:
        """Advance simulation day counter."""

        self.day += 1

    def produce(self) -> dict[str, dict[CargoType, int]]:
        """Apply daily production and return produced quantities."""

        produced: dict[str, dict[CargoType, int]] = {loc: {} for loc in DEFAULT_LOCATIONS}
        for location in DEFAULT_LOCATIONS:
            for cargo_type, qty in self.production_rates[location].items():
                if qty <= 0:
                    continue
                self.inventories[location][cargo_type] += qty
                produced[location][cargo_type] = qty
        return produced

    def available(self, location: str, cargo_type: CargoType) -> int:
        """Current available units at ``location`` for ``cargo_type``."""

        return self.inventories[location][cargo_type]

    def remove_cargo(self, location: str, cargo_type: CargoType, units: int) -> int:
        """Remove up to ``units`` and return actual removed quantity."""

        units = max(0, units)
        available = self.inventories[location][cargo_type]
        moved = min(units, available)
        self.inventories[location][cargo_type] -= moved
        return moved

    def add_cargo(self, location: str, cargo_type: CargoType, units: int) -> None:
        """Add ``units`` cargo to a location."""

        if units > 0:
            self.inventories[location][cargo_type] += units
