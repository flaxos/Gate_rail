"""Tests for simulation run horizons, report readability, and failure detection."""

from gaterail.schedule import DailySchedule
from gaterail.simulation import Simulation


def test_run_one_day_returns_single_readable_report() -> None:
    sim = Simulation(max_days=30)

    reports = sim.run(days=1)

    assert len(reports) == 1
    report = reports[0]
    assert report["day"] == 1
    assert report["status"] == "running"
    assert report["phase_order"][0] == "reset_gate_slots"
    assert report["phase_order"][-1] == "failure_success_checks"


def test_run_thirty_days_reaches_success_and_has_readable_summary_fields() -> None:
    sim = Simulation(max_days=30)

    reports = sim.run(days=30)

    assert len(reports) == 30
    final = reports[-1]
    assert sim.status == "success"
    assert final["status"] == "success"
    assert final["reason"] == "survived_duration"
    assert isinstance(final["finance"]["cash"], float)
    assert isinstance(final["colony"]["population"], int)


def test_failure_state_detection_when_gate_is_non_operational() -> None:
    sim = Simulation(max_days=10)
    sim.gate.max_wear = 1.0
    sim.gate.wear = 1.0

    report = sim.run_day(DailySchedule())

    assert report["status"] == "failed"
    assert report["reason"] == "gate_failed"
    assert sim.status == "failed"
