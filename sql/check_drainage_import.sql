BEGIN READ ONLY;

SELECT 'rivers' AS layer, count(*) AS features, count(DISTINCT source_fid) AS keys,
       array_agg(DISTINCT ST_SRID(geom)) AS stored_srids,
       count(*) FILTER (WHERE ST_IsValid(geom) AND NOT ST_IsEmpty(geom)) AS valid_nonempty,
       min(source_url) AS source_url, min(source_sha256) AS source_sha256,
       md5(string_agg(row_to_json(r)::text, '' ORDER BY source_fid)) AS digest
FROM public.pilot_rivers r
UNION ALL
SELECT 'catchments', count(*), count(DISTINCT hybas_id), array_agg(DISTINCT ST_SRID(geom)),
       count(*) FILTER (WHERE ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
       min(source_url), min(source_sha256),
       md5(string_agg(row_to_json(c)::text, '' ORDER BY hybas_id))
FROM public.pilot_catchments c
ORDER BY layer;

WITH commune_lines AS (
    SELECT c.commune_id, c.name_fr,
           ST_CollectionExtract(ST_Intersection(c.geom, r.geom), 2) AS geom
    FROM public.pilot_communes c JOIN public.pilot_rivers r ON r.geom && c.geom
)
SELECT commune_id, name_fr,
       round(sum(ST_Length(ST_Transform(geom, 4326)::geography))::numeric, 3) AS geodesic_m
FROM commune_lines
GROUP BY commune_id, name_fr
ORDER BY commune_id;

WITH pilot AS (
    SELECT ST_Union(geom) AS geom FROM public.pilot_communes
), dissolved AS (
    SELECT ST_Union(geom) AS geom FROM public.pilot_rivers
), network AS (
    SELECT ST_CollectionExtract(ST_Intersection(d.geom, p.geom), 2) AS geom
    FROM pilot p CROSS JOIN dissolved d
), lengths AS (
    SELECT ST_Length(geom) AS projected_m,
           ST_Length(ST_Transform(geom, 4326)::geography) AS geodesic_m
    FROM network
)
SELECT round(projected_m::numeric, 3) AS dissolved_projected_m,
       round(geodesic_m::numeric, 3) AS dissolved_geodesic_m,
       abs(projected_m - 217463.96587680033) <= 0.001 AS projected_total_matches_audit
FROM lengths;

WITH pilot AS (
    SELECT ST_Transform(ST_Union(geom), 4326) AS geom FROM public.pilot_communes
), catchments AS (
    SELECT ST_Union(geom) AS geom FROM public.pilot_catchments
), areas AS (
    SELECT ST_Area(p.geom::geography) AS pilot_m2,
           ST_Area(ST_CollectionExtract(ST_Intersection(p.geom, c.geom), 3)::geography) AS covered_m2
    FROM pilot p CROSS JOIN catchments c
)
SELECT round((pilot_m2 / 1e6)::numeric, 6) AS pilot_km2,
       round((covered_m2 / 1e6)::numeric, 6) AS covered_km2,
       round((100 * covered_m2 / pilot_m2)::numeric, 4) AS covered_pct,
       abs(100 * covered_m2 / pilot_m2 - 99.9874) <= 0.00005 AS coverage_matches_audit
FROM areas;

ROLLBACK;
