"""Preview window for the computed schedule."""

from __future__ import annotations

from typing import Any, Sequence

from aqt.qt import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from aqt.utils import qconnect

from .date_utils import card_count_label, format_date_for_offset, human_start_label
from .load_bar import LoadBarWidget
from .scheduler import DayBucket


class PreviewDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        config: dict[str, Any],
        tr,
        buckets: Sequence[DayBucket],
        distribution_text: str,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.tr = tr
        self.buckets = buckets
        self.distribution_text = distribution_text

        self.setWindowTitle(tr.t("preview.title"))
        self.resize(
            int(config.get("ui", {}).get("preview_window_width", 620)),
            int(config.get("ui", {}).get("preview_window_height", 560)),
        )

        layout = QVBoxLayout(self)

        heading = QLabel(f"<b>{tr.t('preview.heading')}</b>")
        layout.addWidget(heading)

        description = QLabel(tr.t("preview.description"))
        description.setWordWrap(True)
        layout.addWidget(description)

        self.summary_label = QLabel(self._summary_text())
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.load_help_label = QLabel(self.tr.t("preview.load_help"))
        self.load_help_label.setWordWrap(True)
        layout.addWidget(self.load_help_label)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [
                tr.t("preview.column_date"),
                tr.t("preview.column_starts"),
                tr.t("preview.column_cards"),
                tr.t("preview.column_load"),
            ]
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
            if hasattr(QAbstractItemView, "EditTrigger")
            else QAbstractItemView.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
            if hasattr(QAbstractItemView, "SelectionBehavior")
            else QAbstractItemView.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        stretch_mode = QHeaderView.ResizeMode.Stretch if hasattr(QHeaderView, "ResizeMode") else QHeaderView.Stretch
        resize_to_contents = (
            QHeaderView.ResizeMode.ResizeToContents
            if hasattr(QHeaderView, "ResizeMode")
            else QHeaderView.ResizeToContents
        )
        header.setSectionResizeMode(0, stretch_mode)
        header.setSectionResizeMode(1, stretch_mode)
        header.setSectionResizeMode(2, stretch_mode)
        header.setSectionResizeMode(3, resize_to_contents)
        self.table.setColumnWidth(3, 190)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(self)
        buttons.addButton(
            tr.t("buttons.close"),
            QDialogButtonBox.ButtonRole.AcceptRole
            if hasattr(QDialogButtonBox, "ButtonRole")
            else QDialogButtonBox.AcceptRole,
        )
        qconnect(buttons.accepted, self.accept)
        layout.addWidget(buttons)

        self._populate_table()

    def _summary_text(self) -> str:
        counts = [bucket.count for bucket in self.buckets]
        total = sum(counts)
        days = len(counts)
        min_count = min(counts) if counts else 0
        max_count = max(counts) if counts else 0
        average = (total / days) if days else 0

        return (
            self.tr.t(
                "preview.summary",
                total=total,
                days=days,
                min_count=min_count,
                max_count=max_count,
                average=f"{average:.1f}",
            )
            + "\n"
            + self.tr.t(
                "preview.distribution_summary",
                distribution=self.distribution_text,
            )
        )

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.buckets))
        max_count = max((bucket.count for bucket in self.buckets), default=0)

        for row, bucket in enumerate(self.buckets):
            ratio = (bucket.count / max_count) if max_count else 0.0
            percent = round(ratio * 100)
            label = f"{percent}%"

            self.table.setItem(row, 0, QTableWidgetItem(format_date_for_offset(bucket.offset_days, self.config)))
            self.table.setItem(row, 1, QTableWidgetItem(human_start_label(bucket.offset_days, self.tr)))
            self.table.setItem(row, 2, QTableWidgetItem(card_count_label(bucket.count, self.tr)))
            self.table.setCellWidget(row, 3, LoadBarWidget(ratio=ratio, label=label, parent=self.table))
            self.table.setRowHeight(row, 26)
