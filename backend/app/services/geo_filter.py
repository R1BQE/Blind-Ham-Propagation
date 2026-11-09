"""Geographic filtering for PSK Reporter regional observations.

Locator-derived coordinates refer to Maidenhead cell centers, not exact station
positions. Distances are therefore approximate.
"""
from __future__ import annotations

import math
from typing import Any

from backend.app.services.maidenhead import LocatorError, locator_to_center

EARTH_RADIUS_KM = 6371.0088
DEFAULT_RADIUS_KM = 100.0


def haversine_km(latitude_1: float, longitude_1: float,
                 latitude_2: float, longitude_2: float) -> float:
    """Return great-circle distance between two geographic coordinates."""
    values = (latitude_1, longitude_1, latitude_2, longitude_2)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Координаты должны быть конечными числами.")
    if not -90 <= latitude_1 <= 90 or not -90 <= latitude_2 <= 90:
        raise ValueError("Широта должна находиться в диапазоне от -90 до 90.")
    if not -180 <= longitude_1 <= 180 or not -180 <= longitude_2 <= 180:
        raise ValueError("Долгота должна находиться в диапазоне от -180 до 180.")

    lat_1 = math.radians(latitude_1)
    lat_2 = math.radians(latitude_2)
    delta_lat = math.radians(latitude_2 - latitude_1)
    delta_lon = math.radians(longitude_2 - longitude_1)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * math.asin(math.sqrt(min(1.0, haversine)))
    return EARTH_RADIUS_KM * central_angle


def distance_between_locators(locator_1: str, locator_2: str) -> float:
    """Return approximate distance between the centers of two locator cells."""
    latitude_1, longitude_1 = locator_to_center(locator_1)
    latitude_2, longitude_2 = locator_to_center(locator_2)
    return haversine_km(latitude_1, longitude_1, latitude_2, longitude_2)


def _optional_locator_distance(center: tuple[float, float],
                               locator: str | None) -> float | None:
    if not isinstance(locator, str) or not locator.strip():
        return None
    try:
        latitude, longitude = locator_to_center(locator)
    except (LocatorError, AttributeError):
        return None
    return haversine_km(center[0], center[1], latitude, longitude)


def classify_spot_region(
    spot: dict[str, Any],
    qth_locator: str,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> dict[str, float | bool | None]:
    """Classify TX and RX independently against the QTH observation area.

    A missing or invalid station locator has no distance and is not in-area.
    An invalid QTH locator or radius raises an exception.
    """
    if not math.isfinite(radius_km) or radius_km <= 0:
        raise ValueError("Радиус области наблюдения должен быть положительным числом.")

    center = locator_to_center(qth_locator)
    tx_distance = _optional_locator_distance(center, spot.get("tx_grid"))
    rx_distance = _optional_locator_distance(center, spot.get("rx_grid"))
    return {
        "tx_distance_km": round(tx_distance, 3) if tx_distance is not None else None,
        "rx_distance_km": round(rx_distance, 3) if rx_distance is not None else None,
        "tx_in_area": tx_distance is not None and tx_distance <= radius_km,
        "rx_in_area": rx_distance is not None and rx_distance <= radius_km,
    }
