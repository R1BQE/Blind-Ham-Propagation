# HTTP API

**Language:** [Русский](../api.md) | English

The application exposes versioned routes under `/api/v1`. In local development the base URL is usually `http://127.0.0.1:8765`; production is served through the configured reverse proxy.

This document describes the implementation in `backend/app/api/routes.py`. Verify the route source and tests before relying on it as a compatibility guarantee.

## Health

`GET /api/v1/health`

Returns the service health object with `status` and `service`.

## Solar and geomagnetic activity

`GET /api/v1/solar/activity`

Returns NOAA SWPC space-weather data, D-RAP data, and HamQSL solar XML. Providers are fetched independently; one provider failure may produce a partial response without discarding other results.

## Local QTH report

`GET /api/v1/local/report?locator=KP50DB`

The required `locator` parameter is a 2–12 character Maidenhead locator. The response includes geographic/solar context and attempts to include the nearest NOAA D-RAP grid cell. The nearest cell is a model estimate, not a direct station measurement.

## Locator validation

`POST /api/v1/locator/validate`

JSON request:

```json
{"locator":"KP50DB"}
```

Returns the normalized locator and the cell-centre coordinates. Invalid locators return HTTP 422.

## Geographic lookup

`POST /api/v1/geography/lookup`

Accepts Maidenhead locators and returns country, region, and nearest populated place from the offline `data/geography.sqlite3` database. This geography database remains required and is unrelated to PSK Reporter spot history.

## PSK Reporter MQTT collector status

`GET /api/v1/psk-reporter/status`

Returns MQTT connection state and live-feed counters: MQTT messages, valid spots, malformed messages, and errors. These counters do not indicate persistent storage; spot history is not saved.

## Manual PSK Reporter regional sessions

Collection starts only after an explicit user action. Opening the “My area” or “Stations” tabs never starts collection automatically.

### Start a session

`POST /api/v1/psk-reporter/regional/sessions`

JSON request:

```json
{"locator":"KO59XX","radius_km":100,"duration_seconds":60}
```

- `locator`: Maidenhead centre of the region.
- `radius_km`: greater than 0 and at most 1000 km; default 100.
- `duration_seconds`: 60, 120, 180, or 300; default 60.

The MQTT collector must be connected. If unavailable, the API returns HTTP 503. The active-session limit returns HTTP 429.

### Session status and result

`GET /api/v1/psk-reporter/regional/sessions/{session_id}`

While collecting, returns state, remaining time, and the number of matching spots. After completion, returns an aggregated report with separate TX and RX directions.

### Station pages

`GET /api/v1/psk-reporter/regional/sessions/{session_id}/stations?direction=tx&offset=0&limit=10`

`direction` is `tx` or `rx`; `offset` selects the page position and `limit` is 1–100. The frontend loads stations in pages of 10.

### Cancel

`DELETE /api/v1/psk-reporter/regional/sessions/{session_id}`

Stops an active collection. A cancelled session is not returned as a completed report.

Sessions receive spots from the shared live MQTT feed. The regional manager filters them by locator and radius and keeps only aggregated results in RAM. Raw spots and a historical SQLite database are not used. Results remain in memory for a limited time (10 minutes after completion); restarting the backend clears all sessions.

## MQTT collector settings

The collector starts with the backend when `[psk_reporter] enabled = true` is set in `settings.ini`. It subscribes to all supported bands and digital modes and forwards valid spots to active regional sessions. No persistent spot history is created.

For temporary diagnostics, an administrator may set `PSK_REPORTER_TOPICS`. The legacy `topics` setting in `settings.ini` is ignored.

## Errors

- HTTP 422: invalid parameters or request data.
- HTTP 429: maximum number of active regional sessions reached.
- HTTP 503: MQTT collector or regional manager unavailable.
- HTTP 404: session not found or result retention expired.

When routes change, update this document and the corresponding API tests in the same change.
