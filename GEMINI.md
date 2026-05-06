# Gate Horizons / Gate Rail Agent Instructions

You are assisting with a Python prototype for a logistics/automation game inspired by OpenTTD, Factorio, Dyson Sphere Program, and wormhole rail networks.

## Core Concept

The game is about building industrial rail logistics across worlds connected by directional wormhole gates.

Primary pillars:
- Galaxy map
- Local region map
- Industrial production chains
- Train routing
- Warehouses and receiving docks as active logistics buffers
- Directional wormhole gates
- One-way rail approaches and dense yards
- Future 3D station/depot/hub placement layer

## Design Rules

Do not drift into generic sci-fi city builder design.

Respect these locked concepts:
- Wormhole gates are 1:1 links unless explicitly modelled otherwise.
- The outbound/source gate powers the aperture.
- The receiving gate is an exit/anchor.
- Reciprocal travel requires a separate active route or explicit activation.
- Directed rail is allowed.
- Local region routes should make wrong-way track and no-safe-path reasons visible.
- Warehouses are active logistics buffers, not passive cargo boxes.
- Receiving docks/platforms matter through unload rate, storage target, and blocked reason.
- Player should control stock targets, priorities, pull/push rules, and train services.
- Projects request materials: outposts, power plants, orbital yards, gate upgrades, factories, and facilities.

## Coding Rules

- Prefer simple, readable Python.
- Preserve existing architecture unless clearly broken.
- Do not rewrite the whole project without explicit instruction.
- Before editing, identify the exact files you intend to change.
- Prefer small, testable implementation slices.
- Add or update tests when changing behaviour.
- Avoid hidden magic.
- Keep simulation logic separate from UI rendering where possible.

## Output Rules

When proposing implementation work, return:
1. Changed files
2. Purpose of each change
3. Risk level
4. Test plan
5. Exact next command to run

When implementing:
- Do not delete existing features unless explicitly asked.
- Do not silently change data schemas.
- If schema changes are required, explain migration impact.
