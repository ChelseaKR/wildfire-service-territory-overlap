"""The offline build, and the gate behind the byte-identical claim.

`tools/determinism.sh` is run here against trees that should fail it, because a gate
nobody has watched fail is a gate that might not be able to.
"""

from __future__ import annotations

import importlib.metadata as metadata
import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from wildfire_service_territory_overlap import cli, sensitivity

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
SCRIPT = ROOT / "tools" / "determinism.sh"

_DROP_CO_OP = "inclusion_rule_dropping_the_cooperative.json"
_EXAMPLE = "inclusion_rule_example.json"


def build_into(out: Path) -> tuple[Path, Path]:
    return cli.build(
        dins_path=FIXTURES / "dins_sample.json",
        iou_pou_path=FIXTURES / "else_iou_pou_sample.geojson",
        other_path=FIXTURES / "else_other_sample.geojson",
        counties_path=FIXTURES / "county_boundaries_sample.geojson",
        out_dir=out,
        is_fixture=True,
    )


def run_gate(a: Path, b: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(SCRIPT), str(a), str(b)], capture_output=True, text=True, check=False
    )


def test_the_offline_build_writes_both_artifacts(tmp_path: Path) -> None:
    artifact, document = build_into(tmp_path / "out")
    assert artifact.exists() and document.exists()
    assert artifact.name == "measurements.json"
    assert document.name == "REPORT.md"


def test_a_fixture_build_is_marked_as_one(tmp_path: Path) -> None:
    import json

    artifact, _ = build_into(tmp_path / "out")
    assert json.loads(artifact.read_text(encoding="utf-8"))["is_fixture"] is True


def test_the_cli_returns_zero_and_names_what_it_wrote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(
        [
            "--fixture",
            "--dins",
            str(FIXTURES / "dins_sample.json"),
            "--iou-pou",
            str(FIXTURES / "else_iou_pou_sample.geojson"),
            "--other",
            str(FIXTURES / "else_other_sample.geojson"),
            "--counties",
            str(FIXTURES / "county_boundaries_sample.geojson"),
            "--out",
            str(tmp_path / "out"),
        ]
    )
    assert code == 0
    assert "measurements.json" in capsys.readouterr().out


def test_two_builds_of_the_same_inputs_are_byte_identical(tmp_path: Path) -> None:
    build_into(tmp_path / "one")
    build_into(tmp_path / "two")
    result = run_gate(tmp_path / "one", tmp_path / "two")
    assert result.returncode == 0, result.stderr


def test_the_gate_fails_on_trees_that_differ(tmp_path: Path) -> None:
    build_into(tmp_path / "one")
    build_into(tmp_path / "two")
    (tmp_path / "two" / "REPORT.md").write_text("edited", encoding="utf-8")
    assert run_gate(tmp_path / "one", tmp_path / "two").returncode == 1


def test_the_gate_refuses_an_empty_tree_rather_than_calling_it_a_match(
    tmp_path: Path,
) -> None:
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    assert run_gate(tmp_path / "one", tmp_path / "two").returncode == 2


def test_the_gate_refuses_a_missing_tree(tmp_path: Path) -> None:
    build_into(tmp_path / "one")
    assert run_gate(tmp_path / "one", tmp_path / "absent").returncode == 2


def test_the_gate_refuses_the_wrong_number_of_arguments() -> None:
    result = subprocess.run(  # noqa: S603
        [str(SCRIPT), "only-one"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert "usage" in result.stderr


def test_the_version_flag_prints_the_installed_version_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0
    printed = capsys.readouterr().out.strip()
    assert printed == f"{cli.DISTRIBUTION} {metadata.version(cli.DISTRIBUTION)}"


def test_the_version_cannot_drift_from_pyproject() -> None:
    """One source of truth, checked from both ends.

    `pyproject.toml` holds the version, hatchling copies it into the installed
    distribution metadata, and the flag reads it back from there. There is no second
    copy to drift, and these two assertions are what hold the chain together: the name
    the flag looks up has to be the name the project is packaged under, and the version
    that comes back has to be the one declared.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == cli.DISTRIBUTION
    assert metadata.version(cli.DISTRIBUTION) == config["project"]["version"]


def test_a_version_that_cannot_be_read_is_refused_rather_than_guessed(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not measured, on stderr, with a nonzero exit. Never a placeholder string."""

    def absent(_name: str) -> str:
        raise metadata.PackageNotFoundError(cli.DISTRIBUTION)

    monkeypatch.setattr(cli.metadata, "version", absent)
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == "", "a version that could not be read was printed anyway"
    assert "not measured" in captured.err
    assert "uv sync --locked" in captured.err


def test_a_build_never_asks_for_the_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The trap this flag was written around, held shut by a test.

    Resolving the version while the parser is built runs the lookup on every
    invocation. Here the lookup is rigged to fail outright, and a full fixture build
    still has to succeed, because a build has no business asking what version it is.
    """

    def never(_name: str) -> str:
        raise AssertionError("a build asked for the version")

    monkeypatch.setattr(cli.metadata, "version", never)
    code = cli.main(
        [
            "--fixture",
            "--dins",
            str(FIXTURES / "dins_sample.json"),
            "--iou-pou",
            str(FIXTURES / "else_iou_pou_sample.geojson"),
            "--other",
            str(FIXTURES / "else_other_sample.geojson"),
            "--counties",
            str(FIXTURES / "county_boundaries_sample.geojson"),
            "--out",
            str(tmp_path / "out"),
        ]
    )
    assert code == 0


# --- The reviewer-supplied inclusion rule, end to end -------------------------------


def cli_args(out: Path, *rules: Path) -> list[str]:
    args = [
        "--fixture",
        "--dins",
        str(FIXTURES / "dins_sample.json"),
        "--iou-pou",
        str(FIXTURES / "else_iou_pou_sample.geojson"),
        "--other",
        str(FIXTURES / "else_other_sample.geojson"),
        "--counties",
        str(FIXTURES / "county_boundaries_sample.geojson"),
        "--out",
        str(out),
    ]
    for rule in rules:
        args.extend(["--inclusion-rule", str(rule)])
    return args


def test_the_committed_fixture_rule_reproduces_the_built_without_co_op_row(
    tmp_path: Path,
) -> None:
    """The issue's control, run over the committed fixture layers by the real CLI.

    `fixtures/inclusion_rule_dropping_the_cooperative.json` names exactly the types the
    fixture layer carries once the cooperative is dropped, so its row has to come out
    identical to the built "without CO-OP" row. A supplied path with its own filter,
    its own denominator or its own baseline fails here.
    """
    out = tmp_path / "out"
    assert cli.main(cli_args(out, FIXTURES / _DROP_CO_OP)) == 0
    variants = json.loads((out / "measurements.json").read_text(encoding="utf-8"))[
        "sensitivity"
    ]["type_inclusion"]["variants"]
    rows = {row["variant"]: row for row in variants}
    built = rows["without CO-OP"]
    supplied = rows["without CO-OP, as supplied by a reviewer"]
    for key in (
        "counts",
        "contested",
        "placed",
        "uncovered",
        "territories_indexed",
        "contested_difference_from_the_rule_as_built",
    ):
        assert supplied[key] == built[key], key
    # Pinned against the literal the fixture geography produces, because two rows that
    # both measured nothing would also be equal.
    assert built["counts"] == {
        "placed_in_exactly_one_territory": 5,
        "contested_between_two_or_more": 3,
        "covered_by_no_published_territory": 2,
        "coordinate_not_usable": 2,
    }


def test_a_supplied_rule_reaches_both_artifacts_with_its_role_and_date(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    assert cli.main(cli_args(out, FIXTURES / _EXAMPLE)) == 0
    tree = json.loads((out / "measurements.json").read_text(encoding="utf-8"))
    row = tree["sensitivity"]["type_inclusion"]["variants"][-1]
    assert row["rule_file"] == _EXAMPLE
    assert row["supplied_by_a_reviewer"] is True
    document = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "### Rules supplied by a reviewer" in document
    assert row["reviewer_role"] in document
    assert row["reviewed_on"] in document
    assert f"`{_EXAMPLE}`" in document
    assert row["outline_overrides"], "the example fixture declares no override"
    for outline, override in row["outline_overrides"].items():
        assert outline in document
        assert override["reviewer_reason"] in document


def test_a_build_given_no_rule_file_writes_the_document_it_always_wrote(
    tmp_path: Path,
) -> None:
    """The flag existing must not move a published byte."""
    plain = tmp_path / "plain"
    assert cli.main(cli_args(plain)) == 0
    document = (plain / "REPORT.md").read_text(encoding="utf-8")
    assert "supplied by a reviewer" not in document
    tree = json.loads((plain / "measurements.json").read_text(encoding="utf-8"))
    for row in tree["sensitivity"]["type_inclusion"]["variants"]:
        assert "supplied_by_a_reviewer" not in row


def test_two_builds_given_the_same_rule_files_are_byte_identical(
    tmp_path: Path,
) -> None:
    rules = (FIXTURES / _EXAMPLE, FIXTURES / _DROP_CO_OP)
    assert cli.main(cli_args(tmp_path / "one", *rules)) == 0
    # The same two files in the other order: the artifact is keyed on the filenames,
    # not on the order they were typed.
    assert cli.main(cli_args(tmp_path / "two", *reversed(rules))) == 0
    assert run_gate(tmp_path / "one", tmp_path / "two").returncode == 0


def test_a_rule_naming_an_outline_the_retrieval_lacks_exits_two_before_placing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refused before any placement runs, and nothing at all is written.

    The empty output directory is the load-bearing assertion. A refusal raised after
    the pipeline had run would still exit 2 and still name the outline, and it would
    have spent the whole placement to say so.
    """
    rule = tmp_path / "renamed.json"
    rule.write_text(
        json.dumps(
            {
                "variant": "a reading written against an older retrieval",
                "reviewer_role": "Distribution planning engineer",
                "reviewed_on": "2026-09-06",
                "types_read_as_territories": ["IOU"],
                "outline_overrides": {
                    "Epsilon Withdrawn Utility": {
                        "read_as_a_territory": False,
                        "reason": "Named in a retrieval this build is not measuring.",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert cli.main(cli_args(out, rule)) == 2
    captured = capsys.readouterr()
    assert captured.out == "", "a refused build printed as though it had written"
    assert "Epsilon Withdrawn Utility" in captured.err
    assert "renamed.json" in captured.err
    assert not out.exists(), "a refused build wrote an artifact anyway"


def test_a_rule_naming_a_type_the_retrieval_lacks_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rule = tmp_path / "admin.json"
    rule.write_text(
        json.dumps(
            {
                "variant": "with ADMIN read as a territory, supplied",
                "reviewer_role": "Distribution planning engineer",
                "reviewed_on": "2026-09-06",
                "types_read_as_territories": ["ADMIN", "IOU"],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert cli.main(cli_args(out, rule)) == 2
    assert "ADMIN" in capsys.readouterr().err
    assert not out.exists()


def test_a_rule_file_that_cannot_be_read_exits_two_before_anything_is_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rule = tmp_path / "typo.json"
    rule.write_text(
        json.dumps(
            {
                "variant": "a reading",
                "reviewer_role": "Distribution planning engineer",
                "reviewed_on": "2026-09-06",
                "types": ["IOU"],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    assert cli.main(cli_args(out, rule)) == 2
    captured = capsys.readouterr()
    assert "typo.json" in captured.err
    assert "types" in captured.err
    assert not out.exists()


def test_the_two_committed_rule_fixtures_are_documented_and_readable() -> None:
    """A committed fixture nobody documented is a file the next reader has to guess at."""
    readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
    for name in (_DROP_CO_OP, _EXAMPLE):
        rule = sensitivity.read_rule_file(FIXTURES / name)
        assert rule.file_name == name
        assert name in readme
