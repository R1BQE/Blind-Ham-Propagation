"""Build a regional PSK Reporter report around a Maidenhead QTH."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
import math
from typing import Any

from backend.app.services.geo_filter import classify_spot_region, distance_between_locators
from backend.app.services.maidenhead import locator_to_center
from backend.app.services.spot_store import SpotStore

COMPASS_POINTS = (
    "Север", "Северо-восток", "Восток", "Юго-восток",
    "Юг", "Юго-запад", "Запад", "Северо-запад",
)


@lru_cache(maxsize=131_072)
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
    return round(degrees, 1), COMPASS_POINTS[int((degrees + 22.5) // 45.0) % 8]


def _iso_utc(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()


def build_regional_report(
    locator: str,
    radius_km: float = 100.0,
    hours: float = 6,
    *,
    store: SpotStore | Any | None = None,
    now: int | None = None,
    details_limit: int = 10,
    details_offset: int = 0,
    bands: list[str] | None = None,
    modes: list[str] | None = None,
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
    if hours not in {0.5, 1, 2, 3, 4, 5, 6}:
        raise ValueError("Период должен быть одним из значений: 30 минут, 1, 2, 3, 4, 5 или 6 часов.")
    if details_limit < 1 or details_limit > 100:
        raise ValueError("Лимит подробных записей должен быть от 1 до 100.")
    if details_offset < 0:
        raise ValueError("Смещение списка станций не может быть отрицательным.")

    current = int(time.time()) if now is None else int(now)
    spot_store = store or SpotStore()
    cutoff = current - hours * 3600
    selected_bands = {value.strip().lower() for value in bands or [] if value.strip()}
    selected_modes = {value.strip().upper() for value in modes or [] if value.strip()}
    regional_iterator = getattr(spot_store, "iter_recent_for_region", None)
    iterator = getattr(spot_store, "iter_recent", None)
    if callable(regional_iterator):
        spots = regional_iterator(
            locator=normalized_locator,
            radius_km=radius_km,
            now=current,
            since=cutoff,
            bands=list(selected_bands),
            modes=list(selected_modes),
        )
    elif callable(iterator):
        spots = iterator(now=current, since=cutoff)
    else:
        # Compatibility with lightweight custom stores used by integrations/tests.
        spots = spot_store.list_recent(now=current, limit=5_000_000)
    scanned_spots = 0

    spot_counts = {"tx": 0, "rx": 0}
    last_seen: dict[str, int | None] = {"tx": None, "rx": None}
    band_stats: dict[str, dict[tuple[str, str], dict[str, Any]]] = {
        "tx": defaultdict(lambda: {"count": 0, "stations": set(), "last_seen": None}),
        "rx": defaultdict(lambda: {"count": 0, "stations": set(), "last_seen": None}),
    }
    station_sets: dict[str, set[str]] = {"tx": set(), "rx": set()}
    station_details: dict[str, dict[str, dict[str, Any]]] = {"tx": {}, "rx": {}}

    for spot in spots:
        scanned_spots += 1
        observed_at = int(spot.get("observed_at") or 0)
        if observed_at < cutoff or observed_at > current + 300:
            continue
        if selected_bands and str(spot.get("band") or "").lower() not in selected_bands:
            continue
        if selected_modes and str(spot.get("mode") or "").upper() not in selected_modes:
            continue
        region = classify_spot_region(
            spot, normalized_locator, radius_km, center=(center_lat, center_lon)
        )

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

            spot_counts[direction] += 1
            if last_seen[direction] is None or observed_at > last_seen[direction]:
                last_seen[direction] = observed_at

            station_key = local_call or (
                str(local_grid).strip().upper() if local_grid else ""
            )
            station = None
            needs_detail = False
            if station_key:
                station_sets[direction].add(station_key)
                station = station_details[direction].get(station_key)
                if station is None:
                    station = {"station_spots": 0}
                    station_details[direction][station_key] = station
                    needs_detail = True
                elif observed_at > int(station.get("observed_at_epoch") or 0):
                    needs_detail = True
                station["station_spots"] += 1

            band_value = str(spot.get("band") or "Неизвестно")
            mode_value = str(spot.get("mode") or "Неизвестно")

            # Detailed geodesic calculations are needed only for the newest
            # observation of each local station, not for every repeated spot.
            if needs_detail and station is not None:
                remote_distance = None
                bearing_degrees = None
                bearing_direction = None
                station_distance = None
                station_azimuth_degrees = None
                station_azimuth_direction = None

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

                if (isinstance(local_grid, str) and local_grid.strip()
                        and isinstance(remote_grid, str) and remote_grid.strip()):
                    try:
                        local_lat, local_lon = locator_to_center(local_grid)
                        remote_lat, remote_lon = locator_to_center(remote_grid)
                        station_distance = distance_between_locators(local_grid, remote_grid)
                        tx_lat, tx_lon = (
                            (local_lat, local_lon) if direction == "tx"
                            else (remote_lat, remote_lon)
                        )
                        rx_lat, rx_lon = (
                            (remote_lat, remote_lon) if direction == "tx"
                            else (local_lat, local_lon)
                        )
                        station_azimuth_degrees, station_azimuth_direction = _bearing(
                            tx_lat, tx_lon, rx_lat, rx_lon
                        )
                    except (ValueError, TypeError):
                        pass

                item = {
                    "band": band_value,
                    "mode": mode_value,
                    "local_call": local_call or "Неизвестно",
                    "local_grid": local_grid,
                    "remote_call": remote_call or "Неизвестно",
                    "remote_grid": remote_grid,
                    "distance_km": (
                        round(float(remote_distance), 1)
                        if remote_distance is not None else None
                    ),
                    "local_distance_km": (
                        round(float(local_distance), 1)
                        if local_distance is not None else None
                    ),
                    "bearing_degrees": bearing_degrees,
                    "bearing": bearing_direction,
                    "station_distance_km": (
                        round(float(station_distance), 1)
                        if station_distance is not None else None
                    ),
                    "station_azimuth_degrees": station_azimuth_degrees,
                    "station_azimuth": station_azimuth_direction,
                    "snr_db": spot.get("snr_db"),
                    "frequency_hz": spot.get("frequency_hz"),
                    "observed_at": _iso_utc(observed_at),
                    "observed_at_epoch": observed_at,
                }
                station_spots = station["station_spots"]
                station.update(item)
                station["station_spots"] = station_spots

            key = (band_value, mode_value)
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
        "bands": sorted(selected_bands),
        "modes": sorted(selected_modes),
        "generated_at": _iso_utc(current),
        "period_started_at": _iso_utc(cutoff),
        "stored_spots_scanned": scanned_spots,
        "tx": {},
        "rx": {},
        "explanation": {
            "tx": "Передатчики внутри области QTH были услышаны удалёнными приёмниками.",
            "rx": "Приёмники внутри области QTH услышали удалённые передатчики.",
            "distance": (
                "Расстояния от QTH считаются от центра твоего локатора. "
                "Расстояние между станциями считается отдельно по их локаторам. "
                "Азимут радиотрассы направлен от передатчика к приёмнику."
            ),
        },
    }

    for direction in ("tx", "rx"):
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
        ordered_stations = sorted(
            station_details[direction].values(),
            key=lambda row: row["observed_at_epoch"],
            reverse=True,
        )
        page_stations = ordered_stations[details_offset:details_offset + details_limit]
        public_stations = [
            {key: value for key, value in entry.items() if key != "observed_at_epoch"}
            for entry in page_stations
        ]

        result[direction] = {
            "spots": spot_counts[direction],
            "unique_local_stations": len(station_sets[direction]),
            "last_seen": _iso_utc(last_seen[direction]),
            "by_band": band_rows,
            "stations": public_stations,
            "latest": public_stations,
            "stations_total": len(ordered_stations),
            "stations_offset": details_offset,
            "stations_limit": details_limit,
        }

    return result
