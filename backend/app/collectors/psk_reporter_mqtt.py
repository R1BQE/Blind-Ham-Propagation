"""Controlled PSK Reporter MQTT collector.

The first production-safe stage listens to a deliberately narrow topic filter.
It does not subscribe to the complete worldwide feed by default.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.app.services.psk_reporter import SpotFormatError, parse_spot
from backend.app.services.spot_store import SpotStore

logger = logging.getLogger(__name__)

DEFAULT_TOPIC_FILTERS = ("pskr/filter/v2/20m/FT8/#",)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MQTTConfig:
    enabled: bool = False
    host: str = "mqtt.pskreporter.info"
    port: int = 1884
    keepalive: int = 60
    topic_filters: tuple[str, ...] = DEFAULT_TOPIC_FILTERS

    @classmethod
    def from_environment(cls) -> "MQTTConfig":
        raw_topics = os.getenv("PSK_REPORTER_TOPICS", "").strip()
        if raw_topics:
            topics = tuple(item.strip() for item in raw_topics.split(",") if item.strip())
        else:
            topics = DEFAULT_TOPIC_FILTERS

        if not topics:
            raise ValueError("PSK_REPORTER_TOPICS не содержит MQTT-фильтров.")
        if any(not item.startswith("pskr/filter/v2/") for item in topics):
            raise ValueError("Разрешены только MQTT-фильтры pskr/filter/v2/.")

        return cls(
            enabled=_env_bool("PSK_REPORTER_ENABLED"),
            host=os.getenv("PSK_REPORTER_HOST", "mqtt.pskreporter.info").strip(),
            port=int(os.getenv("PSK_REPORTER_PORT", "1884")),
            keepalive=int(os.getenv("PSK_REPORTER_KEEPALIVE", "60")),
            topic_filters=topics,
        )


class PSKReporterCollector:
    """Receive, normalize and persist a bounded stream of PSK Reporter spots."""

    def __init__(
        self,
        config: MQTTConfig | None = None,
        *,
        store: SpotStore | Any | None = None,
    ) -> None:
        self.config = config or MQTTConfig.from_environment()
        self.store = store
        self._client: Any = None
        self._lock = threading.Lock()
        self._stopping = False
        self._state = "disabled" if not self.config.enabled else "idle"
        self._messages_received = 0
        self._spots_saved = 0
        self._duplicates = 0
        self._invalid_messages = 0
        self._errors = 0
        self._last_message_at: str | None = None
        self._last_spot_at: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if not self.config.enabled:
            self._state = "disabled"
            return

        if self.store is None:
            self.store = SpotStore()

        try:
            import paho.mqtt.client as mqtt

            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"blind-ham-prop-{uuid.uuid4().hex[:12]}",
                protocol=mqtt.MQTTv311,
            )
            client.tls_set()
            client.reconnect_delay_set(min_delay=1, max_delay=60)
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            self._client = client
            self._state = "connecting"
            client.connect_async(
                self.config.host,
                self.config.port,
                self.config.keepalive,
            )
            client.loop_start()
        except Exception as exc:
            self._record_error(exc)
            self._state = "error"
            logger.exception("Не удалось запустить PSK Reporter MQTT collector")

    def stop(self) -> None:
        self._stopping = True
        client = self._client
        if client is not None:
            try:
                client.disconnect()
            finally:
                client.loop_stop()
        self._state = "stopped"

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            self._record_error(f"MQTT connection rejected: {reason_code}")
            self._state = "error"
            return

        try:
            for topic_filter in self.config.topic_filters:
                result, _message_id = client.subscribe(topic_filter, qos=0)
                if result != 0:
                    raise RuntimeError(
                        f"Не удалось подписаться на MQTT-топик: {topic_filter} (код {result})"
                    )
            self._state = "connected"
            logger.info(
                "PSK Reporter MQTT подключён; подписки: %s",
                ", ".join(self.config.topic_filters),
            )
        except Exception as exc:
            self._record_error(exc)
            self._state = "error"
            logger.exception("Ошибка подписки PSK Reporter MQTT")

    def _on_disconnect(
        self,
        client: Any,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if not self._stopping:
            self._state = "reconnecting"
            if getattr(reason_code, "is_failure", False):
                self._record_error(f"MQTT disconnected: {reason_code}")

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        self._handle_message(message.topic, message.payload)

    def _handle_message(self, topic: str, payload: bytes | str) -> None:
        now = int(time.time())
        with self._lock:
            self._messages_received += 1
            self._last_message_at = datetime.fromtimestamp(
                now, tz=timezone.utc
            ).isoformat()

        try:
            spot = parse_spot(topic, payload)
        except SpotFormatError:
            with self._lock:
                self._invalid_messages += 1
            return

        try:
            inserted = self.store.add_spot(spot, received_at=now)
        except Exception as exc:
            self._record_error(exc)
            logger.exception("Не удалось сохранить спот PSK Reporter")
            return

        with self._lock:
            if inserted:
                self._spots_saved += 1
                self._last_spot_at = datetime.fromtimestamp(
                    spot["observed_at"], tz=timezone.utc
                ).isoformat()
            else:
                self._duplicates += 1

    def _record_error(self, error: Any) -> None:
        message = str(error)
        with self._lock:
            self._errors += 1
            self._last_error = message[:500]

    def status(self) -> dict[str, Any]:
        with self._lock:
            result = {
                "enabled": self.config.enabled,
                "state": self._state,
                "broker": self.config.host,
                "port": self.config.port,
                "transport": "MQTT over TLS",
                "topic_filters": list(self.config.topic_filters),
                "messages_received": self._messages_received,
                "spots_saved": self._spots_saved,
                "duplicates": self._duplicates,
                "invalid_messages": self._invalid_messages,
                "errors": self._errors,
                "last_message_at": self._last_message_at,
                "last_spot_at": self._last_spot_at,
                "last_error": self._last_error,
            }

        if self.store is not None:
            try:
                result["stored_spots"] = self.store.count()
            except Exception as exc:
                result["stored_spots"] = None
                result["storage_error"] = str(exc)[:300]
        else:
            result["stored_spots"] = 0
        return result
