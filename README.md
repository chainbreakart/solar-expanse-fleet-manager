# Solar Expanse Fleet Manager

Solar Expanse Fleet Manager is a read-only companion dashboard for **Solar Expanse** save files. It opens local save data, defaults to the newest detected save, and helps you inspect fleet movement, population logistics, cargo transit, production, and technology effects without writing back to the game.

This is an early public preview. It is meant for logistics inspection and validation, not save editing.

## Questions, Feedback, And Roadmap

Start with [GitHub Discussions](https://github.com/chainbreakart/solar-expanse-fleet-manager/discussions) if you are not sure whether something is a bug, feature request, save-specific edge case, or general question. The [Start here discussion](https://github.com/chainbreakart/solar-expanse-fleet-manager/discussions/65) is the best first stop for confusing warnings, logistics assumptions, install trouble, and early feature ideas.

Use [Issues](https://github.com/chainbreakart/solar-expanse-fleet-manager/issues) for confirmed, focused work once there is enough detail to track a fix or feature. Maintainers may promote a discussion into an issue when it becomes actionable. The public roadmap lives in the [Fleet Manager Roadmap project](https://github.com/users/chainbreakart/projects/1).

Please do not post private save files publicly. Screenshots, dashboard names, expected vs. actual behavior, and the Fleet Manager version are usually enough to start.

## Current Features

- Automatic save discovery for standard Windows/WSL Solar Expanse save locations.
- Sticky save selection while navigating between dashboard sections.
- Player-company-first filtering, with a de-emphasized toggle for AI/WG company data.
- Overview page with top-line save context, operations status tiles, next arrival/departure, idle craft, and needs-attention count.
- Fleet Control dashboard for ship inventory, idle/active/planned craft, locations, assignment state, cargo, crew, fuel context, warnings, and source links.
- Population dashboards for people in transit, destination readiness, housing, Supply runway, and place sustainment.
- Cargo dashboards split into Overview, Movement, Receipts, and Manifests so route timing, destination receipts, and raw cargo inspection stay separate.
- Cargo support classification for colony-start evidence such as Supply, habitat/crew modules, outpost/build modules, compatible fuel, and common construction resources.
- Production dashboards with stock, intake, outtake, net flow, runway focus, balance bars, heatmap modes, sustainment watchlists, candidate-site stock summaries, and resource opportunity rows.
- Technology dashboard showing focused-save research unlocks, active/queued research, unlocked spacecraft/buildables, and tech modifiers currently used by planner math.
- Shared attention rows for return fuel, population readiness, capacity diagnostics, and save/parser anomalies.
- Data tables for fleet, routes, bodies, people transit, return-fuel estimates, technology, and attention rows.
- Hard sci-fi command console visual theme.

## Windows Installer

Windows users can download the latest `SolarExpanseFleetManager-Setup-...-x64.exe` from the GitHub Releases page:

```text
https://github.com/chainbreakart/solar-expanse-fleet-manager/releases
```

The installer adds Start Menu shortcuts for the normal desktop app, Browser Mode, port configuration, and logs. Use the normal **Solar Expanse Fleet Manager** shortcut first. If the app does not open, use **Solar Expanse Fleet Manager (Browser Mode)** to run the same local server in your browser, **Configure Fleet Manager Port** to change the port or strict-port behavior, and **Open Fleet Manager Logs** to inspect startup output.

The installed app keeps local state under `%LOCALAPPDATA%\SolarExpanseFleetManager` and does not write to save files.

## Install From Source

Requires Python 3.11 or 3.12 x64.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python desktop_launcher.py
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python desktop_launcher.py
```

The desktop launcher starts a local NiceGUI server and opens Fleet Manager in a standalone window when the platform supports `pywebview`. If the window cannot be created, it falls back to opening the app in your browser. If the server cannot start, the launcher shows a recovery window with the port config path, log path, and last server output. Direct browser/server mode is still available with `python app.py`.

The tray menu can open the app, open the browser URL, copy the URL, restart or stop the local server, open logs, and open the port configuration file.

The local server usually runs at:

```text
http://localhost:8080
```

If port `8080` is already in use, the app does not stop or overwrite the existing listener. It starts on the next free nearby port and opens the resolved URL through the desktop launcher or browser mode. To choose a port manually:

```powershell
$env:FLEET_MANAGER_PORT="8090"
python app.py
```

To make port contention fail fast instead of falling back:

```powershell
$env:FLEET_MANAGER_STRICT_PORT="1"
python app.py
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
