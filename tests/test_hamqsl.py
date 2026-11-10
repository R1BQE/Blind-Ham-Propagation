from backend.app.services.hamqsl import parse_solar_xml


def test_parse_solar_xml_preserves_values_attributes_and_repeated_rows():
    xml = """<?xml version="1.0"?>
    <solar>
      <solardata>
        <solarflux>128.4</solarflux>
        <kindex>2</kindex>
        <muf>28.1</muf>
        <band name="20m"><time name="day">Good</time></band>
        <band name="20m"><time name="night">Fair</time></band>
      </solardata>
    </solar>"""
    data = parse_solar_xml(xml)["solardata"]
    assert data["solarflux"] == "128.4"
    assert data["kindex"] == "2"
    assert data["muf"] == "28.1"
    assert data["band"] == [
        {"@name": "20m", "time": {"@name": "day", "#text": "Good"}},
        {"@name": "20m", "time": {"@name": "night", "#text": "Fair"}},
    ]


def test_parse_solar_xml_rejects_invalid_xml():
    import pytest
    with pytest.raises(ValueError, match="некорректный XML"):
        parse_solar_xml("<solar>")
