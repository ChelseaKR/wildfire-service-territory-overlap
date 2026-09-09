# Contributing

## The one gate

```
make verify
```

CI runs the same target. The two must stay identical: if you add a check, add it to the
`verify` list, not only to the workflow.

`make verify` runs `uv lock --check`, ruff, `ruff format --check`, `mypy --strict`,
pytest with branch coverage against a 90% floor, `pip-audit`, an offline build over the
fixtures, and the determinism gate.

## Setup

```
uv sync --locked
```

`uv sync --locked`, never `--frozen`. `--frozen` means "do not resolve", not "the lock is
current": against a `pyproject.toml` the lockfile does not satisfy, `--frozen` exits 0 and
installs the stale set.

## What needs care

**`src/wildfire_service_territory_overlap/artifacts.py`.** These are the rules about what this project will say
about a named company. Weakening one is not a refactor. Every rule has a test that feeds
it something it must refuse; keep that pairing.

**`src/wildfire_service_territory_overlap/intervals.py`.** The only route a proportion takes to an artifact. If you
find yourself dividing two integers anywhere else, that is the bug.

**`src/wildfire_service_territory_overlap/sources.py`.** Reviewed endpoints and quoted publisher caveats. A change
here moves published numbers or points the acquisition somewhere new. `PROVENANCE.md`
must be updated in the same change; a test compares them.

**`src/wildfire_service_territory_overlap/acquire.py`.** Run by hand, never in CI. It must never gain a retry under
a different identity, a browser-shaped User-Agent, or a path that writes a partial walk.

## Things this project will not do

- Publish a rate without its denominator and its interval.
- Publish a zero for a measurement that could not be made.
- Publish a damage rate for a named utility, or order territories by any measured value.
- Read, infer, approximate, or publish the location of any physical utility asset, from
  any source.
- Award a contested record to one of the territories contesting it.
- Fetch an address, parcel number or assessed value it does not need.

A change that does any of these will be declined regardless of how well it is written.

## Refreshing the data

```
make acquire        # network, by hand, never in CI
make report         # rebuild published/ from data/raw/
```

Then copy the new feature counts, byte counts and hashes from `data/raw/acquisition.json`
into `src/wildfire_service_territory_overlap/sources.py`, update `PROVENANCE.md` and the figures in `README.md`,
and commit the new `published/` tree. `data/raw/` stays out of git.

## Style

Prose in comments and documentation explains why, not what. No em dashes or en dashes.

## Your first change, start to finish

A tour of the whole pipeline in about five minutes. It needs uv and nothing else, it
touches the network exactly once (`uv sync`), and every build below runs offline over
committed fixtures.

### 1. Build the offline report

```
uv sync --locked
make report-offline
```

That writes two files into `build/offline/`, and prints both paths:

- `measurements.json`, every measurement as data. It is the artifact; the document is
  rendered from it and never written by hand.
- `REPORT.md`, the generated document.

Open `build/offline/measurements.json` and look at the first key, `is_fixture`. It is
`true` here and `false` in `published/measurements.json`. That flag is the reason a
fixture build can never be mistaken for the published one: `make report-offline` passes
`--fixture`, the flag rides along inside the artifact, and a test asserts the published
artifact does not carry it. `build/` is not in git.

### 2. Find the invented geography

Open `build/offline/REPORT.md` and scroll to "Every published territory, in name order".
The utilities there are not real:

| Fixture territory | Type | What it is there to exercise |
|---|---|---|
| Alpha Electric Company | IOU | Ordinary containment, and the edge band |
| Beta Municipal Utility | POU | Overlaps Alpha, so the overlap is contested |
| Gamma Rural Cooperative | CO-OP | Ships as a bowtie, so the repair ledger has an entry |
| Delta Choice Energy | CCA | Overlaps Alpha entirely, and must be excluded by type |

`fixtures/README.md` says why they are invented rather than sampled: the real DINS file
carries structure-level records at their published coordinates, with site addresses and
parcel numbers, and a "small sample for the tests" cut from it would put real structures
into git for the convenience of a test suite.

Two things to notice in the report. Gamma's `geometry_state` reads `repaired`, which is
the bowtie being made valid before it is used. And Delta appears nowhere in the territory
table, because the inclusion rule excluded it by `Type`; it is named in the excluded
types section instead, with the reason.

### 3. Break something on purpose

A gate you have never watched refuse is a gate you are trusting rather than using. Break
two things, and notice that they are caught by different gates.

**Rename a fixture territory.** In `fixtures/else_iou_pou_sample.geojson`, change
`Alpha Electric Company` to anything else, then:

```
make test
```

It refuses, with around eight failures. The fixture geography is asserted by name across
`tests/`, because a test that says "the record landed in the right territory" has to name
which one.

Now run the other gate, without reverting yet:

```
make determinism
```

**It passes.** That is not a bug, and it is worth understanding before you trust either
gate. `make determinism` builds the fixtures twice and compares the two trees byte for
byte. A change to an input changes both builds identically, so it proves that the
pipeline is a function of its inputs; it says nothing about whether the inputs are the
ones you meant. Revert the rename now.

**Make two builds actually differ.** This is what the determinism gate is for:

```
make determinism
echo "edited" >> build/run-two/REPORT.md
tools/determinism.sh build/run-one build/run-two
```

It prints the two differing hashes and exits 1. Ask it to compare a tree that is not
there, and it exits 2 rather than calling an empty comparison a match:

```
tools/determinism.sh build/run-one build/absent
```

Both refusals matter because the byte-identical claim in `README.md` rests on this
script, and `tests/test_cli_and_determinism.py` runs it against trees that must fail it.
Nothing in `build/` is in git, so there is nothing to revert.

### 4. The gates, in the order `make verify` runs them

`docs/RUNBOOK.md` is the deep version, including what to do about each refusal.

| Target | What a failure there means |
|---|---|
| `lock-check` | `uv.lock` no longer satisfies `pyproject.toml`. Run `uv lock`. |
| `sync` | The locked dependency set would not install. |
| `lint` | ruff found a lint error, including a complexity over the cap of 10. |
| `format` | Code is not formatted. Run `uv run ruff format .`; the gate never rewrites for you. |
| `typecheck` | `mypy --strict` rejected `src`. |
| `test` | A test failed, or branch coverage fell below the 90% floor. |
| `audit` | pip-audit found a known vulnerability in the installed set. |
| `report-offline` | The pipeline refused to build, usually a publication rule in `artifacts.py`. |
| `determinism` | Two builds of byte-identical inputs disagreed. |

`make help` lists every target with one line. Bare `make` runs `verify`, not `help`.

### 5. Before you open a pull request

The checklist in `.github/PULL_REQUEST_TEMPLATE.md` is `docs/DEFINITION_OF_DONE.md`
copied item for item, and a test holds the two together. If your change adds or repairs
a gate, say what you broke to prove it can refuse, and what it printed.

## Commercial solicitation

Issues here are not open to bids. They are design records, written so a decision is
reconstructable later, rather than scope documents for outside quoting. Unsolicited offers to
implement one for a fee will be declined.

Contributions through the normal fork-and-PR process are welcome, and `good first issue` is the
place to start.
