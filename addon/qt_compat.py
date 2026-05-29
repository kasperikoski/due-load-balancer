"""Compatibility helpers for Qt enums across Anki/PyQt versions."""

from __future__ import annotations

from aqt.qt import Qt, QMessageBox


def _enum_value(enum_group_name: str, value_name: str, fallback_name: str):
    group = getattr(Qt, enum_group_name, None)
    if group is not None and hasattr(group, value_name):
        return getattr(group, value_name)
    return getattr(Qt, fallback_name)


CHECKED = _enum_value("CheckState", "Checked", "Checked")
UNCHECKED = _enum_value("CheckState", "Unchecked", "Unchecked")
PARTIALLY_CHECKED = _enum_value("CheckState", "PartiallyChecked", "PartiallyChecked")
USER_ROLE = _enum_value("ItemDataRole", "UserRole", "UserRole")
ITEM_IS_USER_CHECKABLE = _enum_value("ItemFlag", "ItemIsUserCheckable", "ItemIsUserCheckable")
ITEM_IS_ENABLED = _enum_value("ItemFlag", "ItemIsEnabled", "ItemIsEnabled")
ITEM_IS_SELECTABLE = _enum_value("ItemFlag", "ItemIsSelectable", "ItemIsSelectable")


def message_box_button(name: str):
    standard_button = getattr(QMessageBox, "StandardButton", None)
    if standard_button is not None and hasattr(standard_button, name):
        return getattr(standard_button, name)
    return getattr(QMessageBox, name)


YES_BUTTON = message_box_button("Yes")
CANCEL_BUTTON = message_box_button("Cancel")
OK_BUTTON = message_box_button("Ok")
