# Architecture

## First deployment target

The public application URL is planned as `https://blind-ham.ru/prop/`. The existing Apache2 virtual host remains the public entry point. Apache serves the static PWA frontend and reverse-proxies only `/prop/api/` to Uvicorn bound to loopback.

The backend is a separate systemd service. It must not be exposed directly to the public network.

## Components

- `frontend/`: semantic HTML, responsive CSS, vanilla JavaScript, web app manifest and service worker.
- `backend/app/api/`: versioned HTTP API.
- `backend/app/services/`: domain logic such as Maidenhead locator conversion and later propagation calculations.
- `backend/app/collectors/`: planned provider-specific data collectors.
- `data/`: runtime-only storage; excluded from Git.
- `tests/`: unit and API tests.
- `deploy/`: deployment examples for Apache2 and systemd.

## Request flow

1. The browser loads the PWA from `/prop/`.
2. The visitor enters a Maidenhead locator.
3. The frontend sends a same-origin request to `/prop/api/v1/`.
4. Apache proxies that request to Uvicorn.
5. FastAPI validates input and returns JSON.
6. The frontend renders the result as ordinary text in the document.

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
