import json
import logging
import os
import shutil
import tempfile

from paths import writable_data_dir

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(writable_data_dir(), "grid.json")

DEFAULT_CACHE = {"last_updated": None, "season": None, "drivers": []}


def _normalize_cache_data(data):
    if not data:
        return dict(DEFAULT_CACHE)
    data.setdefault("drivers", [])
    data.setdefault("teams", [])
    return data


def load_cache():
    if not os.path.exists(CACHE_PATH):
        return dict(DEFAULT_CACHE)

    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return _normalize_cache_data(json.load(f))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt or unreadable grid cache: %s", exc)

    backup_path = CACHE_PATH + ".bak"
    if os.path.exists(backup_path):
        try:
            with open(backup_path, encoding="utf-8") as f:
                data = _normalize_cache_data(json.load(f))
            logger.warning("Restored grid cache from backup")
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Grid cache backup also unreadable: %s", exc)

    return dict(DEFAULT_CACHE)


def save_cache(data):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=os.path.dirname(CACHE_PATH), suffix=".tmp", prefix="grid-"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

        with open(temp_path, encoding="utf-8") as handle:
            json.loads(handle.read())

        if os.path.exists(CACHE_PATH):
            try:
                shutil.copy2(CACHE_PATH, CACHE_PATH + ".bak")
            except OSError:
                logger.warning("Could not write grid cache backup")

        os.replace(temp_path, CACHE_PATH)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def get_drivers():
    return load_cache().get("drivers", [])
