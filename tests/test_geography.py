import sqlite3

import pytest

from backend.app.services.geography import (
    GeographyDatabase,
    SETTLEMENT_RADIUS_KM,
    _distance_km,
    _geometry_contains,
)


def polygon(min_lon, min_lat, max_lon, max_lat):
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]],
    }


def make_database(path, settlement=None):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE countries (
            id INTEGER PRIMARY KEY, name TEXT, geometry TEXT
        );
        CREATE VIRTUAL TABLE countries_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE admin1 (
            id INTEGER PRIMARY KEY, name TEXT, geometry TEXT
        );
        CREATE VIRTUAL TABLE admin1_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
        CREATE TABLE settlements (
            geoname_id INTEGER PRIMARY KEY, name TEXT, name_ru TEXT,
            latitude REAL, longitude REAL,
            population INTEGER
        );
        CREATE VIRTUAL TABLE settlements_rtree USING rtree(id, min_lon, max_lon, min_lat, max_lat);
    """)
    country_geometry = polygon(-10, -10, 10, 10)
    connection.execute(
        "INSERT INTO countries VALUES (1, 'Testland', ?)",
        (__import__("json").dumps(country_geometry),),
    )
    connection.execute("INSERT INTO countries_rtree VALUES (1, -10, 10, -10, 10)")
    region_geometry = polygon(-5, -5, 5, 5)
    connection.execute(
        "INSERT INTO admin1 VALUES (1, 'Test Region', ?)",
        (__import__("json").dumps(region_geometry),),
    )
    connection.execute("INSERT INTO admin1_rtree VALUES (1, -5, 5, -5, 5)")
    if settlement:
        geoname_id, name, latitude, longitude = settlement
        connection.execute(
            "INSERT INTO settlements VALUES (?, ?, NULL, ?, ?, 100)",
            (geoname_id, name, latitude, longitude),
        )
        connection.execute(
            "INSERT INTO settlements_rtree VALUES (?, ?, ?, ?, ?)",
            (geoname_id, longitude, longitude, latitude, latitude),
        )
    connection.commit()
    connection.close()


def test_point_in_polygon_and_hole():
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
        ],
    }
    assert _geometry_contains(geometry, 2, 2)
    assert not _geometry_contains(geometry, 5, 5)
    assert not _geometry_contains(geometry, 20, 20)


def test_distance_uses_great_circle():
    assert _distance_km(0, 0, 0, 1) == pytest.approx(111.195, abs=0.02)


def test_lookup_returns_country_region_and_nearest_settlement(tmp_path):
    path = tmp_path / "geography.sqlite3"
    make_database(path, (123, "Village", 0.1, 0.1))

    result = GeographyDatabase(path).lookup(0, 0)

    assert result["country"] == "Testland"
    assert result["region"] == "Test Region"
    assert result["settlement"] == "Village"
    assert result["settlement_distance_km"] is not None
    assert result["text"] == "Testland, Test Region, Village"


def test_lookup_keeps_country_and_region_without_settlement(tmp_path):
    path = tmp_path / "geography.sqlite3"
    make_database(path)

    result = GeographyDatabase(path).lookup(0, 0)

    assert result["country"] == "Testland"
    assert result["region"] == "Test Region"
    assert result["settlement"] is None
    assert result["text"] == "Testland, Test Region"


def test_lookup_does_not_show_settlement_beyond_50_km(tmp_path):
    path = tmp_path / "geography.sqlite3"
    make_database(path, (123, "Far town", 0, 0.6))

    result = GeographyDatabase(path).lookup(0, 0)

    assert SETTLEMENT_RADIUS_KM == 50
    assert result["settlement"] is None
    assert result["country"] == "Testland"


def test_lookup_returns_empty_geography_when_database_is_missing(tmp_path):
    result = GeographyDatabase(tmp_path / "missing.sqlite3").lookup(0, 0)
    assert result["country"] is None
    assert result["region"] is None
    assert "не подготовлена" in result["text"]


def test_lookup_rejects_invalid_coordinates(tmp_path):
    with pytest.raises(ValueError):
        GeographyDatabase(tmp_path / "missing.sqlite3").lookup(91, 0)



def test_lookup_prefers_russian_settlement_name(tmp_path):
    path = tmp_path / "geography.sqlite3"
    make_database(path, (123, "Moscow", 0.1, 0.1))
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE settlements SET name_ru = 'Москва' WHERE geoname_id = 123"
    )
    connection.commit()
    connection.close()

    result = GeographyDatabase(path).lookup(0, 0)

    assert result["settlement"] == "Москва"
    assert result["text"] == "Testland, Test Region, Москва"


def test_lookup_falls_back_to_primary_name_without_russian_name(tmp_path):
    path = tmp_path / "geography.sqlite3"
    make_database(path, (123, "Moscow", 0.1, 0.1))

    result = GeographyDatabase(path).lookup(0, 0)

    assert result["settlement"] == "Moscow"
