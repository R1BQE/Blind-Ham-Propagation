import sqlite3

from scripts.ensure_geography import validate_database


def create_valid_database(path):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE countries (id INTEGER PRIMARY KEY);
        CREATE VIRTUAL TABLE countries_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE admin1 (id INTEGER PRIMARY KEY);
        CREATE VIRTUAL TABLE admin1_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE settlements (geoname_id INTEGER PRIMARY KEY);
        CREATE VIRTUAL TABLE settlements_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO metadata VALUES ('database_schema', '2');
        INSERT INTO settlements VALUES (1);
    """)
    connection.commit()
    connection.close()


def test_validate_database_accepts_complete_schema_two_database(tmp_path):
    database = tmp_path / "geography.sqlite3"
    create_valid_database(database)
    valid, details = validate_database(database)
    assert valid
    assert "1" in details
    assert "схема 2" in details


def test_validate_database_rejects_missing_database(tmp_path):
    valid, details = validate_database(tmp_path / "missing.sqlite3")
    assert not valid
    assert "отсутствует" in details


def test_validate_database_rejects_missing_required_index(tmp_path):
    database = tmp_path / "geography.sqlite3"
    create_valid_database(database)
    connection = sqlite3.connect(database)
    connection.execute("DROP TABLE settlements_rtree")
    connection.commit()
    connection.close()
    valid, details = validate_database(database)
    assert not valid
    assert "settlements_rtree" in details


def test_validate_database_rejects_wrong_schema(tmp_path):
    database = tmp_path / "geography.sqlite3"
    create_valid_database(database)
    connection = sqlite3.connect(database)
    connection.execute("UPDATE metadata SET value = '1' WHERE key = 'database_schema'")
    connection.commit()
    connection.close()
    valid, details = validate_database(database)
    assert not valid
    assert "схема" in details


def test_validate_database_rejects_empty_settlements(tmp_path):
    database = tmp_path / "geography.sqlite3"
    create_valid_database(database)
    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM settlements")
    connection.commit()
    connection.close()
    valid, details = validate_database(database)
    assert not valid
    assert "не содержит" in details
