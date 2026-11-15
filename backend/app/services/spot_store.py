"""SQLite storage for a bounded, deduplicated PSK Reporter spot history."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
import time
from pathlib import Path
from typing import Any

DEFAULT_RETENTION_SECONDS = 6 * 60 * 60
DEFAULT_MAX_RECORDS = 5_000_000


def default_database_path() -> Path:
    """Return the repository data directory without creating it on import."""
    return Path(__file__).resolve().parents[3] / "data" / "psk_reporter.sqlite3"


class SpotStore:
    """Persist normalized spots while bounding age and total database size."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        retention_seconds: int = DEFAULT_RETENTION_SECONDS,
        max_records: int = DEFAULT_MAX_RECORDS,
    ) -> None:
        if retention_seconds <= 0:
            raise ValueError("Срок хранения должен быть положительным.")
        if max_records <= 0:
            raise ValueError("Лимит записей должен быть положительным.")
        self.database_path = Path(database_path) if database_path else default_database_path()
        self.retention_seconds = int(retention_seconds)
        self.max_records = int(max_records)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS spots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    observed_at INTEGER NOT NULL,
                    received_at INTEGER NOT NULL,
                    band TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    tx_call TEXT NOT NULL,
                    rx_call TEXT NOT NULL,
                    tx_grid TEXT,
                    rx_grid TEXT,
                    tx_dxcc TEXT,
                    rx_dxcc TEXT,
                    frequency_hz INTEGER NOT NULL,
                    snr_db REAL,
                    sequence TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_spots_observed_at ON spots(observed_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_spots_band_observed ON spots(band, observed_at)"
            )
            # Regional reports filter by Maidenhead 4-character prefixes. These
            # expression indexes let SQLite seek directly to matching TX/RX
            # squares instead of evaluating substr() for every recent spot.
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_spots_tx_grid4_observed
                ON spots(upper(substr(tx_grid, 1, 4)), observed_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_spots_rx_grid4_observed
                ON spots(upper(substr(rx_grid, 1, 4)), observed_at)
                """
            )
            # Preserve support for coarse 2-character locators without making
            # the main prefix lookup fall back to a full time-range scan.
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_spots_tx_short_observed
                ON spots(observed_at)
                WHERE tx_grid IS NOT NULL AND length(tx_grid) < 4
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_spots_rx_short_observed
                ON spots(observed_at)
                WHERE rx_grid IS NOT NULL AND length(rx_grid) < 4
                """
            )

    @staticmethod
    def _dedupe_key(spot: dict[str, Any]) -> str:
        identity = {
            key: spot.get(key)
            for key in (
                "band", "mode", "tx_call", "rx_call", "tx_grid", "rx_grid",
                "frequency_hz", "observed_at", "sequence",
            )
        }
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _prepare_values(spot: dict[str, Any], received_at: int | None) -> tuple[Any, ...]:
        required = ("band", "mode", "tx_call", "rx_call", "frequency_hz", "observed_at")
        missing = [key for key in required if spot.get(key) is None]
        if missing:
            raise ValueError("В споте отсутствуют обязательные поля: " + ", ".join(missing))

        received = int(time.time()) if received_at is None else int(received_at)
        return (
            SpotStore._dedupe_key(spot),
            int(spot["observed_at"]),
            received,
            str(spot["band"]),
            str(spot["mode"]),
            str(spot["tx_call"]),
            str(spot["rx_call"]),
            spot.get("tx_grid"),
            spot.get("rx_grid"),
            str(spot["tx_dxcc"]) if spot.get("tx_dxcc") is not None else None,
            str(spot["rx_dxcc"]) if spot.get("rx_dxcc") is not None else None,
            int(spot["frequency_hz"]),
            float(spot["snr_db"]) if spot.get("snr_db") is not None else None,
            str(spot["sequence"]) if spot.get("sequence") is not None else None,
        )

    def _prune_connection(self, connection: sqlite3.Connection, now: int) -> int:
        cutoff = now - self.retention_seconds
        cursor = connection.execute(
            "DELETE FROM spots WHERE observed_at < ? OR received_at < ?",
            (cutoff, cutoff),
        )
        deleted = cursor.rowcount
        total = connection.execute(
            "SELECT COUNT(*) FROM spots"
        ).fetchone()[0]
        excess = total - self.max_records
        if excess > 0:
            cursor = connection.execute(
                """
                DELETE FROM spots
                WHERE id IN (
                    SELECT id FROM spots
                    ORDER BY observed_at ASC, id ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )
            deleted += cursor.rowcount
        return deleted

    def add_spots(
        self,
        spots: list[tuple[dict[str, Any], int | None]],
    ) -> tuple[int, int]:
        """Insert a batch in one transaction and prune once; return (inserted, duplicates)."""
        if not spots:
            return 0, 0

        prepared = [self._prepare_values(spot, received_at) for spot, received_at in spots]
        inserted = 0

        with self._connection() as connection:
            for values in prepared:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO spots (
                        dedupe_key, observed_at, received_at, band, mode,
                        tx_call, rx_call, tx_grid, rx_grid, tx_dxcc, rx_dxcc,
                        frequency_hz, snr_db, sequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                inserted += cursor.rowcount

        return inserted, len(prepared) - inserted

    def add_spot(self, spot: dict[str, Any], *, received_at: int | None = None) -> bool:
        """Insert one normalized spot; return False when it is a duplicate."""
        inserted, _duplicates = self.add_spots([(spot, received_at)])
        return inserted == 1

    def prune(self, *, now: int | None = None) -> int:
        """Delete expired rows and enforce the maximum history size."""
        current = int(time.time()) if now is None else int(now)
        with self._connection() as connection:
            return self._prune_connection(connection, current)

    def list_recent(
        self,
        *,
        now: int | None = None,
        limit: int = 1000,
        band: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return newest non-expired observations, optionally for one band."""
        if limit <= 0:
            raise ValueError("Лимит выборки должен быть положительным.")
        current = int(time.time()) if now is None else int(now)
        with self._connect() as connection:
            if band is None:
                rows = connection.execute(
                    """
                    SELECT * FROM spots
                    WHERE observed_at >= ?
                    ORDER BY observed_at DESC, id DESC LIMIT ?
                    """,
                    (current - self.retention_seconds, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM spots
                    WHERE observed_at >= ? AND band = ?
                    ORDER BY observed_at DESC, id DESC LIMIT ?
                    """,
                    (current - self.retention_seconds, band, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def iter_recent(
        self,
        *,
        now: int | None = None,
        since: int | None = None,
        batch_size: int = 5000,
    ):
        """Yield recent spots in bounded batches without loading the full history."""
        if batch_size <= 0:
            raise ValueError("Размер порции должен быть положительным.")
        current = int(time.time()) if now is None else int(now)
        cutoff = current - self.retention_seconds
        if since is not None:
            cutoff = max(cutoff, int(since))

        with self._connection() as connection:
            cursor = connection.execute(
                """
                SELECT * FROM spots
                WHERE observed_at >= ? AND observed_at <= ?
                ORDER BY observed_at DESC, id DESC
                """,
                (cutoff, current + 300),
            )
            while rows := cursor.fetchmany(batch_size):
                for row in rows:
                    yield dict(row)


    def iter_recent_for_region(
        self,
        *,
        locator: str,
        radius_km: float,
        now: int | None = None,
        since: int | None = None,
        bands: list[str] | None = None,
        modes: list[str] | None = None,
        batch_size: int = 5000,
    ):
        """Stream only recent spots with at least one endpoint in candidate grids.

        SQLite applies a conservative Maidenhead 4-character prefix filter.
        Exact great-circle distance remains the responsibility of the report
        builder, so the SQL prefilter cannot introduce false negatives.
        """
        from backend.app.services.geo_filter import locator_prefixes_for_radius

        if batch_size <= 0:
            raise ValueError("Размер порции должен быть положительным.")
        current = int(time.time()) if now is None else int(now)
        cutoff = current - self.retention_seconds
        if since is not None:
            cutoff = max(cutoff, int(since))
        prefixes = locator_prefixes_for_radius(locator, radius_km)
        if not prefixes:
            return

        placeholders = ",".join("?" for _ in prefixes)
        # UNION gives each endpoint its own indexable lookup. A single OR
        # expression makes SQLite fall back to idx_spots_observed_at and scan
        # every spot in the requested time window.
        query = f"""
            SELECT * FROM spots
            WHERE id IN (
                SELECT id FROM spots
                WHERE observed_at >= ? AND observed_at <= ?
                  AND upper(substr(tx_grid, 1, 4)) IN ({placeholders})
                UNION
                SELECT id FROM spots
                WHERE observed_at >= ? AND observed_at <= ?
                  AND upper(substr(rx_grid, 1, 4)) IN ({placeholders})
                UNION
                SELECT id FROM spots
                WHERE observed_at >= ? AND observed_at <= ?
                  AND tx_grid IS NOT NULL AND length(tx_grid) < 4
                UNION
                SELECT id FROM spots
                WHERE observed_at >= ? AND observed_at <= ?
                  AND rx_grid IS NOT NULL AND length(rx_grid) < 4
            )
        """
        parameters: list[Any] = [
            cutoff, current + 300, *prefixes,
            cutoff, current + 300, *prefixes,
            cutoff, current + 300,
            cutoff, current + 300,
        ]

        normalized_bands = sorted({value.strip().lower() for value in bands or [] if value.strip()})
        if normalized_bands:
            query += f" AND lower(band) IN ({','.join('?' for _ in normalized_bands)})"
            parameters.extend(normalized_bands)

        normalized_modes = sorted({value.strip().upper() for value in modes or [] if value.strip()})
        if normalized_modes:
            query += f" AND upper(mode) IN ({','.join('?' for _ in normalized_modes)})"
            parameters.extend(normalized_modes)

        query += " ORDER BY observed_at DESC, id DESC"
        with self._connection() as connection:
            cursor = connection.execute(query, parameters)
            while rows := cursor.fetchmany(batch_size):
                for row in rows:
                    yield dict(row)

    def count(self) -> int:
        """Return the current number of stored observations."""
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM spots").fetchone()
            return int(row["total"])
