BEGIN READ ONLY;
SET LOCAL TIME ZONE 'UTC';

SELECT run_id, count(*) AS forecasts, count(DISTINCT commune_id) AS unique_communes,
       min(ingested_at) AS ingested_at_utc,
       min(payload->'hourly'->'time'->>0) AS first_forecast_utc,
       max(payload->'hourly'->'time'->>-1) AS last_forecast_utc,
       min(jsonb_array_length(payload->'hourly'->'time')) AS min_hourly_samples,
       max(jsonb_array_length(payload->'hourly'->'time')) AS max_hourly_samples,
       count(*) FILTER (WHERE source = 'open_meteo' AND NOT is_fixture
           AND requested_latitude IS NOT NULL AND requested_longitude IS NOT NULL
           AND returned_latitude = (payload->>'latitude')::numeric
           AND returned_longitude = (payload->>'longitude')::numeric) AS matching_metadata_rows
FROM public.weather_forecasts
WHERE run_id = :'run_id'::uuid
GROUP BY run_id;

SELECT returned_latitude, returned_longitude, count(*) AS forecasts,
       array_agg(commune_id ORDER BY commune_id) AS commune_ids
FROM public.weather_forecasts
WHERE run_id = :'run_id'::uuid
GROUP BY returned_latitude, returned_longitude
HAVING count(*) > 1
ORDER BY returned_latitude, returned_longitude;

SELECT commune_id, requested_latitude, requested_longitude,
       returned_latitude, returned_longitude,
       payload->'hourly'->'time'->>0 AS first_forecast_utc,
       payload->'hourly'->'time'->>-1 AS last_forecast_utc
FROM public.weather_forecasts
WHERE run_id = :'run_id'::uuid
ORDER BY commune_id;

SELECT count(*) AS original_rows,
       md5(string_agg(row_to_json(original)::text, '' ORDER BY id)) AS original_digest
FROM (
    SELECT id, source, is_fixture, ingested_at, payload
    FROM public.weather_forecasts
    WHERE run_id IS NULL
) original;

ROLLBACK;
