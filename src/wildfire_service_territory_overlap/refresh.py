"""The deliberate refresh, in two modes: ask whether the pin is stale, then run it.

``PROVENANCE.md`` names three triggers under Cadence and ``docs/RUNBOOK.md`` describes the
refresh as a sequence of hand-run steps. The triggers are the part nobody can answer from
their desk: two of them are questions about somebody else's server, and the only way to
ask has been to run the whole acquisition, which downloads 180 MB and 132,522 structure
records to find out whether anything moved.

This asks instead. ``--check`` is read-only and reads no rows: it takes the layer's own
record count under the walk's predicate, and the item metadata behind the two territory
layers, and compares both against what ``sources.py`` pins. Nothing is written, nothing is
acquired, and no artifact moves.

``--run`` is the other half, and the reason it is one command rather than eight numbered
steps is that a sequence can be run out of order and the step that matters most -- the
comparison against what is already published -- is the easiest to leave out. It acquires
into a fresh directory, builds into a fresh directory, and compares the build against
``published/measurements.json``, **in that order, stopping at the first refusal**. It
writes ``refresh-receipt.json`` and stops. It does not touch ``published/``, does not
commit, does not tag, and does not edit ``sources.py``: adoption is a person's, and the
receipt is what that person reads before doing it.

**A receipt exists only for a run that finished.** Every refusal leaves none. A short
walk leaves no build directory either, because the build is never reached. This matters
more than it looks: a receipt is the document a later reader treats as the record of a
refresh, and one written after a step that refused would be a record of something that
did not happen. Where the comparison itself is the refusal (a value was removed and
nothing said it was deliberate) the full diff is printed instead, so the refusal costs
no information.

**The provenance block in the artifact ``--run`` builds is the old pin's.** It is read
from ``sources.py``, which only a person can update, and updating it is the first line
of the adoption note the receipt carries. The receipt therefore records what each layer
actually returned beside what ``sources.py`` pins, and whether the two agree, so the
edit can be made from the receipt rather than from a terminal that has scrolled.

**What ``--check``'s exit code means, exactly.**

- ``0`` -- every declared trigger this command checks was checked, and none fired.
- ``1`` -- a declared trigger fired. The pin is stale by this project's own cadence.
- ``2`` -- a declared trigger could not be checked. This is not ``0``, and the distinction
  is the whole reason the command exists: exit ``0`` meaning "I asked and the answer was
  no" and exit ``0`` meaning "I could not ask" would put a stale pin and a healthy pin
  behind the same green, which is the defect class this repository keeps finding.

**And ``--run``'s, which reads the same way and is a different question.**

- ``0`` -- acquire, build and compare all ran, and the receipt is written.
- ``1`` -- a step refused. The refusal names the step and nothing after it happened.
- ``2`` -- the comparison could not be made at all: the published artifact was
  unreadable, was not a JSON object, or the two artifacts carried no values between
  them. A comparison that did not happen is not a comparison in which nothing moved,
  and the two do not share an exit code here either.

Two things it deliberately does not do, both stated on every run rather than left for a
reader to notice.

**Trigger 3 is not checked here.** "This pipeline changed shape" is a judgment about this
repository, not a fact about a server, and a command that reported it as passing would be
claiming to have checked something it cannot see. It is listed every time as not checked
here, and it does not move the exit code.

**A record count that has moved does not fire anything.** It is reported, with the pinned
figure beside it, because a layer that has grown is the plainest evidence there is that a
published measurement describes a superseded file. It is not one of the three triggers
``PROVENANCE.md`` declares, and adding a fourth is an edit to that document rather than a
line of code here.

**This has never been run against the live endpoints.** Nothing in this repository does:
``acquire.py`` is the same, and both are excluded from CI on purpose. The record count is
read through the call the acquisition already makes, so its shape is proven; the item
metadata request is not. Every way that answer can fail to be a date -- a refusal, an
error payload, a missing field, a number that is not a timestamp -- is an *unmeasurable*
naming the URL and what came back, never a trigger that did not fire.
"""

from __future__ import annotations

import argparse
import enum
import importlib.metadata as metadata
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from perimeter.acquire import AcquisitionBlocked, AcquisitionFailed, fetch_document

from wildfire_service_territory_overlap import artifact_diff, cli
from wildfire_service_territory_overlap.acquire import (
    USER_AGENT,
    Acquired,
    acquire_all,
    layer_record_count,
)
from wildfire_service_territory_overlap.artifacts import PublicationRefused
from wildfire_service_territory_overlap.sources import (
    COUNTIES,
    DINS,
    ELSE_IOU_POU,
    ELSE_OTHER,
    RETRIEVED,
    Source,
)

ITEM_METADATA_URL = "https://www.arcgis.com/sharing/rest/content/items/{item_id}?f=json"
"""Where an ArcGIS Online item's own metadata is published.

``sources.py`` records an ``item_id`` and an ``item_modified`` for the layers whose
publisher exposes one, and this is the document those two fields were read from. The
layer's ``lastEditDate`` under ``FeatureServer/0`` is a different fact about a different
object, so it is not substituted for this one.
"""

STALE_AFTER_DAYS = 365
"""Trigger 1's cadence, from PROVENANCE.md: "at least once every twelve months"."""

# The two layers trigger 2 is written about. It says "either territory layer", and it
# says so for a reason: the boundaries are what this project measures against, and a
# boundary that moved invalidates every placement. The damage inspections growing is a
# different fact, reported below as an observation.
TERRITORY_LAYERS: tuple[Source, ...] = (ELSE_IOU_POU, ELSE_OTHER)

ALL_SOURCES: tuple[Source, ...] = (DINS, ELSE_IOU_POU, ELSE_OTHER, COUNTIES)

EXIT_NO_TRIGGER = 0
EXIT_TRIGGER_FIRED = 1
EXIT_COULD_NOT_CHECK = 2


class Verdict(enum.Enum):
    """What became of one trigger on one run. Four values, and three of them are not two.

    ``UNMEASURABLE`` and ``NOT_CHECKED_HERE`` are both "no answer" and they are not the
    same claim. The first means this command asked and could not read the reply, which is
    a fault to chase. The second means it never asks, by design, and says so every time.
    """

    FIRED = "fired"
    NOT_FIRED = "not_fired"
    UNMEASURABLE = "unmeasurable"
    NOT_CHECKED_HERE = "not_checked_here"


@dataclass(frozen=True)
class Trigger:
    """One of PROVENANCE.md's declared triggers, and what this run found."""

    name: str
    question: str
    verdict: Verdict
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.name,
            "question": self.question,
            "verdict": self.verdict.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CountObservation:
    """What one layer says it holds now, against what the pin says it held."""

    source_key: str
    pinned: int
    now: int | None
    detail: str

    @property
    def moved(self) -> bool:
        return self.now is not None and self.now != self.pinned

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_key,
            "pinned": self.pinned,
            "now": self.now,
            "moved": None if self.now is None else self.moved,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CheckResult:
    """Everything one `--check` run found."""

    retrieved: str
    as_of: str
    triggers: tuple[Trigger, ...]
    counts: tuple[CountObservation, ...]

    @property
    def exit_code(self) -> int:
        """Fired beats unmeasurable beats clean.

        A trigger that fired is actionable whatever else could not be read, so it wins.
        Observations never reach this: the exit code is a statement about the three
        declared triggers and nothing else, which is what lets the contract be written
        down in one sentence.
        """
        verdicts = {trigger.verdict for trigger in self.triggers}
        if Verdict.FIRED in verdicts:
            return EXIT_TRIGGER_FIRED
        if Verdict.UNMEASURABLE in verdicts:
            return EXIT_COULD_NOT_CHECK
        return EXIT_NO_TRIGGER

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "refresh-check",
            "as_of": self.as_of,
            "pin": {"retrieved": self.retrieved},
            "exit_code": self.exit_code,
            "triggers": [trigger.to_dict() for trigger in self.triggers],
            "record_counts": [count.to_dict() for count in self.counts],
        }


def _parse_iso_date(value: str) -> date | None:
    """A date, or ``None`` for anything that is not one. Never a guess."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def age_trigger(retrieved: str, today: date) -> Trigger:
    """Trigger 1, with the third state a two-way age check does not have.

    A date this command cannot read, and a date in the future, are both unmeasurable
    rather than fresh. A future retrieval date yields a negative age, which satisfies
    "younger than 365 days" permanently: it is not a young pin, it is a broken record or
    a broken clock, and reporting it as fresh would hide whichever it is for good.
    """
    question = (
        "Is the pin more than twelve months old? PROVENANCE.md: the record set grows "
        "through every fire season, so a year-old pin describes a year that has since "
        "been appended to it."
    )
    pinned = _parse_iso_date(retrieved)
    if pinned is None:
        return Trigger(
            name="age",
            question=question,
            verdict=Verdict.UNMEASURABLE,
            detail=(
                f"sources.py records RETRIEVED as {retrieved!r}, which is not an ISO "
                "date. The age of the pin cannot be computed from it, and an age that "
                "cannot be computed is not a young age."
            ),
        )
    days = (today - pinned).days
    if days < 0:
        return Trigger(
            name="age",
            question=question,
            verdict=Verdict.UNMEASURABLE,
            detail=(
                f"the pin is dated {retrieved}, which is {-days} days after today "
                f"({today.isoformat()}). A retrieval that has not happened yet is a "
                "broken record or a broken clock, and either way its age is not a "
                "number. Left unmeasurable rather than counted as fresh, because a "
                "negative age satisfies a twelve-month check forever."
            ),
        )
    if days > STALE_AFTER_DAYS:
        return Trigger(
            name="age",
            question=question,
            verdict=Verdict.FIRED,
            detail=(
                f"the pin is dated {retrieved} and is {days} days old, past the "
                f"{STALE_AFTER_DAYS}-day cadence."
            ),
        )
    return Trigger(
        name="age",
        question=question,
        verdict=Verdict.NOT_FIRED,
        detail=(
            f"the pin is dated {retrieved} and is {days} days old, inside the "
            f"{STALE_AFTER_DAYS}-day cadence."
        ),
    )


def _read_item_modified(source: Source, fetch: Any) -> tuple[date | None, str]:
    """The item's published modification date, or why there is not one.

    Every failure is the second half of the tuple and never a date. The refusals inside
    ``fetch`` already separate a blocked endpoint from a broken one; what this adds is the
    two ways a 200 can carry no answer, a missing field and a value that is not a
    timestamp, which are exactly the ways a check like this reports "nothing changed".
    """
    url = ITEM_METADATA_URL.format(item_id=source.item_id)
    try:
        payload = fetch(url, user_agent=USER_AGENT)
    except (AcquisitionBlocked, AcquisitionFailed) as error:
        return None, f"{url} could not be read: {error}"
    raw = payload.get("modified")
    if raw is None:
        return None, (
            f"{url} answered with no 'modified' field. Keys present: "
            f"{sorted(payload)!r}. An answer this command cannot read is not an answer "
            "that the layer has not moved."
        )
    if not isinstance(raw, int) or isinstance(raw, bool):
        return None, (
            f"{url} answered 'modified': {raw!r}, which is not an epoch timestamp in "
            "milliseconds. Nothing is coerced here; a timestamp that has to be guessed "
            "at is not one."
        )
    try:
        moved = datetime.fromtimestamp(raw / 1000, tz=UTC).date()
    except (OverflowError, OSError, ValueError):
        return None, (
            f"{url} answered 'modified': {raw!r}, which is a number and is not a point "
            "in time this platform can represent."
        )
    return moved, f"{url} reports {moved.isoformat()}"


def publisher_trigger(
    fetch: Any, layers: tuple[Source, ...] = TERRITORY_LAYERS
) -> Trigger:
    """Trigger 2, over the two layers PROVENANCE.md names.

    One layer that cannot be read makes the whole trigger unmeasurable, deliberately.
    "One of the two moved and I could not ask the other" is not "neither moved", and a
    trigger reported per layer would let a reader take the half that was answered for the
    whole question.
    """
    question = (
        "Has either territory layer been modified since the retrieval date? "
        "PROVENANCE.md: the boundaries are what this project measures against; when "
        "they change, the measurement starts over rather than being patched."
    )
    if not layers:
        # A rule that iterates over nothing reports the same clean line as a rule that
        # examined everything and found nothing. There is no caller that passes an empty
        # set and there never should be, so this is a refusal rather than a branch.
        raise ValueError(
            "trigger 2 is written about specific territory layers, and a check over none "
            "of them would report that the publisher had not moved, having asked nobody"
        )
    fired: list[str] = []
    unreadable: list[str] = []
    clean: list[str] = []
    for source in layers:
        if not source.item_id:
            unreadable.append(
                f"{source.key}: sources.py records no item id, so there is no item "
                "metadata document to ask."
            )
            continue
        pinned = _parse_iso_date(source.item_modified)
        if pinned is None:
            unreadable.append(
                f"{source.key}: sources.py records item_modified as "
                f"{source.item_modified!r}, which is not an ISO date, so there is "
                "nothing to compare an answer against."
            )
            continue
        moved, detail = _read_item_modified(source, fetch)
        if moved is None:
            unreadable.append(f"{source.key}: {detail}")
        elif moved > pinned:
            fired.append(
                f"{source.key}: pinned at {pinned.isoformat()}, {detail}, which is later."
            )
        else:
            clean.append(
                f"{source.key}: pinned at {pinned.isoformat()}, {detail}, which is not "
                "later."
            )
    if fired:
        return Trigger(
            name="publisher_moved",
            question=question,
            verdict=Verdict.FIRED,
            detail=" ".join(fired + unreadable),
        )
    if unreadable:
        return Trigger(
            name="publisher_moved",
            question=question,
            verdict=Verdict.UNMEASURABLE,
            detail=" ".join(unreadable + clean),
        )
    return Trigger(
        name="publisher_moved",
        question=question,
        verdict=Verdict.NOT_FIRED,
        detail=" ".join(clean),
    )


def pipeline_trigger() -> Trigger:
    """Trigger 3, which this command does not check and says so on every run."""
    return Trigger(
        name="pipeline_shape",
        question=(
            "Has this pipeline changed shape since the pin? PROVENANCE.md: a new "
            "measurement cannot reach an old pin, because data/raw/ is never committed."
        ),
        verdict=Verdict.NOT_CHECKED_HERE,
        detail=(
            "This is a judgment about this repository rather than a fact about a "
            "server, and nothing here can see it. It is listed on every run so that a "
            "clean exit is never read as three triggers checked, and it does not move "
            "the exit code."
        ),
    )


def count_observations(
    sources: tuple[Source, ...] = ALL_SOURCES, *, count: Any = layer_record_count
) -> tuple[CountObservation, ...]:
    """What each layer says it holds now, beside what the pin says it held.

    Not a trigger. PROVENANCE.md declares three and a moved record count is not one of
    them; adding a fourth is an edit to that document. It is reported because a layer
    that has grown is the plainest evidence there is that the published measurement
    describes a superseded file, and because leaving it out would mean this command asked
    the cheapest question there is and threw the answer away.
    """
    observations: list[CountObservation] = []
    for source in sources:
        try:
            now = count(source.endpoint)
        except (AcquisitionBlocked, AcquisitionFailed) as error:
            observations.append(
                CountObservation(
                    source_key=source.key,
                    pinned=source.feature_count,
                    now=None,
                    detail=f"the layer's own count could not be read: {error}",
                )
            )
            continue
        if now == source.feature_count:
            detail = (
                f"the layer holds {now:,} records, the number the pin was built on."
            )
        else:
            delta = now - source.feature_count
            direction = "more" if delta > 0 else "fewer"
            detail = (
                f"the layer holds {now:,} records, {abs(delta):,} {direction} than the "
                f"{source.feature_count:,} the pin was built on. This is not one of the "
                "three triggers PROVENANCE.md declares and does not move the exit code."
            )
        observations.append(
            CountObservation(
                source_key=source.key,
                pinned=source.feature_count,
                now=now,
                detail=detail,
            )
        )
    return tuple(observations)


def check(
    *,
    today: date | None = None,
    fetch: Any = None,
    count: Any = layer_record_count,
    sources: tuple[Source, ...] = ALL_SOURCES,
    layers: tuple[Source, ...] = TERRITORY_LAYERS,
) -> CheckResult:
    """Run every check this command makes, and return what they found.

    ``today``, ``fetch`` and ``count`` are parameters so a test can supply all three and
    reach every branch without a socket or a clock. Their defaults are what the command
    line uses, so a test that leaves one out is testing the shipped path for it.
    """
    if fetch is None:
        fetch = fetch_document
    as_of = today if today is not None else datetime.now(tz=UTC).date()
    return CheckResult(
        retrieved=RETRIEVED,
        as_of=as_of.isoformat(),
        triggers=(
            age_trigger(RETRIEVED, as_of),
            publisher_trigger(fetch, layers),
            pipeline_trigger(),
        ),
        counts=count_observations(sources, count=count),
    )


# --- `--run`: acquire, build, compare, and stop -------------------------------------
#
# The sequence docs/RUNBOOK.md used to describe as eight numbered steps, in one command
# that refuses to do them out of order. Nothing below adopts anything: `published/` is
# read and never written, `sources.py` is read and never edited, and the last thing this
# writes is a receipt for a person to read.

RAW_DIR_NAME = "raw"
BUILD_DIR_NAME = "build"
RECEIPT_NAME = "refresh-receipt.json"

STEP_WORKDIR = "workdir"
STEP_ACQUIRE = "acquire"
STEP_BUILD = "build"
STEP_COMPARE = "compare"

EXIT_REFRESH_DONE = 0
EXIT_REFRESH_REFUSED = 1
EXIT_REFRESH_UNREADABLE = 2

ADOPTION: tuple[str, ...] = (
    "Read the diff above and the built report end to end. The figures are checked by "
    "machinery; whether they still say something coherent is not.",
    "Update src/wildfire_service_territory_overlap/sources.py from the retrievals block "
    "in this receipt: retrieval date, feature count, byte count and SHA-256 per layer. "
    "Until that edit lands, the artifact built here carries the previous pin's dates in "
    "its provenance block.",
    "Rebuild after that edit, because the provenance block is part of the artifact and "
    "the build above predates the edit.",
    "Copy the build into published/ and write a dated PROVENANCE.md section saying what "
    "moved, following the 2026-08-17 pattern. Add a CHANGELOG.md entry, and update the "
    "README status line if the headline moved.",
    "Commit published/ and the source-record edits together. Never commit data/raw/.",
)
"""What a person does after a completed run. Carried in the receipt rather than only in
the runbook, because the receipt is what gets read at the moment the work happens."""


class RefreshRefused(Exception):
    """One step of a refresh refused, and nothing after it ran.

    ``step`` is the named step rather than a free-text prefix so a caller can tell a
    refused acquisition from a refused comparison without reading the sentence. The two
    mean different things: one is a fault to chase with the publisher, the other is the
    refresh working exactly as designed and asking for a decision.

    ``exit_code`` carries the same distinction out to the process. A refresh that
    refused and a refresh whose comparison could not be made are both non-zero and they
    are not the same fact: the first is an answer, the second is the absence of one, and
    collapsing them is this repository's named defect class.
    """

    def __init__(
        self,
        step: str,
        detail: str,
        *,
        exit_code: int = 1,
        diff: artifact_diff.DiffResult | None = None,
    ) -> None:
        super().__init__(detail)
        self.step = step
        self.detail = detail
        self.exit_code = exit_code
        self.diff = diff


@dataclass(frozen=True)
class LayerRetrieval:
    """What one layer returned on this run, beside what ``sources.py`` pins.

    Three facts identify a retrieval and all three are recorded: the record count, the
    byte count and the hash. A count on its own moves for an ordinary reason (the layer
    grew) and a hash on its own moves for every reason at once, so the pair is what makes
    an unchanged retrieval legible as unchanged.

    Disagreement with the pin is an **observation**, never a refusal. A refresh exists
    because the publisher moved; refusing on the evidence of that would refuse every
    refresh that was worth running.
    """

    source_key: str
    endpoint: str
    file: str
    retrieved: str
    feature_count: int
    raw_bytes: int
    sha256: str
    pinned_feature_count: int
    pinned_raw_bytes: int
    pinned_sha256: str

    @property
    def matches_pin(self) -> bool:
        return (
            self.feature_count == self.pinned_feature_count
            and self.raw_bytes == self.pinned_raw_bytes
            and self.sha256 == self.pinned_sha256
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_key,
            "endpoint": self.endpoint,
            "file": self.file,
            "retrieved": self.retrieved,
            "feature_count": self.feature_count,
            "raw_bytes": self.raw_bytes,
            "sha256": self.sha256,
            "pinned": {
                "feature_count": self.pinned_feature_count,
                "raw_bytes": self.pinned_raw_bytes,
                "sha256": self.pinned_sha256,
            },
            "matches_pin": self.matches_pin,
        }


@dataclass(frozen=True)
class RunResult:
    """Everything one completed `--run` produced. Never built for a refused run."""

    as_of: str
    retrieved_pin: str
    tool: dict[str, Any]
    retrievals: tuple[LayerRetrieval, ...]
    diff: artifact_diff.DiffResult
    allow_removals: bool
    artifact: str
    report: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "refresh-receipt",
            "as_of": self.as_of,
            "tool": self.tool,
            "pin": {"retrieved": self.retrieved_pin},
            "retrievals": [item.to_dict() for item in self.retrievals],
            "built": {"artifact": self.artifact, "report": self.report},
            "diff": json.loads(
                artifact_diff.as_json(self.diff, allow_removals=self.allow_removals)
            ),
            "adopted": False,
            "adoption": list(ADOPTION),
        }


def tool_identity(version: Callable[[str], str] | None = None) -> dict[str, Any]:
    """Which build of this tool produced a receipt, or why that is not known.

    The issue this was built from asked for a commit. There is not one to read: the
    installed distribution carries a version and no revision, and shelling out to git
    would answer for the checkout a person happened to be standing in rather than for
    the code that ran, which on an installed copy is a different thing. So the version
    is what is recorded, under its own name, with the distribution beside it.

    A version that cannot be read is reported as not measured with the reason, which is
    the shape every other unanswerable question in this project takes. It is not omitted:
    an absent key and an unread one are the same character in a receipt somebody reads a
    year later.
    """
    read = metadata.version if version is None else version
    try:
        return {"distribution": cli.DISTRIBUTION, "version": read(cli.DISTRIBUTION)}
    except metadata.PackageNotFoundError:
        return {
            "distribution": cli.DISTRIBUTION,
            "version": None,
            "detail": (
                f"nothing installed under {cli.DISTRIBUTION} carries the distribution "
                "metadata to read a version from, so which build produced this receipt "
                "is not recorded. It is not the version the repository declares: that "
                "would be a guess."
            ),
        }


def prepare_workdir(workdir: Path) -> tuple[Path, Path]:
    """The two fresh directories, or a refusal naming the one that is not fresh.

    A refresh that acquires on top of a previous run's files measures a mixture of two
    retrievals, and the resulting artifact would carry one pin's records under another
    pin's date with nothing to show for it. So a run refuses a workdir that already
    holds either directory rather than emptying it: deleting a previous acquisition is
    a person's decision, and it is the one thing here that cannot be undone.
    """
    raw = workdir / RAW_DIR_NAME
    build = workdir / BUILD_DIR_NAME
    for existing in (raw, build):
        if existing.exists():
            raise RefreshRefused(
                STEP_WORKDIR,
                f"{existing} already exists. A refresh acquires into a fresh directory "
                "and builds into a fresh directory, because a run on top of a previous "
                "one measures two retrievals mixed together. Point --workdir somewhere "
                "new, or move the previous run out of the way yourself.",
            )
    raw.mkdir(parents=True)
    return raw, build


def _pin_for(source_key: str) -> Source:
    for source in ALL_SOURCES:
        if source.key == source_key:
            return source
    raise RefreshRefused(  # pragma: no cover - acquire_all only returns pinned sources
        STEP_ACQUIRE,
        f"the acquisition returned a layer called {source_key!r}, which sources.py "
        "does not pin. Nothing can be compared against a pin that does not exist.",
    )


def acquire_step(
    raw_dir: Path, acquire: Callable[[Path], Sequence[Acquired]] | None = None
) -> tuple[LayerRetrieval, ...]:
    """Every layer, or nothing. The refusals are upstream's and acquire.py's.

    ``AcquisitionBlocked`` is a publisher declining automated access, ``AcquisitionFailed``
    is a request that did not produce a layer, and ``IncompleteAcquisition`` -- which is
    an ``AcquisitionFailed`` -- is a walk that finished without evidence that it read the
    whole layer. All three stop the refresh here, before a build exists, because a build
    over a short walk publishes a hole nothing downstream can see.
    """
    read = acquire_all if acquire is None else acquire
    try:
        acquired = read(raw_dir)
    except (AcquisitionBlocked, AcquisitionFailed) as error:
        raise RefreshRefused(
            STEP_ACQUIRE,
            f"the acquisition refused: {error}. Nothing was built and no receipt was "
            "written. docs/RUNBOOK.md, 'When acquisition refuses', says what each one "
            "means; none of them is worked around by re-running in a loop.",
        ) from error
    retrievals = []
    for item in acquired:
        pin = _pin_for(item.source_key)
        retrievals.append(
            LayerRetrieval(
                source_key=item.source_key,
                endpoint=item.endpoint,
                file=item.path.name,
                retrieved=item.retrieved,
                feature_count=item.feature_count,
                raw_bytes=item.raw_bytes,
                sha256=item.sha256,
                pinned_feature_count=pin.feature_count,
                pinned_raw_bytes=pin.raw_bytes,
                pinned_sha256=pin.sha256,
            )
        )
    return tuple(retrievals)


def build_step(
    raw_dir: Path,
    build_dir: Path,
    build: Callable[..., tuple[Path, Path]] | None = None,
) -> tuple[Path, Path]:
    """The ordinary build, over the files just acquired, marked as the real retrieval.

    ``is_fixture`` is ``False`` here and nowhere else in this module. A refresh that
    produced an artifact flagged as a fixture would be a refresh whose output can never
    be adopted, and one that flagged a fixture build as real is the failure the flag
    exists to prevent; the flag is set from the mode rather than from a parameter so
    neither can happen by passing the wrong thing.
    """
    run_build = cli.build if build is None else build
    try:
        return run_build(
            dins_path=raw_dir / DINS.raw_file,
            iou_pou_path=raw_dir / ELSE_IOU_POU.raw_file,
            other_path=raw_dir / ELSE_OTHER.raw_file,
            counties_path=raw_dir / COUNTIES.raw_file,
            out_dir=build_dir,
            is_fixture=False,
        )
    except PublicationRefused as error:
        raise RefreshRefused(
            STEP_BUILD,
            f"the build refused to publish: {error}. The fix is in the measurement that "
            "produced the shape, never in the rule. No comparison was run and no "
            "receipt was written.",
        ) from error
    except (OSError, ValueError) as error:
        raise RefreshRefused(
            STEP_BUILD,
            f"the build could not read what the acquisition wrote: {error}. No "
            "comparison was run and no receipt was written.",
        ) from error


def compare_step(
    published: Path, built: Path, *, allow_removals: bool
) -> artifact_diff.DiffResult:
    """The refresh diff, with the three ways it can fail to be a comparison at all.

    Every refusal here is ``artifact_diff``'s own, reached through the same functions
    the command line reaches them through rather than through a second reading of the
    same rules. A comparison that compared nothing and a comparison in which nothing
    moved print the same verdict if nobody separates them, which is why that separation
    lives in one place and is called from both.
    """
    try:
        old = json.loads(published.read_text(encoding="utf-8"))
    except OSError as error:
        raise RefreshRefused(
            STEP_COMPARE,
            f"the published artifact could not be read: {error}. Without it there is "
            "nothing to compare the build against, and a refresh nobody compared is the "
            "step this command exists to make unskippable.",
            exit_code=EXIT_REFRESH_UNREADABLE,
        ) from error
    except json.JSONDecodeError as error:
        raise RefreshRefused(
            STEP_COMPARE,
            f"the published artifact is not valid JSON: {error}",
            exit_code=EXIT_REFRESH_UNREADABLE,
        ) from error
    new = json.loads(built.read_text(encoding="utf-8"))
    for side, tree in (("old", old), ("new", new)):
        complaint = artifact_diff.not_an_artifact(side, tree)
        if complaint is not None:
            raise RefreshRefused(
                STEP_COMPARE, complaint, exit_code=EXIT_REFRESH_UNREADABLE
            )
    result = artifact_diff.diff_trees(old, new)
    empty = artifact_diff.compared_nothing(result)
    if empty is not None:
        raise RefreshRefused(STEP_COMPARE, empty, exit_code=EXIT_REFRESH_UNREADABLE)
    if result.removed and not allow_removals:
        raise RefreshRefused(
            STEP_COMPARE,
            f"{len(result.removed)} published value(s) were removed by this refresh and "
            "nothing has said they were meant to go. No receipt was written. Re-run "
            "with --allow-removals once PROVENANCE.md names them, or find out why the "
            "measurement stopped producing them.",
            diff=result,
        )
    return result


def run(
    *,
    workdir: Path,
    published: Path,
    allow_removals: bool = False,
    today: date | None = None,
    acquire: Callable[[Path], Sequence[Acquired]] | None = None,
    build: Callable[..., tuple[Path, Path]] | None = None,
    version: Callable[[str], str] | None = None,
) -> RunResult:
    """Acquire, build, compare. Raises :class:`RefreshRefused` at the first refusal.

    Every collaborator is a parameter with the shipped value as its default, so the
    whole sequence runs in a test with no socket and no clock, and so a test that leaves
    one out is exercising the shipped path for it.

    Nothing here writes the receipt. Returning a result and persisting it are separated
    because the only correct moment to write a receipt is after the last step has
    returned, and a function that wrote as it went would have to decide what a
    half-written receipt means.
    """
    as_of = today if today is not None else datetime.now(tz=UTC).date()
    raw_dir, build_dir = prepare_workdir(workdir)
    retrievals = acquire_step(raw_dir, acquire)
    artifact_path, report_path = build_step(raw_dir, build_dir, build)
    diff = compare_step(published, artifact_path, allow_removals=allow_removals)
    return RunResult(
        as_of=as_of.isoformat(),
        retrieved_pin=RETRIEVED,
        tool=tool_identity(version),
        retrievals=retrievals,
        diff=diff,
        allow_removals=allow_removals,
        artifact=str(artifact_path.relative_to(workdir)),
        report=str(report_path.relative_to(workdir)),
    )


def write_receipt(result: RunResult, workdir: Path) -> Path:
    """One receipt, for one finished run, in the workdir the run used."""
    path = workdir / RECEIPT_NAME
    path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return path


def render_run(result: RunResult, receipt: Path) -> str:
    """The report a person reads after a completed run."""
    lines = [
        f"refresh run, {result.as_of}",
        f"pin retrieved : {result.retrieved_pin}",
        "",
        "Retrieved, against what sources.py pins:",
    ]
    for item in result.retrievals:
        verdict = "same as the pin" if item.matches_pin else "DIFFERS from the pin"
        lines.append(f"  {item.source_key}: {verdict}")
        lines.append(
            f"    {item.feature_count:,} features, {item.raw_bytes:,} bytes, "
            f"sha256 {item.sha256}"
        )
        lines.append(
            f"    pinned: {item.pinned_feature_count:,} features, "
            f"{item.pinned_raw_bytes:,} bytes, sha256 {item.pinned_sha256}"
        )
    lines.append("")
    lines.append(
        artifact_diff.render(result.diff, allow_removals=result.allow_removals)
    )
    lines.append("")
    lines.append(f"Receipt: {receipt}")
    lines.append(
        "Nothing was adopted. published/ is untouched, sources.py is unedited, and "
        "nothing was committed. The receipt lists what a person does next."
    )
    return "\n".join(lines) + "\n"


_LABELS = {
    Verdict.FIRED: "FIRED",
    Verdict.NOT_FIRED: "not fired",
    Verdict.UNMEASURABLE: "COULD NOT CHECK",
    Verdict.NOT_CHECKED_HERE: "not checked here",
}

_VERDICT_SENTENCE = {
    EXIT_NO_TRIGGER: (
        "Every declared trigger this command checks was checked, and none fired. "
        "Trigger 3 is a person's call and is listed above unchecked."
    ),
    EXIT_TRIGGER_FIRED: (
        "A declared trigger fired. The pin is stale by this project's own cadence; "
        "docs/RUNBOOK.md has the refresh procedure."
    ),
    EXIT_COULD_NOT_CHECK: (
        "A declared trigger could not be checked. This is not a clean result and it is "
        "not a stale pin: it is an unanswered question, and the detail above names what "
        "could not be read."
    ),
}


def render(result: CheckResult) -> str:
    """The report a person reads."""
    lines = [
        f"refresh check, {result.as_of}",
        f"pin retrieved : {result.retrieved}",
        "",
        "Declared triggers (PROVENANCE.md, Cadence):",
    ]
    for trigger in result.triggers:
        lines.append(f"  [{_LABELS[trigger.verdict]}] {trigger.name}")
        lines.append(f"    {trigger.question}")
        lines.append(f"    {trigger.detail}")
    lines.append("")
    lines.append("Record counts, reported and not a trigger:")
    for observation in result.counts:
        lines.append(f"  {observation.source_key}: {observation.detail}")
    lines.append("")
    lines.append(_VERDICT_SENTENCE[result.exit_code])
    return "\n".join(lines) + "\n"


def _check_mode(as_json: bool) -> int:
    result = check()
    if as_json:
        print(
            json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        )
    else:
        sys.stdout.write(render(result))
    return result.exit_code


def _run_mode(args: argparse.Namespace) -> int:
    """Drive one refresh, and say what happened whether or not it finished.

    A refusal writes no receipt and prints why on stderr. Where the refusal *is* the
    comparison, the whole diff goes to stdout first: the run is refused because a value
    was removed and nobody said so, and the list of removed values is precisely what the
    person deciding needs. A refusal that swallowed it would make re-running with
    ``--allow-removals`` the cheapest way to find out what it was, which is the opposite
    of what that flag is for.
    """
    try:
        result = run(
            workdir=args.workdir,
            published=args.published,
            allow_removals=args.allow_removals,
        )
    except RefreshRefused as refusal:
        if refusal.diff is not None:
            print(artifact_diff.render(refusal.diff, allow_removals=False))
        print(f"refresh refused at {refusal.step}: {refusal.detail}", file=sys.stderr)
        return refusal.exit_code
    receipt = write_receipt(result, args.workdir)
    if args.as_json:
        print(
            json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        )
    else:
        sys.stdout.write(render_run(result, receipt))
    return EXIT_REFRESH_DONE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m wildfire_service_territory_overlap.refresh",
        description=(
            "The deliberate refresh. --check asks whether the pin has gone stale under "
            "PROVENANCE.md's declared triggers, reading no rows and writing nothing. "
            "--run acquires, builds and compares against published/, in that order, "
            "stopping at the first refusal, and writes a receipt for a person to read. "
            "Neither adopts anything. Both touch the network and neither runs in CI."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="read-only: has the pin gone stale? Exit 0 means every trigger this "
        "command checks was checked and none fired; 1 means one fired; 2 means one "
        "could not be checked, which is not the same as clean",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        dest="do_run",
        help="acquire, build and compare into --workdir. Writes a receipt and nothing "
        "else; published/ and sources.py are read and never written",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        help="where --run acquires and builds. Required with --run. Refused if it "
        "already holds a raw/ or build/ directory, because a run on top of a previous "
        "one measures two retrievals mixed together",
    )
    parser.add_argument(
        "--published",
        type=Path,
        default=Path("published") / cli.ARTIFACT_NAME,
        help="the artifact --run compares its build against",
    )
    parser.add_argument(
        "--allow-removals",
        action="store_true",
        help="accept a refresh that removes published values; say why they went in "
        "PROVENANCE.md",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print one JSON object instead of the prose report; exit codes unchanged",
    )
    args = parser.parse_args(argv)
    if args.do_run and args.workdir is None:
        parser.error(
            "--run needs --workdir. A default would put an acquisition somewhere "
            "nobody named, and the directory it acquires into is the one thing about a "
            "refresh that must not be a surprise."
        )
    if args.check:
        return _check_mode(args.as_json)
    return _run_mode(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
