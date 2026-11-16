"""Validate and prepare the local offline geography database."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "geography.sqlite3"
BUILDER = ROOT / "scripts" / "build_geography.py"
EXPECTED_SCHEMA = "2"
REQUIRED_TABLES = {
    "countries", "countries_rtree", "admin1", "admin1_rtree",
    "settlements", "settlements_rtree", "metadata",
}


def validate_database(database: str | Path = DATABASE) -> tuple[bool, str]:
    path = Path(database)
    if not path.is_file() or path.stat().st_size == 0:
        return False, "файл отсутствует или пуст"
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return False, f"ошибка целостности SQLite: {integrity[0] if integrity else 'нет результата'}"
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                )
            }
            missing = REQUIRED_TABLES - tables
            if missing:
                return False, "отсутствуют таблицы или индексы: " + ", ".join(sorted(missing))
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("database_schema") != EXPECTED_SCHEMA:
                return False, (
                    f"неподдерживаемая схема {metadata.get('database_schema')!r}; "
                    f"ожидается {EXPECTED_SCHEMA}"
                )
            count = connection.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
            if count <= 0:
                return False, "таблица settlements не содержит населённых пунктов"
            return True, f"{count:,} населённых пунктов; схема {EXPECTED_SCHEMA}"
        finally:
            connection.close()
    except (sqlite3.Error, OSError, ValueError) as error:
        return False, f"не удалось проверить SQLite: {error}"


def ensure_database(
    database: str | Path = DATABASE,
    builder: str | Path = BUILDER,
) -> None:
    path = Path(database)
    valid, details = validate_database(path)
    if valid:
        print(f"Офлайн-база географии готова: {details}. Повторная загрузка не нужна.", flush=True)
        return
    print(f"Офлайн-база географии требует подготовки: {details}.", flush=True)
    print("Загружаем GeoNames и Natural Earth; это может занять некоторое время.", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(builder)], cwd=ROOT, check=True)
    valid, details = validate_database(path)
    if not valid:
        raise RuntimeError(f"После построения геобаза не прошла проверку: {details}")
    print(f"Офлайн-база географии успешно подготовлена: {details}.", flush=True)


if __name__ == "__main__":
    try:
        ensure_database()
    except Exception as error:
        print(f"Ошибка подготовки географической базы: {error}", file=sys.stderr)
        raise SystemExit(1)
