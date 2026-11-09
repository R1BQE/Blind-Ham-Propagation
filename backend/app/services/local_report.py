"""Geographic context derived from a Maidenhead locator."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.services.maidenhead import locator_to_center


def solar_position(latitude: float, longitude: float, moment: datetime) -> dict[str, Any]:
    """Approximate solar elevation and local mean solar time (NOAA equations).

    This is a geometric estimate, not a measured ionospheric condition.
    """
    utc = moment.astimezone(timezone.utc)
    day = utc.timetuple().tm_yday
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    gamma = 2 * 3.141592653589793 / 365 * (day - 1 + (hour - 12) / 24)

    equation_time = 229.18 * (
        0.000075 + 0.001868 * __import__("math").cos(gamma)
        - 0.032077 * __import__("math").sin(gamma)
        - 0.014615 * __import__("math").cos(2 * gamma)
        - 0.040849 * __import__("math").sin(2 * gamma)
    )
    declination = (
        0.006918 - 0.399912 * __import__("math").cos(gamma)
        + 0.070257 * __import__("math").sin(gamma)
        - 0.006758 * __import__("math").cos(2 * gamma)
        + 0.000907 * __import__("math").sin(2 * gamma)
        - 0.002697 * __import__("math").cos(3 * gamma)
        + 0.00148 * __import__("math").sin(3 * gamma)
    )
    true_solar_minutes = (hour * 60 + equation_time + 4 * longitude) % 1440
    hour_angle = true_solar_minutes / 4 - 180
    if hour_angle < -180:
        hour_angle += 360

    import math
    lat_rad = math.radians(latitude)
    ha_rad = math.radians(hour_angle)
    cosine_zenith = (
        math.sin(lat_rad) * math.sin(declination)
        + math.cos(lat_rad) * math.cos(declination) * math.cos(ha_rad)
    )
    elevation = 90 - math.degrees(math.acos(max(-1.0, min(1.0, cosine_zenith))))

    if elevation >= 0:
        daylight = "Солнце над горизонтом"
    elif elevation > -6:
        daylight = "Гражданские сумерки"
    elif elevation > -12:
        daylight = "Навигационные сумерки"
    elif elevation > -18:
        daylight = "Астрономические сумерки"
    else:
        daylight = "Ночь"

    local_minutes = (hour * 60 + longitude * 4) % 1440
    local_hour = int(local_minutes // 60)
    local_minute = int(local_minutes % 60)
    return {
        "solar_elevation_degrees": round(elevation, 2),
        "illumination": daylight,
        "local_mean_solar_time": f"{local_hour:02d}:{local_minute:02d}",
        "calculation": "Геометрическая оценка по координатам и UTC; не измерение ионосферы.",
    }


def build_local_report(locator: str, now: datetime | None = None) -> dict[str, Any]:
    latitude, longitude = locator_to_center(locator)
    moment = now or datetime.now(timezone.utc)
    return {
        "locator": locator.strip().upper(),
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "generated_at": moment.astimezone(timezone.utc).isoformat(),
        "solar": solar_position(latitude, longitude, moment),
        "interpretation": (
            "Локальная геометрия освещения помогает оценивать дневные и ночные "
            "условия. Для прогноза прохождения между двумя станциями потребуются "
            "модель трассы и координаты второй станции."
        ),
    }
