"""Facility-layer simulation: per-component flow, blocked-component detection."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.models import (
    Facility,
    FacilityBlockReason,
    FacilityComponent,
    FacilityComponentKind,
    GameState,
    InternalConnection,
    NetworkNode,
    FacilityPort,
    PortDirection,
)
from gaterail.local_rules import (
    infer_connection_cargo,
    transfer_link_rate_multiplier,
    transfer_link_supports_cargo,
)

# Kinds that consume cargo inputs and emit cargo outputs (treated like FACTORY_BLOCK).
# REACTOR, POWER_MODULE, CAPACITOR_BANK are excluded — handled by apply_facility_power.
_FACTORY_LIKE_KINDS: frozenset[FacilityComponentKind] = frozenset({
    FacilityComponentKind.FACTORY_BLOCK,
    FacilityComponentKind.EXTRACTOR_HEAD,
    FacilityComponentKind.CRUSHER,
    FacilityComponentKind.SORTER,
    FacilityComponentKind.SMELTER,
    FacilityComponentKind.REFINERY,
    FacilityComponentKind.CHEMICAL_PROCESSOR,
    FacilityComponentKind.FABRICATOR,
    FacilityComponentKind.ELECTRONICS_ASSEMBLER,
    FacilityComponentKind.SEMICONDUCTOR_LINE,
})


UNBOUNDED_PORT_CAPACITY = 1_000_000_000


class _FacilityBlockEntry(dict):
    """Structured facility block entry with legacy equality compatibility."""

    _LEGACY_REASON_LABELS = {
        FacilityBlockReason.OPEN_INPUT_PORTS.value: "open input ports",
        FacilityBlockReason.MISSING_INPUTS.value: "missing inputs",
        FacilityBlockReason.OUTPUT_PORTS_FULL.value: "output ports full",
        FacilityBlockReason.NODE_STORAGE_FULL.value: "node storage full",
        FacilityBlockReason.POWER_SHORTFALL.value: "power shortfall",
    }

    def __eq__(self, other: object) -> bool:
        """Compare equal to both structured entries and Sprint-16 foundation entries."""

        if not isinstance(other, dict):
            return False
        if dict.__eq__(self, other):
            return True
        reason = _block_reason_value(self.get("reason"))
        legacy_reason = self._LEGACY_REASON_LABELS.get(reason, reason)
        if other.get("node") != self.get("node") or other.get("component") != self.get("component"):
            return False
        if other.get("reason") != legacy_reason:
            return False
        detail = self.get("detail", {})
        if not isinstance(detail, dict):
            detail = {}
        if reason == FacilityBlockReason.OPEN_INPUT_PORTS.value:
            return other.get("open_inputs") == detail.get("open_inputs")
        if reason == FacilityBlockReason.MISSING_INPUTS.value:
            return other.get("missing") == detail.get("missing")
        if reason == FacilityBlockReason.OUTPUT_PORTS_FULL.value:
            return other.get("missing_capacity") == detail.get("missing_capacity")
        return True


def _plain_cargo_map(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed maps to report-safe dictionaries."""

    return {
        cargo_type.value: int(units)
        for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)
        if int(units) > 0
    }


def _block_reason_value(reason: object) -> str:
    """Return a stable string value for a facility blocked-reason field."""

    return reason.value if isinstance(reason, FacilityBlockReason) else str(reason)


def _is_power_block_entry(entry: object) -> bool:
    """Return whether an existing block entry came from facility-power evaluation."""

    if not isinstance(entry, dict):
        return False
    return _block_reason_value(entry.get("reason")) == FacilityBlockReason.POWER_SHORTFALL.value


def _blocked_components_by_node(entries: list[dict[str, object]]) -> dict[str, list[str]]:
    """Build the legacy node→component blocked aggregate from structured entries."""

    blocked: dict[str, list[str]] = {}
    for entry in entries:
        node_id = str(entry.get("node", ""))
        component_id = str(entry.get("component", ""))
        if not node_id or not component_id:
            continue
        components = blocked.setdefault(node_id, [])
        if component_id not in components:
            components.append(component_id)
    return {node_id: sorted(components) for node_id, components in sorted(blocked.items())}


def _add_cargo(total: dict[CargoType, int], cargo_type: CargoType, units: int) -> None:
    """Accumulate cargo units."""

    if units > 0:
        total[cargo_type] = total.get(cargo_type, 0) + units


def _port_inventory(component: FacilityComponent, port_id: str) -> dict[CargoType, int]:
    """Return the mutable cargo buffer for one component port."""

    return component.port_inventory.setdefault(port_id, {})


def _port_stock(component: FacilityComponent, port_id: str, cargo_type: CargoType) -> int:
    """Return cargo currently buffered at one port."""

    return int(component.port_inventory.get(port_id, {}).get(cargo_type, 0))


def _port_total(component: FacilityComponent, port_id: str) -> int:
    """Return total units buffered at one port across all cargo types."""

    return sum(max(0, int(units)) for units in component.port_inventory.get(port_id, {}).values())


def _effective_port_capacity(port: FacilityPort, required_hint: int = 0) -> int:
    """Return a practical per-port buffer cap for internal flow."""

    if port.capacity > 0:
        return int(port.capacity)
    if port.rate > 0:
        return max(int(port.rate), int(required_hint))
    if required_hint > 0:
        return int(required_hint)
    return UNBOUNDED_PORT_CAPACITY


def _port_remaining_capacity(
    component: FacilityComponent,
    port: FacilityPort,
    required_hint: int = 0,
) -> int:
    """Return remaining shared buffer capacity for a component port."""

    capacity = _effective_port_capacity(port, required_hint=required_hint)
    if capacity >= UNBOUNDED_PORT_CAPACITY:
        return capacity
    return max(0, capacity - _port_total(component, port.id))


def _add_port_inventory(
    component: FacilityComponent,
    port: FacilityPort,
    cargo_type: CargoType,
    units: int,
    *,
    required_hint: int = 0,
) -> int:
    """Add cargo to a component port buffer, respecting port capacity."""

    accepted = min(max(0, int(units)), _port_remaining_capacity(component, port, required_hint))
    if accepted <= 0:
        return 0
    inventory = _port_inventory(component, port.id)
    inventory[cargo_type] = inventory.get(cargo_type, 0) + accepted
    return accepted


def _remove_port_inventory(
    component: FacilityComponent,
    port_id: str,
    cargo_type: CargoType,
    units: int,
) -> int:
    """Remove cargo from a component port buffer."""

    inventory = component.port_inventory.get(port_id)
    if not inventory:
        return 0
    available = int(inventory.get(cargo_type, 0))
    removed = min(max(0, int(units)), available)
    if removed <= 0:
        return 0
    remaining = available - removed
    if remaining > 0:
        inventory[cargo_type] = remaining
    else:
        inventory.pop(cargo_type, None)
    if not inventory:
        component.port_inventory.pop(port_id, None)
    return removed


def _ports_for_cargo(
    component: FacilityComponent,
    direction: PortDirection,
    cargo_type: CargoType,
) -> list[FacilityPort]:
    """Return deterministic ports matching one cargo flow."""

    return [
        port
        for port in sorted(component.ports.values(), key=lambda item: item.id)
        if port.direction == direction
        and (port.cargo_type is None or port.cargo_type == cargo_type)
    ]


def _factory_uses_port_inputs(component: FacilityComponent) -> bool:
    """Return whether a factory block should consume from input port buffers."""

    return any(port.direction == PortDirection.INPUT for port in component.ports.values())


def _factory_uses_port_outputs(component: FacilityComponent, cargo_type: CargoType) -> bool:
    """Return whether a factory block should emit cargo into output port buffers."""

    return bool(_ports_for_cargo(component, PortDirection.OUTPUT, cargo_type))


def _connection_parts(
    facility: Facility,
    connection: InternalConnection,
) -> tuple[FacilityComponent, FacilityPort, FacilityComponent, FacilityPort] | None:
    """Return connection endpoints, or None for stale save data."""

    source_component = facility.components.get(connection.source_component_id)
    destination_component = facility.components.get(connection.destination_component_id)
    if source_component is None or destination_component is None:
        return None
    source_port = source_component.ports.get(connection.source_port_id)
    destination_port = destination_component.ports.get(connection.destination_port_id)
    if source_port is None or destination_port is None:
        return None
    if source_port.direction != PortDirection.OUTPUT or destination_port.direction != PortDirection.INPUT:
        return None
    return source_component, source_port, destination_component, destination_port


def _connection_cargo_type(
    source_component: FacilityComponent,
    source_port: FacilityPort,
    destination_component: FacilityComponent,
    destination_port: FacilityPort,
) -> CargoType | None:
    """Infer the single cargo type a connection should move."""

    return infer_connection_cargo(source_component, source_port, destination_component, destination_port)


def _connection_rate(
    source_port: FacilityPort,
    destination_port: FacilityPort,
    connection: InternalConnection,
) -> int:
    """Return the per-tick movement limit for one internal connection."""

    rates = [int(port.rate) for port in (source_port, destination_port) if port.rate > 0]
    if rates:
        base_rate = min(rates)
        return max(1, int(base_rate * transfer_link_rate_multiplier(connection.link_type)))
    return UNBOUNDED_PORT_CAPACITY


def _source_available(
    node: NetworkNode,
    source_component: FacilityComponent,
    source_port: FacilityPort,
    cargo_type: CargoType,
) -> int:
    """Return units available at a connection source endpoint."""

    if source_component.kind in _FACTORY_LIKE_KINDS:
        return _port_stock(source_component, source_port.id, cargo_type)
    return node.stock(cargo_type)


def _remove_connection_source(
    node: NetworkNode,
    source_component: FacilityComponent,
    source_port: FacilityPort,
    cargo_type: CargoType,
    units: int,
) -> int:
    """Remove cargo from a connection source endpoint."""

    if source_component.kind in _FACTORY_LIKE_KINDS:
        return _remove_port_inventory(source_component, source_port.id, cargo_type, units)
    return node.remove_inventory(cargo_type, units)


def _refund_connection_source(
    node: NetworkNode,
    source_component: FacilityComponent,
    source_port: FacilityPort,
    cargo_type: CargoType,
    units: int,
) -> None:
    """Return cargo to a source endpoint after a partial destination accept."""

    if units <= 0:
        return
    if source_component.kind in _FACTORY_LIKE_KINDS:
        _add_port_inventory(source_component, source_port, cargo_type, units)
    else:
        node.add_inventory(cargo_type, units)


def _destination_capacity(
    node: NetworkNode,
    destination_component: FacilityComponent,
    destination_port: FacilityPort,
    cargo_type: CargoType,
    required_hint: int = 0,
) -> int:
    """Return how much cargo a connection destination can accept."""

    if destination_component.kind in _FACTORY_LIKE_KINDS:
        return _port_remaining_capacity(destination_component, destination_port, required_hint)
    return max(0, node.effective_storage_capacity() - node.total_inventory())


def _accept_connection_destination(
    node: NetworkNode,
    destination_component: FacilityComponent,
    destination_port: FacilityPort,
    cargo_type: CargoType,
    units: int,
    *,
    required_hint: int = 0,
) -> int:
    """Add cargo to a connection destination endpoint."""

    if destination_component.kind in _FACTORY_LIKE_KINDS:
        return _add_port_inventory(
            destination_component,
            destination_port,
            cargo_type,
            units,
            required_hint=required_hint,
        )
    return node.add_inventory(cargo_type, units)


def _apply_internal_connections(
    node_id: str,
    node: NetworkNode,
    facility: Facility,
    *,
    source_factory_only: bool = False,
) -> list[dict[str, object]]:
    """Move cargo along internal facility connections."""

    transfers: list[dict[str, object]] = []
    for connection in sorted(facility.connections.values(), key=lambda item: item.id):
        parts = _connection_parts(facility, connection)
        if parts is None:
            continue
        source_component, source_port, destination_component, destination_port = parts
        if source_factory_only and source_component.kind not in _FACTORY_LIKE_KINDS:
            continue
        cargo_type = _connection_cargo_type(
            source_component,
            source_port,
            destination_component,
            destination_port,
        )
        if cargo_type is None:
            continue
        if not transfer_link_supports_cargo(connection.link_type, cargo_type):
            continue
        available = _source_available(node, source_component, source_port, cargo_type)
        if available <= 0:
            continue
        rate = _connection_rate(source_port, destination_port, connection)
        destination_room = _destination_capacity(
            node,
            destination_component,
            destination_port,
            cargo_type,
            required_hint=rate if rate < UNBOUNDED_PORT_CAPACITY else available,
        )
        units = min(available, rate, destination_room)
        if units <= 0:
            continue
        removed = _remove_connection_source(
            node,
            source_component,
            source_port,
            cargo_type,
            units,
        )
        if removed <= 0:
            continue
        accepted = _accept_connection_destination(
            node,
            destination_component,
            destination_port,
            cargo_type,
            removed,
            required_hint=removed,
        )
        if accepted < removed:
            _refund_connection_source(
                node,
                source_component,
                source_port,
                cargo_type,
                removed - accepted,
            )
        if accepted <= 0:
            continue
        transfers.append(
            {
                "node": node_id,
                "connection": connection.id,
                "source_component": source_component.id,
                "source_port": source_port.id,
                "destination_component": destination_component.id,
                "destination_port": destination_port.id,
                "link_type": connection.link_type.value,
                "cargo": cargo_type.value,
                "units": accepted,
            }
        )
    return transfers


def _factory_block_inputs_satisfied(node: NetworkNode, component: FacilityComponent) -> bool:
    """Return whether a factory block's input demands are met by node inventory."""

    if _factory_uses_port_inputs(component):
        return not _missing_inputs(node, component)
    return all(node.stock(cargo) >= units for cargo, units in component.inputs.items())


def _missing_inputs(node: NetworkNode, component: FacilityComponent) -> dict[CargoType, int]:
    """Return per-cargo input shortfall for a factory block."""

    if _factory_uses_port_inputs(component):
        missing: dict[CargoType, int] = {}
        for cargo, units in component.inputs.items():
            available = sum(
                _port_stock(component, port.id, cargo)
                for port in _ports_for_cargo(component, PortDirection.INPUT, cargo)
            )
            if available < units:
                missing[cargo] = units - available
        return missing
    return {
        cargo: units - node.stock(cargo)
        for cargo, units in component.inputs.items()
        if node.stock(cargo) < units
    }


def _output_port_shortfalls(component: FacilityComponent) -> dict[CargoType, int]:
    """Return outputs that cannot fit in their matching output port buffers."""

    shortfalls: dict[CargoType, int] = {}
    for cargo_type, units in component.outputs.items():
        ports = _ports_for_cargo(component, PortDirection.OUTPUT, cargo_type)
        if not ports:
            continue
        room = sum(
            _port_remaining_capacity(component, port, required_hint=units)
            for port in ports
        )
        if room < units:
            shortfalls[cargo_type] = units - room
    return shortfalls


def _consume_factory_inputs(
    node: NetworkNode,
    component: FacilityComponent,
) -> dict[CargoType, int]:
    """Consume one factory batch from either input ports or node inventory."""

    consumed: dict[CargoType, int] = {}
    if not _factory_uses_port_inputs(component):
        for cargo_type, units in component.inputs.items():
            removed = node.remove_inventory(cargo_type, units)
            _add_cargo(consumed, cargo_type, removed)
        return consumed

    for cargo_type, units in component.inputs.items():
        remaining = units
        for port in _ports_for_cargo(component, PortDirection.INPUT, cargo_type):
            if remaining <= 0:
                break
            removed = _remove_port_inventory(component, port.id, cargo_type, remaining)
            _add_cargo(consumed, cargo_type, removed)
            remaining -= removed
    return consumed


def _produce_factory_outputs(
    node: NetworkNode,
    component: FacilityComponent,
) -> dict[CargoType, int]:
    """Produce one factory batch into output ports or node inventory."""

    produced: dict[CargoType, int] = {}
    for cargo_type, units in component.outputs.items():
        if _factory_uses_port_outputs(component, cargo_type):
            remaining = units
            for port in _ports_for_cargo(component, PortDirection.OUTPUT, cargo_type):
                if remaining <= 0:
                    break
                accepted = _add_port_inventory(
                    component,
                    port,
                    cargo_type,
                    remaining,
                    required_hint=units,
                )
                _add_cargo(produced, cargo_type, accepted)
                remaining -= accepted
            continue
        accepted = node.add_inventory(cargo_type, units)
        _add_cargo(produced, cargo_type, accepted)
    return produced


def _run_factory_block(
    node: NetworkNode,
    component: FacilityComponent,
) -> tuple[dict[CargoType, int], dict[CargoType, int]]:
    """Consume inputs and emit outputs for one factory-block batch."""

    consumed = _consume_factory_inputs(node, component)
    produced = _produce_factory_outputs(node, component)
    return consumed, produced


def _ports_with_open_inputs(facility: Facility, component: FacilityComponent) -> list[str]:
    """Return component input port ids that have no incoming internal connection."""

    incoming: set[tuple[str, str]] = {
        (connection.destination_component_id, connection.destination_port_id)
        for connection in facility.connections.values()
    }
    open_inputs: list[str] = []
    for port in component.ports.values():
        if port.direction != PortDirection.INPUT:
            continue
        if (component.id, port.id) in incoming:
            continue
        open_inputs.append(port.id)
    return open_inputs


def _factory_block_open_input_ports(facility: Facility, component: FacilityComponent) -> list[str]:
    """Return required factory-block input ports that are not internally wired."""

    if not component.inputs:
        return []
    input_ports = [
        port
        for port in component.ports.values()
        if port.direction == PortDirection.INPUT
    ]
    if not input_ports:
        return []
    open_input_ids = set(_ports_with_open_inputs(facility, component))
    required_cargo = set(component.inputs)
    return sorted(
        port.id
        for port in input_ports
        if port.id in open_input_ids
        and (port.cargo_type is None or port.cargo_type in required_cargo)
    )


def _power_component_missing_inputs(
    node: NetworkNode,
    component: FacilityComponent,
) -> dict[CargoType, int]:
    """Return node-inventory shortfalls for a power-generating component."""

    return {
        cargo_type: units - node.stock(cargo_type)
        for cargo_type, units in component.inputs.items()
        if node.stock(cargo_type) < units
    }


def _consume_power_component_inputs(node: NetworkNode, component: FacilityComponent) -> None:
    """Consume one tick of node inventory for a power-generating component."""

    for cargo_type, units in component.inputs.items():
        node.remove_inventory(cargo_type, units)


def apply_facility_power(state: GameState) -> dict[str, object]:
    """Apply facility power generation and burst discharge to owning worlds.

    The contribution is idempotent across ticks: the previous facility
    contribution is removed before the new one is calculated, so deleting a
    component restores the world's static power baseline on the next tick.
    """

    for world_id, contribution in sorted(state.facility_power_contribution.items()):
        world = state.worlds.get(world_id)
        if world is not None:
            world.power_available -= int(contribution)
    state.facility_power_contribution = {}
    state.facility_block_entries = []
    state.facility_blocked = {}

    contribution_by_world: dict[str, int] = {}
    component_entries: list[dict[str, object]] = []
    blocked_entries: list[dict[str, object]] = []
    capacitors: list[tuple[str, NetworkNode, FacilityComponent]] = []

    for node_id, node in sorted(state.nodes.items()):
        if node.facility is None:
            continue
        world_id = node.world_id
        for component in sorted(node.facility.components.values(), key=lambda item: item.id):
            if component.kind == FacilityComponentKind.CAPACITOR_BANK:
                capacitors.append((node_id, node, component))
                continue

            provided = max(0, int(component.power_provided))
            required = max(0, int(component.power_required))
            generated = 0
            consumed_inputs: dict[CargoType, int] = {}

            if component.kind == FacilityComponentKind.REACTOR:
                missing = _power_component_missing_inputs(node, component)
                if missing:
                    entry = {
                        "node": node_id,
                        "component": component.id,
                        "kind": component.kind.value,
                        "reason": FacilityBlockReason.POWER_SHORTFALL.value,
                        "detail": {
                            "missing": _plain_cargo_map(missing),
                            "power_provided": provided,
                        },
                    }
                    blocked_entries.append(entry)
                    component_entries.append(
                        {
                            "node": node_id,
                            "component": component.id,
                            "kind": component.kind.value,
                            "world": world_id,
                            "power_required": required,
                            "power_provided": provided,
                            "net": -required,
                            "blocked": True,
                        }
                    )
                    if required:
                        contribution_by_world[world_id] = contribution_by_world.get(world_id, 0) - required
                    continue
                consumed_inputs = dict(component.inputs)
                _consume_power_component_inputs(node, component)
                generated = provided
            else:
                generated = provided

            net = generated - required
            if net:
                contribution_by_world[world_id] = contribution_by_world.get(world_id, 0) + net
            if generated or required or consumed_inputs:
                component_entries.append(
                    {
                        "node": node_id,
                        "component": component.id,
                        "kind": component.kind.value,
                        "world": world_id,
                        "power_required": required,
                        "power_provided": provided,
                        "generated": generated,
                        "net": net,
                        "consumed": _plain_cargo_map(consumed_inputs),
                        "blocked": False,
                    }
                )

    capacitor_entries: list[dict[str, object]] = []
    for node_id, node, component in capacitors:
        world_id = node.world_id
        world = state.worlds[world_id]
        pending_contribution = contribution_by_world.get(world_id, 0)
        available_after_static = world.power_available + pending_contribution
        deficit = max(0, world.power_used - available_after_static)
        discharge = min(
            deficit,
            max(0, int(component.stored_charge)),
            max(0, int(component.discharge_per_tick)),
        )
        if discharge <= 0:
            continue
        component.stored_charge -= discharge
        contribution_by_world[world_id] = pending_contribution + discharge
        capacitor_entries.append(
            {
                "node": node_id,
                "component": component.id,
                "kind": component.kind.value,
                "world": world_id,
                "discharged": discharge,
                "stored_charge": int(component.stored_charge),
            }
        )

    for world_id, contribution in sorted(contribution_by_world.items()):
        if contribution == 0:
            continue
        state.worlds[world_id].power_available += contribution
        state.facility_power_contribution[world_id] = contribution

    state.facility_block_entries = blocked_entries
    state.facility_blocked = _blocked_components_by_node(blocked_entries)
    return {
        "contribution": {
            world_id: int(contribution)
            for world_id, contribution in sorted(state.facility_power_contribution.items())
        },
        "components": component_entries,
        "capacitors": capacitor_entries,
        "blocked": blocked_entries,
    }


def apply_facility_components(state: GameState) -> dict[str, object]:
    """Run one tick of facility-component flow.

    Internal connections first move cargo from source output ports or shared
    node stock into destination ports. Factory-like components with input ports
    consume from those port buffers; legacy factory blocks without ports still
    consume from node inventory. Blocked components are recorded on
    ``state.facility_blocked`` keyed by node id and in ``state.facility_block_entries``.
    """

    power_block_entries = [
        dict(entry)
        for entry in state.facility_block_entries
        if _is_power_block_entry(entry)
    ]
    connection_transfers: list[dict[str, object]] = []
    consumed_by_node: dict[str, dict[CargoType, int]] = {}
    produced_by_node: dict[str, dict[CargoType, int]] = {}
    blocked_entries: list[dict[str, object]] = []
    blocked_by_node: dict[str, list[str]] = _blocked_components_by_node(power_block_entries)

    for node_id, node in sorted(state.nodes.items()):
        facility = node.facility
        if facility is None:
            continue
        connection_transfers.extend(_apply_internal_connections(node_id, node, facility))
        for component in sorted(facility.components.values(), key=lambda item: item.id):
            if component.kind not in _FACTORY_LIKE_KINDS:
                continue
            if not component.inputs and not component.outputs:
                continue
            open_inputs = _factory_block_open_input_ports(facility, component)
            if open_inputs:
                entry: dict[str, object] = _FacilityBlockEntry({
                    "node": node_id,
                    "component": component.id,
                    "kind": component.kind.value,
                    "reason": FacilityBlockReason.OPEN_INPUT_PORTS,
                    "detail": {"open_inputs": open_inputs},
                })
                blocked_entries.append(entry)
                blocked_by_node.setdefault(node_id, []).append(component.id)
                continue
            if not _factory_block_inputs_satisfied(node, component):
                missing = _missing_inputs(node, component)
                entry = _FacilityBlockEntry({
                    "node": node_id,
                    "component": component.id,
                    "kind": component.kind.value,
                    "reason": FacilityBlockReason.MISSING_INPUTS,
                    "detail": {"missing": _plain_cargo_map(missing)},
                })
                blocked_entries.append(entry)
                blocked_by_node.setdefault(node_id, []).append(component.id)
                continue
            output_shortfalls = _output_port_shortfalls(component)
            if output_shortfalls:
                entry = _FacilityBlockEntry({
                    "node": node_id,
                    "component": component.id,
                    "kind": component.kind.value,
                    "reason": FacilityBlockReason.OUTPUT_PORTS_FULL,
                    "detail": {"missing_capacity": _plain_cargo_map(output_shortfalls)},
                })
                blocked_entries.append(entry)
                blocked_by_node.setdefault(node_id, []).append(component.id)
                continue
            consumed, produced = _run_factory_block(node, component)
            for cargo_type, units in consumed.items():
                _add_cargo(
                    consumed_by_node.setdefault(node_id, {}),
                    cargo_type,
                    units,
                )
            for cargo_type, units in produced.items():
                _add_cargo(
                    produced_by_node.setdefault(node_id, {}),
                    cargo_type,
                    units,
                )
        connection_transfers.extend(
            _apply_internal_connections(node_id, node, facility, source_factory_only=True)
        )

    all_block_entries = power_block_entries + blocked_entries
    state.facility_blocked = _blocked_components_by_node(all_block_entries)
    state.facility_block_entries = all_block_entries
    return {
        "connection_transfers": connection_transfers,
        "consumed": {
            node_id: _plain_cargo_map(cargo_map)
            for node_id, cargo_map in sorted(consumed_by_node.items())
        },
        "produced": {
            node_id: _plain_cargo_map(cargo_map)
            for node_id, cargo_map in sorted(produced_by_node.items())
        },
        "blocked": blocked_entries,
    }


def facility_summary(facility: Facility) -> dict[str, object]:
    """Return a stable JSON summary of one facility for snapshot/save use."""

    components_payload: list[dict[str, object]] = []
    for component in sorted(facility.components.values(), key=lambda item: item.id):
        ports_payload = [
            {
                "id": port.id,
                "direction": port.direction.value,
                "cargo": None if port.cargo_type is None else port.cargo_type.value,
                "rate": int(port.rate),
                "capacity": int(port.capacity),
                "inventory": _plain_cargo_map(component.port_inventory.get(port.id, {})),
            }
            for port in sorted(component.ports.values(), key=lambda item: item.id)
        ]
        components_payload.append(
            {
                "id": component.id,
                "kind": component.kind.value,
                "capacity": int(component.capacity),
                "rate": int(component.rate),
                "power_required": int(component.power_required),
                "power_provided": int(component.power_provided),
                "train_capacity": int(component.train_capacity),
                "concurrent_loading_limit": int(component.concurrent_loading_limit),
                "stored_charge": int(component.stored_charge),
                "discharge_per_tick": int(component.discharge_per_tick),
                "build_cost": round(float(component.build_cost), 2),
                "inputs": _plain_cargo_map(component.inputs),
                "outputs": _plain_cargo_map(component.outputs),
                "ports": ports_payload,
            }
        )

    connections_payload = [
        {
            "id": connection.id,
            "source_component_id": connection.source_component_id,
            "source_port_id": connection.source_port_id,
            "destination_component_id": connection.destination_component_id,
            "destination_port_id": connection.destination_port_id,
            "link_type": connection.link_type.value,
        }
        for connection in sorted(facility.connections.values(), key=lambda item: item.id)
    ]

    return {
        "components": components_payload,
        "connections": connections_payload,
        "storage_capacity_override": facility.storage_capacity_override(),
        "loader_rate_override": facility.loader_rate_override(),
        "unloader_rate_override": facility.unloader_rate_override(),
        "power_required": facility.power_required(),
        "power_provided": facility.power_provided(),
    }


def open_input_ports(facility: Facility, component: FacilityComponent) -> list[str]:
    """Public alias for unwired input port detection (used by previews)."""

    return _ports_with_open_inputs(facility, component)
