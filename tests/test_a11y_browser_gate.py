"""The browser gate has to be able to fail too, so this runs it against inputs that should.

``tools/a11y_browser`` is the check behind README.md's claim that ``site/index.html`` is
held to WCAG 2.2 SC 1.4.10 Reflow and to the axe rule sets in an engine that does layout.
A check is not adopted here until it has been seen to fail on the input it exists to
catch, and ``tests/test_a11y_gate.py`` is the model: the same evidence, for the jsdom
half.

Three of these cases are things the jsdom gate cannot see at all, which is the argument
for having a second engine:

* a page that scrolls sideways at 320 CSS pixels, because reflow is a property of the
  viewport and jsdom has none;
* a scrollable container nobody can focus, because whether a container scrolls depends
  on layout. That was a real serious-rated defect on the sibling `perimeter` pages until
  a browser run found it, and every wide table on this page sits in such a container;
* text that fails the contrast threshold, which jsdom reports as undecided.

The last of those is why the browser run declares nothing undecidable. In jsdom four
rules land in ``incomplete`` and are declared in ``tools/a11y.mjs`` with a reason. Here
an undecided rule fails, because there is nothing this engine cannot decide.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "a11y_browser"
RUNNER = HARNESS / "node_modules" / ".bin" / "playwright"

CLEAN = 0

# The harness needs node, the packages `make browser-sync` installs, and a browser
# binary. `make verify` runs browser-sync before test for exactly this reason. If the
# toolchain is genuinely absent these tests skip locally and say so, but never on CI,
# where a silently skipped gate test is the same lie the gate itself would be telling.
NODE = shutil.which("node")
BROWSERS = Path.home() / "Library" / "Caches" / "ms-playwright"
LINUX_BROWSERS = Path.home() / ".cache" / "ms-playwright"
HAVE_TOOLCHAIN = (
    NODE is not None
    and RUNNER.is_file()
    and (BROWSERS.is_dir() or LINUX_BROWSERS.is_dir())
)

if not HAVE_TOOLCHAIN and os.environ.get("CI"):  # pragma: no cover - CI-only guard
    raise RuntimeError(
        "node, @playwright/test or the browser binary is missing and CI is set: the "
        "browser WCAG gate's own tests cannot run, and a skipped gate test must not "
        "read as a passing one. Run `make browser-sync` before `make test`."
    )

pytestmark = [
    pytest.mark.skipif(
        not HAVE_TOOLCHAIN,
        reason="node with @playwright/test and a browser is required; run `make browser-sync`",
    ),
    pytest.mark.slow,
]


#: Environment names that tell Playwright it is running inside a GitHub Actions job.
#: Its git-info plugin keys off ``GITHUB_ACTIONS`` -- not ``CI`` -- and, given a
#: ``GITHUB_EVENT_PATH`` naming a pull request, runs
#: ``git fetch origin <base sha> --depth=1`` in whatever work tree the harness's working
#: directory belongs to. That is this repository, and the fetch writes ``.git/shallow``.
#: In the sibling ``perimeter`` that made a tag-reading test refuse and failed
#: ``make verify`` on branches that changed nothing related. ``playwright.config.ts``
#: turns the capture off at the source; these are removed as well so the harness behaves
#: the same way here as it does on a laptop, and so a future config edit cannot quietly
#: re-enable a git write from inside a test run.
_CI_NAMES_PLAYWRIGHT_READS = (
    "GITHUB_ACTIONS",
    "GITHUB_EVENT_PATH",
    "GITLAB_CI",
    "JENKINS_URL",
)


def harness_env(site_dir: Path, *, floors: bool = False) -> dict[str, str]:
    """The environment the harness runs in: this build's pages, and no CI identity.

    ``floors`` holds the fixture to the two specs that describe the served page -- at
    least one table region scrolls at 320 pixels, and no number in a table is split
    across lines. Off by default, because a fixture built to break one rule has no
    tables and would fail those for a reason unrelated to the rule it breaks.
    """
    env = {k: v for k, v in os.environ.items() if k not in _CI_NAMES_PLAYWRIGHT_READS}
    env.pop("WILDFIRE_SHIPPED_FLOORS", None)
    env["WILDFIRE_SITE_DIR"] = str(site_dir)
    env["CI"] = ""
    if floors:
        env["WILDFIRE_SHIPPED_FLOORS"] = "1"
    return env


def run(
    spec: str, site_dir: Path, *, floors: bool = False, grep: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one spec file against one directory of pages."""
    # Fixed argv, absolute runner, no shell. The only interpolated value is the test's
    # own tmp_path, passed through the environment rather than the command line, and
    # a literal grep pattern chosen by the test itself.
    argv = [str(RUNNER), "test", spec]
    if grep is not None:
        argv += ["--grep", grep]
    return subprocess.run(  # noqa: S603
        argv,
        capture_output=True,
        text=True,
        check=False,
        cwd=HARNESS,
        env=harness_env(site_dir, floors=floors),
    )


def page(body: str, *, style: str = "") -> str:
    """A minimal conformant page, with the body under test dropped into its main."""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Browser gate test page</title>"
        f"<style>body{{margin:0;background:#fff;color:#111}}{style}</style></head><body>"
        "<nav aria-label='test'><a href='#content'>Skip to content</a></nav>"
        f"<main id='content'><h1>Browser gate test page</h1>{body}</main>"
        "<footer><p>Test material generated by tests/test_a11y_browser_gate.py.</p>"
        "</footer></body></html>"
    )


def site(tmp_path: Path, body: str, *, style: str = "") -> Path:
    out = tmp_path / "pages"
    out.mkdir()
    (out / "under-test.html").write_text(page(body, style=style), encoding="utf-8")
    return out


CLEAN_BODY = "<p>Ordinary prose that wraps inside any viewport.</p>"


# --- the gate passes what it should ---------------------------------------------------


@pytest.mark.parametrize("spec", ["reflow.spec.ts", "axe.spec.ts"])
def test_a_conformant_page_passes_both_specs(spec: str, tmp_path: Path) -> None:
    """The positive control. Without it a gate that fails everything looks like a gate."""
    result = run(spec, site(tmp_path, CLEAN_BODY))
    assert result.returncode == CLEAN, result.stdout + result.stderr


# --- reflow: SC 1.4.10, which no DOM-only engine can decide ---------------------------


def test_a_page_that_scrolls_sideways_at_320px_fails(tmp_path: Path) -> None:
    body = "<div class='wide'>A block wider than any narrow viewport.</div>"
    result = run(
        "reflow.spec.ts",
        site(tmp_path, body, style=".wide{width:900px;background:#eee}"),
    )
    assert result.returncode != CLEAN
    assert "SC 1.4.10" in result.stdout


def test_text_that_spills_out_of_a_correctly_sized_block_fails(tmp_path: Path) -> None:
    """The sneaky half: the box fits, the content does not, and nothing looks wrong."""
    body = "<p class='long'>https://example.invalid/" + "a" * 300 + "</p>"
    result = run(
        "reflow.spec.ts",
        site(tmp_path, body, style=".long{overflow-x:visible;word-break:normal}"),
    )
    assert result.returncode != CLEAN
    assert "SC 1.4.10" in result.stdout


# --- axe in an engine that does layout ------------------------------------------------


def test_a_scrollable_region_nobody_can_focus_fails(tmp_path: Path) -> None:
    """The defect this harness found on the sibling `perimeter` pages, kept here too.

    On this repository's page it is also the control that showed axe needed a
    320-pixel run: removing `tabindex` from every region stayed green at 1280.

    A container with overflow-x: auto scrolls for a pointer and not for a keyboard. It
    is invisible to jsdom, which computes no layout and so never knows the container
    scrolls at all.
    """
    body = (
        "<div class='box'><table><caption>Wide</caption><tbody><tr>"
        + "".join(f"<td>cell {n}</td>" for n in range(40))
        + "</tr></tbody></table></div>"
    )
    result = run(
        "axe.spec.ts",
        site(
            tmp_path,
            body,
            style=".box{overflow-x:auto;width:200px}.box td{white-space:nowrap}",
        ),
    )
    assert result.returncode != CLEAN
    assert "scrollable-region-focusable" in result.stdout


def test_text_below_the_contrast_threshold_fails(tmp_path: Path) -> None:
    """jsdom paints nothing and files this as undecided; a browser decides it."""
    body = "<p class='faint'>Grey on white, below 4.5:1.</p>"
    result = run(
        "axe.spec.ts",
        site(tmp_path, body, style=".faint{color:#aaa;background:#fff}"),
    )
    assert result.returncode != CLEAN
    assert "color-contrast" in result.stdout


def test_a_pointer_target_under_24px_fails(tmp_path: Path) -> None:
    """SC 2.5.8. Needs box geometry, which is the whole reason it was unchecked."""
    body = "<p><a class='tiny' href='#content'>a</a> <a class='tiny' href='#content'>b</a></p>"
    result = run(
        "axe.spec.ts",
        site(
            tmp_path,
            body,
            style=".tiny{display:inline-block;width:8px;height:8px;overflow:hidden;font-size:6px}",
        ),
    )
    assert result.returncode != CLEAN
    assert "target-size" in result.stdout


# --- a gate that can find nothing to examine fails ------------------------------------


@pytest.mark.parametrize("spec", ["reflow.spec.ts", "axe.spec.ts"])
def test_a_directory_with_no_pages_fails_rather_than_passing(
    spec: str, tmp_path: Path
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = run(spec, empty)
    assert result.returncode != CLEAN
    assert "no .html files" in result.stdout + result.stderr


@pytest.mark.parametrize("spec", ["reflow.spec.ts", "axe.spec.ts"])
def test_a_missing_directory_fails_rather_than_passing(
    spec: str, tmp_path: Path
) -> None:
    result = run(spec, tmp_path / "was-never-built")
    assert result.returncode != CLEAN
    assert "cannot read" in result.stdout + result.stderr


# --- the two floors that describe the served page -------------------------------------
#
# Both specs are scoped to the shipped page, so the only way to watch them fail is to
# hold a fixture to them on purpose. Each fixture carries enough numbers and enough
# table to satisfy every refusal but the one under test: a split-number page with
# three numbers would fail on the examined-count floor first and prove nothing about
# split numbers, which is the shape of a control that passes for the wrong reason.


def wide_table(*, rows: int = 12, columns: int = 12) -> str:
    """A labelled, focusable scroll region holding a numeric table too wide for 320px."""
    head = "".join(f"<th scope='col' class='num'>Col {c}</th>" for c in range(columns))
    body = "".join(
        f"<tr><th scope='row'>Row {r}</th>"
        + "".join(f"<td class='num'>{r * 1000 + c:,}</td>" for c in range(columns - 1))
        + "</tr>"
        for r in range(1, rows + 1)
    )
    return (
        "<section class='scroll' tabindex='0' aria-labelledby='wide'>"
        "<table><caption id='wide'>Wide numeric table</caption>"
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>"
    )


# The served page declares a background on each scroll region and on its header row,
# and this fixture has to as well. Measured: without them, axe at 320 pixels filed
# `color-contrast` as undecided for the caption and for every header cell sitting
# outside the viewport, and the positive control failed for a reason that has nothing
# to do with either floor.
WIDE_STYLE = (
    ".scroll{overflow-x:auto;background:#fff}thead th{background:#fff}"
    ".num{white-space:nowrap}th,td{padding:4px 12px}"
)


def test_a_wide_numeric_table_passes_both_floors(tmp_path: Path) -> None:
    """The positive control, and it runs axe at 320px over a real scroll region."""
    pages = site(tmp_path, wide_table(), style=WIDE_STYLE)
    numbers = run("numbers.spec.ts", pages, floors=True)
    assert numbers.returncode == CLEAN, numbers.stdout + numbers.stderr
    assert "0 of " in numbers.stdout
    axe = run("axe.spec.ts", pages, floors=True)
    assert axe.returncode == CLEAN, axe.stdout + axe.stderr
    assert "1 of 1 scroll regions overflow at 320px" in axe.stdout


def test_a_number_split_across_two_lines_fails(tmp_path: Path) -> None:
    """The defect the first version of the served page shipped, and no engine saw."""
    narrow = (
        "<table class='fixed'><caption>Narrow</caption><tbody><tr>"
        "<th scope='row'>Total</th><td>123,456,789,012</td></tr></tbody></table>"
    )
    style = (
        WIDE_STYLE
        + ".fixed{table-layout:fixed;width:120px}.fixed td{overflow-wrap:anywhere}"
    )
    result = run(
        "numbers.spec.ts",
        site(tmp_path, wide_table() + narrow, style=style),
        floors=True,
    )
    assert result.returncode != CLEAN
    assert "numbers split across two lines" in result.stdout
    assert "123,456,789,012" in result.stdout


def test_a_page_whose_regions_never_scroll_fails_the_floor(tmp_path: Path) -> None:
    """If nothing scrolls, `scrollable-region-focusable` examined nothing.

    Only the floor runs, by name, so axe cannot be what fails; and the assertion is on
    the floor's own sentence, so "no tests found" cannot be what passes.
    """
    fits = (
        "<section class='scroll' tabindex='0' aria-labelledby='small'>"
        "<table><caption id='small'>Small</caption><tbody>"
        "<tr><th scope='row'>A</th><td>1</td></tr></tbody></table></section>"
    )
    result = run(
        "axe.spec.ts",
        site(tmp_path, fits, style=".scroll{overflow-x:auto}"),
        floors=True,
        grep="really scrolls",
    )
    assert result.returncode != CLEAN
    assert "0 of 1 scroll regions overflow at 320px" in result.stdout
    assert "had nothing to decide" in result.stdout
