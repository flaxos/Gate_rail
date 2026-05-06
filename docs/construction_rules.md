# GateRail Construction Rules

This document is the canonical rules reference for player-built local infrastructure and Railgate corridor infrastructure. The Python backend owns validation, pricing, pathfinding, power context, and mutation. Godot may propose positions and commands, but it should preview through the backend before committing a build.

## Build Flow

1. The client sends a preview command such as `PreviewBuildNode`, `PreviewBuildLink`, `PreviewPurchaseTrain`, or `PreviewCreateSchedule`.
2. The backend returns `ok`, a human-readable `message`, relevant cost/route metadata, and a `normalized_command` when valid.
3. The client commits by sending the returned normalized command.
4. Invalid previews return `ok: false` inside `bridge.command_results`; they should not become bridge-level errors.

## Node Roles

- `settlement`: colony logistics hub and demand endpoint for people and local consumption.
- `depot`: train-facing rail yard with stronger transfer than a basic node.
- `warehouse`: high-capacity buffer for smoothing supply flow and future bottleneck gameplay.
- `extractor`: local extraction outpost such as mines, farms, wells, or remote receiving works.
- `industry`: refinery, processor, factory, or industrial material node.
- `gate_hub`: local Railgate anchor or receiving terminal for interworld corridor logistics.

Default node costs and capacities are centralized in `src/gaterail/construction.py`. Current costs are settlement 800, depot 1200, warehouse 1600, extractor 1500, industry 2000, and Railgate anchor (`gate_hub`) 8000.

## Local Layout

- Built nodes may include `layout: {"x": float, "y": float}`.
- The backend persists layout as `layout_x` and `layout_y`.
- Snapshots expose node layout as `node.layout`.
- Missing layout is allowed for legacy/scenario nodes; Godot falls back to deterministic visual placement.

## Rail Links

- Rail endpoints must be different nodes on the same world.
- Duplicate rail links between the same endpoint pair are rejected.
- Capacity and travel ticks must be positive.
- If `travel_ticks` is omitted, the backend derives it from persisted local layout distance using 50 layout units per travel tick, minimum 1.
- Rail cost is `150 * travel_ticks`.
- Link build-time metadata is `travel_ticks * 2`, but Sprint 13 construction still completes immediately.
- Current rail links are endpoint-only. Future rail construction should support backend-owned alignment geometry so local rails can curve, branch, enter underground vacuum tubes, and expose route/signal constraints without Godot inventing simulation rules.

## Future Rail Geometry, Branches, and Signals

Planned rail-depth work is tracked in `docs/rail_network_plan.md`. The intended direction:

- `BuildLink` / `PreviewBuildLink` should eventually accept optional waypoint/control-point geometry.
- Snapshots should expose persisted track alignment so Godot renders the same geometry Python prices and routes over.
- Surface rail and underground vacuum tubes should have distinct costs, constraints, and power/maintenance implications.
- Branches and junctions should become explicit routing objects rather than only visual line intersections.
- Stop signals and path signals should protect blocks, junctions, station throats, and vacuum-tube portals.
- Train capacity should evolve toward consists and cargo wagons so bulk ore, liquids, electronics, reactor inputs, construction modules, and exotic cargo can require different wagon types.

## Railgate Links

- Railgate links use `PreviewBuildLink` / `BuildLink` with `mode: "gate"` for stable bridge compatibility.
- Railgate endpoints must be different `gate_hub` nodes on different worlds.
- Railgate links are interpreted as a source-to-exit derivative aperture from `origin` to `destination`.
- `bidirectional: true` remains the default for legacy and simple Railgates. `bidirectional: false` creates a one-way aperture corridor.
- Duplicate links in the same direction are rejected. A reciprocal one-way Railgate in the opposite direction is allowed, unless either link is bidirectional.
- If `travel_ticks` is omitted by a JSON client, the backend defaults Railgate travel to 1 tick.
- If `capacity_per_tick` or `power_required` are omitted by a JSON client, the backend defaults them to 4 slots/tick and 80 MW.
- If `power_source_world_id` is omitted, the backend uses the origin node's world.
- Railgate power source must be one of the endpoint worlds.
- Railgate preview/build results include source/exit node ids, whether the corridor is directional, reverse-link availability, origin/destination world labels, power source, power required, current available power, power shortfall, and `powered_if_built`.
- Railgate links may be built even if they would be unpowered; route usage still depends on the normal Railgate power evaluation.
- Current Railgate-link cost is 10000 and build-time metadata is `travel_ticks * 2`; construction still completes immediately.

## Trains

- `PreviewPurchaseTrain` and `PurchaseTrain` use backend-owned pricing.
- Train ids must be unique, target nodes must exist, names cannot be blank, and capacity must be positive.
- Train consists are validated by the backend. Current consist ids are `general`, `bulk_hopper`, `liquid_tanker`, `protected`, and `heavy_flat`.
- `general` trains remain universal for existing scenarios and saves. Specialized consists are narrower: bulk cargo needs `bulk_hopper`, liquid cargo needs `liquid_tanker`, electronics/advanced systems need `protected`, and machinery/parts/construction materials need `heavy_flat`.
- Current train cost is `500 + capacity * 20`.
- A purchased train starts idle at its target node.

## Route Schedules

- `PreviewCreateSchedule` and `CreateSchedule` create recurring freight routes from existing infrastructure.
- The train must exist, be idle, and be located at the schedule origin.
- Origin and destination nodes must exist and be different.
- Schedules may include optional intermediate `stops`; the backend resolves the exact route as `origin -> stops... -> destination`.
- A backend route must exist for every segment in the configured stop sequence.
- Specialized trains can only be scheduled or dispatched for compatible cargo. Invalid previews and dispatch blockers report the required consist.
- Units per departure and interval ticks must be positive.
- Units per departure cannot exceed train capacity.
- Clients should let players tune units per departure and interval ticks before sending `PreviewCreateSchedule`; these values are not client constants.
- If `next_departure_tick` is omitted, the backend normalizes it to `state.tick + 1`.
- Preview returns route travel ticks, route stop ids, route segment details, route node ids, route link ids, and a normalized `CreateSchedule` command.
- Preview and create results also return `gate_link_ids`, `gate_handoffs`, and `route_warnings`.
- Railgate handoff context includes endpoint worlds, power state, power shortfall, effective slots, used slots, pressure, disruption reasons, and per-corridor warnings.
- Invalid previews return structured `validation_errors` and per-segment `route_segments` where possible.
- If no operational route exists because a Railgate is unpowered, disrupted, or capacity-blocked, preview remains invalid but may still return structural route context and `blocked_links` so the client can explain the blocker.
- `PreviewUpdateSchedule` and `UpdateSchedule` edit an existing schedule's train, origin, destination, stops, cargo, units, interval, next departure, priority, active flag, and return-to-origin flag through the same backend route and consist validation used by schedule creation.
- Schedule edits are rejected while the schedule's train is actively running that schedule trip. Disable the schedule first to prevent future departures; wait for the active trip to complete before changing route/cargo fields.
- `PreviewDeleteSchedule` and `DeleteSchedule` remove schedules only when no train is currently running that schedule trip.
- Snapshots expose schedule `stops`, `route_stop_ids`, `priority`, and `return_to_origin`; legacy two-node schedules use an empty `stops` list.

## Cargo Flow Visibility

- Snapshots expose `cargo_flows` as route-level visualization data for schedule services.
- Each flow includes service id, schedule id, train id, cargo type, configured stop sequence, resolved route nodes/links, route validity, units per departure, delivered units, in-transit units, trip counts, and active state.
- Flow payloads are read-only visibility data. They do not change dispatch, warehouse, demand, or production rules.
- Godot may draw cargo-flow overlays from `cargo_flows`, but the Python snapshot remains authoritative for route and cargo identity.

## Deferred

- Delayed construction jobs and queue simulation.
- New-world discovery and arbitrary interworld expansion beyond linking existing Railgate anchors.
- Per-tile collision, zoning, terrain costs, and bridge/tunnel rules.
- Dedicated multi-stop route authoring UI with graphical waypoint picking.
