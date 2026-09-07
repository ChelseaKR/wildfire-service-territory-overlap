"""The refresh diff, as a tool rather than a one-off.

A published number changing quietly is the failure mode this project exists to avoid,
and the only difference between a quiet change and a measured one is whether somebody
ran the comparison. The refresh of 2026-08-17 was compared leaf by leaf by hand:
4,370 published values, none removed, none changed. That comparison is now a command,
so the next refresh cannot skip it by being tedious.

Usage::

    python -m wildfire_service_territory_overlap.artifact_diff OLD.json NEW.json [--allow-removals]

Semantics
---------
Every leaf of the JSON tree is compared by path. A leaf is a scalar, or an empty
container standing alone. Three things are reported:

added
    A leaf the previous artifact did not carry. Expected on a refresh that widens a
    cut, such as the county field arriving.

changed
    A leaf present twice with different values. This is what a deliberate refresh is
    for, so a change is reported, not refused.

removed
    A leaf the previous artifact carried and the new one does not. A published value
    disappearing shrinks what the record set promises its readers, so removal refuses
    the run with a nonzero exit unless ``--allow-removals`` names it deliberately.

Lists are paired before comparison. When every element on both sides carries exactly
one identifying field from :data:`IDENTITY_KEYS`, elements pair on that field, so a
collection reordered between retrievals reports nothing and a changed row stays
attached to its own name. Lists without a common identifying field pair positionally;
a size-ordered collection such as ``contested_groups`` can therefore report movement
at adjacent indices when two combinations swap size. Read those rows together.

Output
------
By default the report is prose, ending in a verdict line. ``--json`` prints exactly one
JSON object instead, carrying the same information with none of the wording: the five
counts, the full added, removed and changed lists with their paths and their values,
whether ``--allow-removals`` was given, and whether the run was refused. Values are
carried whole there, where the prose shortens a long one for the terminal.

``--json`` is a second way to read the same comparison. It does not soften the removal
refusal and it does not change an exit code.

What this tool refuses to compare
--------------------------------
A verdict is a claim about a comparison that happened. Three inputs produce a verdict
that no comparison earned, and all three are refused before anything is printed:

* **A side that is not a JSON object.** ``measurements.json`` is an object. A file
  holding ``null``, a list or a scalar is not an artifact, and comparing two of them
  reads as one unchanged leaf and a clean run. A build that failed and wrote ``null``
  must not pass for a refresh in which nothing moved.
* **A comparison in which no value was compared.** Two empty objects agree on every
  one of their zero values, so the tool reported ``0 values compared`` and
  ``No published value moved.`` and exited ``0``: the same verdict, and the same exit
  code, as the 4,370-value comparison this module was written for. That is the shape
  :func:`wildfire_service_territory_overlap.intervals.wilson` already refuses one layer
  down: zero out of zero is not zero percent, it is not measured. Nothing compared is
  not nothing moved.
* **Two paths that are the same file.** A file cannot differ from itself, so a clean
  verdict from that comparison is guaranteed rather than earned, and the refresh step
  it was standing in for did not happen.

Each exits ``2`` and prints nothing on stdout, so a caller reading ``--json`` never
receives an object describing a comparison that was not made.

Exit codes: ``0`` when there is nothing to refuse, ``1`` when values were removed and
``--allow-removals`` was not given, ``2`` on bad usage or on any of the three refusals
above.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Fields that name what a list row is about. Exactly one of these per element, on both
# sides, is what turns a positional comparison into a keyed one.
IDENTITY_KEYS: tuple[str, ...] = (
    "territory",
    "county",
    "year",
    "label",
    "published_type",
    "rule",
)

Identity = tuple[str, str | int]


@dataclass(frozen=True)
class Leaf:
    """One published value, located by its path in the tree."""

    path: str
    value: Any


@dataclass(frozen=True)
class ChangedLeaf:
    """One published value that moved, with what it moved from."""

    path: str
    before: Any
    after: Any


@dataclass
class DiffResult:
    """Everything the comparison found, plus how much agreed."""

    added: list[Leaf]
    removed: list[Leaf]
    changed: list[ChangedLeaf]
    unchanged: int

    @property
    def total(self) -> int:
        return len(self.added) + len(self.removed) + len(self.changed) + self.unchanged


def _is_leaf(node: Any) -> bool:
    """A scalar, or an empty container, which carries itself rather than children."""
    if isinstance(node, dict | list):
        return len(node) == 0
    return True


def _flatten(node: Any, path: str, into: list[Leaf]) -> None:
    """Every leaf under ``node``, for subtrees present on one side only."""
    if _is_leaf(node):
        into.append(Leaf(path, node))
        return
    if isinstance(node, dict):
        for key, value in node.items():
            _flatten(value, f"{path}.{key}", into)
        return
    for index, value in enumerate(node):
        _flatten(value, f"{path}[{index}]", into)


def _identity_of(item: Any) -> Identity | None:
    """The single identifying field an element carries, or None."""
    if not isinstance(item, dict):
        return None
    found = [
        (key, item[key])
        for key in IDENTITY_KEYS
        if key in item and isinstance(item[key], str | int)
    ]
    if len(found) != 1:
        return None
    ((key, value),) = found
    return (key, value)


def _identities_of(items: list[Any]) -> list[Identity] | None:
    """Every element's identifying field, or None when any element carries none."""
    found = [_identity_of(item) for item in items]
    if any(identity is None for identity in found):
        return None
    return [identity for identity in found if identity is not None]


def _keyed_pairing(
    old_items: list[Any], new_items: list[Any]
) -> tuple[set[tuple[int, int]], tuple[list[int], list[int]]] | None:
    """Indices paired by identity when both sides agree on one identifying field.

    Uniqueness is part of the deal: two rows answering to the same name means the field
    is not doing identification work, and the pairing falls back to position. Returns
    the matched index pairs plus the indices left over on each side.
    """
    old_ids = _identities_of(old_items)
    new_ids = _identities_of(new_items)
    if old_ids is None or new_ids is None or not old_ids or not new_ids:
        return None
    # Every element carries exactly one identifying field. They must agree on which.
    names = {identity[0] for identity in (*old_ids, *new_ids)}
    if len(names) != 1:
        return None
    old_index = {identity: i for i, identity in enumerate(old_ids)}
    new_index = {identity: i for i, identity in enumerate(new_ids)}
    if len(old_index) != len(old_ids) or len(new_index) != len(new_ids):
        return None
    shared = sorted(set(old_index) & set(new_index))
    return {(old_index[i], new_index[i]) for i in shared}, (
        [i for i in range(len(old_items)) if old_ids[i] not in new_index],
        [i for i in range(len(new_items)) if new_ids[i] not in old_index],
    )


def _walk(old: Any, new: Any, path: str, result: DiffResult) -> None:
    """Compare one position, recursing while both sides stay the same kind of thing."""
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            if key not in old:
                _flatten(new[key], f"{path}.{key}", result.added)
            elif key not in new:
                _flatten(old[key], f"{path}.{key}", result.removed)
            else:
                _walk(old[key], new[key], f"{path}.{key}", result)
        return
    if isinstance(old, list) and isinstance(new, list):
        _walk_lists(old, new, path, result)
        return
    # Everything below here is a leaf on at least one side. A container replacing a
    # scalar is reported whole rather than half-read.
    if type(old) is type(new) and old == new:
        result.unchanged += 1
        return
    result.changed.append(ChangedLeaf(path, old, new))


def _walk_lists(old: list[Any], new: list[Any], path: str, result: DiffResult) -> None:
    """Pair two lists, then compare the pairs.

    Keyed pairing keeps a reordered collection silent and a changed row attached to its
    own name. Positional pairing is the fallback, and a collection ordered by a measured
    size can move rows past each other under it; that is stated in the module docstring
    rather than smoothed over, because smoothing it over would mean deciding which rows
    are "really" the same row, which is a judgment this tool does not get to make.
    """
    pairing = _keyed_pairing(old, new)
    if pairing is None:
        for index, (one, two) in enumerate(zip(old, new, strict=False)):
            _walk(one, two, f"{path}[{index}]", result)
        for index in range(len(new), len(old)):
            _flatten(old[index], f"{path}[{index}]", result.removed)
        for index in range(len(old), len(new)):
            _flatten(new[index], f"{path}[{index}]", result.added)
        return
    pairs, (extra_old, extra_new) = pairing
    for one, two in sorted(pairs):
        _walk(old[one], new[two], f"{path}[{one}]", result)
    for index in extra_old:
        _flatten(old[index], f"{path}[{index}]", result.removed)
    for index in extra_new:
        _flatten(new[index], f"{path}[{index}]", result.added)


def diff_trees(old: Any, new: Any) -> DiffResult:
    """Compare two artifact trees leaf by leaf."""
    result = DiffResult(added=[], removed=[], changed=[], unchanged=0)
    _walk(old, new, "$", result)
    return result


def _short(value: Any, limit: int = 120) -> str:
    text = repr(value)
    if len(text) > limit:
        text = text[: limit - 1] + "\u2026"
    return text


def render(result: DiffResult, *, allow_removals: bool) -> str:
    """The human-readable report, ending in the verdict."""
    lines: list[str] = []
    for change in result.changed:
        lines.append(
            f"changed  {change.path}: {_short(change.before)} -> {_short(change.after)}"
        )
    for leaf in result.added:
        lines.append(f"added    {leaf.path}: {_short(leaf.value)}")
    for gone in result.removed:
        lines.append(f"REMOVED  {gone.path}: {_short(gone.value)}")
    lines.append(
        f"{result.total} values compared: "
        f"{len(result.added)} added, "
        f"{len(result.removed)} removed, "
        f"{len(result.changed)} changed."
    )
    if result.removed and not allow_removals:
        lines.append(
            "REFUSED: published values disappeared. If the removal is deliberate, "
            "re-run with --allow-removals and say so in PROVENANCE.md."
        )
    elif result.removed:
        # --allow-removals accepts a removal. It does not make the removal stop having
        # happened, and the verdict line is the one line a reader skims. Saying
        # "Nothing was removed." directly under a REMOVED line is the quiet
        # disappearance this tool exists to prevent, carrying this tool's signature.
        count = len(result.removed)
        lines.append(
            f"{count} published value{'' if count == 1 else 's'} "
            f"{'was' if count == 1 else 'were'} removed, and --allow-removals accepted "
            "the removal. Say why in PROVENANCE.md."
        )
    elif not result.changed and not result.added:
        lines.append("No published value moved.")
    else:
        lines.append("Nothing was removed.")
    return "\n".join(lines)


def as_json(result: DiffResult, *, allow_removals: bool) -> str:
    """The same comparison as one JSON object, for a caller that is not a person.

    The refresh procedure in ``docs/RUNBOOK.md`` copies the summary into
    ``PROVENANCE.md`` by hand. This makes that step mechanical without changing what the
    prose mode prints or what either mode exits with.

    ``allow_removals`` is reported alongside ``refused`` on purpose. Without it,
    ``"refused": false`` on a run that removed values and was told to accept them reads
    as a run where nothing was removed, which is the same misreading the prose verdict
    used to invite.

    Values are whole here. :func:`_short` shortens a long value so a terminal line stays
    readable, and a machine-readable mode that did the same would be publishing a
    truncated value under the name of the real one.
    """
    payload: dict[str, Any] = {
        "counts": {
            "total": result.total,
            "added": len(result.added),
            "removed": len(result.removed),
            "changed": len(result.changed),
            "unchanged": result.unchanged,
        },
        "added": [{"path": leaf.path, "value": leaf.value} for leaf in result.added],
        "removed": [
            {"path": leaf.path, "value": leaf.value} for leaf in result.removed
        ],
        "changed": [
            {"path": change.path, "before": change.before, "after": change.after}
            for change in result.changed
        ],
        "allow_removals": allow_removals,
        "refused": bool(result.removed) and not allow_removals,
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _not_an_artifact(side: str, tree: Any) -> str | None:
    """Why ``tree`` cannot be one side of an artifact comparison, or ``None``.

    ``published/measurements.json`` is a JSON object. Anything else read from that
    position is a file that failed to become an artifact, and the comparison below
    would happily give it a verdict: two ``null`` documents pair as a single scalar
    leaf that equals itself, print ``No published value moved.`` and exit ``0``.
    """

    if isinstance(tree, dict):
        return None
    kind = "a list" if isinstance(tree, list) else f"{type(tree).__name__} ({tree!r})"
    return (
        f"the {side} artifact is not a JSON object but {kind}. "
        "published/measurements.json is an object; a file that is not one did not "
        "finish being built, and comparing two of them is not a comparison."
    )


def _compared_nothing(result: DiffResult) -> str | None:
    """Why a comparison of zero values must not be reported, or ``None``.

    Two empty objects agree on all zero of their values. The verdict for that run was
    ``No published value moved.`` with exit ``0``, which is what this tool prints when
    it has checked several thousand published figures and found them identical. The
    two runs are not the same claim and must not share a verdict.
    """

    if result.total > 0:
        return None
    return (
        "no value was compared. Two artifacts with nothing in them agree about "
        "nothing, which is not the same fact as a refresh in which no published value "
        "moved, and this tool will not print the second verdict for the first run."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m wildfire_service_territory_overlap.artifact_diff",
        description=(
            "Compare two measurements.json artifacts value by value, so a refresh "
            "cannot change the published figures quietly."
        ),
    )
    parser.add_argument("old", type=Path, help="the artifact built before the refresh")
    parser.add_argument("new", type=Path, help="the artifact built after it")
    parser.add_argument(
        "--allow-removals",
        action="store_true",
        help="accept removed values; say why they went in PROVENANCE.md",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print one JSON object instead of the prose report; exit codes unchanged",
    )
    args = parser.parse_args(argv)
    try:
        old = json.loads(args.old.read_text(encoding="utf-8"))
        new = json.loads(args.new.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"could not read an artifact: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(f"an artifact is not valid JSON: {error}", file=sys.stderr)
        return 2
    try:
        same_file = args.old.resolve() == args.new.resolve()
    except OSError:  # pragma: no cover - both paths were readable a moment ago
        same_file = False
    if same_file:
        print(
            "both paths are the same file. A file cannot differ from itself, so the "
            "clean verdict that comparison produces is guaranteed rather than earned, "
            "and the refresh step it stands in for did not happen.",
            file=sys.stderr,
        )
        return 2
    for side, tree in (("old", old), ("new", new)):
        complaint = _not_an_artifact(side, tree)
        if complaint is not None:
            print(complaint, file=sys.stderr)
            return 2
    result = diff_trees(old, new)
    empty = _compared_nothing(result)
    if empty is not None:
        print(empty, file=sys.stderr)
        return 2
    if args.as_json:
        print(as_json(result, allow_removals=args.allow_removals))
    else:
        print(render(result, allow_removals=args.allow_removals))
    if result.removed and not args.allow_removals:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
