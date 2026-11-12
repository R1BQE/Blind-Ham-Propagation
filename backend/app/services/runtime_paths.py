"""Stable runtime paths shared by versioned application releases.

When the application is launched through a `current` symlink, Path.resolve()
points into the selected release. Persistent state must therefore be supplied
through environment variables rather than inferred from the release directory.
"""
from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Return the physical root of the checked-out application release."""
    return Path(__file__).resolve().parents[3]


def settings_file_path() -> Path:
    """Return the runtime settings file, optionally outside the release tree."""
    configured = os.environ.get("BLIND_HAM_SETTINGS_FILE", "").strip()
    return Path(configured).expanduser() if configured else project_root() / "settings.ini"


def data_directory() -> Path:
    """Return the persistent data directory, optionally shared by releases."""
    configured = os.environ.get("BLIND_HAM_DATA_DIR", "").strip()
    return Path(configured).expanduser() if configured else project_root() / "data"
