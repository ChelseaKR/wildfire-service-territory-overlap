"""What `refresh --check` says, and the three states its exit code has to carry.

The command exists because `PROVENANCE.md` declares three staleness triggers and, until
now, two of them could only be answered by running the whole acquisition: 180 MB and
132,522 structure records downloaded to find out whether anything had moved.

The thing that would make it worse than useless is the one these tests are mostly about.
Exit `0` meaning "I asked and the answer was no" and exit `0` meaning "I could not ask"
would put a stale pin and a healthy pin behind the same green. Every branch below that
produces an unmeasurable verdict has a test, and one asserts that the two states do not
share an exit code.

Nothing here opens a socket. `check` takes its clock, its fetch and its count as
parameters, and every test supplies them.
"""

from __future__ import annotations

import inspect
import json
from datetime import date
from typing import Any

import pytest
from perimeter.acquire import AcquisitionBlocked, AcquisitionFailed

from wildfire_service_territory_overlap import refresh as refresh_module
from wildfire_service_territory_overlap.acquire import USER_AGENT
from wildfire_service_territory_overlap.refresh import (
    ALL_SOURCES,
    EXIT_COULD_NOT_CHECK,
    EXIT_NO_TRIGGER,
    EXIT_TRIGGER_FIRED,
    STALE_AFTER_DAYS,
    TERRITORY_LAYERS,
    CheckResult,
    Verdict,
    age_trigger,
    check,
    count_observations,
    main,
    publisher_trigger,
    render,
)

PINNED = "2026-08-23"


def epoch_ms(day: str) -> int:
    """An ArcGIS item's `modified`, which is milliseconds since the epoch, in UTC."""
    return (
        int(date.fromisoformat(day).toordinal() - date(1970, 1, 1).toordinal())
        * 86_400_000
    )


def item_metadata(modified: dict[str, str]) -> Any:
    """A fetch that answers each territory layer's item document."""

    def fetch(url: str, **_: object) -> dict[str, Any]:
        for source in TERRITORY_LAYERS:
            if source.item_id in url:
                return {
                    "id": source.item_id,
                    "modified": epoch_ms(modified[source.key]),
                }
        raise AssertionError(f"the check asked for {url}, which is no layer's item")

    return fetch


def counts_at(values: dict[str, int]) -> Any:
    def count(endpoint: str) -> int:
        for source in ALL_SOURCES:
            if source.endpoint == endpoint:
                return values[source.key]
        raise AssertionError(f"the check counted {endpoint}, which is no source")

    return count


def clean_fetch() -> Any:
    return item_metadata({source.key: "2026-08-12" for source in TERRITORY_LAYERS})


def clean_counts() -> Any:
    return counts_at({source.key: source.feature_count for source in ALL_SOURCES})


def verdict_for(result: CheckResult, name: str) -> Verdict:
    return next(trigger.verdict for trigger in result.triggers if trigger.name == name)


def detail_for(result: CheckResult, name: str) -> str:
    return next(trigger.detail for trigger in result.triggers if trigger.name == name)


# --- trigger 1: age, and the third state a two-way check does not have ----------------


def test_a_pin_inside_the_cadence_has_not_fired() -> None:
    trigger = age_trigger(PINNED, date.fromisoformat("2026-09-08"))
    assert trigger.verdict is Verdict.NOT_FIRED
    assert "16 days old" in trigger.detail


def test_a_pin_past_the_cadence_has_fired() -> None:
    trigger = age_trigger(PINNED, date.fromisoformat("2027-09-08"))
    assert trigger.verdict is Verdict.FIRED
    assert str(STALE_AFTER_DAYS) in trigger.detail


def test_the_boundary_day_itself_has_not_fired() -> None:
    """Exactly the cadence is inside it. Stated as a test so it is not decided twice."""
    on_the_day = date.fromordinal(
        date.fromisoformat(PINNED).toordinal() + STALE_AFTER_DAYS
    )
    assert age_trigger(PINNED, on_the_day).verdict is Verdict.NOT_FIRED
    assert (
        age_trigger(PINNED, date.fromordinal(on_the_day.toordinal() + 1)).verdict
        is Verdict.FIRED
    )


def test_a_retrieval_date_in_the_future_is_unmeasurable_and_not_fresh() -> None:
    """A negative age satisfies a twelve-month check forever.

    A future retrieval date is not a young pin. It is a broken record or a broken clock,
    and reporting it as fresh would hide whichever it is for as long as it lasted.
    """
    trigger = age_trigger("2027-01-01", date.fromisoformat("2026-09-08"))
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert "after today" in trigger.detail
    assert "rather than counted as fresh" in trigger.detail


def test_a_retrieval_date_that_is_not_a_date_is_unmeasurable() -> None:
    trigger = age_trigger("last August", date.fromisoformat("2026-09-08"))
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert "not an ISO date" in trigger.detail


# --- trigger 2: the publisher, and every way a 200 can carry no answer ----------------


def test_a_publisher_that_has_not_moved_has_not_fired() -> None:
    trigger = publisher_trigger(clean_fetch())
    assert trigger.verdict is Verdict.NOT_FIRED
    for source in TERRITORY_LAYERS:
        assert source.key in trigger.detail


def test_a_publisher_that_has_moved_has_fired() -> None:
    fetch = item_metadata(
        {TERRITORY_LAYERS[0].key: "2026-09-01", TERRITORY_LAYERS[1].key: "2026-08-12"}
    )
    trigger = publisher_trigger(fetch)
    assert trigger.verdict is Verdict.FIRED
    assert "which is later" in trigger.detail


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"id": "x"}, "no 'modified' field"),
        ({"modified": "2026-09-01"}, "not an epoch timestamp"),
        ({"modified": True}, "not an epoch timestamp"),
        ({"modified": 10**20}, "not a point in time"),
    ],
)
def test_an_answer_that_is_not_a_date_is_unmeasurable_and_not_unchanged(
    payload: dict[str, Any], expected: str
) -> None:
    """The four ways an HTTP 200 can carry no answer.

    Each of them is the shape a check like this reports as "nothing changed": a field
    that moved, a type that changed, a number that is not a time. None of them is
    coerced, and none of them reaches `not_fired`.
    """
    trigger = publisher_trigger(lambda url, **_: payload)
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert expected in trigger.detail


@pytest.mark.parametrize("error", [AcquisitionBlocked("no"), AcquisitionFailed("no")])
def test_a_refused_request_is_unmeasurable(error: Exception) -> None:
    def fetch(url: str, **_: object) -> dict[str, Any]:
        raise error

    trigger = publisher_trigger(fetch)
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert "could not be read" in trigger.detail


def test_one_layer_that_moved_fires_even_though_the_other_could_not_be_read() -> None:
    """A fired trigger is actionable whatever else went unanswered.

    The reverse would be worse: reporting the whole trigger unmeasurable because one
    layer refused would bury a boundary that has demonstrably moved.
    """
    moved, unreadable = TERRITORY_LAYERS

    def fetch(url: str, **_: object) -> dict[str, Any]:
        if moved.item_id in url:
            return {"modified": epoch_ms("2026-09-01")}
        raise AcquisitionFailed("the second layer's item is private")

    trigger = publisher_trigger(fetch)
    assert trigger.verdict is Verdict.FIRED
    assert moved.key in trigger.detail
    assert unreadable.key in trigger.detail, (
        "the layer that could not be read has to stay in the report; a fired trigger is "
        "not permission to stop saying what went unanswered"
    )


def test_a_source_with_no_recorded_item_id_is_unmeasurable_rather_than_skipped() -> (
    None
):
    """A layer the pin records no item for cannot answer the question.

    Skipping it would leave the trigger reporting `not_fired` over a set it silently
    narrowed, which is the same green a full check produces.
    """
    trigger = publisher_trigger(clean_fetch(), (ALL_SOURCES[0],))
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert "no item id" in trigger.detail


def test_a_source_whose_pinned_modification_date_is_blank_is_unmeasurable() -> None:
    """The pin can carry an item id and no date to compare an answer against.

    `county_boundaries` is exactly that today: `item_id` is set and `item_modified` is
    the empty string. Fetching its item and reporting `not_fired` would be comparing a
    real date against nothing and calling the result "no later".
    """
    counties = next(s for s in ALL_SOURCES if s.key == "county_boundaries")
    assert counties.item_id and not counties.item_modified, (
        "this test is about a source with an id and no pinned date; if sources.py has "
        "since recorded one, point it at whichever source is in that state or delete it"
    )
    trigger = publisher_trigger(clean_fetch(), (counties,))
    assert trigger.verdict is Verdict.UNMEASURABLE
    assert "not an ISO date" in trigger.detail


def test_a_check_over_no_layers_is_refused_rather_than_reported_as_clean() -> None:
    """A rule that iterates over nothing prints the same line as one that found nothing."""
    with pytest.raises(ValueError, match="having asked nobody"):
        publisher_trigger(clean_fetch(), ())


# --- trigger 3, which is never checked here and says so -------------------------------


def test_the_pipeline_trigger_is_reported_as_not_checked_on_every_run() -> None:
    result = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    assert verdict_for(result, "pipeline_shape") is Verdict.NOT_CHECKED_HERE
    assert "nothing here can see it" in detail_for(result, "pipeline_shape")
    assert result.exit_code == EXIT_NO_TRIGGER, (
        "a trigger this command does not check must not make every run non-zero; the "
        "sentence is what carries it, and a permanently red command is a command "
        "somebody switches off"
    )


# --- the exit code, which is the whole contract ---------------------------------------


def test_a_clean_run_exits_zero() -> None:
    result = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    assert result.exit_code == EXIT_NO_TRIGGER
    assert "none fired" in render(result)


def test_a_fired_trigger_exits_one() -> None:
    result = check(
        today=date.fromisoformat("2027-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    assert result.exit_code == EXIT_TRIGGER_FIRED
    assert "stale by this project's own cadence" in render(result)


def test_a_trigger_that_could_not_be_checked_does_not_exit_zero() -> None:
    """The distinction the whole command is for.

    A run that could not ask and a run that asked and got no is the same output to a
    caller reading only the exit code, unless they are different numbers.
    """

    def refuse(url: str, **_: object) -> dict[str, Any]:
        raise AcquisitionFailed("the item is private")

    unmeasurable = check(
        today=date.fromisoformat("2026-09-08"), fetch=refuse, count=clean_counts()
    )
    clean = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    assert clean.exit_code == EXIT_NO_TRIGGER
    assert unmeasurable.exit_code == EXIT_COULD_NOT_CHECK
    assert unmeasurable.exit_code != clean.exit_code
    assert "unanswered question" in render(unmeasurable)


def test_a_fired_trigger_beats_one_that_could_not_be_checked() -> None:
    """Both states are present and the actionable one decides the exit code."""

    def refuse(url: str, **_: object) -> dict[str, Any]:
        raise AcquisitionFailed("the item is private")

    result = check(
        today=date.fromisoformat("2027-09-08"), fetch=refuse, count=clean_counts()
    )
    assert verdict_for(result, "age") is Verdict.FIRED
    assert verdict_for(result, "publisher_moved") is Verdict.UNMEASURABLE
    assert result.exit_code == EXIT_TRIGGER_FIRED


# --- record counts: reported, never a trigger -----------------------------------------


def test_a_count_that_matches_the_pin_is_reported_as_the_pinned_number() -> None:
    observations = count_observations(ALL_SOURCES, count=clean_counts())
    assert len(observations) == len(ALL_SOURCES)
    assert all(not observation.moved for observation in observations)
    assert all("the number the pin was built on" in o.detail for o in observations)


def test_a_grown_layer_is_reported_and_does_not_move_the_exit_code() -> None:
    """Not a trigger, and the output says so rather than leaving it implied.

    PROVENANCE.md declares three triggers and a record count that moved is not one of
    them. Adding a fourth is an edit to that document, so this command reports the
    number and stops there. It is reported because a layer that has grown is the plainest
    evidence there is that the published measurement describes a superseded file.
    """
    grown = {source.key: source.feature_count for source in ALL_SOURCES}
    dins = ALL_SOURCES[0]
    grown[dins.key] += 7_580
    result = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=counts_at(grown),
    )
    assert result.exit_code == EXIT_NO_TRIGGER
    observation = next(o for o in result.counts if o.source_key == dins.key)
    assert observation.moved is True
    assert observation.now == dins.feature_count + 7_580
    printed = render(result)
    assert "7,580 more" in printed
    assert "not one of the three triggers" in printed


def test_a_count_that_could_not_be_read_is_null_rather_than_the_pinned_number() -> None:
    """`now: null` and `now: <the pinned figure>` are different facts.

    Falling back to the pin would publish "unchanged" for a layer nobody could reach,
    which is the defect this whole command is built against, one level down.
    """

    def refuse(endpoint: str) -> int:
        raise AcquisitionBlocked("the layer answered 403")

    result = check(
        today=date.fromisoformat("2026-09-08"), fetch=clean_fetch(), count=refuse
    )
    assert all(o.now is None for o in result.counts)
    assert all(o.moved is False for o in result.counts), (
        "moved is False, not None, in Python"
    )
    assert all(o.to_dict()["moved"] is None for o in result.counts), (
        "the record a machine reads must not say a layer did not move when nobody could "
        "count it"
    )
    assert result.exit_code == EXIT_NO_TRIGGER, (
        "an observation is not a trigger in either direction; the exit code is a "
        "statement about the three declared triggers and nothing else"
    )
    assert "could not be read" in render(result)


# --- the two renderings -----------------------------------------------------------------


def test_the_json_report_carries_every_trigger_and_the_exit_code() -> None:
    result = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["kind"] == "refresh-check"
    assert payload["exit_code"] == EXIT_NO_TRIGGER
    assert [t["trigger"] for t in payload["triggers"]] == [
        "age",
        "publisher_moved",
        "pipeline_shape",
    ]
    assert {t["verdict"] for t in payload["triggers"]} == {
        "not_fired",
        "not_checked_here",
    }
    assert len(payload["record_counts"]) == len(ALL_SOURCES)


def test_the_prose_report_names_every_trigger_and_every_source() -> None:
    result = check(
        today=date.fromisoformat("2026-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    printed = render(result)
    for name in ("age", "publisher_moved", "pipeline_shape"):
        assert name in printed
    for source in ALL_SOURCES:
        assert source.key in printed
    assert printed.endswith("\n")


def test_the_default_fetch_is_the_shared_reader_rather_than_a_second_one() -> None:
    """The refusals this check depends on are upstream's, not a copy of them.

    `fetch_document` carries HTTPS only, an honest User-Agent, the stop on 401, 403 and
    429, the non-JSON challenge page and the error payload. A default that was anything
    else here would be a sixth copy of those five, which is what the pin move deleted.
    """
    seen: list[tuple[str, object]] = []

    def spy(url: str, **kwargs: object) -> dict[str, Any]:
        seen.append((url, kwargs.get("user_agent")))
        return {"modified": epoch_ms("2026-08-12")}

    monkeyed = check(
        today=date.fromisoformat("2026-09-08"), fetch=spy, count=clean_counts()
    )
    assert monkeyed.exit_code == EXIT_NO_TRIGGER
    assert {identity for _url, identity in seen} == {USER_AGENT}, (
        "every request this command makes names this project, like every other request "
        "in this repository"
    )
    assert inspect.signature(check).parameters["fetch"].default is None


def test_omitting_the_fetch_reaches_upstreams_reader_and_not_a_local_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default is proven by driving it, not by reading the source.

    A default that is accepted and never reached looks exactly like one that works, and
    every other test here passes its own fetch, so nothing else would notice if this
    line stopped naming upstream's reader. `fetch_document` is substituted on the module
    under test, so no socket opens and the call has to arrive through the default.
    """
    called: list[str] = []

    def spy(url: str, **_: object) -> dict[str, Any]:
        called.append(url)
        return {"modified": epoch_ms("2026-08-12")}

    monkeypatch.setattr(refresh_module, "fetch_document", spy)
    result = check(today=date.fromisoformat("2026-09-08"), count=clean_counts())
    assert called, (
        "the default fetch was never called, so it is a parameter in name only"
    )
    assert len(called) == len(TERRITORY_LAYERS)
    assert result.exit_code == EXIT_NO_TRIGGER


def test_main_prints_the_report_and_returns_the_results_own_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`main` opens a socket on its own, so what is checked here is the wiring.

    The exit code has to be the result's rather than recomputed, or the contract could
    drift between the object and the process.
    """
    stale = check(
        today=date.fromisoformat("2027-09-08"),
        fetch=clean_fetch(),
        count=clean_counts(),
    )
    monkeypatch.setattr(refresh_module, "check", lambda: stale)
    assert main(["--check"]) == EXIT_TRIGGER_FIRED
    assert "stale by this project's own cadence" in capsys.readouterr().out
    assert main(["--check", "--json"]) == EXIT_TRIGGER_FIRED
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == EXIT_TRIGGER_FIRED
    assert payload["kind"] == "refresh-check"


def test_the_command_line_requires_check_rather_than_defaulting_to_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A network command with a bare invocation is one somebody runs by accident.

    Requiring the mode also means a later `--run` is an addition rather than a change to
    what a bare `python -m ...refresh` already did.
    """
    with pytest.raises(SystemExit):
        main([])
    assert "--check" in capsys.readouterr().err
