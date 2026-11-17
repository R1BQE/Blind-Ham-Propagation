"""Build the offline geography database from GeoNames and Natural Earth.

Run from the repository root:
    python scripts/build_geography.py

The generated database is runtime data and must not be committed.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT = DATA_DIR / "geography.sqlite3"
GEONAMES_URL = "https://download.geonames.org/export/dump/allCountries.zip"
GEONAMES_ALT_NAMES_URL = "https://download.geonames.org/export/dump/alternateNamesV2.zip"
NATURAL_EARTH = {
    "countries": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip",
    "admin1": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip",
}
USER_AGENT = "Blind-Ham-Propagation geography database builder"


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def read_tsv(archive: zipfile.ZipFile, member: str):
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8")
        yield from csv.reader(text, delimiter="\t")


def field_value(record: dict, *names: str) -> str:
    for name in names:
        value = record.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def shape_records(archive_path: Path, table: str, connection: sqlite3.Connection) -> int:
    try:
        import shapefile
    except ImportError as exc:
        raise RuntimeError("Для подготовки границ установи зависимость: pip install pyshp") from exc

    with zipfile.ZipFile(archive_path) as archive:
        shp_name = next((name for name in archive.namelist() if name.lower().endswith(".shp")), None)
        if not shp_name:
            raise RuntimeError(f"В архиве {archive_path.name} не найден SHP-файл")
        with tempfile.TemporaryDirectory() as temporary:
            archive.extractall(temporary)
            reader = shapefile.Reader(str(Path(temporary) / shp_name))
            try:
                fields = [item[0] for item in reader.fields[1:]]
                count = 0
                for shape_record in reader.iterShapeRecords():
                    properties = dict(zip(fields, shape_record.record))
                    geometry = shape_record.shape.__geo_interface__
                    if not geometry or geometry.get("type") not in ("Polygon", "MultiPolygon"):
                        continue
                    if table == "countries":
                        code = field_value(properties, "ADM0_A3", "SOV_A3", "ISO_A3")
                        name = field_value(properties, "NAME_RU", "NAME", "ADMIN")
                        iso2 = field_value(properties, "ISO_A2")
                        if not code or not name:
                            continue
                        xmin, ymin, xmax, ymax = shape_record.shape.bbox
                        cursor = connection.execute(
                            "INSERT INTO countries(code, iso2, name, min_lon, max_lon, min_lat, max_lat, geometry) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (code, iso2, name, xmin, xmax, ymin, ymax, json.dumps(geometry, separators=(",", ":"))),
                        )
                        connection.execute(
                            "INSERT INTO countries_rtree(id, min_lon, max_lon, min_lat, max_lat) VALUES (?, ?, ?, ?, ?)",
                            (cursor.lastrowid, xmin, xmax, ymin, ymax),
                        )
                    else:
                        code = field_value(properties, "adm1_code", "postal", "iso_3166_2")
                        country = field_value(properties, "adm0_a3", "adm0_a3_us")
                        name = field_value(properties, "name_ru", "name", "name_en", "gn_name")
                        if not code or not country or not name:
                            continue
                        xmin, ymin, xmax, ymax = shape_record.shape.bbox
                        cursor = connection.execute(
                            "INSERT INTO admin1(code, country_code, name, min_lon, max_lon, min_lat, max_lat, geometry) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (code, country, name, xmin, xmax, ymin, ymax, json.dumps(geometry, separators=(",", ":"))),
                        )
                        connection.execute(
                            "INSERT INTO admin1_rtree(id, min_lon, max_lon, min_lat, max_lat) VALUES (?, ?, ?, ?, ?)",
                            (cursor.lastrowid, xmin, xmax, ymin, ymax),
                        )
                    count += 1
                return count
            finally:
                reader.close()


def import_russian_alternate_names(archive_path: Path, connection: sqlite3.Connection) -> int:
    """Import Russian GeoNames alternate names for populated places only."""
    connection.execute("""
        CREATE TEMP TABLE russian_names (
            geoname_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            preferred INTEGER NOT NULL
        )
    """)
    batch = []
    with zipfile.ZipFile(archive_path) as archive:
        for row in read_tsv(archive, "alternateNamesV2.txt"):
            if len(row) < 5 or row[2] != "ru" or not row[3]:
                continue
            try:
                geoname_id = int(row[1])
            except ValueError:
                continue
            preferred = 1 if row[4] == "1" else 0
            batch.append((geoname_id, row[3], preferred))
            if len(batch) >= 10000:
                connection.executemany("""
                    INSERT INTO russian_names(geoname_id, name, preferred)
                    VALUES (?, ?, ?)
                    ON CONFLICT(geoname_id) DO UPDATE SET
                        name = excluded.name,
                        preferred = excluded.preferred
                    WHERE excluded.preferred > russian_names.preferred
                """, batch)
                batch.clear()
    if batch:
        connection.executemany("""
            INSERT INTO russian_names(geoname_id, name, preferred)
            VALUES (?, ?, ?)
            ON CONFLICT(geoname_id) DO UPDATE SET
                name = excluded.name,
                preferred = excluded.preferred
            WHERE excluded.preferred > russian_names.preferred
        """, batch)

    connection.execute("""
        UPDATE settlements
        SET name_ru = (
            SELECT russian_names.name
            FROM russian_names
            WHERE russian_names.geoname_id = settlements.geoname_id
        )
        WHERE geoname_id IN (SELECT geoname_id FROM russian_names)
    """)
    matched = connection.execute(
        "SELECT COUNT(*) FROM settlements WHERE name_ru IS NOT NULL"
    ).fetchone()[0]
    connection.execute("DROP TABLE russian_names")
    return matched


def build() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        print("Скачиваем GeoNames allCountries…", flush=True)
        geonames_zip = temp / "allCountries.zip"
        download(GEONAMES_URL, geonames_zip)
        new_db = temp / "geography.sqlite3"
        connection = sqlite3.connect(new_db)
        try:
            connection.executescript("""
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                CREATE TABLE countries (
                    id INTEGER PRIMARY KEY, code TEXT NOT NULL, iso2 TEXT,
                    name TEXT NOT NULL, min_lon REAL, max_lon REAL, min_lat REAL, max_lat REAL,
                    geometry TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE countries_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
                CREATE TABLE admin1 (
                    id INTEGER PRIMARY KEY, code TEXT NOT NULL, country_code TEXT NOT NULL,
                    name TEXT NOT NULL, min_lon REAL NOT NULL, max_lon REAL NOT NULL,
                    min_lat REAL NOT NULL, max_lat REAL NOT NULL, geometry TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE admin1_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
                CREATE TABLE settlements (
                    geoname_id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ru TEXT,
                    ascii_name TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL,
                    country_code TEXT NOT NULL, admin1_code TEXT, feature_code TEXT,
                    population INTEGER NOT NULL DEFAULT 0
                );
                CREATE VIRTUAL TABLE settlements_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE INDEX settlements_country_admin ON settlements(country_code, admin1_code);
            """)

            print("Импортируем населённые пункты GeoNames…", flush=True)
            inserted = 0
            with zipfile.ZipFile(geonames_zip) as archive:
                for row in read_tsv(archive, "allCountries.txt"):
                    if len(row) < 19 or row[6] != "P":
                        continue
                    try:
                        geoname_id = int(row[0])
                        latitude = float(row[4])
                        longitude = float(row[5])
                        population = int(row[14] or 0)
                    except ValueError:
                        continue
                    name = row[1] or row[2]
                    cursor = connection.execute(
                        "INSERT OR IGNORE INTO settlements VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)",
                        (geoname_id, name, row[2], latitude, longitude, row[8], row[10], row[7], population),
                    )
                    if cursor.rowcount:
                        connection.execute(
                            "INSERT INTO settlements_rtree VALUES (?, ?, ?, ?, ?)",
                            (geoname_id, longitude, longitude, latitude, latitude),
                        )
                        inserted += 1
                    if inserted and inserted % 100000 == 0:
                        print(f"  Населённых пунктов: {inserted:,}", flush=True)

            print("Скачиваем русские альтернативные названия GeoNames…", flush=True)
            alternate_names_zip = temp / "alternateNamesV2.zip"
            download(GEONAMES_ALT_NAMES_URL, alternate_names_zip)
            russian_names = import_russian_alternate_names(alternate_names_zip, connection)
            print(f"  Населённых пунктов с русским названием: {russian_names:,}", flush=True)

            for table, key in (("countries", "countries"), ("admin1", "admin1")):
                print(f"Скачиваем границы Natural Earth: {table}…", flush=True)
                archive_path = temp / f"{table}.zip"
                download(NATURAL_EARTH[key], archive_path)
                count = shape_records(archive_path, table, connection)
                print(f"  Объектов границ: {count:,}", flush=True)

            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                [
                    ("geonames_settlements", str(inserted)),
                    ("database_schema", "2"),
                    ("source_geonames", GEONAMES_URL),
                    ("source_geonames_alternate_names", GEONAMES_ALT_NAMES_URL),
                    ("source_natural_earth_version", "5.1.1"),
                ],
            )
            connection.commit()
            connection.execute("PRAGMA optimize")
            connection.commit()
        finally:
            connection.close()

        replacement = DATA_DIR / "geography.sqlite3.new"
        shutil.copyfile(new_db, replacement)
        replacement.replace(OUTPUT)
    print(f"Готово: {OUTPUT}", flush=True)


if __name__ == "__main__":
    try:
        build()
    except Exception as error:
        print(f"Ошибка подготовки географической базы: {error}", file=sys.stderr)
        raise
