# 6. The inclusion rule is measured against its alternatives, and left alone

Date: 2026-08-17

## Status

Accepted. Extends ADR 0002, which is not superseded.

## Context

ADR 0002 reads `IOU`, `POU`, `CO-OP` and `Tribal` as service territories and excludes
`CCA` and `ADMIN`, on the strength of the publisher's own `Type` field. It recorded that
nobody with California utility service territory expertise had reviewed that, and it did
not say what the choice was worth. A rule whose cost is unknown cannot be argued with:
a reader has no way to tell whether the reasoning matters or is decorative.

Two things were established before this decision.

**The publisher documents none of the six values.** As retrieved on 2026-08-17, the layer
metadata carries no description on the `Type` field and no coded-value domain, the FGDC
record carries no entity and attribute section, and no data dictionary is attached to
either item. The publisher's own load serving entities page names four categories in
prose and does not name `Tribal` or `ADMIN` at all. So the rule reads a field whose
values are defined nowhere by the party that publishes them. That is a fact about the
source, and it is now stated in the output rather than left for a reader to discover.

**The rule was run against its alternatives over the whole record set.** Not a sample and
not an argument: the same 132,520 records placed again under each variant.

| Inclusion rule | Contested | Share | Inside no published territory |
|---|---:|---:|---:|
| The rule as built | 50,167 | 37.86% | 0 |
| Without CO-OP | 50,081 | 37.79% | 1,406 |
| Without Tribal | 50,167 | 37.86% | 0 |
| Without CO-OP or Tribal | 50,081 | 37.79% | 1,406 |
| With CCA read as a territory | 74,661 | 56.34% | 0 |
| With ADMIN read as a territory | 98,541 | 74.36% | 0 |
| Every published type read as a territory | 119,704 | 90.33% | 0 |

The two inclusions the ADR was least sure of are worth **0.065 percentage points** on the
headline together. The two exclusions are worth 18.5 and 36.5 points. The uncertain half
of the rule is the half that does not matter to the figure the project leads with.

Dropping `Tribal` changes nothing at all: no record in the file falls inside either
tribal outline, so the count is zero rather than small. Dropping `CO-OP` moves 1,320
records out of placed and 1,406 into inside no published territory, which is the more
interesting cost. Those records are not made unattributable by a narrower rule; they are
made to look uncovered, which is a statement about the boundary layer that the dropped
entity's own published polygon contradicts. This project refuses to publish a
measurement that could not be made as a zero, and a narrower rule here would publish
1,406 of exactly that.

## Decision

The rule does not change. It is published with its sensitivity instead:
`wildfire_service_territory_overlap.sensitivity.type_inclusion` re-places the whole record set under seven
readings of the `Type` field and publishes each with its denominator, its interval, and
its difference from the rule as built. The undocumented state of the field is published
alongside it.

`sensitivity` chooses nothing. Every variant is a row, the rule as built is the reference
row, and no variant is marked better.

## Consequences

The unreviewed part of ADR 0002 is now bounded: a domain reviewer who disagrees about
`CO-OP` or `Tribal` can see immediately that the disagreement is worth six hundredths of
a percentage point and 1,406 records of false coverage, and can spend their attention on
the parts that move the number.

What is still missing is the entity-level review. This measures what the rule costs; it
does not establish that any particular organization in the layer operates a distribution
system, and it is not evidence that the publisher's classification of any named entity is
right. The README continues to ask for that under "What still needs a person."

The variants are held in one tuple. A new published type, or a change of mind about an
existing one, is a change to that tuple and to this log, not to a call site.
