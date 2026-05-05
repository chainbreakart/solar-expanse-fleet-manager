from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.fact_model import TechAdjustedValue, TechReferenceRow
from fleet_core.normalizer import fmt_num


unlock_columns = [
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "category", "label": "Category", "field": "category", "sortable": True, "align": "left"},
    {"name": "title", "label": "Research", "field": "title", "sortable": True, "align": "left"},
    {"name": "progress", "label": "Progress", "field": "progress", "sortable": True, "align": "right"},
    {"name": "spacecraft", "label": "Spacecraft", "field": "spacecraft", "sortable": True, "align": "left"},
    {"name": "buildables", "label": "Buildables", "field": "buildables", "sortable": True, "align": "left"},
    {"name": "modules", "label": "Modules", "field": "modules", "sortable": True, "align": "left"},
    {"name": "resources", "label": "Resources", "field": "resources", "sortable": True, "align": "left"},
    {"name": "modifiers", "label": "Modifiers", "field": "modifiers", "sortable": True, "align": "left"},
]

active_columns = [
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "title", "label": "Research", "field": "title", "sortable": True, "align": "left"},
    {"name": "category", "label": "Category", "field": "category", "sortable": True, "align": "left"},
    {"name": "progress", "label": "Progress", "field": "progress", "sortable": True, "align": "right"},
    {"name": "source", "label": "Source", "field": "source", "sortable": True, "align": "left"},
]

used_modifier_columns = [
    {"name": "area", "label": "Area", "field": "area", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "target", "label": "Target", "field": "target", "sortable": True, "align": "left"},
    {"name": "basis", "label": "Tech Basis", "field": "basis", "sortable": True, "align": "left"},
    {"name": "raw", "label": "Raw", "field": "raw", "sortable": True, "align": "right"},
    {"name": "adjusted", "label": "Adjusted", "field": "adjusted", "sortable": True, "align": "right"},
    {"name": "multiplier", "label": "Multiplier", "field": "multiplier", "sortable": True, "align": "right"},
    {"name": "confidence", "label": "Confidence", "field": "confidence", "sortable": True, "align": "left"},
]


STATUS_ORDER = {"Active": 0, "In Progress": 1, "Queued": 2, "Completed": 3}


def join_items(items: tuple[str, ...], *, limit: int = 3) -> str:
    if not items:
        return ""
    visible = list(items[:limit])
    if len(items) > limit:
        visible.append(f"+{len(items) - limit} more")
    return ", ".join(visible)


def modifier_summary(analysis: SaveAnalysis, research_id: str) -> str:
    modifiers = analysis.technology_reference.modifiers_by_research_id.get(research_id, ())
    if not modifiers:
        return ""
    counts = Counter(modifier.modifier_type for modifier in modifiers)
    return ", ".join(f"{name} x{count}" if count > 1 else name for name, count in sorted(counts.items()))


def reference_for(analysis: SaveAnalysis, research_id: str) -> TechReferenceRow | None:
    return analysis.technology_reference.by_research_id.get(research_id)


def progress_text(value: float | None, status: str) -> str:
    if value is None:
        return "100%" if status == "Completed" else ""
    if status == "Completed" and abs(value - 1.0) < 0.0001:
        return "100%"
    return fmt_num(value)


def technology_unlock_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fact in analysis.tech_unlock_facts:
        reference = reference_for(analysis, fact.research_id)
        rows.append(
            {
                "key": f"{fact.company}:{fact.status}:{fact.research_id}:{fact.source_field}",
                "company": fact.company,
                "research_id": fact.research_id,
                "status": fact.status,
                "category": reference.category if reference else fact.category,
                "title": reference.title if reference else fact.display_name,
                "progress": progress_text(fact.progress, fact.status),
                "spacecraft": join_items(reference.unlocked_spacecraft if reference else ()),
                "buildables": join_items(reference.unlocked_facilities if reference else ()),
                "modules": join_items(reference.unlocked_modules if reference else ()),
                "resources": join_items(reference.unlocked_resources if reference else ()),
                "modifiers": modifier_summary(analysis, fact.research_id),
                "source": fact.source_field,
                "confidence": fact.confidence,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["company"],
            STATUS_ORDER.get(str(row["status"]), 9),
            str(row["category"]),
            str(row["title"]),
        ),
    )


def active_technology_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    return [row for row in technology_unlock_rows(analysis) if row["status"] in {"Active", "In Progress", "Queued"}]


def modifier_value(value: float | None) -> str:
    if value is None:
        return ""
    return fmt_num(value)


def adjustment_row(
    *,
    area: str,
    company: str,
    target: str,
    adjustment: TechAdjustedValue,
) -> dict[str, Any]:
    return {
        "key": f"{area}:{company}:{target}:{adjustment.basis}",
        "area": area,
        "company": company,
        "target": target,
        "basis": adjustment.basis,
        "raw": modifier_value(adjustment.raw_value),
        "adjusted": modifier_value(adjustment.adjusted_value),
        "multiplier": f"{adjustment.multiplier:.2f}x" if adjustment.multiplier is not None else "",
        "source": adjustment.source,
        "confidence": adjustment.confidence,
    }


def used_modifier_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any]) -> None:
        rows[str(row["key"])] = row

    for craft in analysis.craft_facts:
        adjustment = craft.capacity_metrics.tech_adjustment
        if adjustment:
            add(adjustment_row(area="Fleet capacity", company=craft.company, target=craft.craft_name, adjustment=adjustment))

    for crew in analysis.crew_metrics:
        if crew.tech_adjustment:
            add(adjustment_row(area="Transport seats", company=crew.company, target=crew.cargo_item, adjustment=crew.tech_adjustment))

    for metric in analysis.production_balance_metrics:
        if metric.tech_adjustment:
            add(adjustment_row(area="Production", company=metric.company, target=metric.resource_name, adjustment=metric.tech_adjustment))

    for metric in analysis.population_readiness_metrics:
        if metric.tech_adjustment:
            add(adjustment_row(area="Life support", company=metric.company, target=metric.destination, adjustment=metric.tech_adjustment))

    return sorted(rows.values(), key=lambda row: (str(row["area"]), str(row["company"]), str(row["target"])))


def technology_kpis(analysis: SaveAnalysis) -> list[tuple[str, str, str]]:
    unlocks = technology_unlock_rows(analysis)
    completed = [row for row in unlocks if row["status"] == "Completed"]
    active = active_technology_rows(analysis)
    used = used_modifier_rows(analysis)
    categories = {row["category"] for row in completed if row["category"]}
    return [
        ("Completed", fmt_num(len(completed)), f"{len(categories)} categories with completed research"),
        ("Active / Queued", fmt_num(len(active)), "Current save research work visible in save data"),
        ("Used Modifiers", fmt_num(len(used)), "Tech effects currently attached to planner facts"),
        ("Reference Rows", fmt_num(len(analysis.technology_reference.rows)), f"{fmt_num(len(analysis.technology_reference.modifiers))} reference modifiers loaded"),
    ]


def category_summary_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"completed": 0, "active": 0, "modifiers": 0})
    for row in technology_unlock_rows(analysis):
        key = (str(row["company"]), str(row["category"] or "Research"))
        if row["status"] == "Completed":
            grouped[key]["completed"] += 1
        elif row["status"] in {"Active", "In Progress", "Queued"}:
            grouped[key]["active"] += 1
        if row["modifiers"]:
            grouped[key]["modifiers"] += 1

    return [
        {
            "key": f"{company}:{category}",
            "company": company,
            "category": category,
            "completed": values["completed"],
            "active": values["active"],
            "modifiers": values["modifiers"],
        }
        for (company, category), values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1]))
    ]


def render_kpi_strip(kpis: list[tuple[str, str, str]]) -> None:
    with ui.element("div").classes("population-kpis"):
        for label, value, hint in kpis:
            with ui.element("div").classes("population-kpi"):
                ui.label(label).classes("population-kpi-label")
                ui.label(value).classes("population-kpi-value")
                ui.label(hint).classes("population-kpi-hint")


def render_table(title: str, columns: list[dict[str, object]], rows: list[dict[str, Any]], *, pagination: int = 12) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label(title).classes("dashboard-card-title")
        if not rows:
            ui.label("No rows for the current save scope.").classes("empty-state-note")
            return
        table = ui.table(columns=columns, rows=rows, row_key="key", pagination=pagination).classes("w-full")
        table.props("flat bordered dense wrap-cells")


def render_category_cards(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("tech-category-grid"):
        for row in rows[:12]:
            with ui.element("div").classes("tech-category-card"):
                ui.label(str(row["category"])).classes("tech-category-title")
                ui.label(str(row["company"])).classes("tech-category-company")
                ui.label(f"{row['completed']} completed").classes("tech-category-value")
                ui.label(f"{row['active']} active/queued, {row['modifiers']} modifier-bearing").classes("tech-category-hint")
        if len(rows) > 12:
            with ui.element("div").classes("tech-category-card"):
                ui.label("More Categories").classes("tech-category-title")
                ui.label(f"+{len(rows) - 12} more category/company pairs").classes("tech-category-hint")


def render_technology_dashboard(analysis: SaveAnalysis, container) -> None:
    container.clear()
    unlocks = technology_unlock_rows(analysis)
    active = active_technology_rows(analysis)
    used_modifiers = used_modifier_rows(analysis)
    categories = category_summary_rows(analysis)

    with container:
        render_kpi_strip(technology_kpis(analysis))
        if categories:
            render_category_cards(categories)
        render_table("Active Research", active_columns, active, pagination=8)
        render_table("Modifier Effects Used By Planner Math", used_modifier_columns, used_modifiers, pagination=10)
        render_table("Research Unlocks And Reference Effects", unlock_columns, unlocks, pagination=18)
