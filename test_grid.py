import wec_data
from ratings import STAT_COLUMNS


def test_build_grid_is_deterministic():
    teams_a, drivers_a = wec_data.build_grid(seed=2025)
    teams_b, drivers_b = wec_data.build_grid(seed=2025)
    assert [d["id"] for d in drivers_a] == [d["id"] for d in drivers_b]
    assert drivers_a[0]["ppr"] == drivers_b[0]["ppr"]


def test_grid_has_both_classes_and_free_agents():
    teams, drivers = wec_data.build_grid()
    classes = {t["class"] for t in teams}
    assert classes == {"Hypercar", "LMGT3"}
    assert any(d["team_id"] is None for d in drivers), "expected free agents"
    assert all(stat in drivers[0] for stat in STAT_COLUMNS)


def test_calendar_has_eight_rounds_with_finale():
    cal = wec_data.calendar()
    assert len(cal) == 8
    assert sum(1 for r in cal if r["finale"]) == 1
    assert any(r["marquee"] for r in cal)


def test_team_lookup():
    team = wec_data.team_by_id(1)
    assert team is not None
    assert "full_name" in team and team["full_name"].startswith("#")
