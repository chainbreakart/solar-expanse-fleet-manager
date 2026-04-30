from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import fmt_num

from .shared import TableModule, TableRow


columns = [
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "craft_count", "label": "Assignments", "field": "craft_count", "sortable": True, "align": "right"},
    {"name": "active_craft_count", "label": "Moving", "field": "active_craft_count", "sortable": True, "align": "right"},
    {"name": "planned_craft_count", "label": "Planned", "field": "planned_craft_count", "sortable": True, "align": "right"},
    {"name": "cargo_tons", "label": "Cargo Assigned", "field": "cargo_tons", "sortable": True, "align": "right"},
    {"name": "people_in_transit", "label": "People Assigned", "field": "people_in_transit", "sortable": True, "align": "right"},
    {"name": "companies", "label": "Companies", "field": "companies", "sortable": True, "align": "left"},
    {"name": "statuses", "label": "Statuses", "field": "statuses", "sortable": True, "align": "left"},
    {"name": "next_departure", "label": "Next Departure", "field": "next_departure", "sortable": True, "align": "left"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "attention_count", "label": "Attention", "field": "attention_count", "sortable": True, "align": "right"},
    {"name": "craft", "label": "Assigned Craft", "field": "craft", "sortable": False, "align": "left"},
    {"name": "transfer", "label": "Transfer", "field": "transfer", "sortable": False, "align": "left"},
    {"name": "capacity", "label": "Capacity", "field": "capacity", "sortable": False, "align": "left"},
    {"name": "fuel_plan", "label": "Fuel Plan", "field": "fuel_plan", "sortable": False, "align": "left"},
    {"name": "warnings", "label": "Warnings", "field": "warnings", "sortable": False, "align": "left"},
    {"name": "cargo", "label": "Cargo", "field": "cargo", "sortable": False, "align": "left"},
]


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    result: list[TableRow] = []
    for metric in analysis.route_metrics:
        result.append(
            {
                "key": metric.route_key,
                "route": metric.route,
                "craft_count": metric.total_craft_count,
                "active_craft_count": metric.active_craft_count,
                "planned_craft_count": metric.planned_craft_count,
                "cargo_tons": f"{fmt_num(metric.cargo_tons_in_transit)}t" if metric.cargo_tons_in_transit else "",
                "people_in_transit": metric.people_in_transit,
                "companies": ", ".join(metric.companies),
                "statuses": ", ".join(f"{status} {count}" for status, count in metric.status_counts),
                "next_departure": metric.next_departure,
                "next_arrival": metric.next_arrival,
                "attention_count": metric.attention_count,
                "craft": "; ".join(metric.assigned_craft),
                "cargo": "; ".join(metric.cargo_summaries),
                "fuel_plan": "; ".join(metric.fuel_plan_summaries),
                "capacity": "; ".join(metric.capacity_summaries),
                "transfer": "; ".join(metric.transfers),
                "warnings": "; ".join(metric.warnings),
            }
        )
    return result


MODULE = TableModule(
    key="routes",
    label="Route Board",
    columns=columns,
    build_rows=build_rows,
)
