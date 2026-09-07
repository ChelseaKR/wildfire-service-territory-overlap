"""Re-running the two choices that could have gone another way, and publishing the gap.

Two decisions in this project are judgment calls made from the publisher's own fields.
Both were documented and neither was measured, which meant a reader had to take the
reasoning on trust and the author had to take the size of the exposure on trust too.

``type_inclusion``
    ADR 0002 reads ``IOU``, ``POU``, ``CO-OP`` and ``Tribal`` as service territories and
    excludes ``CCA`` and ``ADMIN``. This runs the entire placement under that rule and
    under six alternatives, and reports what each one does to the headline figure. It
    does not choose between them. The point is that a reader can see which parts of the
    rule the result is sensitive to and which parts make no difference at all.

    A reviewer can add an alternative of their own without touching this file. A rule
    file names the variant, the reviewer's role, the date, the types read as service
    territories and, optionally, per-outline overrides with a one-line reason each;
    ``--inclusion-rule FILE`` runs it to completion over the same record set and
    publishes it as one more row. It is measured, not adopted: the rule as built stays
    the reference row and nothing is marked better.

``repair_comparison``
    ADR 0005 repairs an invalid published polygon with ``make_valid``. An earlier draft
    used ``buffer(0)``, and the note that survived said the two disagreed on "roughly
    770 placements", which is a recollection rather than a measurement. This runs every
    repair in :data:`wildfire_service_territory_overlap.geometry.REPAIR_STRATEGIES` to completion over the same
    records, counts the records whose outcome changes under each pair and under any
    pair, and names the direction of the change. The default does not move; what moves
    is measured.

``untouched_outlines``
    ADR 0002 declines to decide whether any named entity in the layer operates a
    distribution system, and ADR 0006 measures what the type rule costs without
    reaching that question either. What neither answers is the one a reader arrives
    with about a specific outline: would dropping this one change anything? For an
    outline no record falls inside, that is answerable without deciding what the
    entity is. This counts those outlines, counts the records they touch, and re-places
    the whole record set without them to show that the counts hold.

None of the three decides anything. All produce numbers with denominators and intervals,
in the same shapes the rest of the output uses, so the publication rules in
:mod:`wildfire_service_territory_overlap.artifacts` apply to them unchanged.
"""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from wildfire_service_territory_overlap.geometry import (
    BUFFER_ZERO,
    MAKE_VALID,
    REPAIR_STRATEGIES,
    Territory,
    load_territories,
)
from wildfire_service_territory_overlap.intervals import Difference, Rate
from wildfire_service_territory_overlap.placement import (
    Placement,
    Record,
    classify,
    containment_signatures,
)
from wildfire_service_territory_overlap.sources import (
    PUBLISHED_TYPES,
    TYPE_FIELD_IS_UNDOCUMENTED,
    WIRES_TYPES,
)

TYPE_VARIANTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("the rule as built", WIRES_TYPES),
    ("without CO-OP", ("IOU", "POU", "Tribal")),
    ("without Tribal", ("CO-OP", "IOU", "POU")),
    ("without CO-OP or Tribal", ("IOU", "POU")),
    ("with CCA read as a territory", ("CCA", "CO-OP", "IOU", "POU", "Tribal")),
    ("with ADMIN read as a territory", ("ADMIN", "CO-OP", "IOU", "POU", "Tribal")),
    ("every published type read as a territory", PUBLISHED_TYPES),
)
"""The rule, the two inclusions it could drop, and the two exclusions it could take back."""

CONTESTED_LABEL = "inside two or more published territories"


# --- A rule a reviewer supplies, measured the same way the built rule is -----------
#
# `docs/outreach/inclusion-rule-review-packet.md` promises a domain reviewer that a
# finding "lands as a new sensitivity row rather than as an edit to the rule". Until
# now, landing it meant editing `TYPE_VARIANTS` above, which is a Python change made by
# somebody other than the reviewer, and it put an engineering step between the
# reviewer's judgment and the published number the packet says there will not be.
#
# A supplied rule is a small JSON document. It is loaded strictly: an unknown key is
# refused rather than ignored, because a reviewer who writes `type` instead of
# `variant`, or `types` instead of `types_read_as_territories`, has to be told rather
# than quietly measured under a rule they did not write. It fetches nothing, it reaches
# no network, and it cannot change the rule as built: every supplied file is one more
# row beside the built ones, with the built rule still the reference row.

RULE_FILE_KEYS: frozenset[str] = frozenset(
    {
        "variant",
        "reviewer_role",
        "reviewed_on",
        "types_read_as_territories",
        "outline_overrides",
    }
)
"""Every key a rule file may carry. Anything else is refused, never ignored."""

REQUIRED_RULE_FILE_KEYS: frozenset[str] = frozenset(
    {"variant", "reviewer_role", "reviewed_on", "types_read_as_territories"}
)
"""The four a rule file must carry. ``outline_overrides`` is the optional one."""

OVERRIDE_KEYS: frozenset[str] = frozenset({"read_as_a_territory", "reason"})
"""Every key one per-outline override may carry. Both are required."""

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class InclusionRuleRefused(ValueError):
    """A reviewer-supplied inclusion rule file this project will not measure."""


@dataclass(frozen=True)
class OutlineOverride:
    """One named outline read against the type rule, with the reviewer's reason."""

    outline: str
    read_as_a_territory: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "read_as_a_territory": self.read_as_a_territory,
            "reviewer_reason": self.reason,
        }


@dataclass(frozen=True)
class SuppliedRule:
    """One reviewer's reading of the ``Type`` field, as a rule this can re-place under.

    ``file_name`` is the basename and never the path the file was read from. A rule
    supplied out of a temporary directory would otherwise write that directory into
    ``measurements.json``, and two builds of the same inputs on two machines would stop
    being byte-identical, which is the property `make determinism` exists to hold.
    """

    file_name: str
    variant: str
    reviewer_role: str
    reviewed_on: str
    types: tuple[str, ...]
    overrides: tuple[OutlineOverride, ...]


def _refuse(file_name: str, message: str) -> InclusionRuleRefused:
    return InclusionRuleRefused(f"{file_name}: {message}")


def _string(file_name: str, key: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _refuse(file_name, f"{key} has to be a non-empty string")
    return value.strip()


def _read_overrides(file_name: str, value: Any) -> tuple[OutlineOverride, ...]:
    if not isinstance(value, dict):
        raise _refuse(
            file_name,
            "outline_overrides has to be an object keyed by the outline name the "
            "publisher gives it",
        )
    overrides: list[OutlineOverride] = []
    for outline in sorted(value):
        entry = value[outline]
        name = _string(file_name, "an outline_overrides key", outline)
        if not isinstance(entry, dict):
            raise _refuse(
                file_name,
                f"the override for {name} has to be an object carrying "
                "read_as_a_territory and reason",
            )
        unknown = sorted(set(entry) - OVERRIDE_KEYS)
        if unknown:
            raise _refuse(
                file_name,
                f"the override for {name} carries keys this project does not read: "
                f"{', '.join(unknown)}",
            )
        missing = sorted(OVERRIDE_KEYS - set(entry))
        if missing:
            raise _refuse(
                file_name,
                f"the override for {name} carries no {', '.join(missing)}",
            )
        read_as = entry["read_as_a_territory"]
        if not isinstance(read_as, bool):
            raise _refuse(
                file_name,
                f"the override for {name} gives read_as_a_territory as "
                f"{type(read_as).__name__}, not true or false",
            )
        reason = _string(file_name, f"the reason for {name}", entry["reason"])
        overrides.append(OutlineOverride(name, read_as, reason))
    return tuple(overrides)


def _read_document(path: Path, file_name: str) -> dict[str, Any]:
    """The file as a JSON object, with every key it carries recognised."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise _refuse(file_name, f"cannot be read: {error.strerror}") from None
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise _refuse(file_name, f"is not JSON: {error.args[0]}") from None
    if not isinstance(document, dict):
        raise _refuse(file_name, "has to be a JSON object")
    unknown = sorted(set(document) - RULE_FILE_KEYS)
    if unknown:
        raise _refuse(
            file_name,
            f"carries keys this project does not read: {', '.join(unknown)}. The keys "
            f"a rule file may carry are {', '.join(sorted(RULE_FILE_KEYS))}.",
        )
    missing = sorted(REQUIRED_RULE_FILE_KEYS - set(document))
    if missing:
        raise _refuse(file_name, f"carries no {', '.join(missing)}")
    read: dict[str, Any] = document
    return read


def _read_variant(file_name: str, value: Any) -> str:
    variant = _string(file_name, "variant", value)
    if variant in {label for label, _ in TYPE_VARIANTS}:
        raise _refuse(
            file_name,
            f"names itself {variant!r}, which is already the name of a variant this "
            "project builds. A supplied rule is published beside the built ones and "
            "needs a name of its own.",
        )
    return variant


def _read_role(file_name: str, value: Any) -> str:
    """The reviewer's role, refused when it is an address.

    The packet asks for a role rather than a name, and this cannot tell one from the
    other: "Distribution planning engineer" and "Jane Doe" are both non-empty strings
    and no rule here separates them. What it can refuse is the one personal identifier
    that has a shape, so an address pasted into this published field is caught instead
    of published. The rest is the reviewer's own decision, which is what the packet
    says it is.
    """
    role = _string(file_name, "reviewer_role", value)
    if "@" in role:
        raise _refuse(
            file_name,
            "reviewer_role carries an address. This field is published, and it is the "
            "reviewer's role rather than a way to reach them.",
        )
    return role


def _read_date(file_name: str, value: Any) -> str:
    reviewed_on = _string(file_name, "reviewed_on", value)
    if not _ISO_DATE.match(reviewed_on):
        raise _refuse(
            file_name, f"reviewed_on is {reviewed_on!r}, not a YYYY-MM-DD date"
        )
    try:
        date.fromisoformat(reviewed_on)
    except ValueError:
        raise _refuse(
            file_name, f"reviewed_on is {reviewed_on!r}, which is not a real date"
        ) from None
    return reviewed_on


def _read_types(file_name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _refuse(
            file_name,
            "types_read_as_territories has to be a non-empty list of published Type "
            "values",
        )
    types = tuple(_string(file_name, "a type", kind) for kind in value)
    repeated = sorted({kind for kind in types if types.count(kind) > 1})
    if repeated:
        raise _refuse(file_name, f"names a type more than once: {', '.join(repeated)}")
    return types


def read_rule_file(path: Path) -> SuppliedRule:
    """Load one rule file, or refuse it. Reads the file and nothing else.

    Every refusal names the file and what is wrong with it. None of them is a warning:
    a rule that cannot be read is not measured under a guess about what it meant.
    """
    file_name = path.name
    document = _read_document(path, file_name)
    return SuppliedRule(
        file_name=file_name,
        variant=_read_variant(file_name, document["variant"]),
        reviewer_role=_read_role(file_name, document["reviewer_role"]),
        reviewed_on=_read_date(file_name, document["reviewed_on"]),
        types=_read_types(file_name, document["types_read_as_territories"]),
        overrides=_read_overrides(file_name, document.get("outline_overrides", {})),
    )


def read_rule_files(paths: Sequence[Path]) -> tuple[SuppliedRule, ...]:
    """Load every supplied rule file, in filename order, or refuse the set.

    Order is the filenames', not the order they were given on the command line, so the
    same set of files produces the same artifact whichever way round they were typed.
    Two files with the same basename, or two rules with the same variant name, are
    refused: both would publish two rows a reader could not tell apart.
    """
    rules = [read_rule_file(path) for path in paths]
    for field, described in (("file_name", "basename"), ("variant", "variant name")):
        seen = Counter(getattr(rule, field) for rule in rules)
        clash = sorted(value for value, count in seen.items() if count > 1)
        if clash:
            raise InclusionRuleRefused(
                f"two supplied inclusion rules share a {described}: "
                f"{', '.join(clash)}. Each supplied rule is published as its own row "
                "and has to be told apart from the others."
            )
    return tuple(sorted(rules, key=lambda rule: rule.file_name))


def _names_present(collections: dict[str, dict[str, Any]]) -> set[str]:
    """Every ``Utility`` name in the retrieval, read before any rule filters one out.

    Read from the features for the same reason :func:`_types_present` is: the loader
    has already dropped everything outside the inclusion rule by the time it returns,
    so a check built on its output could never refuse an override naming an outline the
    built rule excludes, which is exactly the override a reviewer is most likely to
    write.
    """
    names: set[str] = set()
    for collection in collections.values():
        for feature in collection.get("features", []):
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue
            name = properties.get("Utility")
            if isinstance(name, str) and name.strip():
                names.add(name.strip())
    return names


def check_rules_against_retrieval(
    rules: Iterable[SuppliedRule], collections: dict[str, dict[str, Any]]
) -> None:
    """Refuse a rule that names something the pinned retrieval does not carry.

    A review is written against one retrieval and the layers move. A file naming a type
    the layer no longer carries, or an outline that has been renamed or withdrawn, would
    otherwise run to completion and publish a variant that measures nothing, or measures
    less than the reviewer asked for, with no line anywhere saying so. It is refused
    before any placement runs instead.
    """
    types = set(_types_present(collections))
    names = _names_present(collections)
    for rule in rules:
        unknown_types = sorted(set(rule.types) - types)
        if unknown_types:
            raise _refuse(
                rule.file_name,
                f"reads {', '.join(unknown_types)} as a service territory, and the "
                "retrieval this build is measuring carries no outline of that type. "
                f"The types it does carry are {', '.join(sorted(types))}.",
            )
        unknown_outlines = sorted(
            override.outline
            for override in rule.overrides
            if override.outline not in names
        )
        if unknown_outlines:
            raise _refuse(
                rule.file_name,
                f"overrides an outline the retrieval this build is measuring does not "
                f"carry: {', '.join(unknown_outlines)}.",
            )


def _subset_for(
    every: tuple[Territory, ...], rule: SuppliedRule
) -> tuple[Territory, ...]:
    """The outlines one supplied rule reads as service territories.

    The type rule first, then the named overrides on top of it. ``every`` is already in
    name order and the filter keeps that order, so nothing here sorts by a measured
    value.
    """
    added = {o.outline for o in rule.overrides if o.read_as_a_territory}
    removed = {o.outline for o in rule.overrides if not o.read_as_a_territory}
    return tuple(
        t
        for t in every
        if t.name in added or (t.kind in rule.types and t.name not in removed)
    )


def _outcome_counts(placement: Placement) -> dict[str, int]:
    return {
        "placed_in_exactly_one_territory": placement.placed,
        "contested_between_two_or_more": placement.contested,
        "covered_by_no_published_territory": placement.uncovered,
        "coordinate_not_usable": placement.not_measured,
    }


def _variant_row(
    label: str,
    kinds: tuple[str, ...],
    placement: Placement,
    indexed: int,
    baseline: Rate | None,
    supplied: SuppliedRule | None = None,
) -> dict[str, Any]:
    total = placement.fire_records
    contested = Rate.of(CONTESTED_LABEL, placement.contested, total)
    row: dict[str, Any] = {
        "variant": label,
        "types_read_as_territories": list(kinds),
        "territories_indexed": indexed,
        "counts": _outcome_counts(placement),
        "contested": contested.as_dict(),
        "placed": Rate.of(
            "placed in exactly one published territory", placement.placed, total
        ).as_dict(),
        "uncovered": Rate.of(
            "inside no published territory", placement.uncovered, total
        ).as_dict(),
    }
    if baseline is not None:
        row["contested_difference_from_the_rule_as_built"] = Difference.between(
            "this variant minus the rule as built, contested share",
            contested,
            baseline,
            note=(
                "The same records measured twice against two different sets of "
                "outlines. The two proportions are positively correlated rather than "
                "independent, so a method built for two independent samples gives a "
                "wider interval here than a paired method would. It is published as "
                "the conservative bound. The exact figures are the two contested "
                "counts, which are a census and not an estimate."
            ),
        ).as_dict()
    if supplied is not None:
        row["supplied_by_a_reviewer"] = True
        row["reviewer_role"] = supplied.reviewer_role
        row["reviewed_on"] = supplied.reviewed_on
        row["rule_file"] = supplied.file_name
        # Keyed by the outline name rather than listed, because the name is the
        # identifier and a list would be a published collection whose order the
        # ordering ledger would have to declare against an artifact that carries
        # it only when a reviewer supplied one. `serialise` sorts keys, and
        # `_read_overrides` builds them in name order, so both readings agree.
        row["outline_overrides"] = {o.outline: o.as_dict() for o in supplied.overrides}
    return row


def _types_present(collections: dict[str, dict[str, Any]]) -> list[str]:
    """Every ``Type`` value in the retrieval, read before any rule filters one out.

    Taken from the features rather than from the loaded territories, because the loader
    has already dropped everything outside the inclusion rule by the time it returns.
    Reading it from there would leave the unexpected-type check unable to ever fire,
    which is a gate that reports rather than a gate that works.
    """
    kinds: set[str] = set()
    for collection in collections.values():
        for feature in collection.get("features", []):
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue
            kind = properties.get("Type")
            if isinstance(kind, str) and kind.strip():
                kinds.add(kind.strip())
    return sorted(kinds)


def type_inclusion(
    collections: dict[str, dict[str, Any]],
    records: tuple[Record, ...],
    excluded_by_hazard: int,
    supplied: Sequence[SuppliedRule] = (),
) -> dict[str, Any]:
    """Re-place every record under each inclusion rule, and report what moves.

    The layers are read once, with every published type kept, and each variant is a
    filter over that one read. Reading them per variant would project the same polygons
    seven times for the same answer.

    ``supplied`` holds the rules a reviewer wrote, already loaded and already checked
    against this retrieval. Each one is run to completion over the same record set and
    lands as a row after the built ones, with the same denominator, the same interval
    and the same difference from the rule as built. The built rule stays the reference
    row and no supplied rule replaces it.
    """
    every, _ = load_territories(collections, keep_types=PUBLISHED_TYPES)
    seen = _types_present(collections)
    baseline: Rate | None = None
    rows: list[dict[str, Any]] = []
    for label, kinds in TYPE_VARIANTS:
        subset = tuple(t for t in every if t.kind in kinds)
        placement = classify(records, subset, excluded_by_hazard)
        rows.append(_variant_row(label, kinds, placement, len(subset), baseline))
        if baseline is None:
            baseline = Rate.of(CONTESTED_LABEL, placement.contested, len(records))
    for rule in supplied:
        subset = _subset_for(every, rule)
        placement = classify(records, subset, excluded_by_hazard)
        rows.append(
            _variant_row(
                rule.variant, rule.types, placement, len(subset), baseline, rule
            )
        )
    return {
        "question": (
            "How much of the headline figure rests on reading CO-OP and Tribal as "
            "service territories, and on not reading CCA and ADMIN as territories?"
        ),
        "rule_as_built": list(WIRES_TYPES),
        "published_types_present_in_this_retrieval": seen,
        "unexpected_published_types": sorted(set(seen) - set(PUBLISHED_TYPES)),
        "the_published_type_field_is_undocumented": TYPE_FIELD_IS_UNDOCUMENTED,
        "variants": rows,
        "note": (
            "No rule is chosen here and none is changed. Each row is the whole record "
            "set re-placed against a different set of published outlines, so a reader "
            "can see which parts of the inclusion rule the result depends on. A variant "
            "that raises the uncovered count is reporting that records the dropped "
            "entities do sit over would be published as inside no territory, which is a "
            "statement about coverage that the dropped entity's own polygon contradicts."
        ),
    }


def _signature_outcome(signature: tuple[str, ...] | None) -> str:
    if signature is None:
        return "coordinate_not_usable"
    if not signature:
        return "covered_by_no_published_territory"
    if len(signature) == 1:
        return "placed_in_exactly_one_territory"
    return "contested_between_two_or_more"


def _transitions(
    chosen: tuple[tuple[str, ...] | None, ...],
    alternative: tuple[tuple[str, ...] | None, ...],
) -> tuple[Counter[tuple[str, str]], int, int]:
    """Count the records whose signature differs, by the transition they make."""
    moves: Counter[tuple[str, str]] = Counter()
    changed = 0
    same_outcome_other_outline = 0
    for left, right in zip(chosen, alternative, strict=True):
        if left == right:
            continue
        changed += 1
        pair = (_signature_outcome(left), _signature_outcome(right))
        moves[pair] += 1
        if pair[0] == pair[1]:
            same_outcome_other_outline += 1
    return moves, changed, same_outcome_other_outline


def _placed_count(signatures: tuple[tuple[str, ...] | None, ...]) -> int:
    return sum(1 for s in signatures if s is not None and len(s) == 1)


def repair_comparison(
    collections: dict[str, dict[str, Any]],
    records: tuple[Record, ...],
    chosen: tuple[Territory, ...],
) -> dict[str, Any]:
    """Place every record under every repair, and count the disagreement.

    The published pair is ``make_valid`` against ``buffer_zero``, which is the
    comparison ADR 0007 was written around. The structure-preserving repair joins as a
    third reading of the same invalid geometry: it is placed over the whole record set
    too, and the pairwise and union disagreement counts below are what bound the
    ambiguity the publisher's invalid polygons leave behind. The default does not move.
    """
    strategies = [MAKE_VALID]
    territories_by_strategy = {MAKE_VALID: chosen}
    signatures_by_strategy = {MAKE_VALID: containment_signatures(records, chosen)}
    unusable_by_strategy: dict[str, int] = {}
    for strategy in REPAIR_STRATEGIES:
        if strategy == MAKE_VALID:
            continue
        alternative_territories, alternative_unusable = load_territories(
            collections, strategy=strategy
        )
        strategies.append(strategy)
        territories_by_strategy[strategy] = alternative_territories
        signatures_by_strategy[strategy] = containment_signatures(
            records, alternative_territories
        )
        unusable_by_strategy[strategy] = len(alternative_unusable)

    total = len(records)
    pairwise = [
        {
            "between": [left, right],
            "records": sum(
                1
                for one, two in zip(
                    signatures_by_strategy[left],
                    signatures_by_strategy[right],
                    strict=True,
                )
                if one != two
            ),
        }
        for left, right in itertools.combinations(strategies, 2)
    ]
    any_disagree = sum(
        1
        for index in range(total)
        if len({signatures[index] for signatures in signatures_by_strategy.values()})
        > 1
    )

    # The detailed census stays on the pair ADR 0007 documents, so the report section
    # keeps one transitions table rather than one per pair. The full set is above.
    alternative = BUFFER_ZERO
    chosen_signatures = signatures_by_strategy[MAKE_VALID]
    alternative_signatures = signatures_by_strategy[alternative]
    moves, changed, same_outcome = _transitions(
        chosen_signatures, alternative_signatures
    )
    chosen_placed = Rate.of(
        f"placed in exactly one published territory, under {MAKE_VALID}",
        _placed_count(chosen_signatures),
        total,
    )
    alternative_placed = Rate.of(
        f"placed in exactly one published territory, under {alternative}",
        _placed_count(alternative_signatures),
        total,
    )
    return {
        "question": (
            "How much of the result depends on which repair is applied to the polygons "
            "the publisher ships invalid?"
        ),
        "chosen": MAKE_VALID,
        "alternative": alternative,
        "strategies_compared": strategies,
        "territories_indexed": {
            strategy: len(territories_by_strategy[strategy]) for strategy in strategies
        },
        "territories_unusable_under_the_alternative": unusable_by_strategy.get(
            alternative, 0
        ),
        "territories_unusable_under_each_strategy": unusable_by_strategy,
        "records_with_a_different_outcome": Rate.of(
            f"records {MAKE_VALID} and {alternative} disagree about",
            changed,
            total,
            note=(
                "Counted per record, not inferred from two totals. A record counts here "
                "if the set of outlines it falls inside is not the same under both "
                "repairs, including when both repairs agree on the kind of outcome."
            ),
        ).as_dict(),
        "records_where_any_two_repairs_disagree": Rate.of(
            "records where at least one pair of repairs disagrees",
            any_disagree,
            total,
            note=(
                "The union over every pair of the strategies compared. It is at least "
                "as large as any single pairwise count, and it is the number that "
                "bounds how much of the result the choice of repair can move."
            ),
        ).as_dict(),
        "pairwise_disagreements": sorted(pairwise, key=lambda row: row["between"]),
        "records_with_the_same_outcome_but_different_outlines": same_outcome,
        "transitions": [
            {"under_the_chosen_repair": a, "under_the_alternative": b, "records": n}
            for (a, b), n in sorted(moves.items())
        ],
        "placed_under_the_chosen_repair": chosen_placed.as_dict(),
        "placed_under_the_alternative": alternative_placed.as_dict(),
        "placed_difference": Difference.between(
            f"{MAKE_VALID} minus {alternative}, placed share",
            chosen_placed,
            alternative_placed,
            note=(
                "The same records placed twice, so the two proportions are not "
                "independent and this Newcombe interval is the conservative bound "
                "rather than the tight one. The exact figure is the disagreement count "
                "above, which needs no interval because it is a census of the "
                "difference and not an estimate of it."
            ),
        ).as_dict(),
        "note": (
            "No repair is correct. Each is an answer to a question the published "
            "polygon does not answer, and the disagreement between them is the size of "
            "the ambiguity the publisher's invalid geometry leaves behind."
        ),
    }


def untouched_outlines(
    placement: Placement,
    records: tuple[Record, ...],
    chosen: tuple[Territory, ...],
) -> dict[str, Any]:
    """Which published outlines hold no record, and what dropping them would change.

    A reader can reasonably doubt whether a particular outline in this layer belongs in
    a retail service territory set at all. This project does not answer that, because
    answering it means classifying a named organisation from outside the publisher's own
    field, which ADR 0002 refuses. It can answer the narrower question the doubt is
    usually a proxy for: could that outline be moving a published figure?

    For an outline no record falls inside, the answer is no, and it is arithmetic rather
    than judgment. Removing an outline can only change the signature of a record that
    was inside it, so a record inside none of the removed outlines keeps the outcome it
    had. That is asserted here by re-placing the whole record set against the reduced
    index and counting the records whose signature moves, which is a census and not an
    argument.
    """
    untouched = tuple(
        t
        for t in chosen
        if placement.tallies[t.name].placed == 0
        and placement.tallies[t.name].contested == 0
    )
    reduced = tuple(t for t in chosen if t not in untouched)
    names = frozenset(t.name for t in untouched)
    before = containment_signatures(records, chosen)
    # An empty index is not something a spatial tree can be built over, and it is not
    # something this comparison needs one for: with every outline removed, every record
    # with a coordinate is inside none of them, which is what the second branch writes.
    after = (
        containment_signatures(records, reduced)
        if reduced
        else tuple(None if s is None else () for s in before)
    )
    _, changed, _ = _transitions(before, after)
    touching = sum(1 for s in before if s is not None and not names.isdisjoint(s))
    total = len(records)
    return {
        "question": (
            "Is a published outline that a reader might question capable of moving a "
            "published figure at all?"
        ),
        "outlines_no_record_falls_inside": sorted(t.name for t in untouched),
        "outlines_no_record_falls_inside_count": len(untouched),
        "outlines_indexed": len(chosen),
        "records_inside_at_least_one_of_them": Rate.of(
            "records falling inside an outline that holds no record",
            touching,
            total,
            note=(
                "Zero by construction when it is zero: an outline holds no record "
                "exactly when no record falls inside it. It is counted from the "
                "signatures rather than asserted, so the two cannot drift apart."
            ),
        ).as_dict(),
        "records_with_a_different_outcome_without_them": Rate.of(
            "records whose outcome changes when all of them are removed",
            changed,
            total,
            note=(
                "The whole record set placed again against the reduced index. Every "
                "published figure in this repository is a function of these signatures, "
                "so a zero here is the statement that no published figure moves."
            ),
        ).as_dict(),
        "note": (
            "This is a count, not a classification. It does not establish that any of "
            "the outlines named here is or is not a retail service territory, and this "
            "project does not decide that; see ADR 0002 and ADR 0010. What it "
            "establishes is that the question cannot change a figure published here, "
            "because the outlines it would be asked about hold nothing."
        ),
    }
