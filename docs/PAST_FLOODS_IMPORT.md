# Historical flood inventory import

The import uses the audited Raw/Floods CSV described in the [audit](PAST_FLOODS_AUDIT.md). The raw Drive link and SHA-256 are stored on each row. PostgreSQL keeps all 42 normalized CSV fields as strings in JSONB, including blanks, links, and uncertainty. `observation_id` is the unique key. The separate `event_id` column is derived from the payload and can repeat.

## Commands

```sh
python3 prepare_past_floods.py --dry-run /tmp/terralert-raw-PAST_FLOODS.csv /tmp/terralert-prepared-PAST_FLOODS.csv
python3 import_past_floods.py /tmp/terralert-prepared-PAST_FLOODS.csv
python3 import_past_floods.py --verify /tmp/terralert-prepared-PAST_FLOODS.csv
python3 import_past_floods.py /tmp/terralert-prepared-PAST_FLOODS.csv
python3 import_past_floods.py --verify /tmp/terralert-prepared-PAST_FLOODS.csv
```

If the prepared file is missing, recreate it with `python3 prepare_past_floods.py /tmp/terralert-raw-PAST_FLOODS.csv /tmp/terralert-prepared-PAST_FLOODS.csv` before running the dry run.

The importer applies `migrations/002_historical_flood_observations.sql`, stages and validates the batch, checks existing keys for conflicts, and inserts missing observations in one transaction. It reports conflicting observation IDs and rolls back. Verification reads the inventory through PostgreSQL and compares all stored field names and values with the parsed CSV, including the provenance.

## SQL checks

The preservation query ran before import and after the second import. The inventory query ran after each import.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SELECT 'weather' AS dataset, count(*), md5(string_agg(row_to_json(w)::text, '' ORDER BY id)) AS digest FROM public.weather_forecasts w
UNION ALL
SELECT 'communes', count(*), md5(string_agg(row_to_json(c)::text, '' ORDER BY commune_id)) FROM public.pilot_communes c
UNION ALL
SELECT 'chirps', count(*), md5(string_agg(row_to_json(r)::text, '' ORDER BY commune_id, rainfall_date, source_sha256)) FROM public.chirps_daily_commune_rainfall r
ORDER BY dataset;
SELECT count(*) AS observations, count(DISTINCT observation_id) AS unique_ids,
       count(DISTINCT event_id) AS events, min(source_url) AS source_url,
       min(source_sha256) AS source_sha256,
       md5(string_agg(row_to_json(f)::text, '' ORDER BY observation_id)) AS digest
FROM public.historical_flood_observations f;
ROLLBACK;
SQL
```

The import first reported `Staged 103 observations; inserted 103; updated 0.` The rerun reported `Staged 103 observations; inserted 0; updated 0.` Both CSV comparisons matched all 42 fields for all observations. SQL returned 103 rows, 103 unique observation IDs, and 18 distinct events. The recorded [Drive source](https://drive.google.com/file/d/1x9T9luY4WFETdW5QknSqXC-8V8aEcw6p/view) matches the raw checksum `338324f793132fff83e3f1e303d08886ce184126fa84fae19f81fe268986d12f`.

| Table | Rows | Ordered content digest before and after rerun |
| --- | ---: | --- |
| Historical flood observations | 103 | `fa646776b9bf179250051477958e9a00` |
| Weather forecasts | 3 | `369c6283837fe6258eb5254af1fd093e` |
| Pilot communes | 11 | `fc4c34a732bbf95d4e69c97f03c9a14b` |
| CHIRPS daily commune rainfall | 24,112 | `cda81869b834b28e64e8c5f99d84e06c` |

An in-memory conflict probe changed only the staged `notes` value for `TF-0001`. PostgreSQL reported `Conflicting observation IDs: TF-0001`, and another readback confirmed all 103 original records still matched the CSV.
