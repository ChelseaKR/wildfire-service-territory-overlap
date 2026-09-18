# Glossary

Every term the README and the generated report use faster than they define it. Each
entry says what the term means *in this repository* and links to where it is settled
authoritatively. Definitions here do not relitigate an ADR; where a term is contested or
undocumented at the source, the entry says so rather than smoothing it over.

## The record set

**DINS.** The CAL FIRE Damage Inspection database, the record set every denominator in
this project counts. Its published scope is structures "impacted by wildland fire within
the Statewide Responsibility Area (SRA) that are inside or within 300 feet of the fire
perimeter", quoted in
[`sources.py`](../src/wildfire_service_territory_overlap/sources.py) and restated in
[`PROVENANCE.md`](../PROVENANCE.md).

**State responsibility area, SRA.** The area in which the State of California bears
primary financial responsibility for wildland fire protection. It appears here only
inside the CAL FIRE scope quote above, because it defines which structures reach the
file; nothing in this project computes or reasons about SRA boundaries. See the scope
caveat in [`sources.py`](../src/wildfire_service_territory_overlap/sources.py).

**Record set, fire records.** The 132,520 records the published file marks as wildfire,
out of 132,522 total. Every rate in the output states which of the two it divides by;
see [ADR 0001, the denominator is the inspected record set](adr/0001-the-denominator-is-the-inspected-record-set.md).

## The territory layer

**Load serving entity, LSE.** The California Energy Commission's own name for the
entities in the two layers this project reads. The CEC publishes their outlines and
warns in its metadata that "Boundaries are approximate, for absolute territory
information, contact the appropriate load serving entity", quoted in
[`sources.py`](../src/wildfire_service_territory_overlap/sources.py).

**`Type`.** The CEC field this project's inclusion rule reads, carrying six values:
`ADMIN`, `CCA`, `CO-OP`, `IOU`, `POU` and `Tribal`. **The publisher documents none of
them**: as retrieved, the layer metadata carries no field description and no coded-value
domain, the FGDC record has no entity and attribute section, and no data dictionary is
attached. That is recorded as `TYPE_FIELD_IS_UNDOCUMENTED` in
[`sources.py`](../src/wildfire_service_territory_overlap/sources.py), and it is why the
four expansions below are given as the conventional reading of the abbreviation rather
than as the publisher's definition.

**IOU.** Investor owned utility, conventionally. Read as a service territory by the
inclusion rule; the publisher defines the value nowhere. See
[ADR 0002, which published outlines are read as service territories](adr/0002-which-published-outlines-are-service-territories.md).

**POU.** Publicly owned utility, conventionally. Read as a service territory. Two
entities carrying this type, a water wholesaler and an agricultural water pooling
authority, are why more than a third of the record set is contested; ADR 0002 records
that they are not excluded by name.

**CO-OP.** Electric cooperative, conventionally. Read as a service territory. Dropping
it moves 1,406 records into "inside no published territory", which
[ADR 0006](adr/0006-the-inclusion-rule-is-measured-against-its-alternatives.md) measures
rather than argues.

**Tribal utility.** A tribal electric utility, conventionally. Read as a service
territory, and worth nothing on the result: no record in the file falls inside either
tribal outline.

**CCA.** Community choice aggregator, defined at
[Public Utilities Code section 331.1](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PUC&sectionNum=331.1)
as a local government electricity buyers' program, with section 366.2 leaving
metering, billing and delivery with the electrical corporation. Excluded here because
its polygon overlays another entity's distribution footprint rather than being one, so
counting a record into both would count it twice; the code citation is carried in
`EXCLUDED_TYPES` in
[`sources.py`](../src/wildfire_service_territory_overlap/sources.py) and the exclusion is
argued in
[ADR 0002](adr/0002-which-published-outlines-are-service-territories.md), which states
the reasoning without citing the section.

**ADMIN.** A federal power marketing administration, in this data the Western Area Power
Administration. Excluded because the mapped area is a marketing and transmission area
rather than a retail service territory; see
[ADR 0002](adr/0002-which-published-outlines-are-service-territories.md).

## The four outcomes

**Placed.** A record whose coordinate falls inside exactly one outline this project
reads as a service territory.

**Contested.** A record whose coordinate falls inside two or more of them. It is
published as a count alongside the combination of outlines involved and is never
awarded to any of them; see
[ADR 0003, contested ground is reported and never resolved](adr/0003-contested-ground-is-reported-never-resolved.md).
A point lying exactly on a shared edge counts as inside both, so an edge case becomes
contested rather than being decided by a floating point comparison.

**Uncovered.** A record inside no published territory. Distinct from not measured,
because only one of the two is a fact about coverage.

**Not measured.** A measurement that could not be made, which is never published as a
zero. A coordinate outside the California bounding box is reported this way rather than
as uncovered, and it is not moved, clipped, or corrected; see `CALIFORNIA_BBOX` in
[`sources.py`](../src/wildfire_service_territory_overlap/sources.py).

## Geometry

**OGC validity check.** The Open Geospatial Consortium's validity rules for a polygon,
as implemented by GEOS through Shapely. Eight of the published territory polygons fail
it on retrieval, and an invalid polygon answers a containment question undefined rather
than refusing it, which is why each is repaired before use; see
[ADR 0005, an invalid published polygon is repaired and the repair is measured](adr/0005-an-invalid-published-polygon-is-repaired-and-the-repair-is-measured.md).

**Geometry repair.** One of three candidate answers to invalidity, named in
`REPAIR_STRATEGIES` in
[`geometry.py`](../src/wildfire_service_territory_overlap/geometry.py): `make_valid`,
which produces the published figures, `buffer_zero`, and the structure preserving
`make_valid_structure`. Each is run over the whole record set and the disagreement
between them is published; see
[ADR 0007](adr/0007-the-two-repairs-are-run-against-each-other.md) and
[ADR 0011](adr/0011-a-third-repair-joins-the-comparison-and-the-default-does-not-move.md).

**Boundary band.** A distance from the nearest published edge, at 100, 250, 500 and
1000 meters, within which a record's placement would be changed by an approximation
error of that size. A territory with no placed records has no bands rather than a row of
zeros.

## Statistics

**Wilson score interval.** The 95% interval published beside every rate here, used
rather than the normal approximation because the normal interval misbehaves near zero
and one and can run below zero or above one exactly where several of these rates sit.
Implemented in [`intervals.py`](../src/wildfire_service_territory_overlap/intervals.py)
and recorded on each rate as `wilson-score-95`.

**Newcombe score interval.** The interval published for a *difference* between two
proportions, built from the two Wilson intervals for the same reason. Recorded on each
difference as `newcombe-score-95`; see
[`intervals.py`](../src/wildfire_service_territory_overlap/intervals.py).

**Denominator.** What a count is divided by. A `Rate` cannot be constructed without one,
a rate with a zero denominator is not zero percent but not measured, and
`artifacts.check_all` refuses to write an artifact containing a rate-shaped object
missing either; see
[`artifacts.py`](../src/wildfire_service_territory_overlap/artifacts.py).

## Process

**Pin.** A dated retrieval of a source, recorded with its byte count and SHA-256 in
[`PROVENANCE.md`](../PROVENANCE.md). Published figures move only when a pin is
deliberately refreshed, and a pin goes stale at twelve months, when the publisher
modifies a layer, or when the pipeline changes shape.

**Artifact diff.** The leaf by leaf comparison a refresh is held to, so a published
number cannot change quietly. It refuses a run in which published values disappeared
unless `--allow-removals` names the removal deliberate; see
[`artifact_diff.py`](../src/wildfire_service_territory_overlap/artifact_diff.py) and the
refresh procedure in [`RUNBOOK.md`](RUNBOOK.md).
