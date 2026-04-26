"""Tests for Sprint 14C per-node recipes and the extractor→industry chain."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.economy import (
    apply_buffer_distribution,
    apply_node_demand,
    apply_node_production,
    apply_node_recipes,
)
from gaterail.models import (
    DevelopmentTier,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    NodeRecipe,
    WorldState,
)
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _world() -> WorldState:
    return WorldState(
        id="frontier",
        name="Brink Frontier",
        tier=DevelopmentTier.OUTPOST,
        population=10_000,
        stability=0.7,
        power_available=200,
        power_used=40,
    )


def _industry_state(
    *,
    inventory: dict[CargoType, int] | None = None,
    recipe: NodeRecipe | None = None,
) -> GameState:
    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_industry",
            name="Frontier Industry",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            inventory=dict(inventory or {}),
            storage_capacity=500,
            transfer_limit_per_tick=24,
            recipe=recipe,
        )
    )
    return state


def test_recipe_consumes_inputs_and_adds_outputs() -> None:
    state = _industry_state(
        inventory={CargoType.ORE: 4},
        recipe=NodeRecipe(
            inputs={CargoType.ORE: 2},
            outputs={CargoType.PARTS: 3},
        ),
    )

    result = apply_node_recipes(state)

    industry = state.nodes["frontier_industry"]
    assert industry.stock(CargoType.ORE) == 2
    assert industry.stock(CargoType.PARTS) == 3
    assert result["consumed"] == {"frontier_industry": {"ore": 2}}
    assert result["produced"] == {"frontier_industry": {"parts": 3}}
    assert result["blocked"] == []
    assert state.recipe_blocked == {}


def test_recipe_blocked_when_inputs_missing() -> None:
    state = _industry_state(
        inventory={CargoType.ORE: 1},
        recipe=NodeRecipe(
            inputs={CargoType.ORE: 2, CargoType.METAL: 1},
            outputs={CargoType.PARTS: 3},
        ),
    )

    result = apply_node_recipes(state)

    industry = state.nodes["frontier_industry"]
    # Nothing was consumed because the full input set was not satisfied.
    assert industry.stock(CargoType.ORE) == 1
    assert industry.stock(CargoType.PARTS) == 0
    assert result["consumed"] == {}
    assert result["produced"] == {}
    assert len(result["blocked"]) == 1
    blocked_entry = result["blocked"][0]
    assert blocked_entry["node"] == "frontier_industry"
    assert blocked_entry["missing"] == {"ore": 1, "metal": 1}
    assert state.recipe_blocked == {
        "frontier_industry": {CargoType.ORE: 1, CargoType.METAL: 1}
    }


def test_nodes_without_recipe_are_skipped() -> None:
    state = _industry_state(
        inventory={CargoType.ORE: 4},
        recipe=None,
    )

    result = apply_node_recipes(state)

    industry = state.nodes["frontier_industry"]
    assert industry.stock(CargoType.ORE) == 4
    assert result == {"consumed": {}, "produced": {}, "blocked": []}


def test_buffer_distribution_satisfies_recipe_inputs() -> None:
    """A depot with ore pushes into a connected industry that needs ore as a recipe input."""

    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Frontier Depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={CargoType.ORE: 50},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_industry",
            name="Frontier Industry",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=500,
            transfer_limit_per_tick=24,
            recipe=NodeRecipe(
                inputs={CargoType.ORE: 4},
                outputs={CargoType.PARTS: 2},
            ),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_depot_industry",
            origin="frontier_depot",
            destination="frontier_industry",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )

    distribution = apply_buffer_distribution(state)

    # Depot pushes exactly 4 (the recipe input deficit), not the full transfer budget.
    assert distribution == {
        "frontier_depot": {"frontier_industry": {CargoType.ORE: 4}}
    }
    assert state.nodes["frontier_industry"].stock(CargoType.ORE) == 4
    assert state.nodes["frontier_depot"].stock(CargoType.ORE) == 46


def test_extractor_to_industry_chain_runs_each_tick() -> None:
    """An extractor produces ore, a depot buffers it, an industry recipe consumes it."""

    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_mine",
            name="Frontier Mine",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            production={CargoType.ORE: 6},
            storage_capacity=200,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Frontier Depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={CargoType.ORE: 30},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_industry",
            name="Frontier Industry",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=500,
            transfer_limit_per_tick=24,
            recipe=NodeRecipe(
                inputs={CargoType.ORE: 4},
                outputs={CargoType.PARTS: 2},
            ),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_depot_industry",
            origin="frontier_depot",
            destination="frontier_industry",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )

    simulation = TickSimulation(state=state)
    simulation.run_ticks(3)

    industry = state.nodes["frontier_industry"]
    # Three full recipe runs: 3 * 2 = 6 parts produced.
    assert industry.stock(CargoType.PARTS) == 6
    # Industry consumed 12 ore over three ticks; depot started with 30, lost 12.
    assert state.nodes["frontier_depot"].stock(CargoType.ORE) == 18


def test_recipe_does_not_consume_or_produce_when_storage_full() -> None:
    """If outputs would overflow capacity, recipe still consumes inputs but accept-clamps outputs."""

    state = _industry_state(
        inventory={CargoType.ORE: 2, CargoType.PARTS: 498},
        recipe=NodeRecipe(
            inputs={CargoType.ORE: 2},
            outputs={CargoType.PARTS: 3},
        ),
    )
    industry = state.nodes["frontier_industry"]
    industry.storage_capacity = 500

    result = apply_node_recipes(state)

    # 498 PARTS + 2 ORE = 500 already at cap. Inputs consume 2 ORE, freeing space.
    # After consume: 0 ORE + 498 PARTS = 498. Then add 3 PARTS → only 2 fit.
    assert industry.stock(CargoType.ORE) == 0
    assert industry.stock(CargoType.PARTS) == 500
    assert result["consumed"] == {"frontier_industry": {"ore": 2}}
    assert result["produced"] == {"frontier_industry": {"parts": 2}}


def test_snapshot_exposes_recipe_and_blocked() -> None:
    state = _industry_state(
        inventory={CargoType.ORE: 0},
        recipe=NodeRecipe(
            inputs={CargoType.ORE: 2},
            outputs={CargoType.PARTS: 3},
        ),
    )
    apply_node_recipes(state)

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    industry = by_id["frontier_industry"]

    assert industry["recipe"] == {"inputs": {"ore": 2}, "outputs": {"parts": 3}}
    assert industry["recipe_blocked"] == {"ore": 2}


def test_snapshot_recipe_null_for_nodes_without_recipe() -> None:
    state = _industry_state(inventory={CargoType.ORE: 4}, recipe=None)
    apply_node_recipes(state)

    snapshot = render_snapshot(state)
    by_id = {node["id"]: node for node in snapshot["nodes"]}
    industry = by_id["frontier_industry"]

    assert industry["recipe"] is None
    assert industry["recipe_blocked"] == {}


def test_recipes_phase_runs_in_full_simulation_report() -> None:
    state = _industry_state(
        inventory={CargoType.ORE: 10},
        recipe=NodeRecipe(
            inputs={CargoType.ORE: 2},
            outputs={CargoType.PARTS: 3},
        ),
    )
    simulation = TickSimulation(state=state)
    report = simulation.step_tick()

    assert "node_recipes" in report["phase_order"]
    assert report["recipes"]["produced"] == {"frontier_industry": {"parts": 3}}
    assert report["recipes"]["consumed"] == {"frontier_industry": {"ore": 2}}
    # Idle scenario: node_production and apply_node_demand should not regress.
    assert report["produced"] == {}


def test_recipe_does_not_steal_from_declared_demand_in_buffer_pull() -> None:
    """When a node has both declared demand and recipe inputs, both are summed for the buffer pull."""

    state = GameState()
    state.add_world(_world())
    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Frontier Depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={CargoType.ORE: 50},
            storage_capacity=2_000,
            transfer_limit_per_tick=24,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_industry",
            name="Frontier Industry",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            demand={CargoType.ORE: 2},
            storage_capacity=500,
            transfer_limit_per_tick=24,
            recipe=NodeRecipe(
                inputs={CargoType.ORE: 3},
                outputs={CargoType.PARTS: 1},
            ),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_depot_industry",
            origin="frontier_depot",
            destination="frontier_industry",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )

    apply_buffer_distribution(state)

    # Effective pull = demand 2 + recipe input 3 = 5 ore.
    assert state.nodes["frontier_industry"].stock(CargoType.ORE) == 5
    assert state.nodes["frontier_depot"].stock(CargoType.ORE) == 45
