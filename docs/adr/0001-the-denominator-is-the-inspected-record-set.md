# 1. The denominator is the inspected record set, and nothing else

Date: 2026-08-17

## Status

Accepted.

## Context

The obvious way to make this project impressive is to publish a rate that sounds like
risk: structures destroyed per thousand housing units, per customer, per square kilometer
of territory. Every one of those needs a denominator drawn from outside the damage
inspection file.

The file will not support it. CAL FIRE states the scope in its own metadata: the database
documents "all structures impacted by wildland fire within the Statewide Responsibility
Area (SRA) that are inside or within 300 feet of the fire perimeter." The numerator is
therefore a population defined by two things at once, where a fire burned and which land
the state is responsible for. Census housing units are defined by neither.

The consequence is not a small bias. A territory that is largely local responsibility
area, which describes most urban footprints, would show a near-zero rate against a
housing-unit denominator, not because little burned but because the state's inspectors
were not the ones counting. Published next to a rural territory's figure, that reads as a
statement about the utility. It would be false and it would be flattering to exactly the
wrong entities.

## Decision

Every denominator in this project is a count of records in this file. The record set for
coverage. The placed population for representativeness. A territory's own placed count
for its within-territory shares. Nothing is divided by housing units, customers, meters,
parcels, or land area.

## Consequences

No rate here can be read as a risk. That is the intended cost. It also means the project
answers a narrower question than a reader might arrive expecting, so the README says
which question in its first sentence.

Restricting the denominator to state responsibility area, by intersecting territories
with the published SRA layer, would make a housing-unit rate defensible. It would also
require a third publisher's polygons, areal apportionment of census geography, and the
uncertainty of both. Not ruled out; not built, and not implied to have been.
