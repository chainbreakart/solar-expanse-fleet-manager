from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
