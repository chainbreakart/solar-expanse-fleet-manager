from __future__ import annotations

from collections import Counter
from typing import Any

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer import fmt_num

from .shared import TableModule, TableRow


columns = [
    {"name": "expand", "label": "", "field": "expand", "sortable": False, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "mission", "label": "Mission", "field": "mission", "sortable": True, "align": "right"},
    {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
    {"name": "route", "label": "Route", "field": "route", "sortable": True, "align": "left"},
    {"name": "departure", "label": "Departure", "field": "departure", "sortable": True, "align": "left"},
    {"name": "arrival", "label": "Arrival", "field": "arrival", "sortable": True, "align": "left"},
    {"name": "timing", "label": "Timing", "field": "timing", "sortable": True, "align": "left"},
    {"name": "people", "label": "People", "field": "people", "sortable": True, "align": "right"},
    {"name": "capacity", "label": "Reference Seats", "field": "capacity", "sortable": True, "align": "right"},
    {"name": "empty_seats", "label": "Empty Seats", "field": "empty_seats", "sortable": True, "align": "right"},
    {"name": "life_support", "label": "Mission LS", "field": "life_support", "sortable": True, "align": "right"},
    {"name": "state", "label": "Manifest", "field": "state", "sortable": True, "align": "left"},
    {"name": "readiness", "label": "Destination Readiness", "field": "readiness", "sortable": True, "align": "left"},
]


def int_or_zero(value: object) -> int:
    return value if isinstance(value, int) else 0


def readiness_payload(analysis: SaveAnalysis, mission_key: str, people: int) -> tuple[str, str, list[str], str]:
    if people <= 0:
        return "", "", [], ""
    readiness = next((metric for metric in analysis.population_readiness_metrics if metric.mission_key == mission_key), None)
    if readiness is None:
        return "Safe", "Safe: no destination housing or supply issue detected", [], "readiness-safe"
    return readiness.status, readiness.message, list(readiness.details), f"readiness-{readiness.status.lower()}"


def module_detail(metric) -> dict[str, object]:
    return {
        "cargo_item": metric.cargo_item,
        "compartment_type": metric.compartment_type,
        "people": metric.people,
        "capacity": metric.reference_seats or "",
        "empty_seats": metric.empty_seats if metric.empty_seats is not None else "",
        "life_support": f"{fmt_num(metric.row_life_support)}" if metric.row_life_support else "",
        "state": metric.state,
        "location": metric.location,
    }


def manifest_summary(details: list[dict[str, object]]) -> str:
    counts = Counter(str(detail["state"]) for detail in details if detail.get("state"))
    pieces = []
    if counts.get("Loaded"):
        pieces.append(f"{counts['Loaded']} loaded")
    if counts.get("Empty"):
        pieces.append(f"{counts['Empty']} empty")
    if counts.get("No people"):
        pieces.append(f"{counts['No people']} no people")
    return "; ".join(pieces) or f"{len(details)} item"


def group_rows(analysis: SaveAnalysis) -> list[TableRow]:
    grouped: dict[str, dict[str, Any]] = {}
    for metric in analysis.crew_metrics:
        group = grouped.setdefault(
            metric.mission_key,
            {
                "key": metric.mission_key,
                "company": metric.company,
                "status": metric.status,
                "mission": metric.mission_id,
                "craft_names": [],
                "route": metric.route,
                "departure": metric.departure,
                "arrival": metric.arrival,
                "timing": metric.timing,
                "people": 0,
                "capacity": 0,
                "has_capacity": False,
                "empty_seats": 0,
                "has_empty_seats": False,
                "life_support_value": metric.life_support_carriage,
                "details": [],
            },
        )
        if metric.craft_name and metric.craft_name not in group["craft_names"]:
            group["craft_names"].append(metric.craft_name)
        group["people"] = int(group["people"]) + metric.people
        if metric.reference_seats is not None:
            group["capacity"] = int(group["capacity"]) + metric.reference_seats
            group["has_capacity"] = True
        if metric.empty_seats is not None:
            group["empty_seats"] = int(group["empty_seats"]) + metric.empty_seats
            group["has_empty_seats"] = True
        if not group["life_support_value"] and metric.life_support_carriage:
            group["life_support_value"] = metric.life_support_carriage
        group["details"].append(module_detail(metric))

    rows: list[TableRow] = []
    for group in grouped.values():
        people = int(group["people"])
        readiness, readiness_message, readiness_details, readiness_class = readiness_payload(
            analysis,
            str(group["key"]),
            people,
        )
        rows.append(
            {
                "key": group["key"],
                "company": group["company"],
                "status": group["status"],
                "mission": group["mission"],
                "craft": ", ".join(group["craft_names"]),
                "route": group["route"],
                "departure": group["departure"],
                "arrival": group["arrival"],
                "timing": group["timing"],
                "people": people,
                "capacity": group["capacity"] if group["has_capacity"] else "",
                "empty_seats": group["empty_seats"] if group["has_empty_seats"] else "",
                "life_support": f"{fmt_num(group['life_support_value'])}" if group["life_support_value"] else "",
                "state": manifest_summary(group["details"]),
                "readiness": readiness,
                "readiness_message": readiness_message,
                "readiness_details": readiness_details,
                "readiness_class": readiness_class,
                "details": group["details"],
                "detail_count": len(group["details"]),
            }
        )
    return sorted(rows, key=lambda row: (str(row.get("arrival") or "9999"), str(row.get("company")), str(row.get("mission"))))


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    return group_rows(analysis)


def build_metrics(_analysis: SaveAnalysis, rows: list[TableRow]) -> dict[str, str]:
    details = [detail for row in rows for detail in row.get("details", []) if isinstance(detail, dict)]
    return {
        "people_in_transit": str(sum(int_or_zero(row.get("people")) for row in rows)),
        "loaded_people_items": str(sum(1 for detail in details if detail.get("state") == "Loaded")),
        "empty_crew_items": str(sum(1 for detail in details if detail.get("state") == "Empty")),
        "empty_crew_seats": str(sum(int_or_zero(row.get("empty_seats")) for row in rows)),
        "population_readiness_alerts": str(sum(1 for row in rows if row.get("readiness") not in {"", "Safe"})),
    }


readiness_chip = r"""
    <span v-if="props.row.readiness" :class="'readiness-chip ' + props.row.readiness_class">
        {{ props.row.readiness }}
        <q-icon name="info_outline" size="14px" class="q-ml-xs" />
        <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
            <div class="return-fuel-tooltip-title">{{ props.row.readiness_message }}</div>
            <div
                v-for="line in props.row.readiness_details"
                :key="line"
                class="return-fuel-tooltip-line"
            >
                {{ line }}
            </div>
        </q-tooltip>
    </span>
"""


slots = {
    "body": rf"""
        <q-tr :props="props">
            <q-td key="expand" :props="props">
                <q-btn
                    v-if="props.row.detail_count > 1"
                    size="sm"
                    color="primary"
                    round
                    dense
                    flat
                    @click="props.expand = !props.expand"
                    :icon="props.expand ? 'expand_less' : 'expand_more'"
                />
            </q-td>
            <q-td key="company" :props="props">{{{{ props.row.company }}}}</q-td>
            <q-td key="status" :props="props">{{{{ props.row.status }}}}</q-td>
            <q-td key="mission" :props="props">{{{{ props.row.mission }}}}</q-td>
            <q-td key="craft" :props="props">{{{{ props.row.craft }}}}</q-td>
            <q-td key="route" :props="props">{{{{ props.row.route }}}}</q-td>
            <q-td key="departure" :props="props">{{{{ props.row.departure }}}}</q-td>
            <q-td key="arrival" :props="props">{{{{ props.row.arrival }}}}</q-td>
            <q-td key="timing" :props="props">{{{{ props.row.timing }}}}</q-td>
            <q-td key="people" :props="props">{{{{ props.row.people }}}}</q-td>
            <q-td key="capacity" :props="props">{{{{ props.row.capacity }}}}</q-td>
            <q-td key="empty_seats" :props="props">{{{{ props.row.empty_seats }}}}</q-td>
            <q-td key="life_support" :props="props">{{{{ props.row.life_support }}}}</q-td>
            <q-td key="state" :props="props">{{{{ props.row.state }}}}</q-td>
            <q-td key="readiness" :props="props">
                {readiness_chip}
            </q-td>
        </q-tr>
        <q-tr v-show="props.expand" :props="props">
            <q-td :colspan="props.cols.length">
                <div class="people-detail">
                    <div class="people-detail-row people-detail-header">
                        <div>Compartment / Humans</div>
                        <div>Type</div>
                        <div>People</div>
                        <div>Seats</div>
                        <div>Empty</div>
                        <div>LS</div>
                        <div>State</div>
                    </div>
                    <div
                        v-for="detail in props.row.details"
                        :key="detail.cargo_item + detail.location + detail.state"
                        class="people-detail-row"
                    >
                        <div>{{{{ detail.cargo_item }}}}</div>
                        <div>{{{{ detail.compartment_type }}}}</div>
                        <div>{{{{ detail.people }}}}</div>
                        <div>{{{{ detail.capacity }}}}</div>
                        <div>{{{{ detail.empty_seats }}}}</div>
                        <div>{{{{ detail.life_support }}}}</div>
                        <div>{{{{ detail.state }}}}</div>
                    </div>
                </div>
            </q-td>
        </q-tr>
    """,
}


MODULE = TableModule(
    key="people",
    label="People Transit",
    columns=columns,
    build_rows=build_rows,
    build_metrics=build_metrics,
    slots=slots,
)
