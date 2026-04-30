from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import ROUTE_ACTIVE_STATUSES, ROUTE_LOAD_STATUSES, ROUTE_PLANNED_STATUSES, fmt_num


CARGO_TRANSIT_KINDS = {"resource", "module", "crew_module", "fuel", "unknown"}


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
    {"name": "top_cargo", "label": "Major Cargo", "field": "top_cargo", "sortable": False, "align": "left"},
]


def sort_dt_key(value: datetime | None) -> datetime:
    return value if value else datetime.max


def cargo_kind_label(kind: str) -> str:
    return {
        "resource": "Resource",
        "module": "Module",
        "crew_module": "Crew module",
        "fuel": "Fuel",
        "unknown": "Unknown",
    }.get(kind, kind.replace("_", " ").title())


def compact_summary(totals: dict[str, float], *, limit: int = 4) -> str:
    items = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    pieces = [f"{name} {fmt_num(mass)}t" for name, mass in items[:limit] if mass > 0]
    if len(items) > limit:
        pieces.append(f"+{len(items) - limit} more")
    return "; ".join(pieces)


def cargo_manifest_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    mission_by_key = {mission.mission_key: mission for mission in analysis.mission_facts}
    craft_by_id = {craft.craft_id: craft for craft in analysis.craft_facts}
    groups: dict[str, dict[str, Any]] = {}

    for cargo in analysis.cargo_facts:
        if cargo.source_type != "mission" or cargo.mission_status not in ROUTE_LOAD_STATUSES:
            continue
        if cargo.cargo_kind not in CARGO_TRANSIT_KINDS:
            continue
        if cargo.mass <= 0:
            continue

        mission = mission_by_key.get(cargo.mission_key)
        mission_key = cargo.mission_key or cargo.source_key
        group = groups.setdefault(
            mission_key,
            {
                "key": mission_key,
                "company": cargo.company,
                "status": cargo.mission_status,
                "mission": cargo.mission_id,
                "craft_ids": set(mission.craft_ids if mission else cargo.craft_ids),
                "route": mission.route if mission else cargo.route,
                "departure": mission.departure if mission else cargo.departure,
                "arrival": mission.arrival if mission else cargo.arrival,
                "arrival_dt": mission.arrival_dt if mission else cargo.arrival_dt,
                "departure_dt": mission.departure_dt if mission else cargo.departure_dt,
                "tons_value": 0.0,
                "fuel_tons_value": 0.0,
                "item_count": 0,
                "cargo_totals": defaultdict(float),
                "kind_counts": Counter(),
                "details": [],
            },
        )

        group["tons_value"] = float(group["tons_value"]) + cargo.mass
        if cargo.cargo_kind == "fuel":
            group["fuel_tons_value"] = float(group["fuel_tons_value"]) + cargo.mass
        group["item_count"] = int(group["item_count"]) + 1
        group["cargo_totals"][cargo.display_name or cargo_kind_label(cargo.cargo_kind)] += cargo.mass
        group["kind_counts"][cargo_kind_label(cargo.cargo_kind)] += 1
        group["details"].append(
            {
                "name": cargo.display_name or cargo_kind_label(cargo.cargo_kind),
                "kind": cargo_kind_label(cargo.cargo_kind),
                "list": cargo.list_label,
                "mass": f"{fmt_num(cargo.mass)}t",
                "mass_value": cargo.mass,
                "resource": cargo.resource_key,
                "module": cargo.module_key,
            }
        )

    rows: list[dict[str, Any]] = []
    for group in groups.values():
        craft_names = [
            craft_by_id[craft_id].craft_name
            for craft_id in sorted(group["craft_ids"])
            if craft_id in craft_by_id
        ]
        kind_summary = ", ".join(f"{kind} {count}" for kind, count in sorted(group["kind_counts"].items()))
        top_cargo = compact_summary(group["cargo_totals"])
        rows.append(
            {
                "key": group["key"],
                "company": group["company"],
                "status": group["status"],
                "mission": group["mission"],
                "craft": ", ".join(craft_names),
                "route": group["route"],
                "departure": group["departure"],
                "arrival": group["arrival"],
                "arrival_dt": group["arrival_dt"],
                "departure_dt": group["departure_dt"],
                "tons_value": group["tons_value"],
                "tons": f"{fmt_num(group['tons_value'])}t",
                "items": group["item_count"],
                "fuel_tons_value": group["fuel_tons_value"],
                "fuel": f"{fmt_num(group['fuel_tons_value'])}t" if group["fuel_tons_value"] else "",
                "top_cargo": top_cargo,
                "kind_summary": kind_summary,
                "details": sorted(group["details"], key=lambda detail: (str(detail["kind"]), str(detail["name"]))),
                "detail_count": len(group["details"]),
            }
        )

    status_rank = {"En route": 0, "Cyclical": 1, "Planned": 2}
    return sorted(
        rows,
        key=lambda row: (
            status_rank.get(str(row["status"]), 9),
            sort_dt_key(row["arrival_dt"]),
            str(row["company"]),
            str(row["mission"]),
        ),
    )


def cargo_kpis(rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    active_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_ACTIVE_STATUSES)
    planned_tons = sum(float(row["tons_value"]) for row in rows if row["status"] in ROUTE_PLANNED_STATUSES)
    fuel_tons = sum(float(row["fuel_tons_value"]) for row in rows)
    routes = {row["route"] for row in rows if row["route"]}
    active_routes = {row["route"] for row in rows if row["route"] and row["status"] in ROUTE_ACTIVE_STATUSES}
    next_arrival = next((row["arrival"] for row in rows if row["arrival"]), "")

    item_totals: dict[str, float] = defaultdict(float)
    for row in rows:
        for detail in row["details"]:
            item_totals[str(detail["name"])] += float(detail["mass_value"])
    top_cargo = compact_summary(item_totals, limit=2) or "-"

    return [
        ("Cargo Moving", f"{fmt_num(active_tons)}t", "active cargo currently en route or cycling"),
        ("Cargo Planned", f"{fmt_num(planned_tons)}t", "cargo assigned to planned flights"),
        ("Cargo Flights", str(len(rows)), "active/planned missions carrying cargo"),
        ("Active Routes", f"{len(active_routes)} / {len(routes)}", "active cargo lanes out of all cargo lanes"),
        ("Next Cargo Arrival", next_arrival or "-", "earliest active/planned cargo arrival"),
        ("Fuel Cargo", f"{fmt_num(fuel_tons)}t", f"top cargo: {top_cargo}"),
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
            <q-td key="craft" :props="props">{{ props.row.craft }}</q-td>
            <q-td key="route" :props="props">{{ props.row.route }}</q-td>
            <q-td key="departure" :props="props">{{ props.row.departure }}</q-td>
            <q-td key="arrival" :props="props">{{ props.row.arrival }}</q-td>
            <q-td key="tons" :props="props">{{ props.row.tons }}</q-td>
            <q-td key="items" :props="props">{{ props.row.items }}</q-td>
            <q-td key="fuel" :props="props">{{ props.row.fuel }}</q-td>
            <q-td key="top_cargo" :props="props">{{ props.row.top_cargo }}</q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td colspan="100%">
                <div class="cargo-detail">
                    <div class="cargo-detail-row cargo-detail-header">
                        <div>Item</div>
                        <div>Kind</div>
                        <div>List</div>
                        <div>Mass</div>
                    </div>
                    <div
                        v-for="detail in props.row.details"
                        :key="detail.name + detail.kind + detail.list + detail.mass"
                        class="cargo-detail-row"
                    >
                        <div>{{ detail.name }}</div>
                        <div>{{ detail.kind }}</div>
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


def render_cargo_dashboard(analysis: SaveAnalysis, container: ui.element) -> None:
    container.clear()
    rows = cargo_manifest_rows(analysis)
    with container:
        with ui.row().classes("dashboard-title-row"):
            with ui.column().classes("gap-0"):
                ui.label("Cargo Transit").classes("text-xl font-semibold")
                ui.label("What cargo is moving, where it is going, what craft carry it, and when it arrives.").classes(
                    "text-sm text-slate-600"
                )
        render_kpis(cargo_kpis(rows))
        render_route_cards(rows)
        render_manifest_table(rows)
