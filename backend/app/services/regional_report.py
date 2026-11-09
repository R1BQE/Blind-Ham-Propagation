"""Build a regional PSK Reporter report around a Maidenhead QTH."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math
from typing import Any

from backend.app.services.geo_filter import classify_spot_region, distance_between_locators
from backend.app.services.maidenhead import locator_to_center
from backend.app.services.spot_store import SpotStore

COMPASS_POINTS = (
    "С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
    "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ",
)


def _bearing(latitude_1: float, longitude_1: float,
             latitude_2: float, longitude_2: float) -> tuple[float, str]:
    """Return initial great-circle bearing and a Russian compass direction."""
    import math

    lat1 = math.radians(latitude_1)
    lat2 = math.radians(latitude_2)
    delta_lon = math.radians(longitude_2 - longitude_1)
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    )
    degrees = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return round(degrees, 1), COMPASS_POINTS[int((degrees + 11.25) // 22.5) % 16]


def _iso_utc(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()


def build_regional_report(
    locator: str,
    radius_km: float = 100.0,
    hours: int = 6,
    *,
    store: SpotStore | Any | None = None,
    now: int | None = None,
    details_limit: int = 30,
) -> dict[str, Any]:
    """Summarize observations with TX and RX stations independently in QTH area.

    TX means a transmitter inside the selected area was heard by a remote
    receiver. RX means a receiver inside the selected area heard a remote
    transmitter. A spot may contribute to both groups if both endpoints are
    inside the area.
    """
    import time

    normalized_locator = locator.strip().upper()
    center_lat, center_lon = locator_to_center(normalized_locator)
    if not math.isfinite(radius_km) or radius_km <= 0:
        raise ValueError("Радиус области наблюдения должен быть положительным числом.")
    if not 1 <= hours <= 6:
        raise ValueError("Период должен быть от 1 до 6 часов.")
    if details_limit < 1 or details_limit > 100:
        raise ValueError("Лимит подробных записей должен быть от 1 до 100.")

    current = int(time.time()) if now is None else int(now)
    spot_store = store or SpotStore()
    spots = spot_store.list_recent(now=current, limit=50_000)
    cutoff = current - hours * 3600

    groups: dict[str, list[dict[str, Any]]] = {"tx": [], "rx": []}
    band_stats: dict[str, dict[tuple[str, str], dict[str, Any]]] = {
        "tx": defaultdict(lambda: {"count": 0, "stations": set(), "last_seen": None}),
        "rx": defaultdict(lambda: {"count": 0, "stations": set(), "last_seen": None}),
    }
    station_sets: dict[str, set[str]] = {"tx": set(), "rx": set()}

    for spot in spots:
        observed_at = int(spot.get("observed_at") or 0)
        if observed_at < cutoff or observed_at > current + 300:
            continue
        region = classify_spot_region(spot, normalized_locator, radius_km)

        for direction, local_side, remote_side in (
            ("tx", "tx", "rx"),
            ("rx", "rx", "tx"),
        ):
            if not region[f"{local_side}_in_area"]:
                continue

            local_call = str(spot.get(f"{local_side}_call") or "").strip().upper()
            local_grid = spot.get(f"{local_side}_grid")
            remote_call = str(spot.get(f"{remote_side}_call") or "").strip().upper()
            remote_grid = spot.get(f"{remote_side}_grid")
            local_distance = region[f"{local_side}_distance_km"]
            remote_distance = None
            bearing_degrees = None
            bearing_direction = None
            if isinstance(remote_grid, str) and remote_grid.strip():
                try:
                    remote_lat, remote_lon = locator_to_center(remote_grid)
                    remote_distance = distance_between_locators(
                        normalized_locator, remote_grid
                    )
                    bearing_degrees, bearing_direction = _bearing(
                        center_lat, center_lon, remote_lat, remote_lon
                    )
                except (ValueError, TypeError):
                    pass

            item = {
                "band": str(spot.get("band") or "Неизвестно"),
                "mode": str(spot.get("mode") or "Неизвестно"),
                "local_call": local_call or "Неизвестно",
                "local_grid": local_grid,
                "remote_call": remote_call or "Неизвестно",
                "remote_grid": remote_grid,
                "distance_km": round(float(remote_distance), 1) if remote_distance is not None else None,
                "local_distance_km": (
                    round(float(local_distance), 1) if local_distance is not None else None
                ),
                "bearing_degrees": bearing_degrees,
                "bearing": bearing_direction,
                "snr_db": spot.get("snr_db"),
                "frequency_hz": spot.get("frequency_hz"),
                "observed_at": _iso_utc(observed_at),
                "observed_at_epoch": observed_at,
            }
            groups[direction].append(item)
            station_sets[direction].add(local_call) if local_call else None
            key = (item["band"], item["mode"])
            stat = band_stats[direction][key]
            stat["count"] += 1
            if local_call:
                stat["stations"].add(local_call)
            stat["last_seen"] = max(stat["last_seen"] or 0, observed_at)

    result: dict[str, Any] = {
        "locator": normalized_locator,
        "latitude": round(center_lat, 6),
        "longitude": round(center_lon, 6),
        "radius_km": float(radius_km),
        "period_hours": hours,
        "generated_at": _iso_utc(current),
        "period_started_at": _iso_utc(cutoff),
        "stored_spots_scanned": len(spots),
        "tx": {},
        "rx": {},
        "explanation": {
            "tx": "Передатчики внутри области QTH были услышаны удалёнными приёмниками.",
            "rx": "Приёмники внутри области QTH услышали удалённые передатчики.",
            "distance": (
                "Расстояние и направление показывают удалённую станцию относительно QTH. "
                "Отдельно указано расстояние до местной станции внутри области."
            ),
        },
    }

    for direction in ("tx", "rx"):
        entries = sorted(groups[direction], key=lambda row: row["observed_at_epoch"], reverse=True)
        band_rows = []
        for (band, mode), stat in sorted(
            band_stats[direction].items(),
            key=lambda pair: (pair[0][0], pair[0][1]),
        ):
            band_rows.append({
                "band": band,
                "mode": mode,
                "spots": stat["count"],
                "stations": len(stat["stations"]),
                "last_seen": _iso_utc(stat["last_seen"]),
            })
        result[direction] = {
            "spots": len(entries),
            "unique_local_stations": len(station_sets[direction]),
            "last_seen": entries[0]["observed_at"] if entries else None,
            "by_band": band_rows,
            "latest": [
                {key: value for key, value in entry.items() if key != "observed_at_epoch"}
                for entry in entries[:details_limit]
            ],
        }

    return result
