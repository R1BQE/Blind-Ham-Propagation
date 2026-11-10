from datetime import datetime, timezone

import pytest

from backend.app.services.psk_reporter import (
    SpotFormatError,
    parse_spot,
    spot_freshness,
)


TOPIC = "pskr/filter/v2/20m/FT8/R1BQE/W1ABC/KO59XX/FN31pr/54/291"
PAYLOAD = (
    '{"sq":30142870791,"f":14074653,"md":"FT8","rp":-5,'
    '"t":1794254400,"t_tx":1794254388,"sc":"R1BQE",'
    '"sl":"KO59XX","rc":"W1ABC","rl":"FN31pr","sa":54,"ra":291,"b":"20m"}'
)


def test_parse_spot_combines_topic_and_payload():
    spot = parse_spot(TOPIC, PAYLOAD)

    assert spot["band"] == "20m"
    assert spot["mode"] == "FT8"
    assert spot["tx_call"] == "R1BQE"
    assert spot["rx_call"] == "W1ABC"
    assert spot["tx_grid"] == "KO59XX"
    assert spot["rx_grid"] == "FN31pr"
    assert spot["frequency_hz"] == 14074653
    assert spot["snr_db"] == -5.0
    assert spot["observed_at"] == 1794254388


def test_parse_spot_prefers_full_locators_from_json_payload():
    topic = "pskr/filter/v2/20m/FT8/R1BQE/W1ABC/KO59/FN31/54/291"
    spot = parse_spot(topic, PAYLOAD)

    assert spot["tx_grid"] == "KO59XX"
    assert spot["rx_grid"] == "FN31pr"


def test_parse_spot_falls_back_to_topic_locators_when_payload_has_none():
    topic = "pskr/filter/v2/20m/FT8/R1BQE/W1ABC/KO59/FN31/54/291"
    spot = parse_spot(topic, '{"f":14074653,"t":1794254400}')

    assert spot["tx_grid"] == "KO59"
    assert spot["rx_grid"] == "FN31"
    assert spot["observed_at"] == 1794254400
    assert spot["tx_started_at"] is None


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        ("invalid/topic", "{}"),
        (TOPIC, "not-json"),
        (TOPIC, "[]"),
        (TOPIC, '{"t":"bad","f":14074653}'),
    ],
)
def test_parse_spot_rejects_invalid_messages(topic, payload):
    with pytest.raises(SpotFormatError):
        parse_spot(topic, payload)


def test_spot_freshness_uses_normalized_observation_timestamp():
    now = datetime.fromtimestamp(1794255000, tz=timezone.utc)
    spot = {"observed_at": 1794254400}

    result = spot_freshness(spot, now=now)

    assert result["status"] == "fresh"
    assert result["age_seconds"] == 600
    assert result["observed_at_utc"].endswith("+00:00")


def test_spot_freshness_marks_old_spot_stale():
    now = datetime.fromtimestamp(1794260000, tz=timezone.utc)
    assert spot_freshness({"observed_at": 1794250000}, now=now)["status"] == "stale"
