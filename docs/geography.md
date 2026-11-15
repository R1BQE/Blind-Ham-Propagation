# Offline geographic database

**Status:** connected to the API and frontend. Reverse geocoding of Maidenhead locators uses the local SQLite database; Yandex remains only for explicit address search.

## Purpose

Convert the centre coordinates of a Maidenhead locator into a short geographic description without making a geocoding API request for every station.

The lookup returns the country and first-level administrative division when a point falls inside the corresponding boundary polygons. It also returns the nearest GeoNames populated place only when its great-circle distance is no more than 50 km. The API endpoint `POST /api/v1/geography/lookup` accepts a batch of up to 100 Maidenhead locators and returns the offline result for each unique locator.

A missing nearby settlement does not remove a country or region result. If no matching boundary is available, that level remains empty rather than being guessed from a distant settlement.

## Data sources

- GeoNames `allCountries.zip`: only feature class `P` (populated places) is imported. The primary GeoNames name is retained, along with coordinates, country/admin codes, feature code, population, and GeoNames ID.
- GeoNames `alternateNamesV2.zip`: Russian (`ru`) alternate names are imported for matching populated places. A preferred Russian name is selected when available; otherwise the primary GeoNames name remains the fallback. Source: https://www.geonames.org/export/
- Natural Earth 1:10m Admin 0 Countries: country polygons. Source: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/
- Natural Earth 1:10m Admin 1 States/Provinces: first-level administrative polygons from the same source.

GeoNames data is licensed under CC BY 4.0 and requires attribution. Natural Earth data is public domain. The application displays this attribution with geographic results: GeoNames (CC BY 4.0) and Natural Earth (public domain).

Natural Earth does not contain a complete or legally authoritative set of boundaries for every country. A missing or approximate boundary must not be presented as definitive. The populated-place catalogue is also not guaranteed to contain every village.

## Build

Install project dependencies, then run from the repository root:

```bash
python scripts/build_geography.py
```

The full builder downloads source archives to a temporary directory, creates `data/geography.sqlite3.new`, and replaces `data/geography.sqlite3` only after the import succeeds. To update an already-built database without downloading allCountries and Natural Earth again, run `python scripts/update_russian_geography_names.py`. This migration copies the existing database, adds Russian names to the copy, checks SQLite integrity, and atomically replaces the original only after success. The generated database is runtime data and is excluded from Git.

The builder needs network access and the `pyshp` Python package. The full GeoNames archive is large; allow sufficient temporary disk space for the archive, extracted boundary archives, and resulting SQLite database.

## Runtime lookup

`backend.app.services.geography.GeographyDatabase` opens the database read-only. SQLite R*Tree indexes narrow the candidate country, region, and settlement records. Polygon containment and great-circle distance are then checked in Python.

The settlement search radius is fixed at 50 km. The closest settlement is selected regardless of population or settlement type; a village closer than a city is therefore preferred. A settlement beyond 50 km is never shown.

## Validation and rollout

The lookup module has deterministic tests using a small synthetic SQLite database. Before replacing the current frontend geocoder:

1. Build the full database on a development machine or staging server.
2. Check a representative set of locators from different continents, coastal areas, islands, rural areas, and administrative borders.
3. Confirm that country/region labels and the 50 km settlement threshold behave as intended.
4. Verify the API and accessible text output with representative production locators.
5. The reverse-geocoding calls to Yandex have been removed. Explicit address search remains a separate Yandex feature.

The standalone build script only creates the database and does not change service configuration. The Debian first-install script invokes the builder automatically before starting systemd, then validates the completed database. Existing deployments are not rebuilt during `bp update`; the updater preserves `data/`.
