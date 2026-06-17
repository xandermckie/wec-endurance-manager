"""Curated FIA WEC grid: teams (car entries), driver line-ups, and the race calendar.

This is the racing equivalent of the static team/player data the original game pulled from a
sports API. There is no free public WEC timing API, so the grid ships as a curated dataset and
the fetcher turns it into the cached, rated grid the game runs on.

Two classes act as the game's "conferences": Hypercar and LMGT3. Each team is a single car
entry with a three-driver crew. Driver grade (Platinum / Gold / Silver / Bronze) is the FIA
driver categorisation and acts as the game's "position".
"""

import random

from assets import logo_slug_from_car

CLASSES = ("Hypercar", "LMGT3")

DRIVER_GRADES = ("Platinum", "Gold", "Silver", "Bronze")

# ── Race calendar (2025 WEC, eight rounds) ──────────────────────────────────
CALENDAR = [
    {"round": 1, "name": "Qatar 1812 km", "circuit": "Lusail International Circuit",
     "country": "Qatar", "flag_code": "qa", "circuit_slug": "lusail",
     "format": "1812 km", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 2, "name": "6 Hours of Imola", "circuit": "Autodromo di Imola",
     "country": "Italy", "flag_code": "it", "circuit_slug": "imola",
     "format": "6 Hours", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 3, "name": "6 Hours of Spa-Francorchamps", "circuit": "Circuit de Spa-Francorchamps",
     "country": "Belgium", "flag_code": "be", "circuit_slug": "spa",
     "format": "6 Hours", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 4, "name": "24 Hours of Le Mans", "circuit": "Circuit de la Sarthe",
     "country": "France", "flag_code": "fr", "circuit_slug": "lemans",
     "format": "24 Hours", "marquee": True, "finale": False, "points_mult": 2.0},
    {"round": 5, "name": "6 Hours of São Paulo", "circuit": "Autódromo José Carlos Pace",
     "country": "Brazil", "flag_code": "br", "circuit_slug": "interlagos",
     "format": "6 Hours", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 6, "name": "Lone Star Le Mans", "circuit": "Circuit of the Americas",
     "country": "United States", "flag_code": "us", "circuit_slug": "cota",
     "format": "6 Hours", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 7, "name": "6 Hours of Fuji", "circuit": "Fuji Speedway",
     "country": "Japan", "flag_code": "jp", "circuit_slug": "fuji",
     "format": "6 Hours", "marquee": False, "finale": False, "points_mult": 1.0},
    {"round": 8, "name": "8 Hours of Bahrain", "circuit": "Bahrain International Circuit",
     "country": "Bahrain", "flag_code": "bh", "circuit_slug": "bahrain",
     "format": "8 Hours", "marquee": True, "finale": True, "points_mult": 1.5},
]

CURRENT_SEASON = 2025

# ── The grid ────────────────────────────────────────────────────────────────
# Each team: number, name (manufacturer/squad), car (model), class, strength (0-100 hidden base
# that seeds driver skill), and a crew of (name, grade, age) tuples.
HYPERCAR_TEAMS = [
    {"number": 7, "name": "Toyota Gazoo Racing", "car": "Toyota GR010 Hybrid", "strength": 91,
     "crew": [("Kamui Kobayashi", "Platinum", 38), ("Mike Conway", "Platinum", 41), ("Nyck de Vries", "Platinum", 30)]},
    {"number": 8, "name": "Toyota Gazoo Racing", "car": "Toyota GR010 Hybrid", "strength": 92,
     "crew": [("Sébastien Buemi", "Platinum", 36), ("Brendon Hartley", "Platinum", 35), ("Ryō Hirakawa", "Platinum", 31)]},
    {"number": 50, "name": "Ferrari AF Corse", "car": "Ferrari 499P", "strength": 93,
     "crew": [("Antonio Fuoco", "Platinum", 29), ("Miguel Molina", "Platinum", 35), ("Nicklas Nielsen", "Platinum", 28)]},
    {"number": 51, "name": "Ferrari AF Corse", "car": "Ferrari 499P", "strength": 92,
     "crew": [("Alessandro Pier Guidi", "Platinum", 41), ("James Calado", "Platinum", 35), ("Antonio Giovinazzi", "Platinum", 31)]},
    {"number": 83, "name": "AF Corse", "car": "Ferrari 499P", "strength": 88,
     "crew": [("Robert Kubica", "Platinum", 40), ("Yifei Ye", "Gold", 24), ("Phil Hanson", "Gold", 25)]},
    {"number": 6, "name": "Porsche Penske Motorsport", "car": "Porsche 963", "strength": 90,
     "crew": [("Kévin Estre", "Platinum", 36), ("André Lotterer", "Platinum", 43), ("Laurens Vanthoor", "Platinum", 33)]},
    {"number": 5, "name": "Porsche Penske Motorsport", "car": "Porsche 963", "strength": 89,
     "crew": [("Matt Campbell", "Platinum", 30), ("Michael Christensen", "Platinum", 35), ("Frédéric Makowiecki", "Platinum", 44)]},
    {"number": 12, "name": "Cadillac Hertz Team Jota", "car": "Cadillac V-Series.R", "strength": 88,
     "crew": [("Will Stevens", "Platinum", 33), ("Norman Nato", "Platinum", 32), ("Alex Lynn", "Platinum", 31)]},
    {"number": 38, "name": "Cadillac Hertz Team Jota", "car": "Cadillac V-Series.R", "strength": 87,
     "crew": [("Earl Bamber", "Platinum", 34), ("Jenson Button", "Platinum", 45), ("Sébastien Bourdais", "Platinum", 46)]},
    {"number": 15, "name": "BMW M Team WRT", "car": "BMW M Hybrid V8", "strength": 86,
     "crew": [("Dries Vanthoor", "Platinum", 27), ("Raffaele Marciello", "Platinum", 30), ("Marco Wittmann", "Platinum", 35)]},
    {"number": 20, "name": "BMW M Team WRT", "car": "BMW M Hybrid V8", "strength": 85,
     "crew": [("Sheldon van der Linde", "Platinum", 26), ("Robin Frijns", "Platinum", 33), ("René Rast", "Platinum", 38)]},
    {"number": 93, "name": "Peugeot TotalEnergies", "car": "Peugeot 9X8", "strength": 84,
     "crew": [("Mikkel Jensen", "Platinum", 30), ("Nico Müller", "Platinum", 33), ("Jean-Éric Vergne", "Platinum", 35)]},
    {"number": 94, "name": "Peugeot TotalEnergies", "car": "Peugeot 9X8", "strength": 83,
     "crew": [("Loïc Duval", "Platinum", 43), ("Gustavo Menezes", "Platinum", 30), ("Paul Di Resta", "Platinum", 39)]},
    {"number": 35, "name": "Alpine Endurance Team", "car": "Alpine A424", "strength": 84,
     "crew": [("Charles Milesi", "Platinum", 24), ("Frédéric Makowiecki", "Gold", 44), ("Jules Gounon", "Platinum", 30)]},
    {"number": 36, "name": "Alpine Endurance Team", "car": "Alpine A424", "strength": 83,
     "crew": [("Nicolas Lapierre", "Platinum", 41), ("Matthieu Vaxivière", "Platinum", 31), ("Mick Schumacher", "Platinum", 26)]},
    {"number": 63, "name": "Lamborghini Iron Lynx", "car": "Lamborghini SC63", "strength": 80,
     "crew": [("Mirko Bortolotti", "Platinum", 35), ("Edoardo Mortara", "Platinum", 38), ("Daniil Kvyat", "Platinum", 31)]},
]

LMGT3_TEAMS = [
    {"number": 27, "name": "Heart of Racing Team", "car": "Aston Martin Vantage", "strength": 84,
     "crew": [("Ian James", "Bronze", 47), ("Daniel Mancinelli", "Gold", 32), ("Alex Riberas", "Platinum", 31)]},
    {"number": 10, "name": "Racing Spirit of Léman", "car": "Aston Martin Vantage", "strength": 78,
     "crew": [("Tom Gamble", "Gold", 24), ("Charlie Eastwood", "Gold", 29), ("Gustav Birch", "Bronze", 33)]},
    {"number": 54, "name": "Vista AF Corse", "car": "Ferrari 296 GT3", "strength": 85,
     "crew": [("Thomas Flohr", "Bronze", 54), ("Francesco Castellacci", "Silver", 39), ("Davide Rigon", "Platinum", 38)]},
    {"number": 21, "name": "Vista AF Corse", "car": "Ferrari 296 GT3", "strength": 83,
     "crew": [("François Heriau", "Silver", 30), ("Simon Mann", "Bronze", 27), ("Alessio Rovera", "Platinum", 29)]},
    {"number": 92, "name": "Manthey PureRxcing", "car": "Porsche 911 GT3 R", "strength": 86,
     "crew": [("Aliaksandr Malykhin", "Bronze", 47), ("Joel Sturm", "Gold", 24), ("Klaus Bachler", "Platinum", 33)]},
    {"number": 91, "name": "Manthey EMA", "car": "Porsche 911 GT3 R", "strength": 82,
     "crew": [("Yasser Shahin", "Bronze", 39), ("Morris Schuring", "Silver", 20), ("Richard Lietz", "Platinum", 41)]},
    {"number": 59, "name": "United Autosports", "car": "McLaren 720S GT3 Evo", "strength": 83,
     "crew": [("Grégoire Saucy", "Gold", 24), ("Marino Sato", "Silver", 26), ("James Cottingham", "Bronze", 29)]},
    {"number": 95, "name": "United Autosports", "car": "McLaren 720S GT3 Evo", "strength": 80,
     "crew": [("Darren Leung", "Bronze", 32), ("Sébastien Baud", "Silver", 25), ("Nico Pino", "Silver", 22)]},
    {"number": 87, "name": "Akkodis ASP Team", "car": "Lexus RC F GT3", "strength": 84,
     "crew": [("Takeshi Kimura", "Bronze", 57), ("Esteban Masson", "Gold", 22), ("José María López", "Platinum", 42)]},
    {"number": 78, "name": "Akkodis ASP Team", "car": "Lexus RC F GT3", "strength": 81,
     "crew": [("Arnold Robin", "Silver", 28), ("Marco Sørensen", "Platinum", 35), ("Petru Umbrarescu", "Bronze", 25)]},
    {"number": 88, "name": "Proton Competition", "car": "Ford Mustang GT3", "strength": 79,
     "crew": [("Giammarco Levorato", "Silver", 21), ("Stefano Gattuso", "Bronze", 35), ("Ben Tuck", "Gold", 30)]},
    {"number": 77, "name": "Proton Competition", "car": "Ford Mustang GT3", "strength": 78,
     "crew": [("Ryan Hardwick", "Bronze", 43), ("Zacharie Robichon", "Gold", 31), ("Ben Barker", "Gold", 38)]},
    {"number": 46, "name": "Team WRT", "car": "BMW M4 GT3 Evo", "strength": 85,
     "crew": [("Ahmad Al Harthy", "Bronze", 43), ("Valentino Rossi", "Gold", 46), ("Kelvin van der Linde", "Platinum", 29)]},
    {"number": 31, "name": "Team WRT", "car": "BMW M4 GT3 Evo", "strength": 82,
     "crew": [("Timur Boguslavskiy", "Gold", 27), ("Augusto Farfus", "Platinum", 41), ("Maxime Martin", "Platinum", 39)]},
    {"number": 33, "name": "TF Sport", "car": "Corvette Z06 GT3.R", "strength": 81,
     "crew": [("Ben Keating", "Bronze", 54), ("Daniel Juncadella", "Platinum", 34), ("Jonny Edgar", "Silver", 21)]},
    {"number": 81, "name": "TF Sport", "car": "Corvette Z06 GT3.R", "strength": 79,
     "crew": [("Tom van Rompuy", "Silver", 28), ("Rui Andrade", "Gold", 30), ("Charlie Eastwood", "Gold", 29)]},
    {"number": 85, "name": "Iron Dames", "car": "Lamborghini Huracán GT3", "strength": 80,
     "crew": [("Sarah Bovy", "Bronze", 38), ("Rahel Frey", "Silver", 39), ("Michelle Gatting", "Gold", 33)]},
    {"number": 60, "name": "Iron Lynx", "car": "Mercedes-AMG GT3", "strength": 79,
     "crew": [("Claudio Schiavoni", "Bronze", 50), ("Matteo Cressoni", "Silver", 41), ("Franck Perera", "Platinum", 40)]},
]


# Out-of-contract drivers available on the market at season start (name, grade, age, skill).
FREE_AGENT_POOL = [
    ("Brendon Leitch", "Gold", 30, 74),
    ("Will Burns", "Silver", 27, 66),
    ("Nico Varrone", "Silver", 24, 68),
    ("Ben Hanley", "Gold", 40, 75),
    ("Oliver Rasmussen", "Gold", 24, 76),
    ("Felipe Drugovich", "Platinum", 25, 82),
    ("Antonio Serravalle", "Silver", 25, 64),
    ("Lilou Wadoux", "Silver", 24, 67),
    ("Esteban Gutiérrez", "Gold", 34, 73),
    ("Théo Pourchaire", "Platinum", 22, 81),
    ("Pietro Fittipaldi", "Gold", 29, 75),
    ("Roberto Merhi", "Gold", 34, 72),
    ("Neel Jani", "Platinum", 41, 80),
    ("Tijmen van der Helm", "Silver", 22, 63),
    ("Reshad de Gerus", "Silver", 22, 65),
    ("Hamda Al Qubaisi", "Silver", 23, 62),
]

GRADE_SKILL_BONUS = {"Platinum": 9, "Gold": 1, "Silver": -7, "Bronze": -16}

# Stat ceilings (per 8-round season) used to turn hidden skill into season form.
_STAT_PROFILE = {
    "ppr": 24.0,   # points per round (primary)
    "pod": 7.0,    # podiums
    "ovt": 16.0,   # positions gained across the season
    "pol": 4.0,    # pole positions
    "fl": 5.0,     # fastest laps
}


def _driver_skill(team_strength, grade, rng):
    base = team_strength + GRADE_SKILL_BONUS.get(grade, 0)
    return max(28, min(99, base + rng.uniform(-4, 4)))


def _season_stats_from_skill(skill, rng):
    """Map a 0-100 skill onto a plausible season stat line."""
    norm = max(0.0, min(1.0, (skill - 30) / 69))
    stats = {}
    for stat, ceiling in _STAT_PROFILE.items():
        if stat == "ppr":
            value = (norm ** 1.25) * ceiling
        elif stat in ("pod", "pol", "fl"):
            value = (norm ** 1.7) * ceiling
        else:  # ovt — even midfielders make moves
            value = (norm ** 0.9) * ceiling
        value *= rng.uniform(0.85, 1.15)
        stats[stat] = round(max(0.0, value), 1)
    return stats


def _build_team(team, class_name, team_id, rng):
    record = {
        "id": team_id,
        "number": team["number"],
        "name": team["name"],
        "full_name": f"#{team['number']} {team['name']}",
        "car": team["car"],
        "class": class_name,
        "strength": team["strength"],
        "logo_slug": logo_slug_from_car(team["car"]),
    }
    return record


def build_grid(seed=CURRENT_SEASON):
    """Return (teams, drivers) with synthetic season stats seeded deterministically."""
    rng = random.Random(seed)
    teams = []
    drivers = []
    team_id = 1
    driver_id = 100

    for class_name, group in (("Hypercar", HYPERCAR_TEAMS), ("LMGT3", LMGT3_TEAMS)):
        for team in group:
            team_record = _build_team(team, class_name, team_id, rng)
            teams.append(team_record)
            for name, grade, age in team["crew"]:
                skill = _driver_skill(team["strength"], grade, rng)
                stats = _season_stats_from_skill(skill, rng)
                driver = {
                    "id": driver_id,
                    "name": name,
                    "team": team_record["full_name"],
                    "team_id": team_id,
                    "class": class_name,
                    "grade": grade,
                    "grades": [grade],
                    "age": age,
                    "gp": len(CALENDAR),
                    **stats,
                }
                drivers.append(driver)
                driver_id += 1
            team_id += 1

    # Out-of-contract drivers on the market (no team).
    for name, grade, age, skill in FREE_AGENT_POOL:
        skill = max(28, min(99, skill + rng.uniform(-3, 3)))
        stats = _season_stats_from_skill(skill, rng)
        drivers.append(
            {
                "id": driver_id,
                "name": name,
                "team": "Free Agent",
                "team_id": None,
                "class": None,
                "grade": grade,
                "grades": [grade],
                "age": age,
                "gp": len(CALENDAR),
                **stats,
            }
        )
        driver_id += 1

    return teams, drivers


def calendar():
    return [dict(round_info) for round_info in CALENDAR]


def teams():
    grid_teams, _ = build_grid()
    return grid_teams


def team_by_id(team_id):
    for team in teams():
        if team["id"] == int(team_id):
            return team
    return None
