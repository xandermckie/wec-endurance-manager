"""Difficulty presets for CPU behaviour, transfers, and race simulation."""

DIFFICULTY_LEVELS = ("easy", "normal", "hard", "legend")

DIFFICULTY_LABELS = {
    "easy": "Rookie",
    "normal": "Pro",
    "hard": "Works Driver",
    "legend": "Le Mans Legend",
}

DIFFICULTY_DESCRIPTIONS = {
    "easy": "Forgiving transfers and light CPU driver-market activity.",
    "normal": "Balanced challenge for most managers.",
    "hard": "Sharp rival principals and tougher transfer partners.",
    "legend": "Aggressive rivals, brutal transfers, minimal sim favours.",
}

PRESETS = {
    "easy": {
        "max_cpu_fa_signings": 6,
        "cpu_fa_retry_stars": False,
        "cpu_star_offer_floor": 0.94,
        "trade_tolerance": 18,
        "race_variance": 8.0,
        "base_dnf_chance": 0.025,
        "gm_personalities_from_start": False,
        "weak_team_fa_boost": 0,
    },
    "normal": {
        "max_cpu_fa_signings": 12,
        "cpu_fa_retry_stars": True,
        "cpu_star_offer_floor": 1.0,
        "trade_tolerance": 15,
        "race_variance": 7.0,
        "base_dnf_chance": 0.03,
        "gm_personalities_from_start": False,
        "weak_team_fa_boost": 4,
    },
    "hard": {
        "max_cpu_fa_signings": 22,
        "cpu_fa_retry_stars": True,
        "cpu_star_offer_floor": 1.05,
        "trade_tolerance": 11,
        "race_variance": 6.0,
        "base_dnf_chance": 0.035,
        "gm_personalities_from_start": True,
        "weak_team_fa_boost": 8,
    },
    "legend": {
        "max_cpu_fa_signings": 30,
        "cpu_fa_retry_stars": True,
        "cpu_star_offer_floor": 1.10,
        "trade_tolerance": 8,
        "race_variance": 5.0,
        "base_dnf_chance": 0.04,
        "gm_personalities_from_start": True,
        "weak_team_fa_boost": 12,
    },
}


def normalize_difficulty(value):
    if value in PRESETS:
        return value
    return "normal"


def difficulty_label(value):
    return DIFFICULTY_LABELS[normalize_difficulty(value)]


def get_difficulty_settings(season):
    slug = normalize_difficulty((season or {}).get("difficulty"))
    return dict(PRESETS[slug])
