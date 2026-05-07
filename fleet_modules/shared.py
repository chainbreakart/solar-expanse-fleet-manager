from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence
from urllib.parse import urlencode

from nicegui import ui

from fleet_core.analysis import SaveAnalysis

TableRow = dict[str, object]
TableColumn = dict[str, object]
RowsBuilder = Callable[[SaveAnalysis], list[TableRow]]
MetricsBuilder = Callable[[SaveAnalysis, list[TableRow]], dict[str, str]]

AUDIT_COLUMNS: list[TableColumn] = [
    {"name": "audit_source", "label": "Audit Source", "field": "audit_source", "sortable": True, "align": "left"},
    {"name": "confidence", "label": "Confidence", "field": "confidence", "sortable": True, "align": "left"},
    {"name": "anomaly_destination", "label": "Anomaly Destination", "field": "anomaly_destination", "sortable": True, "align": "left"},
]

RESOURCE_ICON_FILES = {
    "id_resource_alloy": "resource_definition_id_resource_alloy.png",
    "id_resource_antimatter": "resource_definition_id_resource_antimatter.png",
    "id_resource_chips": "resource_definition_id_resource_chips.png",
    "id_resource_co2": "resource_definition_id_resource_co2.png",
    "id_resource_consumergoods": "resource_definition_id_resource_consumergoods.png",
    "id_resource_energy": "resource_definition_id_resource_energy.png",
    "id_resource_fuel": "resource_definition_id_resource_fuel.png",
    "id_resource_glass": "resource_definition_id_resource_glass.png",
    "id_resource_hel3": "resource_definition_id_resource_HEL3.png",
    "id_resource_human": "resource_definition_id_resource_human.png",
    "id_resource_hydrogen": "resource_definition_id_resource_hydrogen.png",
    "id_resource_metal": "resource_definition_id_resource_metal.png",
    "id_resource_nitrogen": "resource_definition_id_resource_nitrogen.png",
    "id_resource_noblegas": "resource_definition_id_resource_noblegas.png",
    "id_resource_oxygen": "resource_definition_id_resource_oxygen.png",
    "id_resource_plastic": "resource_definition_id_resource_plastic.png",
    "id_resource_raremetal": "resource_definition_id_resource_raremetal.png",
    "id_resource_silicon": "resource_definition_id_resource_silicon.png",
    "id_resource_steel": "resource_definition_id_resource_steel.png",
    "id_resource_supply": "resource_definition_id_resource_supply.png",
    "id_resource_uran": "resource_definition_id_resource_uran.png",
    "id_resource_volatile": "resource_definition_id_resource_volatile.png",
    "id_resource_water": "resource_definition_id_resource_water.png",
}


def no_metrics(_analysis: SaveAnalysis, _rows: list[TableRow]) -> dict[str, str]:
    return {}


def data_tab_link(tab_key: str, **params: object) -> str:
    clean = {"tab": tab_key}
    clean.update({key: value for key, value in params.items() if value not in (None, "")})
    return f"/data?{urlencode(clean)}"


def fleet_link(**params: object) -> str:
    clean = {key: value for key, value in params.items() if value not in (None, "")}
    return f"/fleet?{urlencode(clean)}" if clean else "/fleet"


def resource_icon_url(resource_key: object) -> str:
    filename = RESOURCE_ICON_FILES.get(str(resource_key).lower())
    return f"/fleet-assets/resource_icons/{filename}" if filename else ""


def with_resource_icon(
    row: TableRow,
    *,
    resource_key_field: str = "resource_key",
    resource_label_field: str = "resource",
    prefix: str = "resource",
) -> TableRow:
    label = str(row.get(resource_label_field) or "")
    key = str(row.get(resource_key_field) or "")
    row[f"{prefix}_label"] = label
    row[f"{prefix}_icon"] = resource_icon_url(key)
    row[f"{prefix}_title"] = f"{label} ({key})" if key and key != label else label
    return row


def resource_cell_slot(field: str = "resource", *, label_field: str | None = None) -> str:
    label = label_field or f"{field}_label"
    icon = f"{field}_icon"
    title = f"{field}_title"
    return f"""
    <q-td :props="props">
      <span v-if="props.row.{icon}" class="resource-glyph-cell" :aria-label="props.row.{title}">
        <img class="resource-glyph" :src="props.row.{icon}" :alt="props.row.{label}" />
        <span class="resource-glyph-fallback">{{{{ props.row.{label} }}}}</span>
        <q-tooltip class="return-fuel-tooltip" anchor="top middle" self="bottom middle" :offset="[0, 8]">
          <div class="return-fuel-tooltip-title">{{{{ props.row.{label} }}}}</div>
          <div class="return-fuel-tooltip-line">{{{{ props.row.resource_key }}}}</div>
        </q-tooltip>
      </span>
      <span v-else>{{{{ props.row.{field} }}}}</span>
    </q-td>
    """


@dataclass(frozen=True)
class TableModule:
    key: str
    label: str
    columns: list[TableColumn]
    build_rows: RowsBuilder
    row_key: str = "key"
    pagination: int = 20
    build_metrics: MetricsBuilder = no_metrics
    slots: dict[str, str] | None = None


@dataclass(frozen=True)
class InfoTooltipContent:
    title: str
    lines: tuple[str, ...]


def render_info_tooltip(
    title: str,
    lines: Sequence[str],
    *,
    icon: str = "info_outline",
    tooltip_class: str = "return-fuel-tooltip",
) -> None:
    with ui.element("span").classes("info-tooltip-trigger"):
        ui.icon(icon).classes("info-tooltip-icon")
        with ui.tooltip().classes(tooltip_class).props('anchor="top middle" self="bottom middle" :offset="[0, 8]"'):
            ui.label(title).classes("return-fuel-tooltip-title")
            for line in lines:
                ui.label(str(line)).classes("return-fuel-tooltip-line")
