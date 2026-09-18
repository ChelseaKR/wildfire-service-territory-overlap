"""The bounded county cross-check, and every refusal it can make.

The retrieval half of roadmap item 3.4 does not exist: no county inspection record set
is pinned anywhere in this repository. What is testable without it is the comparison
itself, and the point of this file is that each refusal below is driven until it fires.
A gate nobody has watched refuse is a gate nobody knows the shape of, and this
repository already carries a written-down audit of gates that were numerically
incapable of firing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wildfire_service_territory_overlap import artifacts
from wildfire_service_territory_overlap.cross_check import (
    ABSENT_FROM_THIS_RECORD_SET,
    BLOCK_KEY,
    HERE_UNDER_ANOTHER_COUNTY,
    IN_BOTH,
    NOT_NAMED_BY_THE_COUNTY_RECORD_SET,
    CrossCheckRefused,
    _check,
    as_block,
    compare,
    cross_check,
    main,
    read_external,
)
from wildfire_service_territory_overlap.placement import Record
from wildfire_service_territory_overlap.sources import SOURCES

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
DINS_SAMPLE = FIXTURES / "dins_sample.json"
COUNTY_SAMPLE = FIXTURES / "county_inspections_sample.json"
COUNTY_WITH_A_COORDINATE = FIXTURES / "county_inspections_with_a_coordinate_sample.json"

EAST = "Sample County East"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def block() -> dict[str, Any]:
    return cross_check(EAST, read(DINS_SAMPLE), read(COUNTY_SAMPLE))[BLOCK_KEY]


def placed(**kwargs: Any) -> Record:
    """A record with a usable coordinate, so only the fields under test vary."""
    base: dict[str, Any] = {
        "object_id": 1,
        "damage": "No Damage",
        "incident": "A FIRE",
        "county": "Test County",
        "year": 2020,
        "lon": -120.0,
        "lat": 38.0,
    }
    base.update(kwargs)
    return Record(**base)


# --- the comparison itself -------------------------------------------------------


def test_every_outcome_is_reached_by_the_committed_fixtures(
    block: dict[str, Any],
) -> None:
    """Agreement and all three disagreements, from files a reader can open."""
    assert block["counts"] == {
        ABSENT_FROM_THIS_RECORD_SET: 1,
        HERE_UNDER_ANOTHER_COUNTY: 1,
        IN_BOTH: 1,
        NOT_NAMED_BY_THE_COUNTY_RECORD_SET: 1,
    }


def test_each_fire_carries_the_counts_both_sides_hold_for_it(
    block: dict[str, Any],
) -> None:
    rows = {row["incident"]: row for row in block["incidents"]}
    assert rows["SAMPLE ONE"]["outcome"] == IN_BOTH
    assert rows["SAMPLE ONE"]["records_here_in_this_county"] == 3
    assert rows["SAMPLE ONE"]["records_in_the_county_record_set"] == 2
    # Recorded here under Sample County West, so the fire is in both files and the two
    # publishers disagree about which county it is in. Counted, never corrected.
    assert rows["SAMPLE THREE"]["outcome"] == HERE_UNDER_ANOTHER_COUNTY
    assert rows["SAMPLE THREE"]["records_here_in_this_county"] == 0
    assert rows["SAMPLE THREE"]["records_here_in_another_county"] == 3
    assert rows["SAMPLE FIVE"]["outcome"] == ABSENT_FROM_THIS_RECORD_SET
    assert rows["SAMPLE TWO"]["outcome"] == NOT_NAMED_BY_THE_COUNTY_RECORD_SET


def test_the_fires_come_out_in_name_order(block: dict[str, Any]) -> None:
    names = [row["incident"] for row in block["incidents"]]
    assert names == sorted(names)
    assert names == ["SAMPLE FIVE", "SAMPLE ONE", "SAMPLE THREE", "SAMPLE TWO"]


def test_case_and_spacing_are_folded_and_nothing_else_is(block: dict[str, Any]) -> None:
    """`Sample  One` and `SAMPLE ONE` are one fire; `SAMPLE FIVE` is not `SAMPLE ONE`.

    The fixture spells one row wrong on purpose. Folding case and inner whitespace is
    what two publishers can be expected to differ on; anything past that would be this
    project deciding that two names are one fire.
    """
    rows = {row["incident"]: row for row in block["incidents"]}
    assert rows["SAMPLE ONE"]["records_in_the_county_record_set"] == 2
    assert len(block["incidents"]) == 4


def test_both_shares_are_published_over_their_own_denominators(
    block: dict[str, Any],
) -> None:
    theirs = block["agreement_with_the_county_record_set"]
    ours = block["agreement_with_this_record_set"]
    assert (theirs["numerator"], theirs["denominator"]) == (1, 3)
    assert (ours["numerator"], ours["denominator"]) == (1, 2)
    assert theirs["interval_method"] == "wilson-score-95"
    assert ours["interval_method"] == "wilson-score-95"


def keys_of(node: Any) -> list[str]:
    """Every key anywhere in the block, so a rule can be stated about all of them."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.append(key)
            found.extend(keys_of(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(keys_of(value))
    return found


def test_no_difference_is_drawn_between_the_two_shares(block: dict[str, Any]) -> None:
    """Two questions with two denominators, not one thing measured twice."""
    assert "difference" not in keys_of(block)


def test_no_rate_is_taken_between_the_two_record_sets(block: dict[str, Any]) -> None:
    """Neither file is the other's denominator, so no rate may carry a record count."""
    record_counts = set(block["records"].values())
    incident_counts = {
        block["incidents_named_by_the_county_record_set"],
        block["incidents_this_project_counts_in_this_county"],
    }
    for key in (
        "agreement_with_the_county_record_set",
        "agreement_with_this_record_set",
    ):
        denominator = block[key]["denominator"]
        assert denominator in incident_counts
        assert denominator not in (record_counts - incident_counts)


def test_the_record_counts_are_published_whole_and_never_divided(
    block: dict[str, Any],
) -> None:
    assert block["records"] == {
        "in_this_project_for_this_county": 6,
        "in_this_project_carrying_an_incident_name": 6,
        "in_the_county_record_set": 5,
    }


def test_no_key_anywhere_names_damage_destruction_or_loss(
    block: dict[str, Any],
) -> None:
    """ADR 0004 and ADR 0009 refuse a damage rate for a county. So does this block.

    Stated over keys, the way the territory rule is stated: the prose in the block says
    in as many words that no damage rate is published, and a rule about the prose would
    have to make an exception for the sentence that promises it.
    """
    for key in keys_of(block):
        lowered = key.lower()
        for word in ("damage", "destroy", "destruction", "loss"):
            assert word not in lowered, key


def test_the_block_passes_the_publication_rules_it_declares(
    block: dict[str, Any],
) -> None:
    tree = {BLOCK_KEY: block}
    artifacts.assert_rates_are_denominated(tree)
    artifacts.assert_no_locating_fields(tree)
    artifacts.assert_no_ranking(tree)


def test_the_comparison_is_deterministic() -> None:
    first = cross_check(EAST, read(DINS_SAMPLE), read(COUNTY_SAMPLE))
    second = cross_check(EAST, read(DINS_SAMPLE), read(COUNTY_SAMPLE))
    assert artifacts.serialize(first) == artifacts.serialize(second)


def test_the_county_is_reported_in_this_project_s_own_spelling() -> None:
    """Asked for in any casing, published as the record set spells it."""
    block = cross_check(
        "  sample   county   east  ", read(DINS_SAMPLE), read(COUNTY_SAMPLE)
    )[BLOCK_KEY]
    assert block["county"] == EAST


def test_a_county_with_no_incident_names_reports_not_measured_never_zero() -> None:
    """The one share that can fail to have a denominator, published as words."""
    records = (
        placed(object_id=1, county="Quiet County", incident=None),
        placed(object_id=2, county="Other County", incident="SOME FIRE"),
    )
    external = read_external(
        [{"county": "Quiet County", "incident": "SOME FIRE"}], county="Quiet County"
    )
    block = as_block(compare("Quiet County", records, external))[BLOCK_KEY]
    ours = block["agreement_with_this_record_set"]
    assert ours["state"] == "not_measured"
    assert ours["rate"] is None
    assert ours["interval_low"] is None
    assert block["incidents_this_project_counts_in_this_county"] == 0
    assert block["counts"][HERE_UNDER_ANOTHER_COUNTY] == 1


# --- the refusals ----------------------------------------------------------------


def test_an_external_set_that_is_not_a_list_of_rows_is_refused() -> None:
    with pytest.raises(CrossCheckRefused, match="not a list of rows"):
        read_external({"county": EAST}, county=EAST)


def test_an_empty_external_set_is_refused_rather_than_read_as_disagreement() -> None:
    with pytest.raises(CrossCheckRefused, match="holds no rows"):
        read_external([], county=EAST)


def test_a_row_that_is_not_an_object_is_refused() -> None:
    with pytest.raises(CrossCheckRefused, match=r"row 1 .* is not an object"):
        read_external([{"county": EAST, "incident": "A"}, "SAMPLE ONE"], county=EAST)


@pytest.mark.parametrize(
    "locating", ["latitude", "LONGITUDE", "apn", "siteaddress", "parcel", "x"]
)
def test_an_external_set_carrying_a_position_is_refused(locating: str) -> None:
    """The same key list `artifacts.check_all` refuses a published artifact for."""
    with pytest.raises(CrossCheckRefused, match="does not read an address"):
        read_external(
            [{"county": EAST, "incident": "SAMPLE ONE", locating: 1}], county=EAST
        )


def test_the_committed_file_with_a_coordinate_in_it_is_refused() -> None:
    """The refusal a maintainer will actually meet, driven from a file on disk."""
    with pytest.raises(CrossCheckRefused, match="does not read an address"):
        cross_check(EAST, read(DINS_SAMPLE), read(COUNTY_WITH_A_COORDINATE))


def test_a_row_naming_no_county_is_refused() -> None:
    with pytest.raises(CrossCheckRefused, match="names no county"):
        read_external([{"county": "  ", "incident": "SAMPLE ONE"}], county=EAST)


def test_a_row_naming_no_fire_is_refused_rather_than_dropped() -> None:
    with pytest.raises(CrossCheckRefused, match="names no fire"):
        read_external([{"county": EAST, "incident": None}], county=EAST)


def test_a_row_naming_another_county_is_refused_not_filtered_away() -> None:
    with pytest.raises(CrossCheckRefused, match="asked for another county"):
        read_external(
            [
                {"county": EAST, "incident": "SAMPLE ONE"},
                {"county": "Sample County West", "incident": "SAMPLE THREE"},
            ],
            county=EAST,
        )


def test_a_county_this_project_holds_no_record_for_is_refused() -> None:
    external = read_external(
        [{"county": "Absent County", "incident": "A FIRE"}], county="Absent County"
    )
    with pytest.raises(CrossCheckRefused, match="carries no record under the county"):
        compare("Absent County", (placed(),), external)


def test_a_county_this_project_measured_as_not_measured_is_refused() -> None:
    """Every record has the county and none has a usable coordinate."""
    records = (
        placed(object_id=1, county="Dark County", lon=None, lat=None),
        placed(object_id=2, county="Dark County", lon=999.0, lat=999.0),
    )
    external = read_external(
        [{"county": "Dark County", "incident": "A FIRE"}], county="Dark County"
    )
    with pytest.raises(CrossCheckRefused, match="as not measured"):
        compare("Dark County", records, external)


def test_a_comparison_naming_more_fires_than_the_record_set_does_is_refused() -> None:
    """The cap, driven past. The record set names one fire; the comparison names two."""
    records = (placed(incident="FIRE A"),)
    external = read_external(
        [
            {"county": "Test County", "incident": "FIRE A"},
            {"county": "Test County", "incident": "FIRE B"},
        ],
        county="Test County",
    )
    with pytest.raises(CrossCheckRefused, match="names 2 distinct fires"):
        compare("Test County", records, external)


def test_a_comparison_where_no_name_is_shared_is_refused() -> None:
    """ADR 0015's "defect, not a finding", driven until it fires.

    The third record sits in another county so the record set names three fires and the
    cap above is not what refuses this. A statewide file naming more fires than any one
    county's is the ordinary case, not a contrivance.
    """
    records = (
        placed(object_id=1, county="Test County", incident="FIRE A"),
        placed(object_id=2, county="Test County", incident="FIRE B"),
        placed(object_id=3, county="Other County", incident="FIRE C"),
    )
    external = read_external(
        [{"county": "Test County", "incident": "FIRE A 2020"}], county="Test County"
    )
    with pytest.raises(CrossCheckRefused, match="not one name is shared"):
        compare("Test County", records, external)


def test_the_real_county_set_and_this_project_do_not_share_a_fire_name() -> None:
    """The retrieval that closed the search, held as the case the refusal was built for.

    Napa County's own ATC damage assessments carry two incident names, read from the
    county's layer on 2026-09-05 and recorded in `docs/adr/0018`. CAL FIRE's file
    names the same two ground events its own way and carries neither county spelling
    anywhere in California. Every fire lands in a disagreement bucket and the
    comparison measures nothing, so it is refused rather than printed.

    The names are written out here because the whole finding is that they differ. A
    future edit that makes this test pass by pairing them is the fuzzy match ADR 0003
    and ADR 0013 refuse, and it would be this project deciding that two names are one
    fire.
    """
    napa = tuple(
        placed(object_id=index, county="Napa", incident=name)
        for index, name in enumerate(("Glass", "LNU Lightning Cmplx", "Atlas"), start=1)
    )
    # Two fires from elsewhere in the state, because the cap this comparison runs under
    # is the whole record set's count of distinct fires and CAL FIRE's file is statewide.
    records = (
        *napa,
        placed(object_id=4, county="Butte", incident="Camp"),
        placed(object_id=5, county="Shasta", incident="Carr"),
    )
    external = read_external(
        [
            {"county": "Napa", "incident": "GLASS COMPLEX 2020"},
            {"county": "Napa", "incident": "NAPA LIGHTNING COMPLEX 2020"},
        ],
        county="Napa",
    )
    with pytest.raises(CrossCheckRefused, match="ADR 0015 reads that as a fault"):
        compare("Napa", records, external)


def test_a_zero_agreement_is_not_refused_when_one_side_names_nothing_here() -> None:
    """The boundary of the refusal, from the side that must still be allowed through.

    A county this project counts no incident name in publishes its second share as not
    measured, and a zero agreement there is a join nobody attempted rather than a join
    that failed. `test_a_county_with_no_incident_names_reports_not_measured_never_zero`
    reads the block that case produces; this states why the new refusal leaves it
    alone.
    """
    records = (
        placed(object_id=1, county="Quiet County", incident=None),
        placed(object_id=2, county="Other County", incident="SOME FIRE"),
    )
    external = read_external(
        [{"county": "Quiet County", "incident": "SOME FIRE"}], county="Quiet County"
    )
    result = compare("Quiet County", records, external)
    assert result.outcomes[IN_BOTH] == 0
    assert result.outcomes[HERE_UNDER_ANOTHER_COUNTY] == 1


def test_the_cap_admits_a_comparison_that_exactly_reaches_it() -> None:
    """The boundary, from the other side, so the refusal is not off by one."""
    records = (placed(incident="FIRE A"), placed(object_id=2, incident="FIRE B"))
    external = read_external(
        [
            {"county": "Test County", "incident": "FIRE A"},
            {"county": "Test County", "incident": "FIRE B"},
        ],
        county="Test County",
    )
    result = compare("Test County", records, external)
    assert len(result.incidents) == 2


# --- the lock on the block itself ------------------------------------------------


def test_the_output_check_refuses_a_block_carrying_a_position() -> None:
    with pytest.raises(artifacts.PublicationRefused):
        _check(
            {BLOCK_KEY: {"incidents": [{"incident": "A", "latitude": 1}]}}, ceiling=4
        )


def test_the_output_check_refuses_a_collection_past_the_ceiling() -> None:
    """The aggregate rule, driven past, so it is known to be able to fire at all."""
    rows = [{"incident": f"FIRE {n}"} for n in range(5)]
    with pytest.raises(artifacts.PublicationRefused, match="against a ceiling of 4"):
        _check({BLOCK_KEY: {"incidents": rows}}, ceiling=4)


# --- the command -----------------------------------------------------------------


def test_the_command_prints_the_block_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "--county",
            EAST,
            "--dins",
            str(DINS_SAMPLE),
            "--external",
            str(COUNTY_SAMPLE),
        ]
    )
    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed[BLOCK_KEY]["counts"][IN_BOTH] == 1


def test_the_command_exits_one_on_a_refusal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        [
            "--county",
            EAST,
            "--dins",
            str(DINS_SAMPLE),
            "--external",
            str(COUNTY_WITH_A_COORDINATE),
        ]
    )
    assert code == 1
    assert "cross-check refused" in capsys.readouterr().err


def test_the_command_exits_one_when_the_retrieval_is_missing_a_column(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A schema fault is an acquisition fault, not a comparison with a hole in it."""
    dins = tmp_path / "short.json"
    dins.write_text(json.dumps([{"OBJECTID": 1}]), encoding="utf-8")
    code = main(
        ["--county", EAST, "--dins", str(dins), "--external", str(COUNTY_SAMPLE)]
    )
    assert code == 1
    assert "missing" in capsys.readouterr().err


def test_the_command_exits_two_when_an_input_is_not_there(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "--county",
            EAST,
            "--dins",
            str(DINS_SAMPLE),
            "--external",
            str(tmp_path / "absent.json"),
        ]
    )
    assert code == 2
    assert "could not read an input" in capsys.readouterr().err


def test_the_command_exits_two_when_an_input_is_not_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    code = main(
        ["--county", EAST, "--dins", str(DINS_SAMPLE), "--external", str(broken)]
    )
    assert code == 2
    assert "not valid JSON" in capsys.readouterr().err


# --- the half that is deliberately not done --------------------------------------


def test_the_cross_check_is_not_wired_into_the_published_pipeline(
    published_artifact: dict[str, Any],
) -> None:
    """ADR 0015: no not-measured block in every build until there is a retrieval.

    A section that says nothing on every run is a section a reader learns to skip
    before the run where it says something, and this repository does not publish a
    figure it has not measured. So the published artifact carries no cross-check block
    and the builder does not import this module.
    """
    assert BLOCK_KEY not in published_artifact
    cli = (ROOT / "src" / "wildfire_service_territory_overlap" / "cli.py").read_text(
        encoding="utf-8"
    )
    assert "cross_check" not in cli


def test_no_county_inspection_source_is_pinned_and_the_documents_say_so() -> None:
    """The retrieval half of roadmap 3.4 is not done, and nothing here implies it is."""
    adr = (
        ROOT
        / "docs"
        / "adr"
        / "0015-one-county-inspection-record-set-is-compared-as-counts-and-neither-side-is-corrected.md"
    ).read_text(encoding="utf-8")
    runbook = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    assert "No county inspection record set is pinned" in adr
    assert "not pinned" in runbook
    assert [source.key for source in SOURCES] == [
        "dins_postfire",
        "else_iou_pou",
        "else_other",
        "county_boundaries",
    ], "a fifth source appeared without this test being told what it is"


def test_the_search_for_a_source_is_recorded_as_finished_and_as_negative() -> None:
    """The half a reader would otherwise have to take on trust.

    The search ran twice, on 2026-09-04 and again on 2026-09-05, and the second one
    ended. A set that meets every criterion exists and is named, the reason it is not
    pinned is stated, and the roadmap no longer offers the guess the first search left
    behind. This test holds all three together because the failure mode is one of them
    being quietly improved into a claim that 3.4 shipped.
    """
    adr = (
        ROOT
        / "docs"
        / "adr"
        / "0018-the-one-eligible-county-record-set-names-its-fires-differently.md"
    ).read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    for expected in (
        "2026-09-05",
        "ATC Damage Assessments 2020 public",
        "GLASS COMPLEX 2020",
        "NAPA LIGHTNING COMPLEX 2020",
        "LNU Lightning Cmplx",
    ):
        assert expected in adr, expected
    assert "not pinned" in adr
    assert "does not exist in fetchable form" not in roadmap, (
        "the roadmap still carries the guess the finished search replaced"
    )
    assert "docs/adr/0018" in roadmap
