"""What was downloaded, from where, under what terms, and what its publisher says.

This module is the single reviewed record of provenance. PROVENANCE.md restates it for a
reader and a test asserts the two agree, so the document cannot drift away from the
numbers the report prints.

Four sources, three publishers. The damage inspections come from CAL FIRE. The service
territory boundaries come from the California Energy Commission, in two layers. The
county boundaries used only to check the publisher's own county labels come from the
California Department of Technology. The quotes below are those publishers' own words,
copied from the dataset metadata on the retrieval date, and every measurement in this
project is tied back to one of them.

Nothing here is affiliated with, endorsed by, or approved by CAL FIRE, the California
Energy Commission, or any electric utility.
"""

from __future__ import annotations

from dataclasses import dataclass

RETRIEVED = "2026-08-23"
"""The date the layers were downloaded. Mirrored in PROVENANCE.md, tested."""


@dataclass(frozen=True)
class Caveat:
    """One published limitation, quoted, and the measurement built from it."""

    topic: str
    quote: str
    measured_as: str


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    publisher: str
    landing_page: str
    endpoint: str
    terms: str
    terms_url: str
    item_id: str
    item_modified: str
    retrieved: str
    feature_count: int
    raw_bytes: int
    sha256: str
    raw_file: str
    caveats: tuple[Caveat, ...]


_CEC_APPROXIMATE = Caveat(
    topic="Approximate boundaries",
    quote=(
        "Boundaries are approximate, for absolute territory information, contact the "
        "appropriate load serving entity."
    ),
    measured_as=(
        "Every record placed inside exactly one territory is also measured for its "
        "distance to that territory's published edge, and the counts are published in "
        "bands at 100, 250, 500 and 1000 meters. A reader can then see how much of a "
        "territory's total sits close enough to the edge to move if the approximation "
        "is off by that much. No boundary is corrected, smoothed, or second-guessed."
    ),
)

_CEC_INCOMPLETE = Caveat(
    topic="Missing entities",
    quote=(
        "Not all electric load serving entities are represented, if you have "
        "information on missing territory locations, please contact GIS@energy.ca.gov"
    ),
    measured_as=(
        "A record that lands inside no published territory is counted and published as "
        "covered by no published territory. It is never attached to the nearest one and "
        "it is never reported as a zero for anybody."
    ),
)

_CEC_COMPILED = Caveat(
    topic="Compilation",
    quote=(
        "Data compiled from California Energy Commission staff from georeferenced "
        "electric territory maps and the United States Department of Homeland Security, "
        "Homeland Infrastructure Foundation-Level Data (HIFILD)"
    ),
    measured_as=(
        "The layers are read as published. The polygons are service territory outlines "
        "and nothing in this project reads, infers, or derives the position of any "
        "conductor, pole, substation, or other physical asset from them."
    ),
)


ELSE_IOU_POU = Source(
    key="else_iou_pou",
    title="Electric Load Serving Entities (IOU & POU)",
    publisher="California Energy Commission",
    landing_page=(
        "https://cecgis-caenergy.opendata.arcgis.com/datasets/"
        "CAEnergy::electric-load-serving-entities-iou-pou/about"
    ),
    endpoint=(
        "https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/"
        "ElectricLoadServingEntities_IOU_POU/FeatureServer/0/query"
    ),
    terms="California Energy Commission conditions of use",
    terms_url="https://www.energy.ca.gov/conditions-of-use",
    item_id="30410214d637434ba1003cbdcc32cf55",
    item_modified="2026-08-12",
    retrieved=RETRIEVED,
    feature_count=53,
    raw_bytes=11724721,
    sha256="e805520e747de619c9a97d03f8d70c9125f44b6e6fb2c0067bc122b317f2260e",
    raw_file="else_iou_pou.geojson",
    caveats=(_CEC_APPROXIMATE, _CEC_INCOMPLETE, _CEC_COMPILED),
)

ELSE_OTHER = Source(
    key="else_other",
    title="Electric Load Serving Entities (Other)",
    publisher="California Energy Commission",
    landing_page=(
        "https://cecgis-caenergy.opendata.arcgis.com/datasets/"
        "CAEnergy::electric-load-serving-entities-other/about"
    ),
    endpoint=(
        "https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/"
        "ElectricLoadServingEntities_Other/FeatureServer/0/query"
    ),
    terms="California Energy Commission conditions of use",
    terms_url="https://www.energy.ca.gov/conditions-of-use",
    item_id="07224640a2fe42f89399be796e7b8810",
    item_modified="2026-08-12",
    retrieved=RETRIEVED,
    feature_count=32,
    raw_bytes=7397382,
    sha256="f6e6880c03c4e062aa6f0b2a69a66b74e7782ff62a2a3ce7e641efc4f0f7ffe3",
    raw_file="else_other.geojson",
    caveats=(_CEC_APPROXIMATE, _CEC_INCOMPLETE, _CEC_COMPILED),
)

DINS = Source(
    key="dins_postfire",
    title="CAL FIRE Damage Inspection (DINS) Data",
    publisher="California Department of Forestry and Fire Protection",
    landing_page="https://data.ca.gov/dataset/cal-fire-damage-inspection-dins-data",
    endpoint=(
        "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/"
        "POSTFIRE_MASTER_DATA_SHARE/FeatureServer/0/query"
    ),
    terms="Creative Commons Attribution",
    terms_url="http://www.opendefinition.org/licenses/cc-by",
    item_id="",
    item_modified="",
    retrieved=RETRIEVED,
    feature_count=132522,
    raw_bytes=31908735,
    sha256="28a0bedfc74616281febc2268f40a40304c96c2eb0414e9b04b10f5318f2c496",
    raw_file="dins_postfire.json",
    caveats=(
        Caveat(
            topic="Scope",
            quote=(
                "This database is used to document all structures impacted by wildland "
                "fire within the Statewide Responsibility Area (SRA) that are inside or "
                "within 300 feet of the fire perimeter."
            ),
            measured_as=(
                "Every denominator in this project is a count of DINS records. Nothing "
                "here divides by housing units, parcels, customers, or meters, because "
                "the numerator is drawn from a population defined by fire and by "
                "responsibility area, and those denominators are not that population. "
                "A structure absent from this file is not counted here as undamaged and "
                "is not counted here at all."
            ),
        ),
        Caveat(
            topic="Inspection limits",
            quote=(
                "Fire damage and poor access are major limiting factors for damage "
                "inspectors. All inspections are conducted using a systematic "
                "inspection process, however not all structures impacted by the fire "
                "may be identified due to these factors. Therefore, a small margin of "
                "error is expected."
            ),
            measured_as=(
                "Read as the reason the record set is the population and not a sample "
                "of some larger one. Records CAL FIRE recorded as Inaccessible are "
                "counted in the denominators here, because they were identified even "
                "though they could not be reached, and dropping them would silently "
                "shrink the thing being measured."
            ),
        ),
        Caveat(
            topic="Hazard types",
            quote=(
                "Information such as structure type, construction features, and "
                "defensive actions are determined as best as possible. Attributes with "
                "null values could not be determined."
            ),
            measured_as=(
                "The layer's published HAZARDTYPE domain carries Fire, Earthquake, "
                "Flood, Civil Disturbance and Hazardous Material. This project measures "
                "the Fire records only, and publishes the count of records excluded by "
                "that filter rather than describing the file as wholly a wildfire file."
            ),
        ),
    ),
)

COUNTIES = Source(
    key="county_boundaries",
    title="California County Boundaries and Identifiers",
    publisher="California Department of Technology",
    landing_page=(
        "https://gis.data.ca.gov/datasets/"
        "California::california-county-boundaries-and-identifiers/about"
    ),
    endpoint=(
        "https://services3.arcgis.com/uknczv4rpevve42E/arcgis/rest/services/"
        "California_County_Boundaries_and_Identifiers_Blue_Version_view/"
        "FeatureServer/1/query"
    ),
    terms="State of California terms of use",
    terms_url="https://www.ca.gov/use/terms/",
    item_id="60b7e0f3d33b4064a4b43bf14589bfe3",
    item_modified="",
    retrieved=RETRIEVED,
    feature_count=58,
    raw_bytes=28406231,
    sha256="52cb40c1db91b1a566683a4a6d39d2fad362df6b654e9d4b602bbbfe29601908",
    raw_file="county_boundaries.geojson",
    caveats=(
        Caveat(
            topic="Schema stability",
            quote=(
                "Note: The schema changed in February 2025 - please see below. We will "
                "post a roadmap of upcoming changes, but service URLs and schema are "
                "now stable."
            ),
            measured_as=(
                "Only two fields are read from this layer, OBJECTID and CDT_NAME_SHORT "
                "beside the geometry, and the layer's own record count is checked "
                "against the walk before anything downstream runs. A schema change "
                "would surface as a refused acquisition rather than as silently wrong "
                "county names."
            ),
        ),
        Caveat(
            topic="Boundary accuracy",
            quote=(
                "Boundary accuracy is *not* guaranteed, and though CDTFA works to "
                "align boundaries based on historical records and local changes, "
                "errors will exist."
            ),
            measured_as=(
                "This layer answers one question: does a record's coordinate sit in "
                "the county its publisher recorded, counted and never corrected. The "
                "publisher's own warning that boundary errors will exist is the reason "
                "the comparison is published as counts with intervals rather than as "
                "a list of which record is right."
            ),
        ),
    ),
)

SOURCES: tuple[Source, ...] = (DINS, ELSE_IOU_POU, ELSE_OTHER, COUNTIES)


PUBLISHED_TYPES: tuple[str, ...] = ("ADMIN", "CCA", "CO-OP", "IOU", "POU", "Tribal")
"""Every ``Type`` value the two CEC layers carry, in name order.

Held here so the inclusion rule below can be re-run against its own alternatives. A type
that appears in a future retrieval and not in this tuple is a change in the publisher's
data, and :mod:`wildfire_service_territory_overlap.sensitivity` reports it rather than absorbing it.
"""

WIRES_TYPES: tuple[str, ...] = ("CO-OP", "IOU", "POU", "Tribal")
"""The CEC ``Type`` values read as a retail electric service territory.

The inclusion rule is the publisher's own ``Type`` field, not a judgment made here about
any named entity. Two of the published types are deliberately outside it, for reasons
that are about what the polygon represents rather than about the organization:
"""

EXCLUDED_TYPES: dict[str, str] = {
    "CCA": (
        "A community choice aggregator is defined at Public Utilities Code section "
        "331.1 as a local government electricity buyers' program, and section 366.2 "
        "leaves metering, billing and delivery with the electrical corporation. Its "
        "polygon overlays another entity's distribution footprint rather than being "
        "one, so counting a record into both would count it twice."
    ),
    "ADMIN": (
        "A federal power marketing administration. The polygon is a marketing and "
        "transmission administration area, not a retail service territory."
    ),
}

TYPE_FIELD_IS_UNDOCUMENTED: str = (
    "The inclusion rule reads the publisher's Type field, and the publisher documents "
    "none of its values. As retrieved, the layer metadata carries no description on the "
    "Type field and no coded-value domain, the FGDC record carries no entity and "
    "attribute section, and no data dictionary is attached to either item. What each "
    "value means is therefore inferred from the value itself, which is why the rule is "
    "published with its sensitivity and why the README asks for a domain review."
)
"""Checked against the published metadata on the retrieval date, and recorded as a fact
about the source rather than as a complaint. The measurement built from it is
:mod:`wildfire_service_territory_overlap.sensitivity`, which reports what the rule is worth in records."""

CALIFORNIA_BBOX: tuple[float, float, float, float] = (-124.5, 32.4, -114.0, 42.1)
"""Longitude and latitude bounds used only to refuse a coordinate, never to correct one.

A record whose published coordinate falls outside this box is reported as not measured.
It is not moved, not clipped, and not counted as covered by no territory, because those
are different facts and only one of them is known.
"""
