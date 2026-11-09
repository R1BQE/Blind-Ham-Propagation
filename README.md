# Blind-Ham Propagation

Accessible amateur-radio propagation and space-weather monitoring.

The service is designed around a text-first interface: a visitor enters a Maidenhead QTH locator and receives a structured report about space weather, ionospheric conditions, propagation forecasts and real reception reports.

## Project status

**Stage 0 — foundation.** The repository currently contains the application skeleton, an accessible PWA shell, a Maidenhead locator converter and automated tests. External data providers and propagation calculations will be added in later stages after their APIs, update rates and licensing are verified.

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
```

Run tests:

```bash
pytest
```

Run the API:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The API health endpoint is `/api/v1/health`. The locator validation endpoint is `POST /api/v1/locator/validate`.

## Deployment layout

The intended public URL is:

`https://blind-ham.ru/prop/`

Apache2 serves the files from `frontend/` under that URL and proxies `/prop/api/` to the local Uvicorn process. An example Apache configuration and systemd unit are provided in `deploy/`.

Keep runtime data, secrets, virtual environments, logs and the SQLite database outside the Git checkout. Never commit API keys or personal user data.

## Accessibility principles

- Semantic HTML and correctly associated form labels.
- Full keyboard operation without a mouse.
- Visible keyboard focus.
- Results announced through an appropriate live region.
- No information conveyed by colour alone.
- Text-first reports; maps are optional and never the only way to access information.
- Respect reduced-motion preferences.

## Data quality principles

Every measurement must identify its source, observation time, retrieval time and freshness status. Missing or stale data must be reported as such; the application must never present cached values as current measurements. Forecasts, model estimates and real reception reports must be clearly distinguished.

## License

License has not yet been selected. Until one is added, do not assume that the source code is licensed for redistribution or reuse.
