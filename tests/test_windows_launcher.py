"""Static compatibility checks for the Windows local launcher."""

from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_windows.ps1"
SOURCE = SCRIPT.read_text(encoding="utf-8-sig")


def test_launcher_checks_live_collector_and_offline_geography_apis() -> None:
    assert "/api/v1/psk-reporter/status" in SOURCE
    assert "spots_received" in SOURCE
    assert "/api/v1/geography/lookup" in SOURCE
    assert "GeographyApiAvailable" in SOURCE
    assert "$CollectorApiAvailable -and $GeographyApiAvailable" in SOURCE
    assert "/api/v1/psk-reporter/regional?" not in SOURCE


def test_launcher_requires_a_real_geography_result_before_reusing_server() -> None:
    assert "'KO59XX'" in SOURCE or '"KO59XX"' in SOURCE
    assert "$GeographyResponse.results[0].country" in SOURCE
    assert "does not expose the offline-geography API" in SOURCE


def test_missing_required_api_triggers_backend_restart() -> None:
    assert "a required API is missing" in SOURCE
    assert "Stopping outdated server process PID" in SOURCE
