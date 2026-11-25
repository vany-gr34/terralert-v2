# Open-Meteo pilot sampling plan

[Version 1 of the sampling CSV](../config/open_meteo_points_v1.csv) contains
one candidate forecast location for each of the 11 pilot communes. The
export uses `ST_PointOnSurface` on the stored EPSG:26191 boundaries and
transforms the points to EPSG:4326. It keeps the commune ID and French
name. Latitude and longitude are in decimal degrees, rounded to eight
decimal places for a reproducible file.

One interior point per commune is a reasonable first approximation for
testing coverage of all 11 communes with a small, fixed set of forecast
locations. It provides a point forecast associated with a commune.
Coastal exposure, elevation, and terrain can vary within a commune, so
the point does not measure a commune-wide average or capture local
extremes. The interior-point method makes no assumption about where
population or hazard exposure is concentrated.

## Regenerate and verify

Run from the project folder with the local Compose database running.

```sh
docker compose exec -T db sh -c 'exec psql -Xq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' < sql/export_open_meteo_points.sql > /tmp/terralert-open-meteo-points-v1.csv
cmp /tmp/terralert-open-meteo-points-v1.csv config/open_meteo_points_v1.csv
```

The [export query](../sql/export_open_meteo_points.sql) runs in a read-only
transaction and emits CSV on stdout. It validates the exact rounded
coordinates by reconstructing the EPSG:4326 points, transforming them
back to the source CRS, and testing strict containment with
`ST_Contains`. It reports checks on stderr.

| Check | Observed |
| --- | ---: |
| Candidate points | 11 |
| Distinct commune IDs | 11 |
| Rows missing latitude or longitude | 0 |
| Exported points strictly inside their source commune | 11 |

The CSV records candidate request coordinates. No forecast requests were
made while preparing the plan.
