"""Scenario construction for CLI-playable prototypes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from gaterail.cargo import CargoType
from gaterail.models import (
    ConstructionProject,
    Contract,
    ContractKind,
    DevelopmentTier,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    GameState,
    GatePowerSupport,
    InternalConnection,
    LinkMode,
    NetworkDisruption,
    NetworkLink,
    NetworkNode,
    NodeKind,
    NodeRecipe,
    PowerPlant,
    PowerPlantKind,
    PortDirection,
    ResourceRecipe,
    ResourceRecipeKind,
    SpaceSite,
    TrackPoint,
    TrainConsist,
    WorldState,
)
from gaterail.resources import ResourceDeposit


DEFAULT_SCENARIO = "sprint20"


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
            name="Vesta Industrial Rail Yard",
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
            name="Vesta Railgate Anchor",
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
            name="Brink Railgate Terminal",
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
            name="Brink Colony Logistics Hub",
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
            name="North Ridge Extraction Outpost",
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
            name="Brink Aperture Control Works",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            storage_capacity=420,
            transfer_limit_per_tick=12,
            layout_x=48.0,
            layout_y=112.0,
            resource_recipe=ResourceRecipe(
                id="aperture_control_fabrication",
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
    """Build a Railgate corridor pressure expansion scenario."""

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
            name="Ashfall Railgate Receiving Terminal",
            world_id="outer",
            kind=NodeKind.GATE_HUB,
            storage_capacity=120,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_outer_gate",
            name="Brink Spur Railgate Anchor",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=240,
            layout_x=48.0,
            layout_y=-62.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="outer_outpost",
            name="Ashfall Extraction Outpost",
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
            origin="frontier_outer_gate",
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
            id="rail_frontier_gate_transfer",
            origin="frontier_gate",
            destination="frontier_outer_gate",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=12,
            alignment=(TrackPoint(16.0, -28.0), TrackPoint(34.0, -48.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_outer_gate_settlement",
            origin="frontier_outer_gate",
            destination="frontier_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
            alignment=(TrackPoint(78.0, -18.0), TrackPoint(104.0, 36.0)),
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
    state.links["rail_core_yard_gate"] = replace(state.links["rail_core_yard_gate"], travel_ticks=2)
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
    state.links["rail_core_yard_gate"] = replace(
        state.links["rail_core_yard_gate"],
        capacity_per_tick=1,
        travel_ticks=3,
    )
    state.add_disruption(
        NetworkDisruption(
            id="frontier_outer_gate_alignment",
            link_id="gate_frontier_outer",
            start_tick=13,
            end_tick=14,
            capacity_multiplier=0.0,
            reason="Railgate aperture alignment maintenance",
        )
    )
    return state


def build_sprint8_scenario() -> GameState:
    """Build the balanced playtest scenario for repeatable CLI iteration."""

    state = build_sprint7_scenario()
    state.links["rail_core_yard_gate"] = replace(
        state.links["rail_core_yard_gate"],
        capacity_per_tick=2,
        travel_ticks=3,
    )
    state.disruptions["frontier_outer_gate_alignment"] = NetworkDisruption(
        id="frontier_outer_gate_alignment",
        link_id="gate_frontier_outer",
        start_tick=13,
        end_tick=14,
        capacity_multiplier=0.5,
        reason="Railgate aperture alignment throttling",
    )
    _add_resource_chain_demo(state)
    state.add_contract(
        Contract(
            id="brink_food_relief",
            kind=ContractKind.CARGO_DELIVERY,
            title="Brink Colony Support Freight",
            client="Brink Extraction Combine",
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
            title="Vesta Ore Intake Quota",
            client="Vesta Industrial Combine",
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
            title="Ashfall Colony Support Lifeline",
            client="Ashfall Corridor Logistics",
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
            client="Ashfall Corridor Logistics",
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
            title="Brink Frontier Colony Support Streak",
            client="Frontier Transit Combine Council",
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
        reason="Railgate aperture alignment outage",
    )
    state.add_contract(
        Contract(
            id="ashfall_gate_recovery",
            kind=ContractKind.GATE_RECOVERY,
            title="Ashfall Railgate Corridor Recovery",
            client="Ashfall Corridor Logistics",
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
    """Build the resource-supported Railgate power scenario."""

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


def build_sprint19b_scenario() -> GameState:
    """Build the resource-backed power generation scenario."""

    state = build_sprint8_scenario()
    state.worlds["frontier"].power_available = 110
    state.resource_deposits["frontier_carbon_basin"] = replace(
        state.resource_deposits["frontier_carbon_basin"],
        yield_per_tick=3,
    )
    state.add_node(
        NetworkNode(
            id="frontier_thermal_plant",
            name="Low Basin Thermal Plant",
            world_id="frontier",
            kind=NodeKind.INDUSTRY,
            resource_demand={"carbon_feedstock": 1},
            storage_capacity=160,
            transfer_limit_per_tick=8,
            layout_x=-88.0,
            layout_y=18.0,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_carbon_power",
            origin="frontier_carbon_rig",
            destination="frontier_thermal_plant",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=6,
            alignment=(TrackPoint(-124.0, 24.0), TrackPoint(-104.0, 18.0)),
        )
    )
    state.add_power_plant(
        PowerPlant(
            id="frontier_low_basin_thermal",
            node_id="frontier_thermal_plant",
            kind=PowerPlantKind.THERMAL,
            inputs={"carbon_feedstock": 1},
            power_output=40,
        )
    )
    return state


def build_sprint20_scenario() -> GameState:
    """Build the space extraction scenario."""

    state = build_sprint19b_scenario()
    
    from gaterail.models import SpaceSite
    
    state.add_node(
        NetworkNode(
            id="frontier_orbital",
            name="Brink Orbital Yard",
            world_id="frontier",
            kind=NodeKind.SPACEPORT,
            storage_capacity=3000,
            layout_x=200.0,
            layout_y=-120.0,
        )
    )
    
    state.add_space_site(
        SpaceSite(
            id="site_kessler_belt",
            name="Kessler Debris Belt",
            resource_id="mixed_ore",
            travel_ticks=4,
            base_yield=80,
            discovered=True,
        )
    )
    
    state.add_space_site(
        SpaceSite(
            id="site_jovian_cloud",
            name="Jovian Gas Cloud",
            resource_id="carbon_feedstock",
            travel_ticks=6,
            base_yield=120,
            discovered=True,
        )
    )

    return state


def build_mining_to_manufacturing_scenario() -> GameState:
    """Canonical vertical slice: survey, extract, refine, assemble, and support a colony."""

    state = GameState()
    state.economic_identity_enabled = True
    state.finance.cash = 30_000.0

    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=4_500,
            stability=0.7,
            power_available=240,
            power_used=40,
            specialization="mining",
        )
    )
    state.add_world(
        WorldState(
            id="core",
            name="Vesta Core",
            tier=DevelopmentTier.CORE_WORLD,
            population=8_000_000,
            stability=0.95,
            power_available=600,
            power_used=180,
            specialization="manufacturing",
        )
    )

    state.add_node(
        NetworkNode(
            id="frontier_depot",
            name="Brink Frontier Rail Depot",
            world_id="frontier",
            kind=NodeKind.DEPOT,
            inventory={
                CargoType.CONSTRUCTION_MATERIALS: 300,
                CargoType.ELECTRONICS: 80,
                CargoType.PARTS: 90,
                CargoType.FUEL: 200,
                CargoType.FOOD: 12,
                CargoType.MACHINERY: 4,
            },
            storage_capacity=2_000,
            transfer_limit_per_tick=240,
            layout_x=-120.0,
            layout_y=-60.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_warehouse",
            name="Brink Bulk Freight Warehouse",
            world_id="frontier",
            kind=NodeKind.WAREHOUSE,
            storage_capacity=4_000,
            transfer_limit_per_tick=48,
            layout_x=-84.0,
            layout_y=52.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_collection",
            name="Brink Receiving Terminal",
            world_id="frontier",
            kind=NodeKind.COLLECTION_STATION,
            storage_capacity=600,
            transfer_limit_per_tick=24,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Brink Railgate Anchor",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=400,
            transfer_limit_per_tick=24,
            layout_x=140.0,
            layout_y=20.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_settlement",
            name="Brink Colony Logistics Hub",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory={CargoType.FOOD: 8, CargoType.CONSTRUCTION_MATERIALS: 4},
            demand={CargoType.PARTS: 1},
            storage_capacity=500,
            transfer_limit_per_tick=16,
            layout_x=250.0,
            layout_y=90.0,
        )
    )

    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Vesta Railgate Receiving Terminal",
            world_id="core",
            kind=NodeKind.GATE_HUB,
            storage_capacity=400,
            transfer_limit_per_tick=24,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_smelter",
            name="Vesta Arc Smelter",
            world_id="core",
            kind=NodeKind.INDUSTRY,
            storage_capacity=600,
            transfer_limit_per_tick=24,
            recipe=NodeRecipe(
                inputs={CargoType.ORE: 20},
                outputs={CargoType.METAL: 20},
            ),
            layout_x=180.0,
            layout_y=-100.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_yard",
            name="Vesta Manufacturing Yard",
            world_id="core",
            kind=NodeKind.DEPOT,
            inventory={CargoType.MACHINERY: 4},
            storage_capacity=600,
            transfer_limit_per_tick=24,
            recipe=NodeRecipe(
                inputs={CargoType.METAL: 10},
                outputs={
                    CargoType.CONSTRUCTION_MATERIALS: 8,
                    CargoType.PARTS: 10,
                },
            ),
            pull_logic=False,
            layout_x=160.0,
            layout_y=0.0,
        )
    )

    state.add_link(
        NetworkLink(
            id="rail_frontier_depot_warehouse",
            origin="frontier_depot",
            destination="frontier_warehouse",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=18,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_depot_collection",
            origin="frontier_depot",
            destination="frontier_collection",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_collection_gate",
            origin="frontier_collection",
            destination="frontier_gate",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_frontier_core",
            origin="frontier_gate",
            destination="core_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=8,
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
            capacity_per_tick=12,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_core_gate_yard",
            origin="core_gate",
            destination="core_yard",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_core_yard_smelter",
            origin="core_yard",
            destination="core_smelter",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=12,
        )
    )

    state.add_space_site(
        SpaceSite(
            id="site_brink_belt",
            name="Brink Asteroid Belt",
            resource_id="mixed_ore",
            travel_ticks=4,
            base_yield=60,
            discovered=False,
            cargo_type=CargoType.ORE,
        )
    )

    state.add_train(
        FreightTrain(
            id="constructor",
            name="Constructor",
            node_id="frontier_depot",
            capacity=220,
            consist=TrainConsist.GENERAL,
        )
    )
    state.add_train(
        FreightTrain(
            id="prospector",
            name="Prospector",
            node_id="frontier_collection",
            capacity=24,
            consist=TrainConsist.BULK_HOPPER,
        )
    )
    state.add_train(
        FreightTrain(
            id="metal_runner",
            name="Metal Runner",
            node_id="core_smelter",
            capacity=20,
            consist=TrainConsist.GENERAL,
        )
    )
    state.add_train(
        FreightTrain(
            id="builder",
            name="Builder",
            node_id="core_yard",
            capacity=12,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="ore_haul_to_core",
            train_id="prospector",
            origin="frontier_collection",
            destination="core_smelter",
            cargo_type=CargoType.ORE,
            units_per_departure=20,
            interval_ticks=14,
            next_departure_tick=1,
            priority=80,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="metal_to_assembly_yard",
            train_id="metal_runner",
            origin="core_smelter",
            destination="core_yard",
            cargo_type=CargoType.METAL,
            units_per_departure=10,
            interval_ticks=12,
            next_departure_tick=1,
            priority=75,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="parts_to_frontier_settlement",
            train_id="builder",
            origin="core_yard",
            destination="frontier_settlement",
            cargo_type=CargoType.PARTS,
            units_per_departure=10,
            interval_ticks=18,
            next_departure_tick=1,
            priority=70,
            active=False,
        )
    )
    state.add_contract(
        Contract(
            id="frontier_parts_upgrade",
            kind=ContractKind.CARGO_DELIVERY,
            title="Brink Logistics Hub Maintenance Parts",
            client="Brink Extraction Combine",
            destination_node_id="frontier_settlement",
            cargo_type=CargoType.PARTS,
            target_units=10,
            due_tick=160,
            reward_cash=12_500.0,
            penalty_cash=1_200.0,
            reward_reputation=6,
            penalty_reputation=5,
        )
    )
    state.add_contract(
        Contract(
            id="frontier_colony_stabilization",
            kind=ContractKind.FRONTIER_SUPPORT,
            title="Stabilize Brink Frontier Colony",
            client="Brink Transit Combine",
            target_world_id="frontier",
            target_units=2,
            due_tick=190,
            reward_cash=4_000.0,
            penalty_cash=1_000.0,
            reward_reputation=4,
            penalty_reputation=3,
        )
    )

    return state


def _tutorial_depot_inventory() -> dict[CargoType, int]:
    """Return the generous per-world starter stock for tutorial construction."""

    return {
        CargoType.CONSTRUCTION_MATERIALS: 800,
        CargoType.METAL: 300,
        CargoType.PARTS: 180,
        CargoType.ELECTRONICS: 120,
        CargoType.FUEL: 180,
        CargoType.FOOD: 240,
        CargoType.WATER: 240,
    }


def _tutorial_depot_stock_targets() -> dict[CargoType, int]:
    """Reserve construction stock so tutorial industry does not consume it."""

    return {
        CargoType.CONSTRUCTION_MATERIALS: 500,
        CargoType.METAL: 300,
        CargoType.PARTS: 120,
        CargoType.ELECTRONICS: 80,
        CargoType.FUEL: 100,
    }


def _add_tutorial_local_rail(state: GameState, world_id: str, node_id: str, *, travel_ticks: int = 1) -> None:
    """Connect one local node to its world's depot."""

    state.add_link(
        NetworkLink(
            id=f"rail_{world_id}_depot_{node_id.removeprefix(world_id + '_')}",
            origin=f"{world_id}_depot",
            destination=node_id,
            mode=LinkMode.RAIL,
            travel_ticks=travel_ticks,
            capacity_per_tick=18,
        )
    )


def _tutorial_component(
    component_id: str,
    kind: FacilityComponentKind,
    *,
    rate: int = 0,
    capacity: int = 0,
    power_required: int = 0,
    power_provided: int = 0,
) -> FacilityComponent:
    """Return a compact facility component for tutorial-local node summaries."""

    return FacilityComponent(
        id=component_id,
        kind=kind,
        rate=rate,
        capacity=capacity,
        power_required=power_required,
        power_provided=power_provided,
    )


def _tutorial_facility(*components: FacilityComponent) -> Facility:
    """Return facility metadata used by the tutorial local layer."""

    return Facility(components={component.id: component for component in components})


def _add_tutorial_world(
    state: GameState,
    *,
    world_id: str,
    name: str,
    tier: DevelopmentTier,
    specialization: str,
    position: int,
) -> None:
    """Add one tutorial world with two Railgate terminals and stocked construction depot."""

    state.add_world(
        WorldState(
            id=world_id,
            name=name,
            tier=tier,
            population=75_000 if tier < DevelopmentTier.CORE_WORLD else 4_000_000,
            stability=0.86,
            power_available=520,
            power_used=140,
            specialization=specialization,
        )
    )
    x_offset = float(position * 40)
    state.add_node(
        NetworkNode(
            id=f"{world_id}_depot",
            name=f"{name} Depot",
            world_id=world_id,
            kind=NodeKind.DEPOT,
            inventory=_tutorial_depot_inventory(),
            stock_targets=_tutorial_depot_stock_targets(),
            storage_capacity=4_000,
            transfer_limit_per_tick=36,
            layout_x=x_offset,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id=f"{world_id}_gate_prev",
            name=f"{name} Railgate Receiving Terminal",
            world_id=world_id,
            kind=NodeKind.GATE_HUB,
            storage_capacity=1_500,
            transfer_limit_per_tick=30,
            layout_x=x_offset - 130.0,
            layout_y=-30.0,
        )
    )
    state.add_node(
        NetworkNode(
            id=f"{world_id}_gate_next",
            name=f"{name} Railgate Anchor",
            world_id=world_id,
            kind=NodeKind.GATE_HUB,
            storage_capacity=1_500,
            transfer_limit_per_tick=30,
            layout_x=x_offset + 130.0,
            layout_y=-30.0,
        )
    )
    state.add_node(
        NetworkNode(
            id=f"{world_id}_settlement",
            name=f"{name} Colony Logistics Hub",
            world_id=world_id,
            kind=NodeKind.SETTLEMENT,
            demand={CargoType.FOOD: 1},
            storage_capacity=1_000,
            transfer_limit_per_tick=24,
            layout_x=x_offset,
            layout_y=120.0,
        )
    )
    _add_tutorial_local_rail(state, world_id, f"{world_id}_gate_prev")
    _add_tutorial_local_rail(state, world_id, f"{world_id}_gate_next")
    _add_tutorial_local_rail(state, world_id, f"{world_id}_settlement")


def build_tutorial_six_worlds_scenario() -> GameState:
    """Six-world tutorial start with a powered Railgate corridor ring and active cargo loop."""

    state = GameState()
    state.economic_identity_enabled = True
    state.finance.cash = 150_000.0

    worlds = (
        ("vesta", "Vesta Core", DevelopmentTier.CORE_WORLD, "manufacturing"),
        ("brink", "Brink Mines", DevelopmentTier.FRONTIER_COLONY, "mining"),
        ("cinder", "Cinder Forge", DevelopmentTier.INDUSTRIAL_COLONY, "manufacturing"),
        ("atlas", "Atlas Yards", DevelopmentTier.INDUSTRIAL_COLONY, "manufacturing"),
        ("helix", "Helix Reach", DevelopmentTier.FRONTIER_COLONY, "survey_outpost"),
        ("aurora", "Aurora Farms", DevelopmentTier.FRONTIER_COLONY, "mining"),
    )
    for position, (world_id, name, tier, specialization) in enumerate(worlds):
        _add_tutorial_world(
            state,
            world_id=world_id,
            name=name,
            tier=tier,
            specialization=specialization,
            position=position,
        )

    state.add_node(
        NetworkNode(
            id="brink_mine",
            name="Brink Tutorial Extraction Outpost",
            world_id="brink",
            kind=NodeKind.EXTRACTOR,
            inventory={CargoType.ORE: 80},
            production={CargoType.ORE: 12},
            storage_capacity=1_200,
            transfer_limit_per_tick=24,
            facility=_tutorial_facility(
                _tutorial_component(
                    "brink_extractor_head",
                    FacilityComponentKind.EXTRACTOR_HEAD,
                    rate=12,
                    power_required=8,
                ),
                _tutorial_component(
                    "brink_loader",
                    FacilityComponentKind.LOADER,
                    rate=24,
                    power_required=4,
                ),
            ),
            layout_x=40.0,
            layout_y=210.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="cinder_smelter",
            name="Cinder Tutorial Refinery",
            world_id="cinder",
            kind=NodeKind.INDUSTRY,
            storage_capacity=1_500,
            transfer_limit_per_tick=30,
            facility=_tutorial_facility(
                _tutorial_component(
                    "cinder_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=30,
                    power_required=4,
                ),
                _tutorial_component(
                    "cinder_smelter_block",
                    FacilityComponentKind.SMELTER,
                    rate=20,
                    power_required=18,
                ),
                _tutorial_component(
                    "cinder_loader",
                    FacilityComponentKind.LOADER,
                    rate=30,
                    power_required=4,
                ),
            ),
            recipe=NodeRecipe(
                inputs={CargoType.ORE: 20},
                outputs={CargoType.METAL: 20},
            ),
            layout_x=80.0,
            layout_y=210.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="atlas_factory",
            name="Atlas Tutorial Maintenance Factory",
            world_id="atlas",
            kind=NodeKind.INDUSTRY,
            storage_capacity=1_500,
            transfer_limit_per_tick=30,
            facility=_tutorial_facility(
                _tutorial_component(
                    "atlas_factory_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=30,
                    power_required=4,
                ),
                _tutorial_component(
                    "atlas_factory_fabricator",
                    FacilityComponentKind.FABRICATOR,
                    rate=12,
                    power_required=16,
                ),
                _tutorial_component(
                    "atlas_factory_loader",
                    FacilityComponentKind.LOADER,
                    rate=30,
                    power_required=4,
                ),
            ),
            recipe=NodeRecipe(
                inputs={CargoType.METAL: 10},
                outputs={
                    CargoType.PARTS: 12,
                    CargoType.CONSTRUCTION_MATERIALS: 8,
                },
            ),
            layout_x=120.0,
            layout_y=210.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="atlas_gate_component_line",
            name="Atlas Aperture Control Line",
            world_id="atlas",
            kind=NodeKind.INDUSTRY,
            storage_capacity=1_200,
            transfer_limit_per_tick=24,
            facility=_tutorial_facility(
                _tutorial_component(
                    "atlas_gateworks_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=24,
                    power_required=4,
                ),
                _tutorial_component(
                    "atlas_gateworks_fabricator",
                    FacilityComponentKind.FABRICATOR,
                    rate=8,
                    power_required=20,
                ),
                _tutorial_component(
                    "atlas_gateworks_loader",
                    FacilityComponentKind.LOADER,
                    rate=24,
                    power_required=4,
                ),
            ),
            recipe=NodeRecipe(
                inputs={CargoType.PARTS: 8, CargoType.ELECTRONICS: 4},
                outputs={CargoType.GATE_COMPONENTS: 4},
            ),
            layout_x=230.0,
            layout_y=210.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="atlas_outbound_gate",
            name="Atlas Tutorial Outbound Railgate Terminal",
            world_id="atlas",
            kind=NodeKind.GATE_HUB,
            storage_capacity=1_500,
            transfer_limit_per_tick=30,
            facility=_tutorial_facility(
                _tutorial_component(
                    "atlas_outbound_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=24,
                    power_required=4,
                ),
                _tutorial_component(
                    "atlas_outbound_gate_interface",
                    FacilityComponentKind.GATE_INTERFACE,
                    rate=4,
                    power_required=30,
                ),
            ),
            layout_x=310.0,
            layout_y=-80.0,
        )
    )
    state.add_construction_project(
        ConstructionProject(
            id="proj_atlas_outbound_gate",
            target_node_id="atlas_outbound_gate",
            required_cargo={CargoType.GATE_COMPONENTS: 4},
        )
    )
    state.add_node(
        NetworkNode(
            id="aurora_farm",
            name="Aurora Tutorial Farm",
            world_id="aurora",
            kind=NodeKind.EXTRACTOR,
            production={CargoType.FOOD: 8, CargoType.WATER: 6},
            storage_capacity=1_200,
            transfer_limit_per_tick=24,
            layout_x=200.0,
            layout_y=210.0,
        )
    )

    _add_tutorial_local_rail(state, "brink", "brink_mine")
    _add_tutorial_local_rail(state, "cinder", "cinder_smelter")
    _add_tutorial_local_rail(state, "atlas", "atlas_factory")
    _add_tutorial_local_rail(state, "atlas", "atlas_gate_component_line")
    _add_tutorial_local_rail(state, "atlas", "atlas_outbound_gate")
    _add_tutorial_local_rail(state, "aurora", "aurora_farm")

    state.add_world(
        WorldState(
            id="sable",
            name="Sable Reach",
            tier=DevelopmentTier.OUTPOST,
            population=0,
            stability=0.62,
            power_available=180,
            power_used=35,
            specialization="survey_destination",
        )
    )
    state.add_node(
        NetworkNode(
            id="sable_gate_anchor",
            name="Sable Reach Railgate Receiving Anchor",
            world_id="sable",
            kind=NodeKind.GATE_HUB,
            storage_capacity=1_000,
            transfer_limit_per_tick=24,
            facility=_tutorial_facility(
                _tutorial_component(
                    "sable_anchor_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=20,
                    power_required=4,
                ),
                _tutorial_component(
                    "sable_anchor_gate_interface",
                    FacilityComponentKind.GATE_INTERFACE,
                    rate=4,
                    power_required=20,
                ),
            ),
            layout_x=-80.0,
            layout_y=-30.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="sable_settlement",
            name="Sable Starter Logistics Camp",
            world_id="sable",
            kind=NodeKind.SETTLEMENT,
            demand={CargoType.FOOD: 1},
            storage_capacity=800,
            transfer_limit_per_tick=20,
            facility=_tutorial_facility(
                _tutorial_component(
                    "sable_camp_unloader",
                    FacilityComponentKind.UNLOADER,
                    rate=20,
                    power_required=4,
                ),
                _tutorial_component(
                    "sable_camp_storage",
                    FacilityComponentKind.WAREHOUSE_BAY,
                    capacity=800,
                    power_required=4,
                ),
            ),
            layout_x=80.0,
            layout_y=90.0,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_sable_gate_anchor_settlement",
            origin="sable_gate_anchor",
            destination="sable_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=20,
        )
    )
    state.add_space_site(
        SpaceSite(
            id="site_sable_reach",
            name="Sable Reach Corridor Survey",
            resource_id="gate_reactive_isotope",
            travel_ticks=4,
            base_yield=1,
            discovered=False,
        )
    )

    ring = ("vesta", "brink", "cinder", "atlas", "helix", "aurora")
    for index, origin_world in enumerate(ring):
        destination_world = ring[(index + 1) % len(ring)]
        state.add_link(
            NetworkLink(
                id=f"gate_{origin_world}_{destination_world}",
                origin=f"{origin_world}_gate_next",
                destination=f"{destination_world}_gate_prev",
                mode=LinkMode.GATE,
                travel_ticks=1,
                capacity_per_tick=4,
                power_required=60,
            )
        )

    state.add_train(
        FreightTrain(
            id="tutorial_ore_runner",
            name="Tutorial Ore Runner",
            node_id="brink_mine",
            capacity=30,
            consist=TrainConsist.BULK_HOPPER,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_metal_runner",
            name="Tutorial Metal Runner",
            node_id="cinder_smelter",
            capacity=20,
            consist=TrainConsist.GENERAL,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_parts_runner",
            name="Tutorial Parts Runner",
            node_id="atlas_factory",
            capacity=12,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_gateworks_parts_runner",
            name="Tutorial Gateworks Parts Runner",
            node_id="atlas_factory",
            capacity=16,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_gateworks_electronics_runner",
            name="Tutorial Gateworks Electronics Runner",
            node_id="atlas_depot",
            capacity=12,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_gate_component_runner",
            name="Tutorial Aperture Component Runner",
            node_id="atlas_gate_component_line",
            capacity=8,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_train(
        FreightTrain(
            id="tutorial_starter_runner",
            name="Tutorial Starter Freight Runner",
            node_id="atlas_depot",
            capacity=40,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_ore_to_cinder",
            train_id="tutorial_ore_runner",
            origin="brink_mine",
            destination="cinder_smelter",
            cargo_type=CargoType.ORE,
            units_per_departure=30,
            interval_ticks=8,
            next_departure_tick=1,
            priority=90,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_metal_to_atlas",
            train_id="tutorial_metal_runner",
            origin="cinder_smelter",
            destination="atlas_factory",
            cargo_type=CargoType.METAL,
            units_per_departure=20,
            interval_ticks=10,
            next_departure_tick=1,
            priority=80,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_parts_to_helix",
            train_id="tutorial_parts_runner",
            origin="atlas_factory",
            destination="helix_settlement",
            cargo_type=CargoType.PARTS,
            units_per_departure=12,
            interval_ticks=12,
            next_departure_tick=1,
            priority=70,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_parts_to_gateworks",
            train_id="tutorial_gateworks_parts_runner",
            origin="atlas_factory",
            destination="atlas_gate_component_line",
            cargo_type=CargoType.PARTS,
            units_per_departure=8,
            interval_ticks=10,
            next_departure_tick=1,
            priority=75,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_electronics_to_gateworks",
            train_id="tutorial_gateworks_electronics_runner",
            origin="atlas_depot",
            destination="atlas_gate_component_line",
            cargo_type=CargoType.ELECTRONICS,
            units_per_departure=4,
            interval_ticks=10,
            next_departure_tick=1,
            priority=74,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_components_to_gate",
            train_id="tutorial_gate_component_runner",
            origin="atlas_gate_component_line",
            destination="atlas_outbound_gate",
            cargo_type=CargoType.GATE_COMPONENTS,
            units_per_departure=4,
            interval_ticks=12,
            next_departure_tick=1,
            priority=73,
            active=False,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="tutorial_starter_to_sable",
            train_id="tutorial_starter_runner",
            origin="atlas_depot",
            destination="sable_settlement",
            cargo_type=CargoType.CONSTRUCTION_MATERIALS,
            units_per_departure=40,
            interval_ticks=14,
            next_departure_tick=1,
            priority=72,
            active=False,
        )
    )
    state.add_contract(
        Contract(
            id="helix_parts_tutorial",
            kind=ContractKind.CARGO_DELIVERY,
            title="Helix Corridor Maintenance Parts",
            client="Helix Transit Combine",
            destination_node_id="helix_settlement",
            cargo_type=CargoType.PARTS,
            target_units=12,
            due_tick=90,
            reward_cash=20_000.0,
            penalty_cash=0.0,
            reward_reputation=4,
            penalty_reputation=0,
        )
    )
    state.add_contract(
        Contract(
            id="sable_starter_cargo",
            kind=ContractKind.CARGO_DELIVERY,
            title="Sable Reach Starter Freight",
            client="Sable Reach Charter Combine",
            destination_node_id="sable_settlement",
            cargo_type=CargoType.CONSTRUCTION_MATERIALS,
            target_units=40,
            due_tick=260,
            reward_cash=30_000.0,
            penalty_cash=0.0,
            reward_reputation=6,
            penalty_reputation=0,
        )
    )

    return state


def _facility_port(
    port_id: str,
    direction: PortDirection,
    cargo_type: CargoType,
    *,
    rate: int,
    capacity: int = 0,
) -> FacilityPort:
    """Return a compact typed facility port for local logistics tutorials."""

    return FacilityPort(
        id=port_id,
        direction=direction,
        cargo_type=cargo_type,
        rate=rate,
        capacity=capacity,
    )


def _facility_connection(
    connection_id: str,
    source_component_id: str,
    source_port_id: str,
    destination_component_id: str,
    destination_port_id: str,
) -> InternalConnection:
    """Return a compact internal facility connection."""

    return InternalConnection(
        id=connection_id,
        source_component_id=source_component_id,
        source_port_id=source_port_id,
        destination_component_id=destination_component_id,
        destination_port_id=destination_port_id,
    )


def build_tutorial_local_logistics_scenario() -> GameState:
    """Bottom-up local logistics tutorial from mine wiring to Railgate deployment."""

    state = GameState()
    state.finance.cash = 180_000.0
    state.construction_inventory = {
        CargoType.CONSTRUCTION_MATERIALS: 40,
    }

    state.add_world(
        WorldState(
            id="atlas",
            name="Atlas Yards",
            tier=DevelopmentTier.DEVELOPED_WORLD,
            population=1_200_000,
            stability=0.91,
            power_available=620,
            power_used=180,
            specialization="manufacturing",
        )
    )
    state.add_world(
        WorldState(
            id="sable",
            name="Sable Reach",
            tier=DevelopmentTier.OUTPOST,
            population=0,
            stability=0.62,
            power_available=180,
            power_used=35,
            specialization="survey_destination",
        )
    )

    state.add_node(
        NetworkNode(
            id="atlas_depot",
            name="Atlas Construction Depot",
            world_id="atlas",
            kind=NodeKind.DEPOT,
            inventory={
                CargoType.CONSTRUCTION_MATERIALS: 120,
                CargoType.ELECTRONICS: 20,
                CargoType.FOOD: 40,
                CargoType.WATER: 40,
            },
            storage_capacity=2_000,
            transfer_limit_per_tick=36,
            layout_x=0.0,
            layout_y=0.0,
        )
    )

    state.add_node(
        NetworkNode(
            id="atlas_local_mine",
            name="Atlas Tutorial Ore Loader",
            world_id="atlas",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=220,
            transfer_limit_per_tick=24,
            requires_facility_handling=True,
            facility=Facility(
                components={
                    "mine_head": FacilityComponent(
                        id="mine_head",
                        kind=FacilityComponentKind.EXTRACTOR_HEAD,
                        outputs={CargoType.ORE: 12},
                        ports={
                            "ore_out": _facility_port(
                                "ore_out",
                                PortDirection.OUTPUT,
                                CargoType.ORE,
                                rate=12,
                                capacity=24,
                            )
                        },
                        power_required=8,
                    ),
                    "mine_storage": FacilityComponent(
                        id="mine_storage",
                        kind=FacilityComponentKind.STORAGE_BAY,
                        capacity=220,
                        ports={
                            "ore_in": _facility_port(
                                "ore_in",
                                PortDirection.INPUT,
                                CargoType.ORE,
                                rate=12,
                            ),
                            "ore_out": _facility_port(
                                "ore_out",
                                PortDirection.OUTPUT,
                                CargoType.ORE,
                                rate=24,
                            ),
                        },
                    ),
                }
            ),
            layout_x=-180.0,
            layout_y=118.0,
        )
    )

    state.add_node(
        NetworkNode(
            id="atlas_local_refinery",
            name="Atlas Tutorial Refinery Station",
            world_id="atlas",
            kind=NodeKind.INDUSTRY,
            storage_capacity=260,
            transfer_limit_per_tick=24,
            requires_facility_handling=True,
            facility=Facility(
                components={
                    "refinery_storage": FacilityComponent(
                        id="refinery_storage",
                        kind=FacilityComponentKind.STORAGE_BAY,
                        capacity=260,
                        ports={
                            "ore_out": _facility_port(
                                "ore_out",
                                PortDirection.OUTPUT,
                                CargoType.ORE,
                                rate=20,
                            ),
                            "metal_in": _facility_port(
                                "metal_in",
                                PortDirection.INPUT,
                                CargoType.METAL,
                                rate=20,
                            ),
                        },
                    ),
                    "refinery_block": FacilityComponent(
                        id="refinery_block",
                        kind=FacilityComponentKind.REFINERY,
                        inputs={CargoType.ORE: 20},
                        outputs={CargoType.METAL: 20},
                        ports={
                            "ore_in": _facility_port(
                                "ore_in",
                                PortDirection.INPUT,
                                CargoType.ORE,
                                rate=20,
                                capacity=20,
                            ),
                            "metal_out": _facility_port(
                                "metal_out",
                                PortDirection.OUTPUT,
                                CargoType.METAL,
                                rate=20,
                                capacity=20,
                            ),
                        },
                        power_required=22,
                    ),
                }
            ),
            layout_x=-60.0,
            layout_y=92.0,
        )
    )

    state.add_node(
        NetworkNode(
            id="atlas_gateworks",
            name="Atlas Tutorial Gateworks",
            world_id="atlas",
            kind=NodeKind.INDUSTRY,
            inventory={CargoType.ELECTRONICS: 4},
            storage_capacity=320,
            transfer_limit_per_tick=24,
            requires_facility_handling=True,
            facility=Facility(
                components={
                    "gateworks_unloader": FacilityComponent(
                        id="gateworks_unloader",
                        kind=FacilityComponentKind.UNLOADER,
                        rate=24,
                        power_required=4,
                    ),
                    "gateworks_loader": FacilityComponent(
                        id="gateworks_loader",
                        kind=FacilityComponentKind.LOADER,
                        rate=12,
                        power_required=4,
                    ),
                    "gateworks_storage": FacilityComponent(
                        id="gateworks_storage",
                        kind=FacilityComponentKind.STORAGE_BAY,
                        capacity=320,
                        ports={
                            "metal_out": _facility_port(
                                "metal_out",
                                PortDirection.OUTPUT,
                                CargoType.METAL,
                                rate=20,
                            ),
                            "machinery_in": _facility_port(
                                "machinery_in",
                                PortDirection.INPUT,
                                CargoType.MACHINERY,
                                rate=4,
                            ),
                            "machinery_out": _facility_port(
                                "machinery_out",
                                PortDirection.OUTPUT,
                                CargoType.MACHINERY,
                                rate=4,
                            ),
                            "components_in": _facility_port(
                                "components_in",
                                PortDirection.INPUT,
                                CargoType.GATE_COMPONENTS,
                                rate=4,
                            ),
                        },
                    ),
                    "gateworks_machinery_fabricator": FacilityComponent(
                        id="gateworks_machinery_fabricator",
                        kind=FacilityComponentKind.FABRICATOR,
                        inputs={CargoType.METAL: 10},
                        outputs={CargoType.MACHINERY: 4},
                        ports={
                            "metal_in": _facility_port(
                                "metal_in",
                                PortDirection.INPUT,
                                CargoType.METAL,
                                rate=10,
                                capacity=10,
                            ),
                            "machinery_out": _facility_port(
                                "machinery_out",
                                PortDirection.OUTPUT,
                                CargoType.MACHINERY,
                                rate=4,
                                capacity=4,
                            ),
                        },
                        power_required=16,
                    ),
                    "gateworks_fabricator": FacilityComponent(
                        id="gateworks_fabricator",
                        kind=FacilityComponentKind.FABRICATOR,
                        inputs={CargoType.METAL: 10, CargoType.MACHINERY: 4},
                        outputs={CargoType.GATE_COMPONENTS: 4},
                        ports={
                            "metal_in": _facility_port(
                                "metal_in",
                                PortDirection.INPUT,
                                CargoType.METAL,
                                rate=10,
                                capacity=10,
                            ),
                            "machinery_in": _facility_port(
                                "machinery_in",
                                PortDirection.INPUT,
                                CargoType.MACHINERY,
                                rate=4,
                                capacity=4,
                            ),
                            "components_out": _facility_port(
                                "components_out",
                                PortDirection.OUTPUT,
                                CargoType.GATE_COMPONENTS,
                                rate=4,
                                capacity=4,
                            ),
                        },
                        power_required=20,
                    ),
                },
                connections={
                    "wire_gateworks_metal": _facility_connection(
                        "wire_gateworks_metal",
                        "gateworks_storage",
                        "metal_out",
                        "gateworks_fabricator",
                        "metal_in",
                    ),
                    "wire_gateworks_machinery_metal": _facility_connection(
                        "wire_gateworks_machinery_metal",
                        "gateworks_storage",
                        "metal_out",
                        "gateworks_machinery_fabricator",
                        "metal_in",
                    ),
                    "wire_gateworks_machinery_store": _facility_connection(
                        "wire_gateworks_machinery_store",
                        "gateworks_machinery_fabricator",
                        "machinery_out",
                        "gateworks_storage",
                        "machinery_in",
                    ),
                    "wire_gateworks_machinery_input": _facility_connection(
                        "wire_gateworks_machinery_input",
                        "gateworks_storage",
                        "machinery_out",
                        "gateworks_fabricator",
                        "machinery_in",
                    ),
                    "wire_gateworks_components": _facility_connection(
                        "wire_gateworks_components",
                        "gateworks_fabricator",
                        "components_out",
                        "gateworks_storage",
                        "components_in",
                    ),
                },
            ),
            layout_x=86.0,
            layout_y=86.0,
        )
    )

    state.add_node(
        NetworkNode(
            id="atlas_local_outbound_gate",
            name="Atlas Tutorial Outbound Railgate Terminal",
            world_id="atlas",
            kind=NodeKind.GATE_HUB,
            storage_capacity=240,
            transfer_limit_per_tick=24,
            requires_facility_handling=True,
            facility=Facility(
                components={
                    "outbound_unloader": FacilityComponent(
                        id="outbound_unloader",
                        kind=FacilityComponentKind.UNLOADER,
                        rate=12,
                        power_required=4,
                    ),
                    "outbound_storage": FacilityComponent(
                        id="outbound_storage",
                        kind=FacilityComponentKind.WAREHOUSE_BAY,
                        capacity=240,
                        power_required=4,
                    ),
                    "outbound_gate_interface": FacilityComponent(
                        id="outbound_gate_interface",
                        kind=FacilityComponentKind.GATE_INTERFACE,
                        rate=4,
                        power_required=30,
                    ),
                }
            ),
            layout_x=210.0,
            layout_y=18.0,
        )
    )
    state.add_construction_project(
        ConstructionProject(
            id="proj_atlas_local_outbound_gate",
            target_node_id="atlas_local_outbound_gate",
            required_cargo={CargoType.GATE_COMPONENTS: 4},
        )
    )

    state.add_node(
        NetworkNode(
            id="sable_gate_anchor",
            name="Sable Reach Receiving Anchor",
            world_id="sable",
            kind=NodeKind.GATE_HUB,
            storage_capacity=300,
            transfer_limit_per_tick=20,
            layout_x=-80.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="sable_settlement",
            name="Sable Starter Logistics Camp",
            world_id="sable",
            kind=NodeKind.SETTLEMENT,
            storage_capacity=360,
            transfer_limit_per_tick=20,
            requires_facility_handling=True,
            facility=Facility(
                components={
                    "sable_unloader": FacilityComponent(
                        id="sable_unloader",
                        kind=FacilityComponentKind.UNLOADER,
                        rate=20,
                        power_required=4,
                    ),
                    "sable_storage": FacilityComponent(
                        id="sable_storage",
                        kind=FacilityComponentKind.WAREHOUSE_BAY,
                        capacity=360,
                        power_required=4,
                    ),
                }
            ),
            layout_x=80.0,
            layout_y=80.0,
        )
    )

    state.add_link(
        NetworkLink(
            id="rail_atlas_depot_outbound_gate",
            origin="atlas_depot",
            destination="atlas_local_outbound_gate",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=24,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_sable_anchor_settlement",
            origin="sable_gate_anchor",
            destination="sable_settlement",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=20,
        )
    )

    state.add_space_site(
        SpaceSite(
            id="site_sable_reach",
            name="Sable Reach Corridor Survey",
            resource_id="gate_reactive_isotope",
            travel_ticks=4,
            base_yield=1,
            discovered=False,
        )
    )

    state.add_train(
        FreightTrain(
            id="local_ore_runner",
            name="Local Ore Runner",
            node_id="atlas_local_mine",
            capacity=20,
            consist=TrainConsist.BULK_HOPPER,
        )
    )
    state.add_train(
        FreightTrain(
            id="local_metal_runner",
            name="Local Metal Runner",
            node_id="atlas_local_refinery",
            capacity=20,
            consist=TrainConsist.GENERAL,
        )
    )
    state.add_train(
        FreightTrain(
            id="local_component_runner",
            name="Local Railgate Component Runner",
            node_id="atlas_gateworks",
            capacity=4,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_train(
        FreightTrain(
            id="local_starter_runner",
            name="Local Starter Freight Runner",
            node_id="atlas_depot",
            capacity=40,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )

    state.add_contract(
        Contract(
            id="local_sable_starter_cargo",
            kind=ContractKind.CARGO_DELIVERY,
            title="Sable Reach Starter Freight",
            client="Sable Reach Charter Combine",
            destination_node_id="sable_settlement",
            cargo_type=CargoType.CONSTRUCTION_MATERIALS,
            target_units=40,
            due_tick=900,
            reward_cash=30_000.0,
            penalty_cash=0.0,
            reward_reputation=6,
            penalty_reputation=0,
        )
    )

    return state


def build_early_build_scenario() -> GameState:
    """Build a sparse early-game sandbox for construction and first-route tests."""

    state = GameState()
    state.finance.cash = 3_200.0
    state.add_world(
        WorldState(
            id="core",
            name="Vesta Core",
            tier=DevelopmentTier.CORE_WORLD,
            population=8_500_000,
            stability=0.97,
            power_available=520,
            power_used=210,
            specialization="manufacturing",
        )
    )
    state.add_world(
        WorldState(
            id="frontier",
            name="Brink Frontier",
            tier=DevelopmentTier.OUTPOST,
            population=4_200,
            stability=0.64,
            power_available=95,
            power_used=42,
            specialization="starter_colony",
        )
    )

    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_starter_iron",
            world_id="frontier",
            resource_id="iron_rich_ore",
            name="Starter Ridge Iron",
            grade=0.52,
            yield_per_tick=2,
            remaining_estimate=4_500,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="frontier_starter_silica",
            world_id="frontier",
            resource_id="silica_sand",
            name="Starter Glass Flats",
            grade=0.46,
            yield_per_tick=1,
            remaining_estimate=3_200,
        )
    )

    state.add_node(
        NetworkNode(
            id="core_yard",
            name="Vesta Starter Rail Yard",
            world_id="core",
            kind=NodeKind.DEPOT,
            inventory={
                CargoType.FOOD: 42,
                CargoType.CONSTRUCTION_MATERIALS: 28,
                CargoType.MACHINERY: 6,
                CargoType.PARTS: 4,
            },
            production={CargoType.FOOD: 2},
            storage_capacity=240,
            transfer_limit_per_tick=12,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="core_gate",
            name="Vesta Starter Railgate Anchor",
            world_id="core",
            kind=NodeKind.GATE_HUB,
            storage_capacity=160,
            transfer_limit_per_tick=10,
            layout_x=116.0,
            layout_y=18.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_gate",
            name="Brink Starter Railgate Terminal",
            world_id="frontier",
            kind=NodeKind.GATE_HUB,
            storage_capacity=140,
            transfer_limit_per_tick=10,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_landing",
            name="Brink Starter Colony Logistics Hub",
            world_id="frontier",
            kind=NodeKind.SETTLEMENT,
            inventory={CargoType.FOOD: 6, CargoType.CONSTRUCTION_MATERIALS: 3},
            demand={CargoType.FOOD: 1, CargoType.CONSTRUCTION_MATERIALS: 1},
            stock_targets={CargoType.FOOD: 18, CargoType.CONSTRUCTION_MATERIALS: 14},
            storage_capacity=130,
            transfer_limit_per_tick=8,
            layout_x=98.0,
            layout_y=62.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="frontier_starter_pit",
            name="Starter Ridge Pit",
            world_id="frontier",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=120,
            transfer_limit_per_tick=6,
            layout_x=-84.0,
            layout_y=118.0,
            resource_deposit_id="frontier_starter_iron",
        )
    )

    state.add_link(
        NetworkLink(
            id="rail_core_yard_gate",
            origin="core_yard",
            destination="core_gate",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=12,
            alignment=(TrackPoint(44.0, -12.0), TrackPoint(88.0, 12.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_core_frontier",
            origin="core_gate",
            destination="frontier_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=18,
            power_required=65,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_gate_landing",
            origin="frontier_gate",
            destination="frontier_landing",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(34.0, 18.0), TrackPoint(76.0, 54.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_frontier_landing_pit",
            origin="frontier_landing",
            destination="frontier_starter_pit",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=6,
            alignment=(TrackPoint(52.0, 86.0), TrackPoint(-32.0, 112.0)),
        )
    )

    state.add_train(
        FreightTrain(
            id="pathfinder",
            name="Pathfinder",
            node_id="core_yard",
            capacity=10,
            dispatch_cost=35.0,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="starter_food_service",
            train_id="pathfinder",
            origin="core_yard",
            destination="frontier_landing",
            cargo_type=CargoType.FOOD,
            units_per_departure=6,
            interval_ticks=8,
            next_departure_tick=1,
            priority=90,
            active=False,
        )
    )
    return state


def build_industrial_expansion_scenario() -> GameState:
    """Build a larger connected industry sandbox for late-network stress tests."""

    state = build_sprint20_scenario()
    state.finance.cash = 24_000.0
    state.worlds["core"].power_available = 760
    state.worlds["frontier"].power_available = 135
    state.nodes["core_yard"].add_inventory(CargoType.REACTOR_PARTS, 14)
    state.nodes["core_yard"].add_inventory(CargoType.GATE_COMPONENTS, 8)

    state.add_world(
        WorldState(
            id="forge",
            name="Cinder Forge",
            tier=DevelopmentTier.INDUSTRIAL_COLONY,
            population=240_000,
            stability=0.78,
            power_available=95,
            power_used=48,
            specialization="metallurgy",
        )
    )
    state.add_world(
        WorldState(
            id="research",
            name="Helix Research Reach",
            tier=DevelopmentTier.FRONTIER_COLONY,
            population=42_000,
            stability=0.70,
            power_available=70,
            power_used=40,
            specialization="advanced_systems",
        )
    )

    state.add_resource_deposit(
        ResourceDeposit(
            id="forge_bauxite_basin",
            world_id="forge",
            resource_id="bauxite",
            name="Cinder Bauxite Basin",
            grade=0.68,
            yield_per_tick=5,
            remaining_estimate=14_000,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="forge_carbon_stack",
            world_id="forge",
            resource_id="carbon_feedstock",
            name="Cinder Carbon Stack",
            grade=0.61,
            yield_per_tick=4,
            remaining_estimate=10_500,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="research_rare_earth_ridge",
            world_id="research",
            resource_id="rare_earth_concentrate",
            name="Helix Rare Earth Ridge",
            grade=0.44,
            yield_per_tick=3,
            remaining_estimate=6_800,
        )
    )
    state.add_resource_deposit(
        ResourceDeposit(
            id="research_fissile_trace",
            world_id="research",
            resource_id="fissile_ore",
            name="Helix Fissile Trace",
            grade=0.36,
            yield_per_tick=2,
            remaining_estimate=4_400,
        )
    )

    state.add_node(
        NetworkNode(
            id="forge_gate",
            name="Cinder Railgate Anchor",
            world_id="forge",
            kind=NodeKind.GATE_HUB,
            storage_capacity=420,
            transfer_limit_per_tick=18,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_yard",
            name="Cinder Assembly Yard",
            world_id="forge",
            kind=NodeKind.DEPOT,
            inventory={CargoType.METAL: 38, CargoType.CONSTRUCTION_MATERIALS: 24},
            production={CargoType.METAL: 2},
            storage_capacity=760,
            transfer_limit_per_tick=22,
            layout_x=86.0,
            layout_y=42.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_bauxite_pit",
            name="Cinder Bauxite Pit",
            world_id="forge",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=360,
            transfer_limit_per_tick=14,
            layout_x=-106.0,
            layout_y=130.0,
            resource_deposit_id="forge_bauxite_basin",
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_carbon_rig",
            name="Cinder Carbon Rig",
            world_id="forge",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=320,
            transfer_limit_per_tick=12,
            layout_x=-132.0,
            layout_y=26.0,
            resource_deposit_id="forge_carbon_stack",
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_aluminum_refinery",
            name="Cinder Aluminum Refinery",
            world_id="forge",
            kind=NodeKind.INDUSTRY,
            storage_capacity=440,
            transfer_limit_per_tick=14,
            layout_x=-24.0,
            layout_y=114.0,
            resource_recipe=ResourceRecipe(
                id="aluminum_refining",
                kind=ResourceRecipeKind.REFINING,
                inputs={"bauxite": 4},
                outputs={"aluminum": 2},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_parts_fabricator",
            name="Cinder Parts Fabricator",
            world_id="forge",
            kind=NodeKind.INDUSTRY,
            storage_capacity=460,
            transfer_limit_per_tick=14,
            layout_x=34.0,
            layout_y=104.0,
            resource_inventory={"iron": 12, "semiconductors": 6},
            resource_recipe=ResourceRecipe(
                id="parts_fabrication",
                kind=ResourceRecipeKind.FABRICATION,
                inputs={"aluminum": 1, "iron": 2},
                outputs={"parts": 2},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_gate_component_line",
            name="Cinder Aperture Control Line",
            world_id="forge",
            kind=NodeKind.INDUSTRY,
            storage_capacity=420,
            transfer_limit_per_tick=12,
            layout_x=78.0,
            layout_y=116.0,
            inventory={CargoType.GATE_COMPONENTS: 6},
            resource_inventory={"parts": 4, "semiconductors": 4, "gate_components": 4},
            resource_recipe=ResourceRecipe(
                id="forge_gate_component_fabrication",
                kind=ResourceRecipeKind.FABRICATION,
                inputs={"parts": 2, "semiconductors": 1},
                outputs={"gate_components": 1},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="forge_thermal_plant",
            name="Cinder Thermal Plant",
            world_id="forge",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"carbon_feedstock": 8},
            resource_demand={"carbon_feedstock": 1},
            storage_capacity=220,
            transfer_limit_per_tick=10,
            layout_x=-70.0,
            layout_y=30.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="research_gate",
            name="Helix Railgate Receiving Terminal",
            world_id="research",
            kind=NodeKind.GATE_HUB,
            storage_capacity=360,
            transfer_limit_per_tick=14,
            layout_x=0.0,
            layout_y=0.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="research_labs",
            name="Helix Research Yards",
            world_id="research",
            kind=NodeKind.DEPOT,
            inventory={CargoType.RESEARCH_EQUIPMENT: 12, CargoType.ELECTRONICS: 18},
            storage_capacity=520,
            transfer_limit_per_tick=16,
            layout_x=82.0,
            layout_y=46.0,
        )
    )
    state.add_node(
        NetworkNode(
            id="research_rare_earth_pit",
            name="Helix Rare Earth Pit",
            world_id="research",
            kind=NodeKind.EXTRACTOR,
            storage_capacity=280,
            transfer_limit_per_tick=10,
            layout_x=-84.0,
            layout_y=112.0,
            resource_deposit_id="research_rare_earth_ridge",
        )
    )
    state.add_node(
        NetworkNode(
            id="research_chip_line",
            name="Helix Chip Line",
            world_id="research",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"electronics": 6, "silicon": 6},
            storage_capacity=360,
            transfer_limit_per_tick=12,
            layout_x=34.0,
            layout_y=126.0,
            resource_recipe=ResourceRecipe(
                id="helix_semiconductor_line",
                kind=ResourceRecipeKind.SEMICONDUCTOR,
                inputs={"electronics": 1, "rare_earth_concentrate": 1, "silicon": 1},
                outputs={"semiconductors": 2},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="research_reactor_shop",
            name="Helix Reactor Shop",
            world_id="research",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"electronics": 4, "uranium": 8},
            storage_capacity=360,
            transfer_limit_per_tick=12,
            layout_x=82.0,
            layout_y=122.0,
            resource_recipe=ResourceRecipe(
                id="reactor_parts_fabrication",
                kind=ResourceRecipeKind.FABRICATION,
                inputs={"electronics": 1, "uranium": 1},
                outputs={"reactor_parts": 1},
            ),
        )
    )
    state.add_node(
        NetworkNode(
            id="research_fission_plant",
            name="Helix Fission Plant",
            world_id="research",
            kind=NodeKind.INDUSTRY,
            resource_inventory={"uranium": 8},
            resource_demand={"uranium": 1},
            storage_capacity=180,
            transfer_limit_per_tick=8,
            layout_x=122.0,
            layout_y=78.0,
        )
    )

    state.add_link(
        NetworkLink(
            id="gate_core_forge",
            origin="core_gate",
            destination="forge_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=18,
            power_required=90,
            power_source_world_id="core",
        )
    )
    state.add_link(
        NetworkLink(
            id="gate_forge_research",
            origin="forge_gate",
            destination="research_gate",
            mode=LinkMode.GATE,
            travel_ticks=1,
            capacity_per_tick=14,
            power_required=80,
            power_source_world_id="forge",
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_gate_yard",
            origin="forge_gate",
            destination="forge_yard",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=18,
            alignment=(TrackPoint(28.0, 8.0), TrackPoint(68.0, 36.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_yard_bauxite",
            origin="forge_yard",
            destination="forge_bauxite_pit",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=12,
            alignment=(TrackPoint(42.0, 76.0), TrackPoint(-56.0, 128.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_bauxite_refinery",
            origin="forge_bauxite_pit",
            destination="forge_aluminum_refinery",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
            alignment=(TrackPoint(-82.0, 128.0), TrackPoint(-44.0, 118.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_carbon_power",
            origin="forge_carbon_rig",
            destination="forge_thermal_plant",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=8,
            alignment=(TrackPoint(-116.0, 28.0), TrackPoint(-88.0, 28.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_refinery_parts",
            origin="forge_aluminum_refinery",
            destination="forge_parts_fabricator",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
            alignment=(TrackPoint(-2.0, 112.0), TrackPoint(20.0, 108.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_yard_parts",
            origin="forge_yard",
            destination="forge_parts_fabricator",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=10,
            alignment=(TrackPoint(78.0, 70.0), TrackPoint(44.0, 98.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_parts_gate_components",
            origin="forge_parts_fabricator",
            destination="forge_gate_component_line",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=8,
            alignment=(TrackPoint(52.0, 110.0), TrackPoint(70.0, 116.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_forge_yard_power",
            origin="forge_yard",
            destination="forge_thermal_plant",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(44.0, 48.0), TrackPoint(-36.0, 34.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_research_gate_labs",
            origin="research_gate",
            destination="research_labs",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=14,
            alignment=(TrackPoint(28.0, 8.0), TrackPoint(64.0, 38.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_research_labs_rare_earth",
            origin="research_labs",
            destination="research_rare_earth_pit",
            mode=LinkMode.RAIL,
            travel_ticks=3,
            capacity_per_tick=8,
            alignment=(TrackPoint(44.0, 78.0), TrackPoint(-44.0, 108.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_research_labs_chip_line",
            origin="research_labs",
            destination="research_chip_line",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(70.0, 76.0), TrackPoint(48.0, 116.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_research_labs_reactor_shop",
            origin="research_labs",
            destination="research_reactor_shop",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=8,
            alignment=(TrackPoint(88.0, 74.0), TrackPoint(86.0, 112.0)),
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_research_labs_fission",
            origin="research_labs",
            destination="research_fission_plant",
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=6,
            alignment=(TrackPoint(100.0, 54.0), TrackPoint(118.0, 70.0)),
        )
    )

    state.add_power_plant(
        PowerPlant(
            id="forge_cinder_thermal",
            node_id="forge_thermal_plant",
            kind=PowerPlantKind.THERMAL,
            inputs={"carbon_feedstock": 1},
            power_output=70,
        )
    )
    state.add_power_plant(
        PowerPlant(
            id="research_helix_fission",
            node_id="research_fission_plant",
            kind=PowerPlantKind.FISSION,
            inputs={"uranium": 1},
            power_output=90,
        )
    )
    state.nodes["frontier_gate_fabricator"].add_resource_inventory("gate_components", 4)
    state.add_gate_support(
        GatePowerSupport(
            id="frontier_gate_component_support",
            link_id="gate_frontier_outer",
            node_id="frontier_gate_fabricator",
            inputs={"gate_components": 1},
            power_bonus=40,
        )
    )
    state.add_gate_support(
        GatePowerSupport(
            id="forge_gate_component_support",
            link_id="gate_core_forge",
            node_id="forge_gate_component_line",
            inputs={"gate_components": 1},
            power_bonus=55,
        )
    )

    state.add_train(
        FreightTrain(
            id="forge_runner",
            name="Forge Runner",
            node_id="forge_yard",
            capacity=24,
            consist=TrainConsist.HEAVY_FLAT,
        )
    )
    state.add_train(
        FreightTrain(
            id="research_runner",
            name="Research Runner",
            node_id="research_labs",
            capacity=12,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_train(
        FreightTrain(
            id="bridgewright",
            name="Bridgewright",
            node_id="core_yard",
            capacity=10,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_train(
        FreightTrain(
            id="stabilizer",
            name="Stabilizer",
            node_id="forge_gate_component_line",
            capacity=8,
            consist=TrainConsist.PROTECTED,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="core_reactor_parts_to_helix",
            train_id="bridgewright",
            origin="core_yard",
            destination="research_labs",
            cargo_type=CargoType.REACTOR_PARTS,
            units_per_departure=4,
            interval_ticks=14,
            priority=94,
            stops=("forge_yard",),
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="forge_metal_to_core",
            train_id="forge_runner",
            origin="forge_yard",
            destination="core_yard",
            cargo_type=CargoType.METAL,
            units_per_departure=10,
            interval_ticks=10,
            priority=82,
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="helix_research_to_ashfall",
            train_id="research_runner",
            origin="research_labs",
            destination="outer_outpost",
            cargo_type=CargoType.RESEARCH_EQUIPMENT,
            units_per_departure=3,
            interval_ticks=12,
            priority=86,
            stops=("core_gate", "frontier_outer_gate"),
        )
    )
    state.add_schedule(
        FreightSchedule(
            id="forge_gate_components_to_frontier",
            train_id="stabilizer",
            origin="forge_gate_component_line",
            destination="frontier_gate",
            cargo_type=CargoType.GATE_COMPONENTS,
            units_per_departure=2,
            interval_ticks=18,
            priority=96,
            stops=("core_gate",),
        )
    )
    return state


def scenario_definitions() -> tuple[ScenarioDefinition, ...]:
    """Return all built-in scenarios in roadmap order."""

    return (
        ScenarioDefinition(
            key="sprint1",
            aliases=("foundation",),
            title="Railgate Age Foundation",
            description="Two-world logistics graph with production, demand, rail, and one route-bound Railgate corridor.",
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
            title="Railgate Pressure and Expansion",
            description="An extraction outpost depends on a frontier-powered derivative aperture corridor.",
            builder=build_sprint4_scenario,
        ),
        ScenarioDefinition(
            key="sprint5",
            aliases=("stage1", "operations"),
            title="Stage 1 Operations Ledger",
            description="Recurring schedules, Railgate slots, finance, stockpiles, and monthly tables.",
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
            title="Railgate Corridor Recovery",
            description="Sprint 8 with a full Railgate outage and a GATE_RECOVERY contract to restore it.",
            builder=build_sprint9_recovery_scenario,
        ),
        ScenarioDefinition(
            key="sprint19",
            aliases=("power", "gate_power", "resource_power"),
            title="Resource-backed Railgate Power",
            description="A frontier Railgate recovers when upstream industry fabricates aperture control components.",
            builder=build_sprint19_scenario,
        ),
        ScenarioDefinition(
            key="sprint19b",
            aliases=("power_generation", "plants", "generation"),
            title="Resource-backed Power Generation",
            description="A carbon-fed thermal plant adds generated world power before Railgate operation.",
            builder=build_sprint19b_scenario,
        ),
        ScenarioDefinition(
            key="sprint20",
            aliases=("space", "extraction", "orbital"),
            title="Space Extraction Logistics",
            description="Orbital stations extract resources from remote space sites via mining missions.",
            builder=build_sprint20_scenario,
        ),
        ScenarioDefinition(
            key="early_build",
            aliases=("early", "starter", "new_game"),
            title="Early Build Sandbox",
            description="Sparse two-world start with limited cash, starter materials, and one inactive route.",
            builder=build_early_build_scenario,
        ),
        ScenarioDefinition(
            key="industrial_expansion",
            aliases=("industrial", "expanded", "large_industry"),
            title="Industrial Expansion Web",
            description="Large connected industry sandbox with extra Railgate corridors, power, recipes, and multi-stop services.",
            builder=build_industrial_expansion_scenario,
        ),
        ScenarioDefinition(
            key="mining_to_manufacturing",
            aliases=("mining_loop", "mine_to_factory", "loop_demo"),
            title="Mining-to-Manufacturing Loop",
            description="Mine ore in space, ferry it through a Railgate corridor, and feed a manufacturing recipe end to end.",
            builder=build_mining_to_manufacturing_scenario,
        ),
        ScenarioDefinition(
            key="tutorial_six_worlds",
            aliases=("tutorial_start", "six_world_tutorial", "starter_ring"),
            title="Railgate Age Tutorial Start",
            description="Tutorial corridor with local manufacturing, aperture components, destination survey, and a second-world Railgate shipment.",
            builder=build_tutorial_six_worlds_scenario,
        ),
        ScenarioDefinition(
            key="tutorial_local_logistics",
            aliases=("local_logistics", "bottom_up_logistics", "railgate_bootstrap"),
            title="Bottom-Up Local Logistics Tutorial",
            description="Build tracks, loaders, unloaders, internal transfer links, factory flow, and then feed a new Railgate corridor.",
            builder=build_tutorial_local_logistics_scenario,
        ),
    )


def load_scenario(name: str = DEFAULT_SCENARIO) -> GameState:
    """Load a named built-in scenario."""

    normalized = name.strip().lower()
    for definition in scenario_definitions():
        if normalized in {definition.key, *definition.aliases}:
            return definition.builder()
    raise ValueError(f"unknown scenario: {name}")
