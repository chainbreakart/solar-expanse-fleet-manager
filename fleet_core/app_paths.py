from __future__ import annotations

import os
import socket
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


def server_port_scan_limit() -> int:
    raw = os.environ.get("FLEET_MANAGER_PORT_SCAN_LIMIT", "20")
    try:
        return max(0, int(raw))
    except ValueError:
        return 20


def strict_server_port() -> bool:
    raw = os.environ.get("FLEET_MANAGER_STRICT_PORT", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bind_check_host(host: str) -> str:
    if not host or host == "localhost":
        return "127.0.0.1"
    return host


def _port_is_available(host: str, port: int) -> bool:
    if port < 1 or port > 65535:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((_bind_check_host(host), port))
    except OSError:
        return False
    return True


def resolve_server_port(host: str | None = None) -> tuple[int, list[str]]:
    host = host or server_host()
    preferred_port = server_port()
    if _port_is_available(host, preferred_port):
        return preferred_port, []

    if strict_server_port():
        raise RuntimeError(
            f"Port {preferred_port} is already in use. Close the existing server or set FLEET_MANAGER_PORT to a free port."
        )

    scan_limit = server_port_scan_limit()
    for candidate in range(preferred_port + 1, min(65535, preferred_port + scan_limit) + 1):
        if _port_is_available(host, candidate):
            return candidate, [
                f"Port {preferred_port} is already in use; starting Fleet Manager on port {candidate} instead.",
                "Set FLEET_MANAGER_PORT to choose a specific port, or FLEET_MANAGER_STRICT_PORT=1 to fail instead of falling back.",
            ]

    raise RuntimeError(
        f"Port {preferred_port} is already in use and no free fallback was found in the next {scan_limit} port(s). "
        "Close the existing server or set FLEET_MANAGER_PORT to a free port."
    )


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
