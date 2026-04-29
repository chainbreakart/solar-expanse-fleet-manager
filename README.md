# Solar Expanse Fleet Manager

A read-only companion app for **Solar Expanse** saves. It helps you inspect fleet movement, people in transit, colony/station sustainment, and return-fuel readiness without opening every in-game panel one by one.

The app never writes to your save files.

## Current State

This is an early preview. It is useful today for save inspection and planning, but it is still evolving quickly.

What works now:

- Automatically finds Solar Expanse saves in the standard Windows save folder, including from WSL.
- Opens the newest save by default and lets you switch saves from the UI.
- Reads the paired `.info.gz` sidecar to identify the active player corporation when available.
- Defaults views to the player corporation only, with an optional AI / World Government toggle.
- Shows an overview with top-line movement and planning metrics.
- Provides a Population section split into people movement and colonies/stations sustainment.
- Provides detailed data tables for fleet, routes, bodies, people transit, and return-fuel checks.
- Resolves known object IDs into readable body/orbit names.
- Estimates destination readiness for inbound people using detected housing, queued housing, carried habitat capacity, Supply stock, Supply flow, and projected Supply runway.
- Estimates whether active/planned craft may have enough fuel available at destination for a later return leg.

What is still rough:

- This is not a full colony planner yet.
- Dedicated cargo and production dashboards are not included yet.
- Some estimates depend on save data that the game exposes indirectly, so the UI tries to show the source numbers rather than pretending every warning is certain.
- The parser supports the save structures needed by the current app, but Solar Expanse updates can change save internals.

## Run From Source

Requirements:

- Python 3.11 or 3.12
- A local Solar Expanse save folder

From this project folder:

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

Then open the URL printed by NiceGUI, usually:

```text
http://localhost:8080
```

## Save Discovery

By default, the app looks for saves under:

```text
%USERPROFILE%\AppData\LocalLow\SpaceOps\Solar Expanse\Saves
```

You can override the save folder with:

```bash
SOLAR_EXPANSE_SAVE_DIR=/path/to/Saves python app.py
```

PowerShell:

```powershell
$env:SOLAR_EXPANSE_SAVE_DIR = "C:\Path\To\Saves"
python app.py
```

## Privacy And Safety

- The app is local-first and read-only.
- It does not upload save files.
- Save files are ignored by this repository and should not be committed.
- The app uses local reference CSVs for names, capacities, and first-pass planning metadata.

Solar Expanse is developed by SpaceOps. This is an unofficial companion tool.
