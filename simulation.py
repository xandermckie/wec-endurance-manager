"""Race-weekend simulation: qualifying then a class race producing a classification + points.

Each class (Hypercar, LMGT3) runs as its own field. An entry's race pace is its team overall
plus crew form and randomness; reliability rolls decide DNFs (longer races attrite more). The
result is a per-entry classification with finishing position, championship points, pole and
fastest-lap flags.
"""

import random

# WEC class points for P1..P10.
WEC_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
POLE_POINT = 1

DEFAULT_RACE_VARIANCE = 7.0
BASE_DNF_CHANCE = 0.03


def _entry_overall(entry):
    return entry.get("overall") or 50.0


def _entry_consistency(entry):
    return entry.get("consistency") or 50.0


def qualifying(entries, rng, variance=4.5):
    """Return entries ordered by one-lap pace (grid order). Pole sitter is first."""
    ranked = []
    for entry in entries:
        pace = _entry_overall(entry) + rng.gauss(0, variance)
        ranked.append((pace, entry))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [entry for _pace, entry in ranked]


def _dnf_chance(consistency, dnf_factor, settings):
    base = settings.get("base_dnf_chance", BASE_DNF_CHANCE)
    reliability = (consistency - 50) / 100.0  # -0.25 .. +0.49
    chance = (base + dnf_factor * 0.05) * (1.0 - reliability)
    return max(0.005, min(0.55, chance))


def simulate_class_race(
    entries,
    rng=None,
    settings=None,
    dnf_factor=1.0,
    points_mult=1.0,
    grid=None,
):
    """Simulate one class race.

    entries: list of dicts with team_id, team_name, overall, consistency, crew (driver dicts).
    Returns a list of classification dicts ordered by finishing position (1-based).
    """
    rng = rng or random.Random()
    settings = settings or {}
    variance = settings.get("race_variance", DEFAULT_RACE_VARIANCE)

    grid = grid if grid is not None else qualifying(entries, rng)
    grid_positions = {entry["team_id"]: index + 1 for index, entry in enumerate(grid)}
    field_size = max(1, len(entries))

    runners = []
    retirements = []
    for entry in entries:
        consistency = _entry_consistency(entry)
        dnf = rng.random() < _dnf_chance(consistency, dnf_factor, settings)
        grid_pos = grid_positions.get(entry["team_id"], field_size)
        grid_bonus = (field_size - grid_pos) / field_size * 2.0
        score = _entry_overall(entry) + grid_bonus + rng.gauss(0, variance)
        record = {"entry": entry, "score": score, "grid": grid_pos}
        if dnf:
            # How far into the race they got, for ordering DNFs sensibly.
            record["distance"] = rng.random()
            retirements.append(record)
        else:
            runners.append(record)

    runners.sort(key=lambda r: r["score"], reverse=True)
    retirements.sort(key=lambda r: r["distance"], reverse=True)

    pole_id = grid[0]["team_id"] if grid else None
    fastest_id = None
    if runners:
        # Fastest lap goes to a sharp car near the front, with a little randomness.
        fl_pool = runners[: min(5, len(runners))]
        fastest_id = max(
            fl_pool, key=lambda r: _entry_overall(r["entry"]) + rng.gauss(0, 3)
        )["entry"]["team_id"]

    classification = []
    position = 0
    for record in runners:
        position += 1
        entry = record["entry"]
        points = 0
        if position <= len(WEC_POINTS):
            points = WEC_POINTS[position - 1]
        if entry["team_id"] == pole_id:
            points += POLE_POINT
        points = round(points * points_mult)
        classification.append(
            _classification_row(entry, position, "Classified", points, record["grid"],
                                 pole=entry["team_id"] == pole_id,
                                 fastest=entry["team_id"] == fastest_id)
        )

    for record in retirements:
        position += 1
        entry = record["entry"]
        points = POLE_POINT * points_mult if entry["team_id"] == pole_id else 0
        classification.append(
            _classification_row(entry, position, "DNF", round(points), record["grid"],
                                 pole=entry["team_id"] == pole_id, fastest=False)
        )

    return classification


def _classification_row(entry, position, status, points, grid, pole=False, fastest=False):
    crew = entry.get("crew", [])
    return {
        "team_id": entry["team_id"],
        "team_name": entry.get("team_name", str(entry["team_id"])),
        "class": entry.get("class"),
        "position": position,
        "status": status,
        "points": points,
        "grid": grid,
        "pole": pole,
        "fastest_lap": fastest,
        "crew": [
            {"player_id": d.get("id"), "name": d.get("name", str(d.get("id"))),
             "overall": d.get("overall"), "grade": d.get("grade")}
            for d in crew
        ],
    }
