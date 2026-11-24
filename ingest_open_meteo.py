"""Fetch and store one live Open-Meteo forecast for Tangier."""

import argparse
from datetime import datetime, timedelta
from decimal import Decimal
from http.client import HTTPException
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from weather_storage import reject_non_json_number, write_forecast


HOURLY_FIELDS = (
    "precipitation", "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
)
FORECAST_HOURS = 73  # Include the current hour and 72 subsequent hours.
HTTP_TIMEOUT_SECONDS = 15


def validate_forecast(forecast):
    if not isinstance(forecast, dict) or forecast.get("error"):
        raise ValueError("expected a forecast object")
    if forecast.get("utc_offset_seconds") != 0:
        raise ValueError("expected a zero UTC offset")
    hourly = forecast.get("hourly")
    units = forecast.get("hourly_units")
    if not isinstance(hourly, dict) or not isinstance(units, dict):
        raise ValueError("missing hourly data or units")
    times = hourly.get("time")
    if not isinstance(times, list) or len(times) < FORECAST_HOURS:
        raise ValueError(f"expected at least {FORECAST_HOURS} hourly timestamps")
    try:
        hours = [datetime.strptime(value, "%Y-%m-%dT%H:%M") for value in times]
    except (TypeError, ValueError) as error:
        raise ValueError("invalid hourly timestamp") from error
    if any(end - start != timedelta(hours=1) for start, end in zip(hours, hours[1:])):
        raise ValueError("hourly timestamps are not consecutive")
    for field in ("time", *HOURLY_FIELDS):
        if not isinstance(units.get(field), str) or not units[field]:
            raise ValueError(f"missing hourly unit for {field}")
    for field in HOURLY_FIELDS:
        series = hourly.get(field)
        if not isinstance(series, list) or len(series) != len(times):
            raise ValueError(f"expected one {field} value per hour")
        if any(value is not None and type(value) not in (int, Decimal) for value in series):
            raise ValueError(f"expected numbers or nulls for {field}")


def fetch_forecast(latitude, longitude):
    query = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "UTC",
        "forecast_hours": FORECAST_HOURS,
    })
    with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=HTTP_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"unexpected HTTP status {response.status}")
        payload = response.read().decode("utf-8")
    forecast = json.loads(payload, parse_float=Decimal, parse_constant=reject_non_json_number)
    validate_forecast(forecast)
    return payload, forecast


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        payload, forecast = fetch_forecast(35.76, -5.83)
    except (OSError, HTTPException, ValueError) as error:
        parser.exit(1, f"Open-Meteo request failed: {error}\n")

    try:
        result = write_forecast(payload, "open_meteo", False, read_back=True)
    except OSError as error:
        parser.exit(1, f"Cannot run Docker Compose: {error}\n")
    if result.returncode:
        parser.exit(result.returncode, "Forecast write or readback failed. See the database or Docker error above.\n")
    try:
        row = json.loads(result.stdout, parse_float=Decimal)
    except ValueError as error:
        parser.exit(1, f"Cannot verify stored forecast: {error}\n")
    if row["payload"] != forecast or row["source"] != "open_meteo" or row["is_fixture"] is not False:
        parser.exit(1, f"Stored row {row['id']} differs from the expected forecast or metadata.\n")

    stored = row["payload"]
    times = stored["hourly"]["time"]
    print(json.dumps({
        "id": row["id"],
        "source": row["source"],
        "is_fixture": row["is_fixture"],
        "ingested_at": row["ingested_at"],
        "hourly_units": stored["hourly_units"],
        "first_forecast_utc": times[0],
        "last_forecast_utc": times[-1],
        "hourly_count": len(times),
        "payload_matches_response": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
