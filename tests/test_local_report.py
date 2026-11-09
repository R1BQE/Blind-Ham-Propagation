from datetime import datetime, timezone

from backend.app.services.local_report import build_local_report, solar_position


def test_local_report_contains_locator_and_coordinates():
    report = build_local_report("KO59XX", datetime(2026, 6, 21, 12, tzinfo=timezone.utc))
    assert report["locator"] == "KO59XX"
    assert report["latitude"] > 0
    assert report["longitude"] > 0
    assert "solar_elevation_degrees" in report["solar"]


def test_solar_position_is_daytime_at_equator_noon_equinox():
    result = solar_position(0, 0, datetime(2026, 3, 20, 12, tzinfo=timezone.utc))
    assert result["solar_elevation_degrees"] > 80
    assert result["illumination"] == "Солнце над горизонтом"


def test_solar_position_is_night_at_equator_midnight_equinox():
    result = solar_position(0, 0, datetime(2026, 3, 20, 0, tzinfo=timezone.utc))
    assert result["solar_elevation_degrees"] < -80
    assert result["illumination"] == "Ночь"
