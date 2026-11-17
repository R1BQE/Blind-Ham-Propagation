from backend.app.services.regional_sessions import (
    RegionalSessionCapacityError,
    RegionalSessionError,
    RegionalSessionManager,
)


def make_spot(**overrides):
    spot = {
        "band": "20m", "mode": "FT8",
        "tx_call": "R1ABC", "rx_call": "DL1XYZ",
        "tx_grid": "KO59XX", "rx_grid": "JO31AA",
        "frequency_hz": 14074000, "snr_db": -12,
        "observed_at": 1_800_000_000, "sequence": "123",
    }
    spot.update(overrides)
    return spot


def test_session_collects_tx_and_rx_independently():
    manager = RegionalSessionManager(duration_seconds=180)
    started = manager.start("KO59", 500, now=1_800_000_000)
    manager.add_spot(make_spot(), received_at=1_800_000_001)
    manager.add_spot(make_spot(
        tx_call="DL1AAA", rx_call="R1BQE",
        tx_grid="JO31AA", rx_grid="KO59XX", sequence="124",
    ), received_at=1_800_000_002)
    result = manager.get(started["session_id"], now=1_800_000_180)
    assert result["report"]["tx"]["spots"] == 1
    assert result["report"]["rx"]["spots"] == 1
    assert result["report"]["tx"]["unique_local_stations"] == 1
    assert result["report"]["rx"]["unique_local_stations"] == 1


def test_duplicate_spot_is_counted_once():
    manager = RegionalSessionManager(duration_seconds=10)
    started = manager.start("KO59", 500, now=1_800_000_000)
    spot = make_spot()
    manager.add_spot(spot, received_at=1_800_000_001)
    manager.add_spot(spot, received_at=1_800_000_002)
    result = manager.get(started["session_id"], now=1_800_000_010)
    assert result["report"]["tx"]["spots"] == 1


def test_identical_active_region_reuses_session():
    manager = RegionalSessionManager()
    first = manager.start("ko59", 500, now=1_800_000_000)
    second = manager.start("KO59", 500, now=1_800_000_010)
    assert first["session_id"] == second["session_id"]
    assert second["reused"] is True


def test_active_session_limit_is_enforced():
    manager = RegionalSessionManager(max_active_sessions=1)
    manager.start("KO59", 500, now=1_800_000_000)
    try:
        manager.start("JO31", 500, now=1_800_000_001)
    except RegionalSessionCapacityError:
        pass
    else:
        raise AssertionError("Expected session capacity error")


def test_completed_result_expires():
    manager = RegionalSessionManager(duration_seconds=1, result_ttl_seconds=2)
    started = manager.start("KO59", 500, now=1_800_000_000)
    manager.get(started["session_id"], now=1_800_000_001)
    try:
        manager.get(started["session_id"], now=1_800_000_003)
    except RegionalSessionError:
        pass
    else:
        raise AssertionError("Expected expired session")
