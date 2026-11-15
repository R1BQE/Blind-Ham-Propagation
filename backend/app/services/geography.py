"""Offline geographic lookup for Maidenhead cell centres."""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DATABASE = Path(__file__).resolve().parents[3] / "data" / "geography.sqlite3"
SETTLEMENT_RADIUS_KM = 50.0
EARTH_RADIUS_KM = 6371.0088


def _point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 4:
        return False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[0], previous[1]
        x2, y2 = current[0], current[1]
        if (y1 > latitude) != (y2 > latitude):
            crossing = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < crossing:
                inside = not inside
        previous = current
    return inside


def _geometry_contains(geometry: dict[str, Any], longitude: float, latitude: float) -> bool:
    polygons = geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        polygons = [polygons]
    for polygon in polygons:
        if not polygon or not _point_in_ring(longitude, latitude, polygon[0]):
            continue
        if not any(_point_in_ring(longitude, latitude, hole) for hole in polygon[1:]):
            return True
    return False


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(value)))


class GeographyDatabase:
    """Read-only lookup against the generated SQLite geography database."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE):
        self.database_path = Path(database_path)

    @property
    def available(self) -> bool:
        return self.database_path.is_file()

    def lookup(self, latitude: float, longitude: float) -> dict[str, Any]:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Координаты находятся вне допустимого диапазона.")
        if not self.available:
            return {
                "country": None,
                "region": None,
                "settlement": None,
                "settlement_distance_km": None,
                "text": "Географическая база ещё не подготовлена.",
            }

        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            country = self._find_boundary(connection, "countries", latitude, longitude)
            region = self._find_boundary(connection, "admin1", latitude, longitude)
            settlement = self._nearest_settlement(connection, latitude, longitude)
        finally:
            connection.close()

        country_name = country["name"] if country else None
        region_name = region["name"] if region else None
        settlement_name = settlement["name"] if settlement else None
        parts = [part for part in (country_name, region_name, settlement_name) if part]
        return {
            "country": country_name,
            "region": region_name,
            "settlement": settlement_name,
            "settlement_distance_km": (
                round(settlement["distance_km"], 1) if settlement else None
            ),
            "text": ", ".join(parts) if parts else "Географическое название не определено.",
        }

    @staticmethod
    def _find_boundary(
        connection: sqlite3.Connection, table: str, latitude: float, longitude: float
    ) -> dict[str, Any] | None:
        index = f"{table}_rtree"
        rows = connection.execute(
            f"""
            SELECT item.name, item.geometry
            FROM {index} AS bounds
            JOIN {table} AS item ON item.id = bounds.id
            WHERE bounds.min_lon <= ? AND bounds.max_lon >= ?
              AND bounds.min_lat <= ? AND bounds.max_lat >= ?
            """,
            (longitude, longitude, latitude, latitude),
        )
        for row in rows:
            if _geometry_contains(json.loads(row["geometry"]), longitude, latitude):
                return {"name": row["name"]}
        return None

    @staticmethod
    def _nearest_settlement(
        connection: sqlite3.Connection, latitude: float, longitude: float
    ) -> dict[str, Any] | None:
        latitude_delta = SETTLEMENT_RADIUS_KM / 110.574
        cosine = max(0.01, abs(math.cos(math.radians(latitude))))
        longitude_delta = min(180.0, SETTLEMENT_RADIUS_KM / (111.320 * cosine))
        rows = connection.execute(
            """
            SELECT s.geoname_id, COALESCE(s.name_ru, s.name) AS display_name,
                   s.latitude, s.longitude, s.population
            FROM settlements_rtree AS bounds
            JOIN settlements AS s ON s.geoname_id = bounds.id
            WHERE bounds.min_lon <= ? AND bounds.max_lon >= ?
              AND bounds.min_lat <= ? AND bounds.max_lat >= ?
            """,
            (
                longitude + longitude_delta,
                longitude - longitude_delta,
                latitude + latitude_delta,
                latitude - latitude_delta,
            ),
        )
        nearest = None
        for row in rows:
            distance = _distance_km(latitude, longitude, row["latitude"], row["longitude"])
            if distance > SETTLEMENT_RADIUS_KM:
                continue
            candidate = {
                "name": row["display_name"],
                "distance_km": distance,
                "population": row["population"],
                "geoname_id": row["geoname_id"],
            }
            if nearest is None or distance < nearest["distance_km"]:
                nearest = candidate
        return nearest
