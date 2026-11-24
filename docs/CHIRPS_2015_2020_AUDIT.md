# TERRALERT CHIRPS annual audit, 2015–2020

The six team files are ready for a combined daily **CHIRPS v3 Final SAT** series under the WGS 84 interpretation documented in the [2020 baseline](CHIRPS_2020_AUDIT.md). Together they cover 2,192 consecutive dates from 2015-01-01 through 2020-12-31. No year-specific blocker was found. The audit read the NetCDF files and queried PostGIS in a read-only transaction.

## Annual results

All source links point to files in the [team Drive annual folder](https://drive.google.com/drive/folders/1rC8K0dnmQlYudyAgzq7d6ON5jEqK1Btf) listed in the [ingestion plan](DATA_INGESTION.md). Each row uses the common metadata and grid described below. The coverage count is the number of fully covered pilot communes.

| Year and Drive source | SHA-256 | Decoded dates, inclusive | Duplicate / missing dates | Valid cells / numeric zeros / maximum (mm/day) | Missing / negative cells | Coverage | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [2015](https://drive.google.com/file/d/1TOD3p_jb4d60E-78Zp996tsTnrarwHAH/view) | `60efa742e49c8476445856e1635d79680b909711c787ff1f17f3b0147fa39e3d` | 2015-01-01 to 2015-12-31, 365 | 0 / 0 | 23,360 / 12,037 / 70.51999 | 0 / 0 | 11/11 | Ready |
| [2016](https://drive.google.com/file/d/1cBQfmspkOMbBnFz2IIDaLHFwX2qNFrV2/view) | `43e17f38afc9a96f781bab53637fe4d8db0d150f157eda8bc17e3e35b9b61a38` | 2016-01-01 to 2016-12-31, 366, Feb 29 once | 0 / 0 | 23,424 / 12,554 / 112.00976 | 0 / 0 | 11/11 | Ready |
| [2017](https://drive.google.com/file/d/1RN_iyirQJdHLepDNAAuNxyNSOGqq2AyM/view) | `fd4b695bd39e50baa9fce1da35e4645bc523b4b612de9fbc262845980a8bbe1c` | 2017-01-01 to 2017-12-31, 365 | 0 / 0 | 23,360 / 12,748 / 94.11767 | 0 / 0 | 11/11 | Ready |
| [2018](https://drive.google.com/file/d/1huDtdL0p_2vue8MrVHJZEWLJ6ewF1ZBd/view) | `844af667ec89df9e60b1aea7c2ae2b993cda5c17d8c3d8aca86d0d38aee309d3` | 2018-01-01 to 2018-12-31, 365 | 0 / 0 | 23,360 / 12,064 / 73.73247 | 0 / 0 | 11/11 | Ready |
| [2019](https://drive.google.com/file/d/146VuLGwGuIVVtyxYPFZViApr4L-lVhM-/view) | `51c5608fd88ea27295c91fad5a381b54dfb5c94dacd01730e4668b64cd96a119` | 2019-01-01 to 2019-12-31, 365 | 0 / 0 | 23,360 / 12,382 / 51.57329 | 0 / 0 | 11/11 | Ready |
| [2020](https://drive.google.com/file/d/1_b86diAOiPM-QNUiA7KM2bNAQigJ7Fez/view) | `7b128c8a98de510f7abfca29f80265b4e410bf4e294d72ebed4e674e0c0d92f8` | 2020-01-01 to 2020-12-31, 366, Feb 29 once | 0 / 0 | 23,424 / 12,806 / 106.35635 | 0 / 0 | 11/11 | Ready |

- **Product and units.** Each NetCDF4 file declares `precipitation.source = "CHIRPS v3 Final SAT"` and `precipitation.units = "mm/day"`. The data are `float32` with dimensions `(time, latitude, longitude)`, and there are no global attributes. The files do not carry an upstream artifact identifier or extraction history, so the variant is confirmed from file metadata and the values were not independently checked against the provider archive.
- **Difference from v1.** The v1 downloader at `/home/vany/TERRALERT/gis/chirps/download.py` uses the upstream `daily/final/rnl` archive and `chirps-v3.0.rnl.*.tif` filenames. SAT and RNL use different inputs to distribute pentadal totals across days. A combined 2015–2020 series can use the six SAT files as one cohort. Keep the v1 RNL samples separate so daily differences between the variants do not become apparent changes in the series. [UCSB CHIRPS v3 product documentation](https://www.chc.ucsb.edu/data/chirps3)
- **Time.** Each file has an `int64` time axis in days since January 1 of its year at 00:00:00, with the `proleptic_gregorian` calendar. Every consecutive step is one day. No file has a date outside its expected year.
- **Grid.** Both coordinate arrays match 2020 exactly, element by element and in the same order. Each file has eight longitude centers increasing from −6.024997408 to −5.674997402 and eight latitude centers decreasing from 35.824999640 to 35.474999635. The signed increments are approximately +0.05° and −0.05°, respectively. Half-cell extensions give the shared footprint `(west, south, east, north) = (-6.049997408, 35.449999634, -5.649997402, 35.849999640)`. No file declares a grid mapping, datum, CRS, coordinate units, or bounds variables.
- **Rainfall.** All six files declare a `float32` `_FillValue=-9999.0` without `missing_value`, `scale_factor`, or `add_offset` attributes. The raw sentinel, NaN, and raw negatives each occur zero times in every file. After decoding, every day has 64 finite valid cells, no masked values, and no negatives. All annual minima are zero, and the counts of valid numeric zeros are in the table.
- **Geographic coverage.** A common footprint query applies to all six files because their axes match exactly. PostGIS transformed all 11 stored boundaries from EPSG:26191 to the assumed EPSG:4326 and returned `communes = 11`, `full = 11`, and a null exception list. No commune is partly inside or outside. This geometric check is independent of the rainfall mask check.

## Reproduce the checks

Place the Drive files in `/tmp` under their original names. The following loop uses the same NetCDF decoding and mask checks as the 2020 audit and continues if an individual file cannot be inspected.

```sh
sha256sum /tmp/CHIRPS_v3_TERRALERT_20{15,16,17,18,19,20}.nc
python3 - <<'PY'
from collections import Counter

import numpy as np
from netCDF4 import Dataset, num2date

def inspect(year, reference):
    with Dataset(f'/tmp/CHIRPS_v3_TERRALERT_{year}.nc') as ds:
        print(ds.data_model, vars(ds), {k: len(v) for k, v in ds.dimensions.items()})
        print([(v.name, str(v.dtype), v.dimensions, vars(v)) for v in ds.variables.values()])
        for name, baseline in zip(('longitude', 'latitude'), reference):
            axis = np.asarray(ds[name][:])
            step = np.diff(axis)
            half = abs(step.mean()) / 2
            print(name, axis.tolist(), 'step', np.unique(step),
                  'exact match', np.array_equal(axis, baseline),
                  'edges', (axis.min() - half, axis.max() + half))
        t = ds['time']
        dates = np.array([d.strftime('%Y-%m-%d') for d in num2date(t[:], t.units, t.calendar)])
        expected = np.arange(f'{year}-01-01', f'{year+1}-01-01', dtype='datetime64[D]').astype(str)
        print('dates', dates[0], dates[-1], len(dates), len(set(dates)),
              'step', np.unique(np.diff(dates.astype('datetime64[D]'))),
              'duplicates', [d for d, n in Counter(dates).items() if n > 1],
              'missing', sorted(set(expected) - set(dates)),
              'extra', sorted(set(dates) - set(expected)),
              'leap day', int(sum(dates == f'{year}-02-29')))
        rain = ds['precipitation']
        decoded = rain[:]
        mask = np.ma.getmaskarray(decoded)
        valid = decoded.compressed()
        rain.set_auto_maskandscale(False)
        raw = rain[:]
        print('raw total/fill/NaN/negative', raw.size, (raw == rain._FillValue).sum(),
              np.isnan(raw).sum(), (raw < 0).sum())
        print('decoded valid/masked/zero/negative/nonfinite/min/max',
              valid.size, mask.sum(), (valid == 0).sum(), (valid < 0).sum(),
              (~np.isfinite(valid)).sum(), valid.min(), valid.max())
        print('all-missing dates', dates[mask.all(axis=(1, 2))].tolist(),
              'daily missing counts', dict(Counter(mask.sum(axis=(1, 2)).tolist())))

with Dataset('/tmp/CHIRPS_v3_TERRALERT_2020.nc') as ds:
    reference = [np.asarray(ds[k][:]) for k in ('longitude', 'latitude')]
for year in range(2015, 2021):
    print(year)
    try:
        inspect(year, reference)
    except Exception as error:
        print(type(error).__name__, error)
PY
```

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
WITH footprint AS (
  SELECT ST_MakeEnvelope(-6.04999740794301, 35.44999963417649,
                         -5.649997401982546, 35.84999964013696, 4326) AS geom
), coverage AS (
  SELECT commune_id, ST_CoveredBy(ST_Transform(c.geom, 4326), f.geom) AS covered
  FROM public.pilot_communes c CROSS JOIN footprint f
)
SELECT count(*) AS communes, count(*) FILTER (WHERE covered) AS full,
       array_agg(commune_id ORDER BY commune_id) FILTER (WHERE covered IS NOT TRUE) AS exceptions
FROM coverage;
ROLLBACK;
SQL
```
