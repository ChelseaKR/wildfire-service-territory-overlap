"""The same document, served: `published/REPORT.md` rendered as one HTML page.

The Markdown is the canonical document and this is a second rendering of it, not a
second measurement and not a second set of words. The whole page is a total function
of one string -- the document
:func:`wildfire_service_territory_overlap.report.render` produced -- so the page and
the report cannot disagree about a figure, a row, or an ordering. That is a stronger
guarantee than a second renderer walking the artifact would give, and it is the
reason this module converts rather than re-renders: two renderers reading one
artifact is two places a row can be dropped, and only one of them is the published
document.

What that buys, stated as the test that holds it: every text node on the page is a
text node of the Markdown, in the same order, with the same multiplicity, and the
only text on the page that is not is each table's ``<caption>``, which is composed
from its own section heading and its own first column header. So a renderer that
dropped a row fails, not only one that invented a number.
:mod:`tests.test_page` asserts both directions.

**The converter is total or it refuses.** Every construct it does not understand
raises :class:`PageRefused` and no file is written. A Markdown-to-HTML converter that
passes an unrecognised line through is a converter that publishes ``**`` and ``|`` to
a reader; one that drops it is worse. Neither happens here.

**Nothing is said by colour and nothing is scripted.** The page carries no script, no
web font, no image and no network reference of any kind. The palette is data below,
one entry per colour, and :mod:`tests.test_page` measures every foreground and
background pair that the stylesheet actually uses against the WCAG 2.2 thresholds,
arithmetically, in both the light and the dark presentation -- because a colour
contrast rule is one of the four an accessibility engine cannot decide in a DOM with
no layout.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wildfire_service_territory_overlap import report
from wildfire_service_territory_overlap.artifacts import (
    HEADING,
    is_delimiter_row,
    table_cells,
)
from wildfire_service_territory_overlap.catalog import ENGLISH, Catalog

PAGE_NAME = "index.html"


class PageRefused(ValueError):
    """A document the converter cannot render without inventing or dropping something."""


# ---------------------------------------------------------------------------
# The palette, as data.
#
# One dictionary per presentation, the same keys in both, and the stylesheet below is
# generated from them -- so a colour cannot be used on the page without being here,
# and tests/test_page.py asserts that in both directions. The pairs that actually
# occur are declared in PAIRS; the contrast test reads that list and would rather fail
# than assume.
# ---------------------------------------------------------------------------

LIGHT: dict[str, str] = {
    "page": "#ffffff",
    "surface": "#f3f5f7",
    "ink": "#16181c",
    "ink_quiet": "#4b5158",
    "rule": "#767d86",
    "focus": "#0b4f9e",
}

DARK: dict[str, str] = {
    "page": "#121417",
    "surface": "#1b1f24",
    "ink": "#eef1f4",
    "ink_quiet": "#b9c1ca",
    "rule": "#7d868f",
    "focus": "#79b0f2",
}

PALETTES: dict[str, dict[str, str]] = {"light": LIGHT, "dark": DARK}


@dataclass(frozen=True)
class Pair:
    """One foreground drawn on one background, and the ratio it has to reach.

    ``minimum`` is 4.5 for body text (WCAG 2.2 SC 1.4.3 Contrast (Minimum)), 3.0 for
    a user-interface component boundary or a focus indicator (SC 1.4.11 Non-text
    Contrast). ``where`` names the rule in the stylesheet that puts the two together,
    so the declaration can be checked against the sheet rather than against memory.
    """

    foreground: str
    background: str
    minimum: float
    where: str


PAIRS: tuple[Pair, ...] = (
    Pair("ink", "page", 4.5, "body text on the page"),
    Pair(
        "ink", "surface", 4.5, "table header and row-header text on the raised surface"
    ),
    Pair("ink_quiet", "page", 4.5, "the caption, and the generated-document note"),
    Pair("ink_quiet", "surface", 4.5, "the caption inside a scroll region"),
    Pair("rule", "page", 3.0, "the border of a scroll region against the page"),
    Pair("rule", "surface", 3.0, "the cell rules inside a table"),
    Pair("focus", "page", 3.0, "the focus indicator on a scroll region"),
    Pair("focus", "surface", 3.0, "the focus indicator over a table header"),
)


def _channel(value: int) -> float:
    """One sRGB channel, linearised, per WCAG 2.x relative luminance."""
    fraction = value / 255
    if fraction <= 0.04045:
        return fraction / 12.92
    return float(((fraction + 0.055) / 1.055) ** 2.4)


def luminance(colour: str) -> float:
    """Relative luminance of a ``#rrggbb`` colour."""
    if not re.fullmatch(r"#[0-9a-f]{6}", colour):
        raise PageRefused(
            f"{colour!r} is not a lowercase six-digit hex colour. The contrast "
            "arithmetic reads channels out of the string, so a shorthand or a named "
            "colour would be measured as something it is not."
        )
    red, green, blue = (int(colour[index : index + 2], 16) for index in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast(foreground: str, background: str) -> float:
    """The WCAG contrast ratio between two colours, 1.0 to 21.0."""
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def stylesheet() -> str:
    """The whole stylesheet, with every colour read out of the palettes above.

    The dark presentation is a media query rather than a toggle: there is no script
    on this page to hold a preference with, and a control that does nothing is worse
    than no control.

    **A table cell never breaks inside a word, and a numeric cell never wraps at
    all.** The first version let every cell break anywhere, so a wide table shrank to
    fit rather than scrolling: at 320 pixels 396 of 711 numeric cells printed a number
    split across two lines (`82,3` over `53`), only 1 of 14 scroll regions scrolled,
    and every accessibility engine stayed green, because a split number is still
    text. SC 1.4.10 allows a data table to scroll in two dimensions inside its own
    container, and that is what the containers are for. Paragraphs and list items
    still break anywhere, because they have to reflow.
    """

    def block(scheme: str, indent: str) -> str:
        pad = f"{indent}  "
        declarations = "".join(
            f"{pad}--{name.replace('_', '-')}: {value};\n"
            for name, value in PALETTES[scheme].items()
        )
        return (
            f"{indent}:root {{\n"
            f"{pad}color-scheme: {scheme};\n"
            f"{declarations}"
            f"{indent}}}\n"
        )

    return (
        block("light", "")
        + "@media (prefers-color-scheme: dark) {\n"
        + block("dark", "  ")
        + "}\n"
        + """
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font: 1rem/1.6 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial,
    sans-serif;
}
main {
  max-width: 62rem;
  margin: 0 auto;
  padding: 1.5rem 1rem 4rem;
}
h1 { font-size: 1.75rem; line-height: 1.25; margin: 0 0 1rem; }
h2 { font-size: 1.3rem; line-height: 1.3; margin: 2.5rem 0 0.75rem; }
h3 { font-size: 1.1rem; line-height: 1.3; margin: 2rem 0 0.75rem; }
p { margin: 0 0 1rem; overflow-wrap: anywhere; }
ul { margin: 0 0 1rem; padding-left: 1.25rem; }
li { margin: 0 0 0.35rem; overflow-wrap: anywhere; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.95em;
}
.scroll {
  overflow-x: auto;
  border: 1px solid var(--rule);
  background: var(--surface);
  margin: 0 0 1.5rem;
}
table { border-collapse: collapse; width: 100%; }
caption {
  text-align: left;
  padding: 0.6rem 0.75rem;
  color: var(--ink-quiet);
  font-size: 0.9rem;
}
th, td {
  border-top: 1px solid var(--rule);
  padding: 0.45rem 0.75rem;
  text-align: left;
  vertical-align: top;
}
thead th { background: var(--surface); }
th[scope="row"] { font-weight: 600; }
.num { text-align: right; white-space: nowrap; }
.mid { text-align: center; }
:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  * { scroll-behavior: auto; }
}
"""
    )


# ---------------------------------------------------------------------------
# The document, parsed.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Bullet:
    text: str
    children: tuple[str, ...]


@dataclass(frozen=True)
class Bullets:
    items: tuple[Bullet, ...]


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    alignments: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


Block = Heading | Paragraph | Bullets | Table

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_LINK = re.compile(r"\[[^\]]*\]\(")
_AUTOLINK = re.compile(r"<(?:https?://[^>\s]+)>")
_ALIGNMENT = re.compile(r"^(:?)-+(:?)$")


def _alignment(cell: str) -> str:
    match = _ALIGNMENT.match(cell)
    if match is None:  # pragma: no cover - is_delimiter_row has already said yes
        raise PageRefused(f"{cell!r} is not a table delimiter cell")
    left, right = match.group(1), match.group(2)
    if left and right:
        return "mid"
    if right:
        return "num"
    return ""


def _table(rows: Sequence[str], first_line: int) -> Table:
    if len(rows) < 2 or not is_delimiter_row(rows[1]):
        raise PageRefused(
            f"line {first_line}: a table whose second row is not a delimiter row. "
            "The delimiter row is the whole of what makes the row above it a header, "
            "and without one there is nothing to put a scope on."
        )
    header = tuple(table_cells(rows[0]))
    alignments = tuple(_alignment(cell) for cell in table_cells(rows[1]))
    if len(alignments) != len(header):
        raise PageRefused(
            f"line {first_line}: the delimiter row declares {len(alignments)} columns "
            f"under a header of {len(header)}."
        )
    body: list[tuple[str, ...]] = []
    for offset, row in enumerate(rows[2:], start=first_line + 2):
        cells = tuple(table_cells(row))
        if len(cells) != len(header):
            raise PageRefused(
                f"line {offset}: a row of {len(cells)} cells under a header of "
                f"{len(header)}. Every cell past the mismatch would be announced "
                "under the wrong column name."
            )
        body.append(cells)
    return Table(header=header, alignments=alignments, rows=tuple(body))


class _Walk:
    """One pass over the document's lines, accumulating blocks.

    A class rather than a closure so the two halves of the decision -- is this line a
    heading, a table row or a blank, and if it is none of those is it a bullet, a
    continuation or a paragraph -- can be read separately. They were one function and
    it was over the complexity cap, which is the cap doing its job: the second half is
    the part with the subtle rule in it.
    """

    def __init__(self) -> None:
        self.found: list[Block] = []
        self._paragraph: list[str] = []
        self._bullets: list[Bullet] = []
        self._rows: list[str] = []
        self._table_started_at = 0

    def close(self) -> None:
        if self._paragraph:
            self.found.append(Paragraph(" ".join(self._paragraph)))
            self._paragraph = []
        if self._bullets:
            self.found.append(Bullets(tuple(self._bullets)))
            self._bullets = []
        if self._rows:
            self.found.append(_table(self._rows, self._table_started_at))
            self._rows = []

    def feed(self, number: int, line: str) -> None:
        if _FENCE.match(line):
            raise PageRefused(
                f"line {number}: a fenced code block. The served page has no styling "
                "for one and the document has never carried one; adding one is a "
                "decision about what the page looks like, not a conversion."
            )
        if not line.strip():
            self.close()
            return
        if line.lstrip().startswith("|"):
            if not self._rows:
                self.close()
                self._table_started_at = number
            self._rows.append(line)
            return
        if self._rows:
            self.close()
        match = HEADING.match(line)
        if match is not None:
            self.close()
            hashes = match.group(1)
            self.found.append(Heading(len(hashes), line[len(hashes) :].strip()))
            return
        self._prose(number, line)

    def _prose(self, number: int, line: str) -> None:
        if line.startswith("- "):
            if self._paragraph:
                self.close()
            self._bullets.append(Bullet(line[2:].strip(), ()))
            return
        if line.startswith("  - "):
            if not self._bullets:
                raise PageRefused(
                    f"line {number}: an indented bullet with no bullet above it to "
                    "sit under."
                )
            parent = self._bullets[-1]
            self._bullets[-1] = Bullet(
                parent.text, (*parent.children, line[4:].strip())
            )
            return
        if line.startswith("  ") and self._bullets:
            self._continue(line.strip())
            return
        if self._bullets:
            raise PageRefused(
                f"line {number}: a paragraph interrupting a bullet list with no blank "
                f"line between them: {line.strip()!r}"
            )
        self._paragraph.append(line.strip())

    def _continue(self, text: str) -> None:
        """An indented line goes on with whichever bullet is currently open."""
        parent = self._bullets[-1]
        if parent.children:
            self._bullets[-1] = Bullet(
                parent.text, (*parent.children[:-1], f"{parent.children[-1]} {text}")
            )
        else:
            self._bullets[-1] = Bullet(f"{parent.text} {text}", ())


def blocks(document: str) -> list[Block]:
    """The document as a list of blocks, or :class:`PageRefused`.

    Deliberately not a general Markdown reader. It understands exactly the four
    constructs `report.render` emits -- a heading, a paragraph, a bullet list with at
    most one level of nesting, and a pipe table -- and refuses everything else, so a
    construct arriving in a future catalog entry stops the build instead of reaching
    a reader as literal punctuation.
    """
    walk = _Walk()
    for number, line in enumerate(document.splitlines(), start=1):
        walk.feed(number, line)
    walk.close()
    if not walk.found:
        raise PageRefused(
            "the document is empty. A page built from nothing is not a page that "
            "passed every check; it is a page with nothing to check."
        )
    return walk.found


# ---------------------------------------------------------------------------
# Inline conversion.
# ---------------------------------------------------------------------------


def inline(text: str) -> str:
    """One run of Markdown inline text as HTML, or :class:`PageRefused`.

    Code spans first, then strong, then backslash escapes, and nothing else. The
    order matters: a ``**`` inside a code span is two asterisks a reader is meant to
    see, and converting it would silently rewrite a published value.
    """
    if _LINK.search(text) or _AUTOLINK.search(text):
        raise PageRefused(
            f"a link reached the converter, which has no rendering for one: {text!r}. "
            "The document has never carried a link; adding one is a decision about "
            "what the page offers, and the link rules in artifacts.py apply to it."
        )
    pieces = text.split("`")
    if len(pieces) % 2 == 0:
        raise PageRefused(f"an unclosed code span: {text!r}")
    out: list[str] = []
    for index, piece in enumerate(pieces):
        if index % 2:
            out.append(f"<code>{html.escape(piece, quote=False)}</code>")
            continue
        out.append(_strong(piece))
    return "".join(out)


def _strong(piece: str) -> str:
    parts = piece.split("**")
    if len(parts) % 2 == 0:
        raise PageRefused(f"an unclosed strong span: {piece!r}")
    return "".join(
        f"<strong>{_escape(part)}</strong>" if index % 2 else _escape(part)
        for index, part in enumerate(parts)
    )


def _escape(part: str) -> str:
    """Escape for HTML, resolving the backslash escapes Markdown carries.

    ``table_cells`` keeps the backslash on an escaped pipe, because its job is to
    split a row rather than to read one. Here the backslash is markup and the pipe is
    the value, so it is the pipe that reaches the reader.
    """
    out: list[str] = []
    escaped = False
    for character in part:
        if escaped:
            out.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        else:
            out.append(character)
    if escaped:
        raise PageRefused(f"a trailing backslash with nothing to escape: {part!r}")
    return html.escape("".join(out), quote=False)


def plain(text: str) -> str:
    """The same run with its markup removed and nothing else changed.

    This is what the caption is composed from and what the round-trip test compares,
    so it goes through the same refusals as :func:`inline` rather than a second,
    more forgiving reader.
    """
    rendered = inline(text)
    return html.unescape(re.sub(r"</?(?:code|strong)>", "", rendered))


# ---------------------------------------------------------------------------
# The page.
# ---------------------------------------------------------------------------


def _slug(text: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "table"
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}-{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def caption_for(section: str, table: Table) -> str:
    """A table's caption: the section it is in, and the column it is keyed by.

    Composed rather than written, so it carries no word this document has not already
    published, and so a section holding three tables gives three different captions
    without anybody maintaining a list. The colon is punctuation; both halves come
    from the catalog, and the repository's own writing rule forbids the dash that
    would otherwise separate them.
    """
    return f"{plain(section)}: {plain(table.header[0])}"


def _table_html(table: Table, caption: str, identifier: str) -> Iterator[str]:
    yield f'<section class="scroll" tabindex="0" aria-labelledby="{identifier}">'
    yield "<table>"
    yield f'<caption id="{identifier}">{html.escape(caption, quote=False)}</caption>'
    yield "<thead>"
    yield "<tr>"
    for cell, alignment in zip(table.header, table.alignments, strict=True):
        css = f' class="{alignment}"' if alignment else ""
        yield f'<th scope="col"{css}>{inline(cell)}</th>'
    yield "</tr>"
    yield "</thead>"
    yield "<tbody>"
    for row in table.rows:
        yield "<tr>"
        for index, (cell, alignment) in enumerate(
            zip(row, table.alignments, strict=True)
        ):
            css = f' class="{alignment}"' if alignment else ""
            if index == 0:
                yield f'<th scope="row"{css}>{inline(cell)}</th>'
            else:
                yield f"<td{css}>{inline(cell)}</td>"
        yield "</tr>"
    yield "</tbody>"
    yield "</table>"
    yield "</section>"


def _body(found: Sequence[Block]) -> Iterator[str]:
    section = ""
    taken: set[str] = set()
    for block in found:
        if isinstance(block, Heading):
            if block.level == 1:
                yield f"<h1>{inline(block.text)}</h1>"
            else:
                section = block.text
                yield f"<h{block.level}>{inline(block.text)}</h{block.level}>"
        elif isinstance(block, Paragraph):
            yield f"<p>{inline(block.text)}</p>"
        elif isinstance(block, Bullets):
            yield "<ul>"
            for item in block.items:
                if item.children:
                    yield f"<li>{inline(item.text)}"
                    yield "<ul>"
                    for child in item.children:
                        yield f"<li>{inline(child)}</li>"
                    yield "</ul>"
                    yield "</li>"
                else:
                    yield f"<li>{inline(item.text)}</li>"
            yield "</ul>"
        else:
            caption = caption_for(section, block)
            yield from _table_html(block, caption, _slug(caption, taken))


def to_html(document: str, *, lang: str) -> str:
    """The whole page, deterministic for a given document and a given language."""
    found = blocks(document)
    first = found[0]
    if not isinstance(first, Heading) or first.level != 1:
        raise PageRefused(
            "the document does not open with a level one heading, so the page has no "
            "title to take and no h1 to give a reader."
        )
    title = plain(first.text)
    lines = [
        "<!doctype html>",
        f'<html lang="{html.escape(lang, quote=True)}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title, quote=False)}</title>",
        "<style>",
        stylesheet().strip(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        *_body(found),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(lines) + "\n"


def render(tree: dict[str, Any], cat: Catalog = ENGLISH) -> str:
    """The page for one artifact and one edition, through the canonical document."""
    return to_html(report.render(tree, cat), lang=cat.lang)


def write_page(page: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8", newline="\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wildfire-service-territory-overlap-page",
        description="Render a measurements artifact as one served HTML page. Reads "
        "the named artifact and nothing else; touches no network.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        required=True,
        help="the measurements.json to render",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="the directory to write index.html into"
    )
    args = parser.parse_args(argv)
    tree = json.loads(args.artifact.read_text(encoding="utf-8"))
    written = write_page(render(tree), args.out / PAGE_NAME)
    print(f"wrote {written}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
