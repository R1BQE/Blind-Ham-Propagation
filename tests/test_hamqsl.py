from backend.app.services.hamqsl import parse_solar_xml


def test_parse_solar_xml_preserves_values_attributes_and_repeated_rows():
    xml = """<?xml version="1.0"?>
    <solar>
      <solardata>
        <solarflux>128.4</solarflux>
        <kindex>2</kindex>
        <muf>28.1</muf>
        <calculatedconditions>
          <band name="80m-40m" time="day">Good</band>
          <band name="80m-40m" time="night">Fair</band>
        </calculatedconditions>
      </solardata>
    </solar>"""
    data = parse_solar_xml(xml)["solardata"]
    assert data["solarflux"] == "128.4"
    assert data["kindex"] == "2"
    assert data["muf"] == "28.1"
    assert data["calculatedconditions"]["band"] == [
        {"@name": "80m-40m", "@time": "day", "#text": "Good"},
        {"@name": "80m-40m", "@time": "night", "#text": "Fair"},
    ]


def test_parse_solar_xml_rejects_invalid_xml():
    import pytest
    with pytest.raises(ValueError, match="некорректный XML"):
        parse_solar_xml("<solar>")
