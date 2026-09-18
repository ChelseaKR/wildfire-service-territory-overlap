"""Projection, the published polygons, and the ledger of the ones that arrive broken.

Two decisions in this module carry the whole spatial result, so both are written down
here rather than left implicit in a library call.

**The projection is pinned as a pipeline, not resolved from a CRS pair.** Asking pyproj
to go from EPSG:4326 to EPSG:3310 lets it choose a datum transformation, and which one
it chooses depends on which PROJ grid files happen to be installed on the machine. That
is a reproducibility hole in a project whose output is supposed to be byte-identical
between runs. :data:`ALBERS_PIPELINE` is a bare projection with no datum step, so it
computes the same numbers on every machine with no grids present at all. The cost is
that a WGS84 coordinate is treated as though it were on GRS80, which in California is a
shift of roughly one to two meters. Every distance this project publishes is a band at
100 meters or wider, and PROVENANCE.md records the trade.

**A polygon the publisher ships invalid is repaired, and the repair is published.**
Eight of the territory polygons fail an OGC validity check on retrieval, with ring
self-intersections and nested shells. Shapely will happily answer a containment question
about an invalid polygon and the answer is undefined. So each one is passed through
``make_valid`` and recorded in a ledger, and every territory in the published output
carries whether its geometry was repaired. A reader who wants to discount the repaired
ones can see which they are. A repair that does not produce a polygonal result at all
removes the territory from the index and is reported as unusable, because a territory
this project cannot test containment against is not a territory it can report zero for.

The repair is a parameter rather than a constant, and all three strategies are kept
working. ``make_valid`` is what the published figures use; ``buffer_zero`` and the
structure-preserving ``make_valid_structure`` are the alternatives it is measured
against, and :mod:`wildfire_service_territory_overlap.sensitivity` runs the whole placement under each of them so
the disagreement between them is published as a measurement instead of as an estimate.
A strategy that only exists in an old draft cannot be run against the current one, which
is how the size of that choice went unmeasured in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree
from shapely.validation import make_valid

from wildfire_service_territory_overlap.sources import WIRES_TYPES

ALBERS_PIPELINE: Final[str] = (
    "+proj=pipeline "
    "+step +proj=unitconvert +xy_in=deg +xy_out=rad "
    "+step +proj=aea +lat_0=0 +lon_0=-120 +lat_1=34 +lat_2=40.5 "
    "+x_0=0 +y_0=-4000000 +ellps=GRS80"
)
"""California Albers, as a bare projection. Meters. No datum step, so no grid files."""

REPAIRED: Final[str] = "repaired"
AS_PUBLISHED: Final[str] = "as_published"
UNUSABLE: Final[str] = "unusable"

MAKE_VALID: Final[str] = "make_valid"
BUFFER_ZERO: Final[str] = "buffer_zero"
MAKE_VALID_STRUCTURE: Final[str] = "make_valid_structure"
REPAIR_STRATEGIES: Final[tuple[str, ...]] = (
    MAKE_VALID,
    BUFFER_ZERO,
    MAKE_VALID_STRUCTURE,
)
"""The three repairs. ``make_valid`` produces the published figures; see ADR 0007 and
ADR 0011. A strategy here is a candidate answer to a question the published geometry
does not settle, not a fix: each is run over the whole record set, and the size of the
disagreement between them is published rather than argued away."""


class TerritoryLoadError(ValueError):
    """The territory layer is not shaped the way this project reads it."""


def transformer() -> Transformer:
    """The one projection used everywhere. Constructed per call; pyproj caches PROJ."""
    return Transformer.from_pipeline(ALBERS_PIPELINE)


def project_lonlat(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Longitude and latitude in degrees to Albers meters."""
    x, y = transformer().transform(lon, lat)
    return np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")


def _project_geometry(geom: BaseGeometry) -> BaseGeometry:
    tr = transformer()

    def _apply(coords: np.ndarray) -> np.ndarray:
        x, y = tr.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    projected: BaseGeometry = shapely.transform(geom, _apply)
    return projected


def _polygonal(geom: BaseGeometry) -> BaseGeometry | None:
    """The polygonal part of a geometry, or None when there is not one."""
    if isinstance(geom, Polygon | MultiPolygon):
        return geom if not geom.is_empty else None
    parts = [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
    if not parts:
        return None
    return MultiPolygon(parts) if len(parts) > 1 else parts[0]


def repair(geom: BaseGeometry, strategy: str) -> BaseGeometry | None:
    """Apply one named repair, returning its polygonal part or None.

    ``make_valid`` noding repair produces the published figures. ``buffer_zero`` is the
    repair an earlier draft used and the one a reader is most likely to reach for.
    ``make_valid_structure`` asks GEOS for its structure-preserving repair, which
    answers invalidity differently where rings overlap or nest: the two ``make_valid``
    readings disagree there, and that disagreement is exactly what the sensitivity run
    in :mod:`wildfire_service_territory_overlap.sensitivity` is for.
    """
    if strategy == MAKE_VALID:
        return _polygonal(make_valid(geom))
    if strategy == MAKE_VALID_STRUCTURE:
        return _polygonal(shapely.make_valid(geom, method="structure"))
    if strategy == BUFFER_ZERO:
        return _polygonal(geom.buffer(0))
    raise TerritoryLoadError(
        f"{strategy!r} is not a repair this project knows. Add it to REPAIR_STRATEGIES "
        "and to the sensitivity run, or the published figures will rest on a repair "
        "nothing was compared against."
    )


@dataclass(frozen=True)
class Territory:
    """One published service territory outline, projected and validity-checked."""

    name: str
    kind: str
    object_id: int
    source_key: str
    geometry: BaseGeometry
    geometry_state: str
    geometry_note: str

    @property
    def repaired(self) -> bool:
        return self.geometry_state == REPAIRED


def _feature_fields(feature: dict[str, Any]) -> tuple[str, str, int]:
    props = feature.get("properties")
    if not isinstance(props, dict):
        raise TerritoryLoadError("a feature carries no properties object")
    name = props.get("Utility")
    kind = props.get("Type")
    oid = props.get("OBJECTID")
    if not isinstance(name, str) or not name.strip():
        raise TerritoryLoadError(f"a feature carries no Utility name: {props!r}")
    if not isinstance(kind, str) or not kind.strip():
        raise TerritoryLoadError(f"{name} carries no Type")
    if not isinstance(oid, int):
        raise TerritoryLoadError(f"{name} carries no integer OBJECTID")
    return name.strip(), kind.strip(), oid


def _build_territory(
    feature: dict[str, Any],
    fields: tuple[str, str, int],
    source_key: str,
    strategy: str,
) -> Territory:
    """One published feature, projected, and repaired if the publisher shipped it broken."""
    name, kind, oid = fields
    raw = feature.get("geometry")
    if raw is None:
        return Territory(
            name,
            kind,
            oid,
            source_key,
            Polygon(),
            UNUSABLE,
            "the published feature carries no geometry",
        )
    geom = _project_geometry(shapely.geometry.shape(raw))
    if geom.is_valid:
        return Territory(name, kind, oid, source_key, geom, AS_PUBLISHED, "")
    fixed = repair(geom, strategy)
    if fixed is None:
        return Territory(
            name,
            kind,
            oid,
            source_key,
            Polygon(),
            UNUSABLE,
            f"{strategy} produced no polygonal geometry to test against",
        )
    return Territory(
        name,
        kind,
        oid,
        source_key,
        fixed,
        REPAIRED,
        f"published geometry failed an OGC validity check and was repaired with "
        f"{strategy}",
    )


def load_territories(
    collections: dict[str, dict[str, Any]],
    *,
    keep_types: tuple[str, ...] = WIRES_TYPES,
    strategy: str = MAKE_VALID,
) -> tuple[tuple[Territory, ...], tuple[Territory, ...]]:
    """Read the published layers into projected territories.

    ``collections`` maps a source key to a GeoJSON FeatureCollection. Returns the
    usable territories and, separately, the ones whose geometry could not be repaired
    into anything containment can be tested against.

    ``keep_types`` and ``strategy`` are both parameters so that the two choices this
    project makes here can be re-run and compared rather than argued about. Neither
    default changes without an ADR.

    Territories come back sorted by name. Nothing downstream sorts by a measured value,
    and this is where that starts.
    """
    usable: list[Territory] = []
    unusable: list[Territory] = []
    for source_key in sorted(collections):
        collection = collections[source_key]
        features = collection.get("features")
        if not isinstance(features, list):
            raise TerritoryLoadError(f"{source_key} is not a FeatureCollection")
        for feature in features:
            fields = _feature_fields(feature)
            if fields[1] not in keep_types:
                continue
            territory = _build_territory(feature, fields, source_key, strategy)
            if territory.geometry_state == UNUSABLE:
                unusable.append(territory)
            else:
                usable.append(territory)
    usable.sort(key=lambda t: (t.name, t.object_id))
    unusable.sort(key=lambda t: (t.name, t.object_id))
    return tuple(usable), tuple(unusable)


@dataclass(frozen=True)
class County:
    """One published county outline, projected, with its bare name."""

    name: str
    object_id: int
    geometry: BaseGeometry


def load_counties(
    collection: dict[str, Any],
    *,
    name_field: str = "CDT_NAME_SHORT",
) -> tuple[County, ...]:
    """Read the county boundary layer into projected counties, sorted by name.

    The layer is read as published. A feature without a usable name or geometry is a
    broken retrieval rather than a county to skip silently, so it refuses.
    """
    features = collection.get("features")
    if not isinstance(features, list):
        raise TerritoryLoadError("the county layer is not a FeatureCollection")
    counties: list[County] = []
    for feature in features:
        props = feature.get("properties")
        if not isinstance(props, dict):
            raise TerritoryLoadError("a county feature carries no properties object")
        raw_name = props.get(name_field)
        oid = props.get("OBJECTID")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise TerritoryLoadError(f"a county feature carries no {name_field}")
        if not isinstance(oid, int):
            raise TerritoryLoadError("a county feature carries no integer OBJECTID")
        raw_geometry = feature.get("geometry")
        if raw_geometry is None:
            raise TerritoryLoadError(f"county {raw_name.strip()} carries no geometry")
        geometry = _project_geometry(shapely.geometry.shape(raw_geometry))
        counties.append(County(raw_name.strip(), oid, geometry))
    counties.sort(key=lambda c: (c.name, c.object_id))
    return tuple(counties)


def territory_index(territories: tuple[Territory, ...]) -> STRtree:
    """A spatial index over the territory outlines, in the order given."""
    if not territories:
        raise TerritoryLoadError("no usable territory geometry to index")
    return STRtree([t.geometry for t in territories])


def boundary_segments(geom: BaseGeometry) -> list[LineString]:
    """Every edge of a polygon's rings, as individual two-point lines.

    Distance from a point to a whole outline is linear in the number of vertices, and
    the largest territory here carries over a hundred thousand of them. Indexing the
    edges turns tens of billions of comparisons into a tree lookup. The geometry is not
    altered: these are the same edges the polygon already has.
    """
    polys: list[Polygon]
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:  # pragma: no cover - load_territories only ever produces polygonal geometry
        raise TerritoryLoadError(f"cannot take a boundary from {geom.geom_type}")
    segments: list[LineString] = []
    for poly in polys:
        for ring in (poly.exterior, *poly.interiors):
            coords = list(ring.coords)
            segments.extend(
                LineString([coords[i], coords[i + 1]]) for i in range(len(coords) - 1)
            )
    if not segments:
        raise TerritoryLoadError("a territory outline has no edges")
    return segments


def distances_to_boundary(
    geom: BaseGeometry, xs: np.ndarray, ys: np.ndarray
) -> np.ndarray:
    """Meters from each point to the nearest edge of ``geom``."""
    if len(xs) == 0:
        return np.empty(0, dtype="float64")
    segments = boundary_segments(geom)
    tree = STRtree(segments)
    points = shapely.points(xs, ys)
    nearest = tree.nearest(points)
    return np.asarray(
        shapely.distance(points, np.asarray(segments, dtype=object)[nearest]),
        dtype="float64",
    )
