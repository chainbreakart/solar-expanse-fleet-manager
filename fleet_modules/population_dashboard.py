from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import (
    HUMAN_RESOURCE_KEY,
    SUPPLY_RESOURCE_KEY,
    MissionFact,
    PopulationReadinessMetric,
    effective_supply_modifier,
    fmt_num,
    housing_capacity_for_row,
    load_habitat_capacity_map,
    modeled_surface_supply_demand,
    object_company_rows,
    supply_runway_severity,
    stock_fact_lookup,
)


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


def runway_label(days: float | None, projected_net: float) -> str:
    if projected_net >= 0 or days is None:
        return "stable"
    if days >= 365:
        return f"{fmt_num(days / 365)}y"
    return f"{fmt_num(days)}d"


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


def mission_by_key(analysis: SaveAnalysis) -> dict[str, MissionFact]:
    return {mission.mission_key: mission for mission in analysis.mission_facts}


def object_label(analysis: SaveAnalysis, object_id: int | None) -> str:
    if object_id is None:
        return ""
    fact = analysis.object_facts.get(object_id)
    return fact.label if fact else f"Object {object_id}"


def worst_status(statuses: list[str]) -> str:
    return max(statuses or ["Unknown"], key=lambda status: STATUS_RANK.get(status, -1))


def sort_dt_key(value: datetime | None) -> datetime:
    return value if value else datetime.max


def population_metrics_by_destination(
    analysis: SaveAnalysis,
) -> list[dict[str, Any]]:
    missions = mission_by_key(analysis)
    groups: dict[tuple[str, int | None], list[PopulationReadinessMetric]] = defaultdict(list)
    for metric in analysis.population_readiness_metrics:
        groups[(metric.company, metric.destination_id)].append(metric)

    rows: list[dict[str, Any]] = []
    for (company, destination_id), metrics in groups.items():
        arrivals = [
            mission.arrival_dt
            for metric in metrics
            if (mission := missions.get(metric.mission_key)) is not None
        ]
        next_arrival_dt = min((arrival for arrival in arrivals if arrival is not None), default=None)
        statuses = [metric.status for metric in metrics]
        status = worst_status(statuses)
        worst_metric = max(metrics, key=lambda metric: STATUS_RANK.get(metric.status, -1))
        finite_runways = [
            metric.supply_runway_days
            for metric in metrics
            if metric.supply_runway_days is not None and metric.projected_supply_net_per_day < 0
        ]
        runway_days = min(finite_runways) if finite_runways else None
        projected_net = min((metric.projected_supply_net_per_day for metric in metrics), default=0.0)
        inbound_people = max((metric.inbound_people for metric in metrics), default=0)
        current_population = max((metric.current_population for metric in metrics), default=0.0)
        projected_population = max((metric.projected_population for metric in metrics), default=0.0)
        completed_housing = max((metric.completed_housing for metric in metrics), default=0.0)
        queued_housing = max((metric.queued_housing for metric in metrics), default=0.0)
        arriving_housing = max((metric.arriving_housing for metric in metrics), default=0.0)
        housing_gap = max((metric.housing_gap for metric in metrics), default=0.0)
        supply_stock = max((metric.supply_stock for metric in metrics), default=0.0)
        supply_intake = max((metric.supply_intake_per_day for metric in metrics), default=0.0)
        supply_outtake = max((metric.projected_supply_outtake_per_day for metric in metrics), default=0.0)
        supply_net_label = f"{fmt_num(projected_net)}t/day"
        if projected_net > 0:
            supply_net_label = f"+{supply_net_label}"

        rows.append(
            {
                "key": f"{company}:{destination_id}",
                "company": company,
                "destination_id": destination_id,
                "destination": object_label(analysis, destination_id) or worst_metric.destination,
                "status": status,
                "status_class": f"readiness-{status.lower()}",
                "message": worst_metric.message,
                "details": list(worst_metric.details),
                "inbound_people": inbound_people,
                "current_population": current_population,
                "current_population_label": fmt_num(current_population),
                "projected_population": projected_population,
                "population": f"{fmt_num(current_population)} -> {fmt_num(projected_population)}",
                "completed_housing": completed_housing,
                "completed_housing_label": fmt_num(completed_housing),
                "queued_housing": queued_housing,
                "queued_housing_label": fmt_num(queued_housing),
                "arriving_housing": arriving_housing,
                "arriving_housing_label": fmt_num(arriving_housing),
                "housing_gap": housing_gap,
                "housing_gap_label": fmt_num(housing_gap),
                "housing": (
                    f"{fmt_num(completed_housing)} ready + {fmt_num(queued_housing)} queued + "
                    f"{fmt_num(arriving_housing)} carried; gap {fmt_num(housing_gap)}"
                ),
                "supply_stock": supply_stock,
                "supply_stock_label": f"{fmt_num(supply_stock)}t",
                "supply_intake_per_day": supply_intake,
                "projected_supply_outtake_per_day": supply_outtake,
                "projected_supply_net_per_day": projected_net,
                "supply_net_label": supply_net_label,
                "supply": (
                    f"{fmt_num(supply_stock)}t; "
                    f"{fmt_num(supply_intake)} in / {fmt_num(supply_outtake)} out per day"
                ),
                "runway_days": runway_days,
                "runway": runway_label(runway_days, projected_net),
                "next_arrival_dt": next_arrival_dt,
                "next_arrival": next_arrival_dt.strftime("%Y-%m-%d") if next_arrival_dt else "",
            }
        )
    return sorted(rows, key=lambda row: (STATUS_RANK.get(str(row["status"]), -1) * -1, sort_dt_key(row["next_arrival_dt"])))


def population_flights(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    missions = mission_by_key(analysis)
    readiness_by_mission = {
        metric.mission_key: metric for metric in analysis.population_readiness_metrics
    }
    grouped: dict[str, dict[str, Any]] = {}
    for metric in analysis.crew_metrics:
        group = grouped.setdefault(
            metric.mission_key,
            {
                "mission_key": metric.mission_key,
                "mission_id": metric.mission_id,
                "company": metric.company,
                "status": metric.status,
                "craft": set(),
                "people": 0,
                "empty_seats": 0,
                "loaded_modules": 0,
                "empty_modules": 0,
                "life_support": metric.life_support_carriage,
            },
        )
        if metric.craft_name:
            group["craft"].add(metric.craft_name)
        group["people"] += metric.people
        group["empty_seats"] += metric.empty_seats or 0
        if metric.state == "Loaded":
            group["loaded_modules"] += 1
        if metric.state == "Empty":
            group["empty_modules"] += 1
        if not group["life_support"] and metric.life_support_carriage:
            group["life_support"] = metric.life_support_carriage

    rows: list[dict[str, Any]] = []
    for mission_key, group in grouped.items():
        mission = missions.get(mission_key)
        if mission is None:
            continue
        readiness = readiness_by_mission.get(mission_key)
        rows.append(
            {
                **group,
                "craft": ", ".join(sorted(group["craft"])),
                "route": mission.route,
                "source": object_label(analysis, mission.start_id),
                "destination": object_label(analysis, mission.target_id),
                "departure_dt": mission.departure_dt,
                "arrival_dt": mission.arrival_dt,
                "departure": mission.departure,
                "arrival": mission.arrival,
                "duration_days": mission.timing.duration_days,
                "status_label": readiness.status if readiness else ("Safe" if group["people"] <= 0 else "Unknown"),
                "readiness": readiness,
            }
        )
    return sorted(rows, key=lambda row: (sort_dt_key(row["arrival_dt"]), row["company"], row["mission_id"]))


def population_kpis(destination_rows: list[dict[str, Any]], flight_rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    people = sum(int(row["people"]) for row in flight_rows)
    empty_modules = sum(int(row["empty_modules"]) for row in flight_rows)
    empty_seats = sum(int(row["empty_seats"]) for row in flight_rows)
    next_arrival = next((row["arrival"] for row in flight_rows if row["people"] > 0 and row["arrival"]), "")
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
        ("People Moving", str(people), "loaded humans on active/planned flights"),
        ("Empty Holds", str(empty_modules), "crew modules moving without passengers"),
        ("Empty Seats", str(empty_seats), "unused detected transport seats"),
        ("Next Pop Arrival", next_arrival or "-", "earliest loaded population flight"),
        ("Readiness Mix", readiness_value, readiness_hint),
        ("LS Concerns", "-", "life-support exhaustion count awaits formula validation"),
    ]


def place_status(housing_gap: float, runway_days: float | None, supply_net: float) -> str:
    status = supply_runway_severity(runway_days, supply_net)
    if housing_gap > 0:
        status = worst_status([status, "Urgent"])
    return status


def population_places(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    habitat_capacities = load_habitat_capacity_map(analysis.repo_root)
    object_rows = object_company_rows(analysis.save, analysis.included_companies)
    stocks = stock_fact_lookup(analysis.resource_stock_facts)
    inbound_people: dict[tuple[str, int], int] = defaultdict(int)
    for metric in analysis.population_readiness_metrics:
        if metric.destination_id is not None:
            key = (metric.company, metric.destination_id)
            inbound_people[key] = max(inbound_people[key], metric.inbound_people)

    row_keys = set(object_rows)
    row_keys.update((stock.company, stock.object_id) for stock in analysis.resource_stock_facts if stock.resource_key == HUMAN_RESOURCE_KEY)
    row_keys.update(inbound_people)

    rows: list[dict[str, Any]] = []
    for company, object_id in sorted(row_keys, key=lambda item: (item[0], item[1])):
        object_fact = analysis.object_facts.get(object_id)
        object_row = object_rows.get((company, object_id))
        human_stock = stocks.get((company, object_id, HUMAN_RESOURCE_KEY))
        supply_stock = stocks.get((company, object_id, SUPPLY_RESOURCE_KEY))
        current_population = human_stock.value if human_stock else 0.0
        completed_housing, queued_housing = housing_capacity_for_row(object_row, habitat_capacities)
        incoming = inbound_people.get((company, object_id), 0)
        if current_population <= 0 and completed_housing <= 0 and queued_housing <= 0 and incoming <= 0:
            continue

        modeled_demand = modeled_surface_supply_demand(current_population, completed_housing)
        saved_outtake = supply_stock.outtake if supply_stock else 0.0
        modifier, modifier_basis = effective_supply_modifier(saved_outtake, modeled_demand)
        estimated_outtake = saved_outtake or modeled_demand * modifier
        supply_value = supply_stock.value if supply_stock else 0.0
        supply_intake = supply_stock.intake if supply_stock else 0.0
        supply_net = supply_intake - estimated_outtake
        runway_days = supply_value / abs(supply_net) if supply_net < 0 else None
        housing_gap = max(current_population - completed_housing, 0.0)
        free_housing = max(completed_housing - current_population, 0.0)
        status = place_status(housing_gap, runway_days, supply_net)
        pieces = []
        if housing_gap > 0:
            pieces.append(f"housing short {fmt_num(housing_gap)}")
        if supply_net < 0:
            pieces.append(f"Supply runway {runway_label(runway_days, supply_net)}")
        if incoming:
            pieces.append(f"{incoming} people inbound")
        if status == "Monitor" and pieces:
            message = "Monitor: long-range drawdown; " + "; ".join(pieces)
        else:
            message = f"{status}: " + "; ".join(pieces) if pieces else "Safe: current population support looks stable"
        status_details = [
            f"Population: {fmt_num(current_population)}",
            f"Ready housing: {fmt_num(completed_housing)}",
            f"Queued housing: {fmt_num(queued_housing)}",
            f"Free housing now: {fmt_num(free_housing)}",
            f"Inbound people: {incoming}",
            f"Supply stock: {fmt_num(supply_value)}t",
            f"Supply intake/day: {fmt_num(supply_intake)}",
            f"Estimated Supply out/day: {fmt_num(estimated_outtake)}",
            f"Net Supply/day: {fmt_num(supply_net)}",
            f"Runway: {runway_label(runway_days, supply_net)}",
            f"Supply modifier: {fmt_num(modifier)} ({modifier_basis})",
        ]

        rows.append(
            {
                "key": f"{company}:{object_id}",
                "company": company,
                "object_id": object_id,
                "place": object_fact.label if object_fact else f"Object {object_id}",
                "type": object_fact.object_type if object_fact else "",
                "relationship": object_fact.relationship if object_fact else "",
                "status": status,
                "status_class": f"readiness-{status.lower()}",
                "message": message,
                "status_details": status_details,
                "current_population": current_population,
                "population": fmt_num(current_population),
                "completed_housing": completed_housing,
                "queued_housing": queued_housing,
                "free_housing": free_housing,
                "housing_gap": housing_gap,
                "housing": f"{fmt_num(completed_housing)} ready + {fmt_num(queued_housing)} queued; free {fmt_num(free_housing)}",
                "supply_stock": supply_value,
                "supply_intake_per_day": supply_intake,
                "supply_outtake_per_day": estimated_outtake,
                "supply_net_per_day": supply_net,
                "supply_modifier": modifier,
                "supply_modifier_basis": modifier_basis,
                "supply": f"{fmt_num(supply_value)}t; {fmt_num(supply_intake)} in / {fmt_num(estimated_outtake)} out per day",
                "runway_days": runway_days,
                "runway": runway_label(runway_days, supply_net),
                "inbound_people": incoming,
            }
        )

    return sorted(rows, key=lambda row: (STATUS_RANK.get(str(row["status"]), -1) * -1, -float(row["current_population"]), str(row["place"])))


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


def selected_place_chart_rows(
    place_rows: list[dict[str, Any]],
    *,
    focus: str,
    limit: int,
    include_safe: bool,
) -> list[dict[str, Any]]:
    rows = list(place_rows if include_safe else [row for row in place_rows if row["status"] in ATTENTION_STATUSES])
    if focus == "runway":
        rows.sort(key=lambda row: (place_runway_sort_value(row), -float(row["current_population"]), str(row["place"])))
    elif focus == "population":
        rows.sort(key=lambda row: (-float(row["current_population"]), place_runway_sort_value(row), str(row["place"])))
    elif focus == "housing":
        rows.sort(key=lambda row: (-float(row["housing_gap"]), -float(row["current_population"]), str(row["place"])))
    elif focus == "inbound":
        rows.sort(key=lambda row: (-int(row["inbound_people"]), -STATUS_RANK.get(str(row["status"]), 0), str(row["place"])))
    else:
        rows.sort(
            key=lambda row: (
                -STATUS_RANK.get(str(row["status"]), 0),
                place_runway_sort_value(row),
                -float(row["housing_gap"]),
                -float(row["current_population"]),
                str(row["place"]),
            )
        )
    return rows[:limit]


def supply_burndown_figure(destination_rows: list[dict[str, Any]]) -> go.Figure:
    rows = [row for row in destination_rows if row["inbound_people"] > 0][:6]
    if not rows:
        return empty_figure("Supply Runway", "No inbound population destinations in this save.")
    fig = go.Figure()
    horizon = 730
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
                hovertemplate="Day %{x}<br>Supply %{y:.2f}t<extra></extra>",
            )
        )
    fig.add_hline(y=0, line={"color": "#c53030", "dash": "dot"})
    fig.update_layout(title="Supply Runway Burndown", xaxis_title="Days From Save", yaxis_title="Projected Supply Stock (t)")
    return figure_layout(fig)


def housing_stack_figure(destination_rows: list[dict[str, Any]]) -> go.Figure:
    rows = [row for row in destination_rows if row["inbound_people"] > 0][:8]
    if not rows:
        return empty_figure("Housing Readiness", "No inbound population destinations in this save.")
    labels = [str(row["destination"]) for row in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Ready housing", x=labels, y=[row["completed_housing"] for row in rows], marker_color="#2f855a"))
    fig.add_trace(go.Bar(name="Queued housing", x=labels, y=[row["queued_housing"] for row in rows], marker_color="#b7791f"))
    fig.add_trace(go.Bar(name="Carried habitat", x=labels, y=[row["arriving_housing"] for row in rows], marker_color="#315c72"))
    fig.add_trace(
        go.Scatter(
            name="Projected population",
            x=labels,
            y=[row["projected_population"] for row in rows],
            mode="markers",
            marker={"symbol": "line-ew", "size": 18, "color": "#172026", "line": {"width": 3}},
        )
    )
    fig.update_layout(title="Housing Stack / Gap", barmode="stack", xaxis_title="", yaxis_title="People / Capacity")
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

    links: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in loaded:
        source = row["source"] or "Unknown origin"
        destination = row["destination"] or "Unknown destination"
        links[(source, destination, str(row["status_label"]))] += int(row["people"])

    fig = go.Figure(
        data=[
            go.Sankey(
                node={"label": labels, "pad": 18, "thickness": 16, "color": "#d8ded8"},
                link={
                    "source": [label_index(source) for source, _, _ in links],
                    "target": [label_index(destination) for _, destination, _ in links],
                    "value": list(links.values()),
                    "color": [STATUS_COLORS.get(status, "#64748b") for _, _, status in links],
                    "customdata": [status for _, _, status in links],
                    "hovertemplate": "%{source.label} -> %{target.label}<br>%{value} people<br>Status %{customdata}<extra></extra>",
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
                hovertemplate=(
                    f"Mission {row['mission_id']}<br>{row['route']}<br>"
                    f"{row['people']} people<br>{row['status_label']}<extra></extra>"
                ),
            )
        )
    fig.update_layout(title="Population Arrival Timeline", xaxis_title="", yaxis_title="")
    return figure_layout(fig, height=360)


def place_supply_balance_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = place_rows if limit is None else place_rows[:limit]
    if not rows:
        return empty_figure("Place Supply Balance", "No populated places or habitats detected in this save.")
    labels = [chart_label(row["place"]) for row in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Supply intake/day", x=labels, y=[row["supply_intake_per_day"] for row in rows], marker_color="#43e6a0"))
    fig.add_trace(go.Bar(name="Supply outtake/day", x=labels, y=[row["supply_outtake_per_day"] for row in rows], marker_color="#ff9d2e"))
    fig.add_trace(
        go.Scatter(
            name="Net/day",
            x=labels,
            y=[row["supply_net_per_day"] for row in rows],
            mode="markers",
            marker={"size": 10, "color": [STATUS_COLORS.get(str(row["status"]), "#64748b") for row in rows]},
        )
    )
    fig.update_layout(title="Place Supply Balance", barmode="group", xaxis_title="", yaxis_title="Supply tons / day")
    return figure_layout(fig)


def place_housing_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = [row for row in place_rows if row["current_population"] > 0 or row["completed_housing"] > 0 or row["queued_housing"] > 0]
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return empty_figure("Place Housing", "No local population or habitat capacity detected in this save.")
    labels = [chart_label(row["place"]) for row in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Ready housing", x=labels, y=[row["completed_housing"] for row in rows], marker_color="#35d8ff"))
    fig.add_trace(go.Bar(name="Queued housing", x=labels, y=[row["queued_housing"] for row in rows], marker_color="#ff9d2e"))
    fig.add_trace(
        go.Scatter(
            name="Current population",
            x=labels,
            y=[row["current_population"] for row in rows],
            mode="markers",
            marker={"symbol": "line-ew", "size": 18, "color": "#f7fbff", "line": {"width": 3}},
        )
    )
    fig.update_layout(title="Place Housing / Occupancy", barmode="stack", xaxis_title="", yaxis_title="People / Capacity")
    return figure_layout(fig)


def place_runway_figure(place_rows: list[dict[str, Any]], *, limit: int | None = 6) -> go.Figure:
    rows = [row for row in place_rows if row["supply_net_per_day"] < 0]
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        return empty_figure("Current Supply Runway", "All detected populated places have non-negative Supply flow or no Supply burn.")
    labels = [chart_label(row["place"]) for row in rows]
    years = [(float(row["runway_days"]) / 365.0) if row["runway_days"] is not None else 0.0 for row in rows]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=years,
            marker_color=[STATUS_COLORS.get(str(row["status"]), "#64748b") for row in rows],
            hovertemplate="%{x}<br>%{y:.2f} years<extra></extra>",
        )
    )
    fig.add_hline(y=2, line={"color": "#d9822b", "dash": "dot"})
    fig.add_hline(y=1, line={"color": "#c05621", "dash": "dot"})
    fig.add_hline(y=0.5, line={"color": "#c53030", "dash": "dot"})
    fig.update_layout(title="Current Supply Runway", xaxis_title="", yaxis_title="Years")
    return figure_layout(fig)


def render_kpis(kpis: list[tuple[str, str, str]]) -> None:
    with ui.row().classes("population-kpis"):
        for label, value, hint in kpis:
            with ui.element("div").classes("population-kpi"):
                ui.label(label).classes("population-kpi-label")
                ui.label(value).classes("population-kpi-value")
                ui.label(hint).classes("population-kpi-hint")


def render_chart_card(title: str, fig: go.Figure) -> None:
    fig.update_layout(title=None)
    with ui.element("div").classes("dashboard-card viz-card"):
        ui.label(title).classes("dashboard-card-title viz-card-title")
        ui.plotly(fig).classes("viz-plot")


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


def render_places_table(place_rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
        ui.label("People In Place").classes("dashboard-card-title")
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
            render_chart_card("Housing Stack / Gap", housing_stack_figure(destination_rows))
            render_chart_card("Population Flow", population_flow_sankey(flight_rows))
            render_chart_card("Population Arrival Timeline", arrival_timeline_figure(flight_rows))


def render_population_places_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    place_rows = population_places(analysis)
    kpis = place_kpis(place_rows)

    with container:
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Colonies / Stations").classes("text-xl font-semibold")
                ui.label("Current people in place, housing, Supply flow, and sustainment runway.").classes("text-sm text-slate-600")
        render_kpis(kpis)
        render_places_table(place_rows)
        with ui.element("div").classes("chart-control-panel"):
            ui.label("Chart Controls").classes("dashboard-card-title chart-control-title")
            with ui.row().classes("chart-control-row"):
                focus_select = ui.select(
                    options=list(PLACE_FOCUS_OPTIONS.keys()),
                    value="Risk first",
                    label="Focus",
                ).classes("chart-control")
                limit_select = ui.select(
                    options=[6, 10, 15, 25],
                    value=6,
                    label="Places Shown",
                ).classes("chart-control chart-control-small")
                include_safe = ui.checkbox("Include safe / monitor places", value=False).classes("chart-control-checkbox")
                summary = ui.label("").classes("chart-control-summary")
        chart_container = ui.column().classes("w-full")

        def update_charts() -> None:
            focus = PLACE_FOCUS_OPTIONS.get(str(focus_select.value), "risk")
            limit = int(limit_select.value or 6)
            rows = selected_place_chart_rows(
                place_rows,
                focus=focus,
                limit=limit,
                include_safe=bool(include_safe.value),
            )
            concern_count = sum(1 for row in rows if row["status"] in ATTENTION_STATUSES)
            summary.text = f"Showing {len(rows)} of {len(place_rows)} places; {concern_count} actionable concerns in chart slice."
            render_places_charts(rows, chart_container)

        focus_select.on_value_change(lambda _: update_charts())
        limit_select.on_value_change(lambda _: update_charts())
        include_safe.on_value_change(lambda _: update_charts())
        update_charts()


def render_population_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    render_population_movement_dashboard(analysis, container)
