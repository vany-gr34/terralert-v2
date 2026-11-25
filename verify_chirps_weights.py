"""Verify and export the commune-to-cell weights for the audited CHIRPS grid."""

import argparse
import json
from pathlib import Path
import subprocess

from import_chirps_sample import COMMUNE_ID, DAY, PRODUCT, SOURCE_SHA256, cell_values, psql


def inspect_weights(cells):
    return json.loads(psql(f"""
SET TRANSACTION READ ONLY;
WITH cells (grid_row, grid_col, west, south, east, north, rainfall) AS (
    VALUES {cells}
), grid AS MATERIALIZED (
    SELECT grid_row, grid_col, rainfall,
           ST_Transform(ST_MakeEnvelope(west, south, east, north, 4326), 6933) AS geom
    FROM cells
), projected AS MATERIALIZED (
    SELECT commune_id, name_fr, ST_SRID(geom) AS source_srid,
           ST_IsValidReason(geom) AS source_reason,
           ST_IsValidReason(ST_Transform(geom, 6933)) AS direct_reason,
           ST_NumGeometries(geom) AS source_parts,
           ST_Transform(ST_Segmentize(geom, 5), 6933) AS working,
           ST_Transform(ST_Segmentize(geom, 1), 6933) AS reference
    FROM public.pilot_communes
), geometry_checks AS MATERIALIZED (
    SELECT *, ST_IsValidReason(working) AS working_reason,
           ST_IsValidReason(reference) AS reference_reason,
           ST_NumGeometries(working) AS working_parts,
           ST_NumGeometries(reference) AS reference_parts,
           ST_Area(working) AS full_area_m2,
           ST_Area(reference) AS reference_area_m2,
           CASE WHEN ST_IsValid(working) AND ST_IsValid(reference)
                THEN ST_Area(ST_SymDifference(working, reference)) END AS difference_m2
    FROM projected
), cell_overlaps AS MATERIALIZED (
    SELECT commune_id, grid_row, grid_col, rainfall,
           ST_Area(ST_Intersection(working, grid.geom)) AS overlap_m2
    FROM geometry_checks JOIN grid ON working && grid.geom
    WHERE working_reason = 'Valid Geometry'
), weights AS (
    SELECT * FROM cell_overlaps WHERE overlap_m2 > 0
), totals AS (
    SELECT commune_id, count(*) AS cell_count, sum(overlap_m2) AS summed_overlap_m2,
           sum(rainfall * overlap_m2) / NULLIF(
               sum(overlap_m2) FILTER (WHERE rainfall IS NOT NULL), 0
           ) AS sample_rainfall_mm_per_day,
           json_agg(json_build_object('row', grid_row, 'col', grid_col,
                    'overlap_m2', overlap_m2) ORDER BY grid_row, grid_col) AS weights
    FROM weights GROUP BY commune_id
)
SELECT json_agg(row_to_json(report) ORDER BY commune_id)
FROM (
    SELECT commune_id, name_fr, source_srid, source_reason, direct_reason, working_reason,
           reference_reason, source_parts, working_parts, reference_parts,
           full_area_m2, reference_area_m2, full_area_m2 - reference_area_m2 AS area_delta_m2,
           difference_m2, cell_count, summed_overlap_m2,
           summed_overlap_m2 / NULLIF(full_area_m2, 0) AS footprint_coverage, weights,
           CASE WHEN commune_id = '{COMMUNE_ID}' THEN sample_rainfall_mm_per_day END
               AS bni_makada_sample_mm_per_day
    FROM geometry_checks LEFT JOIN totals USING (commune_id)
) report;
"""))


def issues_for(row):
    # A sub-square-metre comparison with a floor for floating-point noise.
    tolerance = max(0.01, row["full_area_m2"] * 1e-9)
    row["area_tolerance_m2"] = tolerance
    issues = []
    if row["source_srid"] != 26191 or any(
        row[key] != "Valid Geometry" for key in ("source_reason", "working_reason", "reference_reason")
    ):
        issues.append("unexpected source CRS or invalid geometry")
    if not row["source_parts"] == row["working_parts"] == row["reference_parts"]:
        issues.append("polygon-part count changed")
    if row["difference_m2"] is None or row["difference_m2"] > tolerance:
        issues.append("symmetric difference exceeds area tolerance or cannot be measured")
    if abs(row["area_delta_m2"]) > tolerance:
        issues.append("working and reference areas differ beyond tolerance")
    overlap = row["summed_overlap_m2"]
    if overlap is None or abs(overlap - row["full_area_m2"]) > tolerance:
        issues.append("cell overlaps do not close to full commune area")
    for weight in row["weights"] or []:
        weight["fraction_of_commune"] = weight["overlap_m2"] / row["full_area_m2"]
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netcdf", type=Path)
    args = parser.parse_args()
    try:
        rows = inspect_weights(cell_values(args.netcdf)) or []
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"PostGIS verification failed with status {error.returncode}\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot verify CHIRPS weights: {error}\n")
    for row in rows:
        row["issues"] = issues_for(row)

    baseline = 0.3476117492766563
    sample = next((row["bni_makada_sample_mm_per_day"] for row in rows
                   if row["commune_id"] == COMMUNE_ID), None)
    delta = sample - baseline if sample is not None else None
    accepted = len(rows) == 11 and not any(row["issues"] for row in rows)
    print(json.dumps({
        "source_sha256": SOURCE_SHA256, "product": PRODUCT, "sample_date": DAY,
        "weights_accepted": accepted, "sample_baseline_mm_per_day": baseline,
        "sample_delta_mm_per_day": delta, "communes": rows,
    }, ensure_ascii=False, indent=2))
    return 0 if accepted and delta is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
