"""Verify and optionally store the audited Bni Makada CHIRPS example."""

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np
from netCDF4 import Dataset, num2date


COMMUNE_ID = "MA-01-511-0103"
DAY = "2020-01-06"
PRODUCT = "CHIRPS v3 Final SAT"
SOURCE_SHA256 = "7b128c8a98de510f7abfca29f80265b4e410bf4e294d72ebed4e674e0c0d92f8"


def cell_edges(centers):
    return np.r_[
        centers[0] - (centers[1] - centers[0]) / 2,
        (centers[:-1] + centers[1:]) / 2,
        centers[-1] + (centers[-1] - centers[-2]) / 2,
    ]


def cell_values(path):
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("SHA-256 does not match the audited 2020 NetCDF")
    with Dataset(path) as dataset:
        time = dataset["time"]
        dates = [day.strftime("%Y-%m-%d") for day in num2date(time[:], time.units, time.calendar)]
        rain = dataset["precipitation"]
        if rain.source != PRODUCT or rain.units != "mm/day" or dates.count(DAY) != 1:
            raise ValueError("unexpected CHIRPS product, units, or date")
        values = rain[dates.index(DAY)]
        x_edges = cell_edges(dataset["longitude"][:])
        y_edges = cell_edges(dataset["latitude"][:])
    cells = []
    mask = np.ma.getmaskarray(values)
    for (y, x), value in np.ndenumerate(values.data):
        # Only masked cells become SQL NULL. Numeric zero remains valid.
        missing = mask[y, x]
        if not missing and (not np.isfinite(value) or value < 0):
            raise ValueError(f"invalid rainfall at row {y}, column {x}")
        amount = "NULL" if missing else repr(float(value))
        cells.append(
            f"({y}, {x}, {x_edges[x]:.17g}, {y_edges[y+1]:.17g}, "
            f"{x_edges[x+1]:.17g}, {y_edges[y]:.17g}, {amount}::numeric)"
        )
    return ",\n".join(cells)


def psql(sql):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "db", "sh", "-c",
         'exec psql -XqAt --single-transaction -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -'],
        input=sql,
        encoding="utf-8", cwd=Path(__file__).resolve().parent,
    )


def calculate(cells):
    return json.loads(psql(f"""
WITH cells (grid_row, grid_col, west, south, east, north, rainfall) AS (
    VALUES {cells}
), commune AS MATERIALIZED (
    SELECT ST_Transform(geom, 6933) AS geom
    FROM public.pilot_communes WHERE commune_id = '{COMMUNE_ID}'
), cell_overlaps AS (
    SELECT grid_row, grid_col, rainfall,
           ST_Area(ST_Intersection(c.geom,
               ST_Transform(ST_MakeEnvelope(west, south, east, north, 4326), 6933)
           ))::numeric AS area_m2
    FROM cells CROSS JOIN commune c
    WHERE ST_IsValid(c.geom)
), contributions AS (
    SELECT *, rainfall * area_m2 AS contribution FROM cell_overlaps WHERE area_m2 > 0
), totals AS (
    SELECT json_agg(row_to_json(contributions) ORDER BY grid_row, grid_col) AS cells,
           sum(area_m2) AS footprint_m2,
           sum(area_m2) FILTER (WHERE rainfall IS NOT NULL) AS valid_m2,
           sum(contribution) AS weighted_total
    FROM contributions
)
SELECT json_build_object(
    'cells', cells, 'commune_m2', ST_Area(c.geom)::numeric,
    'footprint_m2', footprint_m2, 'valid_m2', valid_m2,
    'rainfall_mm_per_day', weighted_total / NULLIF(valid_m2, 0),
    'footprint_coverage', round(footprint_m2 / ST_Area(c.geom)::numeric, 12),
    'valid_rainfall_coverage', round(valid_m2 / ST_Area(c.geom)::numeric, 12)
)
FROM totals CROSS JOIN commune c;
"""), parse_float=Decimal)


def verify(summary):
    if not summary["cells"] or not summary["valid_m2"]:
        raise ValueError("no valid projected commune overlap with rainfall")
    cells = summary["cells"]
    valid_cells = [cell for cell in cells if cell["rainfall"] is not None]
    footprint = sum(cell["area_m2"] for cell in cells)
    valid = sum(cell["area_m2"] for cell in valid_cells)
    numerator = sum(cell["rainfall"] * cell["area_m2"] for cell in valid_cells)
    expected = {
        "footprint_m2": footprint,
        "valid_m2": valid,
        "rainfall_mm_per_day": numerator / valid,
        "footprint_coverage": footprint / summary["commune_m2"],
        "valid_rainfall_coverage": valid / summary["commune_m2"],
    }
    for key, value in expected.items():
        if abs(summary[key] - value) > Decimal("1e-12"):
            raise ValueError(f"independent recomputation disagrees for {key}")
    return numerator, expected["rainfall_mm_per_day"]


def store(summary):
    return psql(f"""
CREATE TABLE IF NOT EXISTS public.chirps_daily_commune_rainfall (
    commune_id text NOT NULL REFERENCES public.pilot_communes (commune_id),
    rainfall_date date NOT NULL,
    rainfall_mm_per_day numeric NOT NULL CHECK (rainfall_mm_per_day >= 0),
    footprint_coverage numeric NOT NULL CHECK (footprint_coverage BETWEEN 0 AND 1),
    valid_rainfall_coverage numeric NOT NULL CHECK (valid_rainfall_coverage BETWEEN 0 AND footprint_coverage),
    product_variant text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{{64}}$'),
    PRIMARY KEY (commune_id, rainfall_date, product_variant, source_sha256)
);
INSERT INTO public.chirps_daily_commune_rainfall AS stored
    (commune_id, rainfall_date, rainfall_mm_per_day, footprint_coverage,
     valid_rainfall_coverage, product_variant, source_sha256)
VALUES ('{COMMUNE_ID}', '{DAY}', {summary['rainfall_mm_per_day']},
        {summary['footprint_coverage']}, {summary['valid_rainfall_coverage']},
        '{PRODUCT}', '{SOURCE_SHA256}')
ON CONFLICT (commune_id, rainfall_date, product_variant, source_sha256)
DO UPDATE SET rainfall_mm_per_day = EXCLUDED.rainfall_mm_per_day,
              footprint_coverage = EXCLUDED.footprint_coverage,
              valid_rainfall_coverage = EXCLUDED.valid_rainfall_coverage
RETURNING row_to_json(stored);
""").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netcdf", type=Path)
    parser.add_argument("--store", action="store_true", help="store the independently verified result")
    args = parser.parse_args()
    try:
        summary = calculate(cell_values(args.netcdf))
        numerator, independent_mean = verify(summary)
        print(f"{COMMUNE_ID} | {DAY} | {PRODUCT} | SHA-256 {SOURCE_SHA256}")
        print("row,col,rainfall_mm_per_day,overlap_m2,contribution")
        for cell in summary["cells"]:
            print(",".join(str(cell[key]) for key in
                           ("grid_row", "grid_col", "rainfall", "area_m2", "contribution")))
        for key in ("commune_m2", "footprint_m2", "valid_m2", "footprint_coverage",
                    "valid_rainfall_coverage", "rainfall_mm_per_day"):
            print(f"{key}={summary[key]}")
        print(f"Independent recomputation: {numerator} / {summary['valid_m2']} = {independent_mean}")
        if args.store:
            print(store(summary))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"CHIRPS sample failed: psql exited with status {error.returncode}\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"CHIRPS sample failed: {error}\n")


if __name__ == "__main__":
    main()
