# TERRALERT drainage audit

**Verdict.** Use the Clean river GeoPackage for mapped-waterway commune summaries. It is already in the verified metric project CRS and its dissolved network is entirely inside the pilot. The Raw river copy is suitable as a provenance reference. Loading both as one network would double-count the mapped waterways. The catchment GeoPackage is suitable for import as **pilot-area catchment polygons** keyed by `HYBAS_ID`. Use the observed geometry for local overlap and retain the original attributes separately. Full upstream catchment footprints and the exact clipping workflow are unverified.

## Source and geometry checks

| Linked source | SHA-256 | Layer | Declared CRS | Type | Features |
| --- | --- | --- | --- | --- | ---: |
| [rivers_11_communes.gpkg, Clean](https://drive.google.com/file/d/1IDJY_2LA7eseL4A7FxKt1LLpGtOytZQ3/view) | `223fb53113d486b2562a6c64bd3dad974996fe679ba47df5014e9e6b9e41c6c3` | `rivers_11_communes` | EPSG:26191, Merchich / Nord Maroc | 2D MultiLineString | 123 |
| [rivers_traced.gpkg, Raw](https://drive.google.com/file/d/1gxk_bF8u0k72KNs0VlQFxcr_rQS0_d22/view) | `ba7996f38209364e368877172b9d148b696cc12e62cd514bc278db0fe6d70583` | `rivers` | EPSG:4326, WGS 84 | 2D MultiLineString | 123 |
| [bassin_versant_tanger.gpkg, Raw](https://drive.google.com/file/d/14BeykywLiji5IoZ_e2TWzwdniMVhcX2U/view) | `513c608a18d694687c9bb5b00e43c4dc70db54c986958c060f5fa09e83590cfa` | `bassin_versant_tanger` | EPSG:4326, WGS 84 | 2D MultiPolygon | 5 |

The layer CRS comes from the GeoPackage spatial-reference tables. The actual PostGIS geometry types match the declarations. Each layer has **zero null, empty, or invalid geometries**, **zero duplicate WKB geometries**, and **zero topologically equal feature pairs** under `ST_Equals`. The two Raw layers carry QGIS 3.34.4 metadata whose title, abstract, and lineage links are empty. The Clean file has no GeoPackage metadata table. The layer change times are November 20, 2026 for the Raw layers and November 22, 2026 for the Clean layer. [Raw folder](https://drive.google.com/drive/folders/1KaXVE6i5itVtWt9F_GI0c9PBjznaxSRi) · [Ingestion plan](DATA_INGESTION.md)

Both river layers have the same attributes by FID. Source-layer tags identify 110 features from `gis_osm_waterways_free` in a Morocco extract, five from a local Rmilat stream-vector layer, and eight with no source-layer tag. The OSM-tagged features include 82 streams, 21 rivers, and seven canals. The length below includes all mapped waterways. The attributes preserve source hints, but they do not document the Rmilat extraction method, a source for the remaining eight features, or a full processing history. The catchment schema and identifiers are consistent with HydroBASINS Africa level 08. Its packaging metadata does not establish the exact distribution version or clipping method. [HydroBASINS technical documentation](https://data.hydrosheds.org/file/technical-documentation/HydroBASINS_TechDoc_v1c.pdf)

## Mapped river length

PostGIS lists `+units=m` for EPSG:26191. The communes and Clean rivers already use that CRS, and the Raw rivers were transformed from EPSG:4326 before measurement. Each river network was dissolved with `ST_Union` before clipping. Only line components contribute to length. Feature-summed and dissolved lengths agree to well below a millimetre in each source.

The Raw and Clean networks have **217,463.966 m** each inside the pilot at millimetre precision. Clean has zero outside length and Raw has **0.190 m** outside. All 123 FIDs correspond. After reprojecting Raw, one paired geometry is exactly equal in coordinate order. The maximum paired Hausdorff distance is **0.0183 m** and the largest paired length difference is **0.0564 m**. This supports treating the two layers as versions of the same network. The Clean designation, native metric CRS, and exact pilot containment favor that file for summaries. The exact processing sequence is undocumented.

| Commune ID | Commune | Clean (m) | Raw (m) | Indicator `river_m` | Clean minus indicator (m) |
| --- | --- | ---: | ---: | ---: | ---: |
| MA-01-511-0103 | Bni Makada | 3,896.947 | 3,896.947 | 3,894.864 | +2.082 |
| MA-01-511-0105 | Mghogha | 20,738.210 | 20,738.210 | 20,726.665 | +11.544 |
| MA-01-511-0106 | Souani | 4,864.383 | 4,864.383 | 4,861.617 | +2.767 |
| MA-01-511-0107 | Médina | 36,140.578 | 36,140.578 | 36,120.548 | +20.030 |
| MA-01-511-0109 | Gueznaia | 13,649.971 | 13,649.971 | 13,643.166 | +6.805 |
| MA-01-511-0303 | Aquouass Briech | 27,479.856 | 27,479.856 | 27,468.615 | +11.242 |
| MA-01-511-0501 | Al Manzla | 17,312.315 | 17,312.315 | 17,305.587 | +6.728 |
| MA-01-511-0505 | Sebt Azzinate | 32,368.069 | 32,368.069 | 32,352.858 | +15.210 |
| MA-01-511-0507 | Dar Chaoui | 24,875.220 | 24,875.220 | 24,864.993 | +10.227 |
| MA-01-511-0517 | Laaouama | 10,491.084 | 10,491.084 | 10,486.064 | +5.019 |
| MA-01-511-0519 | Hjar Ennhal | 25,647.333 | 25,647.333 | 25,635.574 | +11.759 |

**Shared boundaries.** Intersecting the river lines with exact pairwise commune boundaries found zero positive-length shared segments in both layers. Point crossings contribute zero length. The polygons for Bni Makada and Mghogha overlap by 5.674 m², without a measurable contribution to duplicate river length. Commune totals would include a shared segment in every commune it lies on. The pilot-wide total uses a dissolved river network intersected once with the union of communes, so any shared length is counted once. Here the sum of the 11 commune lengths matches the pilot-wide total within 0.001 m.

**Indicator comparison.** Both indicator exports have the same 11 ISO IDs and identical `river_m`, `river_km`, and `river_n` values. Planar lengths exceed the published `river_m` by 2.082–20.030 m, or 0.0389–0.0569%. None crosses the audit screening threshold of 0.1% of the published length. Recalculating the same clipped line features as WGS 84 geography brings every difference below **0.170 m**, strong evidence that the small offset is a length-method effect. The exact indicator calculation settings are undocumented. [Commune indicators](https://drive.google.com/file/d/1NFXi2K1SM9tehEbkfSkrwtHzQL-6f43v/view) · [Occupation indicators](https://drive.google.com/file/d/1mBqQFnbW0NiU9RcnQdr42OUrx2kEtXrP/view)

## Catchment overlap

PostGIS intersected each supplied WGS 84 polygon with the union of the pilot communes and measured both the inside and directly differenced outside components on the WGS 84 spheroid. These areas describe the file's polygons.

| HYBAS_ID | Supplied area (km²) | Inside pilot (km²) | Outside pilot (m²) | Outside (%) |
| --- | ---: | ---: | ---: | ---: |
| 1080029770 | 5.483414 | 5.483405 | 9.180 | 0.00016741 |
| 1080029780 | 8.563770 | 8.563769 | 1.183 | 0.00001381 |
| 1080029790 | 473.072157 | 473.072089 | 68.058 | 0.00001439 |
| 1080029800 | 220.322734 | 220.322714 | 20.051 | 0.00000910 |
| 1080029810 | 3.453556 | 3.453550 | 6.066 | 0.00017565 |

The five polygons extend approximately **104.54 m²** outside the pilot in total. Their union covers **710.895528 km²** of the **710.985214 km²** pilot, or **99.9874%**. The near-total containment and the differences between supplied geometry area and stored `SUB_AREA` (for example, 5.483 km² versus 267.9 for `1080029770`) indicate that the supplied polygons are already local subsets. The complete upstream catchment areas outside the pilot cannot be inferred from the small outside portions of these geometries.

## Reproduce the checks

Save the five linked source files under `/tmp/terralert-drainage` using their Drive filenames. The commands below read GeoPackage metadata and WKB directly with Python SQLite, then stream the decoded geometries into read-only PostGIS queries. No tables are created.

```sh
cat > /tmp/terralert-drainage/gpkg-values.py <<'PY'
from hashlib import sha256
from pathlib import Path
import sqlite3
import sys

def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'

values = []
for item in sys.argv[1:]:
    kind, filename = item.split('=', 1)
    path = Path(filename).resolve()
    print(path.name, sha256(path.read_bytes()).hexdigest(), file=sys.stderr)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        layers = db.execute("""
            SELECT g.table_name, g.column_name, g.geometry_type_name, g.srs_id, g.z, g.m,
                   s.organization, s.organization_coordsys_id, s.srs_name,
                   c.last_change, c.description
            FROM gpkg_geometry_columns g JOIN gpkg_spatial_ref_sys s USING(srs_id)
            JOIN gpkg_contents c USING(table_name)
        """).fetchall()
        for layer, column, declared, srid, z, m, authority, code, crs, changed, desc in layers:
            print((layer, column, declared, srid, z, m, authority, code, crs, changed, desc),
                  file=sys.stderr)
            assert authority == 'EPSG' and srid == code and z == 0 and m == 0
            assert kind in ('clean', 'raw', 'basin')
            label = '"HYBAS_ID"' if kind == 'basin' else 'NULL'
            sql = f'SELECT fid,{label},{quote(column)} FROM {quote(layer)} ORDER BY fid'
            for fid, basin, blob in db.execute(sql):
                wkb = 'NULL::text'
                if blob is not None:
                    assert blob[:3] == b'GP\x00' and not blob[3] & 0x20
                    order = 'little' if blob[3] & 1 else 'big'
                    assert int.from_bytes(blob[4:8], order, signed=True) == srid
                    size = (0, 32, 48, 48, 64)[(blob[3] >> 1) & 7]
                    wkb = "'" + blob[8 + size:].hex() + "'"
                basin = 'NULL::bigint' if basin is None else str(int(basin))
                values.append(f"('{kind}',{int(fid)},{basin},{srid},{wkb})")
        print('SQLite tables and fields:', db.execute("""
            SELECT name, sql FROM sqlite_schema
            WHERE name IN (SELECT table_name FROM gpkg_geometry_columns)
               OR name LIKE 'gpkg_metadata%'
            ORDER BY name
        """).fetchall(), file=sys.stderr)
        if db.execute("SELECT 1 FROM sqlite_schema WHERE name='gpkg_metadata'").fetchone():
            print('metadata:', db.execute('SELECT md_standard_uri, metadata FROM gpkg_metadata').fetchall(),
                  file=sys.stderr)
print('WITH input(kind, fid, basin_id, srid, wkb) AS (VALUES')
print(',\n'.join(values))
print("), features AS MATERIALIZED (SELECT kind, fid, basin_id, wkb, ST_GeomFromWKB(decode(wkb,'hex'),srid) AS geom FROM input)")
PY
cd /tmp/terralert-drainage
python3 gpkg-values.py clean=rivers_11_communes.gpkg raw=rivers_traced.gpkg basin=bassin_versant_tanger.gpkg > features.sql
cd -
```

```sh
cat > /tmp/terralert-drainage/measure.sql <<'SQL'
, integrity AS (
    SELECT kind, count(*) AS features, array_agg(DISTINCT GeometryType(geom)) AS types,
           count(*) FILTER (WHERE geom IS NULL) AS null_geometries,
           count(*) FILTER (WHERE ST_IsEmpty(geom)) AS empty_geometries,
           count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid_geometries,
           count(wkb)-count(DISTINCT wkb) AS exact_duplicate_excess,
           (SELECT count(*) FROM features b JOIN features a
              ON a.kind=b.kind AND a.fid<b.fid AND a.geom && b.geom AND ST_Equals(a.geom,b.geom)
            WHERE b.kind=f.kind) AS topological_duplicate_pairs,
           ST_Extent(geom)::text AS declared_crs_extent
    FROM features f GROUP BY kind
), pilot AS MATERIALIZED (
    SELECT ST_Union(geom) AS geom FROM public.pilot_communes
), rivers AS MATERIALIZED (
    SELECT kind, fid, ST_Transform(geom, 26191) AS geom
    FROM features WHERE kind IN ('clean','raw')
), networks AS MATERIALIZED (
    SELECT kind, sum(ST_Length(geom)) AS additive_m, ST_Union(geom) AS geom
    FROM rivers GROUP BY kind
), network_stats AS (
    SELECT kind, additive_m, ST_Length(n.geom) AS dissolved_m,
           ST_Length(ST_CollectionExtract(ST_Intersection(n.geom, p.geom), 2)) AS pilot_m,
           ST_Length(ST_CollectionExtract(ST_Difference(n.geom,p.geom), 2)) AS outside_m
    FROM networks n CROSS JOIN pilot p
), communes AS (
    SELECT c.commune_id, c.name_fr, n.kind,
           ST_Length(ST_CollectionExtract(ST_Intersection(n.geom,c.geom),2)) AS length_m,
           (SELECT sum(ST_Length(ST_CollectionExtract(ST_Intersection(r.geom,c.geom),2)))
            FROM rivers r WHERE r.kind=n.kind AND r.geom && c.geom) AS feature_sum_m
    FROM public.pilot_communes c CROSS JOIN networks n
), shared AS (
    SELECT a.commune_id AS commune_a, b.commune_id AS commune_b, n.kind,
           ST_Length(ST_CollectionExtract(ST_Intersection(n.geom,
               ST_Intersection(ST_Boundary(a.geom), ST_Boundary(b.geom))),2)) AS length_m,
           ST_Area(ST_CollectionExtract(ST_Intersection(a.geom,b.geom),3)) AS polygon_overlap_m2
    FROM public.pilot_communes a JOIN public.pilot_communes b
      ON a.commune_id<b.commune_id AND a.geom && b.geom
    CROSS JOIN networks n
), comparison AS (
    SELECT count(*) AS matched_fids,
           count(*) FILTER (WHERE ST_OrderingEquals(c.geom,r.geom)) AS exact_projected,
           max(ST_HausdorffDistance(c.geom,r.geom)) AS max_pair_distance_m,
           max(abs(ST_Length(c.geom)-ST_Length(r.geom))) AS max_pair_length_difference_m
    FROM rivers c JOIN rivers r USING (fid) WHERE c.kind='clean' AND r.kind='raw'
), basins AS (
    SELECT basin_id, ST_Area(f.geom::geography)/1e6 AS total_km2,
           ST_Area(ST_CollectionExtract(
             ST_Intersection(f.geom, ST_Transform(p.geom,4326)),3
           )::geography)/1e6 AS inside_km2
    FROM features f CROSS JOIN pilot p WHERE kind='basin'
), pilot_coverage AS (
    SELECT ST_Area(ST_Transform(p.geom,4326)::geography)/1e6 AS pilot_km2,
           ST_Area(ST_CollectionExtract(ST_Intersection(ST_Transform(p.geom,4326),
              (SELECT ST_Union(geom) FROM features WHERE kind='basin')),3)::geography)/1e6 AS covered_km2
    FROM pilot p
)
SELECT jsonb_pretty(jsonb_build_object(
    'metric_crs', (SELECT proj4text FROM spatial_ref_sys WHERE srid=26191),
    'integrity', (SELECT json_agg(integrity ORDER BY kind) FROM integrity),
    'network_stats', (SELECT json_agg(network_stats ORDER BY kind) FROM network_stats),
    'communes', (SELECT json_agg(communes ORDER BY commune_id,kind) FROM communes),
    'shared', (SELECT json_agg(shared ORDER BY commune_a,commune_b,kind) FROM shared
               WHERE length_m > 0 OR polygon_overlap_m2 > 0.001),
    'comparison', (SELECT row_to_json(comparison) FROM comparison),
    'basins', (SELECT json_agg(basins ORDER BY basin_id) FROM basins),
    'pilot_coverage', (SELECT row_to_json(pilot_coverage) FROM pilot_coverage)
));
SQL
{ printf '%s\n' 'BEGIN READ ONLY;'; cat /tmp/terralert-drainage/features.sql /tmp/terralert-drainage/measure.sql; printf '%s\n' 'ROLLBACK;'; } |
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /tmp/terralert-drainage/results.json
test -s /tmp/terralert-drainage/results.json
```

```sh
cat > /tmp/terralert-drainage/diagnose.sql <<'SQL'
, pilot AS MATERIALIZED (
    SELECT ST_Transform(ST_Union(geom),4326) AS geom FROM public.pilot_communes
), basins AS (
    SELECT basin_id,
           ST_Area(f.geom::geography) AS total_m2,
           ST_Area(ST_CollectionExtract(ST_Intersection(f.geom,p.geom),3)::geography) AS inside_m2,
           ST_Area(ST_CollectionExtract(ST_Difference(f.geom,p.geom),3)::geography) AS outside_m2
    FROM features f CROSS JOIN pilot p WHERE kind='basin'
), commune_lines AS MATERIALIZED (
    SELECT commune_id, ST_CollectionExtract(ST_Intersection(c.geom, f.geom),2) AS geom
    FROM public.pilot_communes c JOIN features f ON f.kind='clean' AND f.geom && c.geom
), lengths AS (
    SELECT commune_id,
           sum(ST_Length(geom)) AS projected_m,
           sum(ST_Length(ST_Transform(geom,4326)::geography)) AS geodesic_m,
           sum(ST_Length(ST_Transform(geom,32630))) AS utm30_m
    FROM commune_lines GROUP BY commune_id
), provenance_check AS (
    SELECT count(*) AS matched_feature_ids
    FROM features raw JOIN features clean USING (fid)
    WHERE raw.kind='raw' AND clean.kind='clean'
)
SELECT jsonb_pretty(jsonb_build_object(
  'basins',(SELECT json_agg(basins ORDER BY basin_id) FROM basins),
  'lengths',(SELECT json_agg(lengths ORDER BY commune_id) FROM lengths),
  'matched_ids',(SELECT matched_feature_ids FROM provenance_check)
));
SQL
{ printf '%s\n' 'BEGIN READ ONLY;'; cat /tmp/terralert-drainage/features.sql /tmp/terralert-drainage/diagnose.sql; printf '%s\n' 'ROLLBACK;'; } |
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /tmp/terralert-drainage/diagnostic.json
test -s /tmp/terralert-drainage/diagnostic.json
```

```sh
cd /tmp/terralert-drainage
sqlite3 -readonly -header bassin_versant_tanger.gpkg 'SELECT HYBAS_ID, SUB_AREA FROM bassin_versant_tanger ORDER BY HYBAS_ID;'
python3 - <<'PY'
import csv
import json
from pathlib import Path
import sqlite3

maps = []
for name in ('commune_indicators.csv', 'indicators_occupation.csv'):
    with open(name, encoding='utf-8-sig', newline='') as f:
        maps.append({row['ISO']: row for row in csv.DictReader(f)})
assert maps[0].keys() == maps[1].keys() and len(maps[0]) == 11
assert all(maps[0][key][field] == maps[1][key][field]
           for key in maps[0] for field in ('river_m', 'river_km', 'river_n'))
attrs = []
for path in (Path('rivers_11_communes.gpkg'), Path('rivers_traced.gpkg')):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        table, = db.execute('SELECT table_name FROM gpkg_geometry_columns').fetchone()
        columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")') if r[1] != 'geom']
        attrs.append(db.execute('SELECT ' + ','.join('"' + n + '"' for n in columns)
                                + f' FROM "{table}" ORDER BY fid').fetchall())
        print(table, db.execute(f'SELECT layer, count(*) FROM "{table}" GROUP BY layer').fetchall())
print('River attributes equal by FID:', attrs[0] == attrs[1])
results = json.load(open('results.json'))
diagnostic = json.load(open('diagnostic.json'))
for row in results['communes']:
    old = float(maps[0][row['commune_id']]['river_m'])
    print(row['commune_id'], row['kind'], row['length_m'], old, row['length_m'] - old)
for row in diagnostic['lengths']:
    old = float(maps[0][row['commune_id']]['river_m'])
    print(row['commune_id'], 'geodesic minus indicator', row['geodesic_m'] - old)
for row in diagnostic['basins']:
    print(row['basin_id'], 'outside m²', row['outside_m2'],
          'outside %', 100 * row['outside_m2'] / row['total_m2'])
PY
```
