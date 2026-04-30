from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app_paths import user_data_dir


@dataclass(frozen=True)
class IpcPaths:
    root: Path
    handoff_file: Path
    command_dir: Path
    status_file: Path


def ipc_paths() -> IpcPaths:
    root = user_data_dir() / "ipc"
    return IpcPaths(
        root=root,
        handoff_file=root / "handoff.json",
        command_dir=root / "commands",
        status_file=root / "status.json",
    )


def ensure_ipc_paths() -> IpcPaths:
    paths = ipc_paths()
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.command_dir.mkdir(parents=True, exist_ok=True)
    return paths
