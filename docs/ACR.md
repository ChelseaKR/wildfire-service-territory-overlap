# Accessibility conformance review

First dated 2026-08-22, against the output of version `0.1.0` as rendered from the
2026-08-17 pins. Reviewed again on 2026-09-04, against the output rendered from the
2026-08-23 pins and against the renderer that produces it.

Both passes are static and structural. Neither was performed with a screen reader or
any assistive technology, and this document says so rather than implying otherwise;
that pass remains open and is listed under what was not done. Nothing below is a claim
about how these tables sound.

What the 2026-09-04 pass changed is where the checks live, not what they say. Ten
checks were recorded here in 2026-08-22 as reviewed once, on one build of one version.
A reviewed-once claim about generated output goes stale the moment the renderer
changes, and the renderer has changed twice since. The checks a build can ask are
asked on every build now, through the same refusal the publication rules use, and the
table below names the rule and the test for each. The checks that are a person reading
a document are still that, and are marked as such.

## What this project's accessibility surface is

Two generated artifacts, `published/REPORT.md` and `published/measurements.json`, plus
the repository documents around them. No web UI, no color, no images, no animation,
no time-dependent content.

## What was checked, and what holds it

Every rule named here lives in `src/wildfire_service_territory_overlap/artifacts.py`,
refuses with `PublicationRefused`, and runs from `artifacts.write_report` before the
document is written, so a report that breaks one is not written at all. `published/` is
built by hand from retrievals CI cannot see, so the committed document is put through
the same gate by `test_the_published_report_passes_every_document_rule` in
`tests/test_published.py`. Each rule also has a test in `tests/test_artifacts.py` that
feeds it output breaking the rule and asserts the refusal, because a check nobody has
watched refuse is not a gate.

| Check | State |
|---|---|
| Every data table has a header row (`\| Outcome \| Share \| ...`) | Enforced by `assert_tables_have_a_header_row`, which refuses a table whose first row is not sitting over a delimiter row. The delimiter row is the whole of what makes a row a header in Markdown. Refusal watched by `test_a_table_with_no_delimiter_row_is_refused` |
| Every table is introduced by a heading or a sentence, rather than dropped in bare | Enforced by `assert_every_table_is_introduced`, which refuses a table whose nearest non-blank line above it is another table's row, and a table that opens a document. Two tables one blank line apart are two tables on the page and one undifferentiated run to a reader going through in order. Refusal watched by `test_a_table_following_a_table_with_nothing_between_them_is_refused` |
| Table cells carry their own context (denominator columns sit beside share columns) | Partly enforced. `assert_tables_are_rectangular` refuses a row that does not carry the column count its header declares, so a value arriving with a `\|` in it cannot shift every later cell under the wrong column name; `assert_no_table_cell_is_empty` refuses a cell that would be announced as its column name and then silence; `assert_rates_are_denominated` keeps the denominator beside the share in the artifact the table is rendered from. Whether the column names are the right names is still a human reading |
| No meaning conveyed by color anywhere in the output | Enforced by `assert_nothing_is_carried_by_styling`, which refuses an ANSI escape sequence or a markup tag anywhere in the document. This was the basis the 2026-08-22 pass gave for the claim, and nothing was reading it |
| No meaning conveyed by shape, size, or position alone | Partly enforced. `assert_collections_are_ordered_as_declared` refuses a collection published in an order nobody declared, and `ORDERINGS` carries the reason for each of the orders that is not by name. Whether each row is self-describing once read out of its table is a human reading |
| Not-measured values render as words ("not measured"), never as blank or zero | Enforced at both ends. `assert_rates_are_denominated` refuses a not-measured rate carrying a value, `report.pct` and `report.rate_line` render the absence as words, and as of this pass `assert_no_table_cell_is_empty` refuses the blank half in the document itself rather than only in the tree behind it |
| Intervals print both ends, widening precision when the ends would round together | Enforced by `report.span`, held by `test_an_interval_never_prints_its_two_ends_as_the_same_number`. "0.7% to 0.7%" cannot be emitted for two ends that differ |
| No em dash or en dash in any document or source file | Enforced by `test_no_file_in_the_repository_uses_an_em_or_en_dash`, which reads every authored file in the repository, and by `test_no_dash_character_appears_in_the_published_documents`. Screen readers read these inconsistently mid-sentence |
| Headings are hierarchical (`#`, then `##` sections) | Enforced by `assert_headings_do_not_skip_a_level`, which refuses a document opening below level one and a heading more than one level deeper than the heading before it. A skipped level puts a section in the heading list with no parent |
| Links are descriptive phrases, never bare URLs or "here" | Enforced by `assert_links_are_descriptive`, over the generated report at write time and over `README.md`, `PROVENANCE.md` and this document by `test_the_documents_this_review_makes_claims_about_pass_the_document_rules`. The generated report carries no links at all today, so over that document the rule is a guard against the first one rather than a check on present content, and this row says so rather than counting it as coverage it does not have |
| The JSON artifact is machine-readable for transform into any accessible format | Enforced by `artifacts.serialize`, one stable serialization with sorted keys, held by `test_serialize_is_stable_for_the_same_tree` and by the `determinism` gate, which builds twice and refuses two trees that differ |

## What this pass found

Three things, none of them found by reading the documents and all of them found by
running the new rules over them.

- **This document's own table was broken.** The row asserting that every data table has
  a header row contained four unescaped pipe characters inside a code span, so Markdown
  read it as a five-cell row under a two-cell header and rendered its second half as
  extra columns. The claim about header rows was itself being read under the wrong
  column name. Fixed here, by escaping the pipes as `\|`.
- **One table in `published/REPORT.md` was not introduced.** In "What the repair is
  worth", the table headed
  `\| Repair \| Placed share \| Placed \| Of \| 95% interval \|` followed the transitions
  table with one blank line and no sentence between them, so a reader arriving at it
  got a second table with nothing saying what changed. This was a nicety rather than a
  conformance failure, and on 2026-09-04 no rule refused it: adding one would have
  refused the currently published document, and the published bytes are not edited to
  fit a gate. **Fixed on 2026-09-04, in that order.** The renderer gained the sentence
  as a catalog entry, `published/REPORT.md` was re-rendered from the unchanged
  `published/measurements.json`, and `assert_every_table_is_introduced` went in behind
  the artifact that could pass it. The rule refused exactly one of thirty-four
  documents before the fix and none after.
- **Two repository documents outside the gated set would be refused.** The same rules
  refuse `docs/METRICS_LEDGER.md`, whose "Next deliberate refresh" row carries two
  cells under a five-column header and reads as two sentences run together where three
  cells went missing, and `docs/adr/0007-the-two-repairs-are-run-against-each-other.md`,
  whose comparison table leaves its corner cell and four share cells empty. Neither was
  generated output and neither was gated here, so both were recorded rather than
  quietly fixed in a review of something else.

## What the fix for that last finding found in turn

Dated 2026-09-04, after the review above.

Both documents were repaired, and the gated set was widened from the three documents
this review names to every Markdown document in the repository. Reading three of
thirty-three is a sample, and the two defects the review had just recorded were both
outside the three.

Widening it immediately refused a third document nobody had looked at:
`docs/adr/0015-one-county-inspection-record-set-is-compared-as-counts-and-neither-side-is-corrected.md`,
merged hours earlier, carried three bare URLs written as autolinks. A bare URL is read
out character by character, and one of these is 66 characters of county website path.
All three now say what is at the other end of them.

That is the argument for a gate over a reading, made by the gate: the review of
2026-09-04 read the documents it knew to name, and a defect landed in a document it did
not name, on the same day, from the same session.

## What was not done

- **No assistive-technology pass.** Nobody has navigated the generated tables with a
  screen reader. Markdown pipe tables are a known rough edge for some of them; whether
  these tables survive that navigation is untested and this review does not claim it.
  Nothing added on 2026-09-04 substitutes for it: a rule that refuses a ragged row says
  the row has the cells it declares, and says nothing at all about how the row sounds.
- **No reading-order audit beyond heading structure.** Whether a section sequence
  makes sense linearly is a judgment this document defers to an actual pass.
- **No plain-language review** beyond the project's own writing rules.
- **No rule that a table is introduced before it appears.** The finding above is the
  reason it is not enforced, and it is the one structural property this pass identified,
  could have gated, and deliberately did not.

## Standing rule

The publication rules that already fail closed do most of the accessibility work this
project needs: a rate without its denominator, a not-measured value printed as zero,
or an interval printed as false certainty would all mislead far more than formatting
ever could, and none of them can ship. This review covers the layer above that, and as
of 2026-09-04 most of that layer fails closed the same way.
