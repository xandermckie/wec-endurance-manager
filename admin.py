"""Localhost-only admin panel for custom drivers and season editing."""

import os
import random

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from attributes import (
    ATTRIBUTE_KEYS,
    MAX_ATTR,
    MIN_ATTR,
    POTENTIAL_MAX,
    POTENTIAL_MIN,
    VALID_GRADES,
    _assign_peak_attributes,
    ensure_grade,
    generate_rookie_profile,
    init_rookie_career_profile,
    refresh_player_from_attributes,
)
from contracts import (
    MIN_SALARY_M,
    apply_roster_salary_multiplier,
    assign_player_contract,
    clear_team_salary_cap,
    ensure_contract_fields,
    get_salary_cap,
    refresh_all_team_finances,
    set_team_salary_cap,
    team_finances,
)
from game import get_game, load_session_season, save_session_season
from names import ensure_unique_name
from ratings import compute_intrinsic_overall
from roster import (
    assign_player_to_team,
    free_agent_players,
    reconcile_team_roster,
    release_player,
    reserve_players,
    roster_size,
)
from season import allocate_player_id, league_lookup, refresh_all_roster_stats, roster_players, team_name

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

LOCAL_HOSTS = {"127.0.0.1", "::1"}

AGE_MIN = 16
AGE_MAX = 60
OVERALL_MIN = 25
OVERALL_MAX = 99


def admin_enabled():
    return os.getenv("ADMIN_ENABLED", "").lower() in {"1", "true", "yes"}


def _admin_allowed():
    if not admin_enabled():
        return False
    if request.remote_addr not in LOCAL_HOSTS:
        return False
    token = os.getenv("ADMIN_TOKEN", "")
    if token and request.args.get("token") != token and request.form.get("token") != token:
        if request.cookies.get("admin_token") != token:
            return False
    return True


@admin_bp.before_request
def guard_admin():
    if not _admin_allowed():
        abort(404)


def _season_or_redirect():
    season_id, season_data = load_session_season()
    if season_data is None:
        return None, None, None, redirect(url_for("season_hub"))
    lookup = league_lookup(season_data)
    return season_id, season_data, lookup, None


def _existing_names(season_data, exclude_player_id=None):
    names = set()
    for key, other in season_data.get("players", {}).items():
        if exclude_player_id is not None and int(other.get("id", key)) == int(exclude_player_id):
            continue
        if other.get("name"):
            names.add(other["name"])
    return names


def _parse_float(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_int(raw, default=None):
    if raw is None:
        return default
    text = str(raw).strip()
    if text == "":
        return default
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _validate_player_form(form, *, is_create=False, existing_player=None, valid_team_ids=None):
    errors = []
    parsed = {}

    age_raw = form.get("age", "").strip()
    if is_create or age_raw:
        age = _parse_int(age_raw, default=20 if is_create else None)
        if age is None:
            errors.append("Age must be a whole number.")
        elif not AGE_MIN <= age <= AGE_MAX:
            errors.append(f"Age must be between {AGE_MIN} and {AGE_MAX}.")
        else:
            parsed["age"] = age

    if is_create:
        overall = _parse_int(form.get("overall", "60").strip())
        if overall is None:
            errors.append("Overall must be a whole number.")
        elif not OVERALL_MIN <= overall <= OVERALL_MAX:
            errors.append(f"Overall must be between {OVERALL_MIN} and {OVERALL_MAX}.")
        else:
            parsed["overall"] = overall

    potential_raw = form.get("potential", "").strip()
    if potential_raw:
        potential = _parse_int(potential_raw)
        if potential is None or not POTENTIAL_MIN <= potential <= POTENTIAL_MAX:
            errors.append(f"Potential must be between {POTENTIAL_MIN} and {POTENTIAL_MAX}.")
        else:
            parsed["potential"] = potential

    for field in ("peak_age", "retirement_age"):
        raw = form.get(field, "").strip()
        if raw:
            value = _parse_int(raw)
            if value is None:
                errors.append(f"{field.replace('_', ' ').title()} must be a whole number.")
            else:
                parsed[field] = value

    grade_raw = form.get("grade", "").strip()
    if grade_raw:
        if grade_raw not in VALID_GRADES:
            errors.append("Grade must be Platinum, Gold, Silver or Bronze.")
        else:
            parsed["grade"] = grade_raw

    salary_raw = form.get("salary", "").strip()
    if salary_raw:
        salary_val = _parse_float(salary_raw)
        if salary_val is None or salary_val < MIN_SALARY_M:
            errors.append(f"Salary must be at least €{MIN_SALARY_M}M.")
        else:
            parsed["salary"] = round(salary_val, 1)

    contract_years_raw = form.get("contract_years", "").strip()
    if contract_years_raw:
        contract_years = _parse_int(contract_years_raw)
        if contract_years is None or not 0 <= contract_years <= 5:
            errors.append("Contract years must be between 0 and 5.")
        else:
            parsed["contract_years"] = contract_years

    parsed["attributes"] = {}
    for key in ATTRIBUTE_KEYS:
        raw = form.get(f"attr_{key}", "").strip()
        if raw:
            attr_val = _parse_int(raw)
            if attr_val is None:
                errors.append(f"{key.replace('_', ' ').title()} must be a whole number.")
            else:
                parsed["attributes"][key] = max(MIN_ATTR, min(MAX_ATTR, attr_val))

    if is_create:
        parsed["destination"] = form.get("destination", "draft")
        team_id_raw = form.get("team_id", "").strip()
        if parsed["destination"] == "team":
            team_id = _parse_int(team_id_raw)
            if team_id is None or (valid_team_ids is not None and team_id not in valid_team_ids):
                errors.append("Select a valid team when assigning to a squad.")
            else:
                parsed["team_id"] = team_id
    elif valid_team_ids is not None:
        team_id_raw = form.get("team_id", "").strip()
        if team_id_raw == "":
            parsed["team_id"] = None
        else:
            team_id = _parse_int(team_id_raw)
            if team_id is None or team_id not in valid_team_ids:
                errors.append("Select a valid team or Free Agent.")
            else:
                parsed["team_id"] = team_id

    parsed["name"] = form.get("name", "").strip() or "Custom Driver"
    return errors, parsed


@admin_bp.route("/")
def admin_index():
    game = get_game()
    season_id, season_data = load_session_season()
    return render_template("admin/index.html", page_title="Admin", game=game,
                           season=season_data, season_id=season_id)


@admin_bp.route("/drivers")
def admin_players():
    season_id, season_data, lookup, redirect_response = _season_or_redirect()
    if redirect_response is not None:
        return redirect_response
    query = request.args.get("q", "").strip().lower()
    players = list(season_data.get("players", {}).values())
    if query:
        players = [p for p in players if query in (p.get("name") or "").lower()]
    players.sort(key=lambda p: p.get("overall") or 0, reverse=True)
    return render_template("admin/players.html", page_title="Admin Drivers",
                           season=season_data, players=players[:100], query=query)


def _admin_teams(season_data):
    teams = [
        {"team_id": int(team_id), "team_name": record.get("team_name", team_id)}
        for team_id, record in season_data.get("standings", {}).items()
    ]
    teams.sort(key=lambda item: item["team_name"])
    return teams


@admin_bp.route("/drivers/<int:player_id>/edit", methods=["GET", "POST"])
def admin_edit_player(player_id):
    season_id, season_data, lookup, redirect_response = _season_or_redirect()
    if redirect_response is not None:
        return redirect_response
    player = lookup.get(player_id)
    if not player:
        flash("Driver not found.", "error")
        return redirect(url_for("admin.admin_players"))

    teams = _admin_teams(season_data)
    valid_team_ids = {t["team_id"] for t in teams}

    if request.method == "POST":
        errors, parsed = _validate_player_form(request.form, is_create=False,
                                               existing_player=player, valid_team_ids=valid_team_ids)
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin/edit_player.html",
                                   page_title=f"Edit {player.get('name', player_id)}", player=player,
                                   teams=teams, attribute_keys=ATTRIBUTE_KEYS, grades=VALID_GRADES,
                                   form_data=request.form)

        player["name"] = ensure_unique_name(parsed["name"], _existing_names(season_data, exclude_player_id=player_id))
        if "age" in parsed:
            player["age"] = parsed["age"]
        if "grade" in parsed:
            player["grade"] = parsed["grade"]
            player["grades"] = [parsed["grade"]]
            ensure_grade(player)
        if "potential" in parsed:
            player["potential"] = parsed["potential"]
            player.pop("peak_attributes", None)
            _assign_peak_attributes(player, random.Random())
        if "peak_age" in parsed:
            player["peak_age"] = parsed["peak_age"]
        if "retirement_age" in parsed:
            player["retirement_age"] = parsed["retirement_age"]

        base = player.setdefault("base_attributes", player.get("attributes", {}))
        for key, value in parsed.get("attributes", {}).items():
            base[key] = value
        refresh_player_from_attributes(player)
        player["overall"] = compute_intrinsic_overall(player)

        if "salary" in parsed:
            player["salary"] = parsed["salary"]
            player["previous_salary"] = parsed["salary"]
        if "contract_years" in parsed:
            player["contract_years"] = parsed["contract_years"]

        if "team_id" in parsed:
            current_team = _parse_int(player.get("team_id"))
            new_team = parsed["team_id"]
            if current_team != new_team:
                ok, team_message = assign_player_to_team(season_data, player_id, new_team, force=True)
                flash(team_message, "success" if ok else "error")

        if player.get("team_id"):
            refresh_all_roster_stats(season_data, lookup)
        refresh_all_team_finances(season_data, lookup)
        save_session_season(season_id, season_data)
        flash(f"Updated {player['name']}.")
        return redirect(url_for("admin.admin_edit_player", player_id=player_id))

    return render_template("admin/edit_player.html",
                           page_title=f"Edit {player.get('name', player_id)}", player=player,
                           teams=teams, attribute_keys=ATTRIBUTE_KEYS, grades=VALID_GRADES)


@admin_bp.route("/drivers/create", methods=["GET", "POST"])
def admin_create_player():
    season_id, season_data, lookup, redirect_response = _season_or_redirect()
    if redirect_response is not None:
        return redirect_response

    teams = _admin_teams(season_data)

    if request.method == "POST":
        valid_team_ids = {t["team_id"] for t in teams}
        errors, parsed = _validate_player_form(request.form, is_create=True, valid_team_ids=valid_team_ids)
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("admin/create_player.html", page_title="Create Driver",
                                   teams=teams, attribute_keys=ATTRIBUTE_KEYS, grades=VALID_GRADES,
                                   form_data=request.form)

        name = ensure_unique_name(parsed["name"], _existing_names(season_data))
        overall = parsed["overall"]
        destination = parsed.get("destination", "draft")

        profile = generate_rookie_profile(overall)
        player_id = allocate_player_id(season_data)
        player = {
            "id": player_id, "name": name, "team_id": None, "team": None, "overall": overall,
            "scout_grade": overall, "age": parsed["age"], "gp": 0, "is_rookie": True,
            "grade": parsed.get("grade", profile["grade"]),
            "grades": [parsed.get("grade", profile["grade"])], "stats_source": "generated",
        }
        for key, value in parsed.get("attributes", {}).items():
            profile["attributes"][key] = value
        init_rookie_career_profile(player, profile["attributes"], scout_grade=overall)

        if "potential" in parsed:
            player["potential"] = parsed["potential"]
            player.pop("peak_attributes", None)
            _assign_peak_attributes(player, random.Random())
        for field in ("peak_age", "retirement_age"):
            if field in parsed:
                player[field] = parsed[field]

        refresh_player_from_attributes(player)
        player["overall"] = compute_intrinsic_overall(player)
        season_data["players"][str(player_id)] = player

        if destination == "team" and "team_id" in parsed:
            team_id = parsed["team_id"]
            player["team_id"] = team_id
            player["team"] = team_name(season_data, team_id)
            player["class"] = season_data.get("team_class", {}).get(str(team_id))
            roster = season_data["rosters"].setdefault(str(team_id), [])
            if player_id not in roster:
                roster.append(player_id)
            assign_player_contract(player)
            refresh_all_roster_stats(season_data, lookup)
            flash(f"Added {name} to {player['team']}.")
        else:
            state = season_data.get("draft_state")
            if state:
                state.setdefault("prospect_pool", []).append(player)
                flash(f"Added {name} to the young-driver pool.")
            else:
                flash(f"Created {name} as a free agent.")

        refresh_all_team_finances(season_data, lookup)
        save_session_season(season_id, season_data)
        return redirect(url_for("admin.admin_players"))

    return render_template("admin/create_player.html", page_title="Create Driver",
                           teams=teams, attribute_keys=ATTRIBUTE_KEYS, grades=VALID_GRADES)


@admin_bp.route("/teams")
def admin_teams():
    season_id, season_data, lookup, redirect_response = _season_or_redirect()
    if redirect_response is not None:
        return redirect_response
    teams = []
    game = get_game()
    user_team_id = int(game["team_id"]) if game and game.get("team_id") else None
    for t in _admin_teams(season_data):
        tid = t["team_id"]
        record = season_data.get("standings", {}).get(str(tid), {})
        cap_override = (season_data.get("salary_cap_overrides") or {}).get(str(tid))
        teams.append({
            **t,
            "roster_size": roster_size(season_data, tid),
            "record": f"{record.get('points', 0)} pts",
            "is_user_team": user_team_id == tid,
            "salary_cap": get_salary_cap(season_data, tid),
            "cap_override": cap_override,
        })
    return render_template("admin/teams.html", page_title="Admin Teams", season=season_data, teams=teams)


@admin_bp.route("/teams/<int:team_id>", methods=["GET", "POST"])
def admin_team_roster(team_id):
    season_id, season_data, lookup, redirect_response = _season_or_redirect()
    if redirect_response is not None:
        return redirect_response
    teams = _admin_teams(season_data)
    valid_team_ids = {t["team_id"] for t in teams}
    if team_id not in valid_team_ids:
        flash("Team not found.", "error")
        return redirect(url_for("admin.admin_teams"))

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "release":
            player_id = _parse_int(request.form.get("player_id"))
            if player_id:
                ok, message = release_player(season_data, team_id, player_id, force=True)
                flash(message, "success" if ok else "error")
        elif action == "add_fa":
            player_id = _parse_int(request.form.get("player_id"))
            if player_id:
                ok, message = assign_player_to_team(season_data, player_id, team_id, force=True)
                flash(message, "success" if ok else "error")
        elif action == "set_cap":
            cap_val = _parse_float(request.form.get("salary_cap", "").strip())
            if cap_val is None:
                flash("Budget must be a number.", "error")
            else:
                try:
                    set_team_salary_cap(season_data, team_id, cap_val)
                    flash(f"Budget set to €{cap_val:.1f}M for {team_name(season_data, team_id)}.")
                except ValueError as exc:
                    flash(str(exc), "error")
        elif action == "reset_cap":
            clear_team_salary_cap(season_data, team_id)
            flash(f"Budget reset to default (€{get_salary_cap(season_data)}M).")
        elif action == "discount_salaries":
            pct_val = _parse_float(request.form.get("salary_pct", "").strip())
            if pct_val is None or not 5 <= pct_val <= 100:
                flash("Salary percentage must be between 5 and 100.", "error")
            else:
                updated = apply_roster_salary_multiplier(season_data, team_id, pct_val / 100.0, lookup)
                flash(f"Scaled {updated} driver salaries to {pct_val:.0f}% of previous pay.")
        reconcile_team_roster(season_data, team_id)
        ensure_contract_fields(season_data)
        refresh_all_roster_stats(season_data, lookup)
        refresh_all_team_finances(season_data, lookup)
        save_session_season(season_id, season_data)
        return redirect(url_for("admin.admin_team_roster", team_id=team_id))

    ensure_contract_fields(season_data)
    roster = roster_players(season_data, team_id, lookup)
    roster.sort(key=lambda p: p.get("overall") or 0, reverse=True)
    reserve_roster = sorted(reserve_players(season_data, team_id, lookup),
                            key=lambda p: p.get("overall") or 0, reverse=True)
    free_agents = sorted(free_agent_players(season_data, lookup),
                         key=lambda p: p.get("overall") or 0, reverse=True)[:50]
    record = season_data.get("standings", {}).get(str(team_id), {})
    game = get_game()
    finances = team_finances(season_data, team_id, lookup)
    is_user_team = game and int(game.get("team_id") or -1) == team_id

    return render_template("admin/team_roster.html",
                           page_title=f"Squad — {team_name(season_data, team_id)}",
                           season=season_data, team_id=team_id,
                           team_name=team_name(season_data, team_id), roster=roster,
                           reserve_roster=reserve_roster, free_agents=free_agents,
                           record=f"{record.get('points', 0)} pts", roster_size=len(roster),
                           finances=finances, is_user_team=is_user_team,
                           league_cap=get_salary_cap(season_data))
