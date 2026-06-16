from roster import (
    MAX_ROSTER,
    MIN_ROSTER,
    assign_to_reserve,
    can_remove_player,
    recall_from_reserve,
    release_player,
    reserve_players,
    roster_size,
)
from season import league_lookup, roster_players


def test_release_moves_to_market(season):
    before = roster_size(season, 1)
    pid = roster_players(season, 1, league_lookup(season))[0]["id"]
    ok, msg = release_player(season, 1, pid)
    assert ok
    assert roster_size(season, 1) == before - 1
    assert pid in season["free_agents"]


def test_cannot_drop_below_min(season):
    # release down to the minimum
    while can_remove_player(season, 1):
        pid = roster_players(season, 1, league_lookup(season))[0]["id"]
        release_player(season, 1, pid)
    assert roster_size(season, 1) == MIN_ROSTER
    pid = roster_players(season, 1, league_lookup(season))[0]["id"]
    ok, _ = release_player(season, 1, pid)
    assert not ok


def test_reserve_round_trip(season):
    lookup = league_lookup(season)
    # find a young driver to send to reserve
    young = None
    for p in roster_players(season, 1, lookup):
        if (p.get("age") or 99) <= 23:
            young = p
            break
    if young is None:
        young = roster_players(season, 1, lookup)[0]
        young["age"] = 22
    ok, msg = assign_to_reserve(season, 1, young["id"])
    assert ok, msg
    assert young["id"] in [p["id"] for p in reserve_players(season, 1, lookup)]
    ok, msg = recall_from_reserve(season, 1, young["id"])
    assert ok, msg
    assert young["id"] in season["rosters"]["1"]
