"""The `secret-scan` check must read the repository, not the commit it was handed.

`secret-scan` is a required status check on `main` under the ruleset committed at
`.github/rulesets/main.json`. Until 2026-09-13 the job ran
`gitleaks/gitleaks-action`, which chooses its range from the triggering event
rather than scanning the repository:

    push, N commits   gitleaks detect --log-opts=--no-merges --first-parent BASE^..HEAD
    push, 1 commit    gitleaks detect --log-opts=-1
    pull_request      the pull request's own commits

Every squash merge into `main` is a single-commit push, and `ci.yml` carries no
`schedule` and no `workflow_dispatch`, so no lane in this repository ever read
more than 1 of `main`'s 59 commits. A credential added in one commit and deleted
in the next was invisible to the check named after finding it.

`fetch-depth: 0` did not prevent that and cannot. It decides how much history
`actions/checkout` puts on disk, not how much of it the scanner is asked to
read, and a checkout deep enough to scan sitting above an invocation that
declines to is exactly the state this job was in. So every assertion below is
about the *invocation*; the `fetch-depth: 0` assertion is kept as the necessary
precondition it actually is, and is not evidence of a history scan on its own.

Measured on a throwaway clone of this repository, remote removed, with the fix
in hand: a random, real-shaped AWS key planted in one commit and removed in the
next left `gitleaks git . --log-opts=-1` exiting 0, while `gitleaks git .`
exited 1 on the same history. The tip tree was byte-identical to the baseline
throughout, so the credential was reachable only from history.

What `gitleaks git .` walks with no range is `git log --all`, every commit in the
checkout, rather than one ref's ancestry. Measured on the runner, pull request
#118: `91 commits scanned`.
"""

from __future__ import annotations

import re
from pathlib import Path

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

# Four conformance checks elsewhere in this portfolio passed because they matched a
# tool name inside a COMMENT, and this repository has already been bitten by the
# same thing twice. The comment above the scan step names both the action that was
# removed and the flag that must not come back, so every assertion here reads the
# workflow with its comments stripped and cannot be satisfied by prose.
_COMMENT = re.compile(r"(?m)^\s*#.*$|\s+#.*$")


def _ci_code() -> str:
    return _COMMENT.sub("", CI.read_text(encoding="utf-8"))


def test_the_scanner_is_never_handed_a_range() -> None:
    text = _ci_code()
    assert "gitleaks git . --no-banner --redact --exit-code 1" in text, (
        "the secret scan no longer runs `gitleaks git .`. Whatever replaces it must "
        "still walk every commit in the checkout on every event, not a range chosen "
        "from the event that triggered the run."
    )
    assert "--log-opts" not in text, (
        "`--log-opts` scopes gitleaks to a commit range. A range picked from the "
        "triggering event is how this required check came to read 1 of 59 commits."
    )


def test_the_event_driven_action_does_not_come_back() -> None:
    assert "gitleaks/gitleaks-action" not in _ci_code(), (
        "gitleaks/gitleaks-action picks its range from the event and degrades to "
        "`--log-opts=-1` on a single-commit push, which is every squash merge here."
    )


def test_checkout_still_fetches_the_history_the_scan_walks() -> None:
    """Necessary, not sufficient: without it there is nothing on disk to walk.

    This line was already in the job while the check read one commit, so it is
    evidence of a precondition and never of a history scan.
    """
    assert re.search(r"^\s*fetch-depth:\s*0\s*$", _ci_code(), flags=re.MULTILINE), (
        "`fetch-depth: 0` is gone from the secret-scan checkout, so `gitleaks git .` "
        "would walk only the single commit actions/checkout fetched"
    )


def test_the_pinned_binary_is_checksum_verified() -> None:
    """A downloaded scanner nobody verifies is a supply chain hole in a security gate."""
    text = _ci_code()
    assert "gitleaks_checksums.txt" in text, (
        "the gitleaks release checksums are not fetched"
    )
    assert "sha256sum --check --strict" in text, (
        "the gitleaks archive is unpacked without checking it against the published "
        "checksum"
    )


def test_the_scan_step_fails_the_job_on_a_finding() -> None:
    """`gitleaks git` exits 0 on a finding unless it is told not to."""
    text = _ci_code()
    assert "--exit-code 1" in text, (
        "without `--exit-code 1` gitleaks reports findings and exits 0, and a gate "
        "that cannot go red is not a gate"
    )
    assert "set -euo pipefail" in text, (
        "the download steps run unguarded, so a failed curl would reach the scan"
    )
