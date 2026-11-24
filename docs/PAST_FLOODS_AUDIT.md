# TERRALERT historical flood inventory audit

**Verdict.** The Raw/Floods copy is structurally suitable for a provenance-preserving inventory import after normalizing the malformed header in a working copy and confirming the source with the data owner, as recorded in the ingestion plan. It is not ready for an unrestricted commune-day join. One observation qualifies for an exploratory rainfall match under the recorded location-precision radius. The original provisional study-area flags and all other uncertainty fields should be retained.

## Source and schema

Audited [Raw/Floods PAST_FLOODS.csv](https://drive.google.com/file/d/1x9T9luY4WFETdW5QknSqXC-8V8aEcw6p/view), the candidate in the [ingestion plan](DATA_INGESTION.md). The independently shared copy with inconsistent row widths was excluded.

- File size 113,047 bytes. SHA-256 `338324f793132fff83e3f1e303d08886ce184126fa84fae19f81fe268986d12f`.
- Python's strict CSV parser, with `encoding="utf-8-sig"` and `newline=""`, read 103 observations and one header, all exactly 42 fields wide. Every observation ID is present and unique. All event IDs are present, with 18 distinct events across the 103 observations.
- The only header containing semicolons is the literal `notes;;;;;;;`. Normalize it to `notes` in a working copy. The two coordinate provenance fields are present.

```text
observation_id, event_id, event_name, event_start_date, event_end_date,
observation_date, event_time, date_precision, region, province, commune,
locality, neighborhood, road_or_landmark, latitude, longitude, x_merchich,
y_merchich, coordinate_reference_system, coordinate_method, location_precision_m,
inside_terralert_study_area, flood_observed, flood_type, observed_impact,
water_depth_m, flood_extent_available, observation_method, primary_source_name,
primary_source_url, source_publication_date, source_type, supporting_source_urls,
evidence_description, verification_status, confidence_level, geographic_uncertainty,
temporal_uncertainty, data_origin, notes;;;;;;;, coordinate_source_url, coordinate_quality
```

## Recorded uncertainty and provenance

| Field | Observed counts |
| --- | --- |
| Date precision | Day 78, range 19, event association unconfirmed 4, year 2 |
| Temporal uncertainty | Day known with onset usually unknown 73, dates approximated from source 26, provisional event-day association 4 |
| Missing observation date | 25. Every event time field is blank. |
| Location precision | 1,000 m for 36 web locality reference points, 2,000 m for 67 estimated representative points |
| Verification status | Source-described location with precise flooded geometry unverified 88, landmark geocoded with inundation location unverified 3, provisional and requiring event-place corroboration 12 |
| Confidence | B 91, C 12 |
| Flood observed | Yes 91, reported and needs confirmation 12 |
| Missing links | Primary source 0, supporting source 89, coordinate source 67 |

All 103 rows come from secondary news reports and retain the study membership value `provisional - commune polygon not supplied`. Every coordinate is recorded as EPSG:4326 and represents a locality or landmark. The source describes possible positional uncertainty of 1–2 km or greater. All rows say flood extent is unavailable. The 12 explicitly provisional records retain both their status and confidence C. All primary URLs use HTTP or HTTPS. Only the example article was opened in this audit.

## Eligibility for a CHIRPS commune-day match

1. Use a parseable `observation_date` with `date_precision=day` and the recorded day-known status. Exclude observations that require event-place corroboration. Preserve the five day-labelled records that also say their dates are approximate as uncertain, along with the 19 ranges, two year-only rows and four unconfirmed event associations. No event start, publication date, or assumed day was substituted for a recorded observation date.
2. Transform the recorded point from EPSG:4326 to the stored metre-based boundary CRS, EPSG:26191. A spatial match requires the point to be covered by exactly one pilot commune, the recorded 1,000 m or 2,000 m radius to reach only that commune, and the distance to its boundary to exceed the radius. Compare a populated `commune` field with the pilot name and reject disagreements. A blank commune can qualify based on the spatial check. Representative coordinates and estimated radii support a screening match only.
3. Join on the resulting commune ID and exact day and select the audited CHIRPS Final SAT version by annual checksum.

| Check | Result |
| --- | --- |
| Event starts before 2015 | 8 events, 38 observations |
| Event starts in 2015–2020 | 3 events, 20 observations |
| Event starts after 2020 | 7 events, 45 observations |
| Approximate or unconfirmed observation dates | 30, all associated with events outside the CHIRPS period |
| In-period exact-date candidates | 20. None had the explicit event-place corroboration flag. |
| Exact-date candidates with spatial ambiguity | 19. Each recorded radius reached multiple communes. TF-0049 also has a name/point conflict, with Laaouama recorded but its point in Bni Makada. |
| Eligible exploratory matches | 1, TF-0043 |

All 103 points fell inside one pilot polygon, but 100 recorded radii reached more than one commune. Of the three radii that reached only one pilot commune, two crossed its boundary toward land or water outside the pilot polygons. Only one radius was wholly contained. There were 68 blank commune labels and 11 disagreements between a populated label and its point across the full inventory. Those counts describe different uncertainty checks and overlap.

## Read-only example

**TF-0043 / E2016NOV21** records Rahrah on **2016-11-21**, confidence **B**. The reported location has a 2,000 m representative-point estimate, and the verification status remains `source-described location; precise flooded geometry not verified`. The point is 2,162.70 m from the boundary of **Médina (MA-01-511-0107)**, and no other pilot polygon is within the recorded radius. Le360 reported traffic disruption in Rahrah during the November 21 flooding. The article was published on November 22. [Original Le360 report](https://fr.le360.ma/societe/diapo-tanger-submergee-par-les-eaux-96411/)

PostgreSQL returned **28.160565805237763 mm/day**, with footprint and valid rainfall coverage both `1.000000000000`, for CHIRPS v3 Final SAT. This links a daily commune-area rainfall estimate to a reported observation. The CSV still flags study membership as provisional, and the actual positional uncertainty could exceed the recorded radius.

```sh
sha256sum /tmp/terralert-raw-PAST_FLOODS.csv
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
WITH p AS (
  SELECT ST_Transform(ST_SetSRID(ST_MakePoint(-5.865,35.758),4326),26191) AS geom
)
SELECT 'TF-0043' AS observation_id, c.commune_id, c.name_fr, r.rainfall_date,
       round(ST_Distance(ST_Boundary(c.geom),p.geom)::numeric,2) AS boundary_distance_m,
       r.rainfall_mm_per_day, r.footprint_coverage, r.valid_rainfall_coverage,
       r.product_variant, r.source_sha256
FROM public.pilot_communes c CROSS JOIN p
JOIN public.chirps_daily_commune_rainfall r ON r.commune_id = c.commune_id
WHERE c.commune_id = 'MA-01-511-0107' AND r.rainfall_date = '2016-11-21'
  AND r.product_variant = 'CHIRPS v3 Final SAT'
  AND r.source_sha256 = '43e17f38afc9a96f781bab53637fe4d8db0d150f157eda8bc17e3e35b9b61a38'
  AND ST_Covers(c.geom,p.geom) AND ST_Distance(ST_Boundary(c.geom),p.geom) > 2000;
ROLLBACK;
SQL
```

No inventory records were imported or changed.

## Prepare and verify a working copy

Run from the project folder with Python 3. The first command creates a
new local working copy and refuses to overwrite an existing file. The
second verifies an existing copy without writing either file or connecting
to PostgreSQL.

```sh
python3 prepare_past_floods.py /tmp/terralert-raw-PAST_FLOODS.csv /tmp/terralert-prepared-PAST_FLOODS.csv
python3 prepare_past_floods.py --dry-run /tmp/terralert-raw-PAST_FLOODS.csv /tmp/terralert-prepared-PAST_FLOODS.csv
```

The dry run passed for 103 unique observation IDs across 18 events.
The only byte change was removing the seven semicolons from the
`notes` header. Every observation byte and parsed field matched,
including source links and date, location, and verification flags.
The working copy SHA-256 is
`b3b292647b0b88cd81634785a20032a7e45923a6e1f533ebbd177f1896702831`.
