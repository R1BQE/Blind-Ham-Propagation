# Production updates on the Debian VDS

The production installation stays in its existing directory:

`/var/www/html/blind-prop`

There is no release directory tree, no `current` symlink, and no separate virtual environment per version. The existing `.venv`, database, settings file, logs, Apache VirtualHost and service account remain in place.

## First transition from the legacy updater

The production VDS may already have an older `/usr/local/sbin/bp` dispatcher. Do not overwrite it before the new updater has been staged and reviewed.

After the repository changes are merged and the server has fetched `origin/main`, prepare a separate bootstrap copy as root:

```sh
git -C /var/www/html/blind-prop show origin/main:scripts/bp > /tmp/bp-bootstrap
bash -n /tmp/bp-bootstrap
install -o root -g root -m 0755 /tmp/bp-bootstrap /usr/local/sbin/bp-bootstrap
rm -f /tmp/bp-bootstrap
```

The bootstrap is deliberately installed under a different name. The legacy `/usr/local/sbin/bp` remains untouched until the first update has passed its tests, configuration validation, service restart and local health check. When invoked by its absolute path as `/usr/local/sbin/bp-bootstrap update`, the successful bootstrap atomically replaces the legacy dispatcher with a symlink to `/var/www/html/blind-prop/scripts/bp`. If the update fails, the legacy dispatcher remains in place.

Do not run the initial update until the separate production preflight and backup checks have been reviewed.

## Commands

- `bp status` — show the checked-out commit, service state, local health and saved rollback commit.
- `bp update` — fast-forward from `origin/main`, install pinned dependencies only when `requirements-vds.lock` changes, run tests, validate changed systemd/Apache files, restart and check health.
- `bp rollback` — return to the previous successfully deployed commit and restore the matching dependencies/configuration.

Run commands as root. The updater takes an exclusive lock and refuses to run if tracked files have local modifications or the checkout is not on `main`. It never stashes or discards local changes.

## What is updated

- Backend and frontend: `git pull --ff-only origin main`.
- Python dependencies: installed from `requirements-vds.lock` only when that file changes.
- systemd: updated only when the tracked unit template differs from the installed unit; checked with `systemd-analyze verify`.
- Apache: updated only when the tracked fragment differs from the installed fragment; checked with `apachectl configtest` and gracefully reloaded only when changed.
- The existing HTTPS VirtualHost, certificates, DNS, firewall and unrelated Apache configuration are not changed.

The updater runs `pytest` before restarting. A successful local check is required at `http://127.0.0.1:8765/api/v1/health`. The public health URL is checked afterward for information but a temporary external failure does not undo a healthy local deployment.

## Rollback and data

Before changing code or configuration, the updater remembers the previous Git commit and keeps copies of any replaced Apache/systemd files under `backups/`. If dependency installation, tests, configuration validation, restart or local health check fails, it returns to the previous commit and restores changed configuration files.

The PSK Reporter SQLite database is a temporary bounded cache, not durable user data. It can be rebuilt from new observations and is deliberately not backed up or restored by the updater. Ordinary code rollback leaves the current database file alone; it does not replace it with an older snapshot. The application itself limits the cache to 50,000 records and applies its configured age retention.

The updater does not overwrite `settings.ini`, `data/` or `logs/`. Old config backups are retained; cleanup is a separate manual task.

## Important

The existing `/usr/local/sbin/bp-update` is the old updater and must not be used for production updates. Install and use the new `bp` command instead. The repository installer `scripts/install_vds.sh` is for initial installation only; it is not an update command.
