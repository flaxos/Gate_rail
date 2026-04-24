"""Tests for schedule ordering, slot exhaustion delays, and accounting."""

from gaterail.cargo import CargoType
from gaterail.schedule import DailySchedule
from gaterail.simulation import Simulation


def test_priority_ordering_is_descending() -> None:
    schedule = DailySchedule()
    schedule.add(CargoType.ORE, "Frontier", "Core", 1, priority=10)
    schedule.add(CargoType.FOOD, "Core", "Frontier", 1, priority=30)
    schedule.add(CargoType.MACHINERY, "Core", "Frontier", 1, priority=20)

    ordered_types = [movement.cargo_type for movement in schedule.ordered()]
    assert ordered_types == [CargoType.FOOD, CargoType.MACHINERY, CargoType.ORE]


def test_slots_exhaustion_skips_lower_priority_movements_and_tracks_results() -> None:
    sim = Simulation()
    sim.gate.max_slots_per_day = 1

    schedule = DailySchedule()
    schedule.add(CargoType.FOOD, "Core", "Frontier", 10, priority=100)
    schedule.add(CargoType.ORE, "Frontier", "Core", 10, priority=10)

    report = sim.run_day(schedule)
    result = report["schedule_result"]

    assert len(result.executed) >= 1
    assert any("No gate slot available" in message for message in result.skipped)

    moved_food = result.moved_units.get(CargoType.FOOD, 0)
    moved_ore = result.moved_units.get(CargoType.ORE, 0)
    assert moved_food > 0
    assert moved_ore == 0

    executed_units = sum(entry["units"] for entry in result.executed)
    assert result.total_units_moved == executed_units
