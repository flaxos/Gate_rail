# Phase 2 Plan

## Purpose

Phase 2 proves that GateRail can become a playable 2D prototype without rewriting the Python simulation. The Godot client is a view and input layer. The Python fixed-tick backend remains authoritative for logistics, contracts, finance, progression, routing, train movement, Railgate power, and snapshots.

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
- Treat station/depot/hub 3D as presentation over a backend-owned facility layer. Do not begin a 3D facility scene until facilities, components, ports, and internal flow exist in Python snapshots.
- Treat the deeper industry game as higher priority than 3D. Do not begin a 3D facility scene until elemental resources, refining/manufacturing chains, power/Railgate energy inputs, space extraction, outpost logistics, and 2D diagnostics are proven.
- Treat curved rails, branches, signals, vacuum tubes, train consists, and cargo wagons as backend-owned systems that should mature alongside industry. Godot may edit and render track plans, but Python owns validation, routing, signaling, and wagon compatibility.

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
- construction rules for buildable node roles: extractor, industry, depot, warehouse, settlement connector, and Railgate anchor (`gate_hub`).
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
  - **Left tool rail (64px):** Select (V), Pan (H), Lay Rail (R), Place Node (N), Railgate (G), Train (T), Demolish (X), Layers (L). Sprint 13 wires each tool to its backend command.
  - **Center canvas:** dark-blue grid wash + corner brackets + compass + scale bar + region label. Sprint 13 adds drag-to-connect ghost path with snap-lock and cost tooltip on the rail tool.
  - **Right HUD (360px):** planet card, local inventory, Railgate throughput, construction queue placeholder until delayed build jobs exist.
  - **Bottom status bar (44px):** mode chip, bridge LIVE/OFFLINE chip, hotkey reminders.

Deliverables:
- tool-rail buttons emit real `BuildNode` / `BuildLink` / `DemolishLink` / `PurchaseTrain` commands via the bridge.
- drag-to-connect interaction: ghost path between source/target with snap-lock, segment length, build cost, power draw, build time, valid/invalid chip.
- backend-owned cost preview tooltip and validation feedback (matches the HTML design without duplicating simulation rules in Godot).
- construction queue panel remains placeholder until delayed build jobs are implemented.
- "Link Corridor" button on the Railgate anchor returns to the corridor map with the chosen destination preselected.
- immediate redraw from returned snapshots.

Exit criteria:
- the player can add rail infrastructure to the benchmark scenario from the Local Region scene and see it affect routing.

Slice 13A completed state:
- Backend preview commands now exist for node and rail construction: `PreviewBuildNode` and `PreviewBuildLink`.
- Preview commands return valid/invalid feedback, cost, build time, normalized build commands, and do not mutate cash or map state.
- Built nodes persist local layout coordinates through save/load and render snapshots.
- Rail links can derive travel ticks from persisted local layout when the client omits a manual travel time.
- Local Region construction uses a preview-then-commit flow for nodes, Railgate anchors, and same-world rail, so Godot no longer hardcodes node or rail construction costs.

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

Slice 14A completed state:
- Depots and warehouses push buffered inventory across same-world rail links to neighbouring demand within their per-tick transfer budget.
- Buffer distribution is reported and exposed in snapshots for local inspection.

Slice 14B completed state:
- Node transfer usage, pressure, and saturation streaks are tracked and exposed in snapshots.
- The Local Region inspector can flag transfer bottlenecks.

Slice 14C completed state:
- `NodeRecipe` gives individual nodes explicit input/output transformations.
- `node_recipes` runs as a fixed tick phase after buffer distribution and before demand consumption.
- Recipe input shortages are tracked on state and exposed in snapshots.
- Buffer pull includes declared demand plus recipe inputs, so depot/warehouse flow can feed industry recipes.
- Tests cover recipe success, missing inputs, storage clamping, snapshot recipe fields, full simulation phase ordering, and the extractor-to-industry chain.

Slice 14D completed state:
- The Local Region `LAYERS` toggle renders supply, demand, inventory/storage pressure, shortages, recipe-blocked inputs, and transfer pressure from backend snapshot data.
- The right HUD has a `Local Overlays` summary/legend so overlay state is understandable without relying only on map glyphs.
- This keeps the client presentation-only: Godot reads `production`, `demand`, `inventory`, `shortages`, `recipe_blocked`, `storage`, and `transfer_pressure` rather than duplicating logistics rules.

## Sprint 15: Gate Expansion, Trains, and Schedule Creation

Goal:
- connect local track networks to interworld Railgate logistics.

Deliverables:
- backend commands for Railgate anchors and links.
- train purchase/build command.
- schedule creation command.
- Godot UI for Railgate construction, train purchase, and schedule creation.
- clear cost, power, capacity, and route feedback.

Exit criteria:
- the player can expand an existing network with rail, warehouses/depots, Railgates, trains, and schedules from Godot.

Slice 15A completed state:
- Backend previews/builds explicit Railgate links via `BuildLink(mode="gate")` between existing Railgate endpoints on different worlds.
- Railgate previews include normalized commands, cost, travel, capacity, endpoint world context, power source, power draw, available power, shortfall, and powered-if-built state.
- The Local Region Railgate tool now supports two flows: empty click previews a local Railgate endpoint, existing endpoint click previews an interworld Railgate link to an available external endpoint.
- The Railgate Throughput HUD now distinguishes missing, unlinked, and linked corridor states.
- Tests lock Railgate defaults, validation, build mutation, snapshot fields, and power-shortfall preview behavior.

Slice 15B completed state:
- Schedule preview/create results now include backend-owned Railgate handoff context for routes that cross Railgates.
- Route context includes gate link ids, endpoint world labels, power state, power shortfall, slot capacity, slot usage, pressure, disruption reasons, and route warnings.
- Invalid previews caused by unpowered Railgates can still return structural corridor context, making blockers explainable in the client.
- The Local Region Build Planner renders Railgate handoff and warning context during route preview.
- Tests cover normal, saturated, degraded, unpowered, and create-result route handoff cases.

Slice 15C completed state:
- Local Region route creation exposes unit and interval tuning before `PreviewCreateSchedule`.
- The route-tuning popup is shown after cargo selection and is bounded by backend-relevant constraints such as train capacity.
- Backend tests lock tuned units/interval through preview normalization, create persistence, and invalid value rejection.
- Sprint 15 is complete against the current plan; further schedule work should be treated as polish or a later schedule-management sprint.

## Sprint 16: Facility Simulation Foundation

Goal:
- create the backend contract for station/depot/hub internals before any 3D view.

Deliverables:
- facility data models attached to `NetworkNode`.
- component models for platforms, loaders, unloaders, storage bays, factory blocks, power modules, and gate interfaces.
- typed input/output ports and internal facility connections.
- save/load and snapshot support for facilities.
- backend preview/build commands for facility components.
- tests for loader rate, storage capacity, internal cargo flow, and blocked components.

Exit criteria:
- a depot or industry can have internal components whose throughput constraints affect loading, unloading, buffering, or recipe output.

## Sprint 17: Elemental Resource Backbone

Goal:
- turn the compact cargo model into a backend-owned resource catalog and deposit model before building more presentation.

Deliverables:
- resource definitions with stable ids, categories, and metadata for raw sources, refined elements, industrial materials, manufactured goods, advanced systems, and exotics.
- a first playable subset for raw ore, refined materials, electronics, semiconductors, reactor inputs, and aperture control components.
- world deposit metadata with grade/yield and deterministic save/load.
- CLI inspection and snapshot fields for deposits and available resources.
- rail sidecar: optional link alignment waypoints/control points persisted and exposed in snapshots so local track is no longer only straight A-to-B.
- tests for catalog parsing, deposit persistence, and snapshot/report stability.

Exit criteria:
- a scenario can explain why a location matters because of specific deposits and resource-chain potential, not only generic cargo, and the local map can render backend-owned non-straight rail geometry.

Implemented slice 17A:
- added the resource catalog and deposit model, with save/load, snapshots, and CLI inspection.
- seeded built-in scenarios with deposits and local rail alignment metadata.
- added rail alignment parsing to build/preview link commands and deterministic tests for the new contracts.

Implemented slice 17B:
- added node-owned resource inventories, resource recipes, deposit-backed extraction, local resource distribution, and blocked resource recipe reporting.
- seeded the default playtest with a narrow ore/carbon -> iron -> aperture control components chain.
- persisted and snapshotted resource recipes, inventories, deposit ids, and blockers.

## Sprint 18: Refining and Manufacturing Chains

Goal:
- add the first deep industry loops from raw sources to refined materials, parts, electronics, semiconductors, and advanced components.

Deliverables:
- smelting/refining recipes.
- alloying, chemistry, and semiconductor preparation recipes.
- manufacturing recipes for parts, electronics, construction modules, reactor parts, and aperture control components.
- facility component or typed factory-block support for smelters, refineries, fabricators, electronics assemblers, and semiconductor lines.
- reports and snapshots that identify missing inputs and blocked processing stages.
- rail sidecar: branch/junction metadata and station-throat warnings for dense industry districts.

Exit criteria:
- the player can improve a local world's industrial output by connecting extraction, refining, and manufacturing rather than only hauling generic cargo.

Implemented slice 18:
- added typed resource recipe kinds for smelting, refining, electronics assembly, semiconductor work, and fabrication.
- expanded the default playtest from ore/carbon -> iron -> aperture control components into silica/copper/silicon/electronics/semiconductors feeding aperture control components.
- added resource branch-pressure warnings to reports and snapshots for dense industry rail clusters.

## Sprint 19: Power and Gate Energy Economy

Goal:
- make power generation and gate operation depend on resource chains.

Deliverables:
- power plant models or facility components.
- fuel, reactor fuel, coolant, capacitor, and gate-efficiency inputs.
- gate charge or operating-energy state.
- reports and snapshot fields explaining power blockers and gate energy burden.
- rail sidecar: stop signals, path signals, protected blocks, and signal/block blocker reports.

Exit criteria:
- gate availability can be improved through upstream mining, refining, manufacturing, and power construction.

Implemented slice 19:
- added resource-backed Railgate support that reduces effective Railgate power draw when a support node has required resource-chain output.
- added a `sprint19` scenario where `gate_frontier_outer` stays underpowered until aperture control components are fabricated.
- persisted and snapshotted support requirements, support shortages, base/effective power draw, and resource bonuses.
- implemented the R19 rail sidecar first slice: backend stop/path signals, one-link protected blocks, dispatch-time signal-block queueing before cargo load, JSON build/preview commands, save/load, snapshots, freight queue reasons, traffic alerts, and text reports.

Power-generation placement:
- implemented the Sprint 19B / Sprint 20A backend foundation before full space extraction: node-attached power plants, resource input consumption, generated-power rollups, missing-input blockers, and gate evaluation that uses generated capacity.

## Sprint 20: Space Extraction and Outpost Logistics

Goal:
- use Railgate corridors and orbital infrastructure to access remote raw resources while keeping Python authoritative.

Deliverables:
- remote extraction sites such as belts, moons, debris fields, gas pockets, and anomalies.
- fixed-tick mining missions with travel time, yield, return node, and fuel/power requirements.
- orbital yards and collection stations that connect returned cargo to rail/gate logistics.
- outpost construction projects requiring delivered cargo.
- rail sidecar: train consists or typed capacity maps for bulk ore, liquids, protected goods, heavy modules, reactor materials, and exotic cargo.

Exit criteria:
- a player can build access to a remote resource, run mining missions, and feed the result into the industrial chain.

## Sprint 21: 2D Facility and Industry Diagnostics

Goal:
- expose facilities, resource-chain blockers, and outpost projects in 2D before any 3D view.

Deliverables:
- local node drill-in to a facility detail panel or scene.
- component boxes, ports, internal cargo-flow arrows, and blocked-flow readouts.
- build-preview UI for loaders, unloaders, buffers, smelters, refineries, fabricators, semiconductor lines, power modules, and gate interfaces.
- overlays or inspectors for resource availability, processing blockers, power blockers, and outpost construction needs.
- grid-snap affordances for local node and gate-hub placement previews.
- a text-first resource relationship atlas for ores, parts, processing nodes, power, gates, and remote sites.
- internal wiring logic that moves cargo between specific facility ports and exposes port buffers in snapshots.
- a Local Region wiring tool that previews backend-owned internal connections and renders visual facility flow.
- local rail planning UI for curved alignments, waypoint edits, branches, signals, protected blocks, vacuum-tube portals, and consist/cargo compatibility.

Exit criteria:
- the player can diagnose and improve an industrial, rail, power, or outpost bottleneck from the 2D client.

Implemented Sprint 22-24 transport/flow slices:
- directional gate links can model source-to-exit apertures while preserving bidirectional legacy gates.
- train consists validate cargo compatibility for schedule previews, schedule creation, and runtime dispatch.
- schedules can resolve ordered intermediate stops and return per-segment route debug, including blocked links for unpowered gates, disrupted links, and full capacity.
- snapshots expose `cargo_flows` for schedule services, including route stops, resolved nodes/links, active state, in-transit units, delivered units, and trip counts.
- Godot draws cargo-flow overlays from backend snapshot data and surfaces route segment blockers in planner/status context.

## Sprint 25: Schedule And Flow Management

Goal:
- make the richer schedule/flow model editable from the bridge and Godot without duplicating route rules in the client.

Deliverables:
- backend preview/apply commands for editing existing schedules.
- backend preview/apply commands for deleting schedules safely.
- edit validation for stops, cargo, units, interval, active state, consist compatibility, train readiness, and route availability.
- route-segment blocker payloads reused for edit previews.
- Godot schedule-row controls for active state, cargo, units, interval, intermediate stops, preview, apply, and delete.
- cargo-flow overlays and command alerts that make invalid schedule edits explainable.

Exit criteria:
- a player can inspect current cargo flows, preview schedule edits, apply safe edits, and delete idle schedules from Godot while Python remains authoritative for every route and cargo rule.

Implemented Sprint 25 completed state:
- `PreviewUpdateSchedule` / `UpdateSchedule` merge partial edits with the existing schedule, normalize a full backend command, validate route stops and consist compatibility, and return the same route segment/gate handoff context as creation previews.
- `PreviewDeleteSchedule` / `DeleteSchedule` remove idle schedules and reject deletion while a train is actively running that schedule trip.
- schedule snapshots now include `priority` and `return_to_origin` alongside `stops` and `route_stop_ids`; `cargo_flows` disappear automatically when a schedule is deleted.
- the Godot bridge exposes schedule preview/update/delete helpers, and the main operations panel can preview/apply cargo, units, interval, active-state, and stop-list edits.
- invalid schedule edit previews push route-segment and blocked-link explanations into the status strip.

## Sprint 26: Save/Load And Scenario Testbeds

Goal:
- make playtest iteration practical from Godot and provide contrasting built-in worlds for early construction versus large industrial stress tests.

Deliverables:
- rudimentary stdio bridge save and load messages that reuse the existing JSON persistence format.
- bridge scenario reset messages for swapping playtest presets without restarting the Python backend process.
- an `early_build` preset for sparse, low-cash first-route and construction testing.
- an `industrial_expansion` preset for large connected industry, power, gate support, and multi-stop schedule testing.
- Godot Galaxy Map controls for save path, Save Game, Load Game, and scenario reset.

Exit criteria:
- a player can save, load, or swap the live simulation from Godot while Python remains authoritative, and can compare a compact early build state against a larger interconnected industrial world.

Implemented Sprint 26 completed state:
- the JSON bridge accepts `save_path`, `load_path`, and `scenario` frames; load/scenario requests replace the live `TickSimulation` state in-place before command/tick processing, and saves happen after requested ticks.
- bridge responses include `saved_path`, `loaded_path`, or `loaded_scenario` metadata for client status text.
- `early_build` seeds two worlds, limited cash/materials, one starter train, and one inactive food route for early route/build tests.
- `industrial_expansion` layers Cinder Forge and Helix Research Reach onto the Sprint 20 baseline with extra gates, rail branches, deposits, recipes, power plants, gate support, specialized trains, and multi-stop services.
- the Godot bridge exposes `save_game`, `load_game`, and `load_scenario`; `main.gd` adds a compact scenario selector and save/load row to the Galaxy Map control panel.

## Sprint 27: Remote Operations Hardening

Goal:
- make mining mission and outpost operations dependable enough to feed the normal rail/gate/resource chain.

Implemented Sprint 27 completed state:
- mining mission previews and dispatches use backend-computed fuel and power requirements when the client omits explicit values, so free launches are rejected.
- previews report missing fuel, power shortfall, invalid site, bad launch/return node, expected yield, return capacity, and normalized dispatch commands.
- mission completion can return either resource-catalog units into `resource_inventory` or train-haulable cargo into `inventory` via optional `SpaceSite.cargo_type`.
- Local Region previews mining missions before dispatch and shows fuel, power, yield, return-space, and haul-bucket context from backend command results.
- outpost bootstrap remains backend-owned through preview/build construction projects and delivered-cargo completion.

## Sprint 28: Mining-To-Manufacturing Payoff Loop

Goal:
- prove the real early gameplay loop: mine ore remotely, haul it by train, smelt it, fabricate parts, deliver those parts to a settlement, and earn rewards that can fund further expansion.

Implemented Sprint 28A/28B plus backend payoff state:
- `mining_to_manufacturing` / `mining_loop` is a built-in scenario with a frontier spaceport, collection station, powered gate, core smelter, manufacturing yard, frontier settlement, bulk ore train, heavy-flat parts train, and paid settlement contract.
- the automated loop test dispatches the mission, activates schedules, verifies ORE leaves the collection station, METAL is produced at the smelter, PARTS and construction materials are fabricated at the yard, PARTS reach the settlement, and the contract pays cash/reputation.
- mission previews now return `site_cargo_type`, `site_resource_id`, `haul_bucket`, and `haul_label`, and Local Region renders cargo-vs-resource badges in the site list and mission planner.
- snapshots expose backend-owned `scenario_catalog` and `cargo_catalog` payloads; Godot scenario/cargo selectors consume those catalogs instead of maintaining parallel hardcoded registries.

Remaining Sprint 28 work:
- add a Local Region one-click workflow for queuing the haul run around mission return timing.
- surface the new haul and settlement-delivery services as clearer cargo-flow overlays and alert chips.

## Sprint 29: Tutorial Start And Loop Usability

Goal:
- provide a generous six-world tutorial start and decide what is backend-complete versus still needing client workflow polish.

Implemented Sprint 29A state:
- `tutorial_six_worlds` / `tutorial_start` is a built-in scenario with six stocked worlds in a powered gate ring.
- each world has two Railgate links to two neighbouring worlds, plus local depots, colony logistics hubs, Railgate anchors, and construction stock.
- active tutorial schedules move ORE to a smelter, METAL to a factory, and PARTS to a settlement contract that pays cash/reputation.
- `saves/tutorial_six_worlds.json` is generated from the scenario for immediate Godot load/save testing.

Implemented Sprint 29B state:
- snapshots expose a backend-owned `tutorial` object for the six-world starter loop.
- tutorial steps report active/pending/complete state, delivered/target cargo, route endpoints, contract reward cash, and reward reputation.
- Godot renders the tutorial checklist and status alert chip from the snapshot contract.
- Godot does not hardcode the tutorial schedule IDs or own loop completion rules.

Manual playtest correction:
- tutorial schedules start disabled, so Play advances time without automatically solving ore, metal, and parts delivery.
- the six-world tutorial map uses circular backend-owned world positions.
- map selection feeds the one-shot dispatch form: train selection fills train/pickup, node selection fills pickup/dropoff, and cargo/units are inferred from origin stock plus destination demand, recipe inputs, or active contracts.

Current playability assessment:
- backend loop is feature-complete enough to run deterministic cargo loops, gate routing, train schedules, recipe processing, settlement delivery contracts, rewards, save/load, and scenario swapping.
- Godot can load scenarios/saves, inspect entities, click-fill and issue one-shot orders, toggle schedules for automation, preview construction, view Local Region diagnostics, and follow the six-world tutorial loop from a backend-provided checklist.
- remaining work is usability polish rather than core-rule invention: richer cargo-flow overlays, one-click mission/haul workflow, and clearer schedule creation from successful manual routes.

## Deferred: 3D Facility View Spike

Goal:
- prove Godot can render a facility snapshot in 3D without owning simulation rules after the core industry loop is stable.

Deliverables:
- one 3D depot or factory scene rendered from backend facility snapshot data.
- rail platform, train placeholder, loader crane, storage bay, and one processing line.
- read-only first pass unless the 2D facility UI contract is already stable.

Exit criteria:
- the 3D scene visually matches the same backend facility state as the 2D facility view.

## Deferred Until After Core Industry

- new world creation.
- re-specialization of worlds.
- rival operators.
- tech tree.
- detailed signal/block simulation.
- 3D facility presentation.

## Interactive Cadence

Each Phase 2 sprint should end with:
- a runnable Godot scene or backend bridge smoke command,
- a short playtest note stating what can be seen and controlled,
- tests for every backend command or bridge contract changed,
- a decision on whether the slice is understandable enough before increasing construction scope.
