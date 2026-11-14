# Development, installation, and deployment

**Language:** [Русский](../development-and-deployment.md) | English

## Local development

Python 3.11 or newer is required. Create a virtual environment and install development dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Debian/Linux:
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

On Windows, use `run-windows.bat` for normal local startup. It updates the local code, prepares the environment, starts the backend, and opens the application. Starting Uvicorn manually does not replace all lifecycle behavior provided by the local launcher.

## Production VDS

The current production installation is located at:

`/var/www/html/blind-prop`

The application runs as the systemd service `blind-ham-propagation`. Uvicorn listens on `127.0.0.1:8765` only; public requests are served through the Apache reverse proxy. Do not expose the Uvicorn port directly to the internet.

The existing installation uses one working directory, one `.venv`, local settings, a database, and logs. It does not use separate release directories or a `current` symlink.

## Manual update commands

Run these commands as root:

- `bp status` — shows the checked-out Git commit, branch, service state, local health check, and rollback commit.
- `bp update` — fast-forwards from `origin/main`, installs pinned dependencies only if `requirements-vds.lock` changes, runs tests, validates changed systemd/Apache configuration, restarts the service, and checks the local health endpoint.
- `bp rollback` — returns to the previous successfully deployed commit and restores matching dependencies/configuration.

A normal manual update can be performed as follows:

```bash
bp status
bp update
bp status
```

The updater uses an exclusive lock and refuses to run if tracked files have local modifications or the checkout is not on branch `main`. It never stashes or discards local changes. Ensure the working tree is clean before starting.

## What gets updated

- Backend and frontend: fast-forward from `origin/main`.
- Python dependencies: from `requirements-vds.lock`, only when the lock file changes.
- systemd: only when the tracked service template differs from the installed unit; validated with `systemd-analyze verify`.
- Apache: only when the tracked fragment differs from the installed fragment; validated with `apachectl configtest` and gracefully reloaded after a change.

The existing HTTPS VirtualHost, certificates, DNS, firewall, and unrelated Apache configuration are not replaced.

The updater runs pytest before restarting. A successful local check at `http://127.0.0.1:8765/api/v1/health` is required. The public health endpoint is checked additionally; a temporary external failure does not undo a successful local deployment.

## Rollback and data preservation

Before changing code or configuration, the updater records the previous Git commit. When Apache/systemd files are replaced, copies are saved under `backups/`. If dependency installation, tests, configuration validation, restart, or the local health check fails, the updater attempts to restore the previous commit and changed configuration files. A successful rollback is confirmed by checking code, configuration, dependencies, and local health again.

The PSK Reporter SQLite database is a temporary bounded cache, not durable user data. It can be rebuilt from new observations and is deliberately not backed up or restored by the updater. A normal code rollback leaves the current database file in place and does not replace it with an older snapshot. The application limits the cache to 50,000 records and applies its configured age retention.

The updater does not overwrite `settings.ini`, `data/`, or `logs/`. Old configuration backups are retained; cleaning them up is a separate manual task.

## Local settings

The `settings.ini` file is stored in the repository root on each machine and must not be committed to Git. It contains local PSK Reporter collector settings, primarily `[psk_reporter] enabled`. When enabled, the MQTT collector starts with the backend service and continuously receives all supported bands and modes. The legacy `topics` option in this file is no longer used. For temporary diagnostic restrictions, an administrator may set the `PSK_REPORTER_TOPICS` environment variable. Website `bands` and `modes` filters apply only to an individual report and never change the shared feed.

The installer creates an initial `settings.ini` if one does not already exist. Existing settings are preserved during updates.

## Initial installation

`scripts/install_vds.sh` is intended only for the initial installation on a Debian VDS. It creates the system user and service, virtual environment, installs dependencies from `requirements-vds.lock`, prepares runtime directories, and creates initial settings.

If the `blind-ham-propagation` service is already installed, the script refuses to perform another installation and directs the operator to `bp update`. Do not use the installer to update an existing server.

## Diagnostics

- Service status: `systemctl status blind-ham-propagation`.
- Service log: `journalctl -u blind-ham-propagation -f`.
- Local API health: `curl --fail http://127.0.0.1:8765/api/v1/health`.
- Updater status: `bp status`.

After a critical automatic rollback error, do not assume the server is recovered until the Git commit, dependencies, configuration files, systemd service, and local health endpoint have all been checked independently.
