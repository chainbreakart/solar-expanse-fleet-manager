from __future__ import annotations

from typing import Any

from .fact_model import CapacityMetrics, TechAdjustedValue
from .normalizer_utils import as_float, fmt_num, pct
from .spacecraft_reference import (
    CAPACITY_SEMANTICS_NORMAL,
    CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER,
)


def metric_percent(part: float | None, total: float | None) -> float | None:
    if not isinstance(part, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return None
    return float(part) / float(total) * 100.0


def metric_free(capacity: float | None, used: float) -> float | None:
    if not isinstance(capacity, (int, float)):
        return None
    return float(capacity) - used


def build_capacity_metrics(
    *,
    cargo_mass_used: float,
    cargo_capacity: float | None,
    raw_cargo_capacity: float | None,
    fuel_mass: float,
    fuel_capacity: float | None,
    raw_fuel_capacity: float | None,
    planned_total_fuel: float | None,
    optimal_fuel: float | None,
    life_support_loaded_value: float,
    capacity_source: str,
    tech_adjustment: TechAdjustedValue | None = None,
) -> CapacityMetrics:
    return CapacityMetrics(
        cargo_mass_used=cargo_mass_used,
        cargo_capacity=cargo_capacity,
        raw_cargo_capacity=raw_cargo_capacity if raw_cargo_capacity is not None else cargo_capacity,
        cargo_free=metric_free(cargo_capacity, cargo_mass_used),
        cargo_percent=metric_percent(cargo_mass_used, cargo_capacity),
        fuel_mass=fuel_mass,
        fuel_capacity=fuel_capacity,
        raw_fuel_capacity=raw_fuel_capacity if raw_fuel_capacity is not None else fuel_capacity,
        fuel_free=metric_free(fuel_capacity, fuel_mass),
        fuel_tank_percent=metric_percent(fuel_mass, fuel_capacity),
        planned_total_fuel=planned_total_fuel,
        optimal_fuel=optimal_fuel,
        saved_residual_or_onboard_fuel=fuel_mass,
        life_support_loaded=life_support_loaded_value,
        capacity_source=capacity_source,
        tech_adjustment=tech_adjustment,
    )


def fuel_plan_summary(required: Any, optimal: Any, onboard: float, fuel_capacity: float | None, status: str) -> str:
    pieces: list[str] = []
    required_f = as_float(required)
    optimal_f = as_float(optimal)
    if required_f is not None:
        pieces.append(f"planned total {fmt_num(required_f)}t")
    if optimal_f is not None and abs(optimal_f - (required_f or 0.0)) > 0.05:
        pieces.append(f"optimal {fmt_num(optimal_f)}t")
    fuel_label = "residual" if status in {"Planned", "En route"} and required_f is not None else "onboard"
    pieces.append(f"{fuel_label} {fmt_num(onboard)}t")
    fuel_pct = pct(onboard, fuel_capacity)
    if fuel_pct:
        pieces.append(f"tank {fuel_pct}")
    return "; ".join(pieces)


def capacity_summary(used: float, capacity: float | None) -> str:
    if capacity is None or capacity <= 0:
        return f"{fmt_num(used)}t"
    return f"{fmt_num(used)} / {fmt_num(capacity)}t ({pct(used, capacity)})"


def capacity_summary_for_semantics(used: float, capacity: float | None, semantics: str) -> str:
    if semantics == CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER:
        nominal = f"nominal {fmt_num(capacity)}t" if isinstance(capacity, (int, float)) and capacity > 0 else "nominal unknown"
        return f"{fmt_num(used)}t loaded; launch-limited upward, orbit-to-surface unlimited ({nominal})"
    return capacity_summary(used, capacity)


def movement_warnings(
    status: str,
    mission_cargo_mass: float,
    capacity: float | None,
    capacity_semantics: str = CAPACITY_SEMANTICS_NORMAL,
) -> str:
    warnings: list[str] = []
    if status in {"Arrived", "Canceled"}:
        return ""
    if capacity_semantics == CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER:
        warnings.append("payload container: launch-limited upward; orbit-to-surface delivery unlimited")
    return "; ".join(warnings)
