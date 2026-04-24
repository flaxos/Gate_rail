"""Train entities and helpers."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.cargo import CargoType, metadata_for


@dataclass(frozen=True, slots=True)
class TrainMovement:
    """Resolved movement performed by a train."""

    train_name: str
    cargo_type: CargoType
    origin: str
    destination: str
    units: int
    revenue: float
    cost: float

    @property
    def profit(self) -> float:
        """Movement profit."""

        return self.revenue - self.cost


@dataclass(slots=True)
class Train:
    """Cargo train with per-trip capacity and economics."""

    name: str
    capacity: int = 20
    trips_per_day: int = 2
    trip_cost: float = 75.0
    variable_cost_per_unit: float = 1.1
    revenue_modifier: float = 1.0
    trips_used_today: int = 0

    def reset_day(self) -> None:
        """Reset usage counters for a new day."""

        self.trips_used_today = 0

    @property
    def trips_remaining(self) -> int:
        """Remaining trips available today."""

        return max(0, self.trips_per_day - self.trips_used_today)

    def can_run_trip(self) -> bool:
        """Whether this train can still run another trip."""

        return self.trips_remaining > 0

    def move(
        self,
        cargo_type: CargoType,
        origin: str,
        destination: str,
        requested_units: int,
    ) -> TrainMovement | None:
        """Execute one trip and return movement details if possible."""

        if requested_units <= 0 or not self.can_run_trip():
            return None
        units = min(requested_units, self.capacity)
        self.trips_used_today += 1
        unit_revenue = metadata_for(cargo_type).base_unit_revenue * self.revenue_modifier
        revenue = units * unit_revenue
        cost = self.trip_cost + (units * self.variable_cost_per_unit)
        return TrainMovement(
            train_name=self.name,
            cargo_type=cargo_type,
            origin=origin,
            destination=destination,
            units=units,
            revenue=revenue,
            cost=cost,
        )
