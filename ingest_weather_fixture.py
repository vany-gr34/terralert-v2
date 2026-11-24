"""Store one synthetic weather forecast fixture in the local database."""

import argparse
import json
from pathlib import Path
import sys

from weather_storage import reject_non_json_number, write_forecast


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="path to a synthetic forecast JSON file")
    args = parser.parse_args()

    try:
        payload = args.fixture.read_text(encoding="utf-8")
        if not isinstance(json.loads(payload, parse_constant=reject_non_json_number), dict):
            raise ValueError("expected a JSON object")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot read fixture {args.fixture}: {error}\n")

    try:
        result = write_forecast(payload, "synthetic_tangier", True)
    except OSError as error:
        parser.exit(1, f"Cannot run Docker Compose: {error}\n")

    if result.returncode:
        print("Fixture ingestion failed. See the database or Docker error above.", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
