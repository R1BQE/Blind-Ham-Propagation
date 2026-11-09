# Blind-Ham Propagation

Accessible amateur-radio propagation and space-weather monitoring.

The service has two deliberately separate report areas:

1. **Solar and geomagnetic activity** — global measurements that do not depend on a user's QTH locator.
2. **My QTH conditions** — geographic context calculated for a supplied Maidenhead locator. The initial version reports coordinates, local mean solar time and geometric solar elevation. It does not pretend these values are an ionospheric measurement or an HF propagation forecast.

## Project status

**Stage 1 — first data-backed foundation.** The application includes a PWA shell, accessible text-first interface, Maidenhead conversion, a NOAA SWPC collector and locator-specific solar geometry. Additional ionospheric data, propagation models and real reception reports are planned.

## Planned stack

- Python 3.11+
- FastAPI and Uvicorn
- HTML, CSS and vanilla JavaScript
- Progressive Web App (PWA)
- pytest
- SQLite for cached measurements and history in a later stage
- Apache2 reverse proxy under `/prop/`

## Development

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Run the API:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

API endpoints:

- `GET /api/v1/health` — service health.
- `GET /api/v1/solar/activity` — global NOAA solar and geomagnetic measurements.
- `GET /api/v1/local/report?locator=KO59XX` — local solar geometry for a Maidenhead locator.
- `POST /api/v1/locator/validate` — validate a locator and return the center coordinates.

## NOAA data

The first collector uses public JSON products from NOAA SWPC. No API key is required for these endpoints:

- F10.7 cm solar radio flux.
- Planetary Kp index.
- Solar-wind proton speed.
- Interplanetary magnetic field Bt and Bz (GSM).
- GOES X-ray flux.

Each feed is fetched independently. A failed feed is reported in the API response instead of causing the entire solar report to fail. Each measurement includes its observation timestamp; the response also includes retrieval time and source errors.

NOAA changed several JSON formats in 2026. The collector accepts both object-based rows and the older header/value array format. Official data catalogue: https://services.swpc.noaa.gov/json/ and https://services.swpc.noaa.gov/products/.

## Deployment layout

The intended public application URL is `https://blind-ham.ru/prop/`. Apache2 serves the files from `frontend/` under that URL and proxies `/prop/api/` to the local Uvicorn process.

Keep runtime data, secrets, virtual environments, logs and the SQLite database outside the Git checkout. Never commit API keys or personal user data.

## Accessibility principles

- Semantic HTML and correctly associated form labels.
- Full keyboard operation without a mouse.
- Visible keyboard focus.
- Results announced through status/live regions.
- No information conveyed by colour alone.
- Text-first reports; maps are optional and never the only way to access information.
- Respect reduced-motion preferences.

## Data quality principles

Every measurement must identify its source, observation time, retrieval time and freshness status. Missing or stale data must be reported as such. Forecasts, model estimates, geometric calculations and real reception reports must be clearly distinguished. Do not infer local ionospheric conditions from global indices alone.

## License

License has not yet been selected. Until one is added, do not assume that the source code is licensed for redistribution or reuse.
