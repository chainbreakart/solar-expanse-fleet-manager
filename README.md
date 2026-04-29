# Solar Expanse Fleet Manager

Lightweight local companion app for reading Solar Expanse saves and showing fleet state.

## Current MVP

- Defaults to the newest `.json.gz` save in the standard Windows/WSL save folder.
- Lets you switch to any paired save in that folder.
- Parses the game's Odin-style JSON-ish save payload.
- Defaults every board/dashboard to the player corporation only, using the paired `.info.gz` `SaveInfo.startGameConfiguration.Company` as the authoritative source when present, with a muted opt-in toggle for AI and World Government data.
- Shows spacecraft, current object ID, mission route/status, ETA, cargo, fuel, and cyclical route tags.
- Provides basic Fleet, Route, Body, People Transit, and Return Fuel boards for movement planning.
- Keeps `/` as a quiet overview with top-line KPIs and section navigation.
- Splits population planning into `/population` as a small section hub, `/population/movement` for people in transit, and `/population/places` for colonies/stations sustainment.
- Scaffolds `/population/movement` with KPI cards, a destination readiness matrix, first-pass Plotly visuals for Supply runway, housing readiness, population flow, and arrival timing, plus a People Transit drill-down table.
- Scaffolds `/population/places` with people-in-place KPIs, a colonies/stations table, chart controls, Supply balance, housing/occupancy, and current Supply runway visuals.
- Uses `assets/command_console.css` for the hard sci-fi command-console visual theme, with responsive panel/table/chart containers for dynamic save content.
- Adds early operational columns for mission timing, fuel/capacity use, transfer details, and warnings.
- Tracks crew-capable cargo on active/planned missions in collapsible flight rows, including loaded people, crew compartment type, reference seats, empty seats, empty crew compartments, and mission life-support carriage.
- Shows destination readiness for inbound people as tooltip-aware `Safe`, `Warning`, `Urgent`, or `Critical`, using detected housing, queued housing, habitat cargo arriving with/before the people, Supply stock, Supply production/use, a save-derived local Supply modifier, and projected burndown.
- Estimates return-fuel margin for active/planned craft from saved fuel, compatible fuel cargo, and same-company destination stock, with separate surface stock only when the destination is an orbit.

## App Shape

- `app.py` is the NiceGUI shell: save picker, section routing, table mounting, and top-level status/KPIs.
- `assets/command_console.css` is the reference-driven app stylesheet.
- `/` is the overview/index surface and should stay limited to top-line status plus navigation.
- `/population` is the first domain dashboard section hub and links to the population movement and colonies/stations subsections.
- `/population/movement` owns people-in-transit visuals plus People Transit drill-downs.
- `/population/places` owns people-in-place, colony growth, and sustainment visuals.
- `/data` keeps the full tabbed Fleet, Route, Body, People Transit, and Return Fuel table workspace.
- `fleet_core.analysis` loads a selected save once and assembles the shared fact/metric bundle.
- `fleet_core.analysis` also classifies company roles from `.info.gz` and save data: player corporation, AI companies, World Government, confidence/source notes, and the currently selected company scope. Filename text is never used as player identity; `.json.gz`-only saves are marked inferred and keep the default scope narrow.
- `fleet_core.normalizer` owns parser-to-fact normalization and reusable metrics.
- `fleet_modules` owns view modules. Each module declares its table columns, row builder, pagination, and optional KPI updates.
- `fleet_modules.population_dashboard` owns the first visualization surface and chart-ready population logistics joins.
- New planner surfaces should usually start as a new `fleet_modules/*.py` module that consumes `SaveAnalysis`.
- `fleet_core.app_paths` centralizes packaged/development resource roots, save discovery, app storage, and localhost settings.

## Windows Packaging

The app is scaffolded for a Windows x64 companion-app build:

- Python 3.11/3.12 x64 runtime.
- PyInstaller `onedir` first, with bundled CSV/reference data.
- Inno Setup installer template.
- App state under `%LOCALAPPDATA%\SolarExpanseFleetManager` by default.
- IPC staging under the app-data `ipc` folder, plus configurable localhost host/port.

See [packaging/windows/README.md](./packaging/windows/README.md).

## Run

From the standalone project root:

```bash
python3 -m venv .venv-fleet
source .venv-fleet/bin/activate
pip install -r requirements.txt
python app.py
```

Then open the URL printed by NiceGUI, usually `http://127.0.0.1:8080`.

When developing from the larger research/workbench repo, run the same commands from `products/apps/fleet_manager` or use:

```bash
pip install -r products/apps/fleet_manager/requirements.txt
python products/apps/fleet_manager/app.py
```

## Notes

The main game save is not strict RFC JSON. It includes `$fstrref:"..."` references and typed value objects with unkeyed scalar entries. The MVP parser handles enough of that format to build a useful read-only fleet view without depending on Unity or the game assemblies.

See [PLANNER_BACKLOG.md](./PLANNER_BACKLOG.md) for the movement-planning features identified but not fully built yet.
