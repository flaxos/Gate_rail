# Phase 2 Plan

## Purpose

Phase 2 proves that GateRail can become a playable 2D prototype without rewriting the Python simulation. The Godot client is a view and input layer. The Python fixed-tick backend remains authoritative for logistics, contracts, finance, progression, routing, train movement, gate power, and snapshots.

## Locked Decisions

- Player agency target: full construction over time.
- Integration architecture: Python subprocess plus newline-delimited JSON over stdio.
- Layout ownership: hybrid. Python owns deterministic galaxy-scale world coordinates in `render_snapshot()` and persists local node layout metadata once the player builds infrastructure. Godot proposes intra-world positions and owns camera placement, presentation, labels, and interaction affordances.

## Guardrails

- Do not duplicate simulation rules in Godot.
- Keep every backend interaction expressible as a versioned JSON command or snapshot.
- Start by controlling existing simulation entities before adding construction commands.
- Add backend commands only when the Godot UI needs them and tests can lock the contract.
- Keep Godot files text-serializable and contained under `godot/`.

## Sprint 10: Godot Bridge Prototype

Goal:
- prove Godot can launch the backend, receive snapshots, render the network, and send one control command.

Deliverables:
- `godot/` project scaffold.
- `GateRailBridge` autoload that starts `gaterail --stdio`.
- `Main` scene that renders worlds, links, nodes, trains, contracts, finance, and reputation from `SNAPSHOT_VERSION = 1`.
- Step button that sends `{"ticks":1}`.
- Schedule toggle path that sends `SetScheduleEnabled`.

Exit criteria:
- Godot can start the Python subprocess, receive a snapshot, draw it, step one tick, toggle a schedule, and redraw from the returned snapshot.

## Sprint 11: Playable Operations UI

Goal:
- make the existing simulation playable from Godot without construction, so the bridge/client loop is solid before track laying begins.

Deliverables:
- pause/step/run controls backed by the stdio bridge.
- click selection for worlds, nodes, links, and trains.
- inspector panel showing the selected entity's operational state.
- clearer map state for rail vs gate links, link capacity, disruptions, and in-transit trains.
- playtest notes documenting what is playable before construction.

Exit criteria:
- a player can run, inspect, and influence the Sprint 8/Sprint 9 scenario outcomes from Godot without touching terminal commands.

## Sprint 12: Track Construction Rules and Backend Commands

Goal:
- define the core track-laying game rules before building the Godot construction UI.

Deliverables:
- construction rules for buildable node roles: extractor, industry, depot, warehouse, settlement connector, and gate hub.
- backend commands for new logistics nodes on existing worlds.
- backend commands for rail links between valid nodes.
- validation for duplicate links, world boundaries, invalid endpoints, cash costs, and storage/transfer defaults.
- JSON bridge error frames for invalid construction.
- snapshot updates that include newly built entities and construction-relevant metadata.

Exit criteria:
- backend tests prove that constructed nodes and rail links can alter routing and logistics outcomes.

Scope note:
- Sprint 12 construction completes immediately. Delayed build jobs and construction queues are deferred until the UI and economy prove they need timed construction.
- `BuildLink` is rail-only in Sprint 12. Gate links, space-lane equivalents, and interworld construction remain Sprint 15+ work.

## Sprint 13: Godot Track Construction Mode

Goal:
- wire the existing Local Region scene chrome into real backend construction commands.

Canonical wireframe:
- `docs/design_handoff/local_region_construction/Local Region Construction.html` (Claude Design handoff). The scene scaffold (Sprint 12 prep, already landed) is `godot/scenes/local_region.tscn` + `godot/scripts/local_region.gd`. Panel structure to honour:
  - **Topbar (56px):** brand mark, breadcrumb `GALAXY › <sector> › <world> · LOCAL`, stat chips (Credits / Power / Tick), Galaxy Map back button.
  - **Left tool rail (64px):** Select (V), Pan (H), Lay Rail (R), Place Node (N), Gate Hub (G), Train (T), Demolish (X), Layers (L). Sprint 13 wires each tool to its backend command.
  - **Center canvas:** dark-blue grid wash + corner brackets + compass + scale bar + region label. Sprint 13 adds drag-to-connect ghost path with snap-lock and cost tooltip on the rail tool.
  - **Right HUD (360px):** planet card, local inventory, gate throughput, construction queue placeholder until delayed build jobs exist.
  - **Bottom status bar (44px):** mode chip, bridge LIVE/OFFLINE chip, hotkey reminders.

Deliverables:
- tool-rail buttons emit real `BuildNode` / `BuildLink` / `DemolishLink` / `PurchaseTrain` commands via the bridge.
- drag-to-connect interaction: ghost path between source/target with snap-lock, segment length, build cost, power draw, build time, valid/invalid chip.
- backend-owned cost preview tooltip and validation feedback (matches the HTML design without duplicating simulation rules in Godot).
- construction queue panel remains placeholder until delayed build jobs are implemented.
- "Link to Galaxy Network" button on the gate hub returns to the galaxy scene with the chosen destination preselected.
- immediate redraw from returned snapshots.

Exit criteria:
- the player can add rail infrastructure to the benchmark scenario from the Local Region scene and see it affect routing.

Slice 13A completed state:
- Backend preview commands now exist for node and rail construction: `PreviewBuildNode` and `PreviewBuildLink`.
- Preview commands return valid/invalid feedback, cost, build time, normalized build commands, and do not mutate cash or map state.
- Built nodes persist local layout coordinates through save/load and render snapshots.
- Rail links can derive travel ticks from persisted local layout when the client omits a manual travel time.
- Local Region construction uses a preview-then-commit flow for nodes, gate hubs, and same-world rail, so Godot no longer hardcodes node or rail construction costs.

Slice 13B completed state:
- `docs/construction_rules.md` records the authoritative construction rules for this phase.
- Backend preview coverage now includes train purchase and route schedule creation.
- `CreateSchedule` lets the client create a recurring route from existing infrastructure once the backend validates idle train, origin, destination, capacity, interval, next departure, and route existence.
- Local Region Train mode can preview/buy a train at a node, select an idle train as route origin, and preview/create a recurring route schedule to a clicked destination.
- Godot no longer hardcodes train purchase cost or route validity.

Slice 13C completed state:
- The Local Region right HUD now contains a `Build Planner` panel instead of a misleading construction queue placeholder.
- The planner mirrors backend preview results with costs, build/travel timing, capacity, storage/transfer, route, cargo, and interval context.
- Valid previews can be committed or cancelled from the HUD, reducing reliance on status-strip-only feedback.
- Delayed construction queues remain deferred.

## Sprint 14: Industry, Depot, and Warehouse Logistics

Goal:
- make local-world rail construction matter as the main game loop.

Deliverables:
- warehouse/depot buffering rules and visible storage pressure.
- clearer extractor to industry to depot flows.
- node transfer constraints that make local track layout meaningful.
- UI overlays for supply, demand, inventory, and shortages.

Exit criteria:
- the player can improve a local world's supply chain by connecting production, storage, demand, and depot nodes.

## Sprint 15: Gate Expansion, Trains, and Schedule Creation

Goal:
- connect local track networks to interworld wormhole logistics.

Deliverables:
- backend commands for gate hubs and gate links.
- train purchase/build command.
- schedule creation command.
- Godot UI for gate construction, train purchase, and schedule creation.
- clear cost, power, capacity, and route feedback.

Exit criteria:
- the player can expand an existing network with rail, warehouses/depots, gates, trains, and schedules from Godot.

## Deferred Until After Sprint 15

- new world creation.
- re-specialization of worlds.
- rival operators.
- tech tree.
- modular station internals.
- detailed signal/block simulation.

## Interactive Cadence

Each Phase 2 sprint should end with:
- a runnable Godot scene or backend bridge smoke command,
- a short playtest note stating what can be seen and controlled,
- tests for every backend command or bridge contract changed,
- a decision on whether the slice is understandable enough before increasing construction scope.
