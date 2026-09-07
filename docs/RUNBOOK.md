# Operations runbook

This repository has exactly one operational surface: a by-hand acquisition, a local
pipeline over it, and the gates around both. No hosted service, no telemetry, no SLO
surface. What follows is what to do when each piece refuses, because every refusal in
this project is deliberate and each one means something specific.

Unofficial. Nothing here speaks for CAL FIRE, the California Energy Commission, or any
electric utility.

## The two builds, and which one is which

- `make report` builds `published/` from `data/raw/`, which exists only on a machine
  that has run `make acquire`. This is the real tree.
- `make report-offline` builds into `build/offline/` from the committed fixtures and
  marks its output with `"is_fixture": true`. It runs anywhere, offline, in about a
  second, and it is what CI measures.

A fixture build can never be mistaken for the real one because the flag travels inside
the artifact itself. Never point `--out` at `published/` while passing `--fixture`.

## A deliberate refresh, start to finish

Triggers and cadence live in `PROVENANCE.md`. The procedure:

1. Set the current artifact aside for comparison:
   `cp published/measurements.json "$OLD"` where `$OLD` lives outside the repository.
2. Run `make acquire`. Network, by hand, never from CI. It writes `data/raw/`.
3. Update `src/wildfire_service_territory_overlap/sources.py`: the new retrieval dates, SHA-256 hashes, byte
   counts and feature counts. The tests hold `PROVENANCE.md` and `README.md` to agree
   with that file, so the document cannot be updated without the source record, or the
   other way round.
4. Run `make report`.
5. Compare: `python -m wildfire_service_territory_overlap.artifact_diff "$OLD" published/measurements.json`.
   Changed and added values are expected on a real refresh; removed values stop the
   run unless `--allow-removals` names them deliberate. Exit `2` means the comparison
   did not happen: `$OLD` and the new artifact are the same file, one of them is not a
   JSON object, or the two carry no values between them. Read the stderr line; do not
   re-run with `--allow-removals`, which accepts removals and not an empty comparison.
6. Read the generated `published/REPORT.md` end to end. The figures are checked by
   machinery; whether they still say something coherent is not.
7. Write a dated section into `PROVENANCE.md` saying what moved, sizes included,
   following the 2026-08-17 pattern. Update the README status line if the headline
   moved. Add a `CHANGELOG.md` entry.
8. Commit `published/` and the source-record edits together. Never commit
   `data/raw/`.

## The bounded county cross-check

Roadmap item 3.4. One county's own inspection records against this project's counts for
that county, as agreement and disagreement counts. The comparison is decided in
`docs/adr/0015`; read it before running any of this, because it settles what agreement
means and what the result is not allowed to be turned into.

**The source is not pinned, and after a finished search that is a decision rather than a
gap.** No county inspection record set exists in this repository. `sources.py` carries
four sources and none of them is a county's own survey, `data/raw/` holds no such file,
and `src/wildfire_service_territory_overlap/acquire.py` has no route that fetches one.
`docs/adr/0018` says why: the one California county set that meets every criterion names
its fires differently from CAL FIRE, so the comparison joins nothing and refuses. The
command below runs the moment a joinable file exists. Everything in this section is a
hand-run step.

### 1. Choose the county

ADR 0015's four criteria, all of which must hold: the county is named as the collector
rather than the host; the set is distinct from CAL FIRE's rather than a merge that
already contains it; it can be retrieved whole and hashed; and it can be read without
fetching an address, a parcel number, a coordinate, or an assessed value. A county GIS
hub carrying CAL FIRE's own assessment fails the first two, and comparing against it
would report a file agreeing with itself.

**This step is already done and its answer is in `docs/adr/0018`.** The search finished
on 2026-09-05. Read that decision before repeating any of it: it enumerates what was
queried, records that no California county publishes on `data.ca.gov` at all, and says
which of Santa Cruz, Sonoma, Los Angeles, Butte and Napa fails which criterion. One set
meets all four, Napa County's own ATC damage assessments for 2020, and it is still not
pinned because the two organisations name the same fires differently. A candidate is
worth the afternoon only if it carries CAL FIRE's incident name or number, or if a
county has answered an ask with counts by fire.

### 2. Acquire it by hand and pin it

There is no automated route and there should not be one until a stable endpoint is
known. Download from the county's own publication, then:

- add a `Source` entry to `src/wildfire_service_territory_overlap/sources.py` with the
  real endpoint, item id, feature count, byte count and SHA-256 of the file you actually
  downloaded, and at least one quoted publisher caveat with what was measured from it,
  which `tests/test_provenance_and_standards.py` requires;
- restate all of it in `PROVENANCE.md`, which the same tests read back;
- update `tests/test_cross_check.py`, whose last test names the four pinned sources so a
  fifth cannot appear without somebody saying what it is.

If the only obtainable form of the county's records carries addresses or parcel numbers,
the item does not ship. Ask the county for counts by fire instead, and record the ask the
way `docs/outreach/` records the others.

### 3. Reduce it to what is compared

The command reads two fields and only two: `county` and `incident`, as a JSON array of
objects. Strip every other column, especially anything locating, before the file reaches
the command. The stripped file is a working file: it is not committed, and it is not
`data/raw/` either, which is reserved for retrievals `make report` reads.

### 4. Run it

```sh
python -m wildfire_service_territory_overlap.cross_check \
  --county "NAME" \
  --dins data/raw/dins_postfire.json \
  --external /path/to/county_inspections.json
```

Exit `0` prints one JSON block. Exit `1` is a refusal, explained below. Exit `2` means an
input could not be read at all.

The block is not published by running this. It is not written into `published/`, and
`cli.py` does not call this module. Record the counts in a dated `PROVENANCE.md` section.
Publishing them is a separate, deliberate change that goes through the refresh procedure
above and adds `$.county_cross_check.incidents` to `artifacts.ORDERINGS` in the same
commit, because a published collection with no declared order refuses the artifact.

### What each refusal means

All of these exit `1` with `cross-check refused:` and leave nothing written.

**`the external record set is not a list of rows` / `row N ... is not an object`.** The
file is not the shape the command reads. Convert it to a JSON array of objects carrying
`county` and `incident`.

**`the external record set holds no rows`.** An empty file is not a county that
inspected nothing. Reading it would report every fire as a disagreement, which would
publish a retrieval fault as a finding. Re-acquire.

**`row N ... carries 'siteaddress'` (or any locating column).** The file carries
something that could place a structure. This project does not read an address, a parcel
number, or a coordinate from anybody and a cross-check is not an exception. Strip the
column, or go back to step 2 and ask the county for counts by fire.

**`row N ... names no county` or `names no fire`.** A row that cannot be compared is
refused rather than dropped, because dropping it would shrink the external set where
nobody could see it. Fix the file or ask the publisher what the blank cell means.

**`row N ... names X and the comparison was asked for another county`.** The file covers
more than the one county. Scope is one county by decision, not by convenience, so the
file is not silently filtered down to it. Either ask for the single county's extract or
split the file yourself and say in `PROVENANCE.md` that you did.

**`this project's record set carries no record under the county name X`.** Either the
name is spelled in a way CAL FIRE's `COUNTY` field does not use, or the county genuinely
has no records in the file. Check the spelling against the county cut in
`published/REPORT.md` first.

**`this project measured X as not measured`.** The county has records and none of them
has a usable coordinate, so the county cut publishes no share for it. A comparison here
would describe the coordinate filter rather than either record set. Nothing to do except
record that the county is not cross-checkable.

**`the comparison names N distinct fires and the whole record set names M`.** The
external file names more distinct fires than CAL FIRE's entire statewide file does. That
is the wrong file, or the wrong column read as the fire name, not a large disagreement.
Check which column the county calls the incident.

**`... and not one name is shared`.** Both files name fires in this county and no name
appears in both, so the comparison joined nothing and every fire fell into a
disagreement bucket. This is ADR 0015's "defect, not a finding" reaching you as a
refusal rather than as a block you might have pasted somewhere. It is the state the one
eligible county set found so far is in: `docs/adr/0018` records that Napa County names
`GLASS COMPLEX 2020` where CAL FIRE names `Glass`, and that Los Angeles County names
`Bobcat Fire` where CAL FIRE names `Bobcat`. Check the incident column against the
county cut in `published/REPORT.md`, then read ADR 0018 before doing anything to the
names. Pairing two spellings by hand is not a fix available here.

**`the retrieval is missing COUNTY, ...`.** The schema guard, reached through this
command instead of through a build. Same meaning and same fix as the `SchemaError`
entry below.

### Reading the result

Agreement is `in_both`. The three disagreements mean three different things and are not
summed:

- `here_under_another_county` is the only one that bears on the county cut, and it bears
  on CAL FIRE's `COUNTY` field rather than on code here. A large count is a published
  limit on the county cut of ADR 0009.
- `absent_from_this_record_set` and `not_named_by_the_county_record_set` are inspection
  scope. A fire the county inspected outside the state responsibility area was never
  going to be in CAL FIRE's file.
- An agreement of zero across fires both organisations plainly worked is a defect in the
  comparison, most likely a name that does not match for a mechanical reason. You will
  not see one in a printed block: since 2026-09-05 the command refuses that case outright
  rather than leaving the reading to whoever meets it.

## When acquisition refuses

All of these come from `src/wildfire_service_territory_overlap/acquire.py`, and all of them leave `data/raw/`
without a file you can trust.

**`AcquisitionBlocked`: a 401, 403 or 429, or an access control on the route.**
Stop. Do not retry in a loop and do not route around the control; routing around one
would convert a public-data project into an unauthorized one. Wait, re-read the
publisher's terms and dataset page, and raise it with the publisher if the block looks
like a misconfiguration. A 429 means back off on human timescales.

**`AcquisitionFailed`: an HTTP error status, an error payload, or a refused endpoint.**
Retry once after a few minutes in case it was transient. If it persists, it is the
publisher's service telling you something; treat the day as a bad day for acquiring,
not as a problem to solve with more requests.

**`IncompleteAcquisition`: the layer's own record count disagrees before versus after
the walk, or identifiers came back duplicated or not strictly increasing.** The walk
fetched part of a dataset and cannot prove otherwise, so nothing it produced may be
measured or published. Delete everything under `data/raw/` from that run. Re-run later;
if it fails the same way twice, suspect the pinned `perimeter` walk rather than the
network: check whether the pin still matches upstream, and take the discrepancy to
that repository instead of re-implementing the walk here with the same defect.

**`SchemaError` at build time: the retrieval is missing a column every measurement
reads.** This is an acquisition fault surfacing late, almost always a publisher-side
field rename or removal. Re-acquire. Do not measure what is left, and do not edit
`REQUIRED_COLUMNS` to make the error go away until the change is confirmed on the
publisher's own layer metadata; if a column is gone for good, that is a pipeline
change and it triggers a full refresh with a dated `PROVENANCE.md` entry explaining it.

## When a gate refuses

**`tools/determinism.sh` reports a difference.** Two builds over byte-identical inputs
produced different bytes, which means nondeterminism entered the pipeline: an
unordered iteration, a timestamp, a set leaking into output order. Fix the code. The
gate does not have a tolerance setting because there is no acceptable amount.

**`PublicationRefused` during `make report`.** One of the publication rules caught the
artifact: a rate without its denominator or interval, a not-measured rate carrying a
value, a locating field, a collection long enough to be a record listing, a ranking
key, or territory rows out of name order. The fix is in the measurement that produced
the shape, never in the rule. Loosening a rule to let a number through is the one
failure mode this repository exists to prevent.

**Coverage below 90.** Add tests for whatever landed uncovered. Lowering the floor is
not among the options.

**`uv lock --check` fails.** The lockfile and `pyproject.toml` disagree. Re-lock
deliberately, review the resolution, and commit both together.

## Re-reading the protection on `main`

The conformance table states what the branch ruleset does. Nothing in this repository
can check that from a test: the ruleset lives in repository settings, and the test suite
runs offline against committed files. So it is re-read by hand, and the command is here
rather than in somebody's memory.

```sh
gh api repos/OWNER/REPO/rulesets --jq '.[].id'
gh api repos/OWNER/REPO/rulesets/RULESET_ID \
  --jq '{enforcement, bypass_actors, checks: [.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]}'
```

Three things have to agree with the README's CI/CD row: `enforcement` is `active`, the
six contexts are all present, and `bypass_actors` is what the row says it is. On
2026-08-28 the third disagreed. The row had said `with no bypass actors` since it was
written; the ruleset carried `RepositoryRole` 5, repository admin, at `bypass_mode:
always`. The row now says so. A required check that the one account which pushes can
skip is a required check by agreement rather than by configuration, and the difference
only shows up if somebody reads the setting back.

Re-read it on every refresh of the pin, and whenever the conformance table is touched.

## What must never happen

- `data/raw/` is never committed, at any granularity, ever.
- `published/` is never edited by hand. If a figure is wrong, the pipeline is wrong.
- Fixture output never becomes `published/` output.
- The fetched field list never grows without `sources.py`, `PROVENANCE.md`, and the
  schema guard moving together; the provenance test reads all three against each
  other precisely so that collection stays disclosed.
- The cross-check is never run against a county file carrying an address, a parcel
  number or a coordinate, and the refusal that stops it is never worked around by
  renaming a column.
