# 4. No damage rate is published for a territory

Date: 2026-08-17

## Status

Accepted.

## Context

The arithmetic is trivial and the data supports it: destroyed records over placed records,
within one territory, is a proportion with a real denominator and a valid interval. It
would be the most-read number in the project.

It would also be a number about a utility, and it is not one. It is a number about which
fires happened to burn inside a boundary. The measurement that shows this is published:
the share of each territory's placed records contributed by its single largest incident
runs to 100% for one territory, 99.7% for another, 82.9% for a third. A territory whose
records are one fire has a "damage rate" that is that fire's damage rate.

Printed as a table, ordered or not, a set of per-utility destroyed shares is read as a
comparison. Readers rank tables. The ranking would track fire history and inspection
coverage, and it would be labeled with company names.

## Decision

No damage rate is published for any territory. Territory rows carry counts, the incident
concentration share, and the boundary proximity bands, all of them within-territory. The
statewide destroyed share is published for the placed and contested populations, because
that comparison is between two subsets of the data and not between two companies.

`tests/test_measure_and_report.py` asserts that no territory row carries a key naming
damage, destruction or loss, so the decision is enforced rather than remembered.

## Consequences

The project declines to publish its most quotable figure and says why in the place the
figure would have been. The concentration column is the argument, sitting in the table
where a reader would look for the rate.
