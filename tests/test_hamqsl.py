from backend.app.services.hamqsl import CACHE_TTL_SECONDS, parse_solar_xml


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


def test_hamqsl_cache_ttl_is_one_hour():
    assert CACHE_TTL_SECONDS == 60 * 60


def test_parse_captured_live_hamqsl_xml():
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "hamqsl-live-2026-11-12.xml"
    data = parse_solar_xml(fixture.read_text(encoding="utf-8"))["solardata"]

    assert data["source"] == {
        "@url": "http://www.hamqsl.com/solar.html",
        "#text": "N0NBH",
    }
    assert data["updated"] == "12 Nov 2026 0134 GMT"
    assert data["solarflux"] == "132"
    assert data["electonflux"] == "2560"
    assert data["magneticfield"] == "1.3"
    assert data["kindexnt"] == "No Report"
    assert data["fof2"] == ""
    assert data["muffactor"] == ""
    assert data["muf"] == "NoRpt"

    bands = data["calculatedconditions"]["band"]
    assert len(bands) == 8
    assert bands[0] == {
        "@name": "80m-40m",
        "@time": "day",
        "#text": "Fair",
    }
    assert bands[-1] == {
        "@name": "12m-10m",
        "@time": "night",
        "#text": "Poor",
    }

    phenomena = data["calculatedvhfconditions"]["phenomenon"]
    assert len(phenomena) == 5
    assert phenomena[0] == {
        "@name": "vhf-aurora",
        "@location": "northern_hemi",
        "#text": "Band Closed",
    }
    assert phenomena[-1] == {
        "@name": "E-Skip",
        "@location": "europe_4m",
        "#text": "Band Closed",
    }
