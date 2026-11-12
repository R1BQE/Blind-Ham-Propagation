# Local development and VDS deployment

## Windows local launch

Run `run-windows.bat` from Explorer or PowerShell. The launcher:
1. Runs `git pull --ff-only`.
2. Creates `.venv` when it does not exist.
3. Updates pip and dependencies from `requirements.txt`.
4. Checks whether an existing local instance supports the regional PSK Reporter API; it reuses a compatible instance or restarts an outdated one.
5. Starts FastAPI on `127.0.0.1:8765` when needed.
6. Opens `http://127.0.0.1:8765/` in the default browser.

The local server runs as `backend.run_local`. The browser uses a WebSocket session; after the last local tab closes, the server exits after a grace period. Logs are written under `%TEMP%\blind-ham-propagation\`. Local-only shutdown endpoints are not registered in the production application.

For tests and manual development commands, see [testing.md](testing.md).

## Debian VDS

Run as root from the repository checkout:

```sh
bash scripts/install_vds.sh
```

The installer is for **initial installation only**. It does not run `git pull` and refuses to run when the systemd service already exists. Prepare the checkout at the intended commit before invoking it. It prepares `.venv`, installs requirements, creates a restricted service account and configures the systemd service. By default Uvicorn listens on `127.0.0.1:8765`. The installer does not configure Apache or expose Uvicorn publicly.

Do not use this installer to update an existing production deployment. The production update procedure is being replaced by a transactional release-based updater; until that procedure is deployed and verified, update the VDS manually only under a separately prepared backup and rollback plan.

Useful commands:

- `systemctl status blind-ham-propagation`
- `journalctl -u blind-ham-propagation -f`
- `systemctl restart blind-ham-propagation`
- `systemctl stop blind-ham-propagation`

Set `BLIND_HAM_PROPAGATION_PORT` when running the installer to select another backend port.

## PSK Reporter MQTT pilot

Collector settings are stored in the untracked project-root `settings.ini`:

```ini
[psk_reporter]
enabled = true
topics = pskr/filter/v2/20m/FT8/#
```

First-run setup creates this file with collection enabled. MQTT connects only while at least one visitor has the observations tab open. Existing settings are not overwritten. The file is excluded from Git.

For a release-based deployment, persistent paths must not be derived from the selected release directory. Set these systemd environment variables to stable paths shared by all releases:

- `BLIND_HAM_DATA_DIR=/var/www/html/blind-prop/data`
- `BLIND_HAM_SETTINGS_FILE=/var/www/html/blind-prop/settings.ini`

If these variables are absent, local development continues to use the current checkout's `data/` and `settings.ini`.

Multiple topic filters can be separated by commas. Only filters beginning with `pskr/filter/v2/` are accepted. Environment variables `PSK_REPORTER_ENABLED` and `PSK_REPORTER_TOPICS` can override settings; broker host, port and keepalive are also configurable.

Status endpoint: `http://127.0.0.1:8765/api/v1/psk-reporter/status`.

## Regional PSK Reporter API

Example:

`GET /api/v1/psk-reporter/regional?locator=KP50DB&radius_km=100&hours=6&limit=30`

Parameters:
- `locator`: QTH Maidenhead locator (default `KP50DB`).
- `radius_km`: radius from the locator-cell centre, greater than 0 and at most 1000 km (default 100).
- `hours`: observation window, 3–24 hours (default 6).
- `limit`: maximum detail rows in each direction, 1–100 (default 30).
- `bands`: optional comma-separated band filter.
- `modes`: optional comma-separated mode filter.

TX counts reports where the transmitting station is inside the region and was heard remotely. RX counts reports where the receiving station is inside the region and heard a remote transmitter. These are different directions and must not be combined. Distances and bearings use Maidenhead cell centres, not exact antenna coordinates. API times are UTC.

## Collector lifecycle

The MQTT collector starts when the first browser opens the “Радионаблюдения” tab. It remains active while at least one browser keeps that tab open. After the last viewer leaves, the backend waits 20 seconds before stopping MQTT. A new viewer during this grace period cancels the pending stop. Observations remain in the bounded SQLite history after MQTT disconnects.

This coordination is in-process. Run a single Uvicorn worker so all viewers share the same collector and viewer count.
