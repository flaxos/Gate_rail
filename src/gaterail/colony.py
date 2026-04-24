"""Colony behavior for population and sustainability."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.cargo import CargoType


@dataclass(slots=True)
class Colony:
    """Simple colony model centered on frontier outcomes."""

    name: str = "Frontier"
    population: int = 1_000
    morale: float = 1.0
    food_per_capita: float = 0.01
    machinery_bonus_factor: float = 0.0005

    def update(self, delivered_to_frontier: dict[CargoType, int]) -> dict[str, float | int]:
        """Apply one day of colony dynamics from delivered cargo."""

        food_units = delivered_to_frontier.get(CargoType.FOOD, 0)
        passenger_units = delivered_to_frontier.get(CargoType.PASSENGERS, 0)
        machinery_units = delivered_to_frontier.get(CargoType.MACHINERY, 0)

        required_food = int(self.population * self.food_per_capita)
        food_ratio = 1.0 if required_food <= 0 else min(1.0, food_units / required_food)
        starvation = max(0.0, 1.0 - food_ratio)

        population_loss = int(self.population * starvation * 0.02)
        self.population = max(0, self.population - population_loss + passenger_units)

        morale_delta = (food_ratio - 0.9) * 0.08 + (machinery_units * self.machinery_bonus_factor)
        self.morale = min(1.5, max(0.0, self.morale + morale_delta))

        return {
            "required_food": required_food,
            "food_ratio": food_ratio,
            "population_loss": population_loss,
            "population": self.population,
            "morale": self.morale,
        }

    @property
    def failed(self) -> bool:
        """Whether colony is considered collapsed."""

        return self.population <= 0 or self.morale <= 0.0
