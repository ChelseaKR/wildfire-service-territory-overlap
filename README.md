# wildfire-service-territory-overlap

**Can a California wildfire damage inspection be attributed to a published electric
service territory? For 37.9% of the record set, using public data alone, no.**

**Unofficial. Not affiliated with, endorsed by, or approved by CAL FIRE, the California
Energy Commission, SMUD, or any electric utility.** This is descriptive geography over
two public datasets. It is not a risk rating of any company, it ranks nobody, and it
contains no information about the location of anybody's infrastructure.

**Status:** Beta, version `0.1.0`. Measured against pinned retrievals of
CAL FIRE DINS (retrieved 2026-08-23), the CEC Electric Load Serving Entities layers
(retrieved 2026-08-23; items last modified 2026-08-12), and the CDT county boundary
layer (retrieved 2026-08-23). The figures move only when those retrievals are
deliberately refreshed. A pin goes stale at twelve months, when the publisher modifies
a layer, or when this pipeline changes shape; the triggers and the refresh procedure
are in `PROVENANCE.md`.

## Quick start

```bash
uv sync --locked
make verify                # lint, types, tests, coverage floor, determinism
make help                  # every target, one line each
```

Then read [`published/REPORT.md`](published/REPORT.md), which is generated, and
[`published/measurements.json`](published/measurements.json), which it is generated from.
`make report-offline` rebuilds the whole pipeline over committed fixtures, offline, in
about a second.

## The question, and why it is worth asking

The useful wildfire analysis for an electric utility joins fire outcomes to network
assets. Asset locations are not public and should not be. So the question that can be
asked from public data is the one below it: **given a structure that burned, which
published service territory boundary is it inside?**

That sounds like a solved problem. Both inputs are public: CAL FIRE publishes 132,522
damage-inspection records with coordinates, and the California Energy Commission
publishes service territory outlines for investor-owned utilities, publicly owned
utilities, cooperatives and tribal utilities. The join is a point-in-polygon.

It does not come out clean, and how it fails is the finding.

## What was measured

Over the 132,520 records the published file marks as wildfire, out of 132,522 total:

| Outcome | Records | Share | 95% interval |
|---|---:|---:|---|
| Inside exactly one published territory | 82,353 | 62.1% | 61.9% to 62.4% |
| Inside two or more published territories | 50,167 | 37.9% | 37.6% to 38.1% |
| Inside no published territory | 0 | 0.0% | 0.000% to 0.003% |
| Coordinate not usable | 0 | 0.0% | 0.000% to 0.003% |

Wilson score intervals. The denominator is the wildfire record set, stated on every row.

**More than a third of the record set is inside more than one published outline.** The
CEC's own metadata says why: *"Boundaries are approximate, for absolute territory
information, contact the appropriate load serving entity."* The published polygons do not
tile the state, they overlap, and the overlaps are not small. A water wholesaler's
published area covers much of southern California and contests records with six other
entities. A pooling authority for agricultural water districts overlays part of the
Central Valley and contests 12,241 records with one investor-owned utility. For a
record inside two outlines, public data does not say which entity serves it, and this
project does not decide on its behalf: it is counted as contested and it is never awarded
to the larger polygon, the smaller one, or the one listed first.

**That third is not spread evenly. It is a property of which fire burned where.** Of the
405 incidents in the record set, 353 have no contested record at all and 29 have nothing
but contested records: 94.3% of incidents fall entirely on one side, interval 91.6% to
96.2%. By year the contested share runs from 0.0% in 2013 to 92.5% in 2025. So 37.9% is
an average over a particular set of fires and not a property of the two datasets. No
trend is drawn through the years and none can be: the territory layer is a single
retrieval, so every year is measured against identical boundaries.

**By county it is starker still, and it is now measured.** CAL FIRE publishes a county
field, this project did not fetch it, and the retrieval was refreshed to add it. 52
counties are named in the record set and 30 records carry no county name. In 36 of the
52 the contested share is not low but zero, and where it is not zero it is mostly very
high: 99.9% of 11,721 classified records in Sonoma, 94.0% of 34,464 in Los Angeles,
93.9% of 2,510 in Orange, 0.0% of 28,747 in Butte. Every row carries its own denominator
and its own interval, the rows are in name order, and no county is compared against
another. No damage rate is published for a county for the same reason none is published
for a territory.

**The records that cannot be attributed look like the ones that can.** Destroyed share
among placed records: 52.95% of 82,353. Among contested records: 53.38% of 50,167.
Difference of minus 0.43 percentage points, Newcombe interval minus 0.98 to plus 0.13.
The interval includes zero, so this comparison does not establish that the attributable
subset is unrepresentative on damage outcome. That is the useful half of a bad result: a
third of the data cannot be attributed, but on this dimension it does not appear to be a
biased third.

**A territory-level damage rate would describe one fire, not a territory.** Which is why
no such rate is published here in any form. The evidence is published instead, as the
share of each territory's placed records contributed by its single largest incident: two
territories are at 100%, a third at 99.7%, a fourth at 82.9%. Dividing destroyed by inspected
inside those boundaries and printing the answers next to each other would produce a
league table of which fires happened where, labelled with company names.

**91.7% of the placed records depend on a geometry repair, and the two obvious repairs
disagree about 927 of them.** Eight published polygons fail an OGC validity check on
retrieval, and two of the eight are the largest territories in the state. An invalid
polygon answers a containment question undefined rather than refusing it, so each is
repaired before use, named in the report, and flagged on its row. Both repairs are then
run to completion over the same records: 927 records, 0.70% of the record set with an
interval of 0.66% to 0.75%, come out differently under `buffer(0)` than under
`make_valid`. 770 of them move from attributable to contested and 157 are contested under
both but between a different pair of outlines. The attributable share is 62.14% under one
repair and 61.56% under the other, a difference of 0.58 percentage points, Newcombe
interval 0.21 to 0.95. No record changes which single territory it is placed in, and none
becomes uncovered. That the two disagree at all is a fact about the published boundaries.

**The inclusion rule is worth less than the part of it nobody has reviewed suggests.**
Reading `CO-OP` and `Tribal` as service territories, which is the unreviewed half of the
rule, is worth 0.065 percentage points on the headline. Dropping `Tribal` changes nothing
at all: no record in the file falls inside either tribal outline. Dropping `CO-OP` moves
1,406 records into "inside no published territory", which would be a false statement
about coverage rather than a tidier result. The exclusions are what carry weight: reading
`CCA` as a territory would take the contested share to 56.3% and reading `ADMIN` would
take it to 74.4%. Every variant is published with its denominator and its interval.

## The rules this project is built on

**Every published rate carries its denominator and its interval.** Not by convention:
`Rate` cannot be constructed without a denominator, and `artifacts.check_all` refuses to
write an artifact containing a rate-shaped object missing either. A rate with a zero
denominator is not zero percent, it is not measured, and the writer refuses a
not-measured rate that carries a value. An interval whose two ends round to the same
string is printed at more decimal places until they do not, because `0.7% to 0.7%` reads
as certainty.

**A judgment call is published with what it is worth.** Two decisions here could have
gone the other way: which published types count as territories, and which repair is
applied to the polygons that arrive invalid. Both are parameters, both are re-run over
the whole record set on every build, and the difference is published as a measurement.
Neither is chosen by the code that measures it.

**A measurement that could not be made is never a zero.** A coordinate outside California
is reported as not measured, not as uncovered. A territory with no placed records has no
boundary-proximity bands, not a row of zeros.

**Nothing here touches infrastructure.** No pole, conductor, substation, or circuit
position is read, inferred, approximated, or published, from these sources or any other.
The CEC layers are administrative outlines. An analysis that would need an asset location
is not built here.

**No utility is compared to another.** Every published collection declares the order it
comes out in, `assert_collections_are_ordered_as_declared` refuses one that is out of
that order, and a collection missing from the ledger refuses the artifact rather than
publishing in whatever order it happened to come out in. Name order is the rule. Four
collections are deliberately not in it, each carrying its reason beside the declaration:
`contested_groups` is largest first, because a row there is a combination of outlines
rather than an entity and a name order cannot select the largest;
`placement_coverage.rates` is the four outcomes in the order the report reads them;
`sensitivity.type_inclusion.variants` puts the rule as built first, because every other
row is published as a difference from it; and
`sensitivity.repair_strategy.strategies_compared` follows `REPAIR_STRATEGIES`, chosen
repair first. `assert_no_ranking` refuses an artifact key that scores or grades, and
`tests/test_published.py` reads the generated report for comparative phrasing.

**An acquisition that fetched part of a dataset must not report as complete.** Each layer
is asked for its own record count before and after the walk, identifiers must come back
strictly increasing and unique, and a walk that fails any of those writes nothing. The
DINS walk is [`perimeter`](https://github.com/ChelseaKR/perimeter)'s, pinned to a commit;
these checks are applied to its output rather than assumed of it.

**A refresh of the pin is compared against what it replaces, value by value.** A
published number changing is fine. A published number changing quietly is not, and the
only difference between the two is whether anybody measured it. The comparison is a
command now rather than an act of care:
`python -m wildfire_service_territory_overlap.artifact_diff OLD.json NEW.json` walks every leaf of both
artifacts, reports what moved with its path and its old value, and refuses to pass if
published values disappeared unless `--allow-removals` names the removal deliberate.
The refresh of 2026-08-17, which added the county field, was compared this way by hand
before the command existed: 4,370 published values, none removed, none changed.

## Relationship to `perimeter`

[`perimeter`](https://github.com/ChelseaKR/perimeter) measures the completeness of the
DINS file itself: how many cells in each field hold a value, how many hold a code meaning
unknown, how many hold nothing. This project takes the file as given and asks a different
question, about geography rather than about fields, and consumes `perimeter` as a
dependency rather than re-implementing its acquisition. Nothing here repeats a
measurement published there.

The rule is consume, do not re-implement, and where it cannot be kept the reason is
written down rather than left as a local workaround nobody revisits. `docs/UPSTREAM.md`
holds the audit of 2026-09-05, read against the commit this project pins: four gaps in
the acquisition, the code here that compensates for each, and the upstream change that
would let the compensation go. None of the four has been sent upstream.

## Layout

Two of these modules open a socket, and both are marked. Every other module in the
package reads files already on disk. A test derives that set by reading which modules
import a network reader and refuses this block if it names a different one, so the mark
cannot go stale the way it did between 2026-09-08 and 2026-09-09.

```
src/wildfire_service_territory_overlap/
  sources.py     provenance and the publishers' own caveats, quoted
  acquire.py     OPENS A SOCKET: the retrieval; run by hand, never in CI
  refresh.py     OPENS A SOCKET: has the pin gone stale, and the deliberate refresh
  geometry.py    the pinned projection, the validity ledger, boundary distances
  placement.py   the four outcomes, and the schema guard on the retrieval
  intervals.py   Wilson and Newcombe; the only route a proportion takes to an artifact
  measure.py     the measurements, and a written record of the ones not built
  sensitivity.py the judgment calls, re-run against every alternative
  cross_check.py one county's own inspection records against this project's counts
  artifacts.py   the publication rules, enforced before anything is written
  artifact_diff.py  what a refresh moved, leaf by leaf, or the run does not pass
  catalog.py     the report's words, so the renderer carries none of its own
  report.py      the generated document
  cli.py         the build: files on disk in, both artifacts out
published/       measurements.json and REPORT.md, from the real retrievals
fixtures/        hand-written, never sampled from the real file
docs/adr/        the decisions, with their reasoning
```

## What still needs a person

- **Nobody with California utility service territory expertise has reviewed the inclusion
  rule.** What the rule costs is now measured, in `docs/adr/0006`: the unreviewed half of
  it moves the headline by 0.065 points. What is not established is whether any named
  entity in the layer operates a distribution system, and this project deliberately does
  not decide that. A reviewer would be checking the publisher's classification, not this
  code. What that review could change is now bounded on one side: 35 of the 59 indexed
  outlines hold no record at all, 0 records fall inside any of them, and removing all 35
  at once changes the outcome of 0 records, so a disagreement about any of those 35 moves
  nothing published here. The other 24 are where the question would matter, and it is
  still open there. See `docs/adr/0010`. The question those 24 raise is now written out
  as a packet a reviewer could answer in an afternoon,
  `docs/outreach/inclusion-rule-review-packet.md`, carrying each outline's published
  `Type` value, what the alternatives were measured to be worth, and the term that any
  finding lands as a new sensitivity row rather than as an edit to the rule. That term is
  now something a reviewer can exercise without anybody editing Python on their behalf:
  `--inclusion-rule FILE` takes a small JSON document naming the reading, the reviewer's
  role and the date, runs it to completion over the whole record set, and publishes it as
  one more row with its own denominator, interval and difference from the rule as built.
  The rule as built does not move and nothing is marked better. Nobody has read the
  packet. What is missing is the person, not the question.
- **The publisher documents none of the six `Type` values.** As retrieved, the layer
  metadata carries no field description and no coded-value domain, the FGDC record has no
  entity and attribute section, and no data dictionary is attached. The rule reads a field
  whose values are defined nowhere by the party that publishes them.
- **The overlap finding has not been raised with the publisher.** CEC's metadata invites
  reports of missing territories at the address in its own text; whether the overlaps are
  intended is not established here. Drafts for both that report and a request for the
  undocumented `Type` domain now exist under `docs/outreach/`; nothing has been sent, and
  when one is, the date and the outcome go into `PROVENANCE.md`.
- **Nothing has been checked against a county's own records.** The county cut is CAL
  FIRE's county field taken as published. Where a record's coordinate and its county
  disagree, this project reports the county the publisher recorded and does not correct
  it, because the correction would be a second opinion about where a structure is.
- **`.github/allowed_signers` names one principal**, the maintainer's release-signing
  key, checked against the GitHub API on 2026-08-17. A release tag verifies against that
  key or the workflow refuses at its first gate, and a comment-only signer list still
  refuses rather than verifying nothing.
- **Two CodeQL findings are accepted rather than fixed.**
  `actions/untrusted-checkout/medium` and `actions/cache-poisoning/poisonable-step`, both
  on the release build, written down with their reasoning in
  `.github/codeql-accepted.json`. Both reduce to one fact: the job runs a commit resolved
  from a workflow input, and the proof that the commit is a signed annotated tag on
  `main` lives in a prior job the queries cannot see. Every release workflow that builds
  the commit it releases carries them. Somebody who disagrees with that reading should
  say so; the entries are there to be argued with rather than to be forgotten.

## Standards conformance

Held to the portfolio's shared engineering standards, pinned in `.standards-version` to
`v2.0.0`. Every row states what is true, not what is intended, as of 2026-09-04. This
line carried 2026-08-17 while rows below it recorded 2026-08-28 and later, which is the
same kind of stale claim the CI/CD row was itself corrected for, so it is now held by a
test: `test_the_conformance_table_is_not_older_than_the_rows_it_carries` refuses an
as-of date earlier than any date the table records.

The applicability manifest has no entry for this repository, so nothing has decided which
standards bind it. The scoping below was derived here and a manifest entry supersedes it.

| Standard | State |
|---|---|
| Code Quality | Applies: uv, ruff, mypy `--strict`, pytest with branch coverage against a 90% floor, complexity capped at 10, `uv lock --check` as the drift gate and `uv sync --locked` as the install |
| Security & Supply-Chain | Applies: semgrep, gitleaks, pip-audit, CodeQL over actions and python, zizmor over the workflows, every action SHA-pinned, `permissions: contents: read` at the top of every workflow, `persist-credentials: false` on every checkout, and the release build writing no Actions cache. A CodeQL finding fails the job unless it is written down in `.github/codeql-accepted.json` with its reasoning, and an entry there fails the job once the finding it excuses is gone. Two entries today, both on the release build. osv-scanner reads the same lockfile against the OSV database in CI as a second feed beside pip-audit, the release build publishes a reproducible CycloneDX SBOM of its locked build environment next to the artifacts, and an OpenSSF Scorecard analysis uploads to code scanning weekly. Not met: nothing recorded |
| CI/CD | Applies (partially met): A branch ruleset on `main`, active 2026-08-22, blocks force push and deletion, requires every change to arrive as a merged pull request, and requires the six PR-facing checks green before merge. Not met: the ruleset carries one bypass actor, the repository admin role at `bypass_mode: always`, which is the maintainer's own account, so every check on that list can be skipped by the one account that pushes. This row claimed none until 2026-08-28, when the ruleset was read back with `gh api repos/OWNER/REPO/rulesets/21222489` and it was not none. The actor is deliberate and stays: the maintainer keeps an administrative way back into the repository. What was wrong was the claim, not the setting, so the correction is to this row. The release workflow stays dispatch-only by design |
| Observability | Applies (Tier C): A library and a CLI writing to stdout. No hosted service, no telemetry, no SLO surface. The operations runbook in `docs/RUNBOOK.md` states what every acquisition and publication refusal means and what to do about it. Not met: nothing recorded |
| Accessibility | Applies (partially met): Output is Markdown and JSON, with no rendered UI and no colour encoding. `docs/ACR.md` records a static structural review, re-run on 2026-09-04. Seven of its checks were asserted as reviewed once against one build and are enforced on every build now, through `artifacts.check_document`, which `artifacts.write_report` runs before the report is written, `tests/test_published.py` runs again over the committed document, and `tests/test_provenance_and_standards.py` runs over every Markdown document in the repository: a table with no header row, a table dropped in with nothing said above it, a row that does not carry the column count its header declares, an empty cell, a document opening below heading level one or skipping a level, a link labelled with a bare URL or with "here", and an ANSI escape or markup tag are each refused with `PublicationRefused`. Every one has a test that feeds it output breaking it and asserts the refusal. That review found and fixed a broken table row in itself; the widening of the gated set from three documents to all of them then found and fixed a mangled row in `docs/METRICS_LEDGER.md`, five empty cells in `docs/adr/0007` and three bare URLs in `docs/adr/0015`. It also found one table in `published/REPORT.md` that no sentence introduced, which was recorded rather than gated because a gate for it would have refused the published document, and was then fixed in that order: the renderer gained the sentence, `published/REPORT.md` was re-rendered from an unchanged `published/measurements.json`, and the rule went in behind the artifact that could pass it. Still not done: an assistive-technology pass over the generated tables, which none of this substitutes for |
| Internationalization | Applies (partially met): `docs/I18N.md` records the declaration and `docs/adr/0016` amends it. The strings the generated report prints on its own account are extracted into a declared, ordered English catalog in `catalog.py`; `report.render` takes a catalog as a parameter defaulting to the English one and carries no prose, which a test enforces by parsing the renderer and refusing any string a reader could read. A second edition is refused unless it holds the same keys and the same placeholder fields, and a test renders the whole report under one to hold every figure, both ends of every interval and the order of every row identical between the two. The numeric helpers take no catalog and no catalog entry may carry a format spec, so no edition can re-punctuate a figure, and the determinism gate is unchanged. Not met: no Spanish catalog exists, and one needs review by somebody who reads Spanish rather than generation, which `docs/adr/0016` states as a rule; the artifact's own row labels and notes are still English, inline in the modules that measure, so a second edition would print translated prose around English labels, and `docs/adr/0017` measures that gap at 28 strings of the artifact's 102 and recommends a way to close it without moving the artifact, proposed and not accepted; and numbers use a hard-coded decimal point with no locale awareness, deliberately, so that one artifact writes every figure one way |
| AI Evaluation | N/A: No model, no LLM, no generated text anywhere in the pipeline or the output |
| Quality & Metrics | Applies: Fail-closed gates throughout: the retrieval schema guard, the acquisition completeness checks, the publication rules, the coverage floor, a performance budget with its own test, and a determinism gate whose own failure modes are tested. Two publication rules were added after an audit found the gate that should have caught them numerically incapable of firing: `assert_contested_groups_are_whole` refuses an overlap table whose rows do not sum to the published contested total, and `assert_collections_are_ordered_as_declared` refuses a collection out of its declared order or with no declaration at all. The dash check now reads the whole repository rather than five globs, and the `verify` prerequisite list is parsed rather than grepped for, so a gate deleted from it fails a test. `docs/DEFINITION_OF_DONE.md` defines done by kind of change, and `docs/METRICS_LEDGER.md` records baselines and outcomes per stream. Not met: nothing recorded |
| Documentation | Applies: README, `PROVENANCE.md`, `CONTRIBUTING.md` including a first-change walkthrough that ends at a gate the reader has watched refuse, `SECURITY.md`, `CHANGELOG.md`, `CITATION.cff`, `docs/GLOSSARY.md` whose every relative link a test resolves, a `docs/adr/` log, this table, and a `.standards-version` pin a test reads. `make help` lists every target and a test refuses a target with no description. GitHub issue forms and a pull request checklist copied item for item from `docs/DEFINITION_OF_DONE.md`, which a test holds together |
| Release & Versioning | Applies: Version `0.1.0` in `pyproject.toml` and `CITATION.cff`, with a CHANGELOG entry for it. The signed annotated tag `v0.1.0` was cut from `main` and released through the hardened three-job workflow on 2026-08-23 UTC: `authorize` verified the tag signature against `.github/allowed_signers`, and `publish` attached the wheel, the sdist, the reproducible CycloneDX SBOM, and a build provenance attestation. Not met: nothing recorded |
| Responsible-Tech Framework | Applies: Unofficial framing on the README and on the generated report, no claim about any utility's posture, no address, parcel number, assessed value or coordinate republished, no ranking of any named company, and an acquisition that stops rather than routing around an access control. `docs/RESPONSIBLE-TECH.md` states the refusals as ethics content, names who each residual misreading lands on, and carries a review date. Not met: nothing recorded |
| Performance | Applies: A CLI over local files. The full build runs in about 18 seconds, and now does twelve placements of the record set rather than one. It was about 50 seconds doing one, before the containment query was changed to narrow by bounding box and then test against a prepared geometry, which a test holds to answering exactly what the predicate form answers. The budget is recorded and enforced in `tests/test_performance_budget.py`: an offline fixture build must finish inside 30 seconds, generous by design because wall clock does not compare across machines; it exists to catch order-of-magnitude regressions over byte-identical inputs |
| Incident Response | Applies: `SECURITY.md` routes reports to GitHub private vulnerability reporting with a 72-hour acknowledgment target, defines severity levels fitted to what a defect could publish or sign rather than to uptime, and carries the secret-leak procedure with rotation ordered before history rewriting. Not met: nothing recorded |
| Data Governance | Applies (L1, handled above the tier): Openly licensed public civic data, republished only as counts. `data/raw/` is gitignored, the address and parcel columns are never fetched, fixtures are hand-written rather than sampled, and a test refuses a published artifact carrying a coordinate. Refreshes are deliberate and hand-run, at least annually and on three triggers written out in `PROVENANCE.md`, each compared against the artifact it replaces before anything is committed. Not met: nothing recorded |
| AI Development Measurement | Applies: Baseline and outcome metrics for each development stream are recorded in `docs/METRICS_LEDGER.md`, including the stream that predates instrumentation, which is recorded as unmeasured rather than reconstructed |

## Licence

Apache-2.0. Source data is published by CAL FIRE under a Creative Commons Attribution
licence and by the California Energy Commission under its own conditions of use, and is
reproduced here only as counts.
