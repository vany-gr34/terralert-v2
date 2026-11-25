# TERRALERT v2

Local ingestion and source-audit checkpoint for the 11-commune Tangier pilot.
The last completed milestone is the [NOAA/NCEI audit](docs/NCEI_WEATHER_AUDIT.md).
See [progress and paused work](docs/TERRALERT_INGESTION_PROGRESS.md),
[project context](PROJECT_CONTEXT.md), and the [ingestion plan](docs/DATA_INGESTION.md).

The 11-commune live Open-Meteo run and infrastructure audit remain pending.
The Meteostat comparison is paused because its CSV could not be downloaded.
Population staging is provisional; producer and reference year are unset.

## Local database setup

Requires Docker with Compose v2 and Python 3.10+ with system timezone data.
The weather, flood, drainage and population commands use the Python standard
library. CHIRPS scripts additionally require NumPy and netCDF4 in your Python
environment. The raster-audit commands document their own dependencies.
Raw datasets and the local database are not distributed in Git.

From the project folder, create the local configuration once.

```sh
cp .env.example .env
```

Set `POSTGRES_PASSWORD` to a local development password in `.env`, which
Git ignores. Then validate the configuration and start the database.

```sh
docker compose config --quiet
docker compose up -d --wait --wait-timeout 90
docker compose ps
```

Run a SQL query from inside the container. The database port is unpublished.

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database(), PostGIS_Version();"'
```

Compose starts one service using `postgis/postgis:17-3.5`, which pairs
PostgreSQL 17 with PostGIS 3.5. On an empty volume, the image creates
`POSTGRES_DB` and runs its bundled `/docker-entrypoint-initdb.d/10_postgis.sh`
script to enable PostGIS there. The health check waits for PostgreSQL to
accept TCP connections inside the container.

Docker stores database files in the named `postgres_data` volume mounted
at `/var/lib/postgresql/data`. Compose reattaches that volume when it
recreates the container.

To verify persistence, write a disposable row, recreate the container,
then read the row back and drop the probe table. The query should return
`id = 1`.

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN;
CREATE TABLE milestone1_persistence_probe (id integer PRIMARY KEY);
INSERT INTO milestone1_persistence_probe VALUES (1);
COMMIT;
SQL
docker compose up -d --force-recreate --wait --wait-timeout 90 db
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT id FROM milestone1_persistence_probe;
DROP TABLE milestone1_persistence_probe;
SQL
```

To stop the stack and preserve the volume, run `docker compose down`.

## Ingest the synthetic Tangier forecast

With the database running, apply the migration and run the CLI from the
project folder. The CLI uses Python 3's standard library and sends the
fixture to `psql` inside the database container.

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < migrations/001_weather_forecasts.sql
python3 ingest_weather_fixture.py fixtures/tangier_forecast.json
```

`COPY 1` confirms that one row was inserted. Each successful run appends a
row. Read the latest fixture back with its ingestion time displayed in UTC.

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SET TIME ZONE 'UTC';
SELECT id, source, is_fixture, ingested_at, jsonb_pretty(payload) AS payload
FROM weather_forecasts
WHERE is_fixture
ORDER BY id DESC
LIMIT 1;
SQL
```

Compare the payload with `fixtures/tangier_forecast.json`. Expect source
`synthetic_tangier`, marker `t`, a UTC timestamp from the import, and
precipitation values `[0, null, 1.25]`. JSONB preserves the values and array
order. PostgreSQL controls how object keys and whitespace are displayed.

## Ingest one live Open-Meteo forecast

With the database running and the migration applied, run this from the
project folder. It requires outbound HTTPS access to Open-Meteo.

```sh
python3 ingest_open_meteo.py
```

The command makes one forecast request for Tangier (35.76, −5.83) with
a 15-second HTTP timeout. It requests the current UTC hour plus 72
subsequent hours for precipitation, temperature, relative humidity, and
wind speed. After validating the response, it appends the full JSON as
`open_meteo` with `is_fixture=false`.

The command reads back the row using the ID assigned in its PostgreSQL
session, compares its entire JSONB payload with the response, and prints
the row ID, source, fixture flag, UTC ingestion time, units, forecast
range, and `payload_matches_response: true`. Each successful run adds a
row. To inspect the same row again, pass the ID printed by the command.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SET TIME ZONE 'UTC';
SELECT id, source, is_fixture, ingested_at,
       payload->'hourly_units' AS hourly_units,
       payload->'hourly'->'time'->>0 AS first_forecast_utc,
       payload->'hourly'->'time'->>-1 AS last_forecast_utc
FROM weather_forecasts
WHERE id = 3;
SQL
```

## Import the 11 pilot commune boundaries

Download [communes_11_fixed.gpkg](https://drive.google.com/file/d/1uGUh0gDd_YcM0NqmbQGLoaZ9ZgH1tkQh/view)
from the team Drive link in the ingestion plan. This is the inspected pilot
boundary file. Its SHA-256 is
`291e590994caad6cc5d4f53049609903dfb68ce40ca2498809bef0fa1675fc84`.
The `communes_11_fixed` layer declares 2D multipolygons in EPSG:32630
(WGS 84 / UTM zone 30N). Its `ISO` field supplies the 11 commune IDs.
PostGIS transforms the geometry to EPSG:26191 (Merchich / Nord Maroc),
the project's working CRS.

With Compose running, use Python 3 on Manjaro. The importer uses standard
library SQLite support and `psql` inside the Compose container.

```sh
sha256sum /path/to/communes_11_fixed.gpkg
python3 import_pilot_communes.py /path/to/communes_11_fixed.gpkg
```

The import checks the CRS and IDs, checks source and transformed geometry
in PostGIS, and commits all 11 rows together. A rerun updates rows by commune
ID. Run the following query before and after a rerun and compare the sorted
IDs. Expect 11 in each count and `{26191}` for the SRIDs.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT count(*) AS rows,
       count(commune_id) AS nonnull_ids,
       count(DISTINCT commune_id) AS distinct_ids,
       count(*) FILTER (WHERE ST_IsValid(geom) AND NOT ST_IsEmpty(geom)
                        AND GeometryType(geom) IN ('POLYGON', 'MULTIPOLYGON')) AS valid_nonempty_polygons,
       array_agg(DISTINCT ST_SRID(geom)) AS srids,
       array_agg(commune_id ORDER BY commune_id) AS ids
FROM public.pilot_communes;
SQL
```

## Ingestion commands and audit evidence

Use the linked milestone documents for exact source downloads, checksums,
command arguments and observed SQL results. Paths and command names below
remain those used during verification. Imports need the local Compose database
and the separately downloaded, audited sources; `/tmp` paths in audit docs are
local examples and may need to be recreated. Do not blindly apply all migrations:
`003_weather_forecast_batches.sql` requires the commune table first; the flood,
drainage and population importers apply their migrations transactionally.

| Area | Command or entry point | Evidence |
| --- | --- | --- |
| Pilot-wide weather sampling | `config/open_meteo_points_v1.csv`, `sql/export_open_meteo_points.sql` | [Sampling plan](docs/OPEN_METEO_SAMPLING_PLAN.md) |
| Manual forecast batch (live run pending) | `python3 ingest_open_meteo_batch.py` | [Batch checks and network diagnosis](docs/OPEN_METEO_BATCH.md) |
| CHIRPS sample and weights | `import_chirps_sample.py`, `verify_chirps_weights.py` | [2020 audit](docs/CHIRPS_2020_AUDIT.md), [six-year audit](docs/CHIRPS_2015_2020_AUDIT.md), [verified weights](docs/CHIRPS_SPATIAL_WEIGHTS.md) |
| Full CHIRPS import | `import_chirps_daily.py` | [Daily import](docs/CHIRPS_DAILY_IMPORT.md) |
| Flood preparation and import | `prepare_past_floods.py`, `import_past_floods.py` | [Source audit](docs/PAST_FLOODS_AUDIT.md), [import](docs/PAST_FLOODS_IMPORT.md) |
| Read-only flood/rainfall match | `sql/check_flood_chirps_matches.sql` | [Exploratory matches](docs/PAST_FLOODS_CHIRPS_MATCHES.md) |
| Terrain and land cover (audit only) | Commands embedded in audit docs | [Terrain](docs/TERRAIN_AUDIT.md), [land cover](docs/LAND_COVER_AUDIT.md) |
| Drainage import | `import_drainage.py`, `sql/check_drainage_import.sql` | [Audit](docs/DRAINAGE_AUDIT.md), [import](docs/DRAINAGE_IMPORT.md) |
| Provisional population | `import_population.py`, `sql/check_population_import.sql` | [Exposure audit and infrastructure blocker](docs/EXPOSURE_AUDIT.md), [population staging](docs/POPULATION_IMPORT.md) |
| NOAA/NCEI station audit | `scripts/audit_ncei_weather.py` | [NCEI audit](docs/NCEI_WEATHER_AUDIT.md) |

[Architecture](docs/Architecture.png) and [pipeline](docs/Pipeline.png) diagrams
show the planned platform, including later capabilities. Scheduling, risk
calculations, exposure calculations, merging and gap-filling remain later work.

## Local files and checkpoint checks

Keep `.env`, credentials, raw datasets, database dumps, caches and generated
outputs outside Git. `.env.example` deliberately has a blank password. The
versioned CSV is the 11-point sampling configuration; the weather fixture is
explicitly synthetic. Source links and hashes are recorded in audit docs.

See [checkpoint verification](docs/CHECKPOINT.md) for the checks rerun for this
checkpoint and the checks still blocked. Existing local data are preserved;
cloning this repository does not recreate the populated database automatically.
