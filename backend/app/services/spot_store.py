"""SQLite storage for a bounded, deduplicated PSK Reporter spot history."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_RETENTION_SECONDS = 6 * 60 * 60
DEFAULT_MAX_RECORDS = 50_000


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

    def _initialize(self) -> None:
        with self._connect() as connection:
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

    def _prune_connection(self, connection: sqlite3.Connection, now: int) -> int:
        cutoff = now - self.retention_seconds
        cursor = connection.execute(
            "DELETE FROM spots WHERE observed_at < ? OR received_at < ?",
            (cutoff, cutoff),
        )
        deleted = cursor.rowcount
        cursor = connection.execute(
            """
            DELETE FROM spots
            WHERE id IN (
                SELECT id FROM spots
                ORDER BY observed_at DESC, id DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (self.max_records,),
        )
        return deleted + cursor.rowcount

    def add_spot(self, spot: dict[str, Any], *, received_at: int | None = None) -> bool:
        """Insert one normalized spot; return False when it is a duplicate."""
        required = ("band", "mode", "tx_call", "rx_call", "frequency_hz", "observed_at")
        missing = [key for key in required if spot.get(key) is None]
        if missing:
            raise ValueError("В споте отсутствуют обязательные поля: " + ", ".join(missing))

        observed_at = int(spot["observed_at"])
        received = int(time.time()) if received_at is None else int(received_at)
        values = (
            self._dedupe_key(spot),
            observed_at,
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
        with self._connect() as connection:
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
            self._prune_connection(connection, received)
            return cursor.rowcount == 1

    def prune(self, *, now: int | None = None) -> int:
        """Delete expired rows and enforce the maximum history size."""
        current = int(time.time()) if now is None else int(now)
        with self._connect() as connection:
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
            self._prune_connection(connection, current)
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

    def count(self) -> int:
        """Return the current number of stored observations."""
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM spots").fetchone()
            return int(row["total"])
