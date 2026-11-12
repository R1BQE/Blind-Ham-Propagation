from pathlib import Path

from backend.app.services.runtime_paths import (
    data_directory,
    project_root,
    settings_file_path,
)


def test_runtime_paths_default_to_release_tree(monkeypatch):
    monkeypatch.delenv("BLIND_HAM_DATA_DIR", raising=False)
    monkeypatch.delenv("BLIND_HAM_SETTINGS_FILE", raising=False)

    root = project_root()
    assert data_directory() == root / "data"
    assert settings_file_path() == root / "settings.ini"


def test_runtime_paths_can_be_shared_between_releases(monkeypatch, tmp_path):
    shared_data = tmp_path / "shared-data"
    shared_settings = tmp_path / "config" / "settings.ini"
    monkeypatch.setenv("BLIND_HAM_DATA_DIR", str(shared_data))
    monkeypatch.setenv("BLIND_HAM_SETTINGS_FILE", str(shared_settings))

    assert data_directory() == shared_data
    assert settings_file_path() == shared_settings


def test_runtime_paths_expand_home_directory(monkeypatch):
    monkeypatch.setenv("BLIND_HAM_DATA_DIR", "~/blind-ham-data")
    monkeypatch.setenv("BLIND_HAM_SETTINGS_FILE", "~/blind-ham/settings.ini")

    assert data_directory() == Path("~/blind-ham-data").expanduser()
    assert settings_file_path() == Path("~/blind-ham/settings.ini").expanduser()
