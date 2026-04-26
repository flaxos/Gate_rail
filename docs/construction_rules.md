# GateRail Construction Rules

This document is the canonical Sprint 13 rules reference for player-built local infrastructure. The Python backend owns validation, pricing, pathfinding, and mutation. Godot may propose positions and commands, but it should preview through the backend before committing a build.

## Build Flow

1. The client sends a preview command such as `PreviewBuildNode`, `PreviewBuildLink`, `PreviewPurchaseTrain`, or `PreviewCreateSchedule`.
2. The backend returns `ok`, a human-readable `message`, relevant cost/route metadata, and a `normalized_command` when valid.
3. The client commits by sending the returned normalized command.
4. Invalid previews return `ok: false` inside `bridge.command_results`; they should not become bridge-level errors.

## Node Roles

- `settlement`: demand endpoint for people and local consumption.
- `depot`: train-facing logistics yard with stronger transfer than a basic node.
- `warehouse`: high-capacity buffer for smoothing supply flow and future bottleneck gameplay.
- `extractor`: local production source such as mines, farms, or wells.
- `industry`: processing and manufacturing node.
- `gate_hub`: local interface to interworld gate logistics.

Default node costs and capacities are centralized in `src/gaterail/construction.py`. Current costs are settlement 800, depot 1200, warehouse 1600, extractor 1500, industry 2000, and gate hub 8000.

## Local Layout

- Built nodes may include `layout: {"x": float, "y": float}`.
- The backend persists layout as `layout_x` and `layout_y`.
- Snapshots expose node layout as `node.layout`.
- Missing layout is allowed for legacy/scenario nodes; Godot falls back to deterministic visual placement.

## Rail Links

- `BuildLink` is rail-only until a later gate-construction sprint.
- Rail endpoints must be different nodes on the same world.
- Duplicate rail links between the same endpoint pair are rejected.
- Capacity and travel ticks must be positive.
- If `travel_ticks` is omitted, the backend derives it from persisted local layout distance using 50 layout units per travel tick, minimum 1.
- Rail cost is `150 * travel_ticks`.
- Link build-time metadata is `travel_ticks * 2`, but Sprint 13 construction still completes immediately.

## Trains

- `PreviewPurchaseTrain` and `PurchaseTrain` use backend-owned pricing.
- Train ids must be unique, target nodes must exist, names cannot be blank, and capacity must be positive.
- Current train cost is `500 + capacity * 20`.
- A purchased train starts idle at its target node.

## Route Schedules

- `PreviewCreateSchedule` and `CreateSchedule` create recurring freight routes from existing infrastructure.
- The train must exist, be idle, and be located at the schedule origin.
- Origin and destination nodes must exist and be different.
- A backend route must exist between origin and destination.
- Units per departure and interval ticks must be positive.
- Units per departure cannot exceed train capacity.
- If `next_departure_tick` is omitted, the backend normalizes it to `state.tick + 1`.
- Preview returns route travel ticks, route node ids, route link ids, and a normalized `CreateSchedule` command.

## Deferred

- Delayed construction jobs and queue simulation.
- Gate-link construction and interworld expansion.
- Per-tile collision, zoning, terrain costs, and bridge/tunnel rules.
- Rich route UI for cargo choice, schedule interval tuning, and multi-stop services.
