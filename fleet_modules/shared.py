from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from nicegui import ui

from fleet_core.analysis import SaveAnalysis

TableRow = dict[str, object]
TableColumn = dict[str, object]
RowsBuilder = Callable[[SaveAnalysis], list[TableRow]]
MetricsBuilder = Callable[[SaveAnalysis, list[TableRow]], dict[str, str]]


def no_metrics(_analysis: SaveAnalysis, _rows: list[TableRow]) -> dict[str, str]:
    return {}


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
