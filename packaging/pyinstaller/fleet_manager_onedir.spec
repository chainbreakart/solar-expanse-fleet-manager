# Run from the repository root:
#   pyinstaller --clean --noconfirm products/apps/fleet_manager/packaging/pyinstaller/fleet_manager_onedir.spec

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None
spec_path = Path(SPECPATH)
monorepo_root = spec_path.parents[4] if len(spec_path.parents) >= 5 else None
if monorepo_root and (monorepo_root / "products" / "apps" / "fleet_manager" / "app.py").exists():
    project_root = monorepo_root
    app_root = project_root / "products" / "apps" / "fleet_manager"
else:
    project_root = spec_path.parents[1]
    app_root = project_root


def data_file(source: Path, dest: str):
    return (str(source), dest)


datas = [
    data_file(app_root / "assets" / "command_console.css", "assets"),
    data_file(app_root / "data" / "object_id_reference.csv", "data"),
    data_file(project_root / "generated_data" / "data_buildables.csv", "generated_data"),
    data_file(project_root / "generated_data" / "spacecraft_base_reference.csv", "generated_data"),
    data_file(project_root / "data" / "derived" / "population" / "resources.csv", "data/derived/population"),
    data_file(project_root / "data" / "derived" / "population" / "habitat_capacities.csv", "data/derived/population"),
]

optional_object_stock = project_root / "inspect" / "economy_equilibrium" / "outputs" / "solar_system_carbon_stock_by_object.csv"
if optional_object_stock.exists():
    datas.append(data_file(optional_object_stock, "inspect/economy_equilibrium/outputs"))

datas += collect_data_files("nicegui")

hiddenimports = (
    collect_submodules("nicegui")
    + collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("plotly")
    + collect_submodules("networkx")
)


a = Analysis(
    [str(app_root / "app.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SolarExpanseFleetManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    codesign_identity=None,
    entitlements_file=None,
    manifest=str(app_root / "packaging" / "windows" / "app.manifest"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SolarExpanseFleetManager",
)
