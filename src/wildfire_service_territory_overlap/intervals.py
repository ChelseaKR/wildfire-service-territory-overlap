"""Rates, and the two things a rate is not allowed to be published without.

A count without a denominator is not a rate, and a rate without an interval is not a
comparison. Both rules are enforced here rather than remembered: :class:`Rate` is the
only way a proportion reaches an artifact in this project, it cannot be constructed
without its denominator, and :func:`wildfire_service_territory_overlap.artifacts.assert_rates_are_denominated`
refuses to serialize a rate-shaped object that is missing either.

The interval is Wilson's score interval, which is used here rather than the normal
approximation for the reason that matters in this data: several territories carry very
few records, and the normal approximation produces intervals that run below zero or
above one exactly there. Differences between two proportions use Newcombe's score
method, built from the two Wilson intervals, for the same reason.

Nothing in this module knows what is being counted. That is deliberate: the arithmetic
should be reviewable without reading the wildfire code, and the wildfire code should not
be able to publish a proportion by any route that skips it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

Z_95: Final[float] = 1.959963984540054
"""Two-sided standard normal quantile for 95%. The only confidence level published."""

MEASURED: Final[str] = "measured"
NOT_MEASURED: Final[str] = "not_measured"


class NotARate(ValueError):
    """A proportion was asked for in a way that cannot produce an honest one."""


def wilson(numerator: int, denominator: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Raises rather than returning a placeholder when the denominator is zero. Zero out of
    zero is not zero percent; it is not measured, and the caller has to say so.
    """
    if denominator <= 0:
        raise NotARate(
            "a proportion with a zero denominator is not a proportion. Report the "
            "measurement as not measured instead of publishing a zero."
        )
    if numerator < 0 or numerator > denominator:
        raise NotARate(
            f"numerator {numerator} is not within the denominator {denominator}"
        )
    n = float(denominator)
    p = numerator / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    # Clamped to the exact endpoint at the extremes. With no successes the score interval
    # evaluates to a value a few times 1e-21 rather than to zero, which is arithmetically
    # fine and reads as an interval that does not contain its own point estimate. The
    # bound at zero successes is zero; the bound at every success is one.
    low = 0.0 if numerator == 0 else max(0.0, center - half)
    high = 1.0 if numerator == denominator else min(1.0, center + half)
    return (low, high)


@dataclass(frozen=True)
class Rate:
    """A proportion that carries its denominator and its interval, or says it cannot.

    ``state`` is ``measured`` or ``not_measured``. There is no third state and there is
    no state in which ``value`` is a number while ``denominator`` is zero.
    """

    label: str
    numerator: int
    denominator: int
    value: float | None
    low: float | None
    high: float | None
    state: str
    method: str
    note: str = ""

    @classmethod
    def of(cls, label: str, numerator: int, denominator: int, note: str = "") -> Rate:
        """Build a measured rate, or a not-measured one when there is nothing to divide."""
        if denominator <= 0:
            return cls.not_measured(
                label,
                numerator=numerator,
                reason="no records fall in this population, so there is nothing to divide",
                note=note,
            )
        low, high = wilson(numerator, denominator)
        return cls(
            label=label,
            numerator=numerator,
            denominator=denominator,
            value=numerator / denominator,
            low=low,
            high=high,
            state=MEASURED,
            method="wilson-score-95",
            note=note,
        )

    @classmethod
    def not_measured(
        cls, label: str, *, numerator: int = 0, reason: str, note: str = ""
    ) -> Rate:
        """A rate that could not be made. Never a zero, never an empty interval."""
        return cls(
            label=label,
            numerator=numerator,
            denominator=0,
            value=None,
            low=None,
            high=None,
            state=NOT_MEASURED,
            method="none",
            note=(f"{note} {reason}".strip() if note else reason),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "rate": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "interval_low": self.low,
            "interval_high": self.high,
            "interval_method": self.method,
            "state": self.state,
            "note": self.note,
        }


@dataclass(frozen=True)
class Difference:
    """A difference between two proportions, with a Newcombe score interval."""

    label: str
    left: Rate
    right: Rate
    value: float | None
    low: float | None
    high: float | None
    state: str
    method: str
    note: str = ""

    @classmethod
    def between(cls, label: str, left: Rate, right: Rate, note: str = "") -> Difference:
        if left.state != MEASURED or right.state != MEASURED:
            return cls(
                label=label,
                left=left,
                right=right,
                value=None,
                low=None,
                high=None,
                state=NOT_MEASURED,
                method="none",
                note=(
                    f"{note} one side has no denominator, so the difference is not "
                    "measured"
                ).strip(),
            )
        p1, p2 = left.value, right.value
        if p1 is None or p2 is None:  # pragma: no cover - guarded by state above
            raise NotARate("a measured rate must carry a value")
        l1, u1 = left.low, left.high
        l2, u2 = right.low, right.high
        if l1 is None or u1 is None or l2 is None or u2 is None:  # pragma: no cover
            raise NotARate("a measured rate must carry an interval")
        delta = p1 - p2
        lower = delta - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
        upper = delta + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
        return cls(
            label=label,
            left=left,
            right=right,
            value=delta,
            low=max(-1.0, lower),
            high=min(1.0, upper),
            state=MEASURED,
            method="newcombe-score-95",
            note=note,
        )

    def excludes_zero(self) -> bool:
        """True when the interval does not contain zero. False when not measured."""
        if self.state != MEASURED or self.low is None or self.high is None:
            return False
        return self.low > 0.0 or self.high < 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "difference": self.value,
            "interval_low": self.low,
            "interval_high": self.high,
            "interval_method": self.method,
            "state": self.state,
            "excludes_zero": self.excludes_zero(),
            "left": self.left.as_dict(),
            "right": self.right.as_dict(),
            "note": self.note,
        }
