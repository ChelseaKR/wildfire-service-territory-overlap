"""The words the generated report is written in, declared apart from the renderer.

A catalog is a declared, ordered mapping from a stable key to one edition's string.
:data:`ENGLISH` is the English edition and it is the reference: its keys, in the order
they are written below, are the keys every other edition has to carry, and its
placeholder fields are the fields every other edition has to keep.

Three rules hold for every edition, and the first two are enforced here rather than
trusted:

1. **A catalog carries words and never numbers.** Every figure in the document is
   formatted by :mod:`wildfire_service_territory_overlap.report`, whose numeric helpers
   take no catalog and therefore cannot be told to punctuate a number differently. A
   catalog entry can say where a number goes; it cannot say how one is written.
2. **An edition is complete or it is refused.** :func:`translation` rejects a missing
   key, an unknown key, an empty string, and an entry whose placeholder fields differ
   from the English entry's. The last one is the dangerous case: an entry that drops
   ``{records}`` drops a measured number out of the document without raising anything.
3. **Reviewed is a human word.** Nothing in this module can check that a string says
   what it means. The English catalog is the reviewed one because it is the text this
   repository has published and corrected. A generated translation is not a reviewed
   catalog, and `docs/adr/0016` records that as a rule rather than a preference.

Not every word a reader of this project meets is in a catalog. The artifact carries
sentences of its own, written into ``measurements.json`` by the modules that measure,
and no edition reaches them. :func:`artifact_prose` is the census of those sentences and
:func:`unclassified_string_fields` is the gate that keeps the census from going quietly
out of date. Neither decides anything: `docs/adr/0017` is the proposal, it is not
accepted, and until it is these two functions only measure the size of the question.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from string import Formatter
from typing import Any, Final


class CatalogRefused(ValueError):
    """An edition that is not a complete, like-for-like edition of the English one."""


def _fields(entry: str) -> frozenset[str]:
    """The placeholder names an entry carries, ignoring the words around them."""
    return frozenset(
        field for _, field, _, _ in Formatter().parse(entry) if field is not None
    )


class Catalog(Mapping[str, str]):
    """One edition of the report's strings, keyed by a key that never changes."""

    def __init__(self, edition: str, entries: Mapping[str, str]) -> None:
        if not edition:
            raise CatalogRefused("a catalog has to name its edition")
        self.edition = edition
        self._entries: dict[str, str] = dict(entries)
        for key, value in self._entries.items():
            if not value:
                raise CatalogRefused(f"{edition} carries an empty string for {key!r}")

    def __getitem__(self, key: str) -> str:
        try:
            return self._entries[key]
        except KeyError:
            raise KeyError(f"{self.edition} carries no string for {key!r}") from None

    def __iter__(self) -> Iterator[str]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"Catalog({self.edition!r}, {len(self._entries)} entries)"


def translation(edition: str, entries: Mapping[str, str]) -> Catalog:
    """A second edition, refused unless it is a complete edition of the English one.

    What is checked is shape: the same keys, and the same placeholder fields inside
    each entry. What is not checked, and cannot be, is whether the strings say what the
    measurement says. That is what review means and it is a person's job.
    """
    missing = sorted(set(ENGLISH) - set(entries))
    if missing:
        raise CatalogRefused(f"{edition} carries no string for {missing}")
    unknown = sorted(set(entries) - set(ENGLISH))
    if unknown:
        raise CatalogRefused(f"{edition} carries strings nothing renders: {unknown}")
    for key in ENGLISH:
        wanted = _fields(ENGLISH[key])
        got = _fields(entries[key])
        if wanted != got:
            raise CatalogRefused(
                f"{edition} entry {key!r} carries the placeholders {sorted(got)} where "
                f"the English entry carries {sorted(wanted)}; an edition that drops a "
                "placeholder drops a measured number out of the document"
            )
    return Catalog(edition, entries)


ARTIFACT_PROSE_FIELDS: Final[tuple[str, ...]] = (
    "affiliation",
    "county_note",
    "geometry_note",
    "label",
    "no_trend_is_published",
    "note",
    "question",
    "reason",
    "the_published_type_field_is_undocumented",
    "variant",
)
"""Artifact fields whose value is a sentence somebody in this repository wrote.

These are the row labels, the measurement notes, the county note and the type-field
note that `docs/adr/0016` named and did not decide. They are written in
``measure.py``, ``sensitivity.py``, ``sources.py``, ``intervals.py``, ``geometry.py``
and ``cli.py``, they land inside ``measurements.json``, and no catalog reaches them.
"""

ARTIFACT_DATA_FIELDS: Final[tuple[str, ...]] = (
    "alternative",
    "between",
    "chosen",
    "contested_with",
    "county",
    "dins_landing_page",
    "dins_retrieved",
    "geometry_state",
    "interval_method",
    "largest_incident",
    "outlines_no_record_falls_inside",
    "published_type",
    "published_types_present_in_this_retrieval",
    "repaired",
    "reviewed_on",
    "reviewer_reason",
    "reviewer_role",
    "rule_as_built",
    "rule_file",
    "source_layer",
    "state",
    "strategies_compared",
    "structure_category",
    "territories",
    "territories_item_modified",
    "territories_landing_page",
    "territories_retrieved",
    "territory",
    "types_read_as_territories",
    "under_the_alternative",
    "under_the_chosen_repair",
)
"""Artifact fields whose value is a string and is not this repository's prose.

A name CAL FIRE or the California Energy Commission published, a machine token such as
``measured`` or ``wilson-score-95``, a retrieval date, or a landing page. None of it is
translated in any edition: a name is reported as published, and a token names a method
rather than describing one.

``reviewed_on``, ``reviewer_reason``, ``reviewer_role`` and ``rule_file`` come from a
reviewer-supplied inclusion rule file. They belong here rather than above for the
reason the list above states in its first line: none of them is this repository's
prose. A review date is a date, a role and a filename are reported as the reviewer
wrote them, and ``reviewer_reason`` is one line a reviewer wrote about one outline,
published in their words. No edition rewrites any of the four, and no edition should:
translating somebody else's stated reason would be putting words in their mouth.
"""


def _string_leaves(node: Any, path: str, field: str) -> Iterator[tuple[str, str, str]]:
    """Every string in the tree, with the path to it and the field it sits under."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _string_leaves(value, f"{path}.{key}", key)
        return
    if isinstance(node, list):
        for index, value in enumerate(node):
            yield from _string_leaves(value, f"{path}[{index}]", field)
        return
    if isinstance(node, str):
        yield path, field, node


def artifact_prose(tree: Any) -> list[tuple[str, str]]:
    """Every sentence this repository publishes inside the artifact, by path.

    Empty strings are returned rather than dropped. An empty ``note`` is a published
    leaf like any other, it is compared by
    :mod:`wildfire_service_territory_overlap.artifact_diff` like any other, and a census
    that skipped it would understate what a keyed artifact would have to move.
    """
    return [
        (path, text)
        for path, field, text in _string_leaves(tree, "$", "")
        if field in ARTIFACT_PROSE_FIELDS
    ]


def unclassified_string_fields(tree: Any) -> set[str]:
    """String-valued fields that are in neither declared list.

    A new field carrying a sentence is a decision: either an edition will one day have
    to reach it or it never will. This returns the fields nobody has said which, so the
    question is asked when the field is added rather than when somebody tries to
    translate the document.
    """
    known = {*ARTIFACT_PROSE_FIELDS, *ARTIFACT_DATA_FIELDS}
    return {
        field for _, field, _ in _string_leaves(tree, "$", "") if field not in known
    }


# The reference edition. Key order below is the declared order of the catalog, and it
# follows the order the sections appear in the document, so a reviewer reads the
# catalog the way a reader reads the report.
_ENGLISH: dict[str, str] = {
    # Words the numeric helpers hand back when there is no number to write.
    "words.not_measured": "not measured",
    "words.interval": "{low} to {high}",
    # The header.
    "header.title": (
        "# Which published electric service territory is a burned structure in?"
    ),
    "header.unofficial": (
        "Unofficial. Not affiliated with, endorsed by, or approved by CAL FIRE, the\n"
        "California Energy Commission, or any electric utility. This is descriptive\n"
        "geography over two public datasets. It is not a risk rating of any company and\n"
        "it contains no information about the location of anybody's infrastructure."
    ),
    "header.retrieval": (
        "Damage inspections retrieved {dins_retrieved}. Territory boundaries\n"
        "retrieved {territories_retrieved}, publisher item last modified\n"
        "{territories_item_modified}."
    ),
    "header.generated": (
        "This document is generated. Every figure below is read from\n"
        "`measurements.json`, which is produced by the same run."
    ),
    # Can the join be made at all.
    "coverage.heading": "## Can the join be made at all",
    "coverage.intro": (
        "The record set holds {fire_records} wildfire damage-inspection\n"
        "records. {excluded_by_hazard_filter} records in the published file describe a\n"
        "hazard other than fire and are excluded here rather than counted as wildfire."
    ),
    "coverage.table_head": (
        "| Outcome | Share | Records | Of | 95% interval |\n|---|---:|---:|---:|---|"
    ),
    "coverage.contested_note": (
        "A record inside two or more published territories is not awarded to either.\n"
        "The publisher states that the boundaries are approximate and that not all\n"
        "entities are represented, so public data does not say which entity such a\n"
        "record belongs to, and this project does not decide on its behalf."
    ),
    # Do the attributable records look like the ones that cannot be attributed.
    "representativeness.heading": (
        "## Do the records that can be attributed look like the ones that cannot"
    ),
    "representativeness.table_head": (
        "| Population | Destroyed share | Destroyed | Inspected | 95% interval |\n"
        "|---|---:|---:|---:|---|"
    ),
    "representativeness.difference": (
        "Difference, placed minus contested: {difference} ({interval}, Newcombe score)."
    ),
    "representativeness.verdict.differs": (
        "The interval excludes zero. The records that can be attributed to a single "
        "territory are therefore not a representative slice of the record set, and any "
        "territory-level reading of them carries that difference with it."
    ),
    "representativeness.verdict.no_difference": (
        "The interval includes zero, so this comparison does not establish a "
        "difference between the two populations."
    ),
    # The same check inside each published structure class.
    "structure_class.heading": (
        "## The placed and contested populations, by structure class"
    ),
    "structure_class.intro": (
        "The placed-versus-contested check from above, run again inside each structure\n"
        "class CAL FIRE publishes. A difference confined to one class would hide inside\n"
        "the aggregate; a difference spread across every class is sturdier than one\n"
        "number. Classes in name order; none is compared against another."
    ),
    "structure_class.table_head": (
        "| Structure class | Placed destroyed share | Contested destroyed share |"
        " Difference (Newcombe) |\n|---|---:|---:|---|"
    ),
    # Is the unattributable share a property of the data or of the fire.
    "by_fire.heading": (
        "## Is the unattributable share a property of the data or of the fire"
    ),
    "by_fire.intro": (
        "The headline is one number over the whole record set, which reads as a property\n"
        "of the two datasets. It is mostly not. The published outlines overlap in\n"
        "particular places, so whether a record is contested is largely settled by where\n"
        "its fire burned."
    ),
    "by_fire.incidents": (
        "Of {distinct_incidents} distinct incidents in the record set,\n"
        "{one_way_share} ({one_way_interval}) fall entirely on one side: every\n"
        "classified record contested, or none of them. Those incidents hold\n"
        "{records_in_settled_share}\n"
        "of the records that carry an incident name."
    ),
    "by_fire.incident_table_head": (
        "| Incidents | Share | Incidents | Of | 95% interval |\n|---|---:|---:|---:|---|"
    ),
    "by_fire.by_year_intro": (
        "The same thing seen by year. The boundaries are one retrieval and are identical\n"
        "for every row, so the movement down this column is where each year's fires\n"
        "burned and not a change in the published boundaries. No trend is published."
    ),
    "by_fire.year_table_head": (
        "| Incident year | Records | Classified | Contested share | 95% interval |\n"
        "|---:|---:|---:|---:|---|"
    ),
    # The same cut by county.
    "by_county.intro": (
        "The same cut by county, from CAL FIRE's own county field. In name order, never\n"
        "in size order, and no county is compared against another. This says where in\n"
        "California the published outlines overlap: {counties_named}\n"
        "counties are named in the record set, and\n"
        "{records_with_no_county} records carry no county name and are\n"
        "left out of this cut alone."
    ),
    "by_county.table_head": (
        "| County | Records | Classified | Contested share | 95% interval |\n"
        "|---|---:|---:|---:|---|"
    ),
    # Does the coordinate agree with the recorded county.
    "county_agreement.heading": (
        "## Does the coordinate agree with the recorded county"
    ),
    "county_agreement.intro": (
        "CAL FIRE records a county name on every row, and this project reports it as\n"
        "published. This section measures that field against an authoritative county\n"
        "boundary layer rather than trusting it or correcting it: how often a record's\n"
        "coordinate lands outside the county its publisher recorded. {compared}\n"
        "of {comparable} records could be compared at all; the rest had no usable\n"
        "coordinate or a county label the boundary layer does not carry, and they stay\n"
        "in every other denominator in this project."
    ),
    "county_agreement.outcome_table_head": (
        "| Outcome | Share | Records | Of | 95% interval |\n|---|---:|---:|---:|---|"
    ),
    "county_agreement.note": (
        "Counted, never corrected. The boundary layer's publisher warns that its own\n"
        "boundary errors will exist, so a disagreement is evidence that two published\n"
        "sources differ and not a verdict on which one is right. No damage rate is\n"
        "published for a county here either."
    ),
    "county_agreement.table_head": (
        "| County | Compared | Agreed | Matched no county | Disagreed share |"
        " 95% interval |\n|---|---:|---:|---:|---:|---|"
    ),
    # Every published territory.
    "territories.heading": "## Every published territory, in name order",
    "territories.intro": (
        "Counts, and two within-territory shares. No damage rate is published for a\n"
        "territory and no territory is ordered against another. The concentration\n"
        "column is why: where one incident supplies most of a territory's records, a\n"
        "territory-level damage rate would be a statement about that one fire."
    ),
    "territories.contested_note": (
        "A territory appears in more than one row of the contested count, because a\n"
        "record inside three outlines is contested for all three."
    ),
    "territories.table_head": (
        "| Territory | Type | Placed | Contested | Incidents | Largest incident share |"
        " Within 250 m of the edge | Geometry |\n|---|---|---:|---:|---:|---|---|---|"
    ),
    # Where the published boundaries overlap.
    "contested.heading": "## Where the published boundaries overlap",
    "contested.intro": (
        "Counts of records falling inside each combination of published outlines. This\n"
        "is a description of the boundary layer, not of any utility. The combinations\n"
        "are listed by size because size is what is being reported."
    ),
    "contested.edge_note": (
        "The last column is the share of each combination's records sitting\n"
        "within 250 metres of the nearest edge among the outlines involved. A\n"
        "contested record stops being contested when any of them ceases to\n"
        "contain it, so that is the edge an approximation error moves first; a\n"
        "combination near 100% here is a thin seam between outlines, and one\n"
        "near 0% is an interior region where two published territories genuinely\n"
        "cover the same ground."
    ),
    "contested.table_head": (
        "| Published outlines a record falls inside | Records |"
        " Within 250 m of an edge |\n|---|---:|---:|"
    ),
    # The published polygons, as they arrived.
    "ledger.heading": "## The published polygons, as they arrived",
    "ledger.intro": (
        "{territories_indexed} outlines were read as electric service\n"
        "territories. {territories_repaired} of them failed an OGC validity\n"
        "check on retrieval and were repaired before any containment question was asked\n"
        "of them, because an invalid polygon answers that question undefined rather than\n"
        "refusing it. The repaired ones are named here and flagged in the table above."
    ),
    "ledger.repaired_share": (
        "{records} placed records, {share} of the placed total ({interval}), sit inside"
        " one of those\n"
        "repaired polygons. A different repair would place a different set, so that\n"
        "figure is the size of this project's exposure to the choice."
    ),
    "ledger.unusable": (
        "{unusable_count} outlines could not be repaired into a testable\n"
        "shape. Those are removed from the index and are not reported as holding\n"
        "zero records."
    ),
    "ledger.excluded_types": (
        "Two published entity types are not read as service territories:"
    ),
    # What the repair is worth.
    "repair.heading": "## What the repair is worth",
    "repair.widened.intro": (
        "All {strategy_count} repairs ({strategies}) run to completion over\n"
        "the same records. {numerator} of {denominator} records, {share}\n"
        "({interval}), come out differently under at least one pair of\n"
        "them. That count is a census of the disagreement and not an estimate\n"
        "of it, and it bounds how much of the result the choice of repair can\n"
        "move. The pairwise counts:"
    ),
    "repair.pairwise_table_head": "| Between | Records |\n|---|---:|",
    "repair.pairwise_row": "| `{left}` and `{right}` | {records} |",
    "repair.adr_0007_pair": (
        "The pair ADR 0007 documents in detail: {numerator}\n"
        "of {denominator} records, {share}\n"
        "({interval}), come out differently under `{alternative}` than under"
        " `{chosen}`."
    ),
    "repair.two.intro": (
        "Both repairs run to completion over the same records. {numerator}\n"
        "of {denominator} records, {share}\n"
        "({interval}), come out differently under `{alternative}` than\n"
        "under `{chosen}`. That count is a census of the disagreement and not an\n"
        "estimate of it."
    ),
    "repair.transitions_table_head": (
        "| Under the repair used here | Under the alternative | Records |\n|---|---|---:|"
    ),
    "repair.no_transitions.widened": "The repairs place every record the same way.",
    "repair.no_transitions.two": "The two repairs place every record the same way.",
    "repair.placed_intro": (
        "What each repair places in total, over the whole record set, rather than\n"
        "only the records whose outcome moved."
    ),
    "repair.placed_table_head": (
        "| Repair | Placed share | Placed | Of | 95% interval |\n|---|---:|---:|---:|---|"
    ),
    "repair.placed_difference": (
        "Difference in the placed share: {difference} ({interval}, Newcombe score)."
        " The same records are placed twice,\n"
        "so that interval is the conservative bound."
    ),
    "repair.verdict.widened": (
        "No repair is correct. Each is an answer to a question the published\n"
        "polygon does not answer, and the disagreement between them is the size of\n"
        "the ambiguity the invalid geometry leaves behind. The default did not\n"
        "move to gain this measurement; it was already `make_valid` under ADR 0007."
    ),
    "repair.verdict.two": (
        "Neither repair is correct. Both are answers to a question the published\n"
        "polygon does not answer, and the gap between them is the size of the\n"
        "ambiguity the invalid geometry leaves behind."
    ),
    # What the inclusion rule is worth.
    "type_inclusion.heading": "## What the inclusion rule is worth",
    "type_inclusion.intro": (
        "Which published outlines count as a service territory is a judgment, and this is\n"
        "the whole record set placed again under each way that judgment could have gone.\n"
        "The first row is the rule this project uses. Nothing here chooses between them,\n"
        "and the difference column is the conservative bound rather than the tight one,\n"
        "because the same records are being measured twice."
    ),
    "type_inclusion.table_head": (
        "| Inclusion rule | Outlines | Contested | Contested share | 95% interval |"
        " Difference from the rule as built | Inside no published territory |\n"
        "|---|---:|---:|---:|---|---|---:|"
    ),
    "type_inclusion.reference": "reference",
    "type_inclusion.closing": (
        "A rule that drops an included type does not only move records out of the\n"
        "contested column. It moves them into the last one, where they are published\n"
        "as inside no published territory, which is a statement about coverage that\n"
        "the dropped entity's own published polygon contradicts."
    ),
    "type_inclusion.supplied_heading": "### Rules supplied by a reviewer",
    "type_inclusion.supplied_intro": (
        "The rows below were not written here. Each one is a rule file a reviewer\n"
        "supplied, run to completion over the same record set and published with its\n"
        "own denominator, interval and difference from the rule as built. Nothing here\n"
        "is adopted and nothing is marked better: the rule as built stays the reference\n"
        "row, and a supplied rule is measured rather than applied. It establishes what\n"
        "one reading would cost. It does not establish that any named organisation in\n"
        "the layer operates a distribution system, which this project does not decide."
    ),
    "type_inclusion.supplied_row": (
        "- **{variant}**, supplied by {role} on {reviewed_on}, from `{rule_file}`."
    ),
    "type_inclusion.supplied_override_read": (
        "  - {outline} is read as a service territory here: {reason}"
    ),
    "type_inclusion.supplied_override_not_read": (
        "  - {outline} is not read as a service territory here: {reason}"
    ),
    # The outlines that hold nothing.
    "untouched.heading": "## The outlines that hold nothing",
    "untouched.intro": (
        "Whether a particular named entity in the published layer operates a retail\n"
        "distribution system is the publisher's classification to make, and this project\n"
        "does not make it. The narrower question can be answered with a count: could that\n"
        "outline be moving a figure here?"
    ),
    "untouched.counts": (
        "{empty_outlines} of the {outlines_indexed} outlines read as service territories"
        " hold no\n"
        "record at all. {inside_numerator} records of {inside_denominator} fall inside"
        " one of them\n"
        "({inside_interval}). Placing the whole record set again with all of them\n"
        "removed changes the outcome of {changed} records\n"
        "({changed_interval}), so no figure in this document depends on any of them."
    ),
    # What this does not measure.
    "limits.heading": "## What this does not measure",
    "limits.body": (
        "- **Nothing about physical infrastructure.** No pole, conductor, substation, or\n"
        "  circuit position is read, inferred, approximated, or published, from these\n"
        "  sources or any other. An analysis that would need one is not built here.\n"
        "- **No comparison between utilities.** A territory's damage figures are driven\n"
        "  by which fires burned in it, and the concentration column shows how strongly.\n"
        "  Nothing here says any utility is more or less exposed than any other.\n"
        "- **No rate against population, housing, customers, or meters.** The record set\n"
        "  is defined by fire and by state responsibility area. A denominator drawn from\n"
        "  a differently defined population would not contain this numerator.\n"
        "- **Coverage is not exposure.** A territory with few placed records may have\n"
        "  burned little, may sit mostly outside the state responsibility area, or may\n"
        "  have most of its records contested. These are different facts and this\n"
        "  project does not merge them."
    ),
}

ENGLISH = Catalog("English", _ENGLISH)
