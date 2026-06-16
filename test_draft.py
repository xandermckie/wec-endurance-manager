import random

from draft import current_pick, draft_board_context, sim_rest_of_draft, start_draft
from season import league_lookup, run_finale, sim_rest_of_regular


def _to_draft(season):
    lookup = league_lookup(season)
    sim_rest_of_regular(season, lookup, rng=random.Random(1))
    run_finale(season, lookup, rng=random.Random(2))
    season["phase"] = "complete"
    start_draft(season, lookup, rng=random.Random(3))
    return lookup


def test_start_draft_builds_queue(season):
    _to_draft(season)
    state = season["draft_state"]
    assert season["phase"] == "draft"
    assert state["queue"]
    assert state["prospect_pool"]
    # reverse championship order: first pick is a weak team
    assert current_pick(season) is not None


def test_board_context_for_user(season):
    _to_draft(season)
    board = draft_board_context(season, 1, league_lookup(season))
    assert "current_pick" in board
    assert board["total_picks"] == len(season["draft_state"]["queue"])


def test_sim_rest_completes_programme(season):
    _to_draft(season)
    sim_rest_of_draft(season, auto_user_picks=True, rng=random.Random(4))
    assert season["phase"] == "offseason"
    assert season["draft_state"] is None
