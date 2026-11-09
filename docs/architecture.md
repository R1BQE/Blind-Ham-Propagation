# Architecture

## First deployment target

The public application URL is planned as `https://blind-ham.ru/prop/`. The existing Apache2 virtual host remains the public entry point. Apache serves the static PWA frontend and reverse-proxies only `/prop/api/` to Uvicorn bound to loopback.

The backend is a separate systemd service. It must not be exposed directly to the public network.

## Components

- `frontend/`: semantic HTML, responsive CSS, vanilla JavaScript, web app manifest and service worker.
- `backend/app/api/`: versioned HTTP API.
- `backend/app/services/`: domain logic such as Maidenhead locator conversion and propagation calculations.
- `backend/app/collectors/`: provider-specific data collectors, including the planned PSK Reporter MQTT consumer.
- `data/`: runtime-only storage; excluded from Git.
- `tests/`: unit and API tests.
- `deploy/`: deployment examples for Apache2 and systemd.

## Request flow

1. The browser loads the PWA from `/prop/`.
2. The visitor enters a Maidenhead locator and station parameters.
3. The frontend sends a same-origin request to `/prop/api/v1/`.
4. Apache proxies that request to Uvicorn.
5. FastAPI validates input and returns JSON.
6. The frontend renders the result as ordinary text in the document.

## PSK Reporter regional observation architecture

The PSK Reporter feed is used as a source of recent reception observations, not as a direct measurement of the user's own station coverage.

### Observation area

- The observation-area center is the user's personal QTH locator.
- The default radius is 100 km.
- The center coordinates are calculated from the center of the Maidenhead cell using the existing locator conversion service.
- The radius is measured as great-circle distance (Haversine) from the observation center to the relevant station coordinates.
- The radius should be a configuration value, defaulting to 100 km, so it can become user-adjustable later without changing the data model.
- The personal station profile (TX power, antenna type and height) is separate from the observation-area filter. Initial station defaults are 100 W, a dipole and 10 m antenna height.

The station locator supplied by PSK Reporter may have different precision. Coordinates derived from a locator are estimates at the center of its grid cell. Preserve the original locator and its precision in each stored spot; do not present derived coordinates as exact station positions.

### Two independent observation directions

Do not combine these into one statistic:

1. **Regional transmitters heard remotely:** include spots whose TX station is within 100 km of the user's QTH; list the remote RX stations and their locations. This shows where stations in the user's region are being decoded.
2. **Remote transmitters heard regionally:** include spots whose RX station is within 100 km of the user's QTH; list the remote TX stations and their locations. This shows which distant stations are being decoded by listeners in the user's region.

Each result must be labelled with its direction. Neither direction proves that the user's own station, antenna or power can establish the same contact. These are regional proxy observations.

If the locator needed for the relevant side of a spot is absent or invalid, do not include that spot in the corresponding radius-filtered metric. It may be counted separately as a location-unavailable observation, but must not be silently assigned to the region.

### MQTT collection and filtering

The PSK Reporter MQTT topic supports exact topic-level filters and single-level/multi-level wildcards, but it cannot express a 100 km radius or a partial Maidenhead locator prefix. A `+` wildcard matches one complete topic segment; it does not mean “all grid squares within this radius”.

Therefore the collector must:
- subscribe only to explicitly selected amateur bands and modes needed by the report;
- receive candidate spots and apply the 100 km geographic filter locally after parsing the TX/RX locator;
- keep TX-area and RX-area matching as separate predicates;
- avoid an unrestricted global subscription until feed volume, CPU, memory and network usage have been measured;
- reconnect with backoff and tolerate malformed messages and temporary broker outages;
- retain only a bounded recent history, with UTC timestamps and deduplication, rather than accumulating the public feed indefinitely.

The initial implementation should keep parsing, geographic filtering and MQTT transport as separate testable components. The public HTTP API reads the collector's recent normalized observations; it must not open a new MQTT connection for every page request.

## Data handling rules

Every external observation should preserve:

- provider and product name;
- observation timestamp in UTC;
- retrieval timestamp in UTC;
- measurement value and unit;
- quality or provisional/final status, when supplied;
- freshness threshold and stale status.

Do not silently merge observations with different time resolutions. Do not label model forecasts as measurements. Do not infer a local ionospheric measurement from a distant ionosonde without clearly identifying the station and distance.

## Future user accounts

The first release is anonymous and does not create user profiles. The API and storage layers should remain separable so that saved locators and band preferences can be introduced later without changing the public report format.
