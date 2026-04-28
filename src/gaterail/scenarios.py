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
    GatePowerSupport,
    LinkMode,
    NetworkDisruption,
    NetworkLink,
    NetworkNode,
    NodeKind,
    ResourceRecipe,
    ResourceRecipeKind,
    TrackPoint,
    WorldState,
)
from gaterail.resources import ResourceDeposit


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
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Core Gate Hub",
            world_id="core",
            kind=NodeKind.GATE_HUB,
            storage_capacity=300,
            layout_x=130.0,
            layout_y=26.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Frontier Gate Hub",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=240,
            layout_x=0.0,
            layout_y=0.0,
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
            layout_x=118.0,
            layout_y=72.0,
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
            layout_x=-82.0,
            layout_y=148.0,
        )
    )

    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_north_ridge_iron",
            world_id="frontier",
            resource_id="iron_rich_ore",
            name="North Ridge Iron Shelf",
            grade=0.74,
            yield_per_tick=6,
            remaining_estimate=18_000,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_silica_flats",
            world_id="frontier",
            resource_id="silica_sand",
            name="Glass Flats Silica Field",
            grade=0.58,
            yield_per_tick=3,
            remaining_estimate=9_500,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_copper_trace",
            world_id="frontier",
            resource_id="copper_sulfide_ore",
            name="Red Wash Copper Trace",
            grade=0.52,
            yield_per_tick=4,
            remaining_estimate=8_400,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_carbon_basin",
            world_id="frontier",
            resource_id="carbon_feedstock",
            name="Low Basin Carbon Seam",
            grade=0.46,
            yield_per_tick=2,
            remaining_estimate=6_000,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="core_reclaimed_metal",
            world_id="core",
            resource_id="mixed_ore",
            name="Reclaimed Metal Reserve",
            grade=0.38,
            yield_per_tick=1,
            remaining_estimate=4_000,
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
            alignment=(TrackPoint(45.0, -18.0), TrackPoint(96.0, 18.0)),
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
            alignment=(TrackPoint(36.0, 12.0), TrackPoint(82.0, 78.0)),
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
            alignment=(
                TrackPoint(-78.0, 192.0),
                TrackPoint(-14.0, 154.0),
                TrackPoint(62.0, 106.0),
            ),
        )
    )
    return state


def _add_resource_chain_demo(state: GameState) -> None:
    """Add the Sprint 17B local resource-chain demo to a mature playtest state."""

    state.add_node(
        NetworkNode(
            id="frontier_ore_pit",
            name="North Ridge Ore Pit",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=320,
            transfer_limit_per_tick=18,
            layout_x=-150.0,
            layout_y=168.0,
            resource_deposit_id="frontier_north_ridge_iron",
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_carbon_rig",
            name="Low Basin Carbon Rig",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=240,
            transfer_limit_per_tick=12,
            layout_x=-138.0,
            layout_y=28.0,
            resource_deposit_id="frontier_carbon_basin",
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_silica_quarry",
            name="Glass Flats Silica Quarry",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=240,
            transfer_limit_per_tick=12,
            layout_x=-52.0,
            layout_y=202.0,
            resource_deposit_id="frontier_silica_flats",
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_copper_pit",
            name="Red Wash Copper Pit",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=260,
            transfer_limit_per_tick=12,
            layout_x=-186.0,
            layout_y=76.0,
            resource_deposit_id="frontier_copper_trace",
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_copper_refinery",
            name="Red Wash Copper Refinery",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=320,
            transfer_limit_per_tick=12,
            layout_x=-102.0,
            layout_y=58.0,
            resource_recipe=ResourceRecipe(
                id="copper_refining",
                kind=ResourceRecipeKind.REFINING,
                inputs={"copper_sulfide_ore": 4},
                outputs={"copper": 2},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_smelter",
            name="Brink Ore Smelter",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=500,
            transfer_limit_per_tick=18,
            layout_x=-34.0,
            layout_y=98.0,
            resource_recipe=ResourceRecipe(
                id="iron_smelting",
                kind=ResourceRecipeKind.SMELTING,
                inputs={
                    "carbon_feedstock": 1,
                    "iron_rich_ore": 6,
                },
                outputs={"iron": 4},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_silicon_refiner",
            name="Glass Flats Silicon Refiner",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=360,
            transfer_limit_per_tick=14,
            layout_x=-18.0,
            layout_y=178.0,
            resource_recipe=ResourceRecipe(
                id="silicon_refining",
                kind=ResourceRecipeKind.REFINING,
                inputs={
                    "carbon_feedstock": 1,
                    "silica_sand": 3,
                },
                outputs={"silicon": 3},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_electronics_assembler",
            name="Brink Electronics Assembler",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=360,
            transfer_limit_per_tick=12,
            layout_x=40.0,
            layout_y=166.0,
            resource_recipe=ResourceRecipe(
                id="electronics_assembly",
                kind=ResourceRecipeKind.ELECTRONICS_ASSEMBLY,
                inputs={
                    "copper": 1,
                    "silicon": 2,
                },
                outputs={"electronics": 2},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_semiconductor_line",
            name="Brink Semiconductor Line",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=320,
            transfer_limit_per_tick=10,
            layout_x=74.0,
            layout_y=142.0,
            resource_recipe=ResourceRecipe(
                id="semiconductor_lithography",
                kind=ResourceRecipeKind.SEMICONDUCTOR,
                inputs={
                    "electronics": 1,
                    "silicon": 1,
                },
                outputs={"semiconductors": 1},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate_fabricator",
            name="Brink Gate Fabricator",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=420,
            transfer_limit_per_tick=12,
            layout_x=48.0,
            layout_y=112.0,
            resource_recipe=ResourceRecipe(
                id="gate_frame_fabrication",
                kind=ResourceRecipeKind.FABRICATION,
                inputs={
                    "iron": 4,
                    "semiconductors": 1,
                },
                outputs={"gate_components": 1},
            ),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_ore_pit_smelter",
            origin="frontier_ore_pit",
            destination="frontier_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=12,
            alignment=(TrackPoint(-116.0, 164.0), TrackPoint(-72.0, 126.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_silica_silicon",
            origin="frontier_silica_quarry",
            destination="frontier_silicon_refiner",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(-42.0, 206.0), TrackPoint(-28.0, 190.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_carbon_smelter",
            origin="frontier_carbon_rig",
            destination="frontier_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=8,
            alignment=(TrackPoint(-112.0, 52.0), TrackPoint(-72.0, 86.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_carbon_silicon",
            origin="frontier_carbon_rig",
            destination="frontier_silicon_refiner",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=8,
            alignment=(TrackPoint(-102.0, 70.0), TrackPoint(-48.0, 134.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_copper_refinery",
            origin="frontier_copper_pit",
            destination="frontier_copper_refinery",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(-154.0, 70.0), TrackPoint(-124.0, 62.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_copper_electronics",
            origin="frontier_copper_refinery",
            destination="frontier_electronics_assembler",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=8,
            alignment=(TrackPoint(-54.0, 88.0), TrackPoint(10.0, 136.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_silicon_electronics",
            origin="frontier_silicon_refiner",
            destination="frontier_electronics_assembler",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(6.0, 182.0), TrackPoint(30.0, 172.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_silicon_semiconductor",
            origin="frontier_silicon_refiner",
            destination="frontier_semiconductor_line",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=6,
            alignment=(TrackPoint(20.0, 172.0), TrackPoint(54.0, 154.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_electronics_semiconductor",
            origin="frontier_electronics_assembler",
            destination="frontier_semiconductor_line",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=6,
            alignment=(TrackPoint(54.0, 158.0),),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_semiconductor_fabricator",
            origin="frontier_semiconductor_line",
            destination="frontier_gate_fabricator",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=6,
            alignment=(TrackPoint(66.0, 128.0),),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_smelter_fabricator",
            origin="frontier_smelter",
            destination="frontier_gate_fabricator",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
            alignment=(TrackPoint(-6.0, 128.0), TrackPoint(28.0, 116.0)),
        )
    )


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
            layout_x=0.0,
            layout_y=0.0,
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
            layout_x=108.0,
            layout_y=-44.0,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="ashfall_fissile_trace",
            world_id="outer",
            resource_id="fissile_ore",
            name="Ashfall Fissile Trace",
            grade=0.31,
            yield_per_tick=1,
            remaining_estimate=2_600,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="ashfall_shadow_ice",
            world_id="outer",
            resource_id="water_ice",
            name="Shadowline Ice Pocket",
            grade=0.67,
            yield_per_tick=2,
            remaining_estimate=7_200,
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
            alignment=(TrackPoint(38.0, -6.0), TrackPoint(82.0, -52.0)),
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
    _add_resource_chain_demo(state)
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


def build_sprint19_scenario() -> GameState:
    """Build the resource-supported gate power scenario."""

    state = build_sprint8_scenario()
    state.worlds["frontier"].power_available = 120
    state.add_gate_support(
        GatePowerSupport(
            id="frontier_gate_component_support",
            link_id="gate_frontier_outer",
            node_id="frontier_gate_fabricator",
            inputs={"gate_components": 1},
            power_bonus=40,
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
        ScenarioDefinition(
            key="sprint19",
            aliases=("power", "gate_power", "resource_power"),
            title="Resource-backed Gate Power",
            description="A frontier gate recovers when upstream industry fabricates gate components.",
            builder=build_sprint19_scenario,
        ),
    )


def load_scenario(name: str = DEFAULT_SCENARIO) -> GameState:
    """Load a named built-in scenario."""

    normalized = name.strip().lower()
    for definition in scenario_definitions():
        if normalized in {definition.key, *definition.aliases}:
            return definition.builder()
    raise ValueError(f"unknown scenario: {name}")
