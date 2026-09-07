"""Build the measurements from files already on disk. No network, ever.

``--fixture`` marks the output as built from the committed sample files rather than from
the real retrievals, so a fixture build can never be mistaken for the published one.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from wildfire_service_territory_overlap import artifacts, measure, report, sensitivity
from wildfire_service_territory_overlap.geometry import load_counties, load_territories
from wildfire_service_territory_overlap.placement import (
    classify,
    classify_county_agreement,
    measure_boundary_distances,
    measure_contested_group_distances,
    read_records,
)
from wildfire_service_territory_overlap.sources import (
    DINS,
    ELSE_IOU_POU,
    ELSE_OTHER,
    RETRIEVED,
)

ARTIFACT_NAME = "measurements.json"
REPORT_NAME = "REPORT.md"

# The name in pyproject.toml, which hatchling copies into the installed distribution
# metadata. There is no second copy of the version anywhere: the flag below reads it
# back from that metadata, so a hardcoded string cannot drift from the packaging.
DISTRIBUTION = "wildfire-service-territory-overlap"


class PrintVersion(argparse.Action):
    """Resolve the version when the flag is used, not while the parser is built.

    ``version=f"%(prog)s {metadata.version(...)}"`` is the obvious form and it is a
    trap: the lookup runs on every invocation, including every build that never asks.
    On a checkout with no installed distribution metadata it raises before ``--dins``
    is even parsed, so the whole command dies in order to offer one flag.

    A version that cannot be read is not guessed. It is reported as not measured, which
    is the shape this project gives every other question it cannot answer.
    """

    def __init__(self, option_strings: Sequence[str], dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        try:
            version = metadata.version(DISTRIBUTION)
        except metadata.PackageNotFoundError:
            print(
                f"{DISTRIBUTION}: version not measured. Nothing installed under "
                f"{DISTRIBUTION} carries the distribution metadata to read it from. "
                "Install the project, with `uv sync --locked`, and ask again.",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
        print(f"{DISTRIBUTION} {version}")
        raise SystemExit(0)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build(
    *,
    dins_path: Path,
    iou_pou_path: Path,
    other_path: Path,
    counties_path: Path,
    out_dir: Path,
    is_fixture: bool,
    inclusion_rules: Sequence[sensitivity.SuppliedRule] = (),
) -> tuple[Path, Path]:
    """Measure, check, and write both artifacts. Nothing is written if a check fails."""
    collections = {
        ELSE_IOU_POU.key: _read_json(iou_pou_path),
        ELSE_OTHER.key: _read_json(other_path),
    }
    # Before the layers are projected and before a single record is placed. A rule
    # naming a type this retrieval does not carry, or an outline it does not carry,
    # would otherwise run to completion and publish a variant measuring less than the
    # reviewer asked for, and the build would exit zero.
    sensitivity.check_rules_against_retrieval(inclusion_rules, collections)
    territories, unusable = load_territories(collections)
    counties = load_counties(_read_json(counties_path))
    records, excluded = read_records(_read_json(dins_path))
    placement = classify(records, territories, excluded)
    measure_boundary_distances(placement, territories)
    measure_contested_group_distances(placement, territories)
    agreement = classify_county_agreement(records, counties)

    tree: dict[str, Any] = {
        "is_fixture": is_fixture,
        "provenance": {
            "dins_retrieved": DINS.retrieved,
            "dins_landing_page": DINS.landing_page,
            "territories_retrieved": RETRIEVED,
            "territories_item_modified": ELSE_IOU_POU.item_modified,
            "territories_landing_page": ELSE_IOU_POU.landing_page,
            "affiliation": (
                "Unofficial. Not affiliated with, endorsed by, or approved by CAL FIRE, "
                "the California Energy Commission, or any electric utility."
            ),
        },
        "placement_coverage": measure.placement_coverage(placement),
        "representativeness": measure.representativeness(placement),
        "representativeness_by_category": measure.representativeness_by_category(
            placement
        ),
        "coordinate_county_agreement": measure.coordinate_county_agreement(
            agreement, len(records)
        ),
        "attributability_by_fire": measure.attributability_by_fire(placement),
        "territories": measure.territory_rows(placement, territories),
        "contested_groups": measure.contested_groups(placement),
        "geometry_ledger": measure.geometry_ledger(placement, territories, unusable),
        "sensitivity": {
            "type_inclusion": sensitivity.type_inclusion(
                collections, records, excluded, inclusion_rules
            ),
            "repair_strategy": sensitivity.repair_comparison(
                collections, records, territories
            ),
            "untouched_outlines": sensitivity.untouched_outlines(
                placement, records, territories
            ),
        },
        "excluded_types": measure.excluded_type_note(),
    }

    # The aggregate ceiling is the largest number of things any one collection here
    # reports on: one row per published outline, or one row per county named in the
    # record set. A list longer than that is a record listing under another name.
    ceiling = max(len(territories) + len(unusable), len(placement.counties), 32)
    artifact_path = artifacts.write_json(
        tree, out_dir / ARTIFACT_NAME, max_rows=ceiling
    )
    # The document goes through a gate of its own. Both artifacts are checked before
    # either is read by anybody: a rate reaching the reader without its denominator and
    # a table reaching the reader with its cells shifted one column left are the same
    # kind of failure, and neither is caught by looking at the output afterwards.
    report_path = artifacts.write_report(report.render(tree), out_dir / REPORT_NAME)
    return artifact_path, report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wildfire-service-territory-overlap",
        description="Measure how much of the DINS record set a published electric "
        "service territory boundary can account for. Reads local files only.",
    )
    parser.add_argument(
        "--version",
        action=PrintVersion,
        help="print the installed version and exit",
    )
    parser.add_argument("--dins", type=Path, required=True)
    parser.add_argument("--iou-pou", type=Path, required=True)
    parser.add_argument("--other", type=Path, required=True)
    parser.add_argument("--counties", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="the inputs are the committed samples, not the real retrievals",
    )
    parser.add_argument(
        "--inclusion-rule",
        type=Path,
        action="append",
        default=None,
        metavar="FILE",
        dest="inclusion_rule",
        help="a reviewer-supplied inclusion rule file, published as one more "
        "sensitivity row beside the built ones; repeatable",
    )
    args = parser.parse_args(argv)
    # Every supplied file is read and checked for shape before anything is measured, so
    # a typo in the fourth file does not surface after three placements have run.
    try:
        rules = sensitivity.read_rule_files(args.inclusion_rule or [])
    except sensitivity.InclusionRuleRefused as refusal:
        print(f"inclusion rule refused. {refusal}", file=sys.stderr)
        return 2
    try:
        artifact, document = build(
            dins_path=args.dins,
            iou_pou_path=args.iou_pou,
            other_path=args.other,
            counties_path=args.counties,
            out_dir=args.out,
            is_fixture=args.fixture,
            inclusion_rules=rules,
        )
    except sensitivity.InclusionRuleRefused as refusal:
        print(f"inclusion rule refused. {refusal}", file=sys.stderr)
        return 2
    for rule in rules:
        print(f"read inclusion rule {rule.file_name} as {rule.variant!r}")
    print(f"wrote {artifact}")
    print(f"wrote {document}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
