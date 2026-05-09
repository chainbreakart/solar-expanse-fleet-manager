# Changelog

## 0.11.2 - Desktop Startup Hotfix

This hotfix release corrects a desktop-launcher readiness bug that could show the recovery screen even after the local NiceGUI server had already started successfully.

### Fixes

- The desktop launcher now recognizes NiceGUI's own `NiceGUI ready to go on ...` startup message as a successful server URL.
- The startup readiness check now uses a lightweight local port connection instead of an HTTP page request, avoiding noisy Windows connection-reset errors during launch.

### Notes

- This release is intended for Windows users who saw "Fleet Manager could not start" while the recovery window also showed `NiceGUI ready to go on http://127.0.0.1:8080`.
- The app remains read-only and does not edit or write save files.

## 0.11.1 - Windows Desktop and Fleet Control Update

This patch release makes Fleet Manager easier to run on Windows and promotes ship inventory into a first-class Fleet Control workflow. The app is still a local, read-only save companion, but Windows users can now start from an installer instead of building from source.

### Features

- Added a Windows x64 installer as a GitHub release asset.
- Added a desktop launcher that owns the local Fleet Manager server and opens the app in a standalone window.
- Added a system tray controller with Open Fleet Manager, Open in Browser, Copy URL, Restart Server, Stop Server, Change Port / Configure Port, Open Logs, and Quit.
- Added Start Menu recovery shortcuts for Browser Mode, port configuration, and logs.
- Added local app-data storage for desktop launcher config and logs under `%LOCALAPPDATA%\SolarExpanseFleetManager`.
- Added a first-class Fleet Control tab for ship inventory, idle/active/planned craft, locations, assignment state, cargo, crew, fuel context, warnings, and source links.
- Added Fleet Control filtering and sorting for company, ship status, location, hull/type, idle state, cargo present, crew/passenger context, warning state, and assignment state.
- Added cross-domain drill-downs between Fleet, Cargo, Route, Return Fuel, Body/location, and Data Tables rows.
- Added Production Opportunities for material shortages, known candidate locations, and no-spoiler resource evidence handoff into colony-planning decisions.
- Added broader audit panes and exact row-filter links across Cargo, Production, and Technology so dashboard numbers can be traced back to source rows.

### Fixes

- Port `8080` contention now has a user-facing recovery path: Fleet Manager falls back to the next available nearby port by default, and strict-port mode reports a clear error when requested.
- The installed app now launches as a windowed application instead of leaving a command prompt window open in the background.
- The desktop launcher cleans up its owned server process on restart, stop, quit, or window close.
- Installer validation now covers clean startup, busy-port fallback, strict-port failure messaging, browser mode, installed-app startup, and uninstall cleanup.
- Arrived historical missions no longer show as main attention warnings.
- Cargo, Production, Technology, and Fleet drill-down links now land closer to the specific evidence rows behind each dashboard summary.

### Notes

- The installer is attached to the GitHub release. Packaging scripts and build scratch remain outside the public source tree.
- Source installs are still supported with `python desktop_launcher.py`, and direct browser/server mode remains available with `python app.py`.
- The app remains read-only and does not edit or write save files.

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
