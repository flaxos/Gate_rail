"""Player command contract for Stage 2 clients."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, TypeAlias

from gaterail.cargo import CargoType, consist_can_carry, required_consist_for
from gaterail.construction import (
    DEFAULT_GATE_CAPACITY_PER_TICK,
    DEFAULT_GATE_POWER_REQUIRED,
    DEFAULT_GATE_TRAVEL_TICKS,
    DEFAULT_RAIL_CAPACITY_PER_TICK,
    facility_component_build_cargo,
    facility_component_build_cost,
    facility_component_default_concurrent_loading_limit,
    facility_component_default_discharge_per_tick,
    facility_component_default_ports,
    facility_component_default_power_provided,
    facility_component_default_power_required,
    facility_component_default_train_capacity,
    link_build_cost,
    link_build_time,
    node_build_cargo,
    node_build_cost,
    node_default_storage,
    node_default_transfer,
    outpost_build_cargo,
    outpost_build_cost,
    outpost_duration_estimate_ticks,
    node_upgrade_cost,
    train_purchase_cost,
    travel_ticks_from_layout_distance,
)
from gaterail.models import (
    ConstructionStatus,
    ConstructionProject,
    Facility,
    FacilityComponent,
    FacilityComponentKind,
    FacilityPort,
    FreightOrder,
    FreightSchedule,
    FreightTrain,
    InternalConnection,
    LinkMode,
    MiningMission,
    MiningMissionStatus,
    NetworkLink,
    NetworkNode,
    NodeKind,
    OperationalAreaState,
    OperationalEntityType,
    OperationalPlacedEntity,
    OutpostKind,
    PortDirection,
    StopAction,
    TrackPoint,
    TrackSignal,
    TrackSignalKind,
    TrainConsist,
    TrainStop,
    TransferLinkKind,
    WaitCondition,
)
from gaterail.local_rules import (
    infer_connection_cargo,
    transfer_link_profile_payload,
    transfer_link_profiles_payload,
    transfer_link_supports_cargo,
)
from gaterail.space import mission_fuel_required, mission_power_required, mission_return_capacity
from gaterail.traffic import effective_link_capacity
from gaterail.transport import route_through_stops, shortest_route


@dataclass(frozen=True, slots=True)
class SetScheduleEnabled:
    """Enable or disable an existing recurring schedule."""

    schedule_id: str
    enabled: bool
    type: Literal["SetScheduleEnabled"] = "SetScheduleEnabled"


@dataclass(frozen=True, slots=True)
class DispatchOrder:
    """Create a one-shot freight order for dispatch by the simulation loop."""

    order_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    requested_units: int
    priority: int = 100
    train_stops: tuple[TrainStop, ...] = ()
    type: Literal["DispatchOrder"] = "DispatchOrder"


@dataclass(frozen=True, slots=True)
class CancelOrder:
    """Cancel a pending one-shot freight order."""

    order_id: str
    type: Literal["CancelOrder"] = "CancelOrder"


@dataclass(frozen=True, slots=True)
class BuildNode:
    """Construct a logistics node on an existing world."""

    node_id: str
    world_id: str
    kind: NodeKind
    name: str
    storage_capacity: int | None = None
    transfer_limit_per_tick: int | None = None
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["BuildNode"] = "BuildNode"


@dataclass(frozen=True, slots=True)
class PreviewBuildNode:
    """Preview a logistics node build without mutating state."""

    node_id: str
    world_id: str
    kind: NodeKind
    name: str
    storage_capacity: int | None = None
    transfer_limit_per_tick: int | None = None
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["PreviewBuildNode"] = "PreviewBuildNode"


@dataclass(frozen=True, slots=True)
class BuildLink:
    """Construct a transport link between two nodes."""

    link_id: str
    origin: str
    destination: str
    mode: LinkMode
    travel_ticks: int | None = None
    capacity_per_tick: int = DEFAULT_RAIL_CAPACITY_PER_TICK
    power_required: int = 0
    power_source_world_id: str | None = None
    bidirectional: bool = True
    alignment: tuple[TrackPoint, ...] = ()
    type: Literal["BuildLink"] = "BuildLink"


@dataclass(frozen=True, slots=True)
class PreviewBuildLink:
    """Preview a transport link build without mutating state."""

    link_id: str
    origin: str
    destination: str
    mode: LinkMode = LinkMode.RAIL
    travel_ticks: int | None = None
    capacity_per_tick: int = DEFAULT_RAIL_CAPACITY_PER_TICK
    power_required: int = 0
    power_source_world_id: str | None = None
    bidirectional: bool = True
    alignment: tuple[TrackPoint, ...] = ()
    type: Literal["PreviewBuildLink"] = "PreviewBuildLink"


@dataclass(frozen=True, slots=True)
class BuildTrackSignal:
    """Place a signal on a rail link endpoint."""

    signal_id: str
    link_id: str
    kind: TrackSignalKind = TrackSignalKind.STOP
    node_id: str | None = None
    active: bool = True
    type: Literal["BuildTrackSignal"] = "BuildTrackSignal"


@dataclass(frozen=True, slots=True)
class PreviewBuildTrackSignal:
    """Preview a signal placement without mutating state."""

    signal_id: str
    link_id: str
    kind: TrackSignalKind = TrackSignalKind.STOP
    node_id: str | None = None
    active: bool = True
    type: Literal["PreviewBuildTrackSignal"] = "PreviewBuildTrackSignal"


@dataclass(frozen=True, slots=True)
class DemolishLink:
    """Demolish an existing transport link."""

    link_id: str
    type: Literal["DemolishLink"] = "DemolishLink"


@dataclass(frozen=True, slots=True)
class PurchaseTrain:
    """Purchase a new freight train."""

    train_id: str
    name: str
    node_id: str
    capacity: int
    consist: str = "general"
    type: Literal["PurchaseTrain"] = "PurchaseTrain"


@dataclass(frozen=True, slots=True)
class PreviewPurchaseTrain:
    """Preview a freight-train purchase without mutating state."""

    train_id: str
    name: str
    node_id: str
    capacity: int
    consist: str = "general"
    type: Literal["PreviewPurchaseTrain"] = "PreviewPurchaseTrain"


@dataclass(frozen=True, slots=True)
class CreateSchedule:
    """Create a recurring freight route schedule."""

    schedule_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    units_per_departure: int
    interval_ticks: int
    next_departure_tick: int | None = None
    priority: int = 100
    active: bool = True
    return_to_origin: bool = True
    stops: tuple[str, ...] = ()
    train_stops: tuple[TrainStop, ...] = ()
    type: Literal["CreateSchedule"] = "CreateSchedule"


@dataclass(frozen=True, slots=True)
class PreviewCreateSchedule:
    """Preview a recurring freight route schedule without mutating state."""

    schedule_id: str
    train_id: str
    origin: str
    destination: str
    cargo_type: CargoType
    units_per_departure: int
    interval_ticks: int
    next_departure_tick: int | None = None
    priority: int = 100
    active: bool = True
    return_to_origin: bool = True
    stops: tuple[str, ...] = ()
    train_stops: tuple[TrainStop, ...] = ()
    type: Literal["PreviewCreateSchedule"] = "PreviewCreateSchedule"


@dataclass(frozen=True, slots=True)
class UpdateSchedule:
    """Edit an existing recurring freight schedule."""

    schedule_id: str
    train_id: str | None = None
    origin: str | None = None
    destination: str | None = None
    cargo_type: CargoType | None = None
    units_per_departure: int | None = None
    interval_ticks: int | None = None
    next_departure_tick: int | None = None
    priority: int | None = None
    active: bool | None = None
    return_to_origin: bool | None = None
    stops: tuple[str, ...] | None = None
    train_stops: tuple[TrainStop, ...] | None = None
    type: Literal["UpdateSchedule"] = "UpdateSchedule"


@dataclass(frozen=True, slots=True)
class PreviewUpdateSchedule:
    """Preview editing an existing recurring freight schedule."""

    schedule_id: str
    train_id: str | None = None
    origin: str | None = None
    destination: str | None = None
    cargo_type: CargoType | None = None
    units_per_departure: int | None = None
    interval_ticks: int | None = None
    next_departure_tick: int | None = None
    priority: int | None = None
    active: bool | None = None
    return_to_origin: bool | None = None
    stops: tuple[str, ...] | None = None
    train_stops: tuple[TrainStop, ...] | None = None
    type: Literal["PreviewUpdateSchedule"] = "PreviewUpdateSchedule"


@dataclass(frozen=True, slots=True)
class DeleteSchedule:
    """Delete an existing recurring freight schedule."""

    schedule_id: str
    type: Literal["DeleteSchedule"] = "DeleteSchedule"


@dataclass(frozen=True, slots=True)
class PreviewDeleteSchedule:
    """Preview deleting an existing recurring freight schedule."""

    schedule_id: str
    type: Literal["PreviewDeleteSchedule"] = "PreviewDeleteSchedule"


@dataclass(frozen=True, slots=True)
class UpgradeNode:
    """Upgrade an existing node's storage and transfer capacity."""

    node_id: str
    storage_capacity_increase: int
    transfer_limit_increase: int
    type: Literal["UpgradeNode"] = "UpgradeNode"


@dataclass(frozen=True, slots=True)
class BuildFacilityComponent:
    """Install a facility component on an existing node."""

    component_id: str
    node_id: str
    kind: FacilityComponentKind | str
    capacity: int = 0
    rate: int = 0
    power_required: int = 0
    power_provided: int = 0
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    construction_cargo: dict[CargoType, int] | None = None
    train_capacity: int = 0
    concurrent_loading_limit: int = 1
    stored_charge: int = 0
    discharge_per_tick: int = 0
    ports: tuple[FacilityPort, ...] = ()
    connections: tuple[InternalConnection, ...] = ()
    type: Literal["BuildFacilityComponent"] = "BuildFacilityComponent"


@dataclass(frozen=True, slots=True)
class PreviewBuildFacilityComponent:
    """Preview a facility component install without mutating state."""

    component_id: str
    node_id: str
    kind: FacilityComponentKind | str
    capacity: int = 0
    rate: int = 0
    power_required: int = 0
    power_provided: int = 0
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    construction_cargo: dict[CargoType, int] | None = None
    train_capacity: int = 0
    concurrent_loading_limit: int = 1
    stored_charge: int = 0
    discharge_per_tick: int = 0
    ports: tuple[FacilityPort, ...] = ()
    connections: tuple[InternalConnection, ...] = ()
    type: Literal["PreviewBuildFacilityComponent"] = "PreviewBuildFacilityComponent"


@dataclass(frozen=True, slots=True)
class DemolishFacilityComponent:
    """Remove an existing facility component from a node."""

    node_id: str
    component_id: str
    type: Literal["DemolishFacilityComponent"] = "DemolishFacilityComponent"


@dataclass(frozen=True, slots=True)
class PreviewDemolishFacilityComponent:
    """Preview facility-component demolition without mutating state."""

    node_id: str
    component_id: str
    type: Literal["PreviewDemolishFacilityComponent"] = "PreviewDemolishFacilityComponent"


@dataclass(frozen=True, slots=True)
class BuildInternalConnection:
    """Create a connection between two ports inside one facility."""

    node_id: str
    connection_id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str
    link_type: TransferLinkKind | str = TransferLinkKind.CONVEYOR
    type: Literal["BuildInternalConnection"] = "BuildInternalConnection"


@dataclass(frozen=True, slots=True)
class PreviewBuildInternalConnection:
    """Preview an internal facility connection without mutating state."""

    node_id: str
    connection_id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str
    link_type: TransferLinkKind | str = TransferLinkKind.CONVEYOR
    type: Literal["PreviewBuildInternalConnection"] = "PreviewBuildInternalConnection"


@dataclass(frozen=True, slots=True)
class RemoveInternalConnection:
    """Remove an existing internal facility connection."""

    node_id: str
    connection_id: str
    type: Literal["RemoveInternalConnection"] = "RemoveInternalConnection"


@dataclass(frozen=True, slots=True)
class PreviewRemoveInternalConnection:
    """Preview removing an internal facility connection."""

    node_id: str
    connection_id: str
    type: Literal["PreviewRemoveInternalConnection"] = "PreviewRemoveInternalConnection"


@dataclass(frozen=True, slots=True)
class SurveySpaceSite:
    """Mark a remote resource site as surveyed and eligible for missions."""

    site_id: str
    type: Literal["SurveySpaceSite"] = "SurveySpaceSite"


@dataclass(frozen=True, slots=True)
class PreviewSurveySpaceSite:
    """Preview surveying a remote resource site without mutating state."""

    site_id: str
    type: Literal["PreviewSurveySpaceSite"] = "PreviewSurveySpaceSite"


@dataclass(frozen=True, slots=True)
class DispatchMiningMission:
    """Launch a fixed-tick mining mission to a remote site."""

    mission_id: str
    site_id: str
    launch_node_id: str
    return_node_id: str
    fuel_input: int = 0
    power_input: int = 0
    type: Literal["DispatchMiningMission"] = "DispatchMiningMission"


@dataclass(frozen=True, slots=True)
class PreviewDispatchMiningMission:
    """Preview a mining mission launch without mutating state."""

    mission_id: str
    site_id: str
    launch_node_id: str
    return_node_id: str
    fuel_input: int = 0
    power_input: int = 0
    type: Literal["PreviewDispatchMiningMission"] = "PreviewDispatchMiningMission"


@dataclass(frozen=True, slots=True)
class BuildOutpost:
    """Stage an outpost construction project on a world."""

    world_id: str
    outpost_kind: str
    outpost_id: str = ""
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["BuildOutpost"] = "BuildOutpost"


@dataclass(frozen=True, slots=True)
class PreviewBuildOutpost:
    """Preview an outpost build without mutating state."""

    world_id: str
    outpost_kind: str
    outpost_id: str = ""
    layout_x: float | None = None
    layout_y: float | None = None
    type: Literal["PreviewBuildOutpost"] = "PreviewBuildOutpost"


@dataclass(frozen=True, slots=True)
class CancelOutpost:
    """Cancel a staged outpost project and refund 50% of cash and delivered cargo."""

    outpost_id: str
    type: Literal["CancelOutpost"] = "CancelOutpost"


@dataclass(frozen=True, slots=True)
class PreviewCancelOutpost:
    """Preview outpost cancellation refunds without mutating state."""

    outpost_id: str
    type: Literal["PreviewCancelOutpost"] = "PreviewCancelOutpost"


@dataclass(frozen=True, slots=True)
class LocalGetOperationalArea:
    """Return one backend-authoritative local operational area."""

    operational_area_id: str
    type: Literal["local.get_operational_area"] = "local.get_operational_area"


@dataclass(frozen=True, slots=True)
class LocalListBuildOptions:
    """Return local construction options for an operational area."""

    operational_area_id: str
    type: Literal["local.list_build_options"] = "local.list_build_options"


@dataclass(frozen=True, slots=True)
class LocalValidatePlacement:
    """Validate local operational-grid placement without mutating state."""

    operational_area_id: str
    entity_type: str
    x: int
    y: int
    entity_id: str = ""
    rotation: int = 0
    width: int = 0
    height: int = 0
    path_cells: tuple[tuple[int, int, int], ...] = ()
    platform_side: str | None = None
    adjacent_to_entity_id: str | None = None
    adjacent_port_id: str | None = None
    owner_node_id: str | None = None
    component_id: str | None = None
    link_id: str | None = None
    origin_node_id: str | None = None
    destination_node_id: str | None = None
    rate: int = 0
    capacity: int = 0
    power_required: int = 0
    power_provided: int = 0
    construction_cargo: dict[CargoType, int] | None = None
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    type: Literal["local.validate_placement"] = "local.validate_placement"


@dataclass(frozen=True, slots=True)
class LocalPlaceEntity:
    """Place one local operational-grid entity after validation."""

    operational_area_id: str
    entity_type: str
    x: int
    y: int
    entity_id: str = ""
    rotation: int = 0
    width: int = 0
    height: int = 0
    path_cells: tuple[tuple[int, int, int], ...] = ()
    platform_side: str | None = None
    adjacent_to_entity_id: str | None = None
    adjacent_port_id: str | None = None
    owner_node_id: str | None = None
    component_id: str | None = None
    link_id: str | None = None
    origin_node_id: str | None = None
    destination_node_id: str | None = None
    name: str = ""
    rate: int = 0
    capacity: int = 0
    power_required: int = 0
    power_provided: int = 0
    construction_cargo: dict[CargoType, int] | None = None
    inputs: dict[CargoType, int] | None = None
    outputs: dict[CargoType, int] | None = None
    type: Literal["local.place_entity"] = "local.place_entity"


@dataclass(frozen=True, slots=True)
class LocalRotateEntity:
    """Rotate a persisted local operational-grid entity."""

    operational_area_id: str
    entity_id: str
    rotation: int
    type: Literal["local.rotate_entity"] = "local.rotate_entity"


@dataclass(frozen=True, slots=True)
class LocalDeleteEntity:
    """Delete a persisted local operational-grid entity and its backed object when safe."""

    operational_area_id: str
    entity_id: str
    type: Literal["local.delete_entity"] = "local.delete_entity"


@dataclass(frozen=True, slots=True)
class LocalInspectEntity:
    """Inspect a persisted local operational-grid entity."""

    operational_area_id: str
    entity_id: str
    type: Literal["local.inspect_entity"] = "local.inspect_entity"


@dataclass(frozen=True, slots=True)
class LocalConnectEntities:
    """Create a backend facility transfer link and persisted local transfer entity."""

    operational_area_id: str
    owner_node_id: str
    source_component_id: str
    source_port_id: str
    destination_component_id: str
    destination_port_id: str
    connection_id: str = ""
    entity_id: str = ""
    link_type: TransferLinkKind | str = TransferLinkKind.CONVEYOR
    x: int | None = None
    y: int | None = None
    type: Literal["local.connect_entities"] = "local.connect_entities"


@dataclass(frozen=True, slots=True)
class LocalValidateSignal:
    """Validate local track-signal placement against a persisted track entity."""

    operational_area_id: str
    track_entity_id: str = ""
    link_id: str = ""
    signal_id: str = ""
    kind: TrackSignalKind = TrackSignalKind.STOP
    node_id: str | None = None
    active: bool = True
    type: Literal["local.validate_signal"] = "local.validate_signal"


@dataclass(frozen=True, slots=True)
class LocalPlaceSignal:
    """Place a backend TrackSignal through local track tooling."""

    operational_area_id: str
    track_entity_id: str = ""
    link_id: str = ""
    signal_id: str = ""
    kind: TrackSignalKind = TrackSignalKind.STOP
    node_id: str | None = None
    active: bool = True
    type: Literal["local.place_signal"] = "local.place_signal"


@dataclass(frozen=True, slots=True)
class LocalSetSwitchRoute:
    """Persist the selected outgoing route for an abstract local switch."""

    operational_area_id: str
    selected_link_id: str
    node_id: str = ""
    switch_id: str = ""
    type: Literal["local.set_switch_route"] = "local.set_switch_route"


PlayerCommand: TypeAlias = (
    SetScheduleEnabled
    | DispatchOrder
    | CancelOrder
    | BuildNode
    | PreviewBuildNode
    | BuildLink
    | PreviewBuildLink
    | BuildTrackSignal
    | PreviewBuildTrackSignal
    | DemolishLink
    | PurchaseTrain
    | PreviewPurchaseTrain
    | CreateSchedule
    | PreviewCreateSchedule
    | UpdateSchedule
    | PreviewUpdateSchedule
    | DeleteSchedule
    | PreviewDeleteSchedule
    | UpgradeNode
    | BuildFacilityComponent
    | PreviewBuildFacilityComponent
    | DemolishFacilityComponent
    | PreviewDemolishFacilityComponent
    | BuildInternalConnection
    | PreviewBuildInternalConnection
    | RemoveInternalConnection
    | PreviewRemoveInternalConnection
    | SurveySpaceSite
    | PreviewSurveySpaceSite
    | DispatchMiningMission
    | PreviewDispatchMiningMission
    | BuildOutpost
    | PreviewBuildOutpost
    | CancelOutpost
    | PreviewCancelOutpost
    | LocalGetOperationalArea
    | LocalListBuildOptions
    | LocalValidatePlacement
    | LocalPlaceEntity
    | LocalRotateEntity
    | LocalDeleteEntity
    | LocalInspectEntity
    | LocalConnectEntities
    | LocalValidateSignal
    | LocalPlaceSignal
    | LocalSetSwitchRoute
)


def _command_type(data: dict[str, Any]) -> str:
    """Read the command type from a JSON-style command object."""

    raw_type = data.get("type") or data.get("command")
    if raw_type is None:
        raise ValueError("command missing type")
    return str(raw_type)


def _optional_int(value: object) -> int | None:
    """Parse optional integer command fields."""

    return None if value is None else int(value)


def _optional_float(value: object) -> float | None:
    """Parse optional float command fields."""

    return None if value is None else float(value)


def _layout_fields(data: dict[str, Any]) -> tuple[float | None, float | None]:
    """Read optional local-world layout fields from a command object."""

    layout = data.get("layout")
    if isinstance(layout, dict):
        return _optional_float(layout.get("x")), _optional_float(layout.get("y"))
    return _optional_float(data.get("layout_x")), _optional_float(data.get("layout_y"))


def _track_point_from_payload(data: object) -> TrackPoint:
    """Parse one local rail-alignment point from a command payload."""

    if isinstance(data, dict):
        return TrackPoint(x=float(data["x"]), y=float(data["y"]))
    if isinstance(data, (list, tuple)) and len(data) >= 2:
        return TrackPoint(x=float(data[0]), y=float(data[1]))
    raise ValueError("alignment points must be objects with x/y or two-item arrays")


def _alignment_fields(data: dict[str, Any]) -> tuple[TrackPoint, ...]:
    """Read optional local rail alignment metadata from a command object."""

    raw_alignment = data.get("alignment")
    if raw_alignment is None:
        raw_alignment = data.get("waypoints")
    if raw_alignment is None:
        raw_alignment = data.get("control_points")
    if raw_alignment is None:
        return ()
    if isinstance(raw_alignment, dict):
        raw_alignment = raw_alignment.get("points", [])
    if not isinstance(raw_alignment, (list, tuple)):
        raise ValueError("alignment must be a list of points")
    return tuple(_track_point_from_payload(point) for point in raw_alignment)


def _node_id_tuple(value: object) -> tuple[str, ...]:
    """Return a stable tuple of node ids from JSON-like input."""

    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ValueError("schedule stops must be a string or list of strings")


def _train_stop_from_payload(value: object) -> TrainStop:
    """Decode a TrainStop from a JSON-like payload."""

    if not isinstance(value, dict):
        raise ValueError("train stop must be a dictionary")
    cargo = value.get("cargo_type")
    return TrainStop(
        node_id=str(value["node_id"]),
        action=StopAction(str(value.get("action", StopAction.PASSTHROUGH.value))),
        cargo_type=None if cargo is None else CargoType(str(cargo)),
        units=int(value.get("units", 0)),
        wait_condition=WaitCondition(
            str(value.get("wait_condition", WaitCondition.NONE.value))
        ),
        wait_ticks=int(value.get("wait_ticks", 0)),
    )


def _train_stop_tuple(value: object) -> tuple[TrainStop, ...]:
    """Decode a tuple of train stops from JSON-like input."""

    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(_train_stop_from_payload(item) for item in value)
    raise ValueError("train_stops must be a list of stop dictionaries")


def _optional_train_stop_tuple(
    data: dict[str, Any],
) -> tuple[TrainStop, ...] | None:
    """Return optional train_stops, preserving absent as no change."""

    if "train_stops" not in data:
        return None
    return _train_stop_tuple(data.get("train_stops"))


def _optional_node_id_tuple(data: dict[str, Any]) -> tuple[str, ...] | None:
    """Return optional schedule stops, preserving absent as no change."""

    for key in ("stops", "stop_ids", "waypoint_node_ids"):
        if key in data:
            return _node_id_tuple(data.get(key))
    return None


def _optional_bool_field(data: dict[str, Any], key: str) -> bool | None:
    """Return an optional boolean command field."""

    if key not in data:
        return None
    return bool(data[key])


def _optional_cargo_field(data: dict[str, Any]) -> CargoType | None:
    """Return an optional cargo type command field."""

    if "cargo_type" not in data and "cargo" not in data:
        return None
    raw = data.get("cargo_type", data.get("cargo"))
    if raw is None:
        return None
    return CargoType(str(raw))


def _optional_str_field(data: dict[str, Any], key: str) -> str | None:
    """Return an optional string command field."""

    if key not in data:
        return None
    raw = data[key]
    if raw is None:
        return None
    return str(raw)


def _path_cells_from_data(data: object) -> tuple[tuple[int, int, int], ...]:
    """Parse optional local path-cell payloads from JSON-safe command data."""

    if data is None:
        return ()
    if not isinstance(data, list):
        raise ValueError("path_cells must be a list")
    cells: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for item in data:
        if isinstance(item, dict):
            cell = (int(item["x"]), int(item["y"]), int(item.get("z", 0)))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            cell = (int(item[0]), int(item[1]), int(item[2]) if len(item) >= 3 else 0)
        else:
            raise ValueError("path_cells entries must be {x,y,z?} objects")
        if cell in seen:
            continue
        seen.add(cell)
        cells.append(cell)
    return tuple(cells)


def command_from_dict(data: dict[str, Any]) -> PlayerCommand:
    """Build a player command from JSON-safe data."""

    command_type = _command_type(data)
    if command_type == "local.get_operational_area":
        return LocalGetOperationalArea(operational_area_id=str(data["operational_area_id"]))
    if command_type == "local.list_build_options":
        return LocalListBuildOptions(operational_area_id=str(data["operational_area_id"]))
    if command_type in {"local.validate_placement", "local.place_entity"}:
        command_cls = LocalValidatePlacement if command_type == "local.validate_placement" else LocalPlaceEntity
        construction_cargo_data = data.get("construction_cargo", data.get("cargo_cost"))
        return command_cls(
            operational_area_id=str(data["operational_area_id"]),
            entity_id=str(data.get("entity_id", "")),
            entity_type=str(data["entity_type"]),
            x=int(data["x"]),
            y=int(data["y"]),
            rotation=int(data.get("rotation", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            path_cells=_path_cells_from_data(data.get("path_cells")),
            platform_side=_optional_str_field(data, "platform_side"),
            adjacent_to_entity_id=_optional_str_field(data, "adjacent_to_entity_id"),
            adjacent_port_id=_optional_str_field(data, "adjacent_port_id"),
            owner_node_id=_optional_str_field(data, "owner_node_id"),
            component_id=_optional_str_field(data, "component_id"),
            link_id=_optional_str_field(data, "link_id"),
            origin_node_id=_optional_str_field(data, "origin_node_id"),
            destination_node_id=_optional_str_field(data, "destination_node_id"),
            rate=int(data.get("rate", 0)),
            capacity=int(data.get("capacity", 0)),
            power_required=int(data.get("power_required", 0)),
            power_provided=int(data.get("power_provided", 0)),
            construction_cargo=(
                None if construction_cargo_data is None else _facility_cargo_map_from_dict(construction_cargo_data)
            ),
            inputs=None if data.get("inputs") is None else _facility_cargo_map_from_dict(data.get("inputs")),
            outputs=None if data.get("outputs") is None else _facility_cargo_map_from_dict(data.get("outputs")),
            **({"name": str(data.get("name", ""))} if command_cls is LocalPlaceEntity else {}),
        )
    if command_type == "local.rotate_entity":
        return LocalRotateEntity(
            operational_area_id=str(data["operational_area_id"]),
            entity_id=str(data["entity_id"]),
            rotation=int(data["rotation"]),
        )
    if command_type == "local.delete_entity":
        return LocalDeleteEntity(
            operational_area_id=str(data["operational_area_id"]),
            entity_id=str(data["entity_id"]),
        )
    if command_type == "local.inspect_entity":
        return LocalInspectEntity(
            operational_area_id=str(data["operational_area_id"]),
            entity_id=str(data["entity_id"]),
        )
    if command_type in {"local.connect_entities", "local.place_transfer_link"}:
        return LocalConnectEntities(
            operational_area_id=str(data["operational_area_id"]),
            entity_id=str(data.get("entity_id", "")),
            connection_id=str(data.get("connection_id", "")),
            owner_node_id=str(data["owner_node_id"]),
            source_component_id=str(data["source_component_id"]),
            source_port_id=str(data["source_port_id"]),
            destination_component_id=str(data["destination_component_id"]),
            destination_port_id=str(data["destination_port_id"]),
            link_type=_resolve_transfer_link_kind(
                data.get("link_type", data.get("transfer_type", TransferLinkKind.CONVEYOR.value))
            ),
            x=None if data.get("x") is None else int(data["x"]),
            y=None if data.get("y") is None else int(data["y"]),
        )
    if command_type in {"local.validate_signal", "local.place_signal"}:
        signal_command = LocalValidateSignal if command_type == "local.validate_signal" else LocalPlaceSignal
        node_id = data.get("node_id")
        return signal_command(
            operational_area_id=str(data["operational_area_id"]),
            track_entity_id=str(data.get("track_entity_id", data.get("entity_id", ""))),
            link_id=str(data.get("link_id", "")),
            signal_id=str(data.get("signal_id", data.get("id", ""))),
            kind=TrackSignalKind(str(data.get("kind", TrackSignalKind.STOP.value))),
            node_id=None if node_id is None else str(node_id),
            active=bool(data.get("active", True)),
        )
    if command_type == "local.set_switch_route":
        return LocalSetSwitchRoute(
            operational_area_id=str(data["operational_area_id"]),
            switch_id=str(data.get("switch_id", "")),
            node_id=str(data.get("node_id", "")),
            selected_link_id=str(data["selected_link_id"]),
        )
    if command_type == "SetScheduleEnabled":
        return SetScheduleEnabled(
            schedule_id=str(data["schedule_id"]),
            enabled=bool(data["enabled"]),
        )
    if command_type == "DispatchOrder":
        return DispatchOrder(
            order_id=str(data["order_id"]),
            train_id=str(data["train_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            cargo_type=CargoType(str(data["cargo_type"])),
            requested_units=int(data["requested_units"]),
            priority=int(data.get("priority", 100)),
            train_stops=_train_stop_tuple(data.get("train_stops")),
        )
    if command_type == "CancelOrder":
        return CancelOrder(order_id=str(data["order_id"]))
    if command_type in {"BuildNode", "PreviewBuildNode"}:
        storage = data.get("storage_capacity")
        transfer = data.get("transfer_limit_per_tick")
        layout_x, layout_y = _layout_fields(data)
        node_command = BuildNode if command_type == "BuildNode" else PreviewBuildNode
        return node_command(
            node_id=str(data["node_id"]),
            world_id=str(data["world_id"]),
            kind=NodeKind(str(data["kind"])),
            name=str(data["name"]),
            storage_capacity=None if storage is None else int(storage),
            transfer_limit_per_tick=None if transfer is None else int(transfer),
            layout_x=layout_x,
            layout_y=layout_y,
        )
    if command_type in {"BuildLink", "PreviewBuildLink"}:
        power_world = data.get("power_source_world_id")
        mode = LinkMode(str(data.get("mode", LinkMode.RAIL.value)))
        default_capacity = (
            DEFAULT_GATE_CAPACITY_PER_TICK
            if mode == LinkMode.GATE
            else DEFAULT_RAIL_CAPACITY_PER_TICK
        )
        default_power = DEFAULT_GATE_POWER_REQUIRED if mode == LinkMode.GATE else 0
        link_command = BuildLink if command_type == "BuildLink" else PreviewBuildLink
        return link_command(
            link_id=str(data["link_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            mode=mode,
            travel_ticks=_optional_int(data.get("travel_ticks")),
            capacity_per_tick=int(data.get("capacity_per_tick", default_capacity)),
            power_required=int(data.get("power_required", default_power)),
            power_source_world_id=None if power_world is None else str(power_world),
            bidirectional=bool(data.get("bidirectional", True)),
            alignment=_alignment_fields(data),
        )
    if command_type in {"BuildTrackSignal", "PreviewBuildTrackSignal"}:
        signal_command = (
            BuildTrackSignal if command_type == "BuildTrackSignal" else PreviewBuildTrackSignal
        )
        signal_id = data.get("signal_id", data.get("id"))
        if signal_id is None:
            raise ValueError("track signal command missing signal_id")
        node_id = data.get("node_id")
        return signal_command(
            signal_id=str(signal_id),
            link_id=str(data["link_id"]),
            kind=TrackSignalKind(str(data.get("kind", TrackSignalKind.STOP.value))),
            node_id=None if node_id is None else str(node_id),
            active=bool(data.get("active", True)),
        )
    if command_type == "DemolishLink":
        return DemolishLink(link_id=str(data["link_id"]))
    if command_type in {"PurchaseTrain", "PreviewPurchaseTrain"}:
        train_command = PurchaseTrain if command_type == "PurchaseTrain" else PreviewPurchaseTrain
        return train_command(
            train_id=str(data["train_id"]),
            name=str(data["name"]),
            node_id=str(data["node_id"]),
            capacity=int(data["capacity"]),
            consist=str(data.get("consist", "general")),
        )
    if command_type in {"CreateSchedule", "PreviewCreateSchedule"}:
        next_departure = data.get("next_departure_tick")
        schedule_command = CreateSchedule if command_type == "CreateSchedule" else PreviewCreateSchedule
        return schedule_command(
            schedule_id=str(data["schedule_id"]),
            train_id=str(data["train_id"]),
            origin=str(data["origin"]),
            destination=str(data["destination"]),
            cargo_type=CargoType(str(data["cargo_type"])),
            units_per_departure=int(data["units_per_departure"]),
            interval_ticks=int(data["interval_ticks"]),
            next_departure_tick=None if next_departure is None else int(next_departure),
            priority=int(data.get("priority", 100)),
            active=bool(data.get("active", True)),
            return_to_origin=bool(data.get("return_to_origin", True)),
            stops=_node_id_tuple(data.get("stops", data.get("stop_ids", data.get("waypoint_node_ids")))),
            train_stops=_train_stop_tuple(data.get("train_stops")),
        )
    if command_type in {"UpdateSchedule", "PreviewUpdateSchedule"}:
        schedule_command = UpdateSchedule if command_type == "UpdateSchedule" else PreviewUpdateSchedule
        return schedule_command(
            schedule_id=str(data["schedule_id"]),
            train_id=_optional_str_field(data, "train_id"),
            origin=_optional_str_field(data, "origin"),
            destination=_optional_str_field(data, "destination"),
            cargo_type=_optional_cargo_field(data),
            units_per_departure=(
                None
                if "units_per_departure" not in data
                else _optional_int(data.get("units_per_departure"))
            ),
            interval_ticks=(
                None
                if "interval_ticks" not in data
                else _optional_int(data.get("interval_ticks"))
            ),
            next_departure_tick=(
                None
                if "next_departure_tick" not in data
                else _optional_int(data.get("next_departure_tick"))
            ),
            priority=None if "priority" not in data else _optional_int(data.get("priority")),
            active=_optional_bool_field(data, "active"),
            return_to_origin=_optional_bool_field(data, "return_to_origin"),
            stops=_optional_node_id_tuple(data),
            train_stops=_optional_train_stop_tuple(data),
        )
    if command_type == "DeleteSchedule":
        return DeleteSchedule(schedule_id=str(data["schedule_id"]))
    if command_type == "PreviewDeleteSchedule":
        return PreviewDeleteSchedule(schedule_id=str(data["schedule_id"]))
    if command_type == "UpgradeNode":
        return UpgradeNode(
            node_id=str(data["node_id"]),
            storage_capacity_increase=int(data["storage_capacity_increase"]),
            transfer_limit_increase=int(data["transfer_limit_increase"]),
        )
    if command_type in {"BuildFacilityComponent", "PreviewBuildFacilityComponent"}:
        ports_payload = data.get("ports", []) or []
        connections_payload = data.get("connections", []) or []
        ports = tuple(_facility_port_from_dict(item) for item in ports_payload)
        connections = tuple(_internal_connection_from_dict(item) for item in connections_payload)
        inputs_data = data.get("inputs")
        outputs_data = data.get("outputs")
        construction_cargo_data = data.get("construction_cargo", data.get("cargo_cost"))
        raw_kind = str(data["kind"])
        try:
            parsed_kind: FacilityComponentKind | str = FacilityComponentKind(raw_kind)
        except ValueError:
            parsed_kind = raw_kind
        component_command = (
            BuildFacilityComponent
            if command_type == "BuildFacilityComponent"
            else PreviewBuildFacilityComponent
        )
        return component_command(
            component_id=str(data["component_id"]),
            node_id=str(data["node_id"]),
            kind=parsed_kind,
            capacity=int(data.get("capacity", 0)),
            rate=int(data.get("rate", 0)),
            power_required=int(data.get("power_required", 0)),
            power_provided=int(data.get("power_provided", 0)),
            inputs=None if inputs_data is None else _facility_cargo_map_from_dict(inputs_data),
            outputs=None if outputs_data is None else _facility_cargo_map_from_dict(outputs_data),
            construction_cargo=(
                None
                if construction_cargo_data is None
                else _facility_cargo_map_from_dict(construction_cargo_data)
            ),
            train_capacity=int(data.get("train_capacity", 0)),
            concurrent_loading_limit=int(data.get("concurrent_loading_limit", 1)),
            stored_charge=int(data.get("stored_charge", 0)),
            discharge_per_tick=int(data.get("discharge_per_tick", 0)),
            ports=ports,
            connections=connections,
        )
    if command_type in {"DemolishFacilityComponent", "PreviewDemolishFacilityComponent"}:
        component_command = (
            DemolishFacilityComponent
            if command_type == "DemolishFacilityComponent"
            else PreviewDemolishFacilityComponent
        )
        return component_command(
            node_id=str(data["node_id"]),
            component_id=str(data["component_id"]),
        )
    if command_type in {"BuildInternalConnection", "PreviewBuildInternalConnection"}:
        connection_command = (
            BuildInternalConnection
            if command_type == "BuildInternalConnection"
            else PreviewBuildInternalConnection
        )
        return connection_command(
            node_id=str(data["node_id"]),
            connection_id=str(data["connection_id"]),
            source_component_id=str(data["source_component_id"]),
            source_port_id=str(data["source_port_id"]),
            destination_component_id=str(data["destination_component_id"]),
            destination_port_id=str(data["destination_port_id"]),
            link_type=_resolve_transfer_link_kind(
                data.get("link_type", data.get("transfer_type", TransferLinkKind.CONVEYOR.value))
            ),
        )
    if command_type in {"RemoveInternalConnection", "PreviewRemoveInternalConnection"}:
        connection_command = (
            RemoveInternalConnection
            if command_type == "RemoveInternalConnection"
            else PreviewRemoveInternalConnection
        )
        return connection_command(
            node_id=str(data["node_id"]),
            connection_id=str(data["connection_id"]),
        )
    if command_type in {"SurveySpaceSite", "PreviewSurveySpaceSite"}:
        survey_command = (
            SurveySpaceSite if command_type == "SurveySpaceSite" else PreviewSurveySpaceSite
        )
        return survey_command(site_id=str(data["site_id"]))
    if command_type in {"DispatchMiningMission", "PreviewDispatchMiningMission"}:
        mission_command = (
            DispatchMiningMission
            if command_type == "DispatchMiningMission"
            else PreviewDispatchMiningMission
        )
        return mission_command(
            mission_id=str(data["mission_id"]),
            site_id=str(data["site_id"]),
            launch_node_id=str(data["launch_node_id"]),
            return_node_id=str(data["return_node_id"]),
            fuel_input=int(data.get("fuel_input", 0)),
            power_input=int(data.get("power_input", 0)),
        )
    if command_type in {"BuildOutpost", "PreviewBuildOutpost"}:
        layout_x, layout_y = _layout_fields(data)
        outpost_command = BuildOutpost if command_type == "BuildOutpost" else PreviewBuildOutpost
        return outpost_command(
            world_id=str(data["world_id"]),
            outpost_kind=str(data["outpost_kind"]),
            outpost_id=str(data.get("outpost_id", "")),
            layout_x=layout_x,
            layout_y=layout_y,
        )
    if command_type in {"CancelOutpost", "PreviewCancelOutpost"}:
        cancel_command = CancelOutpost if command_type == "CancelOutpost" else PreviewCancelOutpost
        return cancel_command(outpost_id=str(data["outpost_id"]))
    raise ValueError(f"unknown command type: {command_type}")


def _facility_cargo_map_from_dict(data: object) -> dict[CargoType, int]:
    """Parse cargo→units maps in facility command payloads."""

    if not isinstance(data, dict):
        return {}
    return {CargoType(str(cargo)): int(units) for cargo, units in data.items()}


def _facility_port_from_dict(data: dict[str, Any]) -> FacilityPort:
    """Parse a FacilityPort spec from a JSON command payload."""

    cargo_type = data.get("cargo_type")
    return FacilityPort(
        id=str(data["id"]),
        direction=PortDirection(str(data["direction"])),
        cargo_type=None if cargo_type is None else CargoType(str(cargo_type)),
        rate=int(data.get("rate", 0)),
        capacity=int(data.get("capacity", 0)),
    )


def _internal_connection_from_dict(data: dict[str, Any]) -> InternalConnection:
    """Parse an InternalConnection spec from a JSON command payload."""

    return InternalConnection(
        id=str(data["id"]),
        source_component_id=str(data["source_component_id"]),
        source_port_id=str(data["source_port_id"]),
        destination_component_id=str(data["destination_component_id"]),
        destination_port_id=str(data["destination_port_id"]),
        link_type=_resolve_transfer_link_kind(
            data.get("link_type", data.get("transfer_type", TransferLinkKind.CONVEYOR.value))
        ),
    )


def command_result(
    command_type: str,
    *,
    ok: bool,
    message: str,
    target_id: str | None = None,
    **extra: object,
) -> dict[str, object]:
    """Return a JSON-safe command result."""

    result: dict[str, object] = {
        "ok": ok,
        "type": command_type,
        "target_id": target_id,
        "message": message,
    }
    result.update(extra)
    return result


def _duplicate_link_between(
    state: object,
    origin: str,
    destination: str,
    mode: LinkMode,
    *,
    bidirectional: bool,
) -> str | None:
    """Return an existing link id with the same mode and endpoints."""

    for link in state.links.values():
        if link.mode != mode:
            continue
        same_direction = link.origin == origin and link.destination == destination
        reverse_direction = link.origin == destination and link.destination == origin
        if same_direction:
            return link.id
        if reverse_direction and (link.bidirectional or bidirectional):
            return link.id
    return None


def _reverse_link_id_for(
    state: object,
    origin: str,
    destination: str,
    mode: LinkMode,
    *,
    ignored_link_id: str | None = None,
) -> str | None:
    """Return an existing link that supports the reverse direction."""

    endpoints = {origin, destination}
    for link in sorted(state.links.values(), key=lambda item: item.id):
        if link.id == ignored_link_id or link.mode != mode:
            continue
        if link.bidirectional and {link.origin, link.destination} == endpoints:
            return link.id
        if link.origin == destination and link.destination == origin:
            return link.id
    return None


def _node_layout_payload(layout_x: float | None, layout_y: float | None) -> dict[str, float] | None:
    """Return JSON-safe node layout payload."""

    if layout_x is None and layout_y is None:
        return None
    if layout_x is None or layout_y is None:
        raise ValueError("layout requires both x and y")
    return {"x": round(layout_x, 3), "y": round(layout_y, 3)}


def _validate_build_node(state: object, command: BuildNode | PreviewBuildNode) -> tuple[float, int, int, dict[str, float] | None]:
    """Validate and normalize a node build command."""

    if command.world_id not in state.worlds:
        raise ValueError(f"unknown world: {command.world_id}")
    if command.node_id in state.nodes:
        raise ValueError(f"duplicate node id: {command.node_id}")
    if not command.name.strip():
        raise ValueError("node name cannot be empty")
    cost = node_build_cost(command.kind)
    storage = command.storage_capacity if command.storage_capacity is not None else node_default_storage(command.kind)
    transfer = command.transfer_limit_per_tick if command.transfer_limit_per_tick is not None else node_default_transfer(command.kind)
    if storage <= 0:
        raise ValueError("storage_capacity must be positive")
    if transfer <= 0:
        raise ValueError("transfer_limit_per_tick must be positive")
    layout = _node_layout_payload(command.layout_x, command.layout_y)
    return cost, storage, transfer, layout


def _node_build_payload(
    command: BuildNode | PreviewBuildNode,
    *,
    storage: int,
    transfer: int,
    layout: dict[str, float] | None,
) -> dict[str, object]:
    """Return a normalized BuildNode command payload."""

    payload: dict[str, object] = {
        "type": "BuildNode",
        "node_id": command.node_id,
        "world_id": command.world_id,
        "kind": command.kind.value,
        "name": command.name,
        "storage_capacity": storage,
        "transfer_limit_per_tick": transfer,
    }
    if layout is not None:
        payload["layout"] = layout
    return payload


def _layout_travel_ticks_for_nodes(state: object, origin: str, destination: str) -> int | None:
    """Estimate travel ticks from persisted node layout when available."""

    origin_node = state.nodes[origin]
    destination_node = state.nodes[destination]
    if (
        origin_node.layout_x is None
        or origin_node.layout_y is None
        or destination_node.layout_x is None
        or destination_node.layout_y is None
    ):
        return None
    dx = destination_node.layout_x - origin_node.layout_x
    dy = destination_node.layout_y - origin_node.layout_y
    return travel_ticks_from_layout_distance((dx * dx + dy * dy) ** 0.5)


def _alignment_travel_ticks_for_nodes(
    state: object,
    origin: str,
    destination: str,
    alignment: tuple[TrackPoint, ...],
) -> int | None:
    """Estimate travel ticks from endpoint layout plus authored rail alignment."""

    if not alignment:
        return None
    origin_node = state.nodes[origin]
    destination_node = state.nodes[destination]
    if (
        origin_node.layout_x is None
        or origin_node.layout_y is None
        or destination_node.layout_x is None
        or destination_node.layout_y is None
    ):
        return None
    points = (
        TrackPoint(origin_node.layout_x, origin_node.layout_y),
        *alignment,
        TrackPoint(destination_node.layout_x, destination_node.layout_y),
    )
    distance = 0.0
    for start, end in zip(points, points[1:]):
        dx = end.x - start.x
        dy = end.y - start.y
        distance += (dx * dx + dy * dy) ** 0.5
    return travel_ticks_from_layout_distance(distance)


def _validate_track_alignment(alignment: tuple[TrackPoint, ...]) -> None:
    """Validate local rail-alignment metadata."""

    for point in alignment:
        if not isfinite(point.x) or not isfinite(point.y):
            raise ValueError("alignment points must be finite numbers")


class CommandValidationError(ValueError):
    """Validation error with structured fields for preview results."""

    def __init__(self, reason: str, **extra: object) -> None:
        super().__init__(reason)
        self.extra = extra


def _track_alignment_payload(alignment: tuple[TrackPoint, ...]) -> list[dict[str, float]]:
    """Return a normalized alignment payload for command previews."""

    return [{"x": round(point.x, 3), "y": round(point.y, 3)} for point in alignment]


def _validate_build_link(
    state: object,
    command: BuildLink | PreviewBuildLink,
) -> tuple[int, int, int, str | None, float, int]:
    """Validate and normalize a transport link build command."""

    if command.link_id in state.links:
        raise ValueError(f"duplicate link id: {command.link_id}")
    if command.origin == command.destination:
        raise ValueError("link origin and destination must be different")
    if command.origin not in state.nodes:
        raise ValueError(f"unknown link origin: {command.origin}")
    if command.destination not in state.nodes:
        raise ValueError(f"unknown link destination: {command.destination}")
    origin_node = state.nodes[command.origin]
    destination_node = state.nodes[command.destination]
    if origin_node.kind == NodeKind.OUTPOST or destination_node.kind == NodeKind.OUTPOST:
        raise ValueError("outpost_not_operational")
    if command.capacity_per_tick <= 0:
        raise ValueError("link capacity_per_tick must be positive")
    if command.power_required < 0:
        raise ValueError("link power_required cannot be negative")
    _validate_track_alignment(command.alignment)

    origin_world_id = origin_node.world_id
    destination_world_id = destination_node.world_id

    if command.mode == LinkMode.RAIL:
        if origin_world_id != destination_world_id:
            raise ValueError("rail links must stay within one world")
        travel_ticks = command.travel_ticks
        if travel_ticks is None:
            travel_ticks = (
                _alignment_travel_ticks_for_nodes(
                    state,
                    command.origin,
                    command.destination,
                    command.alignment,
                )
                or _layout_travel_ticks_for_nodes(state, command.origin, command.destination)
                or 4
            )
        power_required = 0
        power_source_world_id = None
    elif command.mode == LinkMode.GATE:
        if command.alignment:
            raise ValueError("track alignment is only supported on rail links")
        if origin_world_id == destination_world_id:
            raise ValueError("gate links must connect different worlds")
        origin_kind = state.nodes[command.origin].kind
        destination_kind = state.nodes[command.destination].kind
        if origin_kind != NodeKind.GATE_HUB or destination_kind != NodeKind.GATE_HUB:
            raise ValueError("gate links require gate_hub endpoints")
        for endpoint_node in (origin_node, destination_node):
            if endpoint_node.construction_project_id is not None:
                raise CommandValidationError(
                    "gate_endpoint_under_construction",
                    node_id=endpoint_node.id,
                    construction_project_id=endpoint_node.construction_project_id,
                )
        for endpoint_world_id in sorted({origin_world_id, destination_world_id}):
            site_id = f"site_{endpoint_world_id}_reach"
            site = getattr(state, "space_sites", {}).get(site_id)
            if site is not None and not site.discovered:
                raise CommandValidationError(
                    "destination_not_surveyed",
                    site_id=site_id,
                    world_id=endpoint_world_id,
                )
        travel_ticks = command.travel_ticks if command.travel_ticks is not None else DEFAULT_GATE_TRAVEL_TICKS
        power_required = (
            command.power_required
            if command.power_required > 0
            else DEFAULT_GATE_POWER_REQUIRED
        )
        power_source_world_id = command.power_source_world_id or origin_world_id
        if power_source_world_id not in state.worlds:
            raise ValueError(f"unknown Railgate power source: {power_source_world_id}")
        if power_source_world_id not in {origin_world_id, destination_world_id}:
            raise ValueError("Railgate power source must be one of the endpoint worlds")
    else:
        raise ValueError(f"unsupported link mode: {command.mode.value}")

    if travel_ticks <= 0:
        raise ValueError("link travel_ticks must be positive")
    duplicate_link_id = _duplicate_link_between(
        state,
        command.origin,
        command.destination,
        command.mode,
        bidirectional=command.bidirectional,
    )
    if duplicate_link_id is not None:
        raise ValueError(f"duplicate link endpoints: {duplicate_link_id}")
    cost = link_build_cost(command.mode, travel_ticks)
    build_time = link_build_time(travel_ticks)
    return travel_ticks, command.capacity_per_tick, power_required, power_source_world_id, cost, build_time


def _link_build_payload(
    command: BuildLink | PreviewBuildLink,
    *,
    travel_ticks: int,
    capacity_per_tick: int,
    power_required: int,
    power_source_world_id: str | None,
) -> dict[str, object]:
    """Return a normalized BuildLink command payload."""

    payload: dict[str, object] = {
        "type": "BuildLink",
        "link_id": command.link_id,
        "origin": command.origin,
        "destination": command.destination,
        "mode": command.mode.value,
        "travel_ticks": travel_ticks,
        "capacity_per_tick": capacity_per_tick,
        "bidirectional": command.bidirectional,
    }
    if power_required:
        payload["power_required"] = power_required
    if power_source_world_id is not None:
        payload["power_source_world_id"] = power_source_world_id
    if command.alignment:
        payload["alignment"] = _track_alignment_payload(command.alignment)
    return payload


def _validate_track_signal(
    state: object,
    command: BuildTrackSignal | PreviewBuildTrackSignal,
) -> TrackSignal:
    """Validate and normalize a track-signal command."""

    signal = TrackSignal(
        id=command.signal_id,
        link_id=command.link_id,
        kind=command.kind,
        node_id=command.node_id,
        active=command.active,
    )
    if signal.id in state.track_signals:
        raise ValueError(f"duplicate track signal id: {signal.id}")
    if signal.link_id not in state.links:
        raise ValueError(f"track signal {signal.id} references unknown link {signal.link_id}")
    link = state.links[signal.link_id]
    if link.mode != LinkMode.RAIL:
        raise ValueError(f"track signal {signal.id} target link is not rail")
    if signal.node_id is not None:
        if signal.node_id not in state.nodes:
            raise ValueError(f"track signal {signal.id} references unknown node {signal.node_id}")
        if signal.node_id not in {link.origin, link.destination}:
            raise ValueError("track signal node must be one endpoint of its link")
    return signal


def _track_signal_payload(signal: TrackSignal) -> dict[str, object]:
    """Return a normalized BuildTrackSignal command payload."""

    return {
        "type": "BuildTrackSignal",
        "signal_id": signal.id,
        "link_id": signal.link_id,
        "kind": signal.kind.value,
        "node_id": signal.node_id,
        "active": signal.active,
    }


def _gate_preview_payload(
    state: object,
    command: BuildLink | PreviewBuildLink,
    *,
    power_required: int,
    power_source_world_id: str | None,
) -> dict[str, object]:
    """Return UI-friendly Railgate context for previews and build results."""

    if command.mode != LinkMode.GATE:
        return {}
    if power_source_world_id is None:
        raise ValueError("Railgate power source is required")

    from gaterail.gate import preview_gate_power

    origin_world_id = state.nodes[command.origin].world_id
    destination_world_id = state.nodes[command.destination].world_id
    origin_world = state.worlds[origin_world_id]
    destination_world = state.worlds[destination_world_id]
    power_world = state.worlds[power_source_world_id]
    existing_statuses = preview_gate_power(state)
    allocated_power = sum(
        status.power_required
        for status in existing_statuses.values()
        if status.link_id != command.link_id
        and status.powered
        and status.source_world_id == power_source_world_id
    )
    power_available = max(0, power_world.base_power_margin - allocated_power)
    power_shortfall = max(0, power_required - power_available)
    reverse_link_id = _reverse_link_id_for(
        state,
        command.origin,
        command.destination,
        command.mode,
        ignored_link_id=command.link_id,
    )
    return {
        "source_node_id": command.origin,
        "exit_node_id": command.destination,
        "directional": not command.bidirectional,
        "reverse_available": command.bidirectional or reverse_link_id is not None,
        "reverse_link_id": reverse_link_id,
        "origin_world_id": origin_world_id,
        "origin_world_name": origin_world.name,
        "destination_world_id": destination_world_id,
        "destination_world_name": destination_world.name,
        "power_required": power_required,
        "power_source_world_id": power_source_world_id,
        "power_source_world_name": power_world.name,
        "power_available": power_available,
        "power_shortfall": power_shortfall,
        "powered_if_built": power_shortfall == 0,
    }


def _validate_purchase_train(state: object, command: PurchaseTrain | PreviewPurchaseTrain) -> float:
    """Validate and price a train purchase command."""

    if command.train_id in state.trains:
        raise ValueError(f"duplicate train id: {command.train_id}")
    if command.node_id not in state.nodes:
        raise ValueError(f"unknown train node: {command.node_id}")
    if not command.name.strip():
        raise ValueError("train name cannot be empty")
    if command.capacity <= 0:
        raise ValueError("train capacity must be positive")
    try:
        TrainConsist(command.consist)
    except ValueError as exc:
        raise ValueError(f"unknown train consist: {command.consist}") from exc
    return train_purchase_cost(command.capacity)


def _train_purchase_payload(command: PurchaseTrain | PreviewPurchaseTrain) -> dict[str, object]:
    """Return a normalized PurchaseTrain command payload."""

    return {
        "type": "PurchaseTrain",
        "train_id": command.train_id,
        "name": command.name,
        "node_id": command.node_id,
        "capacity": command.capacity,
        "consist": TrainConsist(command.consist).value,
    }


def _effective_next_departure_tick(state: object, command: CreateSchedule | PreviewCreateSchedule) -> int:
    """Return the normalized next departure tick for a schedule command."""

    if command.next_departure_tick is None:
        return int(state.tick) + 1
    return command.next_departure_tick


def _effective_update_next_departure_tick(state: object, schedule: FreightSchedule, explicit_tick: int | None) -> int:
    """Return a safe next departure tick for an edited schedule."""

    if explicit_tick is not None:
        return explicit_tick
    return max(int(schedule.next_departure_tick), int(state.tick) + 1)


def _schedule_route_stop_ids(command: CreateSchedule | PreviewCreateSchedule) -> tuple[str, ...]:
    """Return the exact required stop sequence for a schedule command."""

    if not command.train_stops:
        return (command.origin, *command.stops, command.destination)

    stop_ids = [command.origin]
    stop_ids.extend(stop.node_id for stop in command.train_stops)
    stop_ids.append(command.destination)

    collapsed: list[str] = []
    for stop_id in stop_ids:
        if collapsed and collapsed[-1] == stop_id:
            continue
        collapsed.append(stop_id)
    return tuple(collapsed)


def _route_for_schedule_command(state: object, command: CreateSchedule | PreviewCreateSchedule, *, require_operational: bool = True) -> object | None:
    """Resolve a schedule route using train-stop waypoints when present."""

    stop_ids = _schedule_route_stop_ids(command)
    if len(stop_ids) < 2:
        return None
    return route_through_stops(
        state,
        stop_ids[0],
        tuple(stop_ids[1:-1]),
        stop_ids[-1],
        require_operational=require_operational,
    )


def _validate_schedule_stops(state: object, command: CreateSchedule | PreviewCreateSchedule) -> None:
    """Validate intermediate schedule stops without requiring a route yet."""

    for stop_id in command.stops:
        if stop_id not in state.nodes:
            raise ValueError(f"unknown schedule stop: {stop_id}")
    for stop in command.train_stops:
        if stop.node_id not in state.nodes:
            raise ValueError(f"unknown schedule stop: {stop.node_id}")
        if stop.units < 0:
            raise ValueError("train stop units cannot be negative")
        if stop.wait_ticks < 0:
            raise ValueError("train stop wait_ticks cannot be negative")
    stop_ids = _schedule_route_stop_ids(command)
    for index in range(len(stop_ids) - 1):
        if stop_ids[index] == stop_ids[index + 1]:
            raise ValueError(f"schedule stop sequence repeats node: {stop_ids[index]}")


def _validate_schedule_fields(
    state: object,
    command: CreateSchedule | PreviewCreateSchedule,
    *,
    existing_schedule_id: str | None = None,
) -> tuple[int, object]:
    """Validate a recurring schedule payload and resolve its current route."""

    if existing_schedule_id is None and command.schedule_id in state.schedules:
        raise ValueError(f"duplicate schedule id: {command.schedule_id}")
    if (
        existing_schedule_id is not None
        and command.schedule_id != existing_schedule_id
        and command.schedule_id in state.schedules
    ):
        raise ValueError(f"duplicate schedule id: {command.schedule_id}")
    if command.train_id not in state.trains:
        raise ValueError(f"unknown schedule train: {command.train_id}")
    if command.origin not in state.nodes:
        raise ValueError(f"unknown schedule origin: {command.origin}")
    if command.destination not in state.nodes:
        raise ValueError(f"unknown schedule destination: {command.destination}")
    if command.origin == command.destination:
        raise ValueError("schedule origin and destination must be different")
    _validate_schedule_stops(state, command)
    if command.units_per_departure <= 0:
        raise ValueError("schedule units_per_departure must be positive")
    if command.interval_ticks <= 0:
        raise ValueError("schedule interval_ticks must be positive")
    train = state.trains[command.train_id]
    if not train.idle:
        raise ValueError(f"schedule train {command.train_id} is not idle")
    if train.node_id != command.origin:
        raise ValueError(f"schedule train {command.train_id} is at {train.node_id}, not {command.origin}")
    if command.units_per_departure > train.capacity:
        raise ValueError("schedule units_per_departure cannot exceed train capacity")
    required_consist = required_consist_for(command.cargo_type)
    if not consist_can_carry(train.consist, command.cargo_type):
        raise ValueError(
            f"schedule cargo {command.cargo_type.value} requires "
            f"{required_consist.value} consist, train is {train.consist.value}"
        )
    next_departure_tick = _effective_next_departure_tick(state, command)
    if next_departure_tick <= state.tick:
        raise ValueError("schedule next_departure_tick must be in the future")
    route = _route_for_schedule_command(state, command)
    if route is None:
        raise ValueError(f"no route {'->'.join(_schedule_route_stop_ids(command))}")
    if route.travel_ticks <= 0:
        raise ValueError("schedule route must have positive travel time")
    return next_departure_tick, route


def _validate_create_schedule(
    state: object,
    command: CreateSchedule | PreviewCreateSchedule,
) -> tuple[int, object]:
    """Validate a recurring schedule and resolve its current route."""

    return _validate_schedule_fields(state, command)


def _schedule_payload(
    command: CreateSchedule | PreviewCreateSchedule,
    *,
    next_departure_tick: int,
    include_empty_train_stops: bool = False,
) -> dict[str, object]:
    """Return a normalized CreateSchedule command payload."""

    payload: dict[str, object] = {
        "type": "CreateSchedule",
        "schedule_id": command.schedule_id,
        "train_id": command.train_id,
        "origin": command.origin,
        "destination": command.destination,
        "cargo_type": command.cargo_type.value,
        "units_per_departure": command.units_per_departure,
        "interval_ticks": command.interval_ticks,
        "next_departure_tick": next_departure_tick,
        "priority": command.priority,
        "active": command.active,
        "return_to_origin": command.return_to_origin,
        "stops": list(command.stops),
    }
    if command.train_stops or include_empty_train_stops:
        payload["train_stops"] = [
            {
                "node_id": s.node_id,
                "action": s.action.value,
                "cargo_type": None if s.cargo_type is None else s.cargo_type.value,
                "units": s.units,
                "wait_condition": s.wait_condition.value,
                "wait_ticks": s.wait_ticks,
            }
            for s in command.train_stops
        ]
    return payload


def _schedule_update_draft(
    state: object,
    command: UpdateSchedule | PreviewUpdateSchedule,
    schedule: FreightSchedule,
) -> PreviewCreateSchedule:
    """Merge a partial schedule edit with the existing schedule."""

    return PreviewCreateSchedule(
        schedule_id=schedule.id,
        train_id=schedule.train_id if command.train_id is None else command.train_id,
        origin=schedule.origin if command.origin is None else command.origin,
        destination=schedule.destination if command.destination is None else command.destination,
        cargo_type=schedule.cargo_type if command.cargo_type is None else command.cargo_type,
        units_per_departure=(
            schedule.units_per_departure
            if command.units_per_departure is None
            else command.units_per_departure
        ),
        interval_ticks=schedule.interval_ticks if command.interval_ticks is None else command.interval_ticks,
        next_departure_tick=_effective_update_next_departure_tick(
            state,
            schedule,
            command.next_departure_tick,
        ),
        priority=schedule.priority if command.priority is None else command.priority,
        active=schedule.active if command.active is None else command.active,
        return_to_origin=(
            schedule.return_to_origin
            if command.return_to_origin is None
            else command.return_to_origin
        ),
        stops=schedule.stops if command.stops is None else command.stops,
        train_stops=(
            schedule.train_stops if command.train_stops is None else command.train_stops
        ),
    )


def _schedule_update_payload(
    command: UpdateSchedule | PreviewUpdateSchedule,
    draft: PreviewCreateSchedule,
    *,
    next_departure_tick: int,
) -> dict[str, object]:
    """Return a normalized UpdateSchedule command payload."""

    payload = _schedule_payload(
        draft,
        next_departure_tick=next_departure_tick,
        include_empty_train_stops=command.train_stops is not None,
    )
    payload["type"] = "UpdateSchedule"
    payload["schedule_id"] = command.schedule_id
    return payload


def _schedule_active_trip_train(state: object, schedule_id: str) -> FreightTrain | None:
    """Return a train currently running one schedule trip, if any."""

    service_id = f"schedule:{schedule_id}"
    for train in state.trains.values():
        if train.order_id == service_id and not train.idle:
            return train
    return None


def _validate_update_schedule(
    state: object,
    command: UpdateSchedule | PreviewUpdateSchedule,
) -> tuple[FreightSchedule, PreviewCreateSchedule, int, object]:
    """Validate an existing schedule edit and resolve its route."""

    schedule = state.schedules.get(command.schedule_id)
    if schedule is None:
        raise ValueError(f"unknown schedule: {command.schedule_id}")
    if _schedule_active_trip_train(state, command.schedule_id) is not None:
        raise ValueError("schedule_in_active_trip")
    draft = _schedule_update_draft(state, command, schedule)
    next_departure_tick, route = _validate_schedule_fields(
        state,
        draft,
        existing_schedule_id=schedule.id,
    )
    return schedule, draft, next_departure_tick, route


def _schedule_delete_payload(command: DeleteSchedule | PreviewDeleteSchedule) -> dict[str, object]:
    """Return a normalized DeleteSchedule command payload."""

    return {"type": "DeleteSchedule", "schedule_id": command.schedule_id}


def _validate_delete_schedule(
    state: object,
    command: DeleteSchedule | PreviewDeleteSchedule,
) -> FreightSchedule:
    """Validate deleting a schedule without orphaning an active train trip."""

    schedule = state.schedules.get(command.schedule_id)
    if schedule is None:
        raise ValueError(f"unknown schedule: {command.schedule_id}")
    if _schedule_active_trip_train(state, command.schedule_id) is not None:
        raise ValueError("schedule_in_active_trip")
    return schedule


def _used_slots_for_route_context(state: object, link: NetworkLink, gate_status: object | None) -> int:
    """Return current slot pressure for route preview context."""

    used = int(state.link_usage_this_tick.get(link.id, 0))
    if gate_status is not None:
        used = max(used, int(getattr(gate_status, "slots_used", 0)))
    return used


def _route_context_payload(state: object, route: object) -> dict[str, object]:
    """Return schedule-preview route context focused on gate handoffs."""

    from gaterail.gate import preview_gate_power

    gate_statuses = state.gate_statuses if state.gate_statuses else preview_gate_power(state)
    gate_link_ids: list[str] = []
    gate_handoffs: list[dict[str, object]] = []
    route_warnings: list[dict[str, object]] = []
    node_ids = tuple(route.node_ids)

    for index, link_id in enumerate(route.link_ids):
        link = state.links[link_id]
        if link.mode != LinkMode.GATE:
            continue
        gate_link_ids.append(link.id)
        from_node_id = node_ids[index] if index < len(node_ids) else link.origin
        to_node_id = node_ids[index + 1] if index + 1 < len(node_ids) else link.destination
        from_world = state.worlds[state.nodes[from_node_id].world_id]
        to_world = state.worlds[state.nodes[to_node_id].world_id]
        status = gate_statuses.get(link.id)
        powered = bool(status.powered) if status is not None else state.link_operational(link)
        power_shortfall = int(getattr(status, "power_shortfall", 0)) if status is not None else 0
        capacity, disruptions = effective_link_capacity(state, link)
        used = _used_slots_for_route_context(state, link, status)
        remaining = max(0, capacity - used)
        pressure = round(used / capacity, 3) if capacity > 0 else (1.0 if used > 0 else 0.0)
        disruption_reasons = [disruption.reason for disruption in disruptions]

        warnings: list[dict[str, object]] = []
        if not powered:
            warnings.append(
                {
                    "severity": "blocked",
                    "reason": f"gate {link.id} unpowered",
                }
            )
        if disruptions:
            warnings.append(
                {
                    "severity": "blocked" if capacity == 0 else "degraded",
                    "reason": ", ".join(disruption_reasons),
                }
            )
        if capacity > 0 and used >= capacity:
            warnings.append(
                {
                    "severity": "congested",
                    "reason": f"gate slots full on {link.id}",
                }
            )
        elif capacity > 0 and pressure >= 0.75:
            warnings.append(
                {
                    "severity": "hot",
                    "reason": f"gate {link.id} at {int(round(pressure * 100))}% slot pressure",
                }
            )

        gate_handoff = {
            "link_id": link.id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "source_node_id": link.origin,
            "exit_node_id": link.destination,
            "directional": not link.bidirectional,
            "traversal_direction": "forward" if from_node_id == link.origin else "reverse",
            "from_world_id": from_world.id,
            "from_world_name": from_world.name,
            "to_world_id": to_world.id,
            "to_world_name": to_world.name,
            "powered": powered,
            "power_required": link.power_required,
            "power_shortfall": power_shortfall,
            "slots_used": used,
            "slot_capacity": capacity,
            "base_capacity": link.capacity_per_tick,
            "slots_remaining": remaining,
            "pressure": pressure,
            "disrupted": bool(disruptions),
            "disruption_reasons": disruption_reasons,
            "warnings": warnings,
        }
        gate_handoffs.append(gate_handoff)
        for warning in warnings:
            route_warnings.append({"link_id": link.id, **warning})

    return {
        "gate_link_ids": gate_link_ids,
        "gate_handoffs": gate_handoffs,
        "route_warnings": route_warnings,
    }


def _blocked_links_for_route_debug(state: object, route: object) -> list[dict[str, object]]:
    """Return player-facing link blockers for a structurally valid route."""

    blocked: list[dict[str, object]] = []
    for link_id in route.link_ids:
        link = state.links[link_id]
        status = state.gate_statuses.get(link.id)
        if not link.active:
            blocked.append(
                {
                    "link_id": link.id,
                    "mode": link.mode.value,
                    "severity": "blocked",
                    "reason": f"link {link.id} inactive",
                }
            )
            continue
        if link.mode == LinkMode.GATE and not state.link_operational(link):
            blocked.append(
                {
                    "link_id": link.id,
                    "mode": link.mode.value,
                    "severity": "blocked",
                    "reason": f"gate {link.id} unpowered",
                }
            )
            continue
        capacity, disruptions = effective_link_capacity(state, link)
        used = _used_slots_for_route_context(state, link, status)
        if disruptions and capacity <= 0:
            blocked.append(
                {
                    "link_id": link.id,
                    "mode": link.mode.value,
                    "severity": "blocked",
                    "reason": f"link {link.id} disrupted: {', '.join(item.reason for item in disruptions)}",
                }
            )
        elif capacity > 0 and used >= capacity:
            reason = f"gate slots full on {link.id}" if link.mode == LinkMode.GATE else f"traffic capacity full on {link.id}"
            blocked.append(
                {
                    "link_id": link.id,
                    "mode": link.mode.value,
                    "severity": "blocked",
                    "reason": reason,
                }
            )
    return blocked


def _route_segments_debug(state: object, stop_ids: tuple[str, ...]) -> list[dict[str, object]]:
    """Return per-segment route status for schedule previews."""

    segments: list[dict[str, object]] = []
    for index in range(len(stop_ids) - 1):
        from_node_id = stop_ids[index]
        to_node_id = stop_ids[index + 1]
        if from_node_id not in state.nodes:
            segments.append(
                {
                    "from_node_id": from_node_id,
                    "to_node_id": to_node_id,
                    "ok": False,
                    "reason": f"unknown node {from_node_id}",
                    "travel_ticks": 0,
                    "node_ids": [],
                    "link_ids": [],
                    "blocked_links": [],
                }
            )
            continue
        if to_node_id not in state.nodes:
            segments.append(
                {
                    "from_node_id": from_node_id,
                    "to_node_id": to_node_id,
                    "ok": False,
                    "reason": f"unknown node {to_node_id}",
                    "travel_ticks": 0,
                    "node_ids": [],
                    "link_ids": [],
                    "blocked_links": [],
                }
            )
            continue

        route = shortest_route(state, from_node_id, to_node_id)
        if route is not None:
            segments.append(
                {
                    "from_node_id": from_node_id,
                    "to_node_id": to_node_id,
                    "ok": True,
                    "reason": None,
                    "travel_ticks": route.travel_ticks,
                    "node_ids": list(route.node_ids),
                    "link_ids": list(route.link_ids),
                    "blocked_links": [],
                }
            )
            continue

        structural_route = shortest_route(
            state,
            from_node_id,
            to_node_id,
            require_operational=False,
        )
        if structural_route is None:
            segments.append(
                {
                    "from_node_id": from_node_id,
                    "to_node_id": to_node_id,
                    "ok": False,
                    "reason": f"no route {from_node_id}->{to_node_id}",
                    "travel_ticks": 0,
                    "node_ids": [],
                    "link_ids": [],
                    "blocked_links": [],
                }
            )
            continue

        segments.append(
            {
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "ok": False,
                "reason": f"no operational route {from_node_id}->{to_node_id}",
                "travel_ticks": structural_route.travel_ticks,
                "node_ids": list(structural_route.node_ids),
                "link_ids": list(structural_route.link_ids),
                "blocked_links": _blocked_links_for_route_debug(state, structural_route),
            }
        )
    return segments


def _schedule_validation_errors(reason: str) -> list[dict[str, object]]:
    """Return structured validation reasons for route tooling."""

    code = "invalid_schedule"
    if reason.startswith("unknown schedule stop: "):
        code = "unknown_stop"
    elif reason.startswith("unknown schedule: "):
        code = "unknown_schedule"
    elif reason.startswith("no route "):
        code = "invalid_path"
    elif reason == "schedule_in_active_trip":
        code = "active_trip"
    elif " requires " in reason and " consist" in reason and "train is " in reason:
        code = "incompatible_consist"
    return [{"code": code, "reason": reason}]


def _schedule_route_debug_payload(
    state: object,
    command: CreateSchedule | PreviewCreateSchedule,
    reason: str | None = None,
) -> dict[str, object]:
    """Return route stops, segments, and validation details for a schedule command."""

    stop_ids = _schedule_route_stop_ids(command)
    payload: dict[str, object] = {
        "route_stop_ids": list(stop_ids),
        "route_segments": _route_segments_debug(state, stop_ids),
    }
    if reason is not None:
        payload["validation_errors"] = _schedule_validation_errors(reason)

    if all(node_id in state.nodes for node_id in stop_ids):
        structural_route = _route_for_schedule_command(
            state,
            command,
            require_operational=False,
        )
        if structural_route is not None and structural_route.travel_ticks > 0:
            payload.update(
                {
                    "route_travel_ticks": structural_route.travel_ticks,
                    "route_node_ids": list(structural_route.node_ids),
                    "route_link_ids": list(structural_route.link_ids),
                    **_route_context_payload(state, structural_route),
                }
            )
    return payload


def _preview_error(command_type: str, target_id: str, exc: ValueError) -> dict[str, object]:
    """Return a non-mutating invalid preview result."""

    reason = str(exc)
    extra = exc.extra if isinstance(exc, CommandValidationError) else {}
    return command_result(
        command_type,
        ok=False,
        target_id=target_id,
        message=reason,
        reason=reason,
        **extra,
    )


def _cash_available(state: object, cost: float) -> bool:
    """Return whether the player can afford a construction cost."""

    return state.finance.cash >= cost


def _insufficient_cash_message(state: object, label: str, cost: float) -> str:
    """Return a consistent insufficient-cash validation message."""

    return f"insufficient cash for {label}: need {cost:.0f}, have {state.finance.cash:.0f}"


def _facility_kind_value(kind: FacilityComponentKind | str) -> str:
    """Return a stable string value for one component kind payload."""

    if isinstance(kind, FacilityComponentKind):
        return kind.value
    return str(kind)


def _transfer_link_kind_value(kind: TransferLinkKind | str) -> str:
    """Return a stable string value for one transfer-link kind payload."""

    if isinstance(kind, TransferLinkKind):
        return kind.value
    return str(kind)


def _resolve_transfer_link_kind(kind: TransferLinkKind | str) -> TransferLinkKind:
    """Parse a transfer-link kind or raise a command-facing validation error."""

    if isinstance(kind, TransferLinkKind):
        return kind
    raw_kind = str(kind)
    try:
        return TransferLinkKind(raw_kind)
    except ValueError as exc:
        raise ValueError(f"unknown transfer link kind: {raw_kind}") from exc


def _resolve_facility_component_kind(kind: FacilityComponentKind | str) -> FacilityComponentKind:
    """Parse a component kind or raise a command-facing validation error."""

    if isinstance(kind, FacilityComponentKind):
        return kind
    raw_kind = str(kind)
    try:
        return FacilityComponentKind(raw_kind)
    except ValueError as exc:
        raise ValueError(f"unknown facility component kind: {raw_kind}") from exc


def _plain_cargo_cost(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Return stable JSON-safe cargo build-cost payloads."""

    return {
        cargo.value: int(units)
        for cargo, units in sorted(mapping.items(), key=lambda item: item[0].value)
        if int(units) > 0
    }


_MISSION_LAUNCH_KINDS = frozenset({NodeKind.ORBITAL_YARD, NodeKind.SPACEPORT})
_MISSION_RETURN_KINDS = frozenset(
    {
        NodeKind.COLLECTION_STATION,
        NodeKind.ORBITAL_YARD,
        NodeKind.SPACEPORT,
        NodeKind.WAREHOUSE,
    }
)
_OUTPOST_REFUND_NODE_KINDS = frozenset({NodeKind.DEPOT, NodeKind.WAREHOUSE})


def _command_failure(
    command_type: str,
    target_id: str,
    *,
    reason: str,
    message: str,
    **extra: object,
) -> dict[str, object]:
    """Return one structured command failure without raising."""

    return command_result(
        command_type,
        ok=False,
        target_id=target_id,
        message=message,
        reason=reason,
        **extra,
    )


def _survey_site_payload(
    state: object,
    command: SurveySpaceSite | PreviewSurveySpaceSite,
) -> tuple[dict[str, object] | None, dict[str, object]]:
    """Validate a site survey command and return command-facing payload fields."""

    site = getattr(state, "space_sites", {}).get(command.site_id)
    if site is None:
        return (
            _command_failure(
                command.type,
                command.site_id,
                reason="unknown_space_site",
                message=f"unknown space site: {command.site_id}",
            ),
            {},
        )
    return (
        None,
        {
            "site": site,
            "resource_id": site.resource_id,
            "travel_ticks": int(site.travel_ticks),
            "base_yield": int(site.base_yield),
            "discovered": bool(site.discovered),
            "site_cargo_type": site.cargo_type.value if site.cargo_type is not None else None,
            "normalized_command": {
                "type": "SurveySpaceSite",
                "site_id": command.site_id,
            },
        },
    )


def _next_outpost_id(state: object) -> str:
    """Return the next deterministic outpost id for one state."""

    highest = 0
    for node_id in getattr(state, "nodes", {}):
        if not str(node_id).startswith("outpost_"):
            continue
        suffix = str(node_id)[len("outpost_") :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"outpost_{highest + 1}"


def _resolve_outpost_kind(raw_kind: str) -> OutpostKind:
    """Parse one outpost kind or raise a command-facing validation error."""

    try:
        return OutpostKind(raw_kind)
    except ValueError as exc:
        raise ValueError(f"unknown outpost kind: {raw_kind}") from exc


def _outpost_distance(origin: NetworkNode, candidate: NetworkNode) -> float:
    """Return a deterministic distance metric for refund-node selection."""

    if (
        origin.layout_x is None
        or origin.layout_y is None
        or candidate.layout_x is None
        or candidate.layout_y is None
    ):
        return float("inf")
    dx = candidate.layout_x - origin.layout_x
    dy = candidate.layout_y - origin.layout_y
    return (dx * dx + dy * dy) ** 0.5


def _refund_node_for_outpost(state: object, outpost: NetworkNode) -> NetworkNode | None:
    """Return the nearest same-world refund node for one outpost."""

    candidates = [
        node
        for node in getattr(state, "nodes", {}).values()
        if node.world_id == outpost.world_id
        and node.id != outpost.id
        and node.kind in _OUTPOST_REFUND_NODE_KINDS
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (_outpost_distance(outpost, item), item.id))


def _outpost_project_for_node(state: object, node: NetworkNode) -> ConstructionProject | None:
    """Return the construction project attached to one outpost node."""

    project_id = node.construction_project_id
    if project_id:
        project = getattr(state, "construction_projects", {}).get(project_id)
        if project is not None:
            return project
    for project in getattr(state, "construction_projects", {}).values():
        if project.target_node_id == node.id:
            return project
    return None


def _planned_outpost_refund(project: ConstructionProject) -> dict[CargoType, int]:
    """Return the unbounded half-refund mapping for one outpost project."""

    return {
        cargo_type: units // 2
        for cargo_type, units in project.delivered_cargo.items()
        if units // 2 > 0
    }


def _project_outpost_refund(
    project: ConstructionProject, refund_node: NetworkNode
) -> tuple[dict[CargoType, int], dict[CargoType, int]]:
    """Forecast the refund split between accepted and capacity-dropped units."""

    planned = _planned_outpost_refund(project)
    available_space = max(
        0, refund_node.effective_storage_capacity() - refund_node.total_inventory()
    )
    accepted: dict[CargoType, int] = {}
    dropped: dict[CargoType, int] = {}
    remaining_space = available_space
    for cargo_type in sorted(planned, key=lambda c: c.value):
        wanted = planned[cargo_type]
        fits = max(0, min(wanted, remaining_space))
        remaining_space -= fits
        if fits > 0:
            accepted[cargo_type] = fits
        if fits < wanted:
            dropped[cargo_type] = wanted - fits
    return accepted, dropped


def _outpost_layout_payload(command: BuildOutpost | PreviewBuildOutpost) -> dict[str, float] | None:
    """Return JSON-safe layout metadata for one outpost command."""

    return _node_layout_payload(command.layout_x, command.layout_y)


def _outpost_command_payload(
    outpost_id: str,
    command: BuildOutpost | PreviewBuildOutpost,
    *,
    layout: dict[str, float],
) -> dict[str, object]:
    """Return the normalized BuildOutpost command payload."""

    return {
        "type": "BuildOutpost",
        "outpost_id": outpost_id,
        "world_id": command.world_id,
        "outpost_kind": command.outpost_kind,
        "layout": layout,
    }


def _validate_outpost_build(
    state: object,
    command: BuildOutpost | PreviewBuildOutpost,
) -> tuple[str, OutpostKind, dict[str, float], float, dict[CargoType, int]]:
    """Validate one outpost-build command and return normalized values."""

    outpost_id = command.outpost_id.strip() or _next_outpost_id(state)
    if command.world_id not in state.worlds:
        raise ValueError(f"world_not_found:{command.world_id}")
    if outpost_id in state.nodes:
        raise ValueError(f"duplicate_outpost_id:{outpost_id}")
    layout = _outpost_layout_payload(command)
    if layout is None:
        raise ValueError("missing_layout")
    kind = _resolve_outpost_kind(command.outpost_kind)
    cost = outpost_build_cost(kind)
    cargo_required = outpost_build_cargo(kind)
    return outpost_id, kind, layout, cost, cargo_required


def _validate_mining_mission(
    state: object,
    command: DispatchMiningMission | PreviewDispatchMiningMission,
) -> tuple[dict[str, object] | None, dict[str, object]]:
    """Validate one mining mission command and return either an error or normalized fields."""

    target_id = command.mission_id
    if command.mission_id in state.mining_missions:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="duplicate_mining_mission",
                message=f"duplicate mining mission id: {command.mission_id}",
            ),
            {},
        )
    site = state.space_sites.get(command.site_id)
    if site is None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="unknown_space_site",
                message=f"unknown space site: {command.site_id}",
            ),
            {},
        )
    if not site.discovered:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="site_not_surveyed",
                message=f"space site not surveyed: {command.site_id}",
                site_id=command.site_id,
                normalized_command={
                    "type": "SurveySpaceSite",
                    "site_id": command.site_id,
                },
            ),
            {},
        )
    launch_node = state.nodes.get(command.launch_node_id)
    if launch_node is None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="unknown_launch_node",
                message=f"unknown launch node: {command.launch_node_id}",
            ),
            {},
        )
    return_node = state.nodes.get(command.return_node_id)
    if return_node is None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="unknown_return_node",
                message=f"unknown return node: {command.return_node_id}",
            ),
            {},
        )
    if launch_node.construction_project_id is not None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="extraction_under_construction",
                message=f"launch node under construction: {command.launch_node_id}",
                node_id=command.launch_node_id,
                construction_project_id=launch_node.construction_project_id,
            ),
            {},
        )
    if return_node.construction_project_id is not None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="return_under_construction",
                message=f"return node under construction: {command.return_node_id}",
                node_id=command.return_node_id,
                construction_project_id=return_node.construction_project_id,
            ),
            {},
        )
    if launch_node.kind not in _MISSION_LAUNCH_KINDS:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="invalid_launch_kind",
                message=f"invalid launch kind: {launch_node.kind.value}",
            ),
            {},
        )
    if return_node.kind not in _MISSION_RETURN_KINDS:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="invalid_return_kind",
                message=f"invalid return kind: {return_node.kind.value}",
            ),
            {},
        )
    launch_world = state.worlds.get(launch_node.world_id)
    if launch_world is None:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="world_not_found",
                message=f"unknown world: {launch_node.world_id}",
            ),
            {},
        )
    fuel_input = max(mission_fuel_required(site), max(0, int(command.fuel_input)))
    power_input = max(mission_power_required(site), max(0, int(command.power_input)))
    fuel_available = launch_node.stock(CargoType.FUEL)
    power_available = max(0, int(launch_world.base_power_margin))
    normalized_command = {
        "type": "DispatchMiningMission",
        "mission_id": command.mission_id,
        "site_id": command.site_id,
        "launch_node_id": command.launch_node_id,
        "return_node_id": command.return_node_id,
        "fuel_input": fuel_input,
        "power_input": power_input,
    }
    haul_bucket = "cargo" if site.cargo_type is not None else "resource"
    haul_label = site.cargo_type.value if site.cargo_type is not None else site.resource_id
    result_extra = {
        "travel_ticks": site.travel_ticks * 2,
        "expected_yield": site.base_yield,
        "fuel_required": fuel_input,
        "fuel_available": fuel_available,
        "power_required": power_input,
        "power_available": power_available,
        "power_shortfall_if_dispatched": max(0, power_input - power_available),
        "return_capacity_estimate": mission_return_capacity(return_node),
        "site_cargo_type": site.cargo_type.value if site.cargo_type is not None else None,
        "site_resource_id": site.resource_id,
        "haul_bucket": haul_bucket,
        "haul_label": haul_label,
        "normalized_command": normalized_command,
    }
    if fuel_available < fuel_input:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="insufficient_fuel",
                message=f"insufficient fuel: need {fuel_input}, have {fuel_available}",
                **result_extra,
            ),
            {},
        )
    if power_available < power_input:
        return (
            _command_failure(
                command.type,
                target_id,
                reason="insufficient_power",
                message=f"insufficient power: need {power_input}, have {power_available}",
                **result_extra,
            ),
            {},
        )
    return (
        None,
        {
            "site": site,
            "launch_node": launch_node,
            "return_node": return_node,
            "launch_world": launch_world,
            "fuel_input": fuel_input,
            "power_input": power_input,
            **result_extra,
        },
    )


def _missing_component_build_cargo(
    state: object,
    node: NetworkNode,
    required_cargo: dict[CargoType, int],
) -> dict[CargoType, int]:
    """Return build-cargo shortfall from construction inventory plus node stock."""

    construction_inventory = getattr(state, "construction_inventory", {})
    return {
        cargo_type: units - node.stock(cargo_type) - int(construction_inventory.get(cargo_type, 0))
        for cargo_type, units in required_cargo.items()
        if node.stock(cargo_type) + int(construction_inventory.get(cargo_type, 0)) < units
    }


def _insufficient_component_cargo_message(
    kind: FacilityComponentKind,
    missing: dict[CargoType, int],
) -> str:
    """Return a stable error string for component construction-cargo shortages."""

    parts = ", ".join(
        f"{cargo_type.value} {units}"
        for cargo_type, units in sorted(missing.items(), key=lambda item: item[0].value)
    )
    return f"insufficient construction parts for {kind.value}: missing {parts}"


def _consume_construction_cargo(
    state: object,
    node: NetworkNode,
    required_cargo: dict[CargoType, int],
) -> None:
    """Consume construction cargo, preferring the player construction inventory."""

    construction_inventory = getattr(state, "construction_inventory", {})
    for cargo_type, units in required_cargo.items():
        remaining = int(units)
        from_inventory = min(remaining, int(construction_inventory.get(cargo_type, 0)))
        if from_inventory > 0:
            updated = int(construction_inventory.get(cargo_type, 0)) - from_inventory
            if updated:
                construction_inventory[cargo_type] = updated
            else:
                construction_inventory.pop(cargo_type, None)
            remaining -= from_inventory
        if remaining > 0:
            node.remove_inventory(cargo_type, remaining)


def _validate_facility_component(
    state: object,
    command: BuildFacilityComponent | PreviewBuildFacilityComponent,
) -> tuple[FacilityComponent, float, dict[CargoType, int], tuple[InternalConnection, ...]]:
    """Validate a facility component install and return its normalized fields."""

    if command.node_id not in state.nodes:
        raise ValueError(f"unknown node: {command.node_id}")
    if not command.component_id.strip():
        raise ValueError("component id cannot be empty")
    node = state.nodes[command.node_id]
    facility = node.facility
    if facility is not None and command.component_id in facility.components:
        raise ValueError(f"duplicate component id: {command.component_id}")
    kind = _resolve_facility_component_kind(command.kind)
    if command.capacity < 0:
        raise ValueError("component capacity cannot be negative")
    if command.rate < 0:
        raise ValueError("component rate cannot be negative")
    if command.power_required < 0:
        raise ValueError("component power_required cannot be negative")
    if command.power_provided < 0:
        raise ValueError("component power_provided cannot be negative")
    if command.train_capacity < 0:
        raise ValueError("component train_capacity cannot be negative")
    if command.concurrent_loading_limit <= 0:
        raise ValueError("component concurrent_loading_limit must be positive")
    if command.stored_charge < 0:
        raise ValueError("component stored_charge cannot be negative")
    if command.discharge_per_tick < 0:
        raise ValueError("component discharge_per_tick cannot be negative")

    inputs = dict(command.inputs or {})
    outputs = dict(command.outputs or {})
    cargo_cost = (
        dict(command.construction_cargo)
        if command.construction_cargo is not None
        else facility_component_build_cargo(kind)
    )
    _validate_facility_cargo_quantities(inputs, "input")
    _validate_facility_cargo_quantities(outputs, "output")

    capacity = int(command.capacity)
    rate = int(command.rate)
    power_required = int(command.power_required)
    power_provided = int(command.power_provided)
    train_capacity = int(command.train_capacity)
    concurrent_loading_limit = int(command.concurrent_loading_limit)
    stored_charge = int(command.stored_charge)
    discharge_per_tick = int(command.discharge_per_tick)

    if not command.ports:
        ports = tuple(facility_component_default_ports(kind, command.component_id))
    else:
        ports = command.ports

    if power_required == 0:
        power_required = facility_component_default_power_required(kind)
    if power_provided == 0:
        power_provided = facility_component_default_power_provided(kind)
    if train_capacity == 0:
        train_capacity = facility_component_default_train_capacity(kind)
    if discharge_per_tick == 0:
        discharge_per_tick = facility_component_default_discharge_per_tick(kind)
    concurrent_loading_limit = max(
        concurrent_loading_limit,
        facility_component_default_concurrent_loading_limit(kind),
    )

    if kind == FacilityComponentKind.WAREHOUSE_BAY and capacity <= 0:
        capacity = 600
    if kind == FacilityComponentKind.STORAGE_BAY and capacity <= 0:
        raise ValueError("storage_bay capacity must be positive")
    if kind == FacilityComponentKind.LOADER and rate <= 0:
        raise ValueError("loader rate must be positive")
    if kind == FacilityComponentKind.UNLOADER and rate <= 0:
        raise ValueError("unloader rate must be positive")
    if kind == FacilityComponentKind.FACTORY_BLOCK and not (inputs or outputs):
        raise ValueError("factory_block requires at least one input or output")

    seen_port_ids: set[str] = set()
    for port in ports:
        if not port.id.strip():
            raise ValueError("port id cannot be empty")
        if port.id in seen_port_ids:
            raise ValueError(f"duplicate port id on component: {port.id}")
        seen_port_ids.add(port.id)
        if port.rate < 0:
            raise ValueError(f"port {port.id} rate cannot be negative")
        if port.capacity < 0:
            raise ValueError(f"port {port.id} capacity cannot be negative")

    component = FacilityComponent(
        id=command.component_id,
        kind=kind,
        ports={port.id: port for port in ports},
        capacity=capacity,
        rate=rate,
        power_required=power_required,
        power_provided=power_provided,
        inputs=dict(inputs),
        outputs=dict(outputs),
        train_capacity=train_capacity,
        concurrent_loading_limit=concurrent_loading_limit,
        stored_charge=stored_charge,
        discharge_per_tick=discharge_per_tick,
        build_cost=float(facility_component_build_cost(kind)),
    )
    _validate_inline_facility_connections(node, component, command.connections)
    missing_cargo = _missing_component_build_cargo(state, node, cargo_cost)
    if missing_cargo:
        raise ValueError(_insufficient_component_cargo_message(kind, missing_cargo))
    return component, facility_component_build_cost(kind), cargo_cost, command.connections


def _validate_facility_cargo_quantities(mapping: dict[CargoType, int], label: str) -> None:
    """Validate that component cargo flow quantities are positive."""

    for cargo_type, units in mapping.items():
        if units <= 0:
            raise ValueError(f"{label} units for {cargo_type.value} must be positive")


def _validate_inline_facility_connections(
    node: NetworkNode,
    component: FacilityComponent,
    connections: tuple[InternalConnection, ...],
) -> None:
    """Validate connections bundled into a component build against a prospective facility."""

    if not connections:
        return
    facility = Facility(
        components={} if node.facility is None else dict(node.facility.components),
        connections={} if node.facility is None else dict(node.facility.connections),
    )
    facility.components[component.id] = component
    for connection in connections:
        if (
            connection.source_component_id != component.id
            and connection.destination_component_id != component.id
        ):
            raise ValueError("inline connection must reference the component being built")
        _validate_internal_connection(facility, connection)
        facility.connections[connection.id] = connection


def _facility_component_payload(
    command: BuildFacilityComponent | PreviewBuildFacilityComponent,
    *,
    component: FacilityComponent,
    cargo_cost: dict[CargoType, int],
    connections: tuple[InternalConnection, ...],
) -> dict[str, object]:
    """Return a normalized BuildFacilityComponent command payload."""

    return {
        "type": "BuildFacilityComponent",
        "component_id": command.component_id,
        "node_id": command.node_id,
        "kind": component.kind.value,
        "capacity": int(component.capacity),
        "rate": int(component.rate),
        "power_required": int(component.power_required),
        "power_provided": int(component.power_provided),
        "train_capacity": int(component.train_capacity),
        "concurrent_loading_limit": int(component.concurrent_loading_limit),
        "stored_charge": int(component.stored_charge),
        "discharge_per_tick": int(component.discharge_per_tick),
        "cargo_cost": _plain_cargo_cost(cargo_cost),
        "construction_cargo": _plain_cargo_cost(cargo_cost),
        "inputs": _plain_cargo_cost(component.inputs),
        "outputs": _plain_cargo_cost(component.outputs),
        "ports": [
            {
                "id": port.id,
                "direction": port.direction.value,
                "cargo_type": None if port.cargo_type is None else port.cargo_type.value,
                "rate": int(port.rate),
                "capacity": int(port.capacity),
            }
            for port in sorted(component.ports.values(), key=lambda item: item.id)
        ],
        "connections": [
            {
                "id": connection.id,
                "source_component_id": connection.source_component_id,
                "source_port_id": connection.source_port_id,
                "destination_component_id": connection.destination_component_id,
                "destination_port_id": connection.destination_port_id,
                "link_type": _transfer_link_kind_value(connection.link_type),
            }
            for connection in connections
        ],
    }


def _require_facility(state: object, node_id: str) -> tuple[NetworkNode, Facility]:
    """Return a node's facility, raising a command-facing validation error."""

    if node_id not in state.nodes:
        raise ValueError(f"unknown node: {node_id}")
    node = state.nodes[node_id]
    if node.facility is None:
        raise ValueError(f"node {node_id} has no facility")
    return node, node.facility


def _require_facility_component(
    state: object,
    node_id: str,
    component_id: str,
) -> tuple[NetworkNode, Facility, FacilityComponent]:
    """Return a facility component, raising validation errors for missing pieces."""

    node, facility = _require_facility(state, node_id)
    if component_id not in facility.components:
        raise ValueError(f"unknown facility component: {component_id}")
    return node, facility, facility.components[component_id]


def _connections_referencing_component(facility: Facility, component_id: str) -> list[str]:
    """Return internal connection ids that would be orphaned by removing a component."""

    return sorted(
        connection.id
        for connection in facility.connections.values()
        if connection.source_component_id == component_id
        or connection.destination_component_id == component_id
    )


def _rate_after_component_removal(
    node: NetworkNode,
    facility: Facility,
    component: FacilityComponent,
) -> int | None:
    """Return the relevant effective node rate after removing one component."""

    remaining = [
        item
        for item in facility.components.values()
        if item.id != component.id and item.kind == component.kind
    ]
    if component.kind == FacilityComponentKind.LOADER:
        if remaining:
            return sum(max(0, item.rate) for item in remaining)
        return int(node.transfer_limit_per_tick)
    if component.kind == FacilityComponentKind.UNLOADER:
        if remaining:
            return sum(max(0, item.rate) for item in remaining)
        return int(node.transfer_limit_per_tick)
    return None


def _schedule_conflicts_after_component_removal(
    state: object,
    node: NetworkNode,
    component: FacilityComponent,
    future_rate: int | None,
) -> list[str]:
    """Return active schedule ids whose required rate would exceed a future cap."""

    if future_rate is None:
        return []
    if component.kind == FacilityComponentKind.LOADER:
        current_rate = int(node.effective_outbound_rate())
        relevant = lambda schedule: schedule.origin == node.id
    elif component.kind == FacilityComponentKind.UNLOADER:
        current_rate = int(node.effective_inbound_rate())
        relevant = lambda schedule: schedule.destination == node.id
    else:
        return []
    if future_rate >= current_rate:
        return []
    return sorted(
        schedule.id
        for schedule in state.schedules.values()
        if schedule.active
        and relevant(schedule)
        and schedule.units_per_departure > future_rate
    )


def _validate_demolish_facility_component(
    state: object,
    command: DemolishFacilityComponent | PreviewDemolishFacilityComponent,
) -> tuple[NetworkNode, Facility, FacilityComponent, int | None]:
    """Validate component demolition and return the component plus future rate."""

    node, facility, component = _require_facility_component(
        state,
        command.node_id,
        command.component_id,
    )
    referencing_connections = _connections_referencing_component(facility, component.id)
    buffered_cargo = any(
        units > 0
        for cargo_map in component.port_inventory.values()
        for units in cargo_map.values()
    )
    if referencing_connections and not buffered_cargo:
        raise ValueError(
            f"cannot demolish {component.kind.value} {component.id}; "
            "remove internal connections first: "
            + ", ".join(referencing_connections)
        )
    future_rate = _rate_after_component_removal(node, facility, component)
    conflicts = _schedule_conflicts_after_component_removal(state, node, component, future_rate)
    if conflicts:
        raise ValueError(
            f"cannot demolish {component.kind.value} {component.id}; active schedules exceed future rate "
            f"{future_rate}: "
            + ", ".join(conflicts)
        )
    return node, facility, component, future_rate


def _demolish_facility_component_payload(
    command: DemolishFacilityComponent | PreviewDemolishFacilityComponent,
) -> dict[str, object]:
    """Return a normalized component-demolition command payload."""

    return {
        "type": "DemolishFacilityComponent",
        "node_id": command.node_id,
        "component_id": command.component_id,
    }


def _demolish_cargo_plan(
    node: NetworkNode,
    component: FacilityComponent,
) -> tuple[dict[CargoType, int], dict[CargoType, int]]:
    """Plan cargo returned to node inventory versus dropped on demolition."""

    cargo_returned: dict[CargoType, int] = {}
    cargo_dropped: dict[CargoType, int] = {}
    remaining_capacity = max(0, int(node.storage_capacity) - node.total_inventory())
    for port_id in sorted(component.port_inventory):
        cargo_map = component.port_inventory[port_id]
        for cargo_type, units in sorted(cargo_map.items(), key=lambda item: item[0].value):
            if units <= 0:
                continue
            returned = min(int(units), remaining_capacity)
            dropped = max(0, int(units) - returned)
            if returned > 0:
                cargo_returned[cargo_type] = cargo_returned.get(cargo_type, 0) + returned
                remaining_capacity -= returned
            if dropped > 0:
                cargo_dropped[cargo_type] = cargo_dropped.get(cargo_type, 0) + dropped
    return cargo_returned, cargo_dropped


def _demolish_refund(component: FacilityComponent) -> float:
    """Return the fixed 50% component refund."""

    build_cost = component.build_cost if component.build_cost > 0 else facility_component_build_cost(component.kind)
    return round(build_cost * 0.5, 2)


def _connection_from_command(
    command: BuildInternalConnection | PreviewBuildInternalConnection,
) -> InternalConnection:
    """Build an InternalConnection value from a build-connection command."""

    return InternalConnection(
        id=command.connection_id,
        source_component_id=command.source_component_id,
        source_port_id=command.source_port_id,
        destination_component_id=command.destination_component_id,
        destination_port_id=command.destination_port_id,
        link_type=_resolve_transfer_link_kind(command.link_type),
    )


def _connection_payload(connection: InternalConnection, command_type: str = "BuildInternalConnection") -> dict[str, object]:
    """Return a normalized internal-connection command payload."""

    return {
        "type": command_type,
        "connection_id": connection.id,
        "source_component_id": connection.source_component_id,
        "source_port_id": connection.source_port_id,
        "destination_component_id": connection.destination_component_id,
        "destination_port_id": connection.destination_port_id,
        "link_type": _transfer_link_kind_value(connection.link_type),
        "transfer_profile": transfer_link_profile_payload(connection.link_type),
    }


def _validate_build_internal_connection(
    state: object,
    command: BuildInternalConnection | PreviewBuildInternalConnection,
) -> tuple[NetworkNode, Facility, InternalConnection]:
    """Validate one internal facility connection."""

    node, facility = _require_facility(state, command.node_id)
    connection = _connection_from_command(command)
    _validate_internal_connection(facility, connection)
    return node, facility, connection


def _validate_internal_connection(facility: Facility, connection: InternalConnection) -> None:
    """Validate one internal connection against a facility layout."""

    if not connection.id.strip():
        raise ValueError("connection id cannot be empty")
    if connection.id in facility.connections:
        raise ValueError(f"duplicate connection id: {connection.id}")
    if connection.source_component_id == connection.destination_component_id:
        raise ValueError("internal connection source and destination components must differ")
    if connection.source_component_id not in facility.components:
        raise ValueError(f"unknown source component: {connection.source_component_id}")
    if connection.destination_component_id not in facility.components:
        raise ValueError(f"unknown destination component: {connection.destination_component_id}")

    source_component = facility.components[connection.source_component_id]
    destination_component = facility.components[connection.destination_component_id]
    source_port = source_component.ports.get(connection.source_port_id)
    if source_port is None:
        raise ValueError(f"unknown source port: {connection.source_port_id}")
    destination_port = destination_component.ports.get(connection.destination_port_id)
    if destination_port is None:
        raise ValueError(f"unknown destination port: {connection.destination_port_id}")
    if source_port.direction != PortDirection.OUTPUT:
        raise ValueError("internal connection source port must be an output")
    if destination_port.direction != PortDirection.INPUT:
        raise ValueError("internal connection destination port must be an input")
    if (
        source_port.cargo_type is not None
        and destination_port.cargo_type is not None
        and source_port.cargo_type != destination_port.cargo_type
    ):
        raise ValueError("internal connection cargo types must match")
    cargo_type = infer_connection_cargo(source_component, source_port, destination_component, destination_port)
    if cargo_type is not None and not transfer_link_supports_cargo(connection.link_type, cargo_type):
        raise ValueError(f"{_transfer_link_kind_value(connection.link_type)} cannot move {cargo_type.value}")

    destination_endpoint = (connection.destination_component_id, connection.destination_port_id)
    for existing in facility.connections.values():
        if (existing.destination_component_id, existing.destination_port_id) == destination_endpoint:
            raise ValueError(f"destination port already connected: {connection.destination_port_id}")


def _validate_remove_internal_connection(
    state: object,
    command: RemoveInternalConnection | PreviewRemoveInternalConnection,
) -> tuple[NetworkNode, Facility, InternalConnection]:
    """Validate internal facility connection removal."""

    node, facility = _require_facility(state, command.node_id)
    if command.connection_id not in facility.connections:
        raise ValueError(f"unknown internal connection: {command.connection_id}")
    return node, facility, facility.connections[command.connection_id]


def _require_operational_area(state: object, area_id: str) -> OperationalAreaState:
    """Return a persisted operational area, creating migrated grids when needed."""

    from gaterail.operational import ensure_operational_areas

    ensure_operational_areas(state)
    area = state.operational_areas.get(area_id)
    if area is None:
        raise ValueError(f"unknown operational area: {area_id}")
    return area


def _local_area_payload(state: object, area: OperationalAreaState) -> dict[str, object]:
    """Return one local operational area command payload."""

    from gaterail.operational import operational_area_payload

    return operational_area_payload(state, area)


def _local_entity_payload(
    state: object,
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
) -> dict[str, object]:
    """Return one local operational entity command payload."""

    from gaterail.operational import operational_entity_payload

    return operational_entity_payload(state, area, entity)


def _slug_identifier(value: str) -> str:
    """Return a conservative id fragment for generated local commands."""

    slug = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "item"


def _local_signal_default_node_id(
    state: object,
    entity: OperationalPlacedEntity,
    link_id: str,
) -> str | None:
    """Choose the local track entry node when Godot only supplies a track entity."""

    if entity.input_ports:
        return entity.input_ports[0]
    link = state.links.get(link_id)
    return None if link is None else link.origin


def _local_signal_id(
    state: object,
    command: LocalValidateSignal | LocalPlaceSignal,
    link_id: str,
    node_id: str | None,
) -> str:
    """Return an explicit or generated signal id."""

    if command.signal_id.strip():
        return command.signal_id.strip()
    base = "%s_%s_%s_signal" % (
        _slug_identifier(link_id),
        _slug_identifier(node_id or "block"),
        command.kind.value,
    )
    signal_id = base
    index = 2
    while signal_id in state.track_signals:
        signal_id = f"{base}_{index}"
        index += 1
    return signal_id


def _local_signal_place_payload(
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
    signal: TrackSignal,
) -> dict[str, object]:
    """Return the local commit command for a validated signal preview."""

    return {
        "type": "local.place_signal",
        "operational_area_id": area.id,
        "track_entity_id": entity.id,
        "signal_id": signal.id,
        "kind": signal.kind.value,
        "node_id": signal.node_id,
        "active": signal.active,
    }


def _validate_local_signal(
    state: object,
    command: LocalValidateSignal | LocalPlaceSignal,
) -> tuple[dict[str, object] | None, OperationalAreaState | None, OperationalPlacedEntity | None, TrackSignal | None]:
    """Validate a local track-signal command and normalize it to TrackSignal."""

    try:
        area = _require_operational_area(state, command.operational_area_id)
    except ValueError as exc:
        return (
            _command_failure(
                command.type,
                command.operational_area_id,
                reason="unknown_operational_area",
                message=str(exc),
            ),
            None,
            None,
            None,
        )

    entity: OperationalPlacedEntity | None = None
    if command.track_entity_id.strip():
        entity = area.entities.get(command.track_entity_id.strip())
    elif command.link_id.strip():
        for candidate in area.entities.values():
            if candidate.link_id == command.link_id.strip():
                entity = candidate
                break
    if entity is None:
        target_id = command.track_entity_id.strip() or command.link_id.strip() or area.id
        return (
            _command_failure(
                command.type,
                target_id,
                reason="unknown_track_entity",
                message=f"unknown local track entity: {target_id}",
            ),
            area,
            None,
            None,
        )
    if entity.entity_type != OperationalEntityType.TRACK_SEGMENT or entity.link_id is None:
        return (
            _command_failure(
                command.type,
                entity.id,
                reason="not_track_entity",
                message=f"local entity {entity.id} is not a track segment",
            ),
            area,
            entity,
            None,
        )
    link_id = command.link_id.strip() or entity.link_id
    if link_id != entity.link_id:
        return (
            _command_failure(
                command.type,
                entity.id,
                reason="track_link_mismatch",
                message=f"local track {entity.id} backs {entity.link_id}, not {link_id}",
            ),
            area,
            entity,
            None,
        )

    node_id = command.node_id or _local_signal_default_node_id(state, entity, link_id)
    signal_id = _local_signal_id(state, command, link_id, node_id)
    if signal_id in state.track_signals:
        return (
            _command_failure(
                command.type,
                signal_id,
                reason="duplicate_track_signal_id",
                message=f"duplicate track signal id: {signal_id}",
            ),
            area,
            entity,
            None,
        )

    try:
        signal = _validate_track_signal(
            state,
            BuildTrackSignal(
                signal_id=signal_id,
                link_id=link_id,
                kind=command.kind,
                node_id=node_id,
                active=command.active,
            ),
        )
    except ValueError as exc:
        return (
            _command_failure(
                command.type,
                signal_id,
                reason="invalid_track_signal",
                message=str(exc),
            ),
            area,
            entity,
            None,
        )
    return None, area, entity, signal


def _local_switch_payloads(state: object) -> list[dict[str, object]]:
    """Return current local rail switch diagnostics."""

    from gaterail.local_rail import build_local_rail_diagnostics

    local_rail = build_local_rail_diagnostics(state)
    switches = local_rail.get("switches", [])
    if not isinstance(switches, list):
        return []
    return [dict(item) for item in switches if isinstance(item, dict)]


def _find_local_switch(
    state: object,
    command: LocalSetSwitchRoute,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Find the abstract local switch targeted by a route-control command."""

    requested_switch_id = command.switch_id.strip()
    requested_node_id = command.node_id.strip()
    if not requested_switch_id and requested_node_id:
        requested_switch_id = f"{command.operational_area_id}:{requested_node_id}:switch"
    if not requested_switch_id:
        return (
            _command_failure(
                command.type,
                command.operational_area_id,
                reason="missing_switch",
                message="local switch route command requires switch_id or node_id",
            ),
            None,
        )
    for switch in _local_switch_payloads(state):
        if str(switch.get("operational_area_id", "")) != command.operational_area_id:
            continue
        if str(switch.get("id", "")) == requested_switch_id:
            return None, switch
    return (
        _command_failure(
            command.type,
            requested_switch_id,
            reason="unknown_switch",
            message=f"unknown local switch: {requested_switch_id}",
        ),
        None,
    )


def _validate_local_switch_route(
    state: object,
    command: LocalSetSwitchRoute,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Validate a selected route for one local switch."""

    failure, switch = _find_local_switch(state, command)
    if failure is not None or switch is None:
        return failure, None
    link_ids = switch.get("link_ids", [])
    if not isinstance(link_ids, list) or command.selected_link_id not in [str(item) for item in link_ids]:
        return (
            _command_failure(
                command.type,
                str(switch.get("id", command.operational_area_id)),
                reason="invalid_switch_route",
                message=(
                    f"link {command.selected_link_id} is not a route option for "
                    f"local switch {switch.get('id', '')}"
                ),
            ),
            switch,
        )
    return None, switch


def _resolve_local_entity_type(raw: str) -> OperationalEntityType:
    """Parse local entity type aliases used by Godot and stdio clients."""

    aliases = {
        "mine": OperationalEntityType.EXTRACTOR,
        "extractor": OperationalEntityType.EXTRACTOR,
        "rail_track": OperationalEntityType.TRACK_SEGMENT,
        "track": OperationalEntityType.TRACK_SEGMENT,
        "track_segment": OperationalEntityType.TRACK_SEGMENT,
        "station": OperationalEntityType.STATION_PLATFORM,
        "station_platform": OperationalEntityType.STATION_PLATFORM,
        "loader": OperationalEntityType.LOADER,
        "unloader": OperationalEntityType.UNLOADER,
        "hopper": OperationalEntityType.HOPPER,
        "buffer": OperationalEntityType.HOPPER,
        "storage": OperationalEntityType.STORAGE,
        "warehouse": OperationalEntityType.STORAGE,
        "transfer_link": OperationalEntityType.TRANSFER_LINK,
        "conveyor": OperationalEntityType.TRANSFER_LINK,
        "refinery": OperationalEntityType.REFINERY,
        "factory": OperationalEntityType.FACTORY,
        "assembler": OperationalEntityType.FACTORY,
        "railgate_terminal": OperationalEntityType.RAILGATE_TERMINAL,
        "terminal": OperationalEntityType.RAILGATE_TERMINAL,
    }
    key = str(raw).strip().lower()
    if key in aliases:
        return aliases[key]
    try:
        return OperationalEntityType(key)
    except ValueError as exc:
        raise ValueError(f"unknown local entity type: {raw}") from exc


def _local_default_footprint(entity_type: OperationalEntityType) -> tuple[int, int]:
    """Return default local footprint for command placement."""

    if entity_type in {
        OperationalEntityType.EXTRACTOR,
        OperationalEntityType.STATION_PLATFORM,
        OperationalEntityType.REFINERY,
        OperationalEntityType.FACTORY,
        OperationalEntityType.RAILGATE_TERMINAL,
    }:
        return 2, 2
    return 1, 1


def _local_default_rate(entity_type: OperationalEntityType) -> int:
    """Return a conservative default build rate for local components."""

    if entity_type in {OperationalEntityType.LOADER, OperationalEntityType.UNLOADER}:
        return 20
    if entity_type in {OperationalEntityType.HOPPER, OperationalEntityType.STORAGE}:
        return 12
    if entity_type == OperationalEntityType.RAILGATE_TERMINAL:
        return 4
    return 0


def _local_visual_hint(entity_type: OperationalEntityType) -> str:
    """Return the legacy visual kind to preserve existing Godot/readout contracts."""

    return {
        OperationalEntityType.TRACK_SEGMENT: "rail_track",
        OperationalEntityType.STORAGE: "warehouse",
    }.get(entity_type, entity_type.value)


_VALID_LOCAL_PLATFORM_SIDES: frozenset[str] = frozenset({"north", "east", "south", "west"})


def _local_path_cells_payload(
    cells: tuple[tuple[int, int, int], ...],
    *,
    include_z: bool,
) -> list[dict[str, int]]:
    """Return JSON-safe path cells."""

    payload: list[dict[str, int]] = []
    for x, y, z in cells:
        cell = {"x": int(x), "y": int(y)}
        if include_z:
            cell["z"] = int(z)
        payload.append(cell)
    return payload


def _local_build_options() -> list[dict[str, object]]:
    """Return static local build options exposed to clients."""

    options: list[tuple[OperationalEntityType, str]] = [
        (OperationalEntityType.EXTRACTOR, "Mine / extractor"),
        (OperationalEntityType.TRACK_SEGMENT, "Track segment"),
        (OperationalEntityType.STATION_PLATFORM, "Station platform"),
        (OperationalEntityType.LOADER, "Loader"),
        (OperationalEntityType.UNLOADER, "Unloader"),
        (OperationalEntityType.HOPPER, "Hopper / buffer"),
        (OperationalEntityType.STORAGE, "Storage / warehouse"),
        (OperationalEntityType.TRANSFER_LINK, "Transfer link / conveyor"),
        (OperationalEntityType.REFINERY, "Refinery"),
        (OperationalEntityType.FACTORY, "Factory / assembler"),
        (OperationalEntityType.RAILGATE_TERMINAL, "Railgate terminal"),
    ]
    payload: list[dict[str, object]] = []
    for entity_type, label in options:
        width, height = _local_default_footprint(entity_type)
        component_kind = _local_component_kind(entity_type)
        payload.append(
            {
                "entity_type": entity_type.value,
                "label": label,
                "footprint": {"width": width, "height": height},
                "valid_rotations": [0, 90, 180, 270],
                "kind": _local_visual_hint(entity_type),
                "component_kind": None if component_kind is None else component_kind.value,
                "valid_platform_sides": ["north", "east", "south", "west"],
                "cash_cost": 0.0 if component_kind is None else facility_component_build_cost(component_kind),
                "cargo_cost": (
                    {}
                    if component_kind is None
                    else _plain_cargo_cost(facility_component_build_cargo(component_kind))
                ),
            }
        )
    return payload


def _local_component_kind(entity_type: OperationalEntityType) -> FacilityComponentKind | None:
    """Return the facility component kind backed by one local entity type."""

    return {
        OperationalEntityType.LOADER: FacilityComponentKind.LOADER,
        OperationalEntityType.UNLOADER: FacilityComponentKind.UNLOADER,
        OperationalEntityType.HOPPER: FacilityComponentKind.STORAGE_BAY,
        OperationalEntityType.STORAGE: FacilityComponentKind.WAREHOUSE_BAY,
        OperationalEntityType.REFINERY: FacilityComponentKind.REFINERY,
        OperationalEntityType.FACTORY: FacilityComponentKind.FABRICATOR,
        OperationalEntityType.RAILGATE_TERMINAL: FacilityComponentKind.GATE_INTERFACE,
        OperationalEntityType.STATION_PLATFORM: FacilityComponentKind.PLATFORM,
        OperationalEntityType.EXTRACTOR: FacilityComponentKind.EXTRACTOR_HEAD,
    }.get(entity_type)


def _local_node_kind(entity_type: OperationalEntityType) -> NodeKind:
    """Return a macro-safe node kind for standalone local placements."""

    if entity_type == OperationalEntityType.EXTRACTOR:
        return NodeKind.EXTRACTOR
    if entity_type == OperationalEntityType.RAILGATE_TERMINAL:
        return NodeKind.GATE_HUB
    if entity_type == OperationalEntityType.STORAGE:
        return NodeKind.WAREHOUSE
    if entity_type in {OperationalEntityType.REFINERY, OperationalEntityType.FACTORY}:
        return NodeKind.INDUSTRY
    return NodeKind.DEPOT


def _local_placement_entity_id(command: LocalValidatePlacement | LocalPlaceEntity, entity_type: OperationalEntityType) -> str:
    """Return a stable id for one local placement command."""

    if command.entity_id.strip():
        return command.entity_id.strip()
    if command.component_id:
        return command.component_id
    if command.link_id:
        return f"{command.link_id}:track" if entity_type == OperationalEntityType.TRACK_SEGMENT else command.link_id
    return f"{entity_type.value}_{command.x}_{command.y}"


def _local_component_id(command: LocalValidatePlacement | LocalPlaceEntity, entity_id: str) -> str:
    """Return component id used by component-backed local placements."""

    return command.component_id.strip() if command.component_id else entity_id


def _local_entity_for_command(
    state: object,
    area: OperationalAreaState,
    command: LocalValidatePlacement | LocalPlaceEntity,
    entity_type: OperationalEntityType,
    entity_id: str,
) -> OperationalPlacedEntity:
    """Build a prospective persisted entity from one local placement command."""

    width, height = _local_default_footprint(entity_type)
    if command.width > 0:
        width = command.width
    if command.height > 0:
        height = command.height
    owner_node_id = command.owner_node_id
    component_id: str | None = None
    link_id = command.link_id
    input_ports: tuple[str, ...] = ()
    output_ports: tuple[str, ...] = ()
    blocks_occupancy = entity_type != OperationalEntityType.TRANSFER_LINK

    component_kind = _local_component_kind(entity_type)
    if owner_node_id is not None and component_kind is not None:
        component_id = _local_component_id(command, entity_id)
        ports = facility_component_default_ports(component_kind, component_id)
        input_ports = tuple(port.id for port in ports if port.direction == PortDirection.INPUT)
        output_ports = tuple(port.id for port in ports if port.direction == PortDirection.OUTPUT)
    if entity_type == OperationalEntityType.TRACK_SEGMENT:
        link_id = command.link_id or entity_id
        input_ports = (command.origin_node_id,) if command.origin_node_id else ()
        output_ports = (command.destination_node_id,) if command.destination_node_id else ()

    return OperationalPlacedEntity(
        id=entity_id,
        entity_type=entity_type,
        world_id=area.world_id,
        x=int(command.x),
        y=int(command.y),
        rotation=int(command.rotation),
        width=width,
        height=height,
        path_cells=command.path_cells if entity_type == OperationalEntityType.TRACK_SEGMENT else (),
        platform_side=None if command.platform_side is None else command.platform_side.strip().lower(),
        adjacent_to_entity_id=command.adjacent_to_entity_id,
        adjacent_port_id=command.adjacent_port_id,
        owner_node_id=owner_node_id,
        component_id=component_id,
        link_id=link_id,
        input_ports=input_ports,
        output_ports=output_ports,
        visual_hint=_local_visual_hint(entity_type),
        blocks_occupancy=blocks_occupancy,
    )


def _local_cells_outside(area: OperationalAreaState, entity: OperationalPlacedEntity) -> bool:
    """Return whether an entity footprint extends beyond an area."""

    return any(
        x < 0 or y < 0 or x >= area.width or y >= area.height
        for x, y, _ in entity.occupied_cells()
    )


def _local_overlap(
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
    *,
    exclude_entity_id: str | None = None,
) -> list[dict[str, object]]:
    """Return occupied-cell conflicts for a prospective entity."""

    if not entity.blocks_occupancy:
        return []
    occupied = area.occupied_cells(exclude_entity_id=exclude_entity_id)
    conflicts: list[dict[str, object]] = []
    for x, y, z in entity.occupied_cells():
        blocker = occupied.get((x, y, z))
        if blocker is not None:
            conflicts.append({"x": x, "y": y, "z": z, "entity_id": blocker})
    return conflicts


def _local_adjacent_side(
    entity: OperationalPlacedEntity,
    anchor: OperationalPlacedEntity,
) -> str | None:
    """Return the side of ``anchor`` touched by ``entity`` cells, if any."""

    anchor_cells = set(anchor.occupied_cells())
    for x, y, z in entity.occupied_cells():
        for ax, ay, az in anchor_cells:
            if z != az:
                continue
            if x == ax - 1 and y == ay:
                return "west"
            if x == ax + 1 and y == ay:
                return "east"
            if y == ay - 1 and x == ax:
                return "north"
            if y == ay + 1 and x == ax:
                return "south"
    return None


def _local_entity_port_ids(entity: OperationalPlacedEntity) -> set[str]:
    """Return exposed local port ids for adjacency validation."""

    return set(entity.input_ports) | set(entity.output_ports) | set(entity.connection_ports)


def _validate_local_adjacency(
    command_type: str,
    entity: OperationalPlacedEntity,
    area: OperationalAreaState,
) -> dict[str, object] | None:
    """Validate optional port-adjacent placement hints."""

    if entity.platform_side is not None and entity.platform_side not in _VALID_LOCAL_PLATFORM_SIDES:
        return _local_validation_failure(
            command_type,
            entity.id,
            "invalid_platform_side",
            "platform_side must be one of north, east, south, or west",
        )
    if entity.adjacent_to_entity_id is None:
        return None
    anchor = area.entities.get(entity.adjacent_to_entity_id)
    if anchor is None:
        return _local_validation_failure(
            command_type,
            entity.id,
            "unknown_adjacent_entity",
            f"unknown adjacent local entity: {entity.adjacent_to_entity_id}",
        )
    if entity.adjacent_port_id is not None and entity.adjacent_port_id not in _local_entity_port_ids(anchor):
        return _local_validation_failure(
            command_type,
            entity.id,
            "unknown_adjacent_port",
            f"unknown adjacent port: {entity.adjacent_port_id}",
        )
    actual_side = _local_adjacent_side(entity, anchor)
    if actual_side is None:
        return _local_validation_failure(
            command_type,
            entity.id,
            "not_port_adjacent",
            f"local entity {entity.id} is not adjacent to {anchor.id}",
        )
    if entity.platform_side is None:
        entity.platform_side = actual_side
    elif entity.platform_side != actual_side:
        return _local_validation_failure(
            command_type,
            entity.id,
            "not_port_adjacent",
            f"local entity {entity.id} is on {actual_side}, not {entity.platform_side}",
        )
    return None


def _local_node_storage_like(node: NetworkNode) -> bool:
    """Return whether a node has local storage/buffer components for handling."""

    if node.facility is None:
        return False
    return any(
        component.kind
        in {
            FacilityComponentKind.STORAGE_BAY,
            FacilityComponentKind.WAREHOUSE_BAY,
            FacilityComponentKind.EXTRACTOR_HEAD,
            FacilityComponentKind.GATE_INTERFACE,
            FacilityComponentKind.REFINERY,
            FacilityComponentKind.FABRICATOR,
        }
        for component in node.facility.components.values()
    )


def _local_validation_failure(
    command_type: str,
    target_id: str,
    reason: str,
    message: str,
    **extra: object,
) -> dict[str, object]:
    """Return a structured local placement failure."""

    return _command_failure(command_type, target_id, reason=reason, message=message, **extra)


def _validate_local_placement(
    state: object,
    command: LocalValidatePlacement | LocalPlaceEntity,
) -> tuple[dict[str, object] | None, OperationalAreaState | None, OperationalPlacedEntity | None, float, dict[CargoType, int], object | None]:
    """Validate local placement and return backing command metadata."""

    try:
        area = _require_operational_area(state, command.operational_area_id)
        entity_type = _resolve_local_entity_type(command.entity_type)
    except ValueError as exc:
        target = command.entity_id or command.entity_type
        return _local_validation_failure(command.type, target, str(exc), str(exc)), None, None, 0.0, {}, None

    entity_id = _local_placement_entity_id(command, entity_type)
    if entity_id in area.entities:
        return (
            _local_validation_failure(
                command.type,
                entity_id,
                "duplicate_entity_id",
                f"duplicate local entity id: {entity_id}",
            ),
            area,
            None,
            0.0,
            {},
            None,
        )
    if int(command.rotation) % 90 != 0:
        return (
            _local_validation_failure(
                command.type,
                entity_id,
                "invalid_rotation",
                "local entity rotation must be one of 0, 90, 180, or 270",
            ),
            area,
            None,
            0.0,
            {},
            None,
        )

    entity = _local_entity_for_command(state, area, command, entity_type, entity_id)
    if _local_cells_outside(area, entity):
        return (
            _local_validation_failure(
                command.type,
                entity_id,
                "outside_grid",
                "local entity footprint is outside the operational grid",
            ),
            area,
            entity,
            0.0,
            {},
            None,
        )
    conflicts = _local_overlap(area, entity)
    if conflicts:
        return (
            _local_validation_failure(
                command.type,
                entity_id,
                "occupied_cells",
                "local entity overlaps occupied cells",
                occupied_cells=conflicts,
            ),
            area,
            entity,
            0.0,
            {},
            None,
            )
    adjacency_failure = _validate_local_adjacency(command.type, entity, area)
    if adjacency_failure is not None:
        return adjacency_failure, area, entity, 0.0, {}, None

    cost = 0.0
    cargo_cost: dict[CargoType, int] = {}
    backing_command: object | None = None

    if entity_type == OperationalEntityType.TRACK_SEGMENT:
        if not command.origin_node_id or not command.destination_node_id:
            return (
                _local_validation_failure(
                    command.type,
                    entity_id,
                    "missing_track_endpoints",
                    "track segment placement requires origin_node_id and destination_node_id",
                ),
                area,
                entity,
                0.0,
                {},
                None,
            )
        backing_command = BuildLink(
            link_id=command.link_id or entity_id,
            origin=command.origin_node_id,
            destination=command.destination_node_id,
            mode=LinkMode.RAIL,
            travel_ticks=1,
            capacity_per_tick=DEFAULT_RAIL_CAPACITY_PER_TICK,
        )
        try:
            _, _, _, _, cost, _ = _validate_build_link(state, backing_command)
        except ValueError as exc:
            return _local_validation_failure(command.type, entity_id, "invalid_track", str(exc)), area, entity, 0.0, {}, None
    elif entity.owner_node_id is not None:
        if entity.owner_node_id not in state.nodes:
            return (
                _local_validation_failure(
                    command.type,
                    entity_id,
                    "unknown_owner_node",
                    f"unknown owner node: {entity.owner_node_id}",
                ),
                area,
                entity,
                0.0,
                {},
                None,
            )
        node = state.nodes[entity.owner_node_id]
        if node.world_id != area.world_id:
            return (
                _local_validation_failure(
                    command.type,
                    entity_id,
                    "owner_node_wrong_area",
                    f"owner node {node.id} is not in operational area {area.id}",
                ),
                area,
                entity,
                0.0,
                {},
                None,
            )
        component_kind = _local_component_kind(entity_type)
        if component_kind is None:
            return (
                _local_validation_failure(
                    command.type,
                    entity_id,
                    "unsupported_owner_placement",
                    f"{entity_type.value} cannot be placed on an existing owner node",
                ),
                area,
                entity,
                0.0,
                {},
                None,
            )
        if entity_type in {OperationalEntityType.LOADER, OperationalEntityType.UNLOADER} and not _local_node_storage_like(node):
            return (
                _local_validation_failure(
                    command.type,
                    entity_id,
                    "missing_storage_side",
                    f"{entity_type.value} requires a storage/source side on {node.id}",
                ),
                area,
                entity,
                0.0,
                {},
                None,
            )
        backing_command = BuildFacilityComponent(
            component_id=entity.component_id or entity_id,
            node_id=node.id,
            kind=component_kind,
            capacity=command.capacity,
            rate=command.rate if command.rate > 0 else _local_default_rate(entity_type),
            power_required=command.power_required,
            power_provided=command.power_provided,
            inputs=command.inputs,
            outputs=command.outputs,
            construction_cargo=command.construction_cargo,
        )
        try:
            _, cost, cargo_cost, _ = _validate_facility_component(state, backing_command)
        except ValueError as exc:
            return _local_validation_failure(command.type, entity_id, "invalid_component", str(exc)), area, entity, 0.0, {}, None
    else:
        node_kind = _local_node_kind(entity_type)
        backing_command = BuildNode(
            node_id=entity_id,
            world_id=area.world_id,
            kind=node_kind,
            name=command.name or entity_id.replace("_", " ").title(),
            layout_x=float((entity.x - area.width // 2) * area.cell_size),
            layout_y=float((entity.y - area.height // 3) * area.cell_size),
        )
        try:
            cost, _, _, _ = _validate_build_node(state, backing_command)
        except ValueError as exc:
            return _local_validation_failure(command.type, entity_id, "invalid_node", str(exc)), area, entity, 0.0, {}, None

    if not _cash_available(state, cost):
        return (
            _local_validation_failure(
                command.type,
                entity_id,
                "insufficient_cash",
                _insufficient_cash_message(state, entity_type.value, cost),
                cost=cost,
                cargo_cost=_plain_cargo_cost(cargo_cost),
            ),
            area,
            entity,
            cost,
            cargo_cost,
            backing_command,
        )
    return None, area, entity, cost, cargo_cost, backing_command


def _place_local_entity(
    state: object,
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
    cost: float,
    cargo_cost: dict[CargoType, int],
    backing_command: object | None,
) -> None:
    """Commit a validated local entity and its backing macro/facility state."""

    if isinstance(backing_command, BuildFacilityComponent):
        component, _, _, connections = _validate_facility_component(state, backing_command)
        node = state.nodes[backing_command.node_id]
        if node.facility is None:
            node.facility = Facility()
        _consume_construction_cargo(state, node, cargo_cost)
        node.facility.components[component.id] = component
        for connection in connections:
            node.facility.connections[connection.id] = connection
        state.finance.record_cost(cost)
    elif isinstance(backing_command, BuildLink):
        travel_ticks, capacity_per_tick, power_required, power_source_world_id, _, build_time = _validate_build_link(
            state,
            backing_command,
        )
        link = NetworkLink(
            id=backing_command.link_id,
            origin=backing_command.origin,
            destination=backing_command.destination,
            mode=backing_command.mode,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
            bidirectional=backing_command.bidirectional,
            build_cost=cost,
            build_time=build_time,
            alignment=backing_command.alignment,
        )
        state.add_link(link)
        state.finance.record_cost(cost)
        entity.link_id = link.id
    elif isinstance(backing_command, BuildNode):
        _, storage, transfer, _ = _validate_build_node(state, backing_command)
        node = NetworkNode(
            id=backing_command.node_id,
            name=backing_command.name,
            world_id=backing_command.world_id,
            kind=backing_command.kind,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            layout_x=backing_command.layout_x,
            layout_y=backing_command.layout_y,
        )
        state.add_node(node)
        state.finance.record_cost(cost)
        entity.owner_node_id = node.id
    area.entities[entity.id] = entity


def _local_normalized_place_command(
    command: LocalValidatePlacement,
    area: OperationalAreaState,
    entity: OperationalPlacedEntity,
) -> dict[str, object]:
    """Return the commit command for a validated local placement."""

    normalized: dict[str, object] = {
        "type": "local.place_entity",
        "operational_area_id": area.id,
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "x": entity.x,
        "y": entity.y,
        "rotation": entity.rotation,
        "width": entity.width,
        "height": entity.height,
    }
    optional_fields: dict[str, object | None] = {
        "owner_node_id": entity.owner_node_id,
        "component_id": entity.component_id,
        "link_id": entity.link_id,
        "origin_node_id": command.origin_node_id,
        "destination_node_id": command.destination_node_id,
        "platform_side": entity.platform_side,
        "adjacent_to_entity_id": entity.adjacent_to_entity_id,
        "adjacent_port_id": entity.adjacent_port_id,
    }
    for key, value in optional_fields.items():
        if value is not None:
            normalized[key] = value
    if command.rate > 0:
        normalized["rate"] = command.rate
    if command.capacity > 0:
        normalized["capacity"] = command.capacity
    if command.power_required > 0:
        normalized["power_required"] = command.power_required
    if command.power_provided > 0:
        normalized["power_provided"] = command.power_provided
    if command.construction_cargo:
        normalized["construction_cargo"] = _plain_cargo_cost(command.construction_cargo)
    if command.inputs:
        normalized["inputs"] = _plain_cargo_cost(command.inputs)
    if command.outputs:
        normalized["outputs"] = _plain_cargo_cost(command.outputs)
    if entity.path_cells:
        normalized["path_cells"] = _local_path_cells_payload(entity.path_cells, include_z=False)
    return normalized


def apply_player_command(state: object, command: PlayerCommand) -> dict[str, object]:
    """Apply one player command to a GameState-like object."""

    if isinstance(command, LocalGetOperationalArea):
        try:
            area = _require_operational_area(state, command.operational_area_id)
        except ValueError as exc:
            return _command_failure(
                command.type,
                command.operational_area_id,
                reason="unknown_operational_area",
                message=str(exc),
            )
        return command_result(
            command.type,
            ok=True,
            target_id=area.id,
            message=f"loaded operational area {area.id}",
            operational_area=_local_area_payload(state, area),
        )

    if isinstance(command, LocalListBuildOptions):
        try:
            area = _require_operational_area(state, command.operational_area_id)
        except ValueError as exc:
            return _command_failure(
                command.type,
                command.operational_area_id,
                reason="unknown_operational_area",
                message=str(exc),
            )
        return command_result(
            command.type,
            ok=True,
            target_id=area.id,
            message=f"listed local build options for {area.id}",
            build_options=_local_build_options(),
            transfer_link_profiles=transfer_link_profiles_payload(),
            construction_inventory=_plain_cargo_cost(getattr(state, "construction_inventory", {})),
            cash=round(float(state.finance.cash), 2),
        )

    if isinstance(command, LocalValidatePlacement):
        failure, area, entity, cost, cargo_cost, backing_command = _validate_local_placement(state, command)
        if failure is not None:
            return failure
        assert area is not None and entity is not None
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"valid local placement for {entity.entity_type.value} {entity.id}",
            entity=_local_entity_payload(state, area, entity),
            cost=cost,
            cargo_cost=_plain_cargo_cost(cargo_cost),
            normalized_command=_local_normalized_place_command(command, area, entity),
        )

    if isinstance(command, LocalPlaceEntity):
        failure, area, entity, cost, cargo_cost, backing_command = _validate_local_placement(state, command)
        if failure is not None:
            return failure
        assert area is not None and entity is not None
        _place_local_entity(state, area, entity, cost, cargo_cost, backing_command)
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"placed {entity.entity_type.value} {entity.id}",
            entity=_local_entity_payload(state, area, entity),
            cost=cost,
            cargo_cost=_plain_cargo_cost(cargo_cost),
            operational_area=_local_area_payload(state, area),
        )

    if isinstance(command, LocalRotateEntity):
        try:
            area = _require_operational_area(state, command.operational_area_id)
        except ValueError as exc:
            return _command_failure(command.type, command.entity_id, reason="unknown_operational_area", message=str(exc))
        entity = area.entities.get(command.entity_id)
        if entity is None:
            return _command_failure(
                command.type,
                command.entity_id,
                reason="unknown_entity",
                message=f"unknown local entity: {command.entity_id}",
            )
        if int(command.rotation) % 90 != 0:
            return _command_failure(
                command.type,
                command.entity_id,
                reason="invalid_rotation",
                message="local entity rotation must be one of 0, 90, 180, or 270",
            )
        original_rotation = entity.rotation
        entity.rotation = int(command.rotation) % 360
        if _local_cells_outside(area, entity):
            entity.rotation = original_rotation
            return _command_failure(
                command.type,
                command.entity_id,
                reason="outside_grid",
                message="rotated local entity footprint is outside the operational grid",
            )
        conflicts = _local_overlap(area, entity, exclude_entity_id=entity.id)
        if conflicts:
            entity.rotation = original_rotation
            return _command_failure(
                command.type,
                command.entity_id,
                reason="occupied_cells",
                message="rotated local entity overlaps occupied cells",
                occupied_cells=conflicts,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"rotated local entity {entity.id} to {entity.rotation}",
            entity=_local_entity_payload(state, area, entity),
            operational_area=_local_area_payload(state, area),
        )

    if isinstance(command, LocalInspectEntity):
        try:
            area = _require_operational_area(state, command.operational_area_id)
        except ValueError as exc:
            return _command_failure(command.type, command.entity_id, reason="unknown_operational_area", message=str(exc))
        entity = area.entities.get(command.entity_id)
        if entity is None:
            return _command_failure(
                command.type,
                command.entity_id,
                reason="unknown_entity",
                message=f"unknown local entity: {command.entity_id}",
            )
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"inspected local entity {entity.id}",
            entity=_local_entity_payload(state, area, entity),
        )

    if isinstance(command, LocalConnectEntities):
        try:
            area = _require_operational_area(state, command.operational_area_id)
            node, facility = _require_facility(state, command.owner_node_id)
            connection_id = command.connection_id.strip() or (
                f"wire_{command.source_component_id}_{command.destination_component_id}"
            )
            connection_command = BuildInternalConnection(
                node_id=command.owner_node_id,
                connection_id=connection_id,
                source_component_id=command.source_component_id,
                source_port_id=command.source_port_id,
                destination_component_id=command.destination_component_id,
                destination_port_id=command.destination_port_id,
                link_type=command.link_type,
            )
            _, _, connection = _validate_build_internal_connection(state, connection_command)
        except ValueError as exc:
            return _command_failure(
                command.type,
                command.connection_id or command.entity_id or command.owner_node_id,
                reason="invalid_connection",
                message=str(exc),
            )
        entity_id = command.entity_id.strip() or f"{command.owner_node_id}:{connection.id}"
        if entity_id in area.entities:
            return _command_failure(
                command.type,
                entity_id,
                reason="duplicate_entity_id",
                message=f"duplicate local entity id: {entity_id}",
            )
        sx = sy = dx = dy = None
        for existing in area.entities.values():
            if existing.owner_node_id != command.owner_node_id:
                continue
            if existing.component_id == command.source_component_id:
                sx, sy = existing.x, existing.y
            if existing.component_id == command.destination_component_id:
                dx, dy = existing.x, existing.y
        if command.x is not None and command.y is not None:
            x, y = int(command.x), int(command.y)
        elif sx is not None and sy is not None and dx is not None and dy is not None:
            x, y = int(round((sx + dx) / 2.0)), int(round((sy + dy) / 2.0))
        else:
            owner_entity = area.entities.get(f"{command.owner_node_id}:station")
            x = owner_entity.x if owner_entity is not None else area.width // 2
            y = owner_entity.y if owner_entity is not None else area.height // 2
        entity = OperationalPlacedEntity(
            id=entity_id,
            entity_type=OperationalEntityType.TRANSFER_LINK,
            world_id=area.world_id,
            x=x,
            y=y,
            rotation=0,
            width=1,
            height=1,
            owner_node_id=command.owner_node_id,
            link_id=connection.id,
            link_type=_transfer_link_kind_value(connection.link_type),
            input_ports=(f"{connection.destination_component_id}.{connection.destination_port_id}",),
            output_ports=(f"{connection.source_component_id}.{connection.source_port_id}",),
            visual_hint="transfer_link",
            blocks_occupancy=False,
        )
        if _local_cells_outside(area, entity):
            return _command_failure(
                command.type,
                entity_id,
                reason="outside_grid",
                message="transfer link placement is outside the operational grid",
            )
        facility.connections[connection.id] = connection
        area.entities[entity.id] = entity
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"connected local entities with {connection.link_type.value} {connection.id}",
            node_id=command.owner_node_id,
            **_connection_payload(connection),
            entity=_local_entity_payload(state, area, entity),
            operational_area=_local_area_payload(state, area),
        )

    if isinstance(command, LocalValidateSignal):
        failure, area, entity, signal = _validate_local_signal(state, command)
        if failure is not None:
            return failure
        assert area is not None and entity is not None and signal is not None
        return command_result(
            command.type,
            ok=True,
            target_id=signal.id,
            message=f"valid local {signal.kind.value} signal preview on {signal.link_id}",
            entity=_local_entity_payload(state, area, entity),
            signal=_track_signal_payload(signal),
            track_signal_command=_track_signal_payload(signal),
            normalized_command=_local_signal_place_payload(area, entity, signal),
            link_id=signal.link_id,
            node_id=signal.node_id,
            kind=signal.kind.value,
            active=signal.active,
            block=signal.link_id,
        )

    if isinstance(command, LocalPlaceSignal):
        failure, area, entity, signal = _validate_local_signal(state, command)
        if failure is not None:
            return failure
        assert area is not None and entity is not None and signal is not None
        state.add_track_signal(signal)
        return command_result(
            command.type,
            ok=True,
            target_id=signal.id,
            message=f"placed local {signal.kind.value} signal {signal.id} on {signal.link_id}",
            entity=_local_entity_payload(state, area, entity),
            signal=_track_signal_payload(signal),
            link_id=signal.link_id,
            node_id=signal.node_id,
            kind=signal.kind.value,
            active=signal.active,
            block=signal.link_id,
        )

    if isinstance(command, LocalSetSwitchRoute):
        failure, switch = _validate_local_switch_route(state, command)
        if failure is not None:
            return failure
        assert switch is not None
        switch_id = str(switch["id"])
        state.local_switch_routes[switch_id] = command.selected_link_id
        updated_switch = next(
            item
            for item in _local_switch_payloads(state)
            if str(item.get("id", "")) == switch_id
        )
        return command_result(
            command.type,
            ok=True,
            target_id=switch_id,
            message=f"selected local switch route {command.selected_link_id}",
            switch=updated_switch,
            selected_link_id=command.selected_link_id,
        )

    if isinstance(command, LocalDeleteEntity):
        try:
            area = _require_operational_area(state, command.operational_area_id)
        except ValueError as exc:
            return _command_failure(command.type, command.entity_id, reason="unknown_operational_area", message=str(exc))
        entity = area.entities.get(command.entity_id)
        if entity is None:
            return _command_failure(
                command.type,
                command.entity_id,
                reason="unknown_entity",
                message=f"unknown local entity: {command.entity_id}",
            )
        extra: dict[str, object] = {}
        if entity.component_id is not None and entity.owner_node_id is not None:
            try:
                node, facility, component, future_rate = _validate_demolish_facility_component(
                    state,
                    DemolishFacilityComponent(node_id=entity.owner_node_id, component_id=entity.component_id),
                )
            except ValueError as exc:
                return _command_failure(command.type, entity.id, reason="delete_blocked", message=str(exc))
            refund = _demolish_refund(component)
            cargo_returned, cargo_dropped = _demolish_cargo_plan(node, component)
            connections_removed = _connections_referencing_component(facility, component.id)
            for cargo_type, units in cargo_returned.items():
                node.add_inventory(cargo_type, units)
            for connection_id in connections_removed:
                facility.connections.pop(connection_id, None)
                for other_id, other in list(area.entities.items()):
                    if other.owner_node_id == entity.owner_node_id and other.link_id == connection_id:
                        area.entities.pop(other_id, None)
            del facility.components[component.id]
            state.finance.cash += refund
            extra = {
                "refund": refund,
                "future_rate": future_rate,
                "cargo_returned": _plain_cargo_cost(cargo_returned),
                "cargo_dropped": _plain_cargo_cost(cargo_dropped),
                "connections_removed": connections_removed,
            }
        elif entity.entity_type == OperationalEntityType.TRACK_SEGMENT and entity.link_id is not None:
            for train in state.trains.values():
                if entity.link_id in train.route_link_ids:
                    return _command_failure(
                        command.type,
                        entity.id,
                        reason="delete_blocked",
                        message=f"cannot delete track in active train route: {entity.link_id}",
                    )
            state.links.pop(entity.link_id, None)
        elif entity.entity_type == OperationalEntityType.TRANSFER_LINK and entity.owner_node_id is not None and entity.link_id is not None:
            node = state.nodes.get(entity.owner_node_id)
            if node is not None and node.facility is not None:
                node.facility.connections.pop(entity.link_id, None)
        elif entity.owner_node_id is not None:
            return _command_failure(
                command.type,
                entity.id,
                reason="delete_node_not_supported",
                message="local node deletion is not supported by this command",
            )
        area.entities.pop(entity.id, None)
        return command_result(
            command.type,
            ok=True,
            target_id=entity.id,
            message=f"deleted local entity {entity.id}",
            operational_area=_local_area_payload(state, area),
            **extra,
        )

    if isinstance(command, SetScheduleEnabled):
        schedule = state.schedules.get(command.schedule_id)
        if schedule is None:
            raise ValueError(f"unknown schedule: {command.schedule_id}")
        schedule.active = command.enabled
        state_label = "enabled" if command.enabled else "disabled"
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"schedule {command.schedule_id} {state_label}",
        )

    if isinstance(command, DispatchOrder):
        order = FreightOrder(
            id=command.order_id,
            train_id=command.train_id,
            origin=command.origin,
            destination=command.destination,
            cargo_type=command.cargo_type,
            requested_units=command.requested_units,
            priority=command.priority,
            train_stops=command.train_stops,
        )
        state.add_order(order)
        return command_result(
            command.type,
            ok=True,
            target_id=command.order_id,
            message=f"order {command.order_id} queued",
        )

    if isinstance(command, CancelOrder):
        order = state.orders.get(command.order_id)
        if order is None:
            raise ValueError(f"unknown order: {command.order_id}")
        if not order.active:
            return command_result(
                command.type,
                ok=True,
                target_id=command.order_id,
                message=f"order {command.order_id} already inactive",
            )
        for train in state.trains.values():
            if train.order_id == command.order_id:
                raise ValueError(f"cannot cancel in-flight order: {command.order_id}")
        order.active = False
        return command_result(
            command.type,
            ok=True,
            target_id=command.order_id,
            message=f"order {command.order_id} cancelled",
        )

    if isinstance(command, PreviewSurveySpaceSite):
        error, fields = _survey_site_payload(state, command)
        if error is not None:
            return error
        return command_result(
            command.type,
            ok=True,
            target_id=command.site_id,
            message=f"valid survey preview for site {command.site_id}",
            resource_id=fields["resource_id"],
            travel_ticks=fields["travel_ticks"],
            base_yield=fields["base_yield"],
            discovered=fields["discovered"],
            site_cargo_type=fields["site_cargo_type"],
            normalized_command=fields["normalized_command"],
        )

    if isinstance(command, SurveySpaceSite):
        error, fields = _survey_site_payload(state, command)
        if error is not None:
            return error
        site = fields["site"]
        already_discovered = bool(site.discovered)
        site.discovered = True
        return command_result(
            command.type,
            ok=True,
            target_id=command.site_id,
            message=(
                f"site {command.site_id} already surveyed"
                if already_discovered
                else f"surveyed site {command.site_id}"
            ),
            resource_id=fields["resource_id"],
            travel_ticks=fields["travel_ticks"],
            base_yield=fields["base_yield"],
            discovered=True,
            site_cargo_type=fields["site_cargo_type"],
        )

    if isinstance(command, PreviewDispatchMiningMission):
        error, fields = _validate_mining_mission(state, command)
        if error is not None:
            return error
        return command_result(
            command.type,
            ok=True,
            target_id=command.mission_id,
            message=f"valid mission preview for site {command.site_id}",
            travel_ticks=fields["travel_ticks"],
            expected_yield=fields["expected_yield"],
            fuel_required=fields["fuel_required"],
            fuel_available=fields["fuel_available"],
            power_required=fields["power_required"],
            power_available=fields["power_available"],
            power_shortfall_if_dispatched=fields["power_shortfall_if_dispatched"],
            return_capacity_estimate=fields["return_capacity_estimate"],
            site_cargo_type=fields["site_cargo_type"],
            site_resource_id=fields["site_resource_id"],
            haul_bucket=fields["haul_bucket"],
            haul_label=fields["haul_label"],
            normalized_command=fields["normalized_command"],
        )

    if isinstance(command, DispatchMiningMission):
        error, fields = _validate_mining_mission(state, command)
        if error is not None:
            return error
        launch_node = fields["launch_node"]
        launch_world = fields["launch_world"]
        fuel_input = fields["fuel_input"]
        power_input = fields["power_input"]
        site = fields["site"]
        launch_node.remove_inventory(CargoType.FUEL, fuel_input)
        launch_world.power_used += power_input
        mission = MiningMission(
            id=command.mission_id,
            site_id=command.site_id,
            launch_node_id=command.launch_node_id,
            return_node_id=command.return_node_id,
            status=MiningMissionStatus.EN_ROUTE,
            ticks_remaining=fields["travel_ticks"],
            fuel_input=fuel_input,
            power_input=power_input,
            expected_yield=site.base_yield,
            reserved_power=power_input,
            fuel_consumed=fuel_input,
        )
        state.add_mining_mission(mission)
        return command_result(
            command.type,
            ok=True,
            target_id=command.mission_id,
            message=f"mission {command.mission_id} dispatched",
            travel_ticks=fields["travel_ticks"],
            expected_yield=site.base_yield,
            reserved_power=power_input,
            fuel_consumed=fuel_input,
        )

    if isinstance(command, PreviewBuildOutpost):
        outpost_id = command.outpost_id.strip() or _next_outpost_id(state)
        try:
            resolved_id, outpost_kind, layout, cost, cargo_required = _validate_outpost_build(state, command)
        except ValueError as exc:
            reason = str(exc)
            if reason.startswith("unknown outpost kind: "):
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="unknown_outpost_kind",
                    message=reason,
                )
            if reason == "missing_layout":
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="missing_layout",
                    message="outpost layout requires x and y",
                )
            if reason.startswith("world_not_found:"):
                world_id = reason.split(":", 1)[1]
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="world_not_found",
                    message=f"unknown world: {world_id}",
                )
            if reason.startswith("duplicate_outpost_id:"):
                duplicate_id = reason.split(":", 1)[1]
                return _command_failure(
                    command.type,
                    duplicate_id,
                    reason="duplicate_outpost_id",
                    message=f"duplicate outpost id: {duplicate_id}",
                )
            return _command_failure(
                command.type,
                outpost_id,
                reason="invalid_outpost_command",
                message=reason,
            )
        normalized_command = _outpost_command_payload(resolved_id, command, layout=layout)
        if not _cash_available(state, cost):
            return _command_failure(
                command.type,
                resolved_id,
                reason="insufficient_cash",
                message=_insufficient_cash_message(state, outpost_kind.value, cost),
                cost=cost,
                cargo_required=_plain_cargo_cost(cargo_required),
                duration_estimate_ticks=outpost_duration_estimate_ticks(outpost_kind),
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=resolved_id,
            message=f"valid {outpost_kind.value} preview for {cost:.0f}",
            cost=cost,
            cargo_required=_plain_cargo_cost(cargo_required),
            duration_estimate_ticks=outpost_duration_estimate_ticks(outpost_kind),
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildOutpost):
        outpost_id = command.outpost_id.strip() or _next_outpost_id(state)
        try:
            resolved_id, outpost_kind, _, cost, cargo_required = _validate_outpost_build(state, command)
        except ValueError as exc:
            reason = str(exc)
            if reason.startswith("unknown outpost kind: "):
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="unknown_outpost_kind",
                    message=reason,
                )
            if reason == "missing_layout":
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="missing_layout",
                    message="outpost layout requires x and y",
                )
            if reason.startswith("world_not_found:"):
                world_id = reason.split(":", 1)[1]
                return _command_failure(
                    command.type,
                    outpost_id,
                    reason="world_not_found",
                    message=f"unknown world: {world_id}",
                )
            if reason.startswith("duplicate_outpost_id:"):
                duplicate_id = reason.split(":", 1)[1]
                return _command_failure(
                    command.type,
                    duplicate_id,
                    reason="duplicate_outpost_id",
                    message=f"duplicate outpost id: {duplicate_id}",
                )
            return _command_failure(
                command.type,
                outpost_id,
                reason="invalid_outpost_command",
                message=reason,
            )
        if not _cash_available(state, cost):
            return _command_failure(
                command.type,
                resolved_id,
                reason="insufficient_cash",
                message=_insufficient_cash_message(state, outpost_kind.value, cost),
                cost=cost,
                cargo_required=_plain_cargo_cost(cargo_required),
                duration_estimate_ticks=outpost_duration_estimate_ticks(outpost_kind),
            )
        node = NetworkNode(
            id=resolved_id,
            name=f"{outpost_kind.value.replace('_', ' ').title()} {resolved_id}",
            world_id=command.world_id,
            kind=NodeKind.OUTPOST,
            storage_capacity=node_default_storage(NodeKind.OUTPOST),
            transfer_limit_per_tick=node_default_transfer(NodeKind.OUTPOST),
            layout_x=command.layout_x,
            layout_y=command.layout_y,
            outpost_kind=outpost_kind,
        )
        state.add_node(node)
        state.finance.record_cost(cost)
        project = ConstructionProject(
            id=f"proj_{resolved_id}",
            target_node_id=resolved_id,
            required_cargo=cargo_required,
            status=ConstructionStatus.PENDING,
            cash_cost=cost,
        )
        state.add_construction_project(project)
        return command_result(
            command.type,
            ok=True,
            target_id=resolved_id,
            message=f"staged {outpost_kind.value} {resolved_id}",
            cost=cost,
            cargo_required=_plain_cargo_cost(cargo_required),
            duration_estimate_ticks=outpost_duration_estimate_ticks(outpost_kind),
        )

    if isinstance(command, PreviewCancelOutpost):
        node = state.nodes.get(command.outpost_id)
        if node is None or node.outpost_kind is None:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="unknown_outpost",
                message=f"unknown outpost: {command.outpost_id}",
            )
        project = _outpost_project_for_node(state, node)
        if project is None or project.status == ConstructionStatus.COMPLETED:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="outpost_not_under_construction",
                message=f"outpost {command.outpost_id} is not under construction",
            )
        refund_node = _refund_node_for_outpost(state, node)
        if refund_node is None:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="no_refund_node",
                message=f"no refund node on world {node.world_id}",
            )
        refund_cash = round(project.cash_cost * 0.5, 2)
        refund_cargo, refund_dropped = _project_outpost_refund(project, refund_node)
        return command_result(
            command.type,
            ok=True,
            target_id=command.outpost_id,
            message=f"valid cancellation preview for {command.outpost_id}",
            refund_cash=refund_cash,
            refund_cargo=_plain_cargo_cost(refund_cargo),
            refund_dropped=_plain_cargo_cost(refund_dropped),
            refund_node_id=refund_node.id,
            normalized_command={"type": "CancelOutpost", "outpost_id": command.outpost_id},
        )

    if isinstance(command, CancelOutpost):
        node = state.nodes.get(command.outpost_id)
        if node is None or node.outpost_kind is None:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="unknown_outpost",
                message=f"unknown outpost: {command.outpost_id}",
            )
        project = _outpost_project_for_node(state, node)
        if project is None or project.status == ConstructionStatus.COMPLETED:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="outpost_not_under_construction",
                message=f"outpost {command.outpost_id} is not under construction",
            )
        refund_node = _refund_node_for_outpost(state, node)
        if refund_node is None:
            return _command_failure(
                command.type,
                command.outpost_id,
                reason="no_refund_node",
                message=f"no refund node on world {node.world_id}",
            )
        refund_cash = round(project.cash_cost * 0.5, 2)
        planned_refund = _planned_outpost_refund(project)
        refund_cargo: dict[CargoType, int] = {}
        refund_dropped: dict[CargoType, int] = {}
        for cargo_type in sorted(planned_refund, key=lambda c: c.value):
            wanted = planned_refund[cargo_type]
            accepted = refund_node.add_inventory(cargo_type, wanted)
            if accepted > 0:
                refund_cargo[cargo_type] = accepted
            if accepted < wanted:
                refund_dropped[cargo_type] = wanted - accepted
        state.finance.cash += refund_cash
        state.construction_projects.pop(project.id, None)
        state.nodes.pop(node.id, None)
        return command_result(
            command.type,
            ok=True,
            target_id=command.outpost_id,
            message=f"cancelled outpost {command.outpost_id}",
            refund_cash=refund_cash,
            refund_cargo=_plain_cargo_cost(refund_cargo),
            refund_dropped=_plain_cargo_cost(refund_dropped),
            refund_node_id=refund_node.id,
        )

    if isinstance(command, PreviewBuildNode):
        try:
            cost, storage, transfer, layout = _validate_build_node(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.node_id, exc)
        normalized_command = _node_build_payload(command, storage=storage, transfer=transfer, layout=layout)
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, command.kind.value, cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.node_id,
                message=reason,
                reason=reason,
                cost=cost,
                build_time=0,
                storage_capacity=storage,
                transfer_limit_per_tick=transfer,
                layout=layout,
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=f"valid {command.kind.value} preview for {cost:.0f}",
            cost=cost,
            build_time=0,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            cargo_required=_plain_cargo_cost(node_build_cargo(command.kind)),
            layout=layout,
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildNode):
        cost, storage, transfer, layout = _validate_build_node(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, command.kind.value, cost))
        node = NetworkNode(
            id=command.node_id,
            name=command.name,
            world_id=command.world_id,
            kind=command.kind,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            layout_x=command.layout_x,
            layout_y=command.layout_y,
        )
        state.add_node(node)
        state.finance.record_cost(cost)
        
        required_cargo = node_build_cargo(command.kind)
        if required_cargo:
            project = ConstructionProject(
                id=f"proj_{command.node_id}",
                target_node_id=command.node_id,
                required_cargo=required_cargo,
                cash_cost=cost,
            )
            state.add_construction_project(project)
            message = f"started {command.kind.value} {command.node_id} project for {cost:.0f}"
        else:
            message = f"built {command.kind.value} {command.node_id} for {cost:.0f}"

        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=message,
            cost=cost,
            build_time=0,
            storage_capacity=storage,
            transfer_limit_per_tick=transfer,
            cargo_required=_plain_cargo_cost(required_cargo),
            layout=layout,
        )

    if isinstance(command, PreviewBuildLink):
        try:
            (
                travel_ticks,
                capacity_per_tick,
                power_required,
                power_source_world_id,
                cost,
                build_time,
            ) = _validate_build_link(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.link_id, exc)
        normalized_command = _link_build_payload(
            command,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        gate_context = _gate_preview_payload(
            state,
            command,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, f"{command.mode.value} link", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.link_id,
                message=reason,
                reason=reason,
                cost=cost,
                build_time=build_time,
                travel_ticks=travel_ticks,
                capacity_per_tick=capacity_per_tick,
                normalized_command=normalized_command,
                mode=command.mode.value,
                **gate_context,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"valid {command.mode.value} link preview for {cost:.0f}",
            cost=cost,
            build_time=build_time,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            normalized_command=normalized_command,
            mode=command.mode.value,
            **gate_context,
        )

    if isinstance(command, BuildLink):
        (
            travel_ticks,
            capacity_per_tick,
            power_required,
            power_source_world_id,
            cost,
            build_time,
        ) = _validate_build_link(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, f"{command.mode.value} link", cost))
        link = NetworkLink(
            id=command.link_id,
            origin=command.origin,
            destination=command.destination,
            mode=command.mode,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
            bidirectional=command.bidirectional,
            build_cost=cost,
            build_time=build_time,
            alignment=command.alignment,
        )
        state.add_link(link)
        gate_context = _gate_preview_payload(
            state,
            command,
            power_required=power_required,
            power_source_world_id=power_source_world_id,
        )
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"built {command.mode.value} link {command.link_id} for {cost:.0f}",
            cost=cost,
            build_time=build_time,
            travel_ticks=travel_ticks,
            capacity_per_tick=capacity_per_tick,
            mode=command.mode.value,
            **gate_context,
        )

    if isinstance(command, PreviewBuildTrackSignal):
        try:
            signal = _validate_track_signal(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.signal_id, exc)
        return command_result(
            command.type,
            ok=True,
            target_id=signal.id,
            message=f"valid {signal.kind.value} signal preview on {signal.link_id}",
            normalized_command=_track_signal_payload(signal),
            link_id=signal.link_id,
            node_id=signal.node_id,
            kind=signal.kind.value,
            active=signal.active,
            block=signal.link_id,
        )

    if isinstance(command, BuildTrackSignal):
        signal = _validate_track_signal(state, command)
        state.add_track_signal(signal)
        return command_result(
            command.type,
            ok=True,
            target_id=signal.id,
            message=f"built {signal.kind.value} signal {signal.id} on {signal.link_id}",
            link_id=signal.link_id,
            node_id=signal.node_id,
            kind=signal.kind.value,
            active=signal.active,
            block=signal.link_id,
        )

    if isinstance(command, DemolishLink):
        if command.link_id not in state.links:
            raise ValueError(f"unknown link id: {command.link_id}")
        for train in state.trains.values():
            if command.link_id in train.route_link_ids:
                raise ValueError(f"cannot demolish link in active train route: {command.link_id}")
        signal_ids = [
            signal.id
            for signal in state.track_signals.values()
            if signal.link_id == command.link_id
        ]
        if signal_ids:
            raise ValueError(
                f"cannot demolish link with track signals: {', '.join(sorted(signal_ids))}"
            )
        del state.links[command.link_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.link_id,
            message=f"demolished link {command.link_id}",
        )

    if isinstance(command, PreviewPurchaseTrain):
        try:
            cost = _validate_purchase_train(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.train_id, exc)
        normalized_command = _train_purchase_payload(command)
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, "train", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.train_id,
                message=reason,
                reason=reason,
                cost=cost,
                capacity=command.capacity,
                consist=TrainConsist(command.consist).value,
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.train_id,
            message=f"valid train preview for {cost:.0f}",
            cost=cost,
            capacity=command.capacity,
            consist=TrainConsist(command.consist).value,
            normalized_command=normalized_command,
        )

    if isinstance(command, PurchaseTrain):
        cost = _validate_purchase_train(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, "train", cost))
        train = FreightTrain(
            id=command.train_id,
            name=command.name,
            node_id=command.node_id,
            capacity=command.capacity,
            consist=TrainConsist(command.consist),
        )
        state.add_train(train)
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.train_id,
            message=f"purchased train {command.train_id} for {cost:.0f}",
            cost=cost,
            capacity=command.capacity,
            consist=train.consist.value,
        )

    if isinstance(command, PreviewCreateSchedule):
        try:
            next_departure_tick, route = _validate_create_schedule(state, command)
        except ValueError as exc:
            result = _preview_error(command.type, command.schedule_id, exc)
            result.update(_schedule_route_debug_payload(state, command, str(exc)))
            return result
        normalized_command = _schedule_payload(command, next_departure_tick=next_departure_tick)
        route_context = _route_context_payload(state, route)
        train = state.trains[command.train_id]
        required_consist = required_consist_for(command.cargo_type)
        route_debug = _schedule_route_debug_payload(state, command)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"valid schedule preview over {route.travel_ticks} ticks",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            route_stop_ids=route_debug["route_stop_ids"],
            route_segments=route_debug["route_segments"],
            required_consist=required_consist.value,
            train_consist=train.consist.value,
            normalized_command=normalized_command,
            **route_context,
        )

    if isinstance(command, CreateSchedule):
        next_departure_tick, route = _validate_create_schedule(state, command)
        schedule = FreightSchedule(
            id=command.schedule_id,
            train_id=command.train_id,
            origin=command.origin,
            destination=command.destination,
            cargo_type=command.cargo_type,
            units_per_departure=command.units_per_departure,
            interval_ticks=command.interval_ticks,
            next_departure_tick=next_departure_tick,
            priority=command.priority,
            active=command.active,
            return_to_origin=command.return_to_origin,
            stops=command.stops,
            train_stops=command.train_stops,
        )
        state.add_schedule(schedule)
        route_context = _route_context_payload(state, route)
        train = state.trains[command.train_id]
        required_consist = required_consist_for(command.cargo_type)
        route_debug = _schedule_route_debug_payload(state, command)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"created schedule {command.schedule_id}",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            route_stop_ids=route_debug["route_stop_ids"],
            route_segments=route_debug["route_segments"],
            required_consist=required_consist.value,
            train_consist=train.consist.value,
            **route_context,
        )

    if isinstance(command, PreviewUpdateSchedule):
        try:
            schedule, draft, next_departure_tick, route = _validate_update_schedule(state, command)
        except ValueError as exc:
            result = _preview_error(command.type, command.schedule_id, exc)
            schedule = state.schedules.get(command.schedule_id)
            if schedule is not None:
                draft = _schedule_update_draft(state, command, schedule)
                result.update(_schedule_route_debug_payload(state, draft, str(exc)))
            else:
                result["validation_errors"] = _schedule_validation_errors(str(exc))
            return result
        normalized_command = _schedule_update_payload(
            command,
            draft,
            next_departure_tick=next_departure_tick,
        )
        route_context = _route_context_payload(state, route)
        train = state.trains[draft.train_id]
        required_consist = required_consist_for(draft.cargo_type)
        route_debug = _schedule_route_debug_payload(state, draft)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"valid schedule update preview over {route.travel_ticks} ticks",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            route_stop_ids=route_debug["route_stop_ids"],
            route_segments=route_debug["route_segments"],
            required_consist=required_consist.value,
            train_consist=train.consist.value,
            current_schedule={
                "id": schedule.id,
                "train_id": schedule.train_id,
                "origin": schedule.origin,
                "destination": schedule.destination,
                "stops": list(schedule.stops),
                "cargo_type": schedule.cargo_type.value,
                "units_per_departure": schedule.units_per_departure,
                "interval_ticks": schedule.interval_ticks,
                "next_departure_tick": schedule.next_departure_tick,
                "priority": schedule.priority,
                "active": schedule.active,
                "return_to_origin": schedule.return_to_origin,
            },
            normalized_command=normalized_command,
            **route_context,
        )

    if isinstance(command, UpdateSchedule):
        schedule, draft, next_departure_tick, route = _validate_update_schedule(state, command)
        schedule.train_id = draft.train_id
        schedule.origin = draft.origin
        schedule.destination = draft.destination
        schedule.stops = draft.stops
        schedule.cargo_type = draft.cargo_type
        schedule.units_per_departure = draft.units_per_departure
        schedule.interval_ticks = draft.interval_ticks
        schedule.next_departure_tick = next_departure_tick
        schedule.priority = draft.priority
        schedule.active = draft.active
        schedule.return_to_origin = draft.return_to_origin
        schedule.train_stops = draft.train_stops
        route_context = _route_context_payload(state, route)
        train = state.trains[draft.train_id]
        required_consist = required_consist_for(draft.cargo_type)
        route_debug = _schedule_route_debug_payload(state, draft)
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"updated schedule {command.schedule_id}",
            next_departure_tick=next_departure_tick,
            route_travel_ticks=route.travel_ticks,
            route_node_ids=list(route.node_ids),
            route_link_ids=list(route.link_ids),
            route_stop_ids=route_debug["route_stop_ids"],
            route_segments=route_debug["route_segments"],
            required_consist=required_consist.value,
            train_consist=train.consist.value,
            **route_context,
        )

    if isinstance(command, PreviewDeleteSchedule):
        try:
            schedule = _validate_delete_schedule(state, command)
        except ValueError as exc:
            reason = str(exc)
            return command_result(
                command.type,
                ok=False,
                target_id=command.schedule_id,
                message=(
                    f"cannot delete schedule {command.schedule_id}; active trip in progress"
                    if reason == "schedule_in_active_trip"
                    else reason
                ),
                reason=reason,
                validation_errors=_schedule_validation_errors(reason),
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"valid delete preview for schedule {command.schedule_id}",
            schedule={
                "id": schedule.id,
                "train_id": schedule.train_id,
                "origin": schedule.origin,
                "destination": schedule.destination,
                "stops": list(schedule.stops),
                "cargo_type": schedule.cargo_type.value,
                "units_per_departure": schedule.units_per_departure,
                "interval_ticks": schedule.interval_ticks,
                "next_departure_tick": schedule.next_departure_tick,
                "priority": schedule.priority,
                "active": schedule.active,
                "return_to_origin": schedule.return_to_origin,
                "delivered_units": schedule.delivered_units,
                "trips_dispatched": schedule.trips_dispatched,
                "trips_completed": schedule.trips_completed,
            },
            normalized_command=_schedule_delete_payload(command),
        )

    if isinstance(command, DeleteSchedule):
        _validate_delete_schedule(state, command)
        del state.schedules[command.schedule_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.schedule_id,
            message=f"deleted schedule {command.schedule_id}",
        )

    if isinstance(command, PreviewBuildFacilityComponent):
        try:
            component, cost, cargo_cost, connections = _validate_facility_component(state, command)
        except ValueError as exc:
            if str(exc).startswith("unknown facility component kind: "):
                return command_result(
                    command.type,
                    ok=False,
                    target_id=command.component_id,
                    message=str(exc),
                )
            return _preview_error(command.type, command.component_id, exc)
        normalized_command = _facility_component_payload(
            command,
            component=component,
            cargo_cost=cargo_cost,
            connections=connections,
        )
        if not _cash_available(state, cost):
            reason = _insufficient_cash_message(state, f"{component.kind.value} component", cost)
            return command_result(
                command.type,
                ok=False,
                target_id=command.component_id,
                message=reason,
                reason=reason,
                cost=cost,
                cargo_cost=_plain_cargo_cost(cargo_cost),
                default_ports=normalized_command["ports"],
                node_id=command.node_id,
                kind=component.kind.value,
                power_required=int(component.power_required),
                power_provided=int(component.power_provided),
                normalized_command=normalized_command,
            )
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"valid {component.kind.value} component preview for {cost:.0f}",
            cost=cost,
            cargo_cost=_plain_cargo_cost(cargo_cost),
            default_ports=normalized_command["ports"],
            node_id=command.node_id,
            kind=component.kind.value,
            power_required=int(component.power_required),
            power_provided=int(component.power_provided),
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildFacilityComponent):
        component, cost, cargo_cost, connections = _validate_facility_component(state, command)
        if not _cash_available(state, cost):
            raise ValueError(_insufficient_cash_message(state, f"{component.kind.value} component", cost))
        node = state.nodes[command.node_id]
        if node.facility is None:
            node.facility = Facility()
        _consume_construction_cargo(state, node, cargo_cost)
        node.facility.components[component.id] = component
        for connection in connections:
            if connection.id in node.facility.connections:
                raise ValueError(f"duplicate connection id: {connection.id}")
            node.facility.connections[connection.id] = connection
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"installed {component.kind.value} component {command.component_id} for {cost:.0f}",
            cost=cost,
            cargo_cost=_plain_cargo_cost(cargo_cost),
            node_id=command.node_id,
            kind=component.kind.value,
            power_required=int(component.power_required),
            power_provided=int(component.power_provided),
        )

    if isinstance(command, PreviewDemolishFacilityComponent):
        try:
            node, facility, component, future_rate = _validate_demolish_facility_component(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.component_id, exc)
        cargo_returned, cargo_dropped = _demolish_cargo_plan(node, component)
        connections_removed = _connections_referencing_component(facility, command.component_id)
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"valid demolition preview for {component.kind.value} {component.id}",
            node_id=command.node_id,
            kind=component.kind.value,
            future_rate=future_rate,
            refund=_demolish_refund(component),
            cargo_returned=_plain_cargo_cost(cargo_returned),
            cargo_dropped=_plain_cargo_cost(cargo_dropped),
            connections_removed=connections_removed,
            normalized_command=_demolish_facility_component_payload(command),
        )

    if isinstance(command, DemolishFacilityComponent):
        node, facility, component, future_rate = _validate_demolish_facility_component(state, command)
        refund = _demolish_refund(component)
        cargo_returned, cargo_dropped = _demolish_cargo_plan(node, component)
        connections_removed = _connections_referencing_component(facility, command.component_id)
        for cargo_type, units in cargo_returned.items():
            node.add_inventory(cargo_type, units)
        for connection_id in connections_removed:
            facility.connections.pop(connection_id, None)
        del facility.components[command.component_id]
        state.finance.cash += refund
        return command_result(
            command.type,
            ok=True,
            target_id=command.component_id,
            message=f"demolished {component.kind.value} component {component.id}",
            node_id=command.node_id,
            kind=component.kind.value,
            future_rate=future_rate,
            refund=refund,
            cargo_returned=_plain_cargo_cost(cargo_returned),
            cargo_dropped=_plain_cargo_cost(cargo_dropped),
            connections_removed=connections_removed,
        )

    if isinstance(command, PreviewBuildInternalConnection):
        try:
            _, _, connection = _validate_build_internal_connection(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.connection_id, exc)
        normalized_command = _connection_payload(connection)
        normalized_command["node_id"] = command.node_id
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"valid internal connection preview for {connection.id}",
            node_id=command.node_id,
            normalized_command=normalized_command,
        )

    if isinstance(command, BuildInternalConnection):
        _, facility, connection = _validate_build_internal_connection(state, command)
        facility.connections[connection.id] = connection
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"built internal connection {connection.id}",
            node_id=command.node_id,
            **_connection_payload(connection),
        )

    if isinstance(command, PreviewRemoveInternalConnection):
        try:
            _, _, connection = _validate_remove_internal_connection(state, command)
        except ValueError as exc:
            return _preview_error(command.type, command.connection_id, exc)
        normalized_command = _connection_payload(connection, command_type="RemoveInternalConnection")
        normalized_command["node_id"] = command.node_id
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"valid internal connection removal preview for {connection.id}",
            node_id=command.node_id,
            normalized_command=normalized_command,
        )

    if isinstance(command, RemoveInternalConnection):
        _, facility, connection = _validate_remove_internal_connection(state, command)
        del facility.connections[command.connection_id]
        return command_result(
            command.type,
            ok=True,
            target_id=command.connection_id,
            message=f"removed internal connection {connection.id}",
            node_id=command.node_id,
            **_connection_payload(connection, command_type="RemoveInternalConnection"),
        )

    if isinstance(command, UpgradeNode):
        if command.node_id not in state.nodes:
            raise ValueError(f"unknown node id: {command.node_id}")
        if command.storage_capacity_increase < 0:
            raise ValueError("storage_capacity_increase cannot be negative")
        if command.transfer_limit_increase < 0:
            raise ValueError("transfer_limit_increase cannot be negative")
        if command.storage_capacity_increase == 0 and command.transfer_limit_increase == 0:
            raise ValueError("upgrade must increase storage or transfer capacity")
        node = state.nodes[command.node_id]
        cost = node_upgrade_cost(command.storage_capacity_increase, command.transfer_limit_increase)
        if state.finance.cash < cost:
            raise ValueError(
                f"insufficient cash for upgrade: need {cost:.0f}, have {state.finance.cash:.0f}"
            )
        node.storage_capacity += command.storage_capacity_increase
        node.transfer_limit_per_tick += command.transfer_limit_increase
        state.finance.record_cost(cost)
        return command_result(
            command.type,
            ok=True,
            target_id=command.node_id,
            message=f"upgraded node {command.node_id} for {cost:.0f}",
        )

    raise TypeError(f"unsupported player command: {type(command).__name__}")
