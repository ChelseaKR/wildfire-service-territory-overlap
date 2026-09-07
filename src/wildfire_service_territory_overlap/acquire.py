"""Download the three published layers, once, by hand. The only module that opens a socket.

This never runs in a build and never runs in CI. Everything downstream reads files
already on disk, so the measurements are reproducible without asking anybody's server
for anything.

The damage inspections are fetched through ``perimeter``, which already carries a paged
walk over this exact layer. That walk had a defect in August 2026: it advanced its offset
by the page size it asked for rather than by the number of rows it was handed, so
whenever the service capped a page below the requested size it stepped over the
difference. The download then ended normally, hashed cleanly, and was short. Records that
were skipped look exactly like records that were never there. That is why this project
consumes the fixed walk rather than writing a second one, and why it adds the checks
below on top of it rather than trusting any walk, including that one.

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
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from perimeter.acquire import AcquisitionBlocked, AcquisitionFailed
from perimeter.acquire import fetch_layer as perimeter_fetch_layer
from perimeter.acquire import layer_record_count as perimeter_layer_record_count

from wildfire_service_territory_overlap.sources import (
    COUNTIES,
    DINS,
    ELSE_IOU_POU,
    ELSE_OTHER,
    Source,
)

USER_AGENT = "wildfire-service-territory-overlap/0.1 (+https://github.com/ChelseaKR/wildfire-service-territory-overlap)"
WHERE = "1=1"
PAGE_SIZE = 2000
PAUSE_SECONDS = 0.2
TIMEOUT_SECONDS = 180

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


def _get(url: str) -> dict[str, Any]:
    if not url.startswith("https://"):
        raise AcquisitionFailed(f"refusing to fetch a non-HTTPS endpoint: {url!r}")
    # Audited: both linters flag urllib for accepting schemes such as file://. The scheme
    # is pinned to https on the line above, and the host comes from the reviewed endpoints
    # in sources.py rather than from user input or from any fetched content.
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        if error.code in {401, 403, 429}:
            raise AcquisitionBlocked(
                f"{url} answered {error.code}. This project does not work around access "
                "controls. Download the file from the dataset's landing page by hand and "
                "record the manual acquisition in PROVENANCE.md."
            ) from error
        raise AcquisitionFailed(f"{url} answered {error.code}") from error
    if "json" not in content_type.lower():
        raise AcquisitionBlocked(
            f"{url} answered {content_type!r} rather than JSON, which is what a "
            "challenge page looks like. Acquire the file by hand instead."
        )
    parsed: dict[str, Any] = json.loads(body)
    if "error" in parsed:
        raise AcquisitionFailed(f"{url} returned an error payload: {parsed['error']}")
    return parsed


def layer_record_count(endpoint: str) -> int:
    """How many records the layer says it holds under the predicate the walk uses."""
    query = urllib.parse.urlencode(
        {"where": WHERE, "returnCountOnly": "true", "f": "json"}
    )
    payload = _get(f"{endpoint}?{query}")
    count = payload.get("count")
    if not isinstance(count, int) or isinstance(count, bool):
        raise AcquisitionFailed(
            f"{endpoint} answered returnCountOnly with no count: {payload!r}. A download "
            "nothing checked is not an acquisition."
        )
    return count


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
    out_sr: int = 4326,
) -> list[dict[str, Any]]:
    """Page a layer as GeoJSON, stepping by the rows received, never by the page asked for."""
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "where": WHERE,
                "outFields": ",".join(fields),
                "returnGeometry": "true" if with_geometry else "false",
                "outSR": out_sr,
                "orderByFields": "OBJECTID ASC",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "f": "geojson",
            }
        )
        payload = _get(f"{endpoint}?{query}")
        page = payload.get("features")
        if not isinstance(page, list):
            raise AcquisitionFailed(f"{endpoint} answered with no features array")
        if not page:
            break
        features.extend(page)
        offset += len(page)
        time.sleep(PAUSE_SECONDS)
    return features


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
    before = perimeter_layer_record_count(DINS.endpoint, user_agent=USER_AGENT)
    rows = perimeter_fetch_layer(DINS.endpoint, DINS_FIELDS, user_agent=USER_AGENT)
    after = perimeter_layer_record_count(DINS.endpoint, user_agent=USER_AGENT)
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
