CREATE TABLE IF NOT EXISTS public.pilot_population (
    commune_id text PRIMARY KEY REFERENCES public.pilot_communes(commune_id),
    attributes jsonb NOT NULL CHECK (jsonb_typeof(attributes) = 'object'),
    source_url text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    producer text,
    reference_year integer,
    status text NOT NULL DEFAULT 'provisional' CHECK (status = 'provisional'),
    staged_at timestamptz NOT NULL DEFAULT now(),
    CHECK (attributes->>'ISO' = commune_id)
);
COMMENT ON TABLE public.pilot_population IS
    'Provisional source population attributes. Producer/year unconfirmed. Geometry comes only from public.pilot_communes; source polygons are not imported.';
