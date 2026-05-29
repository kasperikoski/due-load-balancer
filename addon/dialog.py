"""Main dialog for Due Load Balancer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDate,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from aqt.utils import qconnect, showInfo, showWarning

from .anki_api import (
    DeckInfo,
    collection_today_due,
    find_due_review_card_ids,
    list_decks_with_due_counts,
    update_card_due_dates,
)
from .date_utils import (
    format_date_for_offset,
    human_start_label,
    offset_for_calendar_date,
    qt_date_format_from_config,
)
from .preview_dialog import PreviewDialog
from .qt_compat import (
    CANCEL_BUTTON,
    CHECKED,
    ITEM_IS_ENABLED,
    ITEM_IS_SELECTABLE,
    ITEM_IS_USER_CHECKABLE,
    PARTIALLY_CHECKED,
    UNCHECKED,
    USER_ROLE,
    YES_BUTTON,
)
from .scheduler import assign_cards_to_due_days, build_day_buckets


class DueReviewSpreaderDialog(QDialog):
    def __init__(self, parent, *, config: dict[str, Any], tr) -> None:
        super().__init__(parent)
        self.config = config
        self.tr = tr
        self._updating_tree = False
        self._updating_start_widgets = False
        self._deck_infos: list[DeckInfo] = []

        self.review_queue = int(config.get("advanced", {}).get("review_queue_value", 2))
        self.include_due_today = bool(config.get("behavior", {}).get("include_due_today", True))

        self.setWindowTitle(tr.t("dialog.title"))
        self.resize(
            int(config.get("ui", {}).get("window_width", 760)),
            int(config.get("ui", {}).get("window_height", 680)),
        )

        self._build_ui()
        self._load_decks()
        self._sync_start_date_from_spin()
        self._update_summary()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        heading = QLabel(f"<b>{self.tr.t('dialog.heading')}</b>")
        layout.addWidget(heading)

        description = QLabel(self.tr.t("dialog.description"))
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addWidget(self._build_deck_group())
        layout.addWidget(self._build_schedule_group())

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        buttons = QDialogButtonBox(self)
        self.preview_button = QPushButton(self.tr.t("buttons.open_preview"), self)
        self.spread_button = QPushButton(self.tr.t("buttons.spread_cards"), self)
        self.cancel_button = QPushButton(self.tr.t("buttons.cancel"), self)
        buttons.addButton(
            self.preview_button,
            QDialogButtonBox.ButtonRole.ActionRole
            if hasattr(QDialogButtonBox, "ButtonRole")
            else QDialogButtonBox.ActionRole,
        )
        buttons.addButton(
            self.spread_button,
            QDialogButtonBox.ButtonRole.AcceptRole
            if hasattr(QDialogButtonBox, "ButtonRole")
            else QDialogButtonBox.AcceptRole,
        )
        buttons.addButton(
            self.cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole
            if hasattr(QDialogButtonBox, "ButtonRole")
            else QDialogButtonBox.RejectRole,
        )

        qconnect(self.preview_button.clicked, self._open_preview)
        qconnect(self.spread_button.clicked, self._spread_cards)
        qconnect(self.cancel_button.clicked, self.reject)
        layout.addWidget(buttons)

    def _build_deck_group(self) -> QGroupBox:
        group = QGroupBox(self.tr.t("decks.group"), self)
        layout = QVBoxLayout(group)

        controls = QHBoxLayout()
        self.select_all_button = QPushButton(self.tr.t("decks.select_all_visible"), group)
        self.unselect_all_button = QPushButton(self.tr.t("decks.unselect_all"), group)
        self.show_only_due_checkbox = QCheckBox(self.tr.t("decks.show_only_due"), group)
        self.show_only_due_checkbox.setChecked(
            bool(self.config.get("defaults", {}).get("show_only_decks_with_due_reviews", True))
        )

        qconnect(self.select_all_button.clicked, self._select_all_visible_decks)
        qconnect(self.unselect_all_button.clicked, self._unselect_all_decks)
        qconnect(self.show_only_due_checkbox.toggled, self._load_decks)

        controls.addWidget(self.select_all_button)
        controls.addWidget(self.unselect_all_button)
        controls.addStretch(1)
        controls.addWidget(self.show_only_due_checkbox)
        layout.addLayout(controls)

        self.tree = QTreeWidget(group)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([self.tr.t("table.deck"), self.tr.t("table.due_reviews")])
        self.tree.setStyleSheet(
            """
            QHeaderView::section {
                padding-left: 6px;
                padding-right: 6px;
            }

            QTreeView::item {
                padding-left: 4px;
            }
            """
        )
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        qconnect(self.tree.itemChanged, self._on_tree_item_changed)
        layout.addWidget(self.tree)

        return group

    def _build_schedule_group(self) -> QGroupBox:
        group = QGroupBox(self.tr.t("settings.group"), self)
        layout = QVBoxLayout(group)

        date_range_heading = QLabel(f"<b>{self.tr.t('settings.date_range_heading')}</b>", group)
        layout.addWidget(date_range_heading)

        days_row = QHBoxLayout()
        days_label = QLabel(self.tr.t("settings.spread_over_days"), group)
        self.spread_days_spin = QSpinBox(group)
        self.spread_days_spin.setRange(1, 3650)
        self.spread_days_spin.setValue(int(self.config.get("defaults", {}).get("spread_over_days", 30)))
        qconnect(self.spread_days_spin.valueChanged, self._update_summary)
        days_row.addWidget(days_label)
        days_row.addWidget(self.spread_days_spin)
        days_row.addStretch(1)
        layout.addLayout(days_row)

        start_row = QHBoxLayout()
        self.start_after_spin = QSpinBox(group)
        self.start_after_spin.setRange(0, 3650)
        self.start_after_spin.setValue(int(self.config.get("defaults", {}).get("start_after_days", 1)))
        qconnect(self.start_after_spin.valueChanged, self._on_start_after_changed)

        self.start_date_edit = QDateEdit(group)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat(qt_date_format_from_config(self.config))
        self.start_date_edit.setMinimumDate(self._qdate_from_python_date(date.today()))
        self.start_date_edit.setMaximumDate(self._qdate_from_python_date(date.today() + timedelta(days=3650)))
        qconnect(self.start_date_edit.dateChanged, self._on_start_date_changed)

        start_row.addWidget(QLabel(self.tr.t("settings.days_from_today"), group))
        start_row.addWidget(self.start_after_spin)
        start_row.addSpacing(16)
        start_row.addWidget(QLabel(self.tr.t("settings.start_date"), group))
        start_row.addWidget(self.start_date_edit)
        start_row.addStretch(1)
        layout.addLayout(start_row)

        start_help = QLabel(self.tr.t("settings.start_after_help"), group)
        start_help.setWordWrap(True)
        layout.addWidget(start_help)

        distribution_heading = QLabel(f"<b>{self.tr.t('settings.distribution_heading')}</b>", group)
        distribution_heading.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(distribution_heading)

        distribution_row = QHBoxLayout()
        self.distribution_profile_combo = QComboBox(group)
        self._populate_distribution_profiles()

        self.curve_strength_spin = QDoubleSpinBox(group)
        self.curve_strength_spin.setRange(0.1, 5.0)
        self.curve_strength_spin.setSingleStep(0.1)
        self.curve_strength_spin.setDecimals(1)
        self.curve_strength_spin.setValue(float(self.config.get("defaults", {}).get("curve_strength", 1.0)))

        qconnect(self.distribution_profile_combo.currentIndexChanged, self._on_distribution_profile_changed)
        qconnect(self.curve_strength_spin.valueChanged, self._update_summary)

        distribution_row.addWidget(QLabel(self.tr.t("settings.distribution_profile"), group))
        distribution_row.addWidget(self.distribution_profile_combo)
        distribution_row.addSpacing(16)
        self.curve_strength_label = QLabel(self.tr.t("settings.curve_strength"), group)
        distribution_row.addWidget(self.curve_strength_label)
        distribution_row.addWidget(self.curve_strength_spin)
        distribution_row.addStretch(1)
        layout.addLayout(distribution_row)
        self._update_distribution_controls()

        distribution_help = QLabel(self.tr.t("settings.distribution_help"), group)
        distribution_help.setWordWrap(True)
        layout.addWidget(distribution_help)

        order_heading = QLabel(f"<b>{self.tr.t('settings.card_order_heading')}</b>", group)
        order_heading.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(order_heading)

        order_help = QLabel(self.tr.t("settings.card_order_help"), group)
        order_help.setWordWrap(True)
        layout.addWidget(order_help)

        self.shuffle_checkbox = QCheckBox(self.tr.t("settings.shuffle"), group)
        self.shuffle_checkbox.setChecked(
            bool(self.config.get("defaults", {}).get("shuffle_cards_before_spreading", False))
        )
        qconnect(self.shuffle_checkbox.toggled, self._update_summary)
        layout.addWidget(self.shuffle_checkbox)

        return group

    def _populate_distribution_profiles(self) -> None:
        current = str(self.config.get("defaults", {}).get("distribution_profile") or "even")
        profiles = [
            ("even", self.tr.t("distribution.even")),
            ("front_loaded", self.tr.t("distribution.front_loaded")),
            ("back_loaded", self.tr.t("distribution.back_loaded")),
            ("bell_curve", self.tr.t("distribution.bell_curve")),
        ]

        selected_index = 0
        for index, (value, label) in enumerate(profiles):
            self.distribution_profile_combo.addItem(label, value)
            if value == current:
                selected_index = index
        self.distribution_profile_combo.setCurrentIndex(selected_index)

    def _qdate_from_python_date(self, value: date):
        return QDate(value.year, value.month, value.day)

    def _python_date_from_qdate(self, value) -> date:
        return date(int(value.year()), int(value.month()), int(value.day()))

    def _on_start_after_changed(self, *_args) -> None:
        self._sync_start_date_from_spin()
        self._update_summary()

    def _on_start_date_changed(self, *_args) -> None:
        if self._updating_start_widgets:
            return

        self._updating_start_widgets = True
        selected_date = self._python_date_from_qdate(self.start_date_edit.date())
        self.start_after_spin.setValue(offset_for_calendar_date(selected_date))
        self._updating_start_widgets = False
        self._update_summary()

    def _sync_start_date_from_spin(self) -> None:
        if not hasattr(self, "start_date_edit") or self._updating_start_widgets:
            return

        self._updating_start_widgets = True
        start_date = date.today() + timedelta(days=int(self.start_after_spin.value()))
        self.start_date_edit.setDate(self._qdate_from_python_date(start_date))
        self._updating_start_widgets = False

    def _distribution_profile(self) -> str:
        value = self.distribution_profile_combo.currentData()
        return str(value or "even")

    def _distribution_label(self) -> str:
        return str(self.distribution_profile_combo.currentText())

    def _distribution_uses_strength(self) -> bool:
        return self._distribution_profile() != "even"

    def _distribution_text(self) -> str:
        if not self._distribution_uses_strength():
            return self._distribution_label()
        return self.tr.t(
            "distribution.with_strength",
            profile=self._distribution_label(),
            strength=f"{self._curve_strength():.1f}",
        )

    def _curve_strength(self) -> float:
        return float(self.curve_strength_spin.value())

    def _update_distribution_controls(self) -> None:
        show_strength = self._distribution_uses_strength()
        if hasattr(self, "curve_strength_label"):
            self.curve_strength_label.setVisible(show_strength)
        if hasattr(self, "curve_strength_spin"):
            self.curve_strength_spin.setVisible(show_strength)

    def _on_distribution_profile_changed(self, *_args) -> None:
        self._update_distribution_controls()
        self._update_summary()

    def _load_decks(self) -> None:
        self._deck_infos = list_decks_with_due_counts(
            review_queue=self.review_queue,
            include_due_today=self.include_due_today,
        )
        self._populate_tree()
        self._update_summary()

    def _populate_tree(self) -> None:
        self._updating_tree = True
        self.tree.clear()

        show_only_due = self.show_only_due_checkbox.isChecked()
        include_names = self._included_deck_names(show_only_due=show_only_due)
        items_by_path: dict[str, QTreeWidgetItem] = {}
        due_by_name = {deck.name: deck.due_review_count for deck in self._deck_infos}
        id_by_name = {deck.name: deck.deck_id for deck in self._deck_infos}

        for deck in self._deck_infos:
            if deck.name not in include_names:
                continue

            parts = deck.name.split("::")
            current_path = ""
            parent_item: QTreeWidgetItem | None = None
            for part in parts:
                current_path = part if not current_path else f"{current_path}::{part}"
                if current_path in items_by_path:
                    parent_item = items_by_path[current_path]
                    continue

                count = due_by_name.get(current_path, 0)
                item = QTreeWidgetItem([part, str(count)])
                item.setFlags(item.flags() | ITEM_IS_USER_CHECKABLE | ITEM_IS_ENABLED | ITEM_IS_SELECTABLE)
                item.setCheckState(0, UNCHECKED)
                if current_path in id_by_name:
                    item.setData(0, USER_ROLE, int(id_by_name[current_path]))
                else:
                    item.setData(0, USER_ROLE, None)

                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                items_by_path[current_path] = item
                parent_item = item

        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self._updating_tree = False

    def _included_deck_names(self, *, show_only_due: bool) -> set[str]:
        if not show_only_due:
            return {deck.name for deck in self._deck_infos}

        included: set[str] = set()
        for deck in self._deck_infos:
            if deck.due_review_count <= 0:
                continue
            parts = deck.name.split("::")
            current = ""
            for part in parts:
                current = part if not current else f"{current}::{part}"
                included.add(current)
        return included

    def _iter_tree_items(self):
        def walk(item: QTreeWidgetItem):
            yield item
            for index in range(item.childCount()):
                yield from walk(item.child(index))

        for top_index in range(self.tree.topLevelItemCount()):
            yield from walk(self.tree.topLevelItem(top_index))

    def _select_all_visible_decks(self) -> None:
        self._updating_tree = True
        for item in self._iter_tree_items():
            item.setCheckState(0, CHECKED)
        self._updating_tree = False
        self._update_summary()

    def _unselect_all_decks(self) -> None:
        self._updating_tree = True
        for item in self._iter_tree_items():
            item.setCheckState(0, UNCHECKED)
        self._updating_tree = False
        self._update_summary()

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating_tree or column != 0:
            return

        self._updating_tree = True
        state = item.checkState(0)
        if state in (CHECKED, UNCHECKED):
            self._set_children_state(item, state)
        self._update_parent_state(item.parent())
        self._updating_tree = False
        self._update_summary()

    def _set_children_state(self, item: QTreeWidgetItem, state) -> None:
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)
            self._set_children_state(child, state)

    def _update_parent_state(self, item: QTreeWidgetItem | None) -> None:
        if item is None:
            return

        checked = 0
        unchecked = 0
        partial = 0
        for index in range(item.childCount()):
            state = item.child(index).checkState(0)
            if state == CHECKED:
                checked += 1
            elif state == UNCHECKED:
                unchecked += 1
            else:
                partial += 1

        if partial or (checked and unchecked):
            item.setCheckState(0, PARTIALLY_CHECKED)
        elif checked:
            item.setCheckState(0, CHECKED)
        else:
            item.setCheckState(0, UNCHECKED)

        self._update_parent_state(item.parent())

    def _selected_deck_ids(self) -> list[int]:
        selected: list[int] = []
        for item in self._iter_tree_items():
            if item.checkState(0) != CHECKED:
                continue
            value = item.data(0, USER_ROLE)
            if value is not None:
                selected.append(int(value))
        return sorted(set(selected))

    def _selected_card_ids(self) -> list[int]:
        return find_due_review_card_ids(
            self._selected_deck_ids(),
            review_queue=self.review_queue,
            include_due_today=self.include_due_today,
            shuffle=self.shuffle_checkbox.isChecked(),
        )

    def _build_assignments_and_buckets(self):
        card_ids = self._selected_card_ids()
        today_due = collection_today_due()
        spread_over_days = int(self.spread_days_spin.value())
        start_after_days = int(self.start_after_spin.value())

        assignments = assign_cards_to_due_days(
            card_ids,
            today_due=today_due,
            spread_over_days=spread_over_days,
            start_after_days=start_after_days,
            distribution_profile=self._distribution_profile(),
            curve_strength=self._curve_strength(),
        )
        buckets = build_day_buckets(
            assignments,
            today_due=today_due,
            spread_over_days=spread_over_days,
            start_after_days=start_after_days,
        )
        return card_ids, assignments, buckets

    def _update_summary(self, *_args) -> None:
        if not hasattr(self, "summary_label"):
            return

        selected_deck_ids = self._selected_deck_ids() if hasattr(self, "tree") else []
        if not selected_deck_ids:
            self.summary_label.setText(self.tr.t("summary.no_decks"))
            return

        card_ids = find_due_review_card_ids(
            selected_deck_ids,
            review_queue=self.review_queue,
            include_due_today=self.include_due_today,
            shuffle=False,
        )
        if not card_ids:
            self.summary_label.setText(self.tr.t("summary.no_cards"))
            return

        assignments = assign_cards_to_due_days(
            card_ids,
            today_due=collection_today_due(),
            spread_over_days=int(self.spread_days_spin.value()),
            start_after_days=int(self.start_after_spin.value()),
            distribution_profile=self._distribution_profile(),
            curve_strength=self._curve_strength(),
        )
        buckets = build_day_buckets(
            assignments,
            today_due=collection_today_due(),
            spread_over_days=int(self.spread_days_spin.value()),
            start_after_days=int(self.start_after_spin.value()),
        )
        counts = [bucket.count for bucket in buckets]
        min_count = min(counts) if counts else 0
        max_count = max(counts) if counts else 0
        average = (sum(counts) / len(counts)) if counts else 0

        self.summary_label.setText(
            self.tr.t("summary.selected_cards", count=len(card_ids))
            + "\n"
            + self.tr.t(
                "summary.range",
                days=int(self.spread_days_spin.value()),
                start_label=self._start_label_with_date(),
                end_label=self._end_label_with_date(),
            )
            + "\n"
            + self.tr.t(
                "summary.distribution",
                distribution=self._distribution_text(),
            )
            + "\n"
            + self.tr.t(
                "summary.load",
                min_count=min_count,
                max_count=max_count,
                average=f"{average:.1f}",
            )
        )

    def _start_label_with_date(self) -> str:
        start_after = int(self.start_after_spin.value())
        label = human_start_label(start_after, self.tr)
        date_text = format_date_for_offset(start_after, self.config)
        return f"{label} ({date_text})"

    def _end_label_with_date(self) -> str:
        end_offset = int(self.start_after_spin.value()) + int(self.spread_days_spin.value()) - 1
        label = human_start_label(end_offset, self.tr)
        date_text = format_date_for_offset(end_offset, self.config)
        return f"{label} ({date_text})"

    def _validate_before_action(self) -> bool:
        if not self._selected_deck_ids():
            showWarning(self.tr.t("errors.no_decks"), title=self.tr.t("errors.title"))
            return False
        if int(self.spread_days_spin.value()) < 1:
            showWarning(self.tr.t("errors.invalid_days"), title=self.tr.t("errors.title"))
            return False
        if int(self.start_after_spin.value()) < 0:
            showWarning(self.tr.t("errors.invalid_start"), title=self.tr.t("errors.title"))
            return False
        return True

    def _open_preview(self) -> None:
        if not self._validate_before_action():
            return
        card_ids, _assignments, buckets = self._build_assignments_and_buckets()
        if not card_ids:
            showWarning(self.tr.t("errors.no_cards"), title=self.tr.t("errors.title"))
            return
        preview = PreviewDialog(
            self,
            config=self.config,
            tr=self.tr,
            buckets=buckets,
            distribution_text=self._distribution_text(),
        )
        preview.exec()

    def _spread_cards(self) -> None:
        if not self._validate_before_action():
            return

        card_ids, assignments, _buckets = self._build_assignments_and_buckets()
        if not card_ids:
            showWarning(self.tr.t("errors.no_cards"), title=self.tr.t("errors.title"))
            return

        if not self._confirm_if_needed(len(card_ids)):
            return

        try:
            mw.checkpoint(self.config.get("project", {}).get("display_name", "Due Load Balancer"))
            count = update_card_due_dates(assignments)
            mw.col.setMod()
            mw.reset()
        except Exception as exc:
            showWarning(self.tr.t("error.unexpected", error=str(exc)), title=self.tr.t("errors.title"))
            return

        showInfo(
            self.tr.t(
                "result.body",
                count=count,
                days=int(self.spread_days_spin.value()),
                start_label=self._start_label_with_date(),
            ),
            title=self.tr.t("result.title"),
        )
        self.accept()

    def _confirm_if_needed(self, count: int) -> bool:
        if not bool(self.config.get("behavior", {}).get("confirm_before_spreading", True)):
            return True

        body = self.tr.t(
            "confirm.body",
            count=count,
            days=int(self.spread_days_spin.value()),
            start_label=self._start_label_with_date(),
            distribution=self._distribution_text(),
        )
        threshold = int(self.config.get("behavior", {}).get("max_cards_warning_threshold", 1000))
        if count >= threshold:
            body += self.tr.t("confirm.large_warning")

        response = QMessageBox.question(
            self,
            self.tr.t("confirm.title"),
            body,
            YES_BUTTON | CANCEL_BUTTON,
            CANCEL_BUTTON,
        )
        return response == YES_BUTTON
