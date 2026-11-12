"""HamQSL solar XML collector with a shared one-hour cache."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx

URL = "https://www.hamqsl.com/solarxml.php"
CACHE_TTL_SECONDS = 3600
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_cache: dict[str, Any] | None = None
_cache_expires_at = 0.0
_cache_lock = asyncio.Lock()


def _element_to_value(element: ElementTree.Element) -> Any:
    """Convert XML nodes to JSON-safe values without discarding attributes."""
    children = list(element)
    attributes = {f"@{key}": value for key, value in element.attrib.items()}
    value = (element.text or "").strip()
    if not children:
        if attributes:
            if value:
                attributes["#text"] = value
            return attributes
        return value

    result: dict[str, Any] = dict(attributes)
    for child in children:
        child_value = _element_to_value(child)
        if child.tag in result:
            current = result[child.tag]
            if not isinstance(current, list):
                result[child.tag] = [current]
            result[child.tag].append(child_value)
        else:
            result[child.tag] = child_value
    if value:
        result["#text"] = value
    return result


def parse_solar_xml(xml_text: str) -> dict[str, Any]:
    """Parse HamQSL XML and preserve all supplied fields and tables."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("HamQSL вернул некорректный XML.") from exc
    parsed = _element_to_value(root)
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("HamQSL вернул пустой или неизвестный формат XML.")
    return parsed


async def get_hamqsl_data() -> dict[str, Any]:
    """Return HamQSL data, reusing one cached response for 60 minutes."""
    global _cache, _cache_expires_at
    now = time.monotonic()
    if _cache is not None and now < _cache_expires_at:
        return {**_cache, "cache": {"hit": True, "ttl_seconds": CACHE_TTL_SECONDS}}

    async with _cache_lock:
        now = time.monotonic()
        if _cache is not None and now < _cache_expires_at:
            return {**_cache, "cache": {"hit": True, "ttl_seconds": CACHE_TTL_SECONDS}}

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Blind-Ham-Propagation/1.0)",
            "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
            response = await client.get(URL)
            response.raise_for_status()
            xml_text = response.text

        payload = {
            "source": "HamQSL",
            "source_url": URL,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "data": parse_solar_xml(xml_text),
        }
        _cache = payload
        _cache_expires_at = time.monotonic() + CACHE_TTL_SECONDS
        return {**payload, "cache": {"hit": False, "ttl_seconds": CACHE_TTL_SECONDS}}


def clear_hamqsl_cache() -> None:
    """Clear cached data; intended for tests and explicit maintenance."""
    global _cache, _cache_expires_at
    _cache = None
    _cache_expires_at = 0.0
