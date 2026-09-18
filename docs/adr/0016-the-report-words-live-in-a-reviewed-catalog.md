# 16. The report's words live in a catalog, and a generated translation is not a reviewed one

Date: 2026-09-04

## Status

Accepted. Amends the English-only declaration in `docs/I18N.md`. Does not supersede it:
the standard still applies and is still not met, and the reason it is not met is now a
different and smaller one.

## Context

`docs/I18N.md` records the internationalization standard as applying and deferred, on
the grounds that this project's output is a technical measurement document read next to
the code that produced it rather than a page for a general reader. That reasoning still
holds and is not what this decision changes.

What the declaration also recorded, under "What is not done", was this:

> Output strings are written in English, inline, in `report.py` and `measure.py`. There
> is no catalog and no extraction.

That sentence was the blocking half. While every word the document prints is written
inline in the renderer, a second edition is not a translation, it is a second renderer,
and the first thing a second renderer does is drift: two code paths, two chances for a
figure to be assembled differently, and no way to tell whether a number in one edition
is the number in the other. Roadmap 4.2 asks for a Spanish edition rendered from the
same `measurements.json`, with figures identical in both languages and the determinism
gate holding across both. None of that is decidable while the prose is in the code.

Two temptations came with the work, and both are the shape this repository refuses.
The first is a `--lang` flag accepting one value, which is a menu with one item on it
and reads as progress without being any. The second is machine translation, which
would produce a Spanish file quickly and would be a document nobody who reads Spanish
has checked, published under this repository's name.

## Decision

**A catalog is a declared, ordered mapping from a stable key to one edition's string.**
It lives in `src/wildfire_service_territory_overlap/catalog.py`. `ENGLISH` is the
reference edition; its keys, in the order they are declared, are the keys every other
edition carries, and the order is the order the sections appear in the document so a
reviewer reads the catalog the way a reader reads the report. The renderer holds no
prose: `report.render(tree, cat=ENGLISH)` takes the catalog as a parameter, and a test
parses `report.py` and fails if any string a reader could read is left in it.

**A catalog is reviewed when a person who reads that language has checked each entry
against the measurement it sits beside.** That is a human act and nothing in this
repository can perform it or verify it. What the code checks is shape, in
`catalog.translation`: the same keys as English, no keys nothing renders, no empty
strings, and the same placeholder fields inside every entry. The last check is the one
that earns its place, because `str.format` ignores a keyword nothing uses: an entry
that quietly drops `{fire_records}` renders a sentence with the number missing and
raises nothing at all. Shape is machine-checkable and meaning is not, so the code checks
shape and says so rather than implying it has checked more.

**A generated translation is not a reviewed catalog and is not published as one.** No
edition of this report ships on the strength of a machine translation, this project's
own or anybody else's. A generated draft may be an input to review; it is never the
output. This is the same rule the rest of the repository applies to a measurement: the
question is not whether a value can be produced, it is whether anybody has checked it.

**Numbers are never re-formatted per locale inside one artifact.** `report.pct`,
`report.count` and `report.span` take no catalog and cannot be given one, so no edition
has a way to punctuate a figure differently; a test reads their signatures and refuses
one that can see a catalog. `span` returns both ends of an interval separately, because
the word between them is language and the two numbers are not. Catalog entries carry
bare placeholder names with no format spec, which a test enforces, so `{records:,}`
cannot become an edition's private opinion about a thousands separator. One artifact
therefore writes every figure one way, whatever language the sentences around it are in.

**The determinism gate holds across every edition.** The same artifact rendered with the
same catalog produces the same bytes, in the same way and for the same reason it did
before this change. Adding an edition adds a catalog to that guarantee, never an
exception to it.

**No command-line surface is added for a choice of one.** There is no `--lang`. The
edition is a parameter of `render`, so a second edition is a catalog passed to a
function rather than a flag that has to be taught a second value first.

## What this does not decide

**The artifact's own strings are still English and still inline.** Row labels,
measurement notes, the county note and the type-field note are written in `measure.py`,
land in `measurements.json`, and are read straight out of it by the renderer. They are
data in the artifact rather than prose in the renderer, and translating them would make
`measurements.json` differ per language, which would break the one thing 4.2 is built
on: both editions rendering from one artifact. Until that is worked out, a second
edition would print translated prose around English artifact labels. That is a real gap
and `docs/I18N.md` names it rather than leaving it to be discovered by a reader.

**No Spanish catalog exists.** Nothing in this change is a Spanish edition or a step
that has been taken toward one beyond making one possible.

## Consequences

The English document did not move. Every branch of the renderer was run before and
after the extraction against the published artifact, the fixture artifact, and
synthesized trees exercising the two-repair rendering, the empty-transitions rendering
and a tree in which nothing is measured; all twelve came out byte for byte identical,
`published/REPORT.md` still renders exactly from `published/measurements.json`, and the
determinism gate is unchanged.

The cost is one more file and one more indirection between a sentence and the code that
prints it. What is bought is that the second edition, if it is ever written, is a list
of strings a Spanish speaker can read top to bottom and correct, rather than a diff
against a renderer. The work that remains before a Spanish edition exists is the work
that was always the hard part and is not code: somebody who reads Spanish sitting with
the measurements and checking that each string says what the number beside it means.
