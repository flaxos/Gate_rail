# Game Vision

## Premise

GateRail is a logistics and development game set in a future where trains have re-emerged as the dominant infrastructure for moving people and freight at scale. Advances in tunneling, mag-rail, vacuum transit, cargo handling, and wormhole technology have made rail networks the backbone of civilization again.

The player expands from local rail systems to inter-world logistics networks, building frontier worlds into major industrial, civic, and research centers. Wormholes are not a replacement for logistics planning. They are strategic infrastructure that compresses distance at a major energy cost.

## Player fantasy

The game should support all three of these fantasies at once:
- railroad tycoon across impossible space,
- industrial optimizer chaining extraction, production, and delivery,
- frontier builder restoring and growing worlds into higher-tier civilizations.

## Player optimization targets

The player is optimizing:
- throughput across rail and gate networks,
- world development and promotion,
- supply stability under growing complexity,
- strategic use of expensive wormhole power,
- economic scaling through specialization and interdependence.

## Distinctive hook

GateRail is defined by the interaction between:
- trains as the main physical logistics layer on each world,
- wormholes as high-cost topology-changing infrastructure,
- worlds as evolving economic actors rather than static maps,
- recursive expansion where mature worlds help bootstrap frontier worlds.

This should feel different from a conventional rail sim because the objective is not only route profit or station coverage. The player is building a multi-world civilization network.

## World model

Each world has:
- a development tier,
- a population and stability state,
- local resources and environmental constraints,
- import requirements,
- potential specializations,
- transport infrastructure,
- power availability.

Suggested starting tier ladder:
- `Tier 0 Outpost`: survival phase, imports most needs
- `Tier 1 Frontier Colony`: basic extraction and processing
- `Tier 2 Industrial Colony`: refining, manufacturing, stronger freight demand
- `Tier 3 Developed World`: advanced industry and research
- `Tier 4 Core World`: mega-city, mega-industry, major network anchor

Promotion should depend on sustained fulfillment of requirements, not one-time construction alone.

## Transport model

Transport should be modeled in layers:
- local rail between mines, farms, refineries, factories, depots, and population centers,
- long-haul rail on dense developed worlds,
- gate hubs for near-instant inter-world movement,
- optional space lanes or orbital transfer nodes later if needed.

For the backend MVP, train simulation should stay operational rather than hyper-physical:
- trains have capacity, speed, route assignment, and cargo specialization,
- stations have load and unload limits,
- links can express travel time and congestion,
- detailed block signaling can wait until the game proves it needs it.

## Wormholes in gameplay terms

Wormholes are player-built or player-activated infrastructure edges that:
- consume large amounts of power,
- greatly reduce effective travel time,
- relieve distance-driven bottlenecks,
- create strategic decisions around where to place gate hubs,
- should never feel free.

Wormholes solve logistics problems, but they also create new ones through energy demand and hub concentration.

## Resource categories

The first resource model should use a limited set of meaningful categories:

- bulk solids:
  - ore
  - carbon feedstock
  - stone
  - biomass
- energy carriers and utilities:
  - water
  - fuel
  - coolant
  - power as a network requirement rather than a wagon cargo in most cases
- industrial goods:
  - metal
  - parts
  - electronics
  - construction materials
- civil goods:
  - food
  - consumer goods
  - medical supplies
- advanced goods:
  - research equipment
  - reactor parts
  - gate components

## Core constraints

Interesting problems should emerge from:
- travel time,
- finite station throughput,
- train length and wagon specialization,
- loading and unloading delays,
- storage limits,
- power shortages,
- gate activation and upkeep cost,
- link congestion,
- terrain and infrastructure cost,
- uneven resource distribution across worlds.

## MVP statement

The first playable prototype should prove this:

The player can bootstrap a frontier world into a self-sustaining industrial colony by building a rail network, supplying key industries, and using a single costly wormhole hub to solve a major logistics bottleneck.

## Engine strategy

Engine choice stays open for now.

The backend should be built so it can support:
- continued CLI-first development,
- a future custom frontend,
- or a later decision to adapt the design into an existing engine or moddable platform.

That means the Python simulation should remain:
- deterministic,
- data-driven,
- decoupled from rendering,
- explicit about save/load and command interfaces.
