// HTML conformance and markup-level accessibility rules for the served page.
//
// Where a rule is tightened or waived, the reason is here rather than in a commit
// message: a waived rule with no reason beside it is indistinguishable from an
// oversight, which is the shape this repository spends most of its gates refusing.
export default {
  extends: [
    "html-validate:recommended",
    "html-validate:document",
    "html-validate:a11y",
  ],
  rules: {
    // The WHATWG spec writes the doctype lowercase and HTML5 is case-insensitive
    // here. Pinned so the generator and the checker cannot drift on a detail neither
    // of them would otherwise mention.
    "doctype-style": ["error", { style: "lowercase" }],
    // Strict: every <th> carries a scope, not only those in a table that mixes row
    // and column headers. Every table on this page is a data table whose first cell
    // names what the row is about, and a cell read out without its row header is the
    // failure this catches. src/wildfire_service_territory_overlap/page.py emits
    // scope on every th, so strict costs nothing and pins that it keeps doing so.
    "wcag/h63": ["error", { strict: true }],
    // No inline style attribute is emitted, and none should start being. The page
    // has one stylesheet, generated from the palette, and a colour that reached the
    // markup directly would be a colour the contrast test cannot see.
    "no-inline-style": "error",
  },
};
