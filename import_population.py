"""Stage audited population attributes; preserve nulls and reject conflicting reruns."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parent
CHECKSUM = 'a3b84589261744839d9815ac6d2c718dd42f953d7a50126d94679a18c416d89d'
SOURCE = 'https://drive.google.com/file/d/1pzBduO9JHhshw0hvJ2Gzge4BeAqFT593/view'


def read_source(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != CHECKSUM:
        raise ValueError('Source SHA-256 differs from the audited population GeoPackage')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute('SELECT * FROM population_26191 ORDER BY ISO')]
    for row in rows:
        del row['geom']
    if len(rows) != 11 or len({r['ISO'] for r in rows}) != 11 or any(not r['ISO'] for r in rows):
        raise ValueError('Expected 11 unique nonmissing commune IDs')
    if sum(r['P_ensemble'] for r in rows) != 1424783:
        raise ValueError('Unexpected population total')
    return {r['ISO']: r for r in rows}


def psql(sql):
    return subprocess.check_output([
        'docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
        'exec psql -XqAt --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -'
    ], input=sql, text=True, cwd=ROOT).strip()


def stage(expected):
    data = io.StringIO()
    writer = csv.writer(data, lineterminator='\n')
    for key, attributes in expected.items():
        writer.writerow((key, json.dumps(attributes, ensure_ascii=False, allow_nan=False), SOURCE, CHECKSUM))
    sql = (ROOT / 'migrations/005_population.sql').read_text() + r'''
LOCK TABLE public.pilot_population IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE population_stage (LIKE public.pilot_population INCLUDING ALL) ON COMMIT DROP;
\copy population_stage (commune_id, attributes, source_url, source_sha256) FROM STDIN WITH (FORMAT csv)
''' + data.getvalue() + r'''\.
DO $$
DECLARE conflicts text;
BEGIN
    IF (SELECT count(*) FROM population_stage) <> 11
       OR (SELECT sum((attributes->>'P_ensemble')::bigint) FROM population_stage) <> 1424783
       OR EXISTS (SELECT commune_id FROM population_stage EXCEPT SELECT commune_id FROM public.pilot_communes)
       OR EXISTS (SELECT commune_id FROM public.pilot_communes EXCEPT SELECT commune_id FROM population_stage)
    THEN RAISE EXCEPTION 'Source does not match all 11 pilot communes and expected total'; END IF;
    SELECT string_agg(t.commune_id, ', ' ORDER BY t.commune_id) INTO conflicts
    FROM public.pilot_population t LEFT JOIN population_stage s USING (commune_id)
    WHERE s.commune_id IS NULL OR
      (t.attributes,t.source_url,t.source_sha256,t.producer,t.reference_year,t.status)
      IS DISTINCT FROM
      (s.attributes,s.source_url,s.source_sha256,s.producer,s.reference_year,s.status);
    IF conflicts IS NOT NULL THEN
        RAISE EXCEPTION 'Conflicting population records (nothing replaced): %', conflicts;
    END IF;
END $$;
WITH added AS (
 INSERT INTO public.pilot_population (commune_id,attributes,source_url,source_sha256)
 SELECT commune_id,attributes,source_url,source_sha256 FROM population_stage
 ON CONFLICT (commune_id) DO NOTHING RETURNING commune_id
)
SELECT format('Staged 11; inserted %s; updated 0.',count(*)) FROM added;
DO $$ BEGIN
 IF EXISTS (SELECT commune_id,attributes,source_url,source_sha256 FROM population_stage
            EXCEPT SELECT commune_id,attributes,source_url,source_sha256 FROM public.pilot_population)
 THEN RAISE EXCEPTION 'Stored attributes differ from source'; END IF;
END $$;
'''
    return psql(sql)


def verify(expected):
    rows = json.loads(psql('SET TRANSACTION READ ONLY; SELECT coalesce(json_agg(t ORDER BY commune_id),\'[]\') FROM public.pilot_population t;'))
    if len(rows) != 11 or {r['commune_id']: r['attributes'] for r in rows} != expected or any(
        r['source_url'] != SOURCE or r['source_sha256'] != CHECKSUM
        or r['producer'] is not None or r['reference_year'] is not None or r['status'] != 'provisional'
        for r in rows
    ):
        raise ValueError('Stored source attributes or provenance differ')
    return 'Verified 11 rows: all 11 source attribute fields match, total 1424783; 9 household nulls preserved; provisional, producer/year NULL.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geopackage', type=Path)
    parser.add_argument('--verify', action='store_true', help='read-only comparison with the source')
    args = parser.parse_args()
    try:
        expected = read_source(args.geopackage)
        print('Verified source SHA-256:', CHECKSUM)
        if not args.verify:
            print(stage(expected))
        print(verify(expected))
    except (OSError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Population operation failed: {error}\n')


if __name__ == '__main__':
    main()
