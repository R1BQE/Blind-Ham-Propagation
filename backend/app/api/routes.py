import os

from fastapi import APIRouter, HTTPException, Query, Request
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


# These endpoints exist only in the Windows local runner. They are deliberately
# absent from the public VDS application, so a browser cannot stop production.
if os.environ.get("BLIND_HAM_LOCAL_SESSION") == "1":
    from backend.app.services.local_session import (
        heartbeat as local_heartbeat,
        request_shutdown_after_page_close,
    )

    @router.post("/local-session/heartbeat")
    async def local_session_heartbeat() -> dict[str, bool]:
        local_heartbeat()
        return {"enabled": True}

    @router.post("/local-session/close")
    async def local_session_close(request: Request) -> dict[str, bool]:
        await request_shutdown_after_page_close(request.app)
        return {"shutdown_scheduled": True}
