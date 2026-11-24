"""Load the audited 2015–2020 CHIRPS series using the verified spatial weights."""

import argparse
import csv
from datetime import date, timedelta
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

import numpy as np
from netCDF4 import Dataset, num2date

from import_chirps_sample import COMMUNE_ID, DAY, PRODUCT, SOURCE_SHA256, psql


ANNUAL_SHA256 = {
    2015: "60efa742e49c8476445856e1635d79680b909711c787ff1f17f3b0147fa39e3d",
    2016: "43e17f38afc9a96f781bab53637fe4d8db0d150f157eda8bc17e3e35b9b61a38",
    2017: "fd4b695bd39e50baa9fce1da35e4645bc523b4b612de9fbc262845980a8bbe1c",
    2018: "844af667ec89df9e60b1aea7c2ae2b993cda5c17d8c3d8aca86d0d38aee309d3",
    2019: "51c5608fd88ea27295c91fad5a381b54dfb5c94dacd01730e4668b64cd96a119",
    2020: SOURCE_SHA256,
}
BOUNDARY_DIGEST = "fc4c34a732bbf95d4e69c97f03c9a14b"


def annual_path(directory, year):
    return directory / f"CHIRPS_v3_TERRALERT_{year}.nc"


def read_weights(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    communes = report["communes"]
    if (report["weights_accepted"] is not True or report["source_sha256"] != SOURCE_SHA256
            or report["product"] != PRODUCT or len({c["commune_id"] for c in communes}) != 11
            or len(communes) != 11 or sum(len(c["weights"]) for c in communes) != 97):
        raise ValueError("expected the accepted 2020 report with 97 overlaps for 11 communes")
    for commune in communes:
        cells = [(w["row"], w["col"]) for w in commune["weights"]]
        areas = [w["overlap_m2"] for w in commune["weights"]]
        if (commune["issues"] or commune["full_area_m2"] <= 0
                or len(set(cells)) != len(cells)
                or any(not (0 <= r < 8 and 0 <= c < 8) for r, c in cells)
                or any(not np.isfinite(a) or a <= 0 for a in areas)
                or abs(sum(areas) - commune["full_area_m2"]) > commune["area_tolerance_m2"]):
            raise ValueError(f"invalid weight set for {commune['commune_id']}")
    return communes


def batch_csv(directory, communes):
    for year, expected in ANNUAL_SHA256.items():
        if sha256(annual_path(directory, year).read_bytes()).hexdigest() != expected:
            raise ValueError(f"{year} SHA-256 does not match the annual audit")
    with Dataset(annual_path(directory, 2020)) as baseline:
        axes = [baseline[name][:] for name in ("latitude", "longitude")]
    payload = io.StringIO(newline="")
    writer = csv.writer(payload, lineterminator="\n")
    for year, checksum in ANNUAL_SHA256.items():
        with Dataset(annual_path(directory, year)) as ds:
            if not all(np.array_equal(ds[name][:], axis)
                       for name, axis in zip(("latitude", "longitude"), axes)):
                raise ValueError(f"{year} grid differs from the verified 2020 grid")
            time = ds["time"]
            dates = [t.strftime("%Y-%m-%d") for t in num2date(time[:], time.units, time.calendar)]
            start, end = date(year, 1, 1), date(year + 1, 1, 1)
            expected_dates = [(start + timedelta(days=i)).isoformat()
                              for i in range((end - start).days)]
            rain = ds["precipitation"]
            if (dates != expected_dates or rain.source != PRODUCT or rain.units != "mm/day"
                    or rain.dimensions != ("time", "latitude", "longitude")):
                raise ValueError(f"{year} date sequence or rainfall metadata differs from the audit")
            values = rain[:]
        valid_values = values.compressed()
        if not np.all(np.isfinite(valid_values) & (valid_values >= 0)):
            raise ValueError(f"{year} has invalid unmasked rainfall")
        for commune in communes:
            weights = commune["weights"]
            rows, cols, areas = zip(*[(w["row"], w["col"], w["overlap_m2"]) for w in weights])
            cell_rain = values[:, rows, cols]
            valid_area = (~np.ma.getmaskarray(cell_rain)) @ np.asarray(areas)
            numerator = cell_rain.filled(0).astype(float) @ np.asarray(areas)
            full = commune["full_area_m2"]
            footprint = min(1.0, sum(areas) / full)
            for day, area, total in zip(dates, valid_area, numerator):
                mean = f"{total / area:.15f}" if area else None
                writer.writerow((commune["commune_id"], day, mean, f"{footprint:.12f}",
                                 f"{min(footprint, area / full):.12f}", PRODUCT, checksum))
    return payload.getvalue()


def load_batch(csv_data):
    checksums = ", ".join(f"({year}, '{digest}')" for year, digest in ANNUAL_SHA256.items())
    return psql(f"""
LOCK TABLE public.pilot_communes IN SHARE MODE;
LOCK TABLE public.chirps_daily_commune_rainfall IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE stage (
    commune_id text NOT NULL, rainfall_date date NOT NULL,
    rainfall_mm_per_day numeric CHECK (rainfall_mm_per_day >= 0),
    footprint_coverage numeric NOT NULL CHECK (footprint_coverage BETWEEN 0 AND 1),
    valid_rainfall_coverage numeric NOT NULL CHECK (valid_rainfall_coverage BETWEEN 0 AND footprint_coverage),
    product_variant text NOT NULL CHECK (product_variant = '{PRODUCT}'),
    source_sha256 text NOT NULL,
    CHECK ((rainfall_mm_per_day IS NULL) = (valid_rainfall_coverage = 0)),
    PRIMARY KEY (commune_id, rainfall_date)
);
\\copy stage FROM STDIN WITH (FORMAT csv)
{csv_data}\\.
CREATE TEMP TABLE expected_sources AS
SELECT * FROM (VALUES {checksums}) AS src(year, source_sha256);
DO $$
DECLARE conflicts text;
BEGIN
    IF (SELECT md5(string_agg(row_to_json(c)::text, '' ORDER BY commune_id))
        FROM public.pilot_communes c) IS DISTINCT FROM '{BOUNDARY_DIGEST}' THEN
        RAISE EXCEPTION 'Stored commune boundaries differ from the verified weight input';
    END IF;
    IF (SELECT count(*) FROM stage) <> 24112 OR EXISTS (
        SELECT c.commune_id, d.day::date, src.source_sha256
        FROM public.pilot_communes c
        CROSS JOIN generate_series(timestamp '2015-01-01', timestamp '2020-12-31', interval '1 day') d(day)
        JOIN expected_sources src ON src.year = extract(year FROM d.day)
        EXCEPT SELECT commune_id, rainfall_date, source_sha256 FROM stage
    ) THEN
        RAISE EXCEPTION 'Staged data differ from the expected commune, date, and annual checksum set';
    END IF;
    IF NOT EXISTS (SELECT FROM stage WHERE commune_id = '{COMMUNE_ID}'
                   AND rainfall_date = '{DAY}'
                   AND abs(rainfall_mm_per_day - 0.347613591974992) <= 1e-12) THEN
        RAISE EXCEPTION 'Staged Bni Makada sample differs from the verified weights';
    END IF;

    SELECT string_agg(format('%s %s (%s): existing=%s staged=%s',
                      commune_id, rainfall_date, source_sha256, old_value, new_value), E'\\n')
    INTO conflicts
    FROM (
        SELECT commune_id, rainfall_date, source_sha256,
               row(t.rainfall_mm_per_day, t.footprint_coverage, t.valid_rainfall_coverage) AS old_value,
               row(s.rainfall_mm_per_day, s.footprint_coverage, s.valid_rainfall_coverage) AS new_value
        FROM public.chirps_daily_commune_rainfall t
        LEFT JOIN stage s USING (commune_id, rainfall_date, product_variant, source_sha256)
        WHERE t.product_variant = '{PRODUCT}'
          AND t.source_sha256 IN (SELECT source_sha256 FROM expected_sources)
          AND (s.commune_id IS NULL OR
               (t.rainfall_mm_per_day, t.footprint_coverage, t.valid_rainfall_coverage)
               IS DISTINCT FROM
               (s.rainfall_mm_per_day, s.footprint_coverage, s.valid_rainfall_coverage))
          AND NOT (commune_id = '{COMMUNE_ID}' AND rainfall_date = '{DAY}'
                   AND source_sha256 = '{SOURCE_SHA256}'
                   AND t.rainfall_mm_per_day = 0.347611749276656327175544
                   AND t.footprint_coverage = 1 AND t.valid_rainfall_coverage = 1)
        ORDER BY commune_id, rainfall_date LIMIT 10
    ) unexpected;
    IF conflicts IS NOT NULL THEN
        RAISE EXCEPTION 'Unexpected existing rows (first 10): %', conflicts;
    END IF;
END
$$;
ALTER TABLE public.chirps_daily_commune_rainfall ALTER COLUMN rainfall_mm_per_day DROP NOT NULL;
WITH changed AS (
    INSERT INTO public.chirps_daily_commune_rainfall AS target
        (commune_id, rainfall_date, rainfall_mm_per_day, footprint_coverage,
         valid_rainfall_coverage, product_variant, source_sha256)
    SELECT commune_id, rainfall_date, rainfall_mm_per_day, footprint_coverage,
           valid_rainfall_coverage, product_variant, source_sha256 FROM stage
    ON CONFLICT (commune_id, rainfall_date, product_variant, source_sha256)
    DO UPDATE SET rainfall_mm_per_day = EXCLUDED.rainfall_mm_per_day
    WHERE target.rainfall_mm_per_day IS DISTINCT FROM EXCLUDED.rainfall_mm_per_day
    RETURNING 1
)
SELECT format('Staged %s rows; inserted or updated %s rows.',
              (SELECT count(*) FROM stage), count(*)) FROM changed;
""").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netcdf_directory", type=Path)
    parser.add_argument("verified_weights", type=Path)
    args = parser.parse_args()
    try:
        print(load_batch(batch_csv(args.netcdf_directory, read_weights(args.verified_weights))))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"CHIRPS batch rolled back: psql exited with status {error.returncode}\n")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Cannot prepare CHIRPS batch: {error}\n")


if __name__ == "__main__":
    main()
