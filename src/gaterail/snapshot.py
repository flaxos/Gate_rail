"""Stable render snapshots for Stage 2 clients."""

from __future__ import annotations

from math import cos, pi, sin

from gaterail.cargo import CargoType
from gaterail.cargo import cargo_catalog_payload
from gaterail.economy import BUFFER_NODE_KINDS
from gaterail.facilities import facility_summary
from gaterail.gate import preview_gate_power
from gaterail.models import (
    ConstructionStatus,
    Contract,
    ContractKind,
    FacilityBlockReason,
    GameState,
    LinkMode,
    NodeKind,
)
from gaterail.operational import operational_areas_payload
from gaterail.resource_chains import resource_branch_pressure
from gaterail.resources import resource_catalog_payload, resource_deposit_to_dict
from gaterail.traffic import active_signals_for_link, build_signal_report, effective_link_capacity
from gaterail.local_rail import build_local_rail_diagnostics
from gaterail.transport import route_through_stops


SNAPSHOT_VERSION = 1
SCHEDULE_ORDER_PREFIX = "schedule:"


def _serialize_train_stop(stop: object) -> dict[str, object]:
    """Convert a TrainStop dataclass to a JSON-safe dictionary."""

    return {
        "node_id": stop.node_id,
        "action": stop.action.value,
        "cargo_type": None if stop.cargo_type is None else stop.cargo_type.value,
        "units": int(stop.units),
        "wait_condition": stop.wait_condition.value,
        "wait_ticks": int(stop.wait_ticks),
    }


def _schedule_route_stop_ids(schedule: object) -> list[str]:
    """Return display route stops, using ordered train stops when present."""

    train_stops = list(getattr(schedule, "train_stops", ()))
    if not train_stops:
        return [
            str(getattr(schedule, "origin", "")),
            *[str(stop) for stop in getattr(schedule, "stops", ())],
            str(getattr(schedule, "destination", "")),
        ]

    raw_stop_ids = [str(getattr(schedule, "origin", ""))]
    raw_stop_ids.extend(str(getattr(stop, "node_id", "")) for stop in train_stops)
    raw_stop_ids.append(str(getattr(schedule, "destination", "")))
    stop_ids: list[str] = []
    for stop_id in raw_stop_ids:
        if not stop_id:
            continue
        if stop_ids and stop_ids[-1] == stop_id:
            continue
        stop_ids.append(stop_id)
    return stop_ids


def _route_for_schedule_snapshot(state: GameState, schedule: object) -> object | None:
    """Resolve a schedule route using the same route stops rendered to clients."""

    stop_ids = _schedule_route_stop_ids(schedule)
    if len(stop_ids) < 2:
        return None
    return route_through_stops(
        state,
        stop_ids[0],
        tuple(stop_ids[1:-1]),
        stop_ids[-1],
        require_operational=False,
    )


def _cargo_map(mapping: object) -> dict[str, int]:
    """Convert cargo-keyed inventory maps to JSON-safe dictionaries."""

    if not isinstance(mapping, dict):
        return {}
    return {
        str(cargo.value if hasattr(cargo, "value") else cargo): int(units)
        for cargo, units in sorted(
            mapping.items(),
            key=lambda item: str(item[0].value if hasattr(item[0], "value") else item[0]),
        )
        if int(units) > 0
    }


def _resource_map(mapping: object) -> dict[str, int]:
    """Convert resource-id inventory maps to JSON-safe dictionaries."""

    if not isinstance(mapping, dict):
        return {}
    return {
        str(resource_id): int(units)
        for resource_id, units in sorted(mapping.items())
        if int(units) > 0
    }


def _plain_json_value(value: object) -> object:
    """Convert enum-like values inside diagnostic payloads to JSON-safe values."""

    if isinstance(value, dict):
        return {
            str(key.value if hasattr(key, "value") else key): _plain_json_value(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0].value if hasattr(pair[0], "value") else pair[0]),
            )
        }
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _scenario_catalog_payload() -> list[dict[str, object]]:
    """Return backend-owned built-in scenario metadata for clients."""

    from gaterail.scenarios import DEFAULT_SCENARIO, scenario_definitions

    return [
        {
            "key": definition.key,
            "aliases": list(definition.aliases),
            "title": definition.title,
            "description": definition.description,
            "default": definition.key == DEFAULT_SCENARIO,
        }
        for definition in scenario_definitions()
    ]


def _facility_block_entry_payload(entry: object) -> dict[str, object]:
    """Return a stable snapshot payload for one facility block entry."""

    if not isinstance(entry, dict):
        return {}
    reason = entry.get("reason")
    reason_value = reason.value if isinstance(reason, FacilityBlockReason) else str(reason)
    return {
        "node": str(entry.get("node", "")),
        "component": str(entry.get("component", "")),
        "kind": str(entry.get("kind", "")),
        "reason": reason_value,
        "detail": _plain_json_value(entry.get("detail", {})),
    }


def _world_position(index: int, total: int) -> dict[str, int]:
    """Return deterministic galaxy-scale coordinates owned by the Python sim."""

    if total <= 1:
        return {"x": 0, "y": 0}
    radius = 420
    angle = (-pi / 2.0) + ((2.0 * pi * index) / total)
    return {"x": int(round(cos(angle) * radius)), "y": int(round(sin(angle) * radius))}


def _node_layout(node: object) -> dict[str, float] | None:
    """Return node-local layout metadata when the backend owns it."""

    layout_x = getattr(node, "layout_x", None)
    layout_y = getattr(node, "layout_y", None)
    if layout_x is None or layout_y is None:
        return None
    return {"x": round(float(layout_x), 3), "y": round(float(layout_y), 3)}


def _track_alignment(link: object) -> list[dict[str, float]]:
    """Return JSON-safe rail-alignment metadata for a link."""

    return [
        {"x": round(float(point.x), 3), "y": round(float(point.y), 3)}
        for point in getattr(link, "alignment", ())
    ]


def _reverse_link_id_for(state: GameState, link: object) -> str | None:
    """Return an existing link that supports reverse traversal for ``link``."""

    origin = getattr(link, "origin", None)
    destination = getattr(link, "destination", None)
    mode = getattr(link, "mode", None)
    link_id = getattr(link, "id", None)
    endpoints = {origin, destination}
    for candidate in sorted(state.links.values(), key=lambda item: item.id):
        if candidate.id == link_id or candidate.mode != mode:
            continue
        if candidate.bidirectional and {candidate.origin, candidate.destination} == endpoints:
            return candidate.id
        if candidate.origin == destination and candidate.destination == origin:
            return candidate.id
    return None


def _contract_progress(contract: Contract) -> tuple[str, str, int]:
    """Return render labels and current progress for a contract."""

    if contract.kind == ContractKind.CARGO_DELIVERY:
        cargo = contract.cargo_type.value if contract.cargo_type is not None else "unknown"
        destination = contract.destination_node_id or "unknown"
        return cargo, destination, contract.delivered_units
    if contract.kind == ContractKind.FRONTIER_SUPPORT:
        return "support", f"world:{contract.target_world_id}", contract.progress
    if contract.kind == ContractKind.GATE_RECOVERY:
        return "powered", f"link:{contract.target_link_id}", contract.progress
    return "unknown", "unknown", contract.progress


def _facility_component_kind_present(state: GameState, node_id: str, kind: str) -> bool:
    """Return whether a node facility contains a component kind value."""

    node = state.nodes.get(node_id)
    facility = None if node is None else node.facility
    if facility is None:
        return False
    return any(component.kind.value == kind for component in facility.components.values())


def _facility_connection_present(state: GameState, node_id: str, connection_id: str) -> bool:
    """Return whether a facility contains one internal connection."""

    node = state.nodes.get(node_id)
    facility = None if node is None else node.facility
    return bool(facility is not None and connection_id in facility.connections)


def _local_schedule_create_command(schedule_id: str) -> dict[str, object]:
    """Return a deterministic tutorial-local CreateSchedule command."""

    common = {
        "type": "CreateSchedule",
        "schedule_id": schedule_id,
        "active": True,
        "return_to_origin": True,
    }
    if schedule_id == "local_ore_to_refinery":
        return {
            **common,
            "train_id": "local_ore_runner",
            "origin": "atlas_local_mine",
            "destination": "atlas_local_refinery",
            "cargo_type": CargoType.ORE.value,
            "units_per_departure": 20,
            "interval_ticks": 6,
            "train_stops": [
                {
                    "node_id": "atlas_local_mine",
                    "action": "pickup",
                    "cargo_type": CargoType.ORE.value,
                    "units": 20,
                    "wait_condition": "full",
                },
                {
                    "node_id": "atlas_local_refinery",
                    "action": "delivery",
                    "cargo_type": CargoType.ORE.value,
                    "units": 20,
                    "wait_condition": "empty",
                },
            ],
        }
    if schedule_id == "local_metal_to_gateworks":
        return {
            **common,
            "train_id": "local_metal_runner",
            "origin": "atlas_local_refinery",
            "destination": "atlas_gateworks",
            "cargo_type": CargoType.METAL.value,
            "units_per_departure": 20,
            "interval_ticks": 8,
            "train_stops": [
                {
                    "node_id": "atlas_local_refinery",
                    "action": "pickup",
                    "cargo_type": CargoType.METAL.value,
                    "units": 20,
                    "wait_condition": "full",
                },
                {
                    "node_id": "atlas_gateworks",
                    "action": "delivery",
                    "cargo_type": CargoType.METAL.value,
                    "units": 20,
                    "wait_condition": "empty",
                },
            ],
        }
    if schedule_id == "local_components_to_gate":
        return {
            **common,
            "train_id": "local_component_runner",
            "origin": "atlas_gateworks",
            "destination": "atlas_local_outbound_gate",
            "cargo_type": CargoType.GATE_COMPONENTS.value,
            "units_per_departure": 4,
            "interval_ticks": 10,
            "train_stops": [
                {
                    "node_id": "atlas_gateworks",
                    "action": "pickup",
                    "cargo_type": CargoType.GATE_COMPONENTS.value,
                    "units": 4,
                    "wait_condition": "full",
                },
                {
                    "node_id": "atlas_local_outbound_gate",
                    "action": "delivery",
                    "cargo_type": CargoType.GATE_COMPONENTS.value,
                    "units": 4,
                    "wait_condition": "empty",
                },
            ],
        }
    if schedule_id == "local_starter_to_sable":
        return {
            **common,
            "train_id": "local_starter_runner",
            "origin": "atlas_depot",
            "destination": "sable_settlement",
            "cargo_type": CargoType.CONSTRUCTION_MATERIALS.value,
            "units_per_departure": 40,
            "interval_ticks": 12,
            "train_stops": [
                {
                    "node_id": "atlas_depot",
                    "action": "pickup",
                    "cargo_type": CargoType.CONSTRUCTION_MATERIALS.value,
                    "units": 40,
                    "wait_condition": "full",
                },
                {
                    "node_id": "sable_settlement",
                    "action": "delivery",
                    "cargo_type": CargoType.CONSTRUCTION_MATERIALS.value,
                    "units": 40,
                    "wait_condition": "empty",
                },
            ],
        }
    raise ValueError(f"unknown local tutorial schedule: {schedule_id}")


def _local_schedule_progress(state: GameState, schedule_id: str) -> int:
    """Return delivered units for a local tutorial schedule, or zero when absent."""

    schedule = state.schedules.get(schedule_id)
    return 0 if schedule is None else int(schedule.delivered_units)


def _local_project_components(state: GameState) -> int:
    """Return gate-component cargo already consumed by the local Railgate project."""

    project = state.construction_projects.get("proj_atlas_local_outbound_gate")
    if project is None:
        return 0
    return int(project.delivered_cargo.get(CargoType.GATE_COMPONENTS, 0))


def _tutorial_local_statuses(state: GameState) -> dict[str, bool]:
    """Return canonical completion signals for the local logistics tutorial."""

    project = state.construction_projects.get("proj_atlas_local_outbound_gate")
    gate_complete = project is not None and project.status == ConstructionStatus.COMPLETED
    destination_site = state.space_sites.get("site_sable_reach")
    starter_contract = state.contracts.get("local_sable_starter_cargo")
    delivered_component_progress = max(
        _local_schedule_progress(state, "local_components_to_gate"),
        _node_stock(state, "atlas_local_outbound_gate", CargoType.GATE_COMPONENTS),
        _local_project_components(state),
        4 if gate_complete else 0,
    )
    gateworks_progress = max(
        _node_stock(state, "atlas_gateworks", CargoType.GATE_COMPONENTS),
        delivered_component_progress,
    )
    return {
        "connect_mine_storage": _facility_connection_present(
            state,
            "atlas_local_mine",
            "wire_mine_head_to_storage",
        ),
        "build_mine_refinery_track": "rail_atlas_local_mine_refinery" in state.links,
        "build_mine_loader": _facility_component_kind_present(
            state,
            "atlas_local_mine",
            "loader",
        ),
        "build_refinery_unloader": _facility_component_kind_present(
            state,
            "atlas_local_refinery",
            "unloader",
        ),
        "wire_refinery_storage": (
            _facility_connection_present(state, "atlas_local_refinery", "wire_refinery_ore")
            and _facility_connection_present(state, "atlas_local_refinery", "wire_refinery_metal")
        ),
        "automate_ore_train": (
            _local_schedule_progress(state, "local_ore_to_refinery") >= 20
            or _node_stock(state, "atlas_local_refinery", CargoType.METAL) > 0
            or _local_schedule_progress(state, "local_metal_to_gateworks") > 0
            or gateworks_progress > 0
        ),
        "build_refinery_loader": _facility_component_kind_present(
            state,
            "atlas_local_refinery",
            "loader",
        ),
        "build_refinery_gateworks_track": "rail_atlas_refinery_gateworks" in state.links,
        "automate_metal_train": (
            _local_schedule_progress(state, "local_metal_to_gateworks") >= 20
            or gateworks_progress > 0
        ),
        "manufacture_gate_components": gateworks_progress >= 4,
        "build_gateworks_gate_track": "rail_atlas_gateworks_outbound_gate" in state.links,
        "deliver_components_to_gate": delivered_component_progress >= 4,
        "complete_outbound_gate": gate_complete,
        "survey_destination": bool(destination_site is not None and destination_site.discovered),
        "establish_gate_corridor": "gate_atlas_local_sable" in state.links,
        "send_starter_freight": bool(
            starter_contract is not None and starter_contract.status.value == "fulfilled"
        ),
    }


def _tutorial_local_next_action(state: GameState, step_id: str) -> dict[str, object] | None:
    """Return the next real backend command for one local tutorial step."""

    if step_id == "connect_mine_storage":
        return {
            "kind": "command",
            "label": "Connect extractor to storage",
            "command": {
                "type": "local.connect_entities",
                "operational_area_id": "atlas:local",
                "node_id": "atlas_local_mine",
                "owner_node_id": "atlas_local_mine",
                "connection_id": "wire_mine_head_to_storage",
                "source_component_id": "mine_head",
                "source_port_id": "ore_out",
                "destination_component_id": "mine_storage",
                "destination_port_id": "ore_in",
                "link_type": "conveyor",
            },
        }
    if step_id == "build_mine_refinery_track":
        return {
            "kind": "command",
            "label": "Lay rail to refinery",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_atlas_local_mine_refinery",
                "origin_node_id": "atlas_local_mine",
                "destination_node_id": "atlas_local_refinery",
                "x": 19,
                "y": 14,
                "rotation": 90,
            },
        }
    if step_id == "build_mine_loader":
        return {
            "kind": "command",
            "label": "Install mine loader",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "component_id": "mine_loader",
                "entity_id": "mine_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_mine",
                "x": 18,
                "y": 15,
                "rotation": 90,
                "rate": 20,
                "power_required": 4,
                "construction_cargo": {CargoType.CONSTRUCTION_MATERIALS.value: 4},
            },
        }
    if step_id == "build_refinery_unloader":
        return {
            "kind": "command",
            "label": "Install refinery unloader",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "component_id": "refinery_unloader",
                "entity_id": "refinery_unloader",
                "entity_type": "unloader",
                "owner_node_id": "atlas_local_refinery",
                "x": 24,
                "y": 14,
                "rotation": 270,
                "rate": 20,
                "power_required": 4,
                "construction_cargo": {CargoType.CONSTRUCTION_MATERIALS.value: 4},
            },
        }
    if step_id == "wire_refinery_storage":
        return {
            "kind": "commands",
            "label": "Connect refinery transfer links",
            "commands": [
                {
                    "type": "local.connect_entities",
                    "operational_area_id": "atlas:local",
                    "node_id": "atlas_local_refinery",
                    "owner_node_id": "atlas_local_refinery",
                    "connection_id": "wire_refinery_ore",
                    "source_component_id": "refinery_storage",
                    "source_port_id": "ore_out",
                    "destination_component_id": "refinery_block",
                    "destination_port_id": "ore_in",
                    "link_type": "conveyor",
                },
                {
                    "type": "local.connect_entities",
                    "operational_area_id": "atlas:local",
                    "node_id": "atlas_local_refinery",
                    "owner_node_id": "atlas_local_refinery",
                    "connection_id": "wire_refinery_metal",
                    "source_component_id": "refinery_block",
                    "source_port_id": "metal_out",
                    "destination_component_id": "refinery_storage",
                    "destination_port_id": "metal_in",
                    "link_type": "conveyor",
                },
            ],
        }
    if step_id == "automate_ore_train":
        if "local_ore_to_refinery" not in state.schedules:
            return {
                "kind": "command",
                "label": "Create ore train route",
                "command": _local_schedule_create_command("local_ore_to_refinery"),
            }
        schedule = state.schedules["local_ore_to_refinery"]
        if not schedule.active:
            return _tutorial_schedule_action("local_ore_to_refinery", "Activate ore train route")
        return _tutorial_step_action("Run ore train automation", ticks=3)
    if step_id == "build_refinery_loader":
        return {
            "kind": "command",
            "label": "Install refinery loader",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "component_id": "refinery_loader",
                "entity_id": "refinery_loader",
                "entity_type": "loader",
                "owner_node_id": "atlas_local_refinery",
                "x": 24,
                "y": 15,
                "rotation": 90,
                "rate": 20,
                "power_required": 4,
                "construction_cargo": {CargoType.CONSTRUCTION_MATERIALS.value: 4},
            },
        }
    if step_id == "build_refinery_gateworks_track":
        return {
            "kind": "command",
            "label": "Lay rail to gateworks",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_atlas_refinery_gateworks",
                "origin_node_id": "atlas_local_refinery",
                "destination_node_id": "atlas_gateworks",
                "x": 25,
                "y": 14,
                "rotation": 90,
            },
        }
    if step_id == "automate_metal_train":
        if "local_metal_to_gateworks" not in state.schedules:
            return {
                "kind": "command",
                "label": "Create metal train route",
                "command": _local_schedule_create_command("local_metal_to_gateworks"),
            }
        schedule = state.schedules["local_metal_to_gateworks"]
        if not schedule.active:
            return _tutorial_schedule_action("local_metal_to_gateworks", "Activate metal train route")
        return _tutorial_step_action("Run metal train automation", ticks=3)
    if step_id == "manufacture_gate_components":
        return _tutorial_step_action("Run gateworks production", ticks=2)
    if step_id == "build_gateworks_gate_track":
        return {
            "kind": "command",
            "label": "Lay rail to Railgate terminal",
            "command": {
                "type": "local.place_entity",
                "operational_area_id": "atlas:local",
                "entity_type": "track_segment",
                "link_id": "rail_atlas_gateworks_outbound_gate",
                "origin_node_id": "atlas_gateworks",
                "destination_node_id": "atlas_local_outbound_gate",
                "x": 30,
                "y": 12,
                "rotation": 0,
            },
        }
    if step_id == "deliver_components_to_gate":
        if "local_components_to_gate" not in state.schedules:
            return {
                "kind": "command",
                "label": "Create Railgate component route",
                "command": _local_schedule_create_command("local_components_to_gate"),
            }
        schedule = state.schedules["local_components_to_gate"]
        if not schedule.active:
            return _tutorial_schedule_action(
                "local_components_to_gate",
                "Activate Railgate component route",
            )
        return _tutorial_step_action("Run component train automation", ticks=3)
    if step_id == "complete_outbound_gate":
        return _tutorial_step_action("Complete Railgate construction", ticks=2)
    if step_id == "survey_destination":
        return {
            "kind": "command",
            "label": "Survey Sable Reach",
            "command": {"type": "SurveySpaceSite", "site_id": "site_sable_reach"},
        }
    if step_id == "establish_gate_corridor":
        return {
            "kind": "command",
            "label": "Establish Atlas-Sable Railgate",
            "command": {
                "type": "BuildLink",
                "link_id": "gate_atlas_local_sable",
                "origin": "atlas_local_outbound_gate",
                "destination": "sable_gate_anchor",
                "mode": "gate",
                "travel_ticks": 1,
                "capacity_per_tick": 4,
                "power_required": 80,
                "power_source_world_id": "atlas",
            },
        }
    if step_id == "send_starter_freight":
        if "local_starter_to_sable" not in state.schedules:
            return {
                "kind": "command",
                "label": "Create Sable starter freight route",
                "command": _local_schedule_create_command("local_starter_to_sable"),
            }
        schedule = state.schedules["local_starter_to_sable"]
        if not schedule.active:
            return _tutorial_schedule_action("local_starter_to_sable", "Activate Sable freight")
        return _tutorial_step_action("Run Sable freight automation", ticks=3)
    return None


def _tutorial_local_blockers(state: GameState) -> list[dict[str, object]]:
    """Return readable blockers for the bottom-up local tutorial."""

    blockers: list[dict[str, object]] = []

    def add(code: str, message: str, **extra: object) -> None:
        duplicate = any(
            item.get("code") == code
            and item.get("node_id") == extra.get("node_id")
            and item.get("schedule_id") == extra.get("schedule_id")
            for item in blockers
        )
        if not duplicate:
            blockers.append({"code": code, "message": message, **extra})

    if not _facility_connection_present(state, "atlas_local_mine", "wire_mine_head_to_storage"):
        add(
            "transfer_link_missing",
            "Mine extractor output is not connected to the loading storage bay.",
            node_id="atlas_local_mine",
            connection_id="wire_mine_head_to_storage",
        )
    for link_id, origin, destination in (
        ("rail_atlas_local_mine_refinery", "atlas_local_mine", "atlas_local_refinery"),
        ("rail_atlas_refinery_gateworks", "atlas_local_refinery", "atlas_gateworks"),
        ("rail_atlas_gateworks_outbound_gate", "atlas_gateworks", "atlas_local_outbound_gate"),
    ):
        if link_id not in state.links:
            add(
                "track_missing",
                f"Track is missing between {origin} and {destination}.",
                link_id=link_id,
                origin=origin,
                destination=destination,
            )
    for node_id in ("atlas_local_mine", "atlas_local_refinery", "atlas_gateworks"):
        if not _facility_component_kind_present(state, node_id, "loader"):
            add("missing_loader", f"{node_id} has no loader.", node_id=node_id)
    for node_id in (
        "atlas_local_refinery",
        "atlas_gateworks",
        "atlas_local_outbound_gate",
        "sable_settlement",
    ):
        if not _facility_component_kind_present(state, node_id, "unloader"):
            add("missing_unloader", f"{node_id} has no unloader.", node_id=node_id)
    if not (
        _facility_connection_present(state, "atlas_local_refinery", "wire_refinery_ore")
        and _facility_connection_present(state, "atlas_local_refinery", "wire_refinery_metal")
    ):
        add(
            "conveyor_missing",
            "Refinery storage is not wired through the refinery block.",
            node_id="atlas_local_refinery",
        )
    for schedule_id in (
        "local_ore_to_refinery",
        "local_metal_to_gateworks",
        "local_components_to_gate",
        "local_starter_to_sable",
    ):
        schedule = state.schedules.get(schedule_id)
        if schedule is None:
            add("route_missing", f"Schedule {schedule_id} has not been created.", schedule_id=schedule_id)
            continue
        if not schedule.active:
            add("route_inactive", f"Schedule {schedule_id} is inactive.", schedule_id=schedule_id)
        if schedule.train_id not in state.trains:
            add(
                "missing_train",
                f"Schedule {schedule_id} has no assigned train.",
                schedule_id=schedule_id,
                train_id=schedule.train_id,
            )
        else:
            train = state.trains[schedule.train_id]
            if train.status.value == "blocked" and train.blocked_reason:
                add(
                    str(train.blocked_reason),
                    f"Train {train.id} is blocked: {train.blocked_reason}.",
                    train_id=train.id,
                    schedule_id=schedule_id,
                )
        route = route_through_stops(
            state,
            schedule.origin,
            tuple(_schedule_route_stop_ids(schedule)[1:-1]),
            schedule.destination,
            require_operational=False,
        )
        if route is None:
            add(
                "missing_route",
                f"Schedule {schedule_id} has no connected route.",
                schedule_id=schedule_id,
                origin=schedule.origin,
                destination=schedule.destination,
            )
    for node_id in ("atlas_local_refinery", "atlas_gateworks"):
        if state.facility_blocked.get(node_id):
            entries = [
                _facility_block_entry_payload(entry)
                for entry in state.facility_block_entries
                if isinstance(entry, dict) and entry.get("node") == node_id
            ]
            add(
                "factory_blocked",
                f"{node_id} production is blocked.",
                node_id=node_id,
                details=[entry for entry in entries if entry],
            )
    for node_id in (
        "atlas_local_refinery",
        "atlas_gateworks",
        "atlas_local_outbound_gate",
        "sable_settlement",
    ):
        node = state.nodes.get(node_id)
        if node is not None and node.total_inventory() >= node.effective_storage_capacity():
            add("destination_storage_full", f"{node_id} storage is full.", node_id=node_id)

    project = state.construction_projects.get("proj_atlas_local_outbound_gate")
    if project is not None and project.status != ConstructionStatus.COMPLETED:
        add(
            "gate_not_built",
            "Atlas outbound Railgate terminal is waiting on locally produced components.",
            node_id="atlas_local_outbound_gate",
            construction_project_id=project.id,
            missing=_cargo_map(project.remaining_cargo),
        )
        add(
            "macro_waiting_on_local_output",
            "The macro Railgate network is waiting for locally delivered gate components.",
            node_id="atlas_local_outbound_gate",
        )
    site = state.space_sites.get("site_sable_reach")
    if site is not None and not site.discovered:
        add(
            "destination_not_surveyed",
            "Sable Reach must be surveyed before a Railgate corridor can be opened.",
            site_id=site.id,
        )
    if "gate_atlas_local_sable" not in state.links:
        add(
            "gate_connection_incomplete",
            "Atlas and Sable Reach do not have an active Railgate corridor.",
            link_id="gate_atlas_local_sable",
        )
    starter = state.schedules.get("local_starter_to_sable")
    if starter is not None and starter.active and "gate_atlas_local_sable" not in state.links:
        add(
            "gate_not_built",
            "Starter freight cannot route until the local Railgate corridor exists.",
            schedule_id=starter.id,
        )
    return blockers


def _tutorial_local_logistics_payload(state: GameState) -> dict[str, object] | None:
    """Return backend-owned bottom-up tutorial progress when its scenario is loaded."""

    required_nodes = {
        "atlas_local_mine",
        "atlas_local_refinery",
        "atlas_gateworks",
        "atlas_local_outbound_gate",
        "sable_settlement",
    }
    required_trains = {
        "local_ore_runner",
        "local_metal_runner",
        "local_component_runner",
        "local_starter_runner",
    }
    if (
        not required_nodes.issubset(state.nodes)
        or not required_trains.issubset(state.trains)
        or "proj_atlas_local_outbound_gate" not in state.construction_projects
        or "site_sable_reach" not in state.space_sites
        or "local_sable_starter_cargo" not in state.contracts
    ):
        return None

    statuses = _tutorial_local_statuses(state)
    ore_progress = max(
        _local_schedule_progress(state, "local_ore_to_refinery"),
        _node_stock(state, "atlas_local_refinery", CargoType.ORE),
        _node_stock(state, "atlas_local_refinery", CargoType.METAL),
        _local_schedule_progress(state, "local_metal_to_gateworks"),
    )
    metal_progress = max(
        _local_schedule_progress(state, "local_metal_to_gateworks"),
        _node_stock(state, "atlas_gateworks", CargoType.METAL),
        _node_stock(state, "atlas_gateworks", CargoType.GATE_COMPONENTS),
        _local_project_components(state),
    )
    component_progress = max(
        _local_schedule_progress(state, "local_components_to_gate"),
        _node_stock(state, "atlas_gateworks", CargoType.GATE_COMPONENTS),
        _node_stock(state, "atlas_local_outbound_gate", CargoType.GATE_COMPONENTS),
        _local_project_components(state),
        4 if statuses["complete_outbound_gate"] else 0,
    )
    starter_contract = state.contracts["local_sable_starter_cargo"]
    starter_progress = int(starter_contract.delivered_units)

    steps: list[dict[str, object]] = [
        {
            "id": "connect_mine_storage",
            "label": "Connect extractor output to mine storage",
            "node_id": "atlas_local_mine",
            "target": 1,
            "delivered": 1 if statuses["connect_mine_storage"] else 0,
        },
        {
            "id": "build_mine_refinery_track",
            "label": "Lay track from mine to refinery",
            "link_id": "rail_atlas_local_mine_refinery",
            "target": 1,
            "delivered": 1 if statuses["build_mine_refinery_track"] else 0,
        },
        {
            "id": "build_mine_loader",
            "label": "Install a loader at the mine station",
            "node_id": "atlas_local_mine",
            "target": 1,
            "delivered": 1 if statuses["build_mine_loader"] else 0,
        },
        {
            "id": "build_refinery_unloader",
            "label": "Install an unloader at the refinery",
            "node_id": "atlas_local_refinery",
            "target": 1,
            "delivered": 1 if statuses["build_refinery_unloader"] else 0,
        },
        {
            "id": "wire_refinery_storage",
            "label": "Wire refinery storage through the processing block",
            "node_id": "atlas_local_refinery",
            "target": 1,
            "delivered": 1 if statuses["wire_refinery_storage"] else 0,
        },
        {
            "id": "automate_ore_train",
            "label": "Automate ore train loading and unloading",
            "schedule_id": "local_ore_to_refinery",
            "cargo": CargoType.ORE.value,
            "target": 20,
            "target_units": 20,
            "delivered": min(20, ore_progress),
        },
        {
            "id": "build_refinery_loader",
            "label": "Install a loader for refined metal",
            "node_id": "atlas_local_refinery",
            "target": 1,
            "delivered": 1 if statuses["build_refinery_loader"] else 0,
        },
        {
            "id": "build_refinery_gateworks_track",
            "label": "Lay track from refinery to gateworks",
            "link_id": "rail_atlas_refinery_gateworks",
            "target": 1,
            "delivered": 1 if statuses["build_refinery_gateworks_track"] else 0,
        },
        {
            "id": "automate_metal_train",
            "label": "Automate refined metal delivery to gateworks",
            "schedule_id": "local_metal_to_gateworks",
            "cargo": CargoType.METAL.value,
            "target": 20,
            "target_units": 20,
            "delivered": min(20, metal_progress),
        },
        {
            "id": "manufacture_gate_components",
            "label": "Manufacture Railgate control components",
            "node_id": "atlas_gateworks",
            "cargo": CargoType.GATE_COMPONENTS.value,
            "target": 4,
            "target_units": 4,
            "delivered": min(4, component_progress),
        },
        {
            "id": "build_gateworks_gate_track",
            "label": "Lay track to the Railgate terminal",
            "link_id": "rail_atlas_gateworks_outbound_gate",
            "target": 1,
            "delivered": 1 if statuses["build_gateworks_gate_track"] else 0,
        },
        {
            "id": "deliver_components_to_gate",
            "label": "Deliver components into the Railgate terminal",
            "schedule_id": "local_components_to_gate",
            "cargo": CargoType.GATE_COMPONENTS.value,
            "target": 4,
            "target_units": 4,
            "delivered": min(4, component_progress),
        },
        {
            "id": "complete_outbound_gate",
            "label": "Complete the Atlas outbound Railgate",
            "construction_project_id": "proj_atlas_local_outbound_gate",
            "target": 1,
            "delivered": 1 if statuses["complete_outbound_gate"] else 0,
        },
        {
            "id": "survey_destination",
            "label": "Survey Sable Reach",
            "site_id": "site_sable_reach",
            "target": 1,
            "delivered": 1 if statuses["survey_destination"] else 0,
        },
        {
            "id": "establish_gate_corridor",
            "label": "Establish the Atlas-Sable Railgate corridor",
            "link_id": "gate_atlas_local_sable",
            "target": 1,
            "delivered": 1 if statuses["establish_gate_corridor"] else 0,
        },
        {
            "id": "send_starter_freight",
            "label": "Send automated starter freight to Sable",
            "schedule_id": "local_starter_to_sable",
            "contract_id": "local_sable_starter_cargo",
            "cargo": CargoType.CONSTRUCTION_MATERIALS.value,
            "target": int(starter_contract.target_units),
            "target_units": int(starter_contract.target_units),
            "delivered": starter_progress,
        },
    ]

    active_index: int | None = None
    for index, step in enumerate(steps):
        complete = bool(statuses[str(step["id"])])
        if complete:
            step["status"] = "complete"
        elif active_index is None:
            step["status"] = "active"
            active_index = index
        else:
            step["status"] = "pending"

    all_complete = all(str(step.get("status", "")) == "complete" for step in steps)
    current_step_id = None if all_complete else str(steps[active_index or 0]["id"])
    next_action = None if current_step_id is None else _tutorial_local_next_action(state, current_step_id)
    alerts = [
        {
            "kind": "tutorial",
            "message": (
                "Local logistics tutorial complete: Sable Reach received starter freight "
                "through a Railgate fed by locally manufactured components."
                if all_complete
                else "Tutorial active: build the physical local logistics chain before scaling through the Railgate network."
            ),
        }
    ]
    return {
        "id": "tutorial_local_logistics",
        "title": "Bottom-Up Local Logistics Tutorial",
        "summary": (
            "Connect extractor storage, build rail stations, install loaders and unloaders, "
            "wire refinery transfers, automate trains, manufacture Railgate components, "
            "and open a second-world corridor."
        ),
        "active": not all_complete,
        "current_step_id": current_step_id,
        "steps": steps,
        "alerts": alerts,
        "blockers": _tutorial_local_blockers(state),
        "next_action": next_action,
    }


def _tutorial_local_vertical_loop_payload(state: GameState) -> dict[str, object] | None:
    """Return the local tutorial in the existing vertical_loop display shape."""

    tutorial = _tutorial_local_logistics_payload(state)
    if tutorial is None:
        return None
    return {
        "id": tutorial["id"],
        "title": tutorial["title"],
        "summary": tutorial["summary"],
        "active": tutorial["active"],
        "current_step_id": tutorial["current_step_id"],
        "steps": tutorial["steps"],
        "diagnostics": tutorial["blockers"],
        "next_action": tutorial["next_action"],
    }


def _tutorial_six_worlds_payload(state: GameState) -> dict[str, object] | None:
    """Return backend-owned tutorial loop progress for the six-world starter save."""

    required_schedules = {
        "tutorial_ore_to_cinder",
        "tutorial_metal_to_atlas",
        "tutorial_parts_to_helix",
        "tutorial_parts_to_gateworks",
        "tutorial_electronics_to_gateworks",
        "tutorial_components_to_gate",
        "tutorial_starter_to_sable",
    }
    required_contracts = {"helix_parts_tutorial", "sable_starter_cargo"}
    required_nodes = {
        "cinder_smelter",
        "atlas_factory",
        "atlas_gate_component_line",
        "atlas_outbound_gate",
        "sable_settlement",
    }
    if (
        not required_schedules.issubset(state.schedules)
        or not required_contracts.issubset(state.contracts)
        or not required_nodes.issubset(state.nodes)
        or "site_sable_reach" not in state.space_sites
    ):
        return None

    ore_schedule = state.schedules["tutorial_ore_to_cinder"]
    metal_schedule = state.schedules["tutorial_metal_to_atlas"]
    parts_schedule = state.schedules["tutorial_parts_to_helix"]
    gatework_parts_schedule = state.schedules["tutorial_parts_to_gateworks"]
    gatework_electronics_schedule = state.schedules["tutorial_electronics_to_gateworks"]
    gate_component_schedule = state.schedules["tutorial_components_to_gate"]
    starter_schedule = state.schedules["tutorial_starter_to_sable"]
    parts_contract = state.contracts["helix_parts_tutorial"]
    starter_contract = state.contracts["sable_starter_cargo"]
    cinder_smelter = state.nodes.get("cinder_smelter")
    atlas_factory = state.nodes.get("atlas_factory")
    gateworks = state.nodes.get("atlas_gate_component_line")
    outbound_gate = state.nodes.get("atlas_outbound_gate")
    gate_project = state.construction_projects.get("proj_atlas_outbound_gate")
    destination_site = state.space_sites.get("site_sable_reach")
    parts_cargo = parts_contract.cargo_type or parts_schedule.cargo_type

    cinder_ore = 0 if cinder_smelter is None else cinder_smelter.stock(ore_schedule.cargo_type)
    cinder_metal = 0 if cinder_smelter is None else cinder_smelter.stock(metal_schedule.cargo_type)
    atlas_metal = 0 if atlas_factory is None else atlas_factory.stock(metal_schedule.cargo_type)
    atlas_parts = 0 if atlas_factory is None else atlas_factory.stock(parts_cargo)
    gateworks_parts = 0 if gateworks is None else gateworks.stock(CargoType.PARTS)
    gateworks_electronics = 0 if gateworks is None else gateworks.stock(CargoType.ELECTRONICS)
    gateworks_components = 0 if gateworks is None else gateworks.stock(CargoType.GATE_COMPONENTS)
    outbound_components = 0 if outbound_gate is None else outbound_gate.stock(CargoType.GATE_COMPONENTS)
    project_components = (
        0
        if gate_project is None
        else int(gate_project.delivered_cargo.get(CargoType.GATE_COMPONENTS, 0))
    )
    contract_parts = int(parts_contract.delivered_units)
    starter_progress = int(starter_contract.delivered_units)
    gate_completed = gate_project is not None and gate_project.status.value == "completed"
    destination_surveyed = destination_site is not None and destination_site.discovered
    gate_connected = "gate_atlas_sable" in state.links
    ore_progress = max(
        int(ore_schedule.delivered_units),
        cinder_ore,
        cinder_metal,
        atlas_metal,
        atlas_parts,
        contract_parts,
    )
    metal_progress = max(
        int(metal_schedule.delivered_units),
        atlas_metal,
        atlas_parts,
        contract_parts,
    )
    parts_progress = max(int(parts_schedule.delivered_units), contract_parts)
    gatework_parts_progress = min(
        4,
        max(int(gatework_parts_schedule.delivered_units), gateworks_parts) // 2,
    )
    gatework_electronics_progress = min(
        4,
        max(int(gatework_electronics_schedule.delivered_units), gateworks_electronics),
    )
    gatework_input_progress = min(gatework_parts_progress, gatework_electronics_progress)
    component_progress = max(
        int(gate_component_schedule.delivered_units),
        gateworks_components,
        outbound_components,
        project_components,
        4 if gate_completed else 0,
    )
    if parts_progress >= int(parts_contract.target_units) or atlas_parts >= int(parts_contract.target_units):
        metal_progress = max(metal_progress, 10)
        ore_progress = max(ore_progress, 20)
    elif metal_progress >= 10:
        ore_progress = max(ore_progress, 20)

    steps: list[dict[str, object]] = [
        {
            "id": "mine_ore",
            "label": "Move ore through the Brink-Cinder Railgate corridor",
            "cargo": ore_schedule.cargo_type.value,
            "origin": ore_schedule.origin,
            "destination": ore_schedule.destination,
            "schedule_id": ore_schedule.id,
            "delivered": ore_progress,
            "target": 20,
            "dispatch": {
                "train_id": ore_schedule.train_id,
                "origin": ore_schedule.origin,
                "destination": ore_schedule.destination,
                "cargo": ore_schedule.cargo_type.value,
                "requested_units": 20,
            },
        },
        {
            "id": "smelt_metal",
            "label": "Refine metal for Atlas maintenance works",
            "cargo": metal_schedule.cargo_type.value,
            "origin": metal_schedule.origin,
            "destination": metal_schedule.destination,
            "schedule_id": metal_schedule.id,
            "delivered": metal_progress,
            "target": 10,
            "dispatch": {
                "train_id": metal_schedule.train_id,
                "origin": metal_schedule.origin,
                "destination": metal_schedule.destination,
                "cargo": metal_schedule.cargo_type.value,
                "requested_units": 10,
            },
        },
        {
            "id": "deliver_parts",
            "label": "Deliver maintenance parts to Helix Transit Combine",
            "cargo": parts_cargo.value,
            "origin": parts_schedule.origin,
            "destination": parts_contract.destination_node_id or parts_schedule.destination,
            "schedule_id": parts_schedule.id,
            "contract_id": parts_contract.id,
            "delivered": parts_progress,
            "target": int(parts_contract.target_units),
            "reward_cash": round(parts_contract.reward_cash, 2),
            "reward_reputation": int(parts_contract.reward_reputation),
            "dispatch": {
                "train_id": parts_schedule.train_id,
                "origin": parts_schedule.origin,
                "destination": parts_contract.destination_node_id or parts_schedule.destination,
                "cargo": parts_schedule.cargo_type.value,
                "requested_units": int(parts_contract.target_units),
            },
        },
        {
            "id": "manufacture_gate_components",
            "label": "Manufacture aperture control components at Atlas",
            "cargo": CargoType.GATE_COMPONENTS.value,
            "origin": gate_component_schedule.origin,
            "destination": gate_component_schedule.destination,
            "schedule_id": gate_component_schedule.id,
            "delivered": component_progress,
            "target": 4,
            "input_progress": gatework_input_progress,
            "input_schedules": [
                gatework_parts_schedule.id,
                gatework_electronics_schedule.id,
            ],
        },
        {
            "id": "deploy_outbound_gate",
            "label": "Complete the Atlas outbound Railgate terminal",
            "cargo": CargoType.GATE_COMPONENTS.value,
            "origin": gate_component_schedule.origin,
            "destination": "atlas_outbound_gate",
            "construction_project_id": "proj_atlas_outbound_gate",
            "delivered": 1 if gate_completed else 0,
            "target": 1,
        },
        {
            "id": "survey_destination",
            "label": "Survey the Sable Reach destination corridor",
            "cargo": "survey",
            "origin": "atlas_outbound_gate",
            "destination": "site_sable_reach",
            "site_id": "site_sable_reach",
            "delivered": 1 if destination_surveyed else 0,
            "target": 1,
        },
        {
            "id": "establish_gate_corridor",
            "label": "Establish the Atlas-Sable Railgate corridor",
            "cargo": "railgate",
            "origin": "atlas_outbound_gate",
            "destination": "sable_gate_anchor",
            "link_id": "gate_atlas_sable",
            "delivered": 1 if gate_connected else 0,
            "target": 1,
        },
        {
            "id": "send_starter_freight",
            "label": "Automate starter freight to Sable Reach",
            "cargo": starter_schedule.cargo_type.value,
            "origin": starter_schedule.origin,
            "destination": starter_contract.destination_node_id or starter_schedule.destination,
            "schedule_id": starter_schedule.id,
            "contract_id": starter_contract.id,
            "delivered": starter_progress,
            "target": int(starter_contract.target_units),
            "reward_cash": round(starter_contract.reward_cash, 2),
            "reward_reputation": int(starter_contract.reward_reputation),
        },
    ]

    active_index: int | None = None
    for index, step in enumerate(steps):
        complete = int(step["delivered"]) >= int(step["target"])
        if step["id"] == "deliver_parts" and parts_contract.status.value == "fulfilled":
            complete = True
        if step["id"] == "send_starter_freight" and starter_contract.status.value == "fulfilled":
            complete = True
        if complete:
            step["status"] = "complete"
        elif active_index is None:
            step["status"] = "active"
            active_index = index
        else:
            step["status"] = "pending"

    all_complete = all(str(step.get("status", "")) == "complete" for step in steps)
    if all_complete:
        alerts = [
            {
                "kind": "tutorial",
                "message": "Tutorial loop complete: Sable Reach received its automated starter freight through the new Railgate corridor.",
            }
        ]
        current_step_id = None
        next_action = None
    else:
        active_step = steps[active_index or 0]
        current_step_id = str(active_step["id"])
        next_action = _tutorial_next_action_for_step(state, current_step_id)
        alert_messages = {
            "mine_ore": "Tutorial active: move ore through the Brink-Cinder Railgate corridor.",
            "smelt_metal": "Tutorial active: refine ore into metal and move it to Atlas maintenance works.",
            "deliver_parts": "Tutorial active: build maintenance parts at Atlas and ship them to Helix Transit Combine.",
            "manufacture_gate_components": "Tutorial active: feed the Atlas gateworks and manufacture aperture control components.",
            "deploy_outbound_gate": "Tutorial active: deliver aperture control components to complete the Atlas outbound Railgate terminal.",
            "survey_destination": "Tutorial active: survey Sable Reach before opening a new Railgate corridor.",
            "establish_gate_corridor": "Tutorial active: establish the Atlas-Sable Railgate corridor.",
            "send_starter_freight": "Tutorial active: automate starter freight through the new Railgate corridor.",
        }
        alerts = [
            {
                "kind": "tutorial",
                "message": alert_messages.get(current_step_id, "Tutorial active."),
            }
        ]

    return {
        "id": "tutorial_six_worlds",
        "title": "Railgate Age Tutorial Start",
        "summary": "Move ore through a Railgate corridor, refine metal, manufacture aperture control components, deploy an outbound Railgate, and automate starter freight to Sable Reach.",
        "active": not all_complete,
        "current_step_id": current_step_id,
        "steps": steps,
        "alerts": alerts,
        "blockers": _tutorial_six_worlds_blockers(state),
        "next_action": next_action,
    }


def _tutorial_schedule_action(schedule_id: str, label: str) -> dict[str, object]:
    """Return a command action that enables one tutorial schedule."""

    return {
        "kind": "command",
        "label": label,
        "command": {
            "type": "SetScheduleEnabled",
            "schedule_id": schedule_id,
            "enabled": True,
        },
    }


def _tutorial_step_action(label: str, ticks: int = 3) -> dict[str, object]:
    """Return a command action that lets already-enabled automation run."""

    return {"kind": "step_ticks", "label": label, "ticks": ticks}


def _tutorial_next_action_for_step(state: GameState, step_id: str) -> dict[str, object] | None:
    """Return the next backend-owned tutorial action for one active step."""

    schedule_actions = {
        "mine_ore": ("tutorial_ore_to_cinder", "Activate ore haul"),
        "smelt_metal": ("tutorial_metal_to_atlas", "Activate metal haul"),
        "deliver_parts": ("tutorial_parts_to_helix", "Activate Helix parts haul"),
        "send_starter_freight": ("tutorial_starter_to_sable", "Activate Sable starter freight"),
    }
    if step_id in schedule_actions:
        schedule_id, label = schedule_actions[step_id]
        schedule = state.schedules.get(schedule_id)
        if schedule is not None and not schedule.active:
            return _tutorial_schedule_action(schedule_id, label)
        return _tutorial_step_action("Run active freight automation")

    if step_id == "manufacture_gate_components":
        command_payloads: list[dict[str, object]] = []
        for schedule_id in (
            "tutorial_parts_to_gateworks",
            "tutorial_electronics_to_gateworks",
            "tutorial_components_to_gate",
        ):
            schedule = state.schedules.get(schedule_id)
            if schedule is not None and not schedule.active:
                command_payloads.append(
                    {
                        "type": "SetScheduleEnabled",
                        "schedule_id": schedule_id,
                        "enabled": True,
                    }
                )
        if command_payloads:
            return {
                "kind": "commands",
                "label": "Activate gateworks automation",
                "commands": command_payloads,
            }
        return _tutorial_step_action("Run gateworks automation")

    if step_id == "deploy_outbound_gate":
        project = state.construction_projects.get("proj_atlas_outbound_gate")
        component_schedule = state.schedules.get("tutorial_components_to_gate")
        if (
            project is not None
            and project.status.value != "completed"
            and component_schedule is not None
            and not component_schedule.active
        ):
            return _tutorial_schedule_action(
                "tutorial_components_to_gate",
                "Deliver Railgate components",
            )
        return _tutorial_step_action("Complete outbound Railgate construction")

    if step_id == "survey_destination":
        return {
            "kind": "command",
            "label": "Survey Sable Reach",
            "command": {"type": "SurveySpaceSite", "site_id": "site_sable_reach"},
        }

    if step_id == "establish_gate_corridor":
        return {
            "kind": "command",
            "label": "Establish Atlas-Sable Railgate",
            "command": {
                "type": "BuildLink",
                "link_id": "gate_atlas_sable",
                "origin": "atlas_outbound_gate",
                "destination": "sable_gate_anchor",
                "mode": "gate",
                "travel_ticks": 1,
                "capacity_per_tick": 4,
                "power_required": 80,
                "power_source_world_id": "atlas",
            },
        }

    return None


def _tutorial_recipe_shortfall(node: object | None) -> dict[str, int]:
    """Return missing cargo for a tutorial node recipe."""

    if node is None or getattr(node, "recipe", None) is None:
        return {}
    missing: dict[str, int] = {}
    for cargo, units in node.recipe.inputs.items():
        deficit = int(units) - int(node.stock(cargo))
        if deficit > 0:
            missing[cargo.value] = deficit
    return missing


def _tutorial_six_worlds_blockers(state: GameState) -> list[dict[str, object]]:
    """Return stable blocker diagnostics for the tutorial vertical slice."""

    blockers: list[dict[str, object]] = []
    for node_id in ("cinder_smelter", "atlas_factory", "atlas_gate_component_line"):
        missing = _tutorial_recipe_shortfall(state.nodes.get(node_id))
        if missing:
            blockers.append(
                {
                    "code": "missing_recipe_input",
                    "node_id": node_id,
                    "message": f"{node_id} is waiting for recipe input.",
                    "missing": missing,
                }
            )

    project = state.construction_projects.get("proj_atlas_outbound_gate")
    if project is not None and project.status.value != "completed":
        blockers.append(
            {
                "code": "gate_not_built",
                "node_id": "atlas_outbound_gate",
                "construction_project_id": project.id,
                "message": "Atlas outbound Railgate terminal is not complete.",
                "missing": {
                    cargo.value: units
                    for cargo, units in sorted(
                        project.remaining_cargo.items(),
                        key=lambda item: item[0].value,
                    )
                },
            }
        )

    site = state.space_sites.get("site_sable_reach")
    if site is not None and not site.discovered:
        blockers.append(
            {
                "code": "destination_not_surveyed",
                "site_id": site.id,
                "message": "Sable Reach must be surveyed before the Railgate corridor is opened.",
            }
        )

    if "gate_atlas_sable" not in state.links:
        blockers.append(
            {
                "code": "gate_connection_incomplete",
                "link_id": "gate_atlas_sable",
                "message": "Atlas and Sable Reach do not have an active Railgate corridor.",
            }
        )

    starter_schedule = state.schedules.get("tutorial_starter_to_sable")
    if starter_schedule is not None and starter_schedule.active and "gate_atlas_sable" not in state.links:
        blockers.append(
            {
                "code": "missing_route",
                "schedule_id": starter_schedule.id,
                "message": "Starter freight schedule is active but no Atlas-Sable route exists.",
            }
        )

    return blockers


def _node_stock(state: GameState, node_id: str, cargo_type: CargoType) -> int:
    """Return stored cargo for one node, or zero when absent."""

    node = state.nodes.get(node_id)
    return 0 if node is None else node.stock(cargo_type)


def _contract_fulfilled(state: GameState, contract_id: str) -> bool:
    """Return whether one contract has reached fulfilled status."""

    contract = state.contracts.get(contract_id)
    return contract is not None and contract.status.value == "fulfilled"


def _completed_mining_mission_for_site(state: GameState, site_id: str) -> bool:
    """Return whether any mining mission for a site has completed."""

    return any(
        mission.site_id == site_id and mission.status.value == "completed"
        for mission in state.mining_missions.values()
    )


def _vertical_loop_statuses(state: GameState) -> dict[str, bool]:
    """Return canonical completion signals for the mining-to-manufacturing slice."""

    site = state.space_sites.get("site_brink_belt")
    yard = state.nodes.get("frontier_extraction_yard")
    ore_schedule = state.schedules.get("ore_haul_to_core")
    metal_schedule = state.schedules.get("metal_to_assembly_yard")

    support_complete = _contract_fulfilled(state, "frontier_parts_upgrade")
    stabilization_complete = _contract_fulfilled(state, "frontier_colony_stabilization")
    downstream_parts = (
        _node_stock(state, "core_yard", CargoType.PARTS)
        + _node_stock(state, "frontier_settlement", CargoType.PARTS)
    )
    downstream_metal = (
        _node_stock(state, "core_smelter", CargoType.METAL)
        + _node_stock(state, "core_yard", CargoType.METAL)
        + downstream_parts
    )
    ore_progress = int(ore_schedule.delivered_units) if ore_schedule is not None else 0
    metal_progress = int(metal_schedule.delivered_units) if metal_schedule is not None else 0

    extraction_complete = (
        yard is not None
        and yard.kind == NodeKind.ORBITAL_YARD
        and yard.construction_project_id is None
    )
    ore_extracted = (
        _completed_mining_mission_for_site(state, "site_brink_belt")
        or _node_stock(state, "frontier_collection", CargoType.ORE) > 0
        or ore_progress > 0
        or downstream_metal > 0
    )
    ore_delivered = (
        ore_progress >= 20
        or _node_stock(state, "core_smelter", CargoType.ORE) > 0
        or downstream_metal > 0
    )
    metal_processed = (
        _node_stock(state, "core_smelter", CargoType.METAL) > 0
        or metal_progress > 0
        or _node_stock(state, "core_yard", CargoType.METAL) > 0
        or downstream_parts > 0
    )
    metal_delivered = (
        metal_progress >= 10
        or _node_stock(state, "core_yard", CargoType.METAL) > 0
        or downstream_parts > 0
    )
    parts_built = downstream_parts > 0 or support_complete

    return {
        "survey_source": bool(site is not None and site.discovered),
        "build_extraction": extraction_complete,
        "extract_ore": ore_extracted,
        "deliver_ore": ore_delivered,
        "process_metal": metal_processed,
        "deliver_metal": metal_delivered,
        "manufacture_parts": parts_built,
        "support_colony": support_complete,
        "stabilize_colony": stabilization_complete,
        "unlock_next_problem": stabilization_complete,
    }


def _vertical_loop_diagnostics(state: GameState) -> list[dict[str, object]]:
    """Return stable blocker diagnostics for the canonical vertical slice."""

    diagnostics: list[dict[str, object]] = []
    seen: set[str] = set()

    def add(code: str, message: str, **extra: object) -> None:
        if code in seen:
            return
        seen.add(code)
        diagnostics.append({"code": code, "message": message, **extra})

    site = state.space_sites.get("site_brink_belt")
    yard = state.nodes.get("frontier_extraction_yard")
    statuses = _vertical_loop_statuses(state)

    if site is not None and not site.discovered:
        add(
            "site_not_surveyed",
            "Brink Asteroid Belt has not been surveyed.",
            site_id=site.id,
        )
    if site is not None and site.discovered and yard is None:
        add(
            "extraction_not_built",
            "No extraction yard exists for surveyed Brink ore.",
            node_id="frontier_extraction_yard",
        )
    if yard is not None and yard.construction_project_id is not None:
        add(
            "extraction_under_construction",
            "Brink Extraction Yard still needs construction cargo.",
            node_id=yard.id,
            construction_project_id=yard.construction_project_id,
        )
    if (
        not statuses["extract_ore"]
        and _node_stock(state, "frontier_collection", CargoType.ORE) <= 0
    ):
        add(
            "no_source_cargo",
            "The receiving terminal has no ore available for the first haul.",
            node_id="frontier_collection",
            cargo="ore",
        )

    for schedule_id in (
        "ore_haul_to_core",
        "metal_to_assembly_yard",
        "parts_to_frontier_settlement",
    ):
        schedule = state.schedules.get(schedule_id)
        if schedule is None:
            continue
        if schedule.active and schedule.train_id not in state.trains:
            add(
                "missing_train",
                f"Schedule {schedule_id} has no assigned train.",
                schedule_id=schedule_id,
                train_id=schedule.train_id,
            )
        if schedule.origin in state.nodes and schedule.destination in state.nodes:
            route = route_through_stops(
                state,
                schedule.origin,
                schedule.stops,
                schedule.destination,
                require_operational=False,
            )
            if route is None:
                add(
                    "no_route",
                    f"Schedule {schedule_id} has no connected route.",
                    schedule_id=schedule_id,
                    origin=schedule.origin,
                    destination=schedule.destination,
                )

    for node in sorted(state.nodes.values(), key=lambda item: item.id):
        if node.total_inventory() < node.effective_storage_capacity():
            continue
        if node.kind == NodeKind.DEPOT:
            add("depot_full", f"Depot {node.id} is full.", node_id=node.id)
        elif node.kind == NodeKind.WAREHOUSE:
            add("warehouse_full", f"Warehouse {node.id} is full.", node_id=node.id)

    for link_id, status in sorted(preview_gate_power(state).items()):
        if status.power_shortfall > 0:
            add(
                "missing_power",
                f"Railgate {link_id} needs more power.",
                link_id=link_id,
                power_shortfall=status.power_shortfall,
            )
        if status.slot_capacity > 0 and status.slots_used >= status.slot_capacity:
            add(
                "railgate_capacity_exceeded",
                f"Railgate {link_id} is at corridor capacity.",
                link_id=link_id,
                slots_used=status.slots_used,
                slot_capacity=status.slot_capacity,
            )

    if state.shortages.get("frontier_settlement"):
        add(
            "colony_shortage",
            "Brink Colony Logistics Hub has an active shortage.",
            node_id="frontier_settlement",
            shortages=_cargo_map(state.shortages["frontier_settlement"]),
        )
    for node_id in ("core_smelter", "core_yard"):
        blocked = state.recipe_blocked.get(node_id)
        if blocked:
            add(
                "recipe_input_missing",
                f"Recipe at {node_id} is missing input cargo.",
                node_id=node_id,
                missing=_cargo_map(blocked),
            )
            break

    return diagnostics


def _vertical_loop_payload(state: GameState) -> dict[str, object] | None:
    """Return the first complete Factorio/OpenTTD-style loop payload, when present."""

    required = {
        "site_brink_belt",
    }
    if not required.issubset(state.space_sites):
        return None
    if (
        "ore_haul_to_core" not in state.schedules
        or "frontier_parts_upgrade" not in state.contracts
    ):
        return None

    statuses = _vertical_loop_statuses(state)
    support_contract = state.contracts.get("frontier_colony_stabilization")
    parts_contract = state.contracts.get("frontier_parts_upgrade")
    metal_schedule = state.schedules.get("metal_to_assembly_yard")
    steps: list[dict[str, object]] = [
        {
            "id": "survey_source",
            "label": "Survey Brink Asteroid Belt",
            "target": "site_brink_belt",
            "complete": statuses["survey_source"],
            "command": {"type": "SurveySpaceSite", "site_id": "site_brink_belt"},
        },
        {
            "id": "build_extraction",
            "label": "Build Brink Extraction Yard",
            "target": "frontier_extraction_yard",
            "complete": statuses["build_extraction"],
        },
        {
            "id": "extract_ore",
            "label": "Launch ore extraction mission",
            "target": "mission_loop",
            "complete": statuses["extract_ore"],
        },
        {
            "id": "deliver_ore",
            "label": "Haul ore to Vesta Arc Smelter",
            "schedule_id": "ore_haul_to_core",
            "delivered": int(state.schedules["ore_haul_to_core"].delivered_units),
            "target_units": 20,
            "complete": statuses["deliver_ore"],
        },
        {
            "id": "process_metal",
            "label": "Refine ore into metal",
            "node_id": "core_smelter",
            "complete": statuses["process_metal"],
        },
        {
            "id": "deliver_metal",
            "label": "Move metal to Vesta Manufacturing Yard",
            "schedule_id": "metal_to_assembly_yard",
            "delivered": 0 if metal_schedule is None else int(metal_schedule.delivered_units),
            "target_units": 10,
            "complete": statuses["deliver_metal"],
        },
        {
            "id": "manufacture_parts",
            "label": "Manufacture maintenance parts",
            "node_id": "core_yard",
            "complete": statuses["manufacture_parts"],
        },
        {
            "id": "support_colony",
            "label": "Deliver parts to Brink Colony Logistics Hub",
            "schedule_id": "parts_to_frontier_settlement",
            "contract_id": "frontier_parts_upgrade",
            "delivered": 0 if parts_contract is None else int(parts_contract.delivered_units),
            "target_units": 10,
            "complete": statuses["support_colony"],
        },
        {
            "id": "stabilize_colony",
            "label": "Stabilize Brink Frontier Colony",
            "contract_id": "frontier_colony_stabilization",
            "progress": 0 if support_contract is None else int(support_contract.progress),
            "target_units": 0 if support_contract is None else int(support_contract.target_units),
            "complete": statuses["stabilize_colony"],
        },
        {
            "id": "unlock_next_problem",
            "label": "Unlock frontier machinery supply",
            "complete": False,
        },
    ]

    active_assigned = False
    for step in steps[:-1]:
        if bool(step.pop("complete")):
            step["status"] = "complete"
            continue
        if not active_assigned:
            step["status"] = "active"
            active_assigned = True
        else:
            step["status"] = "pending"

    unlock_step = steps[-1]
    unlock_step.pop("complete", None)
    if statuses["unlock_next_problem"]:
        unlock_step["status"] = "active"
    else:
        unlock_step["status"] = "pending"

    active_step = next((step for step in steps if step.get("status") == "active"), None)
    unlocked_problem = (
        {
            "id": "frontier_machinery_supply",
            "label": "Ship machinery to expand Brink extraction throughput",
            "cargo": "machinery",
            "origin": "core_yard",
            "destination": "frontier_settlement",
        }
        if statuses["unlock_next_problem"]
        else None
    )

    return {
        "id": "mining_to_manufacturing",
        "title": "Railgate Age Vertical Loop",
        "summary": (
            "Survey a frontier source, build extraction, move ore by rail, refine metal, "
            "manufacture parts, and stabilize Brink through a Railgate corridor."
        ),
        "active": not statuses["stabilize_colony"],
        "current_step_id": None if active_step is None else active_step["id"],
        "steps": steps,
        "diagnostics": _vertical_loop_diagnostics(state),
        "next_action": active_step,
        "unlocked_problem": unlocked_problem,
    }


def _cargo_flow_payloads(state: GameState) -> list[dict[str, object]]:
    """Return route-level cargo flow visualisation payloads."""

    in_transit_by_schedule: dict[str, int] = {}
    train_count_by_schedule: dict[str, int] = {}
    for train in state.trains.values():
        order_id = train.order_id or ""
        if not order_id.startswith(SCHEDULE_ORDER_PREFIX):
            continue
        schedule_id = order_id.removeprefix(SCHEDULE_ORDER_PREFIX)
        in_transit_by_schedule[schedule_id] = (
            in_transit_by_schedule.get(schedule_id, 0) + int(train.cargo_units)
        )
        train_count_by_schedule[schedule_id] = train_count_by_schedule.get(schedule_id, 0) + 1

    flows: list[dict[str, object]] = []
    for schedule in sorted(state.schedules.values(), key=lambda item: item.id):
        route_stop_ids = _schedule_route_stop_ids(schedule)
        route = _route_for_schedule_snapshot(state, schedule)
        flows.append(
            {
                "id": f"{SCHEDULE_ORDER_PREFIX}{schedule.id}",
                "service_type": "schedule",
                "schedule_id": schedule.id,
                "train_id": schedule.train_id,
                "active": schedule.active,
                "cargo": schedule.cargo_type.value,
                "route_stop_ids": route_stop_ids,
                "route_node_ids": [] if route is None else list(route.node_ids),
                "route_link_ids": [] if route is None else list(route.link_ids),
                "route_travel_ticks": 0 if route is None else route.travel_ticks,
                "route_valid": route is not None,
                "units_per_departure": schedule.units_per_departure,
                "interval_ticks": schedule.interval_ticks,
                "next_departure_tick": schedule.next_departure_tick,
                "delivered_units": schedule.delivered_units,
                "in_transit_units": in_transit_by_schedule.get(schedule.id, 0),
                "trips_dispatched": schedule.trips_dispatched,
                "trips_completed": schedule.trips_completed,
                "trains_in_transit": train_count_by_schedule.get(schedule.id, 0),
            }
        )
    return flows


def render_snapshot(state: GameState) -> dict[str, object]:
    """Return a compact, stable JSON snapshot for render clients."""

    gate_statuses = state.gate_statuses if state.gate_statuses else preview_gate_power(state)
    signal_report = build_signal_report(state)
    rail_blocks = signal_report.get("blocks", {})
    if not isinstance(rail_blocks, dict):
        rail_blocks = {}
    power_plants_by_node: dict[str, list[str]] = {}
    for plant in state.power_plants.values():
        power_plants_by_node.setdefault(plant.node_id, []).append(plant.id)
    world_ids = sorted(state.worlds)
    world_index = {world_id: index for index, world_id in enumerate(world_ids)}

    worlds = []
    for world_id in world_ids:
        world = state.worlds[world_id]
        deposit_ids = [
            deposit.id
            for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id)
            if deposit.world_id == world_id
        ]
        worlds.append(
            {
                "id": world.id,
                "name": world.name,
                "tier": int(world.tier),
                "tier_name": world.tier.name.lower(),
                "population": world.population,
                "stability": round(world.stability, 3),
                "specialization": world.specialization,
                "power_available": world.power_available,
                "power_used": world.power_used,
                "power_pressure": (
                    round(world.power_used / world.power_available, 3)
                    if world.power_available > 0
                    else 0.0
                ),
                "power": {
                    "available": world.power_available,
                    "generated": world.power_generated_this_tick,
                    "used": world.power_used,
                    "gate_used": world.gate_power_used,
                    "margin": world.power_margin,
                },
                "progression": {
                    "progress": world.development_progress,
                    "support_streak": world.support_streak,
                    "shortage_streak": world.shortage_streak,
                    "trend": world.last_trend.value,
                },
                "position": _world_position(world_index[world_id], len(world_ids)),
                "deposits": deposit_ids,
            }
        )

    nodes = []
    # Count trains per link for utilisation
    trains_per_link: dict[str, int] = {}
    for train in state.trains.values():
        for link_id in train.route_link_ids:
            trains_per_link[link_id] = trains_per_link.get(link_id, 0) + 1

    for node in sorted(state.nodes.values(), key=lambda item: item.id):
        node_shortages = state.shortages.get(node.id, {})
        used = node.total_inventory()
        effective_capacity = node.effective_storage_capacity()
        capacity = max(1, effective_capacity)
        transfer_used = int(state.transfer_used_this_tick.get(node.id, 0))
        effective_transfer = int(node.effective_combined_rate())
        transfer_pressure = (
            round(transfer_used / effective_transfer, 3) if effective_transfer > 0 else 0.0
        )
        saturation_streak = int(state.transfer_saturation_streak.get(node.id, 0))
        if node.recipe is None:
            recipe_payload: dict[str, dict[str, int]] | None = None
        else:
            recipe_payload = {
                "inputs": _cargo_map(node.recipe.inputs),
                "outputs": _cargo_map(node.recipe.outputs),
            }
        if node.resource_recipe is None:
            resource_recipe_payload: dict[str, object] | None = None
        else:
            resource_recipe_payload = {
                "id": node.resource_recipe.id,
                "kind": node.resource_recipe.kind.value,
                "inputs": _resource_map(node.resource_recipe.inputs),
                "outputs": _resource_map(node.resource_recipe.outputs),
            }
        recipe_blocked_payload = _cargo_map(state.recipe_blocked.get(node.id, {}))
        resource_recipe_blocked_payload = _resource_map(state.resource_recipe_blocked.get(node.id, {}))
        if node.facility is None:
            facility_payload: dict[str, object] | None = None
        else:
            facility_payload = facility_summary(node.facility)
        facility_blocked_payload = list(state.facility_blocked.get(node.id, []))
        facility_block_entries_payload = [
            payload
            for payload in (
                _facility_block_entry_payload(entry)
                for entry in state.facility_block_entries
                if isinstance(entry, dict) and entry.get("node") == node.id
            )
            if payload
        ]
        loader_summary_payload = {
            "effective_loader_rate": int(node.effective_outbound_rate()),
            "effective_unloader_rate": int(node.effective_inbound_rate()),
            "platform_queue_depth": int(state.platform_queue_depth_this_tick.get(node.id, 0)),
        }
        node_power_required = (
            int(node.facility.power_required()) if node.facility is not None else 0
        )
        overlay_pip: dict[str, str] | None = None
        if facility_blocked_payload:
            block_reason = next(
                (
                    entry.get("reason")
                    for entry in state.facility_block_entries
                    if isinstance(entry, dict) and entry.get("node") == node.id
                ),
                None,
            )
            reason_value = (
                block_reason.value if hasattr(block_reason, "value") else str(block_reason)
            )
            overlay_pip = {
                "layer": "facility_block_layer",
                "severity": "warn",
                "label": reason_value.replace("_", " ") if reason_value else "blocked",
            }
        elif node.outpost_kind is not None:
            project = (
                state.construction_projects.get(node.construction_project_id)
                if node.construction_project_id
                else None
            )
            if project is None or project.status != ConstructionStatus.COMPLETED:
                overlay_pip = {
                    "layer": "outpost_layer",
                    "severity": "info",
                    "label": "outpost in construction",
                }
        elif node_power_required > 0:
            overlay_pip = {
                "layer": "power_layer",
                "severity": "info",
                "label": "power draw",
            }
        is_buffer = node.kind in BUFFER_NODE_KINDS
        if is_buffer:
            buffer_fill_pct: float | None = round(used / capacity, 3)
            served_source = state.buffer_distribution.get(node.id, {})
            served_last_tick: dict[str, dict[str, int]] = {
                target_id: {
                    cargo.value: int(units)
                    for cargo, units in sorted(cargo_map.items(), key=lambda item: item[0].value)
                    if int(units) > 0
                }
                for target_id, cargo_map in sorted(served_source.items())
                if cargo_map
            }
        else:
            buffer_fill_pct = None
            served_last_tick = {}
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "world_id": node.world_id,
                "kind": node.kind.value,
                "inventory": _cargo_map(node.inventory),
                "resource_inventory": _resource_map(node.resource_inventory),
                "demand": _cargo_map(node.demand),
                "production": _cargo_map(node.production),
                "resource_demand": _resource_map(node.resource_demand),
                "resource_production": _resource_map(node.resource_production),
                "storage": {
                    "used": used,
                    "capacity": effective_capacity,
                    "base_capacity": node.storage_capacity,
                },
                "pressure": round(used / capacity, 3),
                "shortages": _cargo_map(node_shortages),
                "transfer_limit": effective_transfer,
                "base_transfer_limit": node.transfer_limit_per_tick,
                "transfer_used": transfer_used,
                "transfer_pressure": transfer_pressure,
                "effective_inbound_rate": int(node.effective_inbound_rate()),
                "effective_outbound_rate": int(node.effective_outbound_rate()),
                "saturation_streak": saturation_streak,
                "buffer_fill_pct": buffer_fill_pct,
                "served_last_tick": served_last_tick,
                "recipe": recipe_payload,
                "recipe_blocked": recipe_blocked_payload,
                "resource_recipe": resource_recipe_payload,
                "resource_recipe_blocked": resource_recipe_blocked_payload,
                "resource_deposit_id": node.resource_deposit_id,
                "requires_facility_handling": node.requires_facility_handling,
                "facility": facility_payload,
                "facility_blocked": facility_blocked_payload,
                "facility_block_entries": facility_block_entries_payload,
                "loader_summary": loader_summary_payload,
                "power_plants": sorted(power_plants_by_node.get(node.id, [])),
                "construction_project_id": node.construction_project_id,
                "outpost_kind": node.outpost_kind.value if node.outpost_kind else None,
                "power_required": node_power_required,
                "overlay_pip": overlay_pip,
                "layout": _node_layout(node),
            }
        )

    links = []
    for link in sorted(state.links.values(), key=lambda item: item.id):
        capacity, disruptions = effective_link_capacity(state, link)
        gate_status = gate_statuses.get(link.id)
        link_signals = active_signals_for_link(state, link.id)
        block_payload = rail_blocks.get(link.id)
        if gate_status is None or gate_status.support_id is None:
            gate_support_payload: dict[str, object] | None = None
        else:
            gate_support_payload = {
                "id": gate_status.support_id,
                "node_id": gate_status.support_node_id,
                "inputs": _resource_map(gate_status.support_inputs),
                "missing": _resource_map(gate_status.support_missing),
                "power_bonus": gate_status.resource_power_bonus,
                "base_power_required": (
                    gate_status.power_required
                    if gate_status.base_power_required is None
                    else gate_status.base_power_required
                ),
                "effective_power_required": gate_status.power_required,
                "available": not gate_status.support_missing and gate_status.resource_power_bonus > 0,
            }
        trains_on_link = trains_per_link.get(link.id, 0)
        utilisation = round(trains_on_link / max(1, link.capacity_per_tick), 3)
        reverse_link_id = _reverse_link_id_for(state, link)
        links.append(
            {
                "id": link.id,
                "origin": link.origin,
                "destination": link.destination,
                "mode": link.mode.value,
                "travel_ticks": link.travel_ticks,
                "capacity": capacity,
                "base_capacity": link.capacity_per_tick,
                "active": link.active,
                "bidirectional": link.bidirectional,
                "directional": not link.bidirectional,
                "source_node_id": link.origin,
                "exit_node_id": link.destination,
                "reverse_available": link.bidirectional or reverse_link_id is not None,
                "reverse_link_id": reverse_link_id,
                "power_required": link.power_required,
                "effective_power_required": (
                    link.power_required if gate_status is None else gate_status.power_required
                ),
                "gate_support": gate_support_payload,
                "powered": None if link.mode != LinkMode.GATE or gate_status is None else gate_status.powered,
                "slots_used": 0 if gate_status is None else gate_status.slots_used,
                "charge_pct": 1.0 if gate_status is None else gate_status.charge_pct,
                "next_activation_tick": None if gate_status is None else gate_status.next_activation_tick,
                "slot_cargo": {} if gate_status is None else _cargo_map(gate_status.slot_cargo),
                "build_cost": round(link.build_cost, 2),
                "build_time": link.build_time,
                "disrupted": bool(disruptions),
                "disruption_reasons": [disruption.reason for disruption in disruptions],
                "utilisation": utilisation,
                "trains_on_link": trains_on_link,
                "alignment": _track_alignment(link),
                "signals": [signal.id for signal in link_signals],
                "rail_block": block_payload,
            }
        )

    trains = [
        {
            "id": train.id,
            "name": train.name,
            "node_id": train.node_id,
            "status": train.status.value,
            "destination": train.destination,
            "capacity": train.capacity,
            "consist": train.consist.value,
            "cargo": None if train.cargo_type is None else train.cargo_type.value,
            "cargo_units": train.cargo_units,
            "remaining_ticks": train.remaining_ticks,
            "route_node_ids": list(train.route_node_ids),
            "route_link_ids": list(train.route_link_ids),
            "order_id": train.order_id,
            "blocked_reason": train.blocked_reason,
            "current_stop_index": train.current_stop_index,
            "arrival_tick": train.arrival_tick,
        }
        for train in sorted(state.trains.values(), key=lambda item: item.id)
    ]

    schedules = [
        {
            "id": schedule.id,
            "train_id": schedule.train_id,
            "origin": schedule.origin,
            "destination": schedule.destination,
            "stops": list(schedule.stops),
            "route_stop_ids": _schedule_route_stop_ids(schedule),
            "train_stops": [_serialize_train_stop(s) for s in schedule.train_stops],
            "cargo": schedule.cargo_type.value,
            "units_per_departure": schedule.units_per_departure,
            "interval_ticks": schedule.interval_ticks,
            "next_departure_tick": schedule.next_departure_tick,
            "priority": schedule.priority,
            "active": schedule.active,
            "return_to_origin": schedule.return_to_origin,
            "trips_dispatched": schedule.trips_dispatched,
            "trips_completed": schedule.trips_completed,
            "delivered_units": schedule.delivered_units,
        }
        for schedule in sorted(state.schedules.values(), key=lambda item: item.id)
    ]

    orders = [
        {
            "id": order.id,
            "train_id": order.train_id,
            "origin": order.origin,
            "destination": order.destination,
            "cargo": order.cargo_type.value,
            "requested_units": order.requested_units,
            "delivered_units": order.delivered_units,
            "remaining_units": order.remaining_units,
            "priority": order.priority,
            "active": order.active,
            "train_stops": [_serialize_train_stop(s) for s in order.train_stops],
        }
        for order in sorted(state.orders.values(), key=lambda item: item.id)
    ]

    contracts = []
    for contract in sorted(state.contracts.values(), key=lambda item: item.id):
        cargo, destination, progress = _contract_progress(contract)
        contracts.append(
            {
                "id": contract.id,
                "kind": contract.kind.value,
                "title": contract.title,
                "client": contract.client,
                "cargo": cargo,
                "destination": destination,
                "progress": progress,
                "target": contract.target_units,
                "due_tick": contract.due_tick,
                "status": contract.status.value,
                "reward_cash": round(contract.reward_cash, 2),
                "penalty_cash": round(contract.penalty_cash, 2),
                "reward_reputation": contract.reward_reputation,
                "penalty_reputation": contract.penalty_reputation,
                "resolved_tick": contract.resolved_tick,
            }
        )

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "tick": state.tick,
        "finance": state.finance.snapshot(),
        "construction_inventory": _cargo_map(state.construction_inventory),
        "reputation": state.reputation,
        "scenario_catalog": _scenario_catalog_payload(),
        "cargo_catalog": cargo_catalog_payload(),
        "tutorial": _tutorial_local_logistics_payload(state) or _tutorial_six_worlds_payload(state),
        "vertical_loop": _tutorial_local_vertical_loop_payload(state) or _vertical_loop_payload(state),
        "operational_areas": operational_areas_payload(state),
        "local_rail": build_local_rail_diagnostics(state),
        "resources": resource_catalog_payload(),
        "resource_deposits": [
            resource_deposit_to_dict(deposit, include_resource=True)
            for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id)
        ],
        "resource_branch_pressure": resource_branch_pressure(state),
        "facility_blocked_entries": [
            payload
            for payload in (
                _facility_block_entry_payload(entry)
                for entry in state.facility_block_entries
            )
            if payload
        ],
        "track_signals": [
            {"id": signal_id, **payload}
            for signal_id, payload in sorted(signal_report["signals"].items())
        ],
        "rail_blocks": [
            block
            for _, block in sorted(rail_blocks.items())
        ],
        "power_generation": {
            world_id: int(power)
            for world_id, power in sorted(state.power_generation_this_tick.items())
        },
        "power_plants": [
            {
                "id": plant.id,
                "node_id": plant.node_id,
                "world_id": state.nodes[plant.node_id].world_id,
                "kind": plant.kind.value,
                "inputs": _resource_map(plant.inputs),
                "power_output": plant.power_output,
                "active": plant.active,
                "missing": _resource_map(state.power_plant_blocked.get(plant.id, {})),
            }
            for plant in sorted(state.power_plants.values(), key=lambda item: item.id)
        ],
        "space_sites": [
            {
                "id": site.id,
                "name": site.name,
                "resource_id": site.resource_id,
                "travel_ticks": site.travel_ticks,
                "base_yield": site.base_yield,
                "discovered": site.discovered,
                "cargo_type": site.cargo_type.value if site.cargo_type is not None else None,
            }
            for site in sorted(state.space_sites.values(), key=lambda item: item.id)
        ],
        "mining_missions": [
            {
                "id": mission.id,
                "site_id": mission.site_id,
                "launch_node_id": mission.launch_node_id,
                "return_node_id": mission.return_node_id,
                "status": mission.status.value,
                "ticks_remaining": mission.ticks_remaining,
                "fuel_input": mission.fuel_input,
                "power_input": mission.power_input,
                "expected_yield": mission.expected_yield,
                "reserved_power": mission.reserved_power,
                "fuel_consumed": mission.fuel_consumed,
                "projected_yield": mission.expected_yield,
            }
            for mission in sorted(state.mining_missions.values(), key=lambda item: item.id)
        ],
        "worlds": worlds,
        "nodes": nodes,
        "links": links,
        "trains": trains,
        "schedules": schedules,
        "cargo_flows": _cargo_flow_payloads(state),
        "orders": orders,
        "contracts": contracts,
        "construction_projects": [
            {
                "id": project.id,
                "target_node_id": project.target_node_id,
                "required_cargo": _cargo_map(project.required_cargo),
                "delivered_cargo": _cargo_map(project.delivered_cargo),
                "status": project.status.value,
            }
            for project in sorted(state.construction_projects.values(), key=lambda item: item.id)
        ],
        "outposts": _outposts_payload(state),
    }


def _outposts_payload(state: GameState) -> list[dict[str, object]]:
    """Render top-level outposts: pending, active, and completed (promoted)."""

    payload: list[dict[str, object]] = []
    for node in sorted(state.nodes.values(), key=lambda item: item.id):
        if node.outpost_kind is None:
            continue
        project = (
            state.construction_projects.get(node.construction_project_id)
            if node.construction_project_id
            else None
        )
        required = project.required_cargo if project else {}
        delivered = project.delivered_cargo if project else {}
        remaining = project.remaining_cargo if project else {}
        required_total = sum(int(v) for v in required.values())
        delivered_total = sum(int(v) for v in delivered.values())
        progress_fraction = (
            delivered_total / required_total if required_total > 0 else 1.0
        )
        top_needs = [
            {"cargo": cargo.value if hasattr(cargo, "value") else str(cargo), "units": int(units)}
            for cargo, units in sorted(
                remaining.items(), key=lambda item: (-int(item[1]), str(item[0]))
            )[:3]
            if int(units) > 0
        ]
        payload.append(
            {
                "id": node.id,
                "kind": node.kind.value,
                "outpost_kind": node.outpost_kind.value,
                "construction_status": project.status.value if project else "completed",
                "required_cargo": _cargo_map(required),
                "delivered_cargo": _cargo_map(delivered),
                "remaining_cargo": _cargo_map(remaining),
                "progress_fraction": progress_fraction,
                "top_needs": top_needs,
                "world_id": node.world_id,
            }
        )
    return payload
