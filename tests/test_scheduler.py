from scheduler import assign_cards_to_due_days, build_day_buckets, build_weighted_day_capacities


def test_even_distribution_when_cards_exceed_days():
    card_ids = list(range(400))
    assignments = assign_cards_to_due_days(
        card_ids,
        today_due=1000,
        spread_over_days=100,
        start_after_days=1,
    )
    buckets = build_day_buckets(
        assignments,
        today_due=1000,
        spread_over_days=100,
        start_after_days=1,
    )

    assert len(assignments) == 400
    assert sum(bucket.count for bucket in buckets) == 400
    assert min(bucket.count for bucket in buckets) >= 3
    assert max(bucket.count for bucket in buckets) <= 5
    assert assignments[0].due_day == 1001
    assert assignments[-1].due_day == 1100


def test_few_cards_are_spread_across_full_range():
    assignments = assign_cards_to_due_days(
        [10, 20, 30],
        today_due=200,
        spread_over_days=30,
        start_after_days=0,
    )

    assert [assignment.day_index for assignment in assignments] == [0, 14, 29]
    assert [assignment.due_day for assignment in assignments] == [200, 214, 229]


def test_start_after_zero_means_today():
    assignments = assign_cards_to_due_days(
        [1],
        today_due=50,
        spread_over_days=10,
        start_after_days=0,
    )

    assert assignments[0].due_day == 50


def test_start_after_one_means_tomorrow():
    assignments = assign_cards_to_due_days(
        [1],
        today_due=50,
        spread_over_days=10,
        start_after_days=1,
    )

    assert assignments[0].due_day == 51

def test_assignments_preserve_input_order():
    card_ids = [30, 10, 20]
    assignments = assign_cards_to_due_days(
        card_ids,
        today_due=100,
        spread_over_days=3,
        start_after_days=1,
    )

    assert [assignment.card_id for assignment in assignments] == card_ids


def test_back_loaded_distribution_places_more_cards_later():
    card_ids = list(range(100))
    assignments = assign_cards_to_due_days(
        card_ids,
        today_due=100,
        spread_over_days=10,
        start_after_days=1,
        distribution_profile="back_loaded",
        curve_strength=2.0,
    )
    buckets = build_day_buckets(
        assignments,
        today_due=100,
        spread_over_days=10,
        start_after_days=1,
    )

    assert buckets[-1].count > buckets[0].count


def test_front_loaded_distribution_places_more_cards_earlier():
    card_ids = list(range(100))
    assignments = assign_cards_to_due_days(
        card_ids,
        today_due=100,
        spread_over_days=10,
        start_after_days=1,
        distribution_profile="front_loaded",
        curve_strength=2.0,
    )
    buckets = build_day_buckets(
        assignments,
        today_due=100,
        spread_over_days=10,
        start_after_days=1,
    )

    assert buckets[0].count > buckets[-1].count


def test_bell_curve_distribution_places_more_cards_in_middle():
    card_ids = list(range(100))
    assignments = assign_cards_to_due_days(
        card_ids,
        today_due=100,
        spread_over_days=11,
        start_after_days=1,
        distribution_profile="bell_curve",
        curve_strength=2.0,
    )
    buckets = build_day_buckets(
        assignments,
        today_due=100,
        spread_over_days=11,
        start_after_days=1,
    )

    middle_count = buckets[len(buckets) // 2].count
    edge_count = max(buckets[0].count, buckets[-1].count)

    assert middle_count > edge_count


def test_weighted_distribution_keeps_one_card_per_day_when_possible():
    capacities = build_weighted_day_capacities(
        76,
        30,
        distribution_profile="front_loaded",
        curve_strength=5.0,
    )

    assert len(capacities) == 30
    assert sum(capacities) == 76
    assert min(capacities) >= 1
    assert capacities[0] > capacities[-1]


def test_sparse_even_cards_are_spread_across_full_range():
    assignments = assign_cards_to_due_days(
        list(range(10)),
        today_due=100,
        spread_over_days=100,
        start_after_days=0,
        distribution_profile="even",
    )
    day_indices = [assignment.day_index for assignment in assignments]
    gaps = [right - left for left, right in zip(day_indices[:-1], day_indices[1:], strict=True)]

    assert day_indices[0] == 0
    assert day_indices[-1] == 99
    assert min(gaps) >= 10
    assert max(gaps) <= 12
