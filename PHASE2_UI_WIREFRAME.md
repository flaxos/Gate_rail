# Phase 2 UI Wireframe Summary

Source: Claude Design handoff bundle, `GateRail Stage 2 — Client Wireframe`.

The HTML wireframe recommends a practical progression from the current Godot scaffold toward a complete operations client.

## Recommended Layout Direction

Start with Layout A: "sim-classic, all panels visible".

Why:
- It matches the current Godot scaffold.
- It keeps map, schedules, contracts, dispatch, orders, HUD, and alerts visible without requiring a complex selection system.
- It is the safest path for Sprint 10 and Sprint 11.

Future direction:
- Move toward Layout B once construction needs more map space.
- Keep Layout C as a north star for later contextual inspection and construction mode.

## Required Panels

- Main map view:
  - worlds, nodes, links, trains,
  - rail vs gate distinction,
  - disruption/congestion visual state,
  - future entity click inspection.

- Top HUD:
  - tick,
  - cash,
  - net this tick,
  - reputation,
  - bridge state,
  - pause/play/step controls.

- Schedules:
  - generated from `schedules[]`,
  - active/inactive status,
  - train, cargo, route, next departure,
  - toggle sends `SetScheduleEnabled`.

- Contracts:
  - generated from `contracts[]`,
  - progress, due tick, reward/penalty,
  - active/fulfilled/failed state.

- Dispatch:
  - train, origin, destination, cargo, units, priority, order id,
  - sends `DispatchOrder`.

- Pending orders:
  - generated from active `orders[]`,
  - cancel sends `CancelOrder`.

- Alert/status strip:
  - last command result,
  - bridge errors,
  - future congestion and disruption chips.

## Build Order

Slice 1:
- HUD, map, schedule toggles, bridge status.

Slice 2:
- Dispatch, pending orders, contracts, finance and reputation.

Slice 3:
- Selection and inspection polish.
- Contract click focuses relevant world/link/route.
- In-transit train visibility.
- Congestion and power overlays.

Slice 4:
- Construction slice 1 hooks for stations and rail.

Slice 5:
- Gate construction, train purchase, schedule creation.

## Current Implementation Status

Already implemented in the Godot scaffold:
- live `--stdio` snapshot request on startup,
- bridge status panel,
- Play/Pause auto-run backed by repeated `ticks:1` bridge messages,
- generated schedule list and schedule toggles,
- finance/reputation panel,
- contract list,
- dispatch form,
- pending-order list with cancel buttons,
- placeholder SVGs on map entities and primary action buttons,
- alert/status strip with command history, bridge errors, disruption chips, and congestion chips,
- click selection and inspector details for worlds, nodes, links, and trains,
- clearer map overlays for link capacity, rail/gate mode, selected entities, and in-transit trains,
- responsive fullscreen layout with anchored side panels, a bottom status strip, and a computed center map region.

Remaining before Sprint 11 is considered playable:
- Sprint 11 is playable for existing scenarios. The remaining work is construction: node placement, rail laying, warehouses/depots, local industry flow, gate expansion, train purchase, and schedule creation.

## Local Region Construction (pre-Sprint-12 scaffold)

Source: Claude Design handoff archived at `docs/design_handoff/local_region_construction/` (`README.md`, `Local Region Construction.html`, `GateRail Wireframe.html`, `chats/chat1.md`).

The Local Region scene is a second Godot scene (`godot/scenes/local_region.tscn` + `godot/scripts/local_region.gd`) that the player drills into from the galaxy map by selecting a world and pressing **View Local Region** in the inspector. Both scenes share the `GateRailBridge` autoload; the new `SceneNav` autoload carries `selected_world_id` across the scene change.

### Panel structure

- **Topbar (56px):** brand mark, breadcrumb `GALAXY › <sector> › <world> · LOCAL`, stat chips for Credits / Power / Tick, **Galaxy Map** back button.
- **Left tool rail (64px):** Select (V), Pan (H), Lay Rail (R), Place Node (N), Gate Hub (G), Train (T), Demolish (X), Layers (L). Active tool gets the amber highlight from the design palette. Early command wiring exists; Sprint 13 must harden it with backend-owned preview/validation feedback before treating it as playable construction.
- **Center canvas:** dark-blue gradient wash with a 24px micro / 120px major grid, corner bracket frames, edge tick ruler, compass rosette, scale bar, and a region label `LOCAL REGION · NN / <WORLD> · <BIOME>`. Nodes for the selected world are drawn at deterministic orbit positions with kind-specific glyphs (hex extractor, square industry, wide-rect depot, house settlement, amber triple-ring gate hub). Links render as straight steel-gray lines.
- **Right HUD (360px):**
  - Planet card — name, tier label, population, stability bar.
  - Local Inventory — aggregated `inventory` totals across the world's nodes with per-item rate (`production - demand`) and a `→ gate N/t` hint when cargo flows through a gate link from this world.
  - Gate Throughput — slot capacity (`slots_used / slot_capacity`), linked-to destination, power draw. Per-cargo bars remain deferred until gate slot cargo accounting is modeled.
  - Construction Queue — "No pending construction" placeholder. Real queue entries are deferred until delayed construction jobs are implemented.
- **Bottom status bar (44px):** mode chip (e.g. `RAIL MODE · drag from source node` once Sprint 13 wires it; neutral otherwise), bridge LIVE/OFFLINE chip, hotkey reminder strip.

### Interaction model (target — Sprint 13 deliverable)

- **Drag-to-connect rails:** click source node, drag to target. Ghost path shows segment length, material, backend-provided build cost, power draw, build time, valid/invalid chip from the design HTML.
- **Snap-lock:** ghost endpoints snap to the nearest valid node within a small radius.
- **Tooltip fields** match the HTML wireframe verbatim so the visual design and the live UI stay in lockstep.
- **Gate Hub CTA:** the "Link to Galaxy Network" button on a placed gate hub returns to the galaxy scene with the chosen destination preselected.

### Palette / typography

Deep blue base `#0b1522`/`#1e3a5f`, steel `#95a5a6`, amber `#f39c12`/`#ffc15e`, green `#2ecc71`, red `#e74c3c`, cyan `#58c6d8`. Display: Orbitron (fall back to Godot defaults if unbundled). Data/stats: JetBrains Mono. Body: Chakra Petch.
