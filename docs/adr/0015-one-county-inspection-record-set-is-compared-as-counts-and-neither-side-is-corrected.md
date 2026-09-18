# 15. One county's own inspection records are compared as counts, and neither side is corrected

Date: 2026-09-04

## Status

Accepted. Extends ADR 0009 and ADR 0013, neither of which is superseded. Decided before
the data exists, in the manner of ADR 0012.

Extended by `docs/adr/0018` on 2026-09-05, which finishes the search this decision left
open. Nothing below is withdrawn. What changed is that the search ended: one California
county record set meets all four criteria stated here, Napa County's own ATC damage
assessments for 2020, and it is still not pinned, because the two organizations name the
same fires differently and the comparison decided below joins nothing. The paragraph
headed "A defect, not a finding" is now enforced in code rather than stated here alone.

## Context

Every measurement in this repository is drawn from one inspection file. The county cut
of ADR 0009 reads CAL FIRE's own `COUNTY` field. The comparison of ADR 0013 checks that
field against a coordinate, using a boundary layer from a second publisher, but the
records being checked are still CAL FIRE's. Nothing here has ever been held against a
record set that a different organization collected by walking the same ground.

Roadmap item 3.4 is that check, deliberately bounded: one county's own inspection
records against this project's counts for that county, reported as agreement and
disagreement counts. It is the first thing in this project that could be wrong in a way
the gates in this repository cannot see, because every gate here reads the same file
the measurements read.

**The retrieval half of the item is not done, and this decision does not pretend it
is.** No county inspection record set is pinned. `data/raw/` holds none. Nothing was
downloaded, nothing was hashed, `src/wildfire_service_territory_overlap/sources.py`
gains no entry, and no number in this repository moved. What follows decides the shape
of the comparison so that the retrieval, when a person runs it by hand, has nothing
left to argue about and no room to be talked into a friendlier measurement.

### What a search on 2026-09-04 found, as prose and not as a pin

Recorded here because the criteria below were written against it, and because the
negative half is the useful half. This is the state of the search on the day this
decision was taken; the search finished the following day and `docs/adr/0018` carries
the full record, including which of the counties below fails which criterion and why.

- **Butte County and CAL FIRE ran independent surveys of the same fire.** GISCorps
  records that after the Camp Fire the two "conducted independent damage assessment
  surveys of structures within the affected area" and that the teams "collected
  different data using different equipment and, in some cases, evolving methodologies",
  consolidating over 30,000 survey points covering over 19,000 structures
  ([the GISCorps account of the Butte County survey](https://www.giscorps.org/butteco_252/)). That is the case this item wants and it is
  documented rather than assumed. The product that reached a public portal, "Camp Fire
  Structure Status" on data.ca.gov, is published by CAL FIRE
  ([the Camp Fire Structure Status dataset on data.ca.gov](https://data.ca.gov/dataset/camp-fire-structure-status)), so downloading it would
  compare CAL FIRE's file against a set that already contains CAL FIRE's file.
- **Santa Cruz County is named as the collector of its own set.** The county's fire
  recovery pages offer "Santa Cruz County CZU Lightning Fire Damage Inspection Data"
  ([Santa Cruz County's fire recovery maps and data page](https://www.santacruzcountyca.gov/FireRecovery/AdditionalResources/MapsData.aspx)),
  presented as a county product rather than as a republication. It is offered as a map
  application; no download endpoint was verified, so nothing about how it could be
  retrieved is claimed here.
- **A county badge on a dataset does not make it a county's record set.** Sonoma
  County's GIS hub carries "CalFire Damage Assessment 2017", which is CAL FIRE's
  assessment hosted by a county. Comparing against it would measure a file against
  itself and report perfect agreement as a finding.
- **The county products that are easiest to find are the ones this project refuses to
  fetch.** The public damage maps from Santa Cruz County and from Los Angeles County
  after the January 2025 fires are address-level and parcel-level. This project does not
  fetch an address, a parcel number, or an assessed value from anybody, and that rule
  does not relax for a cross-check.

## Decision

### One county, chosen by criteria, not by whichever file downloads

A county record set is eligible only if all four hold:

1. **The county is named as the collector**, not as the host. A republication of CAL
   FIRE's own assessment is not a second opinion.
2. **The set is distinct from CAL FIRE's**, not a merge that already contains it. Butte
   County's consolidated Camp Fire product fails here even though the independence of
   the two original surveys is exactly what this item is for.
3. **It can be retrieved whole and hashed**, so it can be pinned the way the four
   existing sources are pinned, with a feature count, a byte count and a SHA-256 in
   `sources.py` and a restatement in `PROVENANCE.md`.
4. **It can be read without fetching an address, a parcel number, a coordinate, or an
   assessed value.** If the only way to get the counts is to download the locations,
   the item does not ship.

On the evidence above, the first county to approach is **Santa Cruz County**, for its
CZU Lightning Complex inspection data, because it is the one case found where the county
itself is named as the collector of its own set. **Butte County** is second, for the
Camp Fire, and only if the county's original survey can be obtained separately from the
consolidated product. If neither can meet criteria 3 and 4, item 3.4 stays open. It does
not ship against a CAL FIRE republication wearing a county's badge, and the absence is
recorded rather than filled.

### The comparison is per fire, by name, and never per structure

Two organizations inspecting one fire do not inspect the same structures. CAL FIRE's
file is bounded by the state responsibility area and by 300 feet of the fire perimeter,
which its own metadata states and this project already quotes. A county's survey is
bounded by its jurisdiction, which includes local responsibility area ground CAL FIRE's
file was never going to carry. A structure-level join is therefore not available, would
need the locations this project refuses to fetch, and would not mean what it looks like
even if it existed.

What both sets can be asked is a question neither has to share a rule to answer: which
fires does this file carry records for, in this county?

### Four outcomes per incident, counted separately

For every incident name either side carries, in name order:

- **in both**: the county's set names the fire and this project counts records for it in
  this county;
- **here under another county**: this project counts records for the fire, and CAL
  FIRE's `COUNTY` field puts them somewhere else;
- **absent from this record set**: this project's record set does not name the fire at
  all;
- **not named by the county record set**: this project counts records for the fire in
  this county and the county's set does not name it.

Agreement is the first. Disagreement is the other three, kept apart rather than summed
into one number, because they mean three different things and collapsing them would
publish inspection scope as if it were error.

### Neither side is corrected and neither is the truth

Nothing in the comparison edits a county label, moves a record, drops a fire, or
reconciles a name. This is ADR 0013's posture applied to a second organization instead
of to a second boundary layer: the output says how often two record sets answer one
question differently and does not say which one is right. The county's set does not
become a correction of CAL FIRE's file, and CAL FIRE's file does not become a test the
county's survey passed or failed.

### Incident names are matched as published, normalized only for case and whitespace

Two organizations name fires their own way. A name that differs between the two sets
falls into "absent from this record set" and "not named by the county record set" at the
same time, and both counts carry it. That is a fact about the two record sets and it is
not repaired by a fuzzy match, because a fuzzy match is this project deciding that two
names are one fire, which is the adjudication ADR 0003 and ADR 0013 both refuse.

### Two shares, two denominators, and no difference drawn between them

Two proportions are published, each over its own denominator, each with a Wilson
interval:

- the share of the incidents the county's set names that this project also counts in
  this county;
- the share of the incidents this project counts in this county that the county's set
  also names.

No Newcombe difference is taken between them. They are two questions with two
denominators, not one thing measured twice, and ADR 0012's rule that each snapshot keeps
its own denominator applies here for the same reason it applies there. Where this
project counts no incident name in the county at all, the second share is published as
not measured. It is never a zero.

### No rate is taken between the two record sets, and no damage rate for the county

The number of records in one file over the number in the other is not published, in
either direction. `measure.py` already refuses a rate whose denominator is drawn from
outside the record set it counts, and two organizations counting two populations under
two rules is exactly that case: neither file is the other's denominator, and the
quotient would read as coverage of one by the other.

No damage rate is published for the county, from either file. ADR 0004 refuses that
arithmetic for a territory and ADR 0009 refuses it for a county, and a second file does
not create an exception. The cross-check counts inspections, never destruction.

### What this can falsify, and what it cannot

- **"Here under another county" is the only outcome that bears on the county cut**, and
  even then it bears on CAL FIRE's `COUNTY` field rather than on code in this
  repository, in exactly the way ADR 0013's disagreement count does. A large count here
  is a published limit on the county cut of ADR 0009: its rows rest on a field two
  organizations do not agree about.
- **"Absent from this record set" and "not named by the county record set" are
  inspection scope**, not error. A fire the county inspected outside the state
  responsibility area was never going to be in CAL FIRE's file, and a fire in the file
  that the county did not publish says nothing about either.
- **A defect, not a finding**: agreement of zero across a set of fires both
  organizations plainly worked would mean the two sets were not joined at all, most
  likely a county name or an incident name that does not match for a mechanical reason.
  That is read as a fault in the comparison and investigated, not published as a result.
- **Nothing here falsifies the placement, the geometry repair, the overlap counts, or
  any figure about a territory.** Those rest on boundaries and coordinates, which a
  county's inspection record set does not speak to. The cross-check is bounded to what
  it can actually test, and the boundary of that is stated here rather than discovered
  by a reader.

### It does not join the pipeline until it has data

The module is a command, `python -m wildfire_service_territory_overlap.cross_check`, run
by hand against local files, with its procedure in `docs/RUNBOOK.md`. It is not called
from `cli.build` and it writes nothing into `published/`.

The alternative was a not-measured block carried in every build until a source is
pinned. It was rejected. A section in the published report that says nothing on every
run is a section a reader learns to skip before the run where it says something, and
adding it would mean regenerating the published tree to carry a block with no
measurement in it. The rule this project runs on is that a measurement which could not
be made is never a zero; the cleanest way to honor it here is for the block not to
exist until the retrieval does. When the source is pinned, the block joins the artifact,
its incident collection joins `artifacts.ORDERINGS` in the same change, and the refresh
goes through the deliberate procedure like any other.

## Consequences

The half that can be built without the data is built, tested, and refuses on its own:
mismatched county, empty external set, a set carrying an address or a coordinate, a
county this project has no records for, a county this project measured as not measured,
a row with no incident name, and a set naming more distinct fires than the whole record
set does. Each refusal has a test that fires it. The half that needs a person is a
retrieval and a pin, and the roadmap keeps saying so until somebody does it.

The cost is that this project still has no external confirmation, and the roadmap row
stays open with the retrieval named as the missing piece rather than the analysis. That
is the honest position: the comparison is decided, the code will run the moment a file
exists, and nothing in the repository claims a cross-check has been performed.
