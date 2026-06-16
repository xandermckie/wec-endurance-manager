from contracts import (
    BUDGET_CAP_M,
    MAX_FA_YEARS,
    compute_asking_salary,
    evaluate_offer,
    market_salary,
    max_player_salary,
    propose_offer,
    team_finances,
    validate_offer_terms,
)
from roster import free_agent_players
from season import league_lookup


def test_market_salary_scales_with_overall():
    low = market_salary({"overall": 55, "age": 30})
    high = market_salary({"overall": 92, "age": 30})
    assert high > low
    assert high <= BUDGET_CAP_M


def test_team_finances_within_budget(season):
    fin = team_finances(season, 1)
    assert fin["payroll"] >= 0
    assert fin["salary_cap"] == BUDGET_CAP_M
    assert fin["cap_space"] == round(fin["salary_cap"] - fin["payroll"], 1)


def test_offer_terms_reject_overpay():
    player = {"overall": 60, "asking_salary": 3.0}
    ok, msg = validate_offer_terms(player, max_player_salary(60) + 50, 2, 1,
                                   {"team_finances": {}, "standings": {}}, {})
    assert not ok


def test_sign_free_agent_succeeds(season):
    lookup = league_lookup(season)
    fas = free_agent_players(season, lookup)
    assert fas, "expected free agents in the market"
    target = max(fas, key=lambda p: p.get("overall") or 0)
    ask = compute_asking_salary(target)
    ok, msg, accepted = propose_offer(season, 1, target["id"], ask, 2)
    assert ok and accepted
    assert target["id"] in season["rosters"]["1"]


def test_evaluate_offer_below_ask_fails():
    player = {"name": "X", "overall": 80, "asking_salary": 10.0, "previous_salary": 9.0}
    season = {"standings": {}, "team_finances": {}}
    accepted, _ = evaluate_offer(player, 4.0, 1, season, 1)
    assert not accepted
