from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Solar Expanse Fleet Manager"
APP_ID = "SolarExpanseFleetManager"
PUBLISHER = "Solar Expanse Tools"


def app_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def source_repo_root() -> Path:
    root = app_dir()
    monorepo_root = root.parents[2] if len(root.parents) >= 3 else root
    if (monorepo_root / "products" / "apps" / "fleet_manager" / "app.py").exists():
        return monorepo_root
    return root


def resource_root() -> Path:
    """Return the root containing bundled reference data."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return source_repo_root()


def user_data_dir() -> Path:
    override = os.environ.get("FLEET_MANAGER_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_ID

    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / APP_ID
    return Path.home() / ".local" / "state" / APP_ID


def ensure_user_dirs() -> Path:
    root = user_data_dir()
    for child in (root, root / "logs", root / "ipc", root / "cache"):
        child.mkdir(parents=True, exist_ok=True)
    return root


def server_host() -> str:
    return os.environ.get("FLEET_MANAGER_HOST", "localhost")


def server_port() -> int:
    raw = os.environ.get("FLEET_MANAGER_PORT", "8080")
    try:
        return int(raw)
    except ValueError:
        return 8080


def _windows_user_profile() -> Path | None:
    profile = os.environ.get("USERPROFILE")
    if profile:
        return Path(profile)
    home_drive = os.environ.get("HOMEDRIVE")
    home_path = os.environ.get("HOMEPATH")
    if home_drive and home_path:
        return Path(home_drive + home_path)
    return None


def candidate_save_dirs() -> list[Path]:
    override = os.environ.get("SOLAR_EXPANSE_SAVE_DIR")
    if override:
        return [Path(override).expanduser()]

    candidates: list[Path] = []
    profile = _windows_user_profile()
    if profile is not None:
        candidates.append(profile / "AppData" / "LocalLow" / "SpaceOps" / "Solar Expanse" / "Saves")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data).parent / "LocalLow" / "SpaceOps" / "Solar Expanse" / "Saves")

    users_root = Path("/mnt/c/Users")
    if users_root.exists():
        candidates.extend(users_root.glob("*/AppData/LocalLow/SpaceOps/Solar Expanse/Saves"))

    return list(dict.fromkeys(candidates))


def default_save_dir() -> Path:
    for candidate in candidate_save_dirs():
        if candidate.exists():
            return candidate
    candidates = candidate_save_dirs()
    if candidates:
        return candidates[0]
    return Path.home() / "AppData" / "LocalLow" / "SpaceOps" / "Solar Expanse" / "Saves"
