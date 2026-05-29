"""Small custom Qt widget for preview load bars."""

from __future__ import annotations

from aqt.qt import QColor, QLinearGradient, QPainter, QRectF, QSize, Qt, QWidget


def _qt_align_center():
    alignment = getattr(Qt, "AlignmentFlag", None)
    if alignment is not None and hasattr(alignment, "AlignCenter"):
        return alignment.AlignCenter
    return Qt.AlignCenter


def _qt_antialiasing():
    render_hint = getattr(QPainter, "RenderHint", None)
    if render_hint is not None and hasattr(render_hint, "Antialiasing"):
        return render_hint.Antialiasing
    return QPainter.Antialiasing


class LoadBarWidget(QWidget):
    """Paint a compact, theme-friendly percentage bar for the preview table."""

    def __init__(self, *, ratio: float, label: str, parent=None) -> None:
        super().__init__(parent)
        self.ratio = min(1.0, max(0.0, float(ratio)))
        self.label = label
        self.setMinimumSize(150, 22)
        self.setToolTip(label)

    def sizeHint(self):
        return QSize(170, 24)

    def _fill_gradient(self, rect: QRectF) -> QLinearGradient:
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())

        if self.ratio >= 0.75:
            start = QColor(72, 149, 239)
            end = QColor(58, 117, 196)
        elif self.ratio >= 0.35:
            start = QColor(78, 186, 111)
            end = QColor(54, 151, 93)
        else:
            start = QColor(110, 193, 228)
            end = QColor(74, 156, 205)

        gradient.setColorAt(0.0, start)
        gradient.setColorAt(1.0, end)
        return gradient

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt method name
        painter = QPainter(self)
        painter.setRenderHint(_qt_antialiasing())

        outer = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        radius = 5.0

        background = QColor(232, 236, 241)
        border = QColor(198, 205, 214)
        painter.setPen(border)
        painter.setBrush(background)
        painter.drawRoundedRect(outer, radius, radius)

        if self.ratio > 0:
            fill_width = max(3.0, outer.width() * self.ratio)
            fill = QRectF(outer.left(), outer.top(), fill_width, outer.height())
            painter.setPen(Qt.PenStyle.NoPen if hasattr(Qt, "PenStyle") else Qt.NoPen)
            painter.setBrush(self._fill_gradient(fill))
            painter.drawRoundedRect(fill, radius, radius)

        painter.setPen(self.palette().text().color())
        painter.drawText(self.rect(), _qt_align_center(), self.label)
