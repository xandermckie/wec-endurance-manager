import random

import pytest

import cache
import fetcher
from season import init_season, league_lookup


@pytest.fixture(scope="session")
def grid_drivers():
    if not cache.get_drivers():
        fetcher.refresh_cache()
    return cache.get_drivers()


@pytest.fixture
def season(grid_drivers):
    data = init_season(grid_drivers, season_year=2025, rng=random.Random(42), difficulty="normal")
    data["user_team_id"] = 1
    return data


@pytest.fixture
def lookup(season):
    return league_lookup(season)
