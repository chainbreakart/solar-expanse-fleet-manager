from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .odin_save_parser import FStringRef

DOTNET_EPOCH = datetime(1, 1, 1)
FILETIME_EPOCH = datetime(1601, 1, 1)

ROUTE_ACTIVE_STATUSES = {"En route", "Cyclical"}
ROUTE_PLANNED_STATUSES = {"Planned"}
ROUTE_LOAD_STATUSES = ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES


def list_content(value: Any) -> list[Any]:
    if isinstance(value, dict):
        content = value.get("$rcontent")
        return content if isinstance(content, list) else []
    return value if isinstance(value, list) else []


def id_value(value: Any, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get("id", default)
    return default


def ref_value(value: Any) -> str:
    if isinstance(value, FStringRef):
        return value.value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("id") or value.get("ID")
        if raw is not None:
            return str(raw)
    return ""


def game_key(value: Any) -> str:
    raw = ref_value(value)
    return raw.rsplit("/", 1)[-1] if raw else ""


def friendly_key(raw: Any) -> str:
    key = game_key(raw)
    prefixes = (
        "id_resource_",
        "spacecraft_",
        "module_",
        "build_",
        "id_Rocket_",
        "research_",
    )
    for prefix in prefixes:
        if key.startswith(prefix):
            key = key[len(prefix) :]
            break
    return key.replace("_", " ").strip().title() if key else ""


def normalized_name(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


def dotnet_ticks_to_datetime(ticks: Any) -> datetime | None:
    if not isinstance(ticks, int):
        return None
    try:
        return DOTNET_EPOCH + timedelta(microseconds=ticks / 10)
    except OverflowError:
        return None


def filetime_to_datetime(ticks: Any) -> datetime | None:
    if not isinstance(ticks, int):
        return None
    try:
        return FILETIME_EPOCH + timedelta(microseconds=ticks / 10)
    except OverflowError:
        return None


def extract_datetime(value: Any) -> datetime | None:
    if isinstance(value, dict):
        type_name = str(value.get("$type") or "")
        if isinstance(value.get("value"), int):
            if "JsonDateTime" in type_name:
                return filetime_to_datetime(value["value"])
            return dotnet_ticks_to_datetime(value["value"])
        values = value.get("$values")
        if isinstance(values, list) and values:
            return dotnet_ticks_to_datetime(values[0])
    return None


def fmt_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def fmt_num(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value - round(value)) < 0.005:
        return f"{value:.0f}"
    return f"{value:.1f}"


def fmt_rate(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 10:
        return fmt_num(value)
    if abs(value) >= 0.1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.4f}".rstrip("0").rstrip(".")


def pct(part: float | None, total: float | None) -> str:
    if not isinstance(part, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return ""
    return f"{part / total * 100:.0f}%"


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def enum_name(value: Any, names: dict[int, str]) -> str:
    return names.get(value, str(value)) if isinstance(value, int) else ""
