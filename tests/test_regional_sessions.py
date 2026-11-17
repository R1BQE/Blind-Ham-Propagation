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



def test_session_accepts_user_selected_duration():
    manager = RegionalSessionManager()
    started = manager.start("KO59", 100, duration_seconds=120, now=1_800_000_000)
    assert started["duration_seconds"] == 120
    assert started["remaining_seconds"] == 120


def test_session_rejects_unsupported_user_duration():
    manager = RegionalSessionManager()
    try:
        manager.start("KO59", 100, duration_seconds=90, now=1_800_000_000)
    except ValueError as exc:
        assert "1, 2, 3 или 5" in str(exc)
    else:
        raise AssertionError("Expected unsupported duration to be rejected")


def test_cancelled_session_does_not_return_report():
    manager = RegionalSessionManager()
    started = manager.start("KO59", 100, duration_seconds=120, now=1_800_000_000)
    cancelled = manager.cancel(started["session_id"], now=1_800_000_030)
    assert cancelled["state"] == "cancelled"
    result = manager.get(started["session_id"], now=1_800_000_031)
    assert result["state"] == "cancelled"
    assert "report" not in result


def test_session_station_pagination_returns_all_station_count():
    manager = RegionalSessionManager(duration_seconds=20)
    started = manager.start("KO59", 100, now=1_800_000_000)
    for index in range(12):
        manager.add_spot(make_spot(
            tx_call=f"R1{index:03d}",
            sequence=str(index),
            observed_at=1_800_000_001 + index,
        ), received_at=1_800_000_001 + index)
    first = manager.get(started["session_id"], now=1_800_000_020)["report"]["tx"]
    second = manager.get_stations(started["session_id"], "tx", offset=10, limit=10, now=1_800_000_020)
    assert len(first["stations"]) == 10
    assert first["stations_total"] == 12
    assert len(second["stations"]) == 2
    assert second["stations_offset"] == 10
