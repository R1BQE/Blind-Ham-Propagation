"""Maidenhead grid locator validation and center-coordinate conversion."""

from __future__ import annotations


class LocatorError(ValueError):
    """Raised when a Maidenhead locator is malformed."""


def locator_to_center(locator: str) -> tuple[float, float]:
    """Return (latitude, longitude) at the center of a 2- to 12-character locator.

    Supported precision levels are 2, 4, 6, 8, 10 and 12 characters.
    The function accepts lower- and upper-case letters and ignores surrounding
    whitespace. It does not guess or repair malformed locators.
    """
    value = locator.strip().upper()

    if len(value) not in (2, 4, 6, 8, 10, 12):
        raise LocatorError("Локатор должен содержать 2, 4, 6, 8, 10 или 12 символов.")

    longitude = -180.0
    latitude = -90.0
    longitude_size = 360.0
    latitude_size = 180.0

    for pair_index in range(len(value) // 2):
        first = value[pair_index * 2]
        second = value[pair_index * 2 + 1]

        if pair_index == 0:
            max_letter = 17
        elif pair_index % 2 == 0:
            max_letter = 23
        else:
            max_letter = 9

        if pair_index % 2 == 0:
            if not ("A" <= first <= chr(ord("A") + max_letter)):
                raise LocatorError(
                    f"Недопустимый символ «{first}» в позиции {pair_index * 2 + 1}."
                )
            if not ("A" <= second <= chr(ord("A") + max_letter)):
                raise LocatorError(
                    f"Недопустимый символ «{second}» в позиции {pair_index * 2 + 2}."
                )
            first_value = ord(first) - ord("A")
            second_value = ord(second) - ord("A")
            divisor = 18 if pair_index == 0 else 24
        else:
            if not first.isdigit() or not second.isdigit():
                raise LocatorError(
                    f"В позициях {pair_index * 2 + 1} и {pair_index * 2 + 2} "
                    "должны находиться цифры."
                )
            first_value = int(first)
            second_value = int(second)
            divisor = 10

        longitude_size /= divisor
        latitude_size /= divisor
        longitude += first_value * longitude_size
        latitude += second_value * latitude_size

    return (
        latitude + latitude_size / 2,
        longitude + longitude_size / 2,
    )



def coordinates_to_locator(
    latitude: float,
    longitude: float,
    accuracy_m: float | None = None,
) -> tuple[str, int]:
    """Convert coordinates to a Maidenhead locator and select useful precision.

    GPS accuracy is a radius in metres. The selected precision avoids implying
    metre-level certainty when the position source is less accurate.
    """
    import math

    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise LocatorError("Широта должна находиться в диапазоне от -90 до 90.")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise LocatorError("Долгота должна находиться в диапазоне от -180 до 180.")
    if accuracy_m is not None and (
        not math.isfinite(accuracy_m) or accuracy_m <= 0
    ):
        raise LocatorError("Точность координат должна быть положительным числом.")

    accuracy = accuracy_m if accuracy_m is not None else 100.0
    # Pick the longest cell whose half-width in the narrower direction is
    # at least the reported position error. Longitude cells shrink toward poles.
    precision = 6
    for candidate in (6, 8, 10, 12):
        candidate_lon_size = 360.0
        candidate_lat_size = 180.0
        for pair_index in range(candidate // 2):
            divisor = 18 if pair_index == 0 else (10 if pair_index % 2 else 24)
            candidate_lon_size /= divisor
            candidate_lat_size /= divisor
        latitude_cell_m = candidate_lat_size * 111_320.0
        longitude_cell_m = (
            candidate_lon_size * 111_320.0 * abs(math.cos(math.radians(latitude)))
        )
        narrow_half_cell_m = min(latitude_cell_m, longitude_cell_m) / 2
        if accuracy <= narrow_half_cell_m:
            precision = candidate
        else:
            break

    lon = min(longitude, 180.0 - 1e-10) + 180.0
    lat = min(latitude, 90.0 - 1e-10) + 90.0
    lon_size = 360.0
    lat_size = 180.0
    result = []

    for pair_index in range(precision // 2):
        if pair_index == 0:
            divisor = 18
        elif pair_index % 2:
            divisor = 10
        else:
            divisor = 24

        lon_size /= divisor
        lat_size /= divisor
        lon_index = min(int(lon / lon_size), divisor - 1)
        lat_index = min(int(lat / lat_size), divisor - 1)
        if pair_index % 2 == 0:
            result.append(chr(ord("A") + lon_index))
            result.append(chr(ord("A") + lat_index))
        else:
            result.append(str(lon_index))
            result.append(str(lat_index))
        lon -= lon_index * lon_size
        lat -= lat_index * lat_size

    locator = "".join(result)
    return locator, precision
