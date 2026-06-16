"""End-of-season awards and stat leaders for the Season Review report."""

from season import CLASSES, league_lookup, roster_players, standings_table, team_class, team_name

MIN_AWARD_GP = 4


def _player_line(player):
    parts = []
    if player.get("ppr") is not None:
        parts.append(f"{player['ppr']:.1f} PPR")
    if player.get("pod") is not None:
        parts.append(f"{player['pod']:.0f} podiums")
    if player.get("pol") is not None:
        parts.append(f"{player['pol']:.0f} poles")
    if player.get("ovt") is not None:
        parts.append(f"{player['ovt']:.0f} positions")
    return " · ".join(parts) if parts else ""


def _winner_entry(player, team_id, season=None, value=None, note=None):
    tid = int(team_id) if team_id else None
    if season and tid:
        tname = team_name(season, tid)
    else:
        tname = player.get("team", "—")
    return {
        "player_id": player.get("id"),
        "name": player.get("name", "Unknown"),
        "team_id": tid,
        "team_name": tname,
        "overall": player.get("overall"),
        "age": player.get("age"),
        "grade": player.get("grade"),
        "gp": player.get("season_gp") or player.get("gp") or 0,
        "line": _player_line(player),
        "value": value,
        "note": note,
    }


def _qualified_players(season, lookup, min_gp=MIN_AWARD_GP):
    qualified = []
    for player in season.get("players", {}).values():
        if not player.get("team_id"):
            continue
        gp = int(player.get("season_gp") or player.get("gp") or 0)
        if gp < min_gp:
            continue
        qualified.append(player)
    return qualified


def _team_form(season, team_id):
    cls = team_class(season, team_id)
    rows = standings_table(season, class_name=cls)
    size = len(rows)
    for row in rows:
        if row["team_id"] == int(team_id):
            return max(0.0, 1.0 - (row["rank"] - 1) / max(size - 1, 1))
    return 0.5


def _doy_score(season, player):
    team_id = player.get("team_id")
    ppr = float(player.get("ppr") or 0)
    overall = float(player.get("overall") or 50)
    form = _team_form(season, team_id)
    return ppr * 1.2 + form * 18 + overall * 0.15


def _quali_score(player):
    pace = float((player.get("attributes") or {}).get("pace") or 50)
    pol = float(player.get("pol") or 0)
    overall = float(player.get("overall") or 50)
    return pol * 8 + pace * 0.45 + overall * 0.1


def _endurance_score(player):
    stamina = float((player.get("attributes") or {}).get("stamina") or 50)
    consistency = float((player.get("attributes") or {}).get("consistency") or 50)
    pod = float(player.get("pod") or 0)
    return stamina * 0.4 + consistency * 0.4 + pod * 5


def _is_rookie_candidate(player, season_year):
    if player.get("is_rookie"):
        return True
    drafted = player.get("drafted")
    if drafted and int(drafted) == int(season_year):
        return True
    age = player.get("age") or 30
    gp = int(player.get("season_gp") or player.get("gp") or 0)
    return age <= 23 and gp >= 3


def _principal_of_year(season):
    rows = standings_table(season)
    champion_ids = set()
    finale = season.get("finale") or {}
    for champ in (finale.get("champions") or {}).values():
        champion_ids.add(champ.get("team_id"))
    non_champ = [row for row in rows if row["team_id"] not in champion_ids]
    if not non_champ:
        non_champ = rows
    best = max(non_champ, key=lambda row: row.get("podiums", 0) + row.get("points", 0) * 0.1, default=None)
    if not best:
        return None
    return {
        "team_id": best["team_id"],
        "team_name": best["team_name"],
        "record": f"{best['points']} pts",
        "win_pct": best.get("podiums", 0),
        "note": "Best campaign without a class title",
    }


def build_year_end_report(season, lookup=None):
    lookup = lookup or league_lookup(season)
    season_year = season.get("season_year", 2025)
    qualified = _qualified_players(season, lookup)

    finale = season.get("finale") or {}
    champions = finale.get("champions") or {}

    for player in qualified:
        if player.get("team_id"):
            player["_team_name"] = team_name(season, player["team_id"])

    doy_sorted = sorted(qualified, key=lambda p: _doy_score(season, p), reverse=True)
    quali_sorted = sorted(qualified, key=_quali_score, reverse=True)
    rookie_pool = [p for p in qualified if _is_rookie_candidate(p, season_year)]
    rookie_sorted = sorted(
        rookie_pool, key=lambda p: float(p.get("ppr") or 0) + float(p.get("overall") or 0) * 0.1, reverse=True
    )
    mip_sorted = sorted(
        qualified, key=lambda p: float(p.get("season_form") or 1.0) * float(p.get("ppr") or 0), reverse=True
    )
    endurance_sorted = sorted(qualified, key=_endurance_score, reverse=True)

    def award_block(key, title, sorted_players, value_fn=None, min_pool=1):
        if len(sorted_players) < min_pool:
            return None
        winner = sorted_players[0]
        val = value_fn(winner) if value_fn else None
        runners = []
        for runner in sorted_players[1:4]:
            runners.append(_winner_entry(runner, runner.get("team_id"), season,
                                         value_fn(runner) if value_fn else None))
        return {
            "key": key,
            "title": title,
            "winner": _winner_entry(winner, winner.get("team_id"), season, val),
            "runners_up": runners,
        }

    awards = []
    for block in (
        award_block("doy", "Driver of the Year", doy_sorted, lambda p: round(_doy_score(season, p), 1)),
        award_block("quali", "Qualifying Master", quali_sorted, lambda p: float(p.get("pol") or 0)),
        award_block("roy", "Rookie of the Year", rookie_sorted, lambda p: float(p.get("ppr") or 0),
                    min_pool=1 if rookie_sorted else 99),
        award_block("mip", "Most Improved Driver", mip_sorted, lambda p: round(float(p.get("season_form") or 1.0), 2)),
        award_block("endurance", "Endurance Award", endurance_sorted, lambda p: float(p.get("pod") or 0)),
    ):
        if block:
            awards.append(block)

    stat_leaders = {}
    for stat, label in (
        ("ppr", "Points Per Round"),
        ("pod", "Podiums"),
        ("pol", "Pole Positions"),
        ("ovt", "Positions Gained"),
        ("fl", "Fastest Laps"),
    ):
        leaders = sorted(qualified, key=lambda p, s=stat: float(p.get(s) or 0), reverse=True)[:5]
        stat_leaders[stat] = {
            "label": label,
            "leaders": [_winner_entry(p, p.get("team_id"), season, float(p.get(stat) or 0)) for p in leaders],
        }

    team_sorted = sorted(qualified, key=lambda p: _doy_score(season, p), reverse=True)
    team_of_season = [_winner_entry(p, p.get("team_id"), season) for p in team_sorted[:5]]

    standings_by_class = {}
    for cls in CLASSES:
        rows = standings_table(season, class_name=cls)
        standings_by_class[cls] = [
            {
                "team_name": row["team_name"],
                "points": row["points"],
                "wins": row["wins"],
                "podiums": row["podiums"],
            }
            for row in rows[:10]
        ]

    report = {
        "season_year": season_year,
        "champions": champions,
        "awards": awards,
        "principal_of_year": _principal_of_year(season),
        "stat_leaders": stat_leaders,
        "team_of_season": team_of_season,
        "all_rookie": [_winner_entry(p, p.get("team_id"), season) for p in rookie_sorted[:5]],
        "standings_by_class": standings_by_class,
    }
    season["year_end_report"] = report
    try:
        from news import append_news

        doy = next((a for a in awards if a["key"] == "doy"), None)
        if doy:
            append_news(season, "year_end", mvp=doy["winner"]["name"], team=doy["winner"]["team_name"])
    except ImportError:
        pass
    return report


def get_year_end_report(season, lookup=None):
    report = season.get("year_end_report")
    if report:
        return report
    if season.get("phase") not in {"complete", "draft", "offseason"}:
        return None
    return build_year_end_report(season, lookup)
