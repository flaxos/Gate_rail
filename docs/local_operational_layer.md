# Local Operational Layer

GateRail now has a persisted backend-owned local construction grid under the
strategic map. The Python fixed-tick backend remains authoritative; Godot reads
snapshots and sends JSON-over-stdio commands.

## Current Model

- `GameState.operational_areas` stores local grids by area id such as
  `atlas:local`.
- Each `OperationalAreaState` has `world_id`, `width`, `height`, `cell_size`,
  and persisted `OperationalPlacedEntity` records.
- Each placed entity stores `entity_id`, `entity_type`, cell `x/y/z`,
  `rotation`, footprint, backing refs (`owner_node_id`, `component_id`,
  `link_id`), optional `path_cells`, platform-side and port-adjacency metadata,
  ports, construction state, visual hint, blockers, and occupancy.
- Snapshots expose `operational_areas[].grid.kind == "local_grid"` and
  `has_cell_occupancy == true`.
- Older saves or scenarios with no persisted grid are migrated from existing
  nodes, links, facilities, components, and internal connections.

## Entity Mapping

| Local entity | Backing model |
| --- | --- |
| extractor | `NetworkNode(kind=extractor)` or `FacilityComponentKind.EXTRACTOR_HEAD` |
| track_segment | `NetworkLink(mode=rail)` |
| station_platform | station/depot node or `FacilityComponentKind.PLATFORM` |
| loader | `FacilityComponentKind.LOADER` |
| unloader | `FacilityComponentKind.UNLOADER` |
| hopper | `FacilityComponentKind.STORAGE_BAY` |
| storage | warehouse/depot node or `FacilityComponentKind.WAREHOUSE_BAY` |
| transfer_link | `InternalConnection(link_type=...)` |
| refinery | `FacilityComponentKind.REFINERY` |
| factory | `FacilityComponentKind.FABRICATOR` |
| railgate_terminal | `NetworkNode(kind=gate_hub)` or `FacilityComponentKind.GATE_INTERFACE` |

## Backend Commands

All commands return readable `ok/message/reason` results and refreshable local
state.

```json
{"type":"local.get_operational_area","operational_area_id":"atlas:local"}
{"type":"local.list_build_options","operational_area_id":"atlas:local"}
{"type":"local.validate_placement","operational_area_id":"atlas:local","entity_type":"loader","entity_id":"mine_loader","owner_node_id":"atlas_local_mine","x":18,"y":15}
{"type":"local.place_entity","operational_area_id":"atlas:local","entity_type":"loader","entity_id":"mine_loader","owner_node_id":"atlas_local_mine","x":18,"y":15,"rotation":90,"platform_side":"east","adjacent_to_entity_id":"atlas_local_mine:station","adjacent_port_id":"rail_out","construction_cargo":{"construction_materials":4}}
{"type":"local.rotate_entity","operational_area_id":"atlas:local","entity_id":"mine_loader","rotation":180}
{"type":"local.delete_entity","operational_area_id":"atlas:local","entity_id":"mine_loader"}
{"type":"local.inspect_entity","operational_area_id":"atlas:local","entity_id":"mine_loader"}
{"type":"local.place_entity","operational_area_id":"atlas:local","entity_type":"track_segment","link_id":"rail_mine_refinery","origin_node_id":"atlas_local_mine","destination_node_id":"atlas_local_refinery","x":18,"y":13,"path_cells":[{"x":18,"y":13},{"x":19,"y":13},{"x":20,"y":13}]}
{"type":"local.connect_entities","operational_area_id":"atlas:local","owner_node_id":"atlas_local_mine","connection_id":"wire_mine_head_to_storage","source_component_id":"mine_head","source_port_id":"ore_out","destination_component_id":"mine_storage","destination_port_id":"ore_in","link_type":"hopper"}
```

## Flow Rules

Placement is authoritative. Local loaders, unloaders, transfer links, storage,
refineries, factories, and Railgate terminals participate through the existing
facility, train, construction-project, and schedule systems. Missing loaders,
unloaders, track, transfer links, or factory wiring produce backend blockers.
Tutorial progress is based on real cargo movement and construction state.

Track can now occupy explicit backend-validated `path_cells`, so clients may
draw multi-cell rail paths while the Python backend still owns occupancy,
overlap, bounds, and graph-link validation. Platform-side and port-adjacency
hints are also backend-validated for local placements.

Local rail diagnostics are exposed in snapshots under `local_rail`. They map
persisted track `path_cells` back to the existing graph link, active
`TrackSignal` blocks, reservations, occupying trains, blocked route events, and
abstract station-throat switch diagnostics. This gives Godot real rail
operations context without making Godot own routing or signal rules.

Godot local track inspection now has backend-backed controls for this layer:
`local.validate_signal` previews a signal on a persisted track entity,
`local.place_signal` commits it as a real Python `TrackSignal`, and
`local.set_switch_route` persists the selected route for an abstract
station-throat switch. The selected switch route is included in `local_rail`
snapshots with its signal ids, block reservation, occupying trains, blocked
events, and save/load data.

Transfer-link kinds expose backend profiles through `local.list_build_options`.
The backend validates known cargo compatibility (`hopper` for bulk, `pipe` for
fluids, etc.) and applies transfer-rate multipliers during facility flow.

## Save/Load

Save files serialize operational areas, grid dimensions, placed entities,
rotations, path cells, occupied cells, platform-side and adjacency metadata,
backing refs, facility cargo buffers, construction inventory, cargo,
connections, local switch route choices, schedules, trains, contracts, and
tutorial state. Loads without `operational_areas` migrate safely from existing
scenario data.

## Known Limits

- Track placement still creates a graph link for trains; `path_cells` provide
  local occupancy, drawing geometry, and diagnostics rather than full per-cell
  train physics.
- Switch route controls persist an operator-selected route over abstract
  station-throat diagnostics; dispatch still reserves graph-link blocks rather
  than full per-cell switch blocks.
- Node deletion through `local.delete_entity` is intentionally limited; backed
  facility components, transfer links, and rail links can be removed safely.
- Godot rendering is functional and backend-driven, not final art.

## Next Recommended Goal

Use the persisted switch-route choices and signal metadata to drive richer local
rail conflicts: per-cell block sections, multi-link path signals, and train
wait reasons that distinguish a reserved station throat from a full graph link.
