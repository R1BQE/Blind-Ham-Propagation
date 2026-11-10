"""PSK Reporter MQTT topic and spot-payload normalization.

This module deliberately contains no network client. It keeps the public feed's
wire format isolated and testable before enabling a long-running MQTT consumer.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


TOPIC_PREFIX = ("pskr", "filter", "v2")
TOPIC_FIELDS = (
    "band",
    "mode",
    "tx_call",
    "rx_call",
    "tx_grid",
    "rx_grid",
    "tx_dxcc",
    "rx_dxcc",
)


class SpotFormatError(ValueError):
    """Raised when an MQTT topic or spot payload is malformed."""


def parse_spot(topic: str, payload: bytes | str) -> dict[str, Any]:
    """Normalize one PSK Reporter v2 MQTT message.

    The topic contains band/mode/callsigns/locators/DXCC identifiers; the JSON
    payload contains frequency, SNR, timestamps and sequence number.
    """
    parts = topic.split("/")
    if len(parts) != 11 or tuple(parts[:3]) != TOPIC_PREFIX:
        raise SpotFormatError("Unsupported PSK Reporter MQTT topic")

    topic_data = dict(zip(TOPIC_FIELDS, parts[3:]))
    try:
        raw = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpotFormatError("Invalid PSK Reporter JSON payload") from exc

    if not isinstance(raw, dict):
        raise SpotFormatError("PSK Reporter payload must be a JSON object")

    # The v2 topic carries only a four-character grid square. The JSON payload
    # may include the more precise station locator in sl/rl; prefer it when present.
    for topic_key, payload_key in (("tx_grid", "sl"), ("rx_grid", "rl")):
        payload_locator = raw.get(payload_key)
        if isinstance(payload_locator, str) and payload_locator.strip():
            topic_data[topic_key] = payload_locator.strip()

    try:
        frequency_hz = int(raw["f"])
        reported_at = int(raw["t"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SpotFormatError("Spot is missing a valid frequency or timestamp") from exc

    tx_started_at = raw.get("t_tx")
    try:
        tx_started_at = int(tx_started_at) if tx_started_at is not None else None
    except (TypeError, ValueError):
        tx_started_at = None

    snr = raw.get("rp")
    try:
        snr = float(snr) if snr is not None else None
    except (TypeError, ValueError):
        snr = None

    return {
        **topic_data,
        "frequency_hz": frequency_hz,
        "snr_db": snr,
        "reported_at": reported_at,
        "tx_started_at": tx_started_at,
        "observed_at": tx_started_at or reported_at,
        "sequence": raw.get("sq"),
    }


def spot_freshness(
    spot: dict[str, Any],
    *,
    now: datetime | None = None,
    fresh_seconds: int = 15 * 60,
    recent_seconds: int = 60 * 60,
) -> dict[str, Any]:
    """Classify spot age without treating old reports as current conditions."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    observed_at = int(spot["observed_at"])
    age = max(0, int(current.timestamp()) - observed_at)
    if age <= fresh_seconds:
        status = "fresh"
    elif age <= recent_seconds:
        status = "recent"
    else:
        status = "stale"

    return {
        "status": status,
        "age_seconds": age,
        "observed_at_utc": datetime.fromtimestamp(
            observed_at, tz=timezone.utc
        ).isoformat(),
    }
