from ratings import (
    apply_ratings,
    compute_overall_ratings,
    compute_team_overall,
    compute_team_consistency_rating,
    build_team_summaries,
)


def _driver(pid, ppr, pod=2, ovt=8, pol=1, fl=1, team_id=1):
    return {"id": pid, "ppr": ppr, "pod": pod, "ovt": ovt, "pol": pol, "fl": fl,
            "gp": 8, "team_id": team_id, "team": "Test", "grade": "Gold", "class": "Hypercar"}


def test_overall_ratings_increase_with_points():
    players = [_driver(1, 4), _driver(2, 12), _driver(3, 22)]
    apply_ratings(players)
    overalls = {p["id"]: p["overall"] for p in players}
    assert overalls[3] > overalls[2] > overalls[1]
    assert all(25 <= o <= 99 for o in overalls.values())


def test_team_overall_uses_crew():
    roster = [_driver(1, 22), _driver(2, 18), _driver(3, 10), _driver(4, 4)]
    apply_ratings(roster)
    team_ovr = compute_team_overall(roster)
    assert team_ovr is not None
    # weighted toward the best drivers
    assert team_ovr > sum(p["overall"] for p in roster) / len(roster) - 5


def test_team_summaries_and_consistency():
    roster = [_driver(i, 20 - i, team_id=1) for i in range(4)]
    apply_ratings(roster)
    summaries = build_team_summaries(roster)
    assert summaries and summaries[0]["team_id"] == 1
    cons = compute_team_consistency_rating(roster)
    assert 0 < cons <= 99
