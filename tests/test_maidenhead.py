import pytest

from backend.app.services.maidenhead import LocatorError, locator_to_center


def test_two_character_locator_center():
    latitude, longitude = locator_to_center("KO")
    assert latitude == pytest.approx(55.0)
    assert longitude == pytest.approx(30.0)


def test_six_character_locator_center():
    latitude, longitude = locator_to_center("KO59XX")
    assert latitude == pytest.approx(59.9791666667)
    assert longitude == pytest.approx(31.9583333333)


def test_locator_is_case_insensitive_and_strips_whitespace():
    assert locator_to_center(" ko59xx ") == locator_to_center("KO59XX")


@pytest.mark.parametrize("locator", ["", "K", "KO5", "KO59X", "KO59XXXXXXX", "ZZ00"])
def test_invalid_locator_is_rejected(locator):
    with pytest.raises(LocatorError):
        locator_to_center(locator)


def test_invalid_character_is_rejected():
    with pytest.raises(LocatorError):
        locator_to_center("KO59!X")


@pytest.mark.parametrize(
    ("accuracy", "expected_length"),
    [(1200, 6), (300, 6), (10, 8), (0.2, 12), (None, 8)],
)
def test_coordinates_to_locator_selects_precision_from_accuracy(accuracy, expected_length):
    from backend.app.services.maidenhead import coordinates_to_locator

    locator, precision = coordinates_to_locator(59.94, 30.31, accuracy)
    assert len(locator) == expected_length
    assert precision == expected_length
    assert locator == locator.upper()


def test_coordinates_to_locator_returns_valid_grid():
    from backend.app.services.maidenhead import coordinates_to_locator

    locator, _ = coordinates_to_locator(59.94, 30.31, 10)
    latitude, longitude = locator_to_center(locator)
    assert abs(latitude - 59.94) < 0.001
    assert abs(longitude - 30.31) < 0.002


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 0), (-91, 0), (0, 181), (0, -181)],
)
def test_coordinates_to_locator_rejects_out_of_range_coordinates(latitude, longitude):
    from backend.app.services.maidenhead import coordinates_to_locator

    with pytest.raises(LocatorError):
        coordinates_to_locator(latitude, longitude, 10)
