"""Canonical game state models for the fixed-tick GateRail backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

from gaterail.cargo import CargoType


class DevelopmentTier(IntEnum):
    """World development ladder."""

    OUTPOST = 0
    FRONTIER_COLONY = 1
    INDUSTRIAL_COLONY = 2
    DEVELOPED_WORLD = 3
    CORE_WORLD = 4


class NodeKind(StrEnum):
    """Network node roles."""

    SETTLEMENT = "settlement"
    DEPOT = "depot"
    WAREHOUSE = "warehouse"
    EXTRACTOR = "extractor"
    INDUSTRY = "industry"
    GATE_HUB = "gate_hub"


class LinkMode(StrEnum):
    """Transport link types."""

    RAIL = "rail"
    GATE = "gate"


class TrainStatus(StrEnum):
    """Fixed-tick freight train operating states."""

    IDLE = "idle"
    IN_TRANSIT = "in_transit"
    BLOCKED = "blocked"


class ProgressionTrend(StrEnum):
    """World development trend reported each tick."""

    IMPROVING = "improving"
    STALLED = "stalled"
    REGRESSING = "regressing"
    PROMOTED = "promoted"
    MAX_TIER = "max_tier"


class ContractKind(StrEnum):
    """Player-facing objective categories."""

    CARGO_DELIVERY = "cargo_delivery"
    FRONTIER_SUPPORT = "frontier_support"
    GATE_RECOVERY = "gate_recovery"


class ContractStatus(StrEnum):
    """Lifecycle state for a contract."""

    ACTIVE = "active"
    FULFILLED = "fulfilled"
    FAILED = "failed"


@dataclass(slots=True)
class FinanceState:
    """Fixed-tick finance ledger for Stage 1 operations."""

    cash: float = 10_000.0
    revenue_total: float = 0.0
    costs_total: float = 0.0
    revenue_this_tick: float = 0.0
    costs_this_tick: float = 0.0

    def reset_tick(self) -> None:
        """Reset daily finance rollups."""

        self.revenue_this_tick = 0.0
        self.costs_this_tick = 0.0

    def record_revenue(self, amount: float) -> None:
        """Record operating revenue."""

        if amount <= 0:
            return
        self.revenue_this_tick += amount
        self.revenue_total += amount
        self.cash += amount

    def record_cost(self, amount: float) -> None:
        """Record operating cost."""

        if amount <= 0:
            return
        self.costs_this_tick += amount
        self.costs_total += amount
        self.cash -= amount

    @property
    def net_this_tick(self) -> float:
        """Net income for the current tick."""

        return self.revenue_this_tick - self.costs_this_tick

    @property
    def net_total(self) -> float:
        """Total net income."""

        return self.revenue_total - self.costs_total

    def snapshot(self) -> dict[str, float]:
        """Return report-safe finance fields."""

        return {
            "cash": round(self.cash, 2),
            "revenue": round(self.revenue_this_tick, 2),
            "costs": round(self.costs_this_tick, 2),
            "net": round(self.net_this_tick, 2),
            "revenue_total": round(self.revenue_total, 2),
            "costs_total": round(self.costs_total, 2),
            "net_total": round(self.net_total, 2),
        }


@dataclass(slots=True)
class WorldState:
    """Strategic world state for development and power planning."""

    id: str
    name: str
    tier: DevelopmentTier
    population: int = 0
    stability: float = 1.0
    power_available: int = 0
    power_used: int = 0
    gate_power_used: int = 0
    specialization: str | None = None
    development_progress: int = 0
    support_streak: int = 0
    shortage_streak: int = 0
    last_trend: ProgressionTrend = ProgressionTrend.STALLED

    @property
    def power_margin(self) -> int:
        """Power remaining after committed infrastructure draw."""

        return self.base_power_margin - self.gate_power_used

    @property
    def base_power_margin(self) -> int:
        """Power margin before gate reservations."""

        return self.power_available - self.power_used


@dataclass(frozen=True, slots=True)
class NodeRecipe:
    """One per-node transformation: consume inputs, produce outputs each tick."""

    inputs: dict[CargoType, int] = field(default_factory=dict)
    outputs: dict[CargoType, int] = field(default_factory=dict)


class FacilityComponentKind(StrEnum):
    """Internal facility component roles."""

    PLATFORM = "platform"
    LOADER = "loader"
    UNLOADER = "unloader"
    STORAGE_BAY = "storage_bay"
    FACTORY_BLOCK = "factory_block"
    POWER_MODULE = "power_module"
    GATE_INTERFACE = "gate_interface"


class PortDirection(StrEnum):
    """Direction of cargo flow through a facility port."""

    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True)
class FacilityPort:
    """Typed input or output connector on a facility component."""

    id: str
    direction: PortDirection
    cargo_type: CargoType | None = None
    rate: int = 0
    capacity: int = 0


@dataclass(slots=True)
class FacilityComponent:
    """One component inside a facility (loader, bay, factory block, etc.)."""

    id: str
    kind: FacilityComponentKind
    ports: dict[str, FacilityPort] = field(default_factory=dict)
    capacity: int = 0
    rate: int = 0
    power_required: int = 0
    inputs: dict[CargoType, int] = field(default_factory=dict)
    outputs: dict[CargoType, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InternalConnection:
    """A wire between two ports inside one facility."""

    id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str


@dataclass(slots=True)
class Facility:
    """Internal layout owned by one NetworkNode."""

    components: dict[str, FacilityComponent] = field(default_factory=dict)
    connections: dict[str, InternalConnection] = field(default_factory=dict)

    def _components_of(self, kind: FacilityComponentKind) -> list[FacilityComponent]:
        """Return components of one kind."""

        return [component for component in self.components.values() if component.kind == kind]

    def storage_capacity_override(self) -> int | None:
        """Return summed storage-bay capacity, or None if no bays exist."""

        bays = self._components_of(FacilityComponentKind.STORAGE_BAY)
        if not bays:
            return None
        return sum(max(0, component.capacity) for component in bays)

    def loader_rate_override(self) -> int | None:
        """Return summed loader rate, or None if no loaders exist."""

        loaders = self._components_of(FacilityComponentKind.LOADER)
        if not loaders:
            return None
        return sum(max(0, component.rate) for component in loaders)

    def unloader_rate_override(self) -> int | None:
        """Return summed unloader rate, or None if no unloaders exist."""

        unloaders = self._components_of(FacilityComponentKind.UNLOADER)
        if not unloaders:
            return None
        return sum(max(0, component.rate) for component in unloaders)

    def power_required(self) -> int:
        """Return total power required by all components."""

        return sum(max(0, component.power_required) for component in self.components.values())


@dataclass(slots=True)
class NetworkNode:
    """A logistics point on a world."""

    id: str
    name: str
    world_id: str
    kind: NodeKind
    inventory: dict[CargoType, int] = field(default_factory=dict)
    production: dict[CargoType, int] = field(default_factory=dict)
    demand: dict[CargoType, int] = field(default_factory=dict)
    storage_capacity: int = 1_000
    transfer_limit_per_tick: int = 24
    layout_x: float | None = None
    layout_y: float | None = None
    recipe: NodeRecipe | None = None
    facility: Facility | None = None

    def effective_storage_capacity(self) -> int:
        """Return active storage cap, derived from facility bays when present."""

        if self.facility is not None:
            override = self.facility.storage_capacity_override()
            if override is not None:
                return override
        return self.storage_capacity

    def effective_outbound_rate(self) -> int:
        """Return active outbound transfer cap, derived from facility loaders when present."""

        if self.facility is not None:
            override = self.facility.loader_rate_override()
            if override is not None:
                return override
        return self.transfer_limit_per_tick

    def effective_inbound_rate(self) -> int:
        """Return active inbound transfer cap, derived from facility unloaders when present."""

        if self.facility is not None:
            override = self.facility.unloader_rate_override()
            if override is not None:
                return override
        return self.transfer_limit_per_tick

    def effective_combined_rate(self) -> int:
        """Return the combined per-tick transfer cap used for saturation rollups."""

        if self.facility is None:
            return self.transfer_limit_per_tick
        loader = self.facility.loader_rate_override()
        unloader = self.facility.unloader_rate_override()
        if loader is None and unloader is None:
            return self.transfer_limit_per_tick
        return max(loader or 0, unloader or 0)

    def total_inventory(self) -> int:
        """Return all stored cargo units."""

        return sum(self.inventory.values())

    def stock(self, cargo_type: CargoType) -> int:
        """Return stored units for one cargo type."""

        return self.inventory.get(cargo_type, 0)

    def add_inventory(self, cargo_type: CargoType, units: int) -> int:
        """Add cargo up to storage capacity and return accepted units."""

        if units <= 0:
            return 0
        available_space = max(0, self.effective_storage_capacity() - self.total_inventory())
        accepted = min(units, available_space)
        if accepted > 0:
            self.inventory[cargo_type] = self.stock(cargo_type) + accepted
        return accepted

    def remove_inventory(self, cargo_type: CargoType, units: int) -> int:
        """Remove cargo and return actual removed units."""

        if units <= 0:
            return 0
        removed = min(units, self.stock(cargo_type))
        if removed <= 0:
            return 0
        remaining = self.stock(cargo_type) - removed
        if remaining:
            self.inventory[cargo_type] = remaining
        else:
            self.inventory.pop(cargo_type, None)
        return removed


@dataclass(frozen=True, slots=True)
class NetworkLink:
    """A rail or gate edge between network nodes."""

    id: str
    origin: str
    destination: str
    mode: LinkMode
    travel_ticks: int
    capacity_per_tick: int
    power_required: int = 0
    power_source_world_id: str | None = None
    active: bool = True
    bidirectional: bool = True
    build_cost: float = 0.0
    build_time: int = 0

    def connects(self, node_id: str) -> bool:
        """Return whether this link touches ``node_id``."""

        return self.origin == node_id or (self.bidirectional and self.destination == node_id)

    def other_end(self, node_id: str) -> str | None:
        """Return the traversable opposite node from ``node_id``."""

        if self.origin == node_id:
            return self.destination
        if self.bidirectional and self.destination == node_id:
            return self.origin
        return None


@dataclass(frozen=True, slots=True)
class NetworkDisruption:
    """A timed capacity reduction on one network link."""

    id: str
    link_id: str
    start_tick: int
    end_tick: int
    capacity_multiplier: float = 0.0
    reason: str = "maintenance"

    def active_at(self, tick: int) -> bool:
        """Return whether the disruption applies on ``tick``."""

        return self.start_tick <= tick <= self.end_tick


@dataclass(slots=True)
class FreightTrain:
    """A fixed-tick train assigned to the logistics graph."""

    id: str
    name: str
    node_id: str
    capacity: int
    cargo_type: CargoType | None = None
    cargo_units: int = 0
    status: TrainStatus = TrainStatus.IDLE
    destination: str | None = None
    route_node_ids: tuple[str, ...] = ()
    route_link_ids: tuple[str, ...] = ()
    remaining_ticks: int = 0
    order_id: str | None = None
    blocked_reason: str | None = None
    dispatch_cost: float = 60.0
    variable_cost_per_unit: float = 1.0
    revenue_modifier: float = 1.0

    @property
    def idle(self) -> bool:
        """Whether the train can accept a new order."""

        return self.status == TrainStatus.IDLE and self.cargo_units == 0


@dataclass(slots=True)
class FreightOrder:
    """A one-shot freight movement assigned to a train."""

    id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    requested_units: int
    priority: int = 100
    delivered_units: int = 0
    active: bool = True

    @property
    def remaining_units(self) -> int:
        """Units still required to satisfy this order."""

        return max(0, self.requested_units - self.delivered_units)


@dataclass(slots=True)
class FreightSchedule:
    """Recurring freight service used by the Stage 1 operations prototype."""

    id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    units_per_departure: int
    interval_ticks: int
    next_departure_tick: int = 1
    priority: int = 100
    active: bool = True
    return_to_origin: bool = True
    delivered_units: int = 0
    trips_completed: int = 0
    trips_dispatched: int = 0


@dataclass(slots=True)
class Contract:
    """A player-facing objective with deadline, reward, and penalty.

    CARGO_DELIVERY uses destination_node_id + cargo_type + target_units.
    FRONTIER_SUPPORT uses target_world_id + target_units (support streak required).
    GATE_RECOVERY uses target_link_id + target_units (consecutive powered ticks required).
    """

    id: str
    kind: ContractKind
    title: str
    target_units: int
    due_tick: int
    destination_node_id: str | None = None
    cargo_type: CargoType | None = None
    target_world_id: str | None = None
    target_link_id: str | None = None
    reward_cash: float = 0.0
    penalty_cash: float = 0.0
    reward_reputation: int = 0
    penalty_reputation: int = 0
    client: str | None = None
    delivered_units: int = 0
    progress: int = 0
    status: ContractStatus = ContractStatus.ACTIVE
    resolved_tick: int | None = None

    @property
    def remaining_units(self) -> int:
        """Units still needed to satisfy this contract."""

        return max(0, self.target_units - self.delivered_units)

    @property
    def active(self) -> bool:
        """Whether the contract is still open."""

        return self.status == ContractStatus.ACTIVE


@dataclass(slots=True)
class GatePowerStatus:
    """Resolved power status for a gate link."""

    link_id: str
    source_world_id: str
    source_world_name: str
    power_required: int
    power_available: int
    power_shortfall: int
    powered: bool
    active: bool
    slot_capacity: int
    slots_used: int = 0
    charge_pct: float = 1.0
    next_activation_tick: int | None = None
    slot_cargo: dict[CargoType, int] = field(default_factory=dict)

    @property
    def slots_remaining(self) -> int:
        """Slots remaining this tick."""

        return max(0, self.slot_capacity - self.slots_used)


@dataclass(slots=True)
class GameState:
    """Canonical deterministic state for the fixed-tick simulation."""

    tick: int = 0
    worlds: dict[str, WorldState] = field(default_factory=dict)
    nodes: dict[str, NetworkNode] = field(default_factory=dict)
    links: dict[str, NetworkLink] = field(default_factory=dict)
    trains: dict[str, FreightTrain] = field(default_factory=dict)
    orders: dict[str, FreightOrder] = field(default_factory=dict)
    schedules: dict[str, FreightSchedule] = field(default_factory=dict)
    disruptions: dict[str, NetworkDisruption] = field(default_factory=dict)
    shortages: dict[str, dict[CargoType, int]] = field(default_factory=dict)
    buffer_distribution: dict[str, dict[str, dict[CargoType, int]]] = field(default_factory=dict)
    recipe_blocked: dict[str, dict[CargoType, int]] = field(default_factory=dict)
    facility_blocked: dict[str, list[str]] = field(default_factory=dict)
    transfer_used_this_tick: dict[str, int] = field(default_factory=dict)
    transfer_saturation_streak: dict[str, int] = field(default_factory=dict)
    gate_statuses: dict[str, GatePowerStatus] = field(default_factory=dict)
    link_usage_this_tick: dict[str, int] = field(default_factory=dict)
    finance: FinanceState = field(default_factory=FinanceState)
    contracts: dict[str, Contract] = field(default_factory=dict)
    reputation: int = 0
    month_length: int = 30
    economic_identity_enabled: bool = False

    def add_world(self, world: WorldState) -> None:
        """Register a world."""

        if world.id in self.worlds:
            raise ValueError(f"duplicate world id: {world.id}")
        self.worlds[world.id] = world

    def add_node(self, node: NetworkNode) -> None:
        """Register a logistics node."""

        if node.id in self.nodes:
            raise ValueError(f"duplicate node id: {node.id}")
        if node.world_id not in self.worlds:
            raise ValueError(f"node {node.id} references unknown world {node.world_id}")
        self.nodes[node.id] = node

    def add_link(self, link: NetworkLink) -> None:
        """Register a transport link."""

        if link.id in self.links:
            raise ValueError(f"duplicate link id: {link.id}")
        if link.origin not in self.nodes:
            raise ValueError(f"link {link.id} references unknown origin {link.origin}")
        if link.destination not in self.nodes:
            raise ValueError(f"link {link.id} references unknown destination {link.destination}")
        if link.power_source_world_id is not None and link.power_source_world_id not in self.worlds:
            raise ValueError(f"link {link.id} references unknown power source {link.power_source_world_id}")
        if link.travel_ticks <= 0:
            raise ValueError("link travel_ticks must be positive")
        if link.capacity_per_tick <= 0:
            raise ValueError("link capacity_per_tick must be positive")
        if link.power_required < 0:
            raise ValueError("link power_required cannot be negative")
        self.links[link.id] = link

    def add_disruption(self, disruption: NetworkDisruption) -> None:
        """Register a timed network disruption."""

        if disruption.id in self.disruptions:
            raise ValueError(f"duplicate disruption id: {disruption.id}")
        if disruption.link_id not in self.links:
            raise ValueError(f"disruption {disruption.id} references unknown link {disruption.link_id}")
        if disruption.start_tick <= 0:
            raise ValueError("disruption start_tick must be positive")
        if disruption.end_tick < disruption.start_tick:
            raise ValueError("disruption end_tick must be >= start_tick")
        if disruption.capacity_multiplier < 0:
            raise ValueError("disruption capacity_multiplier cannot be negative")
        self.disruptions[disruption.id] = disruption

    def add_train(self, train: FreightTrain) -> None:
        """Register a fixed-tick freight train."""

        if train.id in self.trains:
            raise ValueError(f"duplicate train id: {train.id}")
        if train.node_id not in self.nodes:
            raise ValueError(f"train {train.id} references unknown node {train.node_id}")
        if train.capacity <= 0:
            raise ValueError("train capacity must be positive")
        self.trains[train.id] = train

    def add_order(self, order: FreightOrder) -> None:
        """Register a freight order."""

        if order.id in self.orders:
            raise ValueError(f"duplicate order id: {order.id}")
        if order.train_id not in self.trains:
            raise ValueError(f"order {order.id} references unknown train {order.train_id}")
        if order.origin not in self.nodes:
            raise ValueError(f"order {order.id} references unknown origin {order.origin}")
        if order.destination not in self.nodes:
            raise ValueError(f"order {order.id} references unknown destination {order.destination}")
        if order.requested_units <= 0:
            raise ValueError("order requested_units must be positive")
        self.orders[order.id] = order

    def add_schedule(self, schedule: FreightSchedule) -> None:
        """Register a recurring freight schedule."""

        if schedule.id in self.schedules:
            raise ValueError(f"duplicate schedule id: {schedule.id}")
        if schedule.train_id not in self.trains:
            raise ValueError(f"schedule {schedule.id} references unknown train {schedule.train_id}")
        if schedule.origin not in self.nodes:
            raise ValueError(f"schedule {schedule.id} references unknown origin {schedule.origin}")
        if schedule.destination not in self.nodes:
            raise ValueError(f"schedule {schedule.id} references unknown destination {schedule.destination}")
        if schedule.units_per_departure <= 0:
            raise ValueError("schedule units_per_departure must be positive")
        if schedule.interval_ticks <= 0:
            raise ValueError("schedule interval_ticks must be positive")
        self.schedules[schedule.id] = schedule

    def add_contract(self, contract: Contract) -> None:
        """Register a player-facing contract."""

        if contract.id in self.contracts:
            raise ValueError(f"duplicate contract id: {contract.id}")
        if contract.target_units <= 0:
            raise ValueError("contract target_units must be positive")
        if contract.due_tick <= 0:
            raise ValueError("contract due_tick must be positive")
        if contract.kind == ContractKind.CARGO_DELIVERY:
            if contract.destination_node_id is None or contract.destination_node_id not in self.nodes:
                raise ValueError(
                    f"contract {contract.id} references unknown destination {contract.destination_node_id}"
                )
            if contract.cargo_type is None:
                raise ValueError(f"contract {contract.id} is missing cargo_type")
        elif contract.kind == ContractKind.FRONTIER_SUPPORT:
            if contract.target_world_id is None or contract.target_world_id not in self.worlds:
                raise ValueError(
                    f"contract {contract.id} references unknown world {contract.target_world_id}"
                )
        elif contract.kind == ContractKind.GATE_RECOVERY:
            if contract.target_link_id is None or contract.target_link_id not in self.links:
                raise ValueError(
                    f"contract {contract.id} references unknown link {contract.target_link_id}"
                )
            if self.links[contract.target_link_id].mode != LinkMode.GATE:
                raise ValueError(
                    f"contract {contract.id} target link {contract.target_link_id} is not a gate"
                )
        else:
            raise ValueError(f"contract {contract.id} has unsupported kind {contract.kind}")
        self.contracts[contract.id] = contract

    def apply_command(self, command: object) -> dict[str, object]:
        """Apply a player command to this state."""

        from gaterail.commands import apply_player_command

        return apply_player_command(self, command)

    def links_from(self, node_id: str, mode: LinkMode | None = None) -> list[NetworkLink]:
        """Return active links traversable from ``node_id``."""

        links = [
            link
            for link in self.links.values()
            if self.link_operational(link)
            and link.connects(node_id)
            and (mode is None or link.mode == mode)
        ]
        return sorted(links, key=lambda item: item.id)

    def links_by_mode(self, mode: LinkMode) -> list[NetworkLink]:
        """Return all links for a transport mode."""

        return sorted(
            [link for link in self.links.values() if link.mode == mode],
            key=lambda item: item.id,
        )

    def link_power_source_world_id(self, link: NetworkLink) -> str:
        """Return the world responsible for powering a link."""

        if link.power_source_world_id is not None:
            return link.power_source_world_id
        return self.nodes[link.origin].world_id

    def link_operational(self, link: NetworkLink) -> bool:
        """Return whether a link can currently be used for routing."""

        if not link.active:
            return False
        if link.mode != LinkMode.GATE:
            return True
        if link.id in self.gate_statuses:
            return self.gate_statuses[link.id].powered
        source_world = self.worlds[self.link_power_source_world_id(link)]
        return source_world.base_power_margin >= link.power_required
