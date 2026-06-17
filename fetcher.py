"""Builds the cached, rated grid from the curated WEC dataset.

The original game pulled live stats from a sports API. WEC has no free public timing API, so the
"source" here is the bundled curated grid (wec_data.py). The orchestration is the same: build
records, apply ratings + attributes + career profiles, then write the cache atomically.
"""

import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

import cache

logger = logging.getLogger(__name__)

import wec_data
from attributes import apply_attributes, ensure_grade, init_career_profiles
from ratings import apply_ratings

load_dotenv()

CURRENT_SEASON = wec_data.CURRENT_SEASON


def fetch_teams():
    """All WEC car entries from the curated grid (no HTTP)."""
    return wec_data.teams()


def fetch_team(team_id):
    """Single team by id from the curated grid."""
    return wec_data.team_by_id(team_id)


def calendar():
    return wec_data.calendar()


def refresh_cache():
    """Rebuild the cached grid. Returns True on success, False if a stale cache was kept."""
    try:
        teams, drivers = wec_data.build_grid()
        if not drivers:
            raise ValueError("Curated grid produced no drivers")

        for driver in drivers:
            ensure_grade(driver)

        drivers = apply_ratings(drivers)
        drivers = apply_attributes(drivers)
        init_career_profiles(drivers)

        cache.save_cache(
            {
                "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "season": CURRENT_SEASON,
                "source": "wec_data",
                "teams": teams,
                "drivers": drivers,
            }
        )
        return True
    except Exception:
        logger.exception("Grid refresh failed")
        existing = cache.load_cache()
        if existing.get("drivers"):
            return False
        raise


if __name__ == "__main__":
    success = refresh_cache()
    if success:
        count = len(cache.get_drivers())
        print(f"Grid refreshed: {count} drivers")
    else:
        print("Refresh failed; kept existing grid")
