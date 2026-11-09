import pytest

from backend.app.services.spot_store import SpotStore


def make_spot(**overrides):
    spot = {
        "band": "20m",
        "mode": "FT8",
        "tx_call": "R1BQE",
        "rx_call": "W1ABC",
        "tx_grid": "KO59XX",
        "rx_grid": "FN31pr",
        "tx_dxcc": "54",
        "rx_dxcc": "291",
        "frequency_hz": 14074653,
        "snr_db": -5.0,
        "observed_at": 10_000,
        "sequence": 12345,
    }
    spot.update(overrides)
    return spot


def test_store_inserts_and_reads_normalized_spot(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    assert store.add_spot(make_spot(), received_at=10_010) is True

    rows = store.list_recent(now=10_020)

    assert len(rows) == 1
    assert rows[0]["tx_call"] == "R1BQE"
    assert rows[0]["rx_grid"] == "FN31pr"
    assert rows[0]["frequency_hz"] == 14074653
    assert rows[0]["snr_db"] == -5.0
    assert rows[0]["received_at"] == 10_010


def test_store_rejects_duplicate_spot(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    spot = make_spot()
    assert store.add_spot(spot, received_at=10_010) is True
    assert store.add_spot(spot, received_at=10_011) is False
    assert store.count() == 1


def test_different_sequence_or_observation_time_is_not_deduplicated(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    assert store.add_spot(make_spot(), received_at=10_010)
    assert store.add_spot(make_spot(sequence=12346), received_at=10_011)
    assert store.add_spot(make_spot(observed_at=10_001), received_at=10_012)
    assert store.count() == 3


def test_expired_spots_are_removed(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3", retention_seconds=3600)
    store.add_spot(make_spot(observed_at=1_000), received_at=1_000)
    store.add_spot(make_spot(observed_at=4_000, sequence=2), received_at=4_000)

    rows = store.list_recent(now=5_000)

    assert len(rows) == 1
    assert rows[0]["observed_at"] == 4_000
    assert store.count() == 1


def test_maximum_record_count_is_enforced(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3", max_records=2)
    for index in range(3):
        store.add_spot(
            make_spot(observed_at=10_000 + index, sequence=index),
            received_at=10_010 + index,
        )

    rows = store.list_recent(now=10_020)

    assert store.count() == 2
    assert [row["observed_at"] for row in rows] == [10_002, 10_001]


def test_band_filter_and_limit(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    store.add_spot(make_spot(), received_at=10_010)
    store.add_spot(make_spot(band="40m", sequence=2), received_at=10_011)

    rows = store.list_recent(now=10_020, band="40m", limit=1)

    assert len(rows) == 1
    assert rows[0]["band"] == "40m"


def test_required_fields_are_validated(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    with pytest.raises(ValueError, match="обязательные поля"):
        store.add_spot({"band": "20m"})


@pytest.mark.parametrize(
    "kwargs",
    [{"retention_seconds": 0}, {"max_records": 0}],
)
def test_store_limits_must_be_positive(tmp_path, kwargs):
    with pytest.raises(ValueError):
        SpotStore(tmp_path / "spots.sqlite3", **kwargs)
