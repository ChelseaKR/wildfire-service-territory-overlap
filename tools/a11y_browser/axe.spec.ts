import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { SITE_DIR, pagesUnderTest, urlFor } from "./pages";

/**
 * The same axe rule sets `tools/a11y.mjs` runs in jsdom, run in a real engine, at two
 * viewports.
 *
 * jsdom does no layout and paints no pixels, so four rules land in `incomplete` there
 * and are declared in that file with a reason and with where each is covered instead.
 * A browser computes geometry and colour, so it decides all four, and this run has no
 * declared-undecidable list at all: an undecided rule fails here, full stop.
 *
 * **Why two viewports.** `scrollable-region-focusable` can only fire on a region that
 * actually scrolls, and whether a region scrolls depends on the viewport. Every wide
 * table on the served page sits in a `.scroll` container carrying `tabindex="0"`, and
 * at the project's default 1280-pixel viewport none of them overflows, so the rule had
 * no input: deleting `tabindex` from all fourteen regions left this spec green. At
 * 320 by 256, the SC 1.4.10 reference viewport, the wide tables do scroll inside their
 * containers, so that is where the rule can decide something. The floor below makes
 * "it can" a checked statement rather than a hope.
 */

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"];

async function audit(page: Page, name: string, where: string): Promise<void> {
  await page.goto(urlFor(name));
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();

  const violations = results.violations.map(
    (v) => `[${v.impact}] ${v.id}: ${v.help}\n    ${v.nodes.map((n) => n.target.join(" ")).join("\n    ")}`,
  );
  expect(violations, `${name} at ${where}: accessibility violations`).toEqual([]);

  // An undecided rule is not a passing rule. There is nothing this engine cannot
  // decide, so anything landing here is a finding rather than a known gap.
  const undecided = results.incomplete.map(
    (v) => `${v.id}: ${v.help}\n    ${v.nodes.map((n) => n.target.join(" ")).join("\n    ")}`,
  );
  expect(
    undecided,
    `${name} at ${where}: axe ran these rules in a real browser and still could not ` +
      "decide them. That is not a pass.",
  ).toEqual([]);
}

test(`the build in ${SITE_DIR} holds pages to check`, () => {
  expect(pagesUnderTest().length).toBeGreaterThan(0);
});

test.describe("at the default viewport", () => {
  for (const name of pagesUnderTest()) {
    test(`axe in a browser: ${name}`, async ({ page }) => {
      await audit(page, name, "the default viewport");
    });
  }
});

test.describe("at 320 by 256", () => {
  test.use({ viewport: { width: 320, height: 256 } });

  for (const name of pagesUnderTest()) {
    test(`axe in a browser at 320px: ${name}`, async ({ page }) => {
      await audit(page, name, "320 by 256");
    });
  }

  // The floor, scoped to the shipped page. A gate-test fixture pointed here through
  // WILDFIRE_SITE_DIR is a page built to fail one rule and has no tables to scroll,
  // so a floor describing the served page would fail those tests for a reason
  // unrelated to what each one tests. On the served page it must hold: if no region
  // scrolls at 320 pixels, `scrollable-region-focusable` examined nothing, and the
  // green run above says nothing about whether a keyboard can reach a wide table.
  // tests/test_a11y_browser_gate.py sets WILDFIRE_SHIPPED_FLOORS=1 to hold a fixture
  // to it on purpose, which is how the floor is shown to fail.
  if (!process.env.WILDFIRE_SITE_DIR || process.env.WILDFIRE_SHIPPED_FLOORS === "1") {
    for (const name of pagesUnderTest()) {
      test(`at least one table region really scrolls at 320px: ${name}`, async ({ page }) => {
        await page.goto(urlFor(name));
        const counts = await page.evaluate(() => {
          const regions = Array.from(document.querySelectorAll(".scroll"));
          const scrolling = regions.filter((el) => el.scrollWidth > el.clientWidth + 1);
          return { regions: regions.length, scrolling: scrolling.length };
        });
        console.log(
          `${name}: ${counts.scrolling} of ${counts.regions} scroll regions overflow at 320px`,
        );
        expect(
          counts.scrolling,
          `${name}: ${counts.scrolling} of ${counts.regions} scroll regions overflow at ` +
            "320px, so scrollable-region-focusable had nothing to decide",
        ).toBeGreaterThan(0);
      });
    }
  }
});
