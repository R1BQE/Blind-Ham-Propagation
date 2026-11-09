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

The first pilot stores a bounded sample stream in the local SQLite database. It is for measuring connection stability and feed volume, not yet for regional statistics. The 100 km TX/RX geographic filters and multi-band subscription must be added only after the QTH settings and observed message rate are accounted for.
