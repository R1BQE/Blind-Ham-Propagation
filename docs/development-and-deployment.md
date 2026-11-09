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
