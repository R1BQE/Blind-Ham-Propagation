import math

import pytest

from backend.app.services.geo_filter import (
    DEFAULT_RADIUS_KM,
    classify_spot_region,
    distance_between_locators,
    haversine_km,
)
from backend.app.services.maidenhead import LocatorError


def test_default_observation_radius_is_100_km():
    assert DEFAULT_RADIUS_KM == 100.0


def test_haversine_same_point_is_zero():
    assert haversine_km(59.0, 30.0, 59.0, 30.0) == pytest.approx(0.0)


def test_haversine_known_one_degree_equatorial_distance():
    assert haversine_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(111.195, abs=0.01)


def test_haversine_handles_antimeridian():
    assert haversine_km(0.0, 179.5, 0.0, -179.5) == pytest.approx(111.195, abs=0.01)


@pytest.mark.parametrize(
    "coordinates",
    [
        (91.0, 0.0, 0.0, 0.0),
        (0.0, 181.0, 0.0, 0.0),
        (math.nan, 0.0, 0.0, 0.0),
        (0.0, 0.0, math.inf, 0.0),
    ],
)
def test_haversine_rejects_invalid_coordinates(coordinates):
    with pytest.raises(ValueError):
        haversine_km(*coordinates)


def test_distance_between_locator_centers_is_symmetric():
    forward = distance_between_locators("KO59XX", "KO59XW")
    reverse = distance_between_locators("KO59XW", "KO59XX")
    assert forward > 0
    assert forward == pytest.approx(reverse)


def test_spot_classifies_tx_and_rx_independently():
    result = classify_spot_region(
        {"tx_grid": "KO59XX", "rx_grid": "FN31pr"}, "KO59XX"
    )
    assert result["tx_in_area"] is True
    assert result["rx_in_area"] is False
    assert result["tx_distance_km"] == pytest.approx(0.0)
    assert result["rx_distance_km"] is not None
    assert result["rx_distance_km"] > 100


def test_station_inside_radius_is_included():
    result = classify_spot_region(
        {"tx_grid": "KO59XX", "rx_grid": "KO59XW"}, "KO59XX", radius_km=100
    )
    assert result["tx_in_area"] is True
    assert result["rx_in_area"] is True


def test_station_outside_radius_is_excluded():
    result = classify_spot_region(
        {"tx_grid": "KO59XX", "rx_grid": "LO00AA"}, "KO59XX", radius_km=100
    )
    assert result["tx_in_area"] is True
    assert result["rx_in_area"] is False


def test_missing_or_invalid_station_locator_is_not_in_area():
    result = classify_spot_region(
        {"tx_grid": None, "rx_grid": "INVALID"}, "KO59XX"
    )
    assert result["tx_in_area"] is False
    assert result["rx_in_area"] is False
    assert result["tx_distance_km"] is None
    assert result["rx_distance_km"] is None


def test_qth_locator_must_be_valid():
    with pytest.raises(LocatorError):
        classify_spot_region(
            {"tx_grid": "KO59XX", "rx_grid": "KO59XW"}, "INVALID"
        )


@pytest.mark.parametrize("radius", [0, -1, math.nan, math.inf])
def test_radius_must_be_finite_and_positive(radius):
    with pytest.raises(ValueError):
        classify_spot_region(
            {"tx_grid": "KO59XX", "rx_grid": "KO59XW"}, "KO59XX", radius
        )


def test_station_exactly_on_radius_boundary_is_included():
    radius = distance_between_locators("KO59XX", "KO59XW")
    result = classify_spot_region(
        {"tx_grid": "KO59XX", "rx_grid": "KO59XW"},
        "KO59XX",
        radius_km=radius,
    )
    assert result["rx_distance_km"] == pytest.approx(radius, abs=0.001)
    assert result["rx_in_area"] is True
