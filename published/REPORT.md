# Which published electric service territory is a burned structure in?

Unofficial. Not affiliated with, endorsed by, or approved by CAL FIRE, the
California Energy Commission, or any electric utility. This is descriptive
geography over two public datasets. It is not a risk rating of any company and
it contains no information about the location of anybody's infrastructure.

Damage inspections retrieved 2026-08-23. Territory boundaries
retrieved 2026-08-23, publisher item last modified
2026-08-12.

This document is generated. Every figure below is read from
`measurements.json`, which is produced by the same run.

## Can the join be made at all

The record set holds 132,520 wildfire damage-inspection
records. 2 records in the published file describe a
hazard other than fire and are excluded here rather than counted as wildfire.

| Outcome | Share | Records | Of | 95% interval |
|---|---:|---:|---:|---|
| placed in exactly one published territory | 62.1% | 82,353 | 132,520 | 61.9% to 62.4% |
| inside two or more published territories | 37.9% | 50,167 | 132,520 | 37.6% to 38.1% |
| inside no published territory | 0.0% | 0 | 132,520 | 0.000% to 0.003% |
| coordinate not usable | 0.0% | 0 | 132,520 | 0.000% to 0.003% |

A record inside two or more published territories is not awarded to either.
The publisher states that the boundaries are approximate and that not all
entities are represented, so public data does not say which entity such a
record belongs to, and this project does not decide on its behalf.

## Do the records that can be attributed look like the ones that cannot

| Population | Destroyed share | Destroyed | Inspected | 95% interval |
|---|---:|---:|---:|---|
| destroyed share among placed records | 53.0% | 43,609 | 82,353 | 52.6% to 53.3% |
| destroyed share among contested records | 53.4% | 26,780 | 50,167 | 52.9% to 53.8% |
| destroyed share among records in no published territory | not measured | 0 | 0 | not measured |

Difference, placed minus contested: -0.4% (-1.0% to 0.1%, Newcombe score).

The interval includes zero, so this comparison does not establish a difference between the two populations.

## The placed and contested populations, by structure class

The placed-versus-contested check from above, run again inside each structure
class CAL FIRE publishes. A difference confined to one class would hide inside
the aggregate; a difference spread across every class is sturdier than one
number. Classes in name order; none is compared against another.

| Structure class | Placed destroyed share | Contested destroyed share | Difference (Newcombe) |
|---|---:|---:|---|
| Agriculture | 42.9% | not measured | not measured |
| Infrastructure | 15.4% | 5.8% | 9.6% (5.2% to 13.3%) |
| Mixed Commercial/Residential | 28.0% | 25.7% | 2.3% (-9.9% to 12.4%) |
| Multiple Residence | 43.2% | 18.7% | 24.5% (20.3% to 28.7%) |
| Nonresidential Commercial | 41.0% | 34.9% | 6.0% (3.1% to 8.9%) |
| Other Minor Structure | 53.7% | 57.6% | -3.8% (-4.9% to -2.7%) |
| Single Residence | 54.3% | 54.4% | -0.1% (-0.8% to 0.5%) |

## Is the unattributable share a property of the data or of the fire

The headline is one number over the whole record set, which reads as a property
of the two datasets. It is mostly not. The published outlines overlap in
particular places, so whether a record is contested is largely settled by where
its fire burned.

Of 405 distinct incidents in the record set,
94.3% (91.6% to 96.2%) fall entirely on one side: every
classified record contested, or none of them. Those incidents hold
62.4%
of the records that carry an incident name.

| Incidents | Share | Incidents | Of | 95% interval |
|---|---:|---:|---:|---|
| incidents whose every classified record is contested | 7.2% | 29 | 405 | 5.0% to 10.1% |
| incidents no record of which is contested | 87.2% | 353 | 405 | 83.5% to 90.1% |
| incidents with records on both sides | 5.7% | 23 | 405 | 3.8% to 8.4% |

The same thing seen by year. The boundaries are one retrieval and are identical
for every row, so the movement down this column is where each year's fires
burned and not a change in the published boundaries. No trend is published.

| Incident year | Records | Classified | Contested share | 95% interval |
|---:|---:|---:|---:|---|
| 2013 | 279 | 279 | 0.0% | 0.0% to 1.4% |
| 2014 | 310 | 310 | 15.8% | 12.2% to 20.3% |
| 2015 | 3,192 | 3,192 | 0.2% | 0.1% to 0.5% |
| 2016 | 944 | 944 | 3.1% | 2.1% to 4.4% |
| 2017 | 12,757 | 12,757 | 60.5% | 59.7% to 61.4% |
| 2018 | 28,403 | 28,403 | 7.0% | 6.7% to 7.3% |
| 2019 | 2,108 | 2,108 | 86.6% | 85.1% to 88.0% |
| 2020 | 28,626 | 28,626 | 19.9% | 19.5% to 20.4% |
| 2021 | 12,253 | 12,253 | 0.0082% | 0.00% to 0.05% |
| 2022 | 3,009 | 3,009 | 11.8% | 10.7% to 13.0% |
| 2023 | 229 | 229 | 9.2% | 6.1% to 13.6% |
| 2024 | 8,117 | 8,117 | 32.1% | 31.1% to 33.1% |
| 2025 | 32,293 | 32,293 | 92.5% | 92.2% to 92.8% |

The same cut by county, from CAL FIRE's own county field. In name order, never
in size order, and no county is compared against another. This says where in
California the published outlines overlap: 52
counties are named in the record set, and
30 records carry no county name and are
left out of this cut alone.

The county cut carries the contested share and nothing else. A county is not a service territory and this is not a statement about who serves it: it says where in California the published outlines overlap each other. No damage rate is published for a county, for the same reason none is published for a territory.

| County | Records | Classified | Contested share | 95% interval |
|---|---:|---:|---:|---|
| Alameda | 120 | 120 | 0.8% | 0.1% to 4.6% |
| Alpine | 415 | 415 | 0.0% | 0.0% to 0.9% |
| Amador | 87 | 87 | 0.0% | 0.0% to 4.2% |
| Butte | 28,747 | 28,747 | 0.0% | 0.00% to 0.01% |
| Calaveras | 1,281 | 1,281 | 0.0% | 0.0% to 0.3% |
| Colusa | 52 | 52 | 0.0% | 0.0% to 6.9% |
| Contra Costa | 2 | 2 | 50.0% | 9.5% to 90.5% |
| El Dorado | 4,668 | 4,668 | 0.0% | 0.0% to 0.1% |
| Fresno | 2,984 | 2,984 | 0.0% | 0.0% to 0.1% |
| Glenn | 52 | 52 | 0.0% | 0.0% to 6.9% |
| Humboldt | 19 | 19 | 0.0% | 0.0% to 16.8% |
| Inyo | 20 | 20 | 0.0% | 0.0% to 16.1% |
| Kern | 1,478 | 1,478 | 0.0% | 0.0% to 0.3% |
| Kings | 1 | 1 | 0.0% | 0.0% to 79.3% |
| Lake | 3,215 | 3,215 | 0.0% | 0.0% to 0.1% |
| Lassen | 1,020 | 1,020 | 8.3% | 6.8% to 10.2% |
| Los Angeles | 34,464 | 34,464 | 94.0% | 93.8% to 94.3% |
| Madera | 761 | 761 | 0.0% | 0.0% to 0.5% |
| Mariposa | 1,182 | 1,182 | 0.0% | 0.0% to 0.3% |
| Mendocino | 937 | 937 | 0.0% | 0.0% to 0.4% |
| Merced | 3 | 3 | 0.0% | 0.0% to 56.1% |
| Modoc | 7 | 7 | 14.3% | 2.6% to 51.3% |
| Mono | 114 | 114 | 0.0% | 0.0% to 3.3% |
| Monterey | 699 | 699 | 0.0% | 0.0% to 0.5% |
| Napa | 6,320 | 6,320 | 0.2% | 0.1% to 0.3% |
| Nevada | 344 | 344 | 0.0% | 0.0% to 1.1% |
| Orange | 2,510 | 2,510 | 93.9% | 92.9% to 94.7% |
| Placer | 606 | 606 | 0.0% | 0.0% to 0.6% |
| Plumas | 3,593 | 3,593 | 0.0% | 0.0% to 0.1% |
| Riverside | 1,379 | 1,379 | 42.3% | 39.8% to 45.0% |
| Sacramento | 10 | 10 | 0.0% | 0.0% to 27.8% |
| San Benito | 42 | 42 | 2.4% | 0.4% to 12.3% |
| San Bernardino | 1,003 | 1,003 | 8.8% | 7.2% to 10.7% |
| San Diego | 1,114 | 1,114 | 45.4% | 42.5% to 48.4% |
| San Joaquin | 104 | 104 | 2.9% | 1.0% to 8.1% |
| San Luis Obispo | 110 | 110 | 0.0% | 0.0% to 3.4% |
| San Mateo | 207 | 207 | 0.0% | 0.0% to 1.8% |
| Santa Barbara | 376 | 376 | 0.0% | 0.0% to 1.0% |
| Santa Clara | 589 | 589 | 97.8% | 96.3% to 98.7% |
| Santa Cruz | 4,637 | 4,637 | 0.0% | 0.0% to 0.1% |
| Shasta | 3,790 | 3,790 | 0.0% | 0.0% to 0.1% |
| Siskiyou | 1,877 | 1,877 | 0.0% | 0.0% to 0.2% |
| Solano | 2,377 | 2,377 | 0.0% | 0.0% to 0.2% |
| Sonoma | 11,721 | 11,721 | 99.9% | 99.9% to 100.0% |
| Stanislaus | 243 | 243 | 18.9% | 14.5% to 24.3% |
| Tehama | 1,212 | 1,212 | 0.0% | 0.0% to 0.3% |
| Trinity | 572 | 572 | 0.0% | 0.0% to 0.7% |
| Tulare | 1,036 | 1,036 | 0.0% | 0.0% to 0.4% |
| Tuolumne | 352 | 352 | 0.0% | 0.0% to 1.1% |
| Ventura | 3,436 | 3,436 | 52.1% | 50.4% to 53.7% |
| Yolo | 278 | 278 | 0.0% | 0.0% to 1.4% |
| Yuba | 324 | 324 | 0.0% | 0.0% to 1.2% |

## Does the coordinate agree with the recorded county

CAL FIRE records a county name on every row, and this project reports it as
published. This section measures that field against an authoritative county
boundary layer rather than trusting it or correcting it: how often a record's
coordinate lands outside the county its publisher recorded. 132,490
of 132,520 records could be compared at all; the rest had no usable
coordinate or a county label the boundary layer does not carry, and they stay
in every other denominator in this project.

| Outcome | Share | Records | Of | 95% interval |
|---|---:|---:|---:|---|
| coordinate and recorded county agree | 100.0% | 132,459 | 132,490 | 99.97% to 99.98% |
| coordinate sits outside the recorded county | 0.0234% | 31 | 132,490 | 0.02% to 0.03% |
| comparable records whose coordinate reaches no county polygon | 0.0% | 0 | 132,490 | 0.000% to 0.003% |
| records whose COUNTY label the boundary layer does not carry | 0.0% | 0 | 132,520 | 0.000% to 0.003% |

Counted, never corrected. The boundary layer's publisher warns that its own
boundary errors will exist, so a disagreement is evidence that two published
sources differ and not a verdict on which one is right. No damage rate is
published for a county here either.

| County | Compared | Agreed | Matched no county | Disagreed share | 95% interval |
|---|---:|---:|---:|---:|---|
| Alameda | 120 | 120 | 0 | 0.0% | 0.0% to 3.1% |
| Alpine | 415 | 415 | 0 | 0.0% | 0.0% to 0.9% |
| Amador | 87 | 87 | 0 | 0.0% | 0.0% to 4.2% |
| Butte | 28,747 | 28,747 | 0 | 0.0% | 0.00% to 0.01% |
| Calaveras | 1,281 | 1,281 | 0 | 0.0% | 0.0% to 0.3% |
| Colusa | 52 | 52 | 0 | 0.0% | 0.0% to 6.9% |
| Contra Costa | 2 | 2 | 0 | 0.0% | 0.0% to 65.8% |
| El Dorado | 4,668 | 4,668 | 0 | 0.0% | 0.0% to 0.1% |
| Fresno | 2,984 | 2,984 | 0 | 0.0% | 0.0% to 0.1% |
| Glenn | 52 | 52 | 0 | 0.0% | 0.0% to 6.9% |
| Humboldt | 19 | 19 | 0 | 0.0% | 0.0% to 16.8% |
| Inyo | 20 | 20 | 0 | 0.0% | 0.0% to 16.1% |
| Kern | 1,478 | 1,478 | 0 | 0.0% | 0.0% to 0.3% |
| Kings | 1 | 1 | 0 | 0.0% | 0.0% to 79.3% |
| Lake | 3,215 | 3,210 | 0 | 0.2% | 0.1% to 0.4% |
| Lassen | 1,020 | 1,020 | 0 | 0.0% | 0.0% to 0.4% |
| Los Angeles | 34,464 | 34,464 | 0 | 0.0% | 0.00% to 0.01% |
| Madera | 761 | 761 | 0 | 0.0% | 0.0% to 0.5% |
| Mariposa | 1,182 | 1,181 | 0 | 0.1% | 0.0% to 0.5% |
| Mendocino | 937 | 937 | 0 | 0.0% | 0.0% to 0.4% |
| Merced | 3 | 3 | 0 | 0.0% | 0.0% to 56.1% |
| Modoc | 7 | 7 | 0 | 0.0% | 0.0% to 35.4% |
| Mono | 114 | 114 | 0 | 0.0% | 0.0% to 3.3% |
| Monterey | 699 | 699 | 0 | 0.0% | 0.0% to 0.5% |
| Napa | 6,320 | 6,315 | 0 | 0.1% | 0.0% to 0.2% |
| Nevada | 344 | 344 | 0 | 0.0% | 0.0% to 1.1% |
| Orange | 2,510 | 2,510 | 0 | 0.0% | 0.0% to 0.2% |
| Placer | 606 | 606 | 0 | 0.0% | 0.0% to 0.6% |
| Plumas | 3,593 | 3,593 | 0 | 0.0% | 0.0% to 0.1% |
| Riverside | 1,379 | 1,379 | 0 | 0.0% | 0.0% to 0.3% |
| Sacramento | 10 | 10 | 0 | 0.0% | 0.0% to 27.8% |
| San Benito | 42 | 42 | 0 | 0.0% | 0.0% to 8.4% |
| San Bernardino | 1,003 | 1,003 | 0 | 0.0% | 0.0% to 0.4% |
| San Diego | 1,114 | 1,114 | 0 | 0.0% | 0.0% to 0.3% |
| San Joaquin | 104 | 102 | 0 | 1.9% | 0.5% to 6.7% |
| San Luis Obispo | 110 | 109 | 0 | 0.9% | 0.2% to 5.0% |
| San Mateo | 207 | 207 | 0 | 0.0% | 0.0% to 1.8% |
| Santa Barbara | 376 | 376 | 0 | 0.0% | 0.0% to 1.0% |
| Santa Clara | 589 | 587 | 0 | 0.3% | 0.1% to 1.2% |
| Santa Cruz | 4,637 | 4,636 | 0 | 0.0216% | 0.0% to 0.1% |
| Shasta | 3,790 | 3,788 | 0 | 0.1% | 0.0% to 0.2% |
| Siskiyou | 1,877 | 1,877 | 0 | 0.0% | 0.0% to 0.2% |
| Solano | 2,377 | 2,377 | 0 | 0.0% | 0.0% to 0.2% |
| Sonoma | 11,721 | 11,716 | 0 | 0.0427% | 0.0% to 0.1% |
| Stanislaus | 243 | 241 | 0 | 0.8% | 0.2% to 3.0% |
| Tehama | 1,212 | 1,212 | 0 | 0.0% | 0.0% to 0.3% |
| Trinity | 572 | 572 | 0 | 0.0% | 0.0% to 0.7% |
| Tulare | 1,036 | 1,036 | 0 | 0.0% | 0.0% to 0.4% |
| Tuolumne | 352 | 350 | 0 | 0.6% | 0.2% to 2.0% |
| Ventura | 3,436 | 3,433 | 0 | 0.1% | 0.0% to 0.3% |
| Yolo | 278 | 278 | 0 | 0.0% | 0.0% to 1.4% |
| Yuba | 324 | 324 | 0 | 0.0% | 0.0% to 1.2% |

## Every published territory, in name order

Counts, and two within-territory shares. No damage rate is published for a
territory and no territory is ordered against another. The concentration
column is why: where one incident supplies most of a territory's records, a
territory-level damage rate would be a statement about that one fire.

A territory appears in more than one row of the contested count, because a
record inside three outlines is contested for all three.

| Territory | Type | Placed | Contested | Incidents | Largest incident share | Within 250 m of the edge | Geometry |
|---|---|---:|---:|---:|---|---|---|
| Aha Macav Power Service | Tribal | 0 | 0 | 0 | not measured | not measured | as_published |
| Alameda Power & Telecom | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Anza Electric Cooperative, Inc. | CO-OP | 305 | 0 | 11 | 39.0% | 5.2% | as_published |
| Azusa Light & Power | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Bear Valley Electric Service | IOU | 0 | 0 | 0 | not measured | not measured | as_published |
| Biggs Municipal Utilities | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Burbank Water & Power | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City and County of San Francisco - Hetch Hetchy Water and Power | POU | 0 | 4 | 0 | not measured | not measured | repaired |
| City of Anaheim Public Utilities Department | POU | 0 | 46 | 0 | not measured | not measured | as_published |
| City of Banning Electric Department | POU | 23 | 0 | 2 | 69.6% | 95.7% | as_published |
| City of Cerritos | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Corona Department of Water & Power | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Healdsburg Electric Department | POU | 0 | 69 | 0 | not measured | not measured | repaired |
| City of Industry | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Lompoc Electric Division | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Needles | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Palo Alto | POU | 0 | 0 | 0 | not measured | not measured | repaired |
| City of Pittsburg | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Riverside | POU | 0 | 42 | 0 | not measured | not measured | as_published |
| City of Shasta Lake | POU | 25 | 0 | 1 | 100.0% | 0.0% | as_published |
| City of Ukiah Electric Utilities Division | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| City of Vernon Municipal Light Department | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Colton Electric Utility Department | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Eastside Power Authority | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Glendale Water & Power | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Gridley Electric Utility | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Imperial Irrigation District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Kirkwood Meadows Public Utility District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Lassen Municipal Utility District | POU | 203 | 85 | 10 | 47.3% | 20.7% | as_published |
| Lathrop Irrigation District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Liberty Utilities | IOU | 1,512 | 0 | 2 | 73.8% | 5.0% | as_published |
| Lodi Electric Utility | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Los Angeles Department of Water & Power | POU | 18 | 9,794 | 2 | 77.8% | 0.0% | repaired |
| Merced Irrigation District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Metropolitan Water District of So. Cal | POU | 0 | 37,727 | 0 | not measured | not measured | repaired |
| Modesto Irrigation District | POU | 0 | 40 | 0 | not measured | not measured | as_published |
| Moreno Valley Utility | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Morongo Band of Mission Indians | Tribal | 0 | 0 | 0 | not measured | not measured | as_published |
| PacifiCorp | IOU | 1,957 | 1 | 32 | 22.9% | 0.9% | as_published |
| Pacific Gas & Electric Company | IOU | 65,865 | 12,285 | 271 | 35.9% | 0.4% | repaired |
| Pasadena Water & Power | POU | 0 | 1,880 | 0 | not measured | not measured | as_published |
| Plumas-Sierra Rural Electric Cooperative | CO-OP | 1,060 | 85 | 5 | 48.5% | 4.4% | as_published |
| Port of Oakland | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Port of Stockton | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Power and Water Resource Pooling Authority | POU | 0 | 12,310 | 0 | not measured | not measured | repaired |
| Rancho Cucamonga Municipal Utility | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Redding Electric Utility | POU | 399 | 0 | 2 | 99.7% | 21.6% | as_published |
| Roseville Electric | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Sacramento Municipal Utility District | POU | 10 | 0 | 2 | 60.0% | 0.0% | as_published |
| San Diego Gas & Electric | IOU | 608 | 620 | 8 | 73.4% | 0.0% | as_published |
| Shelter Cove Resort Improvement District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Silicon Valley Power | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Southern California Edison | IOU | 9,638 | 25,345 | 46 | 16.2% | 1.6% | repaired |
| Surprise Valley Electrification Corporation | CO-OP | 41 | 1 | 5 | 82.9% | 0.0% | as_published |
| Trinity Public Utilities District | POU | 574 | 0 | 5 | 50.5% | 0.0% | as_published |
| Truckee Donner Public Utilities District | POU | 0 | 0 | 0 | not measured | not measured | as_published |
| Turlock Irrigation District | POU | 115 | 0 | 1 | 100.0% | 19.1% | as_published |
| Valley Electrical Association | CO-OP | 0 | 0 | 0 | not measured | not measured | as_published |
| Victorville Municipal Utilities Services | POU | 0 | 0 | 0 | not measured | not measured | as_published |

## Where the published boundaries overlap

Counts of records falling inside each combination of published outlines. This
is a description of the boundary layer, not of any utility. The combinations
are listed by size because size is what is being reported.

The last column is the share of each combination's records sitting
within 250 meters of the nearest edge among the outlines involved. A
contested record stops being contested when any of them ceases to
contain it, so that is the edge an approximation error moves first; a
combination near 100% here is a thin seam between outlines, and one
near 0% is an interior region where two published territories genuinely
cover the same ground.

| Published outlines a record falls inside | Records | Within 250 m of an edge |
|---|---:|---:|
| Metropolitan Water District of So. Cal, Southern California Edison | 25,345 | 13.8% (13.4% to 14.2%) |
| Pacific Gas & Electric Company, Power and Water Resource Pooling Authority | 12,241 | 0.5% (0.4% to 0.6%) |
| Los Angeles Department of Water & Power, Metropolitan Water District of So. Cal | 9,794 | 7.5% (7.0% to 8.0%) |
| Metropolitan Water District of So. Cal, Pasadena Water & Power | 1,880 | 72.4% (70.4% to 74.4%) |
| Metropolitan Water District of So. Cal, San Diego Gas & Electric | 620 | 18.4% (15.5% to 21.6%) |
| Lassen Municipal Utility District, Plumas-Sierra Rural Electric Cooperative | 85 | 7.1% (3.3% to 14.6%) |
| City of Healdsburg Electric Department, Power and Water Resource Pooling Authority | 69 | 100.0% (94.7% to 100.0%) |
| City of Anaheim Public Utilities Department, Metropolitan Water District of So. Cal | 46 | 10.9% (4.7% to 23.0%) |
| City of Riverside, Metropolitan Water District of So. Cal | 42 | 2.4% (0.4% to 12.3%) |
| Modesto Irrigation District, Pacific Gas & Electric Company | 40 | 0.0% (0.0% to 8.8%) |
| City and County of San Francisco - Hetch Hetchy Water and Power, Pacific Gas & Electric Company | 4 | 75.0% (30.1% to 95.4%) |
| PacifiCorp, Surprise Valley Electrification Corporation | 1 | 0.0% (0.0% to 79.3%) |

## The published polygons, as they arrived

59 outlines were read as electric service
territories. 8 of them failed an OGC validity
check on retrieval and were repaired before any containment question was asked
of them, because an invalid polygon answers that question undefined rather than
refusing it. The repaired ones are named here and flagged in the table above.

- City and County of San Francisco - Hetch Hetchy Water and Power
- City of Healdsburg Electric Department
- City of Palo Alto
- Los Angeles Department of Water & Power
- Metropolitan Water District of So. Cal
- Pacific Gas & Electric Company
- Power and Water Resource Pooling Authority
- Southern California Edison

75,521 placed records, 91.7% of the placed total (91.5% to 91.9%), sit inside one of those
repaired polygons. A different repair would place a different set, so that
figure is the size of this project's exposure to the choice.

0 outlines could not be repaired into a testable
shape. Those are removed from the index and are not reported as holding
zero records.

Two published entity types are not read as service territories:

- **ADMIN**: A federal power marketing administration. The polygon is a marketing and transmission administration area, not a retail service territory.
- **CCA**: A community choice aggregator is defined at Public Utilities Code section 331.1 as a local government electricity buyers' programme, and section 366.2 leaves metering, billing and delivery with the electrical corporation. Its polygon overlays another entity's distribution footprint rather than being one, so counting a record into both would count it twice.

## What the repair is worth

All 3 repairs (`make_valid`, `buffer_zero`, `make_valid_structure`) run to completion over
the same records. 927 of 132,520 records, 0.7%
(0.66% to 0.75%), come out differently under at least one pair of
them. That count is a census of the disagreement and not an estimate
of it, and it bounds how much of the result the choice of repair can
move. The pairwise counts:

| Between | Records |
|---|---:|
| `buffer_zero` and `make_valid_structure` | 0 |
| `make_valid` and `buffer_zero` | 927 |
| `make_valid` and `make_valid_structure` | 927 |

The pair ADR 0007 documents in detail: 927
of 132,520 records, 0.7%
(0.66% to 0.75%), come out differently under `buffer_zero` than under `make_valid`.

| Under the repair used here | Under the alternative | Records |
|---|---|---:|
| contested between two or more | contested between two or more | 157 |
| placed in exactly one territory | contested between two or more | 770 |

What each repair places in total, over the whole record set, rather than
only the records whose outcome moved.

| Repair | Placed share | Placed | Of | 95% interval |
|---|---:|---:|---:|---|
| placed in exactly one published territory, under make_valid | 62.1% | 82,353 | 132,520 | 61.9% to 62.4% |
| placed in exactly one published territory, under buffer_zero | 61.6% | 81,583 | 132,520 | 61.3% to 61.8% |

Difference in the placed share: 0.6% (0.2% to 1.0%, Newcombe score). The same records are placed twice,
so that interval is the conservative bound.

No repair is correct. Each is an answer to a question the published
polygon does not answer, and the disagreement between them is the size of
the ambiguity the invalid geometry leaves behind. The default did not
move to gain this measurement; it was already `make_valid` under ADR 0007.

## What the inclusion rule is worth

Which published outlines count as a service territory is a judgment, and this is
the whole record set placed again under each way that judgment could have gone.
The first row is the rule this project uses. Nothing here chooses between them,
and the difference column is the conservative bound rather than the tight one,
because the same records are being measured twice.

The inclusion rule reads the publisher's Type field, and the publisher documents none of its values. As retrieved, the layer metadata carries no description on the Type field and no coded-value domain, the FGDC record carries no entity and attribute section, and no data dictionary is attached to either item. What each value means is therefore inferred from the value itself, which is why the rule is published with its sensitivity and why the README asks for a domain review.

| Inclusion rule | Outlines | Contested | Contested share | 95% interval | Difference from the rule as built | Inside no published territory |
|---|---:|---:|---:|---|---|---:|
| the rule as built | 59 | 50,167 | 37.9% | 37.6% to 38.1% | reference | 0 |
| without CO-OP | 55 | 50,081 | 37.8% | 37.5% to 38.1% | -0.1% (-0.4% to 0.3%) | 1,406 |
| without Tribal | 57 | 50,167 | 37.9% | 37.6% to 38.1% | 0.0% (-0.4% to 0.4%) | 0 |
| without CO-OP or Tribal | 53 | 50,081 | 37.8% | 37.5% to 38.1% | -0.1% (-0.4% to 0.3%) | 1,406 |
| with CCA read as a territory | 84 | 74,661 | 56.3% | 56.1% to 56.6% | 18.5% (18.1% to 18.9%) | 0 |
| with ADMIN read as a territory | 60 | 98,541 | 74.4% | 74.1% to 74.6% | 36.5% (36.2% to 36.9%) | 0 |
| every published type read as a territory | 85 | 119,704 | 90.3% | 90.2% to 90.5% | 52.5% (52.2% to 52.8%) | 0 |

A rule that drops an included type does not only move records out of the
contested column. It moves them into the last one, where they are published
as inside no published territory, which is a statement about coverage that
the dropped entity's own published polygon contradicts.

## The outlines that hold nothing

Whether a particular named entity in the published layer operates a retail
distribution system is the publisher's classification to make, and this project
does not make it. The narrower question can be answered with a count: could that
outline be moving a figure here?

35 of the 59 outlines read as service territories hold no
record at all. 0 records of 132,520 fall inside one of them
(0.000% to 0.003%). Placing the whole record set again with all of them
removed changes the outcome of 0 records
(0.000% to 0.003%), so no figure in this document depends on any of them.

- Aha Macav Power Service
- Alameda Power & Telecom
- Azusa Light & Power
- Bear Valley Electric Service
- Biggs Municipal Utilities
- Burbank Water & Power
- City of Cerritos
- City of Corona Department of Water & Power
- City of Industry
- City of Lompoc Electric Division
- City of Needles
- City of Palo Alto
- City of Pittsburg
- City of Ukiah Electric Utilities Division
- City of Vernon Municipal Light Department
- Colton Electric Utility Department
- Eastside Power Authority
- Glendale Water & Power
- Gridley Electric Utility
- Imperial Irrigation District
- Kirkwood Meadows Public Utility District
- Lathrop Irrigation District
- Lodi Electric Utility
- Merced Irrigation District
- Moreno Valley Utility
- Morongo Band of Mission Indians
- Port of Oakland
- Port of Stockton
- Rancho Cucamonga Municipal Utility
- Roseville Electric
- Shelter Cove Resort Improvement District
- Silicon Valley Power
- Truckee Donner Public Utilities District
- Valley Electrical Association
- Victorville Municipal Utilities Services

This is a count, not a classification. It does not establish that any of the outlines named here is or is not a retail service territory, and this project does not decide that; see ADR 0002 and ADR 0010. What it establishes is that the question cannot change a figure published here, because the outlines it would be asked about hold nothing.

## What this does not measure

- **Nothing about physical infrastructure.** No pole, conductor, substation, or
  circuit position is read, inferred, approximated, or published, from these
  sources or any other. An analysis that would need one is not built here.
- **No comparison between utilities.** A territory's damage figures are driven
  by which fires burned in it, and the concentration column shows how strongly.
  Nothing here says any utility is more or less exposed than any other.
- **No rate against population, housing, customers, or meters.** The record set
  is defined by fire and by state responsibility area. A denominator drawn from
  a differently defined population would not contain this numerator.
- **Coverage is not exposure.** A territory with few placed records may have
  burned little, may sit mostly outside the state responsibility area, or may
  have most of its records contested. These are different facts and this
  project does not merge them.
