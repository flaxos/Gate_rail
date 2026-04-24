# GateRail Godot Client

This is the Stage 2 client scaffold. It is intentionally thin: Godot renders snapshots and sends player commands, while the Python backend remains authoritative.

## Run

From the repository root:

```bash
godot --path godot
```

The first screen loads `fixtures/sprint9_snapshot.json` as a fallback, then immediately requests a live `{"ticks":0}` snapshot from the Python stdio bridge. The status panel shows whether the current data is fixture or live, and the bottom alert strip shows recent command results, bridge errors, disruptions, and congestion chips. Press `Step 1 tick` to advance, use the generated schedule rows to enable or disable live schedules, or queue/cancel one-shot orders from the operations panel.

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
- Keep simulation rules out of Godot.

Construction commands are deferred to later Phase 2 sprints.
