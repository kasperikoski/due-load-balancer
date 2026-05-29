"""Small adapter around Anki's collection API.

All direct Anki access is kept here so the UI stays readable and the pure
scheduler can be tested independently.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterable

from aqt import mw


@dataclass(frozen=True)
class DeckInfo:
    deck_id: int
    name: str
    due_review_count: int


def collection_today_due() -> int:
    """Return Anki's integer due value for today."""
    return int(mw.col.sched.today)


def _deck_name_and_id(deck: Any) -> tuple[str, int] | None:
    # Modern Anki returns objects with .name and .id from all_names_and_ids().
    name = getattr(deck, "name", None)
    deck_id = getattr(deck, "id", None)

    # Older/fallback data may be dict-like.
    if name is None and isinstance(deck, dict):
        name = deck.get("name")
    if deck_id is None and isinstance(deck, dict):
        deck_id = deck.get("id")

    if name is None or deck_id is None:
        return None
    return str(name), int(deck_id)


def list_decks_with_due_counts(*, review_queue: int, include_due_today: bool) -> list[DeckInfo]:
    """List decks and the number of direct due review cards in each deck."""
    today = collection_today_due()
    comparison = "<=" if include_due_today else "<"

    try:
        raw_decks = mw.col.decks.all_names_and_ids()
    except Exception:
        raw_decks = mw.col.decks.all()

    decks: list[DeckInfo] = []
    for raw in raw_decks:
        parsed = _deck_name_and_id(raw)
        if parsed is None:
            continue
        name, deck_id = parsed
        count = int(
            mw.col.db.scalar(
                f"select count() from cards where did = ? and queue = ? and due {comparison} ?",
                deck_id,
                review_queue,
                today,
            )
            or 0
        )
        decks.append(DeckInfo(deck_id=deck_id, name=name, due_review_count=count))

    decks.sort(key=lambda item: item.name.lower())
    return decks


def find_due_review_card_ids(
    deck_ids: Iterable[int],
    *,
    review_queue: int,
    include_due_today: bool,
    shuffle: bool,
) -> list[int]:
    """Find due review cards in the selected decks.

    New cards and learning cards are ignored because their queues are not the
    review queue.
    """
    ids = [int(deck_id) for deck_id in deck_ids]
    if not ids:
        return []

    placeholders = ",".join("?" for _ in ids)
    today = collection_today_due()
    comparison = "<=" if include_due_today else "<"
    sql = (
        f"select id from cards "
        f"where did in ({placeholders}) and queue = ? and due {comparison} ? "
        f"order by due asc, id asc"
    )
    params: list[Any] = [*ids, review_queue, today]
    card_ids = [int(card_id) for card_id in mw.col.db.list(sql, *params)]

    if shuffle:
        random.shuffle(card_ids)

    return card_ids


def update_card_due_dates(assignments) -> int:
    """Reschedule cards using Anki's native Set Due Date mechanism.

    Here we intentionally use mw.col.sched.set_due_date() instead of directly
    editing card.due or saving a modified Card object.

    The input assignments contain absolute Anki due-day numbers. Anki's native
    Set Due Date API expects an offset from today, such as "0", "1", or "30".

    Important:
    - We do not append "!".
    - For review cards, Set Due Date without "!" changes the due date but keeps
      the current interval.
    - Anki records the operation transparently as a reschedule event.
    """
    today_due = collection_today_due()
    grouped_card_ids: dict[int, list[int]] = {}

    for assignment in assignments:
        offset_days = int(assignment.due_day) - today_due
        grouped_card_ids.setdefault(offset_days, []).append(int(assignment.card_id))

    updated = 0

    for offset_days, card_ids in grouped_card_ids.items():
        # Use Anki's native Set Due Date format.
        # Do not use "!" here, because "!" would also change the interval.
        mw.col.sched.set_due_date(card_ids, str(offset_days))
        updated += len(card_ids)

    return updated