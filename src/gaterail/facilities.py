"""Facility-layer simulation: per-component flow, blocked-component detection."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.models import (
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    GameState,
    NetworkNode,
    PortDirection,
)


def _plain_cargo_map(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed maps to report-safe dictionaries."""

    return {
        cargo_type.value: int(units)
        for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)
        if int(units) > 0
    }


def _add_cargo(total: dict[CargoType, int], cargo_type: CargoType, units: int) -> None:
    """Accumulate cargo units."""

    if units > 0:
        total[cargo_type] = total.get(cargo_type, 0) + units


def _factory_block_inputs_satisfied(node: NetworkNode, component: FacilityComponent) -> bool:
    """Return whether a factory block's input demands are met by node inventory."""

    return all(node.stock(cargo) >= units for cargo, units in component.inputs.items())


def _missing_inputs(node: NetworkNode, component: FacilityComponent) -> dict[CargoType, int]:
    """Return per-cargo input shortfall for a factory block."""

    return {
        cargo: units - node.stock(cargo)
        for cargo, units in component.inputs.items()
        if node.stock(cargo) < units
    }


def _run_factory_block(
    node: NetworkNode,
    component: FacilityComponent,
) -> tuple[dict[CargoType, int], dict[CargoType, int]]:
    """Consume inputs and emit outputs for one factory-block batch."""

    consumed: dict[CargoType, int] = {}
    produced: dict[CargoType, int] = {}
    for cargo_type, units in component.inputs.items():
        removed = node.remove_inventory(cargo_type, units)
        _add_cargo(consumed, cargo_type, removed)
    for cargo_type, units in component.outputs.items():
        accepted = node.add_inventory(cargo_type, units)
        _add_cargo(produced, cargo_type, accepted)
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


def apply_facility_components(state: GameState) -> dict[str, object]:
    """Run one tick of facility-component flow.

    Currently focused on FACTORY_BLOCK components: consume `inputs` from node
    inventory, emit `outputs` back into node inventory through `add_inventory`
    (which respects the facility's effective storage capacity). Blocked factory
    blocks are recorded on ``state.facility_blocked`` keyed by node id.
    """

    consumed_by_node: dict[str, dict[CargoType, int]] = {}
    produced_by_node: dict[str, dict[CargoType, int]] = {}
    blocked_entries: list[dict[str, object]] = []
    blocked_by_node: dict[str, list[str]] = {}

    for node_id, node in sorted(state.nodes.items()):
        facility = node.facility
        if facility is None:
            continue
        for component in sorted(facility.components.values(), key=lambda item: item.id):
            if component.kind != FacilityComponentKind.FACTORY_BLOCK:
                continue
            if not component.inputs and not component.outputs:
                continue
            if not _factory_block_inputs_satisfied(node, component):
                missing = _missing_inputs(node, component)
                blocked_entries.append(
                    {
                        "node": node_id,
                        "component": component.id,
                        "reason": "missing inputs",
                        "missing": _plain_cargo_map(missing),
                    }
                )
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

    state.facility_blocked = blocked_by_node
    return {
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
    }


def open_input_ports(facility: Facility, component: FacilityComponent) -> list[str]:
    """Public alias for unwired input port detection (used by previews)."""

    return _ports_with_open_inputs(facility, component)
