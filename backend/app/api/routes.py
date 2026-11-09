from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.maidenhead import LocatorError, locator_to_center

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
