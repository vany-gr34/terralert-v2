CREATE TABLE IF NOT EXISTS public.historical_flood_observations (
    observation_id text PRIMARY KEY CHECK (btrim(observation_id) <> ''),
    fields jsonb NOT NULL,
    event_id text GENERATED ALWAYS AS (fields->>'event_id') STORED
        NOT NULL CHECK (btrim(event_id) <> ''),
    source_url text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (jsonb_typeof(fields) = 'object'),
    CHECK ((fields->>'observation_id') IS NOT DISTINCT FROM observation_id)
);
