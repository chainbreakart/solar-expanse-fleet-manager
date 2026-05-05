# Changelog

## 0.11.0 - Evidence Console Update

This release turns Fleet Manager from a set of useful dashboards into a more complete read-only logistics evidence console. It is still a local, source-install companion app: create a Python virtual environment, install `requirements.txt`, run `python app.py`, and inspect your saves in the browser.

### Features

- Added a command-console overview with global operations tiles for active missions, planned departures, next arrival, next departure, idle craft, and needs-attention count.
- Split Cargo into focused workflows: Overview, Movement, Receipts, and Manifests.
- Added cargo arrival, in-transit, destination receipt, and manifest views with scalable filters.
- Added colonization-support cargo classification for Supply, habitat/crew modules, outpost/build modules, compatible fuel, and construction resources.
- Added cargo-to-production evidence links so destination receipts can be compared with local stock, net flow, and runway.
- Expanded Production with sustainment watchlists, candidate-site stock summaries, clearer heatmaps, balance/runway views, and drill-down evidence.
- Added Technology parsing and a Technology dashboard for completed research, active/queued research, unlocked spacecraft/buildables, and modifiers used by app calculations.
- Applied known technology modifiers to capacity, transport seats, production, and life-support/Supply calculations where currently modeled.
- Added Attention rows for fuel, population readiness, capacity diagnostics, and save/parser anomalies.
- Improved Population section organization with separate Movement and Place Sustainment workflows.
- Added live save hull-capacity matching with generated spacecraft aliases, including support for renamed hull variants.

### Fixes

- Reload now rescans the save directory while the app is already running, so newly copied saves can appear without restarting.
- The paired `.info.gz` sidecar is used as the authoritative player-company source when available.
- Fixed cargo KPI duplication by making Cargo subsection KPI strips context-sensitive.
- Fixed tech-upgraded hull capacity so known cargo capacity bonuses are reflected in planner-facing values.
- Treated Orbital Payload Containers with special semantics: the nominal capacity is shown as a reference, upward movement is launch-limited, and orbit-to-surface delivery is not treated as a hard capacity problem.
- Added parser smoke coverage for save discovery, player-company inference, live hull capacity, technology modifiers, dashboard rows, and app reload behavior.

### Notes

- This release intentionally includes only the standalone app runtime and reference data needed to run from source.
- Internal planning notes, tests, scratch workspaces, packaging scripts, build outputs, logs, save files, and installer artifacts are not included.
- The app remains read-only and does not edit or write save files.

## 0.1.0 - Public Preview

Initial public release branch.

### Added

- Read-only NiceGUI companion app for local Solar Expanse saves.
- Automatic latest-save loading with sticky manual save selection across pages.
- Player-company-first filtering with an optional AI/WG company toggle.
- Overview section for global save and fleet top lines.
- Population section with movement and colony/station dashboards, including destination readiness, housing, inbound people, supply runway, and status tooltips.
- Cargo section with KPI strip, compact route summary cards, and grouped manifest drill-down table.
- Production section with resource stock/flow KPIs, runway focus, production balance bars, stock/flow table, and heatmap modes for balance, risk, exporter, volume, and stock focus.
- Data Tables section for fleet, routes, bodies, people transit, and return fuel inspection.
- Return fuel estimator using save-grounded route and fuel stock signals.
- Reusable info tooltip primitives for dashboard modes and explanations.
- Command-console stylesheet and responsive layout refinements.

### Notes

- This release does not include installer packaging scripts or internal planning documents.
- The app does not edit or write save files.
