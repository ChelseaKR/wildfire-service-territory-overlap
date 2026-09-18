# 7. The two repairs are run against each other, not recalled

Date: 2026-08-17

## Status

Accepted. Extends ADR 0005, which is not superseded.

## Context

ADR 0005 chose `make_valid` over `buffer(0)` and recorded that "the two disagreed on
roughly 770 placements". That figure came from comparing two drafts during development.
It was a recollection, it carried no denominator and no interval, and by the time it
reached an ADR the older draft no longer existed to re-run. A project whose first rule is
that every rate carries its denominator was citing a number it could not reproduce.

The repair strategy is now a parameter rather than a constant, so both can be run over
the same records in the same build. Over the 132,520 wildfire records:

The first row is the census total. The four rows under it decompose that total, and
say so in words rather than by sitting underneath it, because position is not something
a reader working through the table linearly can see.

| Outcome under the two repairs | Records | Share of the record set |
|---|---:|---:|
| Outcome differs between the two repairs | 927 | 0.70%, interval 0.66% to 0.75% |
| Placed under `make_valid`, contested under `buffer(0)` | 770 | part of the 927 above |
| Contested under both, between a different pair | 157 | part of the 927 above |
| Placed under both, in a different territory | 0 | part of the 927 above |
| Uncovered under either | 0 | part of the 927 above |

The placed share is 62.14% under `make_valid` and 61.56% under `buffer(0)`, a difference
of 0.58 percentage points with a Newcombe interval of 0.21 to 0.95 points. The interval
is the conservative one: the same records are placed twice, so the two proportions are
not independent, and the exact figure is the disagreement count rather than the interval
around the difference of two totals.

The recollection was close. 770 is exactly the placed-to-contested movement, and it
happens to be the number a reader would have derived from the two totals. What it missed
is the other 157: records contested under both repairs but between a different pair of
outlines, which two totals cannot see and a per-record comparison can.

The direction is systematic. `buffer(0)` produced the larger polygon in all eight
repaired cases, and larger polygons overlap more, so every disagreement runs from placed
towards contested and none runs the other way.

## Decision

`make_valid` remains the repair the published figures use. `buffer(0)` stays implemented,
stays exercised by the test suite, and is run to completion on every build by
`wildfire_service_territory_overlap.sensitivity.repair_comparison`, which publishes the disagreement as a count
with its denominator and its interval and names each transition.

A third repair may be added. It goes into `REPAIR_STRATEGIES` and into the comparison at
the same time, and `geometry.repair` raises on a strategy that is in neither, so a repair
cannot be used before it has been measured against the one in force.

## Consequences

The largest caveat on the result now carries two numbers rather than one. 91.7% of placed
records sit inside a repaired polygon, which is the exposure, and 0.70% of the record set
changes outcome between the two obvious repairs, which is what that exposure is worth
under the alternative actually available.

That the two repairs differ at all is a finding about the published boundaries and not
about this code. Eight of the fifty-nine outlines arrive failing an OGC validity check,
and the disagreement between two standard repairs of them covers thousands of square
kilometers of California. It is reported in the README on that basis.

Both figures are honest and neither is reassuring on its own. A reader who wants to
discount the repaired territories can see which they are; a reader who wants to know
whether the repair choice could have changed the headline can see that it moves the
attributable share by about half a percentage point and never turns an attributable
record into an unattributable territory assignment.
