from __future__ import annotations

from collections import defaultdict
from math import isfinite, log10
from typing import Any

import plotly.graph_objects as go
from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import fmt_num
from fleet_modules.shared import InfoTooltipContent, render_info_tooltip


production_columns = [
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "place", "label": "Location", "field": "place", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "resource", "label": "Resource", "field": "resource", "sortable": True, "align": "left"},
    {"name": "stock", "label": "Stock", "field": "stock", "sortable": True, "align": "right"},
    {"name": "intake", "label": "In/day", "field": "intake", "sortable": True, "align": "right"},
    {"name": "outtake", "label": "Out/day", "field": "outtake", "sortable": True, "align": "right"},
    {"name": "net", "label": "Net/day", "field": "net", "sortable": True, "align": "right"},
    {"name": "runway", "label": "Runway", "field": "runway", "sortable": True, "align": "right"},
]

HEATMAP_MODES = {
    "balance": "Balance Focus",
    "exporter": "Exporter Focus",
    "volume": "Volume Focus",
    "stock": "Stock Focus",
}

HEATMAP_MODE_HELP = {
    "balance": InfoTooltipContent(
        title="Balance Focus",
        lines=(
            "Highlights the strongest production surpluses and deficits by net/day.",
            "Use this first when you want to see what can supply what is short.",
            "Color is net/day: green surplus, red deficit.",
        ),
    ),
    "exporter": InfoTooltipContent(
        title="Exporter Focus",
        lines=(
            "Prioritizes strongest positive net/day producers.",
            "Use this to find candidate supply sources for cargo planning.",
            "Color is net/day: greener cells are stronger exporters.",
        ),
    ),
    "volume": InfoTooltipContent(
        title="Volume Focus",
        lines=(
            "Prioritizes highest intake plus outtake activity.",
            "Use this to find where the industrial mass of the economy is moving.",
            "High volume can be healthy, so pair this with Risk or Balance Focus.",
        ),
    ),
    "stock": InfoTooltipContent(
        title="Stock Focus",
        lines=(
            "Prioritizes stored inventory rather than daily flow.",
            "Color uses log10(stock + 1) so huge stockpiles do not flatten smaller reserves.",
            "Hover still shows real stock tons.",
        ),
    ),
}

HEATMAP_MODE_SUMMARIES = {
    "balance": "Surpluses and deficits by net/day; best first pass for logistics planning.",
    "exporter": "Positive-net producers; best for finding candidate supply sources.",
    "volume": "Highest intake plus outtake; best for seeing where industry is active.",
    "stock": "Stored inventory with log color; best for locating reserves without flattening small stocks.",
}

OTHER_PLACES = "Other locations"
OTHER_RESOURCES = "Other resources"
SUPPLY_RESOURCE_KEY = "id_resource_supply"
FUEL_RESOURCE_KEYS = {"id_resource_fuel", "id_resource_noblegas", "id_resource_hydrogen", "id_resource_hel3"}
CONSTRUCTION_RESOURCE_KEYS = {
    "id_resource_alloy",
    "id_resource_chips",
    "id_resource_glass",
    "id_resource_metal",
    "id_resource_plastic",
    "id_resource_raremetal",
    "id_resource_silicon",
    "id_resource_steel",
}


def status_class(status: str) -> str:
    return {
        "Stable": "readiness-safe",
        "Monitor": "readiness-monitor",
        "Warning": "readiness-warning",
        "Urgent": "readiness-urgent",
        "Critical": "readiness-critical",
    }.get(status, "readiness-safe")


def runway_text(days: float | None) -> str:
    if days is None:
        return "stable"
    if days >= 365:
        return f"{fmt_num(days / 365.0)}y"
    return f"{fmt_num(days)}d"


def runway_years(days: float | None) -> str:
    if days is None:
        return "stable"
    return f"{fmt_num(days / 365.0)} years"


def status_weight(status: str) -> int:
    return {"Critical": 0, "Urgent": 1, "Warning": 2, "Monitor": 3, "Stable": 4}.get(status, 9)


def watchlist_read(row: dict[str, Any]) -> str:
    status = str(row["status"])
    if status == "Critical":
        return "Immediate logistics gap"
    if status == "Urgent":
        return "Needs planned resupply"
    if status == "Warning":
        return "Schedule before it tightens"
    if status == "Monitor":
        return "Long-runway drawdown"
    return "Stable"


def chart_label(label: str, *, max_len: int = 18) -> str:
    return label if len(label) <= max_len else f"{label[: max_len - 1]}..."


def axis_label(label: str, *, max_len: int = 24) -> str:
    if len(label) <= max_len:
        return label
    keep = max_len - 3
    front = max(8, keep // 2)
    back = max(6, keep - front)
    return f"{label[:front]}...{label[-back:]}"


def row_activity_score(row: dict[str, Any]) -> float:
    return (
        abs(float(row["net_value"])) * 365.0
        + float(row["intake_value"]) * 90.0
        + float(row["outtake_value"]) * 90.0
        + abs(float(row["stock_value"]))
    )


def heatmap_focus_score(row: dict[str, Any], mode: str) -> float:
    stock = abs(float(row["stock_value"]))
    intake = float(row["intake_value"])
    outtake = float(row["outtake_value"])
    net = float(row["net_value"])
    if mode == "risk":
        if net >= 0:
            return 0.0
        runway = row["runway_days"]
        runway_score = 100000.0 / (1.0 + float(runway)) if runway is not None else 0.0
        return runway_score + abs(net) * 365.0 + outtake * 90.0
    if mode == "exporter":
        return max(net, 0.0) * 365.0 + intake * 30.0
    if mode == "volume":
        return intake + outtake
    if mode == "stock":
        return stock
    return abs(net) * 365.0 + max(intake, outtake) * 30.0


def production_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in analysis.production_balance_metrics:
        details = [
            f"Stock: {fmt_num(metric.stock)}t",
            f"Intake: {fmt_num(metric.intake_per_day)}t/day",
            f"Outtake: {fmt_num(metric.outtake_per_day)}t/day",
            f"Net: {fmt_num(metric.net_per_day)}t/day",
            f"Runway: {runway_text(metric.runway_days)}",
            f"Basis: {metric.status_basis}",
        ]
        rows.append(
            {
                "key": metric.production_key,
                "status": metric.status,
                "status_class": status_class(metric.status),
                "status_basis": metric.status_basis,
                "status_details": details,
                "company": metric.company,
                "object_id": metric.object_id,
                "place": metric.object_label,
                "type": metric.object_type,
                "resource": metric.resource_name,
                "resource_key": metric.resource_key,
                "stock_value": metric.stock,
                "stock": f"{fmt_num(metric.stock)}t",
                "intake_value": metric.intake_per_day,
                "intake": f"{fmt_num(metric.intake_per_day)}t",
                "outtake_value": metric.outtake_per_day,
                "outtake": f"{fmt_num(metric.outtake_per_day)}t",
                "net_value": metric.net_per_day,
                "net": f"{fmt_num(metric.net_per_day)}t",
                "runway_days": metric.runway_days,
                "runway": runway_text(metric.runway_days),
                "source": metric.source,
            }
        )
    return rows


def compact_resource_summary(totals: dict[str, float], *, limit: int = 2) -> str:
    items = sorted(totals.items(), key=lambda item: (-abs(item[1]), item[0]))
    pieces = [f"{name} {fmt_num(value)}t/d" for name, value in items[:limit] if value]
    if len(items) > limit:
        pieces.append(f"+{len(items) - limit} more")
    return "; ".join(pieces) or "-"


def production_kpis(rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    places = {row["place"] for row in rows}
    resources = {row["resource"] for row in rows}
    negative_rows = [row for row in rows if float(row["net_value"]) < 0]
    concern_rows = [row for row in rows if row["status"] in {"Critical", "Urgent", "Warning"}]
    empty_negative = [row for row in negative_rows if float(row["stock_value"]) <= 0]
    exporters: dict[str, float] = defaultdict(float)
    consumers: dict[str, float] = defaultdict(float)
    for row in rows:
        net = float(row["net_value"])
        if net > 0:
            exporters[str(row["resource"])] += net
        elif net < 0:
            consumers[str(row["resource"])] += abs(net)

    return [
        ("Tracked Places", str(len(places)), f"{len(resources)} resources with stock or flow"),
        ("Stock/Flow Rows", str(len(rows)), "company-local resource rows from the save"),
        ("Negative Net", str(len(negative_rows)), "resource/location rows burning down"),
        ("Runway Concerns", str(len(concern_rows)), "negative flow under the two-year threshold"),
        ("Empty + Burning", str(len(empty_negative)), "empty stock with negative net flow"),
        ("Top Flows", compact_resource_summary(exporters), f"largest consumers: {compact_resource_summary(consumers)}"),
    ]


def sustainment_watchlist_rows(rows: list[dict[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    risk_rows = [
        row
        for row in rows
        if float(row["net_value"]) < 0
        and row["runway_days"] is not None
        and isfinite(float(row["runway_days"]))
    ]
    selected = sorted(
        risk_rows,
        key=lambda row: (
            status_weight(str(row["status"])),
            float(row["runway_days"]),
            -abs(float(row["net_value"])),
            str(row["place"]),
            str(row["resource"]),
        ),
    )[:limit]

    watch_rows: list[dict[str, Any]] = []
    for row in selected:
        details = [
            f"Stock: {row['stock']}",
            f"Intake: {row['intake']} per day",
            f"Outtake: {row['outtake']} per day",
            f"Net: {row['net']} per day",
            f"Runway: {runway_years(row['runway_days'])}",
            f"Basis: {row['status_basis']}",
        ]
        watch_rows.append(
            {
                "key": f"watch:{row['key']}",
                "status": row["status"],
                "status_class": row["status_class"],
                "company": row["company"],
                "place": row["place"],
                "type": row["type"],
                "resource": row["resource"],
                "stock": row["stock"],
                "net": row["net"],
                "runway": row["runway"],
                "read": watchlist_read(row),
                "details": details,
            }
        )
    return watch_rows


def candidate_site_stock_rows(rows: list[dict[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["company"]), int(row["object_id"]), str(row["place"]))
        group = groups.setdefault(
            key,
            {
                "key": f"candidate:{row['company']}:{row['object_id']}",
                "company": row["company"],
                "place": row["place"],
                "type": row["type"],
                "rows": 0,
                "support_stock": 0.0,
                "supply_stock": 0.0,
                "supply_net": 0.0,
                "fuel_stock": 0.0,
                "construction_stock": 0.0,
                "other_stock": 0.0,
                "shortest_runway_days": None,
                "worst_status": "Stable",
                "resource_reads": [],
            },
        )
        stock = float(row["stock_value"])
        net = float(row["net_value"])
        resource_key = str(row["resource_key"])
        group["rows"] = int(group["rows"]) + 1
        if resource_key == SUPPLY_RESOURCE_KEY:
            group["supply_stock"] = float(group["supply_stock"]) + stock
            group["supply_net"] = float(group["supply_net"]) + net
            group["support_stock"] = float(group["support_stock"]) + stock
        elif resource_key in FUEL_RESOURCE_KEYS:
            group["fuel_stock"] = float(group["fuel_stock"]) + stock
            group["support_stock"] = float(group["support_stock"]) + stock
        elif resource_key in CONSTRUCTION_RESOURCE_KEYS:
            group["construction_stock"] = float(group["construction_stock"]) + stock
            group["support_stock"] = float(group["support_stock"]) + stock
        else:
            group["other_stock"] = float(group["other_stock"]) + stock

        runway = row["runway_days"]
        if runway is not None and isfinite(float(runway)):
            current = group["shortest_runway_days"]
            group["shortest_runway_days"] = float(runway) if current is None else min(float(current), float(runway))
        if status_weight(str(row["status"])) < status_weight(str(group["worst_status"])):
            group["worst_status"] = str(row["status"])
        if row["status"] != "Stable" or resource_key in {SUPPLY_RESOURCE_KEY, *FUEL_RESOURCE_KEYS, *CONSTRUCTION_RESOURCE_KEYS}:
            group["resource_reads"].append(f"{row['resource']}: {row['stock']} stock, {row['net']} net/day")

    candidate_rows: list[dict[str, Any]] = []
    for group in groups.values():
        support_stock = float(group["support_stock"])
        supply_net = float(group["supply_net"])
        supply_read = "Supply stable" if supply_net >= 0 else "Supply burning down"
        if float(group["supply_stock"]) <= 0:
            supply_read = "No local Supply stock"
        if support_stock <= 0 and float(group["other_stock"]) <= 0:
            continue
        details = [
            f"Support stock: {fmt_num(support_stock)}t",
            f"Supply: {fmt_num(group['supply_stock'])}t, {fmt_num(supply_net)}t/day net",
            f"Compatible fuel: {fmt_num(group['fuel_stock'])}t",
            f"Construction resources: {fmt_num(group['construction_stock'])}t",
            f"Other stock: {fmt_num(group['other_stock'])}t",
            f"Rows summarized: {group['rows']}",
        ] + list(group["resource_reads"])[:8]
        candidate_rows.append(
            {
                "key": group["key"],
                "status": group["worst_status"],
                "status_class": status_class(str(group["worst_status"])),
                "company": group["company"],
                "place": group["place"],
                "type": group["type"],
                "support_stock_value": support_stock,
                "support_stock": f"{fmt_num(support_stock)}t",
                "supply_stock": f"{fmt_num(group['supply_stock'])}t",
                "supply_net": f"{fmt_num(supply_net)}t",
                "fuel_stock": f"{fmt_num(group['fuel_stock'])}t",
                "construction_stock": f"{fmt_num(group['construction_stock'])}t",
                "shortest_runway_days": group["shortest_runway_days"],
                "runway": runway_text(group["shortest_runway_days"]),
                "read": supply_read,
                "details": details,
            }
        )
    return sorted(
        candidate_rows,
        key=lambda row: (
            status_weight(str(row["status"])),
            row["shortest_runway_days"] if row["shortest_runway_days"] is not None else float("inf"),
            -float(row["support_stock_value"]),
            str(row["place"]),
        ),
    )[:limit]


def figure_layout(fig: go.Figure, *, height: int = 320) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 42, "r": 20, "t": 16, "b": 64},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12, "color": "#c7d7e2"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    fig.update_xaxes(gridcolor="rgba(53,216,255,0.14)", zerolinecolor="rgba(53,216,255,0.22)")
    fig.update_yaxes(gridcolor="rgba(53,216,255,0.14)", zerolinecolor="rgba(53,216,255,0.22)")
    return fig


def empty_figure(title: str, note: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=note, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    fig.update_layout(title=title)
    return figure_layout(fig)


def selected_heatmap_dimensions(
    rows: list[dict[str, Any]],
    mode: str,
    *,
    place_limit: int = 12,
    resource_limit: int = 10,
) -> tuple[list[str], list[str]]:
    place_scores: dict[str, float] = defaultdict(float)
    resource_scores: dict[str, float] = defaultdict(float)
    for row in rows:
        score = heatmap_focus_score(row, mode)
        if score <= 0:
            continue
        place_scores[str(row["place"])] += score
        resource_scores[str(row["resource"])] += score

    if not place_scores:
        for row in rows:
            place_scores[str(row["place"])] += row_activity_score(row)
            resource_scores[str(row["resource"])] += row_activity_score(row)

    places = [place for place, _ in sorted(place_scores.items(), key=lambda item: (-item[1], item[0]))[:place_limit]]
    resources = [
        resource for resource, _ in sorted(resource_scores.items(), key=lambda item: (-item[1], item[0]))[:resource_limit]
    ]
    return places, resources


def aggregate_heatmap_cells(
    rows: list[dict[str, Any]],
    places: list[str],
    resources: list[str],
) -> tuple[list[str], list[str], dict[tuple[str, str], dict[str, Any]]]:
    place_set = set(places)
    resource_set = set(resources)
    has_other_places = any(str(row["place"]) not in place_set for row in rows)
    has_other_resources = any(str(row["resource"]) not in resource_set for row in rows)
    all_places = list(places) + ([OTHER_PLACES] if has_other_places else [])
    all_resources = list(resources) + ([OTHER_RESOURCES] if has_other_resources else [])

    cells: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        place = str(row["place"]) if str(row["place"]) in place_set else OTHER_PLACES
        resource = str(row["resource"]) if str(row["resource"]) in resource_set else OTHER_RESOURCES
        cell = cells.setdefault(
            (place, resource),
            {
                "stock": 0.0,
                "intake": 0.0,
                "outtake": 0.0,
                "net": 0.0,
                "rows": 0,
                "places": set(),
                "resources": set(),
                "shortest_runway": None,
                "worst_status": "Stable",
            },
        )
        cell["stock"] = float(cell["stock"]) + float(row["stock_value"])
        cell["intake"] = float(cell["intake"]) + float(row["intake_value"])
        cell["outtake"] = float(cell["outtake"]) + float(row["outtake_value"])
        cell["net"] = float(cell["net"]) + float(row["net_value"])
        cell["rows"] = int(cell["rows"]) + 1
        cell["places"].add(str(row["place"]))
        cell["resources"].add(str(row["resource"]))
        runway = row["runway_days"]
        if runway is not None:
            current = cell["shortest_runway"]
            cell["shortest_runway"] = float(runway) if current is None else min(float(current), float(runway))
        status_rank = {"Stable": 0, "Monitor": 1, "Warning": 2, "Urgent": 3, "Critical": 4}
        if status_rank.get(str(row["status"]), 0) > status_rank.get(str(cell["worst_status"]), 0):
            cell["worst_status"] = str(row["status"])

    return all_places, all_resources, cells


def heatmap_cell_value(cell: dict[str, Any], mode: str) -> float:
    if mode == "stock":
        return log10(max(float(cell["stock"]), 0.0) + 1.0)
    return float(cell["net"])


def heatmap_color_config(mode: str) -> dict[str, Any]:
    if mode == "stock":
        return {
            "colorscale": [
                [0.0, "#082332"],
                [0.35, "#12607a"],
                [0.7, "#28b8d6"],
                [1.0, "#e8f7ff"],
            ],
            "colorbar": {"title": "Log stock", "len": 0.72, "thickness": 14, "x": 1.02},
        }
    return {
        "colorscale": [
            [0.0, "#ff5f6c"],
            [0.48, "#a55d38"],
            [0.5, "#193546"],
            [0.52, "#2a8c78"],
            [1.0, "#43e6a0"],
        ],
        "zmid": 0,
        "colorbar": {"title": "Net/day", "len": 0.72, "thickness": 14, "x": 1.02},
    }


def stock_flow_heatmap_figure(rows: list[dict[str, Any]], *, mode: str = "balance") -> go.Figure:
    if not rows:
        return empty_figure("Stock and Flow Heatmap", "No company-local resource stock or flow rows detected.")

    places, resources = selected_heatmap_dimensions(rows, mode)
    if not places or not resources:
        return empty_figure("Stock and Flow Heatmap", "No ranked production rows are available for this save scope.")
    places, resources, cells = aggregate_heatmap_cells(rows, places, resources)

    z: list[list[float | None]] = []
    customdata: list[list[list[str]]] = []
    for place in places:
        z_row: list[float | None] = []
        custom_row: list[list[str]] = []
        for resource in resources:
            cell = cells.get((place, resource))
            if cell is None:
                z_row.append(None)
                custom_row.append(["", "", "", "", "", "", "", "", ""])
                continue
            color_value = heatmap_cell_value(cell, mode)
            z_row.append(color_value)
            custom_row.append(
                [
                    f"{fmt_num(float(cell['stock']))}t",
                    f"{fmt_num(color_value)}" if mode == "stock" else "",
                    f"{fmt_num(float(cell['intake']))}t",
                    f"{fmt_num(float(cell['outtake']))}t",
                    f"{fmt_num(float(cell['net']))}t",
                    runway_text(cell["shortest_runway"]),
                    str(cell["worst_status"]),
                    str(cell["rows"]),
                    f"{len(cell['places'])} place(s), {len(cell['resources'])} resource(s)",
                ]
            )
        z.append(z_row)
        customdata.append(custom_row)
    color_config = heatmap_color_config(mode)
    mode_label = HEATMAP_MODES.get(mode, HEATMAP_MODES["balance"])

    fig = go.Figure(
        go.Heatmap(
            x=[axis_label(resource, max_len=18) for resource in resources],
            y=[axis_label(place, max_len=26) for place in places],
            z=z,
            customdata=customdata,
            **color_config,
            hovertemplate=(
                "%{y} / %{x}"
                "<br>Stock %{customdata[0]}"
                "<br>Log stock %{customdata[1]}"
                "<br>In %{customdata[2]}"
                "<br>Out %{customdata[3]}"
                "<br>Net %{customdata[4]}"
                "<br>Runway %{customdata[5]}"
                "<br>Status %{customdata[6]}"
                "<br>Rows %{customdata[7]}"
                "<br>%{customdata[8]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(xaxis_title="", yaxis_title="", annotations=[
        {
            "text": f"{mode_label}: top rows plus aggregated Other buckets"
            + ("; color uses log10(stock + 1)" if mode == "stock" else ""),
            "xref": "paper",
            "yref": "paper",
            "x": 0,
            "y": 1.08,
            "showarrow": False,
            "font": {"size": 12, "color": "#8fa7b5"},
            "xanchor": "left",
        }
    ])
    figure_layout(fig, height=560)
    fig.update_layout(margin={"l": 170, "r": 92, "t": 18, "b": 116})
    fig.update_xaxes(tickangle=-35, automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def runway_focus_figure(rows: list[dict[str, Any]]) -> go.Figure:
    risk_rows = [
        row
        for row in rows
        if row["runway_days"] is not None and isfinite(float(row["runway_days"])) and float(row["net_value"]) < 0
    ][:10]
    if not risk_rows:
        return empty_figure("Runway Focus", "No negative-net stock runway detected in this save scope.")

    labels = [chart_label(f"{row['place']} / {row['resource']}") for row in risk_rows]
    years = [float(row["runway_days"]) / 365.0 for row in risk_rows]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=years,
            marker_color=[
                {
                    "Critical": "#ff5f6c",
                    "Urgent": "#ff9d2e",
                    "Warning": "#ffd166",
                    "Monitor": "#43e6a0",
                }.get(str(row["status"]), "#35d8ff")
                for row in risk_rows
            ],
            customdata=[
                [row["stock"], row["intake"], row["outtake"], row["net"], row["runway"]]
                for row in risk_rows
            ],
            hovertemplate=(
                "%{x}<br>%{customdata[0]} stock"
                "<br>%{customdata[1]} in/day"
                "<br>%{customdata[2]} out/day"
                "<br>%{customdata[3]} net/day"
                "<br>%{customdata[4]} runway<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=2, line={"color": "#ffd166", "dash": "dot"})
    fig.add_hline(y=1, line={"color": "#ff9d2e", "dash": "dot"})
    fig.add_hline(y=0.5, line={"color": "#ff5f6c", "dash": "dot"})
    fig.update_layout(xaxis_title="", yaxis_title="Years")
    return figure_layout(fig)


def production_balance_bars_figure(rows: list[dict[str, Any]]) -> go.Figure:
    if not rows:
        return empty_figure("Production Balance Bars", "No company-local resource stock or flow rows detected.")

    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"stock": 0.0, "intake": 0.0, "outtake": 0.0, "net": 0.0, "activity": 0.0}
    )
    for row in rows:
        resource = str(row["resource"])
        totals[resource]["stock"] += float(row["stock_value"])
        totals[resource]["intake"] += float(row["intake_value"])
        totals[resource]["outtake"] += float(row["outtake_value"])
        totals[resource]["net"] += float(row["net_value"])
        totals[resource]["activity"] += row_activity_score(row)

    selected = sorted(totals.items(), key=lambda item: (-item[1]["activity"], item[0]))[:10]
    labels = [chart_label(resource) for resource, _ in selected]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Intake/day", x=labels, y=[values["intake"] for _, values in selected], marker_color="#43e6a0"))
    fig.add_trace(go.Bar(name="Outtake/day", x=labels, y=[values["outtake"] for _, values in selected], marker_color="#ff9d2e"))
    fig.add_trace(
        go.Scatter(
            name="Net/day",
            x=labels,
            y=[values["net"] for _, values in selected],
            mode="markers",
            marker={
                "size": 11,
                "color": ["#43e6a0" if values["net"] >= 0 else "#ff5f6c" for _, values in selected],
                "line": {"color": "#f7fbff", "width": 1},
            },
            customdata=[[fmt_num(values["stock"])] for _, values in selected],
            hovertemplate="%{x}<br>Net %{y:.2f}t/day<br>Total stock %{customdata[0]}t<extra></extra>",
        )
    )
    fig.add_hline(y=0, line={"color": "rgba(199,215,226,0.42)", "dash": "dot"})
    fig.update_layout(barmode="group", xaxis_title="", yaxis_title="Tons / day")
    return figure_layout(fig)


def render_kpis(kpis: list[tuple[str, str, str]]) -> None:
    with ui.row().classes("population-kpis"):
        for label, value, hint in kpis:
            with ui.element("div").classes("population-kpi"):
                ui.label(label).classes("population-kpi-label")
                ui.label(value).classes("population-kpi-value")
                ui.label(hint).classes("population-kpi-hint")


def render_sustainment_watchlist(rows: list[dict[str, Any]]) -> None:
    watch_rows = sustainment_watchlist_rows(rows)
    with ui.element("div").classes("dashboard-card dashboard-card-wide sustainment-watchlist-card"):
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Sustainment Watchlist").classes("dashboard-card-title")
                ui.label(
                    "Exact resource/location rows with negative net flow, ranked by runway. Long-runway drawdowns are informational, not urgent."
                ).classes("chart-control-summary")
            render_info_tooltip(
                "Sustainment Watchlist",
                (
                    "This board is disaggregated: no Other buckets and no hidden averaging.",
                    "Critical: under half a year of stock. Urgent: under one year. Warning: under two years.",
                    "Monitor means the row is depleting but has more than two years of stock, so it is a planning note rather than an immediate problem.",
                ),
            )
        if not watch_rows:
            ui.label("No negative-net resource runway detected in this save scope.").classes("empty-state-note")
            return

        table = ui.table(
            columns=[
                {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
                {"name": "place", "label": "Location", "field": "place", "sortable": True, "align": "left"},
                {"name": "resource", "label": "Resource", "field": "resource", "sortable": True, "align": "left"},
                {"name": "stock", "label": "Stock", "field": "stock", "sortable": True, "align": "right"},
                {"name": "net", "label": "Net/day", "field": "net", "sortable": True, "align": "right"},
                {"name": "runway", "label": "Runway", "field": "runway", "sortable": True, "align": "right"},
                {"name": "read", "label": "Planning Read", "field": "read", "sortable": True, "align": "left"},
            ],
            rows=watch_rows,
            row_key="key",
            pagination=8,
        ).classes("w-full sustainment-watchlist-table")
        table.props("flat bordered dense wrap-cells")
        table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <span :class="'readiness-chip ' + props.row.status_class">
                    {{ props.row.status }}
                    <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                    <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                        <div class="return-fuel-tooltip-title">{{ props.row.place }} / {{ props.row.resource }}</div>
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
        )


def render_candidate_site_stock_summary(rows: list[dict[str, Any]]) -> None:
    candidate_rows = candidate_site_stock_rows(rows)
    with ui.element("div").classes("dashboard-card dashboard-card-wide sustainment-watchlist-card"):
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Candidate Site Stock Summary").classes("dashboard-card-title")
                ui.label(
                    "Location-level stock evidence for future colony prep: Supply, fuel, construction resources, and shortest runway."
                ).classes("chart-control-summary")
            render_info_tooltip(
                "Candidate Site Stock Summary",
                (
                    "This is evidence, not a demand model.",
                    "Rows group company-local stock and flow by location so a future Prep Watchlist can explain what is already present.",
                    "Support stock includes Supply, compatible fuel, and common construction resources.",
                ),
            )
        if not candidate_rows:
            ui.label("No local stock evidence was detected for candidate site summaries in this save scope.").classes(
                "empty-state-note"
            )
            return

        table = ui.table(
            columns=[
                {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
                {"name": "place", "label": "Location", "field": "place", "sortable": True, "align": "left"},
                {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
                {"name": "support_stock", "label": "Support Stock", "field": "support_stock", "sortable": True, "align": "right"},
                {"name": "supply_stock", "label": "Supply", "field": "supply_stock", "sortable": True, "align": "right"},
                {"name": "supply_net", "label": "Supply Net/day", "field": "supply_net", "sortable": True, "align": "right"},
                {"name": "fuel_stock", "label": "Fuel", "field": "fuel_stock", "sortable": True, "align": "right"},
                {"name": "construction_stock", "label": "Construction", "field": "construction_stock", "sortable": True, "align": "right"},
                {"name": "runway", "label": "Shortest Runway", "field": "runway", "sortable": True, "align": "right"},
                {"name": "read", "label": "Planning Read", "field": "read", "sortable": True, "align": "left"},
            ],
            rows=candidate_rows,
            row_key="key",
            pagination=8,
        ).classes("w-full sustainment-watchlist-table")
        table.props("flat bordered dense wrap-cells")
        table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <span :class="'readiness-chip ' + props.row.status_class">
                    {{ props.row.status }}
                    <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                    <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                        <div class="return-fuel-tooltip-title">{{ props.row.place }}</div>
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
        )


def render_chart_card(title: str, fig: go.Figure, *, wide: bool = False) -> None:
    fig.update_layout(title=None)
    classes = "dashboard-card viz-card viz-card-wide" if wide else "dashboard-card viz-card"
    with ui.element("div").classes(classes):
        ui.label(title).classes("dashboard-card-title viz-card-title")
        ui.plotly(fig).classes("viz-plot w-full")


def render_heatmap_section(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card viz-card viz-card-wide"):
        with ui.row().classes("dashboard-title-row"):
            ui.label("Stock and Flow Heatmap").classes("dashboard-card-title viz-card-title")
            with ui.row().classes("mode-control-row"):
                mode_select = ui.select(
                    options=HEATMAP_MODES,
                    value="balance",
                    label="Mode",
                ).classes("chart-control-small")
                help_container = ui.element("span").classes("mode-info")
        summary = ui.label("").classes("chart-control-summary heatmap-mode-summary")
        plot_container = ui.column().classes("w-full heatmap-plot-container")

        def render_mode_help() -> None:
            mode = str(mode_select.value)
            content = HEATMAP_MODE_HELP.get(mode, HEATMAP_MODE_HELP["balance"])
            help_container.clear()
            with help_container:
                render_info_tooltip(content.title, content.lines)
            summary.text = (
                f"{HEATMAP_MODES.get(mode, HEATMAP_MODES['balance'])}: "
                f"{HEATMAP_MODE_SUMMARIES.get(mode, HEATMAP_MODE_SUMMARIES['balance'])} "
                "Top rows/resources remain explicit; the rest is included in Other buckets."
            )

        def render_selected_mode() -> None:
            render_mode_help()
            plot_container.clear()
            with plot_container:
                ui.plotly(stock_flow_heatmap_figure(rows, mode=str(mode_select.value))).classes(
                    "viz-plot heatmap-plot w-full"
                )

        mode_select.on_value_change(lambda _: render_selected_mode())
        render_selected_mode()


def render_production_table(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Stock / Flow Drill-Down").classes("dashboard-card-title")
        table = ui.table(
            columns=production_columns,
            rows=rows,
            row_key="key",
            pagination=12,
        ).classes("w-full")
        table.props("flat bordered dense wrap-cells")
        table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <span :class="'readiness-chip ' + props.row.status_class">
                    {{ props.row.status }}
                    <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                    <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                        <div class="return-fuel-tooltip-title">{{ props.row.place }} / {{ props.row.resource }}</div>
                        <div
                            v-for="line in props.row.status_details"
                            :key="line"
                            class="return-fuel-tooltip-line"
                        >
                            {{ line }}
                        </div>
                    </q-tooltip>
                </span>
            </q-td>
            """,
        )


def render_production_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    rows = production_rows(analysis)
    with container:
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Production").classes("text-xl font-semibold")
                ui.label("Company-local stock, intake, outtake, net flow, and depletion runway from save data.").classes(
                    "text-sm text-slate-600"
                )
        render_kpis(production_kpis(rows))
        render_sustainment_watchlist(rows)
        render_candidate_site_stock_summary(rows)
        render_heatmap_section(rows)
        with ui.row().classes("dashboard-grid"):
            render_chart_card("Runway Focus", runway_focus_figure(rows))
            render_chart_card("Production Balance Bars", production_balance_bars_figure(rows))
        render_production_table(rows)
