CREATE TABLE IF NOT EXISTS weather_forecasts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    is_fixture boolean NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    payload jsonb NOT NULL
);
