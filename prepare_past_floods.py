"""Prepare or dry-run check the audited Raw/Floods CSV working copy."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import io
from pathlib import Path


SOURCE_SHA256 = "338324f793132fff83e3f1e303d08886ce184126fa84fae19f81fe268986d12f"
OLD_HEADER = "notes;;;;;;;"


def parse(data):
    with io.TextIOWrapper(io.BytesIO(data), encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream, strict=True))


def verify(source, working):
    header, *observations = parse(source)
    expected_header = ["notes" if name == OLD_HEADER else name for name in header]
    normalized_header, *normalized_rows = parse(working)
    if normalized_header != expected_header or normalized_rows != observations:
        raise ValueError("working copy changed the header unexpectedly or changed observation fields")
    if len(header) != 42 or len(set(normalized_header)) != 42 or len(normalized_rows) != 103:
        raise ValueError("expected 42 distinct fields and 103 observations")
    if any(len(row) != 42 for row in normalized_rows):
        raise ValueError("an observation does not have 42 fields")
    rows = [dict(zip(normalized_header, row)) for row in normalized_rows]
    ids = {row["observation_id"].strip() for row in rows}
    events = {row["event_id"].strip() for row in rows}
    if len(ids) != 103 or len(events) != 18 or "" in ids or "" in events:
        raise ValueError("expected 103 unique nonblank observation IDs across 18 distinct nonblank events")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="untouched Raw/Floods CSV")
    parser.add_argument("working_copy", type=Path, help="normalized CSV")
    parser.add_argument("--dry-run", action="store_true", help="check an existing copy without writing files")
    args = parser.parse_args()
    try:
        source = args.source.read_bytes()
        if sha256(source).hexdigest() != SOURCE_SHA256:
            raise ValueError("source SHA-256 differs from the Raw/Floods audit")
        header, newline, body = source.partition(b"\n")
        old_field = b",notes;;;;;;;"
        if not newline or header.count(old_field + b",") != 1:
            raise ValueError("expected one malformed notes field in the original header")
        normalized = header.replace(old_field + b",", b",notes,", 1) + newline + body
        working = args.working_copy.read_bytes() if args.dry_run else normalized
        if working != normalized:
            raise ValueError("working copy differs beyond the single approved header change")
        rows = verify(source, working)
        if not args.dry_run:
            with args.working_copy.open("xb") as destination:
                destination.write(working)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Flood inventory check failed: {error}\n")

    print(f"Source SHA-256 verified: {SOURCE_SHA256}")
    print("103 unique observation IDs across 18 distinct events; 42 fields per row.")
    print("Only notes;;;;;;; → notes changed. Observation bytes and all parsed field values match.")
    for field in ("date_precision", "temporal_uncertainty", "location_precision_m",
                  "coordinate_quality", "confidence_level"):
        counts = Counter(row[field] for row in rows)
        print(f"{field}: " + ", ".join(f"{value}={count}" for value, count in sorted(counts.items())))
    print(f"{'Dry-run verified' if args.dry_run else 'Prepared'} {args.working_copy}")


if __name__ == "__main__":
    main()
