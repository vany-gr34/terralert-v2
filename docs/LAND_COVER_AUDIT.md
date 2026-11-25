# TERRALERT land-cover audit

**Verdict.** The linked raster is spatially usable for numeric-code pixel summaries. Its counts reproduce both indicator CSVs for all 11 pilot communes. Hold semantic class import and named percentages until the team confirms the source product, reference year, class legend, and treatment of code 0. PostgreSQL was accessed in a read-only transaction.

## Source and grid

- [occupation_sol_TERRALERT_26191_FIXED.tif](https://drive.google.com/file/d/1ssezCSd2s04ZVkiyfo0goAJ2l4990l6m/view), 45,902,110 bytes. SHA-256 `7a1597917c47f27c9ee25ec3cf3673f9279c0dac25e3c31c485605801086058a`.
- Single-band, uncompressed Float32 GeoTIFF, 2,900 columns × 3,955 rows. All samples were finite integers in the stored band despite the floating-point data type.
- GeoTIFF keys declare EPSG:26191, Merchich / Nord Maroc, horizontal metres and pixel-is-area registration. The north-up pixel size is 10 × 10 m. Affine coefficients in `(a,b,c,d,e,f)` order are `(10, 0, 444510, 0, -10, 580640)`. Outer bounds in west, south, east, north order are `(444510, 541090, 473510, 580640)` m.
- The TIFF declares `GDAL_NODATA=-9999`. It has no additional mask page, overview, local sidecar, color table, class names, source-product tag, acquisition year, or processing history. Its Drive modification date is November 21, 2026, which describes the file rather than the mapped land cover. The 10 m resolution agrees with the [ingestion plan](DATA_INGESTION.md).

## Codes and NoData

The full raster contains 11,469,500 pixels, of which 7,115,643 are valid under the file's metadata and 4,353,857 are NoData.

| Stored code | Full-raster count | File mask status |
| ---: | ---: | --- |
| -9999 | 4,353,857 | NoData |
| 0 | 918 | Unmasked, class meaning unresolved |
| 10 | 1,108,918 | Unmasked |
| 20 | 327,428 | Unmasked |
| 30 | 2,361,190 | Unmasked |
| 40 | 2,072,967 | Unmasked |
| 50 | 621,349 | Unmasked |
| 60 | 249,899 | Unmasked |
| 80 | 241,651 | Unmasked |
| 90 | 131,323 | Unmasked |

The TIFF puts **0 outside its NoData mask**. Both CSVs also count it
separately in `lc_0` and use `lc_NODATA` for NoData. This confirms
the literal encoding of the delivered file and prior summaries. An
unmasked zero could still represent background carried through from an
upstream product or an intentional recode. No class name is assigned
to it or to the other numeric codes.

## Commune coverage and counts

A pixel is counted for a commune when its centre falls inside the
stored EPSG:26191 polygon. Multipolygon parts are combined, and holes
are excluded. Each commune lies entirely within the rectangular
extent (100% footprint coverage for all 11). Counts describe centre
assignment, not fractional pixel overlap areas; NoData percentages use
all selected centres as their denominator. No selected centres belonged to multiple communes. One valid
centre lies outside the pilot union. The pilot contains **7,115,642
valid** and **962 NoData** pixel centres. All 918 zero-valued cells
are inside the pilot. NoData reaches its largest commune share in
Aquouass Briech, **0.0460%** of selected centres.

| Commune ID | Commune | NoData | 0 | 10 | 20 | 30 | 40 | 50 | 60 | 80 | 90 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MA-01-511-0103 | Bni Makada | 0 | 0 | 6,844 | 722 | 77,171 | 110,279 | 146,675 | 17,086 | 212 | 0 |
| MA-01-511-0105 | Mghogha | 1 | 321 | 46,565 | 8,794 | 246,000 | 66,532 | 117,188 | 23,688 | 2,307 | 154 |
| MA-01-511-0106 | Souani | 0 | 0 | 2,699 | 3 | 2,566 | 209 | 44,646 | 580 | 28 | 0 |
| MA-01-511-0107 | Médina | 1 | 378 | 256,745 | 21,963 | 190,414 | 91,148 | 166,308 | 30,569 | 8,530 | 194 |
| MA-01-511-0109 | Gueznaia | 91 | 101 | 123,331 | 12,173 | 233,515 | 101,467 | 86,422 | 67,380 | 34,257 | 15,701 |
| MA-01-511-0303 | Aquouass Briech | 280 | 0 | 34,924 | 5,225 | 177,036 | 215,938 | 9,977 | 42,953 | 48,975 | 73,719 |
| MA-01-511-0501 | Al Manzla | 264 | 0 | 213,639 | 101,034 | 318,987 | 245,367 | 1,353 | 4,704 | 21,817 | 448 |
| MA-01-511-0505 | Sebt Azzinate | 98 | 65 | 33,116 | 20,728 | 277,841 | 284,408 | 3,021 | 6,392 | 39,096 | 60 |
| MA-01-511-0507 | Dar Chaoui | 227 | 0 | 239,827 | 127,461 | 334,732 | 208,917 | 1,617 | 1,725 | 62,116 | 0 |
| MA-01-511-0517 | Laaouama | 0 | 53 | 10,335 | 1,497 | 160,168 | 334,218 | 21,701 | 6,443 | 5,438 | 136 |
| MA-01-511-0519 | Hjar Ennhal | 0 | 0 | 140,893 | 27,828 | 342,759 | 414,484 | 22,441 | 48,379 | 18,875 | 40,911 |

## Product, legend, and indicators

The 10 m spacing and nonzero code subset resemble ESA WorldCover.
ESA's product documentation provides a candidate legend and distinct
2020 v100 and 2021 v200 releases. Its thematic class list does not
define 0 as a land-cover class. If the team raster was derived from
WorldCover, file-valid zero and the upstream class list would require
explaining how background or NoData was handled. Resolution and a
matching code subset cannot establish lineage, reference year, or
whether the local processing changed the legend. [ESA product versions](https://esa-worldcover.org/en/data-access) · [ESA WorldCover v2 product manual, Map codes](https://worldcover2021.esa.int/data/docs/WorldCover_PUM_V2.0.pdf)

The earlier catalogue cell and note lookup returned HTTP 404, but used
a mistyped catalogue ID (ending `EV4` rather than the ingestion plan’s
`EVR4`). A recheck with the correct ID failed at the connector transport
(`HTTP request failed` for the connector backend); catalogue contents
remain unverified. The
ingestion plan gives the resolution and explicitly leaves provenance
and legend open. The two indicator CSVs contain 11 matching ISO IDs
and reproduce **every numeric code and NoData count** in the table.
Their shared counts show a reproducible pixel tally. They do not
identify the product, reference year, or authoritative legend.
`commune_indicators.csv` leaves urban, forest, and vegetation
percentages blank, while `indicators_occupation.csv` contains
published values. The audit did not recompute or endorse named
percentages without a confirmed legend. [Team catalogue](https://docs.google.com/spreadsheets/d/1DcHzrqA1H9TcGERAsNHMQTv8Vzh2PedQJHseyS8EVR4/edit) · [Commune indicators](https://drive.google.com/file/d/1NFXi2K1SM9tehEbkfSkrwtHzQL-6f43v/view) · [Occupation indicators](https://drive.google.com/file/d/1mBqQFnbW0NiU9RcnQdr42OUrx2kEtXrP/view)

The team needs to confirm the upstream product and version or source
tiles, reference year, any reprojection or recoding, what 0 means,
and the definitions of the three named indicator categories and their
denominators. For a numeric summary using the delivered mask, the
denominator would be all selected unmasked centres, including zeros,
with `-9999` counted separately. Semantic percentages may require a
different denominator if zero is confirmed to be background.

## Reproduce

Save the audited TIFF to `/tmp` and the two linked indicator CSVs to
`/tmp/terralert-drainage` with their original filenames. Run from the
project folder. The local script uses NumPy, tifffile, and Matplotlib.

```sh
sha256sum /tmp/occupation_sol_TERRALERT_26191_FIXED.tif
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /tmp/terralert-land-cover-communes.json <<'SQL'
BEGIN READ ONLY;
SELECT json_agg(row_to_json(c) ORDER BY commune_id)
FROM (
   SELECT commune_id, name_fr, ST_SRID(geom) AS srid, ST_AsGeoJSON(geom, 12)::json AS geometry
   FROM public.pilot_communes
) c;
ROLLBACK;
SQL
```

```sh
cat > /tmp/terralert-land-cover-audit.py <<'PY'
import csv
import json
from pathlib import Path

from matplotlib.path import Path as PolygonPath
import numpy as np
from tifffile import TiffFile

base = Path('/tmp')
raster = base / 'occupation_sol_TERRALERT_26191_FIXED.tif'
with TiffFile(raster) as tif:
    page = tif.pages[0]
    tags = page.geotiff_tags
    assert len(tif.pages) == 1 and not page.subifds and not page.is_mask
    assert tags['GTRasterTypeGeoKey'] == 1 and page.samplesperpixel == 1
    assert not any(Path(str(raster) + suffix).exists() for suffix in ('.msk', '.aux.xml'))
    sx, sy, _ = tags['ModelPixelScale']
    i, j, _, x, y, _ = tags['ModelTiepoint']
    west, north = x - i * sx, y + j * sy
    grid = page.asarray()
    epsg = int(tags['ProjectedCSTypeGeoKey'])
    nodata = float(page.tags[42113].value)
    print('GeoTIFF keys:', tags)
    print('Tag names:', [tag.name for tag in page.tags.values()])
    print('Data type and shape:', grid.dtype, grid.shape)
height, width = grid.shape
south, east = north - height * sy, west + width * sx
print('EPSG', epsg, 'affine', (sx, 0, west, 0, -sy, north))
print('bounds', (west, south, east, north), 'NoData', nodata)
assert np.isfinite(grid).all() and np.equal(grid, np.trunc(grid)).all()
codes, counts = np.unique(grid.astype('int32'), return_counts=True)
global_counts = dict(zip(codes.tolist(), counts.tolist()))
print('Global raw counts:', global_counts)

communes = json.loads((base / 'terralert-land-cover-communes.json').read_text())
assert len({c['commune_id'] for c in communes}) == len(communes) == 11
maps = []
for filename in ('commune_indicators.csv', 'indicators_occupation.csv'):
    with (base / 'terralert-drainage' / filename).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len({row['ISO'] for row in rows}) == 11
    maps.append({row['ISO']: row for row in rows})
assert all(mapping.keys() == {c['commune_id'] for c in communes} for mapping in maps)
union = np.zeros(grid.shape, dtype=bool)
overlap_count = 0
report = []
codes = [code for code in global_counts if code != nodata]
for commune in communes:
    assert commune['srid'] == epsg
    geometry = commune['geometry']
    polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    vertices = np.array([v for poly in polygons for ring in poly for v in ring])
    xmin, ymin = vertices.min(axis=0)
    xmax, ymax = vertices.max(axis=0)
    covers = west <= xmin and south <= ymin and xmax <= east and ymax <= north
    col0 = max(0, int(np.floor((xmin-west)/sx)))
    col1 = min(width, int(np.ceil((xmax-west)/sx)))
    row0 = max(0, int(np.floor((north-ymax)/sy)))
    row1 = min(height, int(np.ceil((north-ymin)/sy)))
    xx, yy = np.meshgrid(west + (np.arange(col0, col1)+0.5)*sx,
                         north - (np.arange(row0, row1)+0.5)*sy)
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    selected = np.zeros(len(xy), dtype=bool)
    for polygon in polygons:
        inside = PolygonPath(polygon[0]).contains_points(xy)
        for hole in polygon[1:]:
            inside &= ~PolygonPath(hole).contains_points(xy)
        selected |= inside
    window = np.s_[row0:row1, col0:col1]
    selected = selected.reshape(xx.shape)
    overlap_count += int((union[window] & selected).sum())
    union[window] |= selected
    classes, frequency = np.unique(grid[window][selected].astype('int32'), return_counts=True)
    histogram = dict(zip(classes.tolist(), frequency.tolist()))
    by_code = {code: histogram.get(code, 0) for code in codes}
    missing = histogram.get(int(nodata), 0)
    key = commune['commune_id']
    expected = {'lc_NODATA': missing, **{f'lc_{code}': n for code, n in by_code.items()}}
    differences = [{field: n-int(mapping[key][field]) for field,n in expected.items()
                    if n != int(mapping[key][field])} for mapping in maps]
    report.append(dict(commune_id=key, name=commune['name_fr'], full_extent=bool(covers),
                       valid=sum(by_code.values()), nodata=missing, counts=by_code,
                       indicator_differences=differences))
print('Overlapping selected centres:', overlap_count)
print('Outside pilot valid centres:', int(((grid != nodata) & ~union).sum()))
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
MPLCONFIGDIR=/tmp/terralert-matplotlib python3 /tmp/terralert-land-cover-audit.py > /tmp/terralert-land-cover-results.txt
```

The result file lists the embedded GeoTIFF keys, full-raster histogram,
footprint and mask counts, and per-commune differences against both CSVs.
Every indicator difference map was empty.
