"""Local rail diagnostics derived from persisted operational track geometry."""

from __future__ import annotations

from typing import Any

from gaterail.models import LinkMode, OperationalEntityType, OperationalPlacedEntity, TrainStatus
from gaterail.traffic import active_signals_for_link, build_signal_report


def _cell_payload(cells: tuple[tuple[int, int, int], ...]) -> list[dict[str, int]]:
    """Return JSON-safe local rail cells."""

    return [
        {"x": int(x), "y": int(y), "z": int(z)}
        for x, y, z in cells
    ]


def _track_entities_by_link(state: Any) -> dict[str, tuple[str, OperationalPlacedEntity]]:
    """Return persisted local track entities keyed by backing graph link id."""

    tracks: dict[str, tuple[str, OperationalPlacedEntity]] = {}
    for area in getattr(state, "operational_areas", {}).values():
        for entity in area.entities.values():
            if entity.entity_type != OperationalEntityType.TRACK_SEGMENT or entity.link_id is None:
                continue
            tracks[entity.link_id] = (area.id, entity)
    return tracks


def _trains_for_link(state: Any, link_id: str) -> list[str]:
    """Return trains currently using one backing link."""

    trains: list[str] = []
    for train in sorted(state.trains.values(), key=lambda item: item.id):
        if train.status == TrainStatus.IN_TRANSIT and link_id in train.route_link_ids:
            trains.append(train.id)
    return trains


def _blocked_events_for_link(signal_report: dict[str, object], link_id: str) -> list[dict[str, object]]:
    """Return signal-blocked route events for one link."""

    blocked = signal_report.get("blocked", [])
    if not isinstance(blocked, list):
        return []
    return [
        dict(event)
        for event in blocked
        if isinstance(event, dict) and str(event.get("link", "")) == link_id
    ]


def _link_diagnostic_payload(
    state: Any,
    signal_report: dict[str, object],
    link_id: str,
    area_id: str,
    entity: OperationalPlacedEntity,
) -> dict[str, object]:
    """Return one local rail diagnostic payload."""

    blocks = signal_report.get("blocks", {})
    block_payload = blocks.get(link_id) if isinstance(blocks, dict) else None
    if not isinstance(block_payload, dict):
        block_payload = None
    link = state.links.get(link_id)
    return {
        "link_id": link_id,
        "operational_area_id": area_id,
        "entity_id": entity.id,
        "world_id": entity.world_id,
        "origin": None if link is None else link.origin,
        "destination": None if link is None else link.destination,
        "path_cells": _cell_payload(entity.path_cells),
        "signal_ids": [signal.id for signal in active_signals_for_link(state, link_id)],
        "block": block_payload,
        "reserved_by": state.rail_block_reservations.get(link_id),
        "trains": _trains_for_link(state, link_id),
        "blocked_events": _blocked_events_for_link(signal_report, link_id),
    }


def _switch_position(state: Any, area_id: str, node_id: str) -> dict[str, int] | None:
    """Return the local station cell for a node if present."""

    area = state.operational_areas.get(area_id)
    if area is None:
        return None
    for entity in area.entities.values():
        if entity.owner_node_id == node_id and entity.entity_type != OperationalEntityType.TRACK_SEGMENT:
            return {"x": int(entity.x), "y": int(entity.y), "z": int(entity.z)}
    return None


def _switch_route_payload(
    state: Any,
    signal_report: dict[str, object],
    link_id: str,
    entity: OperationalPlacedEntity,
) -> dict[str, object]:
    """Return route-reservation context for one switch option."""

    blocks = signal_report.get("blocks", {})
    block_payload = blocks.get(link_id) if isinstance(blocks, dict) else None
    if isinstance(block_payload, dict):
        block = dict(block_payload)
    else:
        block = None
    return {
        "link_id": link_id,
        "path_entity_id": entity.id,
        "signal_ids": [signal.id for signal in active_signals_for_link(state, link_id)],
        "block": block,
        "reserved_by": state.rail_block_reservations.get(link_id),
        "trains": _trains_for_link(state, link_id),
        "blocked_events": _blocked_events_for_link(signal_report, link_id),
    }


def _switch_payloads(
    state: Any,
    signal_report: dict[str, object],
    tracks: dict[str, tuple[str, OperationalPlacedEntity]],
) -> list[dict[str, object]]:
    """Return abstract local switch/station-throat diagnostics."""

    by_node: dict[tuple[str, str], list[tuple[str, OperationalPlacedEntity]]] = {}
    for link_id, (area_id, entity) in tracks.items():
        link = state.links.get(link_id)
        if link is None or link.mode != LinkMode.RAIL:
            continue
        by_node.setdefault((area_id, link.origin), []).append((link_id, entity))
        by_node.setdefault((area_id, link.destination), []).append((link_id, entity))

    switches: list[dict[str, object]] = []
    for (area_id, node_id), entries in sorted(by_node.items(), key=lambda item: (item[0][0], item[0][1])):
        if len(entries) < 2:
            continue
        entries = sorted(entries, key=lambda item: item[0])
        area = state.operational_areas.get(area_id)
        switch_id = f"{area_id}:{node_id}:switch"
        selected_link_id = getattr(state, "local_switch_routes", {}).get(switch_id)
        selected_path_entity_id = None
        if selected_link_id not in {link_id for link_id, _ in entries}:
            selected_link_id = None
        if selected_link_id is not None:
            for link_id, entity in entries:
                if link_id == selected_link_id:
                    selected_path_entity_id = entity.id
                    break
        route_payloads = [
            _switch_route_payload(state, signal_report, link_id, entity)
            for link_id, entity in entries
        ]
        selected_route = None
        if selected_link_id is not None:
            for route in route_payloads:
                if route["link_id"] == selected_link_id:
                    selected_route = route
                    break
        switches.append(
            {
                "id": switch_id,
                "kind": "station_throat",
                "operational_area_id": area_id,
                "world_id": None if area is None else area.world_id,
                "node_id": node_id,
                "position": _switch_position(state, area_id, node_id),
                "link_ids": [link_id for link_id, _ in entries],
                "path_entity_ids": [entity.id for _, entity in entries],
                "selected_link_id": selected_link_id,
                "selected_path_entity_id": selected_path_entity_id,
                "routes": route_payloads,
                "selected_route": selected_route,
            }
        )
    return switches


def build_local_rail_diagnostics(state: Any) -> dict[str, object]:
    """Return local rail diagnostics for snapshots and Godot."""

    from gaterail.operational import ensure_operational_areas

    ensure_operational_areas(state)
    tracks = _track_entities_by_link(state)
    signal_report = build_signal_report(state)
    links = {
        link_id: _link_diagnostic_payload(state, signal_report, link_id, area_id, entity)
        for link_id, (area_id, entity) in sorted(tracks.items())
        if link_id in state.links and state.links[link_id].mode == LinkMode.RAIL
    }
    return {
        "links": links,
        "switches": _switch_payloads(state, signal_report, tracks),
    }


def local_rail_entity_diagnostics(state: Any, entity: OperationalPlacedEntity) -> dict[str, object] | None:
    """Return diagnostics for one persisted local track entity."""

    if entity.entity_type != OperationalEntityType.TRACK_SEGMENT or entity.link_id is None:
        return None
    links = build_local_rail_diagnostics(state).get("links", {})
    if not isinstance(links, dict):
        return None
    payload = links.get(entity.link_id)
    return dict(payload) if isinstance(payload, dict) else None
