# Offline geographic database

**Status:** preparation and lookup module added; the existing interface still uses its current Yandex integration until a later migration step.

## Purpose

Convert the centre coordinates of a Maidenhead locator into a short geographic description without making a geocoding API request for every station.

The lookup returns the country and first-level administrative division when a point falls inside the corresponding boundary polygons. It also returns the nearest GeoNames populated place only when its great-circle distance is no more than 50 km.

A missing nearby settlement does not remove a country or region result. If no matching boundary is available, that level remains empty rather than being guessed from a distant settlement.

## Data sources

- GeoNames `allCountries.zip`: only feature class `P` (populated places) is imported. The primary GeoNames name is retained, along with coordinates, country/admin codes, feature code, population, and GeoNames ID. Source: https://www.geonames.org/export/
- Natural Earth 1:10m Admin 0 Countries: country polygons. Source: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/
- Natural Earth 1:10m Admin 1 States/Provinces: first-level administrative polygons from the same source.

GeoNames data is licensed under CC BY 4.0 and requires attribution. Natural Earth data is public domain. The application must display a concise attribution for both datasets when the offline lookup is connected to the public interface.

Natural Earth does not contain a complete or legally authoritative set of boundaries for every country. A missing or approximate boundary must not be presented as definitive. The populated-place catalogue is also not guaranteed to contain every village.

## Build

Install project dependencies, then run from the repository root:

```bash
python scripts/build_geography.py
```

The script downloads source archives to a temporary directory, creates `data/geography.sqlite3.new`, and replaces `data/geography.sqlite3` only after the import succeeds. The generated database is runtime data and is excluded from Git.

The builder needs network access and the `pyshp` Python package. The full GeoNames archive is large; allow sufficient temporary disk space for the archive, extracted boundary archives, and resulting SQLite database.

## Runtime lookup

`backend.app.services.geography.GeographyDatabase` opens the database read-only. SQLite R*Tree indexes narrow the candidate country, region, and settlement records. Polygon containment and great-circle distance are then checked in Python.

The settlement search radius is fixed at 50 km. The closest settlement is selected regardless of population or settlement type; a village closer than a city is therefore preferred. A settlement beyond 50 km is never shown.

## Validation and rollout

The lookup module has deterministic tests using a small synthetic SQLite database. Before replacing the current frontend geocoder:

1. Build the full database on a development machine or staging server.
2. Check a representative set of locators from different continents, coastal areas, islands, rural areas, and administrative borders.
3. Confirm that country/region labels and the 50 km settlement threshold behave as intended.
4. Connect the lookup to the API and accessible text output.
5. Only after successful verification, remove the reverse-geocoding calls to Yandex. Address search can remain a separate feature.

The production VDS is not modified by the build script or this repository change.
