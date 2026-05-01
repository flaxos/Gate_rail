"""Sprint 29 tutorial start scenario coverage."""

from __future__ import annotations

from pathlib import Path

from gaterail.cargo import CargoType
from gaterail.commands import DispatchOrder
from gaterail.models import LinkMode
from gaterail.persistence import load_simulation, save_simulation
from gaterail.scenarios import load_scenario, scenario_definitions
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _gate_neighbour_worlds(state, world_id: str) -> set[str]:
    neighbours: set[str] = set()
    for link in state.links.values():
        if link.mode != LinkMode.GATE:
            continue
        origin_world = state.nodes[link.origin].world_id
        destination_world = state.nodes[link.destination].world_id
        if origin_world == world_id:
            neighbours.add(destination_world)
        if destination_world == world_id:
            neighbours.add(origin_world)
    return neighbours


def _run_until(simulation: TickSimulation, predicate, *, max_ticks: int = 80) -> None:
    for _ in range(max_ticks):
        simulation.run_ticks(1)
        if predicate():
            return
    raise AssertionError("condition was not reached before tick limit")


def _run_manual_tutorial_loop(simulation: TickSimulation) -> None:
    state = simulation.state
    state.apply_command(
        DispatchOrder(
            order_id="manual_ore_to_cinder",
            train_id="tutorial_ore_runner",
            origin="brink_mine",
            destination="cinder_smelter",
            cargo_type=CargoType.ORE,
            requested_units=20,
        )
    )
    _run_until(
        simulation,
        lambda: state.nodes["cinder_smelter"].stock(CargoType.METAL) >= 20,
    )

    state.apply_command(
        DispatchOrder(
            order_id="manual_metal_to_atlas",
            train_id="tutorial_metal_runner",
            origin="cinder_smelter",
            destination="atlas_factory",
            cargo_type=CargoType.METAL,
            requested_units=10,
        )
    )
    _run_until(
        simulation,
        lambda: state.nodes["atlas_factory"].stock(CargoType.PARTS) >= 12,
    )

    state.apply_command(
        DispatchOrder(
            order_id="manual_parts_to_helix",
            train_id="tutorial_parts_runner",
            origin="atlas_factory",
            destination="helix_settlement",
            cargo_type=CargoType.PARTS,
            requested_units=12,
        )
    )
    _run_until(
        simulation,
        lambda: state.contracts["helix_parts_tutorial"].status.value == "fulfilled",
    )


def test_tutorial_six_worlds_is_registered_with_ring_gate_topology() -> None:
    keys = {definition.key for definition in scenario_definitions()}
    aliases = {alias for definition in scenario_definitions() for alias in definition.aliases}
    state = load_scenario("tutorial_start")

    assert "tutorial_six_worlds" in keys
    assert {"tutorial_start", "six_world_tutorial", "starter_ring"}.issubset(aliases)
    assert len(state.worlds) == 6
    assert len(state.links_by_mode(LinkMode.GATE)) == 6
    assert state.finance.cash >= 120_000

    for world_id in state.worlds:
        assert len(_gate_neighbour_worlds(state, world_id)) == 2
        depot = state.nodes[f"{world_id}_depot"]
        assert depot.stock(CargoType.CONSTRUCTION_MATERIALS) >= 500
        assert depot.stock(CargoType.PARTS) >= 120
        assert depot.stock(CargoType.ELECTRONICS) >= 80
        assert depot.stock(CargoType.FUEL) >= 100


def test_tutorial_six_worlds_starts_manual_and_does_not_autocomplete_on_play() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    state = simulation.state
    starting_cash = state.finance.cash

    assert all(not schedule.active for schedule in state.schedules.values())

    simulation.run_ticks(30)

    assert state.schedules["tutorial_ore_to_cinder"].delivered_units == 0
    assert state.schedules["tutorial_metal_to_atlas"].delivered_units == 0
    assert state.schedules["tutorial_parts_to_helix"].delivered_units == 0
    assert state.contracts["helix_parts_tutorial"].status.value == "active"
    assert state.finance.cash < starting_cash


def test_tutorial_six_worlds_manual_one_shot_dispatch_loop_pays_off() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    state = simulation.state
    starting_cash = state.finance.cash

    _run_manual_tutorial_loop(simulation)

    assert state.contracts["helix_parts_tutorial"].status.value == "fulfilled"
    assert state.contracts["helix_parts_tutorial"].delivered_units >= 12
    assert state.finance.cash > starting_cash

    assert state.orders["manual_ore_to_cinder"].delivered_units == 20
    assert state.orders["manual_metal_to_atlas"].delivered_units == 10
    assert state.orders["manual_parts_to_helix"].delivered_units == 12


def test_tutorial_six_worlds_snapshot_uses_circular_world_layout() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")
    snapshot = render_snapshot(simulation.state)

    positions = {world["id"]: world["position"] for world in snapshot["worlds"]}

    assert set(positions) == {"atlas", "aurora", "brink", "cinder", "helix", "vesta"}
    assert min(position["x"] for position in positions.values()) < 0
    assert max(position["x"] for position in positions.values()) > 0
    assert min(position["y"] for position in positions.values()) < 0
    assert max(position["y"] for position in positions.values()) > 0
    assert len({position["y"] for position in positions.values()}) > 2


def test_tutorial_six_worlds_save_round_trips(tmp_path) -> None:
    save_path = tmp_path / "tutorial_six_worlds.json"
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")

    save_simulation(simulation, save_path)
    loaded = load_simulation(save_path)

    assert len(loaded.state.worlds) == 6
    assert loaded.state.finance.cash == simulation.state.finance.cash
    assert set(loaded.state.schedules) == set(simulation.state.schedules)


def test_tutorial_snapshot_reports_loop_progress_and_next_action() -> None:
    simulation = TickSimulation.from_scenario("tutorial_six_worlds")

    initial = render_snapshot(simulation.state)["tutorial"]

    assert initial["id"] == "tutorial_six_worlds"
    assert initial["active"] is True
    assert initial["next_action"] == {
        "kind": "manual_dispatch",
        "label": "Set up a manual freight order",
    }
    assert initial["alerts"] == [
        {
            "kind": "tutorial",
            "message": "Tutorial active: move ore from Brink Mines to Cinder Forge.",
        }
    ]
    assert [step["id"] for step in initial["steps"]] == [
        "mine_ore",
        "smelt_metal",
        "deliver_parts",
    ]
    assert [step["status"] for step in initial["steps"]] == [
        "active",
        "pending",
        "pending",
    ]
    assert initial["steps"][0]["delivered"] == 0
    assert initial["steps"][0]["target"] == 20
    assert initial["steps"][0]["cargo"] == "ore"
    assert initial["steps"][0]["origin"] == "brink_mine"
    assert initial["steps"][0]["destination"] == "cinder_smelter"

    _run_manual_tutorial_loop(simulation)
    finished = render_snapshot(simulation.state)["tutorial"]

    assert finished["active"] is False
    assert finished["alerts"] == [
        {
            "kind": "tutorial",
            "message": "Tutorial loop complete: Helix paid for delivered parts.",
        }
    ]
    assert finished["next_action"] is None
    assert [step["status"] for step in finished["steps"]] == [
        "complete",
        "complete",
        "complete",
    ]
    assert finished["steps"][2]["reward_cash"] == 20_000.0
    assert finished["steps"][2]["reward_reputation"] == 4


def test_godot_tutorial_ui_consumes_snapshot_contract_without_rules() -> None:
    main_script = (Path("godot/scripts/main.gd")).read_text()

    assert "_tutorial_list" in main_script
    assert "_tutorial_action_button" in main_script
    assert "_rebuild_tutorial_panel" in main_script
    assert "_dispatch_status_label" in main_script
    assert "_apply_selection_to_dispatch_builder" in main_script
    assert "_preferred_cargo_for_route" in main_script
    assert 'snapshot.get("tutorial"' in main_script
    assert "GateRailBridge.step_ticks" in main_script
    assert "reward_cash" in main_script
    assert "reward_reputation" in main_script
    assert "tutorial_ore_to_cinder" not in main_script
    assert "tutorial_metal_to_atlas" not in main_script
    assert "tutorial_parts_to_helix" not in main_script
