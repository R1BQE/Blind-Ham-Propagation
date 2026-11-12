# Production update design

## Goal

Keep one operator command:

```sh
bp update
```

The command updates application code, the isolated Python environment, pinned dependencies, and the managed Apache/systemd configuration. It does not ask the operator to run a sequence of manual deployment commands.

## Deliberately small deployment model

There are only two deployment operations:

1. **One-time migration** from the current in-place installation to the release layout. This is separate because the current service and Apache configuration point directly at `/var/www/html/blind-prop`.
2. **Normal update** after migration. Prepare a new release, test it, switch one symlink, restart, and verify. If verification fails, switch back to the previous release and restore any configuration files changed by that attempt.

The normal update does not move the database or settings and does not copy the live project tree.

## Filesystem layout

```text
/var/www/html/blind-prop/
  .git/                 # deployment Git metadata, retained outside releases
  releases/
    <full-commit-sha>/
      .venv/
      backend/
      frontend/
      ...
  current -> releases/<full-commit-sha>
  data/                 # persistent SQLite database
  logs/                 # persistent logs
  backups/              # timestamped pre-change snapshots
  settings.ini          # persistent MQTT settings
```

Each release has its own virtual environment. The database, settings, logs, and backups are never part of a release and are never deleted by normal update or rollback.

## Normal update transaction

1. Acquire one `flock` lock.
2. Check root privileges, required commands, current symlink, active service, local health, and a clean deployment Git checkout.
3. Fetch `origin/main` and resolve the exact target commit.
4. Create a release directory for that commit. If it already exists and is valid, reuse it; otherwise populate it from the target Git commit.
5. Create its venv, install `requirements-vds.lock`, install the application, and run the test suite.
6. Validate the candidate systemd unit and Apache fragment. Back up live config files before replacing them. Do not touch the main HTTPS VirtualHost.
7. Atomically switch `current` to the candidate release, reload systemd/Apache only when their managed config changed, and restart the service.
8. Require local health to return `status=ok`; also check public health and report its result.
9. If a required check fails, restore the previous symlink and any config files changed in this transaction, reload affected services, restart the previous release, and verify it.
10. Keep the previous release and backups. Pruning old releases/backups is a separate explicit maintenance operation, not part of update.

## Database migrations

There are currently no formal database migration files or migration runner. Therefore the first updater version must not attempt to infer migrations by searching source diffs. It must preserve the existing SQLite file and reject a release that declares a database migration until an explicit migration mechanism exists.

When migrations are introduced, they will be a separate, explicit step with a pre-migration SQLite backup and a tested recovery procedure. A normal code rollback must not restore an older database snapshot and discard new PSK Reporter observations.

## One-time migration

The migration script must:
- verify the existing installation and service are healthy;
- verify the exact live systemd unit and Apache fragment match the audited production configuration;
- create and integrity-check a SQLite backup using SQLite's backup API;
- back up `settings.ini`, the systemd unit, and Apache fragment;
- prepare the first release and its venv before changing the live service;
- switch systemd and Apache to the stable `current` path;
- validate both configurations before applying them;
- perform the switch and health checks;
- restore the original unit, Apache fragment, service paths, and original layout on failure.

It must refuse to proceed if the live configuration differs from the audited expected configuration. No wildcard overwrite and no guessed paths.

## Explicit non-goals

- No Docker, Kubernetes, database server, or external deployment service.
- No automatic cleanup of old releases or backups.
- No changes to the HTTPS VirtualHost, certificates, domain, Apache modules, firewall, or DNS.
- No destructive database rollback on an ordinary application failure.
- No deployment from an arbitrary branch or unverified short commit.
