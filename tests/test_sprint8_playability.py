"""Tests for Sprint 8 CLI playability and repeatable playtest support."""

from io import StringIO

from gaterail.cli import run_cli
from gaterail.persistence import load_simulation, save_simulation
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation


def test_sprint8_scenario_balances_the_default_benchmark() -> None:
    state = build_sprint8_scenario()

    assert state.links["rail_core_yard_gate"].capacity_per_tick == 2
    assert state.disruptions["frontier_outer_gate_alignment"].capacity_multiplier == 0.5
    assert state.disruptions["frontier_outer_gate_alignment"].reason == "gate alignment throttling"


def test_cli_lists_scenarios_and_marks_sprint8_default() -> None:
    output = StringIO()

    result = run_cli(["--list-scenarios"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "sprint20 default:" in text
    assert "aliases: playtest, benchmark, balanced" in text


def test_cli_inspect_prints_selected_setup_sections_without_advancing() -> None:
    output = StringIO()

    result = run_cli(["--inspect", "--report", "schedules,stockpiles"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Scenario Inspection" in text
    assert "Schedule Plan" in text
    assert "Initial Stockpiles" in text
    assert "Tick 0001" not in text


def test_cli_report_filter_limits_tick_and_monthly_sections() -> None:
    output = StringIO()

    result = run_cli(["--ticks", "30", "--report", "traffic,finance", "--no-summary"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Traffic:" in text
    assert "Finance:" in text
    assert "Traffic Pressure" in text
    assert "Produced:" not in text
    assert "Freight:" not in text
    assert "Settlement Stockpiles" not in text
    assert "Schedule Status" not in text


def test_sprint8_monthly_benchmark_has_tuned_traffic_pressure() -> None:
    simulation = TickSimulation.from_scenario("sprint8")

    simulation.run_ticks(30)

    ledger = simulation.monthly_reports[0]
    assert ledger["traffic_pressure"]["rail_core_yard_gate"]["full_ticks"] == 1
    assert ledger["traffic_pressure"]["gate_core_frontier"]["full_ticks"] == 1
    assert ledger["traffic_pressure"]["gate_frontier_outer"]["disrupted_ticks"] == 2
    assert ledger["traffic_pressure"]["gate_frontier_outer"]["peak_pressure"] == 1.0
    assert ledger["finance"]["ending_cash"] == 7816.0


def test_save_load_round_trip_continues_deterministically(tmp_path) -> None:
    save_path = tmp_path / "phase8_save.json"
    simulation = TickSimulation.from_scenario("sprint8")
    baseline = TickSimulation.from_scenario("sprint8")

    simulation.run_ticks(10)
    baseline.run_ticks(10)
    save_simulation(simulation, save_path)

    loaded = load_simulation(save_path)
    loaded_reports = loaded.run_ticks(5)
    baseline_reports = baseline.run_ticks(5)

    assert loaded.state.tick == 15
    assert loaded_reports == baseline_reports
    assert loaded.state.finance.snapshot() == baseline.state.finance.snapshot()


def test_cli_save_and_load_workflow(tmp_path) -> None:
    save_path = tmp_path / "cli_save.json"
    save_output = StringIO()
    load_output = StringIO()

    save_result = run_cli(["--ticks", "3", "--save", str(save_path), "--no-summary"], output=save_output)
    load_result = run_cli(
        ["--load", str(save_path), "--ticks", "2", "--report", "finance", "--no-summary"],
        output=load_output,
    )

    assert save_result == 0
    assert load_result == 0
    assert save_path.exists()
    assert "Saved simulation to" in save_output.getvalue()
    assert "Tick 0004" in load_output.getvalue()
    assert "Tick 0005" in load_output.getvalue()
    assert "Finance:" in load_output.getvalue()


def test_cli_load_only_prints_new_monthly_ledgers(tmp_path) -> None:
    save_path = tmp_path / "month_end_save.json"
    save_output = StringIO()
    load_output = StringIO()

    save_result = run_cli(["--ticks", "30", "--save", str(save_path), "--no-summary"], output=save_output)
    load_result = run_cli(
        ["--load", str(save_path), "--ticks", "1", "--report", "finance", "--no-summary"],
        output=load_output,
    )

    assert save_result == 0
    assert load_result == 0
    assert "Month 01 Operations Ledger" not in load_output.getvalue()
    assert "Tick 0031" in load_output.getvalue()
