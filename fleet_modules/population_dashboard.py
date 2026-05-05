from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlencode

import plotly.graph_objects as go
from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import fmt_num
from fleet_core.population_facts import runway_label


STATUS_RANK = {"Safe": 0, "Monitor": 1, "Warning": 2, "Urgent": 3, "Critical": 4}
ATTENTION_STATUSES = {"Warning", "Urgent", "Critical"}
STATUS_COLORS = {
    "Safe": "#2f855a",
    "Monitor": "#2b6cb0",
    "Warning": "#d9822b",
    "Urgent": "#c05621",
    "Critical": "#c53030",
    "Unknown": "#64748b",
}
READINESS_KPI_ORDER = ("Safe", "Monitor", "Warning", "Urgent", "Critical")
READINESS_KPI_ABBR = {
    "Safe": "S",
    "Monitor": "M",
    "Warning": "W",
    "Urgent": "U",
    "Critical": "C",
}


PLACE_FOCUS_OPTIONS = {
    "Risk first": "risk",
    "Shortest runway": "runway",
    "Largest population": "population",
    "Housing pressure": "housing",
    "Inbound people": "inbound",
}
PLACE_STATUS_FILTER_OPTIONS = {
    "All statuses": "all",
    "Monitor + concerns": "attention",
    "Actionable concerns": "concerns",
    "Safe only": "safe",
}
PLACE_INBOUND_FILTER_OPTIONS = {
    "All inbound states": "all",
    "Has inbound people": "has_inbound",
    "No inbound people": "no_inbound",
}
PLACE_HOUSING_FILTER_OPTIONS = {
    "All housing states": "all",
    "Housing gap": "gap",
    "Free housing": "free",
    "Queued housing": "queued",
}
PLACE_RUNWAY_FILTER_OPTIONS = {
    "All runway states": "all",
    "Burning down": "burning",
    "Under 2 years": "under_2y",
    "Under 1 year": "under_1y",
    "Under 6 months": "under_6m",
    "Stable / net positive": "stable",
}
PLACE_POPULATION_FILTER_OPTIONS = {
    "All population states": "all",
    "Has population": "populated",
    "No local population": "empty",
    "At or above ready housing": "full",
}


def movement_link(**params: object) -> str:
    clean = {key: str(value) for key, value in params.items() if value not in {None, ""}}
    query = urlencode(clean)
    return f"/population/movement?{query}" if query else "/population/movement"


readiness_columns = [
    {"name": "destination", "label": "Destination", "field": "destination", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "inbound_people", "label": "Inbound", "field": "inbound_people", "sortable": True, "align": "right"},
    {"name": "current_population_label", "label": "Current Pop", "field": "current_population_label", "sortable": True, "align": "right"},
    {"name": "completed_housing_label", "label": "Ready Housing", "field": "completed_housing_label", "sortable": True, "align": "right"},
    {"name": "queued_housing_label", "label": "Queued Housing", "field": "queued_housing_label", "sortable": True, "align": "right"},
    {"name": "arriving_housing_label", "label": "Arriving Habitat", "field": "arriving_housing_label", "sortable": True, "align": "right"},
    {"name": "housing_gap_label", "label": "Housing Gap", "field": "housing_gap_label", "sortable": True, "align": "right"},
    {"name": "supply_stock_label", "label": "Supply Stock", "field": "supply_stock_label", "sortable": True, "align": "right"},
    {"name": "supply_net_label", "label": "Supply Net/day", "field": "supply_net_label", "sortable": True, "align": "right"},
    {"name": "runway", "label": "Runway", "field": "runway", "sortable": True, "align": "right"},
    {"name": "next_arrival", "label": "Next Arrival", "field": "next_arrival", "sortable": True, "align": "left"},
    {"name": "drilldown", "label": "Drill-Down", "field": "drilldown", "sortable": False, "align": "left"},
]


place_columns = [
    {"name": "place", "label": "Colony / Station", "field": "place", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "status", "label": "Sustainment", "field": "status", "sortable": True, "align": "left"},
    {"name": "population", "label": "Population", "field": "population", "sortable": True, "align": "right"},
    {"name": "housing", "label": "Housing", "field": "housing", "sortable": True, "align": "right"},
    {"name": "supply", "label": "Supply", "field": "supply", "sortable": True, "align": "right"},
    {"name": "runway", "label": "Runway", "field": "runway", "sortable": True, "align": "right"},
    {"name": "inbound_people", "label": "Inbound", "field": "inbound_people", "sortable": True, "align": "right"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
]


def chart_label(value: object, *, max_length: int = 22) -> str:
    text = str(value)
    text = text.replace("Low Orbit of ", "LO ")
    if len(text) <= max_length:
        return text
    if " (" in text and text.endswith(")"):
        name, suffix = text.rsplit(" (", 1)
        room = max(max_length - len(suffix) - 6, 8)
        return f"{name[:room].rstrip()}...<br>({suffix}"
    return f"{text[: max_length - 3].rstrip()}..."


def figure_layout(fig: go.Figure, *, height: int = 320) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 58, "r": 20, "t": 58, "b": 82},
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12, "color": "#d7f7ff"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title={"font": {"color": "#f7fbff", "size": 15}, "x": 0.0, "xanchor": "left"},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 11},
        },
        hoverlabel={"bgcolor": "#06131c", "bordercolor": "#35d8ff", "font": {"color": "#e8f7ff"}},
    )
    fig.update_xaxes(
        automargin=True,
        color="#8fa7b5",
        gridcolor="rgba(86,179,214,0.16)",
        zerolinecolor="rgba(86,179,214,0.22)",
        tickfont={"size": 10},
        title_standoff=12,
    )
    fig.update_yaxes(
        automargin=True,
        color="#8fa7b5",
        gridcolor="rgba(86,179,214,0.16)",
        zerolinecolor="rgba(86,179,214,0.22)",
        tickfont={"size": 10},
        title_standoff=12,
    )
    return fig


def empty_figure(title: str, note: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=note,
        x=0.5,
        y=0.5,
        showarrow=False,
        xref="paper",
        yref="paper",
        font={"size": 13, "color": "#64706d"},
    )
    fig.update_layout(title=title)
    return figure_layout(fig)


def population_metrics_by_destination(
    analysis: SaveAnalysis,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in analysis.population_destination_metrics:
        projected_net = metric.projected_supply_net_per_day
        supply_net_label = f"{fmt_num(projected_net)}t/day"
        if projected_net > 0:
            supply_net_label = f"+{supply_net_label}"
        rows.append(
            {
                "key": metric.destination_key,
                "company": metric.company,
                "destination_id": metric.destination_id,
                "destination": metric.destination,
                "status": metric.status,
                "status_class": f"readiness-{metric.status.lower()}",
                "message": metric.message,
                "details": list(metric.details),
                "inbound_people": metric.inbound_people,
                "current_population": metric.current_population,
                "current_population_label": fmt_num(metric.current_population),
                "projected_population": metric.projected_population,
                "population": f"{fmt_num(metric.current_population)} -> {fmt_num(metric.projected_population)}",
                "completed_housing": metric.completed_housing,
                "completed_housing_label": fmt_num(metric.completed_housing),
                "queued_housing": metric.queued_housing,
                "queued_housing_label": fmt_num(metric.queued_housing),
                "arriving_housing": metric.arriving_housing,
                "arriving_housing_label": fmt_num(metric.arriving_housing),
                "housing_gap": metric.housing_gap,
                "housing_gap_label": fmt_num(metric.housing_gap),
                "housing": (
                    f"{fmt_num(metric.completed_housing)} ready + {fmt_num(metric.queued_housing)} queued + "
                    f"{fmt_num(metric.arriving_housing)} carried; gap {fmt_num(metric.housing_gap)}"
                ),
                "supply_stock": metric.supply_stock,
                "supply_stock_label": f"{fmt_num(metric.supply_stock)}t",
                "supply_intake_per_day": metric.supply_intake_per_day,
                "projected_supply_outtake_per_day": metric.projected_supply_outtake_per_day,
                "projected_supply_net_per_day": metric.projected_supply_net_per_day,
                "supply_net_label": supply_net_label,
                "supply": (
                    f"{fmt_num(metric.supply_stock)}t; "
                    f"{fmt_num(metric.supply_intake_per_day)} in / {fmt_num(metric.projected_supply_outtake_per_day)} out per day"
                ),
                "runway_days": metric.supply_runway_days,
                "runway": runway_label(metric.supply_runway_days, metric.projected_supply_net_per_day),
                "next_arrival_dt": metric.next_arrival_dt,
                "next_arrival": metric.next_arrival,
                "drilldown_url": movement_link(destination=metric.destination),
            }
        )
    return rows


def population_flights(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    return [
        {
            "mission_key": metric.mission_key,
            "mission_id": metric.mission_id,
            "company": metric.company,
            "status": metric.status,
            "craft": ", ".join(metric.craft_names),
            "people": metric.people,
            "empty_seats": metric.empty_seats,
            "loaded_modules": metric.loaded_modules,
            "empty_modules": metric.empty_modules,
            "life_support": metric.life_support,
            "route": metric.route,
            "source": metric.source,
            "destination": metric.destination,
            "departure_dt": metric.departure_dt,
            "arrival_dt": metric.arrival_dt,
            "departure": metric.departure,
            "arrival": metric.arrival,
            "duration_days": metric.duration_days,
            "status_label": metric.readiness_status,
            "readiness_message": metric.readiness_message,
            "readiness_details": list(metric.readiness_details),
            "drilldown_url": movement_link(mission=metric.mission_key),
        }
        for metric in analysis.population_flight_metrics
    ]


def population_kpis(destination_rows: list[dict[str, Any]], flight_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    people = sum(int(row["people"]) for row in flight_rows)
    empty_modules = sum(int(row["empty_modules"]) for row in flight_rows)
    empty_seats = sum(int(row["empty_seats"]) for row in flight_rows)
    next_flight = next((row for row in flight_rows if row["people"] > 0 and row["arrival"]), None)
    next_arrival = str(next_flight["arrival"]) if next_flight else ""
    readiness_counts = defaultdict(int)
    for row in destination_rows:
        readiness_counts[str(row["status"])] += 1
    readiness_value = " ".join(
        f"{READINESS_KPI_ABBR[status]}:{readiness_counts[status]}" for status in READINESS_KPI_ORDER
    )
    readiness_hint = (
        ", ".join(f"{status}: {readiness_counts[status]}" for status in READINESS_KPI_ORDER)
        if destination_rows
        else "no population destinations detected"
    )
    return [
        {
            "label": "People Moving",
            "value": str(people),
            "hint": "loaded humans on active/planned flights",
            "url": movement_link(state="loaded"),
        },
        {
            "label": "Empty Holds",
            "value": str(empty_modules),
            "hint": "crew modules moving without passengers",
            "url": movement_link(state="empty"),
        },
        {
            "label": "Empty Seats",
            "value": str(empty_seats),
            "hint": "unused detected transport seats",
            "url": movement_link(state="empty_seats"),
        },
        {
            "label": "Next Pop Arrival",
            "value": next_arrival or "-",
            "hint": "earliest loaded population flight",
            "url": movement_link(mission=next_flight["mission_key"]) if next_flight else movement_link(state="loaded"),
        },
        {
            "label": "Readiness Mix",
            "value": readiness_value,
            "hint": readiness_hint,
            "url": movement_link(readiness="attention"),
        },
        {
            "label": "LS Concerns",
            "value": "-",
            "hint": "life-support exhaustion count awaits formula validation",
            "url": movement_link(),
        },
    ]


def population_places(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    return [
        {
            "key": metric.place_key,
            "company": metric.company,
            "object_id": metric.object_id,
            "place": metric.place,
            "type": metric.object_type,
            "relationship": metric.relationship,
            "status": metric.status,
            "status_class": f"readiness-{metric.status.lower()}",
            "message": metric.message,
            "status_details": list(metric.details),
            "current_population": metric.current_population,
            "population": fmt_num(metric.current_population),
            "completed_housing": metric.completed_housing,
            "queued_housing": metric.queued_housing,
            "free_housing": metric.free_housing,
            "housing_gap": metric.housing_gap,
            "housing": f"{fmt_num(metric.completed_housing)} ready + {fmt_num(metric.queued_housing)} queued; free {fmt_num(metric.free_housing)}",
            "supply_stock": metric.supply_stock,
            "supply_intake_per_day": metric.supply_intake_per_day,
            "supply_outtake_per_day": metric.supply_outtake_per_day,
            "supply_net_per_day": metric.supply_net_per_day,
            "supply_modifier": metric.supply_modifier,
            "supply_modifier_basis": metric.supply_modifier_basis,
            "supply": f"{fmt_num(metric.supply_stock)}t; {fmt_num(metric.supply_intake_per_day)} in / {fmt_num(metric.supply_outtake_per_day)} out per day",
            "runway_days": metric.supply_runway_days,
            "runway": runway_label(metric.supply_runway_days, metric.supply_net_per_day),
            "inbound_people": metric.inbound_people,
            "place_count": 1,
            "is_other": False,
        }
        for metric in analysis.population_place_metrics
    ]


def place_kpis(place_rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    population = sum(float(row["current_population"]) for row in place_rows)
    housing = sum(float(row["completed_housing"]) for row in place_rows)
    queued = sum(float(row["queued_housing"]) for row in place_rows)
    inbound = sum(int(row["inbound_people"]) for row in place_rows)
    concerns = sum(1 for row in place_rows if row["status"] in ATTENTION_STATUSES)
    monitor = sum(1 for row in place_rows if row["status"] == "Monitor")
    stable = sum(1 for row in place_rows if row["supply_net_per_day"] >= 0)
    return [
        ("Population", fmt_num(population), "humans detected in company-local stock"),
        ("Places", str(len(place_rows)), "colonies/stations with population, housing, or inbound people"),
        ("Housing", fmt_num(housing), "detected completed habitat capacity"),
        ("Queued Housing", fmt_num(queued), "habitat capacity still in build queue"),
        ("Inbound", str(inbound), "people currently routed to these places"),
        ("Concerns", str(concerns), f"{monitor} monitor-only; {stable} places have non-negative Supply flow"),
    ]


def place_runway_sort_value(row: dict[str, Any]) -> float:
    if row["supply_net_per_day"] >= 0:
        return float("inf")
    if row["runway_days"] is None:
        return float("inf")
    return float(row["runway_days"])


def place_risk_sort_key(row: dict[str, Any]) -> tuple[object, ...]:
    return (
        -STATUS_RANK.get(str(row["status"]), 0),
        place_runway_sort_value(row),
        -float(row["housing_gap"]),
        -int(row["inbound_people"]),
        -float(row["current_population"]),
        str(row["place"]),
    )


def sort_place_rows(place_rows: list[dict[str, Any]], *, focus: str) -> list[dict[str, Any]]:
    rows = list(place_rows)
    if focus == "runway":
        rows.sort(key=lambda row: (place_runway_sort_value(row), place_risk_sort_key(row)))
    elif focus == "population":
        rows.sort(key=lambda row: (-float(row["current_population"]), place_risk_sort_key(row)))
    elif focus == "housing":
        rows.sort(key=lambda row: (-float(row["housing_gap"]), place_risk_sort_key(row)))
    elif focus == "inbound":
        rows.sort(key=lambda row: (-int(row["inbound_people"]), place_risk_sort_key(row)))
    else:
        rows.sort(key=place_risk_sort_key)
    return rows


def finite_place_runway_years(row: dict[str, Any]) -> float | None:
    if row["supply_net_per_day"] >= 0:
        return None
    runway_days = row.get("runway_days")
    if runway_days is None:
        return None
    return float(runway_days) / 365.0


def place_row_matches_filters(row: dict[str, Any], filters: dict[str, str]) -> bool:
    status_filter = filters.get("status", "all")
    status = str(row["status"])
    if status_filter == "concerns" and status not in ATTENTION_STATUSES:
        return False
    if status_filter == "attention" and status not in ATTENTION_STATUSES | {"Monitor"}:
        return False
    if status_filter == "safe" and status != "Safe":
        return False

    company_filter = filters.get("company", "All companies")
    if company_filter != "All companies" and str(row["company"]) != company_filter:
        return False

    type_filter = filters.get("type", "All types")
    if type_filter != "All types" and str(row["type"]) != type_filter:
        return False

    inbound_filter = filters.get("inbound", "all")
    inbound = int(row["inbound_people"])
    if inbound_filter == "has_inbound" and inbound <= 0:
        return False
    if inbound_filter == "no_inbound" and inbound > 0:
        return False

    housing_filter = filters.get("housing", "all")
    if housing_filter == "gap" and float(row["housing_gap"]) <= 0:
        return False
    if housing_filter == "free" and float(row["free_housing"]) <= 0:
        return False
    if housing_filter == "queued" and float(row["queued_housing"]) <= 0:
        return False

    runway_filter = filters.get("runway", "all")
    runway_years = finite_place_runway_years(row)
    if runway_filter == "burning" and runway_years is None:
        return False
    if runway_filter == "under_2y" and (runway_years is None or runway_years >= 2):
        return False
    if runway_filter == "under_1y" and (runway_years is None or runway_years >= 1):
        return False
    if runway_filter == "under_6m" and (runway_years is None or runway_years >= 0.5):
        return False
    if runway_filter == "stable" and float(row["supply_net_per_day"]) < 0:
        return False

    population_filter = filters.get("population", "all")
    population = float(row["current_population"])
    if population_filter == "populated" and population <= 0:
        return False
    if population_filter == "empty" and population > 0:
        return False
    if population_filter == "full" and (population <= 0 or population < float(row["completed_housing"])):
        return False
    return True


def filter_place_rows(place_rows: list[dict[str, Any]], filters: dict[str, str]) -> list[dict[str, Any]]:
    return [row for row in place_rows if place_row_matches_filters(row, filters)]


def aggregate_other_places(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    population = sum(float(row["current_population"]) for row in rows)
    completed_housing = sum(float(row["completed_housing"]) for row in rows)
    queued_housing = sum(float(row["queued_housing"]) for row in rows)
    free_housing = sum(float(row["free_housing"]) for row in rows)
    housing_gap = sum(max(float(row["housing_gap"]), 0.0) for row in rows)
    supply_stock = sum(float(row["supply_stock"]) for row in rows)
    intake = sum(float(row["supply_intake_per_day"]) for row in rows)
    outtake = sum(float(row["supply_outtake_per_day"]) for row in rows)
    net = intake - outtake
    runway_days = supply_stock / abs(net) if net < 0 and supply_stock > 0 else None
    status = max((str(row["status"]) for row in rows), key=lambda value: STATUS_RANK.get(value, 0))
    place_count = sum(int(row.get("place_count") or 1) for row in rows)
    return {
        "key": "other-places",
        "company": "Mixed",
        "object_id": "",
        "place": "Other places",
        "type": "Mixed",
        "relationship": "Mixed",
        "status": status,
        "status_class": f"readiness-{status.lower()}",
        "message": f"{place_count} lower-ranked places aggregated into this chart bucket.",
        "status_details": [
            f"Aggregated places: {place_count}",
            f"Supply stock: {fmt_num(supply_stock)}t",
            f"Supply flow: {fmt_num(intake)} in / {fmt_num(outtake)} out per day",
            f"Housing: {fmt_num(completed_housing)} ready + {fmt_num(queued_housing)} queued",
        ],
        "current_population": population,
        "population": fmt_num(population),
        "completed_housing": completed_housing,
        "queued_housing": queued_housing,
        "free_housing": free_housing,
        "housing_gap": housing_gap,
        "housing": f"{fmt_num(completed_housing)} ready + {fmt_num(queued_housing)} queued; free {fmt_num(free_housing)}",
        "supply_stock": supply_stock,
        "supply_intake_per_day": intake,
        "supply_outtake_per_day": outtake,
        "supply_net_per_day": net,
        "supply_modifier": None,
        "supply_modifier_basis": "aggregate",
        "supply": f"{fmt_num(supply_stock)}t; {fmt_num(intake)} in / {fmt_num(outtake)} out per day",
        "runway_days": runway_days,
        "runway": runway_label(runway_days, net),
        "inbound_people": sum(int(row["inbound_people"]) for row in rows),
        "place_count": place_count,
        "is_other": True,
    }


def chart_place_rows(place_rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected = place_rows[:limit]
    other = aggregate_other_places(place_rows[limit:])
    return selected + ([other] if other else [])


def selected_place_chart_rows(
    place_rows: list[dict[str, Any]],
    *,
    focus: str,
    limit: int,
    include_safe: bool,
) -> list[dict[str, Any]]:
    rows = list(place_rows if include_safe else [row for row in place_rows if row["status"] in ATTENTION_STATUSES])
    return chart_place_rows(sort_place_rows(rows, focus=focus), limit=limit)


def finite_runway_years(row: dict[str, Any]) -> float | None:
    if row["projected_supply_net_per_day"] >= 0:
        return None
    runway_days = row.get("runway_days")
    if runway_days is None:
        return None
    return float(runway_days) / 365.0


def supply_burndown_figure(destination_rows: list[dict[str, Any]]) -> go.Figure:
    rows = [row for row in destination_rows if row["inbound_people"] > 0]
    rows.sort(
        key=lambda row: (
            finite_runway_years(row) is None,
            finite_runway_years(row) if finite_runway_years(row) is not None else float("inf"),
            -STATUS_RANK.get(str(row["status"]), 0),
            str(row["destination"]),
        )
    )
    rows = rows[:6]
    if not rows:
        return empty_figure("Supply Runway", "No inbound population destinations in this save.")
    fig = go.Figure()
    horizon = max(730, int(max((row["runway_days"] or 0 for row in rows), default=0)) + 30)
    horizon = min(horizon, 3650)
    x = [day for day in range(0, horizon + 1, 30)]
    for row in rows:
        net = float(row["projected_supply_net_per_day"])
        stock = float(row["supply_stock"])
        y = [max(stock + net * day, 0.0) for day in x]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name=f"{row['destination']} ({row['status']})",
                line={"color": STATUS_COLORS.get(str(row["status"]), "#64748b"), "width": 3},
                customdata=[[row["runway"], row["projected_supply_net_per_day"], row["inbound_people"]] for _ in x],
                hovertemplate=(
                    "%{fullData.name}<br>Day %{x}<br>Supply %{y:.2f}t"
                    "<br>Runway %{customdata[0]}"
                    "<br>Net %{customdata[1]:.4f}t/day"
                    "<br>Inbound people %{customdata[2]}<extra></extra>"
                ),
            )
        )
        if row["runway_days"] is not None and net < 0:
            fig.add_trace(
                go.Scatter(
                    x=[float(row["runway_days"])],
                    y=[0],
                    mode="markers",
                    name=f"{row['destination']} stockout",
                    marker={
                        "symbol": "x",
                        "size": 10,
                        "color": STATUS_COLORS.get(str(row["status"]), "#c53030"),
                        "line": {"width": 2},
                    },
                    showlegend=False,
                    hovertemplate=f"{row['destination']} stockout<br>Day {float(row['runway_days']):.0f}<extra></extra>",
                )
            )
    fig.add_hline(y=0, line={"color": "#c53030", "dash": "dot"})
    for days, label, color in (
        (365 * 0.5, "Critical 0.5y", "#c53030"),
        (365, "Urgent 1y", "#c05621"),
        (365 * 2, "Warning 2y", "#d9822b"),
    ):
        if days <= horizon:
            fig.add_vline(
                x=days,
                line={"color": color, "dash": "dot", "width": 1},
                annotation_text=label,
                annotation_position="top",
                annotation_font={"size": 10, "color": color},
            )
    fig.update_layout(
        title="Supply Runway Burndown",
        xaxis_title="Days From Save",
        yaxis_title="Projected Supply Stock (t)",
    )
    return figure_layout(fig)


def housing_stack_figure(destination_rows: list[dict[str, Any]]) -> go.Figure:
    rows = [row for row in destination_rows if row["inbound_people"] > 0]
    rows.sort(
        key=lambda row: (
            -float(row["housing_gap"]),
            -STATUS_RANK.get(str(row["status"]), 0),
            str(row["destination"]),
        )
    )
    rows = rows[:8]
    if not rows:
        return empty_figure("Housing Readiness", "No inbound population destinations in this save.")
    labels = [str(row["destination"]) for row in rows]
    fig = go.Figure()
    fig.add_trace(
        go.Waterfall(
            name="Housing path",
            orientation="v",
            x=labels,
            measure=["relative"] * len(rows),
            y=[
                float(row["completed_housing"])
                + float(row["queued_housing"])
                + float(row["arriving_housing"])
                - float(row["projected_population"])
                for row in rows
            ],
            customdata=[
                [
                    row["completed_housing"],
                    row["queued_housing"],
                    row["arriving_housing"],
                    row["projected_population"],
                    row["housing_gap"],
                    row["inbound_people"],
                ]
                for row in rows
            ],
            connector={"line": {"color": "rgba(143, 167, 181, 0.28)"}},
            decreasing={"marker": {"color": "#ff5f6c"}},
            increasing={"marker": {"color": "#43e6a0"}},
            totals={"marker": {"color": "#35d8ff"}},
            hovertemplate=(
                "%{x}<br>Housing margin %{y:.0f}"
                "<br>Ready %{customdata[0]:.0f}"
                "<br>Queued %{customdata[1]:.0f}"
                "<br>Carried habitat %{customdata[2]:.0f}"
                "<br>Projected population %{customdata[3]:.0f}"
                "<br>Gap %{customdata[4]:.0f}"
                "<br>Inbound people %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=0, line={"color": "#f7fbff", "dash": "dot"})
    fig.update_layout(
        title="Housing Margin Waterfall",
        xaxis_title="",
        yaxis_title="Housing surplus / deficit",
        showlegend=False,
    )
    return figure_layout(fig)


def population_flow_sankey(flight_rows: list[dict[str, Any]]) -> go.Figure:
    loaded = [row for row in flight_rows if row["people"] > 0]
    if not loaded:
        return empty_figure("Population Flow", "No loaded population flights in this save.")
    labels: list[str] = []
    index: dict[str, int] = {}

    def label_index(label: str) -> int:
        if label not in index:
            index[label] = len(labels)
            labels.append(label)
        return index[label]

    links: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in loaded:
        source = row["source"] or "Unknown origin"
        destination = row["destination"] or "Unknown destination"
        key = (source, destination, str(row["status_label"]))
        link = links.setdefault(
            key,
            {
                "people": 0,
                "mission_keys": [],
                "destination": destination,
                "url": movement_link(destination=destination),
            },
        )
        link["people"] = int(link["people"]) + int(row["people"])
        link["mission_keys"].append(row["mission_key"])

    fig = go.Figure(
        data=[
            go.Sankey(
                node={"label": labels, "pad": 18, "thickness": 16, "color": "#d8ded8"},
                link={
                    "source": [label_index(source) for source, _, _ in links],
                    "target": [label_index(destination) for _, destination, _ in links],
                    "value": [link["people"] for link in links.values()],
                    "color": [STATUS_COLORS.get(status, "#64748b") for _, _, status in links],
                    "customdata": [
                        [status, link["destination"], ", ".join(str(key) for key in link["mission_keys"]), link["url"]]
                        for (_, _, status), link in links.items()
                    ],
                    "hovertemplate": (
                        "%{source.label} -> %{target.label}<br>%{value} people"
                        "<br>Status %{customdata[0]}"
                        "<br>Click: People Transit filtered to %{customdata[1]}<extra></extra>"
                    ),
                },
            )
        ]
    )
    fig.update_layout(title="Population Flow")
    return figure_layout(fig)


def arrival_timeline_figure(flight_rows: list[dict[str, Any]]) -> go.Figure:
    loaded = [row for row in flight_rows if row["people"] > 0 and row["arrival_dt"] is not None]
    if not loaded:
        return empty_figure("Population Arrival Timeline", "No dated loaded population flights in this save.")
    fig = go.Figure()
    for index, row in enumerate(loaded[:12]):
        y = f"{row['mission_id']} {row['craft']}".strip()
        departure = row["departure_dt"] or row["arrival_dt"]
        arrival = row["arrival_dt"]
        color = STATUS_COLORS.get(str(row["status_label"]), "#64748b")
        fig.add_trace(
            go.Scatter(
                x=[departure, arrival],
                y=[y, y],
                mode="lines+markers",
                line={"color": color, "width": 5},
                marker={"size": [7, 10], "color": color},
                name=str(row["status_label"]) if index == 0 else None,
                showlegend=False,
                customdata=[[row["mission_key"], row["destination"], row["drilldown_url"]] for _ in range(2)],
                hovertemplate=(
                    f"Mission {row['mission_id']}<br>{row['route']}<br>"
                    f"{row['people']} people<br>{row['status_label']}<br>"
                    f"Click: People Transit mission {row['mission_id']}<extra></extra>"
                ),
            )
        )
    fig.update_layout(title="Population Arrival Timeline", xaxis_title="", yaxis_title="")
    return figure_layout(fig, height=360)


def place_supply_balance_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = place_rows if limit is None else place_rows[:limit]
    if not rows:
        return empty_figure("Place Supply Balance", "No populated places or habitats detected in this save.")
    labels = [chart_label(row["place"], max_length=18) for row in rows]
    customdata = [
        [
            row["place"],
            row["status"],
            row["place_count"],
            row["supply_stock"],
            row["supply_net_per_day"],
            row["runway"],
        ]
        for row in rows
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Supply intake/day",
            x=labels,
            y=[row["supply_intake_per_day"] for row in rows],
            marker_color="#43e6a0",
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{y:.4f}t/day intake"
                "<br>Status %{customdata[1]}"
                "<br>Places %{customdata[2]}"
                "<br>Stock %{customdata[3]:.2f}t"
                "<br>Net %{customdata[4]:.4f}t/day"
                "<br>Runway %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Supply outtake/day",
            x=labels,
            y=[row["supply_outtake_per_day"] for row in rows],
            marker_color="#ff9d2e",
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{y:.4f}t/day outtake"
                "<br>Status %{customdata[1]}"
                "<br>Places %{customdata[2]}"
                "<br>Stock %{customdata[3]:.2f}t"
                "<br>Net %{customdata[4]:.4f}t/day"
                "<br>Runway %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Net/day",
            x=labels,
            y=[row["supply_net_per_day"] for row in rows],
            mode="markers",
            marker={"size": 10, "color": [STATUS_COLORS.get(str(row["status"]), "#64748b") for row in rows]},
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{y:.4f}t/day net"
                "<br>Status %{customdata[1]}"
                "<br>Places %{customdata[2]}"
                "<br>Stock %{customdata[3]:.2f}t"
                "<br>Runway %{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(title="Place Supply Balance", barmode="group", xaxis_title="", yaxis_title="Supply tons / day")
    fig.update_xaxes(tickangle=-30)
    return figure_layout(fig)


def place_housing_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = [row for row in place_rows if row["current_population"] > 0 or row["completed_housing"] > 0 or row["queued_housing"] > 0]
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return empty_figure("Place Housing", "No local population or habitat capacity detected in this save.")
    labels = [chart_label(row["place"], max_length=18) for row in rows]
    customdata = [
        [
            row["place"],
            row["status"],
            row["place_count"],
            row["current_population"],
            row["housing_gap"],
            row["free_housing"],
        ]
        for row in rows
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Ready housing",
            x=labels,
            y=[row["completed_housing"] for row in rows],
            marker_color="#35d8ff",
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>Ready housing %{y:.0f}"
                "<br>Population %{customdata[3]:.0f}"
                "<br>Housing gap %{customdata[4]:.0f}"
                "<br>Free housing %{customdata[5]:.0f}"
                "<br>Status %{customdata[1]}<br>Places %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Queued housing",
            x=labels,
            y=[row["queued_housing"] for row in rows],
            marker_color="#ff9d2e",
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>Queued housing %{y:.0f}"
                "<br>Population %{customdata[3]:.0f}"
                "<br>Housing gap %{customdata[4]:.0f}"
                "<br>Free housing %{customdata[5]:.0f}"
                "<br>Status %{customdata[1]}<br>Places %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Current population",
            x=labels,
            y=[row["current_population"] for row in rows],
            mode="markers",
            marker={"symbol": "line-ew", "size": 18, "color": "#f7fbff", "line": {"width": 3}},
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>Current population %{y:.0f}"
                "<br>Housing gap %{customdata[4]:.0f}"
                "<br>Free housing %{customdata[5]:.0f}"
                "<br>Status %{customdata[1]}<br>Places %{customdata[2]}<extra></extra>"
            ),
        )
    )
    fig.update_layout(title="Place Housing / Occupancy", barmode="stack", xaxis_title="", yaxis_title="People / Capacity")
    fig.update_xaxes(tickangle=-30)
    return figure_layout(fig)


def place_runway_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = [row for row in place_rows if row["supply_net_per_day"] < 0]
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return empty_figure("Current Supply Runway", "All detected populated places have non-negative Supply flow or no Supply burn.")
    labels = [chart_label(row["place"], max_length=18) for row in rows]
    years = [(float(row["runway_days"]) / 365.0) if row["runway_days"] is not None else 0.0 for row in rows]
    customdata = [
        [
            row["place"],
            row["status"],
            row["place_count"],
            row["supply_stock"],
            row["supply_net_per_day"],
            row["supply"],
        ]
        for row in rows
    ]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=years,
            marker_color=[STATUS_COLORS.get(str(row["status"]), "#64748b") for row in rows],
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>%{y:.2f} years runway"
                "<br>Status %{customdata[1]}"
                "<br>Places %{customdata[2]}"
                "<br>Stock %{customdata[3]:.2f}t"
                "<br>Net %{customdata[4]:.4f}t/day"
                "<br>%{customdata[5]}<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=2, line={"color": "#d9822b", "dash": "dot"})
    fig.add_hline(y=1, line={"color": "#c05621", "dash": "dot"})
    fig.add_hline(y=0.5, line={"color": "#c53030", "dash": "dot"})
    fig.update_layout(title="Current Supply Runway", xaxis_title="", yaxis_title="Years")
    fig.update_xaxes(tickangle=-30)
    return figure_layout(fig)


def normalize_kpi(kpi: dict[str, str] | tuple[str, str, str]) -> dict[str, str]:
    if isinstance(kpi, dict):
        return kpi
    label, value, hint = kpi
    return {"label": str(label), "value": str(value), "hint": str(hint), "url": ""}


def render_kpis(kpis: list[dict[str, str] | tuple[str, str, str]], *, classes: str = "") -> None:
    container_classes = "population-kpis"
    if classes:
        container_classes = f"{container_classes} {classes}"
    with ui.row().classes(container_classes):
        for source_kpi in kpis:
            kpi = normalize_kpi(source_kpi)
            url = kpi.get("url") or ""
            element = (
                ui.link(target=url).classes("population-kpi population-kpi-link")
                if url
                else ui.element("div").classes("population-kpi")
            )
            with element:
                ui.label(kpi["label"]).classes("population-kpi-label")
                ui.label(kpi["value"]).classes("population-kpi-value")
                ui.label(kpi["hint"]).classes("population-kpi-hint")


def plot_click_url(event_args: Any) -> str:
    points = event_args.get("points") if isinstance(event_args, dict) else None
    if not points:
        return ""
    point = points[0] if isinstance(points, list) and points else {}
    custom = point.get("customdata") if isinstance(point, dict) else None
    if isinstance(custom, list):
        for value in reversed(custom):
            if isinstance(value, str) and value.startswith("/population/movement"):
                return value
    if isinstance(custom, str) and custom.startswith("/population/movement"):
        return custom
    return ""


def render_chart_card(title: str, fig: go.Figure, *, enable_click_drilldown: bool = False) -> None:
    fig.update_layout(title=None)
    with ui.element("div").classes("dashboard-card viz-card"):
        ui.label(title).classes("dashboard-card-title viz-card-title")
        plot = ui.plotly(fig).classes("viz-plot")
        if enable_click_drilldown:
            plot.on(
                "plotly_click",
                lambda event: ui.navigate.to(plot_click_url(event.args)) if plot_click_url(event.args) else None,
            )


def render_places_charts(place_rows: list[dict[str, Any]], container: ui.element) -> None:
    container.clear()
    with container:
        with ui.row().classes("dashboard-grid"):
            render_chart_card("Place Supply Balance", place_supply_balance_figure(place_rows, limit=None))
            render_chart_card("Place Housing / Occupancy", place_housing_figure(place_rows, limit=None))
            render_chart_card("Current Supply Runway", place_runway_figure(place_rows, limit=None))


def render_readiness_table(destination_rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Destination Readiness Matrix").classes("dashboard-card-title")
        table = ui.table(
            columns=readiness_columns,
            rows=destination_rows,
            row_key="key",
            pagination=8,
        ).classes("w-full")
        table.props("flat bordered dense wrap-cells")
        table.add_slot(
            "body-cell-destination",
            r"""
            <q-td :props="props">
                <a :href="props.row.drilldown_url" class="table-drilldown-link">{{ props.row.destination }}</a>
            </q-td>
            """,
        )
        table.add_slot(
            "body-cell-drilldown",
            r"""
            <q-td :props="props">
                <a :href="props.row.drilldown_url" class="table-drilldown-link">People Transit</a>
            </q-td>
            """,
        )
        table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <span :class="'readiness-chip ' + props.row.status_class">
                    {{ props.row.status }}
                    <q-icon name="info_outline" size="14px" class="q-ml-xs" />
                    <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
                        <div class="return-fuel-tooltip-title">{{ props.row.message }}</div>
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


def render_places_table(place_rows: list[dict[str, Any]]) -> ui.table:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("Places").classes("dashboard-card-title")
        table = ui.table(
            columns=place_columns,
            rows=place_rows,
            row_key="key",
            pagination=8,
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
                        <div class="return-fuel-tooltip-title">{{ props.row.message }}</div>
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
    return table


def render_population_movement_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    destination_rows = population_metrics_by_destination(analysis)
    flight_rows = population_flights(analysis)
    kpis = population_kpis(destination_rows, flight_rows)

    with container:
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Population Logistics").classes("text-xl font-semibold")
                ui.label("Visual scaffold for moving people, housing, and Supply together.").classes("text-sm text-slate-600")
        render_kpis(kpis)
        render_readiness_table(destination_rows)
        with ui.row().classes("dashboard-grid"):
            render_chart_card("Supply Runway Burndown", supply_burndown_figure(destination_rows))
            render_chart_card("Housing Margin Waterfall", housing_stack_figure(destination_rows))
            render_chart_card("Population Flow", population_flow_sankey(flight_rows), enable_click_drilldown=True)
            render_chart_card("Population Arrival Timeline", arrival_timeline_figure(flight_rows), enable_click_drilldown=True)


def render_population_places_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    place_rows = sort_place_rows(population_places(analysis), focus="risk")
    kpis = place_kpis(place_rows)
    company_options = ["All companies"] + sorted({str(row["company"]) for row in place_rows if row["company"]})
    type_options = ["All types"] + sorted({str(row["type"]) for row in place_rows if row["type"]})

    with container:
        render_kpis(kpis, classes="population-kpis-compact")
        with ui.element("div").classes("chart-control-panel chart-control-panel-compact"):
            with ui.row().classes("chart-control-row"):
                focus_select = ui.select(
                    options=list(PLACE_FOCUS_OPTIONS.keys()),
                    value="Risk first",
                    label="Focus",
                ).classes("chart-control")
                status_select = ui.select(
                    options=list(PLACE_STATUS_FILTER_OPTIONS.keys()),
                    value="All statuses",
                    label="Concern",
                ).classes("chart-control")
                company_select = ui.select(
                    options=company_options,
                    value="All companies",
                    label="Company",
                ).classes("chart-control")
                type_select = ui.select(
                    options=type_options,
                    value="All types",
                    label="Type",
                ).classes("chart-control")
                inbound_select = ui.select(
                    options=list(PLACE_INBOUND_FILTER_OPTIONS.keys()),
                    value="All inbound states",
                    label="Inbound",
                ).classes("chart-control")
                housing_select = ui.select(
                    options=list(PLACE_HOUSING_FILTER_OPTIONS.keys()),
                    value="All housing states",
                    label="Housing",
                ).classes("chart-control")
                runway_select = ui.select(
                    options=list(PLACE_RUNWAY_FILTER_OPTIONS.keys()),
                    value="All runway states",
                    label="Runway",
                ).classes("chart-control")
                population_select = ui.select(
                    options=list(PLACE_POPULATION_FILTER_OPTIONS.keys()),
                    value="All population states",
                    label="Population",
                ).classes("chart-control")
                limit_select = ui.select(
                    options=[6, 10, 15, 25, 50],
                    value=10,
                    label="Places Shown",
                ).classes("chart-control chart-control-small")
                summary = ui.label("").classes("chart-control-summary")
        table = render_places_table(place_rows)
        chart_container = ui.column().classes("w-full")

        def update_charts() -> None:
            focus = PLACE_FOCUS_OPTIONS.get(str(focus_select.value), "risk")
            limit = int(limit_select.value or 6)
            filters = {
                "status": PLACE_STATUS_FILTER_OPTIONS.get(str(status_select.value), "all"),
                "company": str(company_select.value or "All companies"),
                "type": str(type_select.value or "All types"),
                "inbound": PLACE_INBOUND_FILTER_OPTIONS.get(str(inbound_select.value), "all"),
                "housing": PLACE_HOUSING_FILTER_OPTIONS.get(str(housing_select.value), "all"),
                "runway": PLACE_RUNWAY_FILTER_OPTIONS.get(str(runway_select.value), "all"),
                "population": PLACE_POPULATION_FILTER_OPTIONS.get(str(population_select.value), "all"),
            }
            filtered_rows = filter_place_rows(place_rows, filters)
            sorted_rows = sort_place_rows(filtered_rows, focus=focus)
            rows = chart_place_rows(sorted_rows, limit=limit)
            concern_count = sum(1 for row in sorted_rows if row["status"] in ATTENTION_STATUSES)
            other_count = max(len(sorted_rows) - limit, 0)
            table.rows = sorted_rows
            table.update()
            other_text = f"; {other_count} lower-ranked places aggregated as Other" if other_count else ""
            summary.text = (
                f"Showing {min(limit, len(sorted_rows))} ranked places from {len(sorted_rows)} filtered "
                f"of {len(place_rows)} total; {concern_count} actionable concerns{other_text}."
            )
            render_places_charts(rows, chart_container)

        for control in (
            focus_select,
            status_select,
            company_select,
            type_select,
            inbound_select,
            housing_select,
            runway_select,
            population_select,
            limit_select,
        ):
            control.on_value_change(lambda _: update_charts())
        update_charts()


def render_population_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    render_population_movement_dashboard(analysis, container)
