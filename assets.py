"""Static image resolution for team logos, circuit thumbnails, and flags."""

import os

_STATIC_ROOT = os.path.join(os.path.dirname(__file__), "static", "img")

# Car model prefix → manufacturer logo slug.
_CAR_LOGO_SLUGS = (
    ("Mercedes-AMG", "mercedes"),
    ("Aston Martin", "aston-martin"),
    ("Corvette", "chevrolet"),
    ("Lamborghini", "lamborghini"),
    ("McLaren", "mclaren"),
    ("Porsche", "porsche"),
    ("Ferrari", "ferrari"),
    ("Cadillac", "cadillac"),
    ("Peugeot", "peugeot"),
    ("Alpine", "alpine"),
    ("Toyota", "toyota"),
    ("BMW", "bmw"),
    ("Lexus", "lexus"),
    ("Ford", "ford"),
)

_COUNTRY_FLAG_CODES = {
    "Qatar": "qa",
    "Italy": "it",
    "Belgium": "be",
    "France": "fr",
    "Brazil": "br",
    "United States": "us",
    "Japan": "jp",
    "Bahrain": "bh",
}

_BRAND_COLORS = {
    "toyota": "#EB0A1E",
    "ferrari": "#DC0000",
    "porsche": "#D5001C",
    "cadillac": "#0A2342",
    "bmw": "#0066B1",
    "peugeot": "#00A19C",
    "alpine": "#0090FF",
    "lamborghini": "#DDB321",
    "aston-martin": "#00665E",
    "mclaren": "#FF8000",
    "lexus": "#1A1A1A",
    "ford": "#003478",
    "chevrolet": "#F2BC18",
    "mercedes": "#00D2BE",
}

_ASSET_SUBDIRS = {
    "logo": "logos",
    "circuit": "circuits",
    "flag": "flags",
    "hero": "hero",
}

# Real manufacturer marks via Simple Icons CDN (https://simpleicons.org).
_SIMPLE_ICONS_CDN = "https://cdn.simpleicons.org"
_LOGO_SIMPLE_ICONS_SLUG = {
    "toyota": "toyota",
    "ferrari": "ferrari",
    "porsche": "porsche",
    "cadillac": "cadillac",
    "bmw": "bmw",
    "peugeot": "peugeot",
    "lamborghini": "lamborghini",
    "aston-martin": "astonmartin",
    "mclaren": "mclaren",
    "ford": "ford",
    "chevrolet": "chevrolet",
    "mercedes": "mercedes",
}

# Brands not in Simple Icons — other public logo CDNs.
_LOGO_EXTERNAL_URLS = {
    "alpine": "https://cdn.worldvectorlogo.com/logos/alpine-1.svg",
    "lexus": "https://cdn.worldvectorlogo.com/logos/lexus.svg",
}


def logo_slug_from_car(car: str) -> str:
    """Map a car model string to a manufacturer logo slug."""
    if not car:
        return "unknown"
    for prefix, slug in _CAR_LOGO_SLUGS:
        if car.startswith(prefix):
            return slug
    token = car.split()[0].lower() if car.split() else "unknown"
    return token.replace(" ", "-")


def brand_color(slug: str) -> str:
    """Accent color for a manufacturer slug (fallback monograms)."""
    return _BRAND_COLORS.get(slug or "", "#6ec1ff")


def brand_initial(slug: str) -> str:
    """Single-letter monogram for fallback badges."""
    if not slug or slug == "unknown":
        return "?"
    return slug[0].upper()


def flag_code_from_country(country: str) -> str:
    """ISO 3166-1 alpha-2 code for a calendar country name."""
    return _COUNTRY_FLAG_CODES.get(country or "", "")


def circuit_slug_from_round(round_info: dict) -> str:
    """Stable circuit image slug from a calendar round dict."""
    if round_info.get("circuit_slug"):
        return round_info["circuit_slug"]
    mapping = {
        1: "lusail",
        2: "imola",
        3: "spa",
        4: "lemans",
        5: "interlagos",
        6: "cota",
        7: "fuji",
        8: "bahrain",
    }
    return mapping.get(round_info.get("round"), "unknown")


def _asset_path(kind: str, slug: str, ext: str) -> str:
    subdir = _ASSET_SUBDIRS.get(kind, kind)
    return os.path.join(_STATIC_ROOT, subdir, f"{slug}.{ext}")


def asset_exists(kind: str, slug: str, ext: str = "svg") -> bool:
    if not slug:
        return False
    return os.path.isfile(_asset_path(kind, slug, ext))


def static_relpath(kind: str, slug: str, ext: str = "svg") -> str | None:
    """Relative path under static/ if the asset file exists."""
    if not slug or not asset_exists(kind, slug, ext):
        return None
    subdir = _ASSET_SUBDIRS.get(kind, kind)
    return f"img/{subdir}/{slug}.{ext}"


def logo_external_url(slug: str) -> str | None:
    """HTTPS URL for a real manufacturer logo (online CDN)."""
    if not slug:
        return None
    if slug in _LOGO_EXTERNAL_URLS:
        return _LOGO_EXTERNAL_URLS[slug]
    si_slug = _LOGO_SIMPLE_ICONS_SLUG.get(slug)
    if not si_slug:
        return None
    color = brand_color(slug).lstrip("#")
    return f"{_SIMPLE_ICONS_CDN}/{si_slug}/{color}"


def build_team_logo_lookup(teams: list) -> dict:
    """Map team_id → logo_slug from team records."""
    lookup = {}
    for team in teams:
        team_id = team.get("id")
        if team_id is None:
            continue
        slug = team.get("logo_slug") or logo_slug_from_car(team.get("car", ""))
        lookup[team_id] = slug
    return lookup


def team_logo_context(team_id, team_logos: dict) -> dict:
    """Template context for one team logo (url or fallback)."""
    slug = team_logos.get(team_id) if team_id is not None else None
    if not slug and team_id is not None:
        slug = "unknown"
    external = logo_external_url(slug) if slug else None
    rel = static_relpath("logo", slug) if slug else None
    return {
        "slug": slug,
        "url": external or rel,
        "brand": brand_color(slug or ""),
        "initial": brand_initial(slug or ""),
        "has_image": external is not None or rel is not None,
    }
