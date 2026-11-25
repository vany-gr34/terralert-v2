"""Fetch one manual Open-Meteo forecast batch for the 11 pilot communes."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
from errno import ENETUNREACH, ETIMEDOUT
from http.client import HTTPException
from pathlib import Path
from socket import EAI_AGAIN, gaierror
import sys
from time import sleep
from urllib.error import HTTPError, URLError
from uuid import uuid4

from ingest_open_meteo import fetch_forecast
from weather_storage import write_forecast_batch


DEFAULT_POINTS = Path(__file__).resolve().parent / "config/open_meteo_points_v1.csv"
REQUEST_PAUSE_SECONDS = 3


def fetch_with_retry(latitude, longitude, context):
    try:
        return fetch_forecast(latitude, longitude)
    except HTTPError:
        # In particular, leave a provider rate-limit response to the caller.
        raise
    except OSError as error:
        reason = error.reason if isinstance(error, URLError) else error
        transient = (
            isinstance(reason, TimeoutError)
            or (isinstance(reason, gaierror) and reason.errno == EAI_AGAIN)
            or (isinstance(reason, OSError) and reason.errno in (ENETUNREACH, ETIMEDOUT))
        )
        if not transient:
            raise
        print(f"{context}: {error}. Retrying once in {REQUEST_PAUSE_SECONDS}s.",
              file=sys.stderr, flush=True)
        sleep(REQUEST_PAUSE_SECONDS)
        return fetch_forecast(latitude, longitude)


def read_points(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != ["commune_id", "name", "latitude", "longitude"]:
            raise ValueError("expected CSV columns commune_id, name, latitude, longitude")
        points = list(reader)
    ids = {point["commune_id"] for point in points}
    if len(points) != 11 or len(ids) != 11 or any(not key or not key.strip() for key in ids):
        raise ValueError("expected exactly 11 unique nonblank commune IDs")
    for point in points:
        try:
            if None in point or not point["name"] or not (
                -90 <= Decimal(point["latitude"]) <= 90
                and -180 <= Decimal(point["longitude"]) <= 180
            ):
                raise ValueError("invalid sampling row or coordinates")
        except (TypeError, ValueError, InvalidOperation) as error:
            raise ValueError(f"{point['commune_id']}: invalid sampling row or coordinates") from error
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("points", nargs="?", type=Path, default=DEFAULT_POINTS)
    args = parser.parse_args()
    try:
        points = read_points(args.points)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Cannot read sampling points: {error}\n")

    run_id = uuid4()
    print(f"Run ID: {run_id}", flush=True)
    forecasts = []
    for index, point in enumerate(points):
        if index:
            sleep(REQUEST_PAUSE_SECONDS)
        commune_id = point["commune_id"]
        context = f"Run {run_id}: {commune_id} ({point['name']})"
        latitude, longitude = point["latitude"], point["longitude"]
        try:
            payload, forecast = fetch_with_retry(latitude, longitude, context)
            returned_latitude = forecast.get("latitude")
            returned_longitude = forecast.get("longitude")
            if not (type(returned_latitude) in (int, Decimal)
                    and type(returned_longitude) in (int, Decimal)
                    and -90 <= returned_latitude <= 90
                    and -180 <= returned_longitude <= 180):
                raise ValueError("invalid returned latitude or longitude")
        except (OSError, HTTPException, ValueError) as error:
            parser.exit(1, f"{context}: {error}\n")
        forecasts.append((payload, (commune_id, latitude, longitude,
                                    returned_latitude, returned_longitude)))

    try:
        # A single COPY statement commits all rows together or rolls them all back.
        result = write_forecast_batch(run_id, forecasts)
    except OSError as error:
        parser.exit(1, f"Run {run_id}: cannot run Docker Compose: {error}\n")
    if result.returncode:
        parser.exit(result.returncode, f"Run {run_id}: batch storage failed. See PostgreSQL error above.\n")


if __name__ == "__main__":
    main()
