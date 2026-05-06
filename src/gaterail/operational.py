"""Derived local operational-area model for backend snapshots.

This module does not run a second logistics simulation. It projects the
authoritative node/link/facility state into a local operational view that Godot
and tests can consume as a bottom-up entity model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from gaterail.cargo import CargoType
from gaterail.models import (
    FacilityComponentKind,
    LinkMode,
    NetworkNode,
    NodeKind,
    OperationalAreaState,
    OperationalEntityType,
    OperationalPlacedEntity,
    PortDirection,
)


class OperationalEntityKind(StrEnum):
    """Physical/local entities exposed to the operational view."""

    EXTRACTOR = "extractor"
    RAIL_TRACK = "rail_track"
    STATION_PLATFORM = "station_platform"
    LOADER = "loader"
    UNLOADER = "unloader"
    HOPPER = "hopper"
    WAREHOUSE = "warehouse"
    TRANSFER_LINK = "transfer_link"
    REFINERY = "refinery"
    FACTORY = "factory"
    RAILGATE_TERMINAL = "railgate_terminal"
    POWER_CONNECTOR = "power_connector"


@dataclass(frozen=True, slots=True)
class OperationalEntity:
    """One backend-owned local operational entity in snapshot form."""

    id: str
    kind: OperationalEntityKind
    world_id: str
    x: float
    y: float
    rotation: int = 0
    owner_node_id: str | None = None
    component_id: str | None = None
    link_id: str | None = None
    link_type: str | None = None
    status: str = "active"
    cargo_buffers: dict[CargoType, int] = field(default_factory=dict)
    input_ports: tuple[str, ...] = ()
    output_ports: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def payload(self) -> dict[str, object]:
        """Return JSON-safe snapshot data."""

        data: dict[str, object] = {
            "id": self.id,
            "kind": self.kind.value,
            "world_id": self.world_id,
            "position": {"x": round(float(self.x), 3), "y": round(float(self.y), 3)},
            "rotation": int(self.rotation) % 360,
            "status": self.status,
            "cargo_buffers": _cargo_payload(self.cargo_buffers),
            "input_ports": list(self.input_ports),
            "output_ports": list(self.output_ports),
            "blocked_reasons": list(self.blocked_reasons),
        }
        if self.owner_node_id is not None:
            data["owner_node_id"] = self.owner_node_id
        if self.component_id is not None:
            data["component_id"] = self.component_id
        if self.link_id is not None:
            data["link_id"] = self.link_id
        if self.link_type is not None:
            data["link_type"] = self.link_type
        return data


@dataclass(frozen=True, slots=True)
class OperationalArea:
    """Pseudo-grid operational area owned by one world."""

    id: str
    world_id: str
    entities: tuple[OperationalEntity, ...]
    cell_size: int = 24

    def payload(self) -> dict[str, object]:
        """Return JSON-safe snapshot data."""

        bounds = _area_bounds(self.entities)
        return {
            "id": self.id,
            "world_id": self.world_id,
            "grid": {
                "kind": "pseudo_grid",
                "cell_size": self.cell_size,
                "has_cell_occupancy": False,
                "bounds": bounds,
            },
            "entities": [entity.payload() for entity in self.entities],
        }


def operational_areas_payload(state: Any) -> list[dict[str, object]]:
    """Return persisted local operational areas, migrating old state when needed."""

    ensure_operational_areas(state)
    return [
        operational_area_payload(state, area)
        for area in sorted(getattr(state, "operational_areas", {}).values(), key=lambda item: item.id)
    ]


def ensure_operational_areas(state: Any) -> None:
    """Initialise missing persisted local operational areas from current backend state."""

    areas: dict[str, OperationalAreaState] = getattr(state, "operational_areas", {})
    if areas is None:
        areas = {}
        state.operational_areas = areas
    for world_id in sorted(getattr(state, "worlds", {})):
        area_id = f"{world_id}:local"
        if area_id in areas:
            continue
        areas[area_id] = _derive_operational_area(state, world_id)


def operational_area_payload(state: Any, area: OperationalAreaState) -> dict[str, object]:
    """Return one persisted operational area as JSON-safe snapshot data."""

    entities = [
        operational_entity_payload(state, area, entity)
        for entity in sorted(area.entities.values(), key=lambda item: item.id)
    ]
    return {
        "id": area.id,
        "world_id": area.world_id,
        "grid": {
            "kind": "local_grid",
            "cell_size": int(area.cell_size),
            "width": int(area.width),
            "height": int(area.height),
            "has_cell_occupancy": True,
            "bounds": {
                "min_x": 0.0,
                "min_y": 0.0,
                "max_x": float(area.width * area.cell_size),
                "max_y": float(area.height * area.cell_size),
            },
        },
        "entities": entities,
    }


def operational_entity_payload(
    state: Any,
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
) -> dict[str, object]:
    """Return one persisted local entity with dynamic backing-state status."""

    cargo_buffers = _placed_entity_cargo_buffers(state, entity)
    input_ports, output_ports = _placed_entity_ports(state, entity)
    blocked_reasons = tuple(
        dict.fromkeys((*entity.blocked_reasons, *_placed_entity_blockers(state, entity)))
    )
    status = "blocked" if blocked_reasons else entity.construction_state.value
    payload: dict[str, object] = {
        "id": entity.id,
        "kind": _visual_kind(entity),
        "entity_type": entity.entity_type.value,
        "world_id": entity.world_id,
        "cell": {"x": int(entity.x), "y": int(entity.y), "z": int(entity.z)},
        "position": {
            "x": round(float(entity.x * area.cell_size), 3),
            "y": round(float(entity.y * area.cell_size), 3),
        },
        "rotation": int(entity.rotation) % 360,
        "footprint": {
            "width": entity.footprint_size()[0],
            "height": entity.footprint_size()[1],
        },
        "path_cells": [
            {"x": x, "y": y, "z": z}
            for x, y, z in entity.path_cells
        ],
        "occupied_cells": [
            {"x": x, "y": y, "z": z}
            for x, y, z in entity.occupied_cells()
        ],
        "status": status,
        "cargo_buffers": _cargo_payload(cargo_buffers),
        "input_ports": list(input_ports),
        "output_ports": list(output_ports),
        "connection_ports": list(entity.connection_ports),
        "blocked_reasons": list(blocked_reasons),
        "construction_state": entity.construction_state.value,
        "blocks_occupancy": bool(entity.blocks_occupancy),
    }
    if entity.visual_hint is not None:
        payload["visual_hint"] = entity.visual_hint
    if entity.owner_node_id is not None:
        payload["owner_node_id"] = entity.owner_node_id
    if entity.component_id is not None:
        payload["component_id"] = entity.component_id
    if entity.link_id is not None:
        payload["link_id"] = entity.link_id
    if entity.link_type is not None:
        payload["link_type"] = entity.link_type
    if entity.entity_type == OperationalEntityType.TRACK_SEGMENT and entity.link_id is not None:
        from gaterail.local_rail import local_rail_entity_diagnostics

        diagnostics = local_rail_entity_diagnostics(state, entity)
        if diagnostics is not None:
            payload["rail_diagnostics"] = diagnostics
    if entity.platform_side is not None:
        payload["platform_side"] = entity.platform_side
    if entity.adjacent_to_entity_id is not None or entity.adjacent_port_id is not None:
        payload["adjacency"] = {
            "entity_id": entity.adjacent_to_entity_id,
            "port_id": entity.adjacent_port_id,
            "side": entity.platform_side,
        }
    return payload


def _derive_operational_area(state: Any, world_id: str) -> OperationalAreaState:
    """Build a persisted local grid for an old save/scenario without one."""

    area = OperationalAreaState(id=f"{world_id}:local", world_id=world_id, width=48, height=32, cell_size=24)
    nodes = [
        node
        for node in sorted(getattr(state, "nodes", {}).values(), key=lambda item: item.id)
        if node.world_id == world_id
    ]
    component_cells: dict[tuple[str, str], tuple[int, int]] = {}
    for node in nodes:
        x, y = _node_cell(node, area)
        entity_type = _node_entity_type(node)
        _add_derived_entity(
            area,
            OperationalPlacedEntity(
                id=f"{node.id}:station",
                entity_type=entity_type,
                world_id=world_id,
                x=x,
                y=y,
                rotation=0,
                width=_default_footprint(entity_type)[0],
                height=_default_footprint(entity_type)[1],
                owner_node_id=node.id,
                input_ports=("rail_in",),
                output_ports=("rail_out",),
                visual_hint=_node_station_kind(node).value,
            ),
        )
        facility = node.facility
        if facility is None:
            continue
        components = sorted(facility.components.values(), key=lambda item: item.id)
        for index, component in enumerate(components):
            entity_type = _component_entity_type(component.kind)
            if entity_type is None:
                continue
            ox, oy = _component_cell_offset(index)
            cx, cy = _clamped_cell(area, x + ox, y + oy)
            component_cells[(node.id, component.id)] = (cx, cy)
            _add_derived_entity(
                area,
                OperationalPlacedEntity(
                    id=f"{node.id}:{component.id}",
                    entity_type=entity_type,
                    world_id=world_id,
                    x=cx,
                    y=cy,
                    rotation=_component_rotation(component.kind),
                    width=_default_footprint(entity_type)[0],
                    height=_default_footprint(entity_type)[1],
                    owner_node_id=node.id,
                    component_id=component.id,
                    input_ports=tuple(
                        port.id
                        for port in sorted(component.ports.values(), key=lambda item: item.id)
                        if port.direction == PortDirection.INPUT
                    ),
                    output_ports=tuple(
                        port.id
                        for port in sorted(component.ports.values(), key=lambda item: item.id)
                        if port.direction == PortDirection.OUTPUT
                    ),
                    visual_hint=_component_entity_kind(component.kind).value
                    if _component_entity_kind(component.kind) is not None
                    else None,
                ),
            )
        for connection in sorted(facility.connections.values(), key=lambda item: item.id):
            sx, sy = component_cells.get((node.id, connection.source_component_id), (x, y))
            dx, dy = component_cells.get((node.id, connection.destination_component_id), (x, y))
            cx, cy = _clamped_cell(area, round((sx + dx) / 2.0), round((sy + dy) / 2.0))
            _add_derived_entity(
                area,
                OperationalPlacedEntity(
                    id=f"{node.id}:{connection.id}",
                    entity_type=OperationalEntityType.TRANSFER_LINK,
                    world_id=world_id,
                    x=cx,
                    y=cy,
                    rotation=_cell_angle_hint(sx, sy, dx, dy),
                    width=1,
                    height=1,
                    owner_node_id=node.id,
                    link_id=connection.id,
                    link_type=connection.link_type.value,
                    input_ports=(f"{connection.destination_component_id}.{connection.destination_port_id}",),
                    output_ports=(f"{connection.source_component_id}.{connection.source_port_id}",),
                    visual_hint=OperationalEntityKind.TRANSFER_LINK.value,
                    blocks_occupancy=False,
                ),
            )
    for link in sorted(getattr(state, "links", {}).values(), key=lambda item: item.id):
        if link.mode != LinkMode.RAIL:
            continue
        origin = getattr(state, "nodes", {}).get(link.origin)
        destination = getattr(state, "nodes", {}).get(link.destination)
        if origin is None or destination is None or origin.world_id != world_id or destination.world_id != world_id:
            continue
        ox, oy = _node_cell(origin, area)
        dx, dy = _node_cell(destination, area)
        cx, cy = _clamped_cell(area, round((ox + dx) / 2.0), round((oy + dy) / 2.0))
        _add_derived_entity(
            area,
            OperationalPlacedEntity(
                id=f"{link.id}:track",
                entity_type=OperationalEntityType.TRACK_SEGMENT,
                world_id=world_id,
                x=cx,
                y=cy,
                rotation=_cell_angle_hint(ox, oy, dx, dy),
                link_id=link.id,
                input_ports=(origin.id,),
                output_ports=(destination.id,),
                visual_hint=OperationalEntityKind.RAIL_TRACK.value,
            ),
        )
    return area


def _node_cell(node: NetworkNode, area: OperationalAreaState) -> tuple[int, int]:
    """Return a stable grid cell for a node's existing layout coordinates."""

    x, y = _node_position(node)
    return _clamped_cell(
        area,
        int(round(x / float(area.cell_size))) + area.width // 2,
        int(round(y / float(area.cell_size))) + area.height // 3,
    )


def _clamped_cell(area: OperationalAreaState, x: int, y: int) -> tuple[int, int]:
    """Clamp a cell coordinate into one area."""

    return (
        max(0, min(int(area.width) - 1, int(x))),
        max(0, min(int(area.height) - 1, int(y))),
    )


def _component_cell_offset(index: int) -> tuple[int, int]:
    """Return a deterministic component offset in grid cells."""

    offsets = (
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
        (0, -2),
        (2, 0),
        (0, 2),
        (-2, 0),
    )
    return offsets[index % len(offsets)]


def _add_derived_entity(area: OperationalAreaState, entity: OperationalPlacedEntity) -> None:
    """Add a migrated entity, nudging it if another blocking entity occupies its cell."""

    if entity.blocks_occupancy:
        occupied = area.occupied_cells()
        if any(cell in occupied for cell in entity.occupied_cells()):
            original_x, original_y = entity.x, entity.y
            placed = False
            for radius in range(1, 8):
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if abs(dx) != radius and abs(dy) != radius:
                            continue
                        nx, ny = _clamped_cell(area, original_x + dx, original_y + dy)
                        entity.x = nx
                        entity.y = ny
                        if not any(cell in occupied for cell in entity.occupied_cells()):
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    break
            if not placed:
                entity.x, entity.y = original_x, original_y
                entity.blocks_occupancy = False
    area.entities[entity.id] = entity


def _node_entity_type(node: NetworkNode) -> OperationalEntityType:
    """Return persisted entity type for a node anchor."""

    if node.kind == NodeKind.EXTRACTOR:
        return OperationalEntityType.EXTRACTOR
    if node.kind == NodeKind.GATE_HUB:
        return OperationalEntityType.RAILGATE_TERMINAL
    if node.kind in {NodeKind.DEPOT, NodeKind.WAREHOUSE, NodeKind.SETTLEMENT}:
        return OperationalEntityType.STORAGE
    return OperationalEntityType.STATION_PLATFORM


def _component_entity_type(kind: FacilityComponentKind) -> OperationalEntityType | None:
    """Map facility component kinds to persisted operational entity types."""

    visual = _component_entity_kind(kind)
    if visual is None:
        return None
    if visual == OperationalEntityKind.EXTRACTOR:
        return OperationalEntityType.EXTRACTOR
    if visual == OperationalEntityKind.RAIL_TRACK:
        return OperationalEntityType.TRACK_SEGMENT
    if visual == OperationalEntityKind.STATION_PLATFORM:
        return OperationalEntityType.STATION_PLATFORM
    if visual == OperationalEntityKind.LOADER:
        return OperationalEntityType.LOADER
    if visual == OperationalEntityKind.UNLOADER:
        return OperationalEntityType.UNLOADER
    if visual == OperationalEntityKind.HOPPER:
        return OperationalEntityType.HOPPER
    if visual == OperationalEntityKind.WAREHOUSE:
        return OperationalEntityType.STORAGE
    if visual == OperationalEntityKind.TRANSFER_LINK:
        return OperationalEntityType.TRANSFER_LINK
    if visual == OperationalEntityKind.REFINERY:
        return OperationalEntityType.REFINERY
    if visual == OperationalEntityKind.FACTORY:
        return OperationalEntityType.FACTORY
    if visual == OperationalEntityKind.RAILGATE_TERMINAL:
        return OperationalEntityType.RAILGATE_TERMINAL
    if visual == OperationalEntityKind.POWER_CONNECTOR:
        return OperationalEntityType.POWER_CONNECTOR
    return None


def _default_footprint(entity_type: OperationalEntityType) -> tuple[int, int]:
    """Return the smallest useful local footprint for one entity type."""

    if entity_type in {
        OperationalEntityType.EXTRACTOR,
        OperationalEntityType.STATION_PLATFORM,
        OperationalEntityType.REFINERY,
        OperationalEntityType.FACTORY,
        OperationalEntityType.RAILGATE_TERMINAL,
    }:
        return 2, 2
    return 1, 1


def _visual_kind(entity: OperationalPlacedEntity) -> str:
    """Return the legacy snapshot kind Godot already understands."""

    if entity.visual_hint:
        return entity.visual_hint
    mapping = {
        OperationalEntityType.TRACK_SEGMENT: OperationalEntityKind.RAIL_TRACK.value,
        OperationalEntityType.STORAGE: OperationalEntityKind.WAREHOUSE.value,
    }
    return mapping.get(entity.entity_type, entity.entity_type.value)


def _cell_angle_hint(sx: int, sy: int, dx: int, dy: int) -> int:
    """Return a cardinal rotation from one cell to another."""

    delta_x = int(dx) - int(sx)
    delta_y = int(dy) - int(sy)
    if abs(delta_x) >= abs(delta_y):
        return 90 if delta_x >= 0 else 270
    return 180 if delta_y >= 0 else 0


def _placed_entity_cargo_buffers(state: Any, entity: OperationalPlacedEntity) -> dict[CargoType, int]:
    """Return dynamic cargo buffers for a persisted entity's backing object."""

    node = getattr(state, "nodes", {}).get(entity.owner_node_id) if entity.owner_node_id else None
    if node is None:
        return {}
    if entity.component_id is None:
        return dict(getattr(node, "inventory", {}))
    facility = getattr(node, "facility", None)
    component = None if facility is None else facility.components.get(entity.component_id)
    if component is None:
        return {}
    return _component_cargo_buffers(component)


def _placed_entity_ports(
    state: Any,
    entity: OperationalPlacedEntity,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return dynamic ports for backed components, or persisted port hints."""

    node = getattr(state, "nodes", {}).get(entity.owner_node_id) if entity.owner_node_id else None
    if node is not None and entity.component_id is not None and node.facility is not None:
        component = node.facility.components.get(entity.component_id)
        if component is not None:
            return (
                tuple(
                    port.id
                    for port in sorted(component.ports.values(), key=lambda item: item.id)
                    if port.direction == PortDirection.INPUT
                ),
                tuple(
                    port.id
                    for port in sorted(component.ports.values(), key=lambda item: item.id)
                    if port.direction == PortDirection.OUTPUT
                ),
            )
    return entity.input_ports, entity.output_ports


def _placed_entity_blockers(state: Any, entity: OperationalPlacedEntity) -> list[str]:
    """Return dynamic blockers for a persisted entity's backing object."""

    if entity.owner_node_id is not None and entity.component_id is None:
        node = getattr(state, "nodes", {}).get(entity.owner_node_id)
        if node is not None:
            return _node_blockers(state, node)
    if entity.owner_node_id is not None and entity.component_id is not None:
        return _component_blockers(state, entity.owner_node_id, entity.component_id)
    if entity.link_id is not None:
        link = getattr(state, "links", {}).get(entity.link_id)
        if link is not None:
            return [str(reason) for reason in getattr(link, "disruption_reasons", ()) if str(reason)]
    return []


def _node_entities(state: Any, node: NetworkNode) -> list[OperationalEntity]:
    """Return operational entities derived from one node and its facility."""

    x, y = _node_position(node)
    blockers = _node_blockers(state, node)
    entities = [
        OperationalEntity(
            id=f"{node.id}:station",
            kind=_node_station_kind(node),
            world_id=node.world_id,
            x=x,
            y=y,
            owner_node_id=node.id,
            cargo_buffers=dict(node.inventory),
            input_ports=("rail_in",),
            output_ports=("rail_out",),
            blocked_reasons=tuple(blockers),
        )
    ]

    facility = node.facility
    if facility is None:
        return entities

    for index, component in enumerate(sorted(facility.components.values(), key=lambda item: item.id)):
        kind = _component_entity_kind(component.kind)
        if kind is None:
            continue
        ox, oy = _component_offset(index)
        ports_in = tuple(
            port.id
            for port in sorted(component.ports.values(), key=lambda item: item.id)
            if port.direction == PortDirection.INPUT
        )
        ports_out = tuple(
            port.id
            for port in sorted(component.ports.values(), key=lambda item: item.id)
            if port.direction == PortDirection.OUTPUT
        )
        cargo_buffers = _component_cargo_buffers(component)
        component_blockers = tuple(_component_blockers(state, node.id, component.id))
        entities.append(
            OperationalEntity(
                id=f"{node.id}:{component.id}",
                kind=kind,
                world_id=node.world_id,
                x=x + ox,
                y=y + oy,
                rotation=_component_rotation(component.kind),
                owner_node_id=node.id,
                component_id=component.id,
                cargo_buffers=cargo_buffers,
                input_ports=ports_in,
                output_ports=ports_out,
                blocked_reasons=component_blockers,
            )
        )

    component_positions = {
        component.id: (x + ox, y + oy)
        for component, (ox, oy) in (
            (component, _component_offset(index))
            for index, component in enumerate(sorted(facility.components.values(), key=lambda item: item.id))
        )
    }
    for connection in sorted(facility.connections.values(), key=lambda item: item.id):
        sx, sy = component_positions.get(connection.source_component_id, (x, y))
        dx, dy = component_positions.get(connection.destination_component_id, (x, y))
        entities.append(
            OperationalEntity(
                id=f"{node.id}:{connection.id}",
                kind=OperationalEntityKind.TRANSFER_LINK,
                world_id=node.world_id,
                x=(sx + dx) / 2.0,
                y=(sy + dy) / 2.0,
                rotation=_angle_hint(sx, sy, dx, dy),
                owner_node_id=node.id,
                link_id=connection.id,
                link_type=connection.link_type.value,
                output_ports=(f"{connection.source_component_id}.{connection.source_port_id}",),
                input_ports=(f"{connection.destination_component_id}.{connection.destination_port_id}",),
            )
        )

    return entities


def _rail_entity(origin: NetworkNode, destination: NetworkNode, link: Any) -> OperationalEntity:
    """Return an operational rail-track entity for one rail link."""

    ox, oy = _node_position(origin)
    dx, dy = _node_position(destination)
    blocked = tuple(str(reason) for reason in getattr(link, "disruption_reasons", ()) if str(reason))
    return OperationalEntity(
        id=f"{link.id}:track",
        kind=OperationalEntityKind.RAIL_TRACK,
        world_id=origin.world_id,
        x=(ox + dx) / 2.0,
        y=(oy + dy) / 2.0,
        rotation=_angle_hint(ox, oy, dx, dy),
        link_id=link.id,
        input_ports=(origin.id,),
        output_ports=(destination.id,),
        status="blocked" if blocked else "active",
        blocked_reasons=blocked,
    )


def _node_station_kind(node: NetworkNode) -> OperationalEntityKind:
    """Return the node-level entity kind for an operational station anchor."""

    if node.kind == NodeKind.EXTRACTOR:
        return OperationalEntityKind.EXTRACTOR
    if node.kind == NodeKind.GATE_HUB:
        return OperationalEntityKind.RAILGATE_TERMINAL
    if node.kind in {NodeKind.DEPOT, NodeKind.WAREHOUSE, NodeKind.SETTLEMENT}:
        return OperationalEntityKind.WAREHOUSE
    return OperationalEntityKind.STATION_PLATFORM


def _component_entity_kind(kind: FacilityComponentKind) -> OperationalEntityKind | None:
    """Map facility component kinds to local operational entity kinds."""

    if kind == FacilityComponentKind.EXTRACTOR_HEAD:
        return OperationalEntityKind.EXTRACTOR
    if kind == FacilityComponentKind.PLATFORM:
        return OperationalEntityKind.STATION_PLATFORM
    if kind == FacilityComponentKind.LOADER:
        return OperationalEntityKind.LOADER
    if kind == FacilityComponentKind.UNLOADER:
        return OperationalEntityKind.UNLOADER
    if kind == FacilityComponentKind.STORAGE_BAY:
        return OperationalEntityKind.HOPPER
    if kind == FacilityComponentKind.WAREHOUSE_BAY:
        return OperationalEntityKind.WAREHOUSE
    if kind in {
        FacilityComponentKind.CRUSHER,
        FacilityComponentKind.SORTER,
        FacilityComponentKind.SMELTER,
        FacilityComponentKind.REFINERY,
        FacilityComponentKind.CHEMICAL_PROCESSOR,
    }:
        return OperationalEntityKind.REFINERY
    if kind in {
        FacilityComponentKind.FACTORY_BLOCK,
        FacilityComponentKind.FABRICATOR,
        FacilityComponentKind.ELECTRONICS_ASSEMBLER,
        FacilityComponentKind.SEMICONDUCTOR_LINE,
    }:
        return OperationalEntityKind.FACTORY
    if kind == FacilityComponentKind.GATE_INTERFACE:
        return OperationalEntityKind.RAILGATE_TERMINAL
    if kind in {
        FacilityComponentKind.POWER_MODULE,
        FacilityComponentKind.REACTOR,
        FacilityComponentKind.CAPACITOR_BANK,
    }:
        return OperationalEntityKind.POWER_CONNECTOR
    return None


def _node_position(node: NetworkNode) -> tuple[float, float]:
    """Return stable pseudo-grid coordinates for one node."""

    if node.layout_x is not None and node.layout_y is not None:
        return float(node.layout_x), float(node.layout_y)
    seed = sum(ord(char) for char in node.id)
    return float((seed % 17) * 48), float(((seed // 17) % 17) * 48)


def _component_offset(index: int) -> tuple[float, float]:
    """Return a small deterministic offset around a node anchor."""

    offsets = (
        (-18.0, -18.0),
        (18.0, -18.0),
        (-18.0, 18.0),
        (18.0, 18.0),
        (0.0, -30.0),
        (30.0, 0.0),
        (0.0, 30.0),
        (-30.0, 0.0),
    )
    return offsets[index % len(offsets)]


def _component_rotation(kind: FacilityComponentKind) -> int:
    """Return a deterministic orientation hint for one component kind."""

    if kind in {FacilityComponentKind.LOADER, FacilityComponentKind.EXTRACTOR_HEAD}:
        return 90
    if kind == FacilityComponentKind.UNLOADER:
        return 270
    return 0


def _angle_hint(sx: float, sy: float, dx: float, dy: float) -> int:
    """Return a coarse orientation hint without importing trigonometry-heavy helpers."""

    delta_x = dx - sx
    delta_y = dy - sy
    if abs(delta_x) >= abs(delta_y):
        return 90 if delta_x >= 0 else 270
    return 180 if delta_y >= 0 else 0


def _component_cargo_buffers(component: Any) -> dict[CargoType, int]:
    """Return cargo currently buffered on component ports."""

    total: dict[CargoType, int] = {}
    for port_inventory in getattr(component, "port_inventory", {}).values():
        for cargo_type, units in port_inventory.items():
            if int(units) > 0:
                total[cargo_type] = total.get(cargo_type, 0) + int(units)
    return total


def _node_blockers(state: Any, node: NetworkNode) -> list[str]:
    """Return node-level operational blockers visible in local UI."""

    blockers: list[str] = []
    if node.requires_facility_handling:
        if node.effective_outbound_rate() <= 0:
            blockers.append("missing_loader")
        if node.effective_inbound_rate() <= 0:
            blockers.append("missing_unloader")
    if node.total_inventory() >= node.effective_storage_capacity():
        blockers.append("destination_storage_full")
    for train in getattr(state, "trains", {}).values():
        if train.node_id == node.id and train.blocked_reason:
            blockers.append(str(train.blocked_reason))
    return list(dict.fromkeys(blockers))


def _component_blockers(state: Any, node_id: str, component_id: str) -> list[str]:
    """Return component-level blockers from structured facility block entries."""

    blockers: list[str] = []
    for entry in getattr(state, "facility_block_entries", ()):
        if not isinstance(entry, dict):
            continue
        if entry.get("node") != node_id or entry.get("component") != component_id:
            continue
        reason = entry.get("reason")
        if reason is not None:
            blockers.append(reason.value if hasattr(reason, "value") else str(reason))
    return list(dict.fromkeys(blockers))


def _cargo_payload(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Return JSON-safe cargo mapping."""

    return {
        cargo_type.value: int(units)
        for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)
        if int(units) > 0
    }


def _area_bounds(entities: tuple[OperationalEntity, ...]) -> dict[str, float]:
    """Return viewport-friendly bounds for one operational area."""

    if not entities:
        return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0}
    xs = [entity.x for entity in entities]
    ys = [entity.y for entity in entities]
    margin = 48.0
    return {
        "min_x": round(min(xs) - margin, 3),
        "min_y": round(min(ys) - margin, 3),
        "max_x": round(max(xs) + margin, 3),
        "max_y": round(max(ys) + margin, 3),
    }
