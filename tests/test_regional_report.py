import pytest

from backend.app.services.regional_report import build_regional_report


class MemoryStore:
    def __init__(self, spots):
        self.spots = spots

    def list_recent(self, *, now=None, limit=1000, band=None):
        rows = list(self.spots)
        if band is not None:
            rows = [row for row in rows if row["band"] == band]
        return rows[:limit]


def spot(tx_call, rx_call, tx_grid, rx_grid, observed_at=10_000, **extra):
    row = {
        "band": "20m",
        "mode": "FT8",
        "tx_call": tx_call,
        "rx_call": rx_call,
        "tx_grid": tx_grid,
        "rx_grid": rx_grid,
        "frequency_hz": 14_074_000,
        "snr_db": -10.0,
        "observed_at": observed_at,
    }
    row.update(extra)
    return row


def test_regional_report_keeps_tx_and_rx_directions_separate():
    store = MemoryStore([
        spot("R1BQE", "W1ABC", "KO59XX", "FN31PR"),
        spot("W1ABC", "R1BQE", "FN31PR", "KO59XX", observed_at=9_999),
        spot("R2ABC", "R3ABC", "KO59XW", "KO59WW", observed_at=9_998),
    ])

    report = build_regional_report("KO59XX", store=store, now=10_100)

    assert report["tx"]["spots"] == 2
    assert report["rx"]["spots"] == 2
    assert report["tx"]["unique_local_stations"] == 2
    assert report["rx"]["unique_local_stations"] == 2
    assert report["tx"]["latest"][0]["local_call"] == "R1BQE"
    assert report["tx"]["latest"][0]["remote_call"] == "W1ABC"
    assert report["rx"]["latest"][0]["local_call"] == "R1BQE"
    assert report["rx"]["latest"][0]["remote_call"] == "W1ABC"


def test_spot_can_contribute_to_both_directions_when_both_ends_are_local():
    store = MemoryStore([spot("R1BQE", "R2ABC", "KO59XX", "KO59XW")])

    report = build_regional_report("KO59XX", store=store, now=10_100)

    assert report["tx"]["spots"] == 1
    assert report["rx"]["spots"] == 1


def test_invalid_or_missing_local_locator_is_not_counted():
    store = MemoryStore([
        spot("N0CALL", "W1ABC", None, "FN31PR"),
        spot("N0CALL", "W1ABC", "INVALID", "FN31PR", observed_at=9_999),
    ])

    report = build_regional_report("KO59XX", store=store, now=10_100)

    assert report["tx"]["spots"] == 0
    assert report["rx"]["spots"] == 0


def test_report_excludes_spots_outside_selected_time_window():
    store = MemoryStore([
        spot("R1BQE", "W1ABC", "KO59XX", "FN31PR", observed_at=1_000),
        spot("R1BQE", "W1ABC", "KO59XX", "FN31PR", observed_at=9_900),
    ])

    report = build_regional_report("KO59XX", hours=3, store=store, now=20_000)

    assert report["tx"]["spots"] == 1


def test_report_contains_bearing_distance_and_band_summary():
    store = MemoryStore([spot("R1BQE", "W1ABC", "KO59XX", "FN31PR")])

    report = build_regional_report("KO59XX", store=store, now=10_100)
    latest = report["tx"]["latest"][0]

    assert latest["distance_km"] > 100
    assert latest["local_distance_km"] == 0.0
    assert latest["bearing"] is not None
    assert latest["bearing_degrees"] is not None
    assert latest["station_distance_km"] > 100
    assert latest["station_azimuth"] is not None
    assert latest["station_azimuth_degrees"] is not None
    assert report["tx"]["by_band"] == [{
        "band": "20m",
        "mode": "FT8",
        "spots": 1,
        "stations": 1,
        "last_seen": "1970-01-01T02:46:40+00:00",
    }]


def test_regional_report_filters_selected_bands_and_modes():
    store = MemoryStore([
        spot("R1BQE", "W1ABC", "KO59XX", "FN31PR"),
        spot("R1BQE", "W2ABC", "KO59XX", "FN32PR", band="40m", mode="FT4"),
        spot("R1BQE", "W3ABC", "KO59XX", "FN33PR", band="40m", mode="FT8"),
    ])

    report = build_regional_report(
        "KO59XX",
        bands=["40m"],
        modes=["FT4"],
        store=store,
        now=10_100,
    )

    assert report["tx"]["spots"] == 1
    assert report["tx"]["by_band"][0]["band"] == "40m"
    assert report["tx"]["by_band"][0]["mode"] == "FT4"
    assert report["bands"] == ["40m"]
    assert report["modes"] == ["FT4"]


def test_invalid_radius_is_rejected_even_when_store_is_empty():
    store = MemoryStore([])
    with pytest.raises(ValueError, match="Радиус"):
        build_regional_report("KO59XX", radius_km=0, store=store, now=10_100)



def test_regional_report_accepts_periods_up_to_24_hours():
    store = MemoryStore([])
    report = build_regional_report("KO59XX", hours=24, store=store, now=10_000)
    assert report["period_hours"] == 24


def test_regional_report_rejects_period_outside_selector_values():
    store = MemoryStore([])
    with pytest.raises(ValueError, match="шагом 3 часа"):
        build_regional_report("KO59XX", hours=7, store=store, now=10_000)



def test_radio_path_azimuth_is_always_from_transmitter_to_receiver():
    store = MemoryStore([
        spot("R1BQE", "W1ABC", "KO59XX", "FN31PR", observed_at=10_000),
        spot("W1ABC", "R1BQE", "FN31PR", "KO59XX", observed_at=9_999),
    ])
    report = build_regional_report("KO59XX", store=store, now=10_100)
    tx_item = report["tx"]["latest"][0]
    rx_item = report["rx"]["latest"][0]

    assert tx_item["station_distance_km"] == rx_item["station_distance_km"]
    assert tx_item["station_azimuth_degrees"] == pytest.approx(304.5)
    assert rx_item["station_azimuth_degrees"] == pytest.approx(33.5)
    assert tx_item["station_azimuth"] == "СЗ"
    assert rx_item["station_azimuth"] == "ССВ"
    assert tx_item["station_azimuth_degrees"] != rx_item["station_azimuth_degrees"]
