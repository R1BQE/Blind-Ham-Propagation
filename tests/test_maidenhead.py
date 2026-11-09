import pytest

from backend.app.services.maidenhead import LocatorError, locator_to_center


def test_two_character_locator_center():
    latitude, longitude = locator_to_center("KO")
    assert latitude == pytest.approx(-5.0)
    assert longitude == pytest.approx(30.0)


def test_six_character_locator_center():
    latitude, longitude = locator_to_center("KO59XX")
    assert latitude == pytest.approx(59.9791666667)
    assert longitude == pytest.approx(30.9583333333)


def test_locator_is_case_insensitive_and_strips_whitespace():
    assert locator_to_center(" ko59xx ") == locator_to_center("KO59XX")


@pytest.mark.parametrize("locator", ["", "K", "KO5", "KO59X", "KO59XXXXXXX", "ZZ00"])
def test_invalid_locator_is_rejected(locator):
    with pytest.raises(LocatorError):
        locator_to_center(locator)


def test_invalid_character_is_rejected():
    with pytest.raises(LocatorError):
        locator_to_center("KO59!X")
