"""
Add LATITUDE and LONGITUD from ipeds_hd2024.csv to ccn-survey-2026.csv
by matching "Institution Name" -> "INSTNM".

Matching strategy:
  1. Exact match (after stripping whitespace)
  2. Case-insensitive match
Unmatched rows are written to unmatched_institutions.txt for manual geolocation.
"""

import csv
import sys
from pathlib import Path

IPEDS_FILE = Path("data/ipeds_hd2024.csv")
SURVEY_FILE = Path("data/ccn-survey-2026.csv")
OUTPUT_FILE = Path("data/ccn-survey-2026-geocoded.csv")
UNMATCHED_FILE = Path("data/unmatched_institutions.txt")


def build_ipeds_lookup(ipeds_path: Path) -> tuple[dict, dict]:
    """Return (exact_lookup, lower_lookup) dicts mapping name -> (lat, lon)."""
    exact: dict[str, tuple[str, str]] = {}
    lower: dict[str, tuple[str, str]] = {}

    with ipeds_path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = row["INSTNM"].strip()
            coords = (row["LATITUDE"].strip(), row["LONGITUD"].strip())
            exact[name] = coords
            lower[name.lower()] = coords

    return exact, lower


def main() -> None:
    exact_lookup, lower_lookup = build_ipeds_lookup(IPEDS_FILE)

    unmatched: list[str] = []
    output_rows: list[dict] = []

    with SURVEY_FILE.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = (reader.fieldnames or []) + ["LATITUDE", "LONGITUD"]

        for row in reader:
            raw_name = row["Institution Name"]
            name = raw_name.strip()

            coords = exact_lookup.get(name) or lower_lookup.get(name.lower())

            if coords:
                row["LATITUDE"], row["LONGITUD"] = coords
            else:
                row["LATITUDE"] = ""
                row["LONGITUD"] = ""
                if name and name not in unmatched:
                    unmatched.append(name)

            output_rows.append(row)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    if unmatched:
        UNMATCHED_FILE.write_text("\n".join(unmatched) + "\n", encoding="utf-8")
        print(f"  {len(unmatched)} unmatched institutions logged to {UNMATCHED_FILE}")
    else:
        print("  All institutions matched.")

    matched = len(output_rows) - sum(1 for r in output_rows if not r["LATITUDE"])
    print(f"  {matched}/{len(output_rows)} rows geocoded -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
