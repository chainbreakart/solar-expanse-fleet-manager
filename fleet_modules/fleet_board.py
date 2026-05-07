from __future__ import annotations

import re

from fleet_core.analysis import SaveAnalysis
from fleet_core.fact_model import FleetRow

from .shared import AUDIT_COLUMNS, TableModule, TableRow, data_tab_link, fleet_link


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
    *AUDIT_COLUMNS,
]


def object_id_from_label(label: str) -> str:
    match = re.search(r"\((\d+)\)\s*$", label or "")
    return match.group(1) if match else ""


def row_from_fleet_row(row: FleetRow) -> TableRow:
    object_id = object_id_from_label(row.current_object)
    return {
        "key": f"{row.company}:{row.craft_id}",
        "company": row.company,
        "id": row.craft_id,
        "name": row.craft_name,
        "fleet_url": fleet_link(craft=row.craft_id),
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
        "cargo_url": f"/cargo/manifests?mission={row.mission_id}" if row.mission_id else "/cargo/manifests",
        "route_url": data_tab_link("routes", route=row.route) if row.route else data_tab_link("routes"),
        "fuel_url": data_tab_link("return_fuel", object=row.craft_id),
        "body_url": data_tab_link("bodies", object=object_id) if object_id else data_tab_link("bodies"),
        "audit_source": "CraftFact + MissionFact + live/reference hull capacity",
        "confidence": "high" if "live" in row.capacity.lower() or "save" in row.capacity.lower() else "medium",
        "anomaly_destination": "Attention / Fleet Board" if row.warnings else "Fleet Board",
    }


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    return [row_from_fleet_row(row) for row in analysis.fleet_rows]


MODULE = TableModule(
    key="fleet",
    label="Fleet Board",
    columns=columns,
    build_rows=build_rows,
    pagination=25,
    slots={
        "body-cell-name": r"""
            <q-td :props="props">
                <a :href="props.row.fleet_url" class="table-drilldown-link">{{ props.row.name }}</a>
            </q-td>
        """,
        "body-cell-current": r"""
            <q-td :props="props">
                <a :href="props.row.body_url" class="table-drilldown-link">{{ props.row.current }}</a>
            </q-td>
        """,
        "body-cell-route": r"""
            <q-td :props="props">
                <a :href="props.row.route_url" class="table-drilldown-link">{{ props.row.route }}</a>
            </q-td>
        """,
        "body-cell-cargo": r"""
            <q-td :props="props">
                <a :href="props.row.cargo_url" class="table-drilldown-link">{{ props.row.cargo }}</a>
            </q-td>
        """,
        "body-cell-fuel_plan": r"""
            <q-td :props="props">
                <a :href="props.row.fuel_url" class="table-drilldown-link">{{ props.row.fuel_plan }}</a>
            </q-td>
        """,
    },
)
