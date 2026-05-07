from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import plotly.graph_objects as go
from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer_utils import ROUTE_ACTIVE_STATUSES, ROUTE_PLANNED_STATUSES, fmt_dt, fmt_num
from fleet_modules.shared import data_tab_link


SEVERITY_RANK = {"Critical": 0, "Urgent": 1, "Warning": 2, "Monitor": 3, "Info": 4}
ATTENTION_STATUSES = {"Critical", "Urgent", "Warning"}
EVENT_COLORS = {
    "Departure": "#35d8ff",
    "Arrival": "#43e6a0",
    "Cargo Receipt": "#ff9d2e",
    "People Arrival": "#b6f36b",
    "Attention": "#ff5f6c",
    "Tech Unlock": "#c99cff",
}
EVENT_SYMBOLS = {
    "Departure": "triangle-up",
    "Arrival": "circle",
    "Cargo Receipt": "diamond",
    "People Arrival": "star",
    "Attention": "x",
    "Tech Unlock": "hexagon",
}
EVENT_ORDER = {event: index for index, event in enumerate(EVENT_COLORS)}
POSTURE_COLORS = {
    "Active missions": "#35d8ff",
    "Planned launches": "#8fa7b5",
    "Idle craft": "#ff9d2e",
    "Support flights": "#43e6a0",
    "Attention rows": "#ff5f6c",
}
ATTENTION_DRILLDOWN_LINKS = {
    "Return Fuel Board": data_tab_link("return_fuel"),
    "Fleet Board": data_tab_link("fleet"),
    "Route Board": data_tab_link("routes"),
    "People Movement": "/population/movement",
    "Cargo": "/cargo/manifests",
    "Technology": "/technology",
    "Body Board": data_tab_link("bodies"),
    "Save Selector": "/",
}
VALID_ATTENTION_LINKS = {
    "/",
    "/population",
    "/population/movement",
    "/population/places",
    "/cargo",
    "/cargo/movement",
    "/cargo/receipts",
    "/cargo/manifests",
    "/production",
    "/production/balance",
    "/production/sites",
    "/technology",
    "/data",
}
ATTENTION_SOURCE_PANES = {
    "Return Fuel Board": "Data Tables / Return Fuel",
    "Fleet Board": "Data Tables / Fleet",
    "Route Board": "Data Tables / Routes",
    "People Movement": "Population / Movement",
    "Cargo": "Cargo / Manifests",
    "Technology": "Technology",
    "Body Board": "Data Tables / Bodies",
    "Save Selector": "Save selector",
}
DIAGNOSTIC_ATTENTION_CATEGORIES = {"Save Data", "Technology"}


@dataclass(frozen=True)
class OverviewEvent:
    when: datetime
    label: str
    hint: str


def earliest_event(events: list[OverviewEvent]) -> OverviewEvent | None:
    return min(events, key=lambda event: event.when) if events else None


def figure_layout(fig: go.Figure, *, height: int = 290) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 120, "r": 18, "t": 16, "b": 44},
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12, "color": "#d7f7ff"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel={"bgcolor": "#06131c", "bordercolor": "#35d8ff", "font": {"color": "#e8f7ff"}},
    )
    fig.update_xaxes(
        automargin=True,
        color="#8fa7b5",
        gridcolor="rgba(86,179,214,0.16)",
        zerolinecolor="rgba(86,179,214,0.22)",
        tickfont={"size": 10},
    )
    fig.update_yaxes(
        automargin=True,
        color="#8fa7b5",
        gridcolor="rgba(86,179,214,0.16)",
        zerolinecolor="rgba(86,179,214,0.22)",
        tickfont={"size": 10},
    )
    return fig


def empty_figure(note: str, *, height: int = 290) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=note,
        x=0.5,
        y=0.5,
        showarrow=False,
        xref="paper",
        yref="paper",
        font={"size": 13, "color": "#8fa7b5"},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return figure_layout(fig, height=height)


def active_node_count(analysis: SaveAnalysis) -> int:
    node_ids: set[int] = set()
    for craft in analysis.craft_facts:
        for object_id in (craft.current_object_id, craft.true_object_id):
            if object_id is not None:
                node_ids.add(object_id)
    for mission in analysis.mission_facts:
        for object_id in (mission.start_id, mission.target_id):
            if object_id is not None:
                node_ids.add(object_id)
    node_ids.update(fact.object_id for fact in analysis.resource_stock_facts)
    node_ids.update(metric.object_id for metric in analysis.population_place_metrics)
    return len(node_ids)


def command_brief(analysis: SaveAnalysis, meta: dict[str, str]) -> dict[str, Any]:
    active_missions = sum(1 for mission in analysis.mission_facts if mission.status in ROUTE_ACTIVE_STATUSES)
    planned_missions = sum(1 for mission in analysis.mission_facts if mission.status in ROUTE_PLANNED_STATUSES)
    population = sum(metric.current_population for metric in analysis.population_place_metrics)
    places = len(analysis.population_place_metrics)
    support_tons = sum(metric.colonization_support_tons for metric in analysis.cargo_flight_metrics)
    attention_count = len(analysis.attention_rows)
    critical_attention = sum(1 for row in analysis.attention_rows if row.severity == "Critical")

    if places:
        title = f"Sustaining {fmt_num(population)} people across {fmt_num(places)} places"
    elif active_missions or planned_missions:
        title = f"Coordinating {fmt_num(active_missions + planned_missions)} logistics assignments"
    else:
        title = "No active logistics web detected"

    if critical_attention:
        posture = f"{fmt_num(critical_attention)} critical issue(s) need review before the network is quiet."
    elif attention_count:
        posture = f"{fmt_num(attention_count)} attention row(s) are queued for validation."
    elif active_missions or planned_missions:
        posture = "The current save has movement on the board and no critical flags."
    else:
        posture = "Use the evidence panes to validate the first routes, stocks, and unlocks for this save."

    return {
        "title": title,
        "posture": posture,
        "stats": [
            ("Game date", meta.get("current_time") or "-"),
            ("Network nodes", fmt_num(active_node_count(analysis))),
            ("Craft", fmt_num(len(analysis.craft_facts))),
            ("Support cargo", f"{fmt_num(support_tons)}t"),
        ],
        "scope": analysis.player_company or ", ".join(sorted(analysis.active_companies)) or "No company detected",
    }


def overview_event_rows(analysis: SaveAnalysis, *, limit: int = 10) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    craft_names = {(craft.company, craft.craft_id): craft.craft_name for craft in analysis.craft_facts}

    def add_event(
        *,
        event: str,
        when_dt: datetime | None,
        route: str,
        company: str,
        status: str,
        mission: str = "",
        craft: str = "",
        source: str = "",
    ) -> None:
        if when_dt is None:
            return
        route = route or source or "Save event"
        rows.append(
            {
                "event": event,
                "when_dt": when_dt,
                "when": fmt_dt(when_dt),
                "route": route,
                "route_label": route_label(route),
                "company": company,
                "status": status,
                "mission": mission,
                "craft": craft or source or "-",
                "source": source or event,
            }
        )

    for mission in analysis.mission_facts:
        names = tuple(
            craft_names[(mission.company, craft_id)]
            for craft_id in mission.craft_ids
            if (mission.company, craft_id) in craft_names
        )
        craft_hint = ", ".join(names) if names else "No craft name"
        if mission.status in ROUTE_PLANNED_STATUSES and mission.departure_dt is not None:
            add_event(
                event="Departure",
                when_dt=mission.departure_dt,
                route=mission.route or "Unknown route",
                company=mission.company,
                status=mission.status,
                mission=mission.mission_id,
                craft=craft_hint,
                source="Mission departure",
            )
        if mission.status in ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES and mission.arrival_dt is not None:
            add_event(
                event="Arrival",
                when_dt=mission.arrival_dt,
                route=mission.route or "Unknown route",
                company=mission.company,
                status=mission.status,
                mission=mission.mission_id,
                craft=craft_hint,
                source="Mission arrival",
            )

    for cargo in analysis.cargo_flight_metrics:
        if cargo.status not in ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES:
            continue
        if cargo.total_tons <= 0:
            continue
        add_event(
            event="Cargo Receipt",
            when_dt=cargo.arrival_dt,
            route=f"{cargo.destination}: {fmt_num(cargo.total_tons)}t inbound",
            company=cargo.company,
            status=cargo.status,
            mission=cargo.mission_id,
            craft=", ".join(cargo.craft_names),
            source="Cargo receipt",
        )

    for flight in analysis.population_flight_metrics:
        if flight.status not in ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES:
            continue
        if flight.people <= 0:
            continue
        add_event(
            event="People Arrival",
            when_dt=flight.arrival_dt,
            route=f"{flight.destination}: {fmt_num(flight.people)} people inbound",
            company=flight.company,
            status=flight.readiness_status,
            mission=flight.mission_id,
            craft=", ".join(flight.craft_names),
            source="Population movement",
        )

    for attention in analysis.attention_rows:
        when_dt = parse_event_date(attention.event_date)
        add_event(
            event="Attention",
            when_dt=when_dt,
            route=f"{attention.category}: {attention.title}",
            company=attention.company,
            status=attention.severity,
            mission=attention.mission_key,
            craft=attention.craft_name,
            source=attention.source,
        )

    for tech in analysis.tech_unlock_facts:
        if tech.unlock_date is None:
            continue
        add_event(
            event="Tech Unlock",
            when_dt=tech.unlock_date,
            route=f"{tech.display_name} ({tech.status})",
            company=tech.company,
            status=tech.category,
            mission=tech.research_id,
            source=tech.source_field,
        )

    return sorted(
        rows,
        key=lambda row: (row["when_dt"], EVENT_ORDER.get(row["event"], 99), row["route"], row["mission"]),
    )[:limit]


def parse_event_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def route_label(route: str, *, max_length: int = 34) -> str:
    label = route.replace("Low Orbit of ", "LO ")
    if len(label) <= max_length:
        return label
    return f"{label[: max_length - 3].rstrip()}..."


def operations_timeline_figure(rows: list[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("No dated departures or arrivals are visible in this save yet.")

    fig = go.Figure()
    for event in EVENT_COLORS:
        subset = [(index, row) for index, row in enumerate(rows) if row["event"] == event]
        if not subset:
            continue
        fig.add_trace(
            go.Scatter(
                x=[row["when_dt"] for _, row in subset],
                y=[index for index, _ in subset],
                mode="markers",
                marker={
                    "size": 15,
                    "color": EVENT_COLORS[event],
                    "symbol": EVENT_SYMBOLS.get(event, "circle"),
                    "line": {"color": "#e8f7ff", "width": 1},
                },
                customdata=[
                    [row["event"], row["when"], row["route"], row["status"], row["company"], row["craft"], row["source"]]
                    for _, row in subset
                ],
                hovertemplate=(
                    "%{customdata[0]} %{customdata[1]}<br>"
                    "%{customdata[2]}<br>"
                    "%{customdata[4]} · %{customdata[3]}<br>"
                    "%{customdata[5]}<br>"
                    "%{customdata[6]}<extra></extra>"
                ),
            )
        )
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(rows))),
        ticktext=[row["route_label"] for row in rows],
        autorange="reversed",
    )
    fig.update_xaxes(type="date")
    return figure_layout(fig, height=310)


def logistics_posture_rows(analysis: SaveAnalysis) -> list[tuple[str, int]]:
    active_missions = sum(1 for mission in analysis.mission_facts if mission.status in ROUTE_ACTIVE_STATUSES)
    planned_missions = sum(1 for mission in analysis.mission_facts if mission.status in ROUTE_PLANNED_STATUSES)
    idle_craft = sum(1 for craft in analysis.craft_facts if craft.status == "Idle")
    support_flights = sum(1 for metric in analysis.cargo_flight_metrics if metric.colonization_support_tons > 0)
    attention_rows = sum(1 for row in analysis.attention_rows if row.severity in ATTENTION_STATUSES)
    return [
        ("Active missions", active_missions),
        ("Planned launches", planned_missions),
        ("Idle craft", idle_craft),
        ("Support flights", support_flights),
        ("Attention rows", attention_rows),
    ]


def logistics_posture_figure(rows: list[tuple[str, int]]) -> go.Figure:
    if not any(value for _, value in rows):
        return empty_figure("No fleet posture has emerged yet.", height=250)
    labels = [label for label, _ in rows]
    values = [value for _, value in rows]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[POSTURE_COLORS.get(label, "#35d8ff") for label in labels],
            text=[fmt_num(value) for value in values],
            textposition="outside",
            hovertemplate="%{y}: %{x}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(rangemode="tozero")
    return figure_layout(fig, height=250)


def attention_group(row: Any) -> str:
    return "Diagnostics" if row.category in DIAGNOSTIC_ATTENTION_CATEGORIES else "Logistics"


def attention_sort_key(row: Any) -> tuple[int, str, str, str, str]:
    return (
        SEVERITY_RANK.get(row.severity, 9),
        row.event_date or "9999-99-99",
        row.category,
        row.title,
        row.attention_key,
    )


def attention_source_pane(drilldown: str) -> str:
    return ATTENTION_SOURCE_PANES.get(drilldown, drilldown if drilldown.startswith("/") else "Data Tables")


def verified_attention_link(drilldown: str) -> tuple[str, bool]:
    link = attention_link(drilldown)
    return (link, urlparse(link).path in VALID_ATTENTION_LINKS)


def attention_queue_rows(analysis: SaveAnalysis, *, limit: int | None = 5) -> list[dict[str, str]]:
    rows = sorted(analysis.attention_rows, key=attention_sort_key)
    if limit is not None:
        rows = rows[:limit]
    return [
        {
            "severity": row.severity,
            "category": row.category,
            "group": attention_group(row),
            "title": row.title,
            "message": row.message,
            "event_date": row.event_date or "-",
            "source": row.source,
            "source_pane": attention_source_pane(row.drilldown),
            "details": " · ".join(row.details[:2]),
            "link": link,
            "link_verified": "yes" if verified else "no",
        }
        for row in rows
        for link, verified in (verified_attention_link(row.drilldown),)
    ]


def attention_link(drilldown: str) -> str:
    if drilldown.startswith("/"):
        return drilldown
    return ATTENTION_DRILLDOWN_LINKS.get(drilldown, "/data")


def attention_queue_sections(analysis: SaveAnalysis, *, limit_per_section: int = 5) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    all_rows = attention_queue_rows(analysis, limit=None)
    for group, title, note in (
        ("Logistics", "Logistics Alerts", "Fuel, capacity, and sustainment rows that may change operations."),
        ("Diagnostics", "Parser Diagnostics", "Save-data and parser rows that explain confidence or missing metadata."),
    ):
        rows = [row for row in all_rows if row["group"] == group]
        if rows:
            sections.append(
                {
                    "group": group,
                    "title": title,
                    "note": note,
                    "count": len(rows),
                    "rows": rows[:limit_per_section],
                }
            )
    return sections


def overview_domain_cards(analysis: SaveAnalysis, meta: dict[str, str]) -> list[dict[str, str]]:
    idle_craft = sum(1 for craft in analysis.craft_facts if craft.status == "Idle" or not craft.has_active_assignment)
    loaded_craft = sum(1 for craft in analysis.craft_facts if craft.cargo_mass > 0 or craft.fuel_mass > 0)
    fleet_attention = sum(1 for row in analysis.attention_rows if row.craft_id is not None)
    population_concerns = sum(1 for row in analysis.attention_rows if row.category == "Population")
    support_flights = sum(1 for metric in analysis.cargo_flight_metrics if metric.colonization_support_tons > 0)
    support_tons = sum(metric.colonization_support_tons for metric in analysis.cargo_flight_metrics)
    cargo_concerns = sum(1 for row in analysis.attention_rows if row.category == "Cargo")
    production_risks = sum(1 for metric in analysis.production_balance_metrics if metric.status in ATTENTION_STATUSES)
    completed_tech = sum(1 for fact in analysis.tech_unlock_facts if fact.status == "Completed")
    active_tech = sum(1 for fact in analysis.tech_unlock_facts if fact.status != "Completed")
    save_data_attention = sum(1 for row in analysis.attention_rows if row.category == "Save Data")
    return [
        {
            "title": "Fleet Control",
            "value": fmt_num(len(analysis.craft_facts)),
            "copy": f"{fmt_num(idle_craft)} idle; {fmt_num(loaded_craft)} loaded; {fmt_num(fleet_attention)} craft attention row(s).",
            "url": "/fleet",
            "audit_url": data_tab_link("fleet"),
        },
        {
            "title": "Colonies",
            "value": fmt_num(len(analysis.population_place_metrics)),
            "copy": f"{meta.get('people_in_transit') or '0'} people moving; {fmt_num(population_concerns)} sustainment flag(s).",
            "url": "/population",
            "audit_url": data_tab_link("people"),
        },
        {
            "title": "Supply Lines",
            "value": fmt_num(support_flights),
            "copy": f"{fmt_num(support_tons)}t colony-support cargo; {fmt_num(cargo_concerns)} cargo concern(s).",
            "url": "/cargo",
            "audit_url": data_tab_link("cargo_audit"),
        },
        {
            "title": "Industrial Base",
            "value": fmt_num(len(analysis.production_balance_metrics)),
            "copy": f"{fmt_num(production_risks)} resource balance row(s) need production review.",
            "url": "/production",
            "audit_url": data_tab_link("production_audit"),
        },
        {
            "title": "Research Horizon",
            "value": fmt_num(completed_tech),
            "copy": f"{fmt_num(active_tech)} active, queued, or in-progress unlock row(s).",
            "url": "/technology",
            "audit_url": data_tab_link("technology_audit"),
        },
        {
            "title": "Evidence Tables",
            "value": fmt_num(save_data_attention),
            "copy": "Parser and save-data anomalies stay available for audit.",
            "url": data_tab_link("attention"),
            "audit_url": data_tab_link("attention"),
        },
    ]


def global_overview_kpis(analysis: SaveAnalysis) -> list[dict[str, str]]:
    active_missions = [mission for mission in analysis.mission_facts if mission.status in ROUTE_ACTIVE_STATUSES]
    planned_missions = [mission for mission in analysis.mission_facts if mission.status in ROUTE_PLANNED_STATUSES]
    idle_craft = [craft for craft in analysis.craft_facts if craft.status == "Idle"]
    next_arrival = earliest_event(
        [
            OverviewEvent(
                when=mission.arrival_dt,
                label=fmt_dt(mission.arrival_dt),
                hint=f"{mission.route or 'Unknown route'} ({mission.company})",
            )
            for mission in analysis.mission_facts
            if mission.status in ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES and mission.arrival_dt is not None
        ]
    )
    next_departure = earliest_event(
        [
            OverviewEvent(
                when=mission.departure_dt,
                label=fmt_dt(mission.departure_dt),
                hint=f"{mission.route or 'Unknown route'} ({mission.company})",
            )
            for mission in planned_missions
            if mission.departure_dt is not None
        ]
    )
    attention_count = len(analysis.attention_rows)
    critical_attention = sum(1 for row in analysis.attention_rows if row.severity == "Critical")

    return [
        {
            "label": "Active Missions",
            "value": fmt_num(len(active_missions)),
            "hint": "en route or cyclical assignments",
            "url": data_tab_link("routes"),
        },
        {
            "label": "Planned Departures",
            "value": fmt_num(len(planned_missions)),
            "hint": "scheduled assignments not yet launched",
            "url": data_tab_link("routes"),
        },
        {
            "label": "Next Arrival",
            "value": next_arrival.label if next_arrival else "-",
            "hint": next_arrival.hint if next_arrival else "no dated active/planned arrivals",
            "url": data_tab_link("routes"),
        },
        {
            "label": "Next Departure",
            "value": next_departure.label if next_departure else "-",
            "hint": next_departure.hint if next_departure else "no dated planned departures",
            "url": data_tab_link("routes"),
        },
        {
            "label": "Idle Craft",
            "value": fmt_num(len(idle_craft)),
            "hint": "craft without active assignments",
            "url": "/fleet",
        },
        {
            "label": "Needs Attention",
            "value": fmt_num(attention_count),
            "hint": f"{fmt_num(critical_attention)} critical row(s)" if critical_attention else "attention rows across all categories",
            "url": data_tab_link("attention"),
        },
    ]


def audit_shortcuts() -> tuple[tuple[str, str], ...]:
    return (
        ("Fleet Control", "/fleet"),
        ("Fleet Audit", data_tab_link("fleet")),
        ("Routes", data_tab_link("routes")),
        ("Bodies", data_tab_link("bodies")),
        ("Cargo", data_tab_link("cargo_audit")),
        ("Production", data_tab_link("production_audit")),
        ("Technology", data_tab_link("technology_audit")),
    )


def render_audit_shortcuts() -> None:
    with ui.row().classes("audit-shortcut-row"):
        ui.label("Audit").classes("overview-small-note")
        for label, url in audit_shortcuts():
            ui.link(label, url).classes("table-drilldown-link")


def render_global_overview_kpis(analysis: SaveAnalysis) -> None:
    with ui.element("div").classes("population-kpis population-kpis-compact"):
        for kpi in global_overview_kpis(analysis):
            element = ui.link(target=kpi["url"]).classes("population-kpi population-kpi-link")
            with element:
                ui.label(kpi["label"]).classes("population-kpi-label")
                ui.label(kpi["value"]).classes("population-kpi-value")
                ui.label(kpi["hint"]).classes("population-kpi-hint")


def render_overview_dashboard(analysis: SaveAnalysis, meta: dict[str, str]) -> None:
    brief = command_brief(analysis, meta)
    event_rows = overview_event_rows(analysis)
    queue_sections = attention_queue_sections(analysis)
    render_audit_shortcuts()
    with ui.element("div").classes("overview-command-grid"):
        with ui.element("div").classes("command-brief-panel"):
            ui.label("Command Brief").classes("command-brief-label")
            ui.label(brief["title"]).classes("command-brief-title")
            ui.label(brief["posture"]).classes("command-brief-copy")
            ui.label(f"Scope: {brief['scope']}").classes("command-brief-scope")
            with ui.element("div").classes("command-brief-stats"):
                for label, value in brief["stats"]:
                    with ui.element("div").classes("command-brief-stat"):
                        ui.label(label).classes("command-brief-stat-label")
                        ui.label(value).classes("command-brief-stat-value")
        with ui.element("div").classes("dashboard-card viz-card overview-viz-card"):
            with ui.row().classes("dashboard-title-row"):
                ui.label("Operations Timeline").classes("dashboard-card-title")
                ui.label(f"{len(event_rows)} next event(s)").classes("overview-small-note")
            ui.plotly(operations_timeline_figure(event_rows)).classes("viz-plot overview-timeline-plot")

    with ui.element("div").classes("overview-visual-grid"):
        with ui.element("div").classes("dashboard-card viz-card overview-viz-card"):
            with ui.row().classes("dashboard-title-row"):
                ui.label("Logistics Posture").classes("dashboard-card-title")
            ui.plotly(logistics_posture_figure(logistics_posture_rows(analysis))).classes("viz-plot overview-posture-plot")
        with ui.element("div").classes("dashboard-card overview-queue-card"):
            with ui.row().classes("dashboard-title-row"):
                ui.label("Attention Queue").classes("dashboard-card-title")
                ui.link("Open audit", data_tab_link("attention")).classes("table-drilldown-link")
            if queue_sections:
                with ui.element("div").classes("overview-queue-list"):
                    for section in queue_sections:
                        with ui.element("div").classes("overview-queue-section"):
                            with ui.row().classes("overview-queue-section-title-row"):
                                ui.label(section["title"]).classes("overview-queue-section-title")
                                ui.label(f"{section['count']} row(s)").classes("overview-small-note")
                            ui.label(section["note"]).classes("overview-queue-section-note")
                            for row in section["rows"]:
                                with ui.link(target=row["link"]).classes("overview-queue-row"):
                                    ui.label(row["severity"]).classes(
                                        f"overview-severity overview-severity-{row['severity'].lower()}"
                                    )
                                    with ui.element("div").classes("overview-queue-copy"):
                                        ui.label(f"{row['category']} · {row['title']}").classes("overview-queue-title")
                                        ui.label(row["message"]).classes("overview-queue-message")
                                        ui.label(f"Source: {row['source_pane']} · {row['event_date']}").classes(
                                            "overview-queue-source"
                                        )
                                        if row["details"]:
                                            ui.label(row["details"]).classes("overview-queue-message")
            else:
                ui.label("No attention rows for the focused save.").classes("empty-state-note")

    with ui.element("div").classes("overview-domain-grid"):
        for card in overview_domain_cards(analysis, meta):
            with ui.element("div").classes("section-card overview-domain-card"):
                ui.label(card["title"]).classes("section-card-title")
                ui.label(card["value"]).classes("overview-domain-value")
                ui.label(card["copy"]).classes("section-card-copy")
                with ui.row().classes("gap-2 mt-3"):
                    ui.link("Open", card["url"]).classes("section-link inline-flex")
                    ui.link("Audit", card["audit_url"]).classes("table-drilldown-link")
