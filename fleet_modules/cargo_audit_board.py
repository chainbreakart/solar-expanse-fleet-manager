from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer_utils import fmt_num

from .shared import AUDIT_COLUMNS, TableModule, TableRow, fleet_link


columns = [
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "mission", "label": "Mission", "field": "mission", "sortable": True, "align": "right"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "source", "label": "Source", "field": "source", "sortable": True, "align": "left"},
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "total_tons", "label": "Cargo", "field": "total_tons", "sortable": True, "align": "right"},
    {"name": "support_tons", "label": "Colony Support", "field": "support_tons", "sortable": True, "align": "right"},
    {"name": "fuel_tons", "label": "Fuel", "field": "fuel_tons", "sortable": True, "align": "right"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": False, "align": "left"},
    {"name": "top_cargo", "label": "Top Cargo", "field": "top_cargo", "sortable": False, "align": "left"},
    {"name": "support_classes", "label": "Support Classes", "field": "support_classes", "sortable": False, "align": "left"},
    *AUDIT_COLUMNS,
]


def tons(value: float) -> str:
    return f"{fmt_num(value)}t" if value else ""


def summary(items: tuple[tuple[str, float], ...], *, limit: int = 4) -> str:
    pieces = [f"{name} {fmt_num(value)}t" for name, value in items[:limit]]
    if len(items) > limit:
        pieces.append(f"+ {len(items) - limit} more")
    return "; ".join(pieces)


def cargo_anomaly_destination(metric) -> str:
    if metric.target_id is None or not metric.destination:
        return "Attention / Cargo destination"
    if metric.arrival_dt is None and metric.status in {"En route", "Planned"}:
        return "Attention / Cargo timing"
    return "Cargo Receipts / Manifests"


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    rows: list[TableRow] = []
    for metric in analysis.cargo_flight_metrics:
        resource_keys = sorted({detail.resource_key for detail in metric.details if detail.resource_key})
        rows.append(
            {
                "key": metric.flight_key,
                "company": metric.company,
                "status": metric.status,
                "mission": metric.mission_id,
                "mission_key": metric.mission_key,
                "route": metric.route,
                "source_id": metric.source_id or "",
                "source": metric.source,
                "target_id": metric.target_id or "",
                "destination": metric.destination,
                "arrival": metric.arrival,
                "resource_keys": "; ".join(resource_keys),
                "total_tons": tons(metric.total_tons),
                "support_tons": tons(metric.colonization_support_tons),
                "fuel_tons": tons(metric.fuel_tons),
                "craft": ", ".join(metric.craft_names),
                "fleet_url": (
                    fleet_link(craft=metric.craft_ids[0])
                    if len(metric.craft_ids) == 1
                    else fleet_link(mission=metric.mission_id or metric.mission_key)
                ),
                "top_cargo": summary(metric.cargo_totals),
                "support_classes": summary(metric.colonization_support_categories),
                "audit_source": "CargoFlightMetric from CargoFact + MissionFact + CraftFact",
                "confidence": "high" if metric.target_id is not None and metric.arrival_dt is not None else "medium",
                "anomaly_destination": cargo_anomaly_destination(metric),
            }
        )
    return rows


MODULE = TableModule(
    key="cargo_audit",
    label="Cargo Audit",
    columns=columns,
    build_rows=build_rows,
    slots={
        "body-cell-craft": r"""
            <q-td :props="props">
                <a :href="props.row.fleet_url" class="table-drilldown-link">{{ props.row.craft }}</a>
            </q-td>
        """,
    },
)
