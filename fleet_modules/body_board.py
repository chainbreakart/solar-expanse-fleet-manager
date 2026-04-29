from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import fmt_num

from .shared import TableModule, TableRow


columns = [
    {"name": "body", "label": "Body / Orbit", "field": "body", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "parent", "label": "Parent", "field": "parent", "sortable": True, "align": "left"},
    {"name": "relationship", "label": "Relationship", "field": "relationship", "sortable": True, "align": "left"},
    {"name": "companies", "label": "Companies", "field": "companies", "sortable": True, "align": "left"},
    {"name": "present", "label": "Craft Here", "field": "present", "sortable": True, "align": "right"},
    {"name": "idle", "label": "Idle", "field": "idle", "sortable": True, "align": "right"},
    {"name": "active_inbound", "label": "Active In", "field": "active_inbound", "sortable": True, "align": "right"},
    {"name": "planned_inbound", "label": "Planned In", "field": "planned_inbound", "sortable": True, "align": "right"},
    {"name": "outbound", "label": "Outbound", "field": "outbound", "sortable": True, "align": "right"},
    {"name": "inbound_people", "label": "People In", "field": "inbound_people", "sortable": True, "align": "right"},
    {"name": "outbound_people", "label": "People Out", "field": "outbound_people", "sortable": True, "align": "right"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "inbound_cargo", "label": "Cargo In", "field": "inbound_cargo", "sortable": False, "align": "left"},
    {"name": "craft_here", "label": "Present Craft", "field": "craft_here", "sortable": False, "align": "left"},
    {"name": "warnings", "label": "Warnings", "field": "warnings", "sortable": False, "align": "left"},
    {"name": "inbound_routes", "label": "Inbound Routes", "field": "inbound_routes", "sortable": False, "align": "left"},
    {"name": "outbound_routes", "label": "Outbound Routes", "field": "outbound_routes", "sortable": False, "align": "left"},
]


def cargo_rollup_text(rollup: tuple[tuple[str, float], ...]) -> str:
    return "; ".join(f"{name} {fmt_num(mass)}t" for name, mass in rollup)


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    result: list[TableRow] = []
    for metric in analysis.body_metrics:
        result.append(
            {
                "key": metric.object_id,
                "body": metric.body,
                "type": metric.object_type,
                "parent": metric.parent,
                "relationship": metric.relationship,
                "companies": ", ".join(metric.companies),
                "present": metric.craft_present,
                "idle": metric.idle_craft,
                "active_inbound": metric.active_inbound_craft,
                "planned_inbound": metric.planned_inbound_craft,
                "outbound": metric.outbound_craft,
                "inbound_people": metric.inbound_people,
                "outbound_people": metric.outbound_people,
                "next_arrival": metric.next_arrival,
                "inbound_cargo": cargo_rollup_text(metric.inbound_cargo),
                "craft_here": "; ".join(metric.craft_here),
                "inbound_routes": "; ".join(metric.inbound_routes),
                "outbound_routes": "; ".join(metric.outbound_routes),
                "warnings": "; ".join(metric.warnings),
            }
        )
    return result


MODULE = TableModule(
    key="bodies",
    label="Body Board",
    columns=columns,
    build_rows=build_rows,
)
