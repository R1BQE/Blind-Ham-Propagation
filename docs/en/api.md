# HTTP API

**Language:** [Русский](../api.md) | English

The application exposes versioned routes under `/api/v1`. In local development the base URL is usually `http://127.0.0.1:8765`; production is served through the configured reverse proxy.

This document describes the implementation currently present in `backend/app/api/routes.py`. Confirm the route source and tests before relying on it as a compatibility guarantee.

## Health

`GET /api/v1/health`

Returns a small service-health object, currently including `status` and `service`.

## Solar and geomagnetic activity

`GET /api/v1/solar/activity`

Returns global space-weather data from NOAA SWPC, D-RAP data, and HamQSL solar XML data. Providers are fetched independently. A provider failure is recorded in `errors` and can produce a partial response rather than discarding other provider results.

The response is a composite object. Inspect current provider service modules and tests for exact field names and nested schemas; do not assume all providers return identical quantities or timestamps.

## Local QTH report

`GET /api/v1/local/report?locator=KP50DB`

Required query parameter: `locator`, a Maidenhead locator of 2–12 characters.

Returns locator-specific geographic/solar context and attempts to include the nearest NOAA D-RAP grid cell. The nearest grid cell is a model product, not a direct measurement at the station.

Invalid locators return HTTP 422.

## Locator validation

`POST /api/v1/locator/validate`

JSON request:

```json
{"locator":"KP50DB"}
```

Returns the normalized locator and centre latitude/longitude. Invalid locators return HTTP 422.

## PSK Reporter collector status

`GET /api/v1/psk-reporter/status`

Returns collector state and counters. If the collector has not been initialized, the route reports `enabled: false` and `state: not_started`.

## Regional PSK Reporter observations

`GET /api/v1/psk-reporter/regional`

Query parameters:

- `locator`: QTH Maidenhead locator; default `KP50DB`.
- `radius_km`: radius around the locator-cell centre; greater than 0 and at most 1000 km; default 100.
- `hours`: observation window; current route accepts 3–24 hours; default 6.
- `limit`: maximum detail rows in each direction; 1–100; default 30.
- `bands`: optional comma-separated band filter.
- `modes`: optional comma-separated mode filter.

The response keeps TX and RX directions separate. TX describes transmissions from stations inside the selected region that were received remotely. RX describes remote transmissions heard by receivers inside the region. These are regional observations, not proof of the user's own station capability.

Invalid parameters/locators return HTTP 422.

## PSK Reporter subscriptions

`POST /api/v1/psk-reporter/subscriptions`

The JSON request contains non-empty arrays `bands` and `modes`. Array sizes are bounded by route validation. The collector validates and applies the filters; invalid filters return 422. If the collector is unavailable, the route returns 503.

## PSK Reporter viewer session

`WS /api/v1/psk-reporter/session`

A browser WebSocket session tells the backend that the observations view is active. The shared collector lifecycle is coordinated across connected viewers. The collector does not open a new MQTT connection for every HTTP report request.

## Errors and compatibility

- HTTP 422: invalid query or request data.
- HTTP 503: required collector/service unavailable.
- External provider failures may be represented inside a successful partial solar report.
- Interpret times according to each field's documented timezone; source timestamps are normally UTC.

When adding, removing, or changing a route, update this document and the corresponding API tests in the same change.
