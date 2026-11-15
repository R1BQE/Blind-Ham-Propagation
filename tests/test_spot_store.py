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



def test_default_retention_keeps_only_the_last_six_hours(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    now = 100_000
    store.add_spot(
        make_spot(observed_at=now - 5 * 60 * 60, sequence=1),
        received_at=now - 5 * 60 * 60,
    )
    store.add_spot(
        make_spot(observed_at=now - 7 * 60 * 60, sequence=2),
        received_at=now - 7 * 60 * 60,
    )

    store.prune(now=now)

    rows = store.list_recent(now=now)
    assert store.retention_seconds == 6 * 60 * 60
    assert len(rows) == 1
    assert rows[0]["sequence"] == "1"

def test_iter_recent_filters_by_period_and_reads_in_batches(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    now = 100_000
    store.add_spot(
        make_spot(observed_at=now - 2 * 60 * 60, sequence=1),
        received_at=now - 2 * 60 * 60,
    )
    store.add_spot(
        make_spot(observed_at=now - 8 * 60 * 60, sequence=2),
        received_at=now - 8 * 60 * 60,
    )
    store.add_spot(
        make_spot(observed_at=now - 25 * 60 * 60, sequence=3),
        received_at=now - 25 * 60 * 60,
    )

    rows = list(store.iter_recent(now=now, since=now - 3 * 60 * 60, batch_size=1))

    assert len(rows) == 1
    assert rows[0]["sequence"] == "1"


def test_store_rejects_duplicate_spot(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    spot = make_spot()
    assert store.add_spot(spot, received_at=10_010) is True
    assert store.add_spot(spot, received_at=10_011) is False
    assert store.count() == 1


def test_batch_insert_uses_one_api_call_and_counts_duplicates(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    first = make_spot(sequence=1)
    second = make_spot(sequence=2)

    inserted, duplicates = store.add_spots([
        (first, 10_010),
        (second, 10_011),
        (first, 10_012),
    ])

    assert inserted == 2
    assert duplicates == 1
    assert store.count() == 2


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

    store.prune(now=5_000)
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

    # Batch insertion no longer performs expensive pruning on every flush.
    assert store.count() == 3

    store.prune(now=10_020)
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



def test_batch_insert_does_not_prune_until_explicit_cleanup(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3", retention_seconds=3600)
    store.add_spot(make_spot(observed_at=1_000), received_at=1_000)
    store.add_spot(make_spot(observed_at=4_000, sequence=2), received_at=4_000)

    assert store.count() == 2

    deleted = store.prune(now=5_000)

    assert deleted == 1
    assert store.count() == 1


def test_list_recent_does_not_modify_storage(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3", retention_seconds=3600)
    store.add_spot(make_spot(observed_at=1_000), received_at=1_000)

    rows = store.list_recent(now=5_000)

    assert rows == []
    assert store.count() == 1



def test_iter_recent_for_region_keeps_tx_and_rx_candidates_and_filters(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    now = 100_000
    store.add_spot(
        make_spot(tx_grid="KO59XX", rx_grid="FN31pr", observed_at=now - 10, sequence=1),
        received_at=now,
    )
    store.add_spot(
        make_spot(tx_grid="FN31pr", rx_grid="KO59XW", observed_at=now - 9, sequence=2),
        received_at=now,
    )
    store.add_spot(
        make_spot(tx_grid="FN31pr", rx_grid="FN32pr", observed_at=now - 8, sequence=3),
        received_at=now,
    )
    store.add_spot(
        make_spot(tx_grid="KO59XX", rx_grid="FN31pr", band="40m", observed_at=now - 7, sequence=4),
        received_at=now,
    )

    rows = list(store.iter_recent_for_region(
        locator="KO59XX",
        radius_km=1,
        now=now,
        since=now - 60,
        bands=["20m"],
        modes=["FT8"],
    ))

    assert {row["sequence"] for row in rows} == {"1", "2"}

def test_regional_lookup_indexes_tx_rx_and_short_locators(tmp_path):
    store = SpotStore(tmp_path / "spots.sqlite3")
    with store._connect() as connection:
        indexes = {
            row["name"]
            for row in connection.execute(
                "PRAGMA index_list(spots)"
            ).fetchall()
        }

    expected = {
        "idx_spots_tx_grid4_observed",
        "idx_spots_rx_grid4_observed",
        "idx_spots_tx_short_observed",
        "idx_spots_rx_short_observed",
    }
    assert expected <= indexes

    prefixes = ["KO59", "KO58"]
    placeholders = ",".join("?" for _ in prefixes)
    query = f"""
        SELECT * FROM spots
        WHERE id IN (
            SELECT id FROM spots
            WHERE observed_at >= ? AND observed_at <= ?
              AND upper(substr(tx_grid, 1, 4)) IN ({placeholders})
            UNION
            SELECT id FROM spots
            WHERE observed_at >= ? AND observed_at <= ?
              AND upper(substr(rx_grid, 1, 4)) IN ({placeholders})
            UNION
            SELECT id FROM spots
            WHERE observed_at >= ? AND observed_at <= ?
              AND tx_grid IS NOT NULL AND length(tx_grid) < 4
            UNION
            SELECT id FROM spots
            WHERE observed_at >= ? AND observed_at <= ?
              AND rx_grid IS NOT NULL AND length(rx_grid) < 4
        )
    """
    parameters = [
        0, 100, *prefixes,
        0, 100, *prefixes,
        0, 100,
        0, 100,
    ]
    with store._connect() as connection:
        plan = " ".join(
            row["detail"]
            for row in connection.execute(
                "EXPLAIN QUERY PLAN " + query, parameters
            ).fetchall()
        )

    assert "idx_spots_tx_grid4_observed" in plan
    assert "idx_spots_rx_grid4_observed" in plan
    assert "idx_spots_tx_short_observed" in plan
    assert "idx_spots_rx_short_observed" in plan

