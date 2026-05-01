"""Sprint 27 remote extraction and outpost operation tests."""

from __future__ import annotations

from pathlib import Path

from gaterail.cargo import CargoType
from gaterail.commands import command_from_dict
from gaterail.models import (
    DevelopmentTier,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    ResourceRecipe,
    ResourceRecipeKind,
    SpaceSite,
    WorldState,
)
from gaterail.simulation import TickSimulation
from gaterail.space import mission_fuel_required, mission_power_required


def _remote_state(*, launch_fuel: int = 100, power_available: int = 200) -> GameState:
    state = GameState()
    state.add_world(
        WorldState(
            id="remote",
            name="Remote Test World",
            tier=DevelopmentTier.OUTPOST,
            power_available=power_available,
            power_used=50,
        )
    )
    state.add_node(
        NetworkNode(
            id="orbital_yard",
            name="Orbital Yard",
            world_id="remote",
            kind=NodeKind.ORBITAL_YARD,
            inventory={CargoType.FUEL: launch_fuel},
            storage_capacity=3_000,
        )
    )
    state.add_node(
        NetworkNode(
            id="collection_station",
            name="Collection Station",
            world_id="remote",
            kind=NodeKind.COLLECTION_STATION,
            storage_capacity=1_000,
            transfer_limit_per_tick=32,
        )
    )
    state.add_node(
        NetworkNode(
            id="ore_smelter",
            name="Ore Smelter",
            world_id="remote",
            kind=NodeKind.INDUSTRY,
            storage_capacity=1_000,
            transfer_limit_per_tick=32,
            resource_recipe=ResourceRecipe(
                id="remote_iron_smelting",
                kind=ResourceRecipeKind.SMELTING,
                inputs={"mixed_ore": 6},
                outputs={"iron": 4},
            ),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_collection_smelter",
            origin="collection_station",
            destination="ore_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=12,
        )
    )
    state.add_space_site(
        SpaceSite(
            id="site_alpha",
            name="Alpha Belt",
            resource_id="mixed_ore",
            travel_ticks=5,
            base_yield=80,
        )
    )
    return state


def _mission_command(command_type: str = "PreviewDispatchMiningMission") -> dict[str, object]:
    return {
        "type": command_type,
        "mission_id": "mission_alpha",
        "site_id": "site_alpha",
        "launch_node_id": "orbital_yard",
        "return_node_id": "collection_station",
    }


def test_mining_mission_preview_uses_backend_fuel_and_power_requirements_when_omitted() -> None:
    state = _remote_state()
    site = state.space_sites["site_alpha"]

    preview = state.apply_command(command_from_dict(_mission_command()))

    assert preview["ok"] is True
    assert preview["fuel_required"] == mission_fuel_required(site) == 30
    assert preview["power_required"] == mission_power_required(site) == 15
    assert preview["normalized_command"]["fuel_input"] == 30
    assert preview["normalized_command"]["power_input"] == 15


def test_mining_mission_without_explicit_inputs_still_reports_missing_fuel() -> None:
    state = _remote_state(launch_fuel=20)

    preview = state.apply_command(command_from_dict(_mission_command()))

    assert preview["ok"] is False
    assert preview["reason"] == "insufficient_fuel"
    assert preview["fuel_required"] == 30
    assert preview["fuel_available"] == 20


def test_dispatched_mission_returns_resources_that_feed_local_industry() -> None:
    state = _remote_state()
    dispatch = state.apply_command(command_from_dict(_mission_command("DispatchMiningMission")))

    assert dispatch["ok"] is True
    assert state.nodes["orbital_yard"].stock(CargoType.FUEL) == 70
    assert state.worlds["remote"].power_used == 65

    mission = state.mining_missions["mission_alpha"]
    mission.ticks_remaining = 1
    simulation = TickSimulation(state=state)
    report = simulation.step_tick()

    assert report["space_missions"]["returned_resources"] == {"mixed_ore": 80}
    assert state.nodes["collection_station"].resource_stock("mixed_ore") == 80
    assert state.nodes["ore_smelter"].resource_stock("mixed_ore") == 0
    assert state.worlds["remote"].power_used == 50

    simulation.step_tick()

    assert state.nodes["collection_station"].resource_stock("mixed_ore") == 74
    assert state.nodes["ore_smelter"].resource_stock("mixed_ore") == 0
    assert state.nodes["ore_smelter"].resource_stock("iron") == 4


def test_godot_local_region_previews_mining_missions_before_dispatch() -> None:
    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert '"type": "PreviewDispatchMiningMission"' in script
    assert "_handle_preview_result(result, \"mining_mission\")" in script
    assert '"DispatchMiningMission"' in script
    assert "Fuel" in script
    assert "Power" in script


def _cargo_site_state(*, launch_fuel: int = 100, return_capacity: int = 1_000) -> GameState:
    state = GameState()
    state.add_world(
        WorldState(
            id="remote",
            name="Remote Test World",
            tier=DevelopmentTier.OUTPOST,
            power_available=200,
            power_used=50,
        )
    )
    state.add_node(
        NetworkNode(
            id="orbital_yard",
            name="Orbital Yard",
            world_id="remote",
            kind=NodeKind.ORBITAL_YARD,
            inventory={CargoType.FUEL: launch_fuel},
            storage_capacity=3_000,
        )
    )
    state.add_node(
        NetworkNode(
            id="collection_station",
            name="Collection Station",
            world_id="remote",
            kind=NodeKind.COLLECTION_STATION,
            storage_capacity=return_capacity,
            transfer_limit_per_tick=32,
        )
    )
    state.add_space_site(
        SpaceSite(
            id="site_ore",
            name="Ore Field",
            resource_id="mixed_ore",
            travel_ticks=5,
            base_yield=80,
            cargo_type=CargoType.ORE,
        )
    )
    return state


def test_cargo_typed_site_returns_haul_into_train_cargo_inventory() -> None:
    state = _cargo_site_state()
    dispatch = state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_ore",
                "site_id": "site_ore",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
            }
        )
    )

    assert dispatch["ok"] is True

    state.mining_missions["mission_ore"].ticks_remaining = 1
    report = TickSimulation(state=state).step_tick()

    assert report["space_missions"]["returned_cargo"] == {"ore": 80}
    assert report["space_missions"]["returned_resources"] == {}
    collection = state.nodes["collection_station"]
    assert collection.stock(CargoType.ORE) == 80
    assert collection.resource_stock("mixed_ore") == 0


def test_cargo_typed_site_drops_overflow_when_return_node_is_full() -> None:
    state = _cargo_site_state(return_capacity=50)
    state.apply_command(
        command_from_dict(
            {
                "type": "DispatchMiningMission",
                "mission_id": "mission_overflow",
                "site_id": "site_ore",
                "launch_node_id": "orbital_yard",
                "return_node_id": "collection_station",
            }
        )
    )

    state.mining_missions["mission_overflow"].ticks_remaining = 1
    report = TickSimulation(state=state).step_tick()

    assert report["space_missions"]["returned_cargo"] == {"ore": 50}
    dropped = report["space_missions"]["dropped_units"]
    assert dropped and dropped[0]["dropped_units"] == 30
    assert state.nodes["collection_station"].stock(CargoType.ORE) == 50


def test_cargo_typed_site_round_trips_through_persistence_and_snapshot() -> None:
    from gaterail.persistence import state_from_dict, state_to_dict
    from gaterail.snapshot import render_snapshot

    state = _cargo_site_state()
    snapshot = render_snapshot(state)
    site_payload = next(item for item in snapshot["space_sites"] if item["id"] == "site_ore")
    assert site_payload["cargo_type"] == "ore"

    restored = state_from_dict(state_to_dict(state))
    assert restored.space_sites["site_ore"].cargo_type == CargoType.ORE
