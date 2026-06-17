import json
from unittest.mock import patch

import pytest

import season_store


def test_load_season_restores_from_backup(tmp_path, monkeypatch):
    season_id = "test-season"
    season_dir = tmp_path / "seasons"
    season_dir.mkdir()
    path = season_dir / f"{season_id}.json"
    backup = season_dir / f"{season_id}.json.bak"
    path.write_text("{bad", encoding="utf-8")
    backup.write_text(json.dumps({"season_year": 2025, "phase": "regular"}), encoding="utf-8")
    monkeypatch.setattr(season_store, "SEASONS_DIR", str(season_dir))

    data, status = season_store.load_season(season_id)

    assert status == "restored"
    assert data["season_year"] == 2025


def test_save_season_raises_season_save_error(tmp_path, monkeypatch):
    season_id = "save-fail"
    season_dir = tmp_path / "seasons"
    season_dir.mkdir()
    monkeypatch.setattr(season_store, "SEASONS_DIR", str(season_dir))

    with patch("season_store.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(season_store.SeasonSaveError):
            season_store.save_season(season_id, dict(season_store.DEFAULT_SEASON))


def test_delete_season_tolerates_missing_file(tmp_path, monkeypatch):
    season_id = "gone"
    season_dir = tmp_path / "seasons"
    season_dir.mkdir()
    monkeypatch.setattr(season_store, "SEASONS_DIR", str(season_dir))

    season_store.delete_season(season_id)
