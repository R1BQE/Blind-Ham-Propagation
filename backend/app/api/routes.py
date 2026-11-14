import configparser
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.app.services.drap import get_drap
from backend.app.services.hamqsl import get_hamqsl_data
from backend.app.services.local_report import build_local_report
from backend.app.services.maidenhead import (
    LocatorError,
    coordinates_to_locator,
    locator_to_center,
)
from backend.app.services.noaa import get_space_weather
from backend.app.services.regional_report import build_regional_report
from backend.app.services.spot_store import SpotStore

router = APIRouter()
SETTINGS_PATH = Path(__file__).resolve().parents[3] / "settings.ini"


class LocatorRequest(BaseModel):
    locator: str = Field(min_length=2, max_length=12, examples=["KO59XX"])


class LocatorResponse(BaseModel):
    locator: str
    latitude: float
    longitude: float


class CoordinatesRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, gt=0, le=100_000)



@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "blind-ham-propagation"}


@router.get("/psk-reporter/status")
async def psk_reporter_status(request: Request) -> dict:
    """Return MQTT collector connection and bounded-storage counters."""
    collector = getattr(request.app.state, "psk_reporter_collector", None)
    if collector is None:
        return {"enabled": False, "state": "not_started"}
    return collector.status()


@router.get("/psk-reporter/regional")
async def psk_reporter_regional(
    request: Request,
    locator: str = Query(default="KP50DB", min_length=2, max_length=12),
    radius_km: float = Query(default=100.0, gt=0, le=1000),
    hours: int = Query(default=6, ge=3, le=24),
    limit: int = Query(default=30, ge=1, le=100),
    bands: str | None = Query(default=None),
    modes: str | None = Query(default=None),
) -> dict:
    """Return independent TX/RX PSK Reporter statistics around a QTH."""
    collector = getattr(request.app.state, "psk_reporter_collector", None)
    store = getattr(collector, "store", None) if collector is not None else None
    try:
        return build_regional_report(
            locator,
            radius_km,
            hours,
            store=store or SpotStore(),
            details_limit=limit,
            bands=[value for value in (bands or "").split(",") if value],
            modes=[value for value in (modes or "").split(",") if value],
        )
    except LocatorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/locator/validate", response_model=LocatorResponse)
async def validate_locator(payload: LocatorRequest) -> LocatorResponse:
    try:
        latitude, longitude = locator_to_center(payload.locator)
    except LocatorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LocatorResponse(
        locator=payload.locator.strip().upper(),
        latitude=round(latitude, 6),
        longitude=round(longitude, 6),
    )




@router.get("/config/public")
async def public_config() -> dict[str, str | bool]:
    """Return browser-facing configuration; the Yandex JS key is public by design."""
    parser = configparser.ConfigParser()
    if SETTINGS_PATH.exists():
        parser.read(SETTINGS_PATH, encoding="utf-8")
    key = os.getenv("YANDEX_MAPS_JS_API_KEY", "").strip()
    if not key and parser.has_section("yandex_maps"):
        key = parser.get("yandex_maps", "javascript_api_key", fallback="").strip()
    return {
        "yandex_maps_enabled": bool(key),
        "yandex_maps_api_key": key,
    }


@router.post("/locator/from-coordinates")
async def locator_from_coordinates(payload: CoordinatesRequest) -> dict[str, float | str | int]:
    """Convert browser/device coordinates into a Maidenhead locator."""
    try:
        locator, precision = coordinates_to_locator(
            payload.latitude,
            payload.longitude,
            payload.accuracy_m,
        )
    except LocatorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "locator": locator,
        "precision": precision,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "accuracy_m": payload.accuracy_m,
    }

@router.get("/solar/activity")
async def solar_activity() -> dict:
    """Global solar and geomagnetic measurements; no QTH is required."""
    report = await get_space_weather()
    try:
        report["drap"] = await get_drap()
    except Exception as exc:
        report.setdefault("errors", {})["drap"] = (
            f"Источник D-RAP временно недоступен: {type(exc).__name__}"
        )
        report["status"] = "partial"
    try:
        report["hamqsl"] = await get_hamqsl_data()
    except Exception as exc:
        report.setdefault("errors", {})["hamqsl"] = (
            f"Источник HamQSL временно недоступен: {type(exc).__name__}"
        )
        report["status"] = "partial"
    return report


@router.get("/local/report")
async def local_report(locator: str = Query(min_length=2, max_length=12)) -> dict:
    """Geographic and solar-illumination context for a Maidenhead locator."""
    try:
        report = build_local_report(locator)
        latitude, longitude = locator_to_center(locator)
    except LocatorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        report["drap"] = await get_drap(latitude, longitude)
    except Exception as exc:
        report["drap"] = {
            "status": "unavailable",
            "error": f"Источник D-RAP временно недоступен: {type(exc).__name__}",
        }
    return report


# Local browser lifecycle endpoints are deliberately absent from production.
if os.environ.get("BLIND_HAM_LOCAL_SESSION") == "1":
    from backend.app.services.local_session import (
        session_connected,
        session_disconnected,
    )

    @router.get("/local-session")
    async def local_session_capability() -> dict[str, bool]:
        return {"enabled": True}

    @router.websocket("/local-session")
    async def local_session_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        connection_id = id(websocket)
        session_connected(connection_id)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await session_disconnected(websocket.app, connection_id)
