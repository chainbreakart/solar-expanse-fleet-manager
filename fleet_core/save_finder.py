from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app_paths import default_save_dir


@dataclass(frozen=True)
class SaveSlot:
    name: str
    json_path: Path
    info_path: Path | None
    modified_ts: float

    @property
    def label(self) -> str:
        return self.name


def discover_saves(save_dir: Path | None = None) -> list[SaveSlot]:
    save_dir = save_dir or default_save_dir()
    if not save_dir.exists():
        return []

    slots: list[SaveSlot] = []
    for json_path in save_dir.glob("*.json.gz"):
        name = json_path.name.removesuffix(".json.gz")
        info_path = save_dir / f"{name}.info.gz"
        slots.append(
            SaveSlot(
                name=name,
                json_path=json_path,
                info_path=info_path if info_path.exists() else None,
                modified_ts=json_path.stat().st_mtime,
            )
        )
    return sorted(slots, key=lambda slot: slot.modified_ts, reverse=True)


def save_options_by_label(slots: list[SaveSlot]) -> dict[str, SaveSlot]:
    return {slot.label: slot for slot in slots}


def select_save_after_refresh(
    slots: list[SaveSlot],
    preferred_label: str | None = None,
    previous_selection: SaveSlot | None = None,
) -> SaveSlot | None:
    options = save_options_by_label(slots)
    if preferred_label and preferred_label in options:
        return options[preferred_label]
    if previous_selection and previous_selection.label in options:
        return options[previous_selection.label]
    return slots[0] if slots else None
