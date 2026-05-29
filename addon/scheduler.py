"""Pure scheduling logic.

This module does not import Anki or Qt, so it can be unit-tested outside Anki.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


DISTRIBUTION_PROFILE_EVEN = "even"
DISTRIBUTION_PROFILE_FRONT_LOADED = "front_loaded"
DISTRIBUTION_PROFILE_BACK_LOADED = "back_loaded"
DISTRIBUTION_PROFILE_BELL_CURVE = "bell_curve"

DISTRIBUTION_PROFILES = {
    DISTRIBUTION_PROFILE_EVEN,
    DISTRIBUTION_PROFILE_FRONT_LOADED,
    DISTRIBUTION_PROFILE_BACK_LOADED,
    DISTRIBUTION_PROFILE_BELL_CURVE,
}


@dataclass(frozen=True)
class DayBucket:
    day_index: int
    offset_days: int
    due_day: int
    count: int


@dataclass(frozen=True)
class CardAssignment:
    card_id: int
    day_index: int
    offset_days: int
    due_day: int


def normalize_distribution_profile(profile: str | None) -> str:
    """Return a safe distribution profile name."""
    normalized = str(profile or DISTRIBUTION_PROFILE_EVEN).strip().lower()
    if normalized in DISTRIBUTION_PROFILES:
        return normalized
    return DISTRIBUTION_PROFILE_EVEN


def normalize_curve_strength(value: float | int | str | None) -> float:
    """Return a safe curve strength value.

    1.0 is the normal strength. Higher values make front-loaded,
    back-loaded, and bell-curve profiles more pronounced.
    """
    try:
        strength = float(value)
    except Exception:
        strength = 1.0
    return min(5.0, max(0.1, strength))


def _day_index_for_position(position: int, total_cards: int, total_days: int) -> int:
    """Return an evenly spaced day index for a card position.

    For many cards, this creates an almost equal number of cards per day.
    For fewer cards than days, this spreads the cards across the full range
    instead of putting them all at the beginning.
    """
    if total_days <= 1 or total_cards <= 1:
        return 0
    return round(position * (total_days - 1) / (total_cards - 1))


def _profile_weight(day_index: int, total_days: int, profile: str, strength: float) -> float:
    if total_days <= 1 or profile == DISTRIBUTION_PROFILE_EVEN:
        return 1.0

    x = day_index / (total_days - 1)
    floor = 0.05

    if profile == DISTRIBUTION_PROFILE_FRONT_LOADED:
        return ((1.0 - x) ** strength) + floor

    if profile == DISTRIBUTION_PROFILE_BACK_LOADED:
        return (x**strength) + floor

    if profile == DISTRIBUTION_PROFILE_BELL_CURVE:
        distance_from_center = abs(x - 0.5) * 2.0
        return ((1.0 - distance_from_center) ** strength) + floor

    return 1.0


def _largest_remainder_capacities(total_cards: int, weights: Sequence[float]) -> list[int]:
    """Split cards by weights while preserving the exact total."""
    if not weights:
        return []

    total_weight = sum(weights) or 1.0
    raw_capacities = [(weight / total_weight) * total_cards for weight in weights]
    capacities = [int(raw) for raw in raw_capacities]

    remaining = total_cards - sum(capacities)
    fractional_order = sorted(
        range(len(weights)),
        key=lambda index: (raw_capacities[index] - capacities[index], -index),
        reverse=True,
    )

    for index in fractional_order[:remaining]:
        capacities[index] += 1

    return capacities


def build_weighted_day_capacities(
    total_cards: int,
    total_days: int,
    *,
    distribution_profile: str = DISTRIBUTION_PROFILE_EVEN,
    curve_strength: float = 1.0,
) -> list[int]:
    """Return how many cards should be assigned to each day.

    When there are enough cards, every day receives at least one card before
    the selected curve is applied to the remaining cards. This keeps strong
    curves from creating surprising zero-card days at the start or end of the
    selected range.
    """
    if total_days < 1:
        raise ValueError("total_days must be at least 1")
    if total_cards < 0:
        raise ValueError("total_cards must not be negative")

    if total_cards == 0:
        return [0 for _ in range(total_days)]

    profile = normalize_distribution_profile(distribution_profile)
    strength = normalize_curve_strength(curve_strength)
    weights = [
        _profile_weight(day_index, total_days, profile, strength)
        for day_index in range(total_days)
    ]

    if total_cards >= total_days:
        capacities = [1 for _ in range(total_days)]
        remaining = total_cards - total_days
        extras = _largest_remainder_capacities(remaining, weights)
        return [base + extra for base, extra in zip(capacities, extras, strict=True)]

    return _largest_remainder_capacities(total_cards, weights)


def _weighted_sparse_day_indices(total_cards: int, total_days: int, profile: str, strength: float) -> list[int]:
    """Return day indices for sparse schedules where cards are fewer than days."""
    if total_cards <= 0:
        return []
    if profile == DISTRIBUTION_PROFILE_EVEN:
        return [_day_index_for_position(position, total_cards, total_days) for position in range(total_cards)]

    weights = [
        _profile_weight(day_index, total_days, profile, strength)
        for day_index in range(total_days)
    ]
    total_weight = sum(weights) or 1.0
    cumulative: list[float] = []
    running = 0.0
    for weight in weights:
        running += weight / total_weight
        cumulative.append(running)

    day_indices: list[int] = []
    search_start = 0
    for position in range(total_cards):
        target = (position + 0.5) / total_cards
        for index in range(search_start, total_days):
            if cumulative[index] >= target:
                day_indices.append(index)
                search_start = index
                break
        else:
            day_indices.append(total_days - 1)

    return day_indices


def assign_cards_to_due_days(
    card_ids: Sequence[int],
    *,
    today_due: int,
    spread_over_days: int,
    start_after_days: int,
    distribution_profile: str = DISTRIBUTION_PROFILE_EVEN,
    curve_strength: float = 1.0,
) -> list[CardAssignment]:
    """Assign cards to due days without changing the card order.

    Args:
        card_ids: Card IDs in the order they should be assigned.
        today_due: Anki's integer due value for today.
        spread_over_days: Number of calendar days to use. Minimum 1.
        start_after_days: 0 means today, 1 means tomorrow, etc.
        distribution_profile: How cards should be distributed across the range.
        curve_strength: How strongly non-even profiles should be shaped.
    """
    if spread_over_days < 1:
        raise ValueError("spread_over_days must be at least 1")
    if start_after_days < 0:
        raise ValueError("start_after_days must be at least 0")

    profile = normalize_distribution_profile(distribution_profile)
    total_cards = len(card_ids)
    assignments: list[CardAssignment] = []

    if total_cards < spread_over_days:
        day_indices = _weighted_sparse_day_indices(
            total_cards,
            spread_over_days,
            profile,
            normalize_curve_strength(curve_strength),
        )
        for card_id, day_index in zip(card_ids, day_indices, strict=True):
            offset_days = start_after_days + day_index
            due_day = today_due + offset_days
            assignments.append(
                CardAssignment(
                    card_id=int(card_id),
                    day_index=day_index,
                    offset_days=offset_days,
                    due_day=due_day,
                )
            )
        return assignments

    if profile == DISTRIBUTION_PROFILE_EVEN and total_cards < spread_over_days:
        for position, card_id in enumerate(card_ids):
            day_index = _day_index_for_position(position, total_cards, spread_over_days)
            offset_days = start_after_days + day_index
            due_day = today_due + offset_days
            assignments.append(
                CardAssignment(
                    card_id=int(card_id),
                    day_index=day_index,
                    offset_days=offset_days,
                    due_day=due_day,
                )
            )
        return assignments

    capacities = build_weighted_day_capacities(
        total_cards,
        spread_over_days,
        distribution_profile=profile,
        curve_strength=curve_strength,
    )

    position = 0
    for day_index, capacity in enumerate(capacities):
        for _ in range(capacity):
            if position >= total_cards:
                break
            offset_days = start_after_days + day_index
            due_day = today_due + offset_days
            assignments.append(
                CardAssignment(
                    card_id=int(card_ids[position]),
                    day_index=day_index,
                    offset_days=offset_days,
                    due_day=due_day,
                )
            )
            position += 1

    while position < total_cards:
        day_index = spread_over_days - 1
        offset_days = start_after_days + day_index
        due_day = today_due + offset_days
        assignments.append(
            CardAssignment(
                card_id=int(card_ids[position]),
                day_index=day_index,
                offset_days=offset_days,
                due_day=due_day,
            )
        )
        position += 1

    return assignments


def build_day_buckets(
    assignments: Iterable[CardAssignment],
    *,
    today_due: int,
    spread_over_days: int,
    start_after_days: int,
) -> list[DayBucket]:
    """Build one preview bucket per day in the selected range."""
    counter = Counter(assignment.day_index for assignment in assignments)
    buckets: list[DayBucket] = []

    for day_index in range(spread_over_days):
        offset_days = start_after_days + day_index
        buckets.append(
            DayBucket(
                day_index=day_index,
                offset_days=offset_days,
                due_day=today_due + offset_days,
                count=counter.get(day_index, 0),
            )
        )

    return buckets
