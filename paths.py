"""Application paths for development and PyInstaller frozen builds."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "WEC-Endurance-Manager"
    else:
        base = Path.home() / ".local" / "share" / "wec-endurance-manager"
    base.mkdir(parents=True, exist_ok=True)
    return base


def writable_data_dir() -> Path:
    """User-writable data/ (season saves, grid cache) — separate from bundle when frozen."""
    if is_frozen():
        path = user_data_dir() / "data"
    else:
        path = bundle_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_data_path(filename: str) -> Path:
    return bundle_dir() / "data" / filename


def init_user_data() -> None:
    """Seed writable data files from the bundle on first run (frozen builds only)."""
    if not is_frozen():
        return

    writable = writable_data_dir()
    seasons = writable / "seasons"
    seasons.mkdir(parents=True, exist_ok=True)

    for filename in ("grid.json", "names.json"):
        dest = writable / filename
        if dest.exists():
            continue
        source = bundled_data_path(filename)
        if source.is_file():
            shutil.copy2(source, dest)
