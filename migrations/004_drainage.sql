CREATE TABLE IF NOT EXISTS public.pilot_rivers (
    source_fid bigint PRIMARY KEY,
    geom geometry(MultiLineString, 26191) NOT NULL
        CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom)),
    attributes jsonb NOT NULL CHECK (jsonb_typeof(attributes) = 'object'),
    source_url text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    source_srid integer NOT NULL CHECK (source_srid = 26191)
);

CREATE TABLE IF NOT EXISTS public.pilot_catchments (
    hybas_id bigint PRIMARY KEY,
    geom geometry(MultiPolygon, 4326) NOT NULL
        CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom)),
    attributes jsonb NOT NULL CHECK (jsonb_typeof(attributes) = 'object'),
    source_url text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    source_srid integer NOT NULL CHECK (source_srid = 4326)
);

COMMENT ON TABLE public.pilot_catchments IS
    'Supplied pilot-area catchment polygons with original coordinates. Full upstream catchment footprints are outside the scope of this dataset.';
