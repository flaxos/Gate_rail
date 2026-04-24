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
- generated schedule list and schedule toggles,
- finance/reputation panel,
- contract list,
- dispatch form,
- pending-order list with cancel buttons,
- placeholder SVGs on map entities and primary action buttons,
- alert/status strip with command history, bridge errors, disruption chips, and congestion chips.

Remaining before Sprint 11 is considered playable:
- play/pause auto-step,
- stronger map readability and in-transit train interpolation,
- selected entity inspector.
