from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable
from urllib.parse import urlencode

import plotly.graph_objects as go
from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.fact_model import CargoFlightMetric
from fleet_core.normalizer_utils import ROUTE_ACTIVE_STATUSES, ROUTE_PLANNED_STATUSES, fmt_num
from fleet_modules.shared import data_tab_link, fleet_link, resource_cell_slot, with_resource_icon


manifest_columns = [
    {"name": "expand", "label": "", "field": "expand", "sortable": False, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "mission", "label": "Mission", "field": "mission", "sortable": True, "align": "right"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "departure", "label": "Departure", "field": "departure", "sortable": True, "align": "left"},
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "tons", "label": "Tons", "field": "tons", "sortable": True, "align": "right"},
    {"name": "items", "label": "Items", "field": "items", "sortable": True, "align": "right"},
    {"name": "fuel", "label": "Fuel Cargo", "field": "fuel", "sortable": True, "align": "right"},
    {"name": "support", "label": "Colony Support", "field": "support", "sortable": True, "align": "left"},
    {"name": "top_cargo", "label": "Major Cargo", "field": "top_cargo", "sortable": False, "align": "left"},
]

SUPPORT_FILTER_ALL = "All cargo"
SUPPORT_FILTER_ANY = "Any colony support"
FILTER_ALL_COMPANIES = "All companies"
FILTER_ALL_STATUSES = "All statuses"
FILTER_ALL_KINDS = "All kinds"
FILTER_ALL_LOCATIONS = "All locations"
FILTER_ALL_ITEMS = "All items"
FILTER_ALL_MISSIONS = "All missions"
ARRIVAL_FILTER_ALL = "All arrivals"
ARRIVAL_FILTER_DATED = "Dated arrivals"
ARRIVAL_FILTER_UNDATED = "Undated arrivals"
ARRIVAL_FILTER_NEXT_180 = "Next 180 days"
ARRIVAL_FILTER_NEXT_YEAR = "Next year"

CargoKpis = list[tuple[str, str, str]]
CargoKpiBuilder = Callable[[list[dict[str, Any]], list[dict[str, Any]]], CargoKpis]
CARGO_FIGURE_COLORS = {
    "support": "#43e6a0",
    "other": "#35d8ff",
    "fuel": "#ff9d2e",
    "missing": "#ff5f6c",
}


def cargo_link(path: str, **params: object) -> str:
    clean = {key: str(value) for key, value in params.items() if value not in {None, ""}}
    query = urlencode(clean)
    return f"{path}?{query}" if query else path


def compact_summary(totals: dict[str, float] | tuple[tuple[str, float], ...], *, limit: int = 4) -> str:
    items = list(totals.items()) if isinstance(totals, dict) else list(totals)
    items = sorted(items, key=lambda item: (-item[1], item[0]))
    pieces = [f"{name} {fmt_num(mass)}t" for name, mass in items[:limit] if mass > 0]
    if len(items) > limit:
        pieces.append(f"+{len(items) - limit} more")
    return "; ".join(pieces)


def chart_label(value: object, *, max_length: int = 34) -> str:
    text = str(value).replace("Low Orbit of ", "LO ")
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def figure_layout(fig: go.Figure, *, height: int = 320) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 118, "r": 20, "t": 16, "b": 52},
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12, "color": "#d7f7ff"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#06131c", "bordercolor": "#35d8ff", "font": {"color": "#e8f7ff"}},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11},
        },
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


def empty_figure(note: str, *, height: int = 320) -> go.Figure:
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


def cargo_manifest_row(metric: CargoFlightMetric) -> dict[str, Any]:
    fleet_url = (
        fleet_link(craft=metric.craft_ids[0])
        if len(metric.craft_ids) == 1
        else fleet_link(mission=metric.mission_id or metric.mission_key)
    )
    return {
        "key": metric.flight_key,
        "company": metric.company,
        "status": metric.status,
        "mission": metric.mission_id,
        "craft_ids": ", ".join(str(craft_id) for craft_id in metric.craft_ids),
        "craft": ", ".join(metric.craft_names),
        "fleet_url": fleet_url,
        "route": metric.route,
        "source_id": metric.source_id,
        "target_id": metric.target_id,
        "source": metric.source,
        "destination": metric.destination,
        "departure": metric.departure,
        "arrival": metric.arrival,
        "arrival_dt": metric.arrival_dt,
        "departure_dt": metric.departure_dt,
        "tons_value": metric.total_tons,
        "tons": f"{fmt_num(metric.total_tons)}t",
        "items": metric.item_count,
        "fuel_tons_value": metric.fuel_tons,
        "fuel": f"{fmt_num(metric.fuel_tons)}t" if metric.fuel_tons else "",
        "support_tons_value": metric.colonization_support_tons,
        "support_items": metric.colonization_support_items,
        "support": compact_summary(metric.colonization_support_categories, limit=2),
        "support_categories": [category for category, _ in metric.colonization_support_categories],
        "top_cargo": compact_summary(metric.cargo_totals),
        "kind_summary": ", ".join(f"{kind} {count}" for kind, count in metric.kind_counts),
        "details": [
            with_resource_icon(
                {
                    "name": detail.name,
                    "kind": detail.kind,
                    "list": detail.list_label,
                    "mass": f"{fmt_num(detail.mass)}t",
                    "mass_value": detail.mass,
                    "resource_key": detail.resource_key,
                    "resource": detail.name,
                    "module": detail.module_key,
                    "support": detail.colonization_support_category,
                    "support_reason": detail.colonization_support_reason,
                }
            )
            for detail in metric.details
        ],
        "detail_count": len(metric.details),
    }


def cargo_manifest_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    return [cargo_manifest_row(metric) for metric in analysis.cargo_flight_metrics]


def cargo_hub_brief(
    analysis: SaveAnalysis,
    rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    active_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_ACTIVE_STATUSES)
    planned_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_PLANNED_STATUSES)
    support_tons = sum(float(row["support_tons_value"]) for row in rows)
    lanes = {str(row["route"]) for row in rows if row["route"]}
    destinations = {str(row["destination"]) for row in rows if row["destination"]}
    support_flights = sum(1 for row in rows if float(row["support_tons_value"]) > 0)
    missing_evidence = sum(1 for row in receipt_rows if row["local_status"] == "Missing")
    next_arrival = next_arrival_text(rows)

    lane_label = "cargo lane" if len(lanes) == 1 else "cargo lanes"
    if support_tons:
        title = f"{fmt_num(support_tons)}t colony support across {fmt_num(len(lanes))} {lane_label}"
    elif active_tons or planned_tons:
        title = f"{fmt_num(active_tons + planned_tons)}t cargo assigned across {fmt_num(len(lanes))} {lane_label}"
    else:
        title = "No cargo web detected"

    if missing_evidence:
        posture = f"{fmt_num(missing_evidence)} receipt row(s) need local stock or production evidence."
    elif support_tons:
        posture = "Support cargo is tied to manifests, receipts, and production evidence where available."
    elif rows:
        posture = "Cargo is moving, but no colonization-support classification is present in the focused save."
    else:
        posture = "Copy or load a save with cargo missions to validate supply lanes and receipts."

    return {
        "title": title,
        "posture": posture,
        "stats": [
            ("Active cargo", f"{fmt_num(active_tons)}t"),
            ("Planned cargo", f"{fmt_num(planned_tons)}t"),
            ("Destinations", fmt_num(len(destinations))),
            ("Next arrival", next_arrival),
        ],
        "scope": analysis.player_company or ", ".join(sorted(analysis.active_companies)) or "No company detected",
        "support_flights": support_flights,
    }


def cargo_lane_rows(rows: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        route = str(row["route"] or "Unknown route")
        group = groups.setdefault(
            route,
            {
                "route": route,
                "tons": 0.0,
                "support_tons": 0.0,
                "missions": set(),
                "next_arrival": "",
                "next_arrival_dt": None,
                "items": defaultdict(float),
            },
        )
        group["tons"] = float(group["tons"]) + float(row["tons_value"])
        group["support_tons"] = float(group["support_tons"]) + float(row["support_tons_value"])
        if row["mission"]:
            group["missions"].add(str(row["mission"]))
        arrival_dt = row.get("arrival_dt")
        if arrival_dt is not None and (group["next_arrival_dt"] is None or arrival_dt < group["next_arrival_dt"]):
            group["next_arrival_dt"] = arrival_dt
            group["next_arrival"] = row["arrival"]
        elif row["arrival"] and not group["next_arrival"]:
            group["next_arrival"] = row["arrival"]
        for detail in row["details"]:
            group["items"][str(detail["name"])] += float(detail["mass_value"])

    lane_rows: list[dict[str, Any]] = []
    for group in groups.values():
        lane_rows.append(
            {
                "route": group["route"],
                "route_label": chart_label(group["route"]),
                "tons": float(group["tons"]),
                "other_tons": max(float(group["tons"]) - float(group["support_tons"]), 0.0),
                "support_tons": float(group["support_tons"]),
                "missions": len(group["missions"]),
                "next_arrival": group["next_arrival"] or "-",
                "items": compact_summary(group["items"], limit=3) or "No item detail",
            }
        )
    return sorted(lane_rows, key=lambda row: (-float(row["support_tons"]), -float(row["tons"]), str(row["route"])))[:limit]


def support_mix_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        for detail in row["details"]:
            if detail["support"]:
                totals[str(detail["support"])] += float(detail["mass_value"])
    return [
        {"category": category, "tons": tons, "category_label": chart_label(category, max_length=24)}
        for category, tons in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]


def receipt_watch_rows(receipt_rows: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, str]]:
    status_rank = {"Missing": 0, "Critical": 1, "Urgent": 2, "Warning": 3, "Monitor": 4, "Stable": 5, "Module": 6}
    watched = sorted(
        receipt_rows,
        key=lambda row: (
            status_rank.get(str(row["local_status"]), 9),
            -float(row["tons_value"]),
            str(row["destination"]),
            str(row["item"]),
        ),
    )[:limit]
    return [
        {
            "status": str(row["local_status"]),
            "destination": str(row["destination"]),
            "item": str(row["item"]),
            "message": f"{row['tons']} inbound across {row['flights']} flight(s); next {row['next_arrival']}",
            "detail": str(row["production_read"]),
            "url": cargo_link("/cargo/receipts", destination=row["destination"], item=row["item"]),
        }
        for row in watched
    ]


def cargo_hub_cards(rows: list[dict[str, Any]], receipt_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    active_rows = [row for row in rows if row["status"] in ROUTE_ACTIVE_STATUSES]
    support_tons = sum(float(row["support_tons_value"]) for row in rows)
    support_flights = sum(1 for row in rows if float(row["support_tons_value"]) > 0)
    destinations = {str(row["destination"]) for row in receipt_rows if row["destination"]}
    local_evidence = sum(1 for row in receipt_rows if row["has_production_evidence"])
    detail_count = sum(len(row["details"]) for row in rows)
    item_count = sum(int(row["items"]) for row in rows)
    return [
        {
            "title": "Supply Lines",
            "value": fmt_num(len({row["route"] for row in rows if row["route"]})),
            "copy": f"{fmt_num(len(active_rows))} active/cyclical cargo flight(s) on the board.",
            "url": "/cargo/movement",
            "audit_url": data_tab_link("cargo_audit"),
        },
        {
            "title": "Colony Support",
            "value": f"{fmt_num(support_tons)}t",
            "copy": f"{fmt_num(support_flights)} flight(s) carry cargo classified for settlement prep.",
            "url": cargo_link("/cargo/manifests", support=SUPPORT_FILTER_ANY),
            "audit_url": data_tab_link("cargo_audit"),
        },
        {
            "title": "Receipts",
            "value": fmt_num(len(destinations)),
            "copy": f"{fmt_num(local_evidence)} of {fmt_num(len(receipt_rows))} receipt row(s) have local production evidence.",
            "url": "/cargo/receipts",
            "audit_url": data_tab_link("cargo_audit"),
        },
        {
            "title": "Manifests",
            "value": fmt_num(item_count),
            "copy": f"{fmt_num(detail_count)} expandable cargo detail line(s) across grouped manifests.",
            "url": "/cargo/manifests",
            "audit_url": data_tab_link("cargo_audit"),
        },
    ]


def cargo_lane_load_figure(lane_rows: list[dict[str, Any]]) -> go.Figure:
    if not lane_rows:
        return empty_figure("No active or planned cargo lanes were detected.")
    labels = [row["route_label"] for row in lane_rows]
    customdata = [
        [row["route"], row["missions"], row["next_arrival"], row["items"], row["support_tons"], row["tons"]]
        for row in lane_rows
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Colony support",
            x=[row["support_tons"] for row in lane_rows],
            y=labels,
            orientation="h",
            marker_color=CARGO_FIGURE_COLORS["support"],
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{x:.1f}t support cargo"
                "<br>%{customdata[1]} mission(s)"
                "<br>Next arrival %{customdata[2]}"
                "<br>%{customdata[3]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Other cargo",
            x=[row["other_tons"] for row in lane_rows],
            y=labels,
            orientation="h",
            marker_color=CARGO_FIGURE_COLORS["other"],
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{x:.1f}t other cargo"
                "<br>%{customdata[5]:.1f}t total"
                "<br>%{customdata[1]} mission(s)"
                "<br>Next arrival %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(barmode="stack", showlegend=True)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Cargo tons")
    return figure_layout(fig, height=330)


def support_mix_figure(rows: list[dict[str, Any]]) -> go.Figure:
    mix_rows = support_mix_rows(rows)
    if not mix_rows:
        return empty_figure("No colony-support cargo classifications are visible in this save.")
    fig = go.Figure(
        go.Bar(
            x=[row["tons"] for row in mix_rows],
            y=[row["category_label"] for row in mix_rows],
            orientation="h",
            marker_color=CARGO_FIGURE_COLORS["support"],
            customdata=[[row["category"], row["tons"]] for row in mix_rows],
            hovertemplate="%{customdata[0]}<br>%{customdata[1]:.1f}t<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Support cargo tons")
    return figure_layout(fig, height=300)


def cargo_kpis(rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    active_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_ACTIVE_STATUSES)
    planned_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_PLANNED_STATUSES)
    fuel_tons = sum(float(row["fuel_tons_value"]) for row in rows)
    support_tons = sum(float(row["support_tons_value"]) for row in rows)
    support_flights = sum(1 for row in rows if float(row["support_tons_value"]) > 0)
    routes = {row["route"] for row in rows if row["route"]}
    active_routes = {row["route"] for row in rows if row["route"] and row["status"] in ROUTE_ACTIVE_STATUSES}
    next_arrival = next_arrival_text(rows)

    item_totals: dict[str, float] = defaultdict(float)
    support_totals: dict[str, float] = defaultdict(float)
    for row in rows:
        for detail in row["details"]:
            item_totals[str(detail["name"])] += float(detail["mass_value"])
            if detail["support"]:
                support_totals[str(detail["support"])] += float(detail["mass_value"])
    top_cargo = compact_summary(item_totals, limit=2) or "-"
    top_support = compact_summary(support_totals, limit=2) or "-"

    return [
        ("Cargo Moving", f"{fmt_num(active_tons)}t", "active cargo currently en route or cycling"),
        ("Cargo Planned", f"{fmt_num(planned_tons)}t", "cargo assigned to planned flights"),
        ("Cargo Flights", str(len(rows)), "active/planned missions carrying cargo"),
        ("Active Routes", f"{len(active_routes)} / {len(routes)}", "active cargo lanes out of all cargo lanes"),
        ("Next Cargo Arrival", next_arrival, "earliest active/planned cargo arrival"),
        ("Top Cargo", top_cargo, "largest resources/modules across shown flights"),
        ("Colony Support", f"{fmt_num(support_tons)}t", f"{support_flights} flight(s); top support: {top_support}"),
        ("Fuel Cargo", f"{fmt_num(fuel_tons)}t", f"top cargo: {top_cargo}"),
    ]


def next_arrival_text(rows: list[dict[str, Any]]) -> str:
    dated_rows = sorted(
        (row for row in rows if row["arrival_dt"] is not None),
        key=lambda row: (row["arrival_dt"] or datetime.max, str(row["route"]), str(row["mission"])),
    )
    return str(dated_rows[0]["arrival"]) if dated_rows else "-"


def cargo_detail_totals(rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float], set[str], int]:
    item_totals: dict[str, float] = defaultdict(float)
    support_totals: dict[str, float] = defaultdict(float)
    kind_values: set[str] = set()
    detail_count = 0
    for row in rows:
        for detail in row["details"]:
            detail_count += 1
            item_totals[str(detail["name"])] += float(detail["mass_value"])
            if detail["kind"]:
                kind_values.add(str(detail["kind"]))
            if detail["support"]:
                support_totals[str(detail["support"])] += float(detail["mass_value"])
    return item_totals, support_totals, kind_values, detail_count


def cargo_movement_kpis(rows: list[dict[str, Any]], _receipt_rows: list[dict[str, Any]]) -> CargoKpis:
    active_rows = [row for row in rows if row["status"] in ROUTE_ACTIVE_STATUSES]
    planned_rows = [row for row in rows if row["status"] in ROUTE_PLANNED_STATUSES]
    active_tons = sum(float(row["tons_value"]) for row in active_rows)
    planned_tons = sum(float(row["tons_value"]) for row in planned_rows)
    routes = {row["route"] for row in rows if row["route"]}
    active_routes = {row["route"] for row in active_rows if row["route"]}
    undated = sum(1 for row in rows if row["arrival_dt"] is None)
    return [
        ("Movement Flights", str(len(rows)), "filtered cargo flights in this Movement view"),
        ("Active Cargo", f"{fmt_num(active_tons)}t", f"{len(active_rows)} active/cyclical flight(s) shown"),
        ("Planned Cargo", f"{fmt_num(planned_tons)}t", f"{len(planned_rows)} planned flight(s) shown"),
        ("Active Routes", f"{len(active_routes)} / {len(routes)}", "active lanes out of filtered cargo lanes"),
        ("Next Arrival", next_arrival_text(rows), "earliest dated arrival in the movement rows"),
        ("Undated Flights", str(undated), "shown flights without a parsed arrival timestamp"),
    ]


def cargo_receipt_kpis(rows: list[dict[str, Any]], receipt_rows: list[dict[str, Any]]) -> CargoKpis:
    destinations = {row["destination"] for row in receipt_rows if row["destination"]}
    items = {row["item"] for row in receipt_rows if row["item"]}
    inbound_tons = sum(float(row["tons_value"]) for row in receipt_rows)
    support_tons = sum(float(row["support_tons_value"]) for row in rows)
    evidence_count = sum(1 for row in receipt_rows if row["has_production_evidence"])
    missing_evidence = sum(1 for row in receipt_rows if row["local_status"] == "Missing")
    return [
        ("Destinations", str(len(destinations)), "receipt destinations in the current filter"),
        ("Receipt Rows", str(len(receipt_rows)), f"{len(items)} distinct cargo item(s) shown"),
        ("Inbound Tons", f"{fmt_num(inbound_tons)}t", "cargo mass represented by displayed receipt rows"),
        ("Local Evidence", f"{evidence_count} / {len(receipt_rows)}", "rows joined to local stock/flow/runway evidence"),
        ("Missing Evidence", str(missing_evidence), "resource receipt rows without local production rows"),
        ("Colony Support", f"{fmt_num(support_tons)}t", "support cargo represented by the receipt filter"),
    ]


def cargo_manifest_kpis(rows: list[dict[str, Any]], _receipt_rows: list[dict[str, Any]]) -> CargoKpis:
    item_totals, support_totals, kind_values, detail_count = cargo_detail_totals(rows)
    total_tons = sum(float(row["tons_value"]) for row in rows)
    item_count = sum(int(row["items"]) for row in rows)
    support_tons = sum(support_totals.values())
    support_flights = sum(1 for row in rows if float(row["support_tons_value"]) > 0)
    return [
        ("Manifest Flights", str(len(rows)), "grouped manifest rows currently shown"),
        ("Cargo Tons", f"{fmt_num(total_tons)}t", "cargo mass in displayed manifests"),
        ("Manifest Items", str(item_count), f"{detail_count} expandable cargo detail line(s)"),
        ("Cargo Kinds", str(len(kind_values)), "distinct cargo detail kinds in shown manifests"),
        ("Colony Support", f"{fmt_num(support_tons)}t", f"{support_flights} support flight(s) shown"),
        ("Top Cargo", compact_summary(item_totals, limit=2) or "-", "largest items in displayed manifests"),
    ]


def render_kpis(kpis: list[tuple[str, str, str]]) -> None:
    with ui.row().classes("population-kpis"):
        for label, value, hint in kpis:
            with ui.element("div").classes("population-kpi"):
                ui.label(label).classes("population-kpi-label")
                ui.label(value).classes("population-kpi-value")
                ui.label(hint).classes("population-kpi-hint")


def render_route_cards(rows: list[dict[str, Any]]) -> None:
    route_groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        route = str(row["route"] or "Unknown route")
        group = route_groups.setdefault(
            route,
            {
                "route": route,
                "tons": 0.0,
                "missions": 0,
                "next_arrival": "",
                "items": defaultdict(float),
            },
        )
        group["tons"] = float(group["tons"]) + float(row["tons_value"])
        group["missions"] = int(group["missions"]) + 1
        if row["arrival"] and (not group["next_arrival"] or row["arrival"] < group["next_arrival"]):
            group["next_arrival"] = row["arrival"]
        for detail in row["details"]:
            group["items"][str(detail["name"])] += float(detail["mass_value"])

    cards = sorted(route_groups.values(), key=lambda group: (-float(group["tons"]), str(group["route"])))[:6]
    with ui.element("div").classes("overview-grid cargo-route-grid"):
        if not cards:
            with ui.element("div").classes("section-card"):
                ui.label("No Cargo Transit").classes("section-card-title")
                ui.label("No active or planned cargo manifests were detected in the selected save scope.").classes("section-card-copy")
            return
        for card in cards:
            with ui.element("div").classes("section-card cargo-route-card"):
                ui.label(str(card["route"])).classes("section-card-title")
                ui.label(
                    f"{fmt_num(card['tons'])}t across {card['missions']} mission(s); "
                    f"next arrival {card['next_arrival'] or '-'}"
                ).classes("section-card-copy")
                ui.label(compact_summary(card["items"], limit=3) or "No item detail").classes("section-card-copy")


def cargo_in_transit_matrix_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        route = str(row["route"] or "Unknown route")
        status = str(row["status"] or "Unknown")
        group = groups.setdefault(
            (route, status),
            {
                "key": f"{route}:{status}",
                "route": route,
                "status": status,
                "flights": 0,
                "tons_value": 0.0,
                "support_value": 0.0,
                "next_arrival": "",
                "top_cargo_totals": defaultdict(float),
            },
        )
        group["flights"] = int(group["flights"]) + 1
        group["tons_value"] = float(group["tons_value"]) + float(row["tons_value"])
        group["support_value"] = float(group["support_value"]) + float(row["support_tons_value"])
        if row["arrival"] and (not group["next_arrival"] or row["arrival"] < group["next_arrival"]):
            group["next_arrival"] = row["arrival"]
        for detail in row["details"]:
            group["top_cargo_totals"][str(detail["name"])] += float(detail["mass_value"])

    matrix_rows: list[dict[str, Any]] = []
    for group in groups.values():
        matrix_rows.append(
            {
                "key": group["key"],
                "route": group["route"],
                "status": group["status"],
                "flights": group["flights"],
                "tons_value": group["tons_value"],
                "tons": f"{fmt_num(group['tons_value'])}t",
                "support_value": group["support_value"],
                "support": f"{fmt_num(group['support_value'])}t" if group["support_value"] else "",
                "next_arrival": group["next_arrival"] or "-",
                "top_cargo": compact_summary(group["top_cargo_totals"], limit=3),
            }
        )
    return sorted(matrix_rows, key=lambda row: (-float(row["tons_value"]), str(row["route"]), str(row["status"])))


def cargo_arrival_schedule_rows(rows: list[dict[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            row["arrival_dt"] is None,
            row["arrival_dt"] or datetime.max,
            str(row["route"]),
            str(row["mission"]),
        ),
    )
    return [
        {
            "key": row["key"],
            "arrival": row["arrival"] or "-",
            "status": row["status"],
            "mission": row["mission"],
            "craft": row["craft"],
            "destination": row["destination"] or "Unknown destination",
            "tons": row["tons"],
            "support": row["support"],
            "top_cargo": row["top_cargo"],
        }
        for row in sorted_rows[:limit]
    ]


def production_evidence_lookup(analysis: SaveAnalysis) -> dict[tuple[str, int, str], dict[str, Any]]:
    lookup: dict[tuple[str, int, str], dict[str, Any]] = {}
    for metric in analysis.production_balance_metrics:
        lookup[(metric.company, metric.object_id, metric.resource_key)] = {
            "key": metric.production_key,
            "status": metric.status,
            "stock_value": metric.stock,
            "stock": f"{fmt_num(metric.stock)}t",
            "net_value": metric.net_per_day,
            "net": f"{fmt_num(metric.net_per_day)}t/day",
            "runway_days": metric.runway_days,
            "runway": production_runway_text(metric.runway_days),
            "source": metric.source,
        }
    return lookup


def production_runway_text(days: float | None) -> str:
    if days is None:
        return "stable"
    if days >= 365:
        return f"{fmt_num(days / 365.0)}y"
    return f"{fmt_num(days)}d"


def destination_receipt_rows(
    rows: list[dict[str, Any]],
    production_evidence: dict[tuple[str, int, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    evidence = production_evidence or {}
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        destination = str(row["destination"] or "Unknown destination")
        for detail in row["details"]:
            item = str(detail["name"])
            resource_key = str(detail["resource_key"] or "")
            module_key = str(detail["module"] or "")
            group = groups.setdefault(
                (str(row["company"]), destination, item, resource_key or module_key),
                {
                    "key": f"{row['company']}:{destination}:{item}:{resource_key or module_key}",
                    "company": row["company"],
                    "target_id": row["target_id"],
                    "destination": destination,
                    "item": item,
                    "resource_key": resource_key,
                    "module_key": module_key,
                    "tons_value": 0.0,
                    "flights": set(),
                    "missions": set(),
                    "craft_ids": set(),
                    "craft": set(),
                    "support_categories": defaultdict(float),
                    "next_arrival": "",
                },
            )
            group["tons_value"] = float(group["tons_value"]) + float(detail["mass_value"])
            group["flights"].add(row["key"])
            if row["mission"]:
                group["missions"].add(str(row["mission"]))
            for craft_id in str(row.get("craft_ids") or "").split(","):
                if craft_id.strip():
                    group["craft_ids"].add(craft_id.strip())
            if row["craft"]:
                group["craft"].add(str(row["craft"]))
            if detail["support"]:
                group["support_categories"][str(detail["support"])] += float(detail["mass_value"])
            if row["arrival"] and (not group["next_arrival"] or row["arrival"] < group["next_arrival"]):
                group["next_arrival"] = row["arrival"]

    receipt_rows: list[dict[str, Any]] = []
    for group in groups.values():
        missions = sorted(group["missions"])
        craft_ids = sorted(group["craft_ids"], key=lambda value: int(value) if value.isdigit() else value)
        craft_names = sorted(group["craft"])
        fleet_url = (
            fleet_link(craft=craft_ids[0])
            if len(craft_ids) == 1
            else fleet_link(mission=missions[0])
            if missions
            else fleet_link(company=group["company"], object=group["target_id"])
        )
        local = {}
        production_link = ""
        if isinstance(group["target_id"], int) and group["resource_key"]:
            production_link = data_tab_link(
                "production_audit",
                company=group["company"],
                object=group["target_id"],
                resource=group["resource_key"],
            )
            local = evidence.get((str(group["company"]), int(group["target_id"]), str(group["resource_key"])), {})
        if local:
            production_read = f"{local['stock']} local; {local['net']} net; runway {local['runway']}"
            local_status = str(local["status"])
        elif group["resource_key"]:
            production_read = "No local stock/flow row"
            local_status = "Missing"
        else:
            production_read = "No production join for module cargo"
            local_status = "Module"
        receipt_rows.append(
            with_resource_icon(
                {
                "key": group["key"],
                "company": group["company"],
                "target_id": group["target_id"],
                "destination": group["destination"],
                "item": group["item"],
                "resource_key": group["resource_key"],
                "craft": "; ".join(craft_names) or "-",
                "craft_ids": ", ".join(craft_ids),
                "fleet_url": fleet_url,
                "tons_value": group["tons_value"],
                "tons": f"{fmt_num(group['tons_value'])}t",
                "flights": len(group["flights"]),
                "support": compact_summary(group["support_categories"], limit=2),
                "next_arrival": group["next_arrival"] or "-",
                "local_status": local_status,
                "local_stock": str(local.get("stock") or "-"),
                "local_net": str(local.get("net") or "-"),
                "local_runway": str(local.get("runway") or "-"),
                "production_read": production_read,
                "production_link": production_link,
                "has_production_evidence": bool(local),
                },
                resource_label_field="item",
                prefix="item",
            )
        )
    return sorted(receipt_rows, key=lambda row: (-float(row["tons_value"]), str(row["destination"]), str(row["item"])))


def destination_cargo_evidence_rows(
    rows: list[dict[str, Any]],
    production_evidence: dict[tuple[str, int, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    receipt_rows = destination_receipt_rows(rows, production_evidence)
    receipts_by_destination: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipt_rows:
        receipts_by_destination[(str(receipt["company"]), str(receipt["destination"]))].append(receipt)

    groups: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    for row in rows:
        if float(row["support_tons_value"]) <= 0:
            continue
        destination = str(row["destination"] or "Unknown destination")
        key = (str(row["company"]), destination, row["target_id"] if isinstance(row["target_id"], int) else None)
        group = groups.setdefault(
            key,
            {
                "key": f"{key[0]}:{key[1]}:{key[2] or 'unknown'}",
                "company": key[0],
                "destination": destination,
                "target_id": key[2],
                "support_tons_value": 0.0,
                "support_categories": defaultdict(float),
                "arrival_dates": set(),
                "missions": [],
                "craft": set(),
            },
        )
        group["support_tons_value"] = float(group["support_tons_value"]) + float(row["support_tons_value"])
        if row["arrival"]:
            group["arrival_dates"].add(str(row["arrival"]))
        if row["mission"]:
            group["missions"].append(str(row["mission"]))
        if row["craft"]:
            group["craft"].add(str(row["craft"]))
        for detail in row["details"]:
            if detail["support"]:
                group["support_categories"][str(detail["support"])] += float(detail["mass_value"])

    evidence_rows: list[dict[str, Any]] = []
    for group in groups.values():
        company = str(group["company"])
        destination = str(group["destination"])
        grouped_receipts = receipts_by_destination.get((company, destination), [])
        local_evidence = sum(1 for receipt in grouped_receipts if receipt["has_production_evidence"])
        missing_evidence = sum(1 for receipt in grouped_receipts if receipt["local_status"] == "Missing")
        production_keys = sorted(
            str(receipt["key"])
            for receipt in grouped_receipts
            if receipt["has_production_evidence"] and receipt.get("resource_key")
        )
        receipt_summary = compact_summary(
            {str(receipt["item"]): float(receipt["tons_value"]) for receipt in grouped_receipts},
            limit=3,
        )
        arrival_dates = sorted(group["arrival_dates"])
        missions = sorted(set(group["missions"]))
        craft = sorted(group["craft"])
        support = compact_summary(group["support_categories"], limit=3)
        link_params = {"company": company, "destination": destination, "support": SUPPORT_FILTER_ANY}
        mission_link = cargo_link("/cargo/manifests", **link_params, mission=missions[0]) if missions else ""
        evidence_rows.append(
            {
                "key": str(group["key"]),
                "company": company,
                "destination": destination,
                "target_id": group["target_id"] or "",
                "support_tons_value": group["support_tons_value"],
                "support": support,
                "support_classes": ", ".join(str(category) for category, _ in sorted(group["support_categories"].items())),
                "next_arrival": arrival_dates[0] if arrival_dates else "-",
                "arrival_dates": ", ".join(arrival_dates) or "-",
                "missions": ", ".join(missions) or "-",
                "craft": "; ".join(craft) or "-",
                "craft_missions": f"{'; '.join(craft) or '-'} / mission(s) {', '.join(missions) or '-'}",
                "receipt_summary": receipt_summary or "-",
                "production_summary": (
                    f"{local_evidence} local evidence row(s); {missing_evidence} missing"
                    if grouped_receipts
                    else "No receipt rows"
                ),
                "production_keys": ", ".join(production_keys),
                "receipts_link": cargo_link("/cargo/receipts", **link_params),
                "manifests_link": cargo_link("/cargo/manifests", **link_params),
                "mission_link": mission_link,
                "production_link": (
                    data_tab_link("production_audit", company=company, object=group["target_id"])
                    if isinstance(group["target_id"], int)
                    else data_tab_link("production_audit", company=company)
                ),
            }
        )
    return sorted(
        evidence_rows,
        key=lambda row: (-float(row["support_tons_value"]), str(row["destination"]), str(row["company"])),
    )


def render_compact_table(title: str, columns: list[dict[str, Any]], rows: list[dict[str, Any]], *, pagination: int = 8) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label(title).classes("dashboard-card-title")
        table = ui.table(columns=columns, rows=rows, row_key="key", pagination=pagination).classes("w-full")
        table.props("flat bordered dense wrap-cells")


def render_destination_receipts_table(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Destination Receipts").classes("dashboard-card-title")
        table = ui.table(columns=receipt_columns, rows=rows, row_key="key", pagination=8).classes("w-full")
        table.props("flat bordered dense wrap-cells")
        table.add_slot("body-cell-item", resource_cell_slot("item"))
        table.add_slot(
            "body-cell-craft",
            r"""
            <q-td :props="props">
                <a :href="props.row.fleet_url" class="table-drilldown-link">{{ props.row.craft }}</a>
            </q-td>
            """,
        )
        table.add_slot(
            "body-cell-production",
            r"""
            <q-td :props="props">
                <a
                    v-if="props.row.production_link"
                    :href="props.row.production_link"
                    class="table-drilldown-link"
                >
                    {{ props.row.production_read }}
                </a>
                <span v-else>{{ props.row.production_read }}</span>
            </q-td>
            """,
        )


def render_prep_evidence_table(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Colonization Prep Cargo Evidence").classes("dashboard-card-title")
        ui.label("Destination-filtered support cargo links for the future Prep Watchlist.").classes("section-card-copy")
        table = ui.table(columns=prep_evidence_columns, rows=rows, row_key="key", pagination=8).classes("w-full")
        table.props("flat bordered dense wrap-cells")
        table.add_slot(
            "body-cell-links",
            r"""
            <q-td :props="props">
                <a :href="props.row.receipts_link" class="table-drilldown-link">Receipts</a>
                <span class="q-mx-xs">/</span>
                <a :href="props.row.manifests_link" class="table-drilldown-link">Manifests</a>
                <span v-if="props.row.mission_link">
                    <span class="q-mx-xs">/</span>
                    <a :href="props.row.mission_link" class="table-drilldown-link">Mission</a>
                </span>
                <span class="q-mx-xs">/</span>
                <a :href="props.row.production_link" class="table-drilldown-link">Production</a>
            </q-td>
            """,
        )


matrix_columns = [
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "flights", "label": "Flights", "field": "flights", "sortable": True, "align": "right"},
    {"name": "tons", "label": "Tons", "field": "tons", "sortable": True, "align": "right"},
    {"name": "support", "label": "Support", "field": "support", "sortable": True, "align": "right"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "top_cargo", "label": "Top Cargo", "field": "top_cargo", "sortable": False, "align": "left"},
]

schedule_columns = [
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "mission", "label": "Mission", "field": "mission", "sortable": True, "align": "right"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "tons", "label": "Tons", "field": "tons", "sortable": True, "align": "right"},
    {"name": "support", "label": "Support", "field": "support", "sortable": True, "align": "left"},
    {"name": "top_cargo", "label": "Top Cargo", "field": "top_cargo", "sortable": False, "align": "left"},
]

receipt_columns = [
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "item", "label": "Item", "field": "item", "sortable": True, "align": "left"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "tons", "label": "Tons", "field": "tons", "sortable": True, "align": "right"},
    {"name": "flights", "label": "Flights", "field": "flights", "sortable": True, "align": "right"},
    {"name": "support", "label": "Support", "field": "support", "sortable": True, "align": "left"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "local_status", "label": "Local Status", "field": "local_status", "sortable": True, "align": "left"},
    {"name": "local_stock", "label": "Local Stock", "field": "local_stock", "sortable": True, "align": "right"},
    {"name": "local_net", "label": "Local Net/day", "field": "local_net", "sortable": True, "align": "right"},
    {"name": "local_runway", "label": "Local Runway", "field": "local_runway", "sortable": True, "align": "right"},
    {"name": "production", "label": "Evidence", "field": "production_read", "sortable": False, "align": "left"},
]

prep_evidence_columns = [
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "support", "label": "Support Cargo", "field": "support", "sortable": False, "align": "left"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "craft_missions", "label": "Craft / Missions", "field": "craft_missions", "sortable": False, "align": "left"},
    {"name": "receipt_summary", "label": "Receipt Summary", "field": "receipt_summary", "sortable": False, "align": "left"},
    {"name": "production_summary", "label": "Production Evidence", "field": "production_summary", "sortable": False, "align": "left"},
    {"name": "links", "label": "Links", "field": "links", "sortable": False, "align": "left"},
]


manifest_slots = {
    "body": r"""
        <q-tr :props="props">
            <q-td key="expand" :props="props">
                <q-btn
                    v-if="props.row.detail_count > 0"
                    size="sm"
                    color="primary"
                    round
                    dense
                    flat
                    @click="props.expand = !props.expand"
                    :icon="props.expand ? 'expand_less' : 'expand_more'"
                />
            </q-td>
            <q-td key="company" :props="props">{{ props.row.company }}</q-td>
            <q-td key="status" :props="props">{{ props.row.status }}</q-td>
            <q-td key="mission" :props="props">{{ props.row.mission }}</q-td>
            <q-td key="craft" :props="props">
                <a :href="props.row.fleet_url" class="table-drilldown-link">{{ props.row.craft }}</a>
            </q-td>
            <q-td key="route" :props="props">{{ props.row.route }}</q-td>
            <q-td key="departure" :props="props">{{ props.row.departure }}</q-td>
            <q-td key="arrival" :props="props">{{ props.row.arrival }}</q-td>
            <q-td key="tons" :props="props">{{ props.row.tons }}</q-td>
            <q-td key="items" :props="props">{{ props.row.items }}</q-td>
            <q-td key="fuel" :props="props">{{ props.row.fuel }}</q-td>
            <q-td key="support" :props="props">{{ props.row.support }}</q-td>
            <q-td key="top_cargo" :props="props">{{ props.row.top_cargo }}</q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td colspan="100%">
                <div class="cargo-detail">
                    <div class="cargo-detail-row cargo-detail-header">
                        <div>Item</div>
                        <div>Kind</div>
                        <div>Support</div>
                        <div>List</div>
                        <div>Mass</div>
                    </div>
                    <div
                        v-for="detail in props.row.details"
                        :key="detail.name + detail.kind + detail.list + detail.mass"
                        class="cargo-detail-row"
                    >
                        <div>
                            <span v-if="detail.resource_icon" class="resource-glyph-cell" :aria-label="detail.resource_title">
                                <img class="resource-glyph" :src="detail.resource_icon" :alt="detail.resource_label" />
                                <span class="resource-glyph-fallback">{{ detail.resource_label }}</span>
                                <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                                    <div class="return-fuel-tooltip-title">{{ detail.resource_label }}</div>
                                    <div class="return-fuel-tooltip-line">{{ detail.resource_key }}</div>
                                </q-tooltip>
                            </span>
                            <span v-else>{{ detail.name }}</span>
                        </div>
                        <div>{{ detail.kind }}</div>
                        <div>
                            <span v-if="detail.support">
                                {{ detail.support }}
                                <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                                <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                                    {{ detail.support_reason }}
                                </q-tooltip>
                            </span>
                        </div>
                        <div>{{ detail.list }}</div>
                        <div>{{ detail.mass }}</div>
                    </div>
                </div>
            </q-td>
        </q-tr>
    """,
}


def render_manifest_table(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Grouped Cargo Manifest").classes("dashboard-card-title")
        table = ui.table(
            columns=manifest_columns,
            rows=rows,
            row_key="key",
            pagination=10,
        ).classes("w-full")
        table.props("flat bordered dense wrap-cells")
        for slot_name, slot_template in manifest_slots.items():
            table.add_slot(slot_name, slot_template)


def support_filter_options(rows: list[dict[str, Any]]) -> list[str]:
    categories = sorted({category for row in rows for category in row["support_categories"]})
    return [SUPPORT_FILTER_ALL, SUPPORT_FILTER_ANY] + categories


def detail_option_values(rows: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(detail[key]) for row in rows for detail in row["details"] if detail.get(key)})


def filter_options(rows: list[dict[str, Any]], *, row_key: str, all_label: str) -> list[str]:
    return [all_label] + sorted({str(row[row_key]) for row in rows if row.get(row_key)})


def selected_filter_value(options: list[str], requested: str, fallback: str) -> str:
    return requested if requested in options else fallback


def cargo_row_matches_support_filter(row: dict[str, Any], support_filter: str) -> bool:
    if support_filter == SUPPORT_FILTER_ALL:
        return True
    categories = set(row["support_categories"])
    if support_filter == SUPPORT_FILTER_ANY:
        return bool(categories)
    return support_filter in categories


def cargo_row_matches_filters(row: dict[str, Any], filters: dict[str, str]) -> bool:
    if not cargo_row_matches_support_filter(row, filters.get("support", SUPPORT_FILTER_ALL)):
        return False
    if filters.get("company", FILTER_ALL_COMPANIES) != FILTER_ALL_COMPANIES and row["company"] != filters["company"]:
        return False
    if filters.get("status", FILTER_ALL_STATUSES) != FILTER_ALL_STATUSES and row["status"] != filters["status"]:
        return False
    if filters.get("mission", FILTER_ALL_MISSIONS) != FILTER_ALL_MISSIONS and str(row["mission"]) != filters["mission"]:
        return False
    if filters.get("source", FILTER_ALL_LOCATIONS) != FILTER_ALL_LOCATIONS and row["source"] != filters["source"]:
        return False
    if filters.get("destination", FILTER_ALL_LOCATIONS) != FILTER_ALL_LOCATIONS and row["destination"] != filters["destination"]:
        return False
    kind_filter = filters.get("kind", FILTER_ALL_KINDS)
    if kind_filter != FILTER_ALL_KINDS and not any(detail["kind"] == kind_filter for detail in row["details"]):
        return False
    item_filter = filters.get("item", FILTER_ALL_ITEMS)
    if item_filter != FILTER_ALL_ITEMS and not any(detail["name"] == item_filter for detail in row["details"]):
        return False
    arrival_filter = filters.get("arrival", ARRIVAL_FILTER_ALL)
    arrival_dt = row["arrival_dt"]
    if arrival_filter == ARRIVAL_FILTER_DATED and arrival_dt is None:
        return False
    if arrival_filter == ARRIVAL_FILTER_UNDATED and arrival_dt is not None:
        return False
    if arrival_filter in {ARRIVAL_FILTER_NEXT_180, ARRIVAL_FILTER_NEXT_YEAR}:
        if arrival_dt is None:
            return False
        dated = [other["arrival_dt"] for other in filters["_rows"] if other["arrival_dt"] is not None]
        if not dated:
            return False
        start = min(dated)
        horizon = timedelta(days=180 if arrival_filter == ARRIVAL_FILTER_NEXT_180 else 365)
        if arrival_dt > start + horizon:
            return False
    return True


def filter_cargo_rows(
    rows: list[dict[str, Any]],
    *,
    support_filter: str = SUPPORT_FILTER_ALL,
    company_filter: str = FILTER_ALL_COMPANIES,
    status_filter: str = FILTER_ALL_STATUSES,
    kind_filter: str = FILTER_ALL_KINDS,
    source_filter: str = FILTER_ALL_LOCATIONS,
    destination_filter: str = FILTER_ALL_LOCATIONS,
    item_filter: str = FILTER_ALL_ITEMS,
    arrival_filter: str = ARRIVAL_FILTER_ALL,
    mission_filter: str = FILTER_ALL_MISSIONS,
) -> list[dict[str, Any]]:
    filters = {
        "support": support_filter,
        "company": company_filter,
        "status": status_filter,
        "kind": kind_filter,
        "source": source_filter,
        "destination": destination_filter,
        "item": item_filter,
        "arrival": arrival_filter,
        "mission": mission_filter,
        "_rows": rows,
    }
    return [row for row in rows if cargo_row_matches_filters(row, filters)]


def render_cargo_section_links() -> None:
    with ui.element("div").classes("overview-grid"):
        for title, copy, path in (
            (
                "Movement",
                "Route cards, cargo in-transit matrix, and arrival schedule for timing-focused planning.",
                "/cargo/movement",
            ),
            (
                "Receipts",
                "Destination receipts joined to local stock, net/day, runway, and production evidence.",
                "/cargo/receipts",
            ),
            (
                "Manifests",
                "Grouped raw manifest inspection with expandable cargo detail and support classification.",
                "/cargo/manifests",
            ),
        ):
            with ui.element("div").classes("section-card"):
                ui.link(title, path).classes("section-card-title table-drilldown-link")
                ui.label(copy).classes("section-card-copy")


def render_chart_card(title: str, fig: go.Figure) -> None:
    fig.update_layout(title=None)
    with ui.element("div").classes("dashboard-card viz-card"):
        ui.label(title).classes("dashboard-card-title viz-card-title")
        ui.plotly(fig).classes("viz-plot")


def render_cargo_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    rows = cargo_manifest_rows(analysis)
    production_evidence = production_evidence_lookup(analysis)
    receipt_rows = destination_receipt_rows(rows, production_evidence)
    brief = cargo_hub_brief(analysis, rows, receipt_rows)
    lane_rows = cargo_lane_rows(rows)
    watch_rows = receipt_watch_rows(receipt_rows)
    cards = cargo_hub_cards(rows, receipt_rows)
    with container:
        with ui.element("div").classes("overview-command-grid cargo-hub-command-grid"):
            with ui.element("div").classes("command-brief-panel"):
                ui.label("Cargo Brief").classes("command-brief-label")
                ui.label(brief["title"]).classes("command-brief-title")
                ui.label(brief["posture"]).classes("command-brief-copy")
                ui.label(f"Scope: {brief['scope']}").classes("command-brief-scope")
                ui.link("Open cargo audit", data_tab_link("cargo_audit")).classes("table-drilldown-link")
                with ui.element("div").classes("command-brief-stats"):
                    for label, value in brief["stats"]:
                        with ui.element("div").classes("command-brief-stat"):
                            ui.label(label).classes("command-brief-stat-label")
                            ui.label(value).classes("command-brief-stat-value")
            render_chart_card("Cargo Lane Load", cargo_lane_load_figure(lane_rows))

        with ui.element("div").classes("overview-visual-grid cargo-hub-visual-grid"):
            render_chart_card("Colony Support Mix", support_mix_figure(rows))
            with ui.element("div").classes("dashboard-card overview-queue-card"):
                with ui.row().classes("dashboard-title-row"):
                    ui.label("Receipt Watch").classes("dashboard-card-title")
                    ui.link("Open receipts", "/cargo/receipts").classes("table-drilldown-link")
                if watch_rows:
                    with ui.element("div").classes("overview-queue-list"):
                        for row in watch_rows:
                            severity_class = "urgent" if row["status"] in {"Missing", "Critical", "Urgent"} else "monitor"
                            with ui.link(target=row["url"]).classes("overview-queue-row"):
                                ui.label(row["status"]).classes(f"overview-severity overview-severity-{severity_class}")
                                with ui.element("div").classes("overview-queue-copy"):
                                    ui.label(f"{row['destination']} · {row['item']}").classes("overview-queue-title")
                                    ui.label(row["message"]).classes("overview-queue-message")
                                    ui.label(row["detail"]).classes("overview-queue-message")
                else:
                    ui.label("No receipt rows for active or planned cargo in the focused save.").classes("empty-state-note")

        with ui.element("div").classes("overview-domain-grid cargo-hub-domain-grid"):
            for card in cards:
                with ui.element("div").classes("section-card overview-domain-card"):
                    ui.label(card["title"]).classes("section-card-title")
                    ui.label(card["value"]).classes("overview-domain-value")
                    ui.label(card["copy"]).classes("section-card-copy")
                    with ui.row().classes("gap-2 mt-3"):
                        ui.link("Open", card["url"]).classes("section-link inline-flex")
                        ui.link("Audit", card["audit_url"]).classes("table-drilldown-link")


def render_cargo_filtered_dashboard(
    analysis: SaveAnalysis,
    container: ui.element,
    *,
    title: str,
    subtitle: str,
    kpi_builder: CargoKpiBuilder,
    initial_filters: dict[str, str] | None = None,
    show_route_cards: bool = False,
    show_matrix: bool = False,
    show_schedule: bool = False,
    show_receipts: bool = False,
    show_manifest: bool = False,
) -> None:
    container.clear()
    rows = cargo_manifest_rows(analysis)
    production_evidence = production_evidence_lookup(analysis)
    requested_filters = initial_filters or {}
    with container:
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-xl font-semibold")
                ui.label(subtitle).classes("text-sm text-slate-600")
        kpi_container = ui.column().classes("w-full")
        with ui.element("div").classes("chart-control-panel chart-control-panel-compact"):
            with ui.row().classes("chart-control-row"):
                support_options = support_filter_options(rows)
                company_options = filter_options(rows, row_key="company", all_label=FILTER_ALL_COMPANIES)
                status_options = filter_options(rows, row_key="status", all_label=FILTER_ALL_STATUSES)
                kind_options = [FILTER_ALL_KINDS] + detail_option_values(rows, "kind")
                source_options = filter_options(rows, row_key="source", all_label=FILTER_ALL_LOCATIONS)
                destination_options = filter_options(rows, row_key="destination", all_label=FILTER_ALL_LOCATIONS)
                item_options = [FILTER_ALL_ITEMS] + detail_option_values(rows, "name")
                arrival_options = [
                    ARRIVAL_FILTER_ALL,
                    ARRIVAL_FILTER_DATED,
                    ARRIVAL_FILTER_UNDATED,
                    ARRIVAL_FILTER_NEXT_180,
                    ARRIVAL_FILTER_NEXT_YEAR,
                ]
                mission_options = filter_options(rows, row_key="mission", all_label=FILTER_ALL_MISSIONS)
                support_select = ui.select(
                    options=support_options,
                    value=selected_filter_value(support_options, requested_filters.get("support", ""), SUPPORT_FILTER_ALL),
                    label="Colonization Support",
                ).classes("chart-control")
                company_select = ui.select(
                    options=company_options,
                    value=selected_filter_value(company_options, requested_filters.get("company", ""), FILTER_ALL_COMPANIES),
                    label="Company",
                ).classes("chart-control")
                status_select = ui.select(
                    options=status_options,
                    value=selected_filter_value(status_options, requested_filters.get("status", ""), FILTER_ALL_STATUSES),
                    label="Status",
                ).classes("chart-control")
                kind_select = ui.select(
                    options=kind_options,
                    value=selected_filter_value(kind_options, requested_filters.get("kind", ""), FILTER_ALL_KINDS),
                    label="Kind",
                ).classes("chart-control")
                source_select = ui.select(
                    options=source_options,
                    value=selected_filter_value(source_options, requested_filters.get("source", ""), FILTER_ALL_LOCATIONS),
                    label="Source",
                ).classes("chart-control")
                destination_select = ui.select(
                    options=destination_options,
                    value=selected_filter_value(
                        destination_options,
                        requested_filters.get("destination", ""),
                        FILTER_ALL_LOCATIONS,
                    ),
                    label="Destination",
                ).classes("chart-control")
                item_select = ui.select(
                    options=item_options,
                    value=selected_filter_value(item_options, requested_filters.get("item", ""), FILTER_ALL_ITEMS),
                    label="Item",
                ).classes("chart-control")
                arrival_select = ui.select(
                    options=arrival_options,
                    value=selected_filter_value(arrival_options, requested_filters.get("arrival", ""), ARRIVAL_FILTER_ALL),
                    label="Arrival",
                ).classes("chart-control")
                mission_select = ui.select(
                    options=mission_options,
                    value=selected_filter_value(mission_options, requested_filters.get("mission", ""), FILTER_ALL_MISSIONS),
                    label="Mission",
                ).classes("chart-control")
                summary = ui.label("").classes("chart-control-summary")
        route_container = ui.column().classes("w-full")
        panel_container = ui.column().classes("w-full")
        table_container = ui.column().classes("w-full")

        def update_filtered_cargo() -> None:
            filtered_rows = filter_cargo_rows(
                rows,
                support_filter=str(support_select.value or SUPPORT_FILTER_ALL),
                company_filter=str(company_select.value or FILTER_ALL_COMPANIES),
                status_filter=str(status_select.value or FILTER_ALL_STATUSES),
                kind_filter=str(kind_select.value or FILTER_ALL_KINDS),
                source_filter=str(source_select.value or FILTER_ALL_LOCATIONS),
                destination_filter=str(destination_select.value or FILTER_ALL_LOCATIONS),
                item_filter=str(item_select.value or FILTER_ALL_ITEMS),
                arrival_filter=str(arrival_select.value or ARRIVAL_FILTER_ALL),
                mission_filter=str(mission_select.value or FILTER_ALL_MISSIONS),
            )
            support_tons = sum(float(row["support_tons_value"]) for row in filtered_rows)
            summary.text = (
                f"Showing {len(filtered_rows)} of {len(rows)} cargo flight(s); "
                f"{fmt_num(support_tons)}t classified as colonization support."
            )
            route_container.clear()
            panel_container.clear()
            table_container.clear()
            receipt_rows = destination_receipt_rows(filtered_rows, production_evidence) if show_receipts else []
            prep_evidence_rows = destination_cargo_evidence_rows(filtered_rows, production_evidence) if show_receipts else []
            kpi_container.clear()
            with kpi_container:
                render_kpis(kpi_builder(filtered_rows, receipt_rows))
            if show_route_cards:
                with route_container:
                    render_route_cards(filtered_rows)
            with panel_container:
                if show_matrix:
                    render_compact_table(
                        "Cargo In-Transit Matrix",
                        matrix_columns,
                        cargo_in_transit_matrix_rows(filtered_rows),
                    )
                if show_schedule:
                    render_compact_table("Cargo Arrival Schedule", schedule_columns, cargo_arrival_schedule_rows(filtered_rows))
                if show_receipts:
                    render_prep_evidence_table(prep_evidence_rows)
                    render_destination_receipts_table(receipt_rows)
            if show_manifest:
                with table_container:
                    render_manifest_table(filtered_rows)

        for control in (
            support_select,
            company_select,
            status_select,
            kind_select,
            source_select,
            destination_select,
            item_select,
            arrival_select,
            mission_select,
        ):
            control.on_value_change(lambda _: update_filtered_cargo())
        update_filtered_cargo()


def render_cargo_movement_dashboard(
    analysis: SaveAnalysis,
    container: ui.element,
    initial_filters: dict[str, str] | None = None,
) -> None:
    render_cargo_filtered_dashboard(
        analysis,
        container,
        title="Cargo Movement",
        subtitle="What cargo is moving, which lanes are active, and when the next receipts arrive.",
        kpi_builder=cargo_movement_kpis,
        initial_filters=initial_filters,
        show_route_cards=True,
        show_matrix=True,
        show_schedule=True,
    )


def render_cargo_receipts_dashboard(
    analysis: SaveAnalysis,
    container: ui.element,
    initial_filters: dict[str, str] | None = None,
) -> None:
    render_cargo_filtered_dashboard(
        analysis,
        container,
        title="Cargo Receipts",
        subtitle="Inbound cargo by destination with local stock, production flow, and runway evidence.",
        kpi_builder=cargo_receipt_kpis,
        initial_filters=initial_filters,
        show_receipts=True,
    )


def render_cargo_manifests_dashboard(
    analysis: SaveAnalysis,
    container: ui.element,
    initial_filters: dict[str, str] | None = None,
) -> None:
    render_cargo_filtered_dashboard(
        analysis,
        container,
        title="Cargo Manifests",
        subtitle="Raw cargo manifest inspection with item, kind, and colonization-support filters.",
        kpi_builder=cargo_manifest_kpis,
        initial_filters=initial_filters,
        show_manifest=True,
    )
