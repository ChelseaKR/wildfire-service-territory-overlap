"""The gate every published number passes through, and the deterministic writer.

The rules here are enforced rather than reviewed by eye, because a rule that lives in a
style guide gets broken by the next contributor and a rule that raises does not. The
first group reads the measurement tree and is called from ``write_json``. The second
group reads the rendered Markdown and is called from ``write_report``; those rules are
listed under their own heading further down, beside the reasoning for moving them out
of a dated review and into the build.

``assert_rates_are_denominated``
    Nothing shaped like a rate leaves this project without its numerator, its
    denominator, its interval and the method that produced the interval. A measured rate
    must have a positive denominator and a real interval. A not-measured rate must have
    no value and no interval, so a measurement that could not be made can never be read
    as a zero.

``assert_no_locating_fields``
    No coordinate, address, parcel number, or per-structure identifier appears in a
    published artifact. The source file carries all of them and none is fetched, so this
    is a second lock on a door that is already shut.

``assert_aggregate_only``
    No published collection may be longer than the number of things being reported on.
    A per-structure list cannot appear without tripping it, whatever it is named.

``assert_no_ranking``
    Territories come out sorted by name, and no key in the output orders, scores, or
    grades one against another. This project describes geography; it does not rate
    companies, and the output should not be one edit away from doing so.

``assert_contested_groups_are_whole``
    The overlap table is capped at the largest combinations. The rows must still sum to
    the published contested total, so a combination cut for sitting past the cap cannot
    take its records out of the artifact without the build stopping. The total is
    required rather than used where present: an artifact that publishes the table and
    not the number it sums to is refused, because otherwise the one rule that can catch
    a cut table goes quiet exactly when the build has changed shape.

``assert_collections_are_ordered_as_declared``
    Every published collection appears in ``ORDERINGS`` with the order it comes out in,
    and a collection missing from that ledger refuses the artifact. Name order is the
    rule; the three collections that are not in name order carry the reason next to the
    declaration rather than only in the sort key that produces them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

RATE_KEYS: tuple[str, ...] = (
    "numerator",
    "denominator",
    "interval_low",
    "interval_high",
    "interval_method",
    "state",
)

LOCATING_KEYS: frozenset[str] = frozenset(
    {
        "apn",
        "address",
        "coordinates",
        "geometry",
        "lat",
        "latitude",
        "lon",
        "long",
        "longitude",
        "objectid",
        "parcel",
        "siteaddress",
        "streetname",
        "streetnumber",
        "x",
        "y",
        "zipcode",
    }
)

RANKING_KEYS: frozenset[str] = frozenset(
    {"best", "grade", "position", "rank", "ranking", "rating", "score", "worst"}
)


class PublicationRefused(ValueError):
    """An artifact broke one of this project's publication rules and was not written."""


def _walk(node: Any, path: str = "$") -> list[tuple[str, Any]]:
    found = [(path, node)]
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk(value, f"{path}[{index}]"))
    return found


def _check_measured_rate(path: str, node: dict[str, Any]) -> None:
    if node["denominator"] <= 0:
        raise PublicationRefused(
            f"{path}: a measured rate has a denominator of {node['denominator']}. "
            "Zero out of zero is not zero percent."
        )
    for key in ("rate", "interval_low", "interval_high"):
        if node.get(key) is None:
            raise PublicationRefused(f"{path}: a measured rate is missing {key}")
    if node["interval_method"] in ("", "none"):
        raise PublicationRefused(f"{path}: a measured rate names no interval method")


def _check_not_measured_rate(path: str, node: dict[str, Any]) -> None:
    for key in ("rate", "interval_low", "interval_high"):
        if node.get(key) is not None:
            raise PublicationRefused(
                f"{path}: a not-measured rate carries {key}. A measurement that could "
                "not be made has no value, not a zero."
            )


def assert_rates_are_denominated(tree: Any) -> None:
    """Refuse any rate-shaped object that does not carry its denominator and interval."""
    for path, node in _walk(tree):
        if not isinstance(node, dict) or "rate" not in node:
            continue
        missing = [key for key in RATE_KEYS if key not in node]
        if missing:
            raise PublicationRefused(
                f"{path}: a rate is missing {', '.join(missing)}. A count without a "
                "denominator is not a risk and a rate without an interval is not a "
                "comparison."
            )
        if node["state"] == "measured":
            _check_measured_rate(path, node)
        else:
            _check_not_measured_rate(path, node)


def assert_differences_carry_intervals(tree: Any) -> None:
    """A difference between two proportions needs an interval for the difference itself."""
    for path, node in _walk(tree):
        if not isinstance(node, dict) or "difference" not in node:
            continue
        if not isinstance(node.get("difference"), float | int | type(None)):
            continue
        for key in ("interval_low", "interval_high", "interval_method", "state"):
            if key not in node:
                raise PublicationRefused(f"{path}: a difference is missing {key}")
        if node["state"] == "measured" and node["interval_low"] is None:
            raise PublicationRefused(f"{path}: a measured difference has no interval")


def assert_no_locating_fields(tree: Any) -> None:
    """Refuse an artifact carrying anything that could place a structure or an asset."""
    for path, node in _walk(tree):
        if not isinstance(node, dict):
            continue
        for key in node:
            if key.lower() in LOCATING_KEYS:
                raise PublicationRefused(
                    f"{path}.{key}: published artifacts carry counts about geography, "
                    "never a position. Nothing here locates a structure, a parcel, or "
                    "any piece of anybody's infrastructure."
                )


def assert_aggregate_only(tree: Any, max_rows: int) -> None:
    """Refuse a collection long enough to be a record-level listing."""
    for path, node in _walk(tree):
        if isinstance(node, list) and len(node) > max_rows:
            raise PublicationRefused(
                f"{path}: a published collection holds {len(node)} entries against a "
                f"ceiling of {max_rows}. Published output is aggregate; a list this "
                "long is a record listing under another name."
            )


def assert_no_ranking(tree: Any) -> None:
    """Refuse a key that orders, scores, or grades one territory against another."""
    for path, node in _walk(tree):
        if not isinstance(node, dict):
            continue
        for key in node:
            if key.lower() in RANKING_KEYS:
                raise PublicationRefused(
                    f"{path}.{key}: this project publishes descriptive geography. It "
                    "does not rate, rank, or score any named utility, and an artifact "
                    "key that does is refused."
                )


CONTESTED_TOTAL_KEY = "contested_between_two_or_more"


def _contested_total(tree: dict[str, Any]) -> int:
    """The published contested total the overlap table must account for, or a refusal.

    Named separately so that every way the number can be missing produces the same
    refusal, with the key that is absent in the message. The build writes this block
    and the table together; a tree that has one without the other is a build that has
    changed shape, and that is exactly when a rule reading "absent" as "nothing to
    check" would go quiet.
    """
    coverage = tree.get("placement_coverage")
    if not isinstance(coverage, dict):
        raise PublicationRefused(
            "$.contested_groups: the artifact publishes a contested-groups table and no "
            "$.placement_coverage block to check it against. The table is capped, so "
            "without the published total nothing can tell a whole table from one cut "
            "short."
        )
    counts = coverage.get("counts")
    if not isinstance(counts, dict) or CONTESTED_TOTAL_KEY not in counts:
        raise PublicationRefused(
            f"$.placement_coverage.counts: carries no {CONTESTED_TOTAL_KEY!r}, and the "
            "artifact publishes a contested-groups table that has to sum to it. Publish "
            "the total, or do not publish the table."
        )
    total = counts[CONTESTED_TOTAL_KEY]
    if not isinstance(total, int):
        raise PublicationRefused(
            f"$.placement_coverage.counts.{CONTESTED_TOTAL_KEY}: is "
            f"{type(total).__name__}, not a record count. The contested table is "
            "checked by summing to it."
        )
    return total


def assert_contested_groups_are_whole(tree: Any) -> None:
    """Refuse a contested-groups table that leaves contested records out of itself.

    ``measure.contested_groups`` keeps the largest ``limit`` combinations and drops the
    rest. Today's retrieval produces twelve against a cap of 25, so nothing is dropped,
    but that is a fact about this retrieval rather than about the code. The published
    territory layer is not static, and a refresh that pushed the count past the cap
    would shorten this table with no line anywhere saying so.

    ``assert_aggregate_only`` cannot catch it. Its ceiling is the number of published
    outlines and never below 32, the cap is 25, so the only length rule in this module
    is numerically incapable of firing on this collection.

    Every contested record falls under exactly one combination of outlines, so the rows
    must sum to the published contested total. Where they do not, the difference is the
    number of records that would have gone missing from the table, and the artifact is
    refused rather than published short.

    **The total this sums against is required, not merely used when present.** A tree
    carrying no ``contested_groups`` publishes no such table and there is nothing here
    to be short, so it passes. Once the table is in the artifact, the absence of
    ``placement_coverage.counts.contested_between_two_or_more`` is a refusal. Reading
    it any other way makes the one rule that can catch a truncated table go quiet by
    losing the key it needs, so the very thing that goes missing when a build changes
    shape is what would silence the check. ``_field_values`` states the same
    discipline one rule down, that a missing field is a refusal rather than a
    traceback, and ``assert_collections_are_ordered_as_declared`` fails closed on
    arrival of a collection nobody declared. This rule was the one that did not.
    """
    if not isinstance(tree, dict):
        return
    rows = tree.get("contested_groups")
    if not isinstance(rows, list):
        # No contested-groups table in this tree, so nothing published here can be
        # short. This is the only absence that stays quiet, and it is quiet because
        # there is no table, not because the check lost its footing.
        return
    total = _contested_total(tree)
    shown = 0
    for index, row in enumerate(rows):
        # A row that does not carry an integer record count used to be dropped from the
        # sum, which refused the artifact for the right reason under the wrong name: the
        # message said a combination had been cut for sitting past the cap. Say what is
        # actually wrong with the row instead.
        if not isinstance(row, dict) or not isinstance(row.get("records"), int):
            raise PublicationRefused(
                f"$.contested_groups[{index}]: carries no integer 'records' count, so "
                "the table cannot be shown to account for every contested record. A "
                "row whose count cannot be read is not a row that counts zero."
            )
        shown += row["records"]
    if shown != total:
        raise PublicationRefused(
            f"$.contested_groups: the table accounts for {shown} of {total} contested "
            f"records, {abs(total - shown)} short. A combination dropped for sitting "
            "past the cap takes its records with it and the reader is told neither. "
            "Raise the cap, or publish what was cut with its own denominator, but do "
            "not publish this table short."
        )


BY_NAME = "name"
BY_SIZE = "size"
DECLARED = "declared"

ORDERINGS: dict[str, tuple[str, str]] = {
    # Every published collection, and the order it comes out in. A collection with no
    # entry here is refused, so a new one cannot reach a reader without somebody saying
    # what its order means. The second element is the field a name order runs on, an
    # empty string when the elements are scalars, and the reason when the order is
    # neither by name nor by size.
    "$.attributability_by_fire.by_county": (BY_NAME, "county"),
    "$.attributability_by_fire.by_incident_year": (BY_NAME, "year"),
    "$.contested_groups": (
        BY_SIZE,
        "the row is a combination of outlines rather than an entity, and the largest "
        "combinations are the ones the cap keeps, which a name order cannot select",
    ),
    "$.contested_groups[].boundary_proximity.bands_m": (BY_NAME, ""),
    "$.contested_groups[].boundary_proximity.rates": (
        DECLARED,
        "one rate per band, in the band order printed directly above it",
    ),
    "$.contested_groups[].territories": (BY_NAME, ""),
    "$.coordinate_county_agreement.by_county": (BY_NAME, "county"),
    "$.excluded_types": (BY_NAME, "published_type"),
    "$.geometry_ledger.repaired": (BY_NAME, ""),
    "$.geometry_ledger.unusable": (BY_NAME, ""),
    "$.placement_coverage.rates": (
        DECLARED,
        "the four outcomes in the order the report reads them, placed then contested "
        "then uncovered then not measured, which is a sequence and not a score",
    ),
    "$.representativeness_by_category": (BY_NAME, "structure_category"),
    "$.sensitivity.repair_strategy.pairwise_disagreements": (BY_NAME, "between"),
    "$.sensitivity.repair_strategy.pairwise_disagreements[].between": (
        DECLARED,
        "the two repairs named in the order REPAIR_STRATEGIES declares them, so the "
        "pair reads the same way everywhere it appears",
    ),
    "$.sensitivity.repair_strategy.strategies_compared": (
        DECLARED,
        "REPAIR_STRATEGIES order, which puts the repair that produces the published "
        "figures first and the candidates it was compared against after it",
    ),
    "$.sensitivity.repair_strategy.transitions": (BY_NAME, "under_the_chosen_repair"),
    "$.sensitivity.type_inclusion.published_types_present_in_this_retrieval": (
        BY_NAME,
        "",
    ),
    "$.sensitivity.type_inclusion.rule_as_built": (BY_NAME, ""),
    "$.sensitivity.type_inclusion.unexpected_published_types": (BY_NAME, ""),
    "$.sensitivity.type_inclusion.variants": (
        DECLARED,
        "the rule as built first, because every other row is published as a difference "
        "from it, then the variants in the order ADR 0006 argues them, then any rule a "
        "reviewer supplied, in the filename order of the files they were read from",
    ),
    "$.sensitivity.type_inclusion.variants[].types_read_as_territories": (BY_NAME, ""),
    "$.sensitivity.untouched_outlines.outlines_no_record_falls_inside": (BY_NAME, ""),
    "$.territories": (BY_NAME, "territory"),
    "$.territories[].boundary_proximity.bands_m": (BY_NAME, ""),
    "$.territories[].boundary_proximity.rates": (
        DECLARED,
        "one rate per band, in the band order the row publishes beside it",
    ),
    "$.territories[].contested_with": (BY_NAME, ""),
}

_INDEX = re.compile(r"\[\d+\]")


def generic_path(path: str) -> str:
    """The path with list indices flattened, so one entry covers every row."""
    return _INDEX.sub("[]", path)


def _field_values(rows: list[Any], field_name: str, where: str) -> list[Any]:
    """The values a declared order runs on, refusing a row that does not carry one.

    A missing field is a refusal rather than a traceback: this module is the last thing
    between a measurement and a reader, and it has to say what is wrong with the
    artifact rather than fail in a way that reads as a bug in the checker.
    """
    if not field_name:
        return list(rows)
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or field_name not in row:
            raise PublicationRefused(
                f"{where}: its declared order runs on {field_name!r}, and row {index} "
                "does not carry it. Declare the order this collection is actually in."
            )
    return [row[field_name] for row in rows]


def _name_ordered(rows: list[Any], field_name: str, where: str) -> bool:
    values = _field_values(rows, field_name, where)
    return values == sorted(values)


def _size_ordered(rows: list[Any], where: str) -> bool:
    counts = _field_values(rows, "records", where)
    names = [row.get("territories", []) for row in rows]
    keys = list(zip([-count for count in counts], names, strict=True))
    return keys == sorted(keys)


def assert_collections_are_ordered_as_declared(tree: Any) -> None:
    """Refuse a published collection out of its declared order, or with none declared.

    The README used to claim, without qualification, that every collection in the
    output is sorted by name. That was false in three places, and nothing read it, so
    it stayed false: `contested_groups` is in size order, `type_inclusion.variants`
    puts the rule as built first, and `repair_strategy.strategies_compared` follows
    REPAIR_STRATEGIES. A prose invariant nothing enforces is a claim, not a rule.

    So the claim is a ledger now. Every collection names its order and the reason when
    that order is neither by name nor by size, an undeclared collection refuses the
    artifact rather than publishing in whatever order it happened to come out in, and
    the exceptions are visible in one place instead of being discoverable only by
    reading the sort key.
    """
    for path, node in _walk(tree):
        if not isinstance(node, list):
            continue
        where = generic_path(path)
        declared = ORDERINGS.get(where)
        if declared is None:
            raise PublicationRefused(
                f"{where}: a published collection whose order nothing has declared. "
                "Add it to ORDERINGS with the order it comes out in, and with the "
                "reason when that order is neither by name nor by size. An order "
                "nobody stated is an order nobody checked."
            )
        kind, field_name = declared
        if len(node) < 2:
            continue
        if kind == BY_NAME and not _name_ordered(node, field_name, where):
            raise PublicationRefused(
                f"{where}: declared in name order and is not in it. Ordering a "
                "collection of named entities by a measured value is a ranking, "
                "whichever direction it runs."
            )
        if kind == BY_SIZE and not _size_ordered(node, where):
            raise PublicationRefused(
                f"{where}: declared in size order, largest first with the names "
                "breaking ties, and is not in it."
            )


def assert_territories_sorted_by_name(rows: list[dict[str, Any]]) -> None:
    """Refuse territory rows in any order other than alphabetical."""
    names = [str(row["territory"]) for row in rows]
    if names != sorted(names):
        raise PublicationRefused(
            "territory rows are not in name order. Ordering them by a measured value "
            "is a ranking, whichever direction it runs."
        )


def check_all(tree: dict[str, Any], *, max_rows: int) -> None:
    """Every publication rule, in one call, before anything is written."""
    assert_rates_are_denominated(tree)
    assert_differences_carry_intervals(tree)
    assert_no_locating_fields(tree)
    assert_aggregate_only(tree, max_rows)
    assert_no_ranking(tree)
    assert_contested_groups_are_whole(tree)
    assert_collections_are_ordered_as_declared(tree)
    rows = tree.get("territories")
    if isinstance(rows, list):
        assert_territories_sorted_by_name(rows)


def serialise(tree: dict[str, Any]) -> str:
    """One representation, so an unchanged measurement is an unchanged file."""
    return json.dumps(tree, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(tree: dict[str, Any], path: Path, *, max_rows: int) -> Path:
    """Check, then write. An artifact that fails a rule is not written at all."""
    check_all(tree, max_rows=max_rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialise(tree), encoding="utf-8")
    return path


# --- The rendered document, held to the same refusal as the artifact ---------------
#
# `docs/ACR.md` asserted the structure of the generated report as a static review of
# one build of one version, dated 2026-08-22. A reviewed-once claim about generated
# output goes stale the moment the renderer changes, and nothing here would have said
# so: a published territory name arriving with a `|` in it shifts every cell after it
# under the wrong column name, a published type arriving empty leaves a cell that is
# announced as its column heading and then silence, and a section added at the wrong
# depth puts a heading in the outline with no parent. Each of those breaks a claim in
# that document, none of them is visible by eye over a 500-line table, and every one
# of them is a question about text that can be asked on every build.
#
# So the mechanically checkable claims are asked on every build now, through the same
# refusal the artifact rules use. The claims that are a human reading stay a human
# reading, and `docs/ACR.md` says which is which.

NON_DESCRIPTIVE_LINK_TEXT: frozenset[str] = frozenset(
    {
        "click",
        "click here",
        "download",
        "follow this",
        "found here",
        "go",
        "here",
        "link",
        "more",
        "read more",
        "see here",
        "this",
        "this link",
        "this page",
    }
)

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_DELIMITER_CELL = re.compile(r"^:?-+:?$")
_HTML_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*(?:\s[^<>]*)?/?>")
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(")
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_URL_AS_TEXT = re.compile(r"^(?:https?://|www\.)", re.IGNORECASE)


def _prose_lines(document: str) -> list[tuple[int, str]]:
    """Every line outside a fenced code block, with its one-based line number.

    A fence holds a shell transcript or a directory listing. Neither is a table and
    neither is a heading, and reading them as one would refuse a document for the shape
    of its own example output.
    """
    lines: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(document.splitlines(), start=1):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            lines.append((number, line))
    return lines


def table_cells(row: str) -> list[str]:
    """The cells of one pipe-table row, splitting on unescaped pipes only.

    Markdown ends a cell at every `|` that is not backslash-escaped, including one
    inside a code span. A literal pipe in a value therefore adds a column rather than
    printing, which is how a row can look right in an editor and reach a reader with
    every cell after it announced under the wrong column name.
    """
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for character in row.strip():
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "|":
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    # A row is written with a leading and a trailing pipe, so the first and last pieces
    # are the empty strings outside the table rather than cells of it.
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [part.strip() for part in parts]


def _is_delimiter_row(row: str) -> bool:
    cells = table_cells(row)
    return bool(cells) and all(_DELIMITER_CELL.match(cell) for cell in cells)


def _table_blocks(document: str) -> list[list[tuple[int, str]]]:
    """Every run of consecutive pipe-table rows, each row with its line number."""
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, line in _prose_lines(document):
        if line.lstrip().startswith("|"):
            current.append((number, line))
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def assert_tables_have_a_header_row(document: str) -> None:
    """Refuse a table whose first row is not a header sitting over a delimiter row.

    The delimiter row is the whole of what makes a row a header in Markdown. Without
    it the block is not a table at all, and what reaches a reader is a run of cells
    with nothing anywhere saying what any of them is.
    """
    for block in _table_blocks(document):
        line, row = block[0]
        header_is_real = not _is_delimiter_row(row)
        has_delimiter = len(block) > 1 and _is_delimiter_row(block[1][1])
        if not (header_is_real and has_delimiter):
            raise PublicationRefused(
                f"line {line}: a table with no header row. A row is a header only "
                "because the delimiter row sits under it, and a table without one is "
                "announced as a run of cells with nothing saying what any of them "
                f"is: {row.strip()}"
            )


def assert_every_table_is_introduced(document: str) -> None:
    """Refuse a table that follows another table with nothing said between them.

    Two tables separated by one blank line are two tables to a reader looking at the
    page and one undifferentiated run to a reader moving through it linearly: the
    second arrives with nothing saying what it counts or how it differs from the first.

    `published/REPORT.md` broke this from the day the third repair joined the
    comparison until the refresh that carried the fix, and `docs/ACR.md` recorded it
    rather than gating it, because the rule would have refused the committed document
    and the published bytes are not edited to fit a gate. The order was the other way
    round: the renderer gained its introducing sentence, the refresh carried it into
    `published/`, and the rule went in behind it.
    """
    prose = dict(_prose_lines(document))
    numbered = sorted(prose)
    for block in _table_blocks(document):
        line = block[0][0]
        said_before = [n for n in numbered if n < line and prose[n].strip()]
        if not said_before:
            raise PublicationRefused(
                f"line {line}: a table opens the document. A reader meets a header row "
                "before anything has said what is being counted."
            )
        previous = prose[said_before[-1]]
        if previous.lstrip().startswith("|"):
            raise PublicationRefused(
                f"line {line}: a table follows a table with nothing between them. The "
                "blank line is a boundary on the page and silence to a reader going "
                f"through in order: {block[0][1].strip()}"
            )


def assert_tables_are_rectangular(document: str) -> None:
    """Refuse a row that does not carry the column count its own header declares."""
    for block in _table_blocks(document):
        header_line, header = block[0]
        columns = len(table_cells(header))
        for line, row in block[1:]:
            found = len(table_cells(row))
            if found != columns:
                raise PublicationRefused(
                    f"line {line}: a table row carries {found} cells under a header "
                    f"of {columns}, declared on line {header_line}. Every cell past "
                    "the mismatch is read under the wrong column name, which is worse "
                    "than no header at all. An unescaped `|` inside a published value "
                    f"is the usual cause: {row.strip()}"
                )


def assert_no_table_cell_is_empty(document: str) -> None:
    """Refuse an empty cell, which carries no context and is announced as nothing.

    A sighted reader takes an empty cell from the column above it or the row beside
    it. A reader hearing the row announced gets the column name and then silence, and
    silence is not a measurement. This project already has a word for a number it does
    not have.
    """
    for block in _table_blocks(document):
        for line, row in block:
            if _is_delimiter_row(row):
                continue
            for index, cell in enumerate(table_cells(row)):
                if not cell:
                    raise PublicationRefused(
                        f"line {line}: column {index + 1} of this row is empty. An "
                        "empty cell is announced as its column name followed by "
                        "nothing. Print the value, or print `not measured`: "
                        f"{row.strip()}"
                    )


def assert_headings_do_not_skip_a_level(document: str) -> None:
    """Refuse a document that opens below level one or skips a level on the way down.

    The heading list is how a document is navigated without being read in order. A
    level three under a level one puts a section in that list with no parent, and the
    reader cannot tell whether they have arrived inside something or beside it.
    """
    previous = 0
    for line, text in _prose_lines(document):
        match = _HEADING.match(text)
        if match is None:
            continue
        level = len(match.group(1))
        if previous == 0 and level != 1:
            raise PublicationRefused(
                f"line {line}: the document opens at heading level {level}. Its "
                f"first heading is its title and belongs at level one: {text.strip()}"
            )
        if previous and level > previous + 1:
            raise PublicationRefused(
                f"line {line}: a level {level} heading under a level {previous} one. "
                "A skipped level is a section that appears in the heading list with "
                f"no parent: {text.strip()}"
            )
        previous = level


def _is_descriptive(label: str) -> bool:
    stripped = label.strip().strip("`*_ ").strip()
    if not stripped or _URL_AS_TEXT.match(stripped):
        return False
    return stripped.lower().rstrip(".") not in NON_DESCRIPTIVE_LINK_TEXT


def assert_links_are_descriptive(document: str) -> None:
    """Refuse a link labelled with a URL, or with a word that names nothing.

    Link text is pulled out of its sentence and read in a list of links, where "here"
    is indistinguishable from every other "here" on the page and a URL is announced
    character by character.
    """
    for line, text in _prose_lines(document):
        autolink = _AUTOLINK.search(text)
        if autolink is not None:
            raise PublicationRefused(
                f"line {line}: {autolink.group(1)} is published as a link with no "
                "text of its own. A bare URL is read out character by character. Say "
                "what is at the other end of it."
            )
        for match in _MARKDOWN_LINK.finditer(text):
            if not _is_descriptive(match.group(1)):
                raise PublicationRefused(
                    f"line {line}: a link labelled {match.group(1).strip()!r}. Link "
                    "text is read in a list of links, out of the sentence that gave "
                    "it its meaning. Say where it goes."
                )


def assert_nothing_is_carried_by_styling(document: str) -> None:
    """Refuse an escape sequence or a markup tag in a published document.

    The claim this replaces was that the artifacts hold no ANSI codes and no styling,
    so nothing in them is said by colour. It was true when it was written and nothing
    was reading it. Colour is not announced; the escape sequence that produces it is.
    """
    if "\x1b" in document:
        raise PublicationRefused(
            "an ANSI escape sequence reached a published document. Nothing here may "
            "say anything by colour, and the escape itself is what gets read out."
        )
    for line, text in _prose_lines(document):
        tag = _HTML_TAG.search(text)
        if tag is not None:
            raise PublicationRefused(
                f"line {line}: the markup {tag.group(0)!r} reached a published "
                "document. This project publishes Markdown and JSON, with no styling "
                "layer for anything to be said in."
            )


def check_document(document: str) -> None:
    """Every rule the rendered document passes, in one call, before it is written."""
    assert_tables_have_a_header_row(document)
    assert_every_table_is_introduced(document)
    assert_tables_are_rectangular(document)
    assert_no_table_cell_is_empty(document)
    assert_headings_do_not_skip_a_level(document)
    assert_links_are_descriptive(document)
    assert_nothing_is_carried_by_styling(document)


def write_report(document: str, path: Path) -> Path:
    """Check, then write. A document that fails a rule is not written at all."""
    check_document(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
