# Solar Expanse Fleet Manager

Solar Expanse Fleet Manager is a read-only companion dashboard for **Solar Expanse** save files. It opens local save data, defaults to the newest detected save, and helps you inspect fleet movement, population logistics, cargo transit, and resource production without writing back to the game.

This is an early public preview. It is meant for planning and inspection, not save editing.

## Current Features

- Automatic save discovery for standard Windows/WSL Solar Expanse save locations.
- Sticky save selection while navigating between dashboard sections.
- Player-company-first filtering, with a de-emphasized toggle for AI/WG company data.
- Overview page with top-line save and fleet indicators.
- Population dashboards for people in transit, destination readiness, housing, supply runway, and colonies/stations.
- Cargo transit dashboard with route KPIs, route cards, and grouped manifest drill-downs.
- Production dashboard with stock, intake, outtake, net flow, runway focus, balance bars, and stock/flow heatmap modes.
- Data tables for fleet, routes, bodies, people transit, and return-fuel estimates.
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

This repo contains the public app runtime and reference data needed for the current dashboards. Internal planning notes, packaging scripts, build outputs, and local installer artifacts are intentionally not included.

## Disclaimer

Solar Expanse Fleet Manager is an unofficial fan-made companion tool and is not affiliated with or endorsed by the creators of Solar Expanse.
