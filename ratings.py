"""Driver and team performance ratings derived from season stat lines.

Stats: ppr (points per round), pod (podiums), ovt (positions gained), pol (poles), fl (fastest
laps). Driver overall is a league-relative percentile blend; team overall is built from a team's
race crew (its strongest drivers).
"""

MIN_ROUNDS_FOR_RATINGS = 1
LEAGUE_OVR_SCALE = 0.94
STAT_WEIGHTS = {"ppr": 3.0, "pod": 1.6, "ovt": 1.2, "pol": 1.4, "fl": 0.8}
STAT_COLUMNS = ("ppr", "pod", "ovt", "pol", "fl")
DERIVED_STATS = ("overall",)
RANK_COLUMNS = STAT_COLUMNS + DERIVED_STATS
STAT_LABELS = {
    "ppr": "PPR",
    "pod": "POD",
    "ovt": "OVT",
    "pol": "POL",
    "fl": "FL",
    "overall": "OVR",
}

ATTR_OVERALL_WEIGHTS = {
    "pace": 3.0,
    "racecraft": 1.5,
    "tyre_management": 1.5,
    "consistency": 2.0,
    "fuel_management": 1.0,
}
MIN_INTRINSIC_OVERALL = 25
MAX_INTRINSIC_OVERALL = 99

# Crew / team rating tuning (a race entry fields a small crew, not a 15-man roster).
CREW_SIZE = 3
TOP_DRIVER_WEIGHT = 2.0
TOP_DRIVER_COUNT = 2
DEPTH_DRIVER_WEIGHT = 0.8
MIN_QUALIFIED_DRIVERS = 2


def rating_pool(players):
    return [p for p in players if (p.get("gp") or 0) >= MIN_ROUNDS_FOR_RATINGS]


def _competition_rank(value, pool_values):
    return 1 + sum(1 for pool_value in pool_values if pool_value > value)


def compute_stat_ranks(players):
    pool = rating_pool(players)
    ranks_by_id = {p["id"]: {} for p in players}

    for stat in RANK_COLUMNS:
        pool_values = [p[stat] for p in pool if p.get(stat) is not None]
        if not pool_values:
            continue
        for p in players:
            value = p.get(stat)
            if value is None:
                continue
            ranks_by_id[p["id"]][stat] = _competition_rank(value, pool_values)

    return ranks_by_id


def compute_stat_percentiles(players):
    pool = rating_pool(players)
    ranks_by_id = compute_stat_ranks(players)
    percentiles_by_id = {p["id"]: {} for p in players}

    for stat in STAT_COLUMNS:
        pool_size = sum(1 for p in pool if p.get(stat) is not None)
        if pool_size == 0:
            continue
        for p in players:
            rank = ranks_by_id[p["id"]].get(stat)
            if rank is not None:
                percentiles_by_id[p["id"]][stat] = 100 * (pool_size - rank + 1) / pool_size

    return percentiles_by_id


def compute_overall_ratings(players):
    percentiles_by_id = compute_stat_percentiles(players)
    overall_by_id = {}

    for p in players:
        player_percentiles = percentiles_by_id.get(p["id"], {})
        weighted_sum = 0.0
        weight_total = 0.0
        for stat, weight in STAT_WEIGHTS.items():
            percentile = player_percentiles.get(stat)
            if percentile is None:
                continue
            weighted_sum += weight * percentile
            weight_total += weight
        if weight_total > 0:
            raw = weighted_sum / weight_total
            overall_by_id[p["id"]] = round(
                max(MIN_INTRINSIC_OVERALL, min(MAX_INTRINSIC_OVERALL, raw * LEAGUE_OVR_SCALE)), 1
            )

    return overall_by_id


def apply_ratings(players):
    overall_by_id = compute_overall_ratings(players)
    for p in players:
        overall = overall_by_id.get(p["id"])
        if overall is not None:
            p["overall"] = overall
        else:
            p.pop("overall", None)
    return players


def compute_intrinsic_overall(player):
    """Absolute OVR from effective attributes (not league-relative percentiles)."""
    from attributes import effective_attributes

    attrs = player.get("attributes") or effective_attributes(player)
    weighted_sum = 0.0
    weight_total = 0.0
    for key, weight in ATTR_OVERALL_WEIGHTS.items():
        value = attrs.get(key)
        if value is None:
            continue
        weighted_sum += weight * value
        weight_total += weight
    if weight_total <= 0:
        return player.get("overall") or 50
    raw = weighted_sum / weight_total
    return round(max(MIN_INTRINSIC_OVERALL, min(MAX_INTRINSIC_OVERALL, raw)), 1)


def needs_ratings(players):
    return any(p.get("overall") is None for p in players) or any(
        p.get("gp") is None for p in players
    )


def team_rating_pool(team_players, team_gp=None):
    return sorted(
        [p for p in team_players if p.get("overall") is not None],
        key=lambda p: p["overall"],
        reverse=True,
    )


def build_team_top_players(pool, team_gp=None):
    return pool[:CREW_SIZE]


def _team_overall_weight(index):
    return TOP_DRIVER_WEIGHT if index < TOP_DRIVER_COUNT else DEPTH_DRIVER_WEIGHT


def compute_team_overall(team_players, team_gp=None):
    pool = team_rating_pool(team_players)
    if len(pool) < MIN_QUALIFIED_DRIVERS:
        if not pool:
            return None
        # Tiny squad: just average what we have.
        return round(sum(p["overall"] for p in pool) / len(pool), 1)

    crew = pool[:CREW_SIZE]
    weighted_sum = sum(p["overall"] * _team_overall_weight(i) for i, p in enumerate(crew))
    weight_total = sum(_team_overall_weight(i) for i, _ in enumerate(crew))
    if weight_total <= 0:
        return None
    return round(weighted_sum / weight_total, 1)


def compute_team_consistency_rating(team_players, team_gp=None):
    """Crew-weighted average consistency attribute (higher = fewer mistakes / DNFs)."""
    from attributes import get_attributes

    pool = team_rating_pool(team_players)
    if not pool:
        pool = sorted(team_players, key=lambda p: p.get("overall") or 0, reverse=True)
    crew = pool[:CREW_SIZE]
    if not crew:
        return 50.0
    total = sum(get_attributes(p).get("consistency", 50) for p in crew)
    return round(total / len(crew), 1)


def build_team_summaries(players):
    teams_by_id = {}

    for p in players:
        team_id = p.get("team_id")
        if not team_id:
            continue
        if team_id not in teams_by_id:
            teams_by_id[team_id] = {
                "team_id": team_id,
                "team": p.get("team", "Unknown"),
                "class": p.get("class"),
                "players": [],
            }
        teams_by_id[team_id]["players"].append(p)

    summaries = []
    for team_data in teams_by_id.values():
        roster = team_data["players"]
        top_player = max(roster, key=lambda p: p.get("overall") or 0, default=None)
        summaries.append(
            {
                "team_id": team_data["team_id"],
                "team": team_data["team"],
                "class": team_data.get("class"),
                "overall": compute_team_overall(roster),
                "roster_size": len(roster),
                "top_player_name": top_player.get("name") if top_player else None,
                "top_player_overall": top_player.get("overall") if top_player else None,
            }
        )

    return summaries


def compute_team_ranks(summaries):
    ranks_by_id = {s["team_id"]: {} for s in summaries}
    pool_values = [s["overall"] for s in summaries if s.get("overall") is not None]
    if not pool_values:
        return ranks_by_id

    for s in summaries:
        overall = s.get("overall")
        if overall is not None:
            ranks_by_id[s["team_id"]]["overall"] = _competition_rank(overall, pool_values)

    return ranks_by_id
