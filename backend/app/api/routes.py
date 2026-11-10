import asyncio
import os

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.app.services.drap import get_drap
from backend.app.services.local_report import build_local_report
from backend.app.services.maidenhead import LocatorError, locator_to_center
from backend.app.services.noaa import get_space_weather
from backend.app.services.regional_report import build_regional_report
from backend.app.services.spot_store import SpotStore

router = APIRouter()


class LocatorRequest(BaseModel):
    locator: str = Field(min_length=2, max_length=12, examples=["KO59XX"])


class LocatorResponse(BaseModel):
    locator: str
    latitude: float
    longitude: float


class PSKSubscriptionRequest(BaseModel):
    bands: list[str] = Field(min_length=1, max_length=13)
    modes: list[str] = Field(min_length=1, max_length=12)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "blind-ham-propagation"}


@router.websocket("/psk-reporter/session")
async def psk_reporter_session(websocket: WebSocket) -> None:
    """Keep the shared collector active while at least one viewer is connected."""
    await websocket.accept()
    sessions = getattr(websocket.app.state, "psk_reporter_sessions", None)
    if sessions is None:
        await websocket.close(code=1011, reason="PSK Reporter session manager unavailable")
        return
    connection_id = id(websocket)
    await sessions.connect(connection_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await sessions.disconnect(connection_id)


@router.get("/psk-reporter/status")
async def psk_reporter_status(request: Request) -> dict:
    """Return MQTT collector connection and bounded-storage counters."""
    collector = getattr(request.app.state, "psk_reporter_collector", None)
    if collector is None:
        return {"enabled": False, "state": "not_started"}
    return collector.status()


@router.post("/psk-reporter/subscriptions")
async def update_psk_reporter_subscriptions(
    payload: PSKSubscriptionRequest,
    request: Request,
) -> dict:
    """Apply selected bands and modes to the live shared MQTT collector."""
    collector = getattr(request.app.state, "psk_reporter_collector", None)
    if collector is None:
        raise HTTPException(status_code=503, detail="Сборщик PSK Reporter недоступен.")
    try:
        topics = await asyncio.to_thread(
            collector.set_filters, payload.bands, payload.modes
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "bands": list(dict.fromkeys(value.strip().lower() for value in payload.bands)),
        "modes": list(dict.fromkeys(value.strip().upper() for value in payload.modes)),
        "topic_filters": list(topics),
    }


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
