# Local Logistics Loop

The playable local tutorial scenario is `tutorial_local_logistics`.
It demonstrates a bottom-up chain from mine output to Railgate deployment while
preserving the strategic map, Railgate network, schedules, contracts, and
save/load flow.

## Run Commands

Inspect the scenario:

```bash
PYTHONPATH=src python3 -m gaterail.main --scenario tutorial_local_logistics --inspect --report schedules,stockpiles,facilities,gates,contracts
```

Run the JSON-over-stdio bridge for Godot:

```bash
PYTHONPATH=src python3 -m gaterail.main --scenario tutorial_local_logistics --stdio
```

Run the focused automated coverage:

```bash
pytest tests/test_sprint32_local_logistics_loop.py -q
```

Run the full backend regression suite:

```bash
PYTHONPATH=src pytest -q
```

## Backend Loop

The tutorial's `tutorial.next_action` payload advances through real backend
commands and ticks. Local construction steps now use the persisted operational
grid commands (`local.place_entity` and `local.connect_entities`):

1. Connect mine extractor output to mine storage with a placed conveyor transfer link.
2. Lay a local track segment from mine to refinery.
3. Place the mine loader, spending starter construction materials.
4. Place the refinery unloader, spending starter construction materials.
5. Wire refinery storage through the refinery block.
6. Create and run the ore train route.
7. Install the refinery loader, spending starter construction materials.
8. Place local track from refinery to gateworks.
9. Create and run the metal train route.
10. Manufacture machinery from metal at gateworks, then manufacture gate
    components from machinery plus more metal.
11. Place local track from gateworks to the Railgate terminal.
12. Create and run the component train route.
13. Let the Railgate construction project consume delivered components.
14. Survey Sable Reach.
15. Build the Atlas-Sable Railgate corridor.
16. Create and run starter freight to Sable.
17. Fulfill the starter cargo contract.

The success condition is not tutorial-only state. It is the fulfilled contract
after real local production, train movement, construction-project cargo
consumption, Railgate construction, and macro freight delivery.

## Manual UAT Checklist

1. Start Godot and select `tutorial_local_logistics`.
2. Enter the local region view for Atlas.
3. Confirm the persisted grid, occupied cells, mine, refinery, gateworks,
   Railgate terminal, depot, rails, trains, inventories, blockers, operational
   area entities, and tutorial panel are visible.
4. Click the backend tutorial action button step by step.
5. Inspect the mine after the first step and verify the conveyor transfer link is
   listed in facility connections.
6. Continue until ore moves by train from mine to refinery.
7. Inspect the refinery and verify ore input, metal output, and blocker changes.
8. Continue until metal reaches gateworks, machinery is fabricated, and gate
   components are manufactured.
9. Continue until components reach the Railgate terminal and the construction
   project completes.
10. Survey Sable and build the Railgate corridor.
11. Run starter freight and verify Sable receives construction materials.
12. Save, load, and confirm local grid entities, rotations, facilities, transfer
    links, cargo buffers, schedules, trains, construction inventory, project
    state, blockers, and tutorial progress remain intact.

## Backend Command Examples

```json
{"type":"local.list_build_options","operational_area_id":"atlas:local"}
{"type":"local.place_entity","operational_area_id":"atlas:local","entity_type":"track_segment","link_id":"rail_atlas_local_mine_refinery","origin_node_id":"atlas_local_mine","destination_node_id":"atlas_local_refinery","x":19,"y":14,"path_cells":[{"x":19,"y":14},{"x":20,"y":14},{"x":21,"y":14}]}
{"type":"local.connect_entities","operational_area_id":"atlas:local","owner_node_id":"atlas_local_refinery","connection_id":"wire_refinery_ore","source_component_id":"refinery_storage","source_port_id":"ore_out","destination_component_id":"refinery_block","destination_port_id":"ore_in","link_type":"hopper"}
```

## Expected Blockers

The scenario intentionally starts with visible blockers:

- `transfer_link_missing`
- `track_missing`
- `missing_loader`
- `missing_unloader`
- `conveyor_missing`
- `route_missing`
- `factory_blocked`
- `destination_storage_full`
- `insufficient construction parts`
- `gate_not_built`
- `macro_waiting_on_local_output`
- `destination_not_surveyed`
- `gate_connection_incomplete`

As the player builds the physical chain, those blockers clear from backend state.

## Known Limits

- Track geometry now persists backend-validated `path_cells`, but trains still
  traverse the backed graph link rather than per-cell switch blocks. Snapshots
  expose `local_rail` diagnostics so the UI can show signal blocks,
  reservations, occupying trains, blocked route events, editable signal
  placement, and selected abstract station-throat routes over those path cells.
- Loader/unloader components affect train transfer rates, occupy local cells,
  and may carry backend-validated platform-side and port-adjacency metadata.
- Transfer-link kinds are backend profiles: incompatible known cargo is rejected
  and movement rates differ by link type.
- The tutorial uses scenario-unlocked recipes and does not require a full tech
  tree.
- Godot automated tests are limited to script/contract checks; use the UAT list
  above for visual verification.

## Next Recommended Goal

Make local rail conflicts more physical: apply persisted switch-route choices
and signal metadata to per-cell block sections, multi-link path signals, and
clear station-throat wait reasons in dispatch reports.
