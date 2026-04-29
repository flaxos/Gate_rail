"""Construction defaults and cost rules for player-built infrastructure."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.models import ConstructionStatus, FacilityComponentKind, FacilityPort, LinkMode, NodeKind, PortDirection


DEFAULT_RAIL_CAPACITY_PER_TICK = 24
DEFAULT_GATE_CAPACITY_PER_TICK = 4
DEFAULT_GATE_POWER_REQUIRED = 80
DEFAULT_GATE_TRAVEL_TICKS = 1
LOCAL_LAYOUT_UNITS_PER_TRAVEL_TICK = 50.0


NODE_BUILD_COST: dict[NodeKind, float] = {
    NodeKind.SETTLEMENT: 800.0,
    NodeKind.DEPOT: 1_200.0,
    NodeKind.WAREHOUSE: 1_600.0,
    NodeKind.EXTRACTOR: 1_500.0,
    NodeKind.INDUSTRY: 2_000.0,
    NodeKind.GATE_HUB: 8_000.0,
    NodeKind.SPACEPORT: 3_000.0,
}


NODE_DEFAULT_STORAGE: dict[NodeKind, int] = {
    NodeKind.SETTLEMENT: 1_000,
    NodeKind.DEPOT: 2_000,
    NodeKind.WAREHOUSE: 4_000,
    NodeKind.EXTRACTOR: 1_000,
    NodeKind.INDUSTRY: 1_000,
    NodeKind.GATE_HUB: 1_500,
    NodeKind.SPACEPORT: 2_000,
}


NODE_DEFAULT_TRANSFER: dict[NodeKind, int] = {
    NodeKind.SETTLEMENT: 24,
    NodeKind.DEPOT: 36,
    NodeKind.WAREHOUSE: 48,
    NodeKind.EXTRACTOR: 24,
    NodeKind.INDUSTRY: 24,
    NodeKind.GATE_HUB: 30,
    NodeKind.SPACEPORT: 24,
}


NODE_BUILD_CARGO: dict[NodeKind, dict[CargoType, int]] = {
    NodeKind.SETTLEMENT: {
        CargoType.CONSTRUCTION_MATERIALS: 50,
        CargoType.FOOD: 100,
        CargoType.WATER: 100,
    },
    NodeKind.SPACEPORT: {
        CargoType.METAL: 200,
        CargoType.ELECTRONICS: 50,
        CargoType.WATER: 50,
    },
}


def node_build_cost(kind: NodeKind) -> float:
    """Return the cash cost to build a node of ``kind``."""

    return NODE_BUILD_COST[kind]


def node_default_storage(kind: NodeKind) -> int:
    """Return the default storage capacity for a freshly built node."""

    return NODE_DEFAULT_STORAGE[kind]


def node_default_transfer(kind: NodeKind) -> int:
    """Return the default per-tick transfer limit for a freshly built node."""

    return NODE_DEFAULT_TRANSFER[kind]


def node_build_cargo(kind: NodeKind) -> dict[CargoType, int]:
    """Return the required cargo to construct a node of ``kind``."""

    return NODE_BUILD_CARGO.get(kind, {})


def link_build_cost(mode: LinkMode, travel_ticks: int) -> float:
    """Return the cash cost to build a transport link."""

    if mode == LinkMode.GATE:
        return 10_000.0
    return 150.0 * travel_ticks


def link_build_time(travel_ticks: int) -> int:
    """Return immediate-mode build-time metadata for a link."""

    return travel_ticks * 2


def travel_ticks_from_layout_distance(distance: float) -> int:
    """Estimate rail travel ticks from local-world layout distance."""

    return max(1, int(round(distance / LOCAL_LAYOUT_UNITS_PER_TRAVEL_TICK)))


def train_purchase_cost(capacity: int) -> float:
    """Return the cash cost to purchase a train."""

    return 500.0 + (capacity * 20.0)


def node_upgrade_cost(storage_increase: int, transfer_increase: int) -> float:
    """Return the cash cost to upgrade a node."""

    return (storage_increase * 0.5) + (transfer_increase * 25.0)


FACILITY_COMPONENT_BUILD_COST: dict[FacilityComponentKind, float] = {
    FacilityComponentKind.PLATFORM: 800.0,
    FacilityComponentKind.LOADER: 1_200.0,
    FacilityComponentKind.UNLOADER: 1_200.0,
    FacilityComponentKind.STORAGE_BAY: 1_500.0,
    FacilityComponentKind.FACTORY_BLOCK: 2_500.0,
    FacilityComponentKind.POWER_MODULE: 1_800.0,
    FacilityComponentKind.GATE_INTERFACE: 4_000.0,
    FacilityComponentKind.WAREHOUSE_BAY: 2_200.0,
    FacilityComponentKind.EXTRACTOR_HEAD: 1_800.0,
    FacilityComponentKind.CRUSHER: 1_700.0,
    FacilityComponentKind.SORTER: 1_500.0,
    FacilityComponentKind.SMELTER: 2_800.0,
    FacilityComponentKind.REFINERY: 3_200.0,
    FacilityComponentKind.CHEMICAL_PROCESSOR: 3_000.0,
    FacilityComponentKind.FABRICATOR: 2_700.0,
    FacilityComponentKind.ELECTRONICS_ASSEMBLER: 3_500.0,
    FacilityComponentKind.SEMICONDUCTOR_LINE: 5_000.0,
    FacilityComponentKind.REACTOR: 6_000.0,
    FacilityComponentKind.CAPACITOR_BANK: 4_000.0,
}

FACILITY_COMPONENT_DEFAULT_POWER_PROVIDED: dict[FacilityComponentKind, int] = {
    FacilityComponentKind.POWER_MODULE: 80,
    FacilityComponentKind.REACTOR: 250,
}

FACILITY_COMPONENT_DEFAULT_POWER_REQUIRED: dict[FacilityComponentKind, int] = {
    FacilityComponentKind.WAREHOUSE_BAY: 4,
    FacilityComponentKind.EXTRACTOR_HEAD: 8,
    FacilityComponentKind.CRUSHER: 10,
    FacilityComponentKind.SORTER: 8,
    FacilityComponentKind.SMELTER: 18,
    FacilityComponentKind.REFINERY: 22,
    FacilityComponentKind.CHEMICAL_PROCESSOR: 20,
    FacilityComponentKind.FABRICATOR: 16,
    FacilityComponentKind.ELECTRONICS_ASSEMBLER: 24,
    FacilityComponentKind.SEMICONDUCTOR_LINE: 40,
    FacilityComponentKind.REACTOR: 0,
    FacilityComponentKind.CAPACITOR_BANK: 0,
}

FACILITY_COMPONENT_BUILD_CARGO: dict[FacilityComponentKind, dict[CargoType, int]] = {
    FacilityComponentKind.SEMICONDUCTOR_LINE: {
        CargoType.ELECTRONICS: 8,
        CargoType.PARTS: 6,
    },
    FacilityComponentKind.REACTOR: {
        CargoType.REACTOR_PARTS: 12,
        CargoType.METAL: 24,
    },
}

FACILITY_COMPONENT_DEFAULT_TRAIN_CAPACITY: dict[FacilityComponentKind, int] = {
    FacilityComponentKind.PLATFORM: 1,
}

FACILITY_COMPONENT_DEFAULT_CONCURRENT_LOADING_LIMIT: dict[FacilityComponentKind, int] = {
    FacilityComponentKind.PLATFORM: 1,
}

FACILITY_COMPONENT_DEFAULT_DISCHARGE_PER_TICK: dict[FacilityComponentKind, int] = {
    FacilityComponentKind.CAPACITOR_BANK: 10,
}

# Default port templates per component kind.
# Each entry is a list of (port_id_suffix, direction, rate) tuples.
# Port ids are generated as f"{kind.value}_{suffix}_{component_id}" at install time,
# but the template here uses simple suffixes; callers must assign real ids.
_DEFAULT_PORT_TEMPLATES: dict[FacilityComponentKind, list[tuple[str, PortDirection, int]]] = {
    FacilityComponentKind.FACTORY_BLOCK: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.EXTRACTOR_HEAD: [
        ("out", PortDirection.OUTPUT, 6),
    ],
    FacilityComponentKind.CRUSHER: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 8),
    ],
    FacilityComponentKind.SORTER: [
        ("in", PortDirection.INPUT, 8),
        ("out_a", PortDirection.OUTPUT, 4),
        ("out_b", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.SMELTER: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.REFINERY: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.CHEMICAL_PROCESSOR: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.FABRICATOR: [
        ("in", PortDirection.INPUT, 8),
        ("out", PortDirection.OUTPUT, 4),
    ],
    FacilityComponentKind.ELECTRONICS_ASSEMBLER: [
        ("in", PortDirection.INPUT, 6),
        ("out", PortDirection.OUTPUT, 3),
    ],
    FacilityComponentKind.SEMICONDUCTOR_LINE: [
        ("in", PortDirection.INPUT, 4),
        ("out", PortDirection.OUTPUT, 2),
    ],
    FacilityComponentKind.REACTOR: [
        ("fuel", PortDirection.INPUT, 2),
    ],
}


def facility_component_build_cost(kind: FacilityComponentKind) -> float:
    """Return the cash cost to install a facility component."""

    return FACILITY_COMPONENT_BUILD_COST[kind]


def facility_component_default_power_provided(kind: FacilityComponentKind) -> int:
    """Return the default power_provided value for a component kind."""

    return FACILITY_COMPONENT_DEFAULT_POWER_PROVIDED.get(kind, 0)


def facility_component_default_power_required(kind: FacilityComponentKind) -> int:
    """Return the default power_required value for a component kind."""

    return FACILITY_COMPONENT_DEFAULT_POWER_REQUIRED.get(kind, 0)


def facility_component_build_cargo(kind: FacilityComponentKind) -> dict[CargoType, int]:
    """Return any cargo consumed immediately when installing a component kind."""

    return dict(FACILITY_COMPONENT_BUILD_CARGO.get(kind, {}))


def facility_component_default_train_capacity(kind: FacilityComponentKind) -> int:
    """Return the default train_capacity value for one component kind."""

    return FACILITY_COMPONENT_DEFAULT_TRAIN_CAPACITY.get(kind, 0)


def facility_component_default_concurrent_loading_limit(kind: FacilityComponentKind) -> int:
    """Return the default concurrent-loading limit for one component kind."""

    return FACILITY_COMPONENT_DEFAULT_CONCURRENT_LOADING_LIMIT.get(kind, 1)


def facility_component_default_discharge_per_tick(kind: FacilityComponentKind) -> int:
    """Return the default capacitor discharge rate for one component kind."""

    return FACILITY_COMPONENT_DEFAULT_DISCHARGE_PER_TICK.get(kind, 0)


def facility_component_default_ports(kind: FacilityComponentKind, component_id: str) -> list[FacilityPort]:
    """Return default FacilityPort instances for a component kind, using component_id to namespace port ids."""

    template = _DEFAULT_PORT_TEMPLATES.get(kind, [])
    return [
        FacilityPort(
            id=f"{suffix}_{component_id}",
            direction=direction,
            rate=rate,
        )
        for suffix, direction, rate in template
    ]


def apply_construction_projects(state: object) -> dict[str, dict[str, int]]:
    """Transfer cargo from node inventory into active construction projects."""

    progress_report: dict[str, dict[str, int]] = {}

    for project in list(getattr(state, "construction_projects", {}).values()):
        if project.status == ConstructionStatus.COMPLETED:
            continue
            
        node = getattr(state, "nodes", {}).get(project.target_node_id)
        if not node:
            continue

        if project.status == ConstructionStatus.PENDING:
            project.status = ConstructionStatus.ACTIVE

        project_progress: dict[str, int] = {}
        for cargo, remaining in project.remaining_cargo.items():
            if remaining <= 0:
                continue
                
            available = node.inventory.get(cargo, 0)
            if available > 0:
                transfer_amount = min(available, remaining)
                node.inventory[cargo] -= transfer_amount
                project.delivered_cargo[cargo] = project.delivered_cargo.get(cargo, 0) + transfer_amount
                project_progress[cargo.value] = transfer_amount

        if project_progress:
            progress_report[project.id] = project_progress

        if project.is_completed:
            project.status = ConstructionStatus.COMPLETED
            node.construction_project_id = None

    return progress_report
