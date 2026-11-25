# TERRALERT exposure audit

Audit date: 2026-11-24. **Partially completed: population inspected; infrastructure acquisition blocked.** PostgreSQL was accessed only through `BEGIN READ ONLY` / `ROLLBACK`. No source geometries were repaired, no tables created, and nothing imported.

## Sources and import verdicts

| Source | SHA-256 | Verdict |
| --- | --- | --- |
| [population_26191.gpkg](https://drive.google.com/file/d/1pzBduO9JHhshw0hvJ2Gzge4BeAqFT593/view) | `a3b84589261744839d9815ac6d2c718dd42f953d7a50126d94679a18c416d89d` | Attribute join is technically ready using ISO and existing commune geometries; hold authoritative population use pending producer, reference year and definitions. Do not replace commune geometries with these polygons. |
| [critical_infrastructure.gpkg](https://drive.google.com/file/d/1oR2IsJrE5H_Ihwy3QFY3IB4Sb_jUDSdj/view) | Unavailable: no bytes downloaded | Hold import. Asset contents and spatial assignments remain unverified. |

### Population structure and provenance

The downloaded file is 163,840 bytes. SQLite inspection found one feature layer, `population_26191`, with 11 records and declared 2D MULTIPOLYGON geometry (`geom`, Z=0, M=0). Its spatial-reference table declares EPSG:26191, Merchich / Nord Maroc, horizontal metres. Observed geometries are all nonempty MultiPolygons. Declared extent is west/south/east/north `(444519.4835150826, 541094.8320036109, 473508.0090181293, 580638.1877723809)` metres.

`gpkg_contents.description` is empty; there are no `gpkg_metadata`, `gpkg_data_columns`, or layer-style tables. No producer, census reference year, licensing statement, or population-definition field is supplied. Drive metadata and `gpkg_contents.last_change` identify modification on 2026-11-22, **not a demographic reference year**. The ingestion plan explicitly asks for demographic source and year confirmation. HCP must not be assumed to be the producer merely because it is the platform's intended user.

Spatial granularity is one aggregate per commune polygon, not household points or a population grid. Fields are `fid`, `geom`, `ISO`, `nom_fr`, `nom_ar`, `P_ensemble`, `P_masculin`, `P_feminins`, `P_menages`, `s`, `Densite`, `classe_pop`. Field names suggest persons, male/female counts, households, area, density, and a class index; these are interpretations, not a supplied data dictionary. All three population counts are non-null, nonnegative integers. Male plus female equals total for every row. Totals are 1,424,783 overall, 723,204 male and 701,579 female.

`Densite = P_ensemble / (s / 1,000,000)` to maximum absolute error `7.105427357601002e-15`. This numerically supports a square-metre area denominator and persons/km² interpretation if the population units are confirmed. The stored `s` differs from projected geometry area by approximately 0.080344–0.112687%; its original calculation method is undocumented. Do not silently substitute a new denominator. `classe_pop` uses codes 1–5 without documented thresholds. Nine household values are NULL; only Aquouass Briech (1,190) and Gueznaia (25,039) are supplied. Missing households are not zero.

### Commune assignment and indicator comparison

Both population `fid` and `ISO` have 11 distinct, non-null values. All 11 ISO values join to exactly one `public.pilot_communes.commune_id`; there are no unmatched population IDs, no missing pilot IDs, and no ambiguous ID assignments. Commune names agree. The reference check returned `11 rows | 11 unique IDs | 0 missing IDs | SRID {26191} | all valid/nonempty true` with `transaction_read_only=on`.

| Commune ID | Commune | Population P_ensemble | Source polygon valid |
| --- | --- | ---: | --- |
| MA-01-511-0103 | Bni Makada | 567,326 | Yes |
| MA-01-511-0105 | Mghogha | 252,177 | No |
| MA-01-511-0106 | Souani | 110,723 | No |
| MA-01-511-0107 | Médina | 342,492 | Yes |
| MA-01-511-0109 | Gueznaia | 88,673 | No |
| MA-01-511-0303 | Aquouass Briech | 4,627 | Yes |
| MA-01-511-0501 | Al Manzla | 2,680 | Yes |
| MA-01-511-0505 | Sebt Azzinate | 7,263 | Yes |
| MA-01-511-0507 | Dar Chaoui | 4,469 | Yes |
| MA-01-511-0517 | Laaouama | 19,052 | Yes |
| MA-01-511-0519 | Hjar Ennhal | 25,301 | Yes |

All exact `ST_Equals` comparisons to stored boundaries return false. However, observed `ST_HausdorffDistance` is at most **0.000002088817 m** (Souani); the differences are numerically tiny, not evidence of a materially different commune footprint. This proximity does not make invalid polygons valid. PostGIS reports:

- Mghogha: `Self-intersection[463558.158467643 572363.73084238]`.
- Souani: `Self-intersection[460539.463670289 572369.621252196]`.
- Gueznaia: `Self-intersection[446952.331556193 554202.763707251]`.

Use the existing valid commune reference for any future spatial analysis; keep the supplied file intact as provenance. No repair was performed during this audit.

The existing copies of [commune_indicators.csv](https://drive.google.com/file/d/1NFXi2K1SM9tehEbkfSkrwtHzQL-6f43v/view) and [indicators_occupation.csv](https://drive.google.com/file/d/1mBqQFnbW0NiU9RcnQdr42OUrx2kEtXrP/view) each have 11 distinct matching ISO values. For every commune, `P_ensemble`, `P_masculin`, `P_feminins`, `s`, and `Densite` agree exactly with this GeoPackage, and `pop_total = P_ensemble`. Both sum to **1,424,783**, difference **0**. Their SHA-256 values are respectively `c09b0844c9ff60745d552394adc44ab7dcf9535f844899cd63c5db39fea01dae` and `ce2cd906363074ba3a343533cc8946c0a7178d5bb5113a6de614397d7a5cfe1a`.

This is an internal consistency comparison, not independent demographic validation: neither the GeoPackage nor these CSV headers establishes a common reference year or population definition. Nine missing household values are blank in the first CSV and literal `NULL` in the second. Those encodings must both remain missing. The indicators' `pop_km2` uses their separate `area_km2` denominator and should not be conflated with `Densite` based on `s`.

## Infrastructure: unresolved access blocker

The metadata lookup and authenticated raw-file fetch returned a connector transport error: `HTTP request failed` while sending to `https://chatgpt.com/backend-api/ps/mcp`. Direct download outside the sandbox timed out, then two bounded IPv4 attempts also timed out (`curl: (28) Connection timed out after 10001` / `10002 milliseconds`). No local copy was found in the project or `/tmp`; no downloaded file was created. This is an access failure, not proof that the source is empty or corrupt.

Consequently **checksum, layer names, declared CRS, geometry types, counts, provenance, asset categories, missing category values, duplicate IDs, outside-pilot features, and ambiguous assignments are all unverified**. There is no defensible observed count for any of them. The filename alone does not establish OpenStreetMap or another source, a capture date, licence, or completeness.

When access is restored, inspect all feature layers and metadata, check null/blank categories and duplicate asset identifiers (separate source IDs from GeoPackage fid), and compare geometries in the verified common CRS. For points, retain every commune satisfying `ST_Covers(commune.geom, point)`; report zero matches as outside and more than one as boundary/overlap ambiguity. For lines or polygons, report all intersected communes and crossing features instead of forcing one assignment. Compare explicit commune attributes with spatial matches. Absence of an asset type in the file does not demonstrate that the pilot lacks that type; completeness needs an inventory definition.

## Commands and reproduction

Run from the project root. Files stay in `/tmp`. The authenticated Drive metadata/fetch tools were attempted first using the two source IDs above and `download_raw_file=true, include_base64=false`; both fetches failed at transport. Initial sandbox curl failed DNS resolution. Outside the sandbox, population's ordinary request timed out; the following IPv4 command succeeded (163,840 bytes). The corresponding infrastructure command was run twice and failed as recorded above:

```sh
curl -4 -L --fail --connect-timeout 10 --max-time 30 'https://drive.google.com/uc?export=download&id=1pzBduO9JHhshw0hvJ2Gzge4BeAqFT593' -o /tmp/population_26191.gpkg
curl -4 -L --fail --connect-timeout 10 --max-time 30 'https://drive.google.com/uc?export=download&id=1oR2IsJrE5H_Ihwy3QFY3IB4Sb_jUDSdj' -o /tmp/critical_infrastructure.gpkg
```

The following Python inspection and SQL generator reproduce the population comparison without database writes. Save as `/tmp/audit_population.py`; the two previously audited CSV copies must be in `/tmp/terralert-drainage/`.

```python
import csv, hashlib, sqlite3
from pathlib import Path
from import_pilot_communes import geometry_wkb
p=Path('/tmp/population_26191.gpkg')
c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True); c.row_factory=sqlite3.Row
rows=list(c.execute('SELECT * FROM population_26191 ORDER BY ISO'))
print('SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
print('rows/unique/null ISO',len(rows),len({r['ISO'] for r in rows}),sum(not r['ISO'] for r in rows))
print('total/male/female',*[sum(r[k] for r in rows) for k in ('P_ensemble','P_masculin','P_feminins')])
print('missing households',sum(r['P_menages'] is None for r in rows))
print('sex sum discrepancies',sum(r['P_ensemble']!=r['P_masculin']+r['P_feminins'] for r in rows))
print('density formula max error',max(abs(r['Densite']-r['P_ensemble']/(r['s']/1e6)) for r in rows))
for name in ('commune_indicators.csv','indicators_occupation.csv'):
 refs=list(csv.DictReader(open('/tmp/terralert-drainage/'+name,encoding='utf-8-sig')))
 ref={r['ISO']:r for r in refs}
 fields=('P_ensemble','P_masculin','P_feminins','s','Densite')
 diffs=[(r['ISO'],k) for r in rows for k in fields if r[k]!=float(ref[r['ISO']][k])]
 print(name,'ID symmetric difference',set(ref)^set(r['ISO'] for r in rows),'field differences',diffs,'pop_total differences',sum(r['P_ensemble']!=int(ref[r['ISO']]['pop_total']) for r in rows))
vals=[]
for r in rows:
 vals.append("('%s',ST_GeomFromWKB(decode('%s','hex'),26191),%s)"%(r['ISO'].replace("'","''"),geometry_wkb(r['geom'],26191),r['s']))
sql="""BEGIN READ ONLY;
WITH source(iso,geom,s) AS (VALUES %s)
SELECT a.iso, p.name_fr, ST_IsValid(a.geom) AS valid, ST_IsValidReason(a.geom) AS validity_reason, ST_HausdorffDistance(a.geom,p.geom) AS hausdorff_m, ST_IsEmpty(a.geom) AS empty,
 ST_GeometryType(a.geom) AS type, ST_Equals(a.geom,p.geom) AS same_boundary,
 (SELECT count(*) FROM public.pilot_communes c WHERE ST_Equals(a.geom,c.geom)) AS equal_matches,
 round((ST_Area(a.geom)/a.s-1)::numeric*100,6) AS area_difference_pct
FROM source a LEFT JOIN public.pilot_communes p ON p.commune_id=a.iso ORDER BY a.iso;
ROLLBACK;
"""%(','.join(vals))
Path('/tmp/exposure_population.sql').write_text(sql)
```

```sh
PYTHONPATH=. python3 /tmp/audit_population.py
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /tmp/exposure_population.sql
```

Observed Python summary: `rows/unique/null ISO 11 11 0`; total/male/female `1424783 723204 701579`; `missing households 9`; `sex sum discrepancies 0`; both CSV comparisons returned empty ID/field differences and zero `pop_total` differences. SQL returned 11 rows, eight valid and three invalid source polygons, zero empty polygons, all MultiPolygon, and the geometry findings above.

## Decisions still needed

1. Population owner: supply producer, source publication/table, reference year, population definition (e.g. census residents versus estimate), licence, household completeness, area calculation method, and class thresholds. Matching existing indicator values does not answer these questions.
2. Infrastructure owner/access: restore access or provide the exact linked GeoPackage locally, then complete the checks before any import decision. Confirm inventory date, producer, licence, category dictionary, stable asset key and coverage expectations.

Stop here: no exposure import, demographic interpolation, or risk calculation was performed.
