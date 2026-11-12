# Architecture

## Runtime layout

The application has a static frontend and a Python/FastAPI backend.

- `frontend/`: semantic HTML, responsive CSS, vanilla JavaScript, web app manifest and service worker.
- `backend/app/main.py`: FastAPI application and router registration.
- `backend/app/api/routes.py`: versioned HTTP and WebSocket route handlers.
- `backend/app/services/`: provider clients, Maidenhead conversion, local/regional reports, MQTT parsing/storage helpers and domain logic.
- `backend/app/collectors/`: long-running collectors, including the PSK Reporter MQTT collector.
- `backend/run_local.py`: local development lifecycle entry point; local-only session shutdown functionality must not leak into production.
- `tests/`: pytest unit and API tests.
- `scripts/`: setup and installation scripts.
- `deploy/`: service and reverse-proxy examples.
- `data/`, `logs/`: runtime-only state; excluded from Git.

Confirm the current repository tree before editing. Documentation describes responsibilities, not a guarantee that every module remains at the same path.

## Request flow

1. The browser loads the frontend from the configured application URL.
2. Frontend JavaScript requests data from the same-origin `/api/v1/` endpoints.
3. In production, Apache serves static files and reverse-proxies API requests to Uvicorn on loopback.
4. FastAPI validates request parameters and calls provider/domain services.
5. Services fetch or calculate data and return normalized structures while preserving provider-specific metadata.
6. Frontend renders the response as accessible text, tables and controls.

The intended public URL is `https://blind-ham.ru/prop/`; production Uvicorn must not be exposed directly to the public network.

## Solar and space-weather report

The `GET /api/v1/solar/activity` route composes independent source results:
- NOAA SWPC global solar/geomagnetic indicators;
- NOAA D-RAP absorption product;
- HamQSL solar XML report.

A provider error is recorded without discarding other successful provider results. The frontend presents the HamQSL monitor and a comparison for selected overlapping NOAA/HamQSL quantities.

The sources are not interchangeable. Preserve original values, units, observation times, retrieval times and product semantics. Do not average values merely to produce one number. The current frontend displays NOAA and HamQSL measurements separately and does not automatically compare similarly named fields: K and Kp, for example, are not interchangeable, and a Bz component is not the same quantity as total magnetic-field strength. A preferred source can be selected only after documented comparison of definition, unit, time, geographic scope and quality. If values are not comparable, show them separately.

## QTH report

The local report uses the Maidenhead locator conversion service to derive the locator-cell centre. It adds local solar geometry and attempts to obtain the nearest NOAA D-RAP grid cell. The nearest grid cell is not an exact measurement at the station and must be labelled as a model estimate.

The current implementation does not provide a validated path-specific HF propagation forecast. Do not imply that the global indices or D-RAP alone predict whether a specific contact will succeed.

## PSK Reporter regional observation architecture

PSK Reporter is a source of reception reports from participating stations, not a direct measurement of the user's own station coverage.

### Observation area

- The observation-area centre is a supplied QTH Maidenhead locator.
- The default radius is 100 km.
- Coordinates are calculated from the centre of the Maidenhead cell.
- Radius filtering uses great-circle distance from that centre to the relevant station locator-cell centre.
- The personal station profile is separate from the regional observation filter.
- A locator describes an area, not an exact antenna position. Preserve the original locator and precision.

### Two independent observation directions

Do not combine these into one statistic:

1. **TX — regional transmitters heard remotely:** the transmitting station is inside the QTH region and a remote receiver reports hearing it.
2. **RX — remote transmitters heard regionally:** a receiver inside the QTH region reports hearing a remote transmitter.

Neither direction proves that the user's own station, antenna or power can establish the same contact. These are regional proxy observations.

### MQTT collection and filtering

The PSK Reporter MQTT topic supports topic-level filters and wildcards, but cannot express a geographic radius. The collector receives candidate spots and applies geographic filtering locally after parsing the TX/RX locators.

The collector:
- subscribes only to configured bands and modes;
- reconnects with backoff and tolerates malformed messages and broker outages;
- stores normalized reports in a bounded SQLite history;
- deduplicates observations;
- runs on demand while one or more visitors have the observations tab open;
- is shared across viewers and must run in a single Uvicorn worker unless coordination is redesigned.

The public HTTP API reads stored observations; it must not create a new MQTT connection per request.

## Data handling rules

Every external observation/value should preserve, where supplied:
- provider and product name;
- observation timestamp in UTC;
- retrieval timestamp in UTC;
- value and unit;
- quality/provisional/final status;
- freshness threshold and stale status.

Do not silently merge observations with different time resolutions. Do not label model forecasts as measurements. Do not infer a local ionospheric measurement from a distant ionosonde without identifying the station and distance.

## Future work

The project roadmap is maintained in [roadmap.md](roadmap.md). In particular, path-specific propagation modelling, source-confidence selection, concise solar-monitor summaries and PWA operational validation remain separate tasks. Do not describe planned features as implemented.
