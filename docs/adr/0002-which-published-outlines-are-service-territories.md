# 2. Which published outlines are read as service territories

Date: 2026-08-17

## Status

Accepted.

## Context

The California Energy Commission publishes electric load serving entities in two layers,
carrying a `Type` field with six values: `IOU`, `POU`, `CO-OP`, `Tribal`, `CCA` and
`ADMIN`. Only some of those describe an area within which an entity owns the distribution
system a burned structure was connected to.

A community choice aggregator procures energy for customers inside somebody else's
distribution footprint. Its polygon is an overlay, not a territory. Counting a record into
both a CCA and the underlying utility would count it twice and would report an overlap
that is not a boundary problem at all.

`ADMIN` in this data is the Western Area Power Administration: a federal power marketing
administration whose mapped area is a marketing and transmission area, not a retail
service territory.

## Decision

Read `IOU`, `POU`, `CO-OP` and `Tribal` as service territories. Exclude `CCA` and
`ADMIN`, publish both exclusions with their reasons in the output, and make the inclusion
rule the publisher's own `Type` field rather than a judgment about any named entity.

## Consequences

The rule is mechanical and reviewable, and it is not a claim about whether any particular
organization operates a distribution system. Nobody with California utility service
territory expertise has reviewed it; the README says so under "What still needs a person."

Two included entities are why more than a third of the record set is contested: a water
wholesaler and an agricultural water pooling authority, both published with the `POU`
type and both with footprints that blanket other entities' areas. Excluding them by name
would clean the result up considerably and would mean deciding, here, which of the
publisher's entities count. That decision is not made. The overlap is reported instead.
