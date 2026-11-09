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
