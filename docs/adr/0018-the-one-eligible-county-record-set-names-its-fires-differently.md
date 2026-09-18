# 18. The one eligible county record set names its fires differently, so nothing is pinned

Date: 2026-09-05

## Status

Accepted. Extends `docs/adr/0015`, which is not superseded: its four criteria, its four
outcomes, its two denominators and its refusal to correct either side all stand. This
decision records what happened when those criteria were taken to the actual supply of
published county data, and it turns one sentence of ADR 0015 into a refusal in code.

## Context

ADR 0015 decided the comparison for roadmap item 3.4 before the data existed and named
the missing piece: a county inspection record set that can be pinned. It listed a search
from 2026-09-04 as prose, put Santa Cruz County first and Butte County second, and said
that if neither could meet its criteria the item stays open.

The search was finished on 2026-09-05. It ended, and this section is the record of it,
because an unevidenced "none was found" is worth nothing to whoever looks next.

### What was queried

Four indexes were used, none of them a guess at a URL. The county portals in the list
below are reached through the indexes that carry them rather than through hostnames.

| Avenue | Query | What came back |
|---|---|---|
| `data.ca.gov` package API | `organization_list` with `all_fields=true` and `limit=1000` | 62 organizations, every one a state department, board or commission. No county publishes on `data.ca.gov` at all, so filtering that portal by owning organization cannot reach a county's own record set, and CAL FIRE's ownership of the Camp Fire package is not an accident of one dataset |
| ArcGIS Online item search | Three keyword queries over damage, destruction, structure status, inspection, assessment, rebuild and recovery, each crossed with fire, bounded to California and paged to exhaustion | 477 distinct feature services. One of them is a county-collected wildfire structure inspection set carrying an incident name |
| ArcGIS Hub dataset index | Free-text queries for structure damage inspection, county damage assessment and Butte County Camp Fire damage | The same county items the item search returned, plus federal, academic and out-of-state sets. Nothing new in California |
| Layer and item metadata | Item, service and layer JSON for every California candidate the two searches surfaced | The schemas recorded in the next section, read from the publishers' own endpoints rather than inferred from titles |

The 2026-09-04 probe recorded in issue #53, a request to the Santa Cruz County ArcGIS
REST directory that redirects and then returns 404, was not repeated. It did not need to
be: the county's layer is reachable through the portal index, which is where the search
went instead.

### What each candidate turned out to be

Read from the publishers' own service metadata on 2026-09-05. The column that decides
each row is which of ADR 0015's four criteria it fails first.

| County and set | What its schema actually carries | Verdict |
|---|---|---|
| Santa Cruz County, "Santa Cruz County CZU Lightning Fire Damage Inspection", owned by the account Santa Cruz County GIS, 1,477 records | `APNNODASH`, `ADDRESS`, `APNToCheck`, `AddressToCheck`, `ASR_APN_UPDATE` and `ASR_ADDRESS_UPDATE` beside `CALFIRE_Damage` and `CALFIRE_Comments`, 1,218 rows carrying a CAL FIRE damage call. No incident name column of any kind | Fails criterion 2 and criterion 4. It is a parcel and address join that already contains CAL FIRE's assessment, and there is nothing in it to compare per fire |
| Sonoma County, `PRMD_Fire_Assessment_2017`, owned by Permit Sonoma, 5,227 parcel polygons | `APN`, `FORMATTED_ADDRESS`, `Record_ID`, `Rec_Type`, `Update_Status`, `RESA_Status`. No incident name and no damage field | Fails criterion 4. It is rebuild permit tracking keyed by parcel, not an inspection record set |
| Los Angeles County, "Recovery Damage Inspection View (Public)", owned by the LA County EOC services account, 378 records | An `IncidentNm` column with a coded domain, and `DAMAGE`, `STRUCTURETYPE` and `STRUCTURECATEGORY`, which are CAL FIRE DINS column names verbatim. The layer describes itself as `EOC.OEM.RECOVERY_DINS` and the county's own maps of it are titled with "(DINS)" | Fails criterion 1. The county names itself the host of CAL FIRE's inspections, not their collector |
| Butte County, the account Butte County GIS | Six published items: zoning, jurisdictional boundaries, parcels, addresses, subdivisions and a logo | No damage survey is published. ADR 0015's second choice cannot be obtained separately from the consolidated product, which is what it required |
| Napa County, `damage_assessments_fire_2017_READ`, owned by Napa County Planning, Building and Environmental Services | `StreetAddr` and `ASMT` beside an ATC-45 posting. No incident name column | Fails criterion 4, and has nothing to compare per fire |
| Napa County, "ATC Damage Assessments 2020 public", owned by Napa County Emergency Operations, 1,685 records | `INCIDENT_NAME`, `INCIDENT_YEAR`, `struc_posting_type`, `struc_type` and `qaqc_completed`. No address, no parcel number, no assessed value, no year built. The posting domain is the ATC one: inspected, restricted use, unsafe | Meets all four criteria |

### The set that meets every criterion

Napa County Emergency Operations publishes the county's own damage assessments for the
2020 fires. The item's own description is the thing ADR 0015's first criterion asks for
and it is unusually explicit: "Assessments were done by Building Division inspectors,
Napa County Planning, Building, and Environmental Services Dept."

Held against the four criteria in turn:

1. **The county is named as the collector.** In the publisher's own words, quoted above,
   naming the department and the inspectors.
2. **The set is distinct from CAL FIRE's.** It is an ATC safety assessment, posted green,
   yellow or red, collected on a Survey123 form the same account also publishes. Nothing
   in its schema is a CAL FIRE column and nothing in it carries a CAL FIRE damage call.
   This is the criterion Santa Cruz County and Los Angeles County both fail.
3. **It can be retrieved whole and hashed.** Retrieved on 2026-09-05, 1,685 records, the
   layer's own count agreeing before and after the walk.
4. **It can be read without fetching a position.** The four columns requested are the two
   incident columns and the two ATC columns, with geometry suppressed and the object
   identifier left out. The layer carries no address, parcel number or assessed value at
   all, so this is a property of the source rather than a filter applied on the way in.

The retrieval produced a working file of 249,244 bytes with a SHA-256 of
`fe7a7c4a6f24d5f203381b8a42abb366bc5d31b5159ac0b57ff09c414f4b49ca`, over a JSON array of
the four columns, indented by two, keys sorted, non-ASCII left as itself, with a trailing
newline. **That is a hash of a working file this repository does not carry and it is not
a pin.** It is written down so the next person can reproduce the retrieval and know
whether they got the same thing, and it is not in `sources.py` for the reason below.

### Why the comparison still cannot be made

The two organizations do not name the same fires the same way, and the join is by name.

Napa County's set carries two incident names, 1,109 records under `GLASS COMPLEX 2020`
and 576 under `NAPA LIGHTNING COMPLEX 2020`. CAL FIRE's file names ten fires in Napa
County: Atlas, County, Glass, Jones, LNU Lightning Cmplx, Nuns, Pickett, Steele, Tubbs
and Valley. Read from CAL FIRE's live layer on 2026-09-05, which is a later state than
this project's pinned retrieval of 2026-08-23; the names are what matter here and they
are the same names the pinned file carries.

Neither county spelling appears anywhere in CAL FIRE's file. Asked for an exact match on
each of the two, in any county, the layer returns a count of zero both times. Two of the
ten CAL FIRE names, Glass and LNU Lightning Cmplx, are plainly the same ground events the
county assessed.

Run as ADR 0015 decided it, the comparison therefore returns an agreement of zero: both
county names land in "absent from this record set", all ten CAL FIRE names land in "not
named by the county record set", and both shares are zero over their own denominators.
ADR 0015 already says what that is. It is the paragraph headed "A defect, not a finding":
an agreement of zero across fires both organizations plainly worked means the two sets
were not joined at all, and it is investigated rather than published as a result.

The investigation is this section, and its answer is that the mismatch is not a bug. The
county appends the incident year and uses its own local name for the complex; CAL FIRE
uses a short operational name. Neither is wrong. This is also not a Napa quirk: Los
Angeles County's layer names `Bobcat Fire`, `Bridge Fire` and `Lake Fire` where CAL FIRE
names Bobcat, Bridge and Lake, the same suffix mismatch in a different county. Every
county set found that names fires at all names them differently from CAL FIRE.

## Decision

**The Napa County set is not pinned.** `src/wildfire_service_territory_overlap/sources.py`
stays at four sources. A fifth entry there is a record of a retrieval that a measurement
is tied back to, and this retrieval produces no measurement: the comparison it exists for
refuses. Pinning it would put a source in `PROVENANCE.md` that nothing reads, and it
would read to a visitor as though 3.4 had shipped.

**ADR 0015's "defect, not a finding" is now a refusal rather than a paragraph.**
`cross_check._refuse_a_comparison_that_did_not_join` stops a comparison in which both
sides name at least one fire in the county and not one name is shared. The command
previously printed that block, and a block a command prints is a block a maintainer can
paste into a document. This repository already carries a written-down audit of gates that
could not fire; a rule stated only in an ADR is that audit's next entry, so it became
code the day the case that triggers it turned up. A test drives it with the real Napa and
CAL FIRE spellings.

The guard needs both sides to have named something. Where this project counts no incident
name in the county, its share over that denominator is already published as not measured,
and a zero there is a join nobody attempted rather than a join that failed. That case
stays legal and has its own test.

**No name is repaired to make the comparison work.** Not a fuzzy match, not an alias
table, not stripping a trailing year or the word "Fire", and not a hand-written pairing
of the two spellings. Any of those is this project deciding that two published names are
one fire, which is the adjudication `docs/adr/0003` refuses for contested ground and
`docs/adr/0013` refuses for a contested county label. It would also be the exact failure
mode this repository is built to prevent: loosening a rule so that a number comes out.

**Roadmap item 3.4 stays open, with the blocker named.** Its open half is no longer "find
a source". A source exists, it is named here, and what is missing is a way to join it that
this project is willing to use.

### What would have to change for the item to become possible

Three routes, in the order of how much they would cost:

1. **A county record set that carries CAL FIRE's incident name or incident number.** The
   join is then the publishers' own key and no adjudication happens here. Nothing found
   in this search carries one, and it is the first thing to check about any new candidate.
2. **Counts by fire, supplied by a county on request.** `docs/RUNBOOK.md` already says to
   ask for counts by fire where the only obtainable form of the records carries addresses,
   and `docs/outreach/` is where an ask is recorded. A county that answers with its own
   fire names beside CAL FIRE's, or with a mapping it stands behind, makes the join the
   publisher's statement rather than this project's guess.
3. **A new decision that a name adjudication is acceptable here.** It would need its own
   ADR, it would have to say what happens when the adjudication is wrong, and it would
   have to survive the two ADRs that refuse the same move elsewhere. It is written down
   as a route because the honest position is that it exists, not because it is
   recommended.

## Consequences

The search that item 3.4 has been waiting on is over, and its result is a negative with
an address: the supply of published California county inspection data was enumerated, one
set qualifies, and it cannot be joined. Anyone picking this up next starts from a named
candidate and a named obstacle instead of from a keyword search, and the table above says
which candidates not to spend the afternoon on.

The cost is that this project still has no external confirmation of anything, and the
roadmap row stays open for a second reason after being open for a first. The comparison
is decided, built, tested, and now guarded against the one way it could have reported a
naming convention as total disagreement. What it has never had is a second organization's
file it can join, and this decision says so rather than manufacturing one.
