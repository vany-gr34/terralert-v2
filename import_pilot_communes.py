"""Import the TERRALERT pilot commune GeoPackage through Docker Compose."""

import argparse
import csv
import io
from pathlib import Path
import sqlite3
import subprocess


LAYER = "communes_11_fixed"
SOURCE_SRID = 32630


def geometry_wkb(blob, source_srid=SOURCE_SRID):
    # GeoPackage stores a header and optional XY envelope before the WKB.
    if not blob or len(blob) < 8 or blob[:3] != b"GP\x00":
        raise ValueError("missing or unsupported GeoPackage geometry header")
    flags = blob[3]
    envelope = (flags >> 1) & 7
    if flags & 0xF0 or envelope not in (0, 1):
        raise ValueError("expected a nonempty standard 2D GeoPackage geometry")
    byte_order = "little" if flags & 1 else "big"
    if int.from_bytes(blob[4:8], byte_order, signed=True) != source_srid:
        raise ValueError("geometry CRS differs from the verified layer CRS")
    return blob[8 + 32 * envelope:].hex()


def read_communes(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        metadata = db.execute("""
            SELECT g.column_name, g.geometry_type_name, g.srs_id, g.z, g.m,
                   s.organization, s.organization_coordsys_id
            FROM gpkg_geometry_columns g
            JOIN gpkg_spatial_ref_sys s USING (srs_id)
            WHERE g.table_name = ?
        """, (LAYER,)).fetchall()
        if metadata != [("geom", "MULTIPOLYGON", SOURCE_SRID, 0, 0, "EPSG", SOURCE_SRID)]:
            raise ValueError(f"unexpected layer metadata: {metadata}")
        rows = db.execute("""
            SELECT "ISO", "nom_fr", "nom_ar", "geom"
            FROM "communes_11_fixed" ORDER BY "ISO"
        """).fetchall()
    ids = [row[0] for row in rows]
    if len(ids) != 11 or len(set(ids)) != 11 or any(
        not isinstance(code, str) or not code.strip() for code in ids
    ):
        raise ValueError("expected 11 unique, nonblank ISO commune IDs")
    return [(code, name_fr, name_ar, geometry_wkb(blob)) for code, name_fr, name_ar, blob in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geopackage", type=Path)
    args = parser.parse_args()
    try:
        rows = read_communes(args.geopackage)
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"Cannot read pilot communes: {error}\n")

    payload = io.StringIO(newline="")
    payload.write(r"""
BEGIN;
CREATE TEMP TABLE commune_wkb (
    commune_id text PRIMARY KEY, name_fr text, name_ar text, wkb text NOT NULL
);
\copy commune_wkb FROM STDIN WITH (FORMAT csv)
""")
    csv.writer(payload, lineterminator="\n").writerows(rows)
    payload.write(r"""\.
CREATE TEMP TABLE commune_source (
    commune_id text PRIMARY KEY, name_fr text, name_ar text,
    geom geometry(MultiPolygon, 32630) NOT NULL CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom))
);
INSERT INTO commune_source
SELECT commune_id, name_fr, name_ar, ST_GeomFromWKB(decode(wkb, 'hex'), 32630)
FROM commune_wkb;

DO $$
BEGIN
    IF (SELECT count(*) FROM commune_source) <> 11 THEN
        RAISE EXCEPTION 'Expected 11 valid source commune geometries';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.pilot_communes (
    commune_id text PRIMARY KEY,
    name_fr text,
    name_ar text,
    geom geometry(MultiPolygon, 26191) NOT NULL CHECK (NOT ST_IsEmpty(geom) AND ST_IsValid(geom))
);
LOCK TABLE public.pilot_communes IN SHARE ROW EXCLUSIVE MODE;
DO $$
BEGIN
    IF EXISTS (
        SELECT commune_id FROM public.pilot_communes
        EXCEPT
        SELECT commune_id FROM commune_source
    ) THEN
        RAISE EXCEPTION 'Existing pilot commune IDs differ from the GeoPackage';
    END IF;
END
$$;

INSERT INTO public.pilot_communes (commune_id, name_fr, name_ar, geom)
SELECT commune_id, name_fr, name_ar, ST_Transform(geom, 26191)
FROM commune_source
ON CONFLICT (commune_id) DO UPDATE
SET name_fr = EXCLUDED.name_fr, name_ar = EXCLUDED.name_ar, geom = EXCLUDED.geom;
COMMIT;
""")
    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "db", "sh", "-c",
             'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
            input=payload.getvalue(), encoding="utf-8", cwd=Path(__file__).resolve().parent,
        )
    except OSError as error:
        parser.exit(1, f"Cannot run Docker Compose: {error}\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
