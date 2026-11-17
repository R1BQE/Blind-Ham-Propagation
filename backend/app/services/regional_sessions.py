"""Bounded in-memory regional analysis sessions fed by the shared MQTT collector."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import math
import secrets
import threading
import time
from typing import Any

from backend.app.services.geo_filter import classify_spot_region, distance_between_locators, locator_prefixes_for_radius
from backend.app.services.maidenhead import locator_to_center
from backend.app.services.regional_report import _bearing, _iso_utc

SESSION_DURATION_SECONDS = 60
RESULT_TTL_SECONDS = 600
MAX_ACTIVE_SESSIONS = 10
MAX_DEDUPE_KEYS = 4096
MAX_STATIONS_PER_DIRECTION = 5000
MAX_SPOT_AGE_SECONDS = 900


class RegionalSessionError(ValueError):
    """A regional session was not found or could not be created."""


class RegionalSessionCapacityError(RegionalSessionError):
    """The active regional session limit has been reached."""


@dataclass
class _Direction:
    spots: int = 0
    last_seen: int | None = None
    stations: dict[str, dict[str, Any]] = field(default_factory=dict)
    bands: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)


@dataclass
class _Session:
    session_id: str
    locator: str
    radius_km: float
    started_at: int
    finishes_at: int
    prefixes: frozenset[str]
    tx: _Direction = field(default_factory=_Direction)
    rx: _Direction = field(default_factory=_Direction)
    seen: OrderedDict[tuple[Any, ...], None] = field(default_factory=OrderedDict)
    scanned: int = 0
    accepted: int = 0
    completed_at: int | None = None
    duration_seconds: int = SESSION_DURATION_SECONDS
    cancelled: bool = False


class RegionalSessionManager:
    """Collect only aggregates for active regions; raw MQTT spots are not retained."""

    def __init__(
        self,
        *,
        duration_seconds: int = SESSION_DURATION_SECONDS,
        result_ttl_seconds: int = RESULT_TTL_SECONDS,
        max_active_sessions: int = MAX_ACTIVE_SESSIONS,
    ) -> None:
        if min(duration_seconds, result_ttl_seconds, max_active_sessions) <= 0:
            raise ValueError("Параметры сессий должны быть положительными.")
        self.duration_seconds = duration_seconds
        self.result_ttl_seconds = result_ttl_seconds
        self.max_active_sessions = max_active_sessions
        self._lock = threading.RLock()
        self._sessions: dict[str, _Session] = {}
        self._active_regions: dict[tuple[str, float], str] = {}

    @staticmethod
    def _region_key(locator: str, radius_km: float) -> tuple[str, float]:
        return locator.strip().upper(), round(float(radius_km), 1)

    def _refresh(self, now: int) -> None:
        expired = []
        for sid, session in self._sessions.items():
            if session.completed_at is None and now >= session.finishes_at:
                session.completed_at = session.finishes_at
                self._active_regions.pop(self._region_key(session.locator, session.radius_km), None)
            if session.completed_at is not None and now - session.completed_at >= self.result_ttl_seconds:
                expired.append(sid)
        for sid in expired:
            self._sessions.pop(sid, None)

    def _summary(self, session: _Session, now: int, reused: bool = False) -> dict[str, Any]:
        done = session.completed_at is not None or now >= session.finishes_at
        state = "cancelled" if session.cancelled else ("completed" if done else "collecting")
        return {
            "session_id": session.session_id,
            "locator": session.locator,
            "radius_km": session.radius_km,
            "state": state,
            "started_at": _iso_utc(session.started_at),
            "finishes_at": _iso_utc(session.finishes_at),
            "remaining_seconds": max(0, session.finishes_at - now),
            "duration_seconds": session.duration_seconds,
            "reused": reused,
        }

    def start(self, locator: str, radius_km: float, *, duration_seconds: int | None = None, now: int | None = None) -> dict[str, Any]:
        normalized = locator.strip().upper()
        locator_to_center(normalized)
        radius = float(radius_km)
        if not math.isfinite(radius) or not 0 < radius <= 1000:
            raise ValueError("Радиус должен быть больше 0 и не более 1000 км.")
        duration = self.duration_seconds if duration_seconds is None else int(duration_seconds)
        if duration_seconds is not None and duration not in {60, 120, 180, 300}:
            raise ValueError("Продолжительность сбора должна составлять 1, 2, 3 или 5 минут.")
        current = int(time.time()) if now is None else int(now)
        key = self._region_key(normalized, radius)
        with self._lock:
            self._refresh(current)
            existing = self._active_regions.get(key)
            if existing:
                return self._summary(self._sessions[existing], current, reused=True)
            active = sum(s.completed_at is None for s in self._sessions.values())
            if active >= self.max_active_sessions:
                raise RegionalSessionCapacityError(
                    "Достигнут лимит одновременных региональных анализов. Попробуй позже."
                )
            session = _Session(
                session_id=secrets.token_urlsafe(24),
                locator=normalized,
                radius_km=radius,
                started_at=current,
                finishes_at=current + duration,
                prefixes=frozenset(locator_prefixes_for_radius(normalized, radius)),
                duration_seconds=duration,
            )
            self._sessions[session.session_id] = session
            self._active_regions[key] = session.session_id
            return self._summary(session, current)

    def add_spot(self, spot: dict[str, Any], *, received_at: int | None = None) -> None:
        now = int(time.time()) if received_at is None else int(received_at)
        try:
            observed = int(spot.get("observed_at") or 0)
        except (TypeError, ValueError):
            return
        if observed < now - MAX_SPOT_AGE_SECONDS or observed > now + 300:
            return
        with self._lock:
            self._refresh(now)
            for session in tuple(self._sessions.values()):
                if session.completed_at is None and session.started_at <= now < session.finishes_at:
                    self._consume(session, spot, observed)

    def _consume(self, session: _Session, spot: dict[str, Any], observed: int) -> None:
        tx_grid, rx_grid = spot.get("tx_grid"), spot.get("rx_grid")
        def candidate(value: Any) -> bool:
            return not isinstance(value, str) or len(value.strip()) < 4 or value.strip().upper()[:4] in session.prefixes
        if not candidate(tx_grid) and not candidate(rx_grid):
            return
        band = str(spot.get("band") or "unknown").strip().lower()
        mode = str(spot.get("mode") or "UNKNOWN").strip().upper()
        key = (
            band, mode, spot.get("tx_call"), spot.get("rx_call"),
            str(tx_grid or "").upper(), str(rx_grid or "").upper(),
            spot.get("frequency_hz"), observed, spot.get("sequence"),
        )
        if key in session.seen:
            return
        session.seen[key] = None
        if len(session.seen) > MAX_DEDUPE_KEYS:
            session.seen.popitem(last=False)
        session.scanned += 1
        center = locator_to_center(session.locator)
        area = classify_spot_region(spot, session.locator, session.radius_km, center=center)
        accepted = False
        for direction, local, remote, stats in (
            ("tx", "tx", "rx", session.tx), ("rx", "rx", "tx", session.rx)
        ):
            if not area[f"{local}_in_area"]:
                continue
            accepted = True
            local_call = str(spot.get(f"{local}_call") or "").strip().upper()
            local_grid, remote_grid = spot.get(f"{local}_grid"), spot.get(f"{remote}_grid")
            remote_call = str(spot.get(f"{remote}_call") or "").strip().upper()
            stats.spots += 1
            stats.last_seen = max(stats.last_seen or 0, observed)
            band_stat = stats.bands.setdefault((band, mode), {"count": 0, "stations": set(), "last_seen": None})
            band_stat["count"] += 1
            if local_call:
                band_stat["stations"].add(local_call)
            band_stat["last_seen"] = max(band_stat["last_seen"] or 0, observed)
            station_key = local_call or (str(local_grid).strip().upper() if local_grid else "")
            if not station_key:
                continue
            station = stats.stations.get(station_key)
            if station is None:
                if len(stats.stations) >= MAX_STATIONS_PER_DIRECTION:
                    continue
                station = {"station_spots": 0, "observed_at_epoch": 0}
                stats.stations[station_key] = station
            station["station_spots"] += 1
            if observed <= station["observed_at_epoch"]:
                continue
            distance = bearing_deg = bearing = None
            route_distance = route_azimuth_deg = route_azimuth = None
            if isinstance(remote_grid, str) and remote_grid.strip():
                try:
                    remote_lat, remote_lon = locator_to_center(remote_grid)
                    distance = distance_between_locators(session.locator, remote_grid)
                    bearing_deg, bearing = _bearing(center[0], center[1], remote_lat, remote_lon)
                except (ValueError, TypeError):
                    pass
            if isinstance(local_grid, str) and local_grid.strip() and isinstance(remote_grid, str) and remote_grid.strip():
                try:
                    local_lat, local_lon = locator_to_center(local_grid)
                    remote_lat, remote_lon = locator_to_center(remote_grid)
                    route_distance = distance_between_locators(local_grid, remote_grid)
                    tx_lat, tx_lon = (local_lat, local_lon) if direction == "tx" else (remote_lat, remote_lon)
                    rx_lat, rx_lon = (remote_lat, remote_lon) if direction == "tx" else (local_lat, local_lon)
                    route_azimuth_deg, route_azimuth = _bearing(tx_lat, tx_lon, rx_lat, rx_lon)
                except (ValueError, TypeError):
                    pass
            station.update({
                "band": band, "mode": mode,
                "local_call": local_call or "Неизвестно", "local_grid": local_grid,
                "remote_call": remote_call or "Неизвестно", "remote_grid": remote_grid,
                "distance_km": round(distance, 1) if distance is not None else None,
                "local_distance_km": area[f"{local}_distance_km"],
                "bearing_degrees": bearing_deg, "bearing": bearing,
                "station_distance_km": round(route_distance, 1) if route_distance is not None else None,
                "station_azimuth_degrees": route_azimuth_deg, "station_azimuth": route_azimuth,
                "snr_db": spot.get("snr_db"), "frequency_hz": spot.get("frequency_hz"),
                "observed_at": _iso_utc(observed), "observed_at_epoch": observed,
            })
        if accepted:
            session.accepted += 1

    @staticmethod
    def _direction_result(stats: _Direction, *, offset: int = 0, limit: int = 10) -> dict[str, Any]:
        bands = [
            {"band": band, "mode": mode, "spots": value["count"],
             "stations": len(value["stations"]), "last_seen": _iso_utc(value["last_seen"])}
            for (band, mode), value in sorted(stats.bands.items())
        ]
        ordered = sorted(stats.stations.values(), key=lambda x: x["observed_at_epoch"], reverse=True)
        page = ordered[offset:offset + limit]
        visible = [{k: v for k, v in row.items() if k != "observed_at_epoch"} for row in page]
        return {
            "spots": stats.spots, "unique_local_stations": len(stats.stations),
            "last_seen": _iso_utc(stats.last_seen), "by_band": bands,
            "stations": visible, "latest": visible, "stations_total": len(ordered),
            "stations_total_all": len(ordered), "stations_offset": offset, "stations_limit": limit,
        }

    def get(self, session_id: str, *, now: int | None = None) -> dict[str, Any]:
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            self._refresh(current)
            session = self._sessions.get(session_id)
            if session is None:
                raise RegionalSessionError("Сессия не найдена или срок хранения результата истёк.")
            summary = self._summary(session, current)
            summary.update({"scanned_spots": session.scanned, "accepted_spots": session.accepted})
            if summary["state"] != "completed":
                return summary
            lat, lon = locator_to_center(session.locator)
            summary["report"] = {
                "locator": session.locator, "latitude": round(lat, 6), "longitude": round(lon, 6),
                "radius_km": session.radius_km, "period_seconds": session.duration_seconds,
                "session_id": session.session_id,
                "generated_at": _iso_utc(current), "period_started_at": _iso_utc(session.started_at),
                "stored_spots_scanned": session.scanned,
                "tx": self._direction_result(session.tx), "rx": self._direction_result(session.rx),
                "explanation": {
                    "tx": "Передатчики внутри области QTH были услышаны удалёнными приёмниками.",
                    "rx": "Приёмники внутри области QTH услышали удалённые передатчики.",
                    "distance": "Расстояния приблизительны и рассчитаны по центрам локаторов. Азимут радиотрассы направлен от передатчика к приёмнику.",
                },
            }
            return summary


    def cancel(self, session_id: str, *, now: int | None = None) -> dict[str, Any]:
        """Stop an active collection without producing a completed report."""
        current = int(time.time()) if now is None else int(now)
        with self._lock:
            self._refresh(current)
            session = self._sessions.get(session_id)
            if session is None:
                raise RegionalSessionError("Сессия не найдена или срок хранения результата истёк.")
            if session.completed_at is None:
                session.cancelled = True
                session.completed_at = current
                self._active_regions.pop(self._region_key(session.locator, session.radius_km), None)
            return self._summary(session, current)

    def get_stations(
        self, session_id: str, direction: str, *, offset: int = 0,
        limit: int = 10, now: int | None = None,
    ) -> dict[str, Any]:
        current = int(time.time()) if now is None else int(now)
        if direction not in {"tx", "rx"}:
            raise ValueError("Направление должно быть tx или rx.")
        if offset < 0 or limit < 1 or limit > 100:
            raise ValueError("Некорректные параметры страницы станций.")
        with self._lock:
            self._refresh(current)
            session = self._sessions.get(session_id)
            if session is None:
                raise RegionalSessionError("Сессия не найдена или срок хранения результата истёк.")
            if session.cancelled or current < session.finishes_at:
                raise RegionalSessionError("Результаты станций появятся после завершения сбора.")
            stats = session.tx if direction == "tx" else session.rx
            return self._direction_result(stats, offset=offset, limit=limit)

    def status(self) -> dict[str, int]:
        now = int(time.time())
        with self._lock:
            self._refresh(now)
            active = sum(s.completed_at is None for s in self._sessions.values())
            return {
                "active_sessions": active, "retained_results": len(self._sessions) - active,
                "max_active_sessions": self.max_active_sessions,
                "duration_seconds": self.duration_seconds,
            }
