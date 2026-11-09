from backend.app.services.noaa import _latest, _number, _rows


def test_normalizes_object_rows():
    rows = _rows([{"time_tag": "2026-01-01T00:00:00Z", "Kp": 2.0}])
    assert _number(_latest(rows), "Kp") == 2.0


def test_normalizes_legacy_header_rows():
    rows = _rows([["time_tag", "Kp"], ["2026-01-01T00:00:00Z", "3.0"]])
    assert _number(_latest(rows), "Kp") == 3.0


def test_empty_payload_is_empty():
    assert _rows([]) == []
