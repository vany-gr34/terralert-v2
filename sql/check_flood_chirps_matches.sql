BEGIN READ ONLY;

WITH annual_sources (year, source_sha256) AS (
    VALUES
        (2015, '60efa742e49c8476445856e1635d79680b909711c787ff1f17f3b0147fa39e3d'),
        (2016, '43e17f38afc9a96f781bab53637fe4d8db0d150f157eda8bc17e3e35b9b61a38'),
        (2017, 'fd4b695bd39e50baa9fce1da35e4645bc523b4b612de9fbc262845980a8bbe1c'),
        (2018, '844af667ec89df9e60b1aea7c2ae2b993cda5c17d8c3d8aca86d0d38aee309d3'),
        (2019, '51c5608fd88ea27295c91fad5a381b54dfb5c94dacd01730e4668b64cd96a119'),
        (2020, '7b128c8a98de510f7abfca29f80265b4e410bf4e294d72ebed4e674e0c0d92f8')
), reports AS (
    SELECT observation_id, event_id, fields,
           CASE WHEN fields->>'observation_date' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                     AND pg_input_is_valid(fields->>'observation_date', 'date')
                THEN (fields->>'observation_date')::date END AS observation_date,
           CASE WHEN pg_input_is_valid(fields->>'longitude', 'double precision')
                THEN (fields->>'longitude')::double precision END AS longitude,
           CASE WHEN pg_input_is_valid(fields->>'latitude', 'double precision')
                THEN (fields->>'latitude')::double precision END AS latitude,
           CASE fields->>'location_precision_m'
                WHEN '1000' THEN 1000 WHEN '2000' THEN 2000 END AS radius_m
    FROM public.historical_flood_observations
    WHERE source_sha256 = '338324f793132fff83e3f1e303d08886ce184126fa84fae19f81fe268986d12f'
      AND fields->>'date_precision' = 'day'
      AND fields->>'temporal_uncertainty' = 'Day known; flood onset time usually unknown'
      AND fields->>'verification_status' NOT ILIKE '%requires event-place corroboration%'
), exact_dates AS (
    SELECT r.*, a.source_sha256 AS rainfall_source_sha256,
           CASE WHEN fields->>'coordinate_reference_system' = 'EPSG:4326'
                     AND longitude BETWEEN -180 AND 180 AND latitude BETWEEN -90 AND 90
                THEN ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 26191)
           END AS point_geom
    FROM reports r
    JOIN annual_sources a ON a.year = extract(year FROM r.observation_date)
), evaluated AS (
    SELECT e.*, spatial.radius_communes, spatial.point_communes,
           spatial.commune_id, spatial.commune_name, spatial.boundary_distance_m
    FROM exact_dates e
    CROSS JOIN LATERAL (
        SELECT count(*) AS radius_communes,
               count(*) FILTER (WHERE ST_Covers(c.geom, e.point_geom)) AS point_communes,
               min(c.commune_id) AS commune_id,
               min(c.name_fr) AS commune_name,
               min(ST_Distance(ST_Boundary(c.geom), e.point_geom)) AS boundary_distance_m
        FROM public.pilot_communes c
        WHERE ST_DWithin(c.geom, e.point_geom, e.radius_m)
    ) spatial
), classified AS (
    SELECT *, COALESCE(
               radius_communes = 1 AND point_communes = 1 AND boundary_distance_m > radius_m
               AND (coalesce(btrim(fields->>'commune'), '') = ''
                    OR lower(btrim(fields->>'commune')) = lower(btrim(commune_name))),
               false) AS assigned
    FROM evaluated
), matches AS (
    SELECT c.observation_id, c.event_id, c.commune_id, c.commune_name,
           c.observation_date, r.rainfall_mm_per_day, r.footprint_coverage,
           r.valid_rainfall_coverage, c.fields->>'confidence_level' AS confidence,
           c.radius_m AS recorded_location_precision_m,
           round(c.boundary_distance_m::numeric, 2) AS boundary_distance_m,
           c.fields->>'geographic_uncertainty' AS geographic_uncertainty,
           c.fields->>'verification_status' AS verification_status,
           c.fields->>'inside_terralert_study_area' AS recorded_study_membership,
           c.fields->>'primary_source_name' AS original_report_source,
           c.fields->>'primary_source_url' AS original_report_url,
           r.product_variant, r.source_sha256 AS rainfall_source_sha256
    FROM classified c
    JOIN public.chirps_daily_commune_rainfall r
      ON r.commune_id = c.commune_id AND r.rainfall_date = c.observation_date
      AND r.product_variant = 'CHIRPS v3 Final SAT'
      AND r.source_sha256 = c.rainfall_source_sha256
    WHERE c.assigned
), summary AS (
    SELECT count(*) AS exact_date_observations,
           count(*) FILTER (WHERE NOT assigned) AS spatially_ambiguous,
           count(*) FILTER (WHERE assigned) AS eligible_assignments,
           (SELECT count(*) FROM matches) AS exploratory_matches
    FROM classified
)
SELECT summary.*, matches.*
FROM summary LEFT JOIN matches ON true
ORDER BY matches.observation_id;

ROLLBACK;
