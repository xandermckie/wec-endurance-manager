import random

from season import (
    CLASSES,
    advance_season,
    can_trade,
    finale_complete,
    league_lookup,
    regular_season_complete,
    rounds_completed,
    run_finale,
    sim_rest_of_regular,
    sim_round,
    sim_to_transfer_deadline,
    standings_table,
)


def test_init_season_shape(season):
    assert season["phase"] == "regular"
    assert len(season["schedule"]) == 8
    assert len(season["rosters"]) >= 20
    assert set(season["team_class"].values()) == set(CLASSES)


def test_sim_round_advances(season):
    lookup = league_lookup(season)
    assert rounds_completed(season) == 0
    sim_round(season, lookup, rng=random.Random(1))
    assert rounds_completed(season) == 1
    # every team has points recorded for one round
    for cls in CLASSES:
        rows = standings_table(season, class_name=cls)
        assert all(r["rounds"] == 1 for r in rows)


def test_transfer_deadline_closes(season):
    lookup = league_lookup(season)
    assert can_trade(season)
    sim_to_transfer_deadline(season, lookup, rng=random.Random(2))
    assert rounds_completed(season) >= season["transfer_deadline_rounds"]
    assert not can_trade(season)


def test_full_season_to_finale(season):
    lookup = league_lookup(season)
    sim_rest_of_regular(season, lookup, rng=random.Random(3))
    assert regular_season_complete(season)
    assert season["phase"] == "regular_complete"
    run_finale(season, lookup, rng=random.Random(4))
    assert finale_complete(season)
    assert season["phase"] == "complete"
    champions = season["finale"]["champions"]
    assert set(champions) == set(CLASSES)
    # champion is the points leader of its class
    for cls in CLASSES:
        leader = standings_table(season, class_name=cls)[0]
        assert champions[cls]["team_id"] == leader["team_id"]


def test_advance_resets_and_ages(season):
    lookup = league_lookup(season)
    sim_rest_of_regular(season, lookup, rng=random.Random(3))
    run_finale(season, lookup, rng=random.Random(4))
    season["phase"] = "offseason"
    year_before = season["season_year"]
    advance_season(season, rng=random.Random(5))
    assert season["season_year"] == year_before + 1
    assert season["phase"] == "regular"
    assert rounds_completed(season) == 0
    assert all(not r["played"] for r in season["schedule"])
