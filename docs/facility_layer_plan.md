# Facility Layer Plan

The third gameplay layer is the facility layer, not the 3D layer. 3D is a presentation mode that should render backend-owned facility state after the rules are proven.

## Layer Stack

- Galaxy layer: worlds, gates, contracts, interworld logistics, macro finance.
- Local planetary layer: local rail, logistics nodes, depots, warehouses, extractors, industries, gate hubs.
- Facility layer: the internal automation of a station, depot, warehouse, industry, extractor, or gate hub.

## Goal

Make station/depot/hub design the place where GateRail becomes more than a rail graph. A player should eventually solve bottlenecks by placing and connecting loaders, unloaders, buffers, platforms, factory blocks, and gate interfaces rather than only placing abstract nodes.

## Backend Concepts

- `Facility`: an internal layout attached to a `NetworkNode`.
- `FacilityComponent`: platform, cargo loader, cargo unloader, storage bay, warehouse bay, extractor head, factory block, power module, gate interface.
- `FacilityPort`: typed input/output connector with cargo type, direction, transfer rate, and capacity.
- `InternalConnection`: a connection between ports inside a facility.
- `FacilitySnapshot`: JSON-safe state exposed to clients for 2D or 3D rendering.

## Rules To Prove First

- Loader/unloader rate limits affect train loading and unloading.
- Buffer/storage component capacity affects whether cargo backs up.
- Factory blocks consume input cargo and emit output cargo through ports.
- Platforms constrain train compatibility, train length, and concurrent loading.
- Gate interfaces constrain local-to-galaxy throughput.
- Power modules and gate modules have explicit power draw.

## Recommended Sprint Sequence

### Sprint 16: Facility Simulation Foundation

- Add facility data models attached to `NetworkNode`.
- Add component, port, and internal connection models.
- Add save/load and snapshot support.
- Add backend preview/build commands for facility components.
- Add tests for loader rate, storage capacity, internal flow, and blocked components.

### Sprint 17: Facility UI Prototype

- Keep this 2D first.
- Selecting a local node opens a facility detail panel or scene.
- Render components as boxes with ports and arrows.
- Allow adding a loader, unloader, buffer, and factory block through backend preview commands.
- Show blocked flow and throughput pressure.

### Sprint 18: 3D Facility View Spike

- Render the same facility snapshot in a Godot 3D scene.
- Start with one depot: rail platform, train placeholder, loader crane, and storage bay.
- Do not add new simulation rules in 3D.
- Use 3D only after the facility contract is stable enough to render consistently.

## Guardrails

- Do not put simulation rules in Godot.
- Do not start 3D before facility data exists.
- Do not replace the local planetary layer; facilities are drilled into from local nodes.
- Keep all facility interactions previewable through Python commands before mutation.
