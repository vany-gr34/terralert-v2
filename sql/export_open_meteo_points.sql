BEGIN READ ONLY;

WITH points AS (
    SELECT commune_id, name_fr AS name, geom AS boundary,
           ST_Transform(ST_PointOnSurface(geom), 4326) AS point
    FROM public.pilot_communes
), coordinates AS (
    SELECT commune_id, name, boundary,
           round(ST_Y(point)::numeric, 8) AS latitude,
           round(ST_X(point)::numeric, 8) AS longitude
    FROM points
), checked AS (
    SELECT *,
           ST_Contains(boundary, ST_Transform(
               ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), ST_SRID(boundary)
           )) AS inside
    FROM coordinates
)
SELECT count(*) AS point_count,
       count(DISTINCT commune_id) AS unique_ids,
       count(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) AS missing_coordinates,
       count(*) FILTER (WHERE inside) AS inside_count,
       count(*) = 11 AND count(DISTINCT commune_id) = 11
           AND count(*) FILTER (WHERE inside) = 11
           AND count(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) = 0
           AND count(name) = 11 AS checks_pass,
       COALESCE(string_agg(format('"%s","%s",%s,%s',
           replace(commune_id, '"', '""'), replace(name, '"', '""'), latitude, longitude
       ), E'\n' ORDER BY commune_id), '') AS csv_rows
FROM checked
\gset

\warn 'Sampling checks: points=' :point_count 'unique_ids=' :unique_ids 'missing_coordinates=' :missing_coordinates 'inside=' :inside_count
\if :checks_pass
    \echo commune_id,name,latitude,longitude
    \echo :csv_rows
\else
    \warn 'Sampling checks failed. No CSV was emitted.'
    -- Raise a SQL error so callers using ON_ERROR_STOP receive a failure.
    DO $$ BEGIN RAISE EXCEPTION 'Open-Meteo sampling checks failed'; END $$;
\endif

ROLLBACK;
