# Upstream gaps in `perimeter`

Roadmap item 4.4 says this project contributes fixes to
[`perimeter`](https://github.com/ChelseaKR/perimeter) where acquisition gaps surface
here, so the relationship stays "consume, do not re-implement" rather than drifting into
a local fork. This file is where a gap is named once it has been found: what it is, the
code here that compensates for it, and the change that would let the compensation go.

The failure mode being guarded against is a local workaround that quietly becomes
permanent. Writing one down is not the same as fixing it, and this file does not claim
any of these has been sent upstream. The pin is a commit rather than a branch, so an
upstream fix reaches this project only when the pin moves, deliberately.

## Re-audit of 2026-09-08, second pass, at the pin this project now runs

Against `perimeter` at commit `d0470bca45b6a1a2c254241537797fe8dc46ce38`, which is what
`pyproject.toml` pins and what `uv.lock` installs. The pass at `b35a8d67`, below, is kept
in full and closed gap 2; this is the gap that closing it revealed.

**Gap 5, raised and closed in the same session.** The half of gap 1 that was downstream
of gap 2 is now closed too.

The pass below records that the duplicated refusals went with the duplicated walk, and
noted that upstream's single-request reader was private. That was true and it was still a
gap: the next thing this project needs to read is the item metadata behind a territory
layer, so that `make refresh-check` can answer "has the publisher moved since the pin"
without downloading 180 MB to find out. There were two ways to do that at `b35a8d67`,
and both were bad. Write a sixth copy of the five refusals -- HTTPS only, an honest
User-Agent, the hard stop on 401, 403 and 429, a non-JSON answer read as a challenge
page, an error payload refused -- or import a private name and take a rename on the chin
at some future pin.

| Gap | State at `d0470bca` | What changed here |
|---|---|---|
| 5. The single-request reader is private, so a consumer that needs one writes the refusals again | **Closed.** `perimeter.acquire.fetch_document` is public, is a rename with no behaviour change, and its docstring says what it is for and that a caller reading a *layer* still wants `iter_features` | `refresh.py` reads item metadata through it. There is no fetch in this repository and no copy of any refusal |

`refresh.py` is the first module here written with no local network code at all: it
imports the reader, the count and the exception types, and adds only the comparisons this
project makes.

## Re-audit of 2026-09-08, first pass

Against `perimeter` at commit `b35a8d67ad1b04311663371acda1c561e520bb31`. The two audits below are kept in full,
for the same reason each of them kept the one before it: they are the record of what was
true at `3a6aa47` and at `dac60195`, and `dac60195` is the commit the retrieval currently
in `published/` was acquired under.

**Gap 2 is closed. Every gap this file has ever recorded is now closed, and the last two
compensations are gone from this repository.**

Upstream #84 added `out_format` to `iter_features`, defaulting to `json` so its own pinned
retrievals stay byte-reproducible. That is the one argument the previous re-audit narrowed
the ask down to, and it is what the three polygon layers needed.

| Compensation | State |
|---|---|
| `fetch_feature_pages`, a second paged walk with a second copy of the offset rule | **Retired.** One call to `perimeter.acquire.iter_features` with `out_format="geojson"`. What keeps the name is a four-line binding of this project's User-Agent, the format and the spatial reference |
| A second `_get`, with a second copy of every refusal around a request | **Deleted.** HTTPS only, stop on 401, 403 and 429, refuse a non-JSON challenge page, refuse an error payload: one copy of each, upstream, where a fix to any of them now reaches this project when the pin moves |
| A second `layer_record_count` | **Deleted.** It existed only because it needed the local `_get`. What is left is a one-line binding so the count is always asked for under this project's own name |

Measured on the diff: `src/wildfire_service_territory_overlap/acquire.py` deletes 89
lines and adds 59, a net 30 shorter, and loses three imports (`time`, `urllib.error`,
`urllib.request`). The module no longer contains the word `urlopen`. Most of what was
added is the docstrings saying what the two remaining functions are for and what they
used to be.

### The refusal tests stayed, and they are the point

Every refusal test in `tests/test_acquire.py` now exercises upstream's code from here, and
every one of them still passes without its assertion changing: the non-HTTPS refusal, all
three access-control codes, a 500, an HTML challenge page, an error payload, a
`returnCountOnly` answer with no count, and a boolean offered as a count. That is the
evidence the duplication was a duplication rather than two different behaviours that
happened to look alike.

They stay for the reason Gap 3 states below. A consumer that stops checking a
dependency's behaviour because the dependency says it checks its own is trusting a
version of the code it has not read, and the pin exists so that an upstream change
arrives deliberately. These assertions are what would notice if a later pin landed on a
walk that had lost one of them.

### One thing was found downstream and fixed upstream, in the same session

The local walk checked that `features` was a list. Upstream did not, and `yield from` over
a mapping yields its **keys**: measured on upstream's tree before the fix, a page carrying
`{"features": {"OBJECTID": 1, "YEAR_": 2020}}` made `iter_features` yield
`['OBJECTID', 'YEAR_']` and stop, after one request, with nothing raised.

Retiring the compensation while keeping that one check downstream would have left a
fragment of the duplication in place for no reason, so it went upstream instead
(`perimeter` #86) and the pin here is the commit that carries it. The assertion in
`tests/test_acquire.py` is now made against upstream's message.

### One behaviour changed, and the guard that makes it safe was already here

The local walk paged until it was handed an empty page. Upstream stops earlier: a page
shorter than the one it asked for, with no `exceededTransferLimit`, is the end of the
layer, which is what a GeoServices layer means by that combination. The local walk made
one more request than upstream does and did not rely on the flag.

Nothing about the acquisition rests on that difference, because `assert_walk_is_whole`
compares what the walk collected against the layer's own count, read before and after.
A walk that stopped early writes nothing and says so.

This has not been run against the live endpoints. The request this project sends is the
same set of parameters in a different order (`outSR` moves to the end, since upstream
sends it only when given and this project gives it), which does not change a response, but
the sha256 figures in `sources.py` are from the retrieval of `dac60195` and the next
acquisition is what will confirm it.

## Re-audit of 2026-09-07

Against `perimeter` at commit `3a6aa47ae9e755a256614bc124a6db960d60dc7a`, which is what
`pyproject.toml` pinned at the time and what `uv.lock` installed. The audit of 2026-09-05 below is kept
in full: it is the record of what was true at `dac60195`, which is the commit the
retrieval currently in `published/` was acquired under.

**Three of the four gaps closed upstream. Two compensations are gone from this
repository. One gap is still open, for a reason the original entry did not anticipate.**

The distribution also renamed. Upstream is now `perimeter-wildfire` on the manifest and
still `perimeter` on the import, because `perimeter` on PyPI is YunoJuno's Django
middleware. That is not a gap and it is worth recording, because it is a break that reads
as something else: pinning the new commit under the old name fails with

```
Package metadata name `perimeter-wildfire` does not match given name `perimeter`
```

which a reader takes for a bad revision rather than a rename. `pyproject.toml` names the
distribution and had to move with it. Nothing that imports `perimeter` changed.

| Gap | State at `3a6aa47` | What changed here |
|---|---|---|
| 1. The walk sends perimeter's User-Agent | **Closed.** `_get`, `layer_record_count`, `iter_features` and `fetch_layer` all take `user_agent` | `acquire_dins` passes this project's. The DINS walk now names the caller |
| 2. The walk cannot return geometry | **Open at this pin.** Geometry and spatial reference arrived; output format did not. Closed at `b35a8d67`, above | Nothing yet. `fetch_feature_pages` stays, and so does the duplicated offset rule |
| 3. Completeness is one count read once | **Closed upstream.** `acquire` recounts after the walk and `identifier_failure` is public | Nothing, deliberately. See below |
| 4. No `py.typed` | **Closed.** `src/perimeter/py.typed` ships and is packaged | Both mypy overrides deleted |

### Gap 1 is closed, and the compensation it named is half gone

`layer_record_count`, `iter_features` and `fetch_layer` take `user_agent`, defaulting to
upstream's own constant. `acquire_dins` now passes `USER_AGENT`, so every request this
project makes names this project, the 132,522-record DINS layer included.

Measured with the socket substituted: `tests/test_acquire.py` asserted, until today, that
every DINS request carried `perimeter-coverage/0.1` and that this project's own name was
absent. Its docstring said it would fail the day the pin moved onto a walk that lets a
caller identify itself. That day is today, and the assertion is now the opposite one.

The second half of gap 1 is not closed and cannot be closed on its own. The refusals
inside the copied `_get`, HTTPS only, stop on 401, 403 and 429, refuse a non-JSON
challenge page, refuse an error payload, still exist twice, because `fetch_feature_pages`
still needs a fetch upstream does not expose. That duplication is downstream of gap 2 and
goes when gap 2 does.

### Gap 2 is still open, and the reason is narrower than the original entry

The original entry asked for "geometry, output format and output spatial reference as
arguments to `fetch_layer`, or the offset loop factored out". Upstream delivered the
offset loop, as `iter_features`, with `return_geometry` and `out_sr`. It did not deliver
the format.

`iter_features` hard-codes `"f": "json"`, so it yields GeoServices features,
`{"attributes": ..., "geometry": ...}` with Esri geometry. The two CEC territory layers
and the county layer are read here as `f=geojson` and written as GeoJSON feature
collections, which is what `geometry.py` and `_write` consume. Reading them through
`iter_features` would mean converting Esri rings to GeoJSON here, which is more
re-implementation than the offset loop it would retire, and it is conversion of the
geometry this project's whole measurement runs on.

So the ask is now one argument rather than three: an output format on `iter_features`,
defaulting to `json` so upstream's own pinned retrievals stay byte-reproducible. Raised
upstream rather than only recorded here, which is what roadmap 4.4 asks for.

### Gap 3 is closed upstream and the local check stays anyway

`perimeter.acquire.acquire` now reads the count before and after the walk and splits the
refusal into a republication and a short walk, and `identifier_failure` checks the
identifiers for repeats and for going backwards. That is the change this project asked
for and it landed.

It retires nothing here, and the reason is worth stating rather than leaving as an
apparent oversight. Those checks live inside upstream's `acquire`, which writes upstream's
own file and manifest. This project calls `layer_record_count` and `fetch_layer` directly,
because it writes its own file in its own format, so upstream's checks are not on the path
this project takes.

`assert_walk_is_whole` therefore stays, and it would stay even if it were. A consumer that
stops checking a dependency's output because the dependency says it checks its own is
trusting a version of the code it has not read. The pin exists so that upstream changes
reach this project deliberately; a check that is only as good as the pinned commit is
exactly what the pin is there to avoid relying on.

### Gap 4 is closed and both overrides are deleted

`src/perimeter/py.typed` ships and `[tool.hatch.build.targets.wheel]` names it under
`artifacts`. Measured on 2026-09-07 at this pin: `uv run mypy --strict src` reports
`Success: no issues found in 14 source files` with

- `perimeter.*` removed from the `ignore_missing_imports` override, and
- the `disallow_subclassing_any = false` override on
  `wildfire_service_territory_overlap.acquire` deleted entirely.

`IncompleteAcquisition` subclasses upstream's `AcquisitionFailed` under `--strict` with
nothing relaxed, because the base class resolves to a real class rather than to `Any`.

`tests/test_provenance_and_standards.py` already refused an `ignore_missing_imports` entry
naming a package that ships the marker, so this removal was forced rather than
remembered: the pin could not move without it.

## Audit of 2026-09-05

Against `perimeter` at commit `dac60195c50786f33f69a8fab70b6230894ed374`, which is what
`pyproject.toml` pins and what `uv.lock` installs. Read at that commit, not on `main`.

Read in full on this side: `src/wildfire_service_territory_overlap/acquire.py`,
`tests/test_acquire.py`, `src/wildfire_service_territory_overlap/sources.py`, the schema
guard and `REQUIRED_COLUMNS` in `src/wildfire_service_territory_overlap/placement.py`,
and the two mypy overrides in `pyproject.toml`. Read at the pinned commit upstream:
`perimeter/acquire.py`, `perimeter/sources.py`, the required-column lists in
`perimeter/schema.py`, `perimeter/dins.py`, and upstream's own `pyproject.toml`,
`Makefile` and `tests/test_acquire.py`.

Four gaps, all in the acquisition. Each row below is expanded underneath.

| Gap | What compensates for it here | The upstream change |
|---|---|---|
| The walk sends `perimeter`'s User-Agent and takes no other | A second copy of the fetch path, so three of the four layers can name this project | A `user_agent` argument, defaulting to today's constant |
| The walk cannot return geometry | `fetch_feature_pages`, a second paged walk holding a second copy of the offset rule | Geometry, format and spatial reference as arguments, or the offset loop exposed |
| Completeness is one count, read once, before the walk | A second count read after the walk, plus uniqueness and ordering checks on the identifiers | Read the count again after the walk, and check the identifiers |
| The package is checked with `mypy --strict` and ships no `py.typed` | Two mypy overrides, one narrowed to a single rule in a single module | One empty file at `src/perimeter/py.typed` |

### Gap 1: the walk sends its own name and takes no other

`perimeter.acquire` reads `USER_AGENT` from a module constant inside its private `_get`,
and neither `layer_record_count` nor `fetch_layer` accepts a User-Agent. A consuming
project has no way to say who is actually calling.

Measured here on 2026-09-05 with the socket substituted: every request the DINS
acquisition makes, the two count queries and each page of the walk, goes out as
`perimeter-coverage/0.1 (+https://github.com/ChelseaKR/perimeter)`. That is the largest
of the four layers at 132,522 records. The other three carry this project's own
User-Agent, because `acquire.py` holds its own `USER_AGENT`, its own `_get` and its own
`layer_record_count`, the last two near-copies of upstream's.

Two costs, not one. An operator at CAL FIRE reading their logs sees a project name that
does not lead back to the caller, which is what an honest User-Agent is for. And the
refusals inside the copied `_get`, HTTPS only, stop on a 401, 403 or 429, refuse a
non-JSON challenge page, refuse an error payload, now exist twice, so a fix to
upstream's copy does not reach this project even when the pin moves.

The upstream change: a `user_agent` argument on `layer_record_count` and `fetch_layer`,
defaulting to the constant they use today and passed through to `_get`. Upstream already
holds a test that its request names the project rather than imitating a browser. This
asks only that the project it names can be the caller.

### Gap 2: the paged walk cannot return geometry

`fetch_layer` pins `returnGeometry=false` and `f=json`. That is the right default for
`perimeter`, which measures how complete the fields of a file are and needs no polygons
to do it, and upstream tests the field lists to keep geometry out of them.

The consequence here is that the two territory layers and the county layer, which are
polygons, cannot be read through it. `fetch_feature_pages` in `acquire.py` is a second
paged walk carrying a second copy of the one rule the pin exists to avoid duplicating:
step the offset by the rows received, never by the page size asked for. That rule was
wrong once, upstream, and there are now two implementations of it in this project's
dependency graph. The local `_write` similarly duplicates upstream's public `write_rows`
because that writer takes attribute rows and cannot write a GeoJSON feature collection.

The upstream change: geometry, output format and output spatial reference as arguments
to `fetch_layer`, or the offset loop factored out so a caller that needs geometry reuses
the stepping rule instead of rewriting it. Either one, not both.

### Gap 3: completeness is one count, read once, before the walk

`perimeter.acquire.acquire` reads the layer's own record count before the walk and
compares it with the number of rows collected. It reads it once, and it compares only
the total.

Reading it once leaves an ambiguity upstream's own refusal message concedes: "If the
layer was republished mid-walk, re-run the acquisition; if it was not, the walk is
dropping records" hands the operator a guess. Comparing only the total is blind to a
different failure: a page served twice while another is stepped over produces exactly
the right count and the wrong rows.

What compensates here: `acquire_dins` reads the count before and after the walk and
raises `IncompleteAcquisition` naming a republication when the two disagree, so the
operator is told which of the two happened. `assert_walk_is_whole` then refuses
identifiers that repeat, and identifiers that do not come back strictly increasing.
`tests/test_acquire.py` exercises all three refusals against walks that should fail
them.

The upstream change: read the count again after the walk and split the one refusal into
two, and check the identifiers for uniqueness and strict increase. The walk already asks
for `orderByFields=OBJECTID ASC`, and `OBJECTID` is the first entry of both
`FRAP_REQUIRED_COLUMNS` and `DINS_REQUIRED_COLUMNS`, so both checks are available
without asking the service for anything it is not already sending.

### Gap 4: the package is typed and does not say so

Upstream sets `strict = true` under `[tool.mypy]` and its `verify` target runs
`mypy --strict src`. The wheel built from the pinned commit carries no `py.typed`
marker, so every consumer sees an untyped package.

What that costs here is both mypy overrides in `pyproject.toml`, measured on 2026-09-05:

- dropping `perimeter.*` from `ignore_missing_imports` produces
  `Skipping analyzing "perimeter.acquire": module is installed, but missing library
  stubs or py.typed marker`;
- dropping `disallow_subclassing_any = false` produces
  `Class cannot subclass "AcquisitionFailed" (has type "Any")`, because the base class
  resolves to `Any` for the same reason;
- adding an empty `py.typed` to the installed package and dropping both overrides leaves
  `mypy --strict src` green, so the marker is the whole of the fix as far as this
  project is concerned.

The upstream change: one empty file at `src/perimeter/py.typed`. Hatchling includes it in
the wheel under the existing `packages` setting. It is a claim about the whole package
rather than about `acquire` alone, which is why it belongs behind upstream's own strict
run and is not asserted from here.

## Checked and found not to be a gap

Recorded so the next audit does not re-open them.

- **`fetch_layer` ends the walk on a short page when the service sets no
  `exceededTransferLimit`.** This looked like trust in a flag the service need not send.
  It is deliberate and tested upstream, in `test_a_short_page_ends_the_walk_even_without_the_transfer_flag`
  and `test_a_full_page_without_the_transfer_flag_is_still_followed`, and a walk cut
  short that way is refused by the count check rather than written. The walk here is
  more conservative, ending only on an empty page, which costs one extra request per
  layer and is a difference in taste, not a defect to report.
- **The fetched field list.** `fetch_layer` already takes its fields as an argument, so
  this project passes its own nine and never downloads the address and parcel columns
  upstream fetches for its own purposes. Nothing here works around the upstream list.
- **`sources.py` and the schema guard.** `REQUIRED_COLUMNS` in `placement.py` is the
  nine columns this project measures, a deliberate subset chosen by the refusal to
  download addresses, not a copy of `DINS_REQUIRED_COLUMNS` kept in sync by hand.
  Nothing in either file exists because upstream fails to surface something.
- **The exception types.** `AcquisitionBlocked` and `AcquisitionFailed` are public
  upstream and are what this module raises. `IncompleteAcquisition` is a local subclass
  because upstream has no name for a walk that finished without evidence, which is a
  consequence of Gap 3 rather than a separate one.
