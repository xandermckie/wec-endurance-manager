"""Driver attributes, season-stat projection, development and aging.

Attributes (0-99): pace, racecraft, tyre_management, consistency, fuel_management, stamina.
Driver grade (Platinum / Gold / Silver / Bronze) is the FIA categorisation and biases attributes
the way a position would in a stick-and-ball game.
"""

import random

from ratings import (
    MIN_ROUNDS_FOR_RATINGS,
    compute_intrinsic_overall,
    compute_stat_percentiles,
)

ATTRIBUTE_KEYS = ("pace", "racecraft", "tyre_management", "consistency", "fuel_management", "stamina")
MIN_ATTR = 25
MAX_ATTR = 99

# Career arc tuning — drivers race far longer than stick-and-ball athletes.
CAREER_START_AGE = 18
CAREER_START_MULTIPLIER = 0.80
PEAK_AGE_MIN = 29
PEAK_AGE_MAX = 34
RETIRE_AGE_MIN = 44
RETIRE_AGE_MAX = 54
DECLINE_RATE = 0.010
STAMINA_DECLINE_RATE = 0.016
MIN_AGE_MULTIPLIER = 0.58
DEFAULT_PEAK_AGE = 31
POTENTIAL_MIN = 40
POTENTIAL_MAX = 99

LEAGUE_SKILL_SCALE = 0.90
STAT_MODIFIER_LOW = 0.80
STAT_MODIFIER_HIGH = 1.20

VALID_GRADES = ("Platinum", "Gold", "Silver", "Bronze")

# How a season stat line maps to / from attributes (ppr uses a curve; others are linear scales).
STAT_FROM_ATTR = {
    "ppr": ("pace", None),
    "pod": ("consistency", 0.060),
    "ovt": ("racecraft", 0.150),
    "pol": ("pace", 0.038),
    "fl": ("tyre_management", 0.045),
}
PPR_CURVE_EXPONENT = 1.40
PPR_CURVE_SCALE = 24.0

STAT_DISPLAY_CAPS = {"ppr": 26.0, "pod": 8.0, "ovt": 18.0, "pol": 6.0, "fl": 6.0}

GRADE_ATTR_BIAS = {
    "Platinum": {"pace": 1.07, "racecraft": 1.05, "tyre_management": 1.03, "consistency": 1.04, "fuel_management": 1.02, "stamina": 1.0},
    "Gold":     {"pace": 1.01, "racecraft": 1.01, "tyre_management": 1.0, "consistency": 1.0, "fuel_management": 1.0, "stamina": 1.0},
    "Silver":   {"pace": 0.96, "racecraft": 0.97, "tyre_management": 0.98, "consistency": 0.97, "fuel_management": 0.98, "stamina": 1.0},
    "Bronze":   {"pace": 0.90, "racecraft": 0.92, "tyre_management": 0.95, "consistency": 0.94, "fuel_management": 0.96, "stamina": 0.98},
}

GRADE_STAT_BIAS = {
    "Platinum": 1.06,
    "Gold": 1.0,
    "Silver": 0.94,
    "Bronze": 0.86,
}

ATTR_BIAS_MIN = 0.88
ATTR_BIAS_MAX = 1.12


def _clamp(value, low=MIN_ATTR, high=MAX_ATTR):
    return max(low, min(high, round(value)))


def _clamp_stat(value, stat):
    cap = STAT_DISPLAY_CAPS.get(stat)
    if cap is not None:
        value = min(value, cap)
    return max(0, round(value, 1))


# ── Grade handling (the "position" of a driver) ─────────────────────────────
def ensure_grade(player):
    grade = player.get("grade")
    if grade in VALID_GRADES:
        player["grades"] = [grade]
        return grade
    grades = player.get("grades")
    if grades:
        for g in grades:
            if g in VALID_GRADES:
                player["grade"] = g
                player["grades"] = [g]
                return g
    inferred = infer_grade_from_stats(player)
    player["grade"] = inferred
    player["grades"] = [inferred]
    return inferred


def infer_grade_from_stats(player):
    overall = player.get("overall") or 50
    age = player.get("age") or 30
    if overall >= 82:
        return "Platinum"
    if overall >= 70:
        return "Gold"
    if overall >= 58 or age < 45:
        return "Silver"
    return "Bronze"


def grades_label(grades):
    if not grades:
        return "—"
    if isinstance(grades, str):
        return grades
    return "/".join(grades)


def grade_of(player):
    return player.get("grade") or ensure_grade(player)


def _grade_attr_bias(grade):
    bias = GRADE_ATTR_BIAS.get(grade, {})
    return {key: bias.get(key, 1.0) for key in ATTRIBUTE_KEYS}


def _apply_grade_attr_bias(attributes, grade):
    bias = _grade_attr_bias(grade)
    adjusted = {}
    for key in ATTRIBUTE_KEYS:
        factor = max(ATTR_BIAS_MIN, min(ATTR_BIAS_MAX, bias.get(key, 1.0)))
        adjusted[key] = _clamp(attributes.get(key, MIN_ATTR) * factor)
    return adjusted


# ── Attribute derivation ────────────────────────────────────────────────────
def _blend(primary, secondary=None, primary_weight=0.82):
    if primary is None:
        return _clamp(secondary if secondary is not None else 50)
    if secondary is None:
        return _clamp(primary)
    return _clamp(primary * primary_weight + secondary * (1 - primary_weight))


def _stamina_from_player(player):
    gp = player.get("gp") or 0
    age = player.get("age") or 30
    gp_factor = min(gp / 8, 1.0) * 35
    age_factor = max(0, 35 - abs(age - 30)) * 1.4
    overall = player.get("overall") or 50
    return _clamp(gp_factor + age_factor + overall * 0.25)


def _fuel_from_player(player, percentiles):
    ppr_pct = percentiles.get("ppr") or 50
    overall = player.get("overall") or 50
    return _clamp(ppr_pct * 0.55 + overall * 0.30 + 8)


def derive_attributes(player, percentiles=None, overall=None):
    if percentiles is None:
        percentiles = {}
    overall = overall if overall is not None else player.get("overall") or 50
    gp = player.get("gp") or 0
    grade = ensure_grade(player)

    if gp < MIN_ROUNDS_FOR_RATINGS:
        base = overall * 0.85 * LEAGUE_SKILL_SCALE
        attrs = {
            "pace": _clamp(base + (player.get("ppr") or 0) * 0.8),
            "racecraft": _clamp(base * 0.8 + (player.get("ovt") or 0) * 2),
            "tyre_management": _clamp(base * 0.8 + (player.get("fl") or 0) * 4),
            "consistency": _clamp(base * 0.8 + (player.get("pod") or 0) * 4),
            "fuel_management": _clamp(overall * 0.9 * LEAGUE_SKILL_SCALE),
            "stamina": _stamina_from_player(player),
        }
        return _apply_grade_attr_bias(attrs, grade)

    pod_pct = percentiles.get("pod") or 50
    fl_pct = percentiles.get("fl") or 50
    pol_pct = percentiles.get("pol") or 50
    ppr_pct = percentiles.get("ppr") or 50

    attrs = {
        "pace": _blend((ppr_pct * 0.7 + pol_pct * 0.3), overall * LEAGUE_SKILL_SCALE),
        "racecraft": _blend(percentiles.get("ovt"), overall * LEAGUE_SKILL_SCALE),
        "tyre_management": _blend((fl_pct * 0.55 + pod_pct * 0.45), overall * LEAGUE_SKILL_SCALE),
        "consistency": _blend(pod_pct, overall * LEAGUE_SKILL_SCALE),
        "fuel_management": _fuel_from_player(player, percentiles),
        "stamina": _stamina_from_player(player),
    }
    return _apply_grade_attr_bias(attrs, grade)


def apply_attributes(players):
    percentiles_by_id = compute_stat_percentiles(players)
    for player in players:
        ensure_grade(player)
        percentiles = percentiles_by_id.get(player["id"], {})
        player["attributes"] = derive_attributes(player, percentiles)
    return players


def needs_attributes(players):
    return any(not p.get("attributes") for p in players)


def get_attributes(player):
    attrs = player.get("attributes")
    if attrs:
        return attrs
    return derive_attributes(player)


def scouting_upside_tier(prospect):
    potential = prospect.get("potential")
    overall = prospect.get("overall") or 50
    if potential is None:
        return "Unknown"
    gap = potential - overall
    if gap >= 14:
        return "High ceiling"
    if gap >= 7:
        return "Solid ceiling"
    return "Limited ceiling"


# ── Season-stat projection from attributes ──────────────────────────────────
def _grade_stat_multiplier(grade):
    return GRADE_STAT_BIAS.get(grade, 1.0)


def _nonlinear_stat_value(attr_value, stat, scale):
    if stat == "ppr":
        normalized = max(MIN_ATTR, min(MAX_ATTR, attr_value)) / 100.0
        return (normalized ** PPR_CURVE_EXPONENT) * PPR_CURVE_SCALE
    return attr_value * scale


def _compute_stat_line(attributes, player=None):
    grade = grade_of(player) if player else "Gold"
    grade_mult = _grade_stat_multiplier(grade)
    stat_mods = player.get("stat_modifiers", {}) if player else {}
    season_form = player.get("season_form", 1.0) if player else 1.0
    stats = {}
    for stat, (attr_key, scale) in STAT_FROM_ATTR.items():
        raw = _nonlinear_stat_value(attributes[attr_key], stat, scale)
        value = raw * grade_mult * stat_mods.get(stat, 1.0) * season_form
        if stat == "ppr":
            value *= player.get("pace_bias", 1.0) if player else 1.0
        stats[stat] = _clamp_stat(value, stat)
    return stats


def season_averages_from_attributes(attributes, rng=None, player=None):
    stats = season_averages_from_attributes_deterministic(attributes, player)
    if rng is None:
        return stats
    for stat in stats:
        stats[stat] = _clamp_stat(stats[stat] * rng.uniform(0.92, 1.08), stat)
    return stats


def season_averages_from_attributes_deterministic(attributes, player=None):
    if player and player.get("stats_source") == "grid":
        cache_stats = player.get("cache_stats") or {}
        season_form = player.get("season_form", 1.0)
        stats = {}
        for stat in STAT_FROM_ATTR:
            base = cache_stats.get(stat, player.get(stat, 0))
            stats[stat] = _clamp_stat(base * season_form, stat)
        return stats
    return _compute_stat_line(attributes, player)


# ── Age curves ───────────────────────────────────────────────────────────────
def age_multiplier(age, peak_age=None, decline_rate=DECLINE_RATE):
    if age is None:
        return 1.0
    peak_age = peak_age or DEFAULT_PEAK_AGE
    age = float(age)
    if age <= peak_age:
        if age <= CAREER_START_AGE or peak_age <= CAREER_START_AGE:
            return CAREER_START_MULTIPLIER
        span = peak_age - CAREER_START_AGE
        progress = (age - CAREER_START_AGE) / span
        return CAREER_START_MULTIPLIER + (1.0 - CAREER_START_MULTIPLIER) * progress
    years_past_peak = age - peak_age
    return max(MIN_AGE_MULTIPLIER, 1.0 - years_past_peak * decline_rate)


def stamina_age_multiplier(age, peak_age=None):
    return age_multiplier(age, peak_age, decline_rate=STAMINA_DECLINE_RATE)


def _player_rng(player, rng=None):
    if rng is None:
        return random.Random(int(player.get("id", 0)))
    seed = rng.randint(0, 2**31) ^ int(player.get("id", 0))
    return random.Random(seed)


def _scale_base_attributes(effective_attrs, multiplier, stamina_multiplier=None):
    stamina_multiplier = stamina_multiplier if stamina_multiplier is not None else multiplier
    base = {}
    for key in ATTRIBUTE_KEYS:
        effective_value = effective_attrs.get(key, MIN_ATTR)
        divisor = stamina_multiplier if key == "stamina" else multiplier
        if divisor <= 0:
            divisor = 1.0
        base[key] = _clamp(effective_value / divisor)
    return base


# ── Rookie generation ────────────────────────────────────────────────────────
def generate_rookie_profile(overall, rng=None):
    rng = rng or random.Random()
    base = overall * 0.84
    spread = rng.uniform(-7, 7)
    archetype = rng.random()

    # Rookies enter as Silver or Bronze (FIA categorisation for newcomers); the quick ones as Gold.
    if overall >= 64:
        grade = "Gold"
    elif overall >= 52:
        grade = "Silver"
    else:
        grade = "Bronze"

    if archetype < 0.35:  # qualifying specialist
        pace = base + spread + 7
        racecraft = base - 3
        tyre = base - 4
    elif archetype < 0.6:  # racecraft / wheel-to-wheel
        pace = base + spread
        racecraft = base + spread + 6
        tyre = base - 2
    elif archetype < 0.82:  # tyre & stint manager
        pace = base + spread - 3
        racecraft = base - 2
        tyre = base + spread + 7
    else:  # all-rounder
        pace = base + spread
        racecraft = base + spread - 2
        tyre = base + spread - 2

    attributes = {
        "pace": _clamp(pace),
        "racecraft": _clamp(racecraft),
        "tyre_management": _clamp(tyre),
        "consistency": _clamp(base + rng.uniform(-6, 6)),
        "fuel_management": _clamp(base + rng.uniform(-5, 5)),
        "stamina": _clamp(78 + rng.uniform(-8, 10)),
    }
    attributes = _apply_grade_attr_bias(attributes, grade)
    return {"attributes": attributes, "grade": grade, "grades": [grade]}


def generate_rookie_attributes(overall, rng=None):
    return generate_rookie_profile(overall, rng)["attributes"]


# ── Career profile / development / aging ─────────────────────────────────────
def _assign_rookie_potential(player, rng):
    scout = player.get("scout_grade") or player.get("overall") or 50
    arc = player.get("career_arc", "role")

    if arc == "generational":
        upside = rng.randint(16, 28)
    elif arc == "star":
        upside = rng.randint(13, 23)
    elif arc == "bust":
        upside = rng.randint(0, 3)
    elif arc == "starter":
        upside = rng.randint(5, 13)
    else:
        upside = rng.randint(2, 10)

    player["potential"] = _clamp(scout + upside, POTENTIAL_MIN, POTENTIAL_MAX)
    if player.get("development_rate") is None:
        if arc in ("generational", "star"):
            player["development_rate"] = round(rng.uniform(1.0, 1.2), 3)
        elif arc == "bust":
            player["development_rate"] = round(rng.uniform(0.7, 0.9), 3)
        else:
            player["development_rate"] = round(rng.uniform(0.85, 1.15), 3)


def _assign_potential(player, rng):
    if player.get("potential") is not None:
        return
    if player.get("is_rookie"):
        _assign_rookie_potential(player, rng)
        return

    overall = player.get("overall") or 50
    age = player.get("age") or 30
    peak_age = player.get("peak_age") or DEFAULT_PEAK_AGE
    years_to_peak = max(0, peak_age - age)
    spread = rng.randint(0, 10) + min(years_to_peak, 8)
    player["potential"] = _clamp(overall + spread, POTENTIAL_MIN, POTENTIAL_MAX)
    if player.get("development_rate") is None:
        player["development_rate"] = round(rng.uniform(0.85, 1.15), 3)


def _assign_ceiling_factor(player, rng):
    if player.get("ceiling_factor") is not None:
        return
    player_rng = _player_rng(player, rng)
    arc = player.get("career_arc", "role")
    if arc == "generational":
        player["ceiling_factor"] = round(player_rng.uniform(1.0, 1.05), 3)
    elif arc == "star":
        player["ceiling_factor"] = round(player_rng.uniform(0.98, 1.05), 3)
    elif arc == "bust":
        player["ceiling_factor"] = round(player_rng.uniform(0.85, 0.92), 3)
    elif arc == "starter":
        player["ceiling_factor"] = round(player_rng.uniform(0.92, 0.98), 3)
    else:
        player["ceiling_factor"] = round(player_rng.uniform(0.88, 0.96), 3)


def _assign_stat_modifiers(player, rng):
    if player.get("stat_modifiers"):
        return
    player_rng = _player_rng(player, rng)
    mods = {
        stat: round(player_rng.uniform(STAT_MODIFIER_LOW, STAT_MODIFIER_HIGH), 3)
        for stat in STAT_FROM_ATTR
    }
    mods["ppr"] = round(player_rng.uniform(0.9, 1.15), 3)
    player["stat_modifiers"] = mods


def _assign_peak_attributes(player, rng):
    if player.get("peak_attributes"):
        return
    _assign_ceiling_factor(player, rng)
    player_rng = _player_rng(player, rng)
    potential = player.get("potential") or player.get("overall") or 50
    ceiling_factor = player.get("ceiling_factor", 1.0)
    grade = ensure_grade(player)
    weights = _grade_attr_bias(grade)
    weight_sum = sum(weights.get(key, 1.0) for key in ATTRIBUTE_KEYS if key != "stamina")
    if weight_sum <= 0:
        weight_sum = 1.0

    peak = {}
    for key in ATTRIBUTE_KEYS:
        if key == "stamina":
            peak[key] = _clamp((potential * 0.95 + player_rng.randint(-3, 3)) * ceiling_factor)
            continue
        share = weights.get(key, 1.0) / weight_sum
        base = potential * (0.78 + share * 0.30)
        spread = player_rng.randint(-5, 5)
        peak[key] = _clamp((base + spread) * ceiling_factor, MIN_ATTR, min(MAX_ATTR, potential + 5))
    player["peak_attributes"] = peak


def _attribute_ceiling(player, attr_key):
    peak = player.get("peak_attributes")
    if peak and attr_key in peak:
        return peak[attr_key]
    potential = player.get("potential") or player.get("overall") or 50
    bias = _grade_attr_bias(ensure_grade(player))
    multiplier = max(ATTR_BIAS_MIN, min(ATTR_BIAS_MAX, bias.get(attr_key, 1.0)))
    if attr_key == "stamina":
        return _clamp(potential * 0.95 + 5)
    return _clamp(potential * multiplier * 0.85)


def _apply_development(player, rng):
    age = player.get("age", 30)
    peak_age = player.get("peak_age", DEFAULT_PEAK_AGE)
    if age >= peak_age or age <= CAREER_START_AGE:
        return

    base = player.setdefault("base_attributes", {})
    dev_rate = player.get("development_rate") or 1.0
    span = max(peak_age - CAREER_START_AGE, 1)
    growth_rate = 0.09 * dev_rate / span

    for key in ATTRIBUTE_KEYS:
        ceiling = _attribute_ceiling(player, key)
        current = base.get(key, MIN_ATTR)
        if current >= ceiling:
            continue
        delta = max(1, round((ceiling - current) * growth_rate))
        if player.get("reserve"):
            delta = max(1, round(delta * 1.4))
        base[key] = _clamp(min(current + delta, ceiling))


def _roll_season_form(rng):
    roll = rng.random()
    if roll < 0.25:
        return round(rng.uniform(0.80, 0.92), 3)
    if roll < 0.40:
        return round(rng.uniform(1.06, 1.18), 3)
    return round(rng.uniform(0.96, 1.05), 3)


def _apply_seasonal_noise(player, rng):
    base = player.get("base_attributes")
    if not base:
        return

    player["season_form"] = _roll_season_form(rng)

    keys = list(ATTRIBUTE_KEYS)
    rng.shuffle(keys)
    for key in keys[: rng.randint(2, 3)]:
        base[key] = _clamp(base.get(key, MIN_ATTR) + rng.randint(-4, 4))

    if rng.random() < 0.10:
        hit_key = rng.choice(list(ATTRIBUTE_KEYS))
        base[hit_key] = _clamp(base.get(hit_key, MIN_ATTR) + rng.randint(-7, -3))
        player["off_season_note"] = "setback"
    else:
        player.pop("off_season_note", None)


def init_career_profile(player, rng=None):
    rng = rng or random.Random()
    if player.get("age") is None:
        player["age"] = 30

    ensure_grade(player)

    if player.get("peak_age") is None:
        player["peak_age"] = rng.randint(PEAK_AGE_MIN, PEAK_AGE_MAX)
    if player.get("retirement_age") is None:
        rolled = rng.randint(RETIRE_AGE_MIN, RETIRE_AGE_MAX)
        player["retirement_age"] = max(rolled, int(player.get("age") or 30) + 1)

    if player.get("season_form") is None:
        player["season_form"] = 1.0
    if not player.get("career_arc"):
        player["career_arc"] = "starter" if (player.get("overall") or 0) >= 75 else "role"

    _assign_potential(player, rng)
    _assign_peak_attributes(player, rng)
    _assign_stat_modifiers(player, rng)
    if player.get("pace_bias") is None:
        player["pace_bias"] = round(rng.uniform(0.94, 1.10), 3)
    if player.get("season_gp") is None:
        player["season_gp"] = 0

    if player.get("base_attributes"):
        return player

    peak_age = player["peak_age"]
    age = player.get("age", 30)
    multiplier = age_multiplier(age, peak_age)
    stamina_multiplier = stamina_age_multiplier(age, peak_age)

    if not player.get("attributes"):
        player["attributes"] = derive_attributes(player)

    player["base_attributes"] = _scale_base_attributes(
        player["attributes"], multiplier, stamina_multiplier
    )
    return player


def init_career_profiles(players, rng=None):
    rng = rng or random.Random()
    for player in players:
        init_career_profile(player, rng)
    return players


def effective_attributes(player):
    init_career_profile(player)
    base = player.get("base_attributes") or player.get("attributes") or derive_attributes(player)
    age = player.get("age", 30)
    peak_age = player.get("peak_age", DEFAULT_PEAK_AGE)
    multiplier = age_multiplier(age, peak_age)
    stamina_multiplier = stamina_age_multiplier(age, peak_age)

    effective = {}
    for key in ATTRIBUTE_KEYS:
        attr_multiplier = stamina_multiplier if key == "stamina" else multiplier
        effective[key] = _clamp(base.get(key, MIN_ATTR) * attr_multiplier)
    return effective


def refresh_player_from_attributes(player, effective_attrs=None):
    manual_ppr = None
    if player.get("stats_source") == "manual" and player.get("ppr") is not None:
        manual_ppr = float(player["ppr"])
    if effective_attrs is None:
        effective_attrs = effective_attributes(player)
    player["attributes"] = dict(effective_attrs)
    stats = season_averages_from_attributes_deterministic(effective_attrs, player)
    player.update(stats)
    if manual_ppr is not None:
        player["ppr"] = round(manual_ppr, 1)
    return player


def refresh_team_roster_stats(team_roster):
    """Recompute each driver's display stats from their attributes."""
    if not team_roster:
        return team_roster
    for player in team_roster:
        refresh_player_from_attributes(player)
    return team_roster


def mark_grid_stats(player, source_gp=None):
    """Preserve curated season stats for established drivers."""
    gp = source_gp if source_gp is not None else (player.get("gp") or 0)
    if gp >= MIN_ROUNDS_FOR_RATINGS and not player.get("is_rookie"):
        player["stats_source"] = "grid"
        player["cache_stats"] = {stat: player.get(stat, 0) for stat in STAT_FROM_ATTR}
    elif not player.get("stats_source"):
        player["stats_source"] = "generated"


def backfill_career_metadata(player, rng=None):
    init_career_profile(player, rng)
    if player.get("stats_source") != "grid":
        refresh_player_from_attributes(player)
    player["overall"] = compute_intrinsic_overall(player)
    return player


def init_rookie_career_profile(player, effective_attrs, rng=None, scout_grade=None):
    rng = rng or random.Random()
    if scout_grade is not None:
        player["scout_grade"] = scout_grade
    player["peak_age"] = rng.randint(PEAK_AGE_MIN, PEAK_AGE_MAX)
    player["retirement_age"] = rng.randint(RETIRE_AGE_MIN, RETIRE_AGE_MAX)
    player["season_gp"] = 0
    player["season_form"] = 1.0
    _assign_potential(player, rng)
    _assign_peak_attributes(player, rng)
    _assign_stat_modifiers(player, rng)
    age = player.get("age", 20)
    multiplier = age_multiplier(age, player["peak_age"])
    stamina_multiplier = stamina_age_multiplier(age, player["peak_age"])
    player["base_attributes"] = _scale_base_attributes(effective_attrs, multiplier, stamina_multiplier)
    refresh_player_from_attributes(player, effective_attributes(player))
    player["overall"] = compute_intrinsic_overall(player)
    return player


def _remove_player_from_league(season, player_id):
    season["players"].pop(str(player_id), None)
    for roster in season.get("rosters", {}).values():
        while player_id in roster:
            roster.remove(player_id)
    for res_ids in season.get("reserve_assignments", {}).values():
        while player_id in res_ids:
            res_ids.remove(player_id)
    free_agents = season.get("free_agents", [])
    while player_id in free_agents:
        free_agents.remove(player_id)


def _should_fa_depart(player):
    unsigned = int(player.get("unsigned_seasons") or 0)
    age = int(player.get("age") or 0)
    overall = int(player.get("overall") or 0)
    if unsigned >= 2 and overall >= 80:
        return True
    if unsigned >= 3 and overall >= 70:
        return True
    if unsigned >= 3 and age >= 40:
        return True
    if unsigned >= 2 and overall < 60:
        return True
    return False


def apply_season_aging(season, rng=None):
    rng = rng or random.Random()
    retirements = []
    departures = []
    players = list(season.get("players", {}).values())
    removing_ids = set()

    for player in players:
        init_career_profile(player, rng)
        player["age"] = int(player.get("age", 30)) + 1
        is_fa = not player.get("team_id")

        if is_fa:
            player["unsigned_seasons"] = int(player.get("unsigned_seasons") or 0) + 1
            try:
                from contracts import compute_asking_salary

                player["asking_salary"] = compute_asking_salary(player)
            except ImportError:
                pass

        if player["age"] >= player["retirement_age"]:
            removing_ids.add(player["id"])
            retirements.append(
                {
                    "player_id": player["id"],
                    "name": player.get("name", str(player["id"])),
                    "age": player["age"],
                    "team": player.get("team"),
                    "team_id": player.get("team_id"),
                }
            )
            continue

        if is_fa and _should_fa_depart(player):
            removing_ids.add(player["id"])
            departures.append(
                {
                    "player_id": player["id"],
                    "name": player.get("name", str(player["id"])),
                    "age": player["age"],
                    "unsigned_seasons": player.get("unsigned_seasons"),
                }
            )
            continue

        _apply_development(player, rng)
        _apply_seasonal_noise(player, rng)
        refresh_player_from_attributes(player)
        player["overall"] = compute_intrinsic_overall(player)

    for player_id in removing_ids:
        _remove_player_from_league(season, player_id)

    season["last_retirements"] = retirements
    season["last_departures"] = departures
    return retirements
