# 10. An outline that holds no record is counted, not classified

Date: 2026-08-17

## Status

Accepted. Extends ADR 0002 and ADR 0006, neither of which is superseded.

## Context

ADR 0002 makes the inclusion rule the publisher's own `Type` field precisely so that this
project never has to decide whether a named organization operates a distribution system.
ADR 0006 measured what that rule costs and stopped in the same place: it establishes what
each reading of the field is worth in records, and it establishes nothing about any
entity.

A reader looking at the territory table does not stop there. They pick one name they
doubt and ask whether it belongs in the set at all. That question has a real answer
somewhere, in filings this project does not read and in a classification only the
publisher can make, and reaching for it here would mean doing exactly what ADR 0002
refuses: deciding, from outside the publisher's field, which of the publisher's entities
count.

The question underneath it is narrower and is answerable from the data already loaded:
**could that outline be moving a figure published here?**

For an outline no record falls inside, it cannot, and this is arithmetic rather than
opinion. Removing an outline can only change the containment signature of a record that
was inside it. A record inside none of the removed outlines keeps the signature it had,
and every figure in this repository is a function of those signatures.

## Decision

Publish the count. `wildfire_service_territory_overlap.sensitivity.untouched_outlines` reports which of the
indexed outlines hold no record, how many records fall inside any of them, and what
happens to the record set when all of them are removed at once. The last of those is not
reasoned about: the whole record set is placed again against the reduced index and the
records whose signature moves are counted, the same way ADR 0007 counts the disagreement
between two repairs.

No entity-level classification is added anywhere in the tree. The measurement names the
outlines because it must, in the same way the territory table already names them and in
the same neutral order, and it attaches a zero to each.

## Consequences

35 of the 59 indexed outlines hold no record. 0 of 132,520 records fall inside any of
them, and removing all 35 changes the outcome of 0 records. So for 35 of the 59 names in
the table, the entity-level question a reader might raise is one this project can decline
without leaving anything unmeasured: whatever the right answer is, the figures published
here are the same either way.

That is a smaller claim than it looks and it is worth being clear about the shape of it.
It does not say those outlines are wrong, or right, or that the publisher misclassified
anything. It does not extend to the 24 outlines that do hold records, where the same
question would matter a great deal and where this project still refuses to answer it. And
it is specific to this record set: an outline that holds nothing today holds nothing
because no fire in this file burned inside it, not because it is empty of the world.

What it does is turn an open judgment into a bounded one. The README asks for a domain
review of the inclusion rule under "What still needs a person"; this narrows what that
reviewer's answer could change.
