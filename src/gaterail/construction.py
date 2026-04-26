"""Construction defaults and cost rules for player-built infrastructure."""

from __future__ import annotations

from gaterail.models import FacilityComponentKind, LinkMode, NodeKind


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
}


NODE_DEFAULT_STORAGE: dict[NodeKind, int] = {
    NodeKind.SETTLEMENT: 1_000,
    NodeKind.DEPOT: 2_000,
    NodeKind.WAREHOUSE: 4_000,
    NodeKind.EXTRACTOR: 1_000,
    NodeKind.INDUSTRY: 1_000,
    NodeKind.GATE_HUB: 1_500,
}


NODE_DEFAULT_TRANSFER: dict[NodeKind, int] = {
    NodeKind.SETTLEMENT: 24,
    NodeKind.DEPOT: 36,
    NodeKind.WAREHOUSE: 48,
    NodeKind.EXTRACTOR: 24,
    NodeKind.INDUSTRY: 24,
    NodeKind.GATE_HUB: 30,
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
}


def facility_component_build_cost(kind: FacilityComponentKind) -> float:
    """Return the cash cost to install a facility component."""

    return FACILITY_COMPONENT_BUILD_COST[kind]
