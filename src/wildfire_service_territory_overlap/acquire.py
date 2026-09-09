"""Download the three published layers, once, by hand. One of two modules that open a socket.

This never runs in a build and never runs in CI. Everything downstream reads files
already on disk, so the measurements are reproducible without asking anybody's server
for anything.

``refresh.py`` is the other one: it asks each layer for its own record count through the
call below, and asks ArcGIS Online for the two territory items' metadata, both through the
same pinned reader. This docstring said ``acquire.py`` was the only module that opens a
socket for a day after that landed, and so did the README and SECURITY.md, because nothing
read the claim. ``tests/test_provenance_and_standards.py`` reads it now.

Every layer is fetched through ``perimeter``, which carries the paged walk. That walk had
a defect in August 2026: it advanced its offset by the page size it asked for rather than
by the number of rows it was handed, so whenever the service capped a page below the
requested size it stepped over the difference. The download then ended normally, hashed
cleanly, and was short. Records that were skipped look exactly like records that were
never there. That is why this project consumes the fixed walk rather than writing a
second one, and why it adds the checks below on top of it rather than trusting any walk,
including that one.

Until the pin moved onto the commit this project now runs, only the damage inspections
went through it. ``perimeter.acquire.iter_features`` hard-coded ``f=json``, and the three
polygon layers are read as GeoJSON, so this module kept a second paged walk with a second
copy of the offset rule and a second copy of the refusals below. That was gap 2 in
``docs/UPSTREAM.md``; it was raised upstream, upstream added an output format, and both
copies are gone. What is left of them is two functions that bind this project's own
User-Agent and the format it needs, and call upstream once.

Three guards, applied to every layer this module fetches:

1. The layer is asked for its own record count under the same predicate, before and
   after the walk. A walk that disagrees with either writes nothing.
2. Object identifiers must come back strictly increasing. A page stepped over leaves no
   trace in the row count alone, but a walk that skipped a block and then resumed still
   produces an ordered sequence, so the count check is what catches that and this check
   is what catches a walk that repeated or reordered a page.
3. Identifiers must be unique. A duplicated page inflates the row count to the right
   total while holding the wrong rows.

There is no fallback path and nothing retries with a different identity. A layer that
declines automated access raises and the file is acquired by hand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from perimeter.acquire import AcquisitionFailed
from perimeter.acquire import fetch_layer as perimeter_fetch_layer
from perimeter.acquire import iter_features as perimeter_iter_features
from perimeter.acquire import layer_record_count as perimeter_layer_record_count

from wildfire_service_territory_overlap.sources import (
    COUNTIES,
    DINS,
    ELSE_IOU_POU,
    ELSE_OTHER,
    Source,
)

USER_AGENT = "wildfire-service-territory-overlap/0.1 (+https://github.com/ChelseaKR/wildfire-service-territory-overlap)"

OUT_SR = 4326
"""The spatial reference every polygon layer is asked for and every measurement assumes.

Sent explicitly rather than left to the service's default, because ``geometry.py`` reads
the coordinates as longitude and latitude and a layer is free to publish in a projected
system. Upstream sends ``outSR`` only when it is given, which is what keeps its own pinned
retrievals reproducible; this project gives it.
"""

DINS_FIELDS: tuple[str, ...] = (
    "OBJECTID",
    "COUNTY",
    "DAMAGE",
    "HAZARDTYPE",
    "INCIDENTNAME",
    "INCIDENTSTARTDATE",
    "LATITUDE",
    "LONGITUDE",
    "STRUCTURECATEGORY",
)
"""The nine fields this project reads.

``COUNTY`` is the publisher's own county name, an administrative area of the same kind
as an incident name and a great deal coarser than a coordinate this project already
holds. It was added in the retrieval of 2026-08-17 so that the overlap can be cut by
county; see ``docs/adr/0009``.

``STRUCTURECATEGORY`` was added in the retrieval of 2026-08-23 so the placed-versus-
contested representativeness check can be run inside each published structure class
rather than only across the whole record set.

Deliberately not fetched: SITEADDRESS, APN, STREETNUMBER, STREETNAME, ZIPCODE,
ASSESSEDIMPROVEDVALUE, CITY. They are published by CAL FIRE and none of them is needed
to answer which polygon a point is in, so they are never downloaded and cannot be
republished by accident.
"""

TERRITORY_FIELDS: tuple[str, ...] = ("OBJECTID", "Acronym", "Utility", "Type")

COUNTY_FIELDS: tuple[str, ...] = (
    "OBJECTID",
    "CDT_NAME_SHORT",
)


class IncompleteAcquisition(AcquisitionFailed):
    """A walk finished without evidence that it read the whole layer."""


@dataclass(frozen=True)
class Acquired:
    source_key: str
    path: Path
    feature_count: int
    raw_bytes: int
    sha256: str
    retrieved: str
    endpoint: str


def layer_record_count(endpoint: str) -> int:
    """Upstream's count, always asked for under this project's own name.

    This module used to carry its own copy of the request and of every refusal around
    it: HTTPS only, stop on 401, 403 and 429, refuse a non-JSON challenge page, refuse an
    error payload. The copy existed because the second walk needed a fetch and upstream's
    is private, and it went when the second walk did. Binding the User-Agent in one place
    is what is left, and it is not a reimplementation of anything.
    """
    return perimeter_layer_record_count(endpoint, user_agent=USER_AGENT)


def assert_walk_is_whole(
    identifiers: Sequence[int], expected: int, *, layer: str
) -> None:
    """Refuse a walk that cannot show it read every row. Never repairs, only refuses."""
    if len(identifiers) != expected:
        raise IncompleteAcquisition(
            f"{layer}: the layer reports {expected} records and the walk collected "
            f"{len(identifiers)}. Nothing was written. A short walk is not a smaller "
            "dataset; it is a dataset with a hole in it that nothing downstream can see."
        )
    if len(set(identifiers)) != len(identifiers):
        raise IncompleteAcquisition(
            f"{layer}: the walk returned {len(identifiers) - len(set(identifiers))} "
            "duplicate identifiers, so the row count is right and the rows are not."
        )
    for previous, current in pairwise(identifiers):
        if current <= previous:
            raise IncompleteAcquisition(
                f"{layer}: identifiers are not strictly increasing at {previous} -> "
                f"{current}. The walk asked for them ordered, so a page arrived out of "
                "order or was served twice."
            )


def fetch_feature_pages(
    endpoint: str,
    fields: tuple[str, ...],
    *,
    with_geometry: bool,
    out_sr: int = OUT_SR,
) -> list[dict[str, Any]]:
    """Upstream's walk, asked for GeoJSON under this project's own name.

    This was a second paged walk until the pin moved. It held its own copy of the offset
    rule -- step by the page that arrived, never by the page that was asked for -- which
    is the rule this whole project exists downstream of, and a copy of it drifts. It is
    now one call.

    The features come back exactly as the service sent them, GeoJSON ``Feature`` objects
    with the attributes under ``properties``, which is what ``geometry.py`` and ``_write``
    consume. Nothing converts, reprojects or renames on the way through, here or upstream.
    """
    return list(
        perimeter_iter_features(
            endpoint,
            fields,
            user_agent=USER_AGENT,
            return_geometry=with_geometry,
            out_sr=out_sr,
            out_format="geojson",
        )
    )


def _write(path: Path, payload: Any) -> Acquired:
    text = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    raw = path.read_bytes()
    count = len(payload["features"]) if isinstance(payload, dict) else len(payload)
    return Acquired(
        source_key=path.stem,
        path=path,
        feature_count=count,
        raw_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        retrieved=datetime.now(tz=UTC).date().isoformat(),
        endpoint="",
    )


def acquire_territories(source: Source, out_dir: Path) -> Acquired:
    """Read a territory layer whole, with geometry, or write nothing."""
    before = layer_record_count(source.endpoint)
    features = fetch_feature_pages(
        source.endpoint, TERRITORY_FIELDS, with_geometry=True
    )
    after = layer_record_count(source.endpoint)
    if before != after:
        raise IncompleteAcquisition(
            f"{source.key}: the layer reported {before} records before the walk and "
            f"{after} after it. It was republished mid-walk; re-run the acquisition."
        )
    identifiers = [int(f["properties"]["OBJECTID"]) for f in features]
    assert_walk_is_whole(identifiers, before, layer=source.key)
    collection = {
        "type": "FeatureCollection",
        "features": sorted(features, key=lambda f: int(f["properties"]["OBJECTID"])),
    }
    acquired = _write(out_dir / source.raw_file, collection)
    return Acquired(
        source_key=source.key,
        path=acquired.path,
        feature_count=acquired.feature_count,
        raw_bytes=acquired.raw_bytes,
        sha256=acquired.sha256,
        retrieved=acquired.retrieved,
        endpoint=source.endpoint,
    )


def acquire_dins(out_dir: Path) -> Acquired:
    """Read the damage inspections through perimeter's walk, then check it independently.

    Every request names this project. Until the pin moved to `3a6aa47`, upstream read its
    own `USER_AGENT` from a module constant inside a private `_get` and took no other, so
    the largest of the four layers at 132,522 records went out as
    `perimeter-coverage/0.1` while the other three carried this project's name. An
    operator at CAL FIRE reading their logs saw a caller that did not lead back here.
    docs/UPSTREAM.md gap 1.
    """
    before = layer_record_count(DINS.endpoint)
    rows = perimeter_fetch_layer(DINS.endpoint, DINS_FIELDS, user_agent=USER_AGENT)
    after = layer_record_count(DINS.endpoint)
    if before != after:
        raise IncompleteAcquisition(
            f"{DINS.key}: the layer reported {before} records before the walk and "
            f"{after} after it. It was republished mid-walk; re-run the acquisition."
        )
    assert_walk_is_whole([int(row["OBJECTID"]) for row in rows], before, layer=DINS.key)
    acquired = _write(out_dir / DINS.raw_file, rows)
    return Acquired(
        source_key=DINS.key,
        path=acquired.path,
        feature_count=acquired.feature_count,
        raw_bytes=acquired.raw_bytes,
        sha256=acquired.sha256,
        retrieved=acquired.retrieved,
        endpoint=DINS.endpoint,
    )


def acquire_counties(source: Source, out_dir: Path) -> Acquired:
    """Read the county boundary layer whole, with geometry, or write nothing."""
    before = layer_record_count(source.endpoint)
    features = fetch_feature_pages(source.endpoint, COUNTY_FIELDS, with_geometry=True)
    after = layer_record_count(source.endpoint)
    if before != after:
        raise IncompleteAcquisition(
            f"{source.key}: the layer reported {before} records before the walk and "
            f"{after} after it. It was republished mid-walk; re-run the acquisition."
        )
    identifiers = [int(f["properties"]["OBJECTID"]) for f in features]
    assert_walk_is_whole(identifiers, before, layer=source.key)
    collection = {
        "type": "FeatureCollection",
        "features": sorted(features, key=lambda f: int(f["properties"]["OBJECTID"])),
    }
    acquired = _write(out_dir / source.raw_file, collection)
    return Acquired(
        source_key=source.key,
        path=acquired.path,
        feature_count=acquired.feature_count,
        raw_bytes=acquired.raw_bytes,
        sha256=acquired.sha256,
        retrieved=acquired.retrieved,
        endpoint=source.endpoint,
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - network entrypoint
    parser = argparse.ArgumentParser(
        prog="wildfire-service-territory-overlap-acquire",
        description=(
            "Download the public source layers into a local directory. "
            "Run by hand; never part of a build or CI."
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)
    manifest: list[dict[str, object]] = []
    results = [
        acquire_dins(args.out),
        acquire_territories(ELSE_IOU_POU, args.out),
        acquire_territories(ELSE_OTHER, args.out),
        acquire_counties(COUNTIES, args.out),
    ]
    for result in results:
        print(
            f"{result.source_key}: {result.feature_count} features, "
            f"{result.raw_bytes} bytes, sha256 {result.sha256}"
        )
        manifest.append(
            {
                "source": result.source_key,
                "endpoint": result.endpoint,
                "file": result.path.name,
                "feature_count": result.feature_count,
                "raw_bytes": result.raw_bytes,
                "sha256": result.sha256,
                "retrieved": result.retrieved,
            }
        )
    path = args.out / "acquisition.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"wrote {path}")
    print(
        "Copy feature_count, raw_bytes and sha256 into src/wildfire_service_territory_overlap/sources.py"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
