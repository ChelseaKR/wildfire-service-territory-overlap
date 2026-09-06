"""The documents that make claims about the repository, checked against the repository.

PROVENANCE.md restates `sources.py` for a reader. A README table states what is true of
the engineering. Both drift the moment nothing reads them.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from wildfire_service_territory_overlap.acquire import DINS_FIELDS
from wildfire_service_territory_overlap.artifacts import (
    BY_NAME,
    ORDERINGS,
    check_document,
    table_cells,
)
from wildfire_service_territory_overlap.sources import RETRIEVED, SOURCES, WIRES_TYPES

ROOT = Path(__file__).resolve().parents[1]
# Written as escapes so this file does not itself contain what it forbids.
DASHES = ("\u2014", "\u2013")
PROVENANCE = (ROOT / "PROVENANCE.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
CONTRIBUTING = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
ROADMAP = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
UPSTREAM = (ROOT / "docs" / "UPSTREAM.md").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def test_every_source_appears_in_provenance_with_its_hash() -> None:
    for source in SOURCES:
        assert source.title in PROVENANCE, source.key
        assert source.sha256 in PROVENANCE, source.key
        assert str(source.raw_bytes) in PROVENANCE, source.key
        assert str(source.feature_count) in PROVENANCE, source.key


def test_no_source_carries_a_placeholder_hash() -> None:
    for source in SOURCES:
        assert len(source.sha256) == 64, f"{source.key} has no hash recorded"
        assert source.raw_bytes > 0, f"{source.key} has no byte count recorded"


def test_the_retrieval_date_is_the_same_everywhere() -> None:
    assert RETRIEVED in PROVENANCE
    assert RETRIEVED in README
    for source in SOURCES:
        assert source.retrieved == RETRIEVED


def test_every_publisher_caveat_names_what_was_built_from_it() -> None:
    for source in SOURCES:
        assert source.caveats, f"{source.key} quotes no published limitation"
        for caveat in source.caveats:
            assert len(caveat.quote) > 40
            assert len(caveat.measured_as) > 60, (
                f"{source.key}/{caveat.topic} quotes a caveat without saying what was "
                "measured from it"
            )


def test_provenance_names_the_fields_that_are_never_fetched() -> None:
    for field in ("SITEADDRESS", "APN", "ASSESSEDIMPROVEDVALUE"):
        assert field in PROVENANCE


def test_provenance_names_every_field_that_is_fetched() -> None:
    """A column added to the retrieval and not to the document is undisclosed collection."""
    for field in DINS_FIELDS:
        assert field in PROVENANCE, field


def test_the_wires_types_are_the_ones_the_adr_argues_for() -> None:
    assert set(WIRES_TYPES) == {"IOU", "POU", "CO-OP", "Tribal"}
    adr = (ROOT / "docs" / "adr").glob("0002-*.md")
    text = next(adr).read_text(encoding="utf-8")
    for kind in ("CCA", "ADMIN"):
        assert kind in text


def test_the_readme_disclaims_affiliation_before_anything_else() -> None:
    head = README.split("## ")[0]
    assert "Not affiliated with, endorsed by, or approved by CAL FIRE" in head
    assert "SMUD" in head
    assert "any electric utility" in head


def test_the_readme_has_a_visitor_first_quickstart_near_the_top() -> None:
    first_sixty = "\n".join(README.splitlines()[:60])
    assert "make verify" in first_sixty
    assert "uv sync --locked" in first_sixty


def test_the_readme_never_claims_users_adopters_or_downloads() -> None:
    lowered = README.lower()
    for phrase in (
        "users",
        "adopters",
        "downloads",
        "in production",
        "widely used",
        "trusted by",
    ):
        assert phrase not in lowered, f"the README says {phrase!r}"


# Directories that hold no authored prose: the virtualenv, build output, caches, and
# the raw retrievals, which are not in git at all.
DASH_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "data",
        "dist",
        "node_modules",
    }
)
DASH_SUFFIXES = frozenset(
    {
        ".cff",
        ".cfg",
        ".geojson",
        ".ini",
        ".json",
        ".md",
        ".py",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
DASH_NAMED = frozenset({"Makefile", "CODEOWNERS", "allowed_signers"})


def authored_files() -> list[Path]:
    """Every authored text file in the repository, wherever it lives.

    The rule is stated as repository wide, so the check has to be. The previous version
    globbed root markdown, `docs/`, `published/`, `src/` and `tests/`, which left
    `.github/`, the `Makefile`, `tools/`, `fixtures/` and `CITATION.cff` unread by the
    one gate that enforces the writing rule over them.
    """
    found: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(ROOT).parts
        if any(part in DASH_SKIP_DIRS for part in parts):
            continue
        if path.suffix in DASH_SUFFIXES or path.name in DASH_NAMED:
            found.append(path)
    return sorted(found)


def test_no_file_in_the_repository_uses_an_em_or_en_dash() -> None:
    for path in authored_files():
        text = path.read_text(encoding="utf-8")
        for dash in DASHES:
            assert dash not in text, f"{path.relative_to(ROOT)} contains {dash!r}"


def test_the_dash_check_reads_the_places_it_used_to_be_blind_to() -> None:
    """Guard the guard.

    Widening a check is worth nothing if the widening is nominal. Every path below sits
    outside the globs the previous version used, so each one going missing from this
    list is the check quietly narrowing back.
    """
    seen = {path.relative_to(ROOT).as_posix() for path in authored_files()}
    for previously_unread in (
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/dependabot.yml",
        ".github/codeql-accepted.json",
        ".github/CODEOWNERS",
        "Makefile",
        "tools/determinism.sh",
        "fixtures/README.md",
        "CITATION.cff",
        "pyproject.toml",
    ):
        assert previously_unread in seen, (
            f"{previously_unread} is outside the dash check again"
        )
    assert len(seen) > 60, "the sweep collapsed to a handful of files"


def test_the_standards_conformance_table_has_no_blank_state() -> None:
    section = README.split("## Standards conformance")[1]
    rows = [
        line
        for line in section.splitlines()
        if line.startswith("| ")
        and not line.startswith("| Standard")
        and "---" not in line
    ]
    assert len(rows) >= 14
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 2, row
        assert cells[1], f"{cells[0]} has no state recorded"
        assert cells[1].startswith(("Applies", "N/A")), row


def _conformance_section() -> str:
    """The conformance heading down to the next one, preamble and table together."""
    return README.split("## Standards conformance")[1].split("\n## ")[0]


def _refuse_a_table_older_than_the_rows_it_carries(section: str) -> None:
    """Raise if the table dates itself earlier than a date one of its rows records.

    Kept out of the test so the test that watches it refuse can call the same code the
    test that guards the README calls, rather than a re-implementation of it.
    """
    head, marker, body = section.partition("| Standard |")
    assert marker, "the conformance table's header row moved"
    stamp = re.search(r"as of (\d{4}-\d{2}-\d{2})", head)
    assert stamp, "the conformance table does not say what it is current as of"
    as_of = stamp.group(1)
    recorded = re.findall(r"\d{4}-\d{2}-\d{2}", body)
    assert recorded, "no row in the conformance table records a date"
    latest = max(recorded)
    if latest > as_of:
        raise AssertionError(
            f"the conformance table says it is current as of {as_of}, and a row "
            f"records {latest}"
        )


def test_the_conformance_table_is_not_older_than_the_rows_it_carries() -> None:
    """The line that says how to read every other claim was itself unread.

    The preamble said 2026-08-17 while the CI/CD row recorded a ruleset read back on
    2026-08-28, and later rows described gates added in September. That is the same
    shape of defect the CI/CD row was written to correct: a claim about the repository
    that stopped being true and went on being asserted.
    """
    _refuse_a_table_older_than_the_rows_it_carries(_conformance_section())


def test_the_conformance_date_check_can_actually_fire() -> None:
    """A gate nobody has watched refuse is not a gate.

    The check compares two dates that both come out of the same document, so it is
    exactly the kind that can be written in a way nothing can trip. This drives it.
    """
    stale = (
        "\n\nEvery row states what is true, as of 2026-08-17.\n\n"
        "| Standard | State |\n|---|---|\n"
        "| CI/CD | Applies: the ruleset was read back on 2026-08-28 |\n"
    )
    with pytest.raises(AssertionError, match="current as of 2026-08-17"):
        _refuse_a_table_older_than_the_rows_it_carries(stale)


def test_the_standards_version_is_pinned_and_read() -> None:
    pin = (ROOT / ".standards-version").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"v\d+\.\d+\.\d+", pin)
    assert pin in README


def test_the_changelog_has_an_unreleased_section_and_the_current_version() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert "## [Unreleased]" in CHANGELOG
    assert f"## [{version}]" in CHANGELOG


def test_the_package_and_citation_versions_agree() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"version: {version}" in citation


def test_the_coverage_floor_and_complexity_cap_are_declared() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 90
    assert config["tool"]["ruff"]["lint"]["mccabe"]["max-complexity"] <= 10
    assert config["project"]["requires-python"].startswith(">=3.1")


def test_the_dev_toolchain_declares_version_floors() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dev = " ".join(config["dependency-groups"]["dev"])
    assert "ruff>=" in dev
    assert "mypy>=" in dev


# --- The two mypy overrides, held against the packages they name -------------------


def test_every_untyped_import_override_names_a_package_that_is_actually_untyped() -> (
    None
):
    """An override that cannot fail is a rule nobody is following.

    `pyproj.*` sat in this list until 2026-09-05 under a comment saying none of the
    three dependencies shipped type information. pyproj 3.7.2 ships `py.typed`, so the
    entry silenced nothing and `mypy --strict src` passes without it. The list is read
    back against the installed packages here so the next entry cannot go quiet the same
    way, and so the day `perimeter` ships the marker this fails rather than leaving a
    workaround in place for nobody's benefit.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    overrides = [
        override
        for override in config["tool"]["mypy"]["overrides"]
        if override.get("ignore_missing_imports")
    ]
    modules = [module for override in overrides for module in override["module"]]
    assert modules, "nothing ignores a missing import, so this test checks nothing"
    for pattern in modules:
        name = pattern.removesuffix(".*")
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            continue  # not importable at all, which is what the override is for
        assert not (Path(spec.origin).parent / "py.typed").exists(), (
            f"{name} ships py.typed, so ignoring its missing imports is inert. Drop "
            "the entry and read the types it publishes."
        )


def test_the_upstream_audit_names_the_commit_this_project_pins() -> None:
    """A dated audit against a moved pin is a dated audit of something else.

    `docs/UPSTREAM.md` records what `perimeter` did at one commit and what this
    repository does to compensate. If the pin moves and the audit does not, every gap in
    it is a claim about code this project no longer runs.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pinned = next(
        line
        for line in config["project"]["dependencies"]
        if line.startswith("perimeter @")
    )
    commit = pinned.rsplit("@", 1)[1]
    assert len(commit) == 40, f"the pin is not a full commit: {commit}"
    assert commit in UPSTREAM, (
        "docs/UPSTREAM.md was written against a different commit than pyproject.toml "
        "pins. Re-audit against the new pin, or say in the document that it was not "
        "re-run."
    )


def test_provenance_does_not_still_make_the_unqualified_user_agent_claim() -> None:
    """The claim the upstream audit of 2026-09-05 found false.

    Three of the four layers carry a User-Agent naming this project. The DINS walk is
    `perimeter`'s and carries `perimeter`'s, and this document said all of them named
    this project. `tests/test_acquire.py` holds both halves of the corrected sentence
    against the code that sends them.
    """
    assert "Requests carry a User-Agent naming this project" not in PROVENANCE
    assert "perimeter-coverage/0.1" in PROVENANCE
    assert "docs/UPSTREAM.md" in PROVENANCE


# Every gate `make verify` runs, in order. CI runs `make verify` and nothing else, so
# this list is the gate list for the whole repository.
VERIFY_GATES: tuple[str, ...] = (
    "lock-check",
    "sync",
    "lint",
    "format",
    "typecheck",
    "test",
    "audit",
    "report-offline",
    "determinism",
)


def verify_prerequisites() -> list[str]:
    for line in MAKEFILE.splitlines():
        if line.startswith("verify:"):
            # The help description lives on the same line, after `## `.
            return line.split(":", 1)[1].split("##")[0].split()
    raise AssertionError("the Makefile defines no verify target")


def test_the_verify_target_runs_every_gate_by_name() -> None:
    """The list, read. The previous version of this check could not see it shrink.

    It asserted that the file contained the text `verify:` and the text
    `uv sync --locked`. The second is satisfied by the `sync:` recipe wherever it sits,
    so deleting `sync`, `audit` or `determinism` from the prerequisites left every test
    in this suite green while `make verify` quietly stopped running them. A gate list
    nothing reads is a gate list that can be shortened by accident.
    """
    assert verify_prerequisites() == list(VERIFY_GATES)


def test_every_gate_verify_names_is_a_target_that_exists() -> None:
    """A prerequisite with no rule behind it is a name, not a gate."""
    for gate in VERIFY_GATES:
        assert re.search(rf"^{re.escape(gate)}:", MAKEFILE, re.MULTILINE), (
            f"verify depends on {gate}, which the Makefile does not define"
        )


def test_the_verify_target_exists_and_is_what_ci_runs() -> None:
    assert "\nverify:" in MAKEFILE
    assert "uv sync --locked" in MAKEFILE
    recipe = [
        line for line in MAKEFILE.splitlines() if not line.lstrip().startswith("#")
    ]
    assert "--frozen" not in "\n".join(recipe), (
        "--frozen means 'do not resolve', not 'the lock is current', and it exits 0 "
        "against a stale lockfile"
    )
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "run: make verify" in ci


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_declares_a_top_level_permissions_block(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert re.search(r"^permissions:$", text, re.MULTILINE), workflow.name


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_full_sha_with_its_version(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- uses:") and not stripped.startswith("uses:"):
            continue
        assert re.search(r"uses:\s+[\w./-]+@[0-9a-f]{40}\s+#\s+v\d", stripped), (
            f"{workflow.name}: {stripped}"
        )


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_security_gate_is_silenced(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert "continue-on-error: true" not in text, workflow.name
    assert "|| true" not in text, workflow.name


SCANNERS = ("codeql", "semgrep", "gitleaks", "zizmor", "pip-audit")


def _uncommented(text: str) -> str:
    """The workflow with its comment lines removed.

    A workflow that explains in a comment why it accepts a scanner finding is not a
    workflow that runs a scanner, and the check below is about the second thing. Matching
    on the whole file made release.yml look like a scanner job the moment it said the
    word CodeQL.
    """
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def test_no_scanner_is_manual_only() -> None:
    """A scanner reachable only by workflow_dispatch is documentation, not enforcement.

    Scoped to workflows that run a scanner. The release workflow is dispatch-only by
    design: a tag push should not be sufficient to publish, so a human names the tag.
    """
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        if not any(scanner in _uncommented(text).lower() for scanner in SCANNERS):
            continue
        triggers = text.split("permissions:")[0]
        if "workflow_dispatch" not in triggers:
            continue
        assert "pull_request" in triggers or "schedule" in triggers, workflow.name


def test_contributing_names_the_rules_the_project_will_not_break() -> None:
    for phrase in (
        "without its denominator",
        "never in CI",
        "make verify",
    ):
        assert phrase in CONTRIBUTING


def test_every_accepted_codeql_finding_is_written_down_with_its_reasoning() -> None:
    """An acceptance nobody can argue with is a suppression with better manners."""
    accepted = json.loads(
        (ROOT / ".github" / "codeql-accepted.json").read_text(encoding="utf-8")
    )
    assert isinstance(accepted, list)
    for entry in accepted:
        assert set(entry) == {"rule", "path", "accepted", "reason"}, entry
        assert (ROOT / entry["path"]).exists(), entry["path"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["accepted"]), entry
        assert len(entry["reason"]) > 200, (
            f"{entry['rule']} is excused in one line. Say why it is not a defect, or "
            "fix it."
        )
    assert len(accepted) <= 3, (
        "an acceptance list this long is a scanner that has been talked out of its job"
    )


def test_the_codeql_gate_refuses_an_acceptance_that_has_outlived_its_finding() -> None:
    """The half of the gate that keeps the list from becoming a graveyard."""
    codeql = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    assert "codeql-accepted.json" in codeql
    assert "no longer reports" in codeql
    assert "stale.json" in codeql


def test_the_release_build_writes_no_actions_cache() -> None:
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert "enable-cache: false" in release, (
        "a release build caching under the main scope is a cross-workflow write it does "
        "not need"
    )


def test_the_unresolvable_dependency_is_ignored_with_its_reason_rather_than_left_red() -> (
    None
):
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'dependency-name: "perimeter"' in dependabot
    assert "PyPI" in dependabot, "the ignore must say what the real fix is and is not"


def test_the_readme_names_every_collection_that_is_not_in_name_order() -> None:
    """The claim issue #23 found false, tied to the ledger that now decides it.

    The README asserted, without qualification and directly beside an enforced rule,
    that every collection in the output is sorted by name. It was false in four places
    and nothing read it, so it stayed false. A fifth exception added to the ledger and
    not to the README fails here.
    """
    top_level = [
        path
        for path, (kind, _) in ORDERINGS.items()
        if kind != BY_NAME and "[]" not in path
    ]
    assert top_level, "the ledger records no exception, so this test checks nothing"
    for path in top_level:
        name = path.removeprefix("$.")
        assert name in README, (
            f"{name} is published in an order other than by name and the README does "
            "not say so"
        )
    assert "Name order is the rule" in README


def test_the_readme_does_not_still_make_the_unqualified_claim() -> None:
    assert "Every collection in the output is sorted by name" not in README


def in_its_own_voice(text: str) -> str:
    """The file with its inline code spans removed.

    A phrase inside backticks is being named, not asserted. `docs/RUNBOOK.md` quotes
    the false claim in exactly that form, in the sentence that records the row having
    made it and having been corrected, and a rule that cannot tell a correction from a
    relapse would push the history out of the document to stay green.
    """
    return re.sub(r"`[^`]*`", " ", text)


# Every file in the repository that says anything about the branch ruleset, found by
# reading the tree rather than by naming three of them.
#
# The hand-written set was `README.md`, `CHANGELOG.md` and `docs/ROADMAP.md`, and the
# rule below is why: on 2026-08-28 the ruleset was read back, it carried a bypass actor
# those three documents denied, and they were corrected. `.github/workflows/ci.yml`
# said the same false thing in its header comment, was not in the set, and went on
# saying it for nine more days -- past a merge that widened the *document* rules from
# three files to thirty-three, because that widening did not reach this rule. A gate
# whose file set excludes the file carrying the violation reports success without
# having looked, which is the same defect as a gate that reads three of thirty-three
# documents, one rule further down.
RULESET_FILES = tuple(
    sorted(
        str(path.relative_to(ROOT))
        for path in [
            *ROOT.glob("*.md"),
            *(ROOT / "docs").rglob("*.md"),
            *(ROOT / ".github").rglob("*.md"),
            *(ROOT / ".github" / "workflows").glob("*.yml"),
        ]
        if "ruleset" in path.read_text(encoding="utf-8").lower()
    )
)
RULESET_DOCUMENTS = {
    name: (ROOT / name).read_text(encoding="utf-8") for name in RULESET_FILES
}


def test_the_ruleset_file_sweep_did_not_collapse() -> None:
    """The set is globbed and filtered, so either step going empty would pass silently.

    Both named files are ones the hand-written set left out, and one of them is where
    the defect this rule exists to catch actually sat.
    """
    assert len(RULESET_DOCUMENTS) >= 6, RULESET_FILES
    for name in (
        "README.md",
        "CHANGELOG.md",
        "docs/ROADMAP.md",
        "docs/RUNBOOK.md",
        ".github/rulesets/README.md",
        ".github/workflows/ci.yml",
    ):
        assert name in RULESET_DOCUMENTS, f"{name} describes the ruleset and is unread"


def test_no_document_claims_the_ruleset_carries_no_bypass_actor() -> None:
    """It carries one, and four files said it carried none.

    Read back from the API on 2026-08-28: the ruleset on `main` grants `RepositoryRole`
    5, repository admin, `bypass_mode: always`. That is the account that pushes, so
    every one of the six required checks is skippable by the person they exist to
    check. The claim had been in the conformance table since the ruleset was created
    and nothing re-read it, which is the failure this repository is otherwise careful
    about. `docs/RUNBOOK.md` now carries the command that reads it back.
    """
    for name, text in RULESET_DOCUMENTS.items():
        assert "no bypass actors" not in in_its_own_voice(text).lower(), (
            f"{name} claims a protection the ruleset does not have"
        )


def test_every_document_describing_the_ruleset_names_its_bypass_actor() -> None:
    """Silence would be the same overstatement with fewer words."""
    for name, text in RULESET_DOCUMENTS.items():
        lowered = text.lower().replace("-", " ")
        assert "bypass" in lowered, name
        assert "repository admin" in lowered, name


def test_the_runbook_carries_the_command_that_reads_the_ruleset_back() -> None:
    runbook = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    assert "gh api repos/OWNER/REPO/rulesets" in runbook
    assert "bypass_actors" in runbook


def make_targets() -> list[str]:
    """Every target named in the Makefile's .PHONY declaration."""
    block = MAKEFILE.split(".PHONY:", 1)[1].split("\n\n", 1)[0]
    return block.replace("\\", " ").split()


def test_make_help_lists_every_target_with_a_description() -> None:
    """A target added without its help line is a target nobody will find.

    The description lives on the target line, so adding a target and documenting it are
    the same edit, and this test is what makes skipping the second half fail.
    """
    result = subprocess.run(
        ["make", "help"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    listed = {
        line.split()[0] for line in result.stdout.splitlines() if line.startswith("  ")
    }
    assert listed == set(make_targets()), (
        "make help and .PHONY disagree about which targets exist"
    )
    for required in ("verify", "report-offline", "determinism", "acquire"):
        assert required in listed, required


def test_make_help_says_which_target_touches_the_network() -> None:
    """`acquire` is the only one, and the listing has to say so."""
    for line in MAKEFILE.splitlines():
        if line.startswith("acquire:"):
            assert "network" in line.split("##", 1)[1]
            return
    raise AssertionError("the Makefile defines no acquire target")


def test_bare_make_still_runs_the_one_gate() -> None:
    """Adding `help` must not turn the habitual keystroke into a listing."""
    assert ".DEFAULT_GOAL := verify" in MAKEFILE
    result = subprocess.run(
        ["make", "--dry-run"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "uv lock --check" in result.stdout
    assert "tools/determinism.sh" in result.stdout


ISSUE_FORMS = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
PR_TEMPLATE = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(
    encoding="utf-8"
)
DEFINITION_OF_DONE = (ROOT / "docs" / "DEFINITION_OF_DONE.md").read_text(
    encoding="utf-8"
)

# Read from the repository on 2026-08-28 with `gh label list`. A form filing under a
# label that does not exist silently files under none, so the set is written down here
# rather than assumed. Re-read it when a label is added or removed.
REPOSITORY_LABELS = frozenset(
    {
        "accessibility",
        "bug",
        "documentation",
        "duplicate",
        "enhancement",
        "good first issue",
        "help wanted",
        "invalid",
        "question",
        "wontfix",
    }
)


def checklist_items(text: str) -> list[str]:
    """Every checklist item, with its continuation lines folded into one string."""
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            items.append(stripped.removeprefix("- [ ]").strip())
        elif items and line.startswith("      ") and stripped:
            items[-1] = f"{items[-1]} {stripped}"
    return [" ".join(item.split()) for item in items]


def test_the_repository_carries_both_issue_forms_and_a_config() -> None:
    names = {path.name for path in ISSUE_FORMS}
    assert names == {"bug_report.yml", "measurement_proposal.yml", "config.yml"}


def test_every_issue_form_names_a_label_the_repository_has() -> None:
    """A form filing under a label that does not exist files under none.

    This is what would have caught a `measurement` label that was never created.
    """
    for path in ISSUE_FORMS:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"labels:\s*\[(.*?)\]", text):
            for raw in match.group(1).split(","):
                label = raw.strip().strip('"').strip("'")
                assert label in REPOSITORY_LABELS, f"{path.name} files under {label!r}"


def test_blank_issues_stay_enabled() -> None:
    """Issues #16 to #23 fit neither form. A form is a funnel, not a gate."""
    config = (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(
        encoding="utf-8"
    )
    assert "blank_issues_enabled: true" in config


def test_the_measurement_form_asks_for_the_denominator() -> None:
    """The one field this project cannot publish a rate without."""
    form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "measurement_proposal.yml").read_text(
        encoding="utf-8"
    )
    assert "id: denominator" in form
    assert "id: numerator" in form
    assert "id: ranks-nobody" in form
    assert "id: touches-no-infrastructure" in form
    denominator = form.split("id: denominator", 1)[1].split("id: ", 1)[0]
    assert "required: true" in denominator, "the denominator field is optional"


def test_the_pull_request_template_mirrors_the_definition_of_done() -> None:
    """The checklist cannot fall behind the rules it states.

    Every item in `docs/DEFINITION_OF_DONE.md` has to appear in the template, so adding
    a rule and forgetting the checklist is a failing build rather than a checklist that
    slowly stops describing the project.
    """
    required = checklist_items(DEFINITION_OF_DONE)
    assert len(required) >= 14, "the Definition of Done parsed to almost nothing"
    template = " ".join(PR_TEMPLATE.split())
    for item in required:
        assert item in template, f"the pull request template is missing: {item}"


def test_the_pull_request_template_asks_whether_published_figures_moved() -> None:
    assert "Does this change published figures?" in PR_TEMPLATE
    assert "Tick exactly one" in PR_TEMPLATE
    assert "docs/RUNBOOK.md" in PR_TEMPLATE


def test_no_issue_template_was_added_under_workflows() -> None:
    """Issue #19 scoped this change out of `.github/workflows`, which tests read."""
    workflow_names = {path.name for path in WORKFLOWS}
    assert workflow_names == {
        "ci.yml",
        "codeql.yml",
        "osv.yml",
        "release.yml",
        "scorecard.yml",
    }


GLOSSARY = (ROOT / "docs" / "GLOSSARY.md").read_text(encoding="utf-8")


def test_the_glossary_defines_every_term_the_readme_uses_without_defining() -> None:
    """The list issue #18 asked for, held so an entry cannot quietly go missing."""
    for term in (
        "DINS",
        "State responsibility area",
        "Load serving entity",
        "IOU",
        "POU",
        "CO-OP",
        "Tribal utility",
        "CCA",
        "ADMIN",
        "OGC validity check",
        "Geometry repair",
        "Contested",
        "Boundary band",
        "Wilson score interval",
        "Newcombe score interval",
    ):
        assert f"**{term}" in GLOSSARY, f"the glossary has no entry for {term}"


def test_the_glossary_says_the_publisher_documents_none_of_the_type_values() -> None:
    """The entry that would be a fabrication if it were written the easy way.

    `sources.py` records that the CEC documents none of the six `Type` values. A
    glossary that stated what IOU or POU means as though the publisher had said so
    would contradict a published document in this repository, which is the case issue
    #18 said to stop and report rather than smooth over. The expansions are given as
    the conventional reading and the gap is named.
    """
    assert "The publisher documents none of\nthem" in GLOSSARY.replace("**", "")
    assert "TYPE_FIELD_IS_UNDOCUMENTED" in GLOSSARY
    assert "conventionally" in GLOSSARY


def test_every_relative_link_in_the_glossary_resolves() -> None:
    """A glossary of dead links is a glossary that stopped being checked."""
    targets = re.findall(r"\]\((?!https?:)([^)#]+)", GLOSSARY)
    assert len(targets) > 15, "the glossary links to almost nothing"
    for target in targets:
        resolved = (ROOT / "docs" / target).resolve()
        assert resolved.exists(), (
            f"the glossary links to {target}, which does not exist"
        )


def test_the_glossary_cites_the_public_utilities_code_for_a_cca() -> None:
    """The citation, checked against where it actually lives.

    Issue #18 asked for section 331.1 "as ADR 0002 does". ADR 0002 does not: it
    describes a community choice aggregator in its own words and cites no section. The
    citation is in `sources.py`, in `EXCLUDED_TYPES`. The glossary cites the code
    section and points at the file that carries it, and this test checks the authority
    rather than the one the issue named from memory.
    """
    assert "331.1" in GLOSSARY
    sources = (
        ROOT / "src" / "wildfire_service_territory_overlap" / "sources.py"
    ).read_text(encoding="utf-8")
    assert "331.1" in sources, "the citation moved out of sources.py"


def test_contributing_carries_a_first_change_walkthrough() -> None:
    for phrase in (
        "## Your first change, start to finish",
        "make report-offline",
        "is_fixture",
        "fixtures/README.md",
        "tools/determinism.sh",
        "docs/RUNBOOK.md",
    ):
        assert phrase in CONTRIBUTING, phrase


def test_the_walkthrough_lists_the_gates_in_the_order_verify_runs_them() -> None:
    """The table cannot drift from the gate list it describes.

    A walkthrough that teaches a newcomer a stale order is worse than one that does not
    try, because they will trust it.
    """
    section = CONTRIBUTING.split("### 4. The gates, in the order")[1]
    found = [
        line.strip("| ").split("|")[0].strip().strip("`")
        for line in section.splitlines()
        if line.startswith("| `")
    ]
    assert found == list(VERIFY_GATES)


def test_the_walkthrough_only_names_make_targets_that_exist() -> None:
    """Issue #21 asked for the target names exactly as currently defined."""
    section = CONTRIBUTING.split("## Your first change, start to finish")[1]
    named = set(re.findall(r"make ([a-z][a-z-]*)", section))
    real = set(make_targets())
    assert named, "the walkthrough names no make target at all"
    assert named <= real, (
        f"the walkthrough names targets that do not exist: {named - real}"
    )


def test_the_walkthrough_does_not_claim_a_fixture_edit_trips_determinism() -> None:
    """The correction that had to be checked rather than copied.

    Issue #21 asked for a step that renames a territory in a fixture, runs
    `make determinism`, and watches it refuse. It does not refuse. The determinism gate
    builds the fixtures twice and compares the two trees, so an edited input changes
    both builds identically and the comparison still matches. Run and confirmed on
    2026-08-28: the rename leaves `make determinism` at exit 0 and fails `make test`
    with eight failures.

    The walkthrough therefore sends the rename at `make test`, says in as many words
    that determinism passes and why, and reaches the determinism refusal by making two
    build trees actually differ.
    """
    section = CONTRIBUTING.split("### 3. Break something on purpose")[1]
    assert "**It passes.**" in section
    assert "changes both builds identically" in section
    assert 'echo "edited" >> build/run-two/REPORT.md' in section


# --- The accessibility review, held against the gates it now cites ------------------

ACR = (ROOT / "docs" / "ACR.md").read_text(encoding="utf-8")

# Every Markdown document in the repository. The generated report goes through
# `artifacts.write_report` on every build and is checked again as committed in
# tests/test_published.py; these are repository prose, held to the same rules.
#
# This started as the three documents `docs/ACR.md` names, and the three were not
# enough. The review of 2026-09-04 recorded two documents outside the gated set that
# the rules refuse, `docs/METRICS_LEDGER.md` and `docs/adr/0007`, and while those were
# being fixed a third turned up in `docs/adr/0015`, merged four hours earlier, carrying
# three bare URLs. A gate that reads three of thirty-three documents is a sample, and
# the documents it does not read are where the defects were.
DOCUMENTS_THE_REVIEW_CLAIMS = tuple(
    sorted(
        str(path.relative_to(ROOT))
        for path in [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")]
    )
)


def test_the_sweep_of_documents_did_not_collapse() -> None:
    """The list is globbed, so an empty glob would pass every document silently."""
    assert len(DOCUMENTS_THE_REVIEW_CLAIMS) > 25
    for name in ("README.md", "PROVENANCE.md", "docs/ACR.md", "docs/METRICS_LEDGER.md"):
        assert name in DOCUMENTS_THE_REVIEW_CLAIMS


@pytest.mark.parametrize("name", DOCUMENTS_THE_REVIEW_CLAIMS)
def test_the_documents_this_review_makes_claims_about_pass_the_document_rules(
    name: str,
) -> None:
    """The review says header rows, descriptive links and hierarchical headings hold
    in these documents. Saying it is not holding it.

    This is what caught `docs/ACR.md` itself: the row asserting that every data table
    has a header row carried four unescaped pipes inside a code span, so the row was
    read as five cells under a two-cell header and the claim rendered under the wrong
    column name.
    """
    check_document((ROOT / name).read_text(encoding="utf-8"))


def document_rules() -> list[str]:
    """Every rule `check_document` runs, read out of the function rather than listed."""
    return re.findall(r"assert_[a-z_]+", inspect.getsource(check_document))


def test_the_accessibility_review_names_the_rule_behind_every_enforced_check() -> None:
    """A rule added to the gate and not to the review is a review going stale again.

    The list is read from `check_document`, so it cannot fall behind the module the way
    a hand-copied list would.
    """
    rules = document_rules()
    assert len(rules) >= 6, "check_document parsed to almost no rules"
    for rule in rules:
        assert rule in ACR, f"{rule} enforces a check the review does not name"


def test_the_accessibility_review_still_says_the_assistive_technology_pass_is_open() -> (
    None
):
    """The sentence in this repository that must never be quietly improved.

    Six structural checks moved from reviewed to enforced on 2026-09-04. None of them
    is a screen reader, nobody has run one, and the value of this document is that it
    says so. A future edit that softens this into a claim of general accessibility
    conformance fails here.
    """
    normalised = " ".join(ACR.split())
    assert "No assistive-technology pass" in normalised
    assert (
        "Nobody has navigated the generated tables with a screen reader" in normalised
    )
    assert "that pass remains open" in normalised
    assert "this review does not claim it" in normalised
    for overstatement in (
        "fully accessible",
        "accessibility conformant",
        "screen reader tested",
        "wcag aa",
        "wcag 2.1 aa",
    ):
        assert overstatement not in ACR.lower(), f"the review claims {overstatement!r}"


def test_the_readme_accessibility_row_says_the_same_thing_the_review_says() -> None:
    """The conformance table and the review cannot disagree about what is outstanding."""
    rows = [line for line in README.splitlines() if line.startswith("| Accessibility")]
    assert len(rows) == 1, "the conformance table has no single Accessibility row"
    row = rows[0]
    assert "assistive-technology pass" in row
    assert "docs/ACR.md" in row
    assert "check_document" in row, (
        "the row states what became enforced, so it names the gate that enforces it"
    )


# The roadmap's phase tables say what this project has built. They carried no status
# column at all until 2026-09-05, so sixteen shipped items read as pending and issues
# #69 to #87 were filed against work that already existed. The column is the repair;
# what follows is what stops it drifting back, by holding every cell to a path in this
# tree rather than to whoever last read the document.
ROADMAP_STATUSES = ("**Shipped.**", "**Partly shipped.**", "**Open.**")


def phase_table_rows(document: str) -> list[tuple[str, list[str]]]:
    """Every row of every `## Phase` table, as its item number and its cells.

    Found by heading and by the shape of the first cell rather than by line number, so
    a table that moves stays covered, and a table that is deleted shows up as a count
    that dropped rather than as a check quietly reading nothing.
    """
    rows: list[tuple[str, list[str]]] = []
    for section in document.split("\n## ")[1:]:
        if not section.startswith("Phase "):
            continue
        for line in section.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = table_cells(line)
            if cells and re.fullmatch(r"\d\.\d", cells[0]):
                rows.append((cells[0], cells))
    return rows


def _names_something_this_repository_has(token: str) -> bool:
    """True when a backticked token resolves to a path in this repository.

    ADRs are cited by number (`docs/adr/0013`) rather than by their full filename, so a
    token also resolves when a path that exists starts with it. `tools/diff_artifacts.py`
    does not resolve, which is the point: roadmap 2.1 named that file, the module
    shipped somewhere else, and nothing read either.
    """
    if not token or " " in token or any(char in token for char in "*?["):
        return False
    if (ROOT / token).exists():
        return True
    return any(ROOT.glob(token + "*"))


def _refuse_a_status_the_tree_contradicts(document: str) -> None:
    """Raise on a phase row whose status this repository does not support.

    Kept out of the tests so the test that watches it refuse drives the same code the
    test guarding the roadmap drives, rather than a re-implementation of it, the way
    the conformance-table date check is arranged.
    """
    for number, cells in phase_table_rows(document):
        status = cells[1]
        marker = next((m for m in ROADMAP_STATUSES if status.startswith(m)), None)
        if marker is None:
            raise AssertionError(
                f"roadmap row {number} states no status. Every phase row opens its "
                f"status cell with one of {', '.join(ROADMAP_STATUSES)}"
            )
        cited = re.findall(r"`([^`]+)`", status)
        for token in cited:
            if "/" in token and not _names_something_this_repository_has(token):
                raise AssertionError(
                    f"roadmap row {number} is marked {marker} and cites `{token}`, "
                    "which is not in this repository"
                )
        if marker == "**Shipped.**":
            if not any(_names_something_this_repository_has(token) for token in cited):
                raise AssertionError(
                    f"roadmap row {number} claims {marker} and names nothing in this "
                    "repository that holds the claim up"
                )
            for overstatement in ("still open", "remains open", "not yet"):
                if overstatement in status.lower():
                    raise AssertionError(
                        f"roadmap row {number} claims {marker} and says "
                        f"{overstatement!r} in the same cell"
                    )
        elif "Still open" not in status:
            raise AssertionError(
                f"roadmap row {number} is marked {marker} and does not say what is "
                "outstanding"
            )


def test_every_phase_table_row_carries_a_status_the_tree_supports() -> None:
    """The defect this column exists for, held shut."""
    _refuse_a_status_the_tree_contradicts(ROADMAP)


def test_the_roadmap_status_check_reads_every_phase_table() -> None:
    """The rows are found by parsing, so an empty parse would pass every row silently."""
    rows = phase_table_rows(ROADMAP)
    assert len(rows) >= 25, "the phase tables collapsed to a handful of rows"
    assert {number.split(".")[0] for number, _ in rows} == {"0", "1", "2", "3", "4"}
    for _, cells in rows:
        assert len(cells) >= 3, cells


def test_no_phase_row_carries_its_status_anywhere_but_the_status_cell() -> None:
    """Two places to read a state is one place too many.

    Rows 0.3 and 0.5 said **Done.** inside their item cell while the twenty-five around
    them said nothing, which is how the tables came to be read as a list of intentions.
    """
    for number, cells in phase_table_rows(ROADMAP):
        assert "**Done.**" not in " ".join(cells[2:]), number
        assert not any(cell.startswith(ROADMAP_STATUSES) for cell in cells[2:]), number


def test_the_roadmap_says_how_to_read_the_status_column() -> None:
    """A vocabulary nobody wrote down is a vocabulary the next writer invents again."""
    preamble = ROADMAP.split("\n## Phase ")[0]
    for marker in ROADMAP_STATUSES:
        assert marker in preamble, marker
    assert "tests/test_provenance_and_standards.py" in preamble, (
        "the roadmap does not name the gate that holds its status cells"
    )


def test_the_roadmap_prose_and_the_status_cells_agree_about_what_is_open() -> None:
    """The two halves of this document cannot disagree about the same item.

    The prose above the tables lists what is still open. Before the status column
    existed that list was the only place an item's state was recorded, and the tables
    were free to imply anything. An item named there and marked shipped below fails
    here.
    """
    paragraph = re.search(
        r"^Still open: .*?(?=\n\n)", ROADMAP, re.MULTILINE | re.DOTALL
    )
    assert paragraph, "the roadmap's summary of what is still open has gone"
    named = set(re.findall(r"\b\d\.\d\b", paragraph.group(0)))
    assert named, "that summary names no item, so this check reads nothing"
    statuses = {number: cells[1] for number, cells in phase_table_rows(ROADMAP)}
    for number in sorted(named):
        assert number in statuses, f"{number} is called open and has no row"
        assert not statuses[number].startswith("**Shipped.**"), (
            f"the prose says {number} is still open and its row says shipped"
        )


CONTRADICTED_STATUSES = (
    # A shipped row citing a path that is not here. This is the roadmap 2.1 defect:
    # the row named `tools/diff_artifacts.py` for two weeks and the module shipped as
    # `artifact_diff.py` instead.
    ("not in this repository", "| 9.1 | **Shipped.** `tools/diff_artifacts.py` | a |"),
    # A row with no status at all, which is every row before this column existed.
    ("states no status", "| 9.1 | it got done at some point | a |"),
    # A shipped row that names nothing, so nothing can contradict it.
    ("names nothing in this repository", "| 9.1 | **Shipped.** trust me | a |"),
    # A shipped row that still says what is outstanding, which is a partly shipped row
    # wearing the stronger word.
    ("says 'still open'", "| 9.1 | **Shipped.** `README.md`. Still open: all | a |"),
    # An open row that does not say what is outstanding.
    ("does not say what is outstanding", "| 9.1 | **Open.** `README.md` | a |"),
)


@pytest.mark.parametrize(("expected", "row"), CONTRADICTED_STATUSES)
def test_the_roadmap_status_check_can_actually_fire(expected: str, row: str) -> None:
    """A gate nobody has watched refuse is not a gate.

    Every branch is driven by a fabricated table rather than by editing the real one,
    so the check is known to be able to fail without the document having to be wrong.
    """
    fabricated = (
        "\n\n## Phase 9: a table written for this check to read\n\n"
        "Introduced, because the document rules refuse a table that opens cold.\n\n"
        f"| # | Status | Item |\n|---|---|---|\n{row}\n"
    )
    assert phase_table_rows(fabricated), "the fabricated table did not parse"
    with pytest.raises(AssertionError, match=expected):
        _refuse_a_status_the_tree_contradicts(fabricated)
