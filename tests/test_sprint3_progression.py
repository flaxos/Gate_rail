"""Tests for Sprint 3 frontier world progression."""

from io import StringIO

import pytest

from gaterail.cli import run_cli
from gaterail.models import DevelopmentTier
from gaterail.simulation import TickSimulation


def test_frontier_stalls_without_stockpile_even_before_shortage() -> None:
    simulation = TickSimulation.from_scenario("sprint3")

    report = simulation.run_ticks(2)[-1]
    frontier = report["progression"]["frontier"]

    assert report["shortages"] == {}
    assert frontier["trend"] == "stalled"
    assert frontier["stockpile_deficits"] == {
        "construction_materials": 1,
        "food": 2,
    }


def test_shortages_regress_frontier_stability_and_report_bottlenecks() -> None:
    simulation = TickSimulation.from_scenario("sprint3")

    report = simulation.run_ticks(4)[-1]
    frontier = report["progression"]["frontier"]

    assert frontier["trend"] == "regressing"
    assert frontier["shortage_streak"] == 1
    assert frontier["stability"] == pytest.approx(0.645)
    assert "shortage food 2" in frontier["bottlenecks"]
    assert "shortage construction_materials 1" in frontier["bottlenecks"]


def test_sustained_support_promotes_frontier_to_colony() -> None:
    simulation = TickSimulation.from_scenario("sprint3")

    report = simulation.run_ticks(11)[-1]
    frontier = report["progression"]["frontier"]

    assert simulation.state.worlds["frontier"].tier == DevelopmentTier.FRONTIER_COLONY
    assert frontier["trend"] == "promoted"
    assert frontier["promotion_ready"] is True
    assert frontier["promoted_to"] == "frontier_colony"
    assert frontier["stability"] == pytest.approx(0.755)


def test_promoted_frontier_stalls_on_next_tier_requirements() -> None:
    simulation = TickSimulation.from_scenario("sprint3")

    report = simulation.run_ticks(12)[-1]
    frontier = report["progression"]["frontier"]

    assert frontier["tier_name"] == "frontier_colony"
    assert frontier["next_tier"] == "industrial_colony"
    assert frontier["trend"] == "stalled"
    assert "stockpile machinery short 8" in frontier["bottlenecks"]
    assert "power margin short 10" in frontier["bottlenecks"]


def test_cli_prints_progression_and_promotion() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint3", "--ticks", "11"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Progression:" in text
    assert "Brink Frontier promoted to frontier_colony" in text
