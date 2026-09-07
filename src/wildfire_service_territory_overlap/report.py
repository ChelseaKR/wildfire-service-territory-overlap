"""The measurements, rendered once, deterministically, as Markdown.

Every number on the page comes from the artifact rather than from a second calculation,
so the document and the JSON cannot disagree. A rate that could not be made prints as
words and never as ``0.0%``.

No prose is written in this module. Every word it emits comes from a
:class:`~wildfire_service_territory_overlap.catalog.Catalog`, which :func:`render` takes
as a parameter defaulting to the English one, so a second edition is a catalog rather
than a second renderer. The numeric helpers below take no catalog and cannot be given
one: how a number is written is not a property of the language it is written beside,
and one artifact does not punctuate its figures two ways.
"""

from __future__ import annotations

from typing import Any

from wildfire_service_territory_overlap.catalog import ENGLISH, Catalog


def pct(value: float) -> str:
    """One decimal place, except where that would print a real measurement as zero.

    A share of three in a hundred thousand is a measurement. Rendering it as `0.0%`
    alongside an interval of `0.0% to 0.0%` reads as certainty about an absence, which is
    the one thing this project is trying never to say by accident.

    A rate that was not measured never reaches here: :func:`share` and :func:`difference`
    hold that branch, because "not measured" is words and this function writes numbers.
    """
    if value == 0.0:
        return "0.0%"
    # On magnitude, not on sign. Testing `value * 100 < 0.05` sent every negative number
    # down the high-precision branch, so a difference of minus a third of a percentage
    # point printed to four decimals beside a positive one printed to one.
    if abs(value) * 100 < 0.05:
        return f"{value * 100:.4f}%"
    return f"{value * 100:.1f}%"


def count(value: int) -> str:
    """Thousands separated. Six-figure record counts are the point of several tables."""
    return f"{value:,}"


def span(low: float, high: float) -> tuple[str, str]:
    """Both ends of an interval, at enough precision to tell them apart.

    :func:`pct` prints one decimal place. Over a six-figure denominator two genuinely
    different bounds round to the same string, and an interval printed as `0.7% to 0.7%`
    reads as certainty, which is the opposite of what an interval is there to say. The
    precision rises until the two ends differ, or until four places has shown that they
    really do not.

    The two ends are returned rather than joined: the word between them is language and
    belongs to the catalog, and the numbers are not.
    """
    rendered = [
        (f"{low * 100:.{places}f}%", f"{high * 100:.{places}f}%")
        for places in (1, 2, 3, 4)
    ]
    for lower, upper in rendered:
        if lower != upper:
            return lower, upper
    return rendered[0]


def share(node: dict[str, Any], cat: Catalog) -> str:
    """A rate as a percentage, or the catalog's words for one that was not measured."""
    if node.get("state") != "measured":
        return cat["words.not_measured"]
    return pct(node["rate"])


def difference(node: dict[str, Any], cat: Catalog) -> str:
    """The same, for a difference between two rates."""
    if node.get("state") != "measured":
        return cat["words.not_measured"]
    return pct(node["difference"])


def interval(node: dict[str, Any], cat: Catalog) -> str:
    if node.get("state") != "measured":
        return cat["words.not_measured"]
    low, high = span(node["interval_low"], node["interval_high"])
    return cat["words.interval"].format(low=low, high=high)


def rate_line(node: dict[str, Any], cat: Catalog) -> str:
    if node.get("state") != "measured":
        words = cat["words.not_measured"]
        return f"| {node['label']} | {words} | {node['numerator']} | 0 | {words} |"
    return (
        f"| {node['label']} | {pct(node['rate'])} | {count(node['numerator'])} | "
        f"{count(node['denominator'])} | {interval(node, cat)} |"
    )


def _header(tree: dict[str, Any], cat: Catalog) -> list[str]:
    prov = tree["provenance"]
    return [
        cat["header.title"],
        "",
        cat["header.unofficial"],
        "",
        cat["header.retrieval"].format(
            dins_retrieved=prov["dins_retrieved"],
            territories_retrieved=prov["territories_retrieved"],
            territories_item_modified=prov["territories_item_modified"],
        ),
        "",
        cat["header.generated"],
        "",
    ]


def _coverage(tree: dict[str, Any], cat: Catalog) -> list[str]:
    cov = tree["placement_coverage"]
    lines = [
        cat["coverage.heading"],
        "",
        cat["coverage.intro"].format(
            fire_records=count(cov["fire_records"]),
            excluded_by_hazard_filter=count(cov["excluded_by_hazard_filter"]),
        ),
        "",
        cat["coverage.table_head"],
    ]
    lines.extend(rate_line(node, cat) for node in cov["rates"])
    lines.extend(["", cat["coverage.contested_note"], ""])
    return lines


def _representativeness(tree: dict[str, Any], cat: Catalog) -> list[str]:
    rep = tree["representativeness"]
    diff = rep["difference"]
    verdict = (
        cat["representativeness.verdict.differs"]
        if diff.get("excludes_zero")
        else cat["representativeness.verdict.no_difference"]
    )
    return [
        cat["representativeness.heading"],
        "",
        cat["representativeness.table_head"],
        rate_line(rep["placed"], cat),
        rate_line(rep["contested"], cat),
        rate_line(rep["uncovered"], cat),
        "",
        cat["representativeness.difference"].format(
            difference=difference(diff, cat), interval=interval(diff, cat)
        ),
        "",
        verdict,
        "",
    ]


def _contested(tree: dict[str, Any], cat: Catalog) -> list[str]:
    rows = tree["contested_groups"]
    lines = [
        cat["contested.heading"],
        "",
        cat["contested.intro"],
        "",
        cat["contested.edge_note"],
        "",
        cat["contested.table_head"],
    ]
    for row in rows:
        rate_250 = _edge_band_rate(row, 250)
        cell = (
            cat["words.not_measured"]
            if rate_250["state"] != "measured"
            else f"{share(rate_250, cat)} ({interval(rate_250, cat)})"
        )
        lines.append(
            f"| {', '.join(row['territories'])} | {count(row['records'])} | {cell} |"
        )
    lines.append("")
    return lines


def _edge_band_rate(row: dict[str, Any], band_m: int) -> dict[str, Any]:
    """The one band rate a row carries for a given distance.

    Read by the band's own distance rather than by matching words in the band's label,
    so the renderer asks the artifact a numeric question and never an English one.
    """
    proximity: dict[str, Any] = row["boundary_proximity"]
    index: int = proximity["bands_m"].index(band_m)
    rate: dict[str, Any] = proximity["rates"][index]
    return rate


def _territories(tree: dict[str, Any], cat: Catalog) -> list[str]:
    lines = [
        cat["territories.heading"],
        "",
        cat["territories.intro"],
        "",
        cat["territories.contested_note"],
        "",
        cat["territories.table_head"],
    ]
    for row in tree["territories"]:
        concentration = row["incident_concentration"]["share"]
        near = _edge_band_rate(row, 250)
        lines.append(
            f"| {row['territory']} | {row['published_type']} | "
            f"{count(row['records_placed_here'])} | "
            f"{count(row['records_contested_here'])} | "
            f"{row['distinct_incidents_among_placed']} | "
            f"{share(concentration, cat)} | "
            f"{share(near, cat)} | "
            f"{row['geometry_state']} |"
        )
    lines.append("")
    return lines


def _ledger(tree: dict[str, Any], cat: Catalog) -> list[str]:
    ledger = tree["geometry_ledger"]
    lines = [
        cat["ledger.heading"],
        "",
        cat["ledger.intro"].format(
            territories_indexed=ledger["territories_indexed"],
            territories_repaired=ledger["territories_repaired"],
        ),
        "",
    ]
    if ledger["repaired"]:
        lines.extend([f"- {name}" for name in ledger["repaired"]])
        lines.append("")
    repaired_share = ledger["records_placed_via_repaired_geometry"]
    lines.extend(
        [
            cat["ledger.repaired_share"].format(
                records=count(repaired_share["numerator"]),
                share=share(repaired_share, cat),
                interval=interval(repaired_share, cat),
            ),
            "",
            cat["ledger.unusable"].format(unusable_count=ledger["unusable_count"]),
            "",
            cat["ledger.excluded_types"],
            "",
        ]
    )
    lines.extend(
        f"- **{row['published_type']}**: {row['reason']}"
        for row in tree["excluded_types"]
    )
    lines.append("")
    return lines


def _by_fire(tree: dict[str, Any], cat: Catalog) -> list[str]:
    block = tree["attributability_by_fire"]
    incidents = block["by_incident"]
    settled = incidents["records_in_an_incident_that_falls_entirely_on_one_side"]
    lines = [
        cat["by_fire.heading"],
        "",
        cat["by_fire.intro"],
        "",
        cat["by_fire.incidents"].format(
            distinct_incidents=count(incidents["distinct_incidents"]),
            one_way_share=share(incidents["one_way_or_the_other"], cat),
            one_way_interval=interval(incidents["one_way_or_the_other"], cat),
            records_in_settled_share=share(settled, cat),
        ),
        "",
        cat["by_fire.incident_table_head"],
        rate_line(incidents["every_record_contested"], cat),
        rate_line(incidents["no_record_contested"], cat),
        rate_line(incidents["split_both_ways"], cat),
        "",
        cat["by_fire.by_year_intro"],
        "",
        cat["by_fire.year_table_head"],
    ]
    for row in block["by_incident_year"]:
        node = row["contested"]
        lines.append(
            f"| {row['year']} | {count(row['records'])} | "
            f"{count(row['records_classified'])} | "
            f"{share(node, cat)} | "
            f"{interval(node, cat)} |"
        )
    lines.append("")
    lines.extend(_by_county(block, cat))
    return lines


def _by_county(block: dict[str, Any], cat: Catalog) -> list[str]:
    """The same cut by county, in name order, with the same refusals stated."""
    lines = [
        cat["by_county.intro"].format(
            counties_named=block["counties_named_in_the_record_set"],
            records_with_no_county=count(block["records_carrying_no_county_name"]),
        ),
        "",
        block["county_note"],
        "",
        cat["by_county.table_head"],
    ]
    for row in block["by_county"]:
        node = row["contested"]
        lines.append(
            f"| {row['county']} | {count(row['records'])} | "
            f"{count(row['records_classified'])} | "
            f"{share(node, cat)} | "
            f"{interval(node, cat)} |"
        )
    lines.append("")
    return lines


def _sensitivity_types(tree: dict[str, Any], cat: Catalog) -> list[str]:
    block = tree["sensitivity"]["type_inclusion"]
    lines = [
        cat["type_inclusion.heading"],
        "",
        cat["type_inclusion.intro"],
        "",
        block["the_published_type_field_is_undocumented"],
        "",
        cat["type_inclusion.table_head"],
    ]
    for row in block["variants"]:
        node = row["contested"]
        moved_by = row.get("contested_difference_from_the_rule_as_built")
        moved = (
            cat["type_inclusion.reference"]
            if moved_by is None
            else f"{difference(moved_by, cat)} ({interval(moved_by, cat)})"
        )
        lines.append(
            f"| {row['variant']} | {row['territories_indexed']} | "
            f"{count(node['numerator'])} | {share(node, cat)} | "
            f"{interval(node, cat)} | {moved} | "
            f"{count(row['counts']['covered_by_no_published_territory'])} |"
        )
    lines.extend(["", cat["type_inclusion.closing"], ""])
    lines.extend(_sensitivity_supplied_rules(block, cat))
    return lines


def _sensitivity_supplied_rules(block: dict[str, Any], cat: Catalog) -> list[str]:
    """Who supplied each reviewer-written row, on what date, and what it overrides.

    Nothing renders when no rule file was supplied, so a build that was given none
    writes exactly the document it wrote before this section existed. The table above
    already carries the supplied rows and their figures; this names the reviewer's
    role and date beside each, because a measured alternative whose provenance is not
    published is a row a reader cannot weigh.
    """
    supplied = [row for row in block["variants"] if row.get("supplied_by_a_reviewer")]
    if not supplied:
        return []
    lines = [
        cat["type_inclusion.supplied_heading"],
        "",
        cat["type_inclusion.supplied_intro"],
        "",
    ]
    for row in supplied:
        lines.append(
            cat["type_inclusion.supplied_row"].format(
                variant=row["variant"],
                role=row["reviewer_role"],
                reviewed_on=row["reviewed_on"],
                rule_file=row["rule_file"],
            )
        )
        for outline, override in sorted(row["outline_overrides"].items()):
            # Read out of the subscript first. A key lookup left inside `cat[...]`
            # reads to the catalog-completeness gate as a catalog key being asked
            # for, and the artifact key would be reported as a string with no
            # entry behind it.
            reads_it = override["read_as_a_territory"]
            lines.append(
                cat[
                    "type_inclusion.supplied_override_read"
                    if reads_it
                    else "type_inclusion.supplied_override_not_read"
                ].format(outline=outline, reason=override["reviewer_reason"])
            )
        lines.append("")
    return lines


def _sensitivity_repair(tree: dict[str, Any], cat: Catalog) -> list[str]:
    block = tree["sensitivity"]["repair_strategy"]
    changed = block["records_with_a_different_outcome"]
    # Two renderings, chosen by what the artifact carries rather than by a version
    # number. A tree built before the third repair joined carries no census keys, and
    # its committed REPORT.md must keep matching exactly what its own run wrote. The
    # branch goes away at the next deliberate refresh, when every published tree is
    # three-repair; until then both readings are kept honest.
    widened = "strategies_compared" in block
    lines = [
        cat["repair.heading"],
        "",
    ]
    if widened:
        union = block["records_where_any_two_repairs_disagree"]
        strategies = block["strategies_compared"]
        lines.extend(
            [
                cat["repair.widened.intro"].format(
                    strategy_count=len(strategies),
                    strategies=", ".join(f"`{s}`" for s in strategies),
                    numerator=count(union["numerator"]),
                    denominator=count(union["denominator"]),
                    share=share(union, cat),
                    interval=interval(union, cat),
                ),
                "",
                cat["repair.pairwise_table_head"],
            ]
        )
        lines.extend(
            cat["repair.pairwise_row"].format(
                left=row["between"][0],
                right=row["between"][1],
                records=count(row["records"]),
            )
            for row in block["pairwise_disagreements"]
        )
        lines.extend(
            [
                "",
                cat["repair.adr_0007_pair"].format(
                    numerator=count(changed["numerator"]),
                    denominator=count(changed["denominator"]),
                    share=share(changed, cat),
                    interval=interval(changed, cat),
                    alternative=block["alternative"],
                    chosen=block["chosen"],
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                cat["repair.two.intro"].format(
                    numerator=count(changed["numerator"]),
                    denominator=count(changed["denominator"]),
                    share=share(changed, cat),
                    interval=interval(changed, cat),
                    alternative=block["alternative"],
                    chosen=block["chosen"],
                ),
                "",
            ]
        )
    if block["transitions"]:
        lines.append(cat["repair.transitions_table_head"])
        lines.extend(
            f"| {row['under_the_chosen_repair'].replace('_', ' ')} | "
            f"{row['under_the_alternative'].replace('_', ' ')} | "
            f"{count(row['records'])} |"
            for row in block["transitions"]
        )
    else:
        lines.append(
            cat["repair.no_transitions.widened"]
            if widened
            else cat["repair.no_transitions.two"]
        )
    placed_diff = block["placed_difference"]
    lines.extend(
        [
            "",
            cat["repair.placed_intro"],
            "",
            cat["repair.placed_table_head"],
            rate_line(block["placed_under_the_chosen_repair"], cat),
            rate_line(block["placed_under_the_alternative"], cat),
            "",
            cat["repair.placed_difference"].format(
                difference=difference(placed_diff, cat),
                interval=interval(placed_diff, cat),
            ),
            "",
        ]
    )
    lines.extend(
        [
            cat["repair.verdict.widened"] if widened else cat["repair.verdict.two"],
            "",
        ]
    )
    return lines


def _untouched(tree: dict[str, Any], cat: Catalog) -> list[str]:
    block = tree["sensitivity"]["untouched_outlines"]
    inside = block["records_inside_at_least_one_of_them"]
    changed = block["records_with_a_different_outcome_without_them"]
    lines = [
        cat["untouched.heading"],
        "",
        cat["untouched.intro"],
        "",
        cat["untouched.counts"].format(
            empty_outlines=block["outlines_no_record_falls_inside_count"],
            outlines_indexed=block["outlines_indexed"],
            inside_numerator=count(inside["numerator"]),
            inside_denominator=count(inside["denominator"]),
            inside_interval=interval(inside, cat),
            changed=count(changed["numerator"]),
            changed_interval=interval(changed, cat),
        ),
        "",
    ]
    if block["outlines_no_record_falls_inside"]:
        lines.extend(f"- {name}" for name in block["outlines_no_record_falls_inside"])
        lines.append("")
    lines.extend([block["note"], ""])
    return lines


def _limits(cat: Catalog) -> list[str]:
    return [
        cat["limits.heading"],
        "",
        cat["limits.body"],
        "",
    ]


def _county_agreement(tree: dict[str, Any], cat: Catalog) -> list[str]:
    block = tree["coordinate_county_agreement"]
    compared = block["records_compared"]
    lines = [
        cat["county_agreement.heading"],
        "",
        cat["county_agreement.intro"].format(
            compared=count(compared["numerator"]),
            comparable=count(compared["denominator"]),
        ),
        "",
        cat["county_agreement.outcome_table_head"],
        rate_line(block["agreed"], cat),
        rate_line(block["disagreed"], cat),
        rate_line(block["matched_no_county"], cat),
        rate_line(block["unmatchable_label"], cat),
        "",
        cat["county_agreement.note"],
        "",
        cat["county_agreement.table_head"],
    ]
    for row in block["by_county"]:
        node = row["disagreed"]
        lines.append(
            f"| {row['county']} | {count(row['resolved'])} | "
            f"{count(row['agreed'])} | {count(row['matched_no_county'])} | "
            f"{share(node, cat)} | "
            f"{interval(node, cat)} |"
        )
    lines.append("")
    return lines


def _by_structure_class(tree: dict[str, Any], cat: Catalog) -> list[str]:
    rows = tree["representativeness_by_category"]
    lines = [
        cat["structure_class.heading"],
        "",
        cat["structure_class.intro"],
        "",
        cat["structure_class.table_head"],
    ]
    for row in rows:
        if "difference" in row:
            diff = row["difference"]
            cell = (
                f"{difference(diff, cat)} ({interval(diff, cat)})"
                if diff["state"] == "measured"
                else cat["words.not_measured"]
            )
        else:
            cell = cat["words.not_measured"]
        lines.append(
            f"| {row['structure_category']} | "
            f"{share(row['placed'], cat)} | "
            f"{share(row['contested'], cat)} | "
            f"{cell} |"
        )
    lines.append("")
    return lines


def render(tree: dict[str, Any], cat: Catalog = ENGLISH) -> str:
    """The whole document, deterministic for a given artifact and a given catalog.

    The catalog is a parameter rather than a flag: a second edition is a second
    catalog passed here, not a second code path, and there is no command-line surface
    offering a choice of one.
    """
    lines: list[str] = []
    for section in (
        _header(tree, cat),
        _coverage(tree, cat),
        _representativeness(tree, cat),
        _by_structure_class(tree, cat),
        _by_fire(tree, cat),
        _county_agreement(tree, cat),
        _territories(tree, cat),
        _contested(tree, cat),
        _ledger(tree, cat),
        _sensitivity_repair(tree, cat),
        _sensitivity_types(tree, cat),
        _untouched(tree, cat),
        _limits(cat),
    ):
        lines.extend(section)
    return "\n".join(lines).rstrip() + "\n"
