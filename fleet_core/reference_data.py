from __future__ import annotations

import csv
from pathlib import Path

from .normalizer import friendly_key


def load_transport_capacities(repo_root: Path) -> dict[str, dict[str, object]]:
    capacities: dict[str, dict[str, object]] = {}
    path = repo_root / "data" / "derived" / "population" / "habitat_capacities.csv"
    if not path.exists():
        return capacities

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("context") != "Transport":
                continue
            key = row.get("game_key") or ""
            try:
                capacity = int(float(row.get("capacity_per_unit") or 0))
            except ValueError:
                capacity = 0
            if key and capacity > 0:
                capacities[key] = {
                    "display_name": row.get("display_name") or friendly_key(key),
                    "capacity": capacity,
                }
    return capacities
