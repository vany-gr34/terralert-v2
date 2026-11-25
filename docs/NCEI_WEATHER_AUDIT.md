# NCEI Tangier station-weather audit

**Verdict:** suitable for a future provenance-preserving raw import of the observations actually present, **2000-11-01 00:00 UTC–2025-08-01 23:30 UTC**. It is not a complete 2000–2025 series. A unique station/timestamp key would lose reports: conflicting reports must remain visible. Under the conservative screening below, **360,615 unique timestamps** are usable and **8,507 local days** qualify for estimated observed daily minimum/maximum. These are sampled extrema, not certified daily extremes or a validated homogeneous climate series. No import or PostgreSQL access was performed. Meteostat was not opened.

## Source and station

- Source: [NCEI_Tangier_2000_2025.csv](https://drive.google.com/file/d/1DsBJhWCvjR2GSXBmh9GjsSFtNkDda_HL/view), in the [station-data folder](https://drive.google.com/drive/folders/1bIi-ZQKJOAJNyHddBD_CioKaCRjXjH6R) linked by `DATA_INGESTION.md`.
- Size: **83,045,411 bytes**. SHA-256: `d1d534a32ed5c907a491f5712379d6dc80786bbe68c05dd56539e07c52cd10a1`.
- **430,097 data rows**, all with 21 fields. There are 20 distinct header names because `REPORT_TYPE` appears twice (columns 8 and 18). The two columns agree on every row; a working schema can retain one only after asserting this equality. Preserve the original source file.
- One station ID, preserved as text: **60101099999** (USAF 601010 / WBAN 99999). All rows give latitude **35.726917**, longitude **−5.916889**, elevation **18.89**. No missing or varying coordinate values were found.
- Station names: `IBN BATOUTA, MO` (418,377 rows) and `TANGER IBN BATOUTA INTERNATIONAL, MA` (11,720 rows). Same station ID and coordinates; a name change alone is not evidence of relocation.
- Actual first/last timestamps are as above, and are also the first/last usable timestamps. Local endpoints are 2000-11-01 00:00+00:00 and **2025-08-02 00:30+01:00**. The final local day has only two usable readings and fails completeness.

## Producer encoding and screening

NCEI identifies `TMP` as dry-bulb temperature in [Global Hourly](https://www.ncei.noaa.gov/access/search/datasets/global-hourly/). The [ISD format specification](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf), pages 5–6 and 10–11, defines UTC observation time, station identifiers, geographic coordinates, and temperature/QC encoding. Signed temperature integers use tenths of °C; `+9999` is missing. Flags 1 and 5 passed all QC (5 denotes an NCEI source); 2 means suspect. Flag 9 denotes a gross-limit pass when the value exists, so missingness must be checked from the value, not the flag alone. Coordinates are degrees and elevation is metres. This file's coordinates are already decimal values: do not apply the fixed-width coordinate scaling again.

Observed `TMP` is `signed_value,quality_flag`: `+0095,1` decodes to 9.5°C. `DATE` is ISO text without a timezone suffix; it is interpreted as UTC according to the producer specification, not as Casablanca wall time. All rows parsed and all temperature fields matched the expected structure. Empty ancillary CSV cells are not zero; this audit only evaluates temperature.

| TMP flag | Rows | Audit handling |
| --- | ---: | --- |
| 1 | 425,808 | Retain nonmissing, in-range values |
| 5 | 727 | Retain nonmissing, in-range values |
| 2 | 125 | Exclude as suspect; preserve raw flag |
| 9 | 3,437 | All are `+9999,9`, hence missing |

Thus 426,660 rows have numeric temperatures and **426,535** pass the audit's strict flag/range screen (−93.2 to +61.8°C). There are no malformed/blank TMP values or other flags. Among accepted rows, 29 are zero and 33 are negative; both remain valid. After duplicate-conflict exclusion, the observed range is **−4.0 to 43.0°C**. `QUALITY_CONTROL` and `SOURCE` are separate metadata; neither substitutes for the per-temperature flag. Passing producer QC is not proof of physical correctness or homogeneity.

The CSV-specific help URL was attempted through the browser and direct curl. It returned inaccessible content / HTML rather than a PDF (`pdftotext` rejected it). The accessible producer ISD specification and Global Hourly field listing support the interpretation above. An attempted one-day NCEI API cross-check was also inaccessible; there is no claim of a fresh producer-data comparison or verified original export query.

## Duplicate and gap rules

There are **395,189 distinct station/timestamp pairs**, **34,908 duplicate groups** (two rows each), and **zero wholly identical data rows**. Of these groups, **31,108** contain more than one distinct accepted temperature. A future import must retain report type, original values/flags and source-row identity; no last-row-wins rule is justified.

For this audit only, equal accepted temperatures at a timestamp count once; one accepted value plus a missing/suspect value retains the accepted value; two different accepted values cause the whole timestamp to be excluded from daily estimates. No averaging, precision preference or report-type preference was imposed. Of the conflicting groups, 31,063 differ by at most 1°C, but 45 differ by more. For example, 2017-06-13 09:00 UTC has 17.0 and 23.1°C, both accepted flags. Small differences may reflect reporting precision, but this does not resolve all conflicts.

Reporting cadence is mixed, mostly half-hourly: successive distinct raw timestamps are 30 minutes apart 361,810 times and 60 minutes apart 26,369 times; other intervals also occur. Therefore “missing hours” below means **empty one-hour bins**, not missing expected CSV rows. Annual gaps use full UTC calendar years (including the uncovered edges of 2000 and 2025). `raw gap h` has no report; `usable gap h` has no accepted, nonconflicting observation; `longest h` is the longest run of those empty usable bins. No regular half-hour schedule is assumed.

## Counts by station and UTC year

All rows below are station **60101099999**. Valid rows precede timestamp conflict exclusion; usable times follow it. Duplicate groups equal extra duplicate rows in this file. Full-row exact duplicates are zero in every year.

| Year | Raw rows | Valid TMP rows | Missing TMP | Suspect | Duplicate groups | Conflicting times | Usable unique times |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2000 | 1,524 | 1,472 | 52 | 0 | 0 | 0 | 1,472 |
| 2001 | 8,705 | 8,345 | 360 | 0 | 2 | 1 | 8,343 |
| 2002 | 12,153 | 11,805 | 346 | 2 | 2 | 0 | 11,805 |
| 2003 | 15,739 | 15,391 | 346 | 2 | 1 | 0 | 15,391 |
| 2004 | 16,484 | 15,999 | 485 | 0 | 4 | 0 | 15,997 |
| 2005 | 16,372 | 16,347 | 21 | 4 | 30 | 21 | 16,296 |
| 2006 | 15,485 | 15,388 | 90 | 7 | 12 | 0 | 15,376 |
| 2007 | 16,505 | 16,467 | 29 | 9 | 8 | 2 | 16,459 |
| 2008 | 15,036 | 15,014 | 16 | 6 | 22 | 8 | 14,984 |
| 2009 | 16,078 | 15,977 | 97 | 4 | 13 | 4 | 15,960 |
| 2010 | 15,832 | 15,645 | 184 | 3 | 6 | 1 | 15,638 |
| 2011 | 15,615 | 15,457 | 154 | 4 | 8 | 1 | 15,448 |
| 2012 | 15,661 | 15,092 | 564 | 5 | 10 | 2 | 15,080 |
| 2013 | 17,476 | 17,223 | 238 | 15 | 1,876 | 1,663 | 13,702 |
| 2014 | 19,274 | 19,051 | 204 | 19 | 2,748 | 2,405 | 13,933 |
| 2015 | 19,804 | 19,751 | 51 | 2 | 2,806 | 2,505 | 14,442 |
| 2016 | 20,103 | 20,003 | 97 | 3 | 2,878 | 2,571 | 14,563 |
| 2017 | 20,094 | 20,040 | 49 | 5 | 2,873 | 2,589 | 14,581 |
| 2018 | 20,156 | 20,144 | 11 | 1 | 2,865 | 2,582 | 14,700 |
| 2019 | 20,202 | 20,180 | 20 | 2 | 2,878 | 2,558 | 14,746 |
| 2020 | 20,288 | 20,281 | 5 | 2 | 2,885 | 2,586 | 14,813 |
| 2021 | 20,034 | 20,033 | 0 | 1 | 2,834 | 2,526 | 14,673 |
| 2022 | 20,250 | 20,250 | 0 | 0 | 2,885 | 2,565 | 14,800 |
| 2023 | 20,048 | 20,014 | 17 | 17 | 2,847 | 2,552 | 14,624 |
| 2024 | 19,459 | 19,449 | 1 | 9 | 2,761 | 2,474 | 14,216 |
| 2025 | 11,720 | 11,717 | 0 | 3 | 1,654 | 1,492 | 8,573 |

## Local-day completeness

This is an explicit **pilot screening rule**, not an NCEI or WMO standard:

1. Convert UTC times to `Africa/Casablanca` using Python `zoneinfo` and the installed IANA tzdata **2026e**. Use successive local midnights converted to UTC to define the day. Do not assume a constant UTC offset.
2. Apply the QC and duplicate rules above. Divide the day into elapsed one-hour bins starting at local midnight; a repeated civil hour counts separately. Require at least `ceil(0.75 × day_hours)` occupied bins: 18 of 23, 18 of 24, or 19 of 25.
3. Require no interval longer than **3 elapsed hours** between consecutive usable observations or between observations and either midnight boundary. This prevents clustered readings from passing the rule.
4. For passing days, take the minimum and maximum of the usable samples. No interpolation or correction for missed between-sample extremes. These estimates can underestimate the true daily maximum and overestimate the true daily minimum.

Across 2000–2025, local calendar lengths are 9,448 ordinary days, 25 short days and 24 long days, totaling 9,497 days. **8,507 pass and 990 fail** (including days outside the source period). The daily output retains eligibility separately from sampled minima/maxima; any extrema printed for a failing day must not be used as a complete-day estimate.

UTC gap columns and local-day counts have different year boundaries intentionally. `days with data` counts days with at least one usable observation, not complete days.

| Year | Raw gap h | Usable gap h | Longest h | Local days with data | Eligible local days / calendar days |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2000 | 7,332 | 7,340 | 7,320 | 61 | 61 / 366 |
| 2001 | 201 | 538 | 23 | 365 | 328 / 365 |
| 2002 | 385 | 481 | 41 | 364 | 336 / 365 |
| 2003 | 435 | 485 | 72 | 361 | 336 / 365 |
| 2004 | 150 | 227 | 24 | 366 | 350 / 366 |
| 2005 | 100 | 103 | 17 | 365 | 356 / 365 |
| 2006 | 642 | 687 | 112 | 361 | 301 / 365 |
| 2007 | 201 | 210 | 25 | 365 | 348 / 365 |
| 2008 | 571 | 577 | 40 | 363 | 298 / 366 |
| 2009 | 291 | 332 | 26 | 365 | 341 / 365 |
| 2010 | 372 | 461 | 99 | 361 | 334 / 365 |
| 2011 | 328 | 402 | 42 | 364 | 351 / 365 |
| 2012 | 238 | 526 | 34 | 366 | 344 / 366 |
| 2013 | 288 | 689 | 78 | 363 | 320 / 365 |
| 2014 | 283 | 475 | 25 | 365 | 318 / 365 |
| 2015 | 80 | 189 | 20 | 365 | 352 / 365 |
| 2016 | 43 | 168 | 11 | 366 | 357 / 366 |
| 2017 | 35 | 100 | 4 | 365 | 361 / 365 |
| 2018 | 30 | 54 | 4 | 365 | 362 / 365 |
| 2019 | 34 | 61 | 6 | 365 | 358 / 365 |
| 2020 | 30 | 54 | 7 | 366 | 364 / 366 |
| 2021 | 124 | 145 | 57 | 363 | 358 / 365 |
| 2022 | 46 | 61 | 6 | 365 | 362 / 365 |
| 2023 | 59 | 109 | 11 | 365 | 359 / 365 |
| 2024 | 370 | 404 | 120 | 359 | 345 / 366 |
| 2025 | 3,698 | 3,709 | 3,648 | 214 | 207 / 365 |

### Worked example: 2000-11-01

Casablanca is UTC+00:00 on this date. There are 23 accepted unique samples in 23 of 24 hour bins, exceeding the required 18. The absent 12:00 reading creates a two-hour interval from 11:00 to 13:00, the maximum gap; the interval from the final 23:00 sample to midnight is one hour. The day passes. Sampled Tmin is **8.0°C** (05:00 and 07:00); Tmax is **19.0°C** (13:00 and 14:00).

| Local/UTC hour | Temperature °C |
| --- | ---: |
| 00:00 | 9.5 |
| 01:00 | 10.0 |
| 02:00 | 9.0 |
| 03:00 | 8.8 |
| 04:00 | 9.0 |
| 05:00 | 8.0 |
| 06:00 | 8.2 |
| 07:00 | 8.0 |
| 08:00 | 11.0 |
| 09:00 | 14.2 |
| 10:00 | 18.0 |
| 11:00 | 18.0 |
| 13:00 | 19.0 |
| 14:00 | 19.0 |
| 15:00 | 18.3 |
| 16:00 | 18.0 |
| 17:00 | 17.0 |
| 18:00 | 13.9 |
| 19:00 | 12.0 |
| 20:00 | 10.0 |
| 21:00 | 9.6 |
| 22:00 | 9.0 |
| 23:00 | 9.0 |

### Long gaps

All runs of at least 24 empty usable hourly bins are listed below. End is exclusive. These are screen-dependent temperature availability gaps, not necessarily station outages. Runs are split at UTC year boundaries. The first and last runs are outside the file's actual period, not internal losses.

| Start UTC | End UTC, exclusive | Empty hours |
| --- | --- | ---: |
| 2000-01-01T00:00 | 2000-11-01T00:00 | 7320 |
| 2002-01-30T15:00 | 2002-02-01T08:00 | 41 |
| 2002-11-25T16:00 | 2002-11-26T18:00 | 26 |
| 2003-09-30T08:00 | 2003-10-01T09:00 | 25 |
| 2003-11-04T17:00 | 2003-11-07T15:00 | 70 |
| 2003-11-11T08:00 | 2003-11-14T08:00 | 72 |
| 2004-12-28T08:00 | 2004-12-29T08:00 | 24 |
| 2006-02-17T11:00 | 2006-02-18T14:00 | 27 |
| 2006-03-11T13:00 | 2006-03-12T16:00 | 27 |
| 2006-11-13T22:00 | 2006-11-18T14:00 | 112 |
| 2007-04-04T09:00 | 2007-04-05T10:00 | 25 |
| 2008-01-01T00:00 | 2008-01-02T00:00 | 24 |
| 2008-03-12T19:00 | 2008-03-14T07:00 | 36 |
| 2008-04-05T19:00 | 2008-04-07T11:00 | 40 |
| 2009-07-21T12:00 | 2009-07-22T14:00 | 26 |
| 2010-09-11T10:00 | 2010-09-13T11:00 | 49 |
| 2010-12-03T17:00 | 2010-12-07T20:00 | 99 |
| 2011-11-09T19:00 | 2011-11-11T13:00 | 42 |
| 2011-12-08T13:00 | 2011-12-09T23:00 | 34 |
| 2012-01-06T07:00 | 2012-01-07T16:00 | 33 |
| 2012-01-10T12:00 | 2012-01-11T16:00 | 28 |
| 2012-06-20T10:00 | 2012-06-21T14:00 | 28 |
| 2012-08-01T01:00 | 2012-08-02T11:00 | 34 |
| 2013-03-24T06:00 | 2013-03-27T12:00 | 78 |
| 2013-10-22T09:00 | 2013-10-23T09:00 | 24 |
| 2014-09-07T09:00 | 2014-09-08T10:00 | 25 |
| 2014-11-29T14:00 | 2014-11-30T15:00 | 25 |
| 2021-02-11T01:00 | 2021-02-13T10:00 | 57 |
| 2021-02-19T13:00 | 2021-02-21T15:00 | 50 |
| 2024-03-27T18:00 | 2024-04-01T18:00 | 120 |
| 2024-04-30T22:00 | 2024-05-01T22:00 | 24 |
| 2024-08-11T21:00 | 2024-08-12T22:00 | 25 |
| 2024-11-17T22:00 | 2024-11-21T22:00 | 96 |
| 2024-11-30T22:00 | 2024-12-01T22:00 | 24 |
| 2025-08-02T00:00 | 2026-01-01T00:00 | 3648 |

## Import suitability

- **Raw archive:** all 430,097 records in the actual source interval are suitable for future staging with original strings, flags, report metadata, ordinal/source checksum, and explicit duplicate status. Do not impose station/timestamp uniqueness or silently discard the repeated header without checking its values.
- **Screened temperature series:** the 360,615 accepted nonconflicting timestamps are a defensible conservative subset under this audit rule. Preserve the excluded records for later review. Source/flag interpretation is verified; report-priority resolution and climate homogenization are not.
- **Daily estimates:** use only the 8,507 days marked `eligible=True` by the reproducible output. No year is entirely complete under this rule. 2000 contributes only November–December (61 eligible days); 2025 contributes January–August 1 (207 eligible days), not the rest of the year. 2006 and 2008 are particularly incomplete (301/365 and 298/366). Even recent years have gaps: 2024 includes a 120-hour gap in March–April and a 96-hour gap in November. Do not use this file alone as an unqualified complete daily 2000–2025 baseline.

## Commands and verification

The original was fetched using the Google Drive connector:

```text
fetch(url="https://drive.google.com/drive/folders/1bIi-ZQKJOAJNyHddBD_CioKaCRjXjH6R")
fetch(url="https://drive.google.com/file/d/1DsBJhWCvjR2GSXBmh9GjsSFtNkDda_HL/view",
      download_raw_file=true, include_base64=false)
```

The returned authenticated download URL was passed to `curl -4 -L --fail --connect-timeout 15 --max-time 180 … -o /tmp/NCEI_Tangier_2000_2025.csv`. The private, expiring URL is intentionally omitted. The download completed at the expected 83,045,411 bytes. For reproduction, download the linked original into that path, then run:

```sh
python3 scripts/audit_ncei_weather.py /tmp/NCEI_Tangier_2000_2025.csv --output /tmp/ncei-audit
head -n 2 /usr/share/zoneinfo/tzdata.zi
```

The script hashes the file before analysis and refuses a different version. It uses only the Python standard library plus system timezone data, reads the original CSV, and writes local audit outputs only:

- `summary.json`: checksum, station metadata, QC counts, annual summaries, and worked example.
- `annual.csv`: full station/year counts and hourly gaps.
- `daily.csv`: all local dates, elapsed day length, occupied/required bins, maximum gap, eligibility, and sampled extrema.
- `gaps_24h.csv`: every long empty-hour run listed above.
- `conflicting_timestamps.json`: all 31,108 unresolved accepted-value conflicts.

An independent in-memory SQLite check of the original CSV returned `430097` rows, `395189` distinct station/timestamps and `360615` usable timestamps, agreeing with the audit. It did not connect to PostgreSQL. Reproduce it with:

```sh
python3 - <<'CHECK'
import csv, sqlite3
c = sqlite3.connect(':memory:')
c.execute('CREATE TABLE obs(station text, stamp text, temp integer, qc text)')
with open('/tmp/NCEI_Tangier_2000_2025.csv') as f:
    rows = csv.DictReader(f)
    c.executemany('INSERT INTO obs VALUES (?,?,?,?)',
        ((r['STATION'], r['DATE'], int(r['TMP'].split(',')[0]), r['TMP'].split(',')[1]) for r in rows))
print(c.execute('SELECT count(*), count(DISTINCT station||stamp) FROM obs').fetchone())
print(c.execute("""SELECT count(*) FROM (
  SELECT station,stamp FROM obs WHERE qc IN ('1','5') AND temp BETWEEN -932 AND 618
  GROUP BY station,stamp HAVING count(DISTINCT temp)=1)""").fetchone())
CHECK
```

Observed results were `(430097, 395189)` and `(360615,)`. Annual count reconciliation also passed: accepted + missing + suspect = 430,097, and annual usable counts sum to 360,615. A second full audit run after adding explicit timestamp-format validation returned the same totals. PostgreSQL was neither queried nor modified.
