"""The served page: what it says, what it is made of, and what it refuses.

The load-bearing test here is :func:`test_the_page_says_exactly_what_the_document_says`,
and it is deliberately not the test the issue asked for. "Every figure on the page equals
the artifact's" catches a *wrong* number and cannot catch a *missing* one: a renderer that
dropped a row satisfies a lookup per figure, because the figures it does publish are all
correct. So the comparison here is set-for-set and ordered: every text node on the page,
against every text node of the Markdown, both directions, same order, same multiplicity.

The one thing on the page that is not a text node of the document is each table's
``<caption>``, and those are held separately, to their own two halves. Nothing else is
exempt, and :func:`test_the_exemption_is_exactly_the_captions` counts the exemption so it
cannot quietly grow.

Colour is measured here rather than by an engine because jsdom paints no pixels: the
contrast rule is one of the four ``tools/a11y.mjs`` declares it cannot decide. Chromium
does decide it, in ``tools/a11y_browser/axe.spec.ts``. This module is the arithmetic
floor under both.
"""

from __future__ import annotations

import itertools
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from wildfire_service_territory_overlap import page, report
from wildfire_service_territory_overlap.catalog import ENGLISH, Catalog, translation

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / page.PAGE_NAME

#: Elements whose text is a unit of content. ``caption`` is read and then separated out
#: by name, rather than skipped, so the exemption is a number this module prints.
TEXT_ELEMENTS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "th", "td", "caption"}
)

Unit = tuple[str, object]


class Reader(HTMLParser):
    """A parser that has never seen ``page.py``, walking the emitted markup.

    Not a regular expression over the file and not the renderer's own data structures:
    a comparison whose two sides were produced by one piece of code compares that code
    against itself. This side is stdlib.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.units: list[Unit] = []
        self.tags: list[str] = []
        self.attributes: list[tuple[str, dict[str, str]]] = []
        self._open: list[tuple[str, list[str], int]] = []
        self._row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.append((tag, {k: (v or "") for k, v in attrs}))
        if tag == "tr":
            self._row = []
        if tag in TEXT_ELEMENTS:
            # A slot is reserved where the element *opens*, not where it closes: a
            # list item holding a nested list closes after its own children, so
            # appending on the closing tag would report a parent bullet as coming
            # after the bullets underneath it.
            slot = -1
            if tag not in {"th", "td"}:
                slot = len(self.units)
                self.units.append(("pending", ""))
            self._open.append((tag, [], slot))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.append((tag, {k: (v or "") for k, v in attrs}))

    def handle_endtag(self, tag: str) -> None:
        if tag in TEXT_ELEMENTS and self._open and self._open[-1][0] == tag:
            name, parts, slot = self._open.pop()
            text = " ".join("".join(parts).split())
            if name in {"th", "td"}:
                assert self._row is not None
                self._row.append(text)
            elif name in {"caption", "p", "li"}:
                self.units[slot] = (name, text)
            else:
                self.units[slot] = ("h", text)
        if tag == "tr" and self._row is not None:
            self.units.append(("tr", tuple(self._row)))
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._open:
            self._open[-1][1].append(data)


def read(markup: str) -> Reader:
    reader = Reader()
    reader.feed(markup)
    assert not [unit for unit in reader.units if unit[0] == "pending"], (
        "an element opened and never closed, so the page is not well-formed and "
        "every comparison below would be over a document nobody can parse"
    )
    return reader


def html_units(markup: str) -> list[Unit]:
    return read(markup).units


def markdown_units(document: str) -> list[Unit]:
    """The same content units, read off the Markdown by the block parser."""
    out: list[Unit] = []
    for block in page.blocks(document):
        if isinstance(block, page.Heading):
            out.append(("h", page.plain(block.text)))
        elif isinstance(block, page.Paragraph):
            out.append(("p", page.plain(block.text)))
        elif isinstance(block, page.Bullets):
            for item in block.items:
                out.append(("li", page.plain(item.text)))
                out.extend(("li", page.plain(child)) for child in item.children)
        else:
            out.append(("tr", tuple(page.plain(cell) for cell in block.header)))
            out.extend(
                ("tr", tuple(page.plain(cell) for cell in row)) for row in block.rows
            )
    return out


@pytest.fixture(scope="module")
def document(published_artifact: dict[str, Any]) -> str:
    return report.render(published_artifact)


@pytest.fixture(scope="module")
def markup(published_artifact: dict[str, Any]) -> str:
    return page.render(published_artifact)


# ---------------------------------------------------------------------------
# What the page says. The two-directional comparison.
# ---------------------------------------------------------------------------


def test_the_page_says_exactly_what_the_document_says(
    document: str, markup: str
) -> None:
    """Every text node, both directions, in order, with multiplicity.

    A dropped row, an added row, a reordered section, a changed figure and a changed
    word all fail this. A per-figure lookup fails only the fourth.
    """
    want = markdown_units(document)
    got = [unit for unit in html_units(markup) if unit[0] != "caption"]
    assert got == want


def test_the_comparison_is_over_a_population_worth_comparing(
    document: str, markup: str
) -> None:
    """The floor. An empty comparison satisfies the test above.

    The numbers are asserted as lower bounds rather than as equalities: this document
    grows a row every time California has a fire season, and a hand-maintained count
    would jam the queue for having done nothing wrong. What must never happen is the
    population collapsing.
    """
    units = markdown_units(document)
    rows = [unit for unit in units if unit[0] == "tr"]
    assert len(units) >= 300, len(units)
    assert len(rows) >= 200, len(rows)
    assert {unit[0] for unit in units} == {"h", "p", "li", "tr"}
    assert len(html_units(markup)) == len(units) + len(
        [unit for unit in html_units(markup) if unit[0] == "caption"]
    )


def test_a_number_changed_on_the_page_is_caught(document: str, markup: str) -> None:
    """The injected-figure control, run as a test rather than described as one."""
    tampered = markup.replace(
        '<td class="num">82,353</td>', '<td class="num">82,354</td>', 1
    )
    assert tampered != markup, (
        "the anchor is not in the page; re-read it before trusting this"
    )
    want = markdown_units(document)
    got = [unit for unit in html_units(tampered) if unit[0] != "caption"]
    assert got != want


def test_a_row_dropped_from_the_page_is_caught(document: str, markup: str) -> None:
    """The control the issue's own wording would have missed.

    Every figure still on the page is still correct, so a lookup per figure passes.
    """
    reader = read(markup)
    rows = [unit for unit in reader.units if unit[0] == "tr"]
    victim = rows[3]
    lines = markup.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if line == "<tr>"
        and any(
            cell in "".join(lines[index : index + 8])
            for cell in [str(victim[1][0])]  # type: ignore[index]
        )
    )
    end = lines.index("</tr>", start)
    tampered = "\n".join(lines[:start] + lines[end + 1 :])
    got = [unit for unit in html_units(tampered) if unit[0] != "caption"]
    want = markdown_units(document)
    assert len(got) == len(want) - 1
    assert got != want


# ---------------------------------------------------------------------------
# The captions: the one exemption, and both halves of it.
# ---------------------------------------------------------------------------


def test_the_exemption_is_exactly_the_captions(markup: str) -> None:
    captions = [unit for unit in html_units(markup) if unit[0] == "caption"]
    tables = markup.count("<table>")
    assert tables >= 10, tables
    assert len(captions) == tables


def test_every_caption_is_composed_of_its_section_and_its_first_column(
    document: str, markup: str
) -> None:
    """Both halves come from the catalog; the em dash is punctuation.

    Checked against the document rather than against the renderer, so a caption that
    started naming something the page does not say fails here.
    """
    section = ""
    expected: list[str] = []
    for block in page.blocks(document):
        if isinstance(block, page.Heading) and block.level >= 2:
            section = block.text
        elif isinstance(block, page.Table):
            expected.append(page.caption_for(section, block))
    found = [str(unit[1]) for unit in html_units(markup) if unit[0] == "caption"]
    assert found == expected
    for caption in found:
        head, _, column = caption.partition(": ")
        assert head and column, caption
        assert head in document
        assert column in document


def test_no_two_tables_carry_the_same_caption(markup: str) -> None:
    """A caption is how a reader tells two tables in one section apart."""
    found = [str(unit[1]) for unit in html_units(markup) if unit[0] == "caption"]
    assert len(set(found)) == len(found), sorted(found)


def test_every_scroll_region_is_labelled_by_its_own_caption(markup: str) -> None:
    """A container a keyboard can focus has to say what it is.

    ``tabindex="0"`` on the scroll container is WCAG 2.1.1: a region that scrolls for
    a pointer and not for a keyboard is a serious failure, and it is one no DOM-only
    engine can see. The label is the table's caption, which every table here has.
    """
    reader = read(markup)
    regions = [attrs for tag, attrs in reader.attributes if tag == "section"]
    caption_ids = {attrs["id"] for tag, attrs in reader.attributes if tag == "caption"}
    assert regions
    assert len(caption_ids) == len(regions)
    for attrs in regions:
        assert attrs.get("tabindex") == "0"
        assert attrs.get("class") == "scroll"
        assert attrs["aria-labelledby"] in caption_ids


# ---------------------------------------------------------------------------
# Structure a screen reader depends on.
# ---------------------------------------------------------------------------


def test_every_table_header_cell_carries_a_scope(markup: str) -> None:
    reader = read(markup)
    headers = [attrs for tag, attrs in reader.attributes if tag == "th"]
    assert headers
    assert {attrs.get("scope") for attrs in headers} == {"col", "row"}
    assert all(attrs.get("scope") in {"col", "row"} for attrs in headers)


def test_the_first_cell_of_every_body_row_is_a_row_header(
    document: str, markup: str
) -> None:
    rows = [unit for unit in html_units(markup) if unit[0] == "tr"]
    body_rows = sum(
        len(b.rows) for b in page.blocks(document) if isinstance(b, page.Table)
    )
    reader = read(markup)
    assert reader.tags.count("th") >= body_rows
    assert len(rows) == body_rows + markup.count("<table>")


def test_the_page_has_exactly_one_h1_and_one_main(markup: str) -> None:
    reader = read(markup)
    assert reader.tags.count("h1") == 1
    assert reader.tags.count("main") == 1
    assert reader.tags.count("body") == 1


def test_no_heading_level_is_skipped(markup: str) -> None:
    levels = [int(tag[1]) for tag in read(markup).tags if re.fullmatch(r"h[1-6]", tag)]
    assert levels[0] == 1
    for previous, level in itertools.pairwise(levels):
        assert level <= previous + 1, (previous, level)


def test_the_document_declares_its_language_and_its_title(markup: str) -> None:
    assert markup.startswith('<!doctype html>\n<html lang="en">\n')
    assert (
        "<title>Which published electric service territory is a burned structure in?</title>"
        in markup
    )


def test_the_language_comes_from_the_catalog_and_not_from_the_renderer() -> None:
    """A second edition announces itself as itself.

    The `lang` attribute is what a screen reader switches voice on. A default would
    mean a Spanish edition read aloud in English, which is the shape of every other
    absence-rendered-as-a-value defect this project refuses.
    """
    mirrored = translation("Mirror", dict(ENGLISH), lang="es")
    assert 'lang="es"' in page.to_html("# Title\n\nBody.\n", lang=mirrored.lang)
    assert mirrored.lang != ENGLISH.lang


def test_a_catalog_has_to_name_a_language() -> None:
    with pytest.raises(Exception, match="language"):
        Catalog("Nameless", dict(ENGLISH), lang="")


# ---------------------------------------------------------------------------
# Nothing loads, nothing is said by colour.
# ---------------------------------------------------------------------------


def test_the_page_loads_nothing_and_runs_nothing(markup: str) -> None:
    """No script, no font, no image, no network reference of any kind.

    A served page that fetches something is a page whose behaviour depends on a third
    party, and a measurement that reads differently depending on who is reachable is
    not a measurement.
    """
    reader = read(markup)
    for forbidden in ("script", "img", "iframe", "link", "object", "embed", "video"):
        assert forbidden not in reader.tags, forbidden
    for scheme in ("http://", "https://", "//", "url("):
        assert scheme not in markup, scheme
    assert "style=" not in markup


def test_every_colour_on_the_page_is_a_declared_palette_colour(markup: str) -> None:
    declared = {
        value for palette in page.PALETTES.values() for value in palette.values()
    }
    used = set(re.findall(r"#[0-9a-fA-F]{3,8}", markup))
    assert used == declared, (used - declared, declared - used)


def test_the_two_palettes_declare_the_same_names() -> None:
    assert set(page.LIGHT) == set(page.DARK)
    assert set(page.PALETTES) == {"light", "dark"}


def test_every_declared_pair_meets_its_threshold_in_both_palettes() -> None:
    """SC 1.4.3 for text, SC 1.4.11 for a boundary or a focus indicator.

    Arithmetic, not a screenshot, because jsdom cannot decide the rule and a browser
    deciding it once is not the same as the palette being right by construction.
    """
    failures = []
    for scheme, palette in page.PALETTES.items():
        for pair in page.PAIRS:
            ratio = page.contrast(palette[pair.foreground], palette[pair.background])
            if ratio < pair.minimum:
                failures.append(
                    f"{scheme}: {pair.foreground} on {pair.background} is {ratio:.2f}:1, "
                    f"below {pair.minimum} ({pair.where})"
                )
    assert not failures, failures


def test_the_contrast_arithmetic_agrees_with_the_published_reference_values() -> None:
    """Two known answers, so a broken formula cannot pass by being generous."""
    assert page.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert page.contrast("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert page.contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


def test_the_pair_list_covers_every_colour_the_stylesheet_puts_together(
    markup: str,
) -> None:
    """Self-limiting, both directions.

    A pair naming a colour the sheet does not carry exempts nothing; a colour used as
    a foreground with no pair for it is a colour nothing measured.
    """
    sheet = page.stylesheet()
    named = {name for pair in page.PAIRS for name in (pair.foreground, pair.background)}
    assert named == set(page.LIGHT), (named - set(page.LIGHT), set(page.LIGHT) - named)
    for name in named:
        assert f"--{name.replace('_', '-')}:" in sheet
        assert f"var(--{name.replace('_', '-')})" in markup
    for pair in page.PAIRS:
        assert pair.where and pair.minimum in {3.0, 4.5}


def test_a_colour_that_is_not_a_lowercase_hex_triple_is_refused() -> None:
    for bad in ("#FFF", "white", "#12345", "rgb(0,0,0)"):
        with pytest.raises(page.PageRefused, match="hex colour"):
            page.luminance(bad)


# ---------------------------------------------------------------------------
# Determinism, and the committed bytes.
# ---------------------------------------------------------------------------


def test_building_twice_gives_the_same_bytes(
    published_artifact: dict[str, Any],
) -> None:
    assert page.render(published_artifact) == page.render(published_artifact)


def test_the_committed_page_is_what_the_renderer_produces_now(
    published_artifact: dict[str, Any],
) -> None:
    """`site/index.html` is a derived artifact of a committed input, so it is checkable.

    `published/` is built from `data/raw/`, which is not in git and never in CI, so
    nothing here can rebuild it. The page is different: it is a pure function of
    `published/measurements.json`, which *is* committed, so the bytes that get served
    can be regenerated and compared on every run. If this fails after a refresh, run
    `make site`.
    """
    assert SITE.is_file(), "site/index.html is missing; run `make site`"
    assert SITE.read_text(encoding="utf-8") == page.render(published_artifact)


def test_the_committed_page_renders_the_committed_document(
    published_report: str, published_artifact: dict[str, Any]
) -> None:
    """The page and REPORT.md are two renderings of one string, not two measurements."""
    assert page.to_html(published_report, lang=ENGLISH.lang) == page.render(
        published_artifact
    )


def test_the_command_line_writes_the_page_where_it_is_told(tmp_path: Path) -> None:
    out = tmp_path / "site"
    assert (
        page.main(
            [
                "--artifact",
                str(ROOT / "published" / "measurements.json"),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    written = out / page.PAGE_NAME
    assert written.is_file()
    assert written.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_the_page_is_written_with_unix_line_endings(tmp_path: Path) -> None:
    out = tmp_path / "site" / page.PAGE_NAME
    page.write_page("<!doctype html>\n<html></html>\n", out)
    assert b"\r" not in out.read_bytes()


# ---------------------------------------------------------------------------
# The converter refuses what it cannot render.
# ---------------------------------------------------------------------------


HEAD = "# Title\n\nIntroducing the table.\n\n"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("# Title\n\n```\ncode\n```\n", "fenced code block"),
        ("# Title\n\nSee [the report](https://example.invalid/).\n", "a link"),
        ("# Title\n\nSee <https://example.invalid/>.\n", "a link"),
        ("# Title\n\nAn `unclosed span.\n", "unclosed code span"),
        ("# Title\n\nAn **unclosed strong.\n", "unclosed strong span"),
        ("# Title\n\nA trailing backslash \\\n", "trailing backslash"),
        (HEAD + "| A | B |\n| Alpha | 12 |\n", "not a delimiter row"),
        (HEAD + "| A | B |\n|---|---|\n| Alpha |\n", "under a header of 2"),
        (HEAD + "| A | B |\n|---|\n", "declares 1 columns"),
        ("# Title\n\n  - orphan\n", "no bullet above it"),
        ("", "the document is empty"),
        ("Body with no heading.\n", "level one heading"),
        ("## Not a title\n\nBody.\n", "level one heading"),
        ("# Title\n\n- a bullet\ntext with no blank line\n", "interrupting a bullet"),
    ],
)
def test_the_converter_refuses_what_it_cannot_render(
    document: str, message: str
) -> None:
    with pytest.raises(page.PageRefused, match=re.escape(message)):
        page.to_html(document, lang="en")


def test_a_nested_bullet_list_renders_as_a_nested_list() -> None:
    """The shape a reviewer-supplied inclusion rule adds to the document.

    No committed build carries one, so this is the only place the branch is exercised;
    without it the converter would first meet that shape on the day a reviewer file
    arrives, which is the day it must not fail.
    """
    markup = page.to_html(
        "# Title\n\n- **Rule**, supplied by a reviewer.\n"
        "  - An outline is read as a territory here: because.\n"
        "  - continued on a second line.\n",
        lang="en",
    )
    assert markup.count("<ul>") == 2
    assert "<li><strong>Rule</strong>, supplied by a reviewer.\n<ul>" in markup
    units = [unit for unit in html_units(markup) if unit[0] == "li"]
    assert units == [
        ("li", "Rule, supplied by a reviewer."),
        ("li", "An outline is read as a territory here: because."),
        ("li", "continued on a second line."),
    ]


def test_a_nested_list_round_trips_as_well() -> None:
    """The reader reports a parent bullet before the bullets underneath it.

    A parent `<li>` closes after its children, so a reader appending on the closing
    tag reports the three in the wrong order -- and the committed document carries no
    nested list, so the round-trip test over it would never have said so. This is the
    branch the reviewer-supplied-rule section will take on the day one arrives.
    """
    document = (
        "# Title\n\n- **Rule**, supplied by a reviewer.\n"
        "  - An outline is read as a territory here: because.\n"
        "- A second rule.\n"
    )
    got = [
        unit
        for unit in html_units(page.to_html(document, lang="en"))
        if unit[0] != "caption"
    ]
    assert got == markdown_units(document)


def test_a_wrapped_paragraph_becomes_one_paragraph() -> None:
    markup = page.to_html("# Title\n\nA sentence\nwrapped in the source.\n", lang="en")
    assert "<p>A sentence wrapped in the source.</p>" in markup


def test_a_pipe_inside_a_cell_reaches_the_reader_as_a_pipe() -> None:
    markup = page.to_html(
        HEAD + "| A | B |\n|---|---|\n| one \\| two | 3 |\n", lang="en"
    )
    assert '<th scope="row">one | two</th>' in markup


def test_markup_inside_a_code_span_is_not_converted() -> None:
    """A published value that happens to contain asterisks is a value, not emphasis."""
    markup = page.to_html("# Title\n\nA literal `**not strong**` value.\n", lang="en")
    assert "<code>**not strong**</code>" in markup
    assert "<strong>" not in markup


def test_the_alignment_of_a_column_comes_from_the_delimiter_row() -> None:
    markup = page.to_html(
        HEAD + "| A | B | C |\n|---|---:|:---:|\n| one | 2 | 3 |\n", lang="en"
    )
    assert '<th scope="col">A</th>' in markup
    assert '<th scope="col" class="num">B</th>' in markup
    assert '<th scope="col" class="mid">C</th>' in markup


def test_the_stylesheet_cannot_split_a_number_in_a_table() -> None:
    """The floor under `tools/a11y_browser/numbers.spec.ts`, holding without a browser.

    The first version of this page let every table cell break anywhere, so at 320
    pixels 396 of 711 numeric cells printed a number across two lines and only 1 of 14
    scroll regions scrolled; every accessibility engine stayed green over it. The
    browser spec measures the property with layout. This asserts the two rules that
    produced it are absent, so a later tidy-up that restores them fails here first,
    before anybody has installed Chromium.
    """
    sheet = page.stylesheet()
    cells = sheet.split("th, td {", 1)[1].split("}", 1)[0]
    code = sheet.split("code {", 1)[1].split("}", 1)[0]
    numeric = sheet.split(".num {", 1)[1].split("}", 1)[0]
    assert "overflow-wrap" not in cells
    assert "overflow-wrap" not in code
    assert "word-break" not in sheet
    assert "white-space: nowrap" in numeric
    # And prose still reflows: the paragraph and list rules are where breaking
    # anywhere is right, because they have no container to scroll in.
    assert "overflow-wrap: anywhere" in sheet.split("p {", 1)[1].split("}", 1)[0]
    assert "overflow-wrap: anywhere" in sheet.split("li {", 1)[1].split("}", 1)[0]
