# Manual Open-Meteo batch

The batch reads the [version 1 sampling CSV](../config/open_meteo_points_v1.csv)
by default and requests 73 consecutive UTC hourly samples for each commune.
It generates a UUID for the run. All 11 responses must pass the shared
forecast checks and include valid returned coordinates before the
importer submits one PostgreSQL COPY. That statement inserts all 11
forecasts atomically. Forecast JSON is sent as originally received.

The manual command waits three seconds between communes. A socket
timeout, temporary DNS error, or unreachable network gets one retry after
three seconds. HTTP errors, including 429, and invalid responses stop
the run immediately. The transport keeps the operating system's default
address selection. [Open-Meteo usage terms](https://open-meteo.com/en/terms)

The migration adds nullable metadata so existing fixture and single-point
rows retain their original format. Batch rows include the run UUID,
commune ID, requested coordinates, returned coordinates, and the
database-generated ingestion time.

## Commands

From the project folder with the Compose database running, apply the
migration and run the batch. Record the UUID printed by the command.

```sh
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' < migrations/003_weather_forecast_batches.sql
python3 ingest_open_meteo_batch.py config/open_meteo_points_v1.csv
```

Replace the example value with the UUID printed by the batch.

```sh
run_id=1a05bbac-a112-4f4c-9087-b5b10edceb70
docker compose exec -T db sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v "run_id=$1" -f -' psql "$run_id" < sql/check_open_meteo_batch.sql
```

The read-only SQL shows the forecast count and bounds, any returned
coordinate pairs shared by more than one commune, each commune's
requested and returned coordinates, and a digest of pre-batch rows.

## Observed results

Live verification was blocked by network errors. The first attempt,
`3750d87d-0916-4135-912b-21023255d927`, stopped at Gueznaia
(`MA-01-511-0109`) with a temporary DNS resolution failure. The retry,
`05185ed7-dc83-4987-95d5-ba6b4769241c`, stopped at Mghogha
(`MA-01-511-0105`) with `Network is unreachable`. PostgreSQL returned
zero forecasts for each UUID. The live count, forecast range, and
shared returned coordinate groups remain unverified.

An end-to-end storage probe mocked all 11 HTTP responses, ran the real
COPY in an explicit transaction, and queried 11 forecasts for 11 unique
communes before rolling back. The probe left zero forecast rows.
Mocked I/O checks also confirmed that the single-point and fixture
commands still use the original three-column COPY. The original three
weather rows matched their previous digest `369c6283837fe6258eb5254af1fd093e`.

## Simulated failures

The following checks mock HTTP so the first response is valid and the
second request either fails or yields invalid JSON forecast content.
Each failure identified Mghogha (MA-01-511-0105), exited with status 1,
and the SQL count for the simulated run was zero.

```sh
python3 - <<'PY'
from datetime import datetime, timedelta
import io
import json
import subprocess
from unittest.mock import patch
from urllib.error import URLError
from uuid import UUID

import ingest_open_meteo as single
import ingest_open_meteo_batch as batch

run_id = UUID('00000000-0000-4000-8000-00000000006b')
times = [(datetime(2026, 11, 24) + timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M')
         for i in range(single.FORECAST_HOURS)]
forecast = {
    'latitude': 35.73, 'longitude': -5.83, 'utc_offset_seconds': 0,
    'hourly': {'time': times, **{field: [0, None] + [1] * 71 for field in single.HOURLY_FIELDS}},
    'hourly_units': {'time': 'iso8601', **dict(zip(single.HOURLY_FIELDS, ('mm', '°C', '%', 'km/h')))},
}
for failure in (URLError('simulated network failure'), io.BytesIO(b'{}')):
    if isinstance(failure, io.BytesIO):
        failure.status = 200
    first = io.BytesIO(json.dumps(forecast).encode())
    first.status = 200
    with patch('sys.argv', ['ingest_open_meteo_batch.py']), patch.object(batch, 'uuid4', return_value=run_id), \
         patch.object(single, 'urlopen', side_effect=[first, failure]) as requests:
        try:
            batch.main()
        except SystemExit as error:
            assert error.code == 1
        else:
            raise AssertionError('Expected the second commune to fail')
        assert requests.call_count == 2
    count = subprocess.check_output([
        'docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
        'exec psql -XAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"',
        'psql', f"SELECT count(*) FROM public.weather_forecasts WHERE run_id = '{run_id}'",
    ], text=True).strip()
    assert count == '0'
    print(f'Confirmed zero stored rows for simulated run {run_id}.')
PY
```

## Transport investigation

The reported run `3530698b-8609-4595-9e17-de30f35f504e` had zero rows
in PostgreSQL. The Mghogha request captured from the command before
editing was:

```text
https://api.open-meteo.com/v1/forecast?latitude=35.76731197&longitude=-5.76327024&hourly=precipitation%2Ctemperature_2m%2Crelative_humidity_2m%2Cwind_speed_10m&timezone=UTC&forecast_hours=73
```

The Python socket timeout was 15 seconds. From the same local execution
environment, with no configured HTTPS proxy, these probes ran in order
with three seconds between calls. Curl used `-4 --connect-timeout 15
--max-time 15`. The short probe asked for three hours of precipitation.
The Python IPv4 probe restricted address resolution for that process.

To repeat the full IPv4 curl comparison, set `url` to the exact URL
above and run:

```sh
curl -4 -sS --connect-timeout 15 --max-time 15 \
  --output /tmp/terralert-open-meteo-diagnostic.json \
  --write-out 'HTTP=%{http_code} elapsed=%{time_total}s dns=%{time_namelookup}s connect=%{time_connect}s TLS=%{time_appconnect}s first_byte=%{time_starttransfer}s\n' "$url"
sleep 3
python3 - <<'PY'
from time import monotonic
import ingest_open_meteo as meteo

start = monotonic()
try:
    _, forecast = meteo.fetch_forecast('35.76731197', '-5.76327024')
    print('HTTP 200, validated hours:', len(forecast['hourly']['time']))
except (OSError, ValueError) as error:
    print(repr(error), 'HTTP status:', getattr(error, 'code', None))
finally:
    print('Elapsed seconds:', round(monotonic() - start, 3))
PY
```

| Probe | Elapsed | HTTP status | Result |
| --- | ---: | ---: | --- |
| Short IPv4 curl | 15.002 s | No response (`000`) | `curl: (28) Connection timed out after 15002 milliseconds` |
| Full IPv4 curl | 15.003 s | No response (`000`) | `curl: (28) Connection timed out after 15002 milliseconds` |
| Full default Python | 1.366 s | 200 | 73 validated hours |
| Full process-only IPv4 Python | 15.027 s | No response | `URLError(TimeoutError('timed out'))` |

Curl completed DNS lookup in under 20 ms for both probes but recorded
no TCP connection or TLS handshake. A separate full-request sequence
for Bni Makada, Mghogha, and Souani, in CSV order and spaced by three
seconds, received HTTP 200 in 1.426, 5.348, and 4.353 seconds,
respectively. All three connections used IPv4 and returned 73 validated
hours. These observations show intermittent connectivity before HTTP
and demonstrate that the full Mghogha forecast can succeed. The short
sequence did not reproduce a sequence-specific failure or return an
HTTP rate-limit response.

The retry simulation recovered after one timeout and one retry. A repeat
timeout at Mghogha stopped after the single permitted retry. A simulated
429 stopped with no retry. Both terminal error paths reported the commune,
skipped storage, and left zero rows under
`00000000-0000-4000-8000-00000000006d`.

The subsequent live batch, `1a05bbac-a112-4f4c-9087-b5b10edceb70`,
recovered on the retry at both Mghogha and Souani. Aquouass Briech
(`MA-01-511-0303`) returned `[Errno 101] Network is unreachable` on
both attempts, and the command exited with status 1. The exact run-ID
query returned zero forecasts and zero communes, so there was no stored
UTC forecast range or shared-coordinate group to verify. The three
original rows still matched their prior digest.
