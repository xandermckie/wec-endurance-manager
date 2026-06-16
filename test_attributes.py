import random

from attributes import (
    ATTRIBUTE_KEYS,
    age_multiplier,
    apply_season_aging,
    derive_attributes,
    ensure_grade,
    generate_rookie_profile,
    init_career_profile,
    scouting_upside_tier,
)


def test_ensure_grade_normalizes():
    p = {"id": 1, "grade": "Platinum", "overall": 90}
    assert ensure_grade(p) == "Platinum"
    p2 = {"id": 2, "overall": 88, "age": 30}
    assert ensure_grade(p2) in ("Platinum", "Gold", "Silver", "Bronze")


def test_derive_attributes_in_range():
    p = {"id": 1, "ppr": 20, "pod": 5, "ovt": 12, "pol": 3, "fl": 4, "gp": 8, "overall": 85, "grade": "Platinum"}
    attrs = derive_attributes(p)
    assert set(attrs) == set(ATTRIBUTE_KEYS)
    assert all(25 <= v <= 99 for v in attrs.values())


def test_age_curve_peaks_then_declines():
    young = age_multiplier(20, peak_age=31)
    peak = age_multiplier(31, peak_age=31)
    old = age_multiplier(45, peak_age=31)
    assert young < peak
    assert old < peak


def test_rookie_profile_has_grade():
    profile = generate_rookie_profile(60, random.Random(1))
    assert profile["grade"] in ("Platinum", "Gold", "Silver", "Bronze")
    assert set(profile["attributes"]) == set(ATTRIBUTE_KEYS)


def test_scouting_upside_tier():
    assert scouting_upside_tier({"overall": 55, "potential": 80}) == "High ceiling"
    assert scouting_upside_tier({"overall": 70, "potential": 72}) == "Limited ceiling"


def test_season_aging_ages_and_retires():
    season = {
        "players": {
            "1": {"id": 1, "name": "Old Hand", "age": 53, "retirement_age": 54, "team_id": 1,
                  "overall": 70, "grade": "Bronze", "gp": 8},
            "2": {"id": 2, "name": "Young Gun", "age": 24, "retirement_age": 48, "team_id": 1,
                  "overall": 78, "grade": "Gold", "gp": 8},
        },
        "rosters": {"1": [1, 2]},
        "free_agents": [],
    }
    for p in season["players"].values():
        init_career_profile(p, random.Random(3))
    retirements = apply_season_aging(season, random.Random(3))
    assert any(r["player_id"] == 1 for r in retirements)
    assert "1" not in season["players"]
    assert "2" in season["players"]
    assert season["players"]["2"]["age"] == 25
