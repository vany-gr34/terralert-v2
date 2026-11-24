# CHIRPS 2020 audit

**Verdict.** Ready for import as the 2020 TERRALERT daily CHIRPS v3 Final SAT subset, using the documented WGS 84 interpretation for the spatial coordinates. All 366 dates and all 23,424 rainfall values passed the checks below. The grid footprint covers all 11 pilot communes under that interpretation. The file does not explicitly declare a datum and does not contain enough lineage metadata to reproduce the provider extract or verify its values against the upstream archive. Preserve the team file and its checksum as the source of this batch.

## Source and layout

- Drive file [CHIRPS_v3_TERRALERT_2020.nc](https://drive.google.com/file/d/1_b86diAOiPM-QNUiA7KM2bNAQigJ7Fez/view) in the [annual folder linked in the ingestion plan](https://drive.google.com/drive/folders/1rC8K0dnmQlYudyAgzq7d6ON5jEqK1Btf). The download was saved locally as `/tmp/CHIRPS_v3_TERRALERT_2020.nc`.
- Size 47,262 bytes. SHA-256 `7b128c8a98de510f7abfca29f80265b4e410bf4e294d72ebed4e674e0c0d92f8`.
- NetCDF4/HDF5 with no global attributes. The `float32 precipitation(time, latitude, longitude)` variable has shape `(366, 8, 8)`, units `mm/day`, source `CHIRPS v3 Final SAT`, and description `Daily precipitation over TERRALERT bounding box`. The SAT designation is from the variable metadata. UCSB distinguishes the satellite-based and reanalysis-based daily disaggregations. [UCSB CHIRPS v3 documentation](https://www.chc.ucsb.edu/data/chirps3)
- The one-dimensional `float64` spatial coordinates are named `latitude` and `longitude`, with no units attributes, grid mapping, CRS WKT, datum, or cell-bounds variables. Longitude increases eastward and latitude decreases southward. Their spacing is about 0.05° in each direction. For coverage, the axis names, coordinate ranges, and CHIRPS grid resolution support interpreting them as geographic longitude and latitude on WGS 84 (EPSG:4326). This is an audit assumption.

| Extent | West | South | East | North |
| --- | ---: | ---: | ---: | ---: |
| Coordinate centers | -6.024997408 | 35.474999635 | -5.674997402 | 35.824999640 |
| Cell edges | -6.049997408 | 35.449999634 | -5.649997402 | 35.849999640 |

Cell edges extend half a grid step past the outer centers. The shared axes define the same 8 × 8 grid for every day.

## Time and rainfall results

| Check | Observed result |
| --- | --- |
| Encoded time | `int64` offsets 0–365, `days since 2020-01-01 00:00:00`, `proleptic_gregorian` |
| Decoded range and cadence | 2020-01-01 through 2020-12-31 inclusive, one day between every consecutive sample |
| Dates | 366 total and 366 unique, no duplicates, missing dates, or dates outside 2020. February 29 occurs once. |
| Raw rainfall metadata | `_FillValue=-9999.0` as `float32`. No `missing_value`, `scale_factor`, or `add_offset` attributes. |
| Raw values | Zero occurrences of the fill sentinel, NaN, or negative values |
| Decoded values | 23,424 valid and finite, zero masked, zero negative, range 0 to approximately 106.35635 mm/day |
| Zero rainfall | 12,806 numeric zeros, all valid |
| Dates with no valid cells | None. Every date has 64 valid cells; no grid cell is missing on any date. |

## Commune coverage

The PostGIS query transformed each boundary from EPSG:26191 to EPSG:4326 and tested it against the cell-edge footprint using `ST_CoveredBy`. The reported area fractions use EPSG:26191. All 11 rows returned `full` and `100.000` percent. No commune was partly inside or outside.

| Commune ID | Commune |
| --- | --- |
| MA-01-511-0103 | Bni Makada |
| MA-01-511-0105 | Mghogha |
| MA-01-511-0106 | Souani |
| MA-01-511-0107 | Médina |
| MA-01-511-0109 | Gueznaia |
| MA-01-511-0303 | Aquouass Briech |
| MA-01-511-0501 | Al Manzla |
| MA-01-511-0505 | Sebt Azzinate |
| MA-01-511-0507 | Dar Chaoui |
| MA-01-511-0517 | Laaouama |
| MA-01-511-0519 | Hjar Ennhal |

The footprint check measures geographic containment. The separate rainfall mask check found zero missing cell-days anywhere in the grid.

## Reproduce the audit

The v1 files `/home/vany/TERRALERT/gis/chirps/validate.py` and `/home/vany/TERRALERT/tests/test_chirps.py` informed the date-order, grid-spacing, coverage, mask, zero, negative, and all-missing checks. The v1 validator accepts one georeferenced raster per day. This file has a single 3D rainfall variable and shared coordinate arrays, so the commands below inspect the NetCDF directly.

```sh
file /tmp/CHIRPS_v3_TERRALERT_2020.nc
wc -c /tmp/CHIRPS_v3_TERRALERT_2020.nc
sha256sum /tmp/CHIRPS_v3_TERRALERT_2020.nc
python3 - <<'PY'
from collections import Counter

import numpy as np
from netCDF4 import Dataset, num2date

with Dataset('/tmp/CHIRPS_v3_TERRALERT_2020.nc') as ds:
    print(ds)
    for variable in ds.variables.values():
        print(variable.name, variable.dtype, variable.dimensions,
              variable.shape, vars(variable))

    time = ds['time']
    offsets = time[:]
    dates = [day.strftime('%Y-%m-%d')
             for day in num2date(offsets, time.units, time.calendar)]
    expected = np.arange('2020-01-01', '2021-01-01', dtype='datetime64[D]').astype(str)
    print('dates', dates[0], dates[-1], len(dates), 'unique', len(set(dates)))
    print('steps in days', np.unique(np.diff(offsets)))
    print('duplicates', [day for day, count in Counter(dates).items() if count > 1])
    print('gaps', sorted(set(expected) - set(dates)),
          'extra', sorted(set(dates) - set(expected)), 'leap day', dates.count('2020-02-29'))

    for axis in ('longitude', 'latitude'):
        centers = np.asarray(ds[axis][:])
        steps = np.diff(centers)
        half = abs(steps.mean()) / 2
        print(axis, 'centers', centers.min(), centers.max(),
              'steps', steps.min(), steps.max(),
              'edges', centers.min() - half, centers.max() + half)

    rain = ds['precipitation']
    decoded = rain[:]
    mask = np.ma.getmaskarray(decoded)
    valid = decoded.compressed()
    rain.set_auto_maskandscale(False)
    raw = rain[:]
    print('raw', raw.size, 'fill', (raw == rain._FillValue).sum(),
          'NaN', np.isnan(raw).sum(), 'negative', (raw < 0).sum())
    print('decoded valid', valid.size, 'masked', mask.sum(),
          'zero', (valid == 0).sum(), 'negative', (valid < 0).sum(),
          'nonfinite', (~np.isfinite(valid)).sum(), 'range', valid.min(), valid.max())
    print('daily missing counts', Counter(mask.sum(axis=(1, 2))))
    print('all-missing dates', np.array(dates)[mask.all(axis=(1, 2))].tolist())
PY
```

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
WITH footprint AS (
  SELECT ST_MakeEnvelope(-6.04999740794301, 35.44999963417649,
                         -5.649997401982546, 35.84999964013696, 4326) AS geom
), communes AS (
  SELECT commune_id, name_fr, ST_Transform(geom, 4326) AS geom
  FROM public.pilot_communes
)
SELECT commune_id, name_fr,
       CASE WHEN ST_CoveredBy(c.geom, f.geom) THEN 'full'
            WHEN ST_Area(ST_Intersection(c.geom, f.geom)) = 0 THEN 'outside'
            ELSE 'partial' END AS coverage,
       round((100 * ST_Area(ST_Transform(ST_Intersection(c.geom, f.geom), 26191))
                  / NULLIF(ST_Area(ST_Transform(c.geom, 26191)), 0))::numeric, 3) AS covered_pct
FROM communes c CROSS JOIN footprint f
ORDER BY commune_id;
ROLLBACK;
SQL
```
