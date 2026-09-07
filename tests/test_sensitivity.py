"""The judgment calls, re-run against their alternatives.

These tests are built on hand-made geography rather than on the shared fixtures, because
the point of each one is a difference between two runs and the difference has to be
arranged deliberately. Nothing here is sampled from the real retrievals.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from wildfire_service_territory_overlap.geometry import (
    BUFFER_ZERO,
    MAKE_VALID,
    MAKE_VALID_STRUCTURE,
    load_territories,
)
from wildfire_service_territory_overlap.placement import (
    Placement,
    Record,
    classify,
    containment_signatures,
)
from wildfire_service_territory_overlap.sensitivity import (
    TYPE_VARIANTS,
    InclusionRuleRefused,
    _transitions,
    _types_present,
    check_rules_against_retrieval,
    read_rule_file,
    read_rule_files,
    repair_comparison,
    type_inclusion,
    untouched_outlines,
)


def square(w: float, s: float, e: float, n: float) -> list[list[float]]:
    return [[w, s], [e, s], [e, n], [w, n], [w, s]]


def bowtie(w: float, s: float, e: float, n: float) -> list[list[float]]:
    """Two lobes crossing at the middle. `make_valid` keeps both; `buffer(0)` keeps one."""
    return [[w, s], [e, n], [w, n], [e, s], [w, s]]


def feature(oid: int, name: str, kind: str, ring: list[list[float]]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"OBJECTID": oid, "Utility": name, "Type": kind},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def collection(*features: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {"a": {"type": "FeatureCollection", "features": list(features)}}


def record(oid: int, lon: float, lat: float, incident: str = "SAMPLE") -> Record:
    return Record(
        object_id=oid,
        damage="Destroyed (>50%)",
        incident=incident,
        county="Sample County East",
        year=2025,
        lon=lon,
        lat=lat,
    )


@pytest.fixture
def two_types() -> dict[str, dict[str, Any]]:
    """An investor-owned square and a cooperative square that do not touch."""
    return collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Rural Co-op", "CO-OP", square(-119.0, 38.0, -118.5, 38.5)),
    )


def test_the_rule_as_built_is_the_first_row_and_is_the_reference(
    two_types: dict[str, dict[str, Any]],
) -> None:
    records = (record(1, -120.75, 38.25),)
    block = type_inclusion(two_types, records, 0)
    first = block["variants"][0]
    assert first["variant"] == "the rule as built"
    assert first["types_read_as_territories"] == ["CO-OP", "IOU", "POU", "Tribal"]
    assert "contested_difference_from_the_rule_as_built" not in first


def test_every_other_variant_carries_a_difference_with_an_interval(
    two_types: dict[str, dict[str, Any]],
) -> None:
    records = (record(1, -120.75, 38.25),)
    block = type_inclusion(two_types, records, 0)
    for row in block["variants"][1:]:
        difference = row["contested_difference_from_the_rule_as_built"]
        assert difference["interval_method"] == "newcombe-score-95"
        assert difference["interval_low"] is not None
        assert difference["interval_high"] is not None


def test_every_variant_measures_the_same_record_set(
    two_types: dict[str, dict[str, Any]],
) -> None:
    records = tuple(record(i, -120.75, 38.25) for i in range(1, 6))
    block = type_inclusion(two_types, records, 0)
    for row in block["variants"]:
        assert sum(row["counts"].values()) == len(records)
        for key in ("placed", "contested", "uncovered"):
            assert row[key]["denominator"] == len(records)


def test_dropping_an_included_type_makes_records_uncovered_rather_than_placed(
    two_types: dict[str, dict[str, Any]],
) -> None:
    """The cost of a narrower rule is a false statement about coverage, not a tidier one."""
    records = (record(1, -120.75, 38.25), record(2, -118.75, 38.25))
    block = type_inclusion(two_types, records, 0)
    rows = {row["variant"]: row for row in block["variants"]}
    assert rows["the rule as built"]["counts"] == {
        "placed_in_exactly_one_territory": 2,
        "contested_between_two_or_more": 0,
        "covered_by_no_published_territory": 0,
        "coordinate_not_usable": 0,
    }
    without = rows["without CO-OP"]["counts"]
    assert without["placed_in_exactly_one_territory"] == 1
    assert without["covered_by_no_published_territory"] == 1


def test_reading_an_overlay_type_as_a_territory_raises_the_contested_share() -> None:
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Choice Energy", "CCA", square(-121.0, 38.0, -120.5, 38.5)),
    )
    records = (record(1, -120.75, 38.25),)
    rows = {
        r["variant"]: r for r in type_inclusion(collections, records, 0)["variants"]
    }
    assert rows["the rule as built"]["contested"]["numerator"] == 0
    assert rows["with CCA read as a territory"]["contested"]["numerator"] == 1


def test_a_type_the_publisher_adds_later_is_reported_rather_than_absorbed() -> None:
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Direct Access Co", "ESP", square(-119.0, 38.0, -118.5, 38.5)),
    )
    block = type_inclusion(collections, (record(1, -120.75, 38.25),), 0)
    assert block["unexpected_published_types"] == ["ESP"]
    assert "ESP" in block["published_types_present_in_this_retrieval"]


def test_the_undocumented_type_field_is_stated_in_the_output() -> None:
    block = type_inclusion(
        collection(feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5))),
        (record(1, -120.75, 38.25),),
        0,
    )
    assert (
        "documents none of its values"
        in (block["the_published_type_field_is_undocumented"])
    )


def test_the_variant_list_covers_both_inclusions_and_both_exclusions() -> None:
    labels = [label for label, _ in TYPE_VARIANTS]
    assert labels[0] == "the rule as built"
    for expected in ("CO-OP", "Tribal", "CCA", "ADMIN"):
        assert any(expected in label for label in labels[1:]), expected


def test_the_two_repairs_are_compared_over_the_whole_record_set() -> None:
    collections = collection(
        feature(1, "Bowtie Utility", "IOU", bowtie(-121.0, 38.0, -120.0, 39.0))
    )
    records = tuple(record(i, -120.9, 38.1 + i * 0.1) for i in range(1, 8))
    chosen, _ = load_territories(collections)
    block = repair_comparison(collections, records, chosen)
    assert block["chosen"] == MAKE_VALID
    assert block["alternative"] == BUFFER_ZERO
    changed = block["records_with_a_different_outcome"]
    assert changed["denominator"] == len(records)
    assert sum(row["records"] for row in block["transitions"]) == changed["numerator"]


def test_a_repair_that_drops_a_lobe_is_counted_as_a_disagreement() -> None:
    """`buffer(0)` keeps one lobe of a bowtie and `make_valid` keeps both."""
    collections = collection(
        feature(1, "Bowtie Utility", "IOU", bowtie(-121.0, 38.0, -120.0, 39.0))
    )
    chosen, _ = load_territories(collections)
    alternative, _ = load_territories(collections, strategy=BUFFER_ZERO)
    grid = tuple(
        record(i, -121.0 + 0.05 * (i % 20), 38.0 + 0.05 * (i // 20))
        for i in range(1, 400)
    )
    left = containment_signatures(grid, chosen)
    right = containment_signatures(grid, alternative)
    assert left != right, "the two repairs must disagree somewhere on a bowtie"
    block = repair_comparison(collections, grid, chosen)
    assert block["records_with_a_different_outcome"]["numerator"] > 0
    assert block["placed_difference"]["state"] == "measured"


def test_two_repairs_that_agree_report_no_disagreement() -> None:
    collections = collection(
        feature(1, "Square Utility", "IOU", square(-121.0, 38.0, -120.0, 39.0))
    )
    records = (record(1, -120.5, 38.5), record(2, -119.0, 38.5))
    chosen, _ = load_territories(collections)
    block = repair_comparison(collections, records, chosen)
    assert block["records_with_a_different_outcome"]["numerator"] == 0
    assert block["transitions"] == []
    assert block["placed_difference"]["difference"] == 0.0


def test_the_disagreement_count_is_a_census_not_a_difference_of_totals() -> None:
    """Two totals can match while the records behind them do not."""
    collections = collection(
        feature(1, "Bowtie Utility", "IOU", bowtie(-121.0, 38.0, -120.0, 39.0))
    )
    chosen, _ = load_territories(collections)
    grid = tuple(
        record(i, -121.0 + 0.05 * (i % 20), 38.0 + 0.05 * (i // 20))
        for i in range(1, 400)
    )
    block = repair_comparison(collections, grid, chosen)
    changed = block["records_with_a_different_outcome"]["numerator"]
    placed_gap = abs(
        block["placed_under_the_chosen_repair"]["numerator"]
        - block["placed_under_the_alternative"]["numerator"]
    )
    assert changed >= placed_gap


def test_all_three_repairs_are_compared_and_the_union_bounds_each_pair() -> None:
    """The third repair widens the census; the union count is at least every pair."""
    collections = collection(
        feature(1, "Bowtie Utility", "IOU", bowtie(-121.0, 38.0, -120.0, 39.0))
    )
    chosen, _ = load_territories(collections)
    grid = tuple(
        record(i, -121.0 + 0.05 * (i % 20), 38.0 + 0.05 * (i // 20))
        for i in range(1, 400)
    )
    block = repair_comparison(collections, grid, chosen)
    assert block["strategies_compared"] == [
        MAKE_VALID,
        BUFFER_ZERO,
        MAKE_VALID_STRUCTURE,
    ]
    pairs = {
        tuple(row["between"]): row["records"] for row in block["pairwise_disagreements"]
    }
    assert ("make_valid", "buffer_zero") in pairs
    union = block["records_where_any_two_repairs_disagree"]
    assert union["denominator"] == len(grid)
    assert union["numerator"] >= max(pairs.values())
    # The pairwise counts must agree with the transitions table on the documented pair.
    assert (
        pairs[("make_valid", "buffer_zero")]
        == block["records_with_a_different_outcome"]["numerator"]
    )


def test_a_structure_repair_that_collapses_geometry_is_counted_as_unusable() -> None:
    """A repair that produces no polygonal result removes that run's territory."""
    collections = collection(
        feature(1, "Bowtie Utility", "IOU", bowtie(-121.0, 38.0, -120.0, 39.0))
    )
    chosen, _ = load_territories(collections)
    records = tuple(record(i, -120.9, 38.1 + i * 0.1) for i in range(1, 4))
    block = repair_comparison(collections, records, chosen)
    per_strategy = block["territories_unusable_under_each_strategy"]
    assert set(per_strategy) <= set(block["strategies_compared"])
    for strategy, unusable in per_strategy.items():
        indexed = block["territories_indexed"][strategy]
        assert isinstance(unusable, int) and isinstance(indexed, int)


def test_three_identical_repairs_would_report_zero_everywhere() -> None:
    """On valid published geometry no repair runs at all, so all readings agree."""
    collections = collection(
        feature(1, "Square Utility", "IOU", square(-121.0, 38.0, -120.0, 39.0))
    )
    records = (record(1, -120.5, 38.5), record(2, -119.5, 38.5))
    chosen, _ = load_territories(collections)
    block = repair_comparison(collections, records, chosen)
    assert block["records_where_any_two_repairs_disagree"]["numerator"] == 0
    assert all(row["records"] == 0 for row in block["pairwise_disagreements"])


def test_a_variant_with_no_usable_geography_still_reports_a_denominator() -> None:
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5))
    )
    records = (record(1, -100.0, 38.25),)
    block = type_inclusion(collections, records, 0)
    first = block["variants"][0]
    assert first["counts"]["coordinate_not_usable"] == 1
    assert first["contested"]["denominator"] == 1


def test_the_classification_underneath_the_variants_is_the_published_one(
    two_types: dict[str, dict[str, Any]],
) -> None:
    """A variant row must be the same measurement the rest of the project makes."""
    records = (record(1, -120.75, 38.25), record(2, -118.75, 38.25))
    territories, _ = load_territories(two_types)
    direct: Placement = classify(records, territories, 0)
    row = type_inclusion(two_types, records, 0)["variants"][0]
    assert row["counts"]["placed_in_exactly_one_territory"] == direct.placed
    assert row["counts"]["contested_between_two_or_more"] == direct.contested


def test_every_kind_of_transition_is_named() -> None:
    """The classifier is tested directly: it decides what the head to head reports."""
    chosen = (None, (), ("A",), ("A", "B"), ("A", "B"), ("A",))
    alternative = (("A",), ("A",), (), ("A", "C"), ("A",), ("A",))
    moves, changed, same_outcome = _transitions(chosen, alternative)
    assert changed == 5
    assert same_outcome == 1, "contested under both, but with a different pair"
    assert moves == {
        ("coordinate_not_usable", "placed_in_exactly_one_territory"): 1,
        ("covered_by_no_published_territory", "placed_in_exactly_one_territory"): 1,
        ("placed_in_exactly_one_territory", "covered_by_no_published_territory"): 1,
        ("contested_between_two_or_more", "contested_between_two_or_more"): 1,
        ("contested_between_two_or_more", "placed_in_exactly_one_territory"): 1,
    }


def test_the_type_census_reads_past_a_feature_it_cannot_parse() -> None:
    """`load_territories` refuses such a feature outright, and runs first. The census
    is defensive about it anyway, because it is the check that would otherwise silently
    report a shorter list of types than the retrieval holds."""
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5))
    )
    collections["a"]["features"].extend(
        [{"type": "Feature"}, {"properties": {"Type": "  "}}, {"properties": None}]
    )
    assert _types_present(collections) == ["IOU"]


def test_an_outline_no_record_falls_inside_cannot_move_a_published_figure() -> None:
    """The question a reader asks about one named entity, answered as a count.

    Two squares, one of which no record is anywhere near. Whether that entity belongs in
    a retail service territory set is not decided here and is not decidable from this
    data. What is decidable is whether it could be moving anything, and the whole record
    set is placed again without it to answer that rather than reasoning about it.
    """
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Empty Utility", "POU", square(-119.0, 38.0, -118.5, 38.5)),
    )
    territories, _ = load_territories(collections)
    records = (record(1, -120.75, 38.25), record(2, -120.6, 38.4))
    placement = classify(records, territories, 0)
    block = untouched_outlines(placement, records, territories)

    assert block["outlines_no_record_falls_inside"] == ["Empty Utility"]
    assert block["outlines_no_record_falls_inside_count"] == 1
    assert block["outlines_indexed"] == 2
    assert block["records_inside_at_least_one_of_them"]["numerator"] == 0
    assert block["records_inside_at_least_one_of_them"]["denominator"] == 2
    assert block["records_with_a_different_outcome_without_them"]["numerator"] == 0


def test_an_outline_that_does_hold_records_is_not_reported_as_holding_none() -> None:
    """Guard the guard: the count above must be able to come back empty."""
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5))
    )
    territories, _ = load_territories(collections)
    records = (record(1, -120.75, 38.25),)
    block = untouched_outlines(classify(records, territories, 0), records, territories)
    assert block["outlines_no_record_falls_inside"] == []
    assert block["records_with_a_different_outcome_without_them"]["numerator"] == 0


def test_removing_every_outline_leaves_every_record_inside_none_of_them() -> None:
    """The degenerate case: an empty index cannot be built, and does not need to be."""
    collections = collection(
        feature(1, "Empty Utility", "POU", square(-119.0, 38.0, -118.5, 38.5))
    )
    territories, _ = load_territories(collections)
    records = (record(1, -120.75, 38.25),)
    block = untouched_outlines(classify(records, territories, 0), records, territories)
    assert block["outlines_no_record_falls_inside"] == ["Empty Utility"]
    assert block["records_inside_at_least_one_of_them"]["numerator"] == 0
    assert block["records_with_a_different_outcome_without_them"]["numerator"] == 0


# --- A rule a reviewer supplies ----------------------------------------------------
#
# `docs/outreach/inclusion-rule-review-packet.md` tells a domain reviewer that their
# finding "lands as a new sensitivity row rather than as an edit to the rule". These
# hold that promise to the code: a supplied file is loaded strictly, refused before any
# placement runs when it names something the retrieval does not carry, and otherwise
# measured through exactly the machinery the built variants go through.


def write_rule(path: Path, **fields: Any) -> Path:
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path


def valid_rule_fields(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "variant": "a reading a reviewer supplied",
        "reviewer_role": "Distribution planning engineer",
        "reviewed_on": "2026-09-06",
        "types_read_as_territories": ["IOU"],
    }
    fields.update(overrides)
    return fields


@pytest.fixture
def four_types() -> dict[str, dict[str, Any]]:
    """One square per type the built variants distinguish, none of them touching."""
    return collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Town POU", "POU", square(-120.0, 38.0, -119.5, 38.5)),
        feature(3, "Rural Co-op", "CO-OP", square(-119.0, 38.0, -118.5, 38.5)),
        feature(4, "Tribal Utility", "Tribal", square(-118.0, 38.0, -117.5, 38.5)),
    )


@pytest.fixture
def one_record_per_square() -> tuple[Record, ...]:
    return (
        record(1, -120.75, 38.25),
        record(2, -119.75, 38.25),
        record(3, -118.75, 38.25),
        record(4, -117.75, 38.25),
    )


def test_a_supplied_rule_that_drops_co_op_reproduces_the_built_variant(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
    tmp_path: Path,
) -> None:
    """The control the issue asks for, run rather than asserted.

    The whole point of publishing a reviewer's rule beside the built ones is that both
    went through the same placement. A supplied file naming exactly the types the built
    "without CO-OP" variant names has to come out with the same counts, the same rates,
    the same intervals and the same difference from the rule as built, to the digit. If
    the supplied path had its own filter, its own denominator, or its own baseline, this
    is where that would show.
    """
    rule = read_rule_file(
        write_rule(
            tmp_path / "drop.json",
            **valid_rule_fields(
                variant="without CO-OP, supplied",
                types_read_as_territories=["IOU", "POU", "Tribal"],
            ),
        )
    )
    block = type_inclusion(four_types, one_record_per_square, 0, (rule,))
    rows = {row["variant"]: row for row in block["variants"]}
    built = rows["without CO-OP"]
    supplied = rows["without CO-OP, supplied"]
    for key in (
        "counts",
        "contested",
        "placed",
        "uncovered",
        "territories_indexed",
        "types_read_as_territories",
        "contested_difference_from_the_rule_as_built",
    ):
        assert supplied[key] == built[key], key
    # The built row is exactly one record short of a placement, which is what the
    # dropped cooperative was holding. A supplied rule that measured nothing would
    # match a built row that also measured nothing, so the figure is pinned here.
    assert built["counts"] == {
        "placed_in_exactly_one_territory": 3,
        "contested_between_two_or_more": 0,
        "covered_by_no_published_territory": 1,
        "coordinate_not_usable": 0,
    }


def test_a_supplied_rule_names_its_reviewer_role_its_date_and_its_file(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
    tmp_path: Path,
) -> None:
    rule = read_rule_file(write_rule(tmp_path / "review.json", **valid_rule_fields()))
    block = type_inclusion(four_types, one_record_per_square, 0, (rule,))
    row = block["variants"][-1]
    assert row["variant"] == "a reading a reviewer supplied"
    assert row["supplied_by_a_reviewer"] is True
    assert row["reviewer_role"] == "Distribution planning engineer"
    assert row["reviewed_on"] == "2026-09-06"
    assert row["rule_file"] == "review.json"
    assert row["outline_overrides"] == {}


def test_a_supplied_rule_never_becomes_the_reference_row(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
    tmp_path: Path,
) -> None:
    """Every supplied row carries a difference, so none of them is the baseline."""
    rules = tuple(
        read_rule_file(
            write_rule(
                tmp_path / f"{name}.json",
                **valid_rule_fields(variant=name),
            )
        )
        for name in ("alpha", "beta")
    )
    block = type_inclusion(four_types, one_record_per_square, 0, rules)
    assert block["variants"][0]["variant"] == "the rule as built"
    assert block["rule_as_built"] == ["CO-OP", "IOU", "POU", "Tribal"]
    for row in block["variants"][1:]:
        assert "contested_difference_from_the_rule_as_built" in row
    assert [row["variant"] for row in block["variants"][-2:]] == ["alpha", "beta"]


def test_supplied_rules_land_after_the_built_ones_in_filename_order(
    tmp_path: Path,
) -> None:
    """Typed in one order, published in another, so the artifact does not depend on it."""
    paths = [
        write_rule(tmp_path / "zulu.json", **valid_rule_fields(variant="zulu")),
        write_rule(tmp_path / "alpha.json", **valid_rule_fields(variant="alpha")),
    ]
    assert [rule.file_name for rule in read_rule_files(paths)] == [
        "alpha.json",
        "zulu.json",
    ]
    assert [rule.file_name for rule in read_rule_files(paths[::-1])] == [
        "alpha.json",
        "zulu.json",
    ]


def test_supplying_nothing_leaves_the_block_exactly_as_it_was(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
) -> None:
    """The published artifact must not move because a flag exists that nobody used."""
    assert type_inclusion(four_types, one_record_per_square, 0) == type_inclusion(
        four_types, one_record_per_square, 0, ()
    )
    block = type_inclusion(four_types, one_record_per_square, 0)
    assert len(block["variants"]) == len(TYPE_VARIANTS)
    for row in block["variants"]:
        assert "supplied_by_a_reviewer" not in row
        assert "outline_overrides" not in row


def test_an_override_reads_a_named_outline_out_of_the_type_rule(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
    tmp_path: Path,
) -> None:
    rule = read_rule_file(
        write_rule(
            tmp_path / "out.json",
            **valid_rule_fields(
                types_read_as_territories=["CO-OP", "IOU", "POU", "Tribal"],
                outline_overrides={
                    "Rural Co-op": {
                        "read_as_a_territory": False,
                        "reason": "Reads as a generation cooperative to this reviewer.",
                    }
                },
            ),
        )
    )
    block = type_inclusion(four_types, one_record_per_square, 0, (rule,))
    row = block["variants"][-1]
    assert row["territories_indexed"] == 3
    assert row["counts"]["covered_by_no_published_territory"] == 1
    assert row["outline_overrides"] == {
        "Rural Co-op": {
            "read_as_a_territory": False,
            "reviewer_reason": "Reads as a generation cooperative to this reviewer.",
        }
    }


def test_an_override_reads_a_named_outline_into_the_type_rule(
    tmp_path: Path,
) -> None:
    """The other direction, which the type rule alone cannot express."""
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Aggregator", "CCA", square(-119.0, 38.0, -118.5, 38.5)),
    )
    records = (record(1, -120.75, 38.25), record(2, -118.75, 38.25))
    rule = read_rule_file(
        write_rule(
            tmp_path / "in.json",
            **valid_rule_fields(
                types_read_as_territories=["IOU"],
                outline_overrides={
                    "Aggregator": {
                        "read_as_a_territory": True,
                        "reason": "Operates the wires in this county, says the reviewer.",
                    }
                },
            ),
        )
    )
    block = type_inclusion(collections, records, 0, (rule,))
    row = block["variants"][-1]
    assert row["territories_indexed"] == 2
    assert row["counts"]["placed_in_exactly_one_territory"] == 2
    assert row["counts"]["covered_by_no_published_territory"] == 0


def test_a_rule_naming_a_type_the_retrieval_does_not_carry_is_refused(
    four_types: dict[str, dict[str, Any]], tmp_path: Path
) -> None:
    """A stale review must not run to completion measuring nothing."""
    rule = read_rule_file(
        write_rule(
            tmp_path / "stale.json",
            **valid_rule_fields(types_read_as_territories=["IOU", "ADMIN"]),
        )
    )
    with pytest.raises(InclusionRuleRefused, match="ADMIN"):
        check_rules_against_retrieval((rule,), four_types)


def test_a_rule_overriding_an_outline_the_retrieval_does_not_carry_is_refused(
    four_types: dict[str, dict[str, Any]], tmp_path: Path
) -> None:
    rule = read_rule_file(
        write_rule(
            tmp_path / "renamed.json",
            **valid_rule_fields(
                outline_overrides={
                    "Withdrawn Utility": {
                        "read_as_a_territory": False,
                        "reason": "Named in a retrieval this build is not measuring.",
                    }
                }
            ),
        )
    )
    with pytest.raises(InclusionRuleRefused, match="Withdrawn Utility"):
        check_rules_against_retrieval((rule,), four_types)


def test_an_override_naming_an_outline_the_built_rule_excludes_is_accepted(
    tmp_path: Path,
) -> None:
    """The check reads the layer, not the loaded set, and this is why that matters.

    A reviewer's most likely finding is about an outline the built rule leaves out. A
    check built on the territories the built rule loads could never see one, so it
    would refuse the one override it exists to let through.
    """
    collections = collection(
        feature(1, "Wires IOU", "IOU", square(-121.0, 38.0, -120.5, 38.5)),
        feature(2, "Aggregator", "CCA", square(-119.0, 38.0, -118.5, 38.5)),
    )
    rule = read_rule_file(
        write_rule(
            tmp_path / "cca.json",
            **valid_rule_fields(
                outline_overrides={
                    "Aggregator": {
                        "read_as_a_territory": True,
                        "reason": "The reviewer reads this one as a wires operator.",
                    }
                }
            ),
        )
    )
    check_rules_against_retrieval((rule,), collections)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"reviewer": "somebody"}, "reviewer"),
        ({"variant": ""}, "variant"),
        ({"variant": "the rule as built"}, "the rule as built"),
        ({"reviewer_role": "reviewer@example.invalid"}, "address"),
        ({"reviewed_on": "6 September 2026"}, "YYYY-MM-DD"),
        ({"reviewed_on": "2026-02-30"}, "not a real date"),
        ({"types_read_as_territories": []}, "non-empty list"),
        ({"types_read_as_territories": "IOU"}, "non-empty list"),
        ({"types_read_as_territories": ["IOU", "IOU"]}, "more than once"),
        ({"outline_overrides": ["Wires IOU"]}, "keyed by the outline name"),
        (
            {"outline_overrides": {"Wires IOU": {"read_as_a_territory": True}}},
            "carries no reason",
        ),
        (
            {
                "outline_overrides": {
                    "Wires IOU": {"read_as_a_territory": "yes", "reason": "a reason"}
                }
            },
            "not true or false",
        ),
        (
            {
                "outline_overrides": {
                    "Wires IOU": {
                        "read_as_a_territory": True,
                        "reason": "a reason",
                        "confidence": "high",
                    }
                }
            },
            "confidence",
        ),
        ({"outline_overrides": {"Wires IOU": "drop it"}}, "has to be an object"),
    ],
)
def test_a_rule_file_this_project_cannot_read_is_refused_not_guessed_at(
    overrides: dict[str, Any], expected: str, tmp_path: Path
) -> None:
    """Every refusal names the file and what is wrong. None of them is a warning."""
    fields = valid_rule_fields()
    fields.update(overrides)
    path = write_rule(tmp_path / "bad.json", **fields)
    with pytest.raises(InclusionRuleRefused, match=re.escape(expected)) as refusal:
        read_rule_file(path)
    assert "bad.json" in str(refusal.value)


def test_a_rule_file_missing_a_required_key_is_refused(tmp_path: Path) -> None:
    fields = valid_rule_fields()
    del fields["reviewed_on"]
    path = write_rule(tmp_path / "short.json", **fields)
    with pytest.raises(InclusionRuleRefused, match="carries no reviewed_on"):
        read_rule_file(path)


def test_a_rule_file_that_is_not_json_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "notjson.json"
    path.write_text("variant: a reading\n", encoding="utf-8")
    with pytest.raises(InclusionRuleRefused, match="is not JSON"):
        read_rule_file(path)


def test_a_rule_file_that_is_a_json_list_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text('["IOU"]', encoding="utf-8")
    with pytest.raises(InclusionRuleRefused, match="JSON object"):
        read_rule_file(path)


def test_a_rule_file_that_is_not_there_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(InclusionRuleRefused, match=re.escape("absent.json")):
        read_rule_file(tmp_path / "absent.json")


def test_two_rule_files_that_cannot_be_told_apart_are_refused(tmp_path: Path) -> None:
    """Two rows a reader could not tell apart are not two measurements."""
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    same_name = [
        write_rule(one / "review.json", **valid_rule_fields(variant="first")),
        write_rule(two / "review.json", **valid_rule_fields(variant="second")),
    ]
    with pytest.raises(InclusionRuleRefused, match="basename"):
        read_rule_files(same_name)

    same_variant = [
        write_rule(tmp_path / "a.json", **valid_rule_fields(variant="one reading")),
        write_rule(tmp_path / "b.json", **valid_rule_fields(variant="one reading")),
    ]
    with pytest.raises(InclusionRuleRefused, match="variant name"):
        read_rule_files(same_variant)


def test_a_rule_file_carries_no_path_into_the_artifact(
    four_types: dict[str, dict[str, Any]],
    one_record_per_square: tuple[Record, ...],
    tmp_path: Path,
) -> None:
    """The determinism gate, held from the side that would break it quietly.

    A rule read out of a temporary directory that wrote its full path into the tree
    would make two builds of the same inputs on two machines differ, and the difference
    would be in a field nobody reads.
    """
    rule = read_rule_file(write_rule(tmp_path / "review.json", **valid_rule_fields()))
    block = type_inclusion(four_types, one_record_per_square, 0, (rule,))
    assert str(tmp_path) not in json.dumps(block)
    assert block["variants"][-1]["rule_file"] == "review.json"
