"""Every branch of the classification, over geography designed to reach all of them."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import shapely

from wildfire_service_territory_overlap.geometry import (
    Territory,
    TerritoryLoadError,
    load_counties,
    load_territories,
    project_lonlat,
)
from wildfire_service_territory_overlap.placement import (
    BOUNDARY_BANDS_M,
    Placement,
    Record,
    SchemaError,
    assert_columns,
    classify,
    classify_county_agreement,
    containment_signatures,
    measure_boundary_distances,
    measure_contested_group_distances,
    read_records,
)

ALPHA = "Alpha Electric Company"
BETA = "Beta Municipal Utility"
GAMMA = "Gamma Rural Cooperative"


def test_the_hazard_filter_keeps_fire_and_counts_what_it_dropped(
    records: tuple[tuple[Record, ...], int],
) -> None:
    kept, excluded = records
    assert excluded == 1, "the fixture holds one flood record"
    assert len(kept) == 12
    assert all(r.damage is not None for r in kept)


def test_every_fire_record_lands_in_exactly_one_of_the_four_outcomes(
    placement: Placement,
) -> None:
    assert placement.classified == placement.fire_records
    assert placement.placed == 6
    assert placement.contested == 3
    assert placement.uncovered == 1
    assert placement.not_measured == 2


def test_a_contested_record_is_not_awarded_to_either_territory(
    placement: Placement,
) -> None:
    assert placement.tallies[ALPHA].contested == 3
    assert placement.tallies[BETA].contested == 3
    assert placement.tallies[ALPHA].placed + placement.tallies[BETA].placed == 5
    assert placement.contested_groups[(ALPHA, BETA)] == 3


def test_contested_partners_are_recorded_both_ways(placement: Placement) -> None:
    assert placement.tallies[ALPHA].contested_with[BETA] == 3
    assert placement.tallies[BETA].contested_with[ALPHA] == 3


def test_a_missing_coordinate_is_not_measured_rather_than_uncovered() -> None:
    record = Record(1, "Destroyed (>50%)", "X", "Sample County East", 2020, None, None)
    assert not record.has_usable_coordinate


@pytest.mark.parametrize(
    ("lon", "lat"),
    [(-100.0, 40.0), (-120.0, 10.0), (-180.0, 38.0), (-120.0, 60.0)],
)
def test_a_coordinate_outside_california_is_refused_not_corrected(
    lon: float, lat: float
) -> None:
    assert not Record(
        1, "No Damage", "X", "Sample County East", 2020, lon, lat
    ).has_usable_coordinate


def test_an_in_state_coordinate_is_usable() -> None:
    assert Record(
        1, "No Damage", "X", "Sample County East", 2020, -121.0, 38.5
    ).has_usable_coordinate


def test_a_record_inside_no_published_outline_is_uncovered(
    placement: Placement,
) -> None:
    assert placement.uncovered == 1
    assert placement.destroyed_uncovered == 1


def test_a_repaired_bowtie_still_holds_its_record(placement: Placement) -> None:
    assert placement.tallies[GAMMA].placed == 1


def test_an_excluded_entity_type_never_becomes_a_territory(
    territories: tuple[Territory, ...],
) -> None:
    names = {t.name for t in territories}
    assert "Delta Choice Energy" not in names, (
        "a CCA overlays a territory, it is not one"
    )
    assert names == {ALPHA, BETA, GAMMA}


def test_boundary_bands_measure_distance_from_the_published_edge(
    placement: Placement,
) -> None:
    alpha = placement.tallies[ALPHA]
    assert alpha.distance_state == "measured"
    # One fixture record sits about 87 m inside Alpha's western edge.
    assert alpha.within_band[100] == 1
    assert alpha.within_band[1000] == 1
    assert set(alpha.within_band) == set(BOUNDARY_BANDS_M)


def test_bands_are_nested_so_a_wider_band_never_holds_fewer(
    placement: Placement,
) -> None:
    for tally in placement.tallies.values():
        if tally.distance_state != "measured":
            continue
        counts = [tally.within_band[band] for band in sorted(BOUNDARY_BANDS_M)]
        assert counts == sorted(counts)


def test_a_territory_with_no_placements_has_no_bands_rather_than_zeroes(
    territories: tuple[Territory, ...],
) -> None:
    empty = classify((), territories, 0)
    measure_boundary_distances(empty, territories)
    for tally in empty.tallies.values():
        assert tally.distance_state == "not_measured"
        assert tally.within_band == {}


def test_classify_with_no_usable_coordinates_still_returns_a_result(
    territories: tuple[Territory, ...],
) -> None:
    result = classify(
        (Record(1, "No Damage", "X", "Sample County East", 2020, None, None),),
        territories,
        0,
    )
    assert result.not_measured == 1
    assert result.placed == 0
    assert result.classified == 1


def test_largest_incident_breaks_ties_on_the_name_not_on_dict_order(
    placement: Placement,
) -> None:
    alpha = placement.tallies[ALPHA]
    largest = alpha.largest_incident
    assert largest is not None
    assert largest == ("SAMPLE ONE", 3)


def test_a_territory_with_no_incidents_reports_none(
    territories: tuple[Territory, ...],
) -> None:
    empty = classify((), territories, 0)
    assert empty.tallies[ALPHA].largest_incident is None


def test_years_are_counted_from_the_published_start_date(placement: Placement) -> None:
    assert placement.years[2020] == 3
    assert sum(placement.years.values()) == placement.fire_records


def test_the_year_split_counts_only_records_that_got_an_outcome(
    placement: Placement,
) -> None:
    """A record with no usable coordinate has a year and no contested answer."""
    classified = sum(placement.year_classified.values())
    assert classified == placement.fire_records - placement.not_measured
    for year, contested in placement.year_contested.items():
        assert contested <= placement.year_classified[year]


def test_the_incident_split_counts_only_records_that_got_an_outcome(
    placement: Placement,
) -> None:
    for name, contested in placement.incident_contested.items():
        assert contested <= placement.incident_classified[name]
    assert sum(placement.incident_classified.values()) <= placement.classified


def test_the_faster_containment_route_answers_what_the_predicate_form_answers(
    territories: tuple[Territory, ...], records: tuple[tuple[Record, ...], int]
) -> None:
    """The two-step query is an optimization, so it has to be exactly equivalent.

    ``STRtree.query(predicate="intersects")`` re-walks every ring on every test and
    costs about forty seconds over the real record set. The tree-then-prepared-test form
    costs a tenth of a second. This asserts the two agree rather than assuming it, over
    a grid dense enough to land points inside, outside, and on the shared edges.
    """
    grid = tuple(
        Record(
            object_id=i,
            damage=None,
            incident=None,
            county=None,
            year=None,
            lon=-121.2 + 0.05 * (i % 30),
            lat=37.9 + 0.05 * (i // 30),
        )
        for i in range(900)
    )
    usable = [r for r in grid if r.has_usable_coordinate]
    xs, ys = project_lonlat(
        np.array([r.lon for r in usable], dtype="float64"),
        np.array([r.lat for r in usable], dtype="float64"),
    )
    points = shapely.points(xs, ys)
    pairs = shapely.STRtree([t.geometry for t in territories]).query(
        points, predicate="intersects"
    )
    expected: list[list[str]] = [[] for _ in range(len(points))]
    for point_index, hit_index in zip(pairs[0], pairs[1], strict=True):
        expected[int(point_index)].append(territories[int(hit_index)].name)

    signatures = [s for s in containment_signatures(grid, territories) if s is not None]
    assert signatures == [tuple(sorted(names)) for names in expected]
    assert any(signatures), (
        "the grid must land inside something for this to mean anything"
    )


def test_a_record_set_with_no_usable_coordinate_has_no_signature() -> None:
    off_map = (
        Record(
            object_id=1,
            damage=None,
            incident=None,
            county=None,
            year=None,
            lon=10.0,
            lat=50.0,
        ),
    )
    territories, _ = load_territories(
        {
            "a": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "OBJECTID": 1,
                            "Utility": "Somewhere Electric",
                            "Type": "IOU",
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [-121.0, 38.0],
                                    [-120.0, 38.0],
                                    [-120.0, 39.0],
                                    [-121.0, 39.0],
                                    [-121.0, 38.0],
                                ]
                            ],
                        },
                    }
                ],
            }
        }
    )
    assert containment_signatures(off_map, territories) == (None,)


def test_a_row_missing_a_column_is_refused_not_read_as_a_value() -> None:
    rows: list[dict[str, Any]] = [{"OBJECTID": 1, "DAMAGE": "No Damage"}]
    with pytest.raises(SchemaError, match="HAZARDTYPE"):
        assert_columns(rows)


def test_an_empty_retrieval_is_refused() -> None:
    with pytest.raises(SchemaError, match="no rows"):
        assert_columns([])


def test_read_records_refuses_a_file_without_the_hazard_column() -> None:
    rows = [
        {
            "OBJECTID": 1,
            "COUNTY": "Sample County East",
            "DAMAGE": "No Damage",
            "INCIDENTNAME": "X",
            "INCIDENTSTARTDATE": 0,
            "LATITUDE": 38.0,
            "LONGITUDE": -121.0,
        }
    ]
    with pytest.raises(SchemaError):
        read_records(rows)


def test_a_non_numeric_coordinate_is_refused_rather_than_coerced() -> None:
    rows = [
        {
            "OBJECTID": 1,
            "COUNTY": "Sample County East",
            "DAMAGE": "No Damage",
            "HAZARDTYPE": "Fire",
            "STRUCTURECATEGORY": "Single Residence",
            "INCIDENTNAME": "X",
            "INCIDENTSTARTDATE": 1_600_000_000_000,
            "LATITUDE": "38.0",
            "LONGITUDE": True,
        }
    ]
    kept, _ = read_records(rows)
    assert kept[0].lat is None and kept[0].lon is None
    assert not kept[0].has_usable_coordinate


def test_a_missing_start_date_leaves_the_year_unknown_rather_than_guessed() -> None:
    rows = [
        {
            "OBJECTID": 1,
            "COUNTY": "Sample County East",
            "DAMAGE": "No Damage",
            "HAZARDTYPE": "Fire",
            "STRUCTURECATEGORY": "Single Residence",
            "INCIDENTNAME": "X",
            "INCIDENTSTARTDATE": None,
            "LATITUDE": 38.0,
            "LONGITUDE": -121.0,
        }
    ]
    kept, _ = read_records(rows)
    assert kept[0].year is None


def test_the_county_is_read_from_the_publishers_own_field(
    placement: Placement,
) -> None:
    """Two invented counties in the fixture, and two records the cell is empty on."""
    assert dict(placement.counties) == {
        "Sample County East": 6,
        "Sample County West": 4,
    }
    assert placement.records_with_no_county == 2
    assert (
        sum(placement.counties.values()) + placement.records_with_no_county
        == placement.fire_records
    )


def test_an_empty_county_cell_is_absent_rather_than_a_county_called_nothing() -> None:
    """A null and an empty string are the same fact: nobody recorded a county."""
    rows: list[dict[str, Any]] = [
        {
            "OBJECTID": oid,
            "COUNTY": value,
            "DAMAGE": "No Damage",
            "HAZARDTYPE": "Fire",
            "STRUCTURECATEGORY": "Single Residence",
            "INCIDENTNAME": "X",
            "INCIDENTSTARTDATE": 0,
            "LATITUDE": 38.0,
            "LONGITUDE": -121.0,
        }
        for oid, value in ((1, None), (2, ""), (3, "  "), (4, " Napa "))
    ]
    kept, _ = read_records(rows)
    assert [r.county for r in kept] == [None, None, None, "Napa"]


def test_the_county_split_counts_only_records_that_got_an_outcome(
    placement: Placement,
) -> None:
    for name, contested in placement.county_contested.items():
        assert contested <= placement.county_classified[name]
    assert sum(placement.county_classified.values()) <= placement.classified
    for name, classified in placement.county_classified.items():
        assert classified <= placement.counties[name]


def _square_feature(oid: int, name: str, kind: str, ring: list[list[float]]) -> dict:
    return {
        "type": "Feature",
        "properties": {"OBJECTID": oid, "Utility": name, "Type": kind},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def _ring(w: float, s: float, e: float, n: float) -> list[list[float]]:
    return [[w, s], [e, s], [e, n], [w, n], [w, s]]


def _classify_two(
    left: dict, right: dict, points: list[tuple[float, float]]
) -> tuple[Placement, tuple[Territory, ...]]:
    collections = {
        "a": {"type": "FeatureCollection", "features": [left]},
        "b": {"type": "FeatureCollection", "features": [right]},
    }
    territories, _ = load_territories(collections)
    records = tuple(
        Record(
            i,
            "Destroyed (>50%)",
            f"INC-{i}",
            "Sample County East",
            2025,
            lon,
            lat,
        )
        for i, (lon, lat) in enumerate(points, start=1)
    )
    placement = classify(records, territories, 0)
    measure_boundary_distances(placement, territories)
    measure_contested_group_distances(placement, territories)
    return placement, territories


def test_a_thin_overlap_sits_wholly_inside_the_first_band() -> None:
    """A seam 0.001 degrees wide: every contested record is near an edge of the pair."""
    sliver_left = _square_feature(
        1, "Seam West", "IOU", _ring(-121.00, 38.00, -120.980, 38.02)
    )
    sliver_right = _square_feature(
        2, "Seam East", "POU", _ring(-120.981, 38.00, -120.970, 38.02)
    )
    placement, _ = _classify_two(
        sliver_left,
        sliver_right,
        [(-120.9805, 38.01), (-120.9806, 38.015)],
    )
    names = ("Seam East", "Seam West")
    assert placement.contested_groups[names] == 2
    state = placement.contested_distance_state[names]
    bands = placement.contested_bands[names]
    assert state == "measured"
    # The strip is roughly 90 meters wide, so both records sit within the 100 m band
    # of some edge in the combination.
    assert bands[100] == 2
    assert bands[1000] == 2


def test_an_interior_overlap_has_records_outside_every_band() -> None:
    """Deep overlap: a central record is over a kilometer from any edge involved."""
    deep_left = _square_feature(
        3, "Wide West", "IOU", _ring(-122.00, 37.00, -121.96, 37.04)
    )
    deep_right = _square_feature(
        4, "Wide East", "POU", _ring(-122.00, 37.00, -121.92, 37.04)
    )
    placement, _ = _classify_two(
        deep_left,
        deep_right,
        [(-121.98, 37.02), (-121.999, 37.02)],
    )
    names = ("Wide East", "Wide West")
    assert placement.contested_groups[names] == 2
    bands = placement.contested_bands[names]
    # The edge-hugging record sits within 100 m of the shared western edge; the
    # central one is more than a kilometer from every edge of either outline.
    assert bands[100] == 1
    assert bands[1000] == 1
    assert placement.contested_distance_state[names] == "measured"


def test_a_combination_holding_no_record_never_gains_a_band_row() -> None:
    """Only combinations that actually hold records reach the distance measurement."""
    lone = _square_feature(
        5, "Lone Rural", "CO-OP", _ring(-119.50, 38.00, -119.40, 38.10)
    )
    far = _square_feature(6, "Far North", "IOU", _ring(-121.00, 39.50, -120.90, 39.60))
    overlap_a = _square_feature(
        7, "Pair A", "IOU", _ring(-120.60, 38.20, -120.59, 38.30)
    )
    overlap_b = _square_feature(
        8, "Pair B", "POU", _ring(-120.595, 38.20, -120.58, 38.30)
    )
    collections = {
        "a": {"type": "FeatureCollection", "features": [lone, overlap_a]},
        "b": {"type": "FeatureCollection", "features": [far, overlap_b]},
    }
    territories, _ = load_territories(collections)
    records = (
        Record(1, "No Damage", "X", "Sample County East", 2025, -119.45, 38.05),
        Record(
            2, "Destroyed (>50%)", "Y", "Sample County East", 2025, -120.5925, 38.25
        ),
    )
    placement = classify(records, territories, 0)
    measure_contested_group_distances(placement, territories)
    assert ("Far North", "Lone Rural") not in placement.contested_groups
    assert set(placement.contested_bands) == {("Pair A", "Pair B")}


def _county(oid: int, name: str, ring: list[list[float]]):
    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": oid, "CDT_NAME_SHORT": name},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ],
    }
    return load_counties(collection)


def test_county_agreement_counts_agree_disagree_and_none() -> None:
    counties = _county(1, "East County", _ring(-120.5, 38.0, -119.7, 39.0))
    records = (
        Record(1, "No Damage", "X", None, 2025, -120.0, 38.4),
        Record(2, "No Damage", "X", "East County", 2025, -120.0, 38.4),
        Record(3, "No Damage", "X", "West County", 2025, -120.0, 38.4),
        Record(4, "No Damage", "X", "East County", 2025, -118.0, 38.4),
        Record(5, "No Damage", "X", "Ghost County", 2025, -120.0, 38.4),
        Record(6, "No Damage", "X", "East County", 2025, None, None),
    )
    result = classify_county_agreement(records, counties)
    # West County is a label the one-county layer does not carry, so it is counted as
    # unmatchable rather than guessed into an outcome.
    assert (result.resolved, result.agreed, result.disagreed) == (2, 1, 0)
    assert result.matched_no_county == 1
    assert result.unmatchable_label == 2
    tally = result.per_label["East County"]
    assert (
        tally.resolved,
        tally.agreed,
        tally.disagreed,
        tally.matched_no_county,
    ) == (2, 1, 0, 1)


def test_county_agreement_with_no_usable_records_is_all_zero() -> None:
    counties = _county(1, "East County", _ring(-120.5, 38.0, -119.7, 39.0))
    records = (Record(1, "No Damage", "X", "East County", 2025, None, None),)
    result = classify_county_agreement(records, counties)
    assert result.resolved == 0 and not result.per_label


def test_a_county_feature_without_geometry_or_name_is_refused() -> None:
    broken = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": 1, "CDT_NAME_SHORT": "X"},
                "geometry": None,
            }
        ],
    }
    with pytest.raises(TerritoryLoadError, match="no geometry"):
        load_counties(broken)
    unnamed = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"OBJECTID": 1}}],
    }
    with pytest.raises(TerritoryLoadError, match="CDT_NAME_SHORT"):
        load_counties(unnamed)
