# Local Build UX

Godot is a view/input layer for the backend-owned operational grid. It may keep
hover, selection, and pending-preview state, but it must not own persistent
placement state.

## Current Behaviour

- Local region snapshots read `operational_areas`.
- The canvas renders persisted operational entities from backend cells.
- Tutorial build actions now send `local.place_entity` and
  `local.connect_entities` for local infrastructure.
- Selecting a persisted local entity can inspect it through
  `local.inspect_entity`.
- Selected local entities expose rotate/delete controls that send
  `local.rotate_entity` and `local.delete_entity`.
- After each command, Godot refreshes from the backend snapshot.
- Facility drill-in still uses backend facility ports and connections.

## Manual UAT Checklist

1. Start Godot with the Python bridge.
2. Load `tutorial_local_logistics`.
3. Open Atlas local region.
4. Confirm the grid and persisted local entities are visible.
5. Run the tutorial action for mine storage connection.
6. Inspect the mine and confirm `wire_mine_head_to_storage` exists.
7. Continue through mine loader, refinery unloader, refinery wiring, and track
   placement.
8. Confirm ore only starts moving after the placed loader/unloader/track chain
   exists.
9. Continue until gate components reach the Railgate terminal and complete the
   construction project.
10. Save, load, and confirm local grid entities, rotations, connections, cargo,
    schedules, and tutorial state remain.

## Bridge Commands

```bash
PYTHONPATH=src python3 -m gaterail.main --scenario tutorial_local_logistics --stdio
```

Run the Local Region Godot smoke check:

```bash
scripts/godot_smoke_local_region.sh
```

Set `GODOT_BIN=/path/to/godot` if Godot is not on `PATH`. The smoke command
generates a `tutorial_local_logistics` snapshot, injects it into
`local_region.tscn`, asserts Atlas has nonempty persisted operational entities,
and redirects Godot user, data, config, and cache paths under `/tmp` so local
log permissions do not mask scene-load failures.

The default smoke command validates script load, scene state, visible UI
structure, and projected local entity positions. A real-window UAT pass is
still required to confirm the player-visible canvas pixels are not blank;
headless Godot does not expose pixel output under the dummy renderer.

On a machine with a working display server, run the same smoke in visual pixel
mode before closing a local-view crash goal:

```bash
scripts/godot_visual_smoke_local_region.sh
```

Visual smoke exits before launching Godot if it cannot open the current X11
display, so display-session failures are separated from Local Region scene
failures.

Example local command frame:

```json
{"commands":[{"type":"local.place_entity","operational_area_id":"atlas:local","entity_type":"loader","entity_id":"mine_loader","owner_node_id":"atlas_local_mine","x":18,"y":15,"rotation":90,"construction_cargo":{"construction_materials":4}}],"ticks":0}
```

## Known Limits

- Hover placement validation is not yet a full cell-preview system.
- Local node and rail placement now preview through `local.validate_placement`,
  including backend-validated rail `path_cells`; Railgate corridor links, train
  purchase, and route scheduling still use their existing macro preview commands.
- Platform-side, port-adjacency, and transfer-link profile data are backend
  snapshot/command fields; Godot may present them, but the Python backend owns
  validation and movement rules.
- Local track inspection can show backend `rail_diagnostics`: signal ids,
  protected block reservation, occupying trains, and blocked route waits from
  the existing Python traffic model.
- Local track inspection can preview and commit a stop signal through
  `local.validate_signal` / `local.place_signal`; committing creates a real
  backend `TrackSignal`. Track inspection also exposes station-throat switch
  route buttons that call `local.set_switch_route`, with the selected route
  persisted into snapshots and saves alongside signal/block reservation
  diagnostics.
- Art is symbolic and intended for functional readability.
