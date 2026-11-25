"""Write raw forecast JSON through psql in the Compose database container."""

import csv
import io
from pathlib import Path
import subprocess


def reject_non_json_number(value):
    raise ValueError(f"{value} is not a valid JSON number")


def write_forecast(payload, source, is_fixture, *, read_back=False):
    return copy_forecasts(
        "source, is_fixture, payload", [(source, str(is_fixture).lower(), payload)],
        read_back=read_back,
    )


def write_forecast_batch(run_id, forecasts):
    return copy_forecasts(
        "source, is_fixture, payload, run_id, commune_id, requested_latitude, "
        "requested_longitude, returned_latitude, returned_longitude",
        [("open_meteo", "false", payload, run_id, *coordinates)
         for payload, coordinates in forecasts],
    )


def copy_forecasts(columns, rows, *, read_back=False):
    # Send the original text so Python never rounds numbers during serialization.
    row = io.StringIO(newline="")
    csv.writer(row).writerows(rows)
    command = [
        "docker", "compose", "exec", "-T", "db", "sh", "-c",
        'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"',
        "psql",
        "-c", f"COPY public.weather_forecasts ({columns}) FROM STDIN WITH (FORMAT csv)",
    ]
    if read_back:
        # currval is scoped to this psql session, even if other writers insert rows.
        command += [
            "-qAt", "-c", "SET TIME ZONE 'UTC'",
            "-c", "SELECT row_to_json(f) FROM weather_forecasts AS f "
            "WHERE id = currval(pg_get_serial_sequence('weather_forecasts', 'id'))",
        ]
    return subprocess.run(
        command, input=row.getvalue(), encoding="utf-8",
        stdout=subprocess.PIPE if read_back else None,
        cwd=Path(__file__).resolve().parent,
    )
