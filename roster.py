"""Squad size limits, releases, reserve/development drivers, and driver-market signings."""

from season import can_trade, league_lookup, team_name

MAX_ROSTER = 6
MIN_ROSTER = 2
MAX_RESERVE = 2
MAX_RESERVE_AGE = 23


def _normalize_team_id(team_id):
    if team_id is None:
        return None
    return int(team_id)


def _player_team_id(player):
    raw = player.get("team_id")
    if raw is None:
        return None
    return int(raw)


def roster_size(season, team_id):
    return len(season.get("rosters", {}).get(str(team_id), []))


def effective_roster_size(season, team_id):
    return roster_size(season, team_id)


def reserve_count(season, team_id):
    return len(reserve_player_ids(season, team_id))


def reserve_player_ids(season, team_id):
    return [int(pid) for pid in season.get("reserve_assignments", {}).get(str(team_id), [])]


def reserve_players(season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    players = []
    for player_id in reserve_player_ids(season, team_id):
        player = lookup.get(player_id)
        if player:
            players.append(player)
    return players


def can_add_player(season, team_id):
    return effective_roster_size(season, team_id) < MAX_ROSTER


def can_assign_reserve(season, team_id):
    return reserve_count(season, team_id) < MAX_RESERVE


def can_remove_player(season, team_id):
    return roster_size(season, team_id) > MIN_ROSTER


def free_agent_ids(season):
    return list(season.get("free_agents", []))


def free_agent_players(season, lookup=None):
    lookup = lookup or league_lookup(season)
    players = []
    for player_id in free_agent_ids(season):
        player = lookup.get(int(player_id))
        if player and not player.get("team_id"):
            players.append(player)
    return players


def validate_roster_sizes_after_trade(
    season,
    user_team_id,
    partner_team_id,
    outgoing_players,
    incoming_players,
    check_partner_max=True,
    check_partner_min=True,
):
    user_size = roster_size(season, user_team_id)
    partner_size = roster_size(season, partner_team_id)
    user_after = user_size - len(outgoing_players) + len(incoming_players)
    partner_after = partner_size - len(incoming_players) + len(outgoing_players)

    if user_after > MAX_ROSTER:
        return False, f"Transfer would exceed squad limit ({MAX_ROSTER} drivers)."
    if check_partner_max and partner_after > MAX_ROSTER:
        return False, "Transfer would exceed partner squad limit."
    if user_after < MIN_ROSTER:
        return False, f"Transfer would drop below minimum squad ({MIN_ROSTER} drivers)."
    if check_partner_min and partner_after < MIN_ROSTER:
        return False, "Transfer would drop partner below minimum squad."
    return True, None


def repair_roster_sync(season, team_id=None):
    if team_id is not None:
        reconcile_team_roster(season, team_id)
        return
    reconcile_all_rosters(season)


def reconcile_team_roster(season, team_id):
    lookup = league_lookup(season)
    tid = _normalize_team_id(team_id)
    roster_key = str(tid)
    roster_ids = [int(pid) for pid in season.get("rosters", {}).get(roster_key, [])]
    label = team_name(season, tid)
    cleaned = []
    for player_id in roster_ids:
        player = lookup.get(player_id)
        if not player:
            continue
        player["team_id"] = tid
        player["team"] = label
        cleaned.append(player_id)
    for player in season.get("players", {}).values():
        if _player_team_id(player) == tid and player.get("id") not in cleaned:
            cleaned.append(int(player["id"]))
    season["rosters"][roster_key] = cleaned


def reconcile_all_rosters(season):
    for team_id_str in season.get("rosters", {}).keys():
        reconcile_team_roster(season, int(team_id_str))


def _sync_free_agents(season):
    pool = []
    for key, player in season.get("players", {}).items():
        if not player.get("team_id"):
            pool.append(player.get("id", int(key)))
    season["free_agents"] = sorted(set(pool))


def ensure_draft_roster_room(season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    while not can_add_player(season, team_id) and can_remove_player(season, team_id):
        roster_ids = season.get("rosters", {}).get(str(team_id), [])
        candidates = [lookup[pid] for pid in roster_ids if pid in lookup]
        if not candidates:
            break
        worst = min(candidates, key=lambda p: p.get("overall") or 0)
        release_player(season, team_id, worst["id"])


def release_worst_players(season, team_id, count, lookup=None):
    lookup = lookup or league_lookup(season)
    team_id = _normalize_team_id(team_id)
    count = max(0, int(count))
    released = []
    for _ in range(count):
        if not can_remove_player(season, team_id):
            break
        roster_ids = season.get("rosters", {}).get(str(team_id), [])
        candidates = [lookup[pid] for pid in roster_ids if pid in lookup]
        if not candidates:
            break
        worst = min(candidates, key=lambda p: p.get("overall") or 0)
        ok, _ = release_player(season, team_id, worst["id"], force=True)
        if ok:
            released.append(worst)
        else:
            break
    return released


def release_player(season, team_id, player_id, force=False):
    if not force and not can_trade(season):
        return False, "Squad moves are not available in this phase."

    team_id = _normalize_team_id(team_id)
    player_id = int(player_id)
    if not force and not can_remove_player(season, team_id):
        return False, f"Cannot drop below {MIN_ROSTER} drivers."

    lookup = league_lookup(season)
    player = lookup.get(player_id)
    roster_list = [int(x) for x in season.get("rosters", {}).get(str(team_id), [])]
    on_roster = player_id in roster_list
    player_team = _player_team_id(player) if player else None

    if not player or (not on_roster and player_team != team_id):
        return False, "Driver is not in your squad."

    roster_list = [int(x) for x in season["rosters"].setdefault(str(team_id), [])]
    if player_id in roster_list:
        roster_list.remove(player_id)
    season["rosters"][str(team_id)] = roster_list

    player["team_id"] = None
    player["team"] = "Free Agent"
    player["unsigned_seasons"] = 0
    player.pop("reserve", None)
    _remove_from_reserve(season, team_id, player_id)
    try:
        from contracts import compute_asking_salary, refresh_all_team_finances

        player["asking_salary"] = compute_asking_salary(player)
        refresh_all_team_finances(season)
    except ImportError:
        pass
    _sync_free_agents(season)
    reconcile_team_roster(season, team_id)
    return True, f"Released {player.get('name', player_id)} to the driver market."


def _remove_from_reserve(season, team_id, player_id):
    assignments = season.setdefault("reserve_assignments", {})
    roster_key = str(_normalize_team_id(team_id))
    ids = [int(pid) for pid in assignments.get(roster_key, [])]
    player_id = int(player_id)
    if player_id in ids:
        ids.remove(player_id)
    assignments[roster_key] = ids


def assign_to_reserve(season, team_id, player_id):
    if not can_trade(season):
        return False, "Squad moves are not available in this phase."

    team_id = _normalize_team_id(team_id)
    player_id = int(player_id)
    lookup = league_lookup(season)
    player = lookup.get(player_id)
    roster_list = [int(pid) for pid in season.get("rosters", {}).get(str(team_id), [])]

    if not player or player_id not in roster_list:
        return False, "Driver is not in your race squad."
    if int(player.get("age") or 99) > MAX_RESERVE_AGE:
        return False, f"Only drivers age {MAX_RESERVE_AGE} or younger can join the development pool."
    if not can_assign_reserve(season, team_id):
        return False, f"Reserve limit reached ({MAX_RESERVE} drivers)."

    roster_list.remove(player_id)
    season["rosters"][str(team_id)] = roster_list
    res_ids = season.setdefault("reserve_assignments", {}).setdefault(str(team_id), [])
    if player_id not in res_ids:
        res_ids.append(player_id)
    player["reserve"] = True
    try:
        from contracts import refresh_all_team_finances

        refresh_all_team_finances(season)
    except ImportError:
        pass
    return True, f"Moved {player.get('name', player_id)} to the development pool."


def recall_from_reserve(season, team_id, player_id):
    if not can_trade(season):
        return False, "Squad moves are not available in this phase."

    team_id = _normalize_team_id(team_id)
    player_id = int(player_id)
    lookup = league_lookup(season)
    player = lookup.get(player_id)
    res_ids = [int(pid) for pid in season.get("reserve_assignments", {}).get(str(team_id), [])]

    if not player or player_id not in res_ids:
        return False, "Driver is not in your development pool."
    if not can_add_player(season, team_id):
        return False, f"Race squad is full ({MAX_ROSTER} drivers). Move someone else first."

    res_ids.remove(player_id)
    season["reserve_assignments"][str(team_id)] = res_ids
    player.pop("reserve", None)
    roster = season["rosters"].setdefault(str(team_id), [])
    if player_id not in roster:
        roster.append(player_id)
    player["team_id"] = team_id
    player["team"] = team_name(season, team_id)
    reconcile_team_roster(season, team_id)
    try:
        from contracts import refresh_all_team_finances

        refresh_all_team_finances(season)
    except ImportError:
        pass
    return True, f"Promoted {player.get('name', player_id)} to the race squad."


def assign_player_to_team(season, player_id, new_team_id, *, force=False):
    """Move a driver to a team or the market. Admin uses force=True to bypass limits."""
    lookup = league_lookup(season)
    player_id = int(player_id)
    player = lookup.get(player_id)
    if not player:
        return False, "Driver not found."

    current_team_id = _player_team_id(player)
    new_team_id = _normalize_team_id(new_team_id)

    if current_team_id == new_team_id:
        return True, "No team change."

    if not force:
        if not can_trade(season):
            return False, "Squad moves are not available in this phase."
        if new_team_id is None and current_team_id is not None:
            if not can_remove_player(season, current_team_id):
                return False, f"Cannot drop below {MIN_ROSTER} drivers."
        if new_team_id is not None and not can_add_player(season, new_team_id):
            return False, f"Cannot exceed squad limit ({MAX_ROSTER} drivers)."

    if current_team_id is not None:
        old_roster = season["rosters"].setdefault(str(current_team_id), [])
        if player_id in old_roster:
            old_roster.remove(player_id)

    if new_team_id is None:
        player["team_id"] = None
        player["team"] = "Free Agent"
        player["unsigned_seasons"] = 0
        player.pop("reserve", None)
        if current_team_id is not None:
            _remove_from_reserve(season, current_team_id, player_id)
        try:
            from contracts import compute_asking_salary, refresh_all_team_finances

            player["asking_salary"] = compute_asking_salary(player)
            refresh_all_team_finances(season)
        except ImportError:
            pass
        _sync_free_agents(season)
        return True, f"Moved {player.get('name', player_id)} to the driver market."

    roster = season["rosters"].setdefault(str(new_team_id), [])
    if player_id not in roster:
        roster.append(player_id)
    player["team_id"] = new_team_id
    player["team"] = team_name(season, new_team_id)
    # Driver inherits the class of their new team.
    new_class = season.get("team_class", {}).get(str(new_team_id))
    if new_class:
        player["class"] = new_class
    try:
        from contracts import assign_player_contract, refresh_all_team_finances

        assign_player_contract(player)
        refresh_all_team_finances(season)
    except ImportError:
        pass
    _sync_free_agents(season)
    return True, f"Moved {player.get('name', player_id)} to {player['team']}."


def sign_free_agent(season, team_id, player_id, salary=None, years=2):
    from contracts import compute_asking_salary, propose_offer

    if not can_trade(season):
        return False, "Driver signings are not available in this phase."

    lookup = league_lookup(season)
    player = lookup.get(int(player_id))
    if not player:
        return False, "Driver not found."
    if salary is None:
        salary = player.get("asking_salary") or compute_asking_salary(player)
    ok, message, _accepted = propose_offer(season, team_id, player_id, salary, years)
    return ok, message
