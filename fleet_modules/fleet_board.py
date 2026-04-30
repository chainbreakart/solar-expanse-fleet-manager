from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import FleetRow

from .shared import TableModule, TableRow


columns = [
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "id", "label": "ID", "field": "id", "sortable": True, "align": "right"},
    {"name": "name", "label": "Craft", "field": "name", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "current", "label": "Current", "field": "current", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "departure", "label": "Departure", "field": "departure", "sortable": True, "align": "left"},
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "timing", "label": "Timing", "field": "timing", "sortable": True, "align": "left"},
    {"name": "capacity", "label": "Capacity", "field": "capacity", "sortable": False, "align": "left"},
    {"name": "fuel_plan", "label": "Fuel Plan", "field": "fuel_plan", "sortable": False, "align": "left"},
    {"name": "transfer", "label": "Transfer", "field": "transfer", "sortable": False, "align": "left"},
    {"name": "warnings", "label": "Warnings", "field": "warnings", "sortable": False, "align": "left"},
    {"name": "cargo", "label": "Cargo", "field": "cargo", "sortable": False, "align": "left"},
    {"name": "fuel", "label": "Fuel / LS", "field": "fuel", "sortable": False, "align": "left"},
]


def row_from_fleet_row(row: FleetRow) -> TableRow:
    return {
        "key": f"{row.company}:{row.craft_id}",
        "company": row.company,
        "id": row.craft_id,
        "name": row.craft_name,
        "type": row.craft_type,
        "current": row.current_object,
        "status": row.status,
        "route": row.route,
        "departure": row.departure,
        "arrival": row.arrival,
        "cargo": row.cargo,
        "fuel": row.fuel,
        "timing": row.mission_timing,
        "fuel_plan": row.fuel_plan,
        "capacity": row.capacity,
        "transfer": row.transfer,
        "warnings": row.warnings,
        "mission": row.mission_id,
    }


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    return [row_from_fleet_row(row) for row in analysis.fleet_rows]


MODULE = TableModule(
    key="fleet",
    label="Fleet Board",
    columns=columns,
    build_rows=build_rows,
    pagination=25,
)
