"""Import or verify the audited historical flood observations in local PostgreSQL."""

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

from prepare_past_floods import SOURCE_SHA256, parse


ROOT = Path(__file__).resolve().parent
MIGRATION = ROOT / "migrations/002_historical_flood_observations.sql"
SOURCE_URL = "https://drive.google.com/file/d/1x9T9luY4WFETdW5QknSqXC-8V8aEcw6p/view"
PREPARED_SHA256 = "b3b292647b0b88cd81634785a20032a7e45923a6e1f533ebbd177f1896702831"


def read_observations(path):
    data = path.read_bytes()
    if sha256(data).hexdigest() != PREPARED_SHA256:
        raise ValueError("prepared CSV SHA-256 differs from the verified working copy")
    header, *rows = parse(data)
    return {row[0]: dict(zip(header, row, strict=True)) for row in rows}


def psql(sql):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "db", "sh", "-c",
         'exec psql -XqAt --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -'],
        input=sql, encoding="utf-8", cwd=ROOT,
    ).strip()


def import_observations(observations):
    stage = io.StringIO(newline="")
    writer = csv.writer(stage, lineterminator="\n")
    for observation_id, fields in observations.items():
        writer.writerow((observation_id, json.dumps(fields, ensure_ascii=False), SOURCE_URL, SOURCE_SHA256))
    return psql(MIGRATION.read_text(encoding="utf-8") + f"""
LOCK TABLE public.historical_flood_observations IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE flood_stage (
    LIKE public.historical_flood_observations INCLUDING GENERATED INCLUDING CONSTRAINTS INCLUDING INDEXES
);
\\copy flood_stage (observation_id, fields, source_url, source_sha256) FROM STDIN WITH (FORMAT csv)
{stage.getvalue()}\\.
DO $$
DECLARE conflicts text;
BEGIN
    IF (SELECT count(*) FROM flood_stage) <> 103
       OR (SELECT count(DISTINCT event_id) FROM flood_stage) <> 18
       OR EXISTS (SELECT FROM flood_stage s
                  WHERE (SELECT count(*) FROM jsonb_object_keys(s.fields)) <> 42) THEN
        RAISE EXCEPTION 'Expected 103 observations, 18 events, and 42 fields per observation';
    END IF;
    SELECT string_agg(s.observation_id, ', ' ORDER BY s.observation_id) INTO conflicts
    FROM flood_stage s JOIN public.historical_flood_observations t USING (observation_id)
    WHERE (s.fields, s.source_url, s.source_sha256)
        IS DISTINCT FROM (t.fields, t.source_url, t.source_sha256);
    IF conflicts IS NOT NULL THEN
        RAISE EXCEPTION 'Conflicting observation IDs: %', conflicts;
    END IF;
END
$$;
WITH inserted AS (
    INSERT INTO public.historical_flood_observations (observation_id, fields, source_url, source_sha256)
    SELECT observation_id, fields, source_url, source_sha256 FROM flood_stage
    ON CONFLICT (observation_id) DO NOTHING
    RETURNING observation_id
)
SELECT format('Staged %s observations; inserted %s; updated 0.',
              (SELECT count(*) FROM flood_stage), count(*))
FROM inserted;
""")


def verify_observations(expected):
    rows = json.loads(psql(f"""
SET TRANSACTION READ ONLY;
SELECT COALESCE(json_agg(row_to_json(t) ORDER BY observation_id), '[]'::json)
FROM public.historical_flood_observations t
WHERE source_sha256 = '{SOURCE_SHA256}';
"""))
    actual = {row["observation_id"]: row["fields"] for row in rows}
    if actual != expected or len(rows) != len(expected) or any(
        row["source_url"] != SOURCE_URL or row["event_id"] != row["fields"]["event_id"]
        for row in rows
    ):
        differences = sorted(key for key in expected.keys() | actual.keys()
                             if expected.get(key) != actual.get(key))
        raise ValueError(f"PostgreSQL readback differs in fields, record set, or provenance: {differences}")
    return f"Verified {len(rows)} observations across {len({r['event_id'] for r in rows})} events; all 42 fields match the prepared CSV."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared_csv", type=Path)
    parser.add_argument("--verify", action="store_true", help="compare stored rows with the CSV read-only")
    args = parser.parse_args()
    try:
        observations = read_observations(args.prepared_csv)
        operation = verify_observations if args.verify else import_observations
        print(operation(observations))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Flood inventory operation failed: psql exited with status {error.returncode}\n")
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Flood inventory operation failed: {error}\n")


if __name__ == "__main__":
    main()
