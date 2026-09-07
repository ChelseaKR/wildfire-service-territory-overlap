"""The acquisition's refusals, with the socket substituted. Nothing here opens one.

The point of these tests is the failure mode that produced this project's guard rails: a
paged walk that ends normally and is short. A download nothing checked is not an
acquisition, so every check that would catch a short, duplicated, or reordered walk is
exercised against a walk that should fail it.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest
from perimeter.acquire import USER_AGENT as PERIMETER_USER_AGENT
from perimeter.acquire import AcquisitionBlocked, AcquisitionFailed

from wildfire_service_territory_overlap import acquire
from wildfire_service_territory_overlap.acquire import (
    IncompleteAcquisition,
    assert_walk_is_whole,
    fetch_feature_pages,
    layer_record_count,
)
from wildfire_service_territory_overlap.placement import REQUIRED_COLUMNS
from wildfire_service_territory_overlap.sources import ELSE_IOU_POU


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        super().__init__(body)
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def install(monkeypatch: pytest.MonkeyPatch, handler: Any) -> list[str]:
    seen: list[str] = []

    def fake_urlopen(request: Any, timeout: int = 0) -> Any:
        seen.append(request.full_url)
        return handler(request.full_url)

    monkeypatch.setattr(acquire.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(acquire.time, "sleep", lambda _seconds: None)
    return seen


def json_response(payload: dict[str, Any]) -> FakeResponse:
    return FakeResponse(json.dumps(payload).encode())


def test_a_non_https_endpoint_is_refused_before_any_request() -> None:
    with pytest.raises(AcquisitionFailed, match="non-HTTPS"):
        layer_record_count("http://example.invalid/query")


@pytest.mark.parametrize("code", [401, 403, 429])
def test_an_access_control_stops_the_run_rather_than_being_worked_around(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    def handler(url: str) -> Any:
        raise urllib.error.HTTPError(url, code, "no", {}, None)  # type: ignore[arg-type]

    install(monkeypatch, handler)
    with pytest.raises(
        AcquisitionBlocked, match="does not work around access controls"
    ):
        layer_record_count("https://example.test/query")


def test_a_server_error_is_a_failure_not_a_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(url: str) -> Any:
        raise urllib.error.HTTPError(url, 500, "no", {}, None)  # type: ignore[arg-type]

    install(monkeypatch, handler)
    with pytest.raises(AcquisitionFailed, match="answered 500"):
        layer_record_count("https://example.test/query")


def test_an_html_challenge_page_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, lambda _url: FakeResponse(b"<html>", "text/html"))
    with pytest.raises(AcquisitionBlocked, match="challenge page"):
        layer_record_count("https://example.test/query")


def test_an_error_payload_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, lambda _url: json_response({"error": {"code": 400}}))
    with pytest.raises(AcquisitionFailed, match="error payload"):
        layer_record_count("https://example.test/query")


def test_a_count_response_with_no_count_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, lambda _url: json_response({"features": []}))
    with pytest.raises(
        AcquisitionFailed, match="nothing checked is not an acquisition"
    ):
        layer_record_count("https://example.test/query")


def test_a_boolean_is_not_accepted_as_a_count(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, lambda _url: json_response({"count": True}))
    with pytest.raises(AcquisitionFailed):
        layer_record_count("https://example.test/query")


def test_a_good_count_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, lambda _url: json_response({"count": 53}))
    assert layer_record_count("https://example.test/query") == 53


def test_a_whole_walk_is_accepted() -> None:
    assert assert_walk_is_whole([1, 2, 3, 4], 4, layer="x") is None


def test_a_short_walk_is_refused_rather_than_published_as_a_smaller_dataset() -> None:
    with pytest.raises(IncompleteAcquisition, match="hole in it"):
        assert_walk_is_whole([1, 2, 3], 4, layer="x")


def test_a_long_walk_is_refused() -> None:
    with pytest.raises(IncompleteAcquisition, match="reports 3 records"):
        assert_walk_is_whole([1, 2, 3, 4], 3, layer="x")


def test_a_duplicated_page_is_refused_even_though_the_count_matches() -> None:
    with pytest.raises(IncompleteAcquisition, match="duplicate identifiers"):
        assert_walk_is_whole([1, 2, 2, 3], 4, layer="x")


def test_a_reordered_walk_is_refused() -> None:
    with pytest.raises(IncompleteAcquisition, match="not strictly increasing"):
        assert_walk_is_whole([1, 3, 2, 4], 4, layer="x")


def test_the_walk_steps_by_rows_received_not_by_the_page_it_asked_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect this project exists downstream of, reproduced as a test.

    The service is asked for 2000 rows and hands back 1200. A walk that adds the page
    size to its offset asks next for records from 2000 and never sees 1200 to 1999.
    """
    pages = {
        0: [{"properties": {"OBJECTID": i}} for i in range(1, 1201)],
        1200: [{"properties": {"OBJECTID": i}} for i in range(1201, 1401)],
        1400: [],
    }

    def handler(url: str) -> Any:
        offset = int(url.split("resultOffset=")[1].split("&")[0])
        if offset not in pages:
            raise AssertionError(
                f"the walk asked for offset {offset}, which means it stepped by the "
                "page size it requested rather than by the rows it was handed"
            )
        return json_response({"features": pages[offset]})

    install(monkeypatch, handler)
    features = fetch_feature_pages(
        "https://example.test/query", ("OBJECTID",), with_geometry=True
    )
    assert len(features) == 1400
    identifiers = [f["properties"]["OBJECTID"] for f in features]
    assert identifiers == list(range(1, 1401))
    assert_walk_is_whole(identifiers, 1400, layer="x")


def test_a_page_that_is_not_an_array_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, lambda _url: json_response({"features": "no"}))
    with pytest.raises(AcquisitionFailed, match="no features array"):
        fetch_feature_pages(
            "https://example.test/query", ("OBJECTID",), with_geometry=False
        )


def _territory_handler(counts: list[int], features: list[dict[str, Any]]) -> Any:
    calls = {"n": 0}

    def handler(url: str) -> Any:
        if "returnCountOnly=true" in url:
            value = counts[min(calls["n"], len(counts) - 1)]
            calls["n"] += 1
            return json_response({"count": value})
        offset = int(url.split("resultOffset=")[1].split("&")[0])
        return json_response({"features": features[offset:]})

    return handler


def test_a_layer_republished_mid_walk_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    features = [
        {"type": "Feature", "properties": {"OBJECTID": i}, "geometry": None}
        for i in range(1, 4)
    ]
    install(monkeypatch, _territory_handler([3, 4], features))
    with pytest.raises(IncompleteAcquisition, match="republished mid-walk"):
        acquire.acquire_territories(ELSE_IOU_POU, tmp_path)


def test_a_clean_territory_acquisition_writes_a_hashed_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    features = [
        {"type": "Feature", "properties": {"OBJECTID": i}, "geometry": None}
        for i in range(1, 4)
    ]
    install(monkeypatch, _territory_handler([3, 3], features))
    result = acquire.acquire_territories(ELSE_IOU_POU, tmp_path)
    assert result.feature_count == 3
    assert len(result.sha256) == 64
    assert result.endpoint == ELSE_IOU_POU.endpoint
    written = json.loads(result.path.read_text(encoding="utf-8"))
    assert written["type"] == "FeatureCollection"
    assert [f["properties"]["OBJECTID"] for f in written["features"]] == [1, 2, 3]


def test_the_same_features_produce_the_same_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    features = [
        {"type": "Feature", "properties": {"OBJECTID": i}, "geometry": None}
        for i in range(1, 4)
    ]
    install(monkeypatch, _territory_handler([3, 3], features))
    first = acquire.acquire_territories(ELSE_IOU_POU, tmp_path / "a")
    install(monkeypatch, _territory_handler([3, 3], features))
    second = acquire.acquire_territories(ELSE_IOU_POU, tmp_path / "b")
    assert first.sha256 == second.sha256, (
        "an unchanged layer must re-download to byte-identical bytes, or the hash in "
        "PROVENANCE.md cannot be compared against anything"
    )


def test_a_walk_that_arrives_out_of_order_is_refused_rather_than_sorted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sorting a scrambled walk would hide the reason it was scrambled.

    The writer does sort before hashing, so that byte-for-byte comparison is possible.
    That is not a licence to accept a walk that came back out of the order it asked for:
    a service that reorders under pagination is a service that may also be repeating or
    skipping pages, and only the order reveals it.
    """
    features = [
        {"type": "Feature", "properties": {"OBJECTID": i}, "geometry": None}
        for i in (3, 1, 2)
    ]
    install(monkeypatch, _territory_handler([3, 3], features))
    with pytest.raises(IncompleteAcquisition, match="not strictly increasing"):
        acquire.acquire_territories(ELSE_IOU_POU, tmp_path)


def test_dins_acquisition_checks_the_walk_it_did_not_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [{"OBJECTID": i, "DAMAGE": "No Damage"} for i in range(1, 5)]
    monkeypatch.setattr(
        acquire, "perimeter_layer_record_count", lambda _e, user_agent="": 4
    )
    monkeypatch.setattr(
        acquire, "perimeter_fetch_layer", lambda _e, _f, user_agent="": rows
    )
    result = acquire.acquire_dins(tmp_path)
    assert result.feature_count == 4


def test_a_short_upstream_walk_is_caught_here_rather_than_trusted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [{"OBJECTID": i} for i in range(1, 4)]
    monkeypatch.setattr(
        acquire, "perimeter_layer_record_count", lambda _e, user_agent="": 4
    )
    monkeypatch.setattr(
        acquire, "perimeter_fetch_layer", lambda _e, _f, user_agent="": rows
    )
    with pytest.raises(IncompleteAcquisition, match="hole in it"):
        acquire.acquire_dins(tmp_path)
    assert not list(tmp_path.iterdir()), "nothing is written when the walk is short"


def test_dins_acquisition_refuses_a_layer_republished_mid_walk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    counts = iter([4, 5])
    monkeypatch.setattr(
        acquire, "perimeter_layer_record_count", lambda _e, user_agent="": next(counts)
    )
    monkeypatch.setattr(
        acquire,
        "perimeter_fetch_layer",
        lambda _e, _f, user_agent="": [{"OBJECTID": 1}],
    )
    with pytest.raises(IncompleteAcquisition, match="republished mid-walk"):
        acquire.acquire_dins(tmp_path)


def test_no_address_or_parcel_field_is_ever_requested() -> None:
    forbidden = {
        "SITEADDRESS",
        "APN",
        "STREETNUMBER",
        "STREETNAME",
        "STREETTYPE",
        "ZIPCODE",
        "ASSESSEDIMPROVEDVALUE",
    }
    assert forbidden.isdisjoint(acquire.DINS_FIELDS)


def test_the_county_column_is_requested_and_is_read_by_the_pipeline() -> None:
    """The field the county cut needs, asked for once, in the one place that asks."""
    assert "COUNTY" in acquire.DINS_FIELDS
    assert set(acquire.DINS_FIELDS) >= set(REQUIRED_COLUMNS), (
        "the retrieval must fetch every column the schema guard then insists on"
    )


# --- Who the publisher's server is told is calling ---------------------------------


def install_recording(
    monkeypatch: pytest.MonkeyPatch, handler: Any
) -> list[tuple[str, str | None]]:
    """Substitute the socket and record the identity each request carried.

    `urllib.request` is one module object, so replacing `urlopen` on it reaches the walk
    inside `perimeter` as well as the walk here. Nothing below opens a socket.
    """
    sent: list[tuple[str, str | None]] = []

    def fake_urlopen(request: Any, timeout: int = 0) -> Any:
        sent.append((request.full_url, request.get_header("User-agent")))
        return handler(request.full_url)

    monkeypatch.setattr(acquire.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(acquire.time, "sleep", lambda _seconds: None)
    return sent


def _dins_handler(rows: list[dict[str, Any]]) -> Any:
    """Answer the walk `perimeter` runs: attribute rows under `f=json`."""

    def handler(url: str) -> Any:
        if "returnCountOnly=true" in url:
            return json_response({"count": len(rows)})
        offset = int(url.split("resultOffset=")[1].split("&")[0])
        page = [{"attributes": row} for row in rows[offset:]]
        return json_response({"features": page})

    return handler


def test_the_walks_written_here_name_this_project_to_the_publisher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An honest User-Agent is what lets an operator see who is calling their service."""
    features = [
        {"type": "Feature", "properties": {"OBJECTID": i}, "geometry": None}
        for i in range(1, 4)
    ]
    sent = install_recording(monkeypatch, _territory_handler([3, 3], features))
    acquire.acquire_territories(ELSE_IOU_POU, tmp_path)
    assert sent, "the acquisition made no request, so this test checked nothing"
    assert {identity for _url, identity in sent} == {acquire.USER_AGENT}
    assert "wildfire-service-territory-overlap" in acquire.USER_AGENT


def test_the_dins_walk_names_this_project_and_not_the_pinned_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The largest of the four layers now identifies as the caller.

    This test used to assert the opposite, and was right to. Until the pin moved to
    `3a6aa47`, `perimeter.acquire` read its User-Agent from a module constant inside a
    private helper and neither function this project calls accepted one, so every request
    of the DINS walk, both counts and each page, named the dependency instead of the
    caller: 132,522 records going out as `perimeter-coverage/0.1` while the other three
    layers carried this project's name. That was gap 1 in `docs/UPSTREAM.md`, recorded
    rather than claimed away.

    Its docstring said it would fail the day the pin moved onto a walk that lets a caller
    identify itself, and that it would be rewritten then. That is what happened, and the
    assertion is now the one the documents can make: an operator at CAL FIRE reading their
    logs sees a name that leads back here.
    """
    rows = [{"OBJECTID": i} for i in range(1, 3)]
    sent = install_recording(monkeypatch, _dins_handler(rows))
    acquire.acquire_dins(tmp_path)
    assert sent, "the acquisition made no request, so this test checked nothing"
    identities = {identity for _url, identity in sent}
    assert identities == {acquire.USER_AGENT}
    assert "wildfire-service-territory-overlap" in acquire.USER_AGENT
    assert PERIMETER_USER_AGENT not in identities
