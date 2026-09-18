# 17. Proposed: the document's row labels come from the edition, and the artifact keeps its own English

Date: 2026-09-05

## Status

**Proposed.** Nothing here is decided, and nothing in this repository behaves as though
it were. This document extends `docs/adr/0016` and amends none of it. `docs/I18N.md`
still records the artifact's own strings as an open gap, because that is what they are.

What shipped alongside this proposal is the census the argument rests on and the tests
that hold it, in `src/wildfire_service_territory_overlap/catalog.py` and
`tests/test_catalog_and_editions.py`. No published figure moved and no file under
`published/` was touched.

## Context

`docs/adr/0016` moved every string the report prints on its own account into a catalog,
so that a second edition is a catalog rather than a second renderer. Under "What this
does not decide" it named the half it did not reach: the row labels, the measurement
notes, the county note and the type-field note are written in the measuring code, land
inside `measurements.json`, and are read straight back out of it by the renderer.
Translating them would give each language its own artifact, which is the opposite of the
property that makes two editions trustworthy, that both render from one artifact.

Issue #56 sketched three ways out and asked for a decision. What none of the three had
was a measurement. This document measures them, in a scratch directory, against the
committed pin.

Two things in that framing are narrower than the repository turned out to be, and both
matter to the argument below.

- The strings are not only in `measure.py`. Six modules author prose that reaches the
  artifact: `measure.py`, `sensitivity.py`, `sources.py`, `intervals.py`, `geometry.py`
  and `cli.py`. One string is written twice independently, in `measure.py` and as
  `sensitivity.CONTESTED_LABEL`, and nothing holds the two equal.
- The tool that would refuse the change is not `tools/diff_artifacts.py`. Item 2.1 of
  `docs/ROADMAP.md` named that path; it shipped as the module
  `wildfire_service_territory_overlap.artifact_diff`, and that module is what was run
  here.

## What was measured

Every figure below comes from the committed `published/measurements.json` and
`published/REPORT.md`. The artifact carries 6,582 leaves, which is what
`artifact_diff` reports when it compares the file with itself. Of those, 1,205 sit under
a field whose value is a sentence somebody in this repository wrote. That is 18.3% of
the artifact by leaf count, 960 of them non-empty, and 102 distinct strings.

Ten fields carry them, and the renderer prints six of the ten. Empty leaves are counted
because `artifact_diff` compares them like any other leaf, so a scheme that replaced
them would have to move them too.

| Field | Leaves | Non-empty | Distinct strings | Read by the renderer |
| --- | --- | --- | --- | --- |
| `label` | 561 | 561 | 59 | yes |
| `note` | 567 | 373 | 24 | yes |
| `geometry_note` | 59 | 8 | 1 | no |
| `variant` | 7 | 7 | 7 | yes |
| `question` | 5 | 5 | 5 | no |
| `reason` | 2 | 2 | 2 | yes |
| `affiliation` | 1 | 1 | 1 | no |
| `county_note` | 1 | 1 | 1 | yes |
| `no_trend_is_published` | 1 | 1 | 1 | no |
| `the_published_type_field_is_undocumented` | 1 | 1 | 1 | yes |
| Every field together | 1,205 | 960 | 102 | six fields of the ten |

The artifact carries 37 string-valued fields in all. The other 27 are publisher data, a
retrieval date, a landing page, or a machine token such as `measured` or
`wilson-score-95`. None of those is translated in any edition: a name is reported as
published, and a token names a method rather than describing one.

**The number that decides this is the last column.** Of the 102 distinct strings, 28
reach `published/REPORT.md`, carried by 65 of the 1,205 prose leaves. The other 74
strings never leave the JSON. A reader of the Spanish document would meet 28 English
strings, not 1,205 English leaves, and `tests/test_catalog_and_editions.py` now holds
that count against the pin so this paragraph cannot go quietly out of date.

Thirty of the 102 are assembled at build time rather than written whole: 8 carry a
distance band, 20 carry a published `STRUCTURECATEGORY` value, and 2 carry a repair
strategy's name. The category values come from the publisher's data, so that family
cannot be enumerated ahead of time. None of the 30 is among the 28 the document prints.

## What the refusal actually does

`artifact_diff` refuses removed keys, so replacing a label string with a key is a
removal. Four candidate artifacts were built from the published one by transformation in
a scratch directory and compared with it.

| Candidate | Compared | Added | Removed | Changed | Exit |
| --- | --- | --- | --- | --- | --- |
| the published artifact against itself | 6,582 | 0 | 0 | 0 | 0 |
| option 1, key plus arguments replacing the words | 8,103 | 1,521 | 1,205 | 0 | 1, refused |
| option 1, arguments baked into the key | 7,787 | 1,205 | 1,205 | 0 | 1, refused |
| option 2, key beside the words | 8,103 | 1,521 | 0 | 0 | 0 |

The refusal is a stop sign the deliberate-refresh procedure is built to carry, not a
wall. Re-run with `--allow-removals` and the third row exits 0 with this verdict:

```
7787 values compared: 1205 added, 1205 removed, 0 changed.
1205 published values were removed, and --allow-removals accepted the removal. Say why in PROVENANCE.md.
```

That is the tool working. It is also 1,205 removals in a change that measures nothing
new, and step 7 of the refresh procedure would have to explain them in `PROVENANCE.md`
next to a refresh that moved no figure.

**The second cost was not visible until it was run.** `label` is one of
`artifact_diff.IDENTITY_KEYS`, and 72 of the artifact's lists pair on it, uniquely, in
all 72. Take the label away and every one of those lists falls back to positional
pairing. Reversing every `rates` list and re-comparing shows what that is worth.

| Artifact, compared with its own `rates` lists reversed | Values reported changed |
| --- | --- |
| the published artifact | 0 |
| option 1, key plus arguments | 624 |
| option 1, key plus arguments, with `label_key` added to `IDENTITY_KEYS` | 604 |
| option 1, arguments baked into the key | 624 |
| option 1, arguments baked into the key, with `label_key` in `IDENTITY_KEYS` | 0 |
| option 2, key beside the words | 0 |

Adding `label_key` to `IDENTITY_KEYS` does not repair the parameterized scheme, because
a parameterized key repeats inside its own list: `label_key` is unique row to row in 1
of the 72 lists where `label` is unique in all 72. Only baking the argument into the key
restores it, and that is the scheme whose keys cannot be enumerated ahead of the
publisher's category values.

## The options, as measured

**Option 1, keys in the artifact and words in the catalog.** 1,205 leaves removed and
1,205 or 1,521 added, refused by `artifact_diff` until `--allow-removals` names the
removal deliberate. It needs a full rebuild through the refresh procedure, and it takes
away the one thing that says what each published row counted. A reader who opens
`measurements.json` on its own would get `label_key` slugs and would have to fetch a
second file to learn what was measured. Every other honesty device in this artifact,
`state`, `note`, `denominator`, `interval_method`, exists so that the record explains
itself where it is read. Keys undo that.

**Option 2, both in the artifact.** Passes clean: nothing removed, exit 0, keyed pairing
untouched. It adds 1,521 leaves, growing the artifact by 23% for no new measurement, and
it publishes the same fact twice, once as a key and once as the words the key already
stands for. It still needs a refresh to land, and the English words stay in the artifact
anyway, which was the objection option 1 was reaching for.

**Option 3, leave it.** Costs nothing and is true. It also leaves the 28 strings in
front of a Spanish reader with no route to ever move them, which is the outcome issue
#56 called half a Spanish edition.

**Option 4, the renderer names the row.** Not in issue #56, and it is where the
measurement points. `docs/adr/0016` already decided that the words the document prints
come from the edition and the numbers come from the artifact. A row label is a word the
document prints. The renderer takes it from the artifact today for no reason beyond
history: `report.rate_line` prints `node['label']` at 13 call sites, and the renderer
already reaches every one of those nodes by a path it hard-codes, so it already knows
which measurement it is printing. Give `rate_line` a catalog key at those call sites, and
do the same for the five other places the renderer reads artifact prose, and every word
in the document comes from the edition. Nothing in `published/` changes, no refresh is
needed, no removal is proposed, and `artifact_diff` is never asked to accept anything.

Option 4 has real costs and they are not small.

- The same sentence would exist twice, once as the artifact's `label` and once as the
  English catalog entry, with nothing holding them equal. That has to be a test: for the
  English edition, the row the renderer prints must equal the label the artifact carries
  at that node, or the two drift and the document starts describing a measurement by a
  name the artifact does not use. The repository already carries one instance of exactly
  this drift risk, unheld: the artifact's `affiliation`, written in `cli.py`, is the
  opening of the catalog's `header.unofficial`, the same sentences with different line
  breaks, and nothing checks that the two still agree.
- One of the 13 call sites is a loop over `placement_coverage.rates`, four rows at once.
  Naming those rows means the renderer pairing a declared key order against the
  artifact's row order. `report._edge_band_rate` shows
  the shape to avoid: it reads a band by its own number rather than by matching words,
  and a positional key list would be the opposite of that. The keys would need to be
  declared next to the code that writes the rows, not next to the code that prints them.
- A lookup table from the artifact's English to a catalog key cannot live in `report.py`.
  `tests/test_catalog_and_editions.py` parses the renderer and refuses any string a
  reader could read, and a dict literal of English labels is exactly that.

## Proposed decision

**Adopt option 4, and do not move the artifact.** The document's 28 remaining English
strings become catalog entries, reached by key from the point in the renderer that
already knows which measurement it is printing. `measurements.json` keeps its `label`,
`note`, `reason` and the rest exactly as they are.

**State that the artifact is one record in one language, and that this is a property of
the artifact rather than a defect of either edition.** English is the reference edition
in `docs/adr/0016`, and the artifact is written in it. Both editions render from that one
artifact, every figure in both comes from it, and its labels say in English what each row
counted for whoever opens the JSON. That is the same rule this project applies to a
publisher's name, which is reported as published and never translated.

**If the artifact is ever keyed anyway, key it option 2's way and never option 1's.**
Nothing is removed, the diff passes on its own terms rather than on an override, keyed
pairing survives, and the artifact keeps explaining itself to a reader who has only the
JSON. The cost is 1,521 leaves of redundancy, and that is a smaller price than a
published record that cannot be read without a second file.

**Whichever is chosen, the census is a gate.** `catalog.ARTIFACT_PROSE_FIELDS` and
`catalog.ARTIFACT_DATA_FIELDS` name every string-valued field the artifact carries, and
`catalog.unclassified_string_fields` refuses one that is in neither. A new field carrying
a sentence is a decision about editions, and this makes the decision get taken when the
field is added rather than when somebody tries to translate the document.

## What this does not decide

**No Spanish catalog exists and nothing here creates one.** Issue #55 is still blocked on
a person who reads Spanish, and `docs/adr/0016`'s rule stands: a generated translation is
not a reviewed catalog and is never published as one.

**No renderer change is made here.** Option 4 is proposed and not built. The 28 catalog
entries do not exist, `report.rate_line` is unchanged, and `published/REPORT.md` is
untouched.

**Nothing decides that the artifact will never be keyed.** If a later reader of the JSON
needs a stable handle on a row that survives a reworded label, option 2 is the shape to
build, and the numbers above are what it costs.

## Consequences if it is accepted

The Spanish document becomes fully Spanish, apart from names the publisher wrote, which
stay as published in both editions. `published/measurements.json` never moves for a
translation, so the property roadmap item 4.2 rests on, both editions rendering from one
artifact, holds by construction instead of by care.

The renderer gains 28 catalog keys and the coupling that goes with them: it has to know
which measurement each row is, which today it learns by printing whatever the artifact
says. A test has to hold the English entry equal to the artifact's own label at each of
those nodes, or the two descriptions of one measurement drift apart.

`measurements.json` stays English. Anybody reading the artifact directly reads English
labels and notes, and that is written down as a decision here rather than left to be
discovered.

## What could not be determined

**Whether the English document comes out byte for byte identical under option 4 is not
measured.** The renderer change was not made, so nothing was rendered and compared. It
would be identical if each catalog entry is the artifact's string verbatim, but that is
an argument and not a run, and `docs/adr/0016` earned its consequences section by running
twelve comparisons rather than reasoning about them.

**Whether a real build reproduces any of the candidate artifacts is not measured.**
`data/raw/` does not exist on the machine this was written on, so `make report` could not
run. All four candidates were produced by transforming the published artifact in a
scratch directory, which is enough to measure what `artifact_diff` does with a shape and
is not enough to say a build would produce that shape.

**How much of the 74 strings that never leave the JSON a Spanish reader would want is not
measured, and cannot be by anybody here.** It is a question for the reviewer issue #55 is
waiting for.
