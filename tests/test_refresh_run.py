"""What `refresh --run` does, and every step at which it refuses to do the next one.

`--check` answers whether the pin has gone stale. This is the other half: acquire, build,
compare, and stop. The tests below are mostly about the stopping.

The thing that would make this command worse than the eight numbered steps it replaces is
a receipt written for a run that did not finish. A receipt is the document a later reader
treats as the record of a refresh, so one that exists after a refused step is a record of
something that did not happen, and it is indistinguishable from a record of something that
did. Every refusal below asserts the absence of the receipt as well as the exit code.

Nothing here opens a socket. The acquisition runs for real -- `acquire_all`, its three
guards, and the writer -- with only `perimeter`'s three readers substituted, so the walk
that is checked is the walk that ships. The clock, the collaborators and the version
lookup are all parameters whose defaults are resolved at call time, and the tests that
omit one are exercising the shipped path for it.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from perimeter.acquire import AcquisitionBlocked

from wildfire_service_territory_overlap import acquire as acquire_module
from wildfire_service_territory_overlap import artifact_diff
from wildfire_service_territory_overlap import refresh as refresh_module
from wildfire_service_territory_overlap.acquire import Acquired
from wildfire_service_territory_overlap.artifacts import PublicationRefused
from wildfire_service_territory_overlap.refresh import (
    ALL_SOURCES,
    BUILD_DIR_NAME,
    EXIT_REFRESH_DONE,
    EXIT_REFRESH_REFUSED,
    EXIT_REFRESH_UNREADABLE,
    RECEIPT_NAME,
    STEP_ACQUIRE,
    STEP_BUILD,
    STEP_COMPARE,
    STEP_WORKDIR,
    RefreshRefused,
    main,
    run,
    tool_identity,
    write_receipt,
)
from wildfire_service_territory_overlap.sources import COUNTIES, DINS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

#: Which committed sample file stands in for which pinned layer. The sample files are the
#: ones `make report-offline` already builds from, so a run over them exercises the real
#: measurement rather than a shape invented for this file.
SAMPLES: dict[str, str] = {
    "dins_postfire": "dins_sample.json",
    "else_iou_pou": "else_iou_pou_sample.geojson",
    "else_other": "else_other_sample.geojson",
    "county_boundaries": "county_boundaries_sample.geojson",
}


def _sample_rows(source_key: str) -> list[dict[str, Any]]:
    payload = json.loads((FIXTURES / SAMPLES[source_key]).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return sorted(payload, key=lambda row: int(row["OBJECTID"]))
    features: list[dict[str, Any]] = payload["features"]
    return sorted(features, key=lambda f: int(f["properties"]["OBJECTID"]))


def _source_for(endpoint: str) -> str:
    for source in ALL_SOURCES:
        if source.endpoint == endpoint:
            return source.key
    raise AssertionError(f"the acquisition asked for {endpoint}, which is no source")


@pytest.fixture
def served_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitute `perimeter`'s three readers, and nothing else in the acquisition.

    `acquire_all`, `assert_walk_is_whole`, the before-and-after count comparison and the
    writer all run for real. A fake that stood in for `acquire_all` itself would leave the
    three guards this project layers on top of upstream's walk untested from here, which
    is the half of the acquisition that is this repository's own.
    """

    def count(endpoint: str, **_: object) -> int:
        return len(_sample_rows(_source_for(endpoint)))

    def rows(endpoint: str, _fields: object, **_kwargs: object) -> list[dict[str, Any]]:
        return _sample_rows(_source_for(endpoint))

    def features(
        endpoint: str, _fields: object, **_kwargs: object
    ) -> Iterator[dict[str, Any]]:
        yield from _sample_rows(_source_for(endpoint))

    monkeypatch.setattr(acquire_module, "perimeter_layer_record_count", count)
    monkeypatch.setattr(acquire_module, "perimeter_fetch_layer", rows)
    monkeypatch.setattr(acquire_module, "perimeter_iter_features", features)


@pytest.fixture
def published(tmp_path: Path, served_fixtures: None) -> Path:
    """An artifact to compare against: one built from the same fixtures, set aside.

    Built through the command rather than copied from `published/`, so a comparison in
    this file is between two artifacts of the same shape and any difference a test sees
    is the one it introduced. `published/measurements.json` is never read here and never
    written; a test that compared against it would go red on every deliberate refresh.
    """
    baseline = tmp_path / "baseline"
    result = run(workdir=baseline, published=_seeded(tmp_path), today=_TODAY)
    return baseline / result.artifact


def _seeded(tmp_path: Path) -> Path:
    """A stand-in published artifact for the very first build, which has nothing to diff.

    It carries one leaf so `compared_nothing` is not reached; the run that uses it is
    only ever the one that produces the baseline above.
    """
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"is_fixture": True}), encoding="utf-8")
    return path


_TODAY = date.fromisoformat("2026-09-09")


def _run(tmp_path: Path, published: Path, **kwargs: Any) -> Any:
    return run(
        workdir=tmp_path / "refresh", published=published, today=_TODAY, **kwargs
    )


# --- a run that finishes -------------------------------------------------------------


def test_a_run_over_the_fixtures_completes_and_writes_a_receipt(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    workdir = tmp_path / "refresh"
    result = _run(tmp_path, published)
    receipt_path = write_receipt(result, workdir)

    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["kind"] == "refresh-receipt"
    assert receipt["as_of"] == "2026-09-09"
    assert (workdir / result.artifact).exists()
    assert (workdir / result.report).exists()


def test_the_receipts_diff_summary_is_what_artifact_diff_prints_by_hand(
    tmp_path: Path, published: Path, served_fixtures: None, capsys: Any
) -> None:
    """The receipt must not paraphrase the comparison; it must carry it.

    A summary computed a second way is a second implementation of the diff, and the two
    would agree right up until the day they did not. So the receipt's block is asserted
    against what `python -m ...artifact_diff old new --json` prints, which is the
    comparison a person runs by hand and the thing this command exists to stop them
    skipping.

    The baseline is deliberately moved in all three directions first. Two artifacts built
    from the same fixtures are byte-identical, so a comparison between them has empty
    `added`, `removed` and `changed` lists, and asserting three empty lists against three
    empty lists would hold over a receipt that carried no comparison at all.
    """
    moved = tmp_path / "moved.json"
    tree = json.loads(published.read_text(encoding="utf-8"))
    tree["a_measurement_this_refresh_no_longer_makes"] = 1
    tree["representativeness"] = {}
    tree["provenance"]["dins_retrieved"] = "1999-01-01"
    moved.write_text(json.dumps(tree), encoding="utf-8")

    workdir = tmp_path / "refresh"
    result = _run(tmp_path, moved, allow_removals=True)
    receipt = json.loads(write_receipt(result, workdir).read_text(encoding="utf-8"))

    assert receipt["diff"]["counts"]["removed"] >= 1
    assert receipt["diff"]["counts"]["added"] >= 1
    assert receipt["diff"]["counts"]["changed"] >= 1

    capsys.readouterr()
    exit_code = artifact_diff.main(
        [
            str(moved),
            str(workdir / result.artifact),
            "--json",
            "--allow-removals",
        ]
    )
    by_hand = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert receipt["diff"] == by_hand


def test_the_run_builds_the_real_retrieval_and_not_a_fixture(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """`is_fixture` travels inside the artifact, and a refresh builds the real one.

    A refresh that produced an artifact flagged as a fixture would be a refresh whose
    output can never be adopted. The flag is set by the mode rather than passed in, so
    this is the assertion that the mode sets it.
    """
    result = _run(tmp_path, published)
    built = json.loads(
        (tmp_path / "refresh" / result.artifact).read_text(encoding="utf-8")
    )
    assert built["is_fixture"] is False


def test_the_receipt_records_every_retrieval_beside_the_pin_it_disagrees_with(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """The sample layers are not the pinned ones, and the receipt has to say so.

    Disagreement is an observation and never a refusal: a refresh happens because the
    publisher moved. What the receipt owes a reader is the three facts that identify a
    retrieval -- count, bytes, hash -- against the three the pin records, so the
    `sources.py` edit can be made from the receipt.
    """
    result = _run(tmp_path, published)
    receipt = result.to_dict()

    assert [item["source"] for item in receipt["retrievals"]] == [
        source.key for source in ALL_SOURCES
    ]
    for item in receipt["retrievals"]:
        assert item["matches_pin"] is False
        assert item["feature_count"] != item["pinned"]["feature_count"]
        assert item["sha256"] != item["pinned"]["sha256"]
        assert len(item["sha256"]) == 64


def test_a_retrieval_identical_to_the_pin_is_reported_as_matching(
    tmp_path: Path, published: Path
) -> None:
    """The other side of the boundary, so `matches_pin` is not a constant False."""

    def acquire(out_dir: Path) -> tuple[Acquired, ...]:
        out_dir.mkdir(parents=True, exist_ok=True)
        return tuple(
            Acquired(
                source_key=source.key,
                path=out_dir / source.raw_file,
                feature_count=source.feature_count,
                raw_bytes=source.raw_bytes,
                sha256=source.sha256,
                retrieved=source.retrieved,
                endpoint=source.endpoint,
            )
            for source in ALL_SOURCES
        )

    def build(**kwargs: Any) -> tuple[Path, Path]:
        out_dir = Path(kwargs["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = out_dir / "measurements.json"
        artifact.write_text(published.read_text(encoding="utf-8"), encoding="utf-8")
        report = out_dir / "REPORT.md"
        report.write_text("# report\n", encoding="utf-8")
        return artifact, report

    result = _run(tmp_path, published, acquire=acquire, build=build)
    assert all(item.matches_pin for item in result.retrievals)
    assert result.diff.added == [] and result.diff.removed == []
    assert result.diff.changed == []


def test_the_run_reads_published_and_never_writes_it(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """Adoption is a person's. The command has to leave the published artifact alone."""
    before = published.read_bytes()
    _run(tmp_path, published)
    assert published.read_bytes() == before


def test_the_receipt_says_plainly_that_nothing_was_adopted(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    receipt = _run(tmp_path, published).to_dict()
    assert receipt["adopted"] is False
    assert receipt["adoption"], (
        "a receipt with no next step is a receipt nobody can act on"
    )
    assert any("sources.py" in step for step in receipt["adoption"])


# --- every step at which it refuses --------------------------------------------------


def test_a_short_walk_aborts_before_the_build_and_leaves_no_receipt(
    tmp_path: Path, published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal the acquisition guards exist for, reached through this command.

    A walk that collected fewer rows than the layer reports is a dataset with a hole in
    it that nothing downstream can see, so the run stops before a build exists. The
    absence of the build directory is asserted rather than the absence of an artifact:
    a directory that was created and then failed to fill is the state a later reader
    would mistake for a build.
    """

    def short_count(endpoint: str, **_: object) -> int:
        return len(_sample_rows(_source_for(endpoint))) + 1

    def rows(endpoint: str, _fields: object, **_kwargs: object) -> list[dict[str, Any]]:
        return _sample_rows(_source_for(endpoint))

    def features(
        endpoint: str, _fields: object, **_kwargs: object
    ) -> Iterator[dict[str, Any]]:
        yield from _sample_rows(_source_for(endpoint))

    monkeypatch.setattr(acquire_module, "perimeter_layer_record_count", short_count)
    monkeypatch.setattr(acquire_module, "perimeter_fetch_layer", rows)
    monkeypatch.setattr(acquire_module, "perimeter_iter_features", features)

    workdir = tmp_path / "refresh"
    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, published)

    assert refusal.value.step == STEP_ACQUIRE
    assert refusal.value.exit_code == EXIT_REFRESH_REFUSED
    assert not (workdir / BUILD_DIR_NAME).exists()
    assert not (workdir / RECEIPT_NAME).exists()


def test_a_blocked_publisher_aborts_before_the_build(
    tmp_path: Path, published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 401, 403 or 429 is the publisher declining, and it is not routed around."""

    def blocked(endpoint: str, **_: object) -> int:
        raise AcquisitionBlocked("429 Too Many Requests")

    monkeypatch.setattr(acquire_module, "perimeter_layer_record_count", blocked)

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, published)
    assert refusal.value.step == STEP_ACQUIRE
    assert "429" in refusal.value.detail
    assert not (tmp_path / "refresh" / BUILD_DIR_NAME).exists()


def test_a_build_that_cannot_read_the_acquisition_refuses_rather_than_tracebacks(
    tmp_path: Path, published: Path
) -> None:
    """An acquisition that returned without writing its files is still a refusal.

    The build is the shipped one here, so what is exercised is the real reader meeting a
    directory that has no layers in it. A traceback out of this command would read as a
    bug in the tool rather than as a refresh that did not happen, and the two need
    different things from whoever is standing there.
    """

    def acquire(out_dir: Path) -> tuple[Acquired, ...]:
        out_dir.mkdir(parents=True, exist_ok=True)
        return ()

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, published, acquire=acquire)
    assert refusal.value.step == STEP_BUILD
    assert "could not read what the acquisition wrote" in refusal.value.detail
    assert not (tmp_path / "refresh" / RECEIPT_NAME).exists()


def test_a_build_that_refuses_publication_writes_no_receipt(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """A publication rule caught the artifact, so there is nothing to compare."""

    def build(**_: Any) -> tuple[Path, Path]:
        raise PublicationRefused("$.territories: rows are not in name order")

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, published, build=build)
    assert refusal.value.step == STEP_BUILD
    assert "name order" in refusal.value.detail
    assert not (tmp_path / "refresh" / RECEIPT_NAME).exists()


def test_a_removed_value_refuses_and_carries_the_diff_out_with_it(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """The refusal this whole command exists to make unskippable.

    A published value that the refresh no longer produces is the failure mode the README
    names, and the run stops rather than writing a receipt somebody could read as a
    successful refresh. The diff travels on the refusal so that finding out what was
    removed does not require re-running with the flag that accepts removals.
    """
    widened = tmp_path / "widened.json"
    tree = json.loads(published.read_text(encoding="utf-8"))
    tree["a_measurement_this_refresh_no_longer_makes"] = 1
    widened.write_text(json.dumps(tree), encoding="utf-8")

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, widened)

    assert refusal.value.step == STEP_COMPARE
    assert refusal.value.exit_code == EXIT_REFRESH_REFUSED
    assert refusal.value.diff is not None
    assert [leaf.path for leaf in refusal.value.diff.removed] == [
        "$.a_measurement_this_refresh_no_longer_makes"
    ]
    assert not (tmp_path / "refresh" / RECEIPT_NAME).exists()


def test_the_same_run_finishes_once_the_removal_is_named_deliberate(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """`--allow-removals` is recorded in the receipt beside `refused`.

    Without both, a receipt saying `refused: false` over a run that removed values reads
    as a run that removed none.
    """
    widened = tmp_path / "widened.json"
    tree = json.loads(published.read_text(encoding="utf-8"))
    tree["a_measurement_this_refresh_no_longer_makes"] = 1
    widened.write_text(json.dumps(tree), encoding="utf-8")

    result = _run(tmp_path, widened, allow_removals=True)
    receipt = result.to_dict()
    assert receipt["diff"]["allow_removals"] is True
    assert receipt["diff"]["refused"] is False
    assert receipt["diff"]["counts"]["removed"] == 1


def test_a_workdir_that_already_holds_a_run_is_refused_rather_than_emptied(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """Two acquisitions in one directory measure a mixture and nothing says so.

    Deleting the previous one is the single irreversible act available here, so it is
    the person's rather than the command's.
    """
    workdir = tmp_path / "refresh"
    (workdir / "raw").mkdir(parents=True)

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, published)
    assert refusal.value.step == STEP_WORKDIR
    assert not (workdir / RECEIPT_NAME).exists()


# --- the comparison that did not happen, which is not a clean comparison -------------


def test_an_unreadable_published_artifact_does_not_exit_like_a_refused_refresh(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, tmp_path / "there-is-no-such-file.json")
    assert refusal.value.step == STEP_COMPARE
    assert refusal.value.exit_code == EXIT_REFRESH_UNREADABLE
    assert refusal.value.exit_code != EXIT_REFRESH_REFUSED


def test_a_published_artifact_that_is_not_an_object_is_unreadable_rather_than_clean(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    """Two nulls pair as one leaf that equals itself and print a clean verdict."""
    not_an_artifact = tmp_path / "null.json"
    not_an_artifact.write_text("null", encoding="utf-8")

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, not_an_artifact)
    assert refusal.value.exit_code == EXIT_REFRESH_UNREADABLE
    assert "did not finish being built" in refusal.value.detail


def test_a_published_artifact_that_is_not_json_is_unreadable(
    tmp_path: Path, published: Path, served_fixtures: None
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, broken)
    assert refusal.value.exit_code == EXIT_REFRESH_UNREADABLE


def test_a_comparison_of_two_empty_artifacts_is_not_a_clean_refresh(
    tmp_path: Path, published: Path
) -> None:
    """`compared_nothing` reached through this command rather than only through the CLI.

    Two artifacts with nothing in them agree about nothing. That is not the fact "no
    published value moved", and the two must not share an exit code.
    """
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")

    def acquire(out_dir: Path) -> tuple[Acquired, ...]:
        out_dir.mkdir(parents=True, exist_ok=True)
        return ()

    def build(**kwargs: Any) -> tuple[Path, Path]:
        out_dir = Path(kwargs["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = out_dir / "measurements.json"
        artifact.write_text("{}", encoding="utf-8")
        report = out_dir / "REPORT.md"
        report.write_text("", encoding="utf-8")
        return artifact, report

    with pytest.raises(RefreshRefused) as refusal:
        _run(tmp_path, empty, acquire=acquire, build=build)
    assert refusal.value.exit_code == EXIT_REFRESH_UNREADABLE
    assert "no value was compared" in refusal.value.detail


# --- the defaults, driven rather than read -------------------------------------------


def test_omitting_the_acquisition_reaches_the_shared_one_and_not_a_second_list(
    tmp_path: Path, published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A default that is accepted and never reached looks exactly like one that works.

    Every other test here passes its own acquisition, so nothing else would notice if
    this line stopped naming `acquire.acquire_all` -- which is the one list of layers,
    and the reason a layer cannot be added to the command line and forgotten here.
    """
    called: list[Path] = []

    def spy(out_dir: Path) -> tuple[Acquired, ...]:
        called.append(out_dir)
        raise AcquisitionBlocked("stop here; reaching this is the whole assertion")

    monkeypatch.setattr(refresh_module, "acquire_all", spy)
    with pytest.raises(RefreshRefused):
        _run(tmp_path, published)
    assert called == [tmp_path / "refresh" / "raw"]


def test_omitting_the_build_reaches_the_shared_pipeline(
    tmp_path: Path, published: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same, for the build: it must be `cli.build` and not a second pipeline."""
    called: list[dict[str, Any]] = []

    def spy(**kwargs: Any) -> tuple[Path, Path]:
        called.append(kwargs)
        raise PublicationRefused("stop here")

    monkeypatch.setattr(refresh_module.cli, "build", spy)

    def acquire(out_dir: Path) -> tuple[Acquired, ...]:
        out_dir.mkdir(parents=True, exist_ok=True)
        return ()

    with pytest.raises(RefreshRefused):
        _run(tmp_path, published, acquire=acquire)
    assert len(called) == 1
    assert called[0]["is_fixture"] is False
    assert called[0]["dins_path"].name == DINS.raw_file
    assert called[0]["counties_path"].name == COUNTIES.raw_file


def test_a_version_that_cannot_be_read_is_not_measured_rather_than_guessed() -> None:
    """The receipt says which build produced it, or says that it does not know.

    Reporting the version the repository declares would be a guess about the code that
    ran, and a receipt is read a year later by somebody who cannot check.
    """
    import importlib.metadata as metadata

    def absent(_name: str) -> str:
        raise metadata.PackageNotFoundError

    identity = tool_identity(absent)
    assert identity["version"] is None
    assert "not recorded" in identity["detail"]

    measured = tool_identity(lambda _name: "0.1.0")
    assert measured["version"] == "0.1.0"
    assert "detail" not in measured


def test_the_shipped_version_lookup_is_reached_when_the_parameter_is_omitted() -> None:
    identity = tool_identity()
    assert identity["distribution"] == "wildfire-service-territory-overlap"
    assert identity["version"] is not None, (
        "the suite runs against an installed distribution, so this is the shipped path"
    )


# --- the command line ----------------------------------------------------------------


def test_the_command_line_completes_a_run_and_prints_where_the_receipt_is(
    tmp_path: Path,
    published: Path,
    served_fixtures: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workdir = tmp_path / "cli-run"
    code = main(["--run", "--workdir", str(workdir), "--published", str(published)])
    printed = capsys.readouterr().out
    assert code == EXIT_REFRESH_DONE
    assert (workdir / RECEIPT_NAME).exists()
    assert "Nothing was adopted" in printed
    assert str(workdir / RECEIPT_NAME) in printed


def test_the_command_line_prints_the_removed_values_it_refused_over(
    tmp_path: Path,
    published: Path,
    served_fixtures: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    widened = tmp_path / "widened.json"
    tree = json.loads(published.read_text(encoding="utf-8"))
    tree["a_measurement_this_refresh_no_longer_makes"] = 1
    widened.write_text(json.dumps(tree), encoding="utf-8")

    workdir = tmp_path / "cli-refused"
    code = main(["--run", "--workdir", str(workdir), "--published", str(widened)])
    captured = capsys.readouterr()
    assert code == EXIT_REFRESH_REFUSED
    assert "a_measurement_this_refresh_no_longer_makes" in captured.out
    assert "refresh refused at compare" in captured.err
    assert not (workdir / RECEIPT_NAME).exists()


def test_a_refusal_with_no_diff_to_show_prints_only_the_refusal(
    tmp_path: Path,
    published: Path,
    served_fixtures: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Only the comparison carries a diff out with it; the other steps have none.

    The alternative would be an empty diff printed for every refusal, which is a
    comparison that did not happen wearing the report of one that found nothing.
    """
    workdir = tmp_path / "occupied"
    (workdir / "raw").mkdir(parents=True)

    code = main(["--run", "--workdir", str(workdir), "--published", str(published)])
    captured = capsys.readouterr()
    assert code == EXIT_REFRESH_REFUSED
    assert captured.out == ""
    assert "refresh refused at workdir" in captured.err


def test_the_command_line_run_mode_requires_a_workdir(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A default acquisition directory is a surprise nobody asked for."""
    with pytest.raises(SystemExit):
        main(["--run"])
    assert "--workdir" in capsys.readouterr().err


def test_the_two_modes_are_exclusive_and_one_is_required(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main([])
    assert "--check" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--check", "--run", "--workdir", "unused"])
    assert "not allowed with" in capsys.readouterr().err


def test_the_json_mode_prints_the_receipt_it_wrote(
    tmp_path: Path,
    published: Path,
    served_fixtures: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workdir = tmp_path / "cli-json"
    code = main(
        [
            "--run",
            "--workdir",
            str(workdir),
            "--published",
            str(published),
            "--json",
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    assert code == EXIT_REFRESH_DONE
    assert printed == json.loads((workdir / RECEIPT_NAME).read_text(encoding="utf-8"))


def test_the_acquisition_list_is_the_one_the_command_line_uses(tmp_path: Path) -> None:
    """One list of layers, so a fifth cannot be added to one caller and not the other."""
    import inspect

    source = inspect.getsource(acquire_module.main)
    assert "acquire_all(" in source, (
        "the acquisition command line no longer calls the shared list, so a layer added "
        "to one is missing from the other and the build reads a stale file"
    )
    assert [
        name
        for name in ("acquire_dins(", "acquire_territories(", "acquire_counties(")
        if name in source
    ] == []
