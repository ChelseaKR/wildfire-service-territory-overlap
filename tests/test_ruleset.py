"""The committed ruleset names every gate a pull request actually runs.

Branch protection is a repository setting. It can be widened, narrowed or deleted
without a commit, and the history would not show it, so `.github/rulesets/main.json`
is committed as the evidence the README's CI/CD row is checked against.

The invariant here is not "the file matches the live ruleset": a public-scope token
cannot read `bypass_actors`, and a comparison that silently drops a field it could not
read is a check that passes for the wrong reason. The invariant is the one that catches
the mistake this repository could actually make, which is **adding a job to CI and
forgetting to require it**. An unrequired job still reports on the pull-request page,
still goes red, and still merges.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULESET = REPO / ".github" / "rulesets" / "main.json"
WORKFLOWS = REPO / ".github" / "workflows"


def required_contexts() -> set[str]:
    ruleset = json.loads(RULESET.read_text(encoding="utf-8"))
    for rule in ruleset["rules"]:
        if rule["type"] == "required_status_checks":
            checks = rule["parameters"]["required_status_checks"]
            return {check["context"] for check in checks}
    raise AssertionError("the committed ruleset requires no status checks at all")


def pull_request_job_names() -> set[str]:
    """Every job of every workflow that triggers on `pull_request`.

    A job's check name is its `name:` where it has one, and its job id otherwise,
    which is how GitHub names them, and therefore how a ruleset must.
    """
    names: set[str] = set()
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        header, _, body = text.partition("\njobs:")
        if not re.search(r"^\s{2}pull_request:", header, re.MULTILINE):
            continue
        for block in re.finditer(
            r"^  ([a-z0-9][a-z0-9_-]*):\n((?:(?:    .*)?\n)*)", body, re.MULTILINE
        ):
            job_id, job_body = block.group(1), block.group(2)
            named = re.search(r"^    name:\s*(.+?)\s*$", job_body, re.MULTILINE)
            names.add(named.group(1).strip("\"'") if named else job_id)
    return names


def test_the_ruleset_requires_every_job_a_pull_request_runs() -> None:
    missing = pull_request_job_names() - required_contexts()
    assert not missing, (
        f"these jobs run on a pull request but are not required by the committed "
        f"ruleset, so they can go red and still merge: {sorted(missing)}"
    )


def test_the_ruleset_requires_nothing_that_does_not_run() -> None:
    """A required check no workflow produces blocks every merge, forever."""
    stale = required_contexts() - pull_request_job_names()
    assert not stale, (
        f"the committed ruleset requires checks no pull-request job produces, which "
        f"would block every merge: {sorted(stale)}"
    )


def test_the_ruleset_still_refuses_deletion_and_force_push() -> None:
    ruleset = json.loads(RULESET.read_text(encoding="utf-8"))
    types = {rule["type"] for rule in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request"} <= types


def test_the_bypass_actors_are_stated_rather_than_omitted() -> None:
    """The admin bypass is real. A file that hides it is a file that lies politely."""
    ruleset = json.loads(RULESET.read_text(encoding="utf-8"))
    assert "bypass_actors" in ruleset, (
        "bypass_actors is absent from the committed ruleset; an omitted bypass reads "
        "as no bypass, which is the claim .github/rulesets/README.md refuses to make"
    )


def push_triggered_workflows() -> dict[str, str]:
    """Every workflow that runs on a push to a branch, with its text.

    `schedule` and `workflow_dispatch` are not push triggers: they fire at most once
    at a time, so a shared slot never has a queue to evict from.
    """
    found: dict[str, str] = {}
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        header, _, _ = text.partition("\njobs:")
        if re.search(r"^\s{2}push:", header, re.MULTILINE):
            found[workflow.name] = text
    return found


def test_the_push_workflow_sweep_did_not_collapse() -> None:
    """Both rules below pass vacuously if this glob or this filter finds nothing."""
    names = set(push_triggered_workflows())
    assert {"ci.yml", "scorecard.yml"} <= names, names


def test_a_commit_pushed_to_main_gets_a_concurrency_slot_of_its_own() -> None:
    """A ref-only key on a push trigger loses a commit's verdict silently.

    A concurrency group holds one running run and exactly one pending run. A third
    arrival evicts the pending one with no jobs ever dispatched, so in a burst of
    merges some commit on `main` gets no run at all: not a red check a reader can
    find, an absent one. `cancel-in-progress` does not decide whether that happens,
    only whether the loss is visible.

    The key must therefore vary per commit on a push while staying per-ref on a pull
    request, so branch supersession still works. Any workflow that gains a `push:`
    trigger later is caught here rather than quietly sharing a slot.
    """
    for name, text in push_triggered_workflows().items():
        group = re.search(r"^  group:\s*(.+?)\s*$", text, re.MULTILINE)
        assert group is not None, (
            f"{name} runs on push and declares no concurrency group"
        )
        key = group.group(1)
        assert "github.sha" in key, (
            f"{name} keys its concurrency group on the ref alone ({key}), so every "
            "commit pushed to main competes for one slot and a burst of merges drops "
            "a verdict with no run to show for it"
        )
        assert "pull_request" in key, (
            f"{name} does not keep pull requests on a per-ref group ({key}), so two "
            "pushes to one branch would both run instead of the later superseding "
            "the earlier"
        )
