import os

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.app.services.drap import get_drap
from backend.app.services.local_report import build_local_report
from backend.app.services.maidenhead import LocatorError, locator_to_center
from backend.app.services.noaa import get_space_weather

router = APIRouter()


class LocatorRequest(BaseModel):
    locator: str = Field(min_length=2, max_length=12, examples=["KO59XX"])


class LocatorResponse(BaseModel):
    locator: str
    latitude: float
    longitude: float


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
