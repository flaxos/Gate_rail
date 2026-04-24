"""Tests for colony food, morale, and population dynamics."""

import pytest

from gaterail.cargo import CargoType
from gaterail.colony import Colony


def test_food_shortage_applies_population_and_morale_penalty() -> None:
    colony = Colony(population=1_000, morale=1.0, food_per_capita=0.01)

    update = colony.update({CargoType.FOOD: 5})

    assert update["required_food"] == 10
    assert update["food_ratio"] == 0.5
    assert update["population_loss"] == 10
    assert colony.population == 990
    assert colony.morale == pytest.approx(0.968)


def test_food_and_machinery_support_recovery_and_passenger_growth() -> None:
    colony = Colony(population=1_000, morale=0.8, food_per_capita=0.01)

    update = colony.update(
        {
            CargoType.FOOD: 20,
            CargoType.MACHINERY: 100,
            CargoType.PASSENGERS: 12,
        }
    )

    assert update["food_ratio"] == 1.0
    assert update["population_loss"] == 0
    assert colony.population == 1_012
    assert colony.morale == pytest.approx(0.858)
