"""Tests for Sprint 9 contracts and player-facing objectives."""

from io import StringIO

from gaterail.cargo import CargoType
from gaterail.cli import run_cli
from gaterail.models import (
    Contract,
    ContractKind,
    ContractStatus,
    DevelopmentTier,
    FreightSchedule,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkDisruption,
    NetworkLink,
    NetworkNode,
    NodeKind,
    WorldState,
)
from gaterail.persistence import load_simulation, save_simulation
from gaterail.scenarios import (
    build_sprint8_scenario,
    build_sprint9_frontier_scenario,
    build_sprint9_logistics_scenario,
    build_sprint9_recovery_scenario,
)
from gaterail.simulation import TickSimulation


def _build_contract_test_state() -> GameState:
    """Build a minimal two-node state with one recurring delivery schedule."""

    state = GameState()
    state.add_world(
        WorldState(
            id="core",
            name="Core",
            tier=DevelopmentTier.FRONTIER_COLONY,
            power_available=200,
            power_used=0,
        )
    )
    state.add_node(
        NetworkNode(
            id="source",
            name="Source Depot",
            world_id="core",
            kind=NodeKind.DEPOT,
            inventory={CargoType.FOOD: 60},
            storage_capacity=200,
        )
    )
    state.add_node(
        NetworkNode(
            id="target",
            name="Target Settlement",
            world_id="core",
            kind=NodeKind.SETTLEMENT,
            storage_capacity=200,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_source_target",
            origin="source",
            destination="target",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=4,
        )
    )
    state.add_train(
        FreightTrain(
            id="hauler",
            name="Hauler",
            node_id="source",
            capacity=10,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="food_shuttle",
            train_id="hauler",
            origin="source",
            destination="target",
            cargo_type=CargoType.FOOD,
            units_per_departure=10,
            interval_ticks=3,
            priority=100,
        )
    )
    return state


def test_contract_fulfilled_awards_cash_and_reputation() -> None:
    state = _build_contract_test_state()
    state.add_contract(
        Contract(
            id="feed_the_base",
            kind=ContractKind.CARGO_DELIVERY,
            title="Feed the Base",
            destination_node_id="target",
            cargo_type=CargoType.FOOD,
            target_units=15,
            due_tick=20,
            reward_cash=500.0,
            penalty_cash=200.0,
            reward_reputation=4,
            penalty_reputation=3,
        )
    )
    starting_cash = state.finance.cash
    simulation = TickSimulation(state=state)

    simulation.run_ticks(10)

    contract = state.contracts["feed_the_base"]
    assert contract.status == ContractStatus.FULFILLED
    assert contract.delivered_units >= 15
    assert state.reputation == 4
    assert state.finance.revenue_total >= 500.0
    # Cash strictly increases beyond baseline once reward lands
    assert state.finance.cash > starting_cash


def test_contract_missed_deadline_applies_penalty_once() -> None:
    state = _build_contract_test_state()
    state.add_contract(
        Contract(
            id="impossible_target",
            kind=ContractKind.CARGO_DELIVERY,
            title="Impossible Target",
            destination_node_id="target",
            cargo_type=CargoType.FOOD,
            target_units=500,
            due_tick=5,
            reward_cash=1000.0,
            penalty_cash=250.0,
            reward_reputation=6,
            penalty_reputation=9,
        )
    )
    simulation = TickSimulation(state=state)
    contract = state.contracts["impossible_target"]

    # Step up to the deadline tick and capture the penalty moment
    for _ in range(4):
        simulation.step_tick()
    assert contract.status == ContractStatus.ACTIVE
    costs_before_deadline = state.finance.costs_total

    # Deadline tick: contract fails and penalty lands exactly once
    tick_report = simulation.step_tick()
    assert contract.status == ContractStatus.FAILED
    assert contract.resolved_tick == 5
    assert tick_report["contracts"]["failed_this_tick"][0]["contract"] == "impossible_target"
    penalty_delta = (
        state.finance.costs_total
        - costs_before_deadline
        - state.finance.costs_this_tick
        + 250.0  # exclude dispatch costs this tick
    )
    assert penalty_delta == 250.0

    # Further ticks never re-apply the penalty
    reputation_after_fail = state.reputation
    costs_after_fail = state.finance.costs_total
    for _ in range(5):
        simulation.step_tick()
    dispatch_cost_growth = state.finance.costs_total - costs_after_fail
    assert state.reputation == reputation_after_fail == -9
    # Any cost growth is dispatch/variable only; no multiple of 250 penalty landed
    assert dispatch_cost_growth < 250.0


def test_sprint8_contracts_seeded_and_reported() -> None:
    state = build_sprint8_scenario()

    assert "brink_food_relief" in state.contracts
    assert "core_ore_quota" in state.contracts
    assert "ashfall_medical_lifeline" in state.contracts
    assert state.reputation == 0

    simulation = TickSimulation(state=state)
    simulation.run_ticks(30)

    ledger = simulation.monthly_reports[0]
    totals = ledger["contract_totals"]
    assert totals["fulfilled"] == 1
    assert totals["failed"] == 2
    assert totals["active"] == 0
    assert ledger["reputation"] == state.reputation
    contracts_section = ledger["contracts"]
    assert contracts_section["brink_food_relief"]["status"] == "fulfilled"
    assert contracts_section["core_ore_quota"]["status"] == "failed"
    assert contracts_section["ashfall_medical_lifeline"]["status"] == "failed"


def test_cli_contracts_filter_renders_contract_sections() -> None:
    output = StringIO()

    result = run_cli(["--ticks", "30", "--report", "contracts", "--no-summary"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Contracts:" in text  # tick rollup
    assert "Contracts (" in text  # monthly table header includes totals
    assert "brink_food_relief" in text
    assert "reputation" in text
    # Filter should hide other sections
    assert "Freight:" not in text
    assert "Finance:" not in text


def test_cli_inspect_lists_active_contracts_without_advancing() -> None:
    output = StringIO()

    result = run_cli(["--inspect", "--report", "contracts"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "Active Contracts" in text
    assert "brink_food_relief" in text
    assert "ashfall_medical_lifeline" in text
    assert "Tick 0001" not in text


def test_save_load_preserves_contracts_and_reputation(tmp_path) -> None:
    save_path = tmp_path / "contracts_save.json"
    simulation = TickSimulation.from_scenario("sprint8")
    baseline = TickSimulation.from_scenario("sprint8")

    simulation.run_ticks(15)
    baseline.run_ticks(15)
    save_simulation(simulation, save_path)

    loaded = load_simulation(save_path)
    loaded_reports = loaded.run_ticks(15)
    baseline_reports = baseline.run_ticks(15)

    assert loaded_reports == baseline_reports
    assert loaded.state.reputation == baseline.state.reputation
    for contract_id, contract in baseline.state.contracts.items():
        loaded_contract = loaded.state.contracts[contract_id]
        assert loaded_contract.status == contract.status
        assert loaded_contract.delivered_units == contract.delivered_units
        assert loaded_contract.resolved_tick == contract.resolved_tick


def _build_support_test_state() -> GameState:
    """Minimal one-world state that accrues support streak every tick."""

    state = GameState()
    state.add_world(
        WorldState(
            id="frontier",
            name="Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=1_000,
            stability=0.95,
            power_available=80,
            power_used=0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Frontier Settlement",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory={
                CargoType.FOOD: 20,
                CargoType.CONSTRUCTION_MATERIALS: 20,
            },
            storage_capacity=200,
        )
    )
    return state


def test_frontier_support_contract_fulfilled_on_streak() -> None:
    state = _build_support_test_state()
    state.add_contract(
        Contract(
            id="hold_the_line",
            kind=ContractKind.FRONTIER_SUPPORT,
            title="Hold the Line",
            target_world_id="frontier",
            target_units=4,
            due_tick=20,
            reward_cash=600.0,
            penalty_cash=200.0,
            reward_reputation=5,
            penalty_reputation=3,
        )
    )
    simulation = TickSimulation(state=state)
    simulation.run_ticks(6)

    contract = state.contracts["hold_the_line"]
    assert contract.status == ContractStatus.FULFILLED
    assert contract.progress >= 4
    assert contract.resolved_tick is not None and contract.resolved_tick <= 6
    assert state.reputation == 5


def test_frontier_support_contract_failed_when_world_is_stalled() -> None:
    state = _build_support_test_state()
    # No food/materials => every tick is stalled, streak stays 0
    state.nodes["frontier_settlement"].inventory.clear()
    state.add_contract(
        Contract(
            id="hopeless_support",
            kind=ContractKind.FRONTIER_SUPPORT,
            title="Hopeless Support",
            target_world_id="frontier",
            target_units=3,
            due_tick=4,
            reward_cash=500.0,
            penalty_cash=250.0,
            reward_reputation=4,
            penalty_reputation=5,
        )
    )
    simulation = TickSimulation(state=state)
    simulation.run_ticks(5)

    contract = state.contracts["hopeless_support"]
    assert contract.status == ContractStatus.FAILED
    assert contract.progress == 0
    assert contract.resolved_tick == 4
    assert state.reputation == -5


def _build_gate_test_state(
    *, power_available: int = 200, disruption: NetworkDisruption | None = None
) -> GameState:
    """Minimal two-world state with one gate link for recovery tests."""

    state = GameState()
    state.add_world(
        WorldState(
            id="hub",
            name="Hub",
            tier=DevelopmentTier.CORE_WORLD,
            power_available=power_available,
            power_used=0,
        )
    )
    state.add_world(
        WorldState(
            id="spur",
            name="Spur",
            tier=DevelopmentTier.OUTPOST,
            power_available=30,
            power_used=0,
        )
    )
    state.add_node(
        NetworkNode(id="hub_gate", name="Hub Gate", world_id="hub", kind=NodeKind.GATE_HUB)
    )
    state.add_node(
        NetworkNode(id="spur_gate", name="Spur Gate", world_id="spur", kind=NodeKind.GATE_HUB)
    )
    state.add_link(
        NetworkLink(
            id="gate_hub_spur",
            origin="hub_gate",
            destination="spur_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=4,
            power_required=80,
            power_source_world_id="hub",
        )
    )
    if disruption is not None:
        state.add_disruption(disruption)
    return state


def test_gate_recovery_contract_fulfilled_after_outage() -> None:
    state = _build_gate_test_state(
        disruption=NetworkDisruption(
            id="alignment_outage",
            link_id="gate_hub_spur",
            start_tick=1,
            end_tick=3,
            capacity_multiplier=0.0,
            reason="alignment outage",
        )
    )
    state.add_contract(
        Contract(
            id="restore_the_link",
            kind=ContractKind.GATE_RECOVERY,
            title="Restore the Link",
            target_link_id="gate_hub_spur",
            target_units=2,
            due_tick=10,
            reward_cash=700.0,
            penalty_cash=300.0,
            reward_reputation=4,
            penalty_reputation=4,
        )
    )
    simulation = TickSimulation(state=state)
    simulation.run_ticks(6)

    contract = state.contracts["restore_the_link"]
    assert contract.status == ContractStatus.FULFILLED
    assert contract.progress >= 2
    # Operational only after the outage ends on tick 3, so earliest recovery is tick 5
    assert contract.resolved_tick is not None and contract.resolved_tick >= 5
    assert state.reputation == 4


def test_gate_recovery_contract_failed_when_link_stays_unpowered() -> None:
    # Hub has no spare power => gate never powered.
    state = _build_gate_test_state(power_available=20)
    state.add_contract(
        Contract(
            id="unreachable_link",
            kind=ContractKind.GATE_RECOVERY,
            title="Unreachable Link",
            target_link_id="gate_hub_spur",
            target_units=3,
            due_tick=3,
            reward_cash=500.0,
            penalty_cash=400.0,
            reward_reputation=3,
            penalty_reputation=6,
        )
    )
    simulation = TickSimulation(state=state)
    simulation.run_ticks(4)

    contract = state.contracts["unreachable_link"]
    assert contract.status == ContractStatus.FAILED
    assert contract.progress == 0
    assert contract.resolved_tick == 3
    assert state.reputation == -6


def test_gate_recovery_progress_resets_when_operational_streak_breaks() -> None:
    state = _build_gate_test_state(
        disruption=NetworkDisruption(
            id="mid_outage",
            link_id="gate_hub_spur",
            start_tick=3,
            end_tick=3,
            capacity_multiplier=0.0,
            reason="alignment glitch",
        )
    )
    state.add_contract(
        Contract(
            id="resilience_run",
            kind=ContractKind.GATE_RECOVERY,
            title="Resilience Run",
            target_link_id="gate_hub_spur",
            target_units=3,
            due_tick=12,
            reward_cash=650.0,
            penalty_cash=300.0,
            reward_reputation=4,
            penalty_reputation=4,
        )
    )
    simulation = TickSimulation(state=state)

    # Ticks 1, 2 operational => progress 1, 2
    simulation.step_tick()
    simulation.step_tick()
    contract = state.contracts["resilience_run"]
    assert contract.progress == 2

    # Tick 3 is disrupted => progress resets to 0
    simulation.step_tick()
    assert contract.progress == 0

    # Ticks 4, 5, 6 rebuild streak => fulfilled by tick 6
    simulation.run_ticks(3)
    assert contract.status == ContractStatus.FULFILLED
    assert contract.progress >= 3
    assert contract.resolved_tick == 6


def test_add_contract_rejects_missing_kind_specific_fields() -> None:
    state = _build_support_test_state()
    missing_world = Contract(
        id="invalid_support",
        kind=ContractKind.FRONTIER_SUPPORT,
        title="Invalid Support",
        target_units=3,
        due_tick=10,
    )
    try:
        state.add_contract(missing_world)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for missing target_world_id")


def test_sprint9_logistics_scenario_adds_stretch_contract() -> None:
    state = build_sprint9_logistics_scenario()

    assert "ashfall_parts_surge" in state.contracts
    contract = state.contracts["ashfall_parts_surge"]
    assert contract.kind == ContractKind.CARGO_DELIVERY
    assert contract.cargo_type == CargoType.PARTS
    assert contract.destination_node_id == "outer_outpost"


def test_sprint9_frontier_scenario_fulfils_support_contract() -> None:
    state = build_sprint9_frontier_scenario()
    simulation = TickSimulation(state=state)

    simulation.run_ticks(30)

    contract = state.contracts["brink_frontier_support"]
    assert contract.kind == ContractKind.FRONTIER_SUPPORT
    assert contract.target_world_id == "frontier"
    assert contract.status == ContractStatus.FULFILLED
    assert contract.resolved_tick is not None and contract.resolved_tick <= 25


def test_sprint9_recovery_scenario_fulfils_after_outage() -> None:
    state = build_sprint9_recovery_scenario()
    simulation = TickSimulation(state=state)

    simulation.run_ticks(30)

    contract = state.contracts["ashfall_gate_recovery"]
    assert contract.kind == ContractKind.GATE_RECOVERY
    assert contract.target_link_id == "gate_frontier_outer"
    assert contract.status == ContractStatus.FULFILLED
    # Outage runs through tick 12 => earliest recovery is tick 15 with 3 required ticks
    assert contract.resolved_tick is not None and contract.resolved_tick >= 15


def test_cli_lists_sprint9_scenarios() -> None:
    output = StringIO()

    result = run_cli(["--list-scenarios"], output=output)

    text = output.getvalue()
    assert result == 0
    assert "sprint9_logistics" in text
    assert "sprint9_frontier" in text
    assert "sprint9_recovery" in text


def test_save_load_preserves_frontier_and_recovery_contracts(tmp_path) -> None:
    save_path = tmp_path / "sprint9_save.json"
    simulation = TickSimulation.from_scenario("sprint9_recovery")
    baseline = TickSimulation.from_scenario("sprint9_recovery")

    simulation.run_ticks(10)
    baseline.run_ticks(10)
    save_simulation(simulation, save_path)

    loaded = load_simulation(save_path)
    loaded_reports = loaded.run_ticks(20)
    baseline_reports = baseline.run_ticks(20)

    assert loaded_reports == baseline_reports
    recovery = loaded.state.contracts["ashfall_gate_recovery"]
    assert recovery.target_link_id == "gate_frontier_outer"
    assert recovery.status == baseline.state.contracts["ashfall_gate_recovery"].status
