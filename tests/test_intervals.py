"""The arithmetic behind every published proportion, including its refusals."""

from __future__ import annotations

import math

import pytest

from wildfire_service_territory_overlap.intervals import (
    MEASURED,
    NOT_MEASURED,
    Difference,
    NotARate,
    Rate,
    wilson,
)


def test_wilson_matches_a_worked_value() -> None:
    low, high = wilson(50, 100)
    assert low == pytest.approx(0.4038, abs=1e-4)
    assert high == pytest.approx(0.5962, abs=1e-4)


def test_wilson_stays_inside_zero_and_one_at_the_extremes() -> None:
    for numerator, denominator in ((0, 5), (5, 5), (0, 1), (1, 1)):
        low, high = wilson(numerator, denominator)
        assert 0.0 <= low <= high <= 1.0


def test_wilson_at_zero_successes_does_not_produce_a_zero_width_interval() -> None:
    low, high = wilson(0, 30)
    assert low == 0.0
    assert high > 0.0, "zero out of thirty is not certainty"


def test_wilson_narrows_as_the_denominator_grows() -> None:
    narrow = wilson(500, 1000)
    wide = wilson(5, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_wilson_refuses_a_zero_denominator() -> None:
    with pytest.raises(NotARate, match="not a proportion"):
        wilson(0, 0)


@pytest.mark.parametrize(("numerator", "denominator"), [(-1, 10), (11, 10)])
def test_wilson_refuses_a_numerator_outside_its_denominator(
    numerator: int, denominator: int
) -> None:
    with pytest.raises(NotARate):
        wilson(numerator, denominator)


def test_rate_of_carries_everything_a_published_rate_needs() -> None:
    rate = Rate.of("share", 3, 12)
    payload = rate.as_dict()
    for key in (
        "rate",
        "numerator",
        "denominator",
        "interval_low",
        "interval_high",
        "interval_method",
        "state",
    ):
        assert key in payload
    assert payload["state"] == MEASURED
    assert payload["rate"] == pytest.approx(0.25)


def test_a_rate_with_no_denominator_is_not_measured_rather_than_zero() -> None:
    rate = Rate.of("share", 0, 0)
    assert rate.state == NOT_MEASURED
    assert rate.value is None
    assert rate.low is None and rate.high is None
    assert rate.as_dict()["rate"] is None
    assert "nothing to divide" in rate.note


def test_not_measured_records_its_reason() -> None:
    rate = Rate.not_measured("share", reason="the layer was never fetched")
    assert rate.state == NOT_MEASURED
    assert "never fetched" in rate.note
    assert rate.method == "none"


def test_difference_interval_brackets_the_point_estimate() -> None:
    left = Rate.of("left", 60, 100)
    right = Rate.of("right", 40, 100)
    diff = Difference.between("left minus right", left, right)
    assert diff.value == pytest.approx(0.2)
    assert diff.low is not None and diff.high is not None
    assert diff.low < diff.value < diff.high
    assert diff.method == "newcombe-score-95"


def test_a_large_clear_difference_excludes_zero() -> None:
    diff = Difference.between("d", Rate.of("a", 900, 1000), Rate.of("b", 100, 1000))
    assert diff.excludes_zero()


def test_an_identical_pair_does_not_exclude_zero() -> None:
    diff = Difference.between("d", Rate.of("a", 50, 100), Rate.of("b", 50, 100))
    assert diff.value == pytest.approx(0.0)
    assert not diff.excludes_zero()


def test_a_difference_against_an_unmeasured_side_is_not_measured() -> None:
    diff = Difference.between("d", Rate.of("a", 5, 10), Rate.of("b", 0, 0))
    assert diff.state == NOT_MEASURED
    assert diff.value is None
    assert not diff.excludes_zero()
    assert "not measured" in diff.as_dict()["note"]


def test_difference_interval_stays_within_minus_one_and_one() -> None:
    diff = Difference.between("d", Rate.of("a", 1, 1), Rate.of("b", 0, 1))
    assert diff.low is not None and diff.high is not None
    assert -1.0 <= diff.low <= diff.high <= 1.0


def test_wilson_center_is_pulled_toward_a_half_on_small_denominators() -> None:
    low, high = wilson(1, 3)
    center = (low + high) / 2
    assert center > 1 / 3, "the score interval is deliberately not symmetric about p"
    assert not math.isnan(center)
