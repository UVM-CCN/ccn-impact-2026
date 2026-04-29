"""
Geocode unmatched institutions in ccn-survey-2026-geocoded.csv using Nominatim.
Reads rows where LATITUDE is blank and "Institution Name" is non-empty,
queries Nominatim with "Institution Name, State, USA", and fills in coordinates.

Results are written back to the same file in-place.
Institutions that Nominatim cannot resolve are appended to unmatched_institutions.txt.

Nominatim usage policy requires:
  - A descriptive User-Agent
  - At least 1 second between requests
"""

import csv
import time
from pathlib import Path

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

GEOCODED_FILE = Path("data/ccn-survey-2026-geocoded.csv")
UNMATCHED_FILE = Path("data/unmatched_institutions.txt")

geolocator = Nominatim(user_agent="ccn-impact-2026-geocoder/1.0 (benjamincooley94@gmail.com)")


def geocode(name: str, state: str) -> tuple[str, str] | None:
    """Try to geocode using state-qualified query, then bare name as fallback."""
    queries = []
    if state.strip():
        queries.append(f"{name}, {state.strip()}, USA")
    queries.append(f"{name}, USA")

    for query in queries:
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                return str(location.latitude), str(location.longitude)
            time.sleep(1)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  [error] {query}: {e}")
            time.sleep(2)

    return None


def main() -> None:
    rows = list(csv.DictReader(GEOCODED_FILE.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else []

    # Build a cache so we only geocode each unique name once
    cache: dict[str, tuple[str, str] | None] = {}
    still_unmatched: list[str] = []

    to_geocode = [
        r for r in rows if not r["LATITUDE"] and r["Institution Name"].strip()
    ]
    unique_names = list(dict.fromkeys(r["Institution Name"].strip() for r in to_geocode))

    print(f"Geocoding {len(unique_names)} unique institution(s) via Nominatim...")

    for name in unique_names:
        # Pull State from the first matching row
        state = next(
            (r["State"] for r in to_geocode if r["Institution Name"].strip() == name), ""
        )
        print(f"  -> {name} ({state})", end=" ... ", flush=True)
        result = geocode(name, state)
        cache[name] = result
        if result:
            print(f"{result[0]}, {result[1]}")
        else:
            print("NOT FOUND")
            still_unmatched.append(name)
        time.sleep(1)  # Nominatim rate limit: 1 req/sec

    # Patch rows
    for row in rows:
        name = row["Institution Name"].strip()
        if not row["LATITUDE"] and name in cache and cache[name]:
            row["LATITUDE"], row["LONGITUD"] = cache[name]

    # Write patched CSV back in-place
    with GEOCODED_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Update unmatched file
    if still_unmatched:
        UNMATCHED_FILE.write_text("\n".join(still_unmatched) + "\n", encoding="utf-8")
        print(f"\n  {len(still_unmatched)} still unresolved -> {UNMATCHED_FILE}")
    else:
        UNMATCHED_FILE.unlink(missing_ok=True)
        print("\n  All institutions resolved. Removed unmatched_institutions.txt.")

    resolved = len(unique_names) - len(still_unmatched)
    print(f"  {resolved}/{len(unique_names)} geocoded -> {GEOCODED_FILE}")


if __name__ == "__main__":
    main()
