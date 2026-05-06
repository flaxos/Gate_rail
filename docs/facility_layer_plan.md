# Facility Layer Plan

The third gameplay layer is the facility layer, not the 3D layer. 3D is a presentation mode that should render backend-owned facility state after the rules are proven.

## Layer Stack

- Galaxy layer: worlds, Railgate corridors, contracts, interworld logistics, macro finance.
- Local planetary layer: local rail, logistics nodes, depots, warehouses, extractors, industries, Railgate anchors, and receiving terminals.
- Facility layer: the internal automation of a station, depot, warehouse, industry, extractor, or Railgate endpoint.

## Goal

Make station/depot/hub design the place where GateRail becomes more than a rail graph. A player should eventually solve bottlenecks by placing and connecting loaders, unloaders, buffers, platforms, smelters, refineries, fabricators, semiconductor lines, power modules, and Railgate interfaces rather than only placing abstract nodes.

## Backend Concepts

- `Facility`: an internal layout attached to a `NetworkNode`.
- `FacilityComponent`: platform, cargo loader, cargo unloader, storage bay, warehouse bay, extractor head, crusher, sorter, smelter, refinery, chemical processor, fabricator, electronics assembler, semiconductor line, factory block, reactor, capacitor bank, power module, Railgate interface.
- `FacilityPort`: typed input/output connector with cargo type, direction, transfer rate, and capacity.
- `InternalConnection`: a connection between ports inside a facility.
- `FacilitySnapshot`: JSON-safe state exposed to clients for 2D or 3D rendering.

## Rules To Prove First

- Loader/unloader rate limits affect train loading and unloading.
- Buffer/storage component capacity affects whether cargo backs up.
- Factory blocks consume input cargo and emit output cargo through ports.
- Industrial components turn raw sources into refined elements, industrial materials, parts, electronics, semiconductors, advanced components, and Railgate aperture inputs.
- Platforms constrain train compatibility, train length, and concurrent loading.
- Railgate interfaces constrain local-to-galaxy throughput.
- Power modules and Railgate modules have explicit power draw and eventually consume fuel, reactor inputs, charge, or advanced components.

## Recommended Sprint Sequence

### Sprint 16: Facility Simulation Foundation

- Add facility data models attached to `NetworkNode`.
- Add component, port, and internal connection models.
- Add save/load and snapshot support.
- Add backend preview/build commands for facility components.
- Add tests for loader rate, storage capacity, internal flow, and blocked components.

### Sprint 17: Resource and Industry Backbone

- Add a data-driven resource catalog that can grow beyond the current cargo enum.
- Model raw sources, refined elements, industrial materials, manufactured goods, advanced systems, and discoverable exotics.
- Add ore/deposit metadata for grade, yield, and world or remote-site availability.
- Keep the first implementation small enough to test through CLI reports.

### Sprint 18: Processing and Manufacturing Chains

- Expand facility processing beyond generic factory blocks.
- Add smelting/refining recipes from raw ore to refined elements or bulk materials.
- Add manufacturing recipes for parts, electronics, semiconductors, and construction modules.
- Add blocked-flow reporting that explains which stage, input, or facility component is limiting production.

### Sprint 19: Power and Railgate Energy Economy

- Add power-plant facility components and recipes.
- Convert selected fuel/reactor inputs into world power capacity or Railgate charge.
- Make Railgate operation and high-throughput corridor use depend on power infrastructure and advanced inputs.
- Status: Railgate-efficiency support landed in Sprint 19, and the backend power-generation foundation landed as Sprint 19B / Sprint 20A before remote mining missions require fuel or power. Facility UI and richer plant component editing remain later work.

### Sprint 20: Space Extraction and Outpost Logistics

- Add remote extraction sites such as belts, moons, debris fields, gas pockets, and anomalies.
- Model mining ships as fixed-tick logistics missions rather than real-time piloting.
- Add orbital yards or collection stations that receive mission output and connect back to rail/Railgate logistics.
- Make outpost and collection-station construction require delivered cargo, not only cash.

### Sprint 21: Facility UI Prototype

- Keep this 2D first.
- Selecting a local node opens a facility detail panel or scene.
- Render components as boxes with ports and arrows.
- Allow adding loaders, unloaders, buffers, smelters, refineries, fabricators, semiconductor lines, power modules, and Railgate interfaces through backend preview commands.
- Show blocked flow and throughput pressure.
- Status: Sprint 21D implemented backend-owned internal wiring flow for specific facility ports, port-buffer persistence/snapshots, and a Godot Local Region wire tool with a 2D drill-in flow panel.

### Deferred: 3D Facility View Spike

- Render the same facility snapshot in a Godot 3D scene.
- Start with one depot: rail platform, train placeholder, loader crane, and storage bay.
- Do not add new simulation rules in 3D.
- Use 3D only after the resource, processing, power, space-extraction, and 2D facility contracts are stable enough to render consistently.

## Guardrails

- Do not put simulation rules in Godot.
- Do not start 3D before facility data, resource chains, power rules, and remote extraction loops exist.
- Do not replace the local planetary layer; facilities are drilled into from local nodes.
- Keep all facility interactions previewable through Python commands before mutation.
