ALTER TABLE public.weather_forecasts
    ADD COLUMN IF NOT EXISTS run_id uuid,
    ADD COLUMN IF NOT EXISTS commune_id text REFERENCES public.pilot_communes (commune_id),
    ADD COLUMN IF NOT EXISTS requested_latitude numeric,
    ADD COLUMN IF NOT EXISTS requested_longitude numeric,
    ADD COLUMN IF NOT EXISTS returned_latitude numeric,
    ADD COLUMN IF NOT EXISTS returned_longitude numeric;

CREATE UNIQUE INDEX IF NOT EXISTS weather_forecasts_run_commune_idx
    ON public.weather_forecasts (run_id, commune_id) WHERE run_id IS NOT NULL;
