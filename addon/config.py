"""Configuration loading and validation.

Anki can expose config.json through Tools -> Add-ons -> Config. We use
mw.addonManager.getConfig(__name__) when possible and then merge the result
with safe defaults, so missing keys do not break the add-on.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from aqt import mw

from .constants import ADDON_VERSION, DEFAULT_LANGUAGE, DEFAULT_PROJECT_NAME, REVIEW_QUEUE


DEFAULT_CONFIG: dict[str, Any] = {
    "project": {
        "display_name": DEFAULT_PROJECT_NAME,
        "version": ADDON_VERSION,
        "menu_label_override": "",
    },
    "ui": {
        "language": DEFAULT_LANGUAGE,
        "window_width": 760,
        "window_height": 780,
        "preview_window_width": 620,
        "preview_window_height": 560,
        "date_format": "%d.%m.%Y",
    },
    "defaults": {
        "spread_over_days": 30,
        "start_after_days": 1,
        "shuffle_cards_before_spreading": False,
        "distribution_profile": "even",
        "curve_strength": 1.0,
        "show_only_decks_with_due_reviews": True,
    },
    "behavior": {
        "confirm_before_spreading": True,
        "include_due_today": True,
        "max_cards_warning_threshold": 1000,
    },
    "advanced": {
        "review_queue_value": REVIEW_QUEUE,
    },
}


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any] | None) -> dict[str, Any]:
    result = copy.deepcopy(base)
    if not override:
        return result

    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_local_config_file() -> dict[str, Any] | None:
    path = Path(__file__).with_name("config.json")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def _coerce_int(value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        coerced = int(value)
    except Exception:
        coerced = default
    if minimum is not None:
        coerced = max(minimum, coerced)
    if maximum is not None:
        coerced = min(maximum, coerced)
    return coerced


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _coerce_float(value: Any, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        coerced = float(value)
    except Exception:
        coerced = default
    if minimum is not None:
        coerced = max(minimum, coerced)
    if maximum is not None:
        coerced = min(maximum, coerced)
    return coerced


def _coerce_distribution_profile(value: Any) -> str:
    normalized = str(value or "even").strip().lower()
    allowed = {"even", "front_loaded", "back_loaded", "bell_curve"}
    if normalized in allowed:
        return normalized
    return "even"


def load_config() -> dict[str, Any]:
    """Load user-editable configuration with safe defaults."""
    raw: dict[str, Any] | None = None

    try:
        raw = mw.addonManager.getConfig(__name__)
    except Exception:
        raw = None

    if raw is None:
        raw = _read_local_config_file()

    config = _deep_merge(DEFAULT_CONFIG, raw)

    # Gentle validation. Values are intentionally permissive so users can edit
    # config.json without making the add-on unusable.
    config["project"]["display_name"] = str(
        config.get("project", {}).get("display_name") or DEFAULT_PROJECT_NAME
    )
    config["project"]["version"] = str(config.get("project", {}).get("version") or ADDON_VERSION)
    config["project"]["menu_label_override"] = str(
        config.get("project", {}).get("menu_label_override") or ""
    )

    config["ui"]["language"] = str(config.get("ui", {}).get("language") or DEFAULT_LANGUAGE)
    config["ui"]["window_width"] = _coerce_int(config["ui"].get("window_width"), 760, minimum=520)
    config["ui"]["window_height"] = _coerce_int(config["ui"].get("window_height"), 780, minimum=420)
    config["ui"]["preview_window_width"] = _coerce_int(
        config["ui"].get("preview_window_width"), 620, minimum=480
    )
    config["ui"]["preview_window_height"] = _coerce_int(
        config["ui"].get("preview_window_height"), 560, minimum=360
    )
    config["ui"]["date_format"] = str(config["ui"].get("date_format") or "%d.%m.%Y")

    config["defaults"]["spread_over_days"] = _coerce_int(
        config["defaults"].get("spread_over_days"), 30, minimum=1
    )
    config["defaults"]["start_after_days"] = _coerce_int(
        config["defaults"].get("start_after_days"), 1, minimum=0
    )
    config["defaults"]["shuffle_cards_before_spreading"] = _coerce_bool(
        config["defaults"].get("shuffle_cards_before_spreading"), False
    )
    config["defaults"]["distribution_profile"] = _coerce_distribution_profile(
        config["defaults"].get("distribution_profile")
    )
    config["defaults"]["curve_strength"] = _coerce_float(
        config["defaults"].get("curve_strength"), 1.0, minimum=0.1, maximum=5.0
    )
    config["defaults"]["show_only_decks_with_due_reviews"] = _coerce_bool(
        config["defaults"].get("show_only_decks_with_due_reviews"), True
    )

    config["behavior"]["confirm_before_spreading"] = _coerce_bool(
        config["behavior"].get("confirm_before_spreading"), True
    )
    config["behavior"]["include_due_today"] = _coerce_bool(
        config["behavior"].get("include_due_today"), True
    )
    config["behavior"]["max_cards_warning_threshold"] = _coerce_int(
        config["behavior"].get("max_cards_warning_threshold"), 1000, minimum=1
    )
    config["advanced"]["review_queue_value"] = _coerce_int(
        config["advanced"].get("review_queue_value"), REVIEW_QUEUE, minimum=0
    )

    return config
