# TERRALERT v2 — Data ingestion progress

**Updated 24 November 2026.** Pilot scope is 11 communes in Tanger–Assilah. Status is based on the reported Codex runs and their observed SQL and test results. Repository paths below are relative to `terralert-v2`.

## Checkpoint through NOAA/NCEI

Last completed milestone: the NOAA/NCEI station audit. The Meteostat comparison
is paused: the Drive file was identified, but download attempts timed out or
failed DNS/connector access. Its checksum, added usable days and temperature
comparison are unverified; no comparison report or import is claimed.

Population is staged provisionally (11 records, total 1,424,783, producer/year
NULL). The full 11-commune live Open-Meteo run and critical-infrastructure audit
remain blocked. No scheduling, risk calculations or weather gap-filling is
included in this checkpoint.

## Milestones

| Milestone | Status | Evidence and current scope |
|---|---|---|
| 1. Local infrastructure | Verified | Docker Compose started PostgreSQL with PostGIS 3.5. The `terralert` database returned its PostGIS version. A probe row survived container recreation and was cleaned up. The database port remained unpublished. |
| 2. Synthetic Tangier weather | Verified | The CLI stored the full JSON payload and fixture metadata. Readback preserved precipitation `[0, null, 1.25]`. Malformed JSON exited with an error and left the row count unchanged. |
| 3. Live Open-Meteo | Verified for one point | A manual request for Tangier (`35.76, -5.83`) stored row `3` with `is_fixture=false`. Readback matched the response and showed 73 hourly timestamps in UTC. A simulated network failure wrote zero rows. See milestones 6A and 6B for pilot-wide sampling and batch collection. |
| 4A. Pilot commune boundaries | Verified | `public.pilot_communes` contains 11 valid polygonal geometries with 11 unique commune IDs. The GeoPackage declares EPSG:32630, and PostGIS stores transformed geometries in EPSG:26191. A rerun reproduced the same IDs. |
| 4B. CHIRPS file audit | Verified for the six Drive files | CHIRPS v3 Final SAT, 2015–2020. All six 8 × 8 grids align exactly, with 2,192 consecutive dates, both leap days and full footprint coverage of the 11 communes under the documented WGS 84 assumption. The NetCDF files lack an explicit datum. Upstream lineage and values were not independently verified. |
| 4C. CHIRPS sample and spatial weights | Verified | The initial Bni Makada sample agreed with a separate calculation. Three geometries became invalid under direct equal-area projection. Densifying working copies resolved the issue while preserving the stored boundaries. Verification accepted 97 positive-area commune-to-cell overlaps for all 11 communes. |
| 4D. CHIRPS commune-day import | Verified | `public.chirps_daily_commune_rainfall` has 24,112 rows, 2,192 dates per commune, zero gaps, zero duplicates, 10,178 zero-rainfall rows and zero NULL rainfall rows. The batch updated the Bni Makada sample to `0.347613591974992 mm/day`. A rerun modified zero rows and preserved the commune and weather tables. |
| 5A. Historical flood inventory audit | Audit complete | The candidate `Raw/Floods/PAST_FLOODS.csv` has 103 unique observations across 18 events. Of 20 exact-date observations in the CHIRPS period, 19 were spatially ambiguous under the audit criteria. TF-0043 yielded one exploratory rainfall match. The audit ran read-only. |
| 5B. Flood inventory preparation and dry run | Verified | The raw SHA-256 matched the audit. The working copy changed only the notes header. All 103 observations, 18 event IDs and 42 fields per row were preserved. A tampered copy was rejected. |
| 5C. Local flood inventory import | Verified | `public.historical_flood_observations` contains 103 observations across 18 events. Readback matched all 42 fields and retained the original Drive link and SHA-256. A rerun inserted or updated zero rows. A conflicting `TF-0001` rolled back without changes. The weather, commune and CHIRPS table digests were unchanged. |
| 5D. Flood reports and CHIRPS integration | Verified | Read-only SQL reproduced the audit from the imported tables. Of 20 exact-date observations in the CHIRPS period, 19 were spatially ambiguous and one matched. TF-0043 matched Médina on 2016-11-21 with 28.160565805237763 mm/day, confidence B and 2,000 m recorded location precision. |
| 6A. Open-Meteo commune sampling | Verified | The versioned CSV contains 11 unique commune IDs and valid EPSG:4326 coordinates. All 11 rounded points were verified strictly inside their source communes in read-only PostGIS. Each point is a sampling location. |
| 6B. Manual Open-Meteo batch | Implemented and tested with mocked HTTP. Live check blocked. | The successful mocked run staged 11 rows for 11 unique communes before test rollback. A simulated network error and malformed response both left zero rows. Live attempts failed intermittently before HTTP and left zero rows. The isolated full request returned HTTP 200 in Python. With 3-second spacing and one retry on transient transport errors, the batch recovered at Mghogha and Souani but failed twice at Aquouass Briech (Errno 101). Simulations verified recovery after one timeout, no rows after retry exhaustion, and no retry on HTTP 429. All three preexisting weather rows remained intact. |
| Terrain audit | Completed with limitations | Matching DEM/slope grids and masks; DEM range 0–633, catalogue 596 discrepancy unresolved. Vertical datum/units and formal lineage remain unconfirmed. See `TERRAIN_AUDIT.md`. |
| Drainage audit and import | Verified | 123 river features and five catchment polygons; idempotent transactional import and unchanged existing tables. Catchments are pilot-area subsets. See `DRAINAGE_AUDIT.md` and `DRAINAGE_IMPORT.md`. |
| Land-cover audit | Completed; semantic import on hold | Numeric code counts match indicators. Code 0 is unmasked, but product/year/legend remain unresolved. See `LAND_COVER_AUDIT.md`. |
| Population and infrastructure audit | Population audited; infrastructure blocked | Population IDs match all 11 communes; source/year not confirmed. Infrastructure GeoPackage download failed; asset audit remains unverified. See `EXPOSURE_AUDIT.md`. |
| Population staging | Verified, provisional | 11 attribute-only records, population 1,424,783, nine household nulls preserved, producer/year NULL. Rerun changed zero rows; other tables unchanged. See `POPULATION_IMPORT.md`. |
| NOAA/NCEI station audit | Completed; no import | 430,097 rows, actual 2000-11-01–2025-08-01 UTC coverage, 360,615 usable timestamps and 8,507 eligible local days under the documented rule. Conflicting reports remain excluded from estimates. See `NCEI_WEATHER_AUDIT.md`. |
| Meteostat comparison | Paused, unverified | CSV unavailable after network failures. No added-day count or cross-archive comparison established. Resume only after obtaining and auditing the original. |

## Flood inventory checklist

- [x] Verify the raw CSV against the checksum in `docs/PAST_FLOODS_AUDIT.md`.
- [x] Preserve the raw file and rename `notes;;;;;;;` to `notes` in the working copy.
- [x] Dry-run the working copy. Verify that only the header changed, all 103 observations across 18 events were preserved, and a changed observation ID causes rejection.
- [ ] Confirm the canonical CSV with the data owner. The audited Raw/Floods copy was used for the local pilot.
- [x] Import the local pilot inventory. Verify all 103 observations against the prepared CSV, a zero-change rerun, and rollback on a conflicting ID.

**Exploratory match.** TF-0043 reports flooding in Rahrah on 2016-11-21, with confidence B. Under the audit’s location rule, it matched Médina (`MA-01-511-0107`) and a CHIRPS value of `28.160565805237763 mm/day`. This is commune-day rainfall context for a reported event. The precise inundation location remains unverified. [Original report](https://fr.le360.ma/societe/diapo-tanger-submergee-par-les-eaux-96411/)

## Later ingestion work

- Retry the manual Open-Meteo batch when the runtime can reach the API. Verify its exact run ID with `sql/check_open_meteo_batch.sql`. Confirm 11 unique communes, requested and returned coordinates, the forecast range, and any shared returned grid points before scheduling.
- Resume Meteostat acquisition/comparison and the critical-infrastructure audit when files are accessible. NCEI import, terrain/land-cover summaries and exposure calculations are later work. Drainage is imported; population is staged provisionally. Confirm the unresolved source definitions before analytical use.
- FIRMS/VIIRS, Sentinel-2, and any ERA5-Land supplement are later source-specific milestones.

## Evidence in the repository

| Area | Files |
|---|---|
| Infrastructure and weather | `README.md`, `ingest_weather_fixture.py`, `ingest_open_meteo.py`, `weather_storage.py` |
| Open-Meteo sampling points | `config/open_meteo_points_v1.csv`, `sql/export_open_meteo_points.sql`, `docs/OPEN_METEO_SAMPLING_PLAN.md` |
| Open-Meteo batch | `ingest_open_meteo_batch.py`, `sql/check_open_meteo_batch.sql`, `docs/OPEN_METEO_BATCH.md` |
| Pilot commune import | `README.md`, `import_pilot_communes.py` |
| CHIRPS | `docs/CHIRPS_2020_AUDIT.md`, `docs/CHIRPS_2015_2020_AUDIT.md`, `docs/CHIRPS_SPATIAL_WEIGHTS.md`, `docs/CHIRPS_DAILY_IMPORT.md` |
| Flood inventory | `docs/PAST_FLOODS_AUDIT.md`, `docs/PAST_FLOODS_IMPORT.md`, `prepare_past_floods.py`, `import_past_floods.py`, `migrations/002_historical_flood_observations.sql` |
| Flood and CHIRPS matching | `sql/check_flood_chirps_matches.sql`, `docs/PAST_FLOODS_CHIRPS_MATCHES.md` |
| Overall ingestion plan | [DATA_INGESTION.md](DATA_INGESTION.md) |
| Later audits and imports | `TERRAIN_AUDIT.md`, `LAND_COVER_AUDIT.md`, `DRAINAGE_AUDIT.md`, `DRAINAGE_IMPORT.md`, `EXPOSURE_AUDIT.md`, `POPULATION_IMPORT.md`, `NCEI_WEATHER_AUDIT.md` |

For each new run, record the status, what was checked, the observed result and the evidence file. Mark a milestone verified once its acceptance check has actually run.
