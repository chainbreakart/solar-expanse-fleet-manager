from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer_utils import fmt_num

from .shared import AUDIT_COLUMNS, TableModule, TableRow, resource_cell_slot, with_resource_icon


columns = [
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "location", "label": "Location", "field": "location", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "resource", "label": "Resource", "field": "resource", "sortable": True, "align": "left"},
    {"name": "stock", "label": "Stock", "field": "stock", "sortable": True, "align": "right"},
    {"name": "intake", "label": "In/Day", "field": "intake", "sortable": True, "align": "right"},
    {"name": "outtake", "label": "Out/Day", "field": "outtake", "sortable": True, "align": "right"},
    {"name": "net", "label": "Net/Day", "field": "net", "sortable": True, "align": "right"},
    {"name": "runway", "label": "Runway", "field": "runway", "sortable": True, "align": "right"},
    {"name": "basis", "label": "Status Basis", "field": "basis", "sortable": True, "align": "left"},
    {"name": "tech", "label": "Tech Adjustment", "field": "tech", "sortable": True, "align": "left"},
    *AUDIT_COLUMNS,
]


def tons(value: float) -> str:
    return f"{fmt_num(value)}t"


def rate(value: float) -> str:
    return f"{fmt_num(value)}t/day"


def runway_text(value: float | None) -> str:
    if value is None:
        return "stable"
    years = value / 365.0
    return f"{fmt_num(years)}y"


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    rows: list[TableRow] = []
    for metric in analysis.production_balance_metrics:
        rows.append(
            with_resource_icon(
                {
                "key": metric.production_key,
                "status": metric.status,
                "company": metric.company,
                "object_id": metric.object_id,
                "location": metric.object_label,
                "type": metric.object_type,
                "resource_key": metric.resource_key,
                "resource": metric.resource_name,
                "stock": tons(metric.stock),
                "intake": rate(metric.intake_per_day),
                "outtake": rate(metric.outtake_per_day),
                "net": rate(metric.net_per_day),
                "runway": runway_text(metric.runway_days),
                "basis": metric.status_basis,
                "tech": metric.tech_adjustment.basis if metric.tech_adjustment else "",
                "audit_source": metric.source,
                "confidence": metric.tech_adjustment.confidence if metric.tech_adjustment else "high",
                "anomaly_destination": "Attention / Production" if metric.status in {"Critical", "Urgent", "Warning"} else "Production Balance / Sites",
                }
            )
        )
    return rows


MODULE = TableModule(
    key="production_audit",
    label="Production Audit",
    columns=columns,
    build_rows=build_rows,
    slots={"body-cell-resource": resource_cell_slot()},
)
