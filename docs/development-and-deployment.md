# Local development and VDS deployment

## Windows local launch

Run `run-windows.bat` from Explorer or a terminal. The launcher:

1. Runs `git pull --ff-only`.
2. Creates `.venv` when it does not exist.
3. Updates pip and all dependencies from `requirements.txt`.
4. Starts the local FastAPI application on `127.0.0.1:8765`.
5. Opens the default browser at `http://127.0.0.1:8765/`.

The console window is hidden. The local server is started as the Python module `backend.run_local`. The page opens a WebSocket session with the local backend. When the last local tab closes or navigates away, the connection closes and the server exits after a 15-second grace period. This avoids timer throttling in background browser tabs. Launcher and server logs are written to:

`%TEMP%\blind-ham-propagation\`

The local session shutdown endpoints are enabled only by `backend/run_local.py`; they are not registered in the production application.

## Debian VDS

Run as root from the repository checkout:

```sh
bash scripts/install_vds.sh
```

The script fast-forwards the checkout, creates or updates `.venv`, installs `requirements.txt`, creates a restricted system account and installs/enables/restarts `blind-ham-propagation.service`.

By default Uvicorn listens only on `127.0.0.1:8765`. Apache should serve `frontend/` and reverse-proxy the public `/prop/api/` path to this backend, as described in the deployment documentation. The script does not modify Apache configuration or expose Uvicorn to the public network.

Useful service commands:

- `systemctl status blind-ham-propagation`
- `journalctl -u blind-ham-propagation -f`
- `systemctl restart blind-ham-propagation`
- `systemctl stop blind-ham-propagation`

Set `BLIND_HAM_PROPAGATION_PORT` when running the installer to choose another backend port.

## PSK Reporter MQTT pilot

Collector settings live in the untracked project-root `settings.ini` file:

```ini
[psk_reporter]
enabled = true
topics = pskr/filter/v2/20m/FT8/#
```

On Windows and Debian, the first-run setup creates this file with `enabled = true`. This permits collection, but MQTT only connects while at least one visitor has the observations tab open. The installer does not overwrite an existing file. Edit `settings.ini` and restart the application/service for changes to take effect. The file is excluded from Git.

Multiple topic filters can be separated by commas. Only filters beginning with `pskr/filter/v2/` are accepted. Environment variables `PSK_REPORTER_ENABLED` and `PSK_REPORTER_TOPICS` remain available as explicit overrides; host, port and keepalive are also configurable through environment variables.

The default topic filter is `pskr/filter/v2/20m/FT8/#`. To inspect the collector, open:

`http://127.0.0.1:8765/api/v1/psk-reporter/status`

The response reports connection state, received MQTT messages, saved spots, duplicates, malformed messages, and storage count.

## Regional PSK Reporter API

Example request:

`GET /api/v1/psk-reporter/regional?locator=KP50DB&radius_km=100&hours=6&limit=30`

Parameters:
- `locator` — QTH Maidenhead locator (default `KP50DB`).
- `radius_km` — radius around the centre of the QTH locator cell, from 1 to 1000 km (default 100).
- `hours` — observation window from 1 to 6 hours (default 6; storage retention is six hours).
- `limit` — maximum latest spots in each direction, from 1 to 100 (default 30).

TX counts spots where the transmitting station's locator is inside the region; the transmitter was heard by the remote receiving station. RX counts spots where the receiving station's locator is inside the region; the local receiver heard the remote transmitter. A spot may appear in both groups if both stations are inside the radius. Invalid or missing locator values are excluded only from the direction that depends on that station's location.

The distance and bearing shown for each record point from the QTH locator-cell centre to the remote station's locator-cell centre. The local station's distance from QTH is also shown. Regional inclusion is based only on the local endpoint's locator; a missing or invalid remote locator does not remove an otherwise valid local observation. All times in the API are UTC.


## PSK Reporter collection lifecycle

The MQTT collector is not started at application boot. It starts when the first browser opens the "Радионаблюдения" tab and remains active while at least one browser keeps that tab open. The browser holds a WebSocket connection; switching to another application tab or closing the page disconnects that viewer. After the last viewer leaves, the backend waits 20 seconds before stopping MQTT. A new viewer during this grace period cancels the pending stop. Observations remain in the bounded six-hour SQLite history after MQTT disconnects. This coordination is in-process; run a single Uvicorn worker so all viewers share the same collector and viewer count.
