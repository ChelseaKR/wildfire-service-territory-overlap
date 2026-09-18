# 12. Two boundary retrievals will invite a before-and-after story, so the shape of that comparison is decided now

Date: 2026-08-22

## Status

Accepted. Extends ADR 0008 before the data exists for it to matter.

## Context

ADR 0008 publishes the contested share per incident year and refuses to draw a trend
through it: with one territory-layer retrieval, every year is measured against
identical boundaries, so movement down that column is where each year's fires burned
and nothing else. The refusal has been cheap so far. One retrieval cannot produce a
trend, so not drawing one costs nothing.

The refresh cadence in `PROVENANCE.md` guarantees a second retrieval eventually.
When it lands, the refusal stops being free. Two boundary sets make these questions
answerable for the first time:

- did the contested share move because the boundaries moved?
- which records changed outcome purely because a publisher redrew an outline?

Both invite a line chart. A direction drawn across two boundary snapshots would be the
first figure in this repository that mixes two causes in one axis, and it would arrive
wearing exactly the authority this project exists to withhold.

## Decision

Three rules hold from the moment a second territory retrieval is taken.

**Comparisons are paired, never modeled.** What gets published is the artifact diff,
value by leaf, produced by `python -m wildfire_service_territory_overlap.artifact_diff` against the previous
pin's `measurements.json`, plus per-record transition counts computed by pairing each
record's containment signature under the old boundaries against its signature under
the new ones, the way `sensitivity.repair_comparison` already pairs repairs. No slope,
no rate of change, no interpolation between retrievals appears anywhere in the output.

**Each snapshot keeps its own denominator.** The contested share under the old
boundaries and under the new ones are two measurements over two different indexes, and
each is published whole, next to the other, never differenced into a single headline.
Where a difference interval is published at all, it carries the Newcombe conservative
bound and says in its own note that the same records were measured twice.

**No figure spans both snapshots without saying so at the key.** Any collection that
names both retrievals carries the retrieval dates on every row, so a reader cannot
copy one number out of a mixed table and mistake it for a single-retrieval fact.

The by-year cut keeps ADR 0008's rule unchanged: within either snapshot alone, still
no trend. Two snapshots do not license a direction across years inside either one;
they only license the paired comparison above.

## Consequences

The comparison tooling already exists, which is the point of deciding now: the
artifact diff refuses removed values, and the transition machinery is the same code
the repair sensitivity runs. When the second retrieval arrives, publishing what moved
is a procedure, and drawing a story through it remains something the output has no
field to carry.

The cost is small and paid anyway: the report gains no new section until there are two
retrievals to compare, and none of the existing figures change. What changes is that
the tempting figure will be visibly absent rather than merely unconsidered.
