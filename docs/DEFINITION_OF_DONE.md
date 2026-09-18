# Definition of done

What "done" means here, by kind of change. A change that meets everything below can be
merged without a conversation about whether it is finished.

## Any change

- [ ] `make verify` passes locally, end to end: lockfile drift, lint, format, mypy
      `--strict`, tests with the branch-coverage floor, pip-audit, the offline report,
      and the determinism gate.
- [ ] No new dependency without a reason written next to its pin.
- [ ] `CHANGELOG.md` carries an entry under `[Unreleased]`.
- [ ] The README conformance table still states what is true, not what is intended;
      if this change moved a row, the row moved with it.

## A change to measurement code

Everything above, plus:

- [ ] New behavior has tests, including at least one refusal path: what the code does
      when it declines to measure is part of the behavior.
- [ ] Every rate the change produces carries numerator, denominator and interval, and
      passes `artifacts.check_all`; if it cannot be measured, it is not-measured
      shaped, never zero.
- [ ] Collections stay aggregate-only and in the order `artifacts.ORDERINGS` declares
      for them; no key ranks or scores.
- [ ] The determinism gate still holds over byte-identical inputs.
- [ ] If the change embeds a judgment call, a sensitivity variant measuring what the
      judgment is worth ships in the same change (the standard set by ADR 0006).
- [ ] If the change touches what is fetched from publishers: `sources.py`,
      `PROVENANCE.md`, and the schema guard move together, or the change does not ship.

## A change to published figures

Everything above, plus:

- [ ] It went through the deliberate-refresh procedure in `docs/RUNBOOK.md`, including
      the artifact diff against the pin it replaces.
- [ ] `PROVENANCE.md` gained a dated section saying what moved, sizes included.
- [ ] The committed `published/REPORT.md` renders from the committed
      `published/measurements.json`, which the report-matches-artifact test holds.

## A change to docs only

- [ ] No em dash or en dash anywhere (a test holds this, but do not make the test do
      your proofreading).
- [ ] Claims about the repository are checkable by a reader with the repository.
