from __future__ import annotations

from fleet_core.analysis import SaveAnalysis

from .shared import TableModule, TableRow


columns = [
    {"name": "severity", "label": "Severity", "field": "severity", "sortable": True, "align": "left"},
    {"name": "category", "label": "Category", "field": "category", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "title", "label": "Attention", "field": "title", "sortable": True, "align": "left"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "body", "label": "Body", "field": "body", "sortable": True, "align": "left"},
    {"name": "event_date", "label": "Date", "field": "event_date", "sortable": True, "align": "left"},
    {"name": "drilldown", "label": "Drill-Down", "field": "drilldown", "sortable": True, "align": "left"},
    {"name": "message", "label": "Message", "field": "message", "sortable": True, "align": "left"},
]


def severity_class(severity: str) -> str:
    normalized = severity.lower()
    if normalized in {"critical", "urgent", "warning", "monitor"}:
        return f"readiness-{normalized}"
    return "readiness-monitor"


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    return [
        {
            "key": row.attention_key,
            "severity": row.severity,
            "severity_class": severity_class(row.severity),
            "category": row.category,
            "company": row.company,
            "title": row.title,
            "craft": row.craft_name,
            "route": row.route,
            "body": row.body,
            "event_date": row.event_date,
            "drilldown": row.drilldown,
            "message": row.message,
            "source": row.source,
            "details": row.details,
        }
        for row in analysis.attention_rows
    ]


def build_metrics(_analysis: SaveAnalysis, rows: list[TableRow]) -> dict[str, str]:
    return {
        "attention_count": str(len(rows)),
        "fuel_attention_count": str(sum(1 for row in rows if row.get("category") == "Fuel")),
        "capacity_attention_count": str(sum(1 for row in rows if row.get("category") == "Capacity")),
        "population_attention_count": str(sum(1 for row in rows if row.get("category") == "Population")),
        "save_data_attention_count": str(sum(1 for row in rows if row.get("category") == "Save Data")),
        "critical_attention_count": str(sum(1 for row in rows if row.get("severity") == "Critical")),
    }


slots = {
    "body-cell-severity": r"""
        <q-td :props="props">
            <span :class="'readiness-chip ' + props.row.severity_class">
                {{ props.row.severity }}
                <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                    <div class="return-fuel-tooltip-title">{{ props.row.title }}</div>
                    <div class="return-fuel-tooltip-line">{{ props.row.message }}</div>
                    <div class="return-fuel-tooltip-line">Source: {{ props.row.source }}</div>
                    <div
                        v-for="line in props.row.details"
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
    key="attention",
    label="Attention",
    columns=columns,
    build_rows=build_rows,
    build_metrics=build_metrics,
    slots=slots,
)
