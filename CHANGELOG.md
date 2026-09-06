# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A status column on every phase table in `docs/ROADMAP.md`, held to the tree by a
  test** (issue #88). Twenty-seven rows across five tables recorded no state at all, so
  the document read as a list of intentions while sixteen of its items were built,
  merged and gated. That is how issues #69 to #87 came to be filed against work that
  already existed. Each row now opens with `**Shipped.**`, `**Partly shipped.**` or
  `**Open.**`, and the two rows that carried **Done.** inside their item cell no longer
  do, so an item's state is in one place. Two rows say plainly that they shipped in a
  different shape than they were written in: 0.3 is a required job rather than a step
  inside `verify`, and 2.1 is
  `src/wildfire_service_territory_overlap/artifact_diff.py` rather than the
  `tools/diff_artifacts.py` the row had named since it was drafted.
- **The status cells are refused when this repository contradicts them**
  (`tests/test_provenance_and_standards.py`). A shipped or partly shipped row has to
  name something that exists in the tree; every path any status cell names has to
  resolve, so the `tools/diff_artifacts.py` claim would have failed the build rather
  than standing for two weeks; a row marked shipped may not also say something is still
  open; a partly shipped or open row has to say what is outstanding; and an item the
  prose above the tables lists as still open may not have a row below saying it
  shipped. Five fabricated rows drive the five refusals, because a gate nobody has
  watched refuse is not a gate.
- **`docs/adr/0018`: the search for a county inspection source finished, and the answer
  is a negative with an address** (issue #53). Roadmap 3.4 has been waiting on a county
  record set that can be pinned. The supply of published California county data was
  enumerated rather than sampled: `data.ca.gov` carries 62 organisations and not one is
  a county, so the sets that exist live in ArcGIS portals, and three keyword sweeps
  bounded to California returned 477 distinct feature services. One is a county-collected
  wildfire structure inspection set carrying an incident name. Napa County Emergency
  Operations publishes "ATC Damage Assessments 2020 public", 1,685 records assessed by
  Napa County Building Division inspectors on ATC forms, with an incident name, an
  incident year, a posting and a structure type, and with no address, parcel number or
  assessed value anywhere in its schema. It meets all four of ADR 0015's criteria and it
  is **not pinned**: the county names its fires `GLASS COMPLEX 2020` and `NAPA LIGHTNING
  COMPLEX 2020`, CAL FIRE names the same two ground events `Glass` and `LNU Lightning
  Cmplx`, and neither county spelling appears anywhere in CAL FIRE's file. Agreement
  would be zero, which ADR 0015 already reads as a defect in the comparison rather than
  as a result. The ADR also records that this is not a Napa quirk: Los Angeles County
  names `Bobcat Fire` where CAL FIRE names `Bobcat`. Every candidate checked, and which
  of the four criteria each fails, is in the ADR so nobody repeats the search.
- **The comparison now refuses a pair of record sets that share no fire name**
  (`cross_check._refuse_a_comparison_that_did_not_join`). ADR 0015 said in prose that an
  agreement of zero across fires both organisations plainly worked is a fault to
  investigate and not a result to publish, and nothing enforced it: the command would
  print the block, and a block a command prints is a block a maintainer can paste into a
  document. It is the eighth refusal in the module and it is driven by two tests, one of
  them using the real Napa and CAL FIRE spellings. The refusal needs both sides to have
  named a fire in the county, so the existing case where this project counts no incident
  name there still publishes its share as not measured rather than refusing.
- **A review packet for the inclusion rule**, `docs/outreach/inclusion-rule-review-packet.md`
  (issue #52, roadmap item 3.3). The item was blocked twice over: it needs a domain
  reviewer, and a reviewer arriving had nothing to review. "Read the code and tell us
  whether the inclusion rule is right" is not an answerable request. The packet is the
  bounded version: one question asked 24 times, over the 24 indexed outlines that hold
  records, with each outline's name, its published `Type` value and its source layer.
  The other 35 are left out because `docs/adr/0010` establishes that they hold 0 of
  132,520 records and that removing all 35 changes the outcome of 0, so a finding about
  them cannot move a figure. It carries what the rule does, what each alternative
  reading was already measured to be worth, a response format, and the term the roadmap
  sets: a finding lands as a new sensitivity row beside the rule as built, not as an
  edit to the rule, so a reviewer knows their judgment gets published as a measurement
  rather than applied silently. Per-outline counts are not restated; the packet points
  at the report's territory table, and no damage rate for a territory appears in either.
  Nothing has been sent and nobody has reviewed it, which the document says in its first
  line. **Item 3.3 stays open. What is missing now is the person, not the question.**
- **A gate holding the packet to the artifact it quotes**, in `tests/test_published.py`.
  The 24 names, their types and their layers are derived from
  `published/measurements.json` and compared against the packet's table row for row, and
  every figure it quotes is derived rather than written out, the way #34 did for the
  README's headline figures. A refreshed retrieval that moves an outline in or out of
  the holding set fails the gate instead of leaving a reviewer working from the wrong
  list. Separate checks hold the list to name order, refuse any of the 35 by name,
  refuse a per-outline record count reaching the document, and refuse the loss of the
  sentence saying nobody has reviewed it.

### Fixed

- **Every commit pushed to `main` competed with every other for one CI slot, so a burst
  of merges could drop a verdict entirely.** `ci.yml` keyed its concurrency group on
  `github.ref`, which is `refs/heads/main` for every push, so every commit ever merged
  shared a single group. A group holds one running run and exactly one pending run; a
  third arrival evicts the pending one with no jobs ever dispatched. The commit that was
  waiting then has no run at all -- not a red check somebody can find, an absent one,
  which is the shape this repository is otherwise built to refuse.
  `cancel-in-progress` does not decide whether that happens, only whether the loss looks
  like a cancellation or like nothing. The key now carries `github.sha` on a push and
  stays per-ref on a pull request, so branch supersession is unchanged. `codeql.yml` and
  `osv.yml` are untouched: neither has a `push:` trigger, so neither has a queue to
  evict from. `scorecard.yml` is untouched for a different reason, recorded below.
- **The rule is now held by a test** (`tests/test_ruleset.py`), which already reads the
  workflows for the required-checks invariant. Any workflow with a `push:` trigger must
  key its concurrency group per commit and keep pull requests per-ref, so a workflow
  that gains a push trigger later cannot quietly share a slot.
  `test_the_push_workflow_sweep_did_not_collapse` fails if the glob or the filter finds
  nothing, because a rule that iterates an empty set passes without checking anything.
- **`scorecard.yml` keeps its ref-only key, as a recorded exception rather than an
  oversight.** CI-CD-STANDARD.md 11c allows one exactly where the newest run is the only
  one that matters: an OpenSSF score is a property of the repository, not of a commit,
  so a superseded run was not a different answer. The standard's test for the exception
  is that the workflow gates no merge, and
  `test_every_converging_exception_still_earns_its_place` enforces that here by reading
  the committed ruleset: if `analysis` ever becomes a required status check, the
  exemption stops being safe and the build says so. An exception list nobody re-checks
  is how a real offender keeps its pass.
- **`.github/workflows/ci.yml` described the branch ruleset as running `with no bypass
  actors`, and the gate that forbids exactly that claim never read the file.** On
  2026-08-28 the
  ruleset was read back, found to carry `RepositoryRole` 5 at `bypass_mode: always`,
  and `README.md`, `CHANGELOG.md`, `docs/ROADMAP.md` and `docs/RUNBOOK.md` were
  corrected. `test_no_document_claims_the_ruleset_carries_no_bypass_actor` was written
  at the same time to stop the claim coming back, over a hand-written set of three
  Markdown documents. The workflow's header comment carried the same sentence, was in
  none of the three, and went on asserting it for nine days -- through the merge that
  widened the *document* rules from three files to thirty-three, which did not reach
  this rule. The comment now states the actor, points at `.github/rulesets/main.json`,
  and says why the gate did not catch it.
- **The rule now reads every file in the repository that mentions the ruleset**, found
  by globbing root Markdown, `docs/`, `.github/` Markdown and `.github/workflows/*.yml`
  and keeping the ones that say `ruleset`, rather than by naming three. That is six
  files today; `test_the_ruleset_file_sweep_did_not_collapse` fails if either the glob
  or the filter goes empty and names both files the hand-written set had left out. The
  claim is tested in each file's own voice: inline code spans come out first, because
  `docs/RUNBOOK.md` quotes the false sentence inside backticks in the paragraph that
  records it having been corrected, and a rule that read a correction as a relapse
  would push the history out of the document to stay green. Both halves were verified
  by sabotage: restoring the sentence to `ci.yml` fails the claim rule, and deleting
  the workflow glob fails the sweep rule.

- **Both unsent CEC letters quoted a retrieval date this project no longer publishes**
  (adjacent to issues #50 and #51). `docs/outreach/cec-overlap-letter.md` and
  `docs/outreach/cec-type-field-request.md` were drafted in #14 against the 2026-08-17
  pins, and #15 moved the pins to 2026-08-23 in the very next merge. Both letters kept
  the old date through a rename, a catalog refactor and a re-render, because nothing
  read them. They are addressed to the California Energy Commission over the
  maintainer's name, so the number they carry is the publisher's own retrieval and it
  was wrong. Every other figure in both letters was checked by hand against
  `published/measurements.json` and held: the leaf-by-leaf diff of #15 recorded that no
  measured figure moved, and none had.
- **The overlap letter named entities the publisher's layer does not name.** Eleven of
  the twelve overlap combinations carried at least one shortened name (`Los Angeles
  DWP`, `SDG&E`, `Pasadena`, `Riverside`), which is not a string the recipient can look
  up in the layer the letter is about, and is not a string any gate can derive. The
  list is now the published names, in the artifact's own order, as a list rather than a
  paragraph, and it states in words that the combinations are all of them rather than
  the largest few. The counts did not move.
- **`PROVENANCE.md` said every request carried a User-Agent naming this project**
  (issue #58). Three of the four layers do. The DINS walk is `perimeter`'s, and
  `perimeter` reads its own name from a module constant no caller can pass, so those
  requests, the walk over the largest layer at 132,522 records, identify as
  `perimeter-coverage/0.1`. Measured on 2026-09-05 with the socket substituted. The
  document now says which requests carry which identity, two tests in
  `tests/test_acquire.py` hold both halves against the code, and the gap is recorded
  upstream-side in `docs/UPSTREAM.md` rather than worked around by reaching into the
  dependency's module constant.
- **A mypy override that could not fail** (issue #58). `pyproj.*` sat in
  `ignore_missing_imports` under a comment saying none of the three dependencies shipped
  type information. pyproj 3.7.2 ships `py.typed`, so the entry silenced nothing;
  `mypy --strict src` passes without it, measured 2026-09-05. The entry is gone, the
  comment says what is now true, and a test reads the list back against the installed
  packages so the next inert entry fails instead of accumulating. The two `perimeter`
  overrides stay, and were measured rather than assumed: dropping either one produces a
  real error at the pinned commit.
- **`docs/ROADMAP.md` item 4.3 stated a sequence nobody could execute** (issue #57). It
  read as though PyPI distribution waited only on `perimeter` cutting a release. The
  name `perimeter` on PyPI is held by an unrelated Django package from YunoJuno,
  checked against the PyPI API on 2026-09-04, so `perimeter` cannot publish under the
  name this project pins. That is `docs/adr/0014` one level down: the same failure that
  forced this project's own rename, in its dependency. The row now states the real
  sequence, two of whose three steps belong to the other repository.
- **The roadmap's status paragraph stopped at 2026-08-23** (issue #59) while the merges
  since went past it. A second dated paragraph records what moved, and records 1.6, 3.4
  and 4.2 as partway with the open half of each named and filed rather than as done.
- **`docs/METRICS_LEDGER.md` recorded 5,120 published leaves in the current pin.**
  `wildfire_service_territory_overlap.artifact_diff` compares 6,582 in the committed
  artifact, and has since the pin of 2026-08-23. The row is the one that says how big
  "nothing changed" is before a refresh needs to claim it, so a stale count there is
  worse than none. Corrected against the tool, with the prose share named beside it.

- **A table in `published/REPORT.md` that no sentence introduced** (issue #43). In
  "What the repair is worth", the placed-share table followed the transitions table
  with one blank line between them, so a reader going through the document in order met
  a second header row with nothing saying what it counts or how it differs from the one
  above. The renderer emits an introducing sentence now, as a catalog entry, and
  `published/REPORT.md` was re-rendered from an unchanged
  `published/measurements.json`. Three lines of prose moved and no measurement did; the
  artifact's sha256 is the same before and after, and `PROVENANCE.md` records the
  re-render as a re-render rather than as a refresh.
- **The conformance table dated itself 2026-08-17 while its own rows recorded later**
  (issue #47). The CI/CD row records a ruleset read back on 2026-08-28 and later rows
  describe gates added in September, under a line saying every row states what is true
  on 2026-08-17. It is the one line in the table that tells a reader how to read every
  other claim in it, and it was the claim nobody was checking. The line now carries an
  as-of date and
  `test_the_conformance_table_is_not_older_than_the_rows_it_carries` refuses an as-of
  date earlier than any date the table records. The check has been watched refuse.
- **`docs/METRICS_LEDGER.md` had a row missing three of its five cells** (issue #45).
  The "Next deliberate refresh" row read `superseded by the row above The refresh
  procedure in ...`: two sentences run together where the cell boundaries went missing
  in an edit. It has its five cells back, and its outcome is recorded as not measured
  because the stream has not run, rather than left blank.
- **`docs/adr/0007` left its corner cell and four share cells empty** (issue #46). The
  four empty cells meant "these rows decompose the 927 above", carried entirely by
  position, which is the one thing the accessibility review says this output does not
  do. They now say it in words. No measurement was added to a merged ADR: the shares
  were not computed and inserted, because a number appearing in a decision record
  today, dated to a census taken then, is a different kind of claim.
- **`docs/adr/0015` carried three bare URLs** and was merged that way hours earlier. A
  bare URL is read out character by character, and one of these was 66 characters of
  county website path. Found by widening the gated set below, not by reading.
- **`artifact_diff` no longer prints `Nothing was removed.` on a run that removed
  values.** With `--allow-removals` the verdict line fell through to the wrong branch
  and contradicted the `REMOVED` lines printed directly above it. The tool exists so a
  published value cannot disappear quietly, and its own summary said nothing had
  disappeared. It now names the count and points at `PROVENANCE.md`.
- **The overlap table can no longer be truncated silently** (issue #22).
  `contested_groups` keeps the largest 25 combinations and dropped the rest with no
  count, no rate and no line saying so. `assert_aggregate_only` could not catch it: its
  ceiling is never below 32 and the cap is 25, so the only length rule in the module was
  numerically incapable of firing on that collection. `assert_contested_groups_are_whole`
  now refuses an artifact whose rows do not sum to the published contested total.
  Nothing under `published/` moves; today's retrieval produces twelve combinations.
- **The claim that every collection is sorted by name was false** (issue #23), and in
  four places rather than the one the issue found. It is now a ledger,
  `artifacts.ORDERINGS`, which names the order of every published collection and the
  reason wherever that order is not by name, refuses a collection nobody declared, and
  is held against the README by a test.
- **The conformance table overstated the protection on `main`.** It said the branch
  ruleset carried no bypass actor. It carries one:
  repository admin at `bypass_mode: always`, which is the account that pushes. Read back
  from the API on 2026-08-28 and corrected in `README.md`, `CHANGELOG.md` and
  `docs/ROADMAP.md`; `docs/RUNBOOK.md` now carries the command that reads it back.
  The actor is deliberate and stays; the maintainer keeps an administrative way back
  into the repository. What was corrected is the claim, not the ruleset.
- **Three gates that could not report what they exist to report.** The dash check read
  five globs and never opened `.github/`, the `Makefile`, `tools/`, `fixtures/` or
  `CITATION.cff`; it now reads the repository. The `verify` gate list was checked with
  two substring greps that a deleted prerequisite could not fail; it is parsed now. The
  coordinate scan matched longitudes only, so a latitude in a published file was
  invisible to the one test that exists to see it.
- **A test that asserted a defect.** `test_contested_groups_are_counts_and_are_capped`
  passed `limit=1` over a fixture holding exactly one combination, which is a slice that
  removes nothing, so it exercised no cap while its name said it did. The cap is now
  exercised against a placement built to have one.
- **`docs/ACR.md` broke the rule it was asserting.** The row claiming that every data
  table has a header row carried four unescaped pipe characters inside a code span, so
  Markdown read it as five cells under a two-cell header and rendered the second half of
  the claim as extra columns. The pipes are escaped, and the rule that found it now
  reads that document on every run.

### Added

- **Five tests holding `docs/outreach/` to `published/measurements.json`**, in
  `tests/test_published.py`, following the pattern #34 established for the README.
  Every expected string is derived from the artifact rather than written down, so a
  deliberate refresh that moves a figure fails the build instead of silently
  invalidating an unsent letter: the retrieval dates, the record total, both headline
  shares, the inclusion rule restated in the publisher's own `Type` values, all twelve
  overlap combinations with their counts and their published order, the repaired
  outline count, the repair delta, the six published `Type` values and the exclusions.
  A sixth holds the drafts to being drafts, because a suite that guarded the figures
  while the status line quietly flipped to sent would be guarding the wrong thing.
  Every one of them has been watched refuse against a mutated letter.
- **`docs/UPSTREAM.md`, the audit behind roadmap item 4.4** (issue #58). The item was
  open as a place to record an acquisition gap when one appeared and nobody had looked.
  Read on 2026-09-05 against `perimeter` at the commit `pyproject.toml` pins, not
  against its `main`: four gaps, all in the acquisition, each written down with the code
  here that compensates for it and the upstream change that would let the compensation
  go. A fifth section records what was checked and found not to be a gap, so the next
  audit does not re-open it. Nothing has been sent upstream and the issue stays open;
  naming a gap is not fixing one. A test refuses a `docs/UPSTREAM.md` that names a
  different commit than the pin, because a dated audit against a moved pin is a dated
  audit of something else.
- **`docs/adr/0017`, proposed rather than accepted** (issue #56), on how the artifact's
  own row labels get an edition. The half of roadmap 4.2 that `docs/adr/0016` named and
  did not decide, measured instead of argued: 1,205 of the artifact's 6,582 leaves carry
  a string this repository wrote, 102 of them distinct, and 28 of those reach
  `published/REPORT.md`. Each option in the issue was built in a scratch directory and
  run through `wildfire_service_territory_overlap.artifact_diff`. Replacing the labels
  with keys removes 1,205 values and is refused with exit 1, which `--allow-removals`
  can carry; it also costs the diff its keyed pairing on 72 lists, which nothing carries,
  and a reordered `rates` list then reports 624 values changed where the published
  artifact reports none. Keys beside the words pass clean and add 1,521 leaves. The ADR
  recommends neither, and proposes that the renderer name the row from the edition while
  the artifact keeps its English. No published figure moved and nothing under
  `published/` was touched.
- **`catalog.artifact_prose` and `catalog.unclassified_string_fields`**, the census that
  proposal rests on. `ARTIFACT_PROSE_FIELDS` and `ARTIFACT_DATA_FIELDS` classify all 37
  string-valued fields the artifact carries, and a thirty-eighth arriving unclassified
  is refused, so the question of whether an edition will ever have to reach a field is
  asked when the field is added. Five tests, one of them watching the refusal fire, and
  the counts the ADR quotes are held against the pin rather than remembered.
- **`assert_every_table_is_introduced`** (issue #44), refusing a table whose nearest
  non-blank line above it is another table's row, and a table that opens a document.
  Added **after** the fix above rather than before it: the rule refused exactly one of
  thirty-four documents while the defect stood, and a gate is never introduced by
  editing the artifact it would refuse into shape. Four tests, two of them driving the
  two refusals.

- `--version` on the CLI (issue #16), resolved inside the flag rather than while the
  parser is built, so a build never asks. A version that cannot be read is reported as
  not measured on stderr with exit 1, never guessed.
- `--json` on `artifact_diff` (issue #20). Default output is locked byte for byte by a
  test, exit codes are unchanged, and the mode does not soften the removal refusal.
- `make help` (issue #17), with `.DEFAULT_GOAL := verify` declared so bare `make` still
  runs the gate. A test refuses a target with no description.
- GitHub issue forms and a pull request template (issue #19). The measurement proposal
  asks for the denominator as a required field.
- `docs/GLOSSARY.md` (issue #18). The `Type` entries state the conventional expansion
  and say the publisher documents none of the six values, because `sources.py` records
  exactly that. Issue #18 asked for Public Utilities Code 331.1 to be cited "as ADR 0002
  does"; ADR 0002 does not cite it, `sources.py` does, and the glossary cites the file
  that carries it.
- A first-change walkthrough in `CONTRIBUTING.md` (issue #21). Issue #21 asked for a
  step that renames a fixture territory and watches `make determinism` refuse. It does
  not refuse: determinism compares two builds of the same inputs, so an edited input
  changes both identically. The walkthrough sends that break at `make test`, says why
  determinism passes, and reaches the determinism refusal by making two build trees
  actually differ.
- **Publication rules over the rendered document** (roadmap 1.6, structural half).
  `docs/ACR.md` recorded ten structural checks over the generated report as reviewed
  once, on 2026-08-22, against one build of version `0.1.0`. A reviewed-once claim about
  generated output goes stale the moment the renderer changes. Six of them are gates
  now, in `artifacts.check_document`, called from the new `artifacts.write_report` so a
  document that breaks one is not written at all, and called again over the committed
  `published/REPORT.md` by `tests/test_published.py` because `published/` is built by
  hand where CI cannot rebuild it. `assert_tables_have_a_header_row` refuses a table
  whose first row is not sitting over a delimiter row; `assert_tables_are_rectangular`
  refuses a row that does not carry the column count its header declares, which is what
  a published territory name arriving with a `|` in it would produce;
  `assert_no_table_cell_is_empty` refuses a cell that reads as its column name followed
  by silence; `assert_headings_do_not_skip_a_level` refuses a document opening below
  level one or skipping a level; `assert_links_are_descriptive` refuses a link labelled
  with a bare URL or with "here"; `assert_nothing_is_carried_by_styling` refuses an ANSI
  escape or a markup tag. Every one is fed output that breaks it in
  `tests/test_artifacts.py`, and `docs/ACR.md` now separates what is enforced from what
  is still a person reading a document. Nothing under `published/` moves. The remaining
  half of roadmap 1.6, an assistive-technology pass over the generated tables, stays
  open; none of this is a screen reader and the review does not claim otherwise.

### Changed
- **The document rules read every Markdown document in the repository**, where they read
  three. `docs/ACR.md` named `README.md`, `PROVENANCE.md` and itself, and the two
  defects the review of 2026-09-04 recorded were both outside that set, as was the
  third found while fixing them. Reading three of thirty-three documents is a sample,
  and the documents it did not read were where the defects were. The list is globbed
  and a test refuses a glob that collapses.
- **`.claude/` is gitignored** (issue #48). Claude Code puts agent worktrees there, and
  a `git add -A` would have staged them.
- Renamed the project to `wildfire-service-territory-overlap` across the distribution, the package, and every
  command reference. The old PyPI name is held by an unrelated tool, which blocked the
  roadmap's distribution item independently of the `perimeter` pin; see
  `docs/adr/0014`. The v0.1.0 tag and release keep their original names and artifacts.
  No measurement changed: the published pair is byte-for-byte what the refresh of
  2026-08-23 wrote.

### Added

- **The bounded county cross-check, decided and built; its retrieval is not done**
  (roadmap 3.4, `docs/adr/0015`). `cross_check.py` holds one county's own inspection
  records against this project's counts for that county and reports agreement and
  disagreement per fire, in name order, with Wilson intervals on two shares that each
  keep their own denominator. Four outcomes, kept apart rather than summed: the fire is
  in both sets; this project records it under another county; this record set does not
  name it at all; the county's set does not name it. Nothing is corrected and neither
  side is treated as the truth, no rate is taken between the two record sets in either
  direction, and no damage rate is published for the county from either file.
  **No county inspection record set is pinned.** Nothing was downloaded or hashed,
  `sources.py` gains no entry, `published/` does not move, and the module is
  deliberately not wired into `cli.build`: a not-measured block in every build would be
  a section that says nothing on every run until the run where it says something. It is
  a command awaiting its retrieval, and `docs/RUNBOOK.md` carries the hand-run
  procedure and what each of its refusals means. A search on 2026-09-04 for a county
  publisher is recorded in the ADR as prose, including the negative half: the county
  datasets that are easiest to find are either CAL FIRE's own assessment hosted by a
  county, or address-level and parcel-level records this project refuses to fetch.
  Every refusal has a test that fires it, including the cap, which is computed from the
  record set rather than written down as a number and is driven past from both sides.
  `placement._key` became the public `fold_name` so the coordinate-county comparison
  and this one share one name normalisation instead of two that can drift.

- **The coordinate-county comparison** (`docs/adr/0013`). CAL FIRE's `COUNTY` field is
  now measured, not just trusted: 132,490 records carry both a usable coordinate and a
  label the new CDT county layer carries, 132,459 agree, and 31 (0.023%) sit outside
  the recorded county. None reaches no polygon and no label went unmatched. Counted,
  never corrected, with the boundary publisher's own warning about its errors quoted
  beside the numbers.
- **Representativeness by structure class.** The ninth fetched field,
  `STRUCTURECATEGORY`, runs the placed-versus-contested destroyed-share check inside
  each published class instead of only across the record set. No address-adjacent
  field was touched; the fetched-fields disclosure moved together with the schema
  guard, as the rules require.
- **The three-repair census over the real record set.** The structure repair sides
  exactly with linework: both differ from `buffer(0)` on the same 927 records, and
  structure against `buffer(0)` on none. The union bound did not move from 927.
- Draft letters to the CEC under `docs/outreach/`: one reporting the twelve measured
  boundary overlaps the publisher's own metadata invites feedback on, and one
  requesting written definitions for the six `Type` values that nothing published by
  the party using them defines. Both are marked draft and unsent; sending dates and
  outcomes belong in `PROVENANCE.md`.
- Edge bands for contested groups. Each overlapping combination now carries how
  much of it sits within 100, 250, 500 and 1000 metres of the nearest edge among the
  outlines involved, with its own denominator and Wilson interval: a contested record
  stops being contested when any outline in its combination ceases to contain it, so
  that nearest edge is what an approximation error moves first. A combination near
  100% at 250 metres is a thin seam between outlines; one near 0% is interior ground
  two published territories genuinely cover together. The report's overlap table gains
  the 250 metre column and still renders artifacts from before it existed unchanged.
- `main` is protected by a branch ruleset: force push and deletion refused, every
  change arriving as a merged pull request, the six PR-facing checks required green.
  One bypass actor stands, the repository admin role at `bypass_mode: always`. This
  entry claimed none until 2026-08-28, when the ruleset was read back from the API and
  it was not none. The ci.yml header paragraph that recorded the gates as
  reporting without blocking is rewritten to match.
- **The report's words are extracted into a string catalog** (`docs/adr/0016`, the half
  of roadmap 4.2 that was not blocked on a translator).
  `src/wildfire_service_territory_overlap/catalog.py` declares an ordered mapping from a
  stable key to one edition's string, and `report.render` takes a catalog as a parameter
  defaulting to the English one, so a second edition is a catalog rather than a second
  renderer. `catalog.translation` refuses an edition that misses a key, adds one nothing
  renders, holds an empty string, or changes the placeholder fields inside an entry;
  that last refusal is the one that matters, because `str.format` ignores a keyword
  nothing uses, so an entry that drops `{fire_records}` would render the sentence
  without the number and raise nothing. A test parses `report.py` and fails on any
  string a reader could read, and it was watched refuse a heading put back on purpose. A
  second test renders the whole report under a second catalog holding the same keys and
  different strings, and holds every figure, both ends of every interval and the order
  of every row identical between the editions. No `--lang` flag was added: a flag
  accepting one value is a menu with one item. `docs/I18N.md` now records what is true,
  including what is still not done, and the README conformance row moved with it.
  The English output did not move by a byte. `published/REPORT.md` still renders exactly
  from `published/measurements.json`, the offline fixture build is byte-identical to the
  build taken before the change, and the old and new renderers were compared branch by
  branch, including the two-repair rendering, the empty-transitions rendering and a tree
  in which nothing is measured.

### Changed

- The renderer's helpers split along the line between a number and a word. `report.pct`
  takes a rate rather than an optional one and `report.span` returns the two ends of an
  interval rather than one joined string, because the word between two bounds is
  language; `report.interval` and `report.rate_line` take the catalog, and the new
  `report.share` and `report.difference` hold the branch that prints words when there is
  no number. The numeric helpers take no catalog and cannot be given one, so no edition
  can punctuate a figure its own way. Nothing in the generated output moved.

## [0.1.0] - 2026-08-18

First release. One entry, because no earlier tag exists: the first measurement and the
work recorded against it before any tag was cut all ship together. Amended 2026-08-22,
before the tag was cut, to fold in the roadmap execution that shipped the same day.

### Added on 2026-08-22, folded in before the tag was cut

- The governance documents from Phase 1 of the roadmap:
  `docs/RESPONSIBLE-TECH.md` (dated ethics statement and residual-risk table),
  `docs/DEFINITION_OF_DONE.md` (done by kind of change),
  `docs/METRICS_LEDGER.md` (baseline and outcome per development stream, gaps
  recorded as unmeasured rather than reconstructed), and `docs/ACR.md` (a static
  accessibility conformance review of the generated output that says plainly it was
  not performed with assistive technology). `SECURITY.md` gains severity levels fitted
  to what a defect could publish or sign, plus the secret-leak procedure.
- ADR 0012, written before the data exists: when the second territory-layer
  retrieval lands, comparisons against the first are paired per-value diffs and
  per-record transition counts, never a modelled direction. Each snapshot keeps its
  own denominator, nothing is differenced into a single headline, and any figure
  spanning both retrievals dates its rows. The by-year cut keeps ADR 0008's no-trend
  rule unchanged within each snapshot.
- A third geometry repair in the sensitivity run. GEOS' structure-preserving
  `make_valid` joins `make_valid` and `buffer(0)` in `REPAIR_STRATEGIES`, the whole
  record set is placed under each, and the comparison publishes a pairwise
  disagreement count for every pair plus a union count bounding how much of the result
  the choice of repair can move. The default does not move; see `docs/adr/0011`. The
  committed `published/` tree still describes the two-repair run against the
  2026-08-17 pin and keeps rendering exactly as written; the three-repair census
  reaches it at the next deliberate refresh.
- A performance budget with a gate on it. `tests/test_performance_budget.py` runs
  the offline fixture build against a recorded 30 second ceiling, generous by design:
  wall clock does not compare across machines, so the budget catches order-of-magnitude
  regressions over byte-identical inputs rather than load noise.
- An operations runbook, `docs/RUNBOOK.md`: the refresh procedure start to finish,
  what each acquisition refusal (`AcquisitionBlocked`, `AcquisitionFailed`,
  `IncompleteAcquisition`) means and what to do, what each build-time gate failure
  means, and the things that must never happen.
- A refresh cadence and a staleness SLA, replacing the recorded absence of both.
  A pin is refreshed at least every twelve months and on three triggers: age of the
  retrieval against continuous fire seasons, a publisher-side last-modified date later
  than the pin on either territory layer, and any change to this pipeline itself,
  which cannot reach an old pin because `data/raw/` is never committed. Every refresh
  stays hand-run, is compared against the artifact it replaces with
  `python -m inspected.artifact_diff` before anything is committed, and writes what
  moved into `PROVENANCE.md`.
- `inspected.artifact_diff`: the leaf-by-leaf refresh comparison from
  `PROVENANCE.md`, promoted from a hand-run exercise into a command.
  `python -m inspected.artifact_diff OLD NEW` reports every added, changed and removed
  value at its path in both trees, pairs list rows by their identifying field where one
  exists so a reordered collection stays silent and a changed row stays attached to its
  name, and refuses to exit zero when published values disappear unless
  `--allow-removals` names the removal deliberate.
- An osv-scanner job in CI, reading the same `uv.lock` that `uv sync --locked`
  installs from, against the OSV database: a second vulnerability feed beside
  pip-audit, failing closed on any reported advisory.
- An OpenSSF Scorecard workflow, publishing results and uploading the SARIF to code
  scanning on a weekly schedule.
- A reproducible CycloneDX SBOM in the release build, generated over the locked build
  environment after `make verify`, attached to the release next to the wheels and
  covered by the provenance attestation.

### Added

- Placement coverage over CAL FIRE DINS against the California Energy Commission's
  published electric service territory outlines: how much of the wildfire record set
  falls inside exactly one territory, inside more than one, inside none, or carries a
  coordinate that cannot be used. Every share carries its denominator and a Wilson
  interval.
- A representativeness check between the placed and contested populations, with a
  Newcombe interval on the difference, so a reader can see whether the third of the
  record set that cannot be attributed resembles the two thirds that can.
- Per-territory counts in name order, with the share of each territory's placed records
  contributed by its single largest incident. No damage rate is published for any
  territory and no territory is ordered against another.
- Boundary-proximity bands at 100, 250, 500 and 1000 metres, operationalizing the
  publisher's statement that the boundaries are approximate.
- A geometry ledger naming the eight published polygons that arrive failing an OGC
  validity check, and measuring what share of the placed total depends on the repair.
- `artifacts.check_all`: publication rules enforced before anything is written. A rate
  without a denominator or an interval, a not-measured rate carrying a zero, a coordinate
  or parcel field, a collection long enough to be a record listing, a key that ranks or
  scores, or territory rows out of name order each refuse the write.
- Acquisition guards on top of the walk consumed from `perimeter`: the layer's own record
  count read before and after, identifiers required to be strictly increasing and unique,
  and nothing written when any of those fails.
- A schema guard on the retrieval, so a file fetched without `HAZARDTYPE` raises instead
  of filtering to zero fire records and producing an honest, empty, misleading report.
- **The county cut, and the pin refresh it needed.** `COUNTY` is the eighth field the
  acquisition requests, and the contested share is published per county with its own two
  denominators and a Wilson interval, in name order. 52 counties are named in the record
  set, 30 records carry no county name, and in 36 of the 52 counties the contested share
  is zero rather than merely low. No damage rate is published for a county, for the same
  reason none is published for a territory. See `docs/adr/0009`.
- **What the refresh moved: nothing.** The artifact built after the re-acquisition was
  compared against the one built before it at every published value. 4,370 values, none
  removed, none changed. The re-acquired DINS file is byte-for-byte the previously pinned
  file once the new column is removed, and both territory layers returned the hashes
  already recorded. `PROVENANCE.md` states this rather than leaving a reader to assume it.
- **What an outline that holds no record is worth.** 35 of the 59 indexed outlines hold
  no record; 0 of 132,520 records fall inside any of them; removing all 35 and placing
  the whole record set again changes the outcome of 0 records. This is a count, not a
  classification: it does not say whether any named entity belongs in the set, it says
  that for 35 of the 59 the answer cannot move a figure published here. See
  `docs/adr/0010`.
- `inspected.sensitivity`: the two judgment calls in this project, re-run over the whole
  record set and published with their denominators and intervals rather than argued for.
  - **The inclusion rule.** Seven readings of the publisher's `Type` field, each one the
    entire record set placed again. Reading `CO-OP` and `Tribal` as service territories,
    the unreviewed half of the rule, is worth 0.065 percentage points on the headline;
    dropping `Tribal` changes nothing at all; dropping `CO-OP` would publish 1,406
    records as inside no published territory. Reading `CCA` as a territory would take the
    contested share to 56.3% and `ADMIN` to 74.4%. The rule is unchanged. See
    `docs/adr/0006`.
  - **The geometry repair.** `make_valid` and `buffer(0)` both run to completion. 927
    records, 0.70% of the record set with an interval of 0.66% to 0.75%, come out
    differently; 770 move from placed to contested and 157 are contested under both but
    between a different pair of outlines. An earlier draft's note that the two disagreed
    on "roughly 770 placements" was a recollection and it missed those 157. See
    `docs/adr/0007`.
- Whether being unattributable is a property of the data or of the fire. 94.3% of the
  405 incidents in the record set fall entirely on one side of the contested line, with
  the contested share by incident year running from 0.0% to 92.5%. No trend is drawn
  through the years and the artifact says why: the territory layer is a single retrieval,
  so every year is measured against identical boundaries. See `docs/adr/0008`.
- That CEC documents none of the six `Type` values is stated in the output and in
  `PROVENANCE.md`, checked against the layer metadata, the FGDC record and the item
  resources on the retrieval date.

### Changed

- Containment narrows by bounding box and then tests against a prepared geometry, rather
  than calling `STRtree.query(predicate="intersects")`, which does not use a prepared
  geometry and re-walks every ring on every test. The full build runs in about 18 seconds
  doing twelve placements of the record set where it took about 50 doing one. A test
  holds the two forms to identical answers, and every published figure is unchanged.
- The Dependabot uv updater failed on every run and therefore checked nothing. The cause
  is a name collision rather than a broken pin: `perimeter` here is a direct git
  reference, and the name on PyPI belongs to an unrelated Django package. It is ignored
  in `.github/dependabot.yml` with that written out, because publishing under this name
  is not available and dropping the URL would resolve somebody else's package.
- The release build writes no Actions cache. `setup-uv` enables one by default on a
  hosted runner, which made the release job a cache write in the `main` scope readable by
  every other workflow, for no reuse a once-per-release build can collect. It does not
  clear `actions/cache-poisoning/poisonable-step`, which the first attempt assumed it
  would: running the workflow moved the alert to `make verify` instead. The query is
  about executing code from an untrusted checkout rather than about writing a cache, so
  every release workflow that builds the commit it releases carries it.
- The CodeQL gate now fails on any finding that is not written down in
  `.github/codeql-accepted.json`, and equally on an entry there whose finding has gone
  away. Two entries today, both on the release build and both reducing to the same fact:
  the job runs a commit that `authorize` has already proved is a signed annotated tag on
  main, which is a runtime check the queries cannot see.
- An interval whose two ends round to the same string is now printed at more decimal
  places until they differ. `0.7% to 0.7%` reads as certainty.
- The repair strategy and the set of included types are parameters on
  `geometry.load_territories`. `geometry.repair` refuses a strategy that is not in
  `REPAIR_STRATEGIES`, so a new repair cannot be used before it has been compared against
  the one in force.
- The per-year record counts moved from a standalone `years` block into the new
  measurement, where each year carries both its record count and the classified count
  that is the denominator of its share.

### Notes

- `perimeter` is consumed as a pinned git dependency rather than vendored. Its paged walk
  is the one this project uses for the damage inspections, and re-implementing it would
  mean re-implementing a defect that has already been found and fixed once.
- `data/raw/` is not in git and never will be.
