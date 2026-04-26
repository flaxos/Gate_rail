# GateRail Godot Client

This is the Stage 2 client scaffold. It is intentionally thin: Godot renders snapshots and sends player commands, while the Python backend remains authoritative.

## Run

From the repository root:

```bash
godot --path godot
```

The first screen loads `fixtures/sprint9_snapshot.json` as a fallback, then immediately requests a live `{"ticks":0}` snapshot from the Python stdio bridge. The layout anchors the control and operations panels to the viewport edges, stretches the alert strip across the bottom, and keeps the map in the available center area. The status panel shows whether the current data is fixture or live, and the bottom alert strip shows recent command results, bridge errors, disruptions, and congestion chips. Press `Step 1 tick` to advance once, `Play` to auto-run, use the generated schedule rows to enable or disable live schedules, or queue/cancel one-shot orders from the operations panel. Click worlds, nodes, links, or trains on the map to inspect their current state.

## Bridge

Default command, with the repository root resolved from `res://`:

```bash
cd <repo-root> && PYTHONPATH=src python3 -m gaterail.main --stdio
```

Override it with:

```bash
GATERAIL_BRIDGE_COMMAND="cd .. && PYTHONPATH=src python3 -m gaterail.main --stdio" godot --path godot
```

## Current Scope

- Render worlds, links, nodes, trains, contracts, finance, and reputation from a snapshot.
- Send `ticks`, `SetScheduleEnabled`, `DispatchOrder`, and `CancelOrder` through the bridge autoload.
- Show finance, reputation, contracts, schedule state, and pending one-shot orders in UI panels.
- Surface command history, bridge errors, disrupted links, and congested gate slots in the alert/status strip.
- Auto-run the live simulation and inspect selected map entities without duplicating simulation rules in Godot.
- Keep simulation rules out of Godot.

Construction now belongs in `scenes/local_region.tscn`. The Local Region scene uses backend-owned preview commands for node, gate-hub, same-world rail, interworld gate-link, train purchase, and first route-schedule creation. Route creation opens cargo and tuning popups so units per departure and interval ticks are chosen before `PreviewCreateSchedule`. The Build Planner in the right HUD shows preview details, gate handoff route warnings, and can confirm or cancel valid normalized backend commands; map clicks still support the quick preview-then-commit flow. Built nodes persist local layout coordinates through the Python snapshot/save-load path. Link demolition remains a direct command. The `LAYERS` toggle is presentation-only and renders supply, demand, inventory/storage fill, shortages, recipe-blocked inputs, and transfer pressure from the Python snapshot.
