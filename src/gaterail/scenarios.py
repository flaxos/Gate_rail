"""Scenario construction for CLI-playable prototypes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from gaterail.cargo import CargoType
from gaterail.models import (
    Contract,
    ContractKind,
    DevelopmentTier,
    FreightOrder,
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


DEFAULT_SCENARIO = "sprint8"


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """Metadata for a built-in scenario."""

    key: str
    aliases: tuple[str, ...]
    title: str
    description: str
    builder: Callable[[], GameState]


def build_sprint1_scenario() -> GameState:
    """Build the deterministic Sprint 1 foundation scenario."""

    state = GameState()
    state.add_world(
        WorldState(
            id="core",
            name="Vesta Core",
            tier=DevelopmentTier.CORE_WORLD,
            population=8_500_000,
            stability=0.96,
            power_available=600,
            power_used=220,
            specialization="manufacturing",
        )
    )
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=12_000,
            stability=0.62,
            power_available=110,
            power_used=60,
            specialization="mining",
        )
    )

    state.add_node(
        NetworkNode(
            id="core_yard",
            name="Core Classification Yard",
            world_id="core",
            kind=NodeKind.DEPOT,
            inventory={
                CargoType.FOOD: 80,
                CargoType.MACHINERY: 40,
                CargoType.CONSTRUCTION_MATERIALS: 30,
            },
            production={CargoType.FOOD: 5, CargoType.MACHINERY: 1},
            storage_capacity=500,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Core Gate Hub",
            world_id="core",
            kind=NodeKind.GATE_HUB,
            storage_capacity=300,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Frontier Gate Hub",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=240,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Brink Landing",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory={CargoType.FOOD: 6, CargoType.CONSTRUCTION_MATERIALS: 3},
            demand={CargoType.FOOD: 2, CargoType.CONSTRUCTION_MATERIALS: 1},
            storage_capacity=160,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_mine",
            name="North Ridge Mine",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            inventory={CargoType.ORE: 10},
            production={CargoType.ORE: 4},
            storage_capacity=180,
        )
    )

    state.add_link(
        NetworkLink(
            id="rail_core_yard_gate",
            origin="core_yard",
            destination="core_gate",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=24,
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_core_frontier",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=40,
            power_required=80,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_gate_settlement",
            origin="frontier_gate",
            destination="frontier_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=14,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_mine_settlement",
            origin="frontier_mine",
            destination="frontier_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=4,
            capacity_per_tick=18,
        )
    )
    return state


def build_sprint2_scenario() -> GameState:
    """Build the first playable fixed-tick freight scenario."""

    state = build_sprint1_scenario()
    state.add_train(
        FreightTrain(
            id="atlas",
            name="Atlas",
            node_id="core_yard",
            capacity=20,
        )
    )
    state.add_train(
        FreightTrain(
            id="civitas",
            name="Civitas",
            node_id="core_yard",
            capacity=12,
        )
    )
    state.add_train(
        FreightTrain(
            id="prospector",
            name="Prospector",
            node_id="frontier_mine",
            capacity=16,
        )
    )
    state.add_order(
        FreightOrder(
            id="food_to_brink",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            requested_units=20,
            priority=100,
        )
    )
    state.add_order(
        FreightOrder(
            id="materials_to_brink",
            train_id="civitas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.CONSTRUCTION_MATERIALS,
            requested_units=12,
            priority=95,
        )
    )
    state.add_order(
        FreightOrder(
            id="ore_to_core",
            train_id="prospector",
            origin="frontier_mine",
            destination="core_yard",
            cargo_type=CargoType.ORE,
            requested_units=14,
            priority=70,
        )
    )
    return state


def build_sprint3_scenario() -> GameState:
    """Build the frontier progression scenario."""

    return build_sprint2_scenario()


def build_sprint4_scenario() -> GameState:
    """Build a gate-pressure expansion scenario."""

    state = build_sprint3_scenario()
    state.add_world(
        WorldState(
            id="outer",
            name="Ashfall Spur",
            tier=DevelopmentTier.OUTPOST,
            population=1_800,
            stability=0.52,
            power_available=35,
            power_used=25,
            specialization="survey_outpost",
        )
    )
    state.add_node(
        NetworkNode(
            id="outer_gate",
            name="Ashfall Gate Skid",
            world_id="outer",
            kind=NodeKind.GATE_HUB,
            storage_capacity=120,
        )
    )
    state.add_node(
        NetworkNode(
            id="outer_outpost",
            name="Ashfall Survey Camp",
            world_id="outer",
            kind=NodeKind.SETTLEMENT,
            demand={CargoType.FOOD: 1, CargoType.MEDICAL_SUPPLIES: 1},
            storage_capacity=80,
        )
    )
    state.nodes["frontier_settlement"].add_inventory(CargoType.MEDICAL_SUPPLIES, 8)
    state.add_link(
        NetworkLink(
            id="gate_frontier_outer",
            origin="frontier_gate",
            destination="outer_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=16,
            power_required=90,
            power_source_world_id="frontier",
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_outer_gate_outpost",
            origin="outer_gate",
            destination="outer_outpost",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
        )
    )
    state.add_train(
        FreightTrain(
            id="mercy",
            name="Mercy",
            node_id="frontier_settlement",
            capacity=8,
        )
    )
    state.add_order(
        FreightOrder(
            id="meds_to_ashfall",
            train_id="mercy",
            origin="frontier_settlement",
            destination="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            requested_units=4,
            priority=98,
        )
    )
    return state


def build_sprint5_scenario() -> GameState:
    """Build the Stage 1 operations ledger scenario."""

    state = build_sprint4_scenario()
    state.orders.clear()
    state.month_length = 30
    state.worlds["frontier"].power_available = 160
    state.links["gate_core_frontier"] = replace(state.links["gate_core_frontier"], capacity_per_tick=1)
    state.links["gate_frontier_outer"] = replace(state.links["gate_frontier_outer"], capacity_per_tick=1)
    state.add_schedule(
        FreightSchedule(
            id="core_food_service",
            train_id="atlas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.FOOD,
            units_per_departure=16,
            interval_ticks=8,
            priority=100,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="core_material_service",
            train_id="civitas",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.CONSTRUCTION_MATERIALS,
            units_per_departure=10,
            interval_ticks=10,
            priority=95,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="frontier_ore_service",
            train_id="prospector",
            origin="frontier_mine",
            destination="core_yard",
            cargo_type=CargoType.ORE,
            units_per_departure=12,
            interval_ticks=12,
            priority=80,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="ashfall_medical_service",
            train_id="mercy",
            origin="frontier_settlement",
            destination="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            units_per_departure=2,
            interval_ticks=7,
            priority=90,
        )
    )
    return state


def build_sprint6_scenario() -> GameState:
    """Build the economic identity scenario."""

    state = build_sprint5_scenario()
    state.economic_identity_enabled = True
    state.nodes["frontier_mine"].add_inventory(CargoType.MACHINERY, 3)
    state.links["gate_core_frontier"] = replace(state.links["gate_core_frontier"], capacity_per_tick=2)
    state.links["gate_frontier_outer"] = replace(state.links["gate_frontier_outer"], capacity_per_tick=2)
    state.schedules["ashfall_medical_service"].units_per_departure = 4
    state.add_train(
        FreightTrain(
            id="pioneer",
            name="Pioneer",
            node_id="core_yard",
            capacity=8,
        )
    )
    state.add_train(
        FreightTrain(
            id="curie",
            name="Curie",
            node_id="outer_outpost",
            capacity=4,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="core_parts_to_ashfall",
            train_id="pioneer",
            origin="core_yard",
            destination="outer_outpost",
            cargo_type=CargoType.PARTS,
            units_per_departure=4,
            interval_ticks=9,
            priority=88,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="ashfall_research_to_core",
            train_id="curie",
            origin="outer_outpost",
            destination="core_yard",
            cargo_type=CargoType.RESEARCH_EQUIPMENT,
            units_per_departure=1,
            interval_ticks=10,
            priority=75,
        )
    )
    return state


def build_sprint7_scenario() -> GameState:
    """Build the traffic pressure and recoverable failure scenario."""

    state = build_sprint6_scenario()
    state.links["rail_core_yard_gate"] = replace(state.links["rail_core_yard_gate"], capacity_per_tick=1)
    state.add_disruption(
        NetworkDisruption(
            id="frontier_outer_gate_alignment",
            link_id="gate_frontier_outer",
            start_tick=13,
            end_tick=14,
            capacity_multiplier=0.0,
            reason="gate alignment maintenance",
        )
    )
    return state


def build_sprint8_scenario() -> GameState:
    """Build the balanced playtest scenario for repeatable CLI iteration."""

    state = build_sprint7_scenario()
    state.links["rail_core_yard_gate"] = replace(state.links["rail_core_yard_gate"], capacity_per_tick=2)
    state.disruptions["frontier_outer_gate_alignment"] = NetworkDisruption(
        id="frontier_outer_gate_alignment",
        link_id="gate_frontier_outer",
        start_tick=13,
        end_tick=14,
        capacity_multiplier=0.5,
        reason="gate alignment throttling",
    )
    state.add_contract(
        Contract(
            id="brink_food_relief",
            kind=ContractKind.CARGO_DELIVERY,
            title="Brink Food Relief",
            client="Brink Frontier",
            destination_node_id="frontier_settlement",
            cargo_type=CargoType.FOOD,
            target_units=30,
            due_tick=30,
            reward_cash=900.0,
            penalty_cash=400.0,
            reward_reputation=5,
            penalty_reputation=6,
        )
    )
    state.add_contract(
        Contract(
            id="core_ore_quota",
            kind=ContractKind.CARGO_DELIVERY,
            title="Core Ore Quota",
            client="Vesta Core",
            destination_node_id="core_yard",
            cargo_type=CargoType.ORE,
            target_units=20,
            due_tick=30,
            reward_cash=700.0,
            penalty_cash=350.0,
            reward_reputation=4,
            penalty_reputation=5,
        )
    )
    state.add_contract(
        Contract(
            id="ashfall_medical_lifeline",
            kind=ContractKind.CARGO_DELIVERY,
            title="Ashfall Medical Lifeline",
            client="Ashfall Spur",
            destination_node_id="outer_outpost",
            cargo_type=CargoType.MEDICAL_SUPPLIES,
            target_units=10,
            due_tick=30,
            reward_cash=1200.0,
            penalty_cash=600.0,
            reward_reputation=8,
            penalty_reputation=10,
        )
    )
    return state


def build_sprint9_logistics_scenario() -> GameState:
    """Sprint 9 slice 4 logistics preset: sprint8 plus one stretched cargo contract."""

    state = build_sprint8_scenario()
    state.add_contract(
        Contract(
            id="ashfall_parts_surge",
            kind=ContractKind.CARGO_DELIVERY,
            title="Ashfall Parts Surge",
            client="Ashfall Spur",
            destination_node_id="outer_outpost",
            cargo_type=CargoType.PARTS,
            target_units=10,
            due_tick=28,
            reward_cash=800.0,
            penalty_cash=350.0,
            reward_reputation=4,
            penalty_reputation=5,
        )
    )
    return state


def build_sprint9_frontier_scenario() -> GameState:
    """Sprint 9 slice 4 frontier preset: sprint8 plus a FRONTIER_SUPPORT objective."""

    state = build_sprint8_scenario()
    state.add_contract(
        Contract(
            id="brink_frontier_support",
            kind=ContractKind.FRONTIER_SUPPORT,
            title="Brink Frontier Support Streak",
            client="Colonial Authority",
            target_world_id="frontier",
            target_units=4,
            due_tick=25,
            reward_cash=1100.0,
            penalty_cash=500.0,
            reward_reputation=7,
            penalty_reputation=7,
        )
    )
    return state


def build_sprint9_recovery_scenario() -> GameState:
    """Sprint 9 slice 4 recovery preset: up-front gate outage plus a GATE_RECOVERY objective."""

    state = build_sprint8_scenario()
    state.disruptions["frontier_outer_gate_alignment"] = NetworkDisruption(
        id="frontier_outer_gate_alignment",
        link_id="gate_frontier_outer",
        start_tick=1,
        end_tick=12,
        capacity_multiplier=0.0,
        reason="gate alignment outage",
    )
    state.add_contract(
        Contract(
            id="ashfall_gate_recovery",
            kind=ContractKind.GATE_RECOVERY,
            title="Ashfall Gate Recovery",
            client="Ashfall Spur",
            target_link_id="gate_frontier_outer",
            target_units=3,
            due_tick=25,
            reward_cash=1000.0,
            penalty_cash=450.0,
            reward_reputation=6,
            penalty_reputation=8,
        )
    )
    return state


def scenario_definitions() -> tuple[ScenarioDefinition, ...]:
    """Return all built-in scenarios in roadmap order."""

    return (
        ScenarioDefinition(
            key="sprint1",
            aliases=("foundation",),
            title="Simulation Foundation",
            description="Two-world logistics graph with production, demand, rail, and one gate.",
            builder=build_sprint1_scenario,
        ),
        ScenarioDefinition(
            key="sprint2",
            aliases=("freight",),
            title="First Freight Prototype",
            description="Assigned trains load, route, travel, unload, and relieve shortages.",
            builder=build_sprint2_scenario,
        ),
        ScenarioDefinition(
            key="sprint3",
            aliases=("frontier", "progression"),
            title="Frontier Progression",
            description="World stability, support streaks, bottlenecks, promotion, and regression.",
            builder=build_sprint3_scenario,
        ),
        ScenarioDefinition(
            key="sprint4",
            aliases=("gate", "expansion"),
            title="Gate Pressure and Expansion",
            description="An outer world depends on a frontier-powered wormhole link.",
            builder=build_sprint4_scenario,
        ),
        ScenarioDefinition(
            key="sprint5",
            aliases=("stage1", "operations"),
            title="Stage 1 Operations Ledger",
            description="Recurring schedules, gate slots, finance, stockpiles, and monthly tables.",
            builder=build_sprint5_scenario,
        ),
        ScenarioDefinition(
            key="sprint6",
            aliases=("economy", "identity"),
            title="Economic Identity",
            description="Specialized mining, manufacturing, and survey worlds depend on each other.",
            builder=build_sprint6_scenario,
        ),
        ScenarioDefinition(
            key="sprint7",
            aliases=("traffic", "failure"),
            title="Traffic, Capacity, and Failure",
            description="A hard chokepoint and full outage expose queueing and recoverable disruption.",
            builder=build_sprint7_scenario,
        ),
        ScenarioDefinition(
            key="sprint8",
            aliases=("playtest", "benchmark", "balanced"),
            title="Playability Pass",
            description="Balanced benchmark with scenario inspection, report filtering, and save/load.",
            builder=build_sprint8_scenario,
        ),
        ScenarioDefinition(
            key="sprint9_logistics",
            aliases=("logistics",),
            title="Logistics Stretch",
            description="Sprint 8 playtest plus an aggressive PARTS delivery contract into Ashfall.",
            builder=build_sprint9_logistics_scenario,
        ),
        ScenarioDefinition(
            key="sprint9_frontier",
            aliases=("frontier_support",),
            title="Frontier Support",
            description="Sprint 8 playtest plus a FRONTIER_SUPPORT contract on Brink Frontier.",
            builder=build_sprint9_frontier_scenario,
        ),
        ScenarioDefinition(
            key="sprint9_recovery",
            aliases=("recovery", "gate_recovery"),
            title="Gate Recovery",
            description="Sprint 8 with a full gate outage and a GATE_RECOVERY contract to restore it.",
            builder=build_sprint9_recovery_scenario,
        ),
    )


def load_scenario(name: str = DEFAULT_SCENARIO) -> GameState:
    """Load a named built-in scenario."""

    normalized = name.strip().lower()
    for definition in scenario_definitions():
        if normalized in {definition.key, *definition.aliases}:
            return definition.builder()
    raise ValueError(f"unknown scenario: {name}")
