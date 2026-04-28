# Rail Network Depth Plan

The current local map treats rail links as direct A-to-B edges. That is useful for early backend validation, but it is too flat for the intended game. GateRail needs rail planning to become a real logistics layer: alignments, curves, branches, junctions, signals, train consists, cargo wagons, and underground vacuum tube constraints.

This work should happen alongside the industry expansion, not after it. Deeper industry creates dense yards, specialized cargo flows, and high-throughput factory districts. Those systems need better rail planning to stay readable and interesting.

## Design Goals

- Rails should not look or behave like perfect straight lines unless the player deliberately builds a direct alignment.
- Underground vacuum tubes can be fast and direct, but they still need portals, curve limits, junction costs, maintenance access, and signal/slot control.
- Branches and junctions should matter because industry creates competing cargo flows.
- Signals should explain why trains wait, not become a hidden expert-only system.
- Cargo wagons and train consists should make resource chains more concrete.
- Godot should render and edit rail plans, but Python should own the authoritative geometry, validation, routing, signaling, and train rules.

## Track Geometry

Move from endpoint-only links to explicit alignments:
- `TrackSegment`: one buildable track piece with origin, destination, mode, geometry, travel ticks, capacity, build cost, and maintenance metadata.
- `TrackAlignment`: a list of control points or a simple polyline that the client can render as curved track.
- `TrackNode`: junction, switch, station throat, portal, depot ladder, or signal boundary.

Early geometry can be a polyline with optional curve metadata. It does not need full spline physics immediately.

Validation targets:
- minimum curve radius,
- maximum grade or depth transition for vacuum tubes,
- terrain or underground cost multipliers,
- collision/overlap checks later,
- portal requirements for underground track,
- junction fan-out limits where needed for readability.

## Surface Rail vs Vacuum Tubes

Surface rail:
- cheaper,
- easier to branch,
- more affected by terrain and settlement layout,
- suitable for local industry, yards, and short hauls.

Underground vacuum tubes:
- expensive,
- faster over distance,
- less visually intrusive on the local map,
- should require portals, power, maintenance, and gentler curves,
- should be capacity/signaling constrained because they are enclosed corridors.

Vac tubes should not become magic straight lines. They can be direct, but the player still chooses portals, corridors, and where branch chambers or junctions exist.

## Branches and Junctions

Industry expansion needs branch logic:
- mines branch into sorting yards,
- refineries split outputs to several factories,
- power plants and gate hubs compete for high-value inputs,
- orbital collection stations feed multiple downstream chains.

Backend concepts:
- junction nodes with allowed outgoing paths,
- switch state or route reservations,
- station throats that limit simultaneous arrivals/departures,
- branch construction cost based on geometry and junction type.

First implementation can keep switches abstract: path reservation chooses a route through the junction, and the report explains conflicts.

## Signals

Signals should start simple and diagnostic:
- stop signal: protects a block; only one train may occupy or reserve the protected section.
- path signal: reserves a path through a junction or station throat.
- chain signal or approach signal can wait until needed.

Backend model:
- `Signal` with id, track/junction location, signal kind, protected links or blocks.
- `TrackBlock` as a group of track segments.
- route reservation checks blocks/signals before dispatch.

Player-facing output should say things like:
- blocked by stop signal at `frontier_smelter_west`,
- waiting for path through `core_yard_throat`,
- no clear block to `ore_sorter_2`.

Signals are not just decoration. They should become the player tool for separating dense industry traffic.

## Train Consists and Cargo Wagons

The current train capacity model should evolve into consists:
- locomotive or power unit,
- cargo wagons,
- tanker wagons,
- refrigerated wagons,
- bulk hoppers,
- container flats,
- passenger or crew cars later,
- special shielded/reactor/exotic wagons.

Industry makes wagon specialization useful:
- ore and regolith use bulk hoppers,
- water and fuel use tankers,
- electronics and semiconductors use protected container wagons,
- reactor fuel and exotics require shielded wagons,
- construction modules need heavy flats.

Early implementation can represent a consist as a typed capacity map rather than individual wagon physics. Later UI can show cars visually.

## Route Planning

Routes should support:
- waypoints,
- preferred track modes such as surface rail or vac tube,
- avoid-gate or prefer-gate options,
- cargo-specific wagon compatibility,
- optional multi-stop service for collecting several inputs or dropping at several factories.

Preview results should include:
- selected track geometry,
- travel ticks,
- signal or block conflicts,
- junction warnings,
- cargo/wagon compatibility,
- route bottlenecks,
- normalized command for commit.

## Implementation Sequence Alongside Industry

### Rail Slice R17: Alignment Data

Pair with Sprint 17 resource catalog work.

- Add backend fields for link geometry/control points.
- Persist and snapshot rail alignments.
- Let `PreviewBuildLink` accept optional waypoints.
- Keep pathfinding endpoint-based at first, but render curved/segmented geometry in snapshots.

Status: implemented in Sprint 17A for `NetworkLink.alignment`, save/load, snapshots, built-in scenario metadata, and `BuildLink` / `PreviewBuildLink` parsing. Junctions, branches, signals, and consists remain future slices.

### Rail Slice R18: Branches and Junctions

Pair with Sprint 18 refining/manufacturing.

- Add junction metadata and station-throat concepts.
- Let industry districts have believable branching rail layouts.
- Add route preview warnings for junction pressure.
- Keep switches abstract until traffic needs more detail.

### Rail Slice R19: Signals and Blocks

Pair with Sprint 19 power and gate energy.

- Add stop signals and path signals.
- Add block reservations to dispatch.
- Report signal blockers in freight and traffic outputs.
- Keep the first UI simple: place signal, inspect protected block, see why a train waits.

### Rail Slice R20: Consists and Cargo Wagons

Pair with Sprint 20 space extraction.

- Replace generic train capacity with typed capacity maps or consists.
- Add wagon compatibility for bulk ore, liquids, protected goods, heavy modules, reactor/exotic cargo.
- Make mining output and high-tier industry care about wagon type.

### Rail Slice R21: Rail Planning UI

Pair with Sprint 21 outpost and 2D facility diagnostics.

- Add curved rail planning and waypoint editing in Local Region.
- Render branches, signals, blocks, and train consists.
- Keep all validation through backend preview commands.

## Non-Goals For The Next Slice

- Do not build full signal simulation before the block model exists.
- Do not add detailed train physics or braking curves yet.
- Do not make Godot own routing decisions.
- Do not require per-tile terrain collision for the first alignment pass.
- Do not let visual curve drawing diverge from backend travel-time and cost rules.
