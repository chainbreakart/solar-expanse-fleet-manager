# Windows Packaging

Target stack:

- UI: NiceGUI
- Visualization: Plotly first, with NetworkX reserved for future graph layout
- Theme assets: bundled command-console CSS under `assets`
- Runtime: Python 3.11/3.12 x64
- Packaging: PyInstaller onedir first
- Installer: Inno Setup initially; WiX/NSIS/MSIX can be added later by audience
- Storage: `%LOCALAPPDATA%\SolarExpanseFleetManager`
- IPC: reserved app-data IPC folder, localhost NiceGUI API surface, and future CLI/file handoff

## Build Onedir

Run this from Windows PowerShell at the standalone project root:

```powershell
packaging\windows\build_onedir.ps1
```

The output lands in:

```text
dist\SolarExpanseFleetManager\
```

The executable remains console-enabled for the first packaging pass so server errors are visible.
Switch PyInstaller `console=False` after the packaged app is stable.

## Build Installer

Install Inno Setup, build the onedir package, then compile:

```powershell
iscc products\apps\fleet_manager\packaging\windows\innosetup\SolarExpanseFleetManager.iss
```

For the standalone public repo, use:

```powershell
iscc packaging\windows\innosetup\SolarExpanseFleetManager.iss
```

The installer output lands in:

```text
dist\installer\
```

The Inno Setup installer executable can be staged in `dist\installer\` for public version drops. The PyInstaller onedir output is build output and should not be committed.

The Inno template is currently a per-user install under `%LOCALAPPDATA%\Programs\Solar Expanse Fleet Manager`.

## Runtime Paths

- Save discovery checks `SOLAR_EXPANSE_SAVE_DIR` first.
- App storage checks `FLEET_MANAGER_DATA_DIR` first, then `%LOCALAPPDATA%\SolarExpanseFleetManager`.
- The bundled app data root comes from PyInstaller's `_MEIPASS`; development uses the repository root.

## Installer Choice

- Inno Setup: best first choice for a personal/modding companion app.
- WiX: better for managed enterprise installs and MSI workflows.
- NSIS: useful for a highly customized lightweight installer.
- MSIX: useful for store-like distribution, signed packages, and tighter Windows integration.
