"""Import both audited TERRALERT drainage layers in one PostGIS transaction."""

import argparse
import csv
from dataclasses import dataclass
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3
import subprocess

from import_pilot_communes import geometry_wkb


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Layer:
    name: str
    table: str
    source_key: str
    db_key: str
    geometry_type: str
    srid: int
    count: int
    source_url: str
    checksum: str


RIVERS = Layer(
    "rivers_11_communes", "pilot_rivers", "fid", "source_fid", "MULTILINESTRING",
    26191, 123, "https://drive.google.com/file/d/1IDJY_2LA7eseL4A7FxKt1LLpGtOytZQ3/view",
    "223fb53113d486b2562a6c64bd3dad974996fe679ba47df5014e9e6b9e41c6c3",
)
CATCHMENTS = Layer(
    "bassin_versant_tanger", "pilot_catchments", "HYBAS_ID", "hybas_id", "MULTIPOLYGON",
    4326, 5, "https://drive.google.com/file/d/14BeykywLiji5IoZ_e2TWzwdniMVhcX2U/view",
    "513c608a18d694687c9bb5b00e43c4dc70db54c986958c060f5fa09e83590cfa",
)


def read_layer(path, layer):
    if sha256(path.read_bytes()).hexdigest() != layer.checksum:
        raise ValueError(f"{path.name}: SHA-256 differs from the audit")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        metadata = db.execute("""
            SELECT g.table_name, g.column_name, g.geometry_type_name, g.srs_id,
                   g.z, g.m, s.organization, s.organization_coordsys_id
            FROM gpkg_geometry_columns g JOIN gpkg_spatial_ref_sys s USING (srs_id)
        """).fetchall()
        expected = (layer.name, "geom", layer.geometry_type, layer.srid, 0, 0, "EPSG", layer.srid)
        if [tuple(row) for row in metadata] != [expected]:
            raise ValueError(f"{path.name}: layer metadata differs from the audit")
        rows = db.execute(f'SELECT * FROM "{layer.name}" ORDER BY fid').fetchall()
    csv_data = io.StringIO(newline="")
    writer = csv.writer(csv_data, lineterminator="\n")
    for row in rows:
        attributes = dict(row)
        wkb = geometry_wkb(attributes.pop("geom"), layer.srid)
        writer.writerow((attributes[layer.source_key], wkb, json.dumps(attributes, ensure_ascii=False)))
    return csv_data.getvalue()


def stage_sql(layer, csv_data):
    name = layer.table
    key = layer.db_key
    return f"""
CREATE TEMP TABLE {name}_input (feature_key bigint PRIMARY KEY, wkb text NOT NULL, attrs jsonb NOT NULL);
\\copy {name}_input FROM STDIN WITH (FORMAT csv)
{csv_data}\\.
CREATE TEMP TABLE {name}_stage (
    LIKE public.{name} INCLUDING CONSTRAINTS INCLUDING INDEXES
);
INSERT INTO {name}_stage ({key}, geom, attributes, source_url, source_sha256, source_srid)
SELECT feature_key, ST_GeomFromWKB(decode(wkb, 'hex'), {layer.srid}), attrs,
       '{layer.source_url}', '{layer.checksum}', {layer.srid}
FROM {name}_input;
DO $$
BEGIN
    IF (SELECT count(*) FROM {name}_stage) <> {layer.count} THEN
        RAISE EXCEPTION 'Expected {layer.count} staged features for {name}';
    END IF;
    IF EXISTS (
        SELECT FROM {name}_stage a
        JOIN {name}_stage b ON a.{key} < b.{key} AND a.geom && b.geom
        WHERE ST_Equals(a.geom, b.geom)
    ) THEN
        RAISE EXCEPTION 'Duplicate staged geometry in {name}';
    END IF;
    IF EXISTS (
        SELECT {key}, ST_AsEWKB(geom), attributes, source_url, source_sha256, source_srid
        FROM public.{name}
        EXCEPT
        SELECT {key}, ST_AsEWKB(geom), attributes, source_url, source_sha256, source_srid
        FROM {name}_stage
    ) THEN
        RAISE EXCEPTION 'Existing data differ from the audited import in {name}';
    END IF;
END
$$;
"""


def insert_sql(layer):
    name = layer.table
    key = layer.db_key
    return f"""
WITH inserted AS (
    INSERT INTO public.{name} ({key}, geom, attributes, source_url, source_sha256, source_srid)
    SELECT {key}, geom, attributes, source_url, source_sha256, source_srid FROM {name}_stage
    ON CONFLICT ({key}) DO NOTHING
    RETURNING 1
)
SELECT format('{name}: %s staged, %s inserted',
              (SELECT count(*) FROM {name}_stage), count(*)) FROM inserted;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rivers", type=Path)
    parser.add_argument("catchments", type=Path)
    args = parser.parse_args()
    try:
        rivers = read_layer(args.rivers, RIVERS)
        catchments = read_layer(args.catchments, CATCHMENTS)
        sql = (
            (ROOT / "migrations/004_drainage.sql").read_text(encoding="utf-8")
            + "\nLOCK TABLE public.pilot_rivers, public.pilot_catchments IN SHARE ROW EXCLUSIVE MODE;\n"
            + stage_sql(RIVERS, rivers) + stage_sql(CATCHMENTS, catchments)
            + insert_sql(RIVERS) + insert_sql(CATCHMENTS)
        )
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "db", "sh", "-c",
             'exec psql -XqAt --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -'],
            input=sql, encoding="utf-8", cwd=ROOT, stdout=subprocess.PIPE,
        )
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"Cannot import drainage layers: {error}\n")
    if result.returncode:
        parser.exit(result.returncode, "Drainage transaction failed. See the PostgreSQL error above.\n")
    print(result.stdout, end="")


if __name__ == "__main__":
    main()
