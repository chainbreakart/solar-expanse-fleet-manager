from __future__ import annotations

from typing import Any

from .fact_model import ObjectFact, ProductionBalanceMetric, ResourceStockFact, TechReferenceCatalog, TechUnlockFact
from .technology_adjustments import summed_percent_multiplier, unlocked_reference_modifiers

PRODUCTION_RUNWAY_WARNING_DAYS = 730
PRODUCTION_RUNWAY_URGENT_DAYS = 365
PRODUCTION_RUNWAY_CRITICAL_DAYS = 183


def list_content(value: Any) -> list[Any]:
    if isinstance(value, dict):
        content = value.get("$rcontent")
        return content if isinstance(content, list) else []
    return value if isinstance(value, list) else []


def id_value(value: Any, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get("id", default)
    return default


def game_key(value: Any) -> str:
    raw = id_value(value, "")
    return str(raw) if raw is not None else ""


def friendly_key(raw: Any) -> str:
    key = game_key(raw)
    if not key:
        return ""
    for prefix in ("id_resource_", "id_", "resource_", "module_", "building_", "spacecraft_"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
            break
    return key.replace("_", " ").title()


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def object_label(object_id: Any, names: dict[int, str]) -> str:
    if isinstance(object_id, int):
        name = names.get(object_id, "")
        if name:
            return f"{name} ({object_id})"
        return f"Object {object_id}"
    return ""


def build_resource_stock_facts(
    save: dict[str, Any],
    object_names: dict[int, str],
    resources: dict[str, str],
    included_companies: set[str] | None = None,
) -> list[ResourceStockFact]:
    facts: list[ResourceStockFact] = []
    for row in list_content(save.get("objectInfoDatas")):
        if not isinstance(row, dict):
            continue
        company = str(id_value(row.get("companyId"), ""))
        if included_companies is not None and company not in included_companies:
            continue
        object_id = row.get("id") if isinstance(row.get("id"), int) else None
        if object_id is None:
            continue
        for resource in list_content(row.get("listRowResourcesData")):
            if not isinstance(resource, dict):
                continue
            resource_key = game_key(resource.get("resourceTypeIDSave"))
            if not resource_key:
                continue
            value = as_float(resource.get("value")) or 0.0
            intake = as_float(resource.get("inTake")) or 0.0
            outtake = as_float(resource.get("outTake")) or 0.0
            if abs(value) < 0.0001 and abs(intake) < 0.0001 and abs(outtake) < 0.0001:
                continue
            facts.append(
                ResourceStockFact(
                    company=company,
                    object_id=object_id,
                    object_label=object_label(object_id, object_names),
                    resource_key=resource_key,
                    resource_name=resources.get(resource_key) or friendly_key(resource_key) or resource_key,
                    value=value,
                    intake=intake,
                    outtake=outtake,
                    source="company_stock",
                )
            )
    return sorted(facts, key=lambda fact: (fact.company, fact.object_label, fact.resource_name))


def production_runway_days(stock: float, net_per_day: float) -> float | None:
    if net_per_day >= 0:
        return None
    if stock <= 0:
        return 0.0
    return stock / abs(net_per_day)


def production_status(stock: float, net_per_day: float) -> tuple[str, str]:
    if net_per_day >= 0:
        return "Stable", "non-negative net flow"
    if stock <= 0:
        return "Critical", "stock is empty and net flow is negative"
    runway_days = stock / abs(net_per_day)
    if runway_days < PRODUCTION_RUNWAY_CRITICAL_DAYS:
        return "Critical", "less than half a year of stock remaining"
    if runway_days < PRODUCTION_RUNWAY_URGENT_DAYS:
        return "Urgent", "less than one year of stock remaining"
    if runway_days < PRODUCTION_RUNWAY_WARNING_DAYS:
        return "Warning", "less than two years of stock remaining"
    return "Monitor", "negative flow, but more than two years of stock remain"


def build_production_balance_metrics(
    resource_stock_facts: list[ResourceStockFact],
    object_facts: dict[int, ObjectFact],
    technology_reference: TechReferenceCatalog | None = None,
    tech_unlock_facts: list[TechUnlockFact] | None = None,
) -> list[ProductionBalanceMetric]:
    metrics: list[ProductionBalanceMetric] = []
    for fact in resource_stock_facts:
        net = fact.intake - fact.outtake
        runway_days = production_runway_days(fact.value, net)
        status, status_basis = production_status(fact.value, net)
        object_fact = object_facts.get(fact.object_id)
        object_type = object_fact.object_type if object_fact else ""
        production_tech = None
        if fact.resource_key == "id_resource_supply":
            production_tech = summed_percent_multiplier(
                unlocked_reference_modifiers(technology_reference, tech_unlock_facts, fact.company),
                modifier_type="production_efficiency_percent",
                target_type="facility",
                target_key="build_farm",
            )
        metrics.append(
            ProductionBalanceMetric(
                production_key=f"{fact.company}:{fact.object_id}:{fact.resource_key}",
                company=fact.company,
                object_id=fact.object_id,
                object_label=fact.object_label,
                object_type=object_type,
                resource_key=fact.resource_key,
                resource_name=fact.resource_name,
                stock=fact.value,
                intake_per_day=fact.intake,
                outtake_per_day=fact.outtake,
                net_per_day=net,
                runway_days=runway_days,
                status=status,
                status_basis=status_basis,
                source=f"{fact.source}; tech {production_tech.basis}" if production_tech else fact.source,
                tech_adjustment=production_tech,
            )
        )

    status_rank = {"Critical": 0, "Urgent": 1, "Warning": 2, "Monitor": 3, "Stable": 4}
    return sorted(
        metrics,
        key=lambda metric: (
            status_rank.get(metric.status, 9),
            metric.runway_days if metric.runway_days is not None else float("inf"),
            metric.object_label,
            metric.resource_name,
        ),
    )
