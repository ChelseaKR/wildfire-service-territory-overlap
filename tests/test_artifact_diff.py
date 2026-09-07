"""The refresh diff, held to the behaviour the refresh procedure will rely on."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wildfire_service_territory_overlap.artifact_diff import diff_trees, main, render


def sample_tree() -> dict:
    """A small artifact with every shape the real one has."""
    return {
        "is_fixture": False,
        "placement_coverage": {
            "fire_records": 132520,
            "counts": {"placed": 82353, "contested": 50167},
            "rates": [
                {
                    "label": "placed in exactly one published territory",
                    "numerator": 82353,
                    "denominator": 132520,
                }
            ],
        },
        "territories": [
            {
                "territory": "Anza Electric Cooperative, Inc.",
                "records_placed_here": 305,
                "contested_with": [],
            },
            {
                "territory": "Pacific Gas & Electric Company",
                "records_placed_here": 65865,
                "contested_with": ["Power and Water Resource Pooling Authority"],
            },
        ],
        "by_county": [
            {"county": "Alameda", "records": 120},
            {"county": "Butte", "records": 28747},
        ],
        "by_year": [{"year": 2024, "records": 8117}],
        "contested_groups": [
            {"records": 25345, "territories": ["Metropolitan Water District", "SCE"]},
            {"records": 12241, "territories": ["PG&E", "PWRPA"]},
        ],
    }


def test_identical_trees_report_nothing_and_count_every_leaf() -> None:
    result = diff_trees(sample_tree(), sample_tree())
    assert not result.added
    assert not result.removed
    assert not result.changed
    assert result.total == result.unchanged
    # A hand count of leaves in sample_tree, so "everything agreed" cannot be vacuous.
    assert result.unchanged == 24


def test_a_changed_leaf_is_reported_at_its_path() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    new["placement_coverage"]["fire_records"] = 132522
    result = diff_trees(old, new)
    assert len(result.changed) == 1
    change = result.changed[0]
    assert change.path == "$.placement_coverage.fire_records"
    assert change.before == 132520
    assert change.after == 132522
    assert not result.removed


def test_a_removed_leaf_is_refused_and_allow_removals_passes_it(tmp_path: Path) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    stripped = sample_tree()
    del stripped["placement_coverage"]["counts"]["placed"]
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(stripped), encoding="utf-8")

    refused = main([str(old), str(new)])
    assert refused == 1

    allowed = main(["--allow-removals", str(old), str(new)])
    assert allowed == 0


def test_an_added_leaf_is_reported_not_refused() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    new["attributability_by_fire"] = {"counties_named_in_the_record_set": 52}
    result = diff_trees(old, new)
    assert [leaf.path for leaf in result.added] == [
        "$.attributability_by_fire.counties_named_in_the_record_set"
    ]
    assert not result.removed and not result.changed


def test_a_reordered_keyed_collection_reports_nothing() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    new["territories"].reverse()
    new["by_county"].reverse()
    result = diff_trees(old, new)
    assert not result.changed, result.changed
    assert not result.added and not result.removed


def test_a_changed_row_stays_attached_to_its_own_name() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    new["territories"][0]["records_placed_here"] = 306
    result = diff_trees(old, new)
    assert len(result.changed) == 1
    # The pairing ran by territory name, so the one moved number belongs to Anza even
    # though PG&E's row sits at index 0 in both files.
    assert result.changed[0].path == "$.territories[0].records_placed_here"
    assert result.changed[0].before == 305
    assert result.changed[0].after == 306


def test_a_positional_collection_reports_movement_when_rows_swap() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    # contested_groups carries no identifying field: identity is positional, and a size
    # swap reports every leaf under both rows rather than guessing which row is which.
    # The noise is visible and the reader judges it; the tool does not smooth it over.
    new["contested_groups"].reverse()
    result = diff_trees(old, new)
    paths = {change.path for change in result.changed}
    assert paths == {
        "$.contested_groups[0].records",
        "$.contested_groups[1].records",
        "$.contested_groups[0].territories[0]",
        "$.contested_groups[0].territories[1]",
        "$.contested_groups[1].territories[0]",
        "$.contested_groups[1].territories[1]",
    }


def test_a_scalar_replaced_by_a_container_is_one_change_whole() -> None:
    old = sample_tree()
    new = json.loads(json.dumps(old))
    new["by_year"][0]["year"] = {"value": 2024}
    result = diff_trees(old, new)
    assert len(result.changed) == 1
    assert result.changed[0].path == "$.by_year[0].year"


def test_bool_and_int_are_not_the_same_leaf() -> None:
    result = diff_trees({"flag": False}, {"flag": 0})
    assert len(result.changed) == 1


def test_an_empty_container_counts_as_a_leaf_on_each_side() -> None:
    gone = diff_trees({"rows": []}, {"rows": {"note": "none"}})
    assert len(gone.changed) == 1
    added = diff_trees({"rows": []}, {"rows": [], "extra": {}})
    assert [leaf.path for leaf in added.added] == ["$.extra"]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["/does/not/exist.json", "/also/missing.json"], 2),
    ],
)
def test_bad_usage_exits_two(tmp_path: Path, argv: list[str], expected: int) -> None:
    assert main(argv) == expected


def test_main_prints_a_verdict_line(capsys: pytest.Capsys, tmp_path: Path) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    changed = sample_tree()
    changed["placement_coverage"]["fire_records"] = 132522
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(changed), encoding="utf-8")
    assert main([str(old), str(new)]) == 0
    out = capsys.readouterr().out
    assert "1 changed." in out
    assert "Nothing was removed." in out


def test_the_verdict_never_says_nothing_was_removed_when_something_was(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The one line a reader skims must not contradict the lines above it.

    `--allow-removals` accepts a removal; it does not make the removal stop having
    happened. A verdict of `Nothing was removed.` printed underneath a `REMOVED` line is
    the quiet disappearance this whole tool exists to prevent, wearing the tool's own
    signature.
    """
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    shrunk = sample_tree()
    del shrunk["placement_coverage"]["counts"]["contested"]
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(shrunk), encoding="utf-8")

    assert main([str(old), str(new), "--allow-removals"]) == 0
    out = capsys.readouterr().out
    assert "REMOVED  $.placement_coverage.counts.contested" in out
    assert "Nothing was removed." not in out, (
        "the verdict contradicted the REMOVED line printed directly above it"
    )
    assert "1 published value was removed" in out
    assert "PROVENANCE.md" in out


def test_the_verdict_still_says_nothing_was_removed_when_nothing_was(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The true case keeps its wording, so the fix above is a narrowing not a rewrite."""
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    changed = sample_tree()
    changed["placement_coverage"]["fire_records"] = 132522
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(changed), encoding="utf-8")

    assert main([str(old), str(new), "--allow-removals"]) == 0
    assert "Nothing was removed." in capsys.readouterr().out


# The prose report, locked. Issue #20 required that adding a mode change nothing about
# the mode that already existed, and "unchanged" is only checkable against a literal.
PROSE_IDENTICAL = (
    "24 values compared: 0 added, 0 removed, 0 changed.\nNo published value moved."
)
PROSE_ONE_CHANGED = (
    "changed  $.placement_coverage.fire_records: 132520 -> 132521\n"
    "24 values compared: 0 added, 0 removed, 1 changed.\nNothing was removed."
)
PROSE_REMOVED_REFUSED = (
    "REMOVED  $.placement_coverage.counts.contested: 50167\n"
    "24 values compared: 0 added, 1 removed, 0 changed.\n"
    "REFUSED: published values disappeared. If the removal is deliberate, re-run with "
    "--allow-removals and say so in PROVENANCE.md."
)


def _mutated(mutate: object = None) -> dict:
    return json.loads(json.dumps(sample_tree()))


def test_the_prose_report_is_byte_for_byte_what_it_printed_before_json_mode() -> None:
    """Adding a mode must not move the mode that was already there."""
    old = sample_tree()
    assert (
        render(diff_trees(old, sample_tree()), allow_removals=False) == PROSE_IDENTICAL
    )

    changed = _mutated()
    changed["placement_coverage"]["fire_records"] = 132521
    assert render(diff_trees(old, changed), allow_removals=False) == PROSE_ONE_CHANGED

    shrunk = _mutated()
    del shrunk["placement_coverage"]["counts"]["contested"]
    assert (
        render(diff_trees(old, shrunk), allow_removals=False) == PROSE_REMOVED_REFUSED
    )


def _run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_json_mode_prints_one_object_and_nothing_else(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    changed = _mutated()
    changed["placement_coverage"]["fire_records"] = 132521
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(changed), encoding="utf-8")

    code, payload = _run_json([str(old), str(new), "--json"], capsys)
    assert code == 0
    assert set(payload) == {
        "counts",
        "added",
        "removed",
        "changed",
        "allow_removals",
        "refused",
    }
    assert payload["counts"]["changed"] == 1
    assert payload["changed"] == [
        {"path": "$.placement_coverage.fire_records", "before": 132520, "after": 132521}
    ]
    assert payload["refused"] is False
    assert payload["allow_removals"] is False


def test_json_mode_counts_agree_with_a_direct_diff_trees_call(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    moved = _mutated()
    moved["placement_coverage"]["fire_records"] = 132521
    moved["territories"][0]["records_placed_here"] = 306
    moved["extra_block"] = {"added": 1}
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(moved), encoding="utf-8")

    _, payload = _run_json([str(old), str(new), "--json"], capsys)
    direct = diff_trees(sample_tree(), moved)
    assert payload["counts"] == {
        "total": direct.total,
        "added": len(direct.added),
        "removed": len(direct.removed),
        "changed": len(direct.changed),
        "unchanged": direct.unchanged,
    }


def test_json_mode_carries_a_long_value_whole_where_the_prose_shortens_it(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A truncated value published under the name of the real one is a wrong value."""
    long_note = "n" * 400
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    moved = _mutated()
    moved["long_note"] = long_note
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(moved), encoding="utf-8")

    _, payload = _run_json([str(old), str(new), "--json"], capsys)
    assert payload["added"] == [{"path": "$.long_note", "value": long_note}]


def test_json_mode_does_not_soften_the_removal_refusal(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    shrunk = _mutated()
    del shrunk["placement_coverage"]["counts"]["contested"]
    old.write_text(json.dumps(sample_tree()), encoding="utf-8")
    new.write_text(json.dumps(shrunk), encoding="utf-8")

    code, payload = _run_json([str(old), str(new), "--json"], capsys)
    assert code == 1, "a removal under --json must still refuse"
    assert payload["refused"] is True
    assert payload["removed"] == [
        {"path": "$.placement_coverage.counts.contested", "value": 50167}
    ]

    code, payload = _run_json(
        [str(old), str(new), "--json", "--allow-removals"], capsys
    )
    assert code == 0
    assert payload["refused"] is False
    assert payload["allow_removals"] is True, (
        "refused false with allow_removals hidden reads as nothing having been removed"
    )
    assert payload["counts"]["removed"] == 1


def test_json_mode_leaves_stdout_empty_on_bad_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["/does/not/exist.json", "/also/missing.json", "--json"]) == 2
    assert capsys.readouterr().out == "", "a failed run printed a JSON object anyway"


# A verdict is a claim about a comparison that happened. These are the inputs that
# produced this tool's clean verdict without any comparison happening: the shape
# `intervals.wilson` already refuses one layer down, where zero out of zero is not
# zero percent but not measured.


def _write(path: Path, tree: object) -> Path:
    path.write_text(json.dumps(tree), encoding="utf-8")
    return path


def test_two_empty_artifacts_are_not_a_refresh_in_which_nothing_moved(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`0 values compared` used to print the same verdict, and exit code, as 6,582."""
    old = _write(tmp_path / "old.json", {})
    new = _write(tmp_path / "new.json", {})

    assert main([str(old), str(new)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "", "a comparison that did not happen printed a verdict"
    assert "no value was compared" in captured.err
    assert "No published value moved." not in captured.out


@pytest.mark.parametrize(
    "not_an_artifact",
    [None, [], [1, 2], "measurements", 0, 4370],
    ids=["null", "empty-list", "list", "string", "zero", "number"],
)
def test_a_side_that_is_not_a_json_object_is_refused(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, not_an_artifact: object
) -> None:
    """A build that failed and wrote `null` must not read as a clean refresh.

    Two `null` documents pair as one scalar leaf that equals itself: `1 values
    compared`, `No published value moved.`, exit 0.
    """
    old = _write(tmp_path / "old.json", not_an_artifact)
    new = _write(tmp_path / "new.json", not_an_artifact)

    assert main([str(old), str(new)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not a JSON object" in captured.err
    assert "old" in captured.err, "the refusal has to say which side was wrong"


def test_the_new_side_is_checked_too_not_only_the_old_one(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    old = _write(tmp_path / "old.json", sample_tree())
    new = _write(tmp_path / "new.json", None)

    assert main([str(old), str(new)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the new artifact is not a JSON object" in captured.err


def test_a_file_compared_with_itself_is_refused(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A file cannot differ from itself, so its clean verdict is guaranteed, not earned."""
    only = _write(tmp_path / "measurements.json", sample_tree())

    assert main([str(only), str(only)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "same file" in captured.err


def test_two_paths_to_one_file_are_still_one_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The refusal resolves the paths, so `./x.json` and `x.json` do not slip past."""
    only = _write(tmp_path / "measurements.json", sample_tree())
    indirect = tmp_path / "." / "measurements.json"

    assert main([str(only), str(indirect)]) == 2
    assert "same file" in capsys.readouterr().err


def test_json_mode_prints_no_object_for_a_comparison_that_was_not_made(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`--json` must not hand a caller `"refused": false` over an empty comparison."""
    old = _write(tmp_path / "old.json", {})
    new = _write(tmp_path / "new.json", {})

    assert main([str(old), str(new), "--json"]) == 2
    assert capsys.readouterr().out == ""


def test_allow_removals_does_not_reach_past_the_refusals(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The flag accepts removals. It is not a way to accept a comparison of nothing."""
    old = _write(tmp_path / "old.json", {})
    new = _write(tmp_path / "new.json", {})

    assert main([str(old), str(new), "--allow-removals"]) == 2
    assert capsys.readouterr().out == ""


def test_a_real_comparison_of_two_distinct_artifacts_still_passes(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The control: the guards narrow, they do not break the comparison they guard."""
    old = _write(tmp_path / "old.json", sample_tree())
    new = _write(tmp_path / "new.json", sample_tree())

    assert main([str(old), str(new)]) == 0
    out = capsys.readouterr().out
    assert "No published value moved." in out
    assert out.startswith(
        f"{diff_trees(sample_tree(), sample_tree()).total} values compared"
    )


def test_one_side_empty_is_still_a_removal_not_a_shape_refusal(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """An artifact that lost everything is the case the tool already caught; keep it.

    `{}` is a JSON object, so it passes the shape check, and the comparison is not
    empty: every leaf of the old artifact is a removal. That must stay a refusal with
    exit 1 and the REMOVED lines, not become the new exit-2 message.
    """
    old = _write(tmp_path / "old.json", sample_tree())
    new = _write(tmp_path / "new.json", {})

    assert main([str(old), str(new)]) == 1
    out = capsys.readouterr().out
    assert "REMOVED  $.placement_coverage.fire_records" in out
    assert "REFUSED: published values disappeared." in out
