"""One county's own inspection records against this project's counts for that county.

Every other measurement here is drawn from CAL FIRE's file. The county cut reads CAL
FIRE's ``COUNTY`` field, and the coordinate comparison checks that field against a
second publisher's boundaries, but the records being checked are still the same
records. This module is the one place that holds them against a set a different
organization collected by walking the same ground.

Usage::

    python -m wildfire_service_territory_overlap.cross_check \\
        --county "NAME" --dins data/raw/dins_postfire.json --external COUNTY.json

**No county inspection record set is pinned.** ``sources.py`` carries no entry for one
and this module is not called from :mod:`wildfire_service_territory_overlap.cli`.
``docs/adr/0015`` decides the comparison and says why it is a command rather than a
not-measured block in every build: a section that says nothing on every run is a
section a reader learns to skip before the run where it says something.

The search for a source is finished and its answer is recorded in ``docs/adr/0018``.
One county record set in California meets all four of ADR 0015's criteria, Napa
County's own ATC damage assessments for 2020, and it is deliberately not pinned: the
two organizations name the same fires differently, so the comparison joins nothing and
``_refuse_a_comparison_that_did_not_join`` below stops it. The command still runs the
moment a joinable file exists, and ``docs/RUNBOOK.md`` carries the hand-run steps.

What is compared, and what is not
---------------------------------
Two organizations inspecting one fire do not inspect the same structures. CAL FIRE's
file is bounded by the state responsibility area and by 300 feet of the fire perimeter;
a county's own survey is bounded by its jurisdiction. A structure-level join is not
available, would need the locations this project refuses to fetch, and would not mean
what it looks like. What both sets can answer without sharing a rule is which fires they
carry records for in this county, so the comparison is per fire, by name, and four
outcomes wide:

``in_both``
    The county's set names the fire and this project counts records for it here.
``here_under_another_county``
    This project counts records for the fire, and CAL FIRE's ``COUNTY`` field puts them
    somewhere else. The only outcome that bears on the county cut, and it bears on the
    publisher's field rather than on code here.
``absent_from_this_record_set``
    This project's record set does not name the fire at all. Inspection scope, not
    error: a fire outside the state responsibility area was never going to be here.
``not_named_by_the_county_record_set``
    This project counts records for it here and the county's set does not name it.

Agreement is the first. Disagreement is the other three, kept apart rather than summed,
because they mean three different things.

Nothing is corrected. No record moves, no county label is edited, no fire is
reconciled, and neither side is treated as the truth. No rate is taken between the two
record sets in either direction: two organizations counting two populations under two
rules means neither file is the other's denominator. No damage rate is published for
the county, from either file.

Refusals
--------
This module refuses rather than guesses, and every refusal below has a test that fires
it. A value that could not be measured is reported as not measured and is never a zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from wildfire_service_territory_overlap import artifacts
from wildfire_service_territory_overlap.intervals import Rate
from wildfire_service_territory_overlap.placement import (
    Record,
    SchemaError,
    fold_name,
    read_records,
)

BLOCK_KEY: Final[str] = "county_cross_check"

COUNTY_FIELD: Final[str] = "county"
INCIDENT_FIELD: Final[str] = "incident"
"""The two fields an external row must carry, and the only two that are read.

An external file may carry more. Anything that could place a structure refuses the run
rather than being ignored, because a file this project has read is a file this project
could publish from by accident.
"""

IN_BOTH: Final[str] = "in_both"
HERE_UNDER_ANOTHER_COUNTY: Final[str] = "here_under_another_county"
ABSENT_FROM_THIS_RECORD_SET: Final[str] = "absent_from_this_record_set"
NOT_NAMED_BY_THE_COUNTY_RECORD_SET: Final[str] = "not_named_by_the_county_record_set"

OUTCOMES: Final[tuple[str, ...]] = (
    ABSENT_FROM_THIS_RECORD_SET,
    HERE_UNDER_ANOTHER_COUNTY,
    IN_BOTH,
    NOT_NAMED_BY_THE_COUNTY_RECORD_SET,
)
"""Every outcome, in name order, so a count of zero for one of them is still printed."""


class CrossCheckRefused(ValueError):
    """The comparison could not be made honestly, so it was not made."""


@dataclass(frozen=True)
class ExternalRecord:
    """One row of a county's own inspection record set, reduced to what is compared."""

    county: str
    incident: str


@dataclass(frozen=True)
class IncidentRow:
    """One fire, as each side counts it in this county."""

    incident: str
    outcome: str
    records_here_in_this_county: int
    records_here_in_another_county: int
    records_in_the_county_record_set: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "incident": self.incident,
            "outcome": self.outcome,
            "records_here_in_this_county": self.records_here_in_this_county,
            "records_here_in_another_county": self.records_here_in_another_county,
            "records_in_the_county_record_set": self.records_in_the_county_record_set,
        }


@dataclass(frozen=True)
class CrossCheck:
    """The comparison, as counts. Nothing here is divided by anything."""

    county: str
    records_here_in_this_county: int
    records_here_carrying_an_incident_name: int
    records_in_the_county_record_set: int
    incident_ceiling: int
    incidents: tuple[IncidentRow, ...]

    @property
    def outcomes(self) -> dict[str, int]:
        """Every outcome and its count, including the outcomes nothing fell into."""
        tally = Counter(row.outcome for row in self.incidents)
        return {outcome: tally[outcome] for outcome in OUTCOMES}


def _refuse_locating_fields(row: dict[str, Any], *, index: int) -> None:
    """An external file carrying a position is not read, not filtered, not published.

    ``artifacts.LOCATING_KEYS`` is the same list ``check_all`` refuses a published
    artifact for, deliberately: a second copy of that list here could drift away from
    the one that guards publication, and this is the door the file comes in through.
    """
    for key in row:
        if key.lower() in artifacts.LOCATING_KEYS:
            raise CrossCheckRefused(
                f"row {index} of the external record set carries {key!r}. This project "
                "does not read an address, a parcel number, or a coordinate from "
                "anybody, and a cross-check is not an exception. Ask the county for "
                "counts by fire, or strip the locating columns before the file reaches "
                "this command."
            )


def _text(value: Any) -> str | None:
    """A published name, or None where the cell is empty, as `placement._name` reads it."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _external_row(row: Any, *, index: int, wanted: str) -> ExternalRecord:
    if not isinstance(row, dict):
        raise CrossCheckRefused(
            f"row {index} of the external record set is not an object. Each row is one "
            f"inspection record carrying {COUNTY_FIELD!r} and {INCIDENT_FIELD!r}."
        )
    _refuse_locating_fields(row, index=index)
    county = _text(row.get(COUNTY_FIELD))
    incident = _text(row.get(INCIDENT_FIELD))
    if county is None:
        raise CrossCheckRefused(
            f"row {index} of the external record set names no county. A row whose "
            "county nobody recorded cannot be held to the one county this comparison "
            "is bounded to."
        )
    if incident is None:
        raise CrossCheckRefused(
            f"row {index} of the external record set names no fire. The comparison is "
            "per fire by name, so a row with no incident name has nothing to compare "
            "and is refused rather than dropped, which would shrink the external set "
            "where nobody could see it."
        )
    if fold_name(county) != wanted:
        raise CrossCheckRefused(
            f"row {index} of the external record set names {county!r} and the "
            "comparison was asked for another county. The scope is one county, decided "
            "in docs/adr/0015; a file carrying two is not the comparison that was "
            "decided and is not silently filtered down to it."
        )
    return ExternalRecord(county=county, incident=incident)


def read_external(payload: Any, *, county: str) -> tuple[ExternalRecord, ...]:
    """Read a county's own inspection record set, or refuse it.

    Four refusals live here: a payload that is not a list of rows, a set with no rows in
    it, a row carrying anything that could place a structure, and a row naming a county
    other than the one asked for.
    """
    if not isinstance(payload, list):
        raise CrossCheckRefused(
            "the external record set is not a list of rows. Expected a JSON array of "
            f"objects, each carrying {COUNTY_FIELD!r} and {INCIDENT_FIELD!r}."
        )
    if not payload:
        raise CrossCheckRefused(
            "the external record set holds no rows. An empty file is not a county that "
            "inspected nothing; it is a file that says nothing, and reporting it as "
            "total disagreement would publish a retrieval fault as a finding."
        )
    wanted = fold_name(county)
    return tuple(
        _external_row(row, index=index, wanted=wanted)
        for index, row in enumerate(payload)
    )


def _county_label(county: str, records: tuple[Record, ...]) -> str:
    """The record set's own spelling of the county, or a refusal to compare against it.

    Two refusals, kept apart because they mean different things. A county this project
    holds no record under cannot be cross-checked at all: every incident the external
    set named would come back as a disagreement with nothing. A county this project
    holds records for but could classify none of is the case the county cut publishes
    as not measured, and comparing against a row this project publishes as not measured
    would report the coordinate filter as if it were evidence about either record set.
    """
    wanted = fold_name(county)
    labels: dict[str, str] = {}
    for record in records:
        if record.county:
            labels.setdefault(fold_name(record.county), record.county)
    if wanted not in labels:
        raise CrossCheckRefused(
            f"this project's record set carries no record under the county name "
            f"{county!r}. There is nothing here to cross-check, and a comparison "
            "against a county this project holds no records for would report the "
            "external set's own contents as disagreement."
        )
    classified = sum(
        1
        for record in records
        if record.county
        and fold_name(record.county) == wanted
        and record.has_usable_coordinate
    )
    if classified == 0:
        raise CrossCheckRefused(
            f"this project measured {labels[wanted]!r} as not measured: it carries "
            "records and none of them has a usable coordinate, so the county cut "
            "publishes no share for it. A cross-check against a not-measured row would "
            "be a statement about the coordinate filter rather than about either "
            "record set."
        )
    return labels[wanted]


def _distinct_incidents(records: tuple[Record, ...]) -> int:
    """How many fires the whole record set names. The bound on a bounded cross-check."""
    return len({fold_name(r.incident) for r in records if r.incident})


def _refuse_an_oversized_union(union: set[str], ceiling: int) -> None:
    """Refuse a comparison naming more fires than the whole record set names.

    Every incident this project contributes is drawn from the record set, so the union
    can only exceed the record set's own count of distinct fires when the external file
    names fires CAL FIRE's whole statewide file does not carry, more of them than that
    file names in total. Against the real retrieval that is not a county's inspection
    record set; it is the wrong file, and reading it would publish a retrieval fault as
    a large disagreement count.

    The bound is computed from the record set handed in rather than written down as a
    number, so it cannot drift away from the data it describes, and
    ``tests/test_cross_check.py`` drives a comparison past it.
    """
    if len(union) > ceiling:
        raise CrossCheckRefused(
            f"the comparison names {len(union)} distinct fires and the whole record "
            f"set names {ceiling}. An external file naming more fires than CAL FIRE's "
            "entire file is the wrong file, not a finding. Check that the file is one "
            "county's inspection records and that its incident column is the fire name."
        )


def _refuse_a_comparison_that_did_not_join(rows: tuple[IncidentRow, ...]) -> None:
    """Refuse a comparison where both sides name fires here and no name is shared.

    ADR 0015 reads an agreement of zero across a set of fires both organizations
    plainly worked as a fault in the comparison rather than as a result, and until
    2026-09-05 that reading lived only in prose. The command would print the block and
    a reader would meet a naming convention rendered as total disagreement.

    The real retrieval is what made this a refusal rather than a note. Napa County's
    own damage assessments name their two fires ``GLASS COMPLEX 2020`` and ``NAPA
    LIGHTNING COMPLEX 2020``; CAL FIRE's file names the same two ground events
    ``Glass`` and ``LNU Lightning Cmplx`` and carries neither county spelling anywhere
    in the state. Every fire falls into a disagreement bucket, agreement is zero, and
    nothing about either organization's inspections has been measured.

    The guard needs both sides to have named something in this county. Where this
    project counts no incident name here, the share over that denominator is already
    published as not measured, and a zero agreement carries no claim about a join that
    was never attempted. ``docs/adr/0018`` records what would have to change for a
    disjoint pair of record sets to be publishable, and it is a decision rather than a
    flag on this function.
    """
    tally = Counter(row.outcome for row in rows)
    named_there = (
        tally[IN_BOTH]
        + tally[HERE_UNDER_ANOTHER_COUNTY]
        + tally[ABSENT_FROM_THIS_RECORD_SET]
    )
    named_here = tally[IN_BOTH] + tally[NOT_NAMED_BY_THE_COUNTY_RECORD_SET]
    if tally[IN_BOTH] or not named_here or not named_there:
        return
    theirs = [row.incident for row in rows if row.outcome != IN_BOTH][:5]
    raise CrossCheckRefused(
        f"the county's record set names {named_there} fires here, this project counts "
        f"{named_here}, and not one name is shared. ADR 0015 reads that as a fault in "
        "the comparison and not as a finding: two organizations that inspected the "
        "same county share no fire name only when the join did not happen, and the "
        "usual cause is that each publisher spells its incidents its own way. Check "
        "the incident column against the county cut in published/REPORT.md before "
        f"anything else. Fires the comparison could not pair: {', '.join(theirs)}."
    )


def _outcome(here: int, elsewhere: int, there: int) -> str:
    if here > 0 and there > 0:
        return IN_BOTH
    if here > 0:
        return NOT_NAMED_BY_THE_COUNTY_RECORD_SET
    if elsewhere > 0:
        return HERE_UNDER_ANOTHER_COUNTY
    return ABSENT_FROM_THIS_RECORD_SET


def _tally_this_project(
    records: tuple[Record, ...], label: str
) -> tuple[Counter[str], Counter[str], dict[str, str], int]:
    """Per fire, how many records this project counts in this county and outside it."""
    wanted = fold_name(label)
    here: Counter[str] = Counter()
    elsewhere: Counter[str] = Counter()
    spellings: dict[str, str] = {}
    in_county = 0
    for record in records:
        is_here = record.county is not None and fold_name(record.county) == wanted
        in_county += int(is_here)
        if not record.incident:
            continue
        key = fold_name(record.incident)
        spellings.setdefault(key, record.incident)
        if is_here:
            here[key] += 1
        else:
            elsewhere[key] += 1
    return here, elsewhere, spellings, in_county


def compare(
    county: str,
    records: tuple[Record, ...],
    external: tuple[ExternalRecord, ...],
) -> CrossCheck:
    """Hold one county's own inspection records against this project's counts for it.

    Neither side is corrected, neither is treated as the truth, and no fire is
    reconciled across the two spellings beyond case and inner whitespace.
    """
    label = _county_label(county, records)
    here, elsewhere, spellings, in_county = _tally_this_project(records, label)
    there: Counter[str] = Counter()
    for row in external:
        key = fold_name(row.incident)
        there[key] += 1
        spellings.setdefault(key, row.incident)
    ceiling = _distinct_incidents(records)
    union = set(here) | set(there)
    _refuse_an_oversized_union(union, ceiling)
    rows = tuple(
        sorted(
            (
                IncidentRow(
                    incident=spellings[key],
                    outcome=_outcome(here[key], elsewhere[key], there[key]),
                    records_here_in_this_county=here[key],
                    records_here_in_another_county=elsewhere[key],
                    records_in_the_county_record_set=there[key],
                )
                for key in union
            ),
            key=lambda row: row.incident,
        )
    )
    _refuse_a_comparison_that_did_not_join(rows)
    return CrossCheck(
        county=label,
        records_here_in_this_county=in_county,
        records_here_carrying_an_incident_name=sum(here.values()),
        records_in_the_county_record_set=len(external),
        incident_ceiling=ceiling,
        incidents=rows,
    )


AGREEMENT_NOTE: Final[str] = (
    "Counted, never corrected. Two organizations inspecting one fire inspect different "
    "structures under different rules, so this compares which fires each set carries "
    "records for in this county and does not compare structure against structure. A "
    "disagreement says the two record sets differ; it does not say which one is right."
)

NO_RATE_NOTE: Final[str] = (
    "No rate is taken between the two record sets in either direction. Two "
    "organizations counting two populations under two rules means neither file is the "
    "other's denominator, and the quotient would read as coverage of one by the other. "
    "No damage rate is published for this county from either file, for the reason ADR "
    "0004 gives for a territory and ADR 0009 gives for a county."
)


def _check(block: dict[str, Any], *, ceiling: int) -> None:
    """The publication rules that apply to a block which is not in the published tree.

    Four of them run unchanged, because a block this command prints is a block a
    maintainer may paste into a document. ``assert_collections_are_ordered_as_declared``
    deliberately does not: ``artifacts.ORDERINGS`` is the ledger of the published
    artifact, and a test refuses an entry there for a collection the artifact does not
    carry. The incident collection is sorted by name at the point it is built and
    ``tests/test_cross_check.py`` reads the order back; it joins the ledger on the day
    the block joins the artifact, which ADR 0015 makes part of that change.

    ``assert_aggregate_only`` runs against the same bound ``_refuse_an_oversized_union``
    already refuses at, so on this block it is a second lock that the refusal reaches
    first. That is said here rather than left for somebody to discover, because this
    repository has a written-down audit of gates that were numerically incapable of
    firing and the refusal is the one carrying the test that fires.
    """
    artifacts.assert_rates_are_denominated(block)
    artifacts.assert_no_locating_fields(block)
    artifacts.assert_no_ranking(block)
    artifacts.assert_aggregate_only(block, ceiling)


def as_block(result: CrossCheck) -> dict[str, Any]:
    """The comparison as an artifact-shaped block, checked before it is returned."""
    outcomes = result.outcomes
    named_there = (
        outcomes[IN_BOTH]
        + outcomes[HERE_UNDER_ANOTHER_COUNTY]
        + outcomes[ABSENT_FROM_THIS_RECORD_SET]
    )
    named_here = outcomes[IN_BOTH] + outcomes[NOT_NAMED_BY_THE_COUNTY_RECORD_SET]
    block = {
        BLOCK_KEY: {
            "question": (
                "Which fires does one county's own inspection record set carry records "
                "for in that county, and which of them does this project count there?"
            ),
            "county": result.county,
            "records": {
                "in_this_project_for_this_county": result.records_here_in_this_county,
                "in_this_project_carrying_an_incident_name": (
                    result.records_here_carrying_an_incident_name
                ),
                "in_the_county_record_set": result.records_in_the_county_record_set,
            },
            "incidents_named_by_the_county_record_set": named_there,
            "incidents_this_project_counts_in_this_county": named_here,
            "counts": outcomes,
            "agreement_with_the_county_record_set": Rate.of(
                "fires the county's record set names that this project also counts here",
                outcomes[IN_BOTH],
                named_there,
                note="Denominator: the fires the county's own record set names.",
            ).as_dict(),
            "agreement_with_this_record_set": Rate.of(
                "fires this project counts here that the county's record set also names",
                outcomes[IN_BOTH],
                named_here,
                note=(
                    "Denominator: the fires this project counts in this county. Two "
                    "questions with two denominators, so no difference is drawn between "
                    "this share and the one above."
                ),
            ).as_dict(),
            "incidents": [row.as_dict() for row in result.incidents],
            "note": AGREEMENT_NOTE,
            "no_rate_is_taken_between_the_two_record_sets": NO_RATE_NOTE,
        }
    }
    _check(block, ceiling=result.incident_ceiling)
    return block


def cross_check(
    county: str, dins_rows: list[dict[str, Any]], external_payload: Any
) -> dict[str, Any]:
    """The whole comparison from two files already read, as one checked block."""
    records, _ = read_records(dins_rows)
    external = read_external(external_payload, county=county)
    return as_block(compare(county, records, external))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    """Read two local files, print one JSON block. No network, ever.

    Exit codes: ``0`` when the comparison was made, ``1`` when it was refused, ``2``
    when an input could not be read at all.
    """
    parser = argparse.ArgumentParser(
        prog="python -m wildfire_service_territory_overlap.cross_check",
        description=(
            "Compare one county's own inspection record set against this project's "
            "counts for that county, as agreement and disagreement counts. Neither "
            "side is corrected and neither is treated as the truth. Reads local files "
            "only; see docs/adr/0015 and docs/RUNBOOK.md."
        ),
    )
    parser.add_argument("--county", required=True, help="the one county in scope")
    parser.add_argument(
        "--dins", type=Path, required=True, help="the pinned DINS retrieval"
    )
    parser.add_argument(
        "--external",
        type=Path,
        required=True,
        help="the county's own inspection records, as rows of county and incident",
    )
    args = parser.parse_args(argv)
    try:
        dins_rows = _load(args.dins)
        external_payload = _load(args.external)
    except OSError as error:
        print(f"could not read an input: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(f"an input is not valid JSON: {error}", file=sys.stderr)
        return 2
    try:
        block = cross_check(args.county, dins_rows, external_payload)
    except (CrossCheckRefused, SchemaError, artifacts.PublicationRefused) as error:
        print(f"cross-check refused: {error}", file=sys.stderr)
        return 1
    print(artifacts.serialize(block), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
