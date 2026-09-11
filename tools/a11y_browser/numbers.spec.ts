import { expect, test } from "@playwright/test";

import { pagesUnderTest, urlFor } from "./pages";

/**
 * No number in a table on the served page is broken across two lines, at either
 * viewport.
 *
 * This is a statement about content, and no accessibility engine makes it: a number
 * split over two lines is still text, still has contrast, and still sits inside a
 * labelled region. Measured on the first version of the page, which let every cell
 * break anywhere so that wide tables shrank instead of scrolling: at 320 by 256,
 * 396 of 711 numeric cells printed a figure split across lines (`82,3` over `53`),
 * and html-validate, axe in jsdom, axe in Chromium and the reflow check were all
 * green. This spec is what would have gone red.
 *
 * Every number in every table cell is examined, not only the right-aligned columns:
 * a share or an interval in a left-aligned column is a number too. Each one is held
 * as its own DOM range and has to occupy exactly one line box. The count examined is
 * printed and floored, so a pattern that stopped matching cannot report a clean page.
 *
 * Scoped to the shipped page. A gate-test fixture pointed here through
 * WILDFIRE_SITE_DIR has no tables, and a floor describing the served page would fail
 * it for a reason unrelated to the rule that fixture exists to break. Setting
 * WILDFIRE_SHIPPED_FLOORS=1 holds a fixture to it anyway, which is how
 * tests/test_a11y_browser_gate.py shows this spec failing on a split number.
 */

const VIEWPORTS = [
  { width: 1280, height: 720 },
  { width: 320, height: 256 },
];

if (!process.env.WILDFIRE_SITE_DIR || process.env.WILDFIRE_SHIPPED_FLOORS === "1") {
  for (const viewport of VIEWPORTS) {
    test.describe(`at ${viewport.width} by ${viewport.height}`, () => {
      test.use({ viewport });

      for (const name of pagesUnderTest()) {
        test(`every number in every table sits on one line: ${name}`, async ({ page }) => {
          await page.goto(urlFor(name));
          const result = await page.evaluate(() => {
            const pattern = /\d[\d,.]*%?/g;
            let examined = 0;
            const broken: string[] = [];
            for (const cell of Array.from(document.querySelectorAll("td, th"))) {
              const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
              for (let node = walker.nextNode(); node; node = walker.nextNode()) {
                const text = node.textContent ?? "";
                for (const match of text.matchAll(pattern)) {
                  const start = match.index ?? 0;
                  examined += 1;
                  const range = document.createRange();
                  range.setStart(node, start);
                  range.setEnd(node, start + match[0].length);
                  if (range.getClientRects().length > 1) {
                    broken.push(match[0]);
                  }
                }
              }
            }
            return { examined, broken };
          });
          console.log(
            `${name} at ${viewport.width}px: ${result.broken.length} of ` +
              `${result.examined} numbers in table cells broken across lines`,
          );
          expect(
            result.examined,
            "no number was found in any table cell, so this examined nothing",
          ).toBeGreaterThan(100);
          expect(
            result.broken,
            `${name} at ${viewport.width}px: numbers split across two lines`,
          ).toEqual([]);
        });
      }
    });
  }
}
