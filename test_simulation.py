import random

from simulation import WEC_POINTS, qualifying, simulate_class_race


def _entry(team_id, overall, consistency=70):
    return {"team_id": team_id, "team_name": f"Team {team_id}", "class": "Hypercar",
            "overall": overall, "consistency": consistency,
            "crew": [{"id": team_id * 10, "name": f"Driver {team_id}", "overall": overall, "grade": "Gold"}]}


def test_qualifying_orders_field():
    entries = [_entry(i, 60 + i) for i in range(6)]
    grid = qualifying(entries, random.Random(1), variance=0.0)
    # zero variance -> fastest (highest overall) on pole
    assert grid[0]["team_id"] == 5


def test_points_awarded_to_top_finishers():
    entries = [_entry(i, 80 - i * 3) for i in range(8)]
    classification = simulate_class_race(entries, rng=random.Random(2), settings={"race_variance": 0.0, "base_dnf_chance": 0.0})
    classified = [r for r in classification if r["status"] == "Classified"]
    assert classified[0]["position"] == 1
    # winner gets at least 25 points (plus possible pole point)
    assert classified[0]["points"] >= WEC_POINTS[0]
    total_positions = [r["position"] for r in classification]
    assert total_positions == list(range(1, len(entries) + 1))


def test_points_multiplier_scales():
    entries = [_entry(i, 80 - i * 4) for i in range(6)]
    base = simulate_class_race(entries, rng=random.Random(5), settings={"race_variance": 0.0, "base_dnf_chance": 0.0}, points_mult=1.0)
    doubled = simulate_class_race(entries, rng=random.Random(5), settings={"race_variance": 0.0, "base_dnf_chance": 0.0}, points_mult=2.0)
    assert doubled[0]["points"] == base[0]["points"] * 2


def test_high_dnf_factor_produces_retirements():
    entries = [_entry(i, 70, consistency=40) for i in range(10)]
    classification = simulate_class_race(entries, rng=random.Random(9),
                                         settings={"race_variance": 5.0, "base_dnf_chance": 0.3},
                                         dnf_factor=1.9)
    assert any(r["status"] == "DNF" for r in classification)
