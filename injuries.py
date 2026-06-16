"""Driver availability: injuries and incidents that sideline a driver for a round or two."""

import random

from ratings import CREW_SIZE, team_rating_pool

INCIDENT_TYPES = (
    "wrist injury",
    "neck strain",
    "concussion protocol",
    "illness",
    "dehydration",
    "back spasm",
    "shoulder strain",
    "hand fracture",
    "fitness setback",
)

INCIDENT_CHANCE_PER_ROUND = 0.03
SEVERE_CHANCE = 0.20
MAX_INCIDENTS_PER_ROUND = 2
MIN_RACE_DRIVERS = 2


def _can_add_league_incident(season, round_num) -> bool:
    counts = season.setdefault("incident_round_counts", {})
    return counts.get(str(round_num), 0) < MAX_INCIDENTS_PER_ROUND


def _record_league_incident(season, round_num) -> None:
    counts = season.setdefault("incident_round_counts", {})
    key = str(round_num)
    counts[key] = counts.get(key, 0) + 1


def driver_is_unavailable(player) -> bool:
    injury = player.get("injury")
    if not injury:
        return False
    return int(injury.get("rounds_remaining") or 0) > 0


def unavailable_driver_ids(roster):
    return {p["id"] for p in roster if driver_is_unavailable(p)}


def race_exclude_ids(roster, min_drivers=MIN_RACE_DRIVERS):
    """Unavailable ids to exclude; reinstate the closest-to-fit if too few healthy drivers."""
    unavailable = {
        p["id"]: int((p.get("injury") or {}).get("rounds_remaining") or 0)
        for p in roster
        if driver_is_unavailable(p)
    }
    if not unavailable:
        return set()

    excluded = set(unavailable.keys())
    available = len(roster) - len(excluded)
    target = min(min_drivers, len(roster))

    while available < target and excluded:
        reinstate = min(excluded, key=lambda pid: unavailable[pid])
        excluded.discard(reinstate)
        available += 1

    return excluded


def build_dnf_list(roster, exclude_ids):
    return [
        {
            "player_id": p["id"],
            "name": p.get("name", str(p["id"])),
            "reason": (p.get("injury") or {}).get("type", "unavailable"),
        }
        for p in roster
        if p["id"] in exclude_ids
    ]


def _incident_duration(rng, severe):
    if severe:
        return rng.randint(2, 3)
    return 1


def roll_round_incidents(season, team_id, roster, round_num, rng=None, user_team_id=None):
    rng = rng or random.Random()
    pool = team_rating_pool(roster)
    if not pool:
        pool = sorted(roster, key=lambda p: p.get("overall") or 0, reverse=True)
    crew = pool[:CREW_SIZE]

    events = []
    incident_log = season.setdefault("incident_log", [])
    pending = season.setdefault("pending_notifications", [])
    notify_user = user_team_id is not None and int(team_id) == int(user_team_id)

    for player in crew:
        if driver_is_unavailable(player):
            continue
        if not _can_add_league_incident(season, round_num):
            continue
        if rng.random() >= INCIDENT_CHANCE_PER_ROUND:
            continue

        severe = rng.random() < SEVERE_CHANCE
        incident_type = rng.choice(INCIDENT_TYPES)
        rounds_out = _incident_duration(rng, severe)
        player["injury"] = {
            "type": incident_type,
            "rounds_remaining": rounds_out,
            "round_reported": round_num,
            "severe": severe,
        }
        _record_league_incident(season, round_num)

        event = {
            "player_id": player["id"],
            "player_name": player.get("name", str(player["id"])),
            "team_id": team_id,
            "type": incident_type,
            "rounds_out": rounds_out,
            "round": round_num,
        }
        events.append(event)
        incident_log.append(event)
        incident_log[:] = incident_log[-40:]
        if notify_user:
            pending.append(
                f"{event['player_name']} ({incident_type}) — out {rounds_out} round"
                f"{'s' if rounds_out != 1 else ''}"
            )
        try:
            from news import append_news
            from season import team_name

            append_news(season, "injury", player=event["player_name"],
                        team=team_name(season, team_id), detail=incident_type)
        except ImportError:
            pass

    return events


def tick_incidents_after_round(roster):
    for player in roster:
        injury = player.get("injury")
        if not injury:
            continue
        remaining = int(injury.get("rounds_remaining") or 0)
        if remaining <= 1:
            player.pop("injury", None)
        else:
            injury["rounds_remaining"] = remaining - 1


def user_team_incident_report(season, user_team_id, lookup):
    if not user_team_id:
        return []
    from season import roster_players

    roster = roster_players(season, int(user_team_id), lookup)
    report = []
    for player in roster:
        injury = player.get("injury")
        if not injury:
            continue
        remaining = int(injury.get("rounds_remaining") or 0)
        if remaining <= 0:
            continue
        report.append(
            {
                "player_id": player["id"],
                "player_name": player.get("name", str(player["id"])),
                "team_id": int(user_team_id),
                "type": injury.get("type", "unavailable"),
                "rounds_remaining": remaining,
            }
        )
    report.sort(key=lambda item: item["rounds_remaining"], reverse=True)
    return report


def drain_pending_notifications(season, user_team_id=None):
    pending = list(season.get("pending_notifications") or [])
    season["pending_notifications"] = []
    return pending
