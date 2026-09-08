"""Ask whether the pin has gone stale, without downloading a record.

``PROVENANCE.md`` names three triggers under Cadence and ``docs/RUNBOOK.md`` describes the
refresh as a sequence of hand-run steps. The triggers are the part nobody can answer from
their desk: two of them are questions about somebody else's server, and the only way to
ask has been to run the whole acquisition, which downloads 180 MB and 132,522 structure
records to find out whether anything moved.

This asks instead. ``--check`` is read-only and reads no rows: it takes the layer's own
record count under the walk's predicate, and the item metadata behind the two territory
layers, and compares both against what ``sources.py`` pins. Nothing is written, nothing is
acquired, and no artifact moves.

**What the exit code means, exactly.**

- ``0`` -- every declared trigger this command checks was checked, and none fired.
- ``1`` -- a declared trigger fired. The pin is stale by this project's own cadence.
- ``2`` -- a declared trigger could not be checked. This is not ``0``, and the distinction
  is the whole reason the command exists: exit ``0`` meaning "I asked and the answer was
  no" and exit ``0`` meaning "I could not ask" would put a stale pin and a healthy pin
  behind the same green, which is the defect class this repository keeps finding.

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
import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from perimeter.acquire import AcquisitionBlocked, AcquisitionFailed, fetch_document

from wildfire_service_territory_overlap.acquire import USER_AGENT, layer_record_count
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m wildfire_service_territory_overlap.refresh",
        description=(
            "Ask whether the pin has gone stale under PROVENANCE.md's declared "
            "triggers. Reads no rows, writes nothing, acquires nothing. Exit 0 means "
            "every trigger this command checks was checked and none fired; 1 means one "
            "fired; 2 means one could not be checked, which is not the same as clean."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        required=True,
        help="the only mode this command has today; required so it cannot be run by "
        "accident and so a later mode is an addition rather than a change",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print one JSON object instead of the prose report; exit codes unchanged",
    )
    args = parser.parse_args(argv)
    result = check()
    if args.as_json:
        print(
            json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)
        )
    else:
        sys.stdout.write(render(result))
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
