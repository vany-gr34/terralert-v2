# CHIRPS daily commune rainfall import

The batch uses all six audited annual NetCDF files and the existing 97
verified positive-area overlaps. See the [annual audit](CHIRPS_2015_2020_AUDIT.md)
for file provenance and the [spatial verification](CHIRPS_SPATIAL_WEIGHTS.md)
for the WGS 84 grid interpretation and EPSG:6933 area method.

## Reproduce

With the audited files and the verified weights JSON in `/tmp`, run:

```sh
sha256sum /tmp/CHIRPS_v3_TERRALERT_20{15,16,17,18,19,20}.nc
python3 import_chirps_daily.py /tmp /tmp/terralert-chirps-weights.json
```

The importer verifies every checksum, compares both grid axes exactly
with the audited 2020 grid, and checks the product metadata and dates.
It reuses the same weights for every date. Numeric zeros remain valid.
Masked cells contribute no area or rainfall to the weighted mean. If
there is no valid overlap the mean is SQL NULL. Footprint coverage and
valid rainfall coverage are calculated separately relative to the full
commune area.

The importer stages and validates the complete commune-date-checksum set
within a single transaction. A changed row with an audited source version
aborts the transaction and reports the conflicting keys and values, with
one exception for the exact previously verified Bni Makada sample.
Identical rows are left in place by the upsert.

## Observed results

The first run staged 24,112 rows and inserted or updated 24,112 rows.
No unexpected conflicts were reported. Bni Makada on 2020-01-06 changed
from `0.347611749276656327175544` to `0.347613591974992` mm/day, with
both coverage fractions equal to 1. The sample comparison uses an
absolute tolerance of `1e-12 mm/day` to allow for numeric rounding.

The query below returned 24,112 rows, 2,192 dates for each of 11 communes,
and zero gaps or duplicates. The date range was 2015-01-01 to 2020-12-31.
Both February 29 dates had 11 rows each. There were 10,178 zero rainfall
rows and no NULL rainfall rows in these inputs. The series digest was
`cda81869b834b28e64e8c5f99d84e06c`.

The second import staged 24,112 rows and inserted or updated zero.
SQL output matched exactly before and after the rerun, including the
series digest. The 11 commune rows and 3 weather rows matched their
previous digests `fc4c34a732bbf95d4e69c97f03c9a14b` and
`369c6283837fe6258eb5254af1fd093e`.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
WITH audited AS (
  SELECT * FROM public.chirps_daily_commune_rainfall
  WHERE product_variant = 'CHIRPS v3 Final SAT'
    AND source_sha256 = ANY (ARRAY[
      '60efa742e49c8476445856e1635d79680b909711c787ff1f17f3b0147fa39e3d',
      '43e17f38afc9a96f781bab53637fe4d8db0d150f157eda8bc17e3e35b9b61a38',
      'fd4b695bd39e50baa9fce1da35e4645bc523b4b612de9fbc262845980a8bbe1c',
      '844af667ec89df9e60b1aea7c2ae2b993cda5c17d8c3d8aca86d0d38aee309d3',
      '51c5608fd88ea27295c91fad5a381b54dfb5c94dacd01730e4668b64cd96a119',
      '7b128c8a98de510f7abfca29f80265b4e410bf4e294d72ebed4e674e0c0d92f8'
    ])
), gaps AS (
  SELECT c.commune_id, d.day::date
  FROM public.pilot_communes c CROSS JOIN generate_series(
    timestamp '2015-01-01', timestamp '2020-12-31', interval '1 day'
  ) d(day)
  EXCEPT SELECT commune_id, rainfall_date FROM audited
)
SELECT count(*) AS rows, count(DISTINCT commune_id) AS communes,
       count(DISTINCT rainfall_date) AS dates, min(rainfall_date), max(rainfall_date),
       count(*) - count(DISTINCT (commune_id, rainfall_date)) AS duplicates,
       (SELECT count(*) FROM gaps) AS gaps,
       count(*) FILTER (WHERE rainfall_date = '2016-02-29') AS leap_2016,
       count(*) FILTER (WHERE rainfall_date = '2020-02-29') AS leap_2020,
       count(*) FILTER (WHERE rainfall_mm_per_day = 0) AS zero_rows,
       count(*) FILTER (WHERE rainfall_mm_per_day IS NULL) AS null_rows,
       md5(string_agg(row_to_json(audited)::text, '' ORDER BY commune_id, rainfall_date, source_sha256)) AS digest
FROM audited;
SELECT commune_id, count(DISTINCT rainfall_date) AS dates
FROM public.chirps_daily_commune_rainfall
GROUP BY commune_id ORDER BY commune_id;
SELECT *, abs(rainfall_mm_per_day - 0.347613591974992) <= 1e-12 AS sample_matches
FROM public.chirps_daily_commune_rainfall
WHERE commune_id = 'MA-01-511-0103' AND rainfall_date = '2020-01-06';
SELECT 'communes' AS dataset, count(*), md5(string_agg(row_to_json(c)::text, '' ORDER BY commune_id)) AS digest
FROM public.pilot_communes c
UNION ALL
SELECT 'weather', count(*), md5(string_agg(row_to_json(w)::text, '' ORDER BY id))
FROM public.weather_forecasts w;
ROLLBACK;
SQL
```
