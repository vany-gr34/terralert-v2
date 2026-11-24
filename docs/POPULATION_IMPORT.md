# Provisional population staging import

## Result and scope

Imported the audited attributes into `public.pilot_population`, keyed by a foreign key to `public.pilot_communes.commune_id`. The table has no geometry. All 11 non-geometry source fields (`fid`, `ISO`, `nom_fr`, `nom_ar`, `P_ensemble`, `P_masculin`, `P_feminins`, `P_menages`, `s`, `Densite`, `classe_pop`) are preserved in `attributes` JSONB, including JSON nulls. Numeric values are not recalculated. Use `public.pilot_communes` for geometry.

Every row records [the source GeoPackage](https://drive.google.com/file/d/1pzBduO9JHhshw0hvJ2Gzge4BeAqFT593/view), SHA-256 `a3b84589261744839d9815ac6d2c718dd42f953d7a50126d94679a18c416d89d`, `status='provisional'`, and a `staged_at` timestamptz. `producer` and `reference_year` are SQL NULL. The source and interpretation limitations in [EXPOSURE_AUDIT.md](EXPOSURE_AUDIT.md) still apply. No source polygons, infrastructure, or derived exposure calculations were imported.

## Files and transaction behavior

- `migrations/005_population.sql`: attribute table, commune foreign key, provenance, and provisional status.
- `import_population.py`: checks the exact file checksum, reads SQLite in read-only mode, stages the complete batch, validates all pilot IDs and the total, rejects conflicting records, inserts only absent records, and compares the committed readback with the source.
- `sql/check_population_import.sql`: repeatable read-only summary and commune join.

The importer applies the migration and imports under a single `psql --single-transaction -v ON_ERROR_STOP=1` invocation. A lock serializes writes to the population table. Source attributes and provenance are compared before insert and again before commit; conflicting IDs cause rollback, without replacing any row. Identical reruns leave values and `staged_at` unchanged. A separate Python readback compares every source attribute, including floats, strings, and nulls, and checks provisional status and unconfirmed provenance.

## Exact import and verification commands

Run from the project root with the audited file at the shown location. The database port stays unpublished; all database access uses Compose exec. Credentials are expanded only inside the container.

```sh
sha256sum /tmp/population_26191.gpkg
python3 import_population.py /tmp/population_26191.gpkg
python3 import_population.py /tmp/population_26191.gpkg
```

Observed checksum matched. First run:

```text
Staged 11; inserted 11; updated 0.
Verified 11 rows: all 11 source attribute fields match, total 1424783; 9 household nulls preserved; provisional, producer/year NULL.
```

Second run:

```text
Staged 11; inserted 0; updated 0.
Verified 11 rows: all 11 source attribute fields match, total 1424783; 9 household nulls preserved; provisional, producer/year NULL.
```

For a future read-only source comparison, run `python3 import_population.py /tmp/population_26191.gpkg --verify`.

Executed SQL check:

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/check_population_import.sql
```

```text
rows | unique_communes | population_total | missing_households | provisional_unconfirmed
  11 |              11 |          1424783 |                  9 |                      11
```

The second SELECT returned all 11 matching commune IDs and names with the same per-commune totals documented in the exposure audit. No check failed.

## Existing tables and rerun identity

Before the first import, and after the rerun, executed the following read-only fingerprint script. It hashes complete row content, including geometries and timestamps, in deterministic order; counts are checked separately. These hashes are operational equality checks, not source-file provenance hashes.

```sh
cat > /tmp/population_fingerprints.sql <<'SQL'
BEGIN READ ONLY;
SELECT format('SELECT %L AS table_name, count(*) AS rows, md5(coalesce(string_agg(md5(row_to_json(t)::text), %L ORDER BY md5(row_to_json(t)::text)), %L)) AS content_hash FROM %I.%I t;', tablename, '', '', schemaname, tablename)
FROM pg_tables WHERE schemaname='public' AND tablename <> 'pilot_population' ORDER BY tablename
\gexec
ROLLBACK;
SQL
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /tmp/population_fingerprints.sql > /tmp/population-before.txt
# Run the import and rerun between the two snapshots.
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /tmp/population_fingerprints.sql > /tmp/population-after.txt
diff -u /tmp/population-before.txt /tmp/population-after.txt
```

Observed: no diff, exit 0. Both snapshots:

```text
chirps_daily_commune_rainfall|24112|d8097afe3534f484be3f00f5b0947c4d
historical_flood_observations|103|c93f702b9d5bea3552a24639884082af
pilot_catchments|5|29b095425048330c9b5f16a4cbfeea5d
pilot_communes|11|af76c4fc0e40d773299498f365392b28
pilot_rivers|123|d9414b725536cba8aca89679bebccb7f
spatial_ref_sys|8500|7c38fdce04bf2f037682a661ee5fa2fb
weather_forecasts|3|1398a36cc16550ac408f6678117dd8c9
```

After the first import, then after the rerun, executed:

```sh
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL' > /tmp/population-first.txt
BEGIN READ ONLY;
SELECT count(*),md5(string_agg(row_to_json(t)::text,'' ORDER BY commune_id)) FROM public.pilot_population t;
ROLLBACK;
SQL
# Repeat after rerun with output redirected to /tmp/population-rerun.txt.
diff -u /tmp/population-first.txt /tmp/population-rerun.txt
```

Both returned `11|4fbcbfad428b292c57fca76b5d357218`; diff exit 0. Thus all staged content, including staging timestamps, remained identical. Existing commune and hazard-data content remained unchanged. Work stopped after the verified staging import.
