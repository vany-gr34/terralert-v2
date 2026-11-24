# TERRALERT terrain audit

**Verdict.** The linked DEM and slope raster can be used together for descriptive commune summaries based on these exact file hashes. Their grids and valid-data masks match, and a degree-based Horn recalculation from the linked DEM reproduces every slope pixel tested with a complete neighborhood. The reported catalogue maximum of 596 remains unresolved. The DEM's physical vertical units and datum and the slope's formal processing lineage are undocumented in the files. Retain those limitations for summaries that depend on absolute elevation or documented provenance.

## Source files

| Drive source | Bytes | SHA-256 |
| --- | ---: | --- |
| [DEM_TERRALERT_26191_NODATA.tif](https://drive.google.com/file/d/1k2Jjt9yiS27kmWbyV4MDKuMchqFjDPF7/view) | 5,106,232 | `4e71e653f5ff3f606992fd0698dbd880a7807edfd217f36ce2ba38a2d9ad8534` |
| [slope_degrees_11_communes.tif](https://drive.google.com/file/d/1Jd_vg_geaaIssOo7irG2v_ZlHhQDuGrP/view) | 5,106,232 | `fedb095a0e168fae04d414ae4a3851ef491f0a681630eb01a94020ca774d0fe7` |

Both are the downloads linked in the [ingestion plan](DATA_INGESTION.md). The slope file's Drive metadata lookup returned HTTP 404, but an authenticated raw-file fetch for the same ID returned the named TIFF. The team catalogue's spreadsheet metadata was accessible. Its cell and note requests failed with 404 or 429, so this audit could not independently retrieve the catalogue's method or source version behind the reported 0–596 figure. No matching processing notes were found in the local project material reviewed. [Team catalogue](https://docs.google.com/spreadsheets/d/1DcHzrqA1H9TcGERAsNHMQTv8Vzh2PedQJHseyS8EV4/edit)

## Grid, masks, and range

The GeoTIFF keys of both files declare **EPSG:26191, Merchich / Nord Maroc**, with horizontal units in metres and pixel-is-area registration. Both are single-band Float32 rasters, **967 columns × 1,319 rows**. Pixels measure **30 × 30 m**.

- North-up affine coefficients `(30, 0, 444510, 0, -30, 580650)` in `(a,b,c,d,e,f)` order.
- Outer bounds in west, south, east, north order `(444510, 541080, 473520, 580650)` metres.
- Each declares `GDAL_NODATA=-9999`. Neither has a separate TIFF mask page or overview. There were no nonfinite values and no accompanying local mask sidecars.
- Pixelwise mask comparison returned **790,724 valid in both**, **484,749 NoData in both**, **0 DEM-only valid**, and **0 slope-only valid**.

| Raster | Exhaustive valid-pixel range | Valid zero cells |
| --- | ---: | ---: |
| DEM | 0–633 | 980 |
| Slope | 0–80.981369 | 15,440 |

The DEM maximum of 633 occurs at two cell centres, `(465195, 551145)` and `(465195, 551115)`, in Dar Chaoui. There are 188 valid pixels above 596, all within that commune, and 13 pixels equal to 596. The exhaustive maximum stayed at 633 after restricting to pilot-centre coverage or the common valid mask. No embedded GDAL statistics were present. Regular subsampling with strides 2, 4, 8, 16, and 32 gave maxima of 632, 632, 632, 603, and 572, respectively. Sampling can miss the peak, but none of these checks reproduced 596. No second hashed DEM version or documented statistics method establishes the cause.

## Commune coverage

The full rectangular extent covers every commune. Counts below use pixel centres inside the stored polygons in EPSG:26191, with holes excluded. The intersection of each commune's selected pixels with the valid-data mask is identical for both layers. These are raster cell counts and do not measure partial pixel areas along polygon edges.

| Commune ID | Commune | Valid cells in each | NoData cells in each | Valid DEM zeros | Valid slope zeros |
| --- | --- | ---: | ---: | ---: | ---: |
| MA-01-511-0103 | Bni Makada | 39,872 | 0 | 0 | 23 |
| MA-01-511-0105 | Mghogha | 56,846 | 0 | 76 | 94 |
| MA-01-511-0106 | Souani | 5,642 | 0 | 0 | 7 |
| MA-01-511-0107 | Médina | 85,155 | 0 | 367 | 339 |
| MA-01-511-0109 | Gueznaia | 74,930 | 0 | 184 | 187 |
| MA-01-511-0303 | Aquouass Briech | 67,660 | 0 | 87 | 305 |
| MA-01-511-0501 | Al Manzla | 100,862 | 0 | 116 | 3,758 |
| MA-01-511-0505 | Sebt Azzinate | 73,839 | 0 | 58 | 111 |
| MA-01-511-0507 | Dar Chaoui | 108,506 | 0 | 76 | 9,768 |
| MA-01-511-0517 | Laaouama | 60,012 | 0 | 16 | 145 |
| MA-01-511-0519 | Hjar Ennhal | 117,400 | 0 | 0 | 703 |

## Units and processing lineage

- **DEM.** The horizontal metre unit is explicit. No vertical CRS, vertical datum, or elevation band unit is declared. The match with a unit-scale Horn calculation shows that the slope is consistent with treating DEM sample differences in the same units as the 30 m grid step. That is evidence of effective scale 1. It does not identify the DEM's physical vertical datum or certify its source product.
- **Slope.** The filename indicates degrees. There is no embedded band-unit or derivation tag. Using the audited DEM and 30 m spacing, Horn slope computed as `degrees(atan(hypot(dx, dy)))` matched **783,363 of 783,363** common valid cells with complete DEM neighborhoods within `0.0001°`, with maximum absolute difference `0.000003101°`. A Zevenbergen–Thorne comparison matched 29,105 cells within the same tolerance and had a mean absolute difference of about 1.007°. This is strong numerical evidence for degrees and a Horn-equivalent derivation from the elevation samples in the linked DEM. The exact upstream file or command cannot be identified from matching values alone. The 7,361 remaining valid slope pixels have incomplete neighborhoods and were excluded from the numerical lineage check. [GDAL slope methods and units](https://gdal.org/en/stable/programs/gdaldem.html#slope)

## Reproduce the checks

Save the linked originals in `/tmp` using the filenames above. The PostGIS export uses a read-only transaction. The local analysis uses NumPy, tifffile, and Matplotlib and reads the original TIFFs without modification.

```sh
sha256sum /tmp/DEM_TERRALERT_26191_NODATA.tif /tmp/slope_degrees_11_communes.tif
docker compose exec -T db sh -c 'exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /tmp/terralert-terrain-communes.json <<'SQL'
BEGIN READ ONLY;
SELECT json_agg(row_to_json(c) ORDER BY commune_id)
FROM (
  SELECT commune_id, name_fr, ST_AsGeoJSON(geom, 12)::json AS geometry,
         ST_Area(geom) AS area_m2
  FROM public.pilot_communes
) c;
ROLLBACK;
SQL
```

```sh
cat > /tmp/terralert-terrain-audit.py <<'PY'
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from matplotlib.path import Path as PolygonPath
import numpy as np
from tifffile import TiffFile

def read(path):
    with TiffFile(path) as tif:
        page = tif.pages[0]
        tags = page.geotiff_tags
        sx, sy, _ = tags['ModelPixelScale']
        i, j, _, x, y, _ = tags['ModelTiepoint']
        west, north = x - i * sx, y + j * sy
        raster = page.asarray()
        height, width = raster.shape
        bounds = (west, north - height * sy, west + width * sx, north)
        transform = (sx, 0, west, 0, -sy, north)
        epsg = int(tags['ProjectedCSTypeGeoKey'])
        assert tags['GTRasterTypeGeoKey'] == 1 and epsg == 26191
        nd_tag = page.tags.get(42113)
        nodata = float(nd_tag.value) if nd_tag else None
        valid = np.isfinite(raster)
        if nodata is not None:
            valid &= raster != nodata
        page_list = list(tif.pages) + (list(page.pages) if page.pages else [])
        masks = [p for p in page_list if p.is_mask and p.shape == raster.shape]
        for mask in masks:
            valid &= mask.asarray().astype(bool)
        if Path(str(path) + '.msk').exists():
            raise ValueError('external mask needs separate inspection')
        print('file', path.name, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
        print('grid', epsg, raster.shape, raster.dtype, 'transform', transform, 'bounds', bounds, 'nodata', nodata)
        print('pages', [(p.shape, p.is_mask, p.is_reduced) for p in page_list], 'geo', tags)
        for tag in page.tags.values():
            if tag.code in (270, 305, 306, 315, 33432, 42112, 42113):
                print('metadata', tag.name, tag.value)
        v = raster[valid]
        print('full stats', 'valid', v.size, 'nodata/masked', raster.size-v.size,
              'valid zeros', int((v == 0).sum()), 'range', float(v.min()), float(v.max()))
        return raster, valid, transform, bounds

def coverage(commune, shape, transform, bounds):
    sx, _, x0, _, neg_sy, y0 = transform
    sy = -neg_sy
    geom = commune['geometry']
    polygons = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    selected = np.zeros(shape, dtype=bool)
    vertices = np.array([point for poly in polygons for ring in poly for point in ring])
    xmin, ymin = vertices.min(axis=0)
    xmax, ymax = vertices.max(axis=0)
    full = bounds[0] <= xmin and bounds[1] <= ymin and xmax <= bounds[2] and ymax <= bounds[3]
    col0 = max(0, int(np.floor((xmin-x0)/sx)))
    col1 = min(shape[1], int(np.ceil((xmax-x0)/sx)))
    row0 = max(0, int(np.floor((y0-ymax)/sy)))
    row1 = min(shape[0], int(np.ceil((y0-ymin)/sy)))
    xx, yy = np.meshgrid(x0 + (np.arange(col0,col1)+0.5)*sx,
                         y0 - (np.arange(row0,row1)+0.5)*sy)
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    area = np.zeros(len(xy), dtype=bool)
    for polygon in polygons:
        inside = PolygonPath(polygon[0]).contains_points(xy)
        for hole in polygon[1:]:
            inside &= ~PolygonPath(hole).contains_points(xy)
        area |= inside
    selected[row0:row1,col0:col1] = area.reshape(xx.shape)
    return selected, full

communes = json.loads(Path('/tmp/terralert-terrain-communes.json').read_text())
results = []
for arg in sys.argv[1:]:
    raster, valid, transform, bounds = read(Path(arg))
    union = np.zeros(raster.shape, dtype=bool)
    for c in communes:
        cells, full = coverage(c, raster.shape, transform, bounds)
        union |= cells
        v = raster[cells & valid]
        print('commune', c['commune_id'], c['name_fr'], full, int(cells.sum()), v.size,
              int((cells & ~valid).sum()), int((v == 0).sum()),
              (float(v.min()), float(v.max())) if v.size else None)
    if Path(arg).name.startswith('DEM'):
        for label, mask in [('inside', union), ('outside', ~union)]:
            v = raster[valid & mask]
            print('DEM', label, 'valid', v.size, 'above596', int((v > 596).sum()),
                  'max', float(v.max()) if v.size else None)
        maximum = raster[valid].max()
        print('DEM max centers', [(transform[2]+(c+.5)*transform[0],
                                   transform[5]+(r+.5)*transform[4])
                                  for r,c in np.argwhere(valid & (raster == maximum))])
    results.append((raster.shape, transform, valid))
if len(results) == 2:
    left, right = results
    print('aligned grid', left[:2] == right[:2])
    if left[:2] == right[:2]:
        a,b = left[2],right[2]
        print('masks', 'both valid', int((a&b).sum()), 'DEM only', int((a&~b).sum()),
              'slope only', int((~a&b).sum()), 'both invalid', int((~a&~b).sum()))
PY
MPLCONFIGDIR=/tmp/terralert-matplotlib python3 /tmp/terralert-terrain-audit.py \
  /tmp/DEM_TERRALERT_26191_NODATA.tif /tmp/slope_degrees_11_communes.tif
```

```sh
python3 - <<'PY'
import numpy as np
from tifffile import imread

dem = imread('/tmp/DEM_TERRALERT_26191_NODATA.tif').astype('float64')
slope = imread('/tmp/slope_degrees_11_communes.tif').astype('float64')
svalid = slope != -9999
print('nonfinite DEM/slope', (~np.isfinite(dem)).sum(), (~np.isfinite(slope)).sum())
print('DEM equal to 596', (dem == 596).sum())
print('DEM above 596', (dem > 596).sum(), 'paired', ((dem > 596) & svalid).sum())
for step in (2, 4, 8, 16, 32):
    print('stride and max', step, dem[::step, ::step].max())

tiles = [dem[i:i+dem.shape[0]-2, j:j+dem.shape[1]-2]
         for i in range(3) for j in range(3)]
a, b, c, d, e, f, g, h, i = tiles
full = np.logical_and.reduce([t != -9999 for t in tiles]) & svalid[1:-1, 1:-1]
reference = slope[1:-1, 1:-1][full]
for name, dx, dy in (
    ('Horn', (c+2*f+i-a-2*d-g)/240, (g+2*h+i-a-2*b-c)/240),
    ('Zevenbergen-Thorne', (f-d)/60, (h-b)/60),
):
    predicted = np.degrees(np.arctan(np.hypot(dx[full], dy[full])))
    error = np.abs(predicted-reference)
    print(name, 'count', len(error), 'within 1e-4', (error <= 1e-4).sum(),
          'median/mean/max abs', np.median(error), error.mean(), error.max())
PY
```
