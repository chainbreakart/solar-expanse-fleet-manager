from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer_utils import fmt_num

from .shared import TableModule, TableRow, data_tab_link, fleet_link


columns = [
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "fuel", "label": "Fuel", "field": "fuel", "sortable": True, "align": "left"},
    {"name": "requirement", "label": "Return Need", "field": "requirement", "sortable": True, "align": "right"},
    {"name": "confidence", "label": "Confidence", "field": "confidence", "sortable": True, "align": "left"},
    {"name": "onboard", "label": "Arrival Fuel", "field": "onboard", "sortable": True, "align": "right"},
    {"name": "onboard_basis", "label": "Arrival Fuel Basis", "field": "onboard_basis", "sortable": True, "align": "left"},
    {"name": "fuel_cargo", "label": "Fuel Cargo", "field": "fuel_cargo", "sortable": True, "align": "right"},
    {"name": "immediate_stock", "label": "Immediate Stock", "field": "immediate_stock", "sortable": True, "align": "right"},
    {"name": "surface_stock", "label": "Surface Stock", "field": "surface_stock", "sortable": True, "align": "right"},
    {"name": "lift_needed", "label": "Lift Needed", "field": "lift_needed", "sortable": True, "align": "right"},
    {"name": "immediate_margin", "label": "Immediate Margin", "field": "immediate_margin", "sortable": True, "align": "right"},
    {"name": "deferred_margin", "label": "After Surface Lift", "field": "deferred_margin", "sortable": True, "align": "right"},
    {"name": "stock_objects", "label": "Stock Objects", "field": "stock_objects", "sortable": False, "align": "left"},
    {"name": "basis", "label": "Basis", "field": "basis", "sortable": True, "align": "left"},
    {"name": "warning", "label": "Warning", "field": "warning", "sortable": True, "align": "left"},
]


def tons(value: float | None) -> str:
    if value is None:
        return ""
    return f"{fmt_num(value)}t"


def named_stock(label: str, value: float, object_name: str) -> str:
    object_text = f" at {object_name}" if object_name else ""
    return f"{label}: {tons(value)}{object_text}"


def warning_details(metric) -> list[str]:
    if not metric.warning:
        return []

    requirement = tons(metric.estimated_return_requirement) or "unknown"
    immediate_object = metric.immediate_stock_object or metric.destination
    surface_object = metric.surface_stock_object or "no linked surface stock"
    return [
        f"Return need: {requirement} ({metric.return_requirement_confidence}; {metric.requirement_basis})",
        f"Arrival fuel: {tons(metric.expected_onboard_fuel_at_arrival)} ({metric.expected_onboard_fuel_basis})",
        f"Compatible fuel cargo: {tons(metric.compatible_fuel_cargo)}",
        named_stock("Destination immediate stock", metric.destination_immediate_stock, immediate_object),
        named_stock("Destination surface stock", metric.destination_surface_stock, surface_object),
        f"Immediate margin: {tons(metric.immediate_return_margin)} = arrival fuel + fuel cargo + immediate stock - return need",
        f"After surface lift: {tons(metric.deferred_return_margin)}",
    ]


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    rows: list[TableRow] = []
    for metric in analysis.return_fuel_metrics:
        stock_objects = "; ".join(
            part
            for part in (
                f"immediate: {metric.immediate_stock_object}" if metric.immediate_stock_object else "",
                f"surface: {metric.surface_stock_object}" if metric.surface_stock_object else "",
            )
            if part
        )
        rows.append(
            {
                "key": metric.return_key,
                "company": metric.company,
                "craft_id": metric.craft_id,
                "fleet_url": fleet_link(craft=metric.craft_id),
                "craft": metric.craft_name,
                "type": metric.craft_type,
                "status": metric.status,
                "route": metric.route,
                "arrival": metric.arrival,
                "destination": metric.destination,
                "destination_url": data_tab_link("bodies", object=metric.destination_id)
                if metric.destination_id is not None
                else data_tab_link("bodies"),
                "fuel": metric.fuel_type,
                "requirement": tons(metric.estimated_return_requirement),
                "confidence": metric.return_requirement_confidence,
                "onboard": tons(metric.expected_onboard_fuel_at_arrival),
                "onboard_basis": metric.expected_onboard_fuel_basis,
                "fuel_cargo": tons(metric.compatible_fuel_cargo),
                "immediate_stock": tons(metric.destination_immediate_stock),
                "surface_stock": tons(metric.destination_surface_stock),
                "lift_needed": tons(metric.lift_needed_surface_fuel),
                "immediate_margin": tons(metric.immediate_return_margin),
                "deferred_margin": tons(metric.deferred_return_margin),
                "stock_objects": stock_objects,
                "basis": metric.requirement_basis,
                "warning": metric.warning,
                "warning_details": warning_details(metric),
            }
        )
    return rows


def build_metrics(_analysis: SaveAnalysis, rows: list[TableRow]) -> dict[str, str]:
    return {
        "return_fuel_shortfalls": str(sum(1 for row in rows if row.get("warning"))),
        "return_fuel_lift_needed": str(sum(1 for row in rows if row.get("warning") == "Return fuel needs surface lift")),
    }


slots = {
    "body-cell-craft": r"""
        <q-td :props="props">
            <a :href="props.row.fleet_url" class="table-drilldown-link">{{ props.row.craft }}</a>
        </q-td>
    """,
    "body-cell-destination": r"""
        <q-td :props="props">
            <a :href="props.row.destination_url" class="table-drilldown-link">{{ props.row.destination }}</a>
        </q-td>
    """,
    "body-cell-warning": r"""
        <q-td :props="props">
            <span v-if="props.row.warning" class="warning-chip">
                {{ props.row.warning }}
                <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                    <div class="return-fuel-tooltip-title">{{ props.row.craft }} fuel assessment</div>
                    <div
                        v-for="line in props.row.warning_details"
                        :key="line"
                        class="return-fuel-tooltip-line"
                    >
                        {{ line }}
                    </div>
                </q-tooltip>
            </span>
        </q-td>
    """,
}


MODULE = TableModule(
    key="return_fuel",
    label="Return Fuel",
    columns=columns,
    build_rows=build_rows,
    build_metrics=build_metrics,
    slots=slots,
)
