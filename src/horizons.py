# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Real Earth–Mars signal delay for every mission day, from NASA/JPL Horizons.

Horizons (https://ssd.jpl.nasa.gov/horizons/) is NASA/JPL's solar-system ephemeris service. For
each mission day it gives the distance from Earth's centre to Mars (`delta`, in AU) and the
Sun–Earth–Mars angle (`S-O-T`, degrees). The one-way light time is distance / speed of light;
a small Sun angle means solar conjunction, when contact with Mars is lost for about two weeks.

Used only by the UI (the delay shown for a crew on Mars); the model and the simulator never read
it, so the frozen hold-out result is unaffected. The raw response is cached in
data/raw/horizons_earth_mars.json; every other module reads only that cache (no network).

Usage:
    python -m src.horizons --start 2024-05-01 --days 120
"""

# ===== Imports =====
from __future__ import annotations

import argparse
import datetime as dt
import sys

from src.common import RAW_DIR, read_json, write_json

# ===== Constants =====
HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
CACHE_PATH = RAW_DIR / "horizons_earth_mars.json"
AU_KM = 149_597_870.7            # IAU 2012 Resolution B2 (exact by definition)
C_KM_S = 299_792.458             # speed of light in vacuum (exact by definition)
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


# ===== Request =====
def query_params(start: dt.date, days: int) -> dict:
    """Horizons API parameters: Mars (499) seen from Earth's centre (500@399), one row per day."""
    stop = start + dt.timedelta(days=days - 1)
    return {
        "format": "text", "COMMAND": "'499'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'",
        "START_TIME": f"'{start.isoformat()}'", "STOP_TIME": f"'{stop.isoformat()}'",
        "STEP_SIZE": "'1 d'", "QUANTITIES": "'20,23'", "CSV_FORMAT": "'YES'",
    }


def fetch_ephemeris(start: dt.date, days: int, timeout: float = 60.0) -> str:
    """Raw Horizons text for the mission window (requires network access)."""
    import requests  # imported here so offline modules never need it

    response = requests.get(HORIZONS_API, params=query_params(start, days), timeout=timeout)
    response.raise_for_status()
    return response.text


# ===== Parsing =====
def light_time_s(distance_au: float) -> float:
    """One-way signal travel time in seconds for a distance in AU."""
    return distance_au * AU_KM / C_KM_S


def parse_ephemeris(text: str, start: dt.date) -> list[dict]:
    """One row per day from the $$SOE … $$EOE block: mission day, date, distance, delay, Sun angle."""
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ValueError("Horizons response has no ephemeris block ($$SOE … $$EOE).")
    block = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = []
    for line in block.strip().splitlines():
        cells = [c.strip() for c in line.split(",")]
        year, month, rest = cells[0].split("-", 2)          # e.g. "2024-May-01 00:00"
        date = dt.date(int(year), MONTHS[month], int(rest.split()[0]))
        distance = float(cells[3])                          # delta (AU)
        rows.append({
            "day": (date - start).days + 1,
            "date": date.isoformat(),
            "distance_au": round(distance, 6),
            "one_way_s": round(light_time_s(distance), 1),
            "sun_angle_deg": float(cells[5]),               # S-O-T (Sun–Earth–Mars angle)
        })
    return rows


# ===== Cache =====
def load_cache() -> dict | None:
    """Cached Horizons table, or None when it does not exist."""
    return read_json(CACHE_PATH) if CACHE_PATH.exists() else None


def delay_by_day(days: int) -> dict | None:
    """Per mission day the real one-way delay (s) and Sun angle, for the UI contract; None without cache."""
    cache = load_cache()
    if cache is None:
        return None
    rows = [r for r in cache["rows"] if 1 <= r["day"] <= days]
    return {
        "source": "NASA/JPL Horizons ephemeris: Earth–Mars distance per day; delay = distance / speed of light",
        "link": "https://ssd.jpl.nasa.gov/horizons/",
        "retrieved": cache["retrieved"],
        "one_way_s": [r["one_way_s"] for r in rows],
        "sun_angle_deg": [r["sun_angle_deg"] for r in rows],
    }


# ===== Main =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cache the real Earth–Mars delay per mission day (JPL Horizons).")
    parser.add_argument("--start", default="2024-05-01", help="Mission day 1 (YYYY-MM-DD).")
    parser.add_argument("--days", type=int, default=120, help="Mission length in days.")
    args = parser.parse_args()

    start_date = dt.date.fromisoformat(args.start)
    try:
        rows = parse_ephemeris(fetch_ephemeris(start_date, args.days), start_date)
    except Exception as error:  # network problems are expected offline
        cached = load_cache()
        if cached is None:
            print(f"Horizons request failed ({error}) and no cache exists. The UI keeps the configured delay range.")
            sys.exit(1)
        print(f"Horizons request failed ({error}); keeping the existing cache with {len(cached['rows'])} days.")
        sys.exit(0)

    write_json(CACHE_PATH, {
        "source": HORIZONS_API,
        "query": query_params(start_date, args.days),
        "start": args.start,
        "days": args.days,
        "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
    })
    lo, hi = min(r["one_way_s"] for r in rows), max(r["one_way_s"] for r in rows)
    print(f"Cached {len(rows)} days to {CACHE_PATH}: one-way delay {lo / 60:.1f}-{hi / 60:.1f} min, "
          f"Sun angle {min(r['sun_angle_deg'] for r in rows):.1f}-{max(r['sun_angle_deg'] for r in rows):.1f} deg")
