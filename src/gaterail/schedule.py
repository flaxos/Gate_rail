"""Daily schedule generation and execution results."""

from __future__ import annotations

from dataclasses import dataclass, field

from gaterail.cargo import CargoType, metadata_for


@dataclass(frozen=True, slots=True)
class ScheduledMovement:
    """A requested movement in the daily plan."""

    cargo_type: CargoType
    origin: str
    destination: str
    units: int
    priority: int


@dataclass(slots=True)
class ScheduleResult:
    """Execution result summary for a daily schedule."""

    executed: list[dict[str, object]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    moved_units: dict[CargoType, int] = field(default_factory=dict)

    @property
    def total_units_moved(self) -> int:
        """Total number of units moved during schedule processing."""

        return sum(self.moved_units.values())


@dataclass(slots=True)
class DailySchedule:
    """Collection of scheduled movements for one simulation day."""

    movements: list[ScheduledMovement] = field(default_factory=list)

    def add(
        self,
        cargo_type: CargoType,
        origin: str,
        destination: str,
        units: int,
        *,
        priority: int | None = None,
    ) -> None:
        """Add one movement to the schedule."""

        resolved_priority = metadata_for(cargo_type).priority if priority is None else priority
        self.movements.append(
            ScheduledMovement(
                cargo_type=cargo_type,
                origin=origin,
                destination=destination,
                units=max(0, units),
                priority=resolved_priority,
            )
        )

    def ordered(self) -> list[ScheduledMovement]:
        """Return movements sorted by descending priority."""

        return sorted(self.movements, key=lambda item: item.priority, reverse=True)

    @classmethod
    def generate_default(cls, world: object) -> DailySchedule:
        """Generate default directional schedule with cargo priorities.

        Priority order and directions:
        - Core -> Frontier: food, passengers, machinery
        - Frontier -> Core: ore
        """

        # We only need ``available`` from world.
        schedule = cls()
        schedule.add(
            CargoType.FOOD,
            "Core",
            "Frontier",
            getattr(world, "available")("Core", CargoType.FOOD),
            priority=100,
        )
        schedule.add(
            CargoType.PASSENGERS,
            "Core",
            "Frontier",
            getattr(world, "available")("Core", CargoType.PASSENGERS),
            priority=90,
        )
        schedule.add(
            CargoType.MACHINERY,
            "Core",
            "Frontier",
            getattr(world, "available")("Core", CargoType.MACHINERY),
            priority=80,
        )
        schedule.add(
            CargoType.ORE,
            "Frontier",
            "Core",
            getattr(world, "available")("Frontier", CargoType.ORE),
            priority=70,
        )
        return schedule
