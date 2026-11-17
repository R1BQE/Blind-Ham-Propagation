"""Regression checks for batched offline-geography lookups."""

from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1] / "frontend" / "js" / "location-tools.js"
).read_text(encoding="utf-8")


def test_geography_lookup_splits_arbitrary_lists_into_batches_of_100() -> None:
    assert "const GEOGRAPHY_LOOKUP_BATCH_SIZE = 100;" in SOURCE
    assert (
        "offset < missing.length; offset += GEOGRAPHY_LOOKUP_BATCH_SIZE"
        in SOURCE
    )
    assert (
        "missing.slice(offset, offset + GEOGRAPHY_LOOKUP_BATCH_SIZE)" in SOURCE
    )
    assert "JSON.stringify({ locators: batch })" in SOURCE
    assert "JSON.stringify({ locators: missing })" not in SOURCE


def test_geography_lookup_keeps_using_the_cache_for_requested_locators() -> None:
    assert "const missing = unique.filter((locator) => !geographyCache.has(locator));" in SOURCE
    assert "geographyCache.set(result.locator, result);" in SOURCE
    assert "new Map(unique.map((locator) => [locator, geographyCache.get(locator)]))" in SOURCE
