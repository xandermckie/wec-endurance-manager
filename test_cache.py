import json
from unittest.mock import patch

import cache


def test_load_cache_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", str(tmp_path / "missing.json"))
    data = cache.load_cache()
    assert data == cache.DEFAULT_CACHE


def test_load_cache_corrupt_restores_backup(tmp_path, monkeypatch):
    cache_path = tmp_path / "grid.json"
    backup_path = tmp_path / "grid.json.bak"
    cache_path.write_text("{not json", encoding="utf-8")
    backup_path.write_text(
        json.dumps({"drivers": [{"id": 1}], "teams": [], "last_updated": "Z", "season": 2025}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cache, "CACHE_PATH", str(cache_path))

    data = cache.load_cache()

    assert len(data["drivers"]) == 1
    assert data["drivers"][0]["id"] == 1


def test_load_cache_corrupt_without_backup_returns_default(tmp_path, monkeypatch):
    cache_path = tmp_path / "grid.json"
    cache_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(cache, "CACHE_PATH", str(cache_path))

    data = cache.load_cache()

    assert data["drivers"] == []


def test_save_cache_logs_backup_failure(tmp_path, monkeypatch, caplog):
    import logging

    cache_path = tmp_path / "grid.json"
    cache_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cache, "CACHE_PATH", str(cache_path))

    payload = {"drivers": [], "teams": [], "last_updated": None, "season": None}
    with patch("cache.shutil.copy2", side_effect=OSError("denied")):
        with caplog.at_level(logging.WARNING):
            cache.save_cache(payload)

    assert cache.load_cache()["drivers"] == []
