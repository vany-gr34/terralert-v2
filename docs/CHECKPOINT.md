# TERRALERT v2 checkpoint through the NCEI audit

Checkpoint scope: completed code and audit evidence through NOAA/NCEI, with
population explicitly provisional. See [progress](TERRALERT_INGESTION_PROGRESS.md)
for the milestone history. The confirmed destination is `origin`,
`git@github.com:vany-gr34/terralert-v2.git`; SSH `git ls-remote origin` returned
`963c5c5ba273d740ab7477591d5bb6777bc1d354` for main before this checkpoint.
The original `oumaima-hahati/TERRALERT` repository remains a v1 reference.
The GitHub connector could not access the v2 repo (404); Git SSH access worked.

## Checks rerun for this checkpoint

```sh
git diff --check
git diff --cached --check
docker compose config --quiet
python3 -m compileall -q *.py scripts
PYTHONPATH=. python3 scripts/check_checkpoint.py
python3 scripts/audit_ncei_weather.py /tmp/NCEI_Tangier_2000_2025.csv --output /tmp/ncei-checkpoint
docker compose ps
```

- Compose validation and Python compilation passed.
- Offline checks passed: synthetic fixture zero/null preservation, malformed
  fixture rejected before storage, UTC forecast validation, 11 unique sampling
  IDs, one bounded transport retry, no retry on HTTP 429, and a mocked batch
  committing only after all responses succeed. A simulated fifth-commune
  failure invoked no write. HTTP and database writes are mocked in this check.
- NCEI source checksum matched. Rerun reproduced 430,097 records, 360,615
  usable unique timestamps and 8,507 eligible local days. Raw input and
  generated audit outputs remain local.
- Docker reports the database healthy; its port is not published to the host
  (`5432/tcp` is an internal exposed port, not a host mapping).
- A read-only SQL transaction returned database `terralert`, PostGIS
  `3.5 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`, and the counts below.

| Dataset | Rows |
| --- | ---: |
| Communes | 11 |
| Weather forecasts | 3 |
| CHIRPS daily commune rainfall | 24,112 |
| Historical flood observations | 103 |
| Rivers | 123 |
| Catchments | 5 |
| Provisional population with producer/year NULL | 11 |

The provisional population sum remained **1,424,783**. The checkpoint did not
rerun data imports or modify the database. Historical transactional and
idempotency results are recorded in their respective import documents.

## Explicitly pending

- The live Open-Meteo batch for all 11 communes is still unverified. Offline
  success does not establish live connectivity or a stored live batch.
- Critical-infrastructure audit remains blocked by unavailable source download.
- Meteostat comparison is paused because its CSV could not be downloaded;
  no added-day count or temperature comparison is claimed.
- Population producer/reference year remain unconfirmed. Terrain vertical
  provenance and land-cover product/year/legend limitations remain open.
- NCEI is audited, not imported. Scheduling, risk/exposure calculations, weather
  merging and gap-filling remain separate milestones.

## What stays local

`.env` and credentials, `.agents/` and `.codex/` settings, Python caches, raw
GeoPackages/NetCDF/rasters/CSVs, database files in the Compose named volume,
dumps, and `/tmp` audit downloads/results are excluded. Existing local files
are preserved. The sampling CSV and synthetic weather fixture are intentional
versioned inputs. Documentation source links and hashes carry provenance;
no expiring authenticated download URLs belong in Git.
