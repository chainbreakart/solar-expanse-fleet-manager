# Fleet Manager Planner Backlog

This captures movement/planning features that are not yet fully implemented in the MVP, now triaged as a dependency stack. The tables are useful drill-downs, but the next product shape should put a compact logistics dashboard in front of them.

## Status Legend

- [Implemented] Working in the current code/UI.
- [Pending] Partially supported by normalized data or a table, but not complete as a planner-facing feature.
- [Not implemented] Not started in code yet.

## Dashboard Goal

A logistics planner should be able to open the app and answer these questions without starting in a data table:

- What is moving right now?
- What is planned but not yet departed?
- What needs attention before advancing time?
- Where are the bottlenecks?
- What happens next?

## Dashboard Surface

### Always-Visible KPIs

- [Pending] Active missions. Mission/craft data exists, but no dashboard KPI tile yet.
- [Pending] Planned departures. Mission/craft data exists, but no dashboard KPI tile yet.
- [Implemented] People in transit. Current top KPI is supplied by the People Transit module.
- [Implemented] Empty crew compartments. Current top KPI is supplied by the People Transit module.
- [Implemented] Return-fuel shortfall count. Current top KPI is supplied by the Return Fuel module.
- [Pending] Next arrival. Route/body metrics expose this, but no dashboard KPI tile yet.
- [Pending] Next departure. Route metrics expose this, but no dashboard KPI tile yet.
- [Pending] Idle craft. Body metrics expose this, but no dashboard KPI tile yet.
- [Not implemented] Needs-attention count. Requires the attention engine.
- [Pending] Fuel or life-support concern missions. Return-fuel concern counts exist; life-support exhaustion does not.

### Primary Visualizations

- [Not implemented] Solar Logistics Map: nodes are bodies/orbits/stations, edges are active or planned routes, edge thickness reflects cargo or craft volume, and edge color reflects status/attention state. Human-specific route lanes belong under Population Visualization.
- [Not implemented] Mission Timeline: one bar per active/planned mission, with departure, arrival, progress, cargo markers, and attention markers. Population flight timing belongs under Population Visualization.
- [Pending] Route Load Matrix: origin by destination matrix showing mission count, tons, and attention count. Route metrics exist; matrix visualization does not. Human movement matrixing belongs under Population Visualization.
- [Pending] Body Readiness Cards: compact cards for key bodies showing present craft, inbound craft, outbound craft, local fuel, cargo pressure, and attention items. Body metrics exist; card UI does not. Housing/Supply readiness belongs under Population Visualization.
- [Not implemented] Alerts Feed: prioritized operational messages such as fuel shortfalls, cyclicals halted by missing cargo/fuel, staleness, and population alerts emitted by the population readiness layer.
- [Implemented] Return Fuel Estimator: per active/planned craft, estimate whether it can leave the destination again using expected onboard fuel at arrival, fuel carried as cargo, destination immediate stock, and destination surface stock that still needs lift.

### Population Visualization

These are the primary visuals for moving humans safely and intentionally. Population now has separate surfaces for movement planning and people-in-place sustainment, with the People Transit table remaining the movement drill-down and colonies/stations becoming the growth/sustainment bridge.

Scalability rule: population charts must stay useful if populated locations grow from a handful into dozens or 100+. Compact dashboard visuals should show ranked actionable slices, aggregate the rest, and leave the full list to searchable/filterable tables.

Tiering basis: MVP items use already-normalized save facts and low-validation calculations; RC items are technically moderate or need interaction polish; Stretch items need heavier modeling, uncertain formulas, or larger visualization architecture.

#### MVP

- [Implemented] Population section split: `/population` is a small hub, `/population/movement` owns people-in-transit planning, and `/population/places` owns colonies/stations sustainment.
- [Pending] Movement KPI Strip: people in transit, empty crew compartments, empty seats, next population arrival, destinations by readiness status, and life-support concern count. Basic dashboard scaffold exists; life-support concern count can wait for RC.
- [Pending] Movement Destination Readiness Matrix: one row per destination with inbound people, current population, current housing, queued housing, arriving habitat capacity, housing gap, Supply stock, Supply net/day, projected runway, next population arrival, and status. Basic dashboard scaffold and status tooltips exist; chart-click drill-down interactions can wait for RC.
- [Pending] Colonies / Stations Sustainment Dashboard: current population, completed housing, queued housing, inbound people, Supply stock, Supply intake/outtake, net Supply/day, runway, and status. Basic table, status tooltips, KPI strip, chart controls, Supply balance, housing/occupancy, and runway visuals exist; colony growth and demand modeling can wait for Stretch.
- [Pending] Supply Runway Burndown: projected Supply stock over time for destinations with inbound people, showing current burn, post-arrival burn, status thresholds at two years, one year, and half a year, and the save-derived local Supply modifier used. Basic Plotly scaffold exists; threshold annotations and reusable projection rows are MVP polish.
- [Pending] Housing Stack / Gap Waterfall: compare current population plus inbound population against completed housing, queued housing, and habitat capacity carried by arriving flights. Basic Plotly scaffold exists; final waterfall treatment is MVP polish because the data basis is already present.
- [Not implemented] Population visualization scalability controls: chart-level filters for All / Concerns Only, company, object type, inbound people, housing gap, Supply runway threshold, and minimum population. The table remains the authoritative full list.
- [Not implemented] Risk Focus panel: show only the top 8-12 actionable places by severity, shortest Supply runway, largest housing gap, or inbound population, with all other places summarized as "Other" rather than plotted individually.
- [Pending] People Transit Drill-Down Integration: link matrix/Sankey/timeline rows back to the grouped People Transit table and carry local population, known housing capacity, destination population delta, and readiness tooltip context into that drill-down.

#### RC

- [Pending] Population Flow Sankey: source body to destination body flows sized by people in transit, colored by destination readiness, with hover details for ship, arrival date, crew modules, housing carried, Supply runway, and readiness basis. Basic Plotly scaffold exists; richer hover/drill-down is pending.
- [Pending] Population Arrival Timeline: active and planned population flights as timeline bars with departure, arrival, people count, loaded/empty module markers, habitat/supply cargo markers, and readiness state at arrival. Basic Plotly scaffold exists; attention/life-support markers can wait for Stretch.
- [Not implemented] Population sustainment scatter/bubble: x-axis Supply runway, y-axis free housing or housing gap, bubble size population, color status, labels only for the worst few places and hover for the rest. This is the preferred compact view for dozens to 100+ places.
- [Not implemented] Population sustainment heatmap: rows are colonies/stations, columns include population, free housing, queued housing, inbound people, Supply runway, and net Supply/day. Use status/magnitude color so high-count colony sets remain scannable.
- [Not implemented] Colonization Site Prep / Watchlist: let the player mark preferred future colony targets and also auto-suggest unpopulated or low-population places with colonization-support cargo already present or inbound. For each site, show local Supply/stock, inbound Supply/building/habitat/outpost cargo with arrival dates, existing/queued housing, current production flow where available, and whether people are already inbound. This belongs in `/population/places` as the planning outcome, with links into cargo and production evidence.
- [Pending] Population Balance by Body: local humans, empty outbound seats, inbound people, housing capacity, queued/carried habitat capacity, Supply runway, and life-support concerns by body. `/population/places` covers local population, housing, inbound people, and Supply runway; empty outbound seats and carried habitat by body are RC scope.
- [Not implemented] Flight Cohort Cards / Manifest Treemap: each population flight rendered as a compact visual block sized by people carried, with module loading, life support, habitat cargo, Supply cargo, and destination readiness visible at a glance. Depends on existing grouped People Transit rows plus chart/card UI.

#### Stretch

- [Not implemented] Life-Support Exhaustion Overlay: mark population flights that appear likely to exhaust mission life support before arrival, using loaded people, mission life-support carriage, and mission duration. This needs formula validation before it becomes planner-facing and should become a marker on the timeline, Sankey hover, and flight cohort cards rather than a standalone table.
- [Not implemented] No-Inbound Population Need Panel: surface destinations with detected population demand but no people inbound. This needs a stronger demand model than empty housing alone and should stay separate from warnings until the demand basis is trustworthy.
- [Not implemented] Route Lane Map for People: body/orbit nodes connected by population-carrying routes, with node size reflecting population pressure or inbound people and edge width reflecting people in transit. Depends on route-level population aggregates, graph layout, and interaction design.
- [Not implemented] Colony growth/demand modeling: fold construction completion, workforce, production, power, and market/demand assumptions into the colonies/stations dashboard. This is high validation lift and should not block the movement/sustainment MVP.

### Cargo Transit Visualization

Cargo transit should be a separate section from production. It answers "what is moving, where, on what craft, and when does it arrive?" Production answers "what is being made, consumed, stored, or depleted at each place?" They should share a commodity/resource drill-down so a player can connect local stock and net production to inbound cargo timing without mixing two different workflows on the same screen.

Tiering basis: MVP items use existing `CargoFact`, `MissionFact`, `CraftFact`, and `RouteMetric` rows; RC items add richer grouping and interactions; Stretch items need demand modeling, route-capacity planning, or what-if behavior.

#### MVP

- [Not implemented] Cargo Transit section scaffold: add a dedicated `/cargo` route with a KPI strip, compact visual row, and grouped manifest drill-down table. This should not pollute the overview except for top-line cargo KPIs.
- [Not implemented] Cargo KPI Strip: total tons in transit/planned, next cargo arrival, active cargo routes, top 3 resources/modules moving, and cargo flights needing attention once the attention engine exists.
- [Not implemented] Cargo In-Transit Matrix: origin by destination matrix showing tons by route, with filters for resource/module category, mission status, company, and concerns-only.
- [Not implemented] Cargo Arrival Schedule: timeline or stacked bar view showing inbound tons by resource/module and arrival date, grouped by destination so players can see whether a production gap is about to be covered.
- [Not implemented] Grouped Cargo Manifest Drill-Down: one top row per mission/flight with craft, route, arrival, total tons, major cargo categories, fuel cargo, modules, and expandable item rows from `CargoFact`.
- [Not implemented] Destination Receipts Panel: top destinations ranked by inbound cargo tonnage, next arrival, and resource mix, with links into the grouped manifest table.
- [Not implemented] Colonization Support Cargo Filter: classify inbound cargo that can support site prep, such as Supply, habitat/outpost/building modules, fuel staging, and construction resources, so `/population/places` can show "supplies and stuff on the way" for preferred colony targets.

#### RC

- [Not implemented] Cargo Flow Sankey: source object to destination object flows sized by cargo tons and colored by resource/module class, with hover details for craft, mission status, arrival date, and manifest summary.
- [Not implemented] Commodity Arrival Calendar: resource-focused calendar/Gantt view for one selected commodity showing inbound shipments, source, destination, and days until arrival.
- [Not implemented] Cargo Route Saturation View: compare assigned cargo tons, craft capacity, route cycle timing, and idle/available craft by route where the data supports it.
- [Not implemented] Cargo-to-Production Join: from a selected resource, show local stock/net production alongside inbound/outbound cargo so players can see whether logistics is actually solving a production shortfall.
- [Not implemented] Destination Cargo Evidence Links: every destination-focused cargo visual should be linkable from Population Site Prep and Production Commodity views with destination/resource filters already applied.

#### Stretch

- [Not implemented] Cargo Demand Gap Estimator: infer likely unmet cargo demand from production shortages, construction queues, halted cyclicals, or market/resource deficits. This needs validation before becoming planner advice.
- [Not implemented] Surface-to-Orbit Cargo Staging View: visualize cargo or fuel present on surfaces versus cargo needed in orbit, including launchcraft dependency and lift bottlenecks.
- [Not implemented] What-if Cargo Move Planner: let players sketch a shipment or route and estimate arrival timing, destination stock impact, and transport capacity pressure without writing to the save.

### Production Visualization

Production should also be a separate section. It answers "where are stocks building or burning down, what resources are bottlenecks, and which places are exporters/importers?" The first pass should stay close to save data: company-local stock, `inTake`, `outTake`, and net/day. Deeper facility formula modeling belongs later.

Tiering basis: MVP items use existing `ResourceStockFact` rows and object metadata; RC items join production to cargo and construction context; Stretch items need facility/refinery/power formula validation.

#### MVP

- [Not implemented] Production section scaffold: add a dedicated `/production` route with a KPI strip, resource/location filters, compact risk visuals, and a stock/flow drill-down table.
- [Not implemented] Production KPI Strip: resource locations tracked, negative-net locations, stockouts under configurable runway thresholds, top bottleneck resources, and largest net exporters.
- [Not implemented] Stock and Flow Heatmap: rows are objects/colonies/stations, columns are key resources, with cells encoding stock, net/day, or runway depending on selected mode. This is the scalable default for dozens to 100+ places.
- [Not implemented] Production Balance Bars: for a selected resource, compare stock, intake/day, outtake/day, and net/day across locations with ranked slices and "Other" aggregation.
- [Not implemented] Runway Risk Focus: top 8-12 resource/location pairs by shortest runway or largest negative net/day, with tooltip primitives for stock, intake, outtake, net, and estimated depletion date.
- [Not implemented] Resource Stock Drill-Down Table: one row per company/object/resource using `ResourceStockFact`, including object type, stock, intake, outtake, net/day, runway, and source.
- [Not implemented] Candidate Site Stock Summary: for unpopulated/pre-colony targets, summarize local stocks and net/day for colonization-critical resources without requiring the site to already have people.

#### RC

- [Not implemented] Commodity Detail Dashboard: selected resource view combining local stock/net production, inbound cargo, outbound cargo, next arrival, and projected stock line.
- [Not implemented] Exporter / Importer Map: classify locations by resource as producer, consumer, balanced, stockpile-only, or depleted; link each location to cargo and body drill-downs.
- [Not implemented] Construction Queue Impact Panel: show queued facilities/modules that will change housing or production where completion/progress data is reliable.
- [Not implemented] Colonization Readiness Stock/Flow Links: link candidate site rows to production/resource views filtered to that destination and to cargo views filtered to inbound support cargo.
- [Not implemented] Production Alerts Export: emit shared attention rows for deterministic stockout/runway and negative-net situations after thresholds are validated.

#### Stretch

- [Not implemented] Facility-Level Production Graph: derive input/output dependencies from facilities/refineries/mines/power and show a resource dependency graph. Requires game formula validation.
- [Not implemented] Power / Workforce / Facility Constraint Model: explain why production is capped or idle by joining facility state, power needs, workforce, and resource inputs. This is high validation lift.
- [Not implemented] Production What-if Planner: estimate how new facilities, imports, or population changes alter stock runway and net/day without writing to the save.

### Visualization Stack

- [Implemented] NiceGUI remains the shell and workflow layer.
- [Implemented] Plotly is the first visualization library added for timeline/Gantt views, heatmaps, Sankey-style flows, hover details, burndown charts, waterfall/stack charts, treemaps, and dashboard charts.
- [Not implemented] ECharts via NiceGUI is a good candidate for compact dashboard-native charts, fast KPI panels, Sankey/graph layouts, and heatmaps when Plotly feels too heavy.
- [Implemented] NetworkX is added as a future graph-layout dependency for route graph analysis, not as the main renderer.
- [Not implemented] PyVis or pydeck/deck.gl should be deferred until the route map needs richer graph or spatial interaction than Plotly can comfortably provide.

## Current Implemented Foundation

- Save discovery defaults to the newest `.json.gz` save and allows save switching.
- Odin-ish save parser supports the save format well enough for read-only planning.
- Company roles are normalized so the app defaults to the player corporation only. The paired `.info.gz` `SaveInfo.startGameConfiguration.Company` is treated as authoritative when present, including autosaves with generic filenames. If the `.info.gz` sidecar is missing or unreadable, the save's `companyAISave` plus non-AI activity scoring can infer the player and marks the source as inferred. Filename text is never used as player identity, and uncertain/empty default scopes no longer widen silently to all companies. AI companies and World Government are hidden unless the user enables the muted AI/WG toggle.
- Object IDs are resolved through `object_id_reference.csv`.
- Mission assignment lookup handles primary `scID` plus typed spacecraft list fields such as `sclistID` and cyclical `scIDList`.
- Shared `MissionFact` rows now normalize standard mission records and cyclical mission records, including reusable timing metrics, before the Fleet Board and People Transit view consume them.
- Shared `CargoFact` rows now normalize mission cargo, onboard craft cargo, special fuel cargo, life-support carriage, modules, crew modules, and direct human resources before the People Transit view consumes them.
- Shared `ObjectFact` rows now normalize object ID, display label, object type, parent body/orbit relationship, surface/orbit classification, company activity/ownership where visible, present craft count, inbound/outbound mission counts, and next arrival before the Body Board consumes them.
- Shared `CraftFact` rows now normalize current object, true object, active assignment, spacecraft type, live cargo/fuel capacities, propulsion, fuel type, construction mode, surface/orbit capability, launchcraft classification, timing metrics, capacity metrics, transfer mode, and Fleet Board display summaries.
- Shared `RouteMetric` rows now normalize route assignment totals, moving/planned craft counts, cargo tons assigned, people assigned, next departure, next arrival, status mix, and warning-count plumbing before the Route Board consumes them.
- Shared `BodyMetric` rows now normalize craft present, idle craft, active/planned inbound craft, outbound craft, inbound cargo rollups, inbound/outbound people, next arrival, and route lists before the Body Board consumes them.
- The UI is atomized into a NiceGUI shell, one shared `SaveAnalysis` bundle, and separate `fleet_modules` table modules for Fleet, Route, Body, and People Transit views.
- Windows companion-app scaffolding exists for Python 3.11/3.12 x64, PyInstaller onedir, bundled reference data, Inno Setup, app-data storage, environment-based save overrides, localhost port overrides, and future IPC handoff files.
- Reference-driven `assets/command_console.css` now provides the hard sci-fi command-console theme, responsive panel grids, dark table styling, dynamic KPI cards, cyan/amber status accents, and packaged stylesheet inclusion.
- Fleet Board shows craft, current object, mission status, route, ETA, cargo, fuel, timing, capacity, transfer details, and a warnings column.
- Route Board groups assignments by route from shared route metrics, including moving/planned split, cargo/people assigned to active or planned missions, next departure, next arrival, and status mix.
- Body Board summarizes object type, parent relationship, visible company activity, present/idle craft, active/planned inbound craft, outbound craft, inbound cargo, people in/out, and next arrival.
- Shared `CrewMetric` rows now normalize loaded people, empty seats, empty crew compartments, compartment type, reference seat capacity, and mission life-support carriage before the People Transit Board consumes them.
- People Transit Board groups loaded/empty crew-compartment rows into one collapsible flight row per mission, with individual module details available on expand.
- People Transit Board shows loaded people, empty seats, empty crew compartments, crew compartment type, reference seats, mission life support, route, craft, timing, and destination readiness for active/planned missions.
- Population Logistics is split into `/population` as a hub, `/population/movement` for people-in-transit planning, and `/population/places` for colonies/stations sustainment.
- The People Movement dashboard renders KPI cards, a destination readiness matrix, Supply runway burndown, housing readiness stack, population flow Sankey, population arrival timeline, and a People Transit drill-down table from the current `SaveAnalysis`.
- The Colonies / Stations dashboard renders people-in-place KPIs, a local sustainment table, chart controls, Supply balance, housing/occupancy, and current Supply runway visuals from current population, habitat, and stock facts.
- The index route `/` is intentionally top-line only: save picker, global KPI cards, and section launchers. Full tabbed boards live at `/data`.
- Shared `PopulationReadinessMetric` rows now estimate inbound-population destination support from current population, completed housing, queued housing, habitat-capable cargo arriving no later than the people flight, same-company Supply stock, same-company Supply intake/outtake, and marginal housed/unhoused consumption adjusted by a save-derived local Supply modifier when current population burn exists. People Transit shows tooltip-aware `Safe`, `Warning`, `Urgent`, or `Critical` chips.
- Shared `ResourceStockFact` rows now normalize same-company stored resource stock from `objectInfoDatas`, separate from natural deposits in `ObjectInfoSaves`.
- Shared `ReturnFuelMetric` rows now normalize fuel type, return requirement estimate, confidence, saved/arrival fuel with an explicit calculation basis, compatible fuel cargo, destination immediate stock, destination surface stock when the destination is an orbit, lift-needed surface fuel, and immediate/deferred return margins before the Return Fuel Board consumes them.
- Return Fuel Board shows active/planned craft return-fuel margins, follows the planned/en-route fuel-basis rules from the estimator scope, distinguishes hard shortfalls from cases that could be covered by lifting surface stock, and gives warning cells tooltip interrogation with the stock numbers behind the assessment.
- Capacity and tank percentages now prefer live company hull data from the selected save's `hullList`, with generated spacecraft reference data only as a fallback. ESA Hermes correctly reads `Hermes Hull` as 300t cargo / 300t fuel in the current save.
- Fuel planning text now treats `allFuelNeed` as planned total fuel and mission `cargoFuel.cargoMass` as saved residual/onboard fuel for planned/en route missions.
- Static-reference over-capacity warnings are intentionally disabled. The warnings column is plumbing for deterministic alerts, not a general advisory engine yet.

## Current Limits

- Attention rows and future dashboard cards are not normalized into dedicated modules yet.
- `fleet_core.normalizer` still carries most of the parsing and metric logic; the module shell reduces UI coupling, but deeper fact packages can be split out later as the planner grows.
- Live hull capacity is matched by known spacecraft/hull names. This covers current core craft such as Hermes, but should be replaced with a fuller game-data mapping for all hull variants and modded/custom designs.
- Life-support exhaustion alerts, no-inbound population-need detection, cyclical halt diagnosis, and full dashboard KPIs are not implemented yet.
- Alerts are not yet severity-ranked planner advice. Existing warning output should be treated as a bug/anomaly surface only until the attention engine exists.

## Movement Data The Save Supports

- Mission performance: `deltaV`, `allFuelNeed`, `optimalFuelNeed`, fuel type, saved mission residual/onboard fuel, duration, percent complete, and days until arrival.
- Route mode: burst vs non-burst, constant acceleration support, transfer type, porkchop/grid selection, and saved constant-acceleration start position.
- Craft suitability: cargo capacity, fuel capacity, propulsion class, fuel resource, orbit-only/surface-capable, construction mode, maintenance, reusability, min/max flight-time factors, and continuous-burn flags.
- Capacity utilization: cargo mass used, free capacity, fuel tank utilization, cargo percentage, and partial/over-capacity flags.
- Surface access: launchcraft present by body, launch time, surface-to-orbit dependency, and any proven exceptions where cargo cannot complete its intended body delivery.
- Cyclical route details: cargo behavior at both endpoints, pause state, completed trip count, max trip count, end condition, transfer type, and assigned craft list.
- Local movement context: inbound cargo, outbound cargo, parked usable craft, local fuel, local market/inventory rows, and refuel/cargo-source feasibility.
- Crew movement context: cargo rows expose `crew`, `crewValue`, `moduleData`, `resourceType`, and `lifeSupportValue`, so crew compartments can be classified as loaded or empty across Type-S/Type-M/Type-L transports.
- Company-local resource storage: `objectInfoDatas` contains company-specific stock by object/resource, distinct from natural deposits in `ObjectInfoSaves`. This is the right source for usable destination fuel.
- Natural resource deposits: `ObjectInfoSaves.ListRowResourcesData` can identify surface/orbit deposits but should not be counted as immediately usable return fuel unless a company-owned stored-resource row exists.

## Dependency Stack

### Layer 0: Data Confidence

These are foundations that every dashboard view depends on.

- [Implemented] Normalize a shared mission fact table from active, planned, arrived, canceled, and cyclical mission records. Current `MissionFact` rows include company, mission key, mission type, raw record, craft IDs, route, status, date fields, timing metrics, cargo/fuel summaries, cargo/fuel mass, fuel resource, planned/optimal fuel, and transfer details.
- [Implemented] Normalize cargo fact rows from mission cargo, onboard craft cargo, fuel cargo, life support, crew modules, and direct human resources. Current `CargoFact` rows include company, source type, source key, mission context, craft IDs, object ID, cargo list, cargo kind, resource/module key, display name, mass, people, life-support value, crew-module flag, and raw row.
- [Implemented] Normalize body/object facts with object ID, display name, object type, parent/surface/orbit relationship, and company ownership where available. Current `ObjectFact` rows include object ID, display name, label, type, type ID, parent ID/name/label, relationship, surface/orbit flags, mining/path reference fields, visible company activity, present craft, inbound/outbound missions, next arrival, and raw object save data.
- [Implemented] Normalize craft facts with current object, active assignment, spacecraft type, cargo capacity, fuel capacity, propulsion class, surface/orbit capability, and launchcraft status. Current `CraftFact` rows include company, craft ID/name/type, current and true object IDs/labels, assignment key/status, mission context, route/timing, timing metrics, capacity metrics, cargo/fuel summaries and masses, planned/optimal fuel, live cargo/fuel capacity, capacity source, fuel type, propulsion class, construction mode, surface/orbit flags, continuous-burn flag, category, launchcraft status, transfer details, warning text, raw craft row, and raw mission row.
- [Implemented] Treat static spacecraft capacity references as fallback data only. The selected save's company `hullList` is now the first source for live cargo/fuel capacity; for example ESA `Hermes Hull` reports 300t cargo and 300t fuel while the older extracted reference table reports 80t/100t.
- [Implemented] Atomize the UI into a shared save-analysis context plus independent table modules. Current `fleet_modules` entries own columns, row shaping, pagination, and optional KPI metrics.
- [Implemented] Add Windows packaging scaffolding. Current package prep includes app path resolution, `%LOCALAPPDATA%` storage, save-dir override support, PyInstaller onedir spec, Windows build script, DPI-aware manifest, Inno Setup template, and IPC folder reservations.
- [Pending] Add parser smoke tests using a tiny fixture save plus one representative real save metadata fixture, including a regression check for live hull capacity.

### Layer 1: Operational Metrics

These turn raw facts into reusable planner measures.

- [Implemented] Mission timing metrics: departure, arrival, duration, percent complete, days until departure, days until arrival, and days since stale arrival. Current `TimingMetrics` rows are attached to `MissionFact` and inherited by assigned `CraftFact` rows while the Fleet Board keeps its compact timing text.
- [Implemented] Capacity metrics: cargo mass used, live save hull capacity where available, fallback reference capacity where not available, free capacity, cargo percent, planned total fuel, optimal fuel, saved residual/onboard fuel, fuel tank percent, and life support loaded. Current `CapacityMetrics` rows are attached to `CraftFact` and feed the existing Fleet Board cargo and fuel/tank summaries.
- [Implemented] Route metrics: active craft count, planned craft count, cargo tons in transit, people in transit, next departure, next arrival, attention count, and route status mix. Current `RouteMetric` rows are built from `CraftFact` and `CargoFact` rows and feed the Route Board; cargo/people totals include active and planned mission assignments, while moving/planned craft counts remain split.
- [Implemented] Body metrics: craft present, idle craft, active inbound craft, planned inbound craft, outbound craft, inbound cargo by resource/module, inbound people, outbound people, and next arrival. Current `BodyMetric` rows are built from `ObjectFact`, `CraftFact`, `CargoFact`, and `MissionFact` rows and feed the Body Board.
- [Implemented] Crew metrics: loaded people, empty seats, empty crew compartments, compartment type, reference seat capacity, and life-support carriage. Current `CrewMetric` rows are built from `CargoFact`, `CraftFact`, and transport-capacity reference data and feed the People Transit Board.
- [Implemented] Return-fuel metrics: fuel type, estimated return requirement, expected onboard fuel at arrival, compatible fuel carried as cargo, destination immediate fuel stock, destination surface fuel stock, lift-needed surface fuel, and immediate return-fuel margin. Current `ReturnFuelMetric` rows are built from `CraftFact`, `MissionFact`, `CargoFact`, `ResourceStockFact`, and `ObjectFact` rows and feed the Return Fuel Board.

### Layer 2: Attention Engine

These should produce planner-facing alert rows and attention badges used by every view. Alerts should be limited to things that plausibly block or invalidate the plan if time advances. Operationally normal states should stay visible as state, notes, or debug signals rather than warnings.

- [Pending] Fuel alerts: likely return-fuel shortfall at destination. Return-fuel warnings exist in the Return Fuel Board; shared alert rows do not. Do not compare mission `cargoFuel.cargoMass` directly to `allFuelNeed`; saved mission fuel is usually residual/onboard fuel after scheduling, not the launch requirement.
- [Not implemented] Capacity diagnostics: payload exceeds the craft cargo hold and route/craft capacity shortfall only where live save hull data makes that deterministic. This should be treated as parser/save-integrity or version-drift detection, not normal planner advice, because the in-game mission planner should block over-capacity launches.
- [Pending] Population alert export: consume the status produced by the population visualization/readiness layer and emit shared attention rows for critical housing, Supply runway, and life-support problems. Destination population need with no people inbound should wait for the population demand model.
- [Not implemented] Cyclical alerts: cyclical route is halted or paused because required cargo is missing, fuel is missing, or another deterministic blocking condition is visible in save data.
- [Not implemented] Staleness alerts: arrived mission still assigned, canceled mission still assigned, planned departure in the past, and mission records that appear stuck.
- [Not implemented] Bug-surfacing alerts: suspicious zero-mass cargo, malformed cargo rows, unknown object IDs, and other data anomalies. These should be labeled as possible save/parser bugs rather than logistics advice.

### Non-Alert State

These are useful to show, but should not count as warnings by themselves.

- [Implemented] Orbit-to-orbit and orbit endpoint operations. For most craft this is normal; ships may remain in orbit while cargo is delivered to the body surface. Only warn if a specific craft/route exception is proven from game data.
- [Implemented] Empty crew modules in transit. These are often legitimate restaging moves back to a population source and are surfaced as state in People Transit rather than warnings.
- [Implemented] Idle craft or craft in the "wrong" place unless the save provides deterministic evidence that a planned route cannot execute because of it.
- [Pending] Broad bottleneck patterns. They are useful, but should be introduced as structured planning analysis after the core fact/metric layer is stable.
- [Implemented] Surface fuel at an orbital destination. This is shown separately as "available after lift" rather than counted as immediate return fuel.
- [Implemented] Mission `cargoFuel.cargoMass` lower than `allFuelNeed`. The game sets saved mission fuel to leftover/onboard fuel in several paths, so this is informative state, not a launch-blocking alert.
- [Implemented] Payload higher than static reference capacity. Live save hull capacity is preferred, and static-reference over-capacity warnings are disabled.

### Return Fuel Estimator

This deserves its own estimator because it answers a different planning question than "can the current mission arrive?"

- [Implemented] Scope: active and planned missions with a real spacecraft assignment and a known fuel resource.
- [Implemented] Fuel type source: mission `cargoAllData.cargoFuel.resourceType`, falling back to spacecraft type fuel from the spacecraft reference data.
- [Implemented] Planned missions: loaded/saved special fuel minus required mission fuel, plus compatible fuel deliberately carried as cargo.
- [Implemented] En route missions: saved special fuel is treated as current onboard fuel; no additional future burn is subtracted.
- [Pending] Arrived/idle craft: helper logic can use current spacecraft `cargoAllData.cargoFuel.cargoMass`, but arrived/idle craft are not currently included because the estimator scope is active/planned assignments.
- [Implemented] Destination immediate fuel: same-company stored fuel on the destination object in `objectInfoDatas`.
- [Implemented] Destination surface fuel: if the destination is an orbit, same-company stored fuel on the parent surface body is shown in a separate "needs lift" bucket.
- [Implemented] Natural deposits: deposits from `ObjectInfoSaves` are not counted as available fuel.
- [Implemented] High return requirement confidence: explicit planned reverse mission or cyclical return leg for that craft/route.
- [Implemented] Medium return requirement confidence: recent/historical reverse leg for same craft type and route pair.
- [Implemented] Low return requirement confidence: symmetric estimate using the outbound `allFuelNeed`.
- [Implemented] Immediate margin formula: `expected_onboard_at_arrival + compatible_arriving_fuel_cargo + destination_immediate_stock - estimated_return_requirement`.
- [Implemented] Deferred margin formula: `immediate_margin + destination_surface_stock`, clearly labeled as requiring lift to orbit first.
- [Implemented] Alert only when immediate margin is negative. Surface fuel can downgrade severity if enough exists but does not make the alert disappear.
- [Implemented] Warning interrogation: the Return Fuel Board warning cell exposes the return need, arrival fuel basis, fuel cargo, immediate stock, surface stock, and both margins in a tooltip.

### Layer 3: Population Visualization Dashboard

These are the highest-value next visuals because population movement has the most compound failure modes: transport capacity, arrival timing, housing, habitat cargo, surface Supply production, stock runway, and local save-derived consumption modifiers.

- [Implemented] Add visualization dependencies and helpers: Plotly and NetworkX are now runtime/package dependencies, PyInstaller hidden imports are prepared, and `fleet_modules.population_dashboard` owns chart helpers outside the table modules.
- [Implemented] Split the population section into discrete surfaces: `/population` hub, `/population/movement`, and `/population/places`.

#### Layer 3 MVP

- [Pending] Extract movement and places aggregate rows from the scaffold into reusable data contracts.
- [Pending] Finish Movement KPI Strip, Destination Readiness Matrix, Supply Runway Burndown, Housing Stack / Gap, and Colonies / Stations Sustainment using already-normalized facts and explicit tooltip data.
- [Not implemented] Add scalable chart controls, Risk Focus ranking, "Other" aggregation, status-first sorting, and hover-first labels before adding more high-density charts.
- [Pending] People Transit drill-down integration from movement dashboard rows into grouped flight/module rows.

#### Layer 3 RC

- [Pending] Upgrade Population Flow Sankey and Population Arrival Timeline hover/drill-down behavior.
- [Not implemented] Add population sustainment scatter/bubble and heatmap as high-count replacements for wide bar charts.
- [Pending] Add Population Balance by Body using local population, empty outbound seats, inbound people, housing, queued/carried habitat, and Supply runway.
- [Not implemented] Add Flight Cohort Cards / Manifest Treemap as the visual drill-down for grouped People Transit rows.
- [Not implemented] Add Colonization Site Prep / Watchlist for preferred future colony targets, combining user-marked places with auto-detected sites that have colonization-support cargo or stock already present/inbound.

#### Layer 3 Stretch

- [Not implemented] Life-support exhaustion overlay after consumption math is validated.
- [Not implemented] No-inbound population need panel after a trustworthy demand model exists.
- [Not implemented] Route Lane Map for People after route-level aggregates and graph interaction design are stable.
- [Not implemented] Colony growth/demand modeling for construction completion, workforce, power, local production, and market demand.

### Layer 4: Cargo Transit Visualization Dashboard

Cargo transit is the next logistics surface after population because the core facts already exist. It should focus on route timing and manifest visibility, then later join into production shortfall questions.

#### Layer 4 MVP

- [Not implemented] Scaffold `/cargo` as a section hub for cargo movement, with a Cargo KPI Strip, Cargo In-Transit Matrix, Cargo Arrival Schedule, Destination Receipts Panel, and grouped manifest drill-down table.
- [Not implemented] Extract reusable cargo flight/manifest aggregate rows from `CargoFact`, `MissionFact`, `CraftFact`, and `RouteMetric` so chart code does not re-group raw facts.
- [Not implemented] Add scalable cargo filters: company, status, resource/module type, source, destination, route, arrival window, and concerns-only.

#### Layer 4 RC

- [Not implemented] Add Cargo Flow Sankey and Commodity Arrival Calendar.
- [Not implemented] Add Cargo Route Saturation View where live craft capacity and route timing make the estimate deterministic enough.
- [Not implemented] Join selected commodity views to production stock/net rows so inbound cargo can be interpreted against destination need.
- [Not implemented] Add destination-filtered cargo evidence links for Colonization Site Prep, including support-cargo classification and arrival dates.

#### Layer 4 Stretch

- [Not implemented] Add Cargo Demand Gap Estimator after production shortage and construction-queue demand signals are validated.
- [Not implemented] Add Surface-to-Orbit Cargo Staging View for fuel/cargo that exists on a surface but needs lift before a route can use it.
- [Not implemented] Add What-if Cargo Move Planner.

### Layer 5: Production Visualization Dashboard

Production is a separate section from cargo transit. It should begin as a save-grounded stock/flow dashboard using `ResourceStockFact` values, then later absorb facility formulas and construction impact once validated.

#### Layer 5 MVP

- [Not implemented] Scaffold `/production` as a section hub for resource stock, intake, outtake, net/day, and runway.
- [Not implemented] Extract reusable production balance rows from `ResourceStockFact` plus object metadata, including stock, intake, outtake, net/day, runway, object type, and company.
- [Not implemented] Add Production KPI Strip, Stock and Flow Heatmap, Production Balance Bars, Runway Risk Focus, and Resource Stock Drill-Down Table.

#### Layer 5 RC

- [Not implemented] Add Commodity Detail Dashboard that joins local production/stock with inbound and outbound cargo timing.
- [Not implemented] Add Exporter / Importer Map by selected resource.
- [Not implemented] Add Construction Queue Impact Panel where saved build progress and facility/module data are reliable.
- [Not implemented] Add Candidate Site Stock Summary and cross-links from Colonization Site Prep into destination-filtered production/resource views.
- [Not implemented] Export deterministic production/runway concerns to the shared attention engine.

#### Layer 5 Stretch

- [Not implemented] Add Facility-Level Production Graph after facility/refinery/mine data and formulas are validated.
- [Not implemented] Add Power / Workforce / Facility Constraint Model.
- [Not implemented] Add Production What-if Planner.

### Layer 6: General Dashboard MVP

These broaden the dashboard after the population logistics surface has a dependable data layer.

- [Pending] Overview/index route with KPI tiles for active missions, planned departures, people in transit, empty crew holds, return-fuel shortfalls, next arrival, next departure, idle craft, needs-attention count, and fuel/life-support concern missions. Basic sectioned overview exists; several KPI sources are still pending.
- [Not implemented] Alerts Feed using the attention engine, sorted by severity and date.
- [Not implemented] Mission Timeline using Plotly, built from the mission fact table and attention engine.
- [Pending] Route Load Matrix using route metrics. Source metrics exist; visualization does not.
- [Pending] Body Readiness strip using body metrics for the most important bodies by current activity. Source metrics exist; dashboard cards do not.
- [Not implemented] Topline cargo and production KPIs only after `/cargo` and `/production` have stable aggregate rows; the index should remain a launcher plus global status, not a chart gallery.

### Layer 7: Drill-Down Enhancements

These improve the existing tables after the dashboard has a dependable data layer.

- [Pending] Fleet Board: next-free date, active assignment, stale-arrived mission detection, stranded/idle flags, and launchcraft/surface capability indicators. Some source fields exist; the board columns and alert semantics are incomplete.
- [Pending] Route Board: throughput, round-trip/cycle timing, cyclical route controls/details, route attention rollups, and bottleneck analysis. Route rollups exist; cycle details and bottleneck analysis do not.
- [Pending] Body Board: inbound/outbound cargo by resource/module, parked craft, parked launchcraft, local fuel split by company/orbit/surface, local inventory/market context, and refuel/cargo-source feasibility. Basic inbound/outbound and stock facts exist; feasibility and inventory context do not.
- [Not implemented] Cargo Board: grouped flight manifests, commodity filters, inbound/outbound context, and links to cargo visualization rows.
- [Not implemented] Production Board: stock/intake/outtake rows, runway calculations, object/resource filters, and links to production visualization rows.
- [Implemented] Return Fuel Board: craft arriving soon, estimated return fuel need, arrival onboard fuel, immediate fuel at destination, surface fuel at destination, immediate/deferred margin, confidence, warning state, and tooltip interrogation.

### Layer 8: Advanced Planning

These are valuable but should wait until the population dashboard, general dashboard, and attention engine are stable.

- [Not implemented] Solar Logistics Map with route graph analysis and interactive route/body selection.
- [Not implemented] Local fuel/inventory feasibility for planned routes, including surface-to-orbit fuel staging.
- [Not implemented] Launchcraft and surface-access board.
- [Not implemented] Scenario layer for what-if route additions, cargo moves, and population transfers.
- [Not implemented] Colony planner integration for housing, workforce, power, construction queues, local production, and market demand.

## Recommended Next Implementation Order

### MVP

1. [Pending] Extract movement and places aggregate rows from the dashboard scaffold into reusable data contracts.
2. [Pending] Add chart-click drill-down links from Movement KPI Strip, Destination Readiness Matrix, Sankey, and timeline into People Transit.
3. [Pending] Upgrade Supply Runway Burndown and Housing Stack scaffolds with threshold annotations and final waterfall treatment.
4. [Not implemented] Add scalable population chart controls: ranked slices, "Other" aggregation, status-first sorting, hover-first labels, and filters for concerns/company/type/inbound/housing/runway/population.
5. [Not implemented] Add Risk Focus ranking and "Other" aggregation so current bar/scaffold charts stay compact as colony counts grow.
6. [Not implemented] Scaffold `/cargo` with reusable cargo aggregate rows, Cargo KPI Strip, Cargo In-Transit Matrix, Cargo Arrival Schedule, Destination Receipts Panel, and grouped manifest drill-down.
7. [Not implemented] Scaffold `/production` with reusable production balance rows, Production KPI Strip, Stock and Flow Heatmap, Production Balance Bars, Runway Risk Focus, and Resource Stock Drill-Down Table.

### RC

1. [Not implemented] Replace high-count colonies/stations bar views with sustainment scatter/bubble and heatmap views before colony counts grow beyond what compact bars can explain.
2. [Pending] Upgrade Population Flow Sankey hover details and route grouping.
3. [Pending] Add Population Arrival Timeline drill-down behavior and Flight Cohort Cards as the visual manifest.
4. [Pending] Add Population Balance by Body and People Transit drill-down links.
5. [Not implemented] Add Colonization Site Prep / Watchlist after cargo and production aggregate rows exist, with user-marked preferred targets plus auto-detected support cargo/stock candidates.
6. [Not implemented] Add Cargo Flow Sankey, Commodity Arrival Calendar, support-cargo classification, destination evidence links, and Cargo-to-Production selected-resource joins.
7. [Not implemented] Add Commodity Detail Dashboard, Exporter / Importer Map, Candidate Site Stock Summary, Construction Queue Impact Panel, and production alert export.

### Stretch

1. [Pending] Upgrade Colonies / Stations sustainment into a full growth dashboard with demand, queued construction completion, workforce, power, and supply planning.
2. [Not implemented] Add life-support exhaustion overlays after consumption math is validated.
3. [Not implemented] Add no-inbound population need detection once the destination demand model is trustworthy.
4. [Not implemented] Add Route Lane Map for People after route-level aggregates and graph interaction design are stable.
5. [Not implemented] Add Cargo Demand Gap Estimator, Surface-to-Orbit Cargo Staging View, and What-if Cargo Move Planner.
6. [Not implemented] Add Facility-Level Production Graph, Power / Workforce / Facility Constraint Model, and Production What-if Planner.

### General / Cross-Cutting

1. [Not implemented] Add the attention engine with severity, message, affected mission/craft/body/route, and suggested drill-down target.
2. [Pending] Add general dashboard KPI tiles and Alerts Feed from the new metrics/attention rows.
3. [Implemented] Keep future boards/dashboard panels on the `SaveAnalysis` plus `fleet_modules` pattern so new views do not rewire the app shell.
