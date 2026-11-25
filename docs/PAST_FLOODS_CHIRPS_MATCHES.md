# Historical flood reports and CHIRPS rainfall

Run from the project folder with the local Compose database running.

```sh
docker compose exec -T db sh -c 'exec psql -X -x -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/check_flood_chirps_matches.sql
```

The query begins a read-only transaction and ends with `ROLLBACK`. It selects the audited flood inventory by its original SHA-256. It accepts a valid recorded observation date only when the date precision is `day`, the temporal uncertainty says the day is known, and the verification status does not require event-place corroboration. It screens dates against the audited 2015–2020 period. [Flood inventory audit](PAST_FLOODS_AUDIT.md)

For each exact-date candidate, the query projects the recorded EPSG:4326 point to the communes' EPSG:26191 CRS. The point and its recorded 1,000 m or 2,000 m uncertainty radius must fit inside one pilot commune, and no other pilot polygon may be within that radius. A populated commune name must agree with the spatial assignment after case and whitespace normalization. The commune ID is derived from the stored boundaries.

Eligible observations join to the recorded commune and date in CHIRPS v3 Final SAT, using the audited checksum for that year. Counts for eligible assignments and rainfall matches are reported separately so a missing rainfall row is visible. [CHIRPS daily import](CHIRPS_DAILY_IMPORT.md)

## Observed result

| Check | Count |
| --- | ---: |
| Exact-date observations in the audited period | 20 |
| Spatially ambiguous observations | 19 |
| Eligible commune assignments | 1 |
| Exploratory rainfall matches | 1 |

The query reproduced the audit without discrepancies. Observation `TF-0043` from event `E2016NOV21` matched **Médina (`MA-01-511-0107`) on 2016-11-21**. PostgreSQL returned **28.160565805237763 mm/day**, with footprint and valid rainfall coverage both `1.000000000000`. Confidence was **B**. The recorded location precision was **2,000 m**, and the representative point was **2,162.70 m** from the commune boundary. The inventory still flags study membership as provisional and precise flood geometry as unverified. [Original Le360 report](https://fr.le360.ma/societe/diapo-tanger-submergee-par-les-eaux-96411/)
