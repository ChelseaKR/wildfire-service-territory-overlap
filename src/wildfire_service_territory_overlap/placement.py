"""Deciding, for each inspected structure, which published territory it sits in.

There are four answers, and the point of this module is that they stay four answers.

``placed``
    The coordinate falls inside exactly one published territory outline.
``contested``
    It falls inside more than one. The published boundaries overlap, so public data does
    not say which entity the record belongs to. It is not awarded to the larger polygon,
    the smaller polygon, the investor-owned one, or the one listed first.
``uncovered``
    It falls inside none of them. The publisher states that not all entities are
    represented, so this is a fact about the boundary layer, not a fact about the record.
``not measured``
    The published coordinate is missing or outside California. Never a zero for anyone.

A point lying exactly on a shared edge is counted as being in both polygons and is
therefore contested. That is the conservative direction: the alternative is a rule that
silently awards edge cases to whichever polygon a floating-point comparison happens to
favor, which is the kind of tie-break that is invisible in the output.

Nothing in this module divides anything. It counts, and :mod:`wildfire_service_territory_overlap.measure` forms
the rates, so that every proportion in the published output goes through one place.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

import numpy as np
import shapely

from wildfire_service_territory_overlap.geometry import (
    Territory,
    distances_to_boundary,
    project_lonlat,
)
from wildfire_service_territory_overlap.geometry import territory_index as build_index
from wildfire_service_territory_overlap.sources import CALIFORNIA_BBOX

FIRE: Final[str] = "Fire"
DESTROYED: Final[str] = "Destroyed (>50%)"

BOUNDARY_BANDS_M: Final[tuple[int, ...]] = (100, 250, 500, 1000)
"""Distances from a published edge at which a placement is reported as close to it."""


@dataclass(frozen=True)
class Record:
    """One damage-inspection record, reduced to the fields this project reads."""

    object_id: int
    damage: str | None
    incident: str | None
    county: str | None
    year: int | None
    lon: float | None
    lat: float | None
    category: str | None = None

    @property
    def destroyed(self) -> bool:
        return self.damage == DESTROYED

    @property
    def has_usable_coordinate(self) -> bool:
        if self.lon is None or self.lat is None:
            return False
        west, south, east, north = CALIFORNIA_BBOX
        return west <= self.lon <= east and south <= self.lat <= north


def _year_of(value: Any) -> int | None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    return datetime.fromtimestamp(float(value) / 1000.0, tz=UTC).year


def _coordinate(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _name(value: Any) -> str | None:
    """A published name, or None when the publisher left the cell empty.

    An empty county cell is an absent value, not a county called "". Records carrying
    one stay in every other denominator here and are counted separately in the county
    cut, because a record whose county nobody recorded is not evidence about a county.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "COUNTY",
    "DAMAGE",
    "HAZARDTYPE",
    "INCIDENTNAME",
    "INCIDENTSTARTDATE",
    "LATITUDE",
    "LONGITUDE",
    "OBJECTID",
    "STRUCTURECATEGORY",
)


class SchemaError(ValueError):
    """The retrieval does not carry the columns every measurement here reads."""


def assert_columns(rows: list[dict[str, Any]]) -> None:
    """Refuse a file missing a column, rather than reading the absence as a value.

    A file fetched without ``HAZARDTYPE`` filters to zero fire records and produces a
    report in which every rate is honestly marked not measured. That output is correct
    and useless, and it looks like a finding. A missing column is an acquisition fault,
    so it is raised as one here instead of traveling downstream as data.
    """
    if not rows:
        raise SchemaError("the retrieval holds no rows")
    missing = sorted(set(REQUIRED_COLUMNS) - set(rows[0]))
    if missing:
        raise SchemaError(
            f"the retrieval is missing {', '.join(missing)}. Re-acquire the layer; do "
            "not measure what is left."
        )


def read_records(rows: list[dict[str, Any]]) -> tuple[tuple[Record, ...], int]:
    """Reduce the raw DINS rows to fire records, and count what the filter removed.

    The published HAZARDTYPE domain carries five hazards. This project measures wildfire
    and says how many records that left behind, rather than describing the file as
    wholly a wildfire file.
    """
    assert_columns(rows)
    kept: list[Record] = []
    excluded = 0
    for row in rows:
        if row.get("HAZARDTYPE") != FIRE:
            excluded += 1
            continue
        kept.append(
            Record(
                object_id=int(row["OBJECTID"]),
                damage=row.get("DAMAGE"),
                incident=row.get("INCIDENTNAME"),
                county=_name(row.get("COUNTY")),
                category=_name(row.get("STRUCTURECATEGORY")),
                year=_year_of(row.get("INCIDENTSTARTDATE")),
                lon=_coordinate(row.get("LONGITUDE")),
                lat=_coordinate(row.get("LATITUDE")),
            )
        )
    return tuple(kept), excluded


@dataclass
class TerritoryTally:
    """Everything counted for one territory. Counts only; no rate is formed here."""

    name: str
    kind: str
    geometry_state: str
    placed: int = 0
    contested: int = 0
    contested_with: Counter[str] = field(default_factory=Counter)
    incidents: Counter[str] = field(default_factory=Counter)
    destroyed: int = 0
    placed_x: list[float] = field(default_factory=list)
    placed_y: list[float] = field(default_factory=list)
    within_band: dict[int, int] = field(default_factory=dict)
    distance_state: str = "not_measured"

    @property
    def largest_incident(self) -> tuple[str, int] | None:
        if not self.incidents:
            return None
        # Ties break on the incident name, so the choice never depends on dict order.
        return max(self.incidents.items(), key=lambda kv: (kv[1], kv[0]))


@dataclass
class Placement:
    """The classification of every fire record, and the per-territory tallies."""

    fire_records: int
    excluded_by_hazard: int
    placed: int = 0
    contested: int = 0
    uncovered: int = 0
    not_measured: int = 0
    destroyed_placed: int = 0
    destroyed_contested: int = 0
    destroyed_uncovered: int = 0
    tallies: dict[str, TerritoryTally] = field(default_factory=dict)
    contested_groups: Counter[tuple[str, ...]] = field(default_factory=Counter)
    # Per combination, the projected coordinates of its contested records, kept so the
    # distance to the nearest edge among the group's outlines can be measured after
    # classification rather than during it.
    contested_xy: dict[tuple[str, ...], tuple[list[float], list[float]]] = field(
        default_factory=dict
    )
    contested_bands: dict[tuple[str, ...], dict[int, int]] = field(default_factory=dict)
    contested_distance_state: dict[tuple[str, ...], str] = field(default_factory=dict)
    years: Counter[int] = field(default_factory=Counter)
    year_classified: Counter[int] = field(default_factory=Counter)
    year_contested: Counter[int] = field(default_factory=Counter)
    incident_classified: Counter[str] = field(default_factory=Counter)
    incident_contested: Counter[str] = field(default_factory=Counter)
    counties: Counter[str] = field(default_factory=Counter)
    county_classified: Counter[str] = field(default_factory=Counter)
    county_contested: Counter[str] = field(default_factory=Counter)
    records_with_no_county: int = 0
    category_placed: Counter[str] = field(default_factory=Counter)
    category_contested: Counter[str] = field(default_factory=Counter)
    category_destroyed_placed: Counter[str] = field(default_factory=Counter)
    category_destroyed_contested: Counter[str] = field(default_factory=Counter)

    @property
    def classified(self) -> int:
        return self.placed + self.contested + self.uncovered + self.not_measured


def _empty_tallies(territories: tuple[Territory, ...]) -> dict[str, TerritoryTally]:
    return {
        t.name: TerritoryTally(
            name=t.name, kind=t.kind, geometry_state=t.geometry_state
        )
        for t in territories
    }


def _hits_by_record(
    territories: tuple[Territory, ...], xs: np.ndarray, ys: np.ndarray
) -> list[list[int]]:
    """For each point, the indices of every territory whose outline it meets.

    Two steps rather than ``STRtree.query(..., predicate="intersects")``, which does not
    use a prepared geometry and re-walks the full ring on every test. The largest
    territory here carries over a hundred thousand vertices, so that form spends about
    forty seconds on this record set where the two-step form spends a tenth of a second.
    The tree narrows by bounding box, then a prepared containment test decides. The pairs
    are identical, including their order; a test asserts that against the predicate form
    rather than taking it on trust.
    """
    tree = build_index(territories)
    geometries = np.asarray([t.geometry for t in territories], dtype=object)
    shapely.prepare(geometries)
    points = shapely.points(xs, ys)
    candidates = tree.query(points)
    inside = shapely.intersects(geometries[candidates[1]], points[candidates[0]])
    hits: list[list[int]] = [[] for _ in range(len(xs))]
    for point_index, hit_index in zip(
        candidates[0][inside], candidates[1][inside], strict=True
    ):
        hits[int(point_index)].append(int(hit_index))
    return hits


def containment_signatures(
    records: tuple[Record, ...], territories: tuple[Territory, ...]
) -> tuple[tuple[str, ...] | None, ...]:
    """Per record, the names of every outline it falls inside, or None for no coordinate.

    An empty tuple means the record is inside no published outline. This is the form two
    runs are compared in: the same records under two different repairs, or under two
    different inclusion rules, so that a change can be counted per record rather than
    inferred from two totals that happen to differ.
    """
    signatures: list[tuple[str, ...] | None] = [None] * len(records)
    usable, lons, lats = _usable_positions(records)
    if not usable:
        return tuple(signatures)
    xs, ys = project_lonlat(lons, lats)
    hits = _hits_by_record(territories, xs, ys)
    for position, record_index in enumerate(usable):
        signatures[record_index] = tuple(
            sorted(territories[i].name for i in hits[position])
        )
    return tuple(signatures)


def _usable_positions(
    records: tuple[Record, ...],
) -> tuple[list[int], np.ndarray, np.ndarray]:
    usable = [i for i, r in enumerate(records) if r.has_usable_coordinate]
    lons = np.array([records[i].lon for i in usable], dtype="float64")
    lats = np.array([records[i].lat for i in usable], dtype="float64")
    return usable, lons, lats


def _tally_placed(
    result: Placement, territory: Territory, record: Record, x: float, y: float
) -> None:
    result.placed += 1
    result.destroyed_placed += int(record.destroyed)
    tally = result.tallies[territory.name]
    tally.placed += 1
    tally.destroyed += int(record.destroyed)
    if record.incident:
        tally.incidents[record.incident] += 1
    tally.placed_x.append(x)
    tally.placed_y.append(y)
    if record.category:
        result.category_placed[record.category] += 1
        result.category_destroyed_placed[record.category] += int(record.destroyed)


def _tally_contested(
    result: Placement,
    territories: tuple[Territory, ...],
    found: list[int],
    record: Record,
    x: float,
    y: float,
) -> None:
    result.contested += 1
    result.destroyed_contested += int(record.destroyed)
    names = tuple(sorted(territories[i].name for i in found))
    result.contested_groups[names] += 1
    coords = result.contested_xy.setdefault(names, ([], []))
    coords[0].append(x)
    coords[1].append(y)
    if record.category:
        result.category_contested[record.category] += 1
        result.category_destroyed_contested[record.category] += int(record.destroyed)
    for name in names:
        tally = result.tallies[name]
        tally.contested += 1
        for other in names:
            if other != name:
                tally.contested_with[other] += 1


def _tally_dispersion(result: Placement, record: Record, contested: bool) -> None:
    """Count each classified record against its year, its incident and its county.

    These three are kept separately from the running totals because they answer a
    different question: whether being inside more than one published outline is a
    property of the record set or a property of where a particular fire burned. Only
    records that could be classified are counted, so the denominator of any share taken
    over them is the population that had an outcome, not the population that has a row.
    """
    if record.year is not None:
        result.year_classified[record.year] += 1
        if contested:
            result.year_contested[record.year] += 1
    if record.incident:
        result.incident_classified[record.incident] += 1
        if contested:
            result.incident_contested[record.incident] += 1
    if record.county:
        result.county_classified[record.county] += 1
        if contested:
            result.county_contested[record.county] += 1


def classify(
    records: tuple[Record, ...],
    territories: tuple[Territory, ...],
    excluded_by_hazard: int,
) -> Placement:
    """Place every record, or record why it could not be placed."""
    result = Placement(
        fire_records=len(records),
        excluded_by_hazard=excluded_by_hazard,
        tallies=_empty_tallies(territories),
    )
    for record in records:
        if record.year is not None:
            result.years[record.year] += 1
        if record.county:
            result.counties[record.county] += 1
        else:
            result.records_with_no_county += 1
    usable, lons, lats = _usable_positions(records)
    result.not_measured = len(records) - len(usable)
    if not usable:
        return result
    xs, ys = project_lonlat(lons, lats)
    hits = _hits_by_record(territories, xs, ys)
    for position, record_index in enumerate(usable):
        record = records[record_index]
        found = hits[position]
        if not found:
            result.uncovered += 1
            result.destroyed_uncovered += int(record.destroyed)
        elif len(found) == 1:
            _tally_placed(
                result,
                territories[found[0]],
                record,
                float(xs[position]),
                float(ys[position]),
            )
        else:
            _tally_contested(
                result,
                territories,
                found,
                record,
                float(xs[position]),
                float(ys[position]),
            )
        _tally_dispersion(result, record, contested=len(found) > 1)
    return result


def measure_boundary_distances(
    placement: Placement, territories: tuple[Territory, ...]
) -> None:
    """Fill in, per territory, how many placements sit within each distance band.

    A territory with no placements has no distances to measure, and its bands stay
    ``not_measured`` rather than becoming a row of zeros.
    """
    for territory in territories:
        tally = placement.tallies[territory.name]
        if not tally.placed_x:
            tally.within_band = {}
            tally.distance_state = "not_measured"
            continue
        distances = distances_to_boundary(
            territory.geometry,
            np.array(tally.placed_x, dtype="float64"),
            np.array(tally.placed_y, dtype="float64"),
        )
        tally.within_band = {
            band: int(np.count_nonzero(distances < band)) for band in BOUNDARY_BANDS_M
        }
        tally.distance_state = "measured"


def measure_contested_group_distances(
    placement: Placement, territories: tuple[Territory, ...]
) -> None:
    """Per combination of overlapping outlines, how near its records sit to an edge.

    A contested record stops being contested when any outline in its combination
    ceases to contain it, so the distance that matters is the smallest one: the nearest
    edge among every outline the record falls inside. That is the edge an approximation
    error moves first, and it is what the bands below are taken against. A combination
    holding no record has no distances, and stays ``not_measured`` rather than becoming
    a row of zeros.
    """
    by_name = {t.name: t for t in territories}
    for names, (xs, ys) in placement.contested_xy.items():
        if not xs:
            placement.contested_bands[names] = {}
            placement.contested_distance_state[names] = "not_measured"
            continue
        points_x = np.array(xs, dtype="float64")
        points_y = np.array(ys, dtype="float64")
        nearest = np.full(len(xs), np.inf)
        for name in names:
            territory = by_name.get(name)
            if territory is None:  # pragma: no cover - names come from territories
                continue
            distances = distances_to_boundary(territory.geometry, points_x, points_y)
            nearest = np.minimum(nearest, distances)
        placement.contested_bands[names] = {
            band: int(np.count_nonzero(nearest < band)) for band in BOUNDARY_BANDS_M
        }
        placement.contested_distance_state[names] = "measured"


@dataclass
class LabelAgreement:
    """The agreement tally for one county label the publisher recorded."""

    label: str
    resolved: int = 0
    agreed: int = 0
    disagreed: int = 0
    matched_no_county: int = 0


@dataclass
class CountyAgreement:
    """Does the coordinate sit in the county the publisher recorded?

    Counted, never corrected. A disagreement is not a correction of CAL FIRE's field:
    it is a count of how often two published sources answer one question differently.
    """

    resolved: int = 0
    agreed: int = 0
    disagreed: int = 0
    matched_no_county: int = 0
    unmatchable_label: int = 0
    per_label: dict[str, LabelAgreement] = field(default_factory=dict)


def classify_county_agreement(
    records: tuple[Record, ...], counties: tuple[Any, ...]
) -> CountyAgreement:
    """Compare each record's coordinate against its own recorded county.

    Only records that could be compared are counted: a record needs a usable
    coordinate and a county label the boundary layer actually carries. Everything else
    stays in every other denominator in this project and none here. A record whose
    coordinate reaches no county polygon is counted as matched no county rather than
    being called a disagreement, because a hole at the edge of a generalized polygon
    is a different fact from a name that does not match.
    """
    result = CountyAgreement()
    if not counties:
        return result
    layer_names: dict[str, str] = {}
    for county in counties:
        layer_names[fold_name(county.name)] = county.name
    usable, lons, lats = _usable_positions(records)
    if not usable:
        return result
    xs, ys = project_lonlat(lons, lats)
    hits = _hits_by_record(counties, xs, ys)
    for position, record_index in enumerate(usable):
        record = records[record_index]
        if not record.county:
            continue
        key = fold_name(record.county)
        if key not in layer_names:
            result.unmatchable_label += 1
            continue
        label = layer_names[key]
        tally = result.per_label.setdefault(label, LabelAgreement(label=label))
        matched_names = {counties[i].name for i in hits[position]}
        result.resolved += 1
        tally.resolved += 1
        if not matched_names:
            result.matched_no_county += 1
            tally.matched_no_county += 1
        elif any(fold_name(name) == key for name in matched_names):
            result.agreed += 1
            tally.agreed += 1
        else:
            result.disagreed += 1
            tally.disagreed += 1
    return result


def fold_name(name: str) -> str:
    """A published name reduced to what two publishers can be expected to share.

    Case and inner whitespace, and nothing else. Two organizations writing the same
    county or the same fire will differ on those and this project will not treat that
    as a disagreement. Anything beyond them would be this project deciding that two
    different names are one thing, which is the adjudication ADR 0013 refuses for
    counties and ADR 0015 refuses for incident names.
    """
    return " ".join(name.split()).casefold()
