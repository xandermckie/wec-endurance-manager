"""Budget cap, driver contracts, and driver-market offer evaluation (all figures in €M)."""

import random

from season import league_lookup, roster_players, standings_table, team_class, team_name

BUDGET_CAP_M = 40.0
MIN_SALARY_M = 0.3
OVER_BUDGET_LINE_M = 48.0
RESERVE_CAP_HIT_PCT = 0.5
MIN_TEAM_SALARY_PCT = 0.60
MAX_FA_YEARS = 3
MAX_ROOKIE_YEARS = 3
MAX_PLAYER_PCT = 0.45
TRADE_SALARY_TOLERANCE_M = 4.0

ROOKIE_SALARY_BY_ROUND = {1: 1.2, 2: 0.5}
CONTRACT_WARNING_YEARS = 1
TEAM_BUDGET_MIN_M = 10.0
TEAM_BUDGET_MAX_M = 150.0

CHAMPIONSHIP_BONUS_BY_OVR = (
    (90, 0.6),
    (85, 0.45),
    (78, 0.30),
    (70, 0.20),
    (0, 0.10),
)


def _round_salary(value):
    return round(max(MIN_SALARY_M, value), 1)


def _parse_contract_terms(salary, years):
    """Return (salary, years, error_message). error_message is None on success."""
    try:
        return _round_salary(float(salary)), int(years), None
    except (TypeError, ValueError):
        return None, None, "Invalid salary or contract length."


def market_salary(player):
    """Fair annual salary (€M) from OVR and age."""
    overall = player.get("overall") or 50
    age = player.get("age") or 30
    base = 0.3 + (overall / 100) ** 1.9 * 14
    if age <= 22:
        base *= 0.80
    elif age <= 27:
        base *= 0.95
    elif age <= 35:
        base *= 1.05
    elif age >= 42:
        base *= 0.80
    max_single = BUDGET_CAP_M * MAX_PLAYER_PCT
    return _round_salary(min(base, max_single))


def max_player_salary(overall):
    if overall >= 88:
        pct = MAX_PLAYER_PCT
    elif overall >= 78:
        pct = 0.32
    elif overall >= 68:
        pct = 0.24
    else:
        pct = 0.16
    return _round_salary(BUDGET_CAP_M * pct)


def min_acceptable_salary(player):
    ask = player.get("asking_salary") or market_salary(player)
    prev = player.get("previous_salary") or 0
    floor = max(MIN_SALARY_M, ask * 0.80, prev * 0.85 if prev else 0)
    overall = player.get("overall") or 50
    if overall < 62:
        floor = max(MIN_SALARY_M, floor * 0.85)
    return _round_salary(floor)


def compute_asking_salary(player):
    market = market_salary(player)
    overall = player.get("overall") or 50
    prev = player.get("previous_salary") or market
    ask = max(market, prev * 1.05)
    if overall >= 85:
        ask = max(ask, market * 1.10)
    elif overall >= 75:
        ask = max(ask, market * 1.05)
    return _round_salary(ask)


def roll_initial_contract_years(player, rng=None):
    rng = rng or random.Random()
    overall = player.get("overall") or 50
    age = player.get("age") or 30
    if overall >= 88:
        choices, weights = [2, 3], [1, 3]
    elif overall >= 78:
        choices, weights = [1, 2, 3], [1, 3, 3]
    else:
        choices, weights = [1, 2, 3], [2, 4, 2]
    if age <= 24:
        weights = [w + (1 if y >= 2 else 0) for w, y in zip(weights, choices)]
    elif age >= 42:
        weights = [w + (1 if y <= 1 else 0) for w, y in zip(weights, choices)]
    return int(rng.choices(choices, weights=weights, k=1)[0])


def championship_bonus_amount(player):
    overall = player.get("overall") or 50
    for threshold, amount in CHAMPIONSHIP_BONUS_BY_OVR:
        if overall >= threshold:
            return amount
    return 0.1


def assign_player_contract(player, years=None, salary=None):
    if salary is None:
        salary = market_salary(player)
    if years is None:
        years = random.randint(1, 3)
    player["salary"] = _round_salary(salary)
    player["contract_years"] = int(years)
    player.setdefault("previous_salary", player["salary"])
    player.setdefault("previous_team_id", player.get("team_id"))


def assign_rookie_contract(player, draft_round=1):
    salary = ROOKIE_SALARY_BY_ROUND.get(draft_round, MIN_SALARY_M)
    player["salary"] = _round_salary(salary)
    player["contract_years"] = MAX_ROOKIE_YEARS
    player["previous_salary"] = player["salary"]
    player["previous_team_id"] = player.get("team_id")


def get_salary_cap(season, team_id=None):
    overrides = season.get("salary_cap_overrides") or {}
    if team_id is not None:
        override = overrides.get(str(team_id))
        if override is not None:
            return float(override)
    return float(season.get("budget_cap_m") or BUDGET_CAP_M)


def set_team_salary_cap(season, team_id, cap_m):
    cap_m = round(float(cap_m), 1)
    if not TEAM_BUDGET_MIN_M <= cap_m <= TEAM_BUDGET_MAX_M:
        raise ValueError(f"Budget must be between €{TEAM_BUDGET_MIN_M}M and €{TEAM_BUDGET_MAX_M}M.")
    season.setdefault("salary_cap_overrides", {})[str(team_id)] = cap_m
    return cap_m


def clear_team_salary_cap(season, team_id):
    overrides = season.get("salary_cap_overrides") or {}
    overrides.pop(str(team_id), None)
    if overrides:
        season["salary_cap_overrides"] = overrides
    else:
        season.pop("salary_cap_overrides", None)


def apply_roster_salary_multiplier(season, team_id, multiplier, lookup=None):
    lookup = lookup or league_lookup(season)
    multiplier = max(0.05, min(1.0, float(multiplier)))
    updated = 0
    players = list(roster_players(season, team_id, lookup))
    try:
        from roster import reserve_players

        players.extend(reserve_players(season, team_id, lookup))
    except ImportError:
        pass
    seen_ids = set()
    for player in players:
        player_id = player.get("id")
        if player_id in seen_ids:
            continue
        seen_ids.add(player_id)
        if player.get("salary") is None:
            continue
        player["salary"] = _round_salary(float(player["salary"]) * multiplier)
        player["previous_salary"] = player["salary"]
        updated += 1
    return updated


def team_payroll(season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    total = 0.0
    for player in roster_players(season, team_id, lookup):
        total += float(player.get("salary") or 0)
    try:
        from roster import reserve_players

        for player in reserve_players(season, team_id, lookup):
            total += float(player.get("salary") or 0) * RESERVE_CAP_HIT_PCT
    except ImportError:
        pass
    return round(total, 1)


def team_finances(season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    payroll = team_payroll(season, team_id, lookup)
    salary_cap = get_salary_cap(season, team_id)
    bonus_paid = float(
        season.get("team_finances", {}).get(str(team_id), {}).get("bonus_paid") or 0
    )
    cap_space = round(salary_cap - payroll, 1)
    min_floor = round(salary_cap * MIN_TEAM_SALARY_PCT, 1)
    return {
        "payroll": payroll,
        "cap_space": cap_space,
        "salary_cap": salary_cap,
        "league_salary_cap": BUDGET_CAP_M,
        "cap_override": (season.get("salary_cap_overrides") or {}).get(str(team_id)),
        "luxury_tax_line": OVER_BUDGET_LINE_M,
        "min_team_salary": min_floor,
        "below_min_warning": payroll < min_floor,
        "bonus_paid": round(bonus_paid, 1),
    }


def refresh_all_team_finances(season, lookup=None):
    lookup = lookup or league_lookup(season)
    finances = season.setdefault("team_finances", {})
    for team_id_str in season.get("rosters", {}).keys():
        finances[team_id_str] = team_finances(season, int(team_id_str), lookup)
    return finances


def ensure_contract_fields(season, rng=None):
    rng = rng or random.Random()
    lookup = league_lookup(season)
    for player in season.get("players", {}).values():
        needs_contract = (
            player.get("salary") is None
            or player.get("contract_years") is None
            or int(player.get("contract_years") or 0) <= 0
        )
        if player.get("team_id") and needs_contract:
            years = roll_initial_contract_years(player, rng)
            assign_player_contract(player, years=years)
        if not player.get("team_id") and player.get("asking_salary") is None:
            player["asking_salary"] = compute_asking_salary(player)
    _normalize_team_payrolls(season, lookup)
    refresh_all_team_finances(season, lookup)
    season.setdefault("news_feed", [])
    season.setdefault("pending_fa_offers", {})
    return season


def _normalize_team_payrolls(season, lookup):
    for team_id_str in season.get("rosters", {}):
        team_id = int(team_id_str)
        salary_cap = get_salary_cap(season, team_id)
        roster = roster_players(season, team_id, lookup)
        payroll = sum(float(p.get("salary") or 0) for p in roster)
        if payroll <= salary_cap or payroll <= 0:
            continue
        scale = (salary_cap * 0.92) / payroll
        for player in roster:
            player["salary"] = _round_salary(float(player.get("salary") or 0) * scale)


def assign_initial_contracts(season, rng=None):
    rng = rng or random.Random()
    lookup = league_lookup(season)
    for team_id_str in season.get("rosters", {}):
        roster_ids = list(season["rosters"][team_id_str])
        for player_id in roster_ids:
            player = lookup.get(int(player_id))
            if not player:
                continue
            years = roll_initial_contract_years(player, rng)
            salary = market_salary(player)
            assign_player_contract(player, years=years, salary=salary)
    for player in season.get("players", {}).values():
        if not player.get("team_id"):
            player["asking_salary"] = compute_asking_salary(player)
    _normalize_team_payrolls(season, lookup)
    refresh_all_team_finances(season, lookup)


def compute_extension_ask(player):
    current = float(player.get("salary") or market_salary(player))
    market = market_salary(player)
    overall = player.get("overall") or 50
    base = max(current * 1.08, market)
    if overall >= 85:
        base = max(base, market * 1.12)
    elif overall >= 75:
        base = max(base, market * 1.06)
    return _round_salary(base)


def suggested_extension_offer(player, season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    ask = compute_extension_ask(player)
    current = float(player.get("salary") or 0)
    overall = player.get("overall") or 50
    finances = team_finances(season, team_id, lookup)
    max_sal = max_player_salary(overall)
    salary = _round_salary(min(max(ask, ask * 1.02), max_sal))
    delta = salary - current
    if delta > finances["cap_space"]:
        salary = _round_salary(current + max(0.0, finances["cap_space"]))
    if salary < ask:
        salary = min(_round_salary(ask), max_sal)
    years = 3 if overall >= 78 else 2
    return {"salary": salary, "years": years, "ask": ask}


def validate_extension_terms(player, salary, years, team_id, season, lookup=None):
    salary, years, err = _parse_contract_terms(salary, years)
    if err:
        return False, err
    lookup = lookup or league_lookup(season)
    finances = team_finances(season, team_id, lookup)
    overall = player.get("overall") or 50
    current = float(player.get("salary") or 0)

    if years < 1 or years > MAX_FA_YEARS:
        return False, f"Extensions must be 1–{MAX_FA_YEARS} years."
    if salary < MIN_SALARY_M:
        return False, f"Minimum salary is €{MIN_SALARY_M}M."
    delta = salary - current
    if delta > finances["cap_space"]:
        return False, f"Extension exceeds budget space (€{finances['cap_space']}M available)."
    max_sal = max_player_salary(overall)
    if salary > max_sal:
        return False, f"Maximum offer for this driver is €{max_sal}M/yr."
    ask = compute_extension_ask(player)
    if salary < ask * 0.95:
        return False, f"Offer too low — driver wants at least €{ask}M/yr."
    return True, None


def expiring_contract_report(season, user_team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    if not user_team_id:
        return []
    report = []
    for player in roster_players(season, int(user_team_id), lookup):
        years = int(player.get("contract_years") or 0)
        if years > CONTRACT_WARNING_YEARS:
            continue
        report.append(
            {
                "player_id": player["id"],
                "player_name": player.get("name", str(player["id"])),
                "salary": player.get("salary"),
                "contract_years": years,
                "extension_ask": compute_extension_ask(player),
            }
        )
    report.sort(key=lambda item: item["contract_years"])
    return report


def evaluate_extension(player, salary, years, season, team_id):
    salary, years, err = _parse_contract_terms(salary, years)
    if err:
        return False, err
    ask = compute_extension_ask(player)
    current = float(player.get("salary") or 0)
    win_pct = _team_win_pct(season, team_id)
    score = 15.0
    if salary >= ask:
        score += 40
    elif salary >= ask * 0.95:
        score += 25
    elif salary >= current * 1.05:
        score += 15
    else:
        score -= 20
    if years >= 3:
        score += 10
    elif years == 2:
        score += 5
    if win_pct >= 0.5:
        score += 8
    threshold = 45 if (player.get("overall") or 50) >= 78 else 35
    if score >= threshold:
        return True, (
            f"{player.get('name', 'Driver')} signed an extension: "
            f"€{salary}M/yr × {years} years."
        )
    return False, f"{player.get('name', 'Driver')} wants at least €{ask}M/yr to extend."


def propose_extension(season, team_id, player_id, salary, years):
    from roster import reconcile_team_roster
    from season import can_trade

    if not can_trade(season):
        return False, "Extensions are not available in this phase.", False

    lookup = league_lookup(season)
    player_id = int(player_id)
    player = lookup.get(player_id)
    if not player:
        return False, "Driver not found.", False
    roster_ids = season.get("rosters", {}).get(str(team_id), [])
    if player_id not in roster_ids:
        return False, "Driver is not in your squad.", False

    current_salary = float(player.get("salary") or 0)
    delta = _round_salary(float(salary)) - current_salary
    finances = team_finances(season, team_id, lookup)
    if delta > finances["cap_space"]:
        return False, f"Extension exceeds budget space (€{finances['cap_space']}M available).", False

    ok, message = validate_extension_terms(player, salary, years, team_id, season, lookup)
    if not ok:
        return False, message, False

    accepted, result_message = evaluate_extension(player, salary, years, season, team_id)
    if accepted:
        player["previous_salary"] = player.get("salary")
        player["salary"] = _round_salary(float(salary))
        player["contract_years"] = int(years)
        refresh_all_team_finances(season, lookup)
        reconcile_team_roster(season, team_id)
        return True, result_message, True
    return False, result_message, False


def apply_championship_bonuses(season, team_id, lookup=None):
    lookup = lookup or league_lookup(season)
    total = 0.0
    for player in roster_players(season, int(team_id), lookup):
        bonus = championship_bonus_amount(player)
        player["championship_bonus"] = bonus
        total += bonus
    finances = season.setdefault("team_finances", {}).setdefault(str(team_id), {})
    finances["bonus_paid"] = round(float(finances.get("bonus_paid") or 0) + total, 1)
    refresh_all_team_finances(season, lookup)
    try:
        from news import append_news

        append_news(season, "championship_bonus", team=team_name(season, team_id), total=round(total, 1))
    except ImportError:
        pass
    return round(total, 1)


def clear_championship_bonuses(season):
    for player in season.get("players", {}).values():
        player.pop("championship_bonus", None)
    for finances in season.get("team_finances", {}).values():
        if isinstance(finances, dict):
            finances.pop("bonus_paid", None)


def validate_offer_terms(player, salary, years, team_id, season, lookup=None):
    salary, years, err = _parse_contract_terms(salary, years)
    if err:
        return False, err
    lookup = lookup or league_lookup(season)
    finances = team_finances(season, team_id, lookup)
    overall = player.get("overall") or 50

    if years < 1 or years > MAX_FA_YEARS:
        return False, f"Offers must be 1–{MAX_FA_YEARS} years."
    if salary < MIN_SALARY_M:
        return False, f"Minimum salary is €{MIN_SALARY_M}M."
    if salary > finances["cap_space"]:
        return False, f"Offer exceeds budget space (€{finances['cap_space']}M available)."
    max_sal = max_player_salary(overall)
    if salary > max_sal:
        return False, f"Maximum offer for this driver is €{max_sal}M/yr."
    min_sal = min_acceptable_salary(player)
    if salary < min_sal:
        return False, f"Offer too low — driver wants at least €{min_sal}M/yr."
    return True, None


def _team_win_pct(season, team_id):
    """Form proxy from championship rank within the team's class (1.0 = leading)."""
    cls = team_class(season, team_id)
    rows = standings_table(season, class_name=cls)
    if not rows:
        return 0.5
    total_rounds = sum(r.get("rounds", 0) for r in rows)
    if total_rounds <= 0:
        return 0.5
    size = len(rows)
    for row in rows:
        if row["team_id"] == int(team_id):
            return max(0.0, 1.0 - (row["rank"] - 1) / max(size - 1, 1))
    return 0.5


def evaluate_offer(player, salary, years, season, team_id):
    salary, years, err = _parse_contract_terms(salary, years)
    if err:
        return False, err
    overall = player.get("overall") or 50
    ask = player.get("asking_salary") or compute_asking_salary(player)
    prev = player.get("previous_salary") or 0
    win_pct = _team_win_pct(season, team_id)

    score = 0.0
    if salary >= ask:
        score += 40
    elif salary >= ask * 0.95:
        score += 25
    elif salary >= ask * 0.90:
        score += 10
    else:
        score -= 20

    if prev and salary >= prev:
        score += 20
    elif prev and salary >= prev * 0.95:
        score += 10
    elif prev:
        score -= 15

    if years >= 3:
        score += 10
    elif years == 2:
        score += 5

    if win_pct >= 0.55:
        score += 10
    elif win_pct >= 0.45:
        score += 5
    elif win_pct < 0.35:
        score -= 10

    if overall >= 85:
        threshold = 55
    elif overall >= 75:
        threshold = 45
    else:
        threshold = 35

    if score >= threshold:
        team = team_name(season, team_id)
        return True, f"{player.get('name', 'Driver')} signs with {team} for €{salary}M/yr × {years} years."

    reasons = [
        f"{player.get('name', 'Driver')} wants at least €{ask}M/yr — your €{salary}M wasn't enough.",
        f"{player.get('name', 'Driver')} declined: 'my manager and I have standards.'",
        f"{player.get('name', 'Driver')} passed — reportedly holding out for a better seat.",
    ]
    if prev and salary < prev:
        reasons.append(
            f"{player.get('name', 'Driver')} won't take a pay cut from €{prev}M to €{salary}M."
        )
    return False, random.choice(reasons)


def _apply_signing(season, team_id, player, salary, years, lookup):
    player_id = player["id"]
    roster = season["rosters"].setdefault(str(team_id), [])
    if player_id not in roster:
        roster.append(player_id)
    player["previous_salary"] = player.get("salary") or salary
    player["previous_team_id"] = player.get("team_id")
    player["salary"] = _round_salary(salary)
    player["contract_years"] = int(years)
    player["team_id"] = team_id
    player["team"] = team_name(season, team_id)
    new_class = season.get("team_class", {}).get(str(team_id))
    if new_class:
        player["class"] = new_class
    player.pop("asking_salary", None)
    player.pop("unsigned_seasons", None)
    player.pop("reserve", None)
    from roster import _remove_from_reserve

    _remove_from_reserve(season, team_id, player_id)
    refresh_all_team_finances(season, lookup)
    try:
        from news import append_news

        append_news(season, "signing", player=player.get("name", player_id),
                    team=team_name(season, team_id), salary=salary)
    except ImportError:
        pass
    from roster import reconcile_team_roster

    reconcile_team_roster(season, team_id)


def propose_offer(season, team_id, player_id, salary, years):
    from roster import can_add_player, _sync_free_agents

    player_id = int(player_id)
    lookup = league_lookup(season)

    if not can_add_player(season, team_id):
        from roster import MAX_ROSTER

        return False, f"Squad is full ({MAX_ROSTER} drivers).", False

    player = lookup.get(player_id)
    if not player:
        return False, "Driver not found.", False
    if player.get("team_id"):
        return False, "Driver is already with a team.", False
    if player_id not in season.get("free_agents", []):
        return False, "Driver is not on the market.", False

    pending = season.setdefault("pending_fa_offers", {})
    if str(player_id) in pending:
        return False, "You already have a pending offer to this driver.", False

    ok, message = validate_offer_terms(player, salary, years, team_id, season, lookup)
    if not ok:
        return False, message, False

    accepted, result_message = evaluate_offer(player, salary, years, season, team_id)
    if accepted:
        _apply_signing(season, team_id, player, salary, years, lookup)
        _sync_free_agents(season)
        return True, result_message, True

    try:
        from news import append_news

        append_news(season, "rejection", player=player.get("name", player_id),
                    team=team_name(season, team_id), salary=salary)
    except ImportError:
        pass
    return False, result_message, False


def expire_contracts(season, lookup=None):
    from roster import _sync_free_agents

    lookup = lookup or league_lookup(season)
    expired = []
    for player in season.get("players", {}).values():
        if not player.get("team_id"):
            continue
        years = int(player.get("contract_years") or 0)
        if years <= 0:
            continue
        years -= 1
        player["contract_years"] = years
        if years <= 0:
            team_id = player.get("team_id")
            player_id = player["id"]
            roster = season.get("rosters", {}).get(str(team_id), [])
            if player_id in roster:
                roster.remove(player_id)
            player["previous_salary"] = player.get("salary")
            player["previous_team_id"] = team_id
            res_ids = season.setdefault("reserve_assignments", {}).get(str(team_id), [])
            if player_id in res_ids:
                res_ids.remove(player_id)
            player.pop("reserve", None)
            player["team_id"] = None
            player["team"] = "Free Agent"
            player["unsigned_seasons"] = 0
            player["asking_salary"] = compute_asking_salary(player)
            expired.append(player)

    _sync_free_agents(season)
    refresh_all_team_finances(season, lookup)
    return expired


def incoming_trade_salary_delta(season, user_team_id, outgoing_players, incoming_players, lookup=None):
    lookup = lookup or league_lookup(season)
    out_sal = sum(float(lookup[int(pid)].get("salary") or 0) for pid in outgoing_players if lookup.get(int(pid)))
    in_sal = sum(float(lookup[int(pid)].get("salary") or 0) for pid in incoming_players if lookup.get(int(pid)))
    return round(in_sal - out_sal, 1)


def validate_trade_cap(season, user_team_id, outgoing_players, incoming_players, lookup=None):
    lookup = lookup or league_lookup(season)
    delta = incoming_trade_salary_delta(season, user_team_id, outgoing_players, incoming_players, lookup)
    if delta <= 0:
        return True, None
    finances = team_finances(season, user_team_id, lookup)
    if delta <= finances["cap_space"] + TRADE_SALARY_TOLERANCE_M:
        return True, None
    needed = delta - finances["cap_space"]
    return False, f"Transfer would exceed budget by €{round(needed, 1)}M (max exception €{TRADE_SALARY_TOLERANCE_M}M)."


def sim_cpu_free_agency(season, rng=None, max_signings=None):
    from difficulty import get_difficulty_settings
    from gm_personalities import cpu_fa_offer_multiplier, cpu_fa_team_priority
    from roster import _sync_free_agents, can_add_player

    rng = rng or random.Random()
    lookup = league_lookup(season)
    settings = get_difficulty_settings(season)
    if max_signings is None:
        max_signings = settings["max_cpu_fa_signings"]

    signed = []
    signed_player_ids = set()
    team_ids = list(season.get("rosters", {}).keys())
    rng.shuffle(team_ids)

    def available_free_agents():
        return sorted(
            [
                lookup[pid]
                for pid in season.get("free_agents", [])
                if pid in lookup and not lookup[pid].get("team_id") and pid not in signed_player_ids
            ],
            key=lambda p: p.get("overall") or 0,
            reverse=True,
        )

    def try_sign(team_id, player):
        ask = player.get("asking_salary") or compute_asking_salary(player)
        finances = team_finances(season, team_id, lookup)
        if finances["cap_space"] < ask * 0.85:
            return False

        overall = player.get("overall") or 50
        multiplier = cpu_fa_offer_multiplier(season, team_id, player)
        if overall >= 80:
            multiplier = max(multiplier, settings["cpu_star_offer_floor"])

        offer = min(
            ask * rng.uniform(multiplier - 0.02, multiplier + 0.04),
            max_player_salary(overall),
            finances["cap_space"],
        )
        years = rng.randint(1, MAX_FA_YEARS)
        accepted, _ = evaluate_offer(player, offer, years, season, team_id)
        if not accepted and settings["cpu_fa_retry_stars"] and overall >= 75:
            retry_offer = min(
                ask * max(multiplier, settings["cpu_star_offer_floor"]),
                max_player_salary(overall),
                finances["cap_space"],
            )
            accepted, _ = evaluate_offer(player, retry_offer, years, season, team_id)
            if accepted:
                offer = retry_offer

        if not accepted:
            return False

        _apply_signing(season, team_id, player, offer, years, lookup)
        signed_player_ids.add(player["id"])
        signed.append((player, team_id))
        return True

    for team_id_str in team_ids:
        if len(signed) >= max_signings:
            break

        team_id = int(team_id_str)
        if not can_add_player(season, team_id):
            continue

        finances = team_finances(season, team_id, lookup)
        if finances["cap_space"] < 0.5:
            continue

        free_agents = available_free_agents()
        if not free_agents:
            break

        affordable = [
            p for p in free_agents[:40]
            if (p.get("asking_salary") or compute_asking_salary(p)) <= finances["cap_space"]
        ]
        candidates = affordable or free_agents[:40]
        player = max(
            candidates,
            key=lambda c: cpu_fa_team_priority(season, team_id, c) + (c.get("overall") or 0) * 0.5,
        )
        try_sign(team_id, player)

    _sync_free_agents(season)
    return signed
