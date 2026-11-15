"""Add Russian GeoNames alternate names to an existing geography database.

This migration downloads only alternateNamesV2.zip. It does not rebuild
the 5+ million settlement records or redownload Natural Earth boundaries.
Run from the repository root:
    python scripts/update_russian_geography_names.py
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from build_geography import (
    GEONAMES_ALT_NAMES_URL,
    download,
    import_russian_alternate_names,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATABASE = DATA_DIR / "geography.sqlite3"


def update() -> None:
    if not DATABASE.is_file():
        raise FileNotFoundError(f"Географическая база не найдена: {DATABASE}")

    with tempfile.TemporaryDirectory(prefix="geography-ru-", dir=DATA_DIR) as temporary:
        temp = Path(temporary)
        working_database = temp / "geography.sqlite3"
        archive_path = temp / "alternateNamesV2.zip"

        print("Копируем существующую базу…", flush=True)
        shutil.copyfile(DATABASE, working_database)

        print("Скачиваем русские альтернативные названия GeoNames…", flush=True)
        download(GEONAMES_ALT_NAMES_URL, archive_path)

        connection = sqlite3.connect(working_database)
        try:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(settlements)")
            }
            if "name_ru" not in columns:
                connection.execute("ALTER TABLE settlements ADD COLUMN name_ru TEXT")

            matched = import_russian_alternate_names(archive_path, connection)
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
                ("source_geonames_alternate_names", GEONAMES_ALT_NAMES_URL),
            )
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
                ("database_schema", "2"),
            )
            connection.commit()

            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"Проверка целостности SQLite не пройдена: {integrity}")
        finally:
            connection.close()

        working_database.replace(DATABASE)

    print(f"Готово. Русские названия добавлены для {matched:,} населённых пунктов.", flush=True)
    print(f"База обновлена: {DATABASE}", flush=True)


if __name__ == "__main__":
    try:
        update()
    except Exception as error:
        print(f"Ошибка обновления русских названий: {error}", file=sys.stderr)
        raise
