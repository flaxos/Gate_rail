# Resource and Industry Plan

This plan expands GateRail from a compact logistics prototype into a deep industrial game. The goal is not to add 3D presentation yet. The goal is to make the economic core worth presenting: raw extraction, refining, manufacturing, power generation, gate operation, space mining, and frontier outpost construction.

Sprint 17A implementation status:
- the backend now has a `resources.py` catalog with raw sources, refined elements, industrial materials, manufactured goods, advanced systems, and undiscovered exotics.
- `GameState` now owns resource deposits with grade/yield metadata, and built-in scenarios include local deposits.
- snapshots and CLI inspection expose the catalog and deposits; refining recipes are the next slice.

Sprint 17B implementation status:
- nodes can now own resource inventories, resource recipes, and optional deposit extraction ids.
- each tick can extract from deposits, move resource units across local rail neighbours, and process all-or-nothing resource recipes.
- the default playtest now demonstrates iron-rich ore plus carbon feedstock becoming iron, then gate components.

Sprint 18 implementation status:
- resource recipes are typed as smelting, refining, electronics assembly, semiconductor work, or fabrication.
- the default playtest now runs silica, copper, silicon, electronics, and semiconductors before gate-component fabrication.
- reports and snapshots expose resource branch-pressure warnings for dense local industry rail clusters.

Sprint 19 implementation status:
- gate links can now have resource-backed support requirements that reduce effective power draw when upstream industry produces the required components.
- the `sprint19` scenario demonstrates a frontier gate that is blocked by missing gate components, then recovers once the resource chain fabricates them.
- reports and snapshots expose base power, effective power, support bonus, support node, support inputs, and missing support resources.

## Design Stance

GateRail should support periodic-table-scale industry over time, but it should not expose every element as a separate cargo problem on day one. The backend should use a data-driven resource catalog that can grow from a small playable subset into dozens or hundreds of elements, isotopes, alloys, chemicals, and exotic discoveries.

The player-facing rule is simple:

1. Find raw deposits.
2. Build extraction and collection infrastructure.
3. Move raw material by rail, gate, or mining logistics.
4. Refine it into usable elements and industrial feedstocks.
5. Manufacture parts, electronics, semiconductors, advanced machinery, reactor systems, and gate components.
6. Use those outputs to expand worlds, power gates, and reach harder deposits.

## Resource Layers

### Layer 0: Raw Sources

Raw sources are messy and location-bound:
- mixed ore
- iron-rich ore
- copper-rich ore
- bauxite
- silica sand
- carbon feedstock
- salt and chemical brines
- water ice
- volatile ice
- rare-earth-bearing ore
- fissile ore
- regolith
- biomass
- exotic-bearing fragments

Raw sources should have grade, impurity, and extraction difficulty fields eventually. Early sprints can model grade as a simple output multiplier or recipe yield.

### Layer 1: Refined Elements and Bulk Materials

Refining separates raw sources into useful materials:
- iron
- copper
- aluminum
- silicon
- carbon
- hydrogen
- oxygen
- nitrogen
- titanium
- nickel
- lithium
- cobalt
- uranium
- thorium
- helium-3
- rare earth concentrate
- noble metal concentrate
- refined stone and glass
- industrial chemicals

The exact catalog should live in backend data, not hardcoded UI assumptions.

### Layer 2: Industrial Materials

Industrial materials are combined or processed forms:
- steel
- aluminum alloy
- titanium alloy
- copper wire
- carbon composite
- glass fiber
- ceramics
- battery chemicals
- reactor fuel
- coolant
- precision substrate
- doped silicon
- superconducting wire
- radiation shielding

These are where factory chains start to feel different. A metalworks, chemical plant, and semiconductor line should not all be the same generic recipe with different names.

### Layer 3: Manufactured Goods

Manufacturing turns refined and industrial materials into gameplay objects:
- machine parts
- heavy machinery
- motors
- pumps
- cargo handling equipment
- power cells
- circuit boards
- sensors
- semiconductors
- control systems
- construction modules
- habitat modules
- mining rigs
- rail equipment

These goods build and upgrade extraction nodes, factories, outposts, power plants, trains, and gates.

### Layer 4: Advanced Systems

Advanced systems should require several upstream chains:
- reactor parts
- high-capacity capacitors
- gate field coils
- gate lenses
- precision stabilizers
- navigation cores
- research equipment
- autonomous mining packages
- orbital collection arrays
- deep-space survey packages

The important design property is dependency depth. A gate upgrade should imply a mature industrial base, not just a large cash cost.

### Layer 5: Discoverable Exotics

Because the setting is science fiction, some elements and materials can be discovered rather than known at game start:
- gate-reactive isotopes
- high-density field conductors
- exotic catalysts
- unstable transuranics
- vacuum-grown crystals
- folded-matter samples

These should be original terms and mechanically distinct. Discovery can unlock new recipes, more efficient gate power, better reactors, or remote mining methods.

## Processing Chain

The core industry ladder should be:

1. Prospecting: find a deposit, asteroid, moon seam, or exotic trace.
2. Extraction: mine, drill, harvest, or collect raw material.
3. Sorting: split mixed raw sources into ore streams or waste.
4. Smelting/refining: produce refined elements, fuel, chemicals, or bulk materials.
5. Alloying/chemistry: produce industrial materials.
6. Fabrication: produce parts, machinery, electronics, and construction modules.
7. Semiconductor line: turn silicon, rare dopants, chemicals, power, and clean-room capacity into chips and control systems.
8. Advanced assembly: produce reactor parts, gate components, mining ships, and high-tier outpost kits.
9. Deployment: deliver outputs to a construction site, outpost, facility, power plant, or gate hub.

Each stage should create visible logistics decisions: throughput caps, storage pressure, recipe blockers, power demand, waste byproducts, and alternate recipes.

## Power and Gates

Power should become a resource economy, not only a static world stat.

Early backend model:
- power plants convert fuels or reactor materials into world power capacity,
- gates reserve power capacity while active,
- large gate moves consume charge or operating energy,
- power plants need maintenance inputs such as coolant, reactor parts, or fuel,
- power shortages block gates, slow industry, or reduce facility throughput.

Sprint placement:
- Sprint 19 implemented resource-backed gate efficiency only.
- Sprint 19B / Sprint 20A implemented the first true power-generation model before remote mining missions depend on fuel or power.
- The first slice is backend-only: operating plants, generated-power totals, missing-input blockers, and gate evaluation using generated capacity. Later slices should add richer reactor-fuel/coolant recipes and plant construction UI.

Power chain examples:
- carbon feedstock -> fuel -> thermal plant -> early power
- uranium/thorium -> reactor fuel -> fission plant -> stable colony power
- helium-3/deuterium -> fusion fuel -> fusion plant -> high-output gate power
- exotic catalyst + advanced capacitors -> gate efficiency upgrades

The player should eventually ask, "Do I ship power inputs to the gate world, build local generation, or route cargo around the gate?"

## Space Extraction

Space extraction should extend the rail game rather than replace it.

Concept:
- Gates and orbital yards can open access to remote belts, moons, and debris fields.
- Mining ships are fixed-tick logistics actors dispatched from an orbital yard or gate hub.
- Trains deliver the construction modules, fuel, crew supplies, and machinery needed to build orbital yards and remote collection stations.
- Mining ships return raw sources to a collection station, gate hub, or orbital depot.
- Rail then moves those resources into refineries and factories.

Early model:
- `SpaceSite`: asteroid, moon, debris field, gas pocket, or exotic anomaly.
- `MiningMission`: ship, source site, return node, cargo yield, travel ticks, fuel/power requirement, risk.
- `CollectionStation`: logistics node that receives mission output and connects to rail/gate networks.

This gives the player a reason to build outposts and ore collection stations without needing real-time ship piloting.

## Rail Network Interaction

The industry expansion should create the need for better rail planning. Dense resource chains naturally create:
- mining branches feeding sorting yards,
- refinery districts with several outputs,
- factory parks competing for parts, chemicals, and electronics,
- power plants and gate hubs needing priority inputs,
- orbital collection stations returning mixed cargo streams.

The rail work should therefore progress in parallel:
- backend-owned rail alignments and waypoints so tracks are not always straight A-to-B,
- branches, junctions, and station throats for industry districts,
- stop signals and path signals for dense yards and vacuum-tube portals,
- cargo wagons and typed consists for bulk ore, liquids, protected goods, heavy modules, reactor materials, and exotics.

This keeps the resource game and transport game coupled. Deeper industry should create rail problems, and better rail planning should solve them.

## Outpost Construction

Outposts should be built by supply chains, not by cash alone.

A remote outpost or ore collection station should require:
- construction modules,
- machinery,
- power equipment,
- habitat supplies,
- food and water,
- electronics or control systems,
- local rail or gate access,
- initial storage and loader capacity.

Construction can start as immediate validation plus cargo costs, then later become staged construction jobs with progress, deliveries, and partial operation.

## Facilities

Facilities are where the industrial chain becomes concrete.

Relevant component families:
- extractor head
- crusher or sorter
- smelter
- refinery
- chemical processor
- alloy furnace
- fabricator
- electronics assembler
- semiconductor line
- clean room
- reactor
- capacitor bank
- gate interface
- storage bay
- loader and unloader

Factory blocks should evolve from generic input/output recipes into typed processing components with clear power draw, throughput, ports, and blocked-flow diagnostics.

## Discovery and Research

Research should reveal new economic possibilities:
- identify unknown elements in raw samples,
- improve yield from poor ore grades,
- unlock alternate recipes,
- reduce gate power cost,
- unlock deeper mining missions,
- improve outpost construction kits,
- stabilize exotic materials.

Unknown materials should first appear as analyzable cargo, then become named resources once researched.

## MVP Slicing

The next core-system sequence should be:

1. Resource catalog and ore deposit model.
2. Refining chain from raw ore to refined elements and industrial materials.
3. Manufacturing chain from materials to parts, electronics, semiconductors, and advanced components.
4. Power plant and gate-energy economy.
5. Space extraction missions and collection stations.
6. Outpost construction as cargo-delivery projects.
7. Rail alignment, branch, signal, and consist depth alongside the above systems.
8. Facility and rail UI for diagnosing these chains.
9. 3D presentation only after the above rules are fun and stable.

## Non-Goals For The Next Slice

- Do not hand-model all real elements before a smaller subset is playable.
- Do not require chemistry-level simulation accuracy.
- Do not add a browser UI.
- Do not duplicate processing rules in Godot.
- Do not begin 3D facility presentation before resource and power chains are proven.
