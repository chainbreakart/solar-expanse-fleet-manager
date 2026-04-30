from __future__ import annotations

from .body_board import MODULE as BODY_BOARD
from .fleet_board import MODULE as FLEET_BOARD
from .people_transit import MODULE as PEOPLE_TRANSIT
from .return_fuel_board import MODULE as RETURN_FUEL_BOARD
from .route_board import MODULE as ROUTE_BOARD
from .shared import TableModule

MODULES: tuple[TableModule, ...] = (
    FLEET_BOARD,
    ROUTE_BOARD,
    BODY_BOARD,
    PEOPLE_TRANSIT,
    RETURN_FUEL_BOARD,
)

__all__ = ["MODULES", "TableModule"]
