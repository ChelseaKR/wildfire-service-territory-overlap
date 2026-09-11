"""The string catalog, and what has to hold across every edition of the report.

Two things are held here. The first is that no word the document prints is written in
the renderer: `report.py` may carry structure, artifact keys and numbers, and nothing
else. The second is that a second edition changes the words and nothing else, so every
figure, every interval and every ordering in one edition is the same as in the other.
"""

from __future__ import annotations

import ast
import copy
import inspect
import json
import re
from pathlib import Path
from string import Formatter
from typing import Any

import pytest

from wildfire_service_territory_overlap import report, sensitivity
from wildfire_service_territory_overlap.catalog import (
    ARTIFACT_DATA_FIELDS,
    ARTIFACT_PROSE_FIELDS,
    ENGLISH,
    Catalog,
    CatalogRefused,
    _string_leaves,
    artifact_prose,
    translation,
    unclassified_string_fields,
)
from wildfire_service_territory_overlap.placement import read_records
from wildfire_service_territory_overlap.sources import ELSE_IOU_POU, ELSE_OTHER

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
RENDERER = ROOT / "src" / "wildfire_service_territory_overlap" / "report.py"
RENDERER_SOURCE = RENDERER.read_text(encoding="utf-8")

LETTER = re.compile(r"[A-Za-z]")

# Methods whose string argument addresses the artifact rather than the reader.
# `append` and `extend` are deliberately absent: that is how a line reaches the
# document, so a literal handed to one of them is output and gets checked.
KEY_METHODS = frozenset({"get", "index", "replace", "startswith", "endswith", "split"})


def _is_string(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _docstrings(module: ast.Module) -> set[int]:
    """A docstring documents the code and never reaches the document."""
    holders = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    found: set[int] = set()
    for node in ast.walk(module):
        if not isinstance(node, holders):
            continue
        first = node.body[0] if node.body else None
        if isinstance(first, ast.Expr) and _is_string(first.value):
            found.add(id(first.value))
    return found


def _artifact_keys(module: ast.Module) -> set[int]:
    """A literal that addresses the artifact rather than the reader.

    A subscript key, a comparison against a published value, and an argument to one of
    the methods above. None of the three can print.
    """
    found: set[int] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Subscript):
            found |= {id(x) for x in ast.walk(node.slice) if _is_string(x)}
        elif isinstance(node, ast.Compare):
            parts = (node.left, *node.comparators)
            found |= {id(x) for x in parts if _is_string(x)}
        elif isinstance(node, ast.Call):
            method = node.func
            if isinstance(method, ast.Attribute) and method.attr in KEY_METHODS:
                found |= {id(x) for x in node.args if _is_string(x)}
    return found


def _format_specs(module: ast.Module) -> set[int]:
    """The inside of a format spec: how a number is punctuated, not what it is called."""
    found: set[int] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            found |= {id(x) for x in ast.walk(node.format_spec) if _is_string(x)}
    return found


def _excused(module: ast.Module) -> set[int]:
    """Every string literal in the module that cannot reach the document."""
    return _docstrings(module) | _artifact_keys(module) | _format_specs(module)


def inline_prose(source: str) -> list[str]:
    """Every string literal in `source` that a reader could read, in source order."""
    module = ast.parse(source)
    excused = _excused(module)
    found: list[str] = []
    for node in ast.walk(module):
        if not _is_string(node) or id(node) in excused:
            continue
        assert isinstance(node, ast.Constant)
        if LETTER.search(node.value):
            found.append(node.value)
    return found


def catalog_keys_used(source: str) -> set[str]:
    """Every catalog key the renderer asks for, read out of the renderer itself."""
    keys: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Subscript):
            continue
        target = node.value
        if not isinstance(target, ast.Name) or target.id != "cat":
            continue
        for inner in ast.walk(node.slice):
            if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                keys.add(inner.value)
    return keys


def test_the_renderer_carries_no_word_of_its_own() -> None:
    """The completeness gate: a string a reader reads may not live in `report.py`."""
    assert inline_prose(RENDERER_SOURCE) == []


SAMPLE_WITH_PROSE = '''
def _section(tree, cat):
    """A docstring is documentation and never reaches the document."""
    lines = [
        cat["limits.heading"],
        "## What this does not measure",
        f"| {tree['territory']} | {tree['published_type']} |",
        f"{tree['rate'] * 100:.1f}%",
    ]
    if tree.get("state") != "measured":
        lines.append("reference")
    return lines
'''


def test_the_completeness_gate_can_actually_fire() -> None:
    """Guard the guard.

    A gate nobody has watched refuse is a gate nobody knows can refuse. The sample
    above carries one heading and one bare lowercase word in output position, next to
    every shape that is allowed to stay in the renderer: a docstring, a catalog lookup,
    artifact keys, a `.get` argument, a comparison against a published value, table
    pipes and a format spec. Only the two prose strings come back.
    """
    assert inline_prose(SAMPLE_WITH_PROSE) == [
        "## What this does not measure",
        "reference",
    ]


def test_every_key_the_renderer_asks_for_is_in_the_catalog_and_no_others() -> None:
    """A key with no string raises at render time; a string with no key is dead weight."""
    assert catalog_keys_used(RENDERER_SOURCE) == set(ENGLISH)


def test_the_catalog_is_declared_in_a_stable_order() -> None:
    keys = list(ENGLISH)
    assert len(keys) == len(set(keys))
    assert keys[0] == "words.not_measured"
    assert list(ENGLISH) == keys, "iterating the catalog twice gave two orders"


def test_no_catalog_entry_carries_a_format_spec_or_conversion() -> None:
    """An edition cannot be given a way to punctuate a number.

    `{records:,}` in a catalog entry would let one edition write a figure differently
    from another inside the same artifact. Every field is a bare name, so the only code
    that decides how a number looks is `report.pct`, `report.count` and `report.span`.
    """
    for key, entry in ENGLISH.items():
        for _, field, spec, conversion in Formatter().parse(entry):
            if field is None:
                continue
            assert not spec, f"{key} formats {field} itself"
            assert not conversion, f"{key} converts {field} itself"


def test_the_numeric_helpers_cannot_be_handed_a_catalog() -> None:
    """The structural half of "numbers are never re-formatted per locale"."""
    for helper in (report.pct, report.count, report.span):
        signature = str(inspect.signature(helper))
        assert "Catalog" not in signature, f"{helper.__name__} can see the catalog"


def _mirror(entry: str) -> str:
    """The same entry with every word reversed and every placeholder left alone."""
    parts: list[str] = []
    for literal, field, _, _ in Formatter().parse(entry):
        parts.append(re.sub(r"[A-Za-z]+", lambda m: m.group()[::-1], literal))
        if field is not None:
            parts.append("{" + field + "}")
    return "".join(parts)


# The mirror edition is written in no language, so it declares the private-use
# subtag rather than borrowing one. A test edition claiming to be `es` would put a
# language code on a page nobody could read, which is the shape this catalog's own
# `lang` requirement exists to refuse.
MIRROR = translation(
    "Mirror",
    {key: _mirror(value) for key, value in ENGLISH.items()},
    lang="qaa",
)


def test_a_second_edition_is_refused_unless_it_is_a_complete_one() -> None:
    entries = dict(ENGLISH)
    dropped = entries.copy()
    del dropped["limits.heading"]
    with pytest.raises(CatalogRefused, match="carries no string"):
        translation("Short", dropped, lang="qaa")

    extra = entries.copy()
    extra["limits.afterword"] = "nothing renders this"
    with pytest.raises(CatalogRefused, match="nothing renders"):
        translation("Long", extra, lang="qaa")

    blank = entries.copy()
    blank["limits.heading"] = ""
    with pytest.raises(CatalogRefused, match="empty string"):
        translation("Blank", blank, lang="qaa")


def test_an_edition_that_drops_a_placeholder_is_refused() -> None:
    """The refusal that matters: a lost placeholder is a lost measurement.

    `str.format` ignores a keyword nothing uses, so an entry that quietly drops
    `{fire_records}` renders a sentence with the number missing and raises nothing.
    """
    entries = dict(ENGLISH)
    entries["coverage.intro"] = entries["coverage.intro"].replace(
        "{fire_records}", "some"
    )
    with pytest.raises(CatalogRefused, match="drops a measured number"):
        translation("Lossy", entries, lang="qaa")


def test_a_catalog_names_its_edition_and_refuses_an_empty_name() -> None:
    with pytest.raises(CatalogRefused, match="name its edition"):
        Catalog("", dict(ENGLISH), lang="qaa")
    assert ENGLISH.edition
    assert ENGLISH.lang == "en"
    with pytest.raises(KeyError, match="carries no string"):
        ENGLISH["nothing.declares.this"]


NUMBER = re.compile(r"\d+(?:,\d+)*(?:\.\d+)?%?")
# What a figure looks like in this project: either ungrouped digits, which is how a
# year and a small count are written, or groups of three after a comma. A full stop
# before the decimals in both cases. Both editions have to write every number this way.
ENGLISH_SHAPED = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?%?$")


def _artifact_strings(node: Any) -> set[str]:
    if isinstance(node, str):
        return {node}
    if isinstance(node, dict):
        return set().union(*(_artifact_strings(v) for v in node.values()), set())
    if isinstance(node, list):
        return set().union(*(_artifact_strings(v) for v in node), set())
    return set()


def _row_labels(document: str, known: set[str]) -> list[str]:
    """The first cell of every table row that names something the artifact carries."""
    labels: list[str] = []
    for line in document.splitlines():
        if not line.startswith("| "):
            continue
        cell = line.split("|")[1].strip()
        if cell in known:
            labels.append(cell)
    return labels


def test_two_editions_agree_on_every_number_interval_and_ordering(
    published_artifact: dict[str, Any],
) -> None:
    """Roadmap 4.2's constraint, held by a test rather than by intent.

    The mirror edition holds the same keys and different strings. Everything that is
    not a word has to come out of both renders identically: every figure, both ends of
    every interval, and the order of every row.
    """
    english = report.render(published_artifact, ENGLISH)
    mirrored = report.render(published_artifact, MIRROR)
    assert english != mirrored, (
        "the mirror edition changed no word, so this proves none"
    )

    assert NUMBER.findall(english) == NUMBER.findall(mirrored)
    assert len(NUMBER.findall(english)) > 100, "the fixture carries almost no figures"

    known = _artifact_strings(published_artifact)
    labels = _row_labels(english, known)
    assert labels == _row_labels(mirrored, known)
    assert len(labels) > 20, "the row scan found almost nothing to compare"

    territories = [row["territory"] for row in published_artifact["territories"]]
    assert [cell for cell in labels if cell in set(territories)] == territories


def test_neither_edition_writes_a_number_in_another_locale_form(
    published_artifact: dict[str, Any],
) -> None:
    for document in (
        report.render(published_artifact, ENGLISH),
        report.render(published_artifact, MIRROR),
    ):
        for token in NUMBER.findall(document):
            assert ENGLISH_SHAPED.match(token), token
        assert re.search(r",\d{1,2}%", document) is None, "a decimal comma appeared"


def test_the_words_for_a_measurement_that_was_not_made_come_from_the_edition(
    published_artifact: dict[str, Any],
) -> None:
    """The one phrase most likely to be left behind in the renderer."""
    english = report.render(published_artifact, ENGLISH)
    mirrored = report.render(published_artifact, MIRROR)
    assert ENGLISH["words.not_measured"] in english
    assert english.count(ENGLISH["words.not_measured"]) == mirrored.count(
        MIRROR["words.not_measured"]
    )
    assert ENGLISH["words.not_measured"] not in mirrored


def _before_the_third_repair(tree: dict[str, Any]) -> dict[str, Any]:
    """The artifact shape a tree built before the third repair joined the census has."""
    older = copy.deepcopy(tree)
    repair = older["sensitivity"]["repair_strategy"]
    del repair["strategies_compared"]
    repair["transitions"] = []
    return older


def test_the_two_repair_rendering_reads_from_the_catalog_as_well(
    published_artifact: dict[str, Any],
) -> None:
    """The branch a published tree no longer takes, kept honest anyway.

    `_sensitivity_repair` renders two ways, and only one of them is reachable from
    today's artifact. The sentences below are what the renderer wrote for the other one
    before the strings moved to the catalog, checked here so the unreachable half
    cannot rot, and checked against the mirror edition so it obeys the same rule.
    """
    older = _before_the_third_repair(published_artifact)
    english = report.render(older, ENGLISH)
    assert "Both repairs run to completion over the same records." in english
    assert "The two repairs place every record the same way." in english
    assert "Neither repair is correct." in english

    mirrored = report.render(older, MIRROR)
    assert NUMBER.findall(english) == NUMBER.findall(mirrored)
    assert ENGLISH["words.not_measured"] not in mirrored


def test_the_render_entry_point_defaults_to_the_english_edition(
    published_artifact: dict[str, Any],
) -> None:
    assert report.render(published_artifact) == report.render(
        published_artifact, ENGLISH
    )


def test_no_command_line_flag_offers_a_choice_of_one_language() -> None:
    """The scaffolding this change deliberately did not build (`docs/adr/0016`).

    A `--lang` accepting only `en` is a menu with one item. The edition is a parameter
    of `render`, so a second edition is a catalog rather than a flag that has to be
    taught a second value.
    """
    cli = (ROOT / "src" / "wildfire_service_territory_overlap" / "cli.py").read_text(
        encoding="utf-8"
    )
    for flag in ("--lang", "--language", "--locale"):
        assert flag not in cli, f"{flag} accepts one value and means nothing yet"


# --- The artifact's own English, which no edition reaches (`docs/adr/0017`) ---------


def artifact_prose_fields_the_renderer_reads(source: str) -> set[str]:
    """Every artifact prose field `report.py` subscripts, read out of the renderer.

    Read from the syntax rather than listed, so a renderer that starts printing a new
    one, or stops printing an old one, moves this set instead of leaving a hand-copied
    list behind.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Subscript):
            continue
        for inner in ast.walk(node.slice):
            if isinstance(inner, ast.Constant) and inner.value in ARTIFACT_PROSE_FIELDS:
                found.add(inner.value)
    return found


def _field_of(path: str) -> str:
    return path.rsplit(".", 1)[-1]


def _printed_by_the_document(
    document: str, prose: list[tuple[str, str]], fields: set[str]
) -> set[str]:
    """The artifact strings the document puts in front of a reader.

    Two shapes, because the renderer emits these two ways and no other: a row label is
    the whole first cell of a table row, and every other one ends a line, either alone
    or after a bullet's bold lead-in.
    """
    first_cells = {
        line.split("|")[1].strip()
        for line in document.splitlines()
        if line.startswith("| ")
    }
    lines = document.splitlines()
    return {
        text
        for path, text in prose
        if text
        and _field_of(path) in fields
        and (text in first_cells or any(line.endswith(text) for line in lines))
    }


def test_every_string_field_in_the_published_artifact_is_classified(
    published_artifact: dict[str, Any],
) -> None:
    """A field carrying a new sentence is a decision, taken when the field is added.

    The two declared lists cover the 37 string-valued fields the published artifact
    carries. A thirty-eighth arriving unclassified is the question `docs/adr/0017`
    asks, turning up again in a place nobody was looking.
    """
    assert unclassified_string_fields(published_artifact) == set()
    fields = {_field_of(path) for path, _ in artifact_prose(published_artifact)}
    assert fields == set(ARTIFACT_PROSE_FIELDS)
    assert not set(ARTIFACT_PROSE_FIELDS) & set(ARTIFACT_DATA_FIELDS)


def test_the_unclassified_field_check_can_actually_fire() -> None:
    """Guard the guard: a sentence under a name nobody has classified comes back."""
    invented = {"territories": [{"territory": "A", "footnote": "a new sentence"}]}
    assert unclassified_string_fields(invented) == {"footnote"}
    assert artifact_prose(invented) == []
    assert artifact_prose({"note": "", "rows": [{"label": "a"}]}) == [
        ("$.note", ""),
        ("$.rows[0].label", "a"),
    ]


def test_the_artifact_carries_prose_that_no_edition_reaches(
    published_artifact: dict[str, Any],
) -> None:
    """The census `docs/adr/0017` quotes, held so the ADR cannot go stale quietly.

    A refresh that moves these counts moves the numbers in that document too, and this
    test is where that is noticed.
    """
    prose = artifact_prose(published_artifact)
    written = [text for _, text in prose if text]
    assert len(prose) == 1205
    assert len(written) == 960
    assert len(set(written)) == 102


def test_the_renderer_reads_six_of_the_ten_prose_fields_out_of_the_artifact() -> None:
    """Which of the artifact's sentences a reader of the document actually meets."""
    read = artifact_prose_fields_the_renderer_reads(RENDERER_SOURCE)
    assert read == {
        "county_note",
        "label",
        "note",
        "reason",
        "the_published_type_field_is_undocumented",
        "variant",
    }
    assert set(ARTIFACT_PROSE_FIELDS) - read == {
        "affiliation",
        "geometry_note",
        "no_trend_is_published",
        "question",
    }


def test_the_document_prints_twenty_eight_of_the_artifacts_own_strings(
    published_artifact: dict[str, Any], published_report: str
) -> None:
    """The size of the gap a second edition would print around, measured not guessed.

    `docs/I18N.md` says a second edition would print translated prose around English
    row labels. This is how much English: 28 strings of the artifact's 102, carried by
    65 of its 1,205 prose leaves. The other 74 never leave `measurements.json`.
    """
    prose = artifact_prose(published_artifact)
    fields = artifact_prose_fields_the_renderer_reads(RENDERER_SOURCE)
    printed = _printed_by_the_document(published_report, prose, fields)
    assert len(printed) == 28
    assert sum(1 for _, text in prose if text in printed) == 65
    assert "inside two or more published territories" in printed
    assert "no records are placed in this territory" not in printed


def test_a_supplied_inclusion_rule_carries_no_unclassified_string_field() -> None:
    """The census reaches the fields only a reviewer-supplied build can produce.

    `test_every_string_field_in_the_published_artifact_is_classified` reads the
    committed artifact, which was built with no rule file and therefore carries none of
    these fields. Without this, four new published strings could reach a reader with
    nobody having said whether an edition will ever have to translate them, and the gate
    that exists to ask that question would have been looking somewhere else.
    """
    supplied = sensitivity.read_rule_files(
        [
            FIXTURES / "inclusion_rule_example.json",
            FIXTURES / "inclusion_rule_dropping_the_cooperative.json",
        ]
    )
    collections = {
        ELSE_IOU_POU.key: json.loads(
            (FIXTURES / "else_iou_pou_sample.geojson").read_text(encoding="utf-8")
        ),
        ELSE_OTHER.key: json.loads(
            (FIXTURES / "else_other_sample.geojson").read_text(encoding="utf-8")
        ),
    }
    records, excluded = read_records(
        json.loads((FIXTURES / "dins_sample.json").read_text(encoding="utf-8"))
    )
    block = sensitivity.type_inclusion(collections, records, excluded, supplied)
    assert any(row.get("supplied_by_a_reviewer") for row in block["variants"])
    assert unclassified_string_fields(block) == set()
    prose = {field for _, field, _ in _string_leaves(block, "$", "")}
    for field in ("reviewed_on", "reviewer_reason", "reviewer_role", "rule_file"):
        assert field in prose, f"{field} never reached the tree, so nothing was checked"
        assert field in ARTIFACT_DATA_FIELDS
