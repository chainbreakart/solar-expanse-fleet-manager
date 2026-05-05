from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import ROUTE_ACTIVE_STATUSES, ROUTE_PLANNED_STATUSES, fmt_dt, fmt_num


@dataclass(frozen=True)
class OverviewEvent:
    when: datetime
    label: str
    hint: str


def earliest_event(events: list[OverviewEvent]) -> OverviewEvent | None:
    return min(events, key=lambda event: event.when) if events else None


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
            "url": "/data",
        },
        {
            "label": "Planned Departures",
            "value": fmt_num(len(planned_missions)),
            "hint": "scheduled assignments not yet launched",
            "url": "/data",
        },
        {
            "label": "Next Arrival",
            "value": next_arrival.label if next_arrival else "-",
            "hint": next_arrival.hint if next_arrival else "no dated active/planned arrivals",
            "url": "/data",
        },
        {
            "label": "Next Departure",
            "value": next_departure.label if next_departure else "-",
            "hint": next_departure.hint if next_departure else "no dated planned departures",
            "url": "/data",
        },
        {
            "label": "Idle Craft",
            "value": fmt_num(len(idle_craft)),
            "hint": "craft without active assignments",
            "url": "/data",
        },
        {
            "label": "Needs Attention",
            "value": fmt_num(attention_count),
            "hint": f"{fmt_num(critical_attention)} critical row(s)" if critical_attention else "attention rows across all categories",
            "url": "/data",
        },
    ]


def render_global_overview_kpis(analysis: SaveAnalysis) -> None:
    with ui.element("div").classes("population-kpis population-kpis-compact"):
        for kpi in global_overview_kpis(analysis):
            element = ui.link(target=kpi["url"]).classes("population-kpi population-kpi-link")
            with element:
                ui.label(kpi["label"]).classes("population-kpi-label")
                ui.label(kpi["value"]).classes("population-kpi-value")
                ui.label(kpi["hint"]).classes("population-kpi-hint")
