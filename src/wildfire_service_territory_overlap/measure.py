"""The measurements, and the two the data does not support.

What is published
-----------------
1. **Placement coverage.** Of every wildfire damage-inspection record, the share that
   falls inside exactly one published service territory, the share that falls inside
   more than one, the share that falls inside none, and the share whose coordinate could
   not be used. Denominator: the fire record set.
2. **Whether the placeable records look like the unplaceable ones.** The destroyed share
   among placed records against the destroyed share among contested records, each with
   its own denominator and interval, and the difference with a Newcombe interval. If the
   two populations differ, then any territory-level reading of the placed subset is
   drawn from a subset that is not representative, and the size of that problem is
   published rather than left for the reader to worry about.
3. **Per territory, counts.** Placed, contested, which territories the contest is with,
   how many distinct incidents, and the share of the territory's placed records
   contributed by its single largest incident. Alphabetical.
4. **Per territory, how much of it sits near a published edge.** The publisher says the
   boundaries are approximate. This says how much would move if they are off by 100,
   250, 500 or 1000 meters.
5. **Whether being unattributable is a property of the data or of the fire.** The share
   of incidents whose classified records fall entirely on one side of the contested
   line, the contested share within each incident year, and the contested share within
   each published county, each with its own denominator. Denominators: the incident set,
   the classified records of one year, and the classified records of one county.
6. **What the judgment calls are worth**, in :mod:`wildfire_service_territory_overlap.sensitivity`: the whole
   placement re-run under each alternative reading of the publisher's ``Type`` field,
   under the other geometry repair, and without every outline that holds no record.

What is not published, and why
------------------------------
**No damage rate is published for a territory.** It would be arithmetic that looks like
a statement about a utility and is not one. Measurement 3 is the evidence: in several
territories a single incident contributes most of the placed records, so a
territory-level destroyed share would be a statement about one fire that happened to
burn there. Publishing that number next to another utility's number would invite a
comparison that the data cannot support, and this project does not publish it in any
form, ordered or unordered.

**No territory is ranked, scored, or ordered by any measured value.** Every collection
in the output is sorted by name.

**No rate is published against a denominator drawn from outside this record set.** Not
housing units, not customers, not meters, not parcels. The numerator here is a
population defined by where fires burned and which land is in the state responsibility
area, and dividing it by a population defined some other way produces a number whose
denominator does not contain its numerator.

**No trend over time.** The contested share is published per incident year and no
direction is drawn through it. The territory layer is a single retrieval, so every year
in the table is measured against the same boundaries, and a rise across years would be a
statement about where those years' fires burned dressed up as a statement about the data
improving or degrading.

**No damage rate is published for a county either.** The county cut carries the contested
share and nothing else. Destroyed over inspected inside a county line would be the same
arithmetic ADR 0004 refuses for a territory, with a place name on it instead of a company
name, and it would still be describing which fires burned where.

**No county is compared against another, and no county is named as a cause.** Counties
come out in name order with their own denominators, exactly as the years do. Which
counties the published outlines overlap in is visible from the rows; it is not restated
as a ranking.
"""

from __future__ import annotations

from typing import Any

from wildfire_service_territory_overlap.geometry import Territory
from wildfire_service_territory_overlap.intervals import Difference, Rate
from wildfire_service_territory_overlap.placement import BOUNDARY_BANDS_M, Placement
from wildfire_service_territory_overlap.sources import EXCLUDED_TYPES


def placement_coverage(placement: Placement) -> dict[str, Any]:
    """How much of the record set can be attributed at all."""
    total = placement.fire_records
    return {
        "fire_records": total,
        "excluded_by_hazard_filter": placement.excluded_by_hazard,
        "counts": {
            "placed_in_exactly_one_territory": placement.placed,
            "contested_between_two_or_more": placement.contested,
            "covered_by_no_published_territory": placement.uncovered,
            "coordinate_not_usable": placement.not_measured,
        },
        "counts_sum_to_fire_records": placement.classified == total,
        "rates": [
            Rate.of(
                "placed in exactly one published territory", placement.placed, total
            ).as_dict(),
            Rate.of(
                "inside two or more published territories", placement.contested, total
            ).as_dict(),
            Rate.of(
                "inside no published territory", placement.uncovered, total
            ).as_dict(),
            Rate.of("coordinate not usable", placement.not_measured, total).as_dict(),
        ],
    }


def representativeness(placement: Placement) -> dict[str, Any]:
    """Do the records that can be attributed resemble the records that cannot."""
    placed = Rate.of(
        "destroyed share among placed records",
        placement.destroyed_placed,
        placement.placed,
    )
    contested = Rate.of(
        "destroyed share among contested records",
        placement.destroyed_contested,
        placement.contested,
    )
    uncovered = Rate.of(
        "destroyed share among records in no published territory",
        placement.destroyed_uncovered,
        placement.uncovered,
    )
    difference = Difference.between(
        "placed minus contested, destroyed share",
        placed,
        contested,
        note=(
            "A difference whose interval excludes zero means the records that can be "
            "attributed to one territory are not a representative sample of the record "
            "set, and a territory-level reading of them inherits that."
        ),
    )
    return {
        "placed": placed.as_dict(),
        "contested": contested.as_dict(),
        "uncovered": uncovered.as_dict(),
        "difference": difference.as_dict(),
    }


def _band_rate_block(
    distance_state: str, within_band: dict[int, int], denominator: int
) -> dict[str, Any]:
    """The proximity block for a contested-group row.

    The denominator is the combination's own record count: every one of its records has
    a nearest-edge distance among the group's outlines, whether or not it falls inside
    any single band.
    """
    if distance_state != "measured":
        return {
            "state": distance_state,
            "bands_m": list(BOUNDARY_BANDS_M),
            "rates": [
                Rate.not_measured(
                    f"within {band} m of an edge in this combination",
                    reason="no records are contested here, so no distance exists",
                ).as_dict()
                for band in BOUNDARY_BANDS_M
            ],
        }
    return {
        "state": distance_state,
        "bands_m": list(BOUNDARY_BANDS_M),
        "rates": [
            Rate.of(
                f"within {band} m of an edge in this combination",
                within_band[band],
                denominator,
                note=(
                    "Distance to the nearest edge among every outline in the "
                    "combination. A contested record stops being contested when any "
                    "of them ceases to contain it, so the nearest edge is the one an "
                    "approximation error moves first."
                ),
            ).as_dict()
            for band in BOUNDARY_BANDS_M
        ],
    }


def _band_rates(tally: Any) -> list[dict[str, Any]]:
    if tally.distance_state != "measured":
        return [
            Rate.not_measured(
                f"within {band} m of the published edge",
                reason="no records are placed in this territory, so no distance exists",
            ).as_dict()
            for band in BOUNDARY_BANDS_M
        ]
    return [
        Rate.of(
            f"within {band} m of the published edge",
            tally.within_band[band],
            tally.placed,
            note=(
                "The publisher states the boundaries are approximate. This is how much "
                "of the territory's placed total sits close enough to the edge to be "
                "affected if the approximation is off by this much."
            ),
        ).as_dict()
        for band in BOUNDARY_BANDS_M
    ]


def _concentration(tally: Any) -> dict[str, Any]:
    largest = tally.largest_incident
    if largest is None or tally.placed == 0:
        return {
            "largest_incident": None,
            "share": Rate.not_measured(
                "share of placed records from the largest single incident",
                reason="no records are placed in this territory",
            ).as_dict(),
        }
    name, count = largest
    return {
        "largest_incident": name,
        "share": Rate.of(
            "share of placed records from the largest single incident",
            count,
            tally.placed,
            note=(
                "Where this is high, a territory-level damage rate would describe one "
                "fire rather than a territory. That is why no such rate is published."
            ),
        ).as_dict(),
    }


def territory_rows(
    placement: Placement, territories: tuple[Territory, ...]
) -> list[dict[str, Any]]:
    """One row per published territory, alphabetical, counts and within-row rates only."""
    rows: list[dict[str, Any]] = []
    for territory in territories:
        tally = placement.tallies[territory.name]
        rows.append(
            {
                "territory": territory.name,
                "published_type": territory.kind,
                "source_layer": territory.source_key,
                "geometry_state": territory.geometry_state,
                "geometry_note": territory.geometry_note,
                "records_placed_here": tally.placed,
                "records_contested_here": tally.contested,
                "contested_with": sorted(tally.contested_with),
                "distinct_incidents_among_placed": len(tally.incidents),
                "incident_concentration": _concentration(tally),
                "boundary_proximity": {
                    "state": tally.distance_state,
                    "bands_m": list(BOUNDARY_BANDS_M),
                    "rates": _band_rates(tally),
                },
            }
        )
    return sorted(rows, key=lambda row: str(row["territory"]))


def contested_groups(placement: Placement, limit: int = 25) -> list[dict[str, Any]]:
    """The overlapping combinations, as counts, largest first.

    Largest first is a size and not a ranking: a row here is a combination of published
    outlines rather than an entity, no row carries a rate about a utility, and no named
    entity stands alone on one. It is also the only order the cap can work with, since
    the rows kept are the largest combinations and a name order cannot select those.

    This is one of the four collections `artifacts.ORDERINGS` records as deliberately
    not in name order, and the reason lives there as well as here, because the README
    once claimed without qualification that every collection was in name order and
    nothing read the claim against the code.

    The cap can cut. Nothing in the rendering says how many combinations were dropped,
    so `artifacts.assert_contested_groups_are_whole` refuses an artifact whose rows do
    not sum to the published contested total, and the build stops rather than
    publishing this table short.
    """
    items = sorted(placement.contested_groups.items(), key=lambda kv: (-kv[1], kv[0]))[
        :limit
    ]
    rows: list[dict[str, Any]] = []
    for names, count_ in items:
        row: dict[str, Any] = {"territories": list(names), "records": count_}
        bands = placement.contested_bands.get(names)
        if bands is not None:
            row["boundary_proximity"] = _band_rate_block(
                placement.contested_distance_state.get(names, "not_measured"),
                bands,
                count_,
            )
        rows.append(row)
    return rows


def geometry_ledger(
    placement: Placement,
    territories: tuple[Territory, ...],
    unusable: tuple[Territory, ...],
) -> dict[str, Any]:
    """Which published polygons arrived invalid, and how much rests on the repair.

    Naming the repaired polygons is not enough on its own. The repair is a modeling
    decision, a different repair puts a different set of records inside a different set
    of outlines, and a reader deciding how much to trust the result needs the size of
    the exposure rather than the fact of it.
    """
    from_repaired = sum(
        placement.tallies[t.name].placed for t in territories if t.repaired
    )
    return {
        "territories_indexed": len(territories),
        "territories_repaired": sum(1 for t in territories if t.repaired),
        "repaired": sorted(t.name for t in territories if t.repaired),
        "records_placed_via_repaired_geometry": Rate.of(
            "placed records that sit inside a polygon this project repaired",
            from_repaired,
            placement.placed,
            note=(
                "A repair is a choice. This is how much of the placed total depends on "
                "it, so a reader can weigh the result rather than take it whole."
            ),
        ).as_dict(),
        "unusable": [
            {"territory": t.name, "reason": t.geometry_note}
            for t in sorted(unusable, key=lambda t: t.name)
        ],
        "unusable_count": len(unusable),
        "note": (
            "A polygon that fails an OGC validity check gives undefined answers to a "
            "containment question, so it is repaired before use and named here. A "
            "polygon that cannot be repaired into a testable shape is removed from the "
            "index and is not reported as holding zero records."
        ),
    }


def excluded_type_note() -> list[dict[str, str]]:
    """The published entity types this project does not read as a service territory."""
    return [
        {"published_type": kind, "reason": reason}
        for kind, reason in sorted(EXCLUDED_TYPES.items())
    ]


def years(placement: Placement) -> list[dict[str, int]]:
    """Fire records per incident year, so the span of the record set is visible."""
    return [
        {"year": year, "records": count}
        for year, count in sorted(placement.years.items())
    ]


def _incident_split(placement: Placement) -> dict[str, Any]:
    """How many incidents are wholly contested, wholly uncontested, or split."""
    totals = placement.incident_classified
    contested = placement.incident_contested
    distinct = len(totals)
    all_contested = [name for name, n in totals.items() if contested[name] == n]
    none_contested = [name for name, n in totals.items() if contested[name] == 0]
    settled = len(all_contested) + len(none_contested)
    in_settled = sum(totals[name] for name in all_contested + none_contested)
    classified = sum(totals.values())
    return {
        "distinct_incidents": distinct,
        "records_carrying_an_incident_name": classified,
        "every_record_contested": Rate.of(
            "incidents whose every classified record is contested",
            len(all_contested),
            distinct,
        ).as_dict(),
        "no_record_contested": Rate.of(
            "incidents no record of which is contested", len(none_contested), distinct
        ).as_dict(),
        "split_both_ways": Rate.of(
            "incidents with records on both sides", distinct - settled, distinct
        ).as_dict(),
        "one_way_or_the_other": Rate.of(
            "incidents that fall entirely on one side", settled, distinct
        ).as_dict(),
        "records_in_an_incident_that_falls_entirely_on_one_side": Rate.of(
            "records belonging to an incident that falls entirely on one side",
            in_settled,
            classified,
        ).as_dict(),
    }


def _by_year(placement: Placement) -> list[dict[str, Any]]:
    """The span of the record set, and the contested share within each year.

    ``records`` is every fire record carrying that incident year. ``records_classified``
    is the subset that had a usable coordinate and therefore an outcome, and it is the
    denominator of the share, so a year of records that could not be placed reads as not
    measured rather than as a year with no overlap.
    """
    rows: list[dict[str, Any]] = []
    for row in years(placement):
        year = row["year"]
        classified = placement.year_classified[year]
        rows.append(
            {
                "year": year,
                "records": row["records"],
                "records_classified": classified,
                "contested": Rate.of(
                    "inside two or more published territories, this year",
                    placement.year_contested[year],
                    classified,
                ).as_dict(),
            }
        )
    return rows


def _by_county(placement: Placement) -> list[dict[str, Any]]:
    """The contested share within each published county, in name order.

    ``records`` is every fire record CAL FIRE recorded that county on.
    ``records_classified`` is the subset that had a usable coordinate and therefore an
    outcome, and it is the denominator of the share, so a county whose records could not
    be placed reads as not measured rather than as a county with no overlap.

    Name order, never size order. The counties where the published outlines overlap are
    readable from the rows, and sorting by the share would turn that into a league table
    of places, which is ADR 0004's objection with a county name in place of a company
    name.
    """
    rows: list[dict[str, Any]] = []
    for county in sorted(placement.counties):
        classified = placement.county_classified[county]
        rows.append(
            {
                "county": county,
                "records": placement.counties[county],
                "records_classified": classified,
                "contested": Rate.of(
                    "inside two or more published territories, in this county",
                    placement.county_contested[county],
                    classified,
                ).as_dict(),
            }
        )
    return rows


def attributability_by_fire(placement: Placement) -> dict[str, Any]:
    """Is the unattributable share a property of the record set or of the fire?

    The headline figure is one number over the whole record set, which invites reading
    it as a property of the two datasets. It is not. The published outlines overlap in
    particular places, so whether a record is contested is mostly settled by where its
    fire burned, and this measures how strongly.

    Three cuts, each with its own denominator: the incident set, the classified records
    of one year, and the classified records of one county. No trend is published across
    the years and none can be: the territory layer is a single retrieval, so a
    year-over-year change in the contested share is a change in where fires burned
    against fixed boundaries, not a change in the boundaries. The dispersion is the
    finding; a direction over time would be an artifact.
    """
    return {
        "question": (
            "Is being inside more than one published outline a property of the record "
            "set, or a property of where a particular fire burned?"
        ),
        "by_incident": _incident_split(placement),
        "by_incident_year": _by_year(placement),
        "by_county": _by_county(placement),
        "counties_named_in_the_record_set": len(placement.counties),
        "records_carrying_no_county_name": placement.records_with_no_county,
        "no_trend_is_published": (
            "The territory layer is one retrieval, so the boundaries are identical for "
            "every year in the table. A rise or fall across years would describe where "
            "that year's fires burned, not a change in the published boundaries, and it "
            "is not published as a trend."
        ),
        "note": (
            "Incident and county names come from the published INCIDENTNAME and COUNTY "
            "fields and are counted as published. A record with no incident name is "
            "left out of the incident cut, a record with no county name is left out of "
            "the county cut, and both stay in every other denominator in this project."
        ),
        "county_note": (
            "The county cut carries the contested share and nothing else. A county is "
            "not a service territory and this is not a statement about who serves it: "
            "it says where in California the published outlines overlap each other. No "
            "damage rate is published for a county, for the same reason none is "
            "published for a territory."
        ),
    }


def representativeness_by_category(placement: Placement) -> list[dict[str, Any]]:
    """The placed-versus-contested destroyed-share check, inside each structure class.

    The headline check compares two populations across the whole record set. This runs
    the same comparison inside each published ``STRUCTURECATEGORY``, because a
    difference confined to one class would be hidden by the aggregate and a difference
    spread across every class is sturdier than one number. Categories in name order;
    no category is compared against another. A class with no contested records has no
    difference to measure, which is published as not measured rather than as zero.
    """
    rows: list[dict[str, Any]] = []
    for category in sorted(
        set(placement.category_placed) | set(placement.category_contested)
    ):
        placed_n = placement.category_placed[category]
        contested_n = placement.category_contested[category]
        placed = Rate.of(
            f"destroyed share among placed records, {category}",
            placement.category_destroyed_placed[category],
            placed_n,
        )
        contested = Rate.of(
            f"destroyed share among contested records, {category}",
            placement.category_destroyed_contested[category],
            contested_n,
        )
        row: dict[str, Any] = {
            "structure_category": category,
            "placed": placed.as_dict(),
            "contested": contested.as_dict(),
        }
        if placed_n > 0 and contested_n > 0:
            row["difference"] = Difference.between(
                f"placed minus contested, destroyed share, {category}",
                placed,
                contested,
                note=(
                    "The same records measured twice within one published structure "
                    "class. The Newcombe interval is the conservative bound; the exact "
                    "figures are the counts above."
                ),
            ).as_dict()
        rows.append(row)
    return rows


def coordinate_county_agreement(
    agreement: Any,
    records_total: int,
) -> dict[str, Any]:
    """Does a record's coordinate sit in the county its publisher recorded?

    Counted against an authoritative boundary layer, never corrected: CAL FIRE's
    ``COUNTY`` field is reported as published everywhere else in this project, and this
    block measures how often it and a coordinate disagree rather than adjudicating
    between them. The boundary layer's publisher warns that its own errors will exist,
    so a disagreement is evidence that two sources differ and not a verdict on which
    one is right.
    """

    def _clean_share(numerator: int, denominator: int) -> dict[str, Any]:
        if denominator <= 0:
            return Rate.not_measured(
                "records whose coordinate sits outside the recorded county",
                reason="no comparable records",
            ).as_dict()
        return Rate.of(
            "records whose coordinate sits outside the recorded county",
            numerator,
            denominator,
        ).as_dict()

    rows = [
        {
            "county": tally.label,
            "resolved": tally.resolved,
            "agreed": tally.agreed,
            "matched_no_county": tally.matched_no_county,
            "disagreed": _clean_share(tally.disagreed, tally.resolved),
        }
        for tally in sorted(agreement.per_label.values(), key=lambda t: t.label)
    ]
    return {
        "question": (
            "How often does a record's coordinate land outside the county its "
            "publisher recorded?"
        ),
        "records_compared": _share_or_not_measured(
            agreement.resolved,
            records_total,
            "records whose county label and coordinate could both be compared",
            note=(
                "The denominator is the whole wildfire record set. A record joins "
                "this comparison only with a usable coordinate and a county label the "
                "boundary layer carries; everything else stays counted where it "
                "already was."
            ),
        ),
        "agreed": _share_or_not_measured(
            agreement.agreed,
            agreement.resolved,
            "coordinate and recorded county agree",
            note="Denominator: the comparable records.",
        ),
        "disagreed": _share_or_not_measured(
            agreement.disagreed,
            agreement.resolved,
            "coordinate sits outside the recorded county",
            note=(
                "Denominator: the comparable records above. The boundary layer's "
                "publisher states that boundary errors will exist, so these are "
                "counts of disagreement, not corrections."
            ),
        ),
        "matched_no_county": _share_or_not_measured(
            agreement.matched_no_county,
            agreement.resolved,
            "comparable records whose coordinate reaches no county polygon",
        ),
        "unmatchable_label": _share_or_not_measured(
            agreement.unmatchable_label,
            records_total,
            "records whose COUNTY label the boundary layer does not carry",
        ),
        "by_county": rows,
        "note": (
            "Counted, never corrected. The COUNTY field is published by CAL FIRE and "
            "is reported as published everywhere else in this project; the boundary "
            "layer comes from the California Department of Technology, whose metadata "
            "warns that boundary errors will exist. Where the two disagree, this "
            "project says how often and does not say who is right."
        ),
    }


def _share_or_not_measured(
    numerator: int,
    denominator: int,
    label: str,
    note: str = "",
) -> dict[str, Any]:
    """A rate with its denominator, or an honest not-measured when there is none."""
    if denominator <= 0:
        return Rate.not_measured(
            label, reason="no records could be compared, so no share exists"
        ).as_dict()
    return Rate.of(label, numerator, denominator, note=note).as_dict()
