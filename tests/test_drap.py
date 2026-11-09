from backend.app.services.drap import lookup_drap_cell, parse_drap_text


SAMPLE = """# DRAP Tabular Values
# Product Valid At : 2026-11-09 20:17 UTC
#  X-RAY Message : Normal X-ray Background
#  Proton Message : Elevated Proton Background
  -2   2   6
----------------
  61 | 0.0  0.5  1.0
  59 | 0.2  0.8  1.4
"""


def test_parse_drap_grid_and_metadata():
    data = parse_drap_text(SAMPLE)
    assert data["valid_at"] == "2026-11-09 20:17 UTC"
    assert data["xray_message"] == "Normal X-ray Background"
    assert data["proton_message"] == "Elevated Proton Background"
    assert data["grid"][59.0] == [0.2, 0.8, 1.4]


def test_lookup_uses_nearest_grid_cell():
    data = parse_drap_text(SAMPLE)
    cell = lookup_drap_cell(data, 59.4, 3.7)
    assert cell["latitude"] == 59.0
    assert cell["longitude"] == 2.0
    assert cell["frequency_mhz"] == 0.8


def test_invalid_drap_payload_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        parse_drap_text("NO DATA")
