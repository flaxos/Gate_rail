# Game Vision

## Premise

GateRail is a logistics and development game set decades after Gate Horizons. The origin-era story discovered the ancient Horizon Artefact and triggered the Horizon Event: proof that true precursor gate technology existed. By the time GateRail begins, corporations still have not mastered the original system. They have reverse-engineered smaller **derivative aperture systems** called **Railgates**.

The Railgate Age is industrial, corporate, and constrained. Railgates are paired, route-bound, energy-hungry, throughput-limited corridors. They work best for fixed freight because trains provide exact alignment, predictable mass, controlled velocity, standardized cargo, and safe automated throughput.

The first gate was a miracle. Railgates are a business model.

The player expands from local rail systems to interworld logistics networks, building extraction outposts and frontier colonies into major industrial, civic, and research hubs. Railgates are not a replacement for logistics planning. They are strategic aperture corridors that compress distance at a major energy cost.

## Player fantasy

The game should support all three of these fantasies at once:
- railroad tycoon across impossible space,
- industrial optimizer chaining extraction, production, and delivery,
- frontier builder growing colonies and industrial hubs under corporate pressure.

## Player optimization targets

The player is optimizing:
- throughput across rail and Railgate networks,
- world development and promotion,
- supply stability under growing complexity,
- strategic use of expensive aperture power,
- economic scaling through specialization and interdependence,
- the transformation of raw elements into higher-order industrial capability.

## Distinctive hook

GateRail is defined by the interaction between:
- trains as the main physical logistics layer on each world,
- Railgates as high-cost topology-changing corridor infrastructure,
- worlds as evolving economic actors rather than static maps,
- recursive expansion where industrial hubs help bootstrap frontier colonies.

This should feel different from a conventional rail sim because the objective is not only route profit or station coverage. The player is building a multi-world industrial network for Transit Combines and megacorporations.

## World model

Each world has:
- a development tier,
- a population and stability state,
- local resources and environmental constraints,
- import requirements,
- potential specializations,
- transport infrastructure,
- power availability.

Worlds, moons, belts, and remote sites should eventually expose different elemental and chemical opportunities. A core world might have manufacturing depth but poor raw supply; a frontier world might have ore and volatiles but lack refining; an orbital site might have rare isotopes but require mining ships and collection stations before trains can move its output.

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
- underground vacuum tubes for expensive high-speed corridors that still require portals, power, maintainable curves, and signal control,
- Railgate anchors and receiving terminals for near-instant interworld freight corridors,
- orbital yards, mining missions, and collection stations for remote extraction,
- optional space lanes or orbital transfer nodes later if needed.

For the backend MVP, train simulation should stay operational rather than hyper-physical:
- trains have capacity, speed, route assignment, and cargo specialization,
- stations have load and unload limits,
- links can express travel time and congestion,
- rail links should evolve from straight A-to-B edges into backend-owned alignments with curves, branches, junctions, stop signals, and path signals,
- detailed block signaling can start simple and diagnostic, then deepen only when dense industry traffic needs it.

## Railgates in gameplay terms

Railgates are player-built or player-activated derivative aperture corridors that:
- consume large amounts of power,
- greatly reduce effective travel time,
- relieve distance-driven bottlenecks,
- create strategic decisions around where to place Railgate anchors and receiving terminals,
- should never feel free.

Railgates solve logistics problems, but they also create new ones through energy demand, corridor capacity, aperture alignment, and hub concentration. The original Horizon Artefact remains beyond corporate mastery; Railgates are the limited business-facing technology that emerged after it.

## Resource and industry model

The first playable resource model should use a limited set of meaningful categories, but the long-term design should support periodic-table-scale industry through a data-driven catalog. The player does not need every element visible at once. The simulation should be able to grow from compact cargo categories into real elements, isotopes, alloys, industrial chemicals, semiconductors, reactor inputs, and discoverable exotic materials.

Resource layers:
- raw sources: mixed ore, iron-rich ore, bauxite, silica, carbon feedstock, brines, water ice, volatile ice, fissile ore, rare-earth-bearing ore, regolith, biomass, and exotic fragments
- refined elements and bulk materials: iron, copper, aluminum, silicon, carbon, hydrogen, oxygen, titanium, lithium, cobalt, uranium, thorium, helium-3, rare earth concentrate, noble metal concentrate, glass, and industrial chemicals
- industrial materials: steel, alloys, wire, composites, ceramics, battery chemicals, reactor fuel, coolant, precision substrates, doped silicon, and superconducting wire
- manufactured goods: machine parts, heavy machinery, motors, cargo equipment, power cells, circuit boards, sensors, semiconductors, control systems, construction modules, rail equipment, and habitat modules
- advanced systems: reactor assemblies, high-capacity capacitors, aperture field coils, aperture lenses, stabilizers, navigation cores, research equipment, mining packages, and orbital collection arrays
- discoverable exotics: Horizon-reactive isotopes, unusual catalysts, vacuum-grown crystals, folded-matter samples, and other original setting-specific materials

The core industrial ladder should be:

1. Prospect a deposit or remote site.
2. Extract raw material.
3. Sort and concentrate ore streams.
4. Smelt or refine into elements and feedstocks.
5. Alloy, process, and chemically prepare industrial materials.
6. Manufacture parts, electronics, semiconductors, machinery, and construction modules.
7. Assemble reactor assemblies, aperture control components, advanced mining systems, and research equipment.
8. Deploy those outputs to power plants, outposts, facilities, trains, and Railgate anchors.

This industrial ladder is now a core design target, not a late-game visual flourish.

## Space extraction and outposts

Railgates should eventually open access not only to settled worlds but also to belts, moons, debris fields, gas pockets, and anomalies. Mining ships can be modeled as fixed-tick logistics actors launched from orbital yards or Railgate anchors. They return cargo to collection stations, which then feed the rail and Railgate network.

Outposts and ore collection stations should be built by deliveries of construction modules, machinery, power equipment, electronics, food, water, and habitat supplies. Cash can authorize construction, but supply chains should make it real.

## Power and Railgates

Power should become a resource economy:
- early plants consume fuel or carbon feedstock,
- fission plants consume refined fissile materials and reactor parts,
- fusion plants consume hydrogen isotopes, helium-3, coolant, and advanced components,
- Railgate anchors reserve power capacity and may consume stored charge for high-throughput operation,
- rare elements and discoverable exotics can improve aperture efficiency or unlock stronger Railgate infrastructure.

The player should have to decide whether to move power inputs, build local generation, upgrade Railgate efficiency, or route cargo around the corridor.

## Core constraints

Interesting problems should emerge from:
- travel time,
- track geometry, curvature, branches, and junction pressure,
- finite station throughput,
- train length and wagon specialization,
- cargo wagon compatibility,
- loading and unloading delays,
- storage limits,
- ore grade and refining yield,
- multi-stage manufacturing dependencies,
- power shortages,
- Railgate activation and upkeep cost,
- link congestion,
- terrain and infrastructure cost,
- uneven resource distribution across worlds.

## MVP statement

The first playable prototype should prove this:

The player can bootstrap a frontier colony into a self-sustaining industrial hub by building a rail network, extracting and refining raw resources, manufacturing key maintenance parts and aperture control components, powering local industry and Railgates, and using a costly corridor to solve a major logistics bottleneck.

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
