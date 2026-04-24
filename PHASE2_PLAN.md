# Phase 2 Plan

## Purpose

Phase 2 proves that GateRail can become a playable 2D prototype without rewriting the Python simulation. The Godot client is a view and input layer. The Python fixed-tick backend remains authoritative for logistics, contracts, finance, progression, routing, train movement, gate power, and snapshots.

## Locked Decisions

- Player agency target: full construction over time.
- Integration architecture: Python subprocess plus newline-delimited JSON over stdio.
- Layout ownership: hybrid. Python owns deterministic galaxy-scale world coordinates in `render_snapshot()`. Godot owns visual layout metadata such as camera placement, intra-world station presentation, labels, and interaction affordances.

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
- make the existing simulation playable from Godot without construction.

Deliverables:
- schedule panel with enable/disable controls.
- one-shot dispatch form using `DispatchOrder`.
- cancel pending order control using `CancelOrder`.
- contract progress panel.
- finance and reputation HUD.
- pause/step/run controls backed by the stdio bridge.

Exit criteria:
- a player can use Godot to influence the Sprint 8/Sprint 9 scenario outcomes without touching terminal commands.

## Sprint 12: Construction Slice 1

Goal:
- begin full construction by expanding an existing galaxy rather than creating arbitrary new worlds.

Deliverables:
- backend build commands for new logistics nodes on existing worlds.
- backend build commands for rail links between valid nodes.
- command validation, cash costs, and error frames.
- Godot build mode for placing a station/node and drawing a rail link.
- snapshot updates that include newly built entities.

Exit criteria:
- the player can add useful rail infrastructure to the existing benchmark scenario and see it affect logistics.

## Sprint 13: Construction Slice 2

Goal:
- add high-impact expansion infrastructure.

Deliverables:
- backend build commands for gate links and gate hubs.
- train purchase/build command.
- schedule creation command.
- Godot UI for gate construction, train purchase, and schedule creation.
- clear cost, power, and capacity feedback.

Exit criteria:
- the player can expand from existing worlds toward a new logistics solution using stations, rail, gates, trains, and schedules.

## Deferred Until After Sprint 13

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
