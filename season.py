"""Season engine: the eight-round WEC calendar, championship points standings, race
orchestration, the season finale, and the off-season roll-over.

Unlike a head-to-head league, every team contests every round. Standings accumulate
championship points within each class (Hypercar, LMGT3). The final round (Bahrain) is the
title-deciding finale.
"""

import random

import wec_data
from attributes import (
    apply_attributes,
    apply_season_aging,
    backfill_career_metadata,
    ensure_grade,
    init_career_profile,
    mark_grid_stats,
    needs_attributes,
    refresh_team_roster_stats,
)
from difficulty import get_difficulty_settings
from names import dedupe_all_player_names
from ratings import (
    CREW_SIZE,
    compute_team_consistency_rating,
    compute_team_overall,
)
from simulation import qualifying, simulate_class_race

CLASSES = wec_data.CLASSES
ROUNDS_PER_SEASON = len(wec_data.CALENDAR)
REGULAR_ROUNDS = ROUNDS_PER_SEASON - 1  # rounds 1..7; round 8 is the finale
TRANSFER_DEADLINE_ROUNDS = 5
NEXT_PLAYER_ID_START = 9000001
DRAFT_ROUNDS = 2

WEC_POINTS_LABEL = "championship points"

DNF_FACTOR_BY_FORMAT = {
    "24 Hours": 1.9,
    "8 Hours": 1.4,
    "1812 km": 1.1,
    "6 Hours": 1.0,
}


# ── Player pool / lookup ─────────────────────────────────────────────────────
def build_player_pool(cache_players, rng=None):
    rng = rng or random.Random()
    pool = {}
    for player in cache_players:
        player_id = player["id"]
        entry = dict(player)
        original_gp = player.get("gp") or 0
        entry["is_rookie"] = False
        entry["season_gp"] = 0
        ensure_grade(entry)
        init_career_profile(entry, rng)
        mark_grid_stats(entry, source_gp=original_gp)
        pool[str(player_id)] = entry
    dedupe_all_player_names(pool.values())
    return pool


def league_lookup(season):
    lookup = {}
    for key, player in season.get("players", {}).items():
        player_id = player.get("id", int(key))
        lookup[player_id] = player
    return lookup


def players_by_id(players):
    return {p["id"]: p for p in players}


def roster_players(season, team_id, lookup=None):
    if lookup is None:
        lookup = league_lookup(season)
    roster_ids = season.get("rosters", {}).get(str(team_id), [])
    players = []
    for player_id in roster_ids:
        pid = int(player_id)
        if pid in lookup:
            players.append(lookup[pid])
    return players


def allocate_player_id(season):
    player_id = season.get("next_player_id", NEXT_PLAYER_ID_START)
    season["next_player_id"] = player_id + 1
    return player_id


def team_class(season, team_id):
    return season.get("team_class", {}).get(str(team_id))


def team_name(season, team_id):
    standing = season.get("standings", {}).get(str(team_id), {})
    return standing.get("team_name", str(team_id))


# ── Draft picks (Young Driver Programme test slots) ─────────────────────────
def init_draft_picks(team_ids, year):
    picks_by_team = {}
    slot_number = 1
    for team_id in sorted(team_ids):
        team_picks = []
        for round_num in range(1, DRAFT_ROUNDS + 1):
            team_picks.append(
                {
                    "id": f"slot-{team_id}-{year}-r{round_num}",
                    "year": year,
                    "round": round_num,
                    "overall": slot_number,
                    "original_team_id": team_id,
                }
            )
            slot_number += 1
        picks_by_team[str(team_id)] = team_picks
    return picks_by_team


# ── Season setup ─────────────────────────────────────────────────────────────
def init_season(players, season_year=None, rng=None, difficulty="normal"):
    rng = rng or random.Random()
    from difficulty import normalize_difficulty

    season_year = season_year or wec_data.CURRENT_SEASON
    difficulty = normalize_difficulty(difficulty)
    difficulty_settings = get_difficulty_settings({"difficulty": difficulty})

    if needs_attributes(players):
        apply_attributes(players)

    team_players = {}
    team_names = {}
    team_class_map = {}
    free_agent_ids = []
    for player in players:
        team_id = player.get("team_id")
        if not team_id:
            free_agent_ids.append(player["id"])
            continue
        team_players.setdefault(team_id, []).append(player["id"])
        team_names[team_id] = player.get("team", "Unknown")
        team_class_map[team_id] = player.get("class", "Hypercar")

    team_ids = sorted(team_players.keys())
    schedule = generate_schedule()
    standings = {
        str(team_id): {
            "points": 0,
            "wins": 0,
            "podiums": 0,
            "poles": 0,
            "rounds": 0,
            "team_name": team_names[team_id],
            "class": team_class_map[team_id],
        }
        for team_id in team_ids
    }
    draft_year = season_year + 1
    future_year = season_year + 2
    player_pool = build_player_pool(players, rng)
    season = {
        "season_year": season_year,
        "phase": "regular",
        "current_round": 1,
        "max_round": ROUNDS_PER_SEASON,
        "regular_rounds": REGULAR_ROUNDS,
        "transfer_deadline_rounds": TRANSFER_DEADLINE_ROUNDS,
        "next_player_id": NEXT_PLAYER_ID_START,
        "players": player_pool,
        "team_class": {str(team_id): team_class_map[team_id] for team_id in team_ids},
        "free_agents": sorted(set(free_agent_ids)),
        "draft_picks": init_draft_picks(team_ids, draft_year),
        "future_draft_picks": init_draft_picks(team_ids, future_year),
        "draft_state": None,
        "trades": [],
        "rosters": {str(team_id): roster for team_id, roster in team_players.items()},
        "standings": standings,
        "schedule": schedule,
        "finale": None,
        "recent_results": [],
        "news_feed": [],
        "team_finances": {},
        "pending_fa_offers": {},
        "incident_log": [],
        "incident_round_counts": {},
        "pending_notifications": [],
        "championships": {},
        "gm_personalities_enabled": difficulty_settings["gm_personalities_from_start"],
        "gm_profiles": {},
        "difficulty": difficulty,
        "contract_alerts": [],
        "pending_championship_bonus": None,
    }
    from roster import _sync_free_agents

    _sync_free_agents(season)
    season["free_agents"] = sorted(set(season.get("free_agents", []) + free_agent_ids))
    refresh_all_roster_stats(season, league_lookup(season))
    from contracts import assign_initial_contracts

    assign_initial_contracts(season, rng)
    if difficulty_settings["gm_personalities_from_start"]:
        from gm_personalities import reroll_gm_personalities

        reroll_gm_personalities(season, rng)
    return season


def generate_schedule():
    schedule = []
    for round_info in wec_data.calendar():
        fmt = round_info.get("format", "6 Hours")
        schedule.append(
            {
                "id": round_info["round"],
                "round": round_info["round"],
                "name": round_info["name"],
                "circuit": round_info["circuit"],
                "country": round_info["country"],
                "format": fmt,
                "marquee": round_info.get("marquee", False),
                "finale": round_info.get("finale", False),
                "points_mult": round_info.get("points_mult", 1.0),
                "dnf_factor": DNF_FACTOR_BY_FORMAT.get(fmt, 1.0),
                "played": False,
                "results": {},
            }
        )
    return schedule


def refresh_all_roster_stats(season, lookup=None):
    lookup = lookup or league_lookup(season)
    for team_id_str in season.get("rosters", {}).keys():
        roster = roster_players(season, int(team_id_str), lookup)
        refresh_team_roster_stats(roster)


# ── Migration for older saves ────────────────────────────────────────────────
def migrate_season(season, rng=None):
    rng = rng or random.Random()
    season.setdefault("free_agents", [])
    season.setdefault("championships", {})
    season.setdefault("incident_round_counts", {})
    season.setdefault("gm_personalities_enabled", False)
    season.setdefault("gm_profiles", {})
    season.setdefault("contract_alerts", [])
    season.setdefault("reserve_assignments", {})
    season.setdefault("team_class", {})
    if "future_draft_picks" not in season:
        team_ids = [int(tid) for tid in season.get("rosters", {}).keys()]
        season["future_draft_picks"] = init_draft_picks(team_ids, season.get("season_year", 2025) + 2)
    if not season.get("team_class"):
        for team_id_str in season.get("rosters", {}).keys():
            roster = season["rosters"][team_id_str]
            cls = "Hypercar"
            for pid in roster:
                player = season.get("players", {}).get(str(pid))
                if player and player.get("class"):
                    cls = player["class"]
                    break
            season["team_class"][team_id_str] = cls
    from roster import reconcile_all_rosters

    reconcile_all_rosters(season)
    lookup = league_lookup(season)
    for player in season.get("players", {}).values():
        backfill_career_metadata(player, rng)
    refresh_all_roster_stats(season, lookup)
    from contracts import ensure_contract_fields

    ensure_contract_fields(season, rng)
    free_agents = []
    for key, player in season.get("players", {}).items():
        if not player.get("team_id"):
            free_agents.append(player.get("id", int(key)))
    season["free_agents"] = sorted(set(free_agents))
    return season


# ── Transfer window ──────────────────────────────────────────────────────────
def rounds_completed(season):
    return sum(1 for r in season.get("schedule", []) if r.get("played"))


def all_teams_at_rounds(season, target):
    return rounds_completed(season) >= target


def can_trade(season):
    phase = season.get("phase", "regular")
    if phase in {"draft", "offseason"}:
        return True
    if phase == "regular":
        target = season.get("transfer_deadline_rounds", TRANSFER_DEADLINE_ROUNDS)
        return not all_teams_at_rounds(season, target)
    return False


def regular_season_complete(season):
    played_regular = sum(
        1 for r in season.get("schedule", []) if r.get("played") and not r.get("finale")
    )
    return played_regular >= REGULAR_ROUNDS


def finale_complete(season):
    for r in season.get("schedule", []):
        if r.get("finale"):
            return r.get("played", False)
    return False


# ── Standings ────────────────────────────────────────────────────────────────
def standings_table(season, class_name=None):
    rows = []
    for team_id_str, record in season.get("standings", {}).items():
        team_id = int(team_id_str)
        row_class = record.get("class") or team_class(season, team_id)
        if class_name and row_class != class_name:
            continue
        rows.append(
            {
                "team_id": team_id,
                "team_name": record.get("team_name", str(team_id)),
                "class": row_class,
                "points": record.get("points", 0),
                "wins": record.get("wins", 0),
                "podiums": record.get("podiums", 0),
                "poles": record.get("poles", 0),
                "rounds": record.get("rounds", 0),
            }
        )

    rows.sort(key=lambda row: (row["points"], row["wins"], row["podiums"], row["poles"]), reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def team_ovr_for_tiebreak(season, team_id, lookup):
    roster = roster_players(season, team_id, lookup)
    return compute_team_overall(roster) or 0


# ── Race orchestration ───────────────────────────────────────────────────────
def _active_crew(season, team_id, roster, round_num, rng, user_team_id):
    from injuries import race_exclude_ids, roll_round_incidents

    roll_round_incidents(season, team_id, roster, round_num, rng, user_team_id=user_team_id)
    excluded = race_exclude_ids(roster)
    available = [p for p in roster if p["id"] not in excluded]
    if not available:
        available = list(roster)
    available.sort(key=lambda p: p.get("overall") or 0, reverse=True)
    return available[:CREW_SIZE], excluded


def _build_entries(season, class_name, lookup, round_num, rng, user_team_id):
    entries = []
    for team_id_str, record in season.get("standings", {}).items():
        team_id = int(team_id_str)
        if (record.get("class") or team_class(season, team_id)) != class_name:
            continue
        roster = roster_players(season, team_id, lookup)
        crew, _excluded = _active_crew(season, team_id, roster, round_num, rng, user_team_id)
        rating_pool = crew or roster
        entries.append(
            {
                "team_id": team_id,
                "team_name": record.get("team_name", str(team_id)),
                "class": class_name,
                "overall": compute_team_overall(rating_pool) or 50,
                "consistency": compute_team_consistency_rating(rating_pool),
                "crew": crew,
            }
        )
    return entries


def _apply_round_result(season, round_entry, classification, lookup, user_team_id):
    from injuries import tick_incidents_after_round

    standings = season["standings"]
    for row in classification:
        record = standings.get(str(row["team_id"]))
        if record is None:
            continue
        record["points"] = record.get("points", 0) + row["points"]
        record["rounds"] = record.get("rounds", 0) + 1
        if row["status"] == "Classified" and row["position"] == 1:
            record["wins"] = record.get("wins", 0) + 1
        if row["status"] == "Classified" and row["position"] <= 3:
            record["podiums"] = record.get("podiums", 0) + 1
        if row.get("pole"):
            record["poles"] = record.get("poles", 0) + 1
        # Driver participation for awards.
        for crew_member in row.get("crew", []):
            player = season.get("players", {}).get(str(crew_member["player_id"]))
            if player is not None:
                player["season_gp"] = int(player.get("season_gp") or 0) + 1
                player["gp"] = int(player.get("gp") or 0) + 1

    # Tick incident counters down for everyone who raced.
    for team_id_str in season.get("rosters", {}).keys():
        tick_incidents_after_round(roster_players(season, int(team_id_str), lookup))


def _record_round_news(season, round_entry, classification_by_class):
    try:
        from news import append_news
    except ImportError:
        return
    for class_name, classification in classification_by_class.items():
        if not classification:
            continue
        winner = classification[0]
        if winner["status"] == "Classified":
            append_news(
                season,
                "race_win",
                team=winner["team_name"],
                race=round_entry["name"],
                cls=class_name,
            )
        # An upset: low grid position winning.
        if winner["status"] == "Classified" and winner.get("grid", 1) >= 4:
            append_news(
                season,
                "upset",
                winner=winner["team_name"],
                race=round_entry["name"],
                grid=winner.get("grid"),
            )


def _play_round(season, round_entry, lookup, rng, user_team_id=None):
    user_team_id = user_team_id or season.get("user_team_id")
    settings = get_difficulty_settings(season)
    round_num = round_entry["round"]
    dnf_factor = round_entry.get("dnf_factor", 1.0)
    points_mult = round_entry.get("points_mult", 1.0)

    classification_by_class = {}
    for class_name in CLASSES:
        entries = _build_entries(season, class_name, lookup, round_num, rng, user_team_id)
        grid = qualifying(entries, rng)
        classification = simulate_class_race(
            entries, rng=rng, settings=settings, dnf_factor=dnf_factor,
            points_mult=points_mult, grid=grid,
        )
        classification_by_class[class_name] = classification

    for classification in classification_by_class.values():
        _apply_round_result(season, round_entry, classification, lookup, user_team_id)

    round_entry["results"] = classification_by_class
    round_entry["played"] = True

    # Recent results banner.
    summary = {"round": round_num, "name": round_entry["name"], "winners": {}}
    for class_name, classification in classification_by_class.items():
        if classification and classification[0]["status"] == "Classified":
            summary["winners"][class_name] = classification[0]["team_name"]
    season.setdefault("recent_results", []).insert(0, summary)
    season["recent_results"] = season["recent_results"][:12]

    _record_round_news(season, round_entry, classification_by_class)
    return round_entry


def _next_regular_round(season):
    for round_entry in season.get("schedule", []):
        if not round_entry.get("played") and not round_entry.get("finale"):
            return round_entry
    return None


def _maybe_finish_regular(season):
    if regular_season_complete(season) and season.get("phase") == "regular":
        season["phase"] = "regular_complete"
        season["current_round"] = ROUNDS_PER_SEASON


def _roll_ambient_news(season, lookup, round_num, rng):
    try:
        from news import maybe_roll_paddock_news, maybe_roll_rookie_news

        maybe_roll_paddock_news(season, lookup, round_num, rng)
        maybe_roll_rookie_news(season, lookup, round_num, rng)
    except ImportError:
        pass


def sim_round(season, lookup, rng=None, user_team_id=None):
    if season.get("phase") != "regular":
        return 0
    rng = rng or random.Random()
    user_team_id = user_team_id or season.get("user_team_id")
    round_entry = _next_regular_round(season)
    if round_entry is None:
        _maybe_finish_regular(season)
        return 0
    _play_round(season, round_entry, lookup, rng, user_team_id=user_team_id)
    _roll_ambient_news(season, lookup, round_entry["round"], rng)
    season["current_round"] = min(round_entry["round"] + 1, ROUNDS_PER_SEASON)
    _maybe_finish_regular(season)
    return 1


def sim_double(season, lookup, rng=None, user_team_id=None):
    """Sim up to two regular rounds (a double-header)."""
    count = 0
    for _ in range(2):
        played = sim_round(season, lookup, rng=rng, user_team_id=user_team_id)
        count += played
        if played == 0:
            break
    return count


def sim_to_transfer_deadline(season, lookup, rng=None, user_team_id=None):
    target = season.get("transfer_deadline_rounds", TRANSFER_DEADLINE_ROUNDS)
    count = 0
    while season.get("phase") == "regular" and rounds_completed(season) < target:
        played = sim_round(season, lookup, rng=rng, user_team_id=user_team_id)
        count += played
        if played == 0:
            break
    return count


def sim_rest_of_regular(season, lookup, rng=None, user_team_id=None):
    count = 0
    while season.get("phase") == "regular":
        played = sim_round(season, lookup, rng=rng, user_team_id=user_team_id)
        count += played
        if played == 0:
            break
    _maybe_finish_regular(season)
    return count


# Aliases mirroring the classic flow.
sim_rest_of_season = sim_rest_of_regular


# ── Finale ───────────────────────────────────────────────────────────────────
def finale_round(season):
    for round_entry in season.get("schedule", []):
        if round_entry.get("finale"):
            return round_entry
    return None


def title_contenders(season, class_name, lookup=None, top=4):
    rows = standings_table(season, class_name=class_name)[:top]
    return rows


def run_finale(season, lookup=None, rng=None):
    """Run the Bahrain finale and crown the class champions."""
    rng = rng or random.Random()
    lookup = lookup or league_lookup(season)
    if not regular_season_complete(season):
        sim_rest_of_regular(season, lookup, rng=rng)

    round_entry = finale_round(season)
    if round_entry is None or round_entry.get("played"):
        return 0

    season["phase"] = "finale"
    _play_round(season, round_entry, lookup, rng, user_team_id=season.get("user_team_id"))
    _roll_ambient_news(season, lookup, round_entry["round"], rng)

    champions = {}
    for class_name in CLASSES:
        rows = standings_table(season, class_name=class_name)
        if rows:
            champ = rows[0]
            champions[class_name] = {
                "team_id": champ["team_id"],
                "team_name": champ["team_name"],
                "points": champ["points"],
            }
            record_championship(season, champ["team_id"])

    season["finale"] = {"champions": champions, "decided": True}
    season["phase"] = "complete"
    try:
        from year_end_report import build_year_end_report

        build_year_end_report(season, lookup)
    except ImportError:
        pass
    return 1


# ── Championships ────────────────────────────────────────────────────────────
def championship_count(season, team_id):
    if not season or not team_id:
        return 0
    return int(season.get("championships", {}).get(str(team_id), 0))


def record_championship(season, team_id):
    championships = season.setdefault("championships", {})
    key = str(team_id)
    championships[key] = championships.get(key, 0) + 1
    season["championships"] = championships
    try:
        from news import append_news

        append_news(season, "championship", team=team_name(season, team_id),
                    cls=team_class(season, team_id))
    except ImportError:
        pass
    from contracts import apply_championship_bonuses

    bonus_total = apply_championship_bonuses(season, team_id)
    user_team_id = season.get("user_team_id")
    if user_team_id and int(user_team_id) == int(team_id):
        season["pending_championship_bonus"] = bonus_total
    return championships[key]


# ── Draft order (Young Driver Programme — reverse championship order) ────────
def draft_order(season, lookup=None, rng=None):
    lookup = lookup or league_lookup(season)
    # Worst combined points first; ties broken by weaker squad overall.
    rows = standings_table(season)
    rows.sort(key=lambda row: (row["points"], row["wins"]))  # ascending → worst first
    round1 = [{"team_id": row["team_id"], "team_name": row["team_name"]} for row in rows]
    team_count = len(round1)
    order = []
    for round_num in range(1, DRAFT_ROUNDS + 1):
        for index, row in enumerate(round1, start=1):
            order.append(
                {
                    "pick_number": (round_num - 1) * team_count + index,
                    "round": round_num,
                    "team_id": row["team_id"],
                    "team_name": row["team_name"],
                }
            )
    return {
        "queue": order,
        "draft_order_rows": round1,
        "round1_team_order": round1,
    }


# ── Off-season ───────────────────────────────────────────────────────────────
def advance_season(season, rng=None):
    rng = rng or random.Random()
    from contracts import expire_contracts, sim_cpu_free_agency

    expire_contracts(season)
    if season.get("phase") in {"draft", "offseason", "complete"}:
        sim_cpu_free_agency(season, rng)
    retirements = apply_season_aging(season, rng)
    team_ids = [int(team_id) for team_id in season.get("rosters", {}).keys()]
    team_names = {
        int(team_id): record.get("team_name", str(team_id))
        for team_id, record in season.get("standings", {}).items()
    }
    team_classes = {
        int(team_id): record.get("class") or team_class(season, int(team_id))
        for team_id, record in season.get("standings", {}).items()
    }

    season_year = season.get("season_year", wec_data.CURRENT_SEASON) + 1
    schedule = generate_schedule()
    standings = {
        str(team_id): {
            "points": 0,
            "wins": 0,
            "podiums": 0,
            "poles": 0,
            "rounds": 0,
            "team_name": team_names.get(team_id, str(team_id)),
            "class": team_classes.get(team_id, "Hypercar"),
        }
        for team_id in team_ids
    }

    season.update(
        {
            "season_year": season_year,
            "phase": "regular",
            "current_round": 1,
            "max_round": ROUNDS_PER_SEASON,
            "schedule": schedule,
            "standings": standings,
            "finale": None,
            "recent_results": [],
            "draft_state": None,
            "draft_picks": season.get("future_draft_picks") or init_draft_picks(team_ids, season_year + 1),
            "future_draft_picks": init_draft_picks(team_ids, season_year + 2),
            "last_retirements": retirements,
        }
    )
    try:
        from news import append_news

        for item in retirements:
            append_news(season, "retirement", player=item.get("name", "Unknown"), age=item.get("age"))
        for item in season.get("last_departures") or []:
            append_news(season, "fa_departure", player=item.get("name", "Unknown"), age=item.get("age"))
    except ImportError:
        pass
    for player in season.get("players", {}).values():
        player["season_gp"] = 0
        player["gp"] = 0
    from contracts import clear_championship_bonuses
    from gm_personalities import reroll_gm_personalities

    clear_championship_bonuses(season)
    reroll_gm_personalities(season, rng)
    return season


# ── Schedule helpers ─────────────────────────────────────────────────────────
def schedule_rounds(season):
    return list(season.get("schedule", []))


def find_schedule_round(season, round_id):
    for round_entry in season.get("schedule", []):
        if round_entry.get("id") == round_id or round_entry.get("round") == round_id:
            return round_entry
    return None


def rounds_played_count(season):
    return rounds_completed(season)


def can_sim_regular(season):
    return season.get("phase") == "regular" and _next_regular_round(season) is not None
