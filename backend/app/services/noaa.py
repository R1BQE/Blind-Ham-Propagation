"""NOAA SWPC public JSON data collector.

Each product is fetched independently: a temporary outage in one feed must not
hide the other measurements. NOAA changed several JSON formats in 2026, so
this module accepts both object rows and the older header/value representation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

BASE = "https://services.swpc.noaa.gov"
PRODUCTS = {
    "solar_flux": f"{BASE}/products/summary/10cm-flux.json",
    "kp": f"{BASE}/products/noaa-planetary-k-index.json",
    "wind_speed": f"{BASE}/products/summary/solar-wind-speed.json",
    "magnetic_field": f"{BASE}/products/summary/solar-wind-mag-field.json",
    "xray": f"{BASE}/json/goes/primary/xrays-6-hour.json",
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    """Normalize NOAA JSON arrays, including legacy [header, values...] data."""
    if not isinstance(payload, list) or not payload:
        return []
    if isinstance(payload[0], dict):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload[0], list) and payload[0] and all(
        isinstance(item, str) for item in payload[0]
    ):
        keys = payload[0]
        return [
            dict(zip(keys, row))
            for row in payload[1:]
            if isinstance(row, list)
        ]
    return []


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: str(row.get("time_tag", "")))


def _number(row: dict[str, Any] | None, *keys: str) -> float | None:
    if not row:
        return None
    for key in keys:
        value = row.get(key)
        try:
            if value is not None and value != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _timestamp(row: dict[str, Any] | None) -> str | None:
    return str(row["time_tag"]) if row and row.get("time_tag") else None


async def get_space_weather() -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "Blind-Ham-Propagation/0.1"}) as client:
        async def fetch(name: str, url: str) -> None:
            try:
                response = await client.get(url)
                response.raise_for_status()
                results[name] = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                errors[name] = f"Источник временно недоступен: {type(exc).__name__}"

        import asyncio
        await asyncio.gather(*(fetch(name, url) for name, url in PRODUCTS.items()))

    flux_row = _latest(_rows(results.get("solar_flux")))
    kp_rows = _rows(results.get("kp"))
    kp_row = _latest(kp_rows)
    speed_row = _latest(_rows(results.get("wind_speed")))
    mag_row = _latest(_rows(results.get("magnetic_field")))

    xray_rows = _rows(results.get("xray"))
    xray_row = next(
        (row for row in reversed(xray_rows)
         if "0.1-0.8" in str(row.get("energy", ""))),
        _latest(xray_rows),
    )

    measurements = {
        "solar_flux": {"value": _number(flux_row, "flux", "f107"), "unit": "sfu", "observed_at": _timestamp(flux_row)},
        "kp": {"value": _number(kp_row, "Kp", "kp"), "unit": "", "observed_at": _timestamp(kp_row)},
        "solar_wind_speed": {"value": _number(speed_row, "proton_speed", "speed"), "unit": "km/s", "observed_at": _timestamp(speed_row)},
        "magnetic_field_bt": {"value": _number(mag_row, "bt"), "unit": "nT", "observed_at": _timestamp(mag_row)},
        "magnetic_field_bz": {"value": _number(mag_row, "bz_gsm", "bz"), "unit": "nT", "observed_at": _timestamp(mag_row)},
        "xray_flux": {"value": _number(xray_row, "flux"), "unit": "W/m²", "observed_at": _timestamp(xray_row)},
    }

    return {
        "source": "NOAA Space Weather Prediction Center",
        "source_url": "https://www.swpc.noaa.gov/",
        "retrieved_at": retrieved_at,
        "measurements": measurements,
        "kp_history": [
            {"observed_at": row.get("time_tag"), "value": _number(row, "Kp", "kp")}
            for row in kp_rows[-8:]
        ],
        "errors": errors,
        "status": "partial" if errors else "ok",
    }
