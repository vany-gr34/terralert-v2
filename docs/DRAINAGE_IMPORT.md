# TERRALERT drainage import

The importer loads the audited Clean river network into `public.pilot_rivers`
using the GeoPackage FID as its key. It loads the five supplied pilot-area
catchment polygons into `public.pilot_catchments` keyed by `HYBAS_ID`.
Each row records the source Drive URL, SHA-256, source SRID, and original
nongeometry attributes. Both layers retain their supplied coordinates.
The catchment geometries represent the supplied pilot-area subsets.
Their source attributes do not establish the full upstream footprints.
The Raw `rivers_traced.gpkg` remains a provenance reference. [Drainage audit](DRAINAGE_AUDIT.md)

The importer checks both hashes and layer declarations before connecting
to PostgreSQL. It applies the migration, stages both layers, checks counts,
keys, geometry validity and distinctness, and compares existing rows with
the staged content. Any conflict aborts the transaction. Both layers
commit together, and exact matches are left in place.

## Commands

From the project folder with the local Compose database running:

```sh
sha256sum /tmp/terralert-drainage/{rivers_11_communes,bassin_versant_tanger}.gpkg
python3 import_drainage.py /tmp/terralert-drainage/rivers_11_communes.gpkg /tmp/terralert-drainage/bassin_versant_tanger.gpkg
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/check_drainage_import.sql > /tmp/terralert-drainage/import-first.txt
python3 import_drainage.py /tmp/terralert-drainage/rivers_11_communes.gpkg /tmp/terralert-drainage/bassin_versant_tanger.gpkg
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/check_drainage_import.sql > /tmp/terralert-drainage/import-rerun.txt
cmp /tmp/terralert-drainage/import-first.txt /tmp/terralert-drainage/import-rerun.txt
docker compose ps
```

The following SQL ran before the first import and after the rerun. The
outputs matched exactly.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SELECT 'communes' AS dataset, count(*), md5(string_agg(row_to_json(c)::text, '' ORDER BY commune_id)) AS digest
FROM public.pilot_communes c
UNION ALL
SELECT 'weather', count(*), md5(string_agg(row_to_json(w)::text, '' ORDER BY id))
FROM public.weather_forecasts w
UNION ALL
SELECT 'chirps', count(*), md5(string_agg(row_to_json(r)::text, '' ORDER BY commune_id, rainfall_date, source_sha256))
FROM public.chirps_daily_commune_rainfall r
UNION ALL
SELECT 'floods', count(*), md5(string_agg(row_to_json(f)::text, '' ORDER BY observation_id))
FROM public.historical_flood_observations f
ORDER BY dataset;
ROLLBACK;
SQL
```

## Observed results

| Layer | Rows / distinct keys | Valid, nonempty | Stored SRID | Content digest |
| --- | ---: | ---: | ---: | --- |
| Rivers | 123 / 123 | 123 | 26191 | `c4a4cf700401a29da6292937ca66e2a5` |
| Catchments | 5 / 5 | 5 | 4326 | `55b45f8ce175bb2cec38c39f80fc0e4f` |

Both hashes matched the audit. The first load staged and inserted 123
rivers and five catchments. The second load staged the same records and
inserted zero for both tables. The read-only output, including the
geometry and attribute digests, matched byte for byte.

| Commune ID | Commune | Geodesic length (m) |
| --- | --- | ---: |
| MA-01-511-0103 | Bni Makada | 3,894.832 |
| MA-01-511-0105 | Mghogha | 20,726.637 |
| MA-01-511-0106 | Souani | 4,861.640 |
| MA-01-511-0107 | Médina | 36,120.394 |
| MA-01-511-0109 | Gueznaia | 13,643.120 |
| MA-01-511-0303 | Aquouass Briech | 27,468.487 |
| MA-01-511-0501 | Al Manzla | 17,305.602 |
| MA-01-511-0505 | Sebt Azzinate | 32,352.749 |
| MA-01-511-0507 | Dar Chaoui | 24,864.824 |
| MA-01-511-0517 | Laaouama | 10,485.947 |
| MA-01-511-0519 | Hjar Ennhal | 25,635.460 |

All 11 results matched the audit's clipped-feature WGS 84 geodesic
calculation to 0.001 m at the displayed precision. The dissolved
pilot network measures **217,463.966 m in EPSG:26191**, reproducing the
audit's approximately 217.464 km with a 0.001 m tolerance. The same
dissolved network measures **217,359.693 m geodesically**.

The union of catchments intersects **710.895528 km²** of the
**710.985214 km²** pilot. Coverage was **99.9874%** with the audit's WGS
84 spheroidal area method. The SQL check allows 0.00005 percentage
points, half the last displayed digit.

| Existing table | Rows | Content digest before and after |
| --- | ---: | --- |
| Pilot communes | 11 | `fc4c34a732bbf95d4e69c97f03c9a14b` |
| Weather forecasts | 3 | `e8a77b70856798255bb49545d547b102` |
| CHIRPS rainfall | 24,112 | `cda81869b834b28e64e8c5f99d84e06c` |
| Historical floods | 103 | `fa646776b9bf179250051477958e9a00` |

The weather checksum here uses whole rows, including nullable batch
metadata columns. Docker Compose reported the database healthy and
showed only its internal `5432/tcp` port.
