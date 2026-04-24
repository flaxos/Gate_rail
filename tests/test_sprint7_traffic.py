"""Tests for Sprint 7 traffic pressure and recoverable disruption behavior."""

from io import StringIO

from gaterail.cli import run_cli
from gaterail.models import NetworkDisruption
from gaterail.scenarios import build_sprint7_scenario
from gaterail.simulation import TickSimulation


def test_sprint7_scenario_adds_chokepoint_and_disruption() -> None:
    state = build_sprint7_scenario()

    assert state.links["rail_core_yard_gate"].capacity_per_tick == 1
    assert state.disruptions["frontier_outer_gate_alignment"] == NetworkDisruption(
        id="frontier_outer_gate_alignment",
        link_id="gate_frontier_outer",
        start_tick=13,
        end_tick=14,
        capacity_multiplier=0.0,
        reason="gate alignment maintenance",
    )


def test_link_capacity_queues_extra_departures() -> None:
    simulation = TickSimulation.from_scenario("sprint7")

    report = simulation.step_tick()

    assert report["traffic"]["links"]["rail_core_yard_gate"]["capacity"] == 1
    assert report["traffic"]["links"]["rail_core_yard_gate"]["used"] == 1
    assert report["traffic"]["links"]["rail_core_yard_gate"]["congested"] is True
    assert {
        "train": "Civitas",
        "order": "schedule:core_material_service",
        "origin": "core_yard",
        "destination": "frontier_settlement",
        "link": "rail_core_yard_gate",
        "reason": "traffic capacity full on rail_core_yard_gate",
    } in report["freight"]["queued"]


def test_timed_disruption_blocks_then_recovers() -> None:
    simulation = TickSimulation.from_scenario("sprint7")

    disrupted_report = simulation.run_ticks(13)[-1]

    assert disrupted_report["traffic"]["links"]["gate_frontier_outer"]["disrupted"] is True
    assert disrupted_report["traffic"]["links"]["gate_frontier_outer"]["capacity"] == 0
    assert {
        "train": "Mercy",
        "order": "schedule:ashfall_medical_service",
        "origin": "frontier_settlement",
        "destination": "outer_outpost",
        "link": "gate_frontier_outer",
        "reason": "link gate_frontier_outer disrupted: gate alignment maintenance",
    } in disrupted_report["freight"]["queued"]

    recovered_report = simulation.run_ticks(2)[-1]

    assert recovered_report["tick"] == 15
    assert recovered_report["traffic"]["links"]["gate_frontier_outer"]["disrupted"] is False
    assert any(event["train"] == "Mercy" for event in recovered_report["freight"]["dispatches"])


def test_monthly_ledger_summarizes_traffic_pressure() -> None:
    simulation = TickSimulation.from_scenario("sprint7")

    simulation.run_ticks(30)

    ledger = simulation.monthly_reports[0]
    assert ledger["traffic_pressure"]["rail_core_yard_gate"]["full_ticks"] == 8
    assert ledger["traffic_pressure"]["rail_core_yard_gate"]["peak_pressure"] == 1.0
    assert ledger["traffic_pressure"]["gate_frontier_outer"]["disrupted_ticks"] == 2


def test_cli_sprint7_prints_traffic() -> None:
    output = StringIO()

    result = run_cli(["--scenario", "sprint7", "--ticks", "15"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Disruptions: frontier_outer_gate_alignment gate_frontier_outer ticks 13-14" in text
    assert "queued Civitas on rail_core_yard_gate" in text
    assert "Traffic: congested rail_core_yard_gate 1/1 capacity exhausted" in text
    assert "Traffic: blocked gate_frontier_outer 0/0 gate alignment maintenance" in text
