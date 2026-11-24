# CHIRPS spatial weight verification

All 11 communes passed. The read-only verifier computed 97 positive-area commune-to-cell weights from the audited 2020 Final SAT grid. Each exported weight contains the zero-based grid row and column, overlap in square metres, and fraction of full commune area. Weights were written to a local JSON report.

## Geometry check

The three affected boundaries were valid in EPSG:26191. Direct transformation to EPSG:6933 produced these PostGIS results.

| Commune | Native validity | Direct EPSG:6933 validity reason | Native / 5 m / 1 m parts | 5 m minus 1 m area (m²) |
| --- | --- | --- | ---: | ---: |
| Mghogha | Valid Geometry | Self-intersection[-560075.879958551 4277261.08252646] | 2 / 2 / 2 | -0.000187 |
| Souani | Valid Geometry | Self-intersection[-562944.072316776 4277259.79751818] | 3 / 3 / 3 | -0.000285 |
| Gueznaia | Valid Geometry | Self-intersection[-577319.425245028 4260155.10286844] | 3 / 3 / 3 | -0.000279 |

The working method adds vertices along straight segments in the original metre-based CRS with `ST_Segmentize(geom, 5)`, then projects to EPSG:6933. Shorter chords approximate the transformed boundary more closely. This avoids topology repair and preserves the original polygon parts. At 100 m, Mghogha still self-intersected. All 11 working geometries and their 1 m reference geometries were valid. The finer subdivision of the same stored boundaries provides a convergence reference in the same equal-area CRS. [PostGIS ST_Segmentize](https://postgis.net/docs/ST_Segmentize.html) · [NSIDC equal-area grid](https://nsidc.org/data/user-resources/help-center/guide-ease-grids)

The acceptance tolerance was `max(0.01 m², full area × 10⁻⁹)` per commune. The 0.01 m² floor allows for numerical overlay and area-summation noise. The relative term scales the check for the larger boundaries while keeping it below 0.11 m² here. The verifier checks total area difference, symmetric-difference area, polygon-part counts, and closure of the summed overlaps. The largest absolute 5 m versus 1 m area difference was 0.000743 m². GEOS reported zero area for every symmetric difference. The largest overlap closure residual was 0.000000760 m². No difference exceeded the tolerance.

## Weight totals

The 2020 grid checksum matches the [audit](CHIRPS_2015_2020_AUDIT.md). Cell rectangles use the documented WGS 84 interpretation and are transformed to EPSG:6933 for intersection. Coverage is the sum of positive overlap areas divided by full commune area. The values below are rounded for display.

| Commune | Positive-area cells | Full area (m²) | Summed overlap (m²) | Footprint coverage |
| --- | ---: | ---: | ---: | ---: |
| Bni Makada | 5 | 35,860,218.21 | 35,860,218.21 | 1.000000 |
| Mghogha | 7 | 51,097,537.39 | 51,097,537.39 | 1.000000 |
| Souani | 1 | 5,071,394.18 | 5,071,394.18 | 1.000000 |
| Médina | 10 | 76,536,267.06 | 76,536,267.06 | 1.000000 |
| Gueznaia | 10 | 67,374,491.96 | 67,374,491.96 | 1.000000 |
| Aquouass Briech | 10 | 60,851,205.76 | 60,851,205.76 | 1.000000 |
| Al Manzla | 13 | 90,690,278.59 | 90,690,278.59 | 1.000000 |
| Sebt Azzinate | 10 | 66,422,107.94 | 66,422,107.94 | 1.000000 |
| Dar Chaoui | 10 | 97,579,811.90 | 97,579,811.90 | 1.000000 |
| Laaouama | 9 | 53,943,734.41 | 53,943,734.41 | 1.000000 |
| Hjar Ennhal | 12 | 105,558,162.69 | 105,558,162.69 | 1.000000 |

## Bni Makada regression and commands

The original 2020-01-06 sample reran at **0.3476117492766563 mm/day**. The new weights gave **0.347613591974992 mm/day**, a change of **+0.000001842698336 mm/day**. Both calculations used the same five cells, including two zeros. Densification changed how the projected boundary cuts those cells. For example, the wettest cell (row 2, column 3) had 152.21 m² more overlap, enough to slightly raise the weighted mean. The new full area is 157.41 m² larger than the original direct-projection area. The area tolerance measures agreement with the finer reference, which uses the same boundary-segment interpretation.

```sh
sha256sum /tmp/CHIRPS_v3_TERRALERT_2020.nc
python3 verify_chirps_weights.py /tmp/CHIRPS_v3_TERRALERT_2020.nc > /tmp/terralert-chirps-weights.json
python3 import_chirps_sample.py /tmp/CHIRPS_v3_TERRALERT_2020.nc
```

The verifier runs the exact PostGIS validity, reference, and intersection checks in `inspect_weights` and exits unsuccessfully if a commune fails its acceptance checks. It does not write to PostGIS. The original sample command above runs without `--store`.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SELECT name_fr, ST_IsValidReason(geom) AS native,
       ST_IsValidReason(ST_Transform(geom, 6933)) AS direct
FROM public.pilot_communes
WHERE commune_id IN ('MA-01-511-0105','MA-01-511-0106','MA-01-511-0109');
SELECT 'communes' AS dataset, count(*), md5(string_agg(row_to_json(c)::text, '' ORDER BY commune_id)) AS digest FROM public.pilot_communes c
UNION ALL
SELECT 'weather', count(*), md5(string_agg(row_to_json(w)::text, '' ORDER BY id)) FROM public.weather_forecasts w;
SELECT * FROM public.chirps_daily_commune_rainfall;
ROLLBACK;
SQL
```

The 11 commune rows and 3 weather rows matched their previous content digests (`fc4c34a732bbf95d4e69c97f03c9a14b` and `369c6283837fe6258eb5254af1fd093e`, respectively). The one stored sample retained its original value of `0.347611749276656327175544` and both coverage fractions of `1.000000000000`.
