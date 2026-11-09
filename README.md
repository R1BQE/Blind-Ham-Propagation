# Blind-Ham Propagation

Accessible amateur-radio propagation and space-weather monitoring.

The service has two deliberately separate report areas:

1. **Solar and geomagnetic activity** — global measurements that do not depend on a user's QTH locator.
2. **My QTH conditions** — geographic context calculated for a supplied Maidenhead locator. The QTH report includes coordinates, local mean solar time, geometric solar elevation and the nearest NOAA D-RAP grid cell. It does not present these model values as direct measurements or as an HF propagation forecast.

## Project status

**Stage 2 — global D-RAP and QTH lookup.** The application includes a PWA shell, accessible text-first interface, Maidenhead conversion, NOAA SWPC global measurements, NOAA D-RAP absorption data and locator-specific solar geometry. Direct GIRO/DIDBase observations remain unavailable until access and permitted use are arranged.

## Planned stack

- Python 3.11+
- FastAPI and Uvicorn
- HTML, CSS and vanilla JavaScript
- Progressive Web App (PWA)
- pytest
- SQLite for cached measurements and history in a later stage
- Apache2 reverse proxy under `/prop/`

## Development

On Windows, run `run-windows.bat` to pull the latest code, create/update the virtual environment and open the local application in a browser. See [Windows and VDS setup](docs/development-and-deployment.md) for details.


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
- `GET /api/v1/solar/activity` — global NOAA solar and geomagnetic measurements plus D-RAP model status.
- `GET /api/v1/local/report?locator=KO59XX` — local solar geometry and the nearest D-RAP grid cell.
- `POST /api/v1/locator/validate` — validate a locator and return the center coordinates.

## NOAA data

The first collector uses public JSON products from NOAA SWPC. No API key is required for these endpoints:

- F10.7 cm solar radio flux.
- Planetary Kp index.
- Solar-wind proton speed.
- Interplanetary magnetic field Bt and Bz (GSM).
- GOES X-ray flux.\n\nThe report also includes NOAA D-RAP tabular values. For a supplied QTH, the service selects the nearest published grid cell (no interpolation) and reports the modelled highest frequency affected by at least 1 dB of D-region absorption. The product grid is approximately 2° latitude by 4° longitude. This is an absorption estimate, not MUF, a band-opening forecast or a direct measurement of link quality. Product documentation: https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap

Each feed is fetched independently. A failed feed is reported in the API response instead of causing the entire solar report to fail. Each measurement includes its observation timestamp; the response also includes retrieval time and source errors.

NOAA changed several JSON formats in 2026. The collector accepts both object-based rows and the older header/value array format. Official data catalogue: https://services.swpc.noaa.gov/json/ and https://services.swpc.noaa.gov/products/.

## GIRO / ionosonde data\n\nGIRO/DIDBase is not currently queried by this public service. Lowell DIDBase numerical access requires a read-only account, and its published rules limit free online access to educational and non-commercial research purposes. Data-provider acknowledgement requirements also apply. Any integration must first establish appropriate access and use conditions; no credentials are embedded in this repository. Rules: https://ulcar.uml.edu/DIDB/RulesOfTheRoadForDIDBase.htm\n\n## Deployment layout

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
