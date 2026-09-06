"""The publication rules, each exercised against something that should break it.

A gate nobody has watched fail is not a gate. Every rule in :mod:`wildfire_service_territory_overlap.artifacts`
gets an input here that must be refused, as well as one that must pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from wildfire_service_territory_overlap.artifacts import (
    BY_NAME,
    BY_SIZE,
    DECLARED,
    ORDERINGS,
    PublicationRefused,
    _walk,
    assert_aggregate_only,
    assert_differences_carry_intervals,
    assert_no_locating_fields,
    assert_no_ranking,
    assert_rates_are_denominated,
    assert_territories_sorted_by_name,
    check_all,
    check_document,
    generic_path,
    serialise,
    table_cells,
    write_json,
    write_report,
)
from wildfire_service_territory_overlap.intervals import Rate


def measured() -> dict[str, Any]:
    return Rate.of("a share", 3, 12).as_dict()


def unmeasured() -> dict[str, Any]:
    return Rate.not_measured("a share", reason="nothing to divide").as_dict()


def test_a_well_formed_rate_passes() -> None:
    assert_rates_are_denominated({"x": measured()})
    assert_rates_are_denominated({"x": unmeasured()})


@pytest.mark.parametrize(
    "dropped",
    ["numerator", "denominator", "interval_low", "interval_high", "interval_method"],
)
def test_a_rate_missing_any_required_field_is_refused(dropped: str) -> None:
    node = measured()
    del node[dropped]
    with pytest.raises(PublicationRefused, match="missing"):
        assert_rates_are_denominated({"x": node})


def test_a_rate_with_a_value_and_no_denominator_is_refused() -> None:
    node = measured()
    node["denominator"] = 0
    with pytest.raises(PublicationRefused, match="not zero percent"):
        assert_rates_are_denominated({"x": node})


def test_a_measured_rate_with_no_interval_is_refused() -> None:
    node = measured()
    node["interval_low"] = None
    with pytest.raises(PublicationRefused, match="missing interval_low"):
        assert_rates_are_denominated({"x": node})


def test_a_measured_rate_with_no_interval_method_is_refused() -> None:
    node = measured()
    node["interval_method"] = "none"
    with pytest.raises(PublicationRefused, match="names no interval method"):
        assert_rates_are_denominated({"x": node})


def test_a_not_measured_rate_carrying_a_zero_is_refused() -> None:
    node = unmeasured()
    node["rate"] = 0.0
    with pytest.raises(PublicationRefused, match="not a zero"):
        assert_rates_are_denominated({"x": node})


def test_a_rate_nested_deep_in_a_list_is_still_checked() -> None:
    node = measured()
    del node["denominator"]
    with pytest.raises(PublicationRefused):
        assert_rates_are_denominated({"a": [{"b": [{"c": node}]}]})


def test_a_difference_without_an_interval_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="missing interval_low"):
        assert_differences_carry_intervals(
            {"d": {"difference": 0.2, "state": "measured"}}
        )


def test_a_measured_difference_with_a_null_interval_is_refused() -> None:
    payload = {
        "difference": 0.2,
        "interval_low": None,
        "interval_high": 0.3,
        "interval_method": "newcombe-score-95",
        "state": "measured",
    }
    with pytest.raises(PublicationRefused, match="no interval"):
        assert_differences_carry_intervals({"d": payload})


def test_a_prose_field_called_difference_is_not_mistaken_for_one() -> None:
    assert_differences_carry_intervals({"d": {"difference": "a sentence about it"}})


@pytest.mark.parametrize(
    "key", ["latitude", "LONGITUDE", "Address", "apn", "siteaddress", "x", "objectid"]
)
def test_anything_that_could_place_a_structure_is_refused(key: str) -> None:
    with pytest.raises(PublicationRefused, match="never a position"):
        assert_no_locating_fields({"rows": [{key: 1}]})


def test_a_key_that_merely_contains_a_forbidden_word_is_allowed() -> None:
    assert_no_locating_fields({"geometry_state": "repaired", "geometry_note": "n"})


def test_a_collection_longer_than_the_ceiling_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="record listing under another name"):
        assert_aggregate_only({"rows": list(range(11))}, max_rows=10)


def test_a_collection_at_the_ceiling_passes() -> None:
    assert_aggregate_only({"rows": list(range(10))}, max_rows=10)


@pytest.mark.parametrize("key", ["rank", "SCORE", "grade", "worst", "rating"])
def test_a_key_that_rates_a_utility_is_refused(key: str) -> None:
    with pytest.raises(PublicationRefused, match="does not rate, rank, or score"):
        assert_no_ranking({"rows": [{key: 1}]})


def test_territory_rows_out_of_name_order_are_refused() -> None:
    with pytest.raises(PublicationRefused, match="not in name order"):
        assert_territories_sorted_by_name(
            [{"territory": "Zulu"}, {"territory": "Alpha"}]
        )


def test_territory_rows_in_name_order_pass() -> None:
    assert_territories_sorted_by_name([{"territory": "Alpha"}, {"territory": "Zulu"}])


def test_check_all_runs_every_rule() -> None:
    tree = {"territories": [{"territory": "Alpha", "share": measured()}]}
    check_all(tree, max_rows=5)


def test_check_all_ignores_a_territories_key_that_is_not_a_list() -> None:
    check_all({"territories": "none indexed"}, max_rows=5)


def test_serialise_is_stable_for_the_same_tree() -> None:
    tree = {"b": 1, "a": {"d": 2, "c": 3}}
    assert serialise(tree) == serialise({"a": {"c": 3, "d": 2}, "b": 1})
    assert serialise(tree).endswith("\n")


def test_a_refused_artifact_is_not_written_at_all(tmp_path: Path) -> None:
    target = tmp_path / "out" / "measurements.json"
    bad = measured()
    del bad["denominator"]
    with pytest.raises(PublicationRefused):
        write_json({"share": bad}, target, max_rows=5)
    assert not target.exists(), "a refused artifact must leave nothing behind"


def test_a_clean_artifact_is_written(tmp_path: Path) -> None:
    target = tmp_path / "out" / "measurements.json"
    written = write_json({"share": measured()}, target, max_rows=5)
    assert written.read_text(encoding="utf-8").startswith("{")


def _coverage_tree(rows: list[dict[str, Any]], total: int) -> dict[str, Any]:
    return {
        "placement_coverage": {"counts": {"contested_between_two_or_more": total}},
        "contested_groups": rows,
    }


def test_a_contested_groups_table_that_accounts_for_every_record_passes() -> None:
    check_all(_coverage_tree([{"records": 30}, {"records": 20}], 50), max_rows=32)


def test_a_truncated_contested_groups_table_is_refused() -> None:
    """The cut issue #22 reports, caught before anything is written.

    `assert_aggregate_only` cannot see this: its ceiling is never below 32 and the cap
    is 25, so the only length rule in the module is numerically incapable of firing on
    this collection.
    """
    with pytest.raises(PublicationRefused, match="15 short"):
        check_all(_coverage_tree([{"records": 30}, {"records": 20}], 65), max_rows=32)


def test_a_contested_groups_table_longer_than_its_total_is_also_refused() -> None:
    """Over as well as under. A double count is a wrong number, not a safe one."""
    with_extra = [{"records": 30}, {"records": 20}, {"records": 5}]
    with pytest.raises(PublicationRefused, match="55 of 50"):
        check_all(_coverage_tree(with_extra, 50), max_rows=32)


def test_the_contested_check_stays_quiet_when_no_table_is_published() -> None:
    """No table, nothing to be short. This is the one absence that is not a refusal.

    It is quiet because there is no contested-groups table in the tree, not because the
    rule lost the key it checks against.
    """
    check_all({"placement_coverage": {"counts": {}}}, max_rows=32)
    check_all({"placement_coverage": "not a block"}, max_rows=32)
    check_all({}, max_rows=32)


def test_a_contested_table_published_without_its_total_is_refused() -> None:
    """The published table stays; the number it must sum to goes missing.

    This is the shape the rule was blind to. `assert_aggregate_only` cannot see a cut
    table (its ceiling is never below 32 and the cap is 25), so this rule is the only
    one that can, and losing the total made it pass. Every way the total can be absent
    refuses, and each names the key.
    """
    table = [{"records": 30}, {"records": 20}]
    with pytest.raises(PublicationRefused, match=r"no .*placement_coverage block"):
        check_all({"contested_groups": table}, max_rows=32)
    with pytest.raises(PublicationRefused, match="carries no 'contested_between"):
        check_all(
            {"contested_groups": table, "placement_coverage": {"counts": {}}},
            max_rows=32,
        )
    with pytest.raises(PublicationRefused, match=r"no .*placement_coverage block"):
        check_all(
            {"contested_groups": table, "placement_coverage": "not a block"},
            max_rows=32,
        )
    with pytest.raises(PublicationRefused, match="not a record count"):
        check_all(
            {
                "contested_groups": table,
                "placement_coverage": {
                    "counts": {"contested_between_two_or_more": "50"}
                },
            },
            max_rows=32,
        )


def test_a_contested_row_that_carries_no_count_is_refused_by_name() -> None:
    """And refused for the reason it is actually wrong.

    Such a row used to be dropped from the sum, so the artifact was refused with a
    message saying a combination had been cut for sitting past the cap. It had not.
    """
    with pytest.raises(PublicationRefused, match=r"contested_groups\[1\]"):
        check_all(_coverage_tree([{"records": 30}, {"other": 20}], 50), max_rows=32)
    with pytest.raises(PublicationRefused, match=r"contested_groups\[1\]"):
        check_all(_coverage_tree([{"records": 30}, {"records": "20"}], 50), max_rows=32)


def test_a_collection_nobody_declared_an_order_for_is_refused() -> None:
    """Fail closed on arrival. A new collection cannot reach a reader undeclared."""
    with pytest.raises(PublicationRefused, match="nothing has declared"):
        check_all({"newly_added_rows": [{"a": 1}, {"a": 2}]}, max_rows=32)


def test_a_name_ordered_collection_out_of_name_order_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="declared in name order"):
        check_all(
            {"territories": [{"territory": "Zulu"}, {"territory": "Alpha"}]},
            max_rows=32,
        )


def test_contested_groups_out_of_size_order_are_refused() -> None:
    rows = [
        {"records": 10, "territories": ["A", "B"]},
        {"records": 90, "territories": ["C", "D"]},
    ]
    with pytest.raises(PublicationRefused, match="declared in size order"):
        check_all(_coverage_tree(rows, 100), max_rows=32)


def test_contested_groups_in_size_order_pass() -> None:
    rows = [
        {"records": 90, "territories": ["C", "D"]},
        {"records": 10, "territories": ["A", "B"]},
    ]
    check_all(_coverage_tree(rows, 100), max_rows=32)


def test_a_row_missing_the_field_its_order_runs_on_is_refused_not_crashed() -> None:
    """A checker that raises KeyError reads as a bug in the checker, not in the data."""
    with pytest.raises(PublicationRefused, match="does not carry it"):
        check_all(
            {"territories": [{"territory": "Alpha"}, {"name": "Beta"}]}, max_rows=32
        )


def test_a_single_row_collection_has_no_order_to_get_wrong() -> None:
    check_all({"territories": [{"territory": "Alpha"}]}, max_rows=32)


def test_every_declared_exception_to_name_order_says_why() -> None:
    """The half that keeps the ledger from becoming a way to opt out of the rule.

    A collection can be published in an order other than by name, and three are. Each
    has to carry the reason next to the declaration, in words, long enough to argue
    with.
    """
    exceptions = {
        path: reason
        for path, (kind, reason) in ORDERINGS.items()
        if kind in (DECLARED, BY_SIZE)
    }
    assert exceptions, "the ledger records no exception, so this test checks nothing"
    for path, reason in exceptions.items():
        assert len(reason) > 60, f"{path} is excused in one line. Say why."
    by_name = [path for path, (kind, _) in ORDERINGS.items() if kind == BY_NAME]
    assert len(by_name) > len(exceptions), "name order must remain the rule"


def test_the_ordering_ledger_describes_collections_that_are_actually_published(
    published_artifact: dict[str, Any],
) -> None:
    """No entry outlives the collection it describes, and none is missing.

    The same shape as the CodeQL acceptance gate: a ledger that can only grow becomes a
    list of things that used to be true. Every path declared here must appear in the
    published artifact, and every collection in the published artifact must be declared.
    """
    published: set[str] = set()
    for path, node in _walk(published_artifact):
        if isinstance(node, list):
            published.add(generic_path(path))
    assert published, "the published artifact carries no collection at all"
    assert published - set(ORDERINGS) == set(), "an undeclared published collection"
    assert set(ORDERINGS) - published == set(), (
        "ORDERINGS declares an order for a collection the artifact no longer carries"
    )


# --- The rules over the rendered document -------------------------------------------
#
# Each one is fed a document that breaks it. This repository has already written down
# an audit of four gates that were numerically incapable of firing and a test that
# asserted a defect, so a rule that has never been watched refuse is not treated here
# as a rule at all.

CLEAN_DOCUMENT = """# A title

One paragraph, and then a table introduced by this sentence.

| Outcome | Records |
|---|---:|
| placed in exactly one published territory | 82,353 |
| inside no published territory | 0 |

## A section

Prose, with a link to [the provenance record](PROVENANCE.md) in it.
"""


def test_a_clean_document_passes_every_document_rule() -> None:
    check_document(CLEAN_DOCUMENT)


def test_a_row_counts_the_same_cells_with_or_without_its_outer_pipes() -> None:
    """Markdown lets the pipes at the ends of a row be left off.

    The rectangularity rule is a comparison of cell counts, so the count has to mean
    the same thing on a row written either way, or the rule would refuse a table for
    the punctuation at its margins rather than for a cell in the wrong column.
    """
    assert table_cells("| Alpha | 12 |") == ["Alpha", "12"]
    assert table_cells("Alpha | 12") == ["Alpha", "12"]
    assert table_cells("| Alpha | 12") == ["Alpha", "12"]


def test_a_table_with_no_delimiter_row_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="no header row"):
        check_document("# T\n\n| Outcome | Records |\n| placed | 12 |\n")


def test_a_table_that_opens_on_its_delimiter_row_is_refused() -> None:
    """Its first row of data would be read out as the name of every column."""
    with pytest.raises(PublicationRefused, match="no header row"):
        check_document("# T\n\n|---|---:|\n| placed | 12 |\n")


def test_a_lone_table_row_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="no header row"):
        check_document("# T\n\n| placed | 12 |\n")


def test_a_table_following_a_table_with_nothing_between_them_is_refused() -> None:
    """The defect this rule was written for, reduced to its smallest form.

    `published/REPORT.md` carried exactly this shape from the day the third repair
    joined the comparison: the placed-share table sat one blank line under the
    transitions table with no sentence between them, so a reader going through the
    document in order met a second header row with nothing saying what changed.
    """
    with pytest.raises(PublicationRefused, match="follows a table"):
        check_document(
            "# T\n\nWhat moved.\n\n"
            "| Outcome | Records |\n|---|---:|\n| placed | 12 |\n"
            "\n"
            "| Repair | Records |\n|---|---:|\n| make_valid | 12 |\n"
        )


def test_a_table_opening_the_document_is_refused() -> None:
    """A header row before anything has said what is being counted."""
    with pytest.raises(PublicationRefused, match="opens the document"):
        check_document("| Outcome | Records |\n|---|---:|\n| placed | 12 |\n")


def test_a_table_introduced_by_a_heading_alone_is_enough() -> None:
    """The rule asks for something said, not for a sentence.

    A heading names what follows it, which is what a reader arriving at the table
    needs. Requiring prose as well would refuse most of the tables in this repository
    to no benefit, and a rule that forces filler text is a rule people route around.
    """
    check_document(
        "# T\n\n## Coverage\n\n| Outcome | Records |\n|---|---:|\n| placed | 12 |\n"
    )


def test_two_tables_separated_by_a_sentence_are_allowed() -> None:
    check_document(
        "# T\n\nWhat moved.\n\n"
        "| Outcome | Records |\n|---|---:|\n| placed | 12 |\n"
        "\nWhat each repair places in total.\n\n"
        "| Repair | Records |\n|---|---:|\n| make_valid | 12 |\n"
    )


def test_a_pipe_inside_a_value_is_refused_rather_than_shifting_the_row() -> None:
    """The failure this rule exists for.

    Territory names come from a published layer this project does not control. One
    arriving with a `|` in it renders as an extra column, and every cell after it is
    announced under the name of the column to its left. The row still looks like a row.
    """
    document = (
        "# T\n\n| Territory | Records |\n|---|---:|\n| Alpha | Beta Electric | 12 |\n"
    )
    with pytest.raises(PublicationRefused, match="carries 3 cells under a header of 2"):
        check_document(document)


def test_a_row_short_of_its_header_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="carries 1 cells under a header of 2"):
        check_document("# T\n\n| Territory | Records |\n|---|---:|\n| Alpha |\n")


def test_a_pipe_escaped_the_way_markdown_requires_stays_one_cell() -> None:
    """The rule refuses a broken row, not a value that happens to contain a pipe."""
    check_document(
        "# T\n\n| Territory | Records |\n|---|---:|\n| Alpha \\| Beta | 12 |\n"
    )


def test_an_empty_cell_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="column 2 of this row is empty"):
        check_document("# T\n\n| Territory | Records |\n|---|---:|\n| Alpha |  |\n")


def test_an_empty_leading_cell_is_refused() -> None:
    """The corner cell a documentation table leaves blank, which reads as nothing."""
    with pytest.raises(PublicationRefused, match="column 1 of this row is empty"):
        check_document("# T\n\n|  | Records |\n|---|---:|\n| Alpha | 12 |\n")


def test_a_skipped_heading_level_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="level 3 heading under a level 1"):
        check_document("# A title\n\n### A subsection with no section\n")


def test_a_document_that_opens_below_level_one_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="opens at heading level 2"):
        check_document("## A section\n\nProse.\n")


def test_a_heading_returning_to_a_shallower_level_is_not_a_skip() -> None:
    check_document("# T\n\n## One\n\n### Under one\n\n## Two\n\nProse.\n")


def test_a_link_labelled_with_its_own_url_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="a link labelled"):
        check_document("# T\n\nSee [https://example.org/a](https://example.org/a).\n")


def test_a_link_labelled_here_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="a link labelled 'here'"):
        check_document("# T\n\nThe method is described [here](PROVENANCE.md).\n")


def test_a_link_with_no_text_at_all_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="a link labelled ''"):
        check_document("# T\n\nThe method is described [](PROVENANCE.md).\n")


def test_a_bare_url_published_as_a_link_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="character by character"):
        check_document("# T\n\nThe source is <https://example.org/data>.\n")


def test_a_link_labelled_with_a_phrase_passes() -> None:
    check_document(
        "# T\n\nSee [the publisher's conditions of use](https://example.org).\n"
    )


def test_an_ansi_escape_sequence_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="ANSI escape sequence"):
        check_document("# T\n\n\x1b[31mnot measured\x1b[0m\n")


def test_a_markup_tag_carrying_a_colour_is_refused() -> None:
    with pytest.raises(PublicationRefused, match="reached a published"):
        check_document('# T\n\n<span style="color: red">37.9%</span>\n')


def test_a_fenced_block_is_not_read_as_a_table_or_as_a_heading() -> None:
    """A shell transcript inside a fence is an example, not the document's own output."""
    check_document(
        "# T\n\nA sample of what the tool prints:\n\n"
        "```\n| not | a | table |\n### not a heading\n```\n"
    )


def test_a_refused_document_is_not_written_at_all(tmp_path: Path) -> None:
    target = tmp_path / "out" / "REPORT.md"
    with pytest.raises(PublicationRefused):
        write_report("# T\n\n| Alpha | 12 |\n", target)
    assert not target.exists(), "a refused document must leave nothing behind"


def test_a_clean_document_is_written(tmp_path: Path) -> None:
    target = tmp_path / "out" / "REPORT.md"
    written = write_report(CLEAN_DOCUMENT, target)
    assert written.read_text(encoding="utf-8") == CLEAN_DOCUMENT
