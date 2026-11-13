# Blind-Ham Propagation

**Language:** [Русский](README.md) | English

An accessible web service for amateur radio operators: solar and geomagnetic activity monitoring, QTH context, and regional PSK Reporter reception observations.

## Features

- **NOAA SWPC:** global solar and geomagnetic indicators.
- **NOAA D-RAP:** D-region absorption estimates; the nearest published grid cell is selected for a QTH.
- **HamQSL:** XML monitor with solar indicators, calculated HF band conditions, and VHF notices.
- **Source comparison:** comparison of selected overlapping NOAA and HamQSL indicators without artificially averaging incompatible values.
- **Maidenhead:** locator validation and coordinate conversion.
- **Local report:** solar geometry and the nearest D-RAP grid cell.
- **PSK Reporter:** MQTT/TLS collector, bounded SQLite storage, and separate regional TX/RX observations.

The project is under active development. Integrating a data source does not mean that a complete radio propagation forecast is available. See the [project roadmap](docs/en/roadmap.md) for current stages and remaining work.

## Quick start on Windows

Run `run-windows.bat`. The script updates the code, prepares the virtual environment, starts the local backend, and opens the application in a browser.

See [development and deployment](docs/en/development-and-deployment.md) for details.

## Manual development setup

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

On Debian/Linux, activate the environment with:

```bash
source .venv/bin/activate
```

To start the API manually:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

For normal local testing on Windows, `run-windows.bat` is preferred because it configures additional local application lifecycle behavior.

## Main API routes

Base prefix: `/api/v1`.

- `GET /health` — service health.
- `GET /solar/activity` — NOAA, D-RAP, and HamQSL data.
- `GET /local/report?locator=KP50DB` — locator geographic context and D-RAP.
- `POST /locator/validate` — validate a Maidenhead locator.
- `GET /psk-reporter/status` — MQTT collector status.
- `GET /psk-reporter/regional?locator=KP50DB&radius_km=100&hours=6` — regional TX/RX observations.
- `POST /psk-reporter/subscriptions` — update collector filters.
- `WS /psk-reporter/session` — active radio-observation viewer session.

See the [API reference](docs/en/api.md) for parameters, limits, and errors.

## Data sources and accuracy

- [NOAA SWPC](https://services.swpc.noaa.gov/json/) — global measurements and indices.
- [NOAA D-RAP](https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap) — D-region absorption model.
- [HamQSL](https://www.hamqsl.com/solarxml.php) — combined XML monitor.
- [PSK Reporter](https://www.mqtt.pskreporter.info/) — actual reception reports from participating stations.

Measurements, model estimates, geometric calculations, and reception reports must not be conflated. Each value must retain its source, unit, and observation time. D-RAP is not MUF. Global indices are not forecasts for a specific radio path. The absence of PSK Reporter spots does not prove that a band is closed.

Read [data sources and interpretation](docs/en/data-sources.md) for details.

## Accessibility

The interface is developed with keyboard and screen-reader accessibility as priorities: semantic HTML, associated labels, visible focus, textual results, and announced status changes. Maps and colour must never be the only way to access information.

## Documentation

- [Architecture](docs/en/architecture.md).
- [API reference](docs/en/api.md).
- [Data sources](docs/en/data-sources.md).
- [AI-assisted development guide](docs/en/ai-development-guide.md).
- [Testing](docs/en/testing.md).
- [Development and deployment](docs/en/development-and-deployment.md).
- [Roadmap](docs/en/roadmap.md).
- [Licensing and third-party components](docs/en/licensing.md).
- [AI agent instructions](AGENTS.en.md).

The Russian documentation is the default and is available in the repository root and [docs/](docs/).

## Production deployment and updates

The public application URL is `https://blind-ham.ru/prop/`. The backend must listen on loopback only; Apache exposes it through a reverse proxy. Do not expose Uvicorn directly to the internet.

For an existing production installation, run `bp update` as root. Check the current state with `bp status`; return to the previous successfully deployed version with `bp rollback`. See the [deployment guide](docs/en/development-and-deployment.md) for details.

Initial installation and updates are separate operations. `scripts/install_vds.sh` is for initial installation only; it is not an update command.

Do not commit secrets, local `settings.ini`, user data, the working SQLite database, or logs.

## License

The project source code is distributed under GNU GPL version 3 or later. See [LICENSE](LICENSE). External data and third-party components may have separate licences and terms; see the [licensing document](docs/en/licensing.md).
