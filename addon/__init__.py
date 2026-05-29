"""
Due Load Balancer for Anki.
"""

from __future__ import annotations

from aqt import mw
from aqt.qt import QAction
from aqt.utils import qconnect

from .config import load_config
from .i18n import Translator
from .dialog import DueReviewSpreaderDialog


def open_due_load_balancer() -> None:
    """Open the main scheduling dialog."""
    if mw.col is None:
        return

    config = load_config()
    tr = Translator(config)
    dialog = DueReviewSpreaderDialog(parent=mw, config=config, tr=tr)
    dialog.exec()


def register_menu_action() -> None:
    """Register the add-on in Anki's Tools menu."""
    config = load_config()
    tr = Translator(config)

    menu_label_override = str(config.get("project", {}).get("menu_label_override") or "").strip()
    menu_label = menu_label_override or tr.t("menu.spread_due_reviews")

    action = QAction(menu_label, mw)
    qconnect(action.triggered, open_due_load_balancer)
    mw.form.menuTools.addAction(action)


register_menu_action()
