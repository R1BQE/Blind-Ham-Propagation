"""NOAA D-RAP global HF absorption-frequency grid parser."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

DRAP_URL = "https://services.swpc.noaa.gov/text/drap_global_frequencies.txt"


def parse_drap_text(payload: str) -> dict[str, Any]:
    """Parse NOAA's tabular D-RAP product into a latitude/longitude grid."""
    valid_at = None
    xray_message = None
    proton_message = None
    longitudes: list[float] = []
    grid: dict[float, list[float | None]] = {}

    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# Product Valid At :"):
            valid_at = line.split(":", 1)[1].strip()
            continue
        if line.startswith("#  X-RAY Message :"):
            xray_message = line.split(":", 1)[1].strip()
            continue
        if line.startswith("#  Proton Message :"):
            proton_message = line.split(":", 1)[1].strip()
            continue
        if line.startswith("#") or set(line) <= {"-"}:
            continue

        parts = line.split()
        if not longitudes:
            try:
                candidate = [float(value) for value in parts]
            except ValueError:
                continue
            if len(candidate) > 20 and min(candidate) >= -180 and max(candidate) <= 180:
                longitudes = candidate
            continue

        try:
            latitude = float(parts[0])
            values = [float(value) for value in parts[1:]]
        except (ValueError, IndexError):
            continue
        if len(values) != len(longitudes):
            continue
        grid[latitude] = values

    if not longitudes or not grid:
        raise ValueError("NOAA D-RAP returned an unrecognized or empty grid")

    return {
        "valid_at": valid_at,
        "xray_message": xray_message,
        "proton_message": proton_message,
        "latitudes": sorted(grid, reverse=True),
        "longitudes": longitudes,
        "grid": grid,
    }


def lookup_drap_cell(data: dict[str, Any], latitude: float, longitude: float) -> dict[str, Any]:
    """Return the nearest published D-RAP grid cell (not an interpolation)."""
    latitudes = data["latitudes"]
    longitudes = data["longitudes"]
    lat = min(latitudes, key=lambda value: abs(value - latitude))
    # Account for the longitude wrap at the date line.
    lon = min(longitudes, key=lambda value: abs((value - longitude + 180) % 360 - 180))
    column = longitudes.index(lon)
    value = data["grid"][lat][column]
    return {
        "latitude": lat,
        "longitude": lon,
        "frequency_mhz": value,
        "meaning": "Highest frequency with estimated 1 dB D-region absorption",
    }


async def get_drap(latitude: float | None = None, longitude: float | None = None) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "Blind-Ham-Propagation/0.1"}) as client:
        response = await client.get(DRAP_URL)
        response.raise_for_status()
    data = parse_drap_text(response.text)
    result: dict[str, Any] = {
        "source": "NOAA SWPC D-RAP",
        "source_url": "https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap",
        "data_url": DRAP_URL,
        "retrieved_at": retrieved_at,
        "valid_at": data["valid_at"],
        "xray_message": data["xray_message"],
        "proton_message": data["proton_message"],
        "grid_resolution_degrees": {"latitude": 2, "longitude": 4},
        "description": (
            "Модельная оценка максимальной частоты (МГц), для которой ожидается "
            "поглощение не менее 1 дБ в D-области. Это не измерение качества связи "
            "и не прогноз MUF."
        ),
    }
    if latitude is not None and longitude is not None:
        result["nearest_cell"] = lookup_drap_cell(data, latitude, longitude)
    return result
