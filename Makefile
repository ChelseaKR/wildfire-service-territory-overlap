.PHONY: help verify lock-check sync lint format typecheck test audit osv \
        report report-offline determinism acquire refresh-check

# Bare `make` runs the one gate, and says so rather than relying on `verify` happening
# to be the first target. Making `help` the default would change what a habitual
# keystroke does, from running every gate to printing a list, and a command quietly
# starting to do something else is the failure mode this repository is built around.
.DEFAULT_GOAL := verify

# Every target carries its one-line description on the same line, after `## `, so
# adding a target and documenting it are one edit. tests/test_provenance_and_standards.py
# refuses a target that has no description.
help:  ## list every target with one line; bare `make` still runs verify, not this
	@grep -hE '^[a-zA-Z][a-zA-Z0-9_-]*:.*## ' $(MAKEFILE_LIST) \
	  | sed 's/:.*## /|/' \
	  | awk -F'|' '{printf "  %-16s %s\n", $$1, $$2}'

# CI and `make verify` run the same list. The two MUST stay identical.
# See CONTRIBUTING.md and .github/workflows/ci.yml.
verify: lock-check sync lint format typecheck test audit report-offline determinism  ## the one gate: lock-check, sync, lint, format, typecheck, test, audit, report-offline, determinism, which is exactly what CI runs

# The lockfile-drift gate. `uv sync --frozen` is not one: against a pyproject.toml the
# lockfile does not satisfy, `uv lock --check` exits 1, `uv sync --locked` exits 1, and
# `uv sync --frozen` exits 0 and installs the stale set. `--frozen` means "do not
# resolve", not "the lock is current".
lock-check:  ## refuse a lockfile that does not satisfy pyproject.toml
	uv lock --check

sync:  ## install the locked dependency set into the virtualenv
	uv sync --locked

lint:  ## ruff over the whole repository
	uv run ruff check .

format:  ## refuse unformatted code, without rewriting it
	uv run ruff format --check .

typecheck:  ## mypy --strict over src
	uv run mypy --strict src

test:  ## pytest with branch coverage against the 90% floor
	uv run pytest -n auto --cov=src --cov-branch --cov-report=xml --cov-fail-under=90

audit:  ## pip-audit over the installed set
	uv run pip-audit

# The second vulnerability feed, locally. `.github/workflows/osv.yml` is the gate of
# record: it is a required check, it reads this same uv.lock with the same scanner
# version, and it fails the pull request. This target exists so the answer is available
# before the push rather than after it.
#
# It is deliberately NOT a prerequisite of `verify`. CI runs `make verify` byte for
# byte, so adding osv here would mean installing a Go binary on the runner to re-run a
# scan that osv.yml has already run against the same file: a second execution, not a
# second feed. `verify` and CI stay identical by staying out of each other's way.
#
# Fails closed on a finding, and fails loudly when the scanner is absent rather than
# passing quietly: a gate that reports success because it did not run is the defect
# this repository is built around.
osv:  ## osv-scanner over uv.lock, the second feed; osv.yml is the gate of record
	@command -v osv-scanner >/dev/null 2>&1 || { \
	  echo "osv-scanner is not installed. Install it (brew install osv-scanner, or"; \
	  echo "see https://google.github.io/osv-scanner/installation/) or read the result"; \
	  echo "of the required 'scan' check on the pull request instead."; \
	  exit 1; \
	}
	osv-scanner scan source --lockfile uv.lock

# Reviewer-supplied inclusion rule files, space separated, passed to `report` and
# `report-offline` as one `--inclusion-rule` each. Empty by default, and CI leaves it
# empty: a build given no rule file writes exactly the tree it wrote before the flag
# existed, which is what keeps published/measurements.json comparable across builds.
#
#   make report-offline INCLUSION_RULES=fixtures/inclusion_rule_without_co_op.json
#
INCLUSION_RULES ?=
INCLUSION_RULE_FLAGS = $(foreach rule,$(INCLUSION_RULES),--inclusion-rule $(rule))

# Build the published tree from locally acquired files. data/raw/ is never in git and
# never in CI, so this target only runs on a machine that has run `make acquire`.
report:  ## rebuild published/ from data/raw/, which only a machine that has run acquire has
	uv run python -m wildfire_service_territory_overlap.cli \
		--dins data/raw/dins_postfire.json \
		--iou-pou data/raw/else_iou_pou.geojson \
		--other data/raw/else_other.geojson \
		--counties data/raw/county_boundaries.geojson \
		$(INCLUSION_RULE_FLAGS) \
		--out published

# The same pipeline over committed fixtures: runs anywhere, output flagged is_fixture.
report-offline:  ## the same pipeline over the committed fixtures, offline, into build/offline
	uv run python -m wildfire_service_territory_overlap.cli --fixture \
		--dins fixtures/dins_sample.json \
		--iou-pou fixtures/else_iou_pou_sample.geojson \
		--other fixtures/else_other_sample.geojson \
		--counties fixtures/county_boundaries_sample.geojson \
		$(INCLUSION_RULE_FLAGS) \
		--out build/offline

# The gate behind the byte-identical claim. Two builds into two directories, compared by
# tools/determinism.sh, which refuses an empty or missing tree instead of calling it a
# match. tests/test_cli_and_determinism.py runs the script against trees that should fail
# it, so this gate is known to be able to fail.
determinism:  ## build the fixtures twice and refuse two trees that differ
	rm -rf build/run-one build/run-two
	uv run python -m wildfire_service_territory_overlap.cli --fixture \
		--dins fixtures/dins_sample.json \
		--iou-pou fixtures/else_iou_pou_sample.geojson \
		--other fixtures/else_other_sample.geojson \
		--counties fixtures/county_boundaries_sample.geojson \
		--out build/run-one
	uv run python -m wildfire_service_territory_overlap.cli --fixture \
		--dins fixtures/dins_sample.json \
		--iou-pou fixtures/else_iou_pou_sample.geojson \
		--other fixtures/else_other_sample.geojson \
		--counties fixtures/county_boundaries_sample.geojson \
		--out build/run-two
	tools/determinism.sh build/run-one build/run-two

# Network. Run by hand, never from a build. See PROVENANCE.md.
acquire:  ## touches the network: fetch the sources by hand into data/raw/
	uv run python -m wildfire_service_territory_overlap.acquire --out data/raw

# Network, and read-only: no row is read and nothing is written. Answers PROVENANCE.md's
# staleness triggers without the 180 MB the answer used to cost. Exit 0 means every
# trigger it checks was checked and none fired, 1 means one fired, and 2 means one could
# not be checked, which is not the same thing. Deliberately not a prerequisite of
# anything: a gate that goes red on a calendar date stops every unrelated change in the
# repository and teaches people to bypass it.
refresh-check:  ## touches the network, read-only: has the pin gone stale?
	uv run python -m wildfire_service_territory_overlap.refresh --check
