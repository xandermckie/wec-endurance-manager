from season import league_lookup, roster_players
from trade import evaluate_trade, execute_trade, other_teams, player_value, validate_trade


def _two_teams(season):
    teams = other_teams(season, 1)
    partner = teams[0]["team_id"]
    return 1, partner


def test_player_value_rewards_overall_and_prime_age():
    young_star = player_value({"overall": 90, "age": 30, "peak_age": 31})
    old_star = player_value({"overall": 90, "age": 46, "peak_age": 31})
    assert young_star > old_star


def test_validate_trade_rejects_empty(season):
    user, partner = _two_teams(season)
    ok, msg = validate_trade(season, user, partner, [], [], [], [])
    assert not ok


def test_validate_trade_rejects_invalid_player_id(season):
    user, partner = _two_teams(season)
    ok, msg = validate_trade(season, user, partner, ["not-a-number"], [], [], [])
    assert not ok
    assert "Invalid" in msg


def test_execute_trade_does_not_mutate_on_invalid_pick(season):
    user, partner = _two_teams(season)
    lookup = league_lookup(season)
    partner_before = list(season["rosters"][str(partner)])
    mine = roster_players(season, user, lookup)[0]["id"]
    theirs = roster_players(season, partner, lookup)[0]["id"]
    ok, _msg = execute_trade(
        season, user, partner, [str(mine)], ["fake-pick-id"], [str(theirs)], [],
    )
    assert not ok
    assert season["rosters"][str(partner)] == partner_before


def test_evaluate_trade_meter(season):
    user, partner = _two_teams(season)
    lookup = league_lookup(season)
    mine = roster_players(season, user, lookup)[-1]["id"]
    result = evaluate_trade(season, user, partner, [str(mine)], [], [], [])
    assert result["has_assets"]
    assert "label" in result and 0 <= result["meter"] <= 100


def test_execute_balanced_trade(season):
    user, partner = _two_teams(season)
    lookup = league_lookup(season)
    mine = roster_players(season, user, lookup)[0]["id"]
    theirs = roster_players(season, partner, lookup)[0]["id"]
    ok, msg = execute_trade(season, user, partner, [str(mine)], [], [str(theirs)], [])
    assert ok, msg
    assert theirs in season["rosters"][str(user)]
    assert mine in season["rosters"][str(partner)]
    assert season["players"][str(theirs)]["team_id"] == user
