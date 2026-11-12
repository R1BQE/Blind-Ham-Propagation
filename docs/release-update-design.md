# Production update design

## Decision

Use a simple in-place deployment. Keep the existing project directory, existing virtual environment, service account, Apache layout and runtime data paths. Do not introduce versioned release directories, symlinks, worktrees, containers or a second deployment environment.

The operator interface is three commands:

- `bp update`
- `bp rollback`
- `bp status`

## Update flow

1. Take an exclusive lock.
2. Verify root privileges, the existing project, the virtual environment, branch `main`, and a clean tracked working tree.
3. Verify the current service is active and its local health endpoint responds.
4. Record the current full Git commit.
5. Run `git pull --ff-only origin main`.
6. If `requirements-vds.lock` changed, install the pinned dependencies into the existing `.venv`. Otherwise leave the environment untouched.
7. Run the test suite.
8. Compare tracked systemd and Apache templates with their live files. Only changed files are backed up, validated and installed.
9. Reload systemd/Apache only if their respective configuration changed.
10. Restart the backend and require the local health endpoint to report `status=ok`.
11. Save the previous commit as the manual rollback target.

Any failure after the Git update triggers an attempt to restore the previous commit, its pinned dependencies and any configuration files changed during that update. The old code remains available in Git; no release directory copies are needed.

## Rollback

`bp rollback` returns to the previous successfully deployed commit. It installs the matching lock-file dependencies if needed, runs tests, restores matching tracked configuration and performs the same restart and local health check. If rollback validation fails, it attempts to return to the version that was active before the rollback command.

## Database policy

PSK Reporter SQLite is a bounded, temporary cache of observations. It is not durable user data and does not need a backup for ordinary application updates. The updater never copies or restores the database. It leaves the live database in place during code rollback; new observations are not discarded by restoring an older snapshot. The application owns cache expiry and the 50,000-record limit.

If the application later requires a schema migration, it must be implemented explicitly and tested. The updater must not guess migrations by searching source diffs.

## Persistent files

- `settings.ini`: never overwritten by update.
- `data/`: never overwritten or restored by update/rollback.
- `logs/`: left in place.
- `backups/`: stores only replaced systemd/Apache configuration snapshots; no database copies.

## Scope and safety

The updater may manage only:

- `/etc/systemd/system/blind-ham-propagation.service`
- `/etc/apache2/conf-available/blind-ham-propagation.conf`

It must not edit the main HTTPS VirtualHost, certificates, DNS, firewall, unrelated Apache configuration or other services. The existing `bp-update` script is not reused.
