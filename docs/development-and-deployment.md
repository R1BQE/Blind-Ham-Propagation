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

The collector is disabled by default. The first test subscribes only to 20 m FT8 over MQTT/TLS on port 1884; it does not subscribe to the full worldwide feed.

For a temporary Windows test, set the environment variable in the same PowerShell session before launching the application:

```powershell
$env:PSK_REPORTER_ENABLED = "true"
.\run-windows.bat
```

The default topic filter is `pskr/filter/v2/20m/FT8/#`. To inspect the collector, open:

`http://127.0.0.1:8765/api/v1/psk-reporter/status`

The response reports connection state, received MQTT messages, saved spots, duplicates, malformed messages, and storage count. To stop the collector on the next launch, use:

```powershell
Remove-Item Env:PSK_REPORTER_ENABLED
```

On Debian, the installer creates `/etc/blind-ham-propagation.env` with the collector disabled. To enable the pilot on the VDS, change `PSK_REPORTER_ENABLED=false` to `PSK_REPORTER_ENABLED=true` in that file and restart the service. The installer does not overwrite an existing environment file.

The collector stores a bounded sample stream in the local SQLite database. The «Радионаблюдения» tab can now build a regional report from the stored spots. The default QTH is KP50DB and the default radius is 100 km; both can be changed in the «Настройки» tab and are saved in the current browser. The report uses the last six hours of stored data and keeps TX and RX independent. It shows band/mode totals, unique local stations, latest observations, distance and bearing to the remote station, plus distance to the local station. The locator coordinates refer to the centre of the Maidenhead cell, so distances are approximate. The collector still subscribes only to 20 m FT8; regional filtering does not expand the MQTT feed.


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
