from __future__ import annotations

from .attention_board import MODULE as ATTENTION_BOARD
from .body_board import MODULE as BODY_BOARD
from .cargo_audit_board import MODULE as CARGO_AUDIT_BOARD
from .fleet_board import MODULE as FLEET_BOARD
from .people_transit import MODULE as PEOPLE_TRANSIT
from .production_audit_board import MODULE as PRODUCTION_AUDIT_BOARD
from .resource_knowledge_board import MODULE as RESOURCE_KNOWLEDGE_BOARD
from .return_fuel_board import MODULE as RETURN_FUEL_BOARD
from .route_board import MODULE as ROUTE_BOARD
from .shared import TableModule
from .technology_audit_board import MODULE as TECHNOLOGY_AUDIT_BOARD

MODULES: tuple[TableModule, ...] = (
    ATTENTION_BOARD,
    FLEET_BOARD,
    ROUTE_BOARD,
    BODY_BOARD,
    RESOURCE_KNOWLEDGE_BOARD,
    CARGO_AUDIT_BOARD,
    PRODUCTION_AUDIT_BOARD,
    TECHNOLOGY_AUDIT_BOARD,
    PEOPLE_TRANSIT,
    RETURN_FUEL_BOARD,
)

__all__ = ["MODULES", "TableModule"]
