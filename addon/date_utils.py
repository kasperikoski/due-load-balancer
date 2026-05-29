"""Date helpers for preview labels."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def calendar_date_for_offset(offset_days: int) -> date:
    return date.today() + timedelta(days=offset_days)


def format_date_for_offset(offset_days: int, config: dict[str, Any]) -> str:
    date_format = str(config.get("ui", {}).get("date_format") or "%d.%m.%Y")
    return calendar_date_for_offset(offset_days).strftime(date_format)


def human_start_label(offset_days: int, tr) -> str:
    if offset_days == 0:
        return tr.t("preview.today")
    if offset_days == 1:
        return tr.t("preview.tomorrow")
    return tr.t("preview.in_days", days=offset_days)


def card_count_label(count: int, tr) -> str:
    if count == 1:
        return tr.t("preview.one_card")
    return tr.t("preview.cards", count=count)


def offset_for_calendar_date(calendar_date: date) -> int:
    return max(0, (calendar_date - date.today()).days)


def qt_date_format_from_config(config: dict[str, Any]) -> str:
    date_format = str(config.get("ui", {}).get("date_format") or "%d.%m.%Y")
    return (
        date_format.replace("%d", "dd")
        .replace("%m", "MM")
        .replace("%Y", "yyyy")
        .replace("%y", "yy")
    )
