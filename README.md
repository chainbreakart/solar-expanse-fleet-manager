# Solar Expanse Fleet Manager

Solar Expanse Fleet Manager is a read-only companion dashboard for **Solar Expanse** save files. It opens local save data, defaults to the newest detected save, and helps you inspect fleet movement, population logistics, cargo transit, production, and technology effects without writing back to the game.

This is an early public preview. It is meant for logistics inspection and validation, not save editing.

## Current Features

- Automatic save discovery for standard Windows/WSL Solar Expanse save locations.
- Sticky save selection while navigating between dashboard sections.
- Player-company-first filtering, with a de-emphasized toggle for AI/WG company data.
- Overview page with top-line save context, operations status tiles, next arrival/departure, idle craft, and needs-attention count.
- Population dashboards for people in transit, destination readiness, housing, Supply runway, and place sustainment.
- Cargo dashboards split into Overview, Movement, Receipts, and Manifests so route timing, destination receipts, and raw cargo inspection stay separate.
- Cargo support classification for colony-start evidence such as Supply, habitat/crew modules, outpost/build modules, compatible fuel, and common construction resources.
- Production dashboard with stock, intake, outtake, net flow, runway focus, balance bars, heatmap modes, sustainment watchlist, and candidate-site stock summaries.
- Technology dashboard showing focused-save research unlocks, active/queued research, unlocked spacecraft/buildables, and tech modifiers currently used by planner math.
- Shared attention rows for return fuel, population readiness, capacity diagnostics, and save/parser anomalies.
- Data tables for fleet, routes, bodies, people transit, return-fuel estimates, technology, and attention rows.
- Hard sci-fi command console visual theme.

## Install From Source

Requires Python 3.11 or 3.12 x64.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The app starts a local NiceGUI server, usually at:

```text
http://localhost:8080
```

## Save Discovery

By default, the app looks for saves in the usual Solar Expanse LocalLow save folder. You can override discovery with:

```bash
SOLAR_EXPANSE_SAVE_DIR="/path/to/Saves" python app.py
```

The app is read-only and does not modify save files.

## Status

This repo contains the public app runtime and reference data needed for the current dashboards. Internal planning notes, tests, scratch workspaces, packaging scripts, build outputs, save files, logs, and local installer artifacts are intentionally not included.

## Disclaimer

Solar Expanse Fleet Manager is an unofficial fan-made companion tool and is not affiliated with or endorsed by the creators of Solar Expanse.
