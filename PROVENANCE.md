# Provenance

Four files, three publishers, one retrieval date. `src/wildfire_service_territory_overlap/sources.py` is the
reviewed record and `tests/test_provenance.py` asserts this document agrees with it, so
the two cannot drift apart.

None of this is affiliated with, endorsed by, or approved by CAL FIRE, the California
Energy Commission, or any electric utility.

## What was downloaded

| Source | Publisher | Features | Bytes | Retrieved |
|---|---|---:|---:|---|
| CAL FIRE Damage Inspection (DINS) Data | California Department of Forestry and Fire Protection | 132522 | 31908735 | 2026-08-23 |
| Electric Load Serving Entities (IOU & POU) | California Energy Commission | 53 | 11724721 | 2026-08-23 |
| Electric Load Serving Entities (Other) | California Energy Commission | 32 | 7397382 | 2026-08-23 |
| California County Boundaries and Identifiers | California Department of Technology | 58 | 28406231 | 2026-08-23 |

SHA-256 of each written file:

- `dins_postfire.json` `28a0bedfc74616281febc2268f40a40304c96c2eb0414e9b04b10f5318f2c496`
- `else_iou_pou.geojson` `e805520e747de619c9a97d03f8d70c9125f44b6e6fb2c0067bc122b317f2260e`
- `else_other.geojson` `f6e6880c03c4e062aa6f0b2a69a66b74e7782ff62a2a3ce7e641efc4f0f7ffe3`
- `county_boundaries.geojson` `52cb40c1db91b1a566683a4a6d39d2fad362df6b654e9d4b602bbbfe29601908`

## The county inspection source search of 2026-09-05, which pinned nothing

Recorded here because a source that was looked for and not taken is part of this
project's provenance, and because the alternative is a reader wondering whether anybody
tried. `docs/adr/0018` carries the full record: what was queried, what each California
county candidate turned out to be, and why the one that qualifies is not in the table
above.

The short version. No California county publishes on `data.ca.gov` at all, so the county
sets that exist live in ArcGIS portals rather than in the state catalog. Santa Cruz
County's CZU inspection layer is a parcel and address join that already carries CAL
FIRE's own damage call, Sonoma County's 2017 layer is rebuild permit tracking keyed by
parcel, Los Angeles County's recovery layer describes itself as CAL FIRE's DINS records,
and Butte County publishes no damage survey. Napa County's own ATC damage assessments
for 2020 meet every criterion in `docs/adr/0015`, including the one this project cares
about most: the layer carries no address, no parcel number and no assessed value, so
reading it fetches no position.

**Nothing was pinned and no number in this repository moved.** The four sources above
are still four. The Napa layer was retrieved once, on 2026-09-05, as four columns with
geometry suppressed, to establish that it can be retrieved and read within this
project's rules; the result is a working file this repository does not carry and
`sources.py` gains no entry for it. It is not pinned because the two organisations name
the same fires differently, so the comparison joins nothing, which ADR 0015 already
reads as a defect rather than as a finding.

## The re-render of 2026-09-04, which moved prose and no measurement

`published/REPORT.md` was rewritten from `published/measurements.json` without
re-acquiring anything. This is not a refresh and is recorded separately from the two
above so that nothing here is mistaken for one: no endpoint was called, no pin moved,
and the artifact the document renders from is byte-identical before and after, sha256
`d473ea9c2ae3fbab00586aff36b97826b5e3b22e19069d9a53867ac53910a274`.

What moved is three lines of prose. In "What the repair is worth", the table of placed
shares followed the transitions table with one blank line and no sentence between them,
which `docs/ACR.md` recorded on 2026-09-04 as a table a reader meets with nothing saying
what it counts. The renderer gained an introducing sentence as a catalog entry, and the
document was re-rendered to carry it.

No measured value changed, because none could: the numbers in the document are read out
of the artifact, and the artifact was not rebuilt. The leaf-by-leaf artifact diff that a
refresh runs has nothing to compare here, and saying so is more honest than running it
against an identical file and reporting that nothing moved.

The order was deliberate, and it is the order any future rule of this kind should
follow: the renderer changed first, the published document was re-rendered to match,
and `assert_every_table_is_introduced` was added last, behind an artifact that could
already pass it. A gate is never added by editing the artifact it would refuse.

## The refresh of 2026-08-23

Trigger: this pipeline changed shape (three triggers in Refresh below would have fired;
the third did). What the refresh carried: the ninth fetched field, a fourth source, two
new measurements, and the three-repair census reaching the real record set.

- Both territory layers returned the hashes the previous pin recorded, and the CEC
  items still carry last-modified 2026-08-12. The boundaries are unchanged.
- The re-acquired DINS file holds the same 132,522 records under the same predicate,
  with `STRUCTURECATEGORY` added to the request. Its hash differs because the column
  does.
- The county boundary layer was acquired once, whole, under the same guards as
  everything else: count before and after, strictly increasing unique identifiers.
- The artifact built after the refresh was compared against the one built before at
  every published value: **6,582 values compared, 1,528 added, none removed, none of
  the measured figures changed.** The four changed leaves are two retrieval dates, one
  label made more precise, and one note rewritten when a second alternative joined the
  run it describes.

What the new measurements found over the real record set:

- **The three-repair census.** The structure-preserving repair agrees exactly with
  the noding repair's disagreements: both differ from `buffer(0)` on the same 927
  records, and `structure` against `buffer(0)` disagrees on none. The union bound does
  not move from 927. A third reading of the invalid geometry widened nothing; it
  corroborated the pair ADR 0007 measured.
- **The coordinate-county comparison.** Of 132,520 records, 132,490 carry a usable
  coordinate and a county label the boundary layer carries. 132,459 agree; 31
  (0.023%, interval 0.016% to 0.034%) sit outside the county their publisher
  recorded; none reaches no polygon and no label went unmatched. The largest county
  counts are five records each in Lake, Napa and Sonoma. Counted against CDT's own
  warning that boundary errors will exist, and never corrected.
- **Representativeness by structure class.** Six of the seven published categories
  carry enough placed and contested records to compare; the aggregate conclusion
  holds inside most classes, with Multiple Residence the widest interval.

## The refresh of 2026-08-17, kept for its pattern

The DINS file was re-acquired to add the publisher's `COUNTY` column, so its byte count
and hash above are not the ones the previous pin carried. What that refresh did and did
not move is recorded rather than assumed:

- The re-acquired file holds the same 132,522 records, and with the new column removed it
  is byte-for-byte the file the previous pin hashed. The only change in the retrieval is
  the added column.
- Both territory layers came back with the hashes the previous pin already recorded, so
  the boundaries are unchanged.
- Every figure published before the refresh is unchanged after it. The artifact was
  compared leaf by leaf against the previous one: 4,370 published values, none removed,
  none changed. What the refresh added is the county cut and nothing else.

A refresh that had moved the figures would say so here, with the sizes. This one did not,
and that is a fact about this retrieval rather than a promise about the next one.

The files themselves are not in git. `data/raw/` is ignored. The DINS retrieval is
132,522 structure-level records at their published coordinates, and this repository
publishes counts.

## Endpoints and terms

**CAL FIRE DINS.** `POSTFIRE_MASTER_DATA_SHARE` layer 0, listed among the dataset's own
resources on [data.ca.gov](https://data.ca.gov/dataset/cal-fire-damage-inspection-dins-data).
Creative Commons Attribution.

**CDT County Boundaries.** Layer 1 of the California County Boundaries and
Identifiers service published by the California Department of Technology on
[data.ca.gov](https://gis.data.ca.gov/datasets/California::california-county-boundaries-and-identifiers/about).
State of California terms of use. Only `OBJECTID` and `CDT_NAME_SHORT` are read
beside the geometry.

**CEC Electric Load Serving Entities.** Two feature services published by the California
Energy Commission, ArcGIS Online items `30410214d637434ba1003cbdcc32cf55` and
`07224640a2fe42f89399be796e7b8810`, both last modified by the publisher 2026-08-12.
Terms: [CEC conditions of use](https://www.energy.ca.gov/conditions-of-use).

Nine DINS fields are requested and no others: `OBJECTID`, `COUNTY`, `DAMAGE`,
`HAZARDTYPE`, `INCIDENTNAME`, `INCIDENTSTARTDATE`, `LATITUDE`, `LONGITUDE`,
`STRUCTURECATEGORY`.
`SITEADDRESS`, `APN`, `STREETNUMBER`, `STREETNAME`, `ZIPCODE` and
`ASSESSEDIMPROVEDVALUE` are published by CAL FIRE, are not needed to answer which polygon
a point is in, and are therefore never downloaded. `tests/test_acquire.py` asserts that.

`COUNTY` is a published administrative area name, coarser by orders of magnitude than the
coordinate this project already reads and does not republish. It is used for one thing,
the county cut in `docs/adr/0009`, and it reaches the output only as a row label beside a
count.

Requests pause between pages and stop rather than route around a 401, 403 or 429. No
agency website is crawled: four REST endpoints are read the way their own dataset pages
document them to be read.

Every request carries a User-Agent naming this project, the DINS walk included, since
the pin moved to `3a6aa47ae9e755a256614bc124a6db960d60dc7a` on 2026-09-07.

That was not true before, and this document said it was until 2026-09-05. The DINS walk
is `perimeter`'s, and `perimeter` used to read its own name from a module constant no
caller could pass, so the largest of the four layers at 132,522 records identified as
`perimeter-coverage/0.1 (+https://github.com/ChelseaKR/perimeter)`, the pinned dependency
performing the walk rather than the project asking for the data. That was gap 1 in
`docs/UPSTREAM.md`; upstream now takes a `user_agent` argument and this project passes
one. `tests/test_acquire.py` holds the sentence against the requests that are actually
sent, and asserts the dependency's own name is not among them.

## How completeness is established

Each layer is asked for its own record count before and after the walk. A walk that
disagrees with either writes nothing. Identifiers must come back strictly increasing and
unique. The DINS walk itself is `perimeter`'s, pinned to commit
`3a6aa47ae9e755a256614bc124a6db960d60dc7a`, and the checks above are applied to its
output rather than assumed of it. Upstream now runs a post-walk recount and identifier
checks of its own; this project keeps its own because a consumer that stops checking a
dependency's output is a consumer trusting a version it did not read.

## Two decisions that move the numbers

**The projection is pinned as a pipeline.** California Albers, GRS80, no datum step, so
no PROJ grid files are involved and the arithmetic is identical on any machine. A WGS84
coordinate is therefore treated as though it were on GRS80, a shift of roughly one to two
metres in California. Every distance published here is a band at 100 metres or wider.
`tests/test_geometry.py` checks the pipeline against EPSG:3310.

**Eight of the published polygons arrive invalid and are repaired.** Ring
self-intersections and nested shells. An invalid polygon answers a containment question
undefined rather than refusing it, so each is passed through `make_valid`, named in the
report, and flagged on its territory row. 91.7% of the placed records sit inside one of
those repaired polygons, because two of the eight are the two largest territories in the
state. Both repairs are then run to completion: 927 records, 0.70% of the record set,
come out differently under `buffer(0)`. The exposure and what it is worth are both
published. See `docs/adr/0007`.

## What the publisher does not document

The inclusion rule reads the CEC `Type` field, and CEC documents none of its six values.
As retrieved on 2026-08-17: the layer metadata carries no description on the `Type` field
and no coded-value domain, the FGDC record carries no entity and attribute section, and
no data dictionary is attached to either item. The published load serving entities page
the metadata points to names four categories in prose and does not name `Tribal` or
`ADMIN` at all.

This is recorded as a fact about the source rather than as a complaint, and it is why the
rule is published with its sensitivity: `docs/adr/0006` reports what each reading of the
field is worth in records. What the rule costs is measured. What each value means is
still the publisher's to say.

## Refresh

The pins move only by deliberate refresh, and a refresh is a measured event:

- `make acquire` runs by hand, never from CI and never from a schedule. Automation
  does not republish figures unattended.
- Before anything is committed, the new artifact is compared against the one it
  replaces, value by value: `python -m wildfire_service_territory_overlap.artifact_diff OLD.json NEW.json`.
  Added and changed values come back with their paths and their old values; removed
  values refuse the run unless `--allow-removals` names the removal deliberate.
- What moved is then written into a dated section of this document, sizes included.
  The 2026-08-17 section above is the pattern: 4,370 values compared, none removed,
  none changed.

Cadence: at least once every twelve months, and sooner when any of these fires.
`make refresh-check` asks the first two without downloading a record, and says plainly
that it does not ask the third; `docs/RUNBOOK.md` has what its three exit codes mean.

1. **Age.** The record set grows through every fire season, so a year-old pin
   describes a year that has since been appended to it.
2. **The publisher moved first.** Either territory layer carries a last-modified date
   later than the retrieval date. The boundaries are what this project measures
   against; when they change, the measurement starts over rather than being patched.
3. **This pipeline changed shape.** A new measurement cannot reach an old pin,
   because `data/raw/` is never committed: regenerating `published/` requires the
   files the pin was built from, so shipping a new cut means re-acquiring.

Staleness is a fact about a pin's age, not a correction of its figures. Every page
states the retrieval date it describes. Nothing here republishes itself quietly to
stay young, and nothing published under an older pin is withdrawn when a newer one
lands: both remain exactly what they were measured against.
